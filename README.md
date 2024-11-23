---
title: Raspberry Pi Access Point Configuration System
---

# Raspberry Pi Access Point Configuration System

This system provides a way to reset and reconfigure a Raspberry Pi\'s
WiFi settings using a physical button. When the button is pressed for 10
seconds, the system creates a temporary WiFi access point named
\"PiConfigWiFi\". Users can then connect to this access point and visit
http://192.168.4.1 to access a web interface where they can configure
the Raspberry Pi to connect to their local WiFi network. Once
configured, the system switches to the new network and provides an admin
interface at http://\[hostname\].local for monitoring system status.

## System Components

1.  `install.py`: Installation script that sets up required packages and
    directories
2.  `access_point.py`: Main script that sets up the WiFi access point
3.  `web_config.py`: Web server that provides the configuration
    interface
4.  `recover.py`: Recovery script to restore system to original state if
    needed
5.  `config.html`: Web interface template for WiFi configuration
6.  `admin/admin_server.py`: Admin interface server that runs after
    configuration
7.  `admin/templates/admin.html`: Admin panel interface template

## How It Works

### 1. Initial Setup

-   Install the system: `sudo python3 install.py`
-   Run the main script: `sudo python3 access_point.py`
-   Two ways to initiate setup:
    -   Press \'w\' key to start access point setup
    -   Hold GPIO Pin 17 for 10 seconds (hardware trigger)

### 2. Access Point Creation

When triggered, `access_point.py`:

-   Sets up a WiFi access point named \"PiConfigWiFi\"
-   Configures the network with IP 192.168.4.1
-   Automatically launches the web configuration server

### 3. Web Configuration

-   Connect to the \"PiConfigWiFi\" network
-   Navigate to http://192.168.4.1 in your web browser
-   The configuration page provides two options:
    -   Manually enter network credentials
    -   Scan for available networks and select one

## Requirements

-   Raspberry Pi with WiFi capability
-   Python 3.x
-   Required packages (automatically installed by install.py):
    -   hostapd
    -   dnsmasq
    -   dhcpcd5
    -   python3-flask
    -   python3-pip
    -   python3-rpi.gpio
    -   net-tools
    -   fuser
    -   wpasupplicant

## System Services

### Admin Server Service

The system creates a systemd service for the admin interface:

        # Service file location
        /etc/systemd/system/pi-admin-panel.service

        # Service management commands
        sudo systemctl status pi-admin-panel    # Check service status
        sudo systemctl start pi-admin-panel     # Start service
        sudo systemctl stop pi-admin-panel      # Stop service
        sudo systemctl restart pi-admin-panel   # Restart service
        sudo systemctl enable pi-admin-panel    # Enable on boot
        sudo journalctl -u pi-admin-panel       # View service logs
        

## Debugging and Testing

### Log Files

All logs are stored in the logs directory:

-   `logs/access_point.log` - Main application logs
-   `logs/wifi_config.log` - Web configuration server logs
-   `logs/admin_server.log` - Admin panel logs
-   `logs/recovery.log` - Recovery operation logs

### Common Issues

1.  Port 80 Already in Use:

        # Check what's using port 80
        sudo lsof -i :80

        # Stop admin panel if running
        sudo systemctl stop pi-admin-panel

2.  Access Point Not Starting:

        # Check service status
        sudo systemctl status hostapd
        sudo systemctl status dnsmasq

        # Run recovery script if needed
        sudo python3 recover.py

## Known Limitations

-   Single-band WiFi support only
-   No HTTPS support
-   Basic authentication
-   Limited error recovery
-   Requires manual initiation

## Future Improvements

-   HTTPS support
-   Improved security
-   Automatic network detection
-   Status LED indicators
-   Connection quality monitoring
-   Automatic fallback mechanism

## Testing Tools

-   `curl` - Test web endpoints
-   `tcpdump` - Monitor network traffic
-   `wireshark` - Detailed packet analysis
-   `htop` - Monitor system resources

## Common Debug Issues

1.  Access Point Not Starting:

            # Check hostapd status
            sudo systemctl status hostapd

            # Test hostapd configuration
            sudo hostapd -dd /etc/hostapd/hostapd.conf

2.  Web Server Issues:

            # Check if port 80 is available
            sudo netstat -tulpn | grep :80

            # Test Flask server response
            curl -v http://192.168.4.1

3.  Network Scanning Problems:

            # Manual network scan
            sudo iwlist wlan0 scan

            # Check wireless interface status
            rfkill list all

## Debug Environment Variables

        export FLASK_ENV=development
        export FLASK_DEBUG=1
        export PYTHONVERBOSE=1

## System Workflow

### System Workflow

1.  Installation:
    -   Run install.py to set up system
    -   Creates necessary directories and sets permissions
    -   Installs required packages
    -   Backs up existing network configuration
2.  Normal Operation:
    -   Admin panel runs on port 80
    -   System connects to configured WiFi
    -   Monitors system status
3.  Configuration Mode:
    -   Triggered by \'w\' key or GPIO button
    -   Stops admin panel service
    -   Creates access point
    -   Runs configuration web server
4.  Recovery:
    -   recover.py available if needed
    -   Restores original configuration
    -   Resets all services

## Admin Interface Features

-   Real-time system monitoring:
    -   CPU usage and temperature
    -   Memory utilization
    -   Disk space information
    -   Network status and WiFi details
    -   System uptime
-   Responsive design for mobile and desktop
-   Auto-refreshing metrics (every 5 seconds)
-   Visual indicators for system health

## Configuration Files

-   `/etc/dhcpcd.conf` - Network interface configuration
-   `/etc/hostapd/hostapd.conf` - Access point configuration
-   `/etc/dnsmasq.conf` - DHCP server configuration
-   `/etc/wpa_supplicant/wpa_supplicant.conf` - WiFi client
    configuration

## Backup and Recovery

The system automatically:

-   Backs up existing network configuration
-   Restores configuration on cleanup
-   Handles unexpected shutdowns
-   Maintains original network settings

## Contributing

1.  Fork the repository
2.  Create feature branch
3.  Submit pull request
4.  Include tests and documentation

## License

\[Your License Information\]

## Authors

Created with assistance from Cursor AI, powered by Anthropic\'s Claude
3.5 Sonnet.

## Acknowledgments

-   Cursor AI - AI-powered development environment
-   Anthropic\'s Claude 3.5 Sonnet - Large Language Model
-   RPi.GPIO documentation
-   Flask documentation
-   Raspberry Pi networking guides

## Directory Structure

        project_root/
        ├── install.py
        ├── access_point.py
        ├── web_config.py
        ├── recover.py
        ├── templates/
        │   └── config.html
        ├── admin/
        │   ├── admin_server.py
        │   └── templates/
        │       └── admin.html
        ├── logs/
        │   ├── access_point.log
        │   ├── wifi_config.log
        │   ├── admin_server.log
        │   └── recovery.log
        └── README.html
        

### Admin Server Debugging

        # Check admin server status
        sudo systemctl status pi-admin-panel

        # View admin server logs
        sudo journalctl -u pi-admin-panel -f

        # Test admin interface
        curl -v http://raspberrypi.local

        # Check avahi-daemon status
        sudo systemctl status avahi-daemon
        

## Installation

1.  Clone the repository:

        git clone [repository-url]

2.  Run the installation script:

        sudo python3 install.py

    This will:

    -   Install all required system packages
    -   Create necessary directories
    -   Set correct permissions
    -   Backup existing network configurations
    -   Create log directory

## Recovery

If something goes wrong with the configuration or you need to restore
the original network settings:

1.  Run the recovery script:

        sudo python3 recover.py

2.  The script will:
    -   Stop all access point services
    -   Restore original network configuration files
    -   Reset the WiFi interface
    -   Restore the desktop environment if needed
    -   Clean up any temporary files
    -   Stop and remove the admin panel service

3.  Reboot your system after recovery:

        sudo reboot

## Admin Panel Service

The admin panel service is automatically created and managed by
web_config.py. The service file is created at:

    /etc/systemd/system/pi-admin-panel.service

Service Configuration:

        [Unit]
        Description=Pi Admin Panel
        After=network.target

        [Service]
        ExecStart=/usr/bin/python3 /path/to/admin/admin_server.py
        WorkingDirectory=/path/to/admin
        User=root
        Restart=always
        RestartSec=3

        [Install]
        WantedBy=multi-user.target
        

Service Management:

        sudo systemctl status pi-admin-panel    # Check status
        sudo systemctl start pi-admin-panel     # Start service
        sudo systemctl stop pi-admin-panel      # Stop service
        sudo systemctl restart pi-admin-panel   # Restart service
        sudo systemctl enable pi-admin-panel    # Enable on boot
        

## Port Management

The system manages port 80 between two services:

-   Admin Panel (normal operation)
-   WiFi Configuration Server (during setup)

When switching to access point mode:

1.  The system automatically stops the admin panel service
2.  Frees up port 80 for the configuration interface
3.  Restarts the admin panel service after configuration is complete

## GPIO Configuration

The system uses GPIO Pin 17 (BCM numbering) for hardware trigger:

-   Pin is configured with internal pull-up resistor
-   Button should connect pin to ground when pressed
-   Hold for 10 seconds to trigger access point setup
-   GPIO functionality can be enabled/disabled in access_point.py

## Configuration Interface (config.html)

The configuration interface is served when users connect to the access
point. Located at `templates/config.html`, it provides:

### Features

-   WiFi Network Configuration:
    -   Network scanning capability
    -   Display of available networks with signal strength
    -   Manual network credential entry
    -   Password validation
-   User Interface Elements:
    -   Network selection dropdown
    -   Manual SSID input field
    -   Password input field
    -   \"Scan Networks\" button
    -   \"Connect\" button
    -   Status messages area
-   Real-time Feedback:
    -   Connection status updates
    -   Error messages
    -   Success confirmation

### Usage

1.  Connect to \"PiConfigWiFi\" network
2.  Navigate to http://192.168.4.1
3.  Either:
    -   Click \"Scan Networks\" to see available WiFi networks
    -   Or manually enter your network SSID
4.  Enter the network password
5.  Click \"Connect\" to apply settings

### Template Location

        project_root/
        └── templates/
            └── config.html    # WiFi configuration interface template
        

### API Endpoints

The template interacts with these endpoints (defined in web_config.py):

-   `/scan` - GET request to scan for available networks
-   `/connect` - POST request to connect to selected network
-   `/status` - GET request to check connection status

### JavaScript Functions

-   `scanNetworks()` - Initiates network scan
-   `connectToNetwork()` - Submits connection credentials
-   `checkStatus()` - Polls connection status
-   `updateStatus()` - Updates status display

### Styling

The interface includes responsive CSS for:

-   Mobile and desktop compatibility
-   Clear status messages
-   User-friendly form layout
-   Loading indicators

### Error Handling

-   Invalid password length
-   Network scan failures
-   Connection timeouts
-   Server communication errors

### Security Notes

-   Passwords are transmitted over HTTP (not HTTPS)
-   Interface only available during configuration mode
-   No persistent storage of credentials
-   Session-based operation only
