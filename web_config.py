"""
Raspberry Pi WiFi Configuration Web Server

This script creates a web server that allows users to configure WiFi settings on a Raspberry Pi.
It works in conjunction with accessPoint.py to provide a complete WiFi setup solution.

Main Functions:
1. Serves a web interface on 192.168.4.1 (port 80)
2. Provides WiFi network scanning capabilities
3. Accepts and validates WiFi credentials
4. Configures the Raspberry Pi's wireless settings
5. Handles the transition from AP mode to client mode

Requirements:
- Flask: pip3 install flask
- Root privileges (sudo) for network operations
- Working wireless interface (wlan0)
- Access point must be running (via accessPoint.py)

Usage:
1. Start the access point using accessPoint.py
2. Run this script: sudo python3 web_config.py
3. Connect to 'PiConfigWiFi' network
4. Navigate to http://192.168.4.1 in a web browser

Error Handling:
- Validates user input on client and server side
- Provides feedback for network scanning errors
- Handles configuration file access errors
- Manages wireless interface reconfiguration failures

Security Notes:
- Runs on HTTP (not HTTPS) - suitable for initial setup only
- Requires root privileges for system configuration
- Credentials are transmitted in plain text
- Intended for initial setup only, not permanent operation

Author: Tom Sepe
Date: 11/10/2024
Version: 1.0
"""

from flask import Flask, render_template, request, jsonify
import subprocess
import os
import sys
import time
import logging

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/wifi_config.log')]
)

app = Flask(__name__)

def setup_admin_server():
    """Setup and start the admin server as a systemd service"""
    try:
        admin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'admin')
        admin_server_path = os.path.join(admin_dir, 'admin_server.py')
        
        if not all(os.path.exists(p) for p in [admin_dir, admin_server_path]):
            raise FileNotFoundError("Admin server files not found")
            
        service_content = f'''[Unit]
Description=Pi Admin Panel
After=network.target

[Service]
ExecStart=/usr/bin/python3 {admin_server_path}
WorkingDirectory={admin_dir}
User=root
Restart=always

[Install]
WantedBy=multi-user.target
'''
        
        with open('/tmp/pi-admin-panel.service', 'w') as f:
            f.write(service_content)
            
        subprocess.run(['sudo', 'mv', '/tmp/pi-admin-panel.service', 
                       '/etc/systemd/system/pi-admin-panel.service'], check=True)
        subprocess.run(['sudo', 'chmod', '644', '/etc/systemd/system/pi-admin-panel.service'], 
                      check=True)
        
        # Enable and start service
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'pi-admin-panel'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'pi-admin-panel'], check=True)
        
        logging.info("Admin server installed and started")
        os._exit(0)
        
    except Exception as e:
        logging.error(f"Admin server setup failed: {str(e)}")
        raise

# Define route for the main page ('/')
@app.route('/')
def index():
    """Serve the main configuration page"""
    if not os.path.exists('/etc/hostapd/hostapd.conf'):
        return "Error: Access point not configured. Run access_point.py first.", 500
    return render_template('config.html')

# Define route for network scanning endpoint
@app.route('/scan_networks')
def scan_networks():
    """Scan for available WiFi networks"""
    try:
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=True)
        time.sleep(1)
        
        result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], 
                              capture_output=True, text=True, check=True)
        
        networks = []
        for line in result.stdout.split('\n'):
            if 'ESSID:' in line:
                ssid = line.split('ESSID:"')[1].split('"')[0]
                if ssid and ssid not in networks:
                    networks.append(ssid)
                    
        return jsonify({'success': True, 'networks': sorted(networks)})
        
    except Exception as e:
        logging.error(f"Network scan failed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Define route for WiFi credentials submission
@app.route('/connect', methods=['POST'])
def connect_wifi():
    try:
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password')
        
        if not ssid or not password:
            raise ValueError("Missing SSID or password")

        # Write WPA supplicant configuration
        wpa_config = f'''
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}'''
        
        with open('/tmp/wpa_supplicant.conf', 'w') as f:
            f.write(wpa_config)
            
        subprocess.run(['sudo', 'mv', '/tmp/wpa_supplicant.conf', 
                       '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
        
        # Stop AP services and connect to WiFi
        services_to_stop = ['hostapd', 'dnsmasq']
        for service in services_to_stop:
            subprocess.run(['sudo', 'systemctl', 'stop', service], check=True)
            
        # Configure network interface
        subprocess.run(['sudo', 'ip', 'link', 'set', 'wlan0', 'down'], check=True)
        time.sleep(1)
        subprocess.run(['sudo', 'ip', 'link', 'set', 'wlan0', 'up'], check=True)
        subprocess.run(['sudo', 'systemctl', 'restart', 'wpa_supplicant'], check=True)
        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=True)
        
        # Wait for connection
        for _ in range(30):
            result = subprocess.run(['iwgetid'], capture_output=True, text=True)
            if ssid in result.stdout:
                # Test internet connectivity
                ping_test = subprocess.run(['ping', '-c', '1', '-W', '2', '8.8.8.8'])
                if ping_test.returncode == 0:
                    setup_admin_server()
                    return jsonify({'success': True})
            time.sleep(1)
            
        raise Exception("Failed to establish connection")
        
    except Exception as e:
        logging.error(f"WiFi connection failed: {str(e)}")
        restore_ap_mode()
        return jsonify({'success': False, 'error': str(e)}), 500

def restore_ap_mode():
    """Restore access point mode if connection fails"""
    try:
        subprocess.run(['sudo', 'systemctl', 'stop', 'dhcpcd'], check=True)
        subprocess.run(['sudo', 'ip', 'link', 'set', 'wlan0', 'down'], check=True)
        time.sleep(1)
        subprocess.run(['sudo', 'systemctl', 'start', 'hostapd'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'dnsmasq'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'dhcpcd'], check=True)
    except Exception as e:
        logging.error(f"Failed to restore AP mode: {str(e)}")

if __name__ == '__main__':
    if os.geteuid() != 0:
        sys.exit("This script must be run as root")
        
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    app.run(host='0.0.0.0', port=80)

