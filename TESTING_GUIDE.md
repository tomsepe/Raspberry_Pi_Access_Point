# Testing Guide for Raspberry Pi Access Point

## Hardware Requirements

- Raspberry Pi (any model with WiFi - Pi 3, Pi 4, Pi Zero W, etc.)
- MicroSD card (8GB minimum)
- Power supply for your Pi
- Push button (momentary switch)
- 2x jumper wires
- (Optional) 10kΩ resistor if not using internal pull-up

## Wiring Diagram

### Simple Button Wiring (Using Internal Pull-Up)

```
Raspberry Pi GPIO Layout (Top View)

    3V3  (1) (2)  5V
  GPIO2  (3) (4)  5V
  GPIO3  (5) (6)  GND
  GPIO4  (7) (8)  GPIO14
    GND  (9) (10) GPIO15
 GPIO17 (11) (12) GPIO18  ← We use GPIO17 (Pin 11)
 GPIO27 (13) (14) GND     ← Ground (Pin 14)
 GPIO22 (15) (16) GPIO23
    3V3 (17) (18) GPIO24
 GPIO10 (19) (20) GND
  GPIO9 (21) (22) GPIO25
 GPIO11 (23) (24) GPIO8
    GND (25) (26) GPIO7
```

### Connection Steps:

**Option 1: Simple Wiring (Recommended)**
```
                 Raspberry Pi
                 ┌──────────┐
    Pin 11 ──────┤ GPIO17   │
    (GPIO17)     │          │
                 │          │
    Pin 14 ──────┤ GND      │
    (Ground)     └──────────┘
         │              │
         │              │
         └──[ BUTTON ]──┘
            (Momentary
             Push Button)
```

**Wiring:**
1. Connect one terminal of the button to **Pin 11 (GPIO17)**
2. Connect the other terminal of the button to **Pin 14 (GND)**
3. That's it! The internal pull-up resistor is enabled in software

**When pressed:** GPIO17 is pulled LOW (connected to ground)
**When released:** GPIO17 is HIGH (pulled up internally to 3.3V)

---

**Option 2: External Pull-Up Resistor (Alternative)**
```
         3.3V (Pin 1)
            │
           ┌┴┐
           │ │ 10kΩ
           │ │ Resistor
           └┬┘
            │
            ├────────── Pin 11 (GPIO17)
            │
        [ BUTTON ]
            │
            └────────── Pin 14 (GND)
```

This provides the same functionality but uses an external resistor instead of the internal pull-up.

## Software Installation

### 1. Initial Setup on Raspberry Pi

```bash
# SSH into your Raspberry Pi or connect via terminal

# Navigate to your project directory
cd /path/to/Raspberry_Pi_Access_Point

# Make install script executable
chmod +x install.py

# Run the installation script (requires internet connection)
sudo python3 install.py
```

### 2. Verify Installation

The install script will:
- ✓ Install required packages (hostapd, dnsmasq, Flask, etc.)
- ✓ Create logs directory
- ✓ Backup existing network configs
- ✓ Set proper permissions

Expected output:
```
Starting WiFi Configuration System Installation

Detected [headless/desktop] environment
Updating package lists...
Installing hostapd...
Installing dnsmasq...
...
Installation completed successfully!
```

## Testing Methods

### Method 1: Direct Testing (Quickest)

1. **Run the script directly:**
   ```bash
   sudo python3 access_point.py
   ```

2. **Expected output:**
   ```
   Initializing access point configuration...
   Created logs directory: /path/to/logs

   Waiting for GPIO button (Pin 17) to be held for 5 seconds...
   Hold for 5 seconds to start access point, or to stop it if running.
   Release button early to cancel.
   ```

3. **Test the button:**
   - Press and hold the button
   - You should see:
     ```
     Button detected! Hold for 5 seconds to start access point...
     Hold for 4 more seconds...
     Hold for 3 more seconds...
     Hold for 2 more seconds...
     Hold for 1 more seconds...
     5 seconds reached! Starting access point...
     ```

4. **If you release early:**
   ```
   Button released after 2.3 seconds. Cancelled.
   ```

5. **Once AP starts successfully:**
   ```
   Access point and web server are ready
   Connect to 'PiConfigWiFi' network (password: 12345678) and visit http://192.168.4.1
   ```

6. **Test from another device:**
   - Connect to WiFi network: **PiConfigWiFi**
   - Password: **12345678**
   - Open browser to: **http://192.168.4.1**
   - You should see the configuration interface

7. **Stop the access point:**
   - Press and hold the button again for 5 seconds
   - The AP will shut down and restore normal networking

### Method 2: Run as System Service

1. **Create systemd service file:**
   ```bash
   sudo nano /etc/systemd/system/wifi-config.service
   ```

2. **Add this content (adjust paths):**
   ```ini
   [Unit]
   Description=WiFi Configuration Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 /home/pi/Raspberry_Pi_Access_Point/access_point.py
   WorkingDirectory=/home/pi/Raspberry_Pi_Access_Point
   User=root
   Restart=always
   RestartSec=10
   StandardOutput=append:/var/log/wifi-config.log
   StandardError=append:/var/log/wifi-config.log

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable wifi-config
   sudo systemctl start wifi-config
   ```

4. **Check status:**
   ```bash
   sudo systemctl status wifi-config
   ```

5. **View logs:**
   ```bash
   sudo journalctl -u wifi-config -f
   ```

