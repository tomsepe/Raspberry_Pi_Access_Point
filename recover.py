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
import logging
import shutil

# Configure logging
logging.basicConfig(
    filename='logs/recovery.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_root():
    """Check if script is running with root privileges"""
    if os.geteuid() != 0:
        print("This script must be run as root (sudo)")
        sys.exit(1)

def restore_network_config():
    """Restore original network configuration files"""
    try:
        config_files = [
            '/etc/dhcpcd.conf',
            '/etc/dnsmasq.conf',
            '/etc/hostapd/hostapd.conf'
        ]
        
        for file in config_files:
            backup_file = f"{file}.backup"
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, file)
                logging.info(f"Restored {file} from backup")
                print(f"Restored {file}")
    except Exception as e:
        logging.error(f"Error restoring config files: {str(e)}")
        print(f"Error restoring config files: {str(e)}")

def recover_system():
    """Recover system to normal networking state"""
    try:
        logging.info("Starting system recovery")
        print("Starting system recovery...\n")
        
        print("1. Stopping AP services...")
        # Stop AP services
        subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'], check=True)
        subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'], check=True)
        subprocess.run(['sudo', 'systemctl', 'disable', 'hostapd'], check=True)
        subprocess.run(['sudo', 'systemctl', 'disable', 'dnsmasq'], check=True)
        
        print("\n2. Restoring network configuration...")
        restore_network_config()
        
        print("\n3. Restoring wpa_supplicant...")
        # Restore wpa_supplicant
        subprocess.run(['sudo', 'systemctl', 'unmask', 'wpa_supplicant'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'wpa_supplicant'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'wpa_supplicant'], check=True)
        
        print("\n4. Resetting network interface...")
        # Reset network interface
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'], check=True)
        time.sleep(1)
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=True)
        
        print("\n5. Restarting network services...")
        # Restart networking
        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=True)
        subprocess.run(['sudo', 'systemctl', 'restart', 'networking'], check=True)

        print("\n6. Ensuring Raspberry Pi Desktop is installed...")
        # Make sure RPD is installed and set as default
        subprocess.run(['sudo', 'apt-get', 'update'], check=True)
        subprocess.run(['sudo', 'apt-get', 'install', '--reinstall', 'raspberrypi-ui-mods', '-y'], check=True)
        
        print("\n7. Setting Raspberry Pi Desktop as default...")
        # Set RPD as default display manager
        subprocess.run(['sudo', 'update-alternatives', '--set', 'x-session-manager', '/usr/bin/startlxde-pi'], check=True)
        
        # Stop admin panel service if it exists
        print("\n8. Cleaning up admin panel service...")
        if os.path.exists('/etc/systemd/system/pi-admin-panel.service'):
            subprocess.run(['sudo', 'systemctl', 'stop', 'pi-admin-panel'], check=False)
            subprocess.run(['sudo', 'systemctl', 'disable', 'pi-admin-panel'], check=False)
            subprocess.run(['sudo', 'rm', '/etc/systemd/system/pi-admin-panel.service'], check=False)
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=False)
        
        logging.info("System recovery completed successfully")
        print("\nSystem recovery completed successfully!")
        print("\nIMPORTANT: Please reboot your system to complete the recovery:")
        print("sudo reboot")
        
    except Exception as e:
        logging.error(f"Recovery error: {str(e)}")
        print(f"\nRecovery error: {str(e)}")
        print("\nPlease check logs/recovery.log for details")
        sys.exit(1)

if __name__ == "__main__":
    try:
        check_root()
        recover_system()
    except KeyboardInterrupt:
        print("\nRecovery interrupted by user")
        sys.exit(1) 