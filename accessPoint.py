import RPi.GPIO as GPIO
import time
import subprocess
import os
import signal
import sys
import json
import psutil

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

        # Check if required packages are available
        for package in ['hostapd', 'dnsmasq']:
            result = subprocess.run(['dpkg', '-s', package], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Installing {package}...")
                subprocess.run(['sudo', 'apt-get', 'update'])
                result = subprocess.run(['sudo', 'apt-get', 'install', '-y', package])
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to install {package}")

        # Backup existing configurations
        config_files = [
            '/etc/dhcpcd.conf',
            '/etc/hostapd/hostapd.conf',
            '/etc/default/hostapd',
            '/etc/dnsmasq.conf'
        ]
        for file in config_files:
            if os.path.exists(file):
                backup_file = f"{file}.backup"
                subprocess.run(['sudo', 'cp', file, backup_file])

        # Install required packages if not already installed
        subprocess.run(['sudo', 'apt-get', 'update'])
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'hostapd', 'dnsmasq'])
        
        # Stop services temporarily
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'])
        
        # Configure static IP
        with open('/etc/dhcpcd.conf', 'a') as f:
            f.write('\ninterface wlan0\n    static ip_address=192.168.4.1/24\n    nohook wpa_supplicant\n')
        
        # Configure hostapd
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
        dnsmasq_conf = '''interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h'''
        
        with open('/etc/dnsmasq.conf', 'w') as f:
            f.write(dnsmasq_conf)
            
        # Enable and start services
        subprocess.run(['sudo', 'systemctl', 'unmask', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'enable', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'enable', 'dnsmasq'])
        subprocess.run(['sudo', 'systemctl', 'start', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'start', 'dnsmasq'])
        
        # Restart dhcpcd
        subprocess.run(['sudo', 'service', 'dhcpcd', 'restart'])
        
        print("Access point setup complete!")
        
        if setup_successful:
            # Launch web configuration server
            print("Starting web configuration server...")
            try:
                # Use subprocess to run web_config.py
                web_process = subprocess.Popen(['sudo', 'python3', 'web_config.py'])
                
                # Store the process ID for later cleanup
                global web_server_process
                web_server_process = web_process
                
                print("Web configuration server started successfully")
                return True
            except Exception as e:
                print(f"Failed to start web configuration server: {str(e)}")
                return False
                
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        return False
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

def main():
    try:
        print("Monitoring GPIO Pin 2 for access point setup...")
        while True:
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
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        cleanup_ap()
        GPIO.cleanup()

if __name__ == "__main__":
    main()