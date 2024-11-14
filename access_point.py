import RPi.GPIO as GPIO
import time
import subprocess
import os
import signal
import sys
import json
import psutil
import termios
import tty  # For keyboard input
import atexit

# Constants and Global Variables
BUTTON_PIN = 17  # GPIO Pin 17
WIFI_INTERFACE = 'wlan0'
AP_SSID = 'PiConfigWiFi'
AP_PASSWORD = '12345678'
AP_IP = '192.168.4.1'

# Global process tracking
web_server_process = None

# Core AP Functions
def setup_access_point():
    """Configure the Raspberry Pi as a WiFi access point"""
    try:
        # Check for root privileges
        if os.geteuid() != 0:
            raise PermissionError("This script must be run as root")

        print("Stopping network services...")
        # Kill any existing wireless processes
        subprocess.run(['sudo', 'killall', 'wpa_supplicant'], check=False)
        subprocess.run(['sudo', 'killall', 'hostapd'], check=False)
        subprocess.run(['sudo', 'killall', 'dnsmasq'], check=False)
        
        # Stop services
        subprocess.run(['sudo', 'systemctl', 'stop', 'NetworkManager'], check=False)
        subprocess.run(['sudo', 'systemctl', 'stop', 'wpa_supplicant'], check=True)
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dhcpcd'])
        time.sleep(2)
        
        print("Reconfiguring wireless interface...")
        # Force disconnect from any networks
        subprocess.run(['sudo', 'rfkill', 'unblock', 'wifi'], check=True)
        subprocess.run(['sudo', 'ifconfig', WIFI_INTERFACE, 'down'], check=True)
        time.sleep(1)
        
        # Modified service start sequence
        print("Starting services...")
        subprocess.run(['sudo', 'ifconfig', WIFI_INTERFACE, 'up'], check=True)
        time.sleep(2)
        
        # Set IP address directly with ip command
        subprocess.run(['sudo', 'ip', 'addr', 'flush', 'dev', WIFI_INTERFACE], check=True)
        subprocess.run(['sudo', 'ip', 'addr', 'add', f'{AP_IP}/24', 'dev', WIFI_INTERFACE], check=True)
        time.sleep(1)
        
        # Ensure hostapd is unmasked and enabled
        print("Configuring hostapd...")
        subprocess.run(['sudo', 'systemctl', 'unmask', 'hostapd'], check=False)
        subprocess.run(['sudo', 'systemctl', 'enable', 'hostapd'], check=False)
        
        # Start dhcpcd first
        print("Starting dhcpcd...")
        subprocess.run(['sudo', 'systemctl', 'start', 'dhcpcd'])
        time.sleep(2)
        
        # Start hostapd with more detailed error checking
        print("Starting hostapd...")
        try:
            # First check if hostapd is installed
            check_hostapd = subprocess.run(['which', 'hostapd'], capture_output=True, text=True)
            if not check_hostapd.stdout:
                print("Error: hostapd not found. Please ensure it's installed.")
                return False

            # Get hostapd service status before starting
            print("\nChecking hostapd service status:")
            status_before = subprocess.run(
                ['sudo', 'systemctl', 'status', 'hostapd'],
                capture_output=True,
                text=True
            )
            print(status_before.stdout)

            # Check journal logs
            print("\nChecking hostapd logs:")
            journal = subprocess.run(
                ['sudo', 'journalctl', '-u', 'hostapd', '-n', '20'],
                capture_output=True,
                text=True
            )
            print(journal.stdout)

            # Verify configuration file
            print("\nVerifying hostapd configuration file:")
            subprocess.run(['sudo', 'cat', '/etc/hostapd/hostapd.conf'])
            
            print("\nAttempting to start hostapd service...")
            try:
                subprocess.run(['sudo', 'systemctl', 'start', 'hostapd'], check=True, timeout=10)
                time.sleep(2)

                # Verify hostapd is running
                status = subprocess.run(
                    ['sudo', 'systemctl', 'status', 'hostapd'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if 'active (running)' not in status.stdout:
                    print("\nFailed to start hostapd. Current service status:")
                    print(status.stdout)
                    
                    # Try starting hostapd directly for more debug info
                    print("\nAttempting to start hostapd directly with debug output...")
                    subprocess.run(
                        ['sudo', 'hostapd', '-dd', '/etc/hostapd/hostapd.conf'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    return False
                
                print("Hostapd started successfully")
                
            except subprocess.TimeoutExpired:
                print("Timeout while starting hostapd")
                return False

            # Start dnsmasq after hostapd is confirmed running
            print("Starting dnsmasq...")
            subprocess.run(['sudo', 'systemctl', 'start', 'dnsmasq'])

            # Start web configuration server
            print("\nStarting web configuration server...")
            try:
                global web_server_process
                if web_server_process:
                    web_server_process.terminate()
                    web_server_process = None
                
                web_server_process = subprocess.Popen(
                    ['sudo', 'python3', 'web_config.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                time.sleep(2)  # Give the web server time to start
                
                # Check if web server is running
                if web_server_process.poll() is None:
                    print("Web configuration server started successfully")
                else:
                    stdout, stderr = web_server_process.communicate()
                    print("Error starting web server:")
                    print("stdout:", stdout.decode())
                    print("stderr:", stderr.decode())
                    return False
                    
                return True
                
            except Exception as e:
                print(f"Error starting web server: {str(e)}")
                return False
            
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error starting hostapd: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Error in setup_access_point: {str(e)}")
        return False

def cleanup_ap():
    """Restore original network configuration"""
    try:
        # Stop web server if running
        global web_server_process
        if web_server_process:
            web_server_process.terminate()
            web_server_process = None

        # Stop AP services
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'], check=False)
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'], check=False)
        
        # Reset network interface
        subprocess.run(['sudo', 'ifconfig', WIFI_INTERFACE, 'down'], check=False)
        time.sleep(1)
        subprocess.run(['sudo', 'ifconfig', WIFI_INTERFACE, 'up'], check=False)
        
        # Restore network services
        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=False)
        subprocess.run(['sudo', 'systemctl', 'start', 'NetworkManager'], check=False)
        subprocess.run(['sudo', 'systemctl', 'restart', 'networking'], check=False)
        
        print("Cleanup completed")
    except Exception as e:
        print(f"Cleanup error: {str(e)}")

# Signal and Status Handling
def signal_handler(signum, frame):
    """Handle cleanup on program termination"""
    print("\nReceived termination signal. Cleaning up...")
    cleanup_ap()
    sys.exit(0)

def update_status(status):
    """Write status to shared file"""
    try:
        with open('logs/wifi_status.json', 'w') as f:
            json.dump(status, f)
    except Exception as e:
        print(f"Error updating status: {str(e)}")

def is_web_server_running():
    """Check if web server is already running"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if 'python' in proc.info['name'] and 'web_config.py' in str(proc.info['cmdline']):
            return True
    return False

def get_keyboard_input():
    """Get a single keyboard character without waiting for enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# After imports, before main code
def setup_gpio():
    """Initialize GPIO settings"""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        return True
    except Exception as e:
        print(f"Error setting up GPIO: {str(e)}")
        return False

def stop_admin_panel():
    """Stop the admin panel service if it's running"""
    try:
        print("Checking for running admin panel service...")
        if os.path.exists('/etc/systemd/system/pi-admin-panel.service'):
            print("Stopping admin panel service...")
            subprocess.run(['sudo', 'systemctl', 'stop', 'pi-admin-panel'], check=True)
            print("Admin panel service stopped")
            return True
    except Exception as e:
        print(f"Error stopping admin panel service: {str(e)}")
        return False

def verify_hostapd_config():
    """Verify hostapd configuration file exists and has correct content"""
    config_path = '/etc/hostapd/hostapd.conf'
    
    print(f"\nChecking hostapd configuration at {config_path}")
    config_content = f"""interface={WIFI_INTERFACE}
driver=nl80211
ssid={AP_SSID}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={AP_PASSWORD}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
country_code=US
"""
    try:
        if os.path.exists(config_path):
            print("Configuration file exists, checking content...")
            with open(config_path, 'r') as f:
                current_content = f.read()
            if current_content.strip() != config_content.strip():
                print("Updating existing configuration...")
                with open('hostapd.conf', 'w') as f:
                    f.write(config_content)
                subprocess.run(['sudo', 'mv', 'hostapd.conf', config_path], check=True)
        else:
            print("Creating new configuration file...")
            with open('hostapd.conf', 'w') as f:
                f.write(config_content)
            subprocess.run(['sudo', 'mv', 'hostapd.conf', config_path], check=True)
            
        subprocess.run(['sudo', 'chmod', '600', config_path], check=True)
        print("Configuration file verified/updated successfully")
        return True
    except Exception as e:
        print(f"Error managing hostapd configuration: {str(e)}")
        return False

# Main Program
def main():
    try:
        if not setup_gpio():
            print("Failed to setup GPIO")
            sys.exit(1)
            
        print("Press 'w' to setup access point (or hold GPIO Pin 17 for hardware trigger)")
        print("Press 'q' to quit")
        
        while True:
            if sys.stdin.isatty():
                key = get_keyboard_input()
                if key == 'w':
                    print("\nSetting up access point...")
                    stop_admin_panel()
                    if setup_access_point():
                        print("Access point and web server are ready")
                        print("Connect to 'PiConfigWiFi' network and visit http://192.168.4.1")
                elif key == 'q':
                    print("\nExiting program...")
                    cleanup_ap()
                    break
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        cleanup_ap()
        GPIO.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    main()
