import RPi.GPIO as GPIO
import time
import subprocess
import os

# GPIO setup
BUTTON_PIN = 2  # GPIO Pin 2
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def setup_access_point():
    """Configure the Raspberry Pi as a WiFi access point"""
    try:
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
        return True
        
    except Exception as e:
        print(f"Error setting up access point: {str(e)}")
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
                        setup_access_point()
                        break
                    time.sleep(0.1)
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
