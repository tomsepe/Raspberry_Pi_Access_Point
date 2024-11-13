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

# GPIO setup
BUTTON_PIN = 2  # GPIO Pin 2
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Should define constants at top of file
WIFI_INTERFACE = 'wlan0'
AP_SSID = 'shelfWIFI'
AP_PASSWORD = '1234'
AP_IP = '192.168.4.1'

# Add global variable for web server process
web_server_process = None

def setup_access_point():
    """Configure the Raspberry Pi as a WiFi access point"""
    try:
        # Check for root privileges
        if os.geteuid() != 0:
            raise PermissionError("This script must be run as root")

        # Install required packages if not already installed
        print("Checking and installing required packages...")
        subprocess.run(['sudo', 'apt-get', 'update'])
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'hostapd', 'dnsmasq', 'dhcpcd5'])
        
        # Stop services before configuration
        print("Stopping services...")
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dhcpcd'])
        
        # Unmask hostapd if it was masked
        print("Unmasking hostapd...")
        subprocess.run(['sudo', 'systemctl', 'unmask', 'hostapd'])
        
        # Configure static IP
        print("Configuring static IP...")
        with open('/etc/dhcpcd.conf', 'a') as f:
            f.write('\ninterface wlan0\n    static ip_address=192.168.4.1/24\n    nohook wpa_supplicant\n')
        
        # Configure hostapd
        print("Configuring hostapd...")
        hostapd_conf = '''interface=wlan0
driver=nl80211
ssid=shelfWIFI
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=1234
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
        dnsmasq_conf = '''interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h'''
        
        with open('/etc/dnsmasq.conf', 'w') as f:
            f.write(dnsmasq_conf)
            
        # Start services in correct order
        print("Starting services...")
        subprocess.run(['sudo', 'systemctl', 'start', 'dhcpcd'])
        time.sleep(2)  # Give dhcpcd time to start
        
        subprocess.run(['sudo', 'systemctl', 'enable', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'start', 'hostapd'])
        time.sleep(2)  # Give hostapd time to start
        
        # Check hostapd status
        result = subprocess.run(['sudo', 'systemctl', 'status', 'hostapd'], capture_output=True, text=True)
        if "active (running)" not in result.stdout:
            print("Warning: hostapd service not running properly")
            print("hostapd status:", result.stdout)
            return False
            
        subprocess.run(['sudo', 'systemctl', 'enable', 'dnsmasq'])
        subprocess.run(['sudo', 'systemctl', 'start', 'dnsmasq'])
        
        print("Access point setup complete!")
        return True
        
    except subprocess.SubprocessError as e:
        print(f"Command execution error: {str(e)}")
        return False
    except IOError as e:
        print(f"File operation error: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False

def cleanup_ap():
    """Restore original network configuration"""
    try:
        # Stop web server if it's running
        if web_server_process:
            web_server_process.terminate()
            web_server_process.wait()
            
        for file in config_files:
            backup_file = f"{file}.backup"
            if os.path.exists(backup_file):
                subprocess.run(['sudo', 'cp', backup_file, file])

    except Exception as e:
        print(f"Cleanup error: {str(e)}")

def signal_handler(signum, frame):
    cleanup_ap()
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def update_status(status):
    """Write status to shared file"""
    with open('wifi_status.json', 'w') as f:
        json.dump(status, f)

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

def main():
    try:
        #print("Monitoring GPIO Pin 2 for access point setup...")
        print("Press 'w' to setup access point (or hold GPIO Pin 2 for hardware trigger)")
        print("Press 'q' to quit")
        
        while True:
            # Check for keyboard input
            if sys.stdin.isatty():  # Only try to read keyboard if we're in a terminal
                key = get_keyboard_input()
                if key == 'w':
                    print("\nSetting up access point...")
                    if setup_access_point():
                        print("Access point and web server are ready")
                        print("Connect to 'shelfWIFI' network and visit http://192.168.4.1")
                elif key == 'q':
                    print("\nExiting program...")
                    break

            # GPIO input check (commented out but preserved)
            '''
             # Check if button is pressed (PIN is LOW)
            if not GPIO.input(BUTTON_PIN):
                start_time = time.time()
                
                # Keep checking if button is still pressed
                while not GPIO.input(BUTTON_PIN):
                    if time.time() - start_time >= 10:
                        print("Button held for 10 seconds, setting up access point...")
                        if setup_access_point():
                            print("Access point and web server are ready")
                            print("Connect to 'shelfWIFI' network and visit http://192.168.4.1")
                        break
                    time.sleep(0.1)
            '''
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        cleanup_ap()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
