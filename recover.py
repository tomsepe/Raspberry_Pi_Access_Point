#!/usr/bin/env python3
"""
System Recovery Script for Raspberry Pi WiFi Configuration

This script restores the system to its normal networking state and desktop environment
if something goes wrong with the WiFi configuration system.

Recovery steps:
1. Stops access point services
2. Restores network configuration
3. Restores desktop environment
4. Cleans up any leftover configuration files

Author: Tom Sepe
Date: 11/10/2024
Version: 1.0
"""

import subprocess
import os
import sys
import time
import shutil

def check_root():
    """Check for root privileges"""
    if os.geteuid() != 0:
        sys.exit("This script must be run as root (sudo)")

def restore_network_config():
    """Restore original network configuration files"""
    config_files = [
        '/etc/dhcpcd.conf',
        '/etc/dnsmasq.conf',
        '/etc/hostapd/hostapd.conf'
    ]
    
    for file in config_files:
        backup_file = f"{file}.backup"
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, file)
            print(f"Restored {file}")

def recover_system():
    """Recover system to normal networking state"""
    try:
        print("Starting system recovery...\n")
        
        # 1. Stop and disable AP services
        print("1. Stopping AP services...")
        services_to_manage = ['hostapd', 'dnsmasq']
        for service in services_to_manage:
            subprocess.run(['sudo', 'systemctl', 'stop', service], check=False)
            subprocess.run(['sudo', 'systemctl', 'disable', service], check=False)
        
        # 2. Restore network configs
        print("\n2. Restoring network configuration...")
        restore_network_config()
        
        # 3. Enable and start wpa_supplicant
        print("\n3. Restoring wpa_supplicant...")
        subprocess.run(['sudo', 'systemctl', 'unmask', 'wpa_supplicant'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'wpa_supplicant'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'wpa_supplicant'], check=True)
        
        # 4. Reset network interface
        print("\n4. Resetting network interface...")
        subprocess.run(['sudo', 'ip', 'link', 'set', 'wlan0', 'down'], check=True)
        time.sleep(1)
        subprocess.run(['sudo', 'ip', 'link', 'set', 'wlan0', 'up'], check=True)
        
        # 5. Restart network services
        print("\n5. Restarting network services...")
        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=True)
        subprocess.run(['sudo', 'systemctl', 'restart', 'networking'], check=True)
""" 
        print("\n6. Ensuring Raspberry Pi Desktop is installed...")
        # Make sure RPD is installed and set as default
        subprocess.run(['sudo', 'apt-get', 'update'], check=True)
        subprocess.run(['sudo', 'apt-get', 'install', '--reinstall', 'raspberrypi-ui-mods', '-y'], check=True)
        
        print("\n7. Setting Raspberry Pi Desktop as default...")
        # Set RPD as default display manager
        subprocess.run(['sudo', 'update-alternatives', '--set', 'x-session-manager', '/usr/bin/startlxde-pi'], check=True)
         """
        # Stop admin panel service if it exists
        print("\n8. Cleaning up admin panel service...")
        if os.path.exists('/etc/systemd/system/pi-admin-panel.service'):
            subprocess.run(['sudo', 'systemctl', 'stop', 'pi-admin-panel'], check=False)
            subprocess.run(['sudo', 'systemctl', 'disable', 'pi-admin-panel'], check=False)
            subprocess.run(['sudo', 'rm', '/etc/systemd/system/pi-admin-panel.service'], check=False)
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=False)
        
        print("\nSystem recovery completed successfully!")
        print("\nIMPORTANT: Please reboot your system to complete the recovery:")
        print("sudo reboot")
        
    except Exception as e:
        print(f"\nRecovery error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        check_root()
        recover_system()
    except KeyboardInterrupt:
        print("\nRecovery interrupted by user")
        sys.exit(1) 