import RPi.GPIO as GPIO
import time
import subprocess
import os
import signal
import sys
import json
import psutil

# Constants and Global Variables
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUTTON_PIN = 17  # GPIO Pin 17
WIFI_INTERFACE = 'wlan0'
AP_SSID = 'PiConfigWiFi'
AP_PASSWORD = '12345678'
AP_IP = '192.168.4.1'
LOGS_DIR = os.path.join(SCRIPT_DIR, 'logs')
WEB_CONFIG_SCRIPT = os.path.join(SCRIPT_DIR, 'web_config.py')

# Global process tracking
web_server_process = None
gpio_initialized = False

# Directory Management
def ensure_directories():
    """Ensure required directories exist"""
    try:
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR, mode=0o755)
            print(f"Created logs directory: {LOGS_DIR}")
        return True
    except Exception as e:
        print(f"Warning: Could not create logs directory: {str(e)}")
        return False

# Network Management Detection
def detect_network_manager():
    """Detect which network management system is in use"""
    managers = []

    # Check NetworkManager
    result = subprocess.run(['systemctl', 'is-active', 'NetworkManager'],
                          capture_output=True, text=True, check=False)
    if result.returncode == 0:
        managers.append('NetworkManager')

    # Check systemd-networkd
    result = subprocess.run(['systemctl', 'is-active', 'systemd-networkd'],
                          capture_output=True, text=True, check=False)
    if result.returncode == 0:
        managers.append('systemd-networkd')

    # Check networking (legacy Debian)
    result = subprocess.run(['systemctl', 'is-active', 'networking'],
                          capture_output=True, text=True, check=False)
    if result.returncode == 0:
        managers.append('networking')

    return managers

