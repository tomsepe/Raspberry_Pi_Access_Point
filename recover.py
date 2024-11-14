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
        
        # Restart RPD desktop environment
        print("Restarting desktop environment...")
        subprocess.run(['sudo', 'systemctl', 'restart', 'raspberrypi-ui-mods'])
        
        print("System recovered to normal networking state")
        
    except Exception as e:
        print(f"Recovery error: {str(e)}")

if __name__ == "__main__":
    recover_system() 