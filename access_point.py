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

        # Now disconnect from existing WiFi
        print("Disconnecting from any existing WiFi networks...")
        subprocess.run(['sudo', 'rfkill', 'unblock', 'wifi'], check=True)
        subprocess.run(['sudo', 'ifconfig', WIFI_INTERFACE, 'down'], check=True)
        subprocess.run(['sudo', 'systemctl', 'stop', 'wpa_supplicant'], check=True)
        subprocess.run(['sudo', 'systemctl', 'mask', 'wpa_supplicant'], check=True)  # Prevent automatic restart
        time.sleep(2)  # Give time for network to disconnect

        # Stop services before configuration
        print("Stopping services...")
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dhcpcd'])
        
        # Unmask and enable hostapd
        print("Configuring hostapd service...")
        subprocess.run(['sudo', 'systemctl', 'unmask', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'enable', 'hostapd'])
        
        # Backup and configure static IP
        print("Configuring static IP...")
        if os.path.exists('/etc/dhcpcd.conf'):
            subprocess.run(['sudo', 'cp', '/etc/dhcpcd.conf', '/etc/dhcpcd.conf.backup'])
        
        dhcpcd_conf = f'''
interface {WIFI_INTERFACE}
    static ip_address={AP_IP}/24
    nohook wpa_supplicant
'''
        with open('/etc/dhcpcd.conf', 'w') as f:
            f.write(dhcpcd_conf)
        
        # Configure hostapd
        print("Configuring hostapd...")
        hostapd_conf = f'''interface={WIFI_INTERFACE}
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
rsn_pairwise=CCMP'''
        
        with open('/etc/hostapd/hostapd.conf', 'w') as f:
            f.write(hostapd_conf)
            
        # Update hostapd default configuration
        with open('/etc/default/hostapd', 'w') as f:
            f.write('DAEMON_CONF="/etc/hostapd/hostapd.conf"')
            
        # Configure DHCP server (dnsmasq)
        print("Configuring DHCP server...")
        dnsmasq_conf = f'''interface={WIFI_INTERFACE}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h'''
        
        with open('/etc/dnsmasq.conf', 'w') as f:
            f.write(dnsmasq_conf)
            
        # Bring up interface and start services in correct order
        print("Starting services...")
        subprocess.run(['sudo', 'ifconfig', WIFI_INTERFACE, 'up'], check=True)
        time.sleep(2)
        
        subprocess.run(['sudo', 'systemctl', 'start', 'dhcpcd'])
        time.sleep(2)
        
        subprocess.run(['sudo', 'systemctl', 'start', 'hostapd'])
        time.sleep(2)
        
        # Check hostapd status
        result = subprocess.run(['sudo', 'systemctl', 'status', 'hostapd'], capture_output=True, text=True)
        if "active (running)" not in result.stdout:
            print("Warning: hostapd service not running properly")
            print("hostapd status:", result.stdout)
            return False
            
        subprocess.run(['sudo', 'systemctl', 'start', 'dnsmasq'])
        
        # Verify AP is broadcasting
        print("Verifying access point...")
        time.sleep(2)
        result = subprocess.run(['iwconfig', WIFI_INTERFACE], capture_output=True, text=True)
        if "Mode:Master" not in result.stdout:
            print("Warning: Access point mode not active")
            print("Interface status:", result.stdout)
            return False
            
        print("Access point setup complete!")
        print(f"SSID: {AP_SSID}")
        print(f"Password: {AP_PASSWORD}")
        print(f"IP Address: {AP_IP}")
        
        # Launch web configuration server
        print("Starting web configuration server...")
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            web_config_path = os.path.join(current_dir, 'web_config.py')
            
            # Use subprocess to run web_config.py
            web_process = subprocess.Popen(['sudo', 'python3', web_config_path])
            
            # Store the process ID for later cleanup
            global web_server_process
            web_server_process = web_process
            
            print("Web configuration server started successfully")
            print("You can now connect to http://192.168.4.1")
            return True
        except Exception as e:
            print(f"Failed to start web configuration server: {str(e)}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def cleanup_ap():
    """Restore original network configuration"""
    print("Cleaning up access point configuration...")
    try:
        # Stop web server if running
        global web_server_process
        if web_server_process:
            try:
                web_server_process.terminate()
                web_server_process.wait(timeout=5)
            except:
                # If normal termination fails, force kill
                try:
                    subprocess.run(['sudo', 'pkill', '-f', 'web_config.py'], check=False)
                except:
                    pass
            web_server_process = None

        # Stop AP services
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'], check=False)
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'], check=False)
        
        # Restore original configuration files
        if os.path.exists('/etc/dhcpcd.conf.backup'):
            subprocess.run(['sudo', 'mv', '/etc/dhcpcd.conf.backup', '/etc/dhcpcd.conf'], check=False)
        
        if os.path.exists('/etc/dnsmasq.conf.backup'):
            subprocess.run(['sudo', 'mv', '/etc/dnsmasq.conf.backup', '/etc/dnsmasq.conf'], check=False)
            
        # Restore wpa_supplicant
        subprocess.run(['sudo', 'systemctl', 'unmask', 'wpa_supplicant'], check=False)
        subprocess.run(['sudo', 'systemctl', 'enable', 'wpa_supplicant'], check=False)
        subprocess.run(['sudo', 'systemctl', 'start', 'wpa_supplicant'], check=False)
        
        # Reset network interface
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'], check=False)
        time.sleep(1)
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=False)
        
        # Restart networking services
        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=False)
        subprocess.run(['sudo', 'systemctl', 'restart', 'networking'], check=False)
        
        # Clean up GPIO safely
        try:
            GPIO.cleanup()
        except:
            pass
            
        print("Cleanup completed. Original network configuration restored.")
        
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

# Register signal handlers and cleanup
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup_ap)

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

# Main Program
def main():
    try:
        if not setup_gpio():
            print("Failed to setup GPIO")
            sys.exit(1)
            
        print("Press 'w' to setup access point (or hold GPIO Pin 17 for hardware trigger)")
        print("Press 'q' to quit")
        
        while True:
            # Check for keyboard input
            if sys.stdin.isatty():  # Only try to read keyboard if we're in a terminal
                key = get_keyboard_input()
                if key == 'w':
                    print("\nSetting up access point...")
                    # Stop admin panel before setting up AP
                    stop_admin_panel()
                    if setup_access_point():
                        print("Access point and web server are ready")
                        print("Connect to 'PiConfigWiFi' network and visit http://192.168.4.1")
                elif key == 'q':
                    print("\nExiting program...")
                    cleanup_ap()  # Ensure cleanup runs before exit
                    break

            # GPIO hardware trigger functionality (preserved for future use)
            # Uncomment to enable button-triggered AP setup
            '''
            if not GPIO.input(BUTTON_PIN):
                start_time = time.time()
                
                # Keep checking if button is still pressed
                while not GPIO.input(BUTTON_PIN):
                    if time.time() - start_time >= 10:
                        print("Button held for 10 seconds, setting up access point...")
                        # Stop admin panel before setting up AP
                        stop_admin_panel()
                        if setup_access_point():
                            print("Access point and web server are ready")
                            print("Connect to 'PiConfigWiFi' network and visit http://192.168.4.1")
                        break
                    time.sleep(0.1)
            '''
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        cleanup_ap()
        GPIO.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    main()
