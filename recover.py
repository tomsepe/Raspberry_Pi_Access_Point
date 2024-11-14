#!/usr/bin/env python3
import subprocess
import os
import time

def recover_system():
    """Recover system to normal networking state"""
    try:
        print("Stopping AP services...")
        # Stop AP services
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'])
        
        print("Restoring wpa_supplicant...")
        # Restore wpa_supplicant
        subprocess.run(['sudo', 'systemctl', 'unmask', 'wpa_supplicant'])
        subprocess.run(['sudo', 'systemctl', 'enable', 'wpa_supplicant'])
        subprocess.run(['sudo', 'systemctl', 'start', 'wpa_supplicant'])
        
        print("Resetting network interface...")
        # Reset network interface
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'])
        time.sleep(1)
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'])
        
        print("Restarting network services...")
        # Restart networking
        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'])
        subprocess.run(['sudo', 'systemctl', 'restart', 'networking'])

        print("Ensuring Raspberry Pi Desktop is installed...")
        # Make sure RPD is installed and set as default
        subprocess.run(['sudo', 'apt-get', 'update'])
        subprocess.run(['sudo', 'apt-get', 'install', '--reinstall', 'raspberrypi-ui-mods', '-y'])
        
        print("Setting Raspberry Pi Desktop as default...")
        # Set RPD as default display manager
        subprocess.run(['sudo', 'update-alternatives', '--set', 'x-session-manager', '/usr/bin/startlxde-pi'])
        
        print("\nSystem recovered to normal networking state")
        print("\nIMPORTANT: Please reboot your system to complete the recovery:")
        print("sudo reboot")
        
    except Exception as e:
        print(f"Recovery error: {str(e)}")

if __name__ == "__main__":
    recover_system() 