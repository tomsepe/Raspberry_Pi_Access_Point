from flask import Flask, render_template
import subprocess
import logging
import os
import sys

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

@app.route('/')
def admin_panel():
    """Serve the admin panel interface"""
    try:
        return render_template('admin.html')
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
