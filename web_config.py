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
3. Connect to 'shelfWIFI' network
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
        print("Starting WiFi connection process...")
        data = request.get_json()
        
        # Validate input data
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
            
        ssid = data.get('ssid')
        password = data.get('password')
        
        print(f"Attempting to connect to network: {ssid}")
        
        try:
            # Turn off WiFi
            print("Turning off WiFi...")
            subprocess.run(['sudo', 'rfkill', 'block', 'wifi'], check=True)
            time.sleep(2)
            
            # Turn WiFi back on
            print("Turning WiFi back on...")
            subprocess.run(['sudo', 'rfkill', 'unblock', 'wifi'], check=True)
            time.sleep(2)
            
            # Stop AP services
            print("Stopping AP services...")
            subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'], check=True)
            subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'], check=True)
            
            # Unmask and enable wpa_supplicant
            print("Configuring wpa_supplicant...")
            subprocess.run(['sudo', 'systemctl', 'unmask', 'wpa_supplicant'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'wpa_supplicant'], check=True)
            
            # Create wpa_supplicant configuration
            print("Writing wpa_supplicant configuration...")
            wpa_supplicant_conf = f'''ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}'''

            # Write the new configuration
            with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as f:
                f.write(wpa_supplicant_conf)
            
            # Restart networking services
            print("Restarting network services...")
            subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'], check=True)
            time.sleep(2)
            subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=True)
            subprocess.run(['sudo', 'systemctl', 'restart', 'wpa_supplicant'], check=True)
            subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=True)
            
            print("Waiting for connection...")
            time.sleep(10)  # Give more time for connection
            
            # Check if connection was successful
            result = subprocess.run(['iwgetid'], capture_output=True, text=True)
            if ssid in result.stdout:
                # Set up admin server
                setup_admin_server()
                
                return jsonify({'success': True, 'message': f'Successfully connected to {ssid}'})
            else:
                return jsonify({'success': False, 'error': 'Failed to connect to network'}), 500
            
        except subprocess.CalledProcessError as e:
            app.logger.error(f"Command failed: {str(e)}")
            
    except Exception as e:
        app.logger.error(f"Error in connect_wifi: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def check_ap_running():
    """Verify that the access point is running"""
    try:
        with open('/etc/hostapd/hostapd.conf', 'r') as f:
            content = f.read()
            return 'ssid=shelfWIFI' in content
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
        print("Error: Access point is not configured. Please run accessPoint.py first.")
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

def write_wpa_config(config_text):
    """Safely write wpa_supplicant configuration"""
    temp_file = '/tmp/wpa_supplicant.conf.tmp'
    try:
        with open(temp_file, 'w') as f:
            f.write(config_text)
        subprocess.run(['sudo', 'mv', temp_file, '/etc/wpa_supplicant/wpa_supplicant.conf'])
        subprocess.run(['sudo', 'chmod', '600', '/etc/wpa_supplicant/wpa_supplicant.conf'])
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise e

def signal_handler(signum, frame):
    """Handle cleanup on web server termination"""
    print("\nWeb server shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def setup_admin_server():
    """Setup and start the admin server"""
    try:
        print("Setting up admin server...")
        # Ensure avahi-daemon is installed
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'avahi-daemon'], check=True)
        
        # Start admin server in a new process
        subprocess.Popen(['sudo', 'python3', 'admin_server.py'])
        
        # Stop the current (config) server
        print("Stopping config server...")
        os._exit(0)
        
    except Exception as e:
        print(f"Error setting up admin server: {str(e)}")