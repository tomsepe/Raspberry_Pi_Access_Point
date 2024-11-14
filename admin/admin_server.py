from flask import Flask, render_template, jsonify
import subprocess
import logging
import os
import sys
import time
import psutil

# Get the absolute path to the admin directory
ADMIN_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ADMIN_DIR)

# Configure logging to use the logs directory
logging.basicConfig(
    filename=os.path.join(PROJECT_ROOT, 'logs', 'admin_server.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create Flask app with correct template directory
app = Flask(__name__, 
    template_folder=os.path.join(ADMIN_DIR, 'templates')
)

def get_system_info():
    """Get current system status"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        mem_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Network status
        wifi_info = subprocess.run(['iwconfig', 'wlan0'], 
                                 capture_output=True, 
                                 text=True).stdout
        
        # Get IP address
        ip_info = subprocess.run(['ip', 'addr', 'show', 'wlan0'],
                               capture_output=True,
                               text=True).stdout
        
        # Internet connectivity
        internet_connected = False
        try:
            ping_test = subprocess.run(['ping', '-c', '1', '-W', '2', '8.8.8.8'],
                                     capture_output=True)
            internet_connected = ping_test.returncode == 0
        except:
            pass
            
        return {
            'cpu': cpu_percent,
            'memory': mem_percent,
            'disk': disk_percent,
            'wifi': wifi_info,
            'ip': ip_info,
            'internet': internet_connected,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logging.error(f"Error getting system info: {str(e)}")
        return None

@app.route('/api/system-info')
def system_info():
    """API endpoint for system information"""
    info = get_system_info()
    if info:
        return jsonify(info)
    return jsonify({'error': 'Failed to get system information'}), 500

@app.route('/')
def admin_panel():
    """Serve the admin panel interface"""
    try:
        # Get initial system info for first page load
        system_info = get_system_info()
        return render_template('admin.html', system_info=system_info)
    except Exception as e:
        logging.error(f"Error rendering template: {str(e)}")
        return str(e), 500

def verify_directories():
    """Verify required directories exist"""
    required_dirs = [
        os.path.join(ADMIN_DIR, 'templates'),
        os.path.join(PROJECT_ROOT, 'logs')
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            logging.error(f"Required directory missing: {directory}")
            return False
    return True

if __name__ == '__main__':
    # Verify directory structure
    if not verify_directories():
        logging.error("Missing required directories")
        sys.exit(1)
        
    logging.info("Starting admin server...")
    app.run(host='0.0.0.0', port=80, debug=True)
