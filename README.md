# Raspberry Pi Access Point Configuration System

This system provides a simple way to configure WiFi settings on a Raspberry Pi through a web interface. It creates a temporary access point that users can connect to for configuring their WiFi credentials.

## System Components

1. `accessPoint.py`: Main script that sets up the WiFi access point
2. `web_config.py`: Web server that provides the configuration interface
3. `config.html`: Web interface template for WiFi configuration

## How It Works

### 1. Initial Setup
'''
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq dhcpcd5
sudo systemctl unmask hostapd
'''
- Run the main script: `sudo python3 accessPoint.py`
- The script monitors GPIO Pin 2 for button press
- Hold the button for 10 seconds to initiate setup

### 2. Access Point Creation
When triggered, `accessPoint.py`:
- Sets up a WiFi access point named "shelfWIFI"
- Configures the network with IP 192.168.4.1
- Automatically launches the web configuration server

### 3. Web Configuration
- Connect to the "shelfWIFI" network
- Navigate to http://192.168.4.1 in your web browser
- The configuration page provides two options:
  - Manually enter network credentials
  - Scan for available networks and select one

### 4. Network Configuration
- After submitting credentials, the Raspberry Pi will:
  - Attempt to connect to the specified network
  - Disconnect from AP mode
  - Join your home network

## Requirements

- Raspberry Pi with WiFi capability
- Python 3.x
- Required Python packages:
'''
sudo pip3 install flask
'''
'''
sudo pip3 install RPi.GPIO
'''
sudo pip3 install psutil
'''

 -Required System Packages:
 '''
 sudo apt-get update
 sudo apt-get install hostapd dnsmasq
 '''
 
## System Workflow

### Script Interaction
1. `accessPoint.py` (Primary Script):
   - Monitors GPIO button
   - Sets up access point
   - Launches web server automatically
   - Handles cleanup on exit

2. `web_config.py` (Web Server):
   - Launched by accessPoint.py
   - Serves configuration interface
   - Handles network scanning
   - Processes WiFi credentials

3. `config.html` (User Interface):
   - Provides user input forms
   - Handles network scanning requests
   - Shows connection status
   - Provides feedback to user

### Data Flow
1. User presses button → accessPoint.py creates AP
2. accessPoint.py → launches web_config.py
3. User connects to AP → accesses web interface
4. User submits credentials → web_config.py configures WiFi
5. System transitions to new network

## Configuration Files

The system interacts with these system files:
- `/etc/dhcpcd.conf` - Network interface configuration
- `/etc/hostapd/hostapd.conf` - Access point configuration
- `/etc/dnsmasq.conf` - DHCP server configuration
- `/etc/wpa_supplicant/wpa_supplicant.conf` - WiFi client configuration

## Backup and Recovery

The system automatically:
- Backs up existing network configuration
- Restores configuration on cleanup
- Handles unexpected shutdowns
- Maintains original network settings

## Development

### Adding Features
To extend the system:
1. Modify web_config.py for new endpoints
2. Update config.html for UI changes
3. Add new functions to accessPoint.py as needed

### Testing
Test the system by:
1. Running in debug mode
2. Verifying AP creation
3. Testing web interface
4. Confirming network transitions

## Known Limitations

- Single-band WiFi support only
- No HTTPS support
- Basic authentication
- Limited error recovery
- Requires manual initiation

## Future Improvements

Potential enhancements:
- HTTPS support
- Improved security
- Automatic network detection
- Status LED indicators
- Connection quality monitoring
- Automatic fallback mechanism

## Contributing

1. Fork the repository
2. Create feature branch
3. Submit pull request
4. Include tests and documentation

## License

[Your License Information]

## Authors

[Your Name/Organization]

## Acknowledgments

- RPi.GPIO documentation
- Flask documentation
- Raspberry Pi networking guides

## Debugging and Testing

### Debug Mode
1. Enable Flask Debug Mode:
# In web_config.py, modify the app.run() line:
'''
if __name__ == '__main__':
app.run(host='192.168.4.1', port=80, debug=True)
'''
2. Enable Verbose Logging in accessPoint.py:
# Add to top of accessPoint.py
'''
import logging
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s - %(message)s',filename='access_point.log')
'''

### Testing Steps

1. Test Access Point Setup:
Run with debug output
'''
sudo python3 -v accessPoint.py
'''
Monitor system logs
'''
sudo tail -f /var/log/syslog | grep -E "hostapd|dnsmasq"
'''
Check network interface
'''
iwconfig wlan0
'''
2. Test Web Server:
Run web server standalone for testing
'''
sudo python3 web_config.py
'''
Test network scanning
'''
curl http://192.168.4.1/scan_networks
'''
Monitor Flask debug output in real-time
'''
tail -f access_point.log
'''

3. Test Network Configuration:
Verify network settings
'''
cat /etc/wpa_supplicant/wpa_supplicant.conf
'''
Check network status
'''
iwconfig
ifconfig wlan0
'''

### Common Debug Issues

1. Access Point Not Starting:
Check hostapd status
'''
sudo systemctl status hostapd
'''
Test hostapd configuration
'''
sudo hostapd -dd /etc/hostapd/hostapd.conf
'''

2. Web Server Issues:
Check if port 80 is available
'''
sudo netstat -tulpn | grep :80
'''
Test Flask server response
'''
curl -v http://192.168.4.1
'''

3. Network Scanning Problems:
Manual network scan
'''
sudo iwlist wlan0 scan
'''
Check wireless interface status
'''
rfkill list all
'''
### Debug Environment Variables

Set these environment variables for additional debugging:
''' 
export FLASK_ENV=development
export FLASK_DEBUG=1
export PYTHONVERBOSE=1
'''
### Logging Locations

Important log files to monitor:
- `/var/log/syslog` - System logs
- `/var/log/hostapd.log` - Access point logs
- `access_point.log` - Application logs
- Flask debug output in terminal

### Testing Tools

Recommended tools for debugging:
- `curl` - Test web endpoints
- `tcpdump` - Monitor network traffic
- `wireshark` - Detailed packet analysis
- `htop` - Monitor system resources