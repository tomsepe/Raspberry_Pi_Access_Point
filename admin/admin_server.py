from flask import Flask, render_template, jsonify
import subprocess
import os
import psutil
import time

# Setup paths and app
ADMIN_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(ADMIN_DIR, 'templates'))

def get_system_info():
    """Get current system status"""
    try:
        # Basic system metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network information
        wifi_cmd = subprocess.run(['iwconfig', 'wlan0'], 
                                capture_output=True, 
                                text=True)
        ip_cmd = subprocess.run(['ip', 'addr', 'show', 'wlan0'],
                              capture_output=True,
                              text=True)
        
        # Internet connectivity check
        ping_test = subprocess.run(['ping', '-c', '1', '-W', '2', '8.8.8.8'],
                                 capture_output=True)
            
        return {
            'cpu': psutil.cpu_percent(),
            'memory': memory.percent,
            'disk': disk.percent,
            'wifi': wifi_cmd.stdout if wifi_cmd.returncode == 0 else 'Not available',
            'ip': ip_cmd.stdout if ip_cmd.returncode == 0 else 'Not available',
            'internet': ping_test.returncode == 0,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"Error getting system info: {str(e)}")
        return None

@app.route('/api/system-info')
def system_info():
    """API endpoint for system information"""
    info = get_system_info()
    return jsonify(info if info else {'error': 'Failed to get system information'}), 
           200 if info else 500

@app.route('/')
def admin_panel():
    """Serve the admin panel interface"""
    return render_template('admin.html', system_info=get_system_info())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
