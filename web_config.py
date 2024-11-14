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

# Import necessary modules
from flask import Flask, render_template, request, jsonify  # Flask web framework components
import subprocess  # For running system commands (wifi scanning)
import os  # For checking file permissions
import logging
import sys
import json
import time
import signal

# Configure logging to both file and console
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG level
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/wifi_config.log'),
        logging.StreamHandler(sys.stdout)  # Add console output
    ]
)

# Create Flask application instance
app = Flask(__name__, 
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
)

def setup_admin_server():
    """Setup and start the admin server"""
    try:
        print("Setting up admin server...")
        
        # Get the current script's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        admin_dir = os.path.join(current_dir, 'admin')
        
        if not os.path.exists(admin_dir):
            raise FileNotFoundError(f"Admin directory not found: {admin_dir}")
            
        admin_server_path = os.path.join(admin_dir, 'admin_server.py')
        if not os.path.exists(admin_server_path):
            raise FileNotFoundError(f"Admin server script not found: {admin_server_path}")
            
        # Create systemd service file
        service_content = f'''[Unit]
Description=Pi Admin Panel
After=network.target

[Service]
ExecStart=/usr/bin/python3 {admin_server_path}
WorkingDirectory={admin_dir}
User=root
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
'''
        
        # Write service file
        service_path = '/etc/systemd/system/pi-admin-panel.service'
        with open('/tmp/pi-admin-panel.service', 'w') as f:
            f.write(service_content)
        
        # Move and set permissions
        subprocess.run(['sudo', 'mv', '/tmp/pi-admin-panel.service', service_path], check=True)
        subprocess.run(['sudo', 'chmod', '644', service_path], check=True)
        
        print("Enabling and starting admin server service...")
        # Reload systemd, enable and start service
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'pi-admin-panel'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'pi-admin-panel'], check=True)
        
        print("Admin server service installed and started")
        print("Exiting config server...")
        
        # Exit immediately
        os._exit(0)
        
    except Exception as e:
        print(f"Error setting up admin server: {str(e)}")
        raise e

# Define route for the main page ('/')
@app.route('/')
def index():
    """Serve the main configuration page"""
    if not os.path.exists('/etc/hostapd/hostapd.conf'):
        return "Error: Access point is not configured. Please run access_point.py first.", 500
    try:
        return render_template('config.html')
    except Exception as e:
        logging.error(f"Error rendering template: {str(e)}")
        return "Error: Could not load configuration page. Check logs for details.", 500

# Define route for network scanning endpoint
@app.route('/scan_networks')
def scan_networks():
    """Scan for available WiFi networks"""
    app.logger.debug("Scan networks endpoint called")  # Add debug logging
    try:
        # First, ensure interface is up and ready
        app.logger.debug("Bringing up wlan0 interface...")
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=True)
        time.sleep(1)
        
        # Try scanning up to 3 times
        for attempt in range(3):
            try:
                app.logger.debug(f"Scan attempt {attempt + 1}")
                # Use iwlist for scanning
                result = subprocess.run(
                    ['sudo', 'iwlist', 'wlan0', 'scan'], 
                    capture_output=True, 
                    text=True,
                    check=True
                )
                
                networks = []
                app.logger.debug(f"Raw scan output: {result.stdout}")  # Log raw output
                
                for line in result.stdout.split('\n'):
                    if 'ESSID:' in line:
                        ssid = line.split('ESSID:')[1].strip().strip('"')
                        if ssid and ssid != '\\x00' and ssid not in networks:
                            networks.append(ssid)
                
                app.logger.debug(f"Found networks: {networks}")  # Log found networks
                return jsonify({'success': True, 'networks': networks})
                
            except subprocess.CalledProcessError as e:
                app.logger.error(f"Scan attempt {attempt + 1} failed: {str(e)}")
                if attempt < 2:
                    app.logger.debug("Waiting before retry...")
                    time.sleep(2)
                    continue
                else:
                    raise
                    
    except Exception as e:
        error_msg = f"Error scanning networks: {str(e)}"
        app.logger.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 500

# Define route for WiFi credentials submission
@app.route('/connect', methods=['POST'])
def connect_wifi():
    try:
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password')
        
        if not ssid or not password:
            return jsonify({'success': False, 'error': 'Missing SSID or password'}), 400
            
        print(f"\n1. Starting connection process to: {ssid}")
            
        # Configure WiFi
        config_text = f'''
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
    scan_ssid=1
}}'''
        
        try:
            print("\n2. Writing wpa_supplicant configuration...")
            with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as f:
                f.write(config_text)
            subprocess.run(['sudo', 'chmod', '600', '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
            print("   Configuration file written successfully")
            
        except Exception as e:
            print(f"   Error writing configuration: {str(e)}")
            raise e
        
        try:
            print("\n3. Stopping network services...")
            subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'], check=True)
            subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'], check=True)
            subprocess.run(['sudo', 'systemctl', 'stop', 'dhcpcd'], check=True)
            print("   Services stopped")
            
            print("\n4. Reconfiguring network interface...")
            subprocess.run(['sudo', 'ip', 'link', 'set', 'wlan0', 'down'], check=True)
            subprocess.run(['sudo', 'killall', 'wpa_supplicant'], check=False)
            time.sleep(2)
            
            print("\n5. Starting wireless services...")
            subprocess.run(['sudo', 'ip', 'link', 'set', 'wlan0', 'up'], check=True)
            time.sleep(1)
            
            # Start wpa_supplicant with detailed output
            print("   Starting wpa_supplicant...")
            wpa_process = subprocess.run([
                'sudo',
                'wpa_supplicant',
                '-B',                # Run in background
                '-i', 'wlan0',       # Interface
                '-c', '/etc/wpa_supplicant/wpa_supplicant.conf',  # Config file
                '-d'                 # Debug output
            ], capture_output=True, text=True)
            print(f"   wpa_supplicant output: {wpa_process.stdout}")
            
            print("\n6. Starting DHCP client...")
            subprocess.run(['sudo', 'systemctl', 'start', 'dhcpcd'], check=True)
            time.sleep(3)
            
            print("\n7. Checking connection status...")
            max_attempts = 30  # Increase from 15 to 30 attempts
            connected = False
            
            for attempt in range(max_attempts):
                try:
                    # Check both connection and IP assignment
                    iwconfig = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
                    ifconfig = subprocess.run(['ifconfig', 'wlan0'], capture_output=True, text=True)
                    
                    print(f"\n   Connection check {attempt + 1}/{max_attempts}:")
                    print(f"   iwconfig output: {iwconfig.stdout.strip()}")
                    print(f"   ifconfig output: {ifconfig.stdout.strip()}")
                    
                    if ssid in iwconfig.stdout:
                        if 'inet ' in ifconfig.stdout:
                            print(f"\n8. Successfully connected to {ssid}")
                            
                            # Test internet connectivity with longer timeout
                            print("\n9. Testing internet connection...")
                            for ping_attempt in range(3):  # Try ping up to 3 times
                                print(f"   Ping attempt {ping_attempt + 1}/3...")
                                ping_test = subprocess.run(
                                    ['ping', '-c', '1', '-W', '5', '8.8.8.8'],  # 5 second timeout
                                    capture_output=True
                                )
                                if ping_test.returncode == 0:
                                    print("   Internet connection successful")
                                    connected = True
                                    break
                                time.sleep(2)
                            
                            if connected:
                                break
                            else:
                                print("   Warning: Internet connection failed, retrying...")
                                
                except Exception as e:
                    print(f"   Error checking connection: {str(e)}")
                
                print(f"   Waiting for connection... ({attempt + 1}/{max_attempts})")
                time.sleep(3)  # Increased from 2 to 3 seconds
                
            if not connected:
                raise Exception("Failed to establish network connection")
                
            print("\n10. Setting up admin server...")
            setup_admin_server()
            return jsonify({'success': True, 'message': f'Successfully connected to {ssid}'})
            
        except Exception as e:
            print(f"Error in network configuration: {str(e)}")
            raise e
            
    except Exception as e:
        print(f"\nError in connect_wifi: {str(e)}")
        restore_ap_mode()
        return jsonify({'success': False, 'error': str(e)}), 500

def check_ap_running():
    """Verify that the access point is running"""
    try:
        with open('/etc/hostapd/hostapd.conf', 'r') as f:
            content = f.read()
            return 'ssid=PiConfigWiFi' in content
    except:
        return False

# Add this function before the if __name__ == '__main__': block
def check_requirements():
    """Check if required packages are installed"""
    required_packages = ['flask']
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Missing required package: {package}")
            return False
    return True

def verify_connection(ssid):
    """Verify successful connection to network"""
    try:
        result = subprocess.run(['iwgetid'], capture_output=True, text=True)
        return ssid in result.stdout
    except:
        return False

def get_ap_status():
    """Read status from shared file"""
    try:
        with open('logs/wifi_status.json', 'r') as f:
            return json.load(f)
    except:
        return {'status': 'unknown'}

def signal_handler(signum, frame):
    """Handle cleanup on web server termination"""
    print("\nWeb server shutting down...")
    sys.exit(0)

def stop_web_server():
    """Stop any running web servers on port 80"""
    try:
        subprocess.run(['sudo', 'fuser', '-k', '80/tcp'], check=False)
        time.sleep(2)  # Give time for the server to stop
    except Exception as e:
        print(f"Error stopping web server: {str(e)}")

def restore_ap_mode():
    """Restore access point mode if client connection fails"""
    try:
        print("\nRestoring access point mode...")
        subprocess.run(['sudo', 'systemctl', 'stop', 'dhcpcd'], check=True)
        subprocess.run(['sudo', 'ip', 'link', 'set', 'wlan0', 'down'], check=True)
        subprocess.run(['sudo', 'killall', 'wpa_supplicant'], check=False)
        time.sleep(2)
        subprocess.run(['sudo', 'systemctl', 'start', 'hostapd'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'dnsmasq'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'dhcpcd'], check=True)
        print("Access point mode restored")
    except Exception as e:
        print(f"Error restoring AP mode: {str(e)}")

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
# Then your main execution block
if __name__ == '__main__':
    if not check_requirements():
        print("Missing required packages. Please install them first.")
        sys.exit(1)
        
    if not check_ap_running():
        print("Error: Access point is not configured. Please run access_point.py first.")
        sys.exit(1)
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    print("Starting web configuration server...")
    # Disable Flask's default logging
    app.logger.handlers = []
    app.logger.propagate = False
    # Use our custom logger
    app.logger.handlers.extend(logging.getLogger().handlers)
    
    app.run(host='0.0.0.0', port=80, debug=True)