## Testing Checklist

### Basic Functionality Tests

- [ ] **Button Detection**
  - Press button briefly - should detect and cancel
  - Hold button for 5 seconds - should start AP

- [ ] **Access Point Creation**
  - AP network "PiConfigWiFi" appears
  - Can connect with password "12345678"
  - Can access http://192.168.4.1

- [ ] **Web Interface**
  - Configuration page loads
  - Can scan for networks
  - Can manually enter network credentials
  - Can submit configuration

- [ ] **Toggle Functionality**
  - Hold button 5 seconds while AP running - should stop AP
  - Hold button 5 seconds again - should restart AP
  - Repeat works multiple times

### Edge Case Tests

- [ ] **Early Release**
  - Press button for only 2 seconds - should cancel
  - System remains in previous state

- [ ] **Service State Verification**
  - Check logs show service state checks
  - No timeout warnings during normal operation

- [ ] **Network Manager Detection**
  - Verify correct network manager detected in logs
  - Only active managers are restarted

- [ ] **Path Independence**
  - Run script from different directory - should still work
  - Logs directory created in correct location

### Cleanup Tests

- [ ] **Ctrl+C Handling**
  - Start AP, press Ctrl+C
  - Should cleanup GPIO and network services
  - No GPIO warnings on next run

- [ ] **Signal Handling**
  - Start AP, send SIGTERM: `sudo kill -TERM <pid>`
  - Should cleanup properly

## Troubleshooting

### Button Not Responding

1. **Check wiring:**
   ```bash
   # Test GPIO state manually
   gpio -g mode 17 in
   gpio -g mode 17 up  # Enable pull-up
   gpio -g read 17     # Should be 1 when not pressed
   # Press button and run:
   gpio -g read 17     # Should be 0 when pressed
   ```

2. **Check for GPIO conflicts:**
   ```bash
   # See what's using GPIO
   sudo lsof | grep gpio
   ```

### Access Point Won't Start

1. **Check service logs:**
   ```bash
   sudo journalctl -u hostapd -n 50
   sudo journalctl -u dnsmasq -n 50
   ```

2. **Verify hostapd config:**
   ```bash
   sudo cat /etc/hostapd/hostapd.conf
   ```

3. **Test hostapd manually:**
   ```bash
   sudo hostapd -dd /etc/hostapd/hostapd.conf
   ```

### Web Server Not Accessible

1. **Check if running:**
   ```bash
   sudo lsof -i :80
   ```

2. **Check web_config.py logs:**
   ```bash
   cat logs/wifi_config.log
   ```

3. **Test port 80:**
   ```bash
   curl http://192.168.4.1
   ```

### Network Not Restoring After Cleanup

1. **Check active network managers:**
   ```bash
   systemctl status NetworkManager
   systemctl status systemd-networkd
   systemctl status networking
   ```

2. **Manually restart:**
   ```bash
   sudo systemctl restart NetworkManager
   sudo systemctl restart wpa_supplicant
   sudo systemctl restart dhcpcd
   ```

3. **Check interface state:**
   ```bash
   ip addr show wlan0
   iwconfig wlan0
   ```

## Expected Log Output

### Successful Startup
```
Initializing access point configuration...
Created logs directory: /home/pi/Raspberry_Pi_Access_Point/logs
Waiting for GPIO button (Pin 17) to be held for 5 seconds...
Hold for 5 seconds to start access point, or to stop it if running.
Release button early to cancel.
```

### Button Press Sequence
```
Button detected! Hold for 5 seconds to start access point...
Hold for 4 more seconds...
Hold for 3 more seconds...
Hold for 2 more seconds...
Hold for 1 more seconds...
5 seconds reached! Starting access point...
```

### AP Setup Sequence
```
Checking for running admin panel service...
Admin panel service stopped
Configuring access point...
Stopping wpa_supplicant...
Stopping hostapd...
Stopping dnsmasq...
Stopping dhcpcd...
Setting up wireless interface...
Starting hostapd...
Starting dnsmasq...
Starting dhcpcd...
Access point and web server are ready
Connect to 'PiConfigWiFi' network (password: 12345678) and visit http://192.168.4.1
```

### Cleanup Sequence
```
5 seconds reached! Stopping access point...
Stopping web server process...
Web server stopped gracefully
Stopping AP services...
Resetting network interface...
Detecting active network managers...
Found active network managers: NetworkManager
Starting network services...
Restarting NetworkManager...
Starting wpa_supplicant...
Bringing interface up...
Restarting dhcpcd...
Cleanup completed
```

## Safety Notes

- The button connection uses 3.3V logic - **never connect to 5V**
- GPIO17 is safe to use and doesn't conflict with common peripherals
- Internal pull-up is sufficient - external resistor is optional
- Always shutdown properly to avoid SD card corruption
- Test on a spare Pi first if possible

## Quick Reference

**GPIO Pin Numbers:**
- Physical Pin 11 = GPIO17 (BCM numbering)
- Physical Pin 14 = Ground

**Network Credentials:**
- SSID: `PiConfigWiFi`
- Password: `12345678`
- Config URL: `http://192.168.4.1`

**Button Timing:**
- Hold: 5 seconds to trigger action
- Release early: Cancels operation
- Works as toggle: Start/Stop AP

**Key Directories:**
- Logs: `./logs/`
- Scripts: Current directory
- Config: `/etc/hostapd/`, `/etc/dnsmasq.conf`
