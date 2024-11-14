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

# Configure logging
logging.basicConfig(
    filename='wifi_config.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create Flask application instance
app = Flask(__name__)

def setup_admin_server():
    """Setup and start the admin server"""
    try:
        print("Setting up admin server...")
        
        # Get the current script's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        admin_dir = os.path.join(current_dir, 'admin')
        admin_server_path = os.path.join(admin_dir, 'admin_server.py')
        
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
    if not os.path.exists('/etc/hostapd/hostapd.conf'):
        return "Error: Access point is not configured. Please run accessPoint.py first.", 500
    try:
        return render_template('config.html')
    except:
        # Fallback HTML if template is missing
        return '''
        <html>
            <head>
                <title>WiFi Configuration</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .container { max-width: 600px; margin: 0 auto; }
                    .form-group { margin-bottom: 15px; }
                    input { width: 100%; padding: 8px; margin-top: 5px; }
                    button { padding: 10px 20px; background: #007bff; color: white; border: none; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>WiFi Configuration</h1>
                    <div class="form-group">
                        <label for="ssid">Network Name:</label>
                        <input type="text" id="ssid" name="ssid" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button onclick="submitForm()">Connect</button>
                    <div id="status"></div>
                </div>
                <script>
                    function submitForm() {
                        const ssid = document.getElementById('ssid').value;
                        const password = document.getElementById('password').value;
                        
                        fetch('/connect', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                ssid: ssid,
                                password: password
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('status').innerText = 
                                data.success ? 'Connected successfully!' : 'Error: ' + data.error;
                        })
                        .catch(error => {
                            document.getElementById('status').innerText = 'Error: ' + error;
                        });
                    }
                </script>
            </body>
        </html>
        '''

# Define route for network scanning endpoint
@app.route('/scan_networks')
def scan_networks():
    try:
        # First, ensure interface is up and ready
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=True)
        time.sleep(1)  # Give interface time to come up
        
        # Try scanning up to 3 times
        for attempt in range(3):
            try:
                print(f"Scanning attempt {attempt + 1}...")
                # Use iwlist for scanning
                result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], 
                                     capture_output=True, 
                                     text=True,
                                     check=True)
                
                networks = []
                for line in result.stdout.split('\n'):
                    if 'ESSID:' in line:
                        # Extract SSID and remove quotes
                        ssid = line.split('ESSID:')[1].strip().strip('"')
                        if ssid and ssid != '\\x00' and ssid not in networks:
                            networks.append(ssid)
                
                return jsonify({'success': True, 'networks': networks})
                
            except subprocess.CalledProcessError as e:
                print(f"Scan attempt {attempt + 1} failed: {str(e)}")
                if attempt < 2:  # If not the last attempt
                    print("Waiting before retry...")
                    time.sleep(2)  # Wait before retrying
                    continue
                else:
                    raise  # Re-raise on final attempt
                    
    except Exception as e:
        error_msg = f"Error scanning networks: {str(e)}"
        print(error_msg)
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
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}'''
        
        # Write the configuration
        try:
            print("\n2. Writing wpa_supplicant configuration...")
            temp_file = '/tmp/wpa_supplicant.conf.tmp'
            with open(temp_file, 'w') as f:
                f.write(config_text)
            
            subprocess.run(['sudo', 'mv', temp_file, '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
            subprocess.run(['sudo', 'chmod', '600', '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
            print("   Configuration file written successfully")
            
        except Exception as e:
            print(f"   Error writing configuration: {str(e)}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise e
        
        try:
            print("\n3. Stopping access point services...")
            subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'], check=True)
            subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'], check=True)
            print("   AP services stopped")
            
            print("\n4. Reconfiguring wireless interface...")
            subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'], check=True)
            subprocess.run(['sudo', 'killall', 'wpa_supplicant'], check=False)
            time.sleep(2)
            print("   Interface down, wpa_supplicant killed")
            
            print("\n5. Starting wireless services...")
            subprocess.run(['sudo', 'systemctl', 'unmask', 'wpa_supplicant'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'wpa_supplicant'], check=True)
            subprocess.run(['sudo', 'systemctl', 'start', 'wpa_supplicant'], check=True)
            time.sleep(2)
            print("   wpa_supplicant service started")
            
            print("\n6. Bringing up interface...")
            subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=True)
            print("   Interface is up")
            
            print("\n7. Restarting DHCP client...")
            subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=True)
            time.sleep(2)
            print("   DHCP client restarted")
            
            # Add wpa_cli reconfigure
            print("\n8. Reconfiguring wpa_supplicant...")
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], check=True)
            print("   wpa_supplicant reconfigured")
            
        except Exception as e:
            print(f"   Error in network reconfiguration: {str(e)}")
            raise e
        
        print("\n9. Waiting for connection...")
        max_attempts = 12
        connected = False
        
        for attempt in range(max_attempts):
            try:
                # Check both connection and IP assignment
                result = subprocess.run(['iwgetid'], capture_output=True, text=True)
                ip_check = subprocess.run(['ip', 'addr', 'show', 'wlan0'], capture_output=True, text=True)
                
                print(f"\n   Connection check {attempt + 1}:")
                print(f"   Network status: {result.stdout.strip() if result.stdout.strip() else 'No network'}")
                print(f"   IP status: {'Has IP' if 'inet ' in ip_check.stdout else 'No IP'}")
                
                if ssid in result.stdout and 'inet ' in ip_check.stdout:
                    print(f"\n10. Successfully connected to {ssid}")
                    print("\n11. Setting up admin server...")
                    setup_admin_server()
                    connected = True
                    return jsonify({'success': True, 'message': f'Successfully connected to {ssid}'})
                
            except Exception as e:
                print(f"   Error checking connection: {str(e)}")
            
            time.sleep(5)
            print(f"   Connection attempt {attempt + 1}/{max_attempts}...")
        
        # If we get here without returning, connection failed
        print("\nFailed to connect to network after all attempts")
        return jsonify({
            'success': False, 
            'error': 'Failed to connect to network after timeout'
        }), 500
            
    except Exception as e:
        print(f"\nError in connect_wifi: {str(e)}")
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

# Then your main execution block
if __name__ == '__main__':
    if not check_requirements():
        print("Missing required packages. Please install them first.")
        sys.exit(1)
        
    if not check_ap_running():
        print("Error: Access point is not configured. Please run access_point.py first.")
        sys.exit(1)
    
    print("Starting web configuration server...")
    app.run(host='0.0.0.0', port=80, debug=True)

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
        with open('wifi_status.json', 'r') as f:
            return json.load(f)
    except:
        return {'status': 'unknown'}

def signal_handler(signum, frame):
    """Handle cleanup on web server termination"""
    print("\nWeb server shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def stop_web_server():
    """Stop any running web servers on port 80"""
    try:
        subprocess.run(['sudo', 'fuser', '-k', '80/tcp'], check=False)
        time.sleep(2)  # Give time for the server to stop
    except Exception as e:
        print(f"Error stopping web server: {str(e)}")