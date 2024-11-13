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
AP_PASSWORD = '12345678'
AP_IP = '192.168.4.1'

# Add global variable for web server process
web_server_process = None

def setup_access_point():
    """Configure the Raspberry Pi as a WiFi access point"""
    try:
        # Check for root privileges
        if os.geteuid() != 0:
            raise PermissionError("This script must be run as root")

        # Install required packages first while we still have internet
        print("Checking and installing required packages...")
        subprocess.run(['sudo', 'apt-get', 'update'])
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'hostapd', 'dnsmasq', 'dhcpcd5'])
        
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
                print("You can now connect to http://192.168.4.1")
                return True
            except Exception as e:
                print(f"Failed to start web configuration server: {str(e)}")
                return False

def cleanup_ap():
    """Restore original network configuration"""
    try:
        # Stop web server if it's running
        global web_server_process
        if web_server_process:
            web_server_process.terminate()
            web_server_process.wait()
            
        # Stop AP services
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'])
        
        # Restore network interface
        subprocess.run(['sudo', 'ifconfig', WIFI_INTERFACE, 'down'])
        time.sleep(1)
        subprocess.run(['sudo', 'ifconfig', WIFI_INTERFACE, 'up'])
        
        # Restart normal networking
        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'])
        subprocess.run(['sudo', 'systemctl', 'restart', 'wpa_supplicant'])
        
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