def wait_for_service_state(service, desired_state, timeout=10):
    """Wait for a service to reach desired state (active/inactive)"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = subprocess.run(['systemctl', 'is-active', service],
                              capture_output=True, text=True, check=False)
        current_state = result.stdout.strip()

        if desired_state == 'inactive' and current_state in ['inactive', 'failed']:
            return True
        elif desired_state == 'active' and current_state == 'active':
            return True

        time.sleep(0.5)

    return False

# Core AP Functions
def setup_access_point():
    """Configure the Raspberry Pi as a WiFi access point"""
    try:
        # Check for root privileges
        if os.geteuid() != 0:
            raise PermissionError("This script must be run as root")

        # Stop admin panel first to free up port 80
        stop_admin_panel()
        
        # Simplified service management
        print("Configuring access point...")
        services_to_stop = ['wpa_supplicant', 'hostapd', 'dnsmasq', 'dhcpcd']
        for service in services_to_stop:
            print(f"Stopping {service}...")
            subprocess.run(['systemctl', 'stop', service], check=False)
            if not wait_for_service_state(service, 'inactive', timeout=5):
                print(f"Warning: {service} may not have stopped cleanly")

        print("Setting up wireless interface...")
        subprocess.run(['rfkill', 'unblock', 'wifi'], check=True)
        subprocess.run(['ip', 'link', 'set', WIFI_INTERFACE, 'up'], check=True)
        subprocess.run(['ip', 'addr', 'flush', 'dev', WIFI_INTERFACE], check=True)
        subprocess.run(['ip', 'addr', 'add', f'{AP_IP}/24', 'dev', WIFI_INTERFACE], check=True)

        # Start core services
        verify_hostapd_config()
        print("Starting hostapd...")
        subprocess.run(['systemctl', 'start', 'hostapd'], check=True)
        if not wait_for_service_state('hostapd', 'active', timeout=10):
            raise Exception("hostapd failed to start")

        print("Starting dnsmasq...")
        subprocess.run(['systemctl', 'start', 'dnsmasq'], check=True)
        if not wait_for_service_state('dnsmasq', 'active', timeout=10):
            raise Exception("dnsmasq failed to start")

        print("Starting dhcpcd...")
        subprocess.run(['systemctl', 'start', 'dhcpcd'], check=True)
        if not wait_for_service_state('dhcpcd', 'active', timeout=10):
            raise Exception("dhcpcd failed to start")

        # Start web server
        global web_server_process
        stop_web_server()
        web_server_process = subprocess.Popen(['python3', WEB_CONFIG_SCRIPT], cwd=SCRIPT_DIR)

        print("\nAccess point and web server are ready")
        print(f"Connect to '{AP_SSID}' network (password: {AP_PASSWORD}) and visit http://{AP_IP}")
        return True
        
    except Exception as e:
        print(f"Error in setup_access_point: {str(e)}")
        return False

def cleanup_ap():
    """Restore original network configuration"""
    try:
        # Stop web server if running
        global web_server_process
        if web_server_process:
            print("Stopping web server process...")
            try:
                web_server_process.terminate()
                # Wait up to 5 seconds for graceful termination
                web_server_process.wait(timeout=5)
                print("Web server stopped gracefully")
            except subprocess.TimeoutExpired:
                print("Web server didn't stop gracefully, forcing kill...")
                web_server_process.kill()
                web_server_process.wait()
            except Exception as e:
                print(f"Error stopping web server process: {str(e)}")
            finally:
                web_server_process = None

        print("Stopping AP services...")
        subprocess.run(['systemctl', 'stop', 'hostapd'], check=False)
        wait_for_service_state('hostapd', 'inactive', timeout=5)
        subprocess.run(['systemctl', 'stop', 'dnsmasq'], check=False)
        wait_for_service_state('dnsmasq', 'inactive', timeout=5)

        print("Resetting network interface...")
        subprocess.run(['ip', 'addr', 'flush', 'dev', WIFI_INTERFACE], check=False)
        subprocess.run(['ip', 'link', 'set', WIFI_INTERFACE, 'down'], check=False)
        time.sleep(1)  # Brief pause for interface to settle

        print("Detecting active network managers...")
        active_managers = detect_network_manager()
        print(f"Found active network managers: {', '.join(active_managers) if active_managers else 'none'}")

        print("Starting network services...")
        if 'NetworkManager' in active_managers:
            print("Restarting NetworkManager...")
            subprocess.run(['systemctl', 'restart', 'NetworkManager'], check=False)
            wait_for_service_state('NetworkManager', 'active', timeout=10)

        if 'systemd-networkd' in active_managers:
            print("Restarting systemd-networkd...")
            subprocess.run(['systemctl', 'restart', 'systemd-networkd'], check=False)
            wait_for_service_state('systemd-networkd', 'active', timeout=10)

        if 'networking' in active_managers:
            print("Restarting networking...")
            subprocess.run(['systemctl', 'restart', 'networking'], check=False)
            wait_for_service_state('networking', 'active', timeout=10)

        # Always try to start wpa_supplicant and dhcpcd
        print("Starting wpa_supplicant...")
        subprocess.run(['systemctl', 'start', 'wpa_supplicant'], check=False)
        wait_for_service_state('wpa_supplicant', 'active', timeout=5)

        print("Bringing interface up...")
        subprocess.run(['ip', 'link', 'set', WIFI_INTERFACE, 'up'], check=False)

        print("Restarting dhcpcd...")
        subprocess.run(['systemctl', 'restart', 'dhcpcd'], check=False)
        wait_for_service_state('dhcpcd', 'active', timeout=10)
        
        print("Cleanup completed")
    except Exception as e:
        print(f"Cleanup error: {str(e)}")

# Signal and Status Handling
def signal_handler(signum, frame):
    """Handle cleanup on program termination"""
    print("\nReceived termination signal. Cleaning up...")
    cleanup_ap()
    cleanup_gpio()
    sys.exit(0)

def update_status(status):
    """Write status to shared file"""
    try:
        status_file = os.path.join(LOGS_DIR, 'wifi_status.json')
        with open(status_file, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        print(f"Error updating status: {str(e)}")

def is_web_server_running():
    """Check if web server is already running"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if 'python' in proc.info['name'] and 'web_config.py' in str(proc.info['cmdline']):
            return True
    return False

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# After imports, before main code
def setup_gpio():
    """Initialize GPIO settings"""
    global gpio_initialized
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        gpio_initialized = True
        return True
    except Exception as e:
        print(f"Error setting up GPIO: {str(e)}")
        gpio_initialized = False
        return False

def cleanup_gpio():
    """Safely cleanup GPIO"""
    global gpio_initialized
    if gpio_initialized:
        try:
            GPIO.cleanup()
            gpio_initialized = False
            print("GPIO cleaned up successfully")
        except Exception as e:
            print(f"Warning: Error during GPIO cleanup: {str(e)}")
    else:
        print("GPIO was not initialized, skipping cleanup")

def stop_admin_panel():
    """Stop the admin panel service if it's running"""
    try:
        print("Checking for running admin panel service...")
        if os.path.exists('/etc/systemd/system/pi-admin-panel.service'):
            print("Stopping admin panel service...")
            subprocess.run(['systemctl', 'stop', 'pi-admin-panel'], check=True)
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
        # Check if config needs updating
        needs_update = False
        if os.path.exists(config_path):
            print("Configuration file exists, checking content...")
            with open(config_path, 'r') as f:
                current_content = f.read()
            if current_content.strip() != config_content.strip():
                print("Configuration needs updating...")
                needs_update = True
        else:
            print("Creating new configuration file...")
            needs_update = True

        # Write directly to /etc/hostapd/hostapd.conf (we're running as root)
        if needs_update:
            with open(config_path, 'w') as f:
                f.write(config_content)
            os.chmod(config_path, 0o600)
            print("Configuration file written successfully")
        else:
            print("Configuration file is up to date")

        return True
    except Exception as e:
        print(f"Error managing hostapd configuration: {str(e)}")
        return False

def stop_web_server():
    """Stop any running web_config.py processes"""
    try:
        stopped_count = 0
        # First, try to find and stop web_config.py processes specifically
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'web_config.py' in ' '.join(cmdline):
                    print(f"Found web_config.py process (PID: {proc.info['pid']}), stopping...")
                    proc.terminate()
                    stopped_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if stopped_count > 0:
            print(f"Waiting for {stopped_count} web server process(es) to stop...")
            time.sleep(2)

        # Fallback: if web_config.py processes weren't found but port 80 is in use,
        # use fuser as last resort
        if stopped_count == 0:
            print("Checking port 80 for any processes...")
            result = subprocess.run(['lsof', '-ti', ':80'],
                                  capture_output=True, text=True, check=False)
            if result.stdout.strip():
                print("Warning: Port 80 is in use. Using fuser to free it...")
                subprocess.run(['fuser', '-k', '80/tcp'], check=False)
                time.sleep(2)
    except Exception as e:
        print(f"Error stopping web server: {str(e)}")

# Main Program
def main():
    try:
        # Ensure required directories exist
        ensure_directories()

        # Setup GPIO first
        if not setup_gpio():
            print("Failed to setup GPIO")
            sys.exit(1)

        ap_running = False
        button_pressed = False
        button_press_start = None
        HOLD_DURATION = 5.0  # seconds
        last_feedback_time = 0

        print("\nWaiting for GPIO button (Pin 17) to be held for 5 seconds...")
        print("Hold for 5 seconds to start access point, or to stop it if running.")
        print("Release button early to cancel.")

        while True:
            # Check GPIO button with 5-second hold detection
            button_state = not GPIO.input(BUTTON_PIN)  # True when pressed (pin pulled LOW)

            if button_state:
                # Button is currently pressed
                if not button_pressed:
                    # Button just pressed (first detection)
                    button_pressed = True
                    button_press_start = time.time()
                    last_feedback_time = time.time()
                    if ap_running:
                        print("\nButton detected! Hold for 5 seconds to stop access point...")
                    else:
                        print("\nButton detected! Hold for 5 seconds to start access point...")
                else:
                    # Button still being held
                    hold_duration = time.time() - button_press_start

                    # Provide feedback every second
                    if time.time() - last_feedback_time >= 1.0:
                        remaining = HOLD_DURATION - hold_duration
                        if remaining > 0:
                            print(f"Hold for {remaining:.0f} more seconds...")
                        last_feedback_time = time.time()

                    # Check if held long enough
                    if hold_duration >= HOLD_DURATION:
                        if ap_running:
                            print("\n5 seconds reached! Stopping access point...")
                            cleanup_ap()
                            ap_running = False
                        else:
                            print("\n5 seconds reached! Starting access point...")
                            if setup_access_point():
                                ap_running = True
                        button_pressed = False
                        button_press_start = None
            else:
                # Button is not pressed
                if button_pressed:
                    # Button was released before 5 seconds
                    hold_duration = time.time() - button_press_start
                    print(f"\nButton released after {hold_duration:.1f} seconds. Cancelled.")
                    button_pressed = False
                    button_press_start = None

            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        cleanup_ap()
    finally:
        cleanup_gpio()
        sys.exit(0)

if __name__ == "__main__":
    main()
