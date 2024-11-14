#!/usr/bin/env python3
import subprocess
import os
import time

def recover_system():
    """Recover system to normal networking state"""
    try:
        # Stop AP services
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'])
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'])
        
        # Restore wpa_supplicant
        subprocess.run(['sudo', 'systemctl', 'unmask', 'wpa_supplicant'])
        subprocess.run(['sudo', 'systemctl', 'enable', 'wpa_supplicant'])
        
        # Reset network interface
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'])
        time.sleep(1)
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'])
        
        # Restart networking
        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'])
        subprocess.run(['sudo', 'systemctl', 'restart', 'networking'])
        subprocess.run(['sudo', 'systemctl', 'restart', 'lxsession'])  # Restart LXDE session
        
        print("System recovered to normal networking state")
        
    except Exception as e:
        print(f"Recovery error: {str(e)}")

if __name__ == "__main__":
    recover_system() 