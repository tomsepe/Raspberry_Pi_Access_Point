# Raspberry_Pi_Access_Point
 
To use this, you'll need to:
Install Flask:
Bash

'''
sudo pip3 install flask
'''

Create a templates directory in the same folder as web_config.py
Save the HTML file as config.html in the templates directory
Run the script with sudo (needed for network scanning):

'''
sudo python3 web_config.py
'''

The web server will run on the IP address 192.168.4.1 (the same IP configured in your access point script). Users connected to the "shelfWIFI" network can access the configuration page by navigating to http://192.168.4.1 in their web browser.

