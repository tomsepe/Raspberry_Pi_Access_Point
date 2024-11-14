#!/usr/bin/env python3
"""
Raspberry Pi WiFi Configuration Installation Script

This script handles one-time installation requirements for the WiFi configuration system.
It installs necessary packages and sets up initial configurations.

Requirements:
- Root privileges (sudo)
- Internet connection for package installation

Author: Tom Sepe
Date: 11/10/2024
Version: 1.0
"""

import subprocess
import os
import sys
import shutil

def check_root():
    """Check if script is running with root privileges"""
    if os.geteuid() != 0:
        print("This script must be run as root (sudo)")
        sys.exit(1)

def install_packages():
    """Install required system packages"""
    required_packages = [
        'hostapd',
        'dnsmasq',
        'dhcpcd5',
        'python3-flask',
        'python3-pip',
        'python3-rpi.gpio',
        'net-tools',  # For network utilities like ifconfig
        'fuser',      # For port management
        'wpasupplicant'  # For WiFi client mode
    ]
    
    try:
        print("Updating package lists...")
        subprocess.run(['apt-get', 'update'], check=True)
        
        print("\nInstalling required packages...")
        for package in required_packages:
            print(f"Installing {package}...")
            subprocess.run(['apt-get', 'install', '-y', package], check=True)
            
        print("\nInstalling Python requirements...")
        subprocess.run(['pip3', 'install', 'psutil'], check=True)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {str(e)}")
        return False

def verify_directories():
    """Verify required directories exist"""
    try:
        required_dirs = [
            'admin',
            'admin/templates',
            'templates',
            'static',
            'logs'
        ]
        
        missing_dirs = []
        for directory in required_dirs:
            if not os.path.exists(directory):
                missing_dirs.append(directory)
        
        if missing_dirs:
            print("\nError: Missing required directories:")
            for dir in missing_dirs:
                print(f"  - {dir}")
            print("\nPlease ensure you've cloned the complete repository")
            return False
            
        return True
        
    except Exception as e:
        print(f"Error verifying directories: {str(e)}")
        return False

def verify_files():
    """Verify all required files exist"""
    try:
        required_files = [
            'access_point.py',
            'web_config.py',
            'admin/admin_server.py',
            'templates/config.html',
            'admin/templates/admin.html'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            print("\nError: Missing required files:")
            for file in missing_files:
                print(f"  - {file}")
            print("\nPlease ensure you've cloned the complete repository")
            return False
            
        return True
        
    except Exception as e:
        print(f"Error verifying files: {str(e)}")
        return False

def backup_config_files():
    """Backup existing configuration files"""
    try:
        config_files = [
            '/etc/dhcpcd.conf',
            '/etc/dnsmasq.conf',
            '/etc/hostapd/hostapd.conf'
        ]
        
        for file in config_files:
            if os.path.exists(file):
                backup_file = f"{file}.backup"
                if not os.path.exists(backup_file):
                    shutil.copy2(file, backup_file)
                    print(f"Backed up {file}")
        
        return True
        
    except Exception as e:
        print(f"Error backing up config files: {str(e)}")
        return False

def set_permissions():
    """Set correct permissions for directories and files"""
    try:
        print("\nSetting directory permissions...")
        
        # Directory permissions
        directories = [
            'admin',
            'admin/templates',
            'templates',
            'static'
        ]
        
        for directory in directories:
            if os.path.exists(directory):
                # 755 = User:rwx Group:r-x Others:r-x
                subprocess.run(['sudo', 'chmod', '755', directory], check=True)
                print(f"Set permissions for {directory}")
                
        # Ensure Python files are executable
        python_files = [
            'access_point.py',
            'web_config.py',
            'admin/admin_server.py'
        ]
        
        for file in python_files:
            if os.path.exists(file):
                # 755 = User:rwx Group:r-x Others:r-x
                subprocess.run(['sudo', 'chmod', '755', file], check=True)
                print(f"Set permissions for {file}")
                
        # Set ownership to current user for all files
        current_user = os.environ.get('SUDO_USER', os.environ.get('USER'))
        if current_user:
            subprocess.run(['sudo', 'chown', '-R', f'{current_user}:{current_user}', '.'], check=True)
            print(f"Set ownership to {current_user}")
            
        return True
        
    except Exception as e:
        print(f"Error setting permissions: {str(e)}")
        return False

def create_log_directory():
    """Create and set permissions for log directory"""
    try:
        if not os.path.exists('logs'):
            os.makedirs('logs')
        subprocess.run(['sudo', 'chmod', '777', 'logs'], check=True)
        return True
    except Exception as e:
        print(f"Error creating log directory: {str(e)}")
        return False

def main():
    """Main installation function"""
    print("Starting WiFi Configuration System Installation\n")
    
    # Check for root privileges
    check_root()
    
    # Verify repository structure
    if not verify_directories():
        sys.exit(1)
    
    # Verify required files
    if not verify_files():
        sys.exit(1)
    
    # Install required packages
    if not install_packages():
        print("Failed to install required packages")
        sys.exit(1)
    
    # Backup existing configuration files
    if not backup_config_files():
        print("Failed to backup configuration files")
        sys.exit(1)
        
    # Create log directory
    if not create_log_directory():
        print("Failed to create log directory")
        sys.exit(1)
        
    # Set correct permissions
    if not set_permissions():
        print("Failed to set permissions")
        sys.exit(1)
    
    print("\nInstallation completed successfully!")
    print("You can now run access_point.py to start the WiFi configuration system")

if __name__ == "__main__":
    main()