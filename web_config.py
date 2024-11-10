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
import wifi  # For wifi operations
import os  # For checking file permissions
import logging
import sys
import json

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
    return render_template('config.html')  # Serve the HTML template

# Define route for network scanning endpoint
@app.route('/scan_networks', methods=['GET'])
def scan_networks():
    if not os.path.exists('/sys/class/net/wlan0'):
        return jsonify({'error': 'Wireless interface not found'}), 500
    try:
        # Run the Linux command 'iwlist wlan0 scan' to scan for WiFi networks
        # subprocess.check_output executes the command and captures the output
        scan_output = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan']).decode('utf-8')
        networks = []
        
        # Parse the command output line by line
        for line in scan_output.split('\n'):
            if 'ESSID:' in line:  # Look for lines containing network names
                # Extract the network name and clean it up
                ssid = line.split('ESSID:')[1].strip().strip('"')
                if ssid:  # Only add non-empty network names
                    networks.append(ssid)
        
        # Return the list of networks as JSON
        return jsonify({'networks': networks})
    except Exception as e:
        # If anything goes wrong, return the error as JSON with a 500 status code
        return jsonify({'error': str(e)}), 500

# Define route for WiFi credentials submission
@app.route('/connect', methods=['POST'])
def connect_wifi():
    try:
        data = request.get_json()
        
        # Validate input data
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
            
        ssid = data.get('ssid')
        password = data.get('password')
        
        # Validate SSID and password
        if not ssid:
            return jsonify({'success': False, 'error': 'Network name (SSID) is required'}), 400
        if not password or len(password) < 8:
            return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400
            
        # Check if wpa_supplicant.conf is writable
        if not os.access('/etc/wpa_supplicant/wpa_supplicant.conf', os.W_OK):
            return jsonify({'success': False, 'error': 'Permission denied: Cannot write to configuration file'}), 403

        # Write configuration with error handling
        try:
            with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as f:
                f.write(wpa_supplicant_conf)
        except IOError as e:
            return jsonify({'success': False, 'error': f'Failed to write configuration: {str(e)}'}), 500

        # Reconfigure wireless interface with error handling
        try:
            result = subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], 
                                 capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return jsonify({'success': False, 'error': f'Failed to reconfigure wireless: {result.stderr}'}), 500
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Timeout while reconfiguring wireless'}), 500
        
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f'Unexpected error in connect_wifi: {str(e)}')
        return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500

def check_ap_running():
    """Verify that the access point is running"""
    try:
        with open('/etc/hostapd/hostapd.conf', 'r') as f:
            content = f.read()
            return 'ssid=shelfWIFI' in content
    except:
        return False

if __name__ == '__main__':
    if not check_ap_running():
        print("Error: Access point is not configured. Please run accessPoint.py first.")
        sys.exit(1)
    
    print("Starting web configuration server...")
    app.run(host='192.168.4.1', port=80, debug=True)

# Need to add requirements check
def check_requirements():
    required_packages = ['flask', 'wifi']
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
        with open('wifi_status.json', 'r') as f:
            return json.load(f)
    except:
        return {'status': 'unknown'}