from flask import Flask, render_template, jsonify, request
import subprocess
import os
import logging
import sys
import psutil
import datetime
import shutil

# Configure logging to both file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('admin_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

app = Flask(__name__)

def get_system_info():
    """Gather detailed system information"""
    try:
        # CPU info
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_temp = subprocess.check_output(['vcgencmd', 'measure_temp']).decode().strip()
        
        # Memory info
        memory = psutil.virtual_memory()
        memory_used = round(memory.used / (1024.0 ** 3), 2)  # GB
        memory_total = round(memory.total / (1024.0 ** 3), 2)  # GB
        memory_percent = memory.percent
        
        # Disk info
        disk = shutil.disk_usage('/')
        disk_total = round(disk.total / (1024.0 ** 3), 2)  # GB
        disk_used = round(disk.used / (1024.0 ** 3), 2)  # GB
        disk_free = round(disk.free / (1024.0 ** 3), 2)  # GB
        
        # Network info
        wifi_status = subprocess.check_output(['iwconfig', 'wlan0']).decode()
        ip_addr = subprocess.check_output(['hostname', '-I']).decode().strip()
        hostname = subprocess.check_output(['hostname']).decode().strip()
        
        # System uptime
        uptime = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            'success': True,
            'cpu': {
                'usage': f"{cpu_percent}%",
                'temperature': cpu_temp
            },
            'memory': {
                'used': f"{memory_used}GB",
                'total': f"{memory_total}GB",
                'percent': f"{memory_percent}%"
            },
            'disk': {
                'total': f"{disk_total}GB",
                'used': f"{disk_used}GB",
                'free': f"{disk_free}GB"
            },
            'network': {
                'wifi_status': wifi_status,
                'ip_address': ip_addr,
                'hostname': hostname
            },
            'system': {
                'uptime': uptime
            }
        }
    except Exception as e:
        logging.error(f"Error getting system info: {str(e)}")
        return {'success': False, 'error': str(e)}

@app.route('/')
def admin_panel():
    """Serve the admin panel"""
    try:
        return render_template('admin.html')
    except Exception as e:
        logging.error(f"Error serving admin panel: {str(e)}")
        return f"Error loading admin panel: {str(e)}", 500

@app.route('/api/status')
def get_status():
    """Get system status"""
    return jsonify(get_system_info())

if __name__ == '__main__':
    logging.info("Starting admin server...")
    app.run(host='0.0.0.0', port=80)
