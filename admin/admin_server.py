from flask import Flask, render_template, jsonify, request
import subprocess
import os
import logging
from functools import wraps

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    filename='admin_server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.route('/')
def admin_panel():
    """Serve the admin panel"""
    try:
        return render_template('admin.html')
    except Exception as e:
        app.logger.error(f"Error serving admin panel: {str(e)}")
        return f"Error loading admin panel: {str(e)}", 500

@app.route('/api/status')
def get_status():
    """Get system status"""
    try:
        # Get system status
        wifi_status = subprocess.check_output(['iwconfig', 'wlan0']).decode()
        ip_addr = subprocess.check_output(['hostname', '-I']).decode().strip()
        hostname = subprocess.check_output(['hostname']).decode().strip()
        
        return jsonify({
            'success': True,
            'wifi_status': wifi_status,
            'ip_address': ip_addr,
            'hostname': hostname
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Make sure we're not using the same port as the config server
    app.run(host='0.0.0.0', port=80)
