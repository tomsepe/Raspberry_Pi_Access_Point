# Import necessary modules
from flask import Flask, render_template, request, jsonify  # Flask web framework components
import subprocess  # For running system commands (wifi scanning)
import wifi  # For wifi operations

# Create Flask application instance
app = Flask(__name__)

# Define route for the main page ('/')
@app.route('/')
def index():
    return render_template('config.html')  # Serve the HTML template

# Define route for network scanning endpoint
@app.route('/scan_networks', methods=['GET'])
def scan_networks():
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

# Run the Flask application if this file is run directly
if __name__ == '__main__':
    # Start the web server:
    # - host='192.168.4.1': Listen on the AP's IP address
    # - port=80: Use standard HTTP port
    # - debug=True: Enable debug mode for development
    app.run(host='192.168.4.1', port=80, debug=True)