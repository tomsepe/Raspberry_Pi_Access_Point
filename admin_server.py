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

# Basic auth decorator
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def check_auth(username, password):
    """Check if username/password combination is valid"""
    # TODO: Implement proper authentication
    return username == 'admin' and password == 'password'

def authenticate():
    """Send 401 response that enables basic auth"""
    return ('Could not verify your access level for that URL.\n'
            'You have to login with proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.route('/')
@require_auth
def admin_panel():
    return render_template('admin.html')

@app.route('/api/status')
@require_auth
def get_status():
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
    # Run the server on port 80 with SSL
    app.run(host='0.0.0.0', port=80, ssl_context='adhoc')
