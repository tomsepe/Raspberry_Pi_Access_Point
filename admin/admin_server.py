from flask import Flask, render_template, jsonify, request
import subprocess
import os
import logging
import sys

# Configure logging to both file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('admin_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create Flask app
app = Flask(__name__)

@app.route('/')
def admin_panel():
    """Serve the admin panel"""
    try:
        logging.info("Attempting to serve admin panel")
        logging.info(f"Current directory: {os.getcwd()}")
        logging.info(f"Template folder: {app.template_folder}")
        logging.info(f"Available templates: {os.listdir(app.template_folder)}")
        
        return render_template('admin.html')
    except Exception as e:
        logging.error(f"Error serving admin panel: {str(e)}")
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
    logging.info("Starting admin server...")
    logging.info(f"Current working directory: {os.getcwd()}")
    logging.info(f"Template folder path: {os.path.join(os.getcwd(), 'templates')}")
    app.run(host='0.0.0.0', port=80)
