# Horsebox Control System - Raspberry Pi 5 Deployment Guide

## Hardware Requirements
- Raspberry Pi 5 (or Pi 4)
- Waveshare 30-Channel Relay Board (Modbus TCP/Ethernet version)
- Ethernet cable connecting Pi to relay board
- Display (HDMI monitor or touchscreen)
- Power supply for Pi and relay board
- (Optional) USB keyboard for initial setup and debugging

## Network Configuration

### Relay Board IP Setup
1. Connect to Waveshare relay board configuration interface
2. Set static IP: `192.168.1.123` (or update `relay_config.json` to match your IP)
3. Set Modbus TCP port: `502` (default)
4. Ensure relay board is on same network as Pi

### Raspberry Pi Network Setup
```bash
# Set static IP for Pi (optional but recommended)
sudo nano /etc/dhcpcd.conf

# Add at the end:
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
```

## Installation Steps

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Required Packages
```bash
# Install Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv

# Install X11 utilities for kiosk mode
sudo apt install -y chromium-browser xserver-xorg x11-xserver-utils unclutter

# (Optional) Hide mouse cursor automatically
sudo apt install -y unclutter
```

### 3. Clone/Copy Project Files
```bash
# Copy project to Pi home directory
mkdir -p /home/pi/horsebox
cd /home/pi/horsebox

# Copy all files from your development machine
# (Or clone from git repository)
```

### 4. Install Python Dependencies
```bash
cd /home/pi/horsebox
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Test Modbus Connection
```bash
# Test connection to relay board
python3 -c "from pymodbus.client import ModbusTcpClient; c = ModbusTcpClient('192.168.1.123', port=502); print('Connected!' if c.connect() else 'Failed'); c.close()"
```

Expected output: `Connected!`

### 6. Configure System Services

#### Backend Service (Flask + Modbus)
```bash
# Copy service file
sudo cp /home/pi/horsebox/horsebox-control.service /etc/systemd/system/

# Edit if needed (update paths to match your installation)
sudo nano /etc/systemd/system/horsebox-control.service

# Enable and start backend
sudo systemctl daemon-reload
sudo systemctl enable horsebox-control.service
sudo systemctl start horsebox-control.service

# Check status
sudo systemctl status horsebox-control.service
```

#### Kiosk Service (Chromium UI)
```bash
# Copy kiosk script and service
sudo cp /home/pi/horsebox/start_kiosk.sh /home/pi/horsebox/
sudo chmod +x /home/pi/horsebox/start_kiosk.sh

sudo cp /home/pi/horsebox/horsebox-kiosk.service /etc/systemd/system/

# Edit if needed (update paths)
sudo nano /etc/systemd/system/horsebox-kiosk.service

# Enable kiosk (but don't start yet - start after reboot)
sudo systemctl daemon-reload
sudo systemctl enable horsebox-kiosk.service
```

### 7. Configure Auto-Login (Optional but Recommended)
```bash
# Auto-login to desktop on boot
sudo raspi-config

# Navigate to: System Options → Boot / Auto Login → Desktop Autologin
# Select: Desktop Autologin (user 'pi' logged in automatically)
```

### 8. Reboot and Test
```bash
sudo reboot
```

After reboot:
- Backend should start automatically
- Kiosk should launch in fullscreen
- UI should be accessible at `http://localhost:5000`

---

## Secure Kiosk Configuration

### Security Features
The kiosk is configured with the following security measures:

1. **Keyboard Shortcuts Disabled**
   - Alt+F4, Ctrl+W, F11, etc. are blocked
   - Prevents unauthorized exit from kiosk mode

2. **Password-Protected Settings**
   - Settings page requires password: `1AmpMatter`
   - Change password in: `/home/pi/horsebox/src/api/templates/index.html` (line ~1267)

3. **Authorized Exit Methods**
   - **Via UI:** Settings → System Info → "Exit Kiosk Mode" button (password required)
   - **Via SSH:** `sudo systemctl stop horsebox-kiosk.service`
   - **Via Terminal (Pi):** Press Ctrl+Alt+F1, login, run `sudo systemctl stop horsebox-kiosk.service`

4. **No Auto-Restart**
   - Kiosk does NOT automatically restart when closed
   - Allows clean exit for debugging
   - Restart manually: `sudo systemctl start horsebox-kiosk.service`

### Physical Security Recommendations
- Mount display out of easy reach
- Secure USB ports (disable or block access)
- Lock Pi in cabinet if needed

---

## Safety Features

### H-Bridge Motor Safety
The popup motor control has built-in safety to prevent short-circuit:
- **Only one relay active at a time** (up OR down, never both)
- **50ms safety delay** between switching directions
- **Popup relays (1 & 2) cannot be manually toggled** from UI
- **Must use UP/STOP/DOWN buttons** which enforce safety logic

### Emergency Stop Button
- Floating red button on all pages
- Turns OFF all 30 relays immediately
- Confirmation dialog prevents accidental activation
- Resets active relay counter

### State Persistence
- Saves relay states after every change
- Restores states on reboot (if < 24 hours old)
- **NEVER restores popup relays** (safety first)
- Survives power outages and crashes

---

## Configuration Files

### relay_config.json
Update this file to match your setup:
```json
{
    "modbus_ip": "192.168.1.123",  // Waveshare board IP
    "modbus_port": 502,              // Modbus TCP port
    "popup_control": {
        "up_relay_id": 1,            // DO NOT CHANGE without updating wiring
        "down_relay_id": 2,          // DO NOT CHANGE without updating wiring
        "zone": "horse_outside"
    },
    "zones": {
        "living": { ... },
        "bedroom": { ... },
        "horse_outside": { ... }
    },
    "relays": [ ... ]  // 30 relays with names, zones, icons
}
```

**Important:** If you change relay names or zones in the UI, they are automatically saved to this file.

---

## Troubleshooting

### Backend Service Issues

**Check service status:**
```bash
sudo systemctl status horsebox-control.service
```

**View logs:**
```bash
sudo journalctl -u horsebox-control.service -f
```

**Manual test:**
```bash
source /home/pi/horsebox/venv/bin/activate
cd /home/pi/horsebox/src/api
python app.py
```

### Kiosk Service Issues

**Check kiosk status:**
```bash
sudo systemctl status horsebox-kiosk.service
```

**View kiosk logs:**
```bash
sudo journalctl -u horsebox-kiosk.service -f
```

**Manual kiosk launch:**
```bash
export DISPLAY=:0
/home/pi/horsebox/start_kiosk.sh
```

### Relay Board Not Responding

1. **Check connection:**
   ```bash
   ping 192.168.1.123
   ```

2. **Check Ethernet cable** - ensure solid connection

3. **Check relay board power** - LEDs should be on

4. **Verify Modbus TCP enabled** - check Waveshare board configuration

5. **Check backend logs:**
   ```bash
   sudo journalctl -u horsebox-control.service | grep -i "modbus\|connection"
   ```

### UI Not Loading

1. **Check Flask is running:**
   ```bash
   curl http://localhost:5000
   ```

2. **Check firewall:**
   ```bash
   sudo ufw status
   # If active, allow port 5000:
   sudo ufw allow 5000
   ```

3. **Test in regular browser first:**
   ```bash
   chromium-browser http://localhost:5000
   ```

### Kiosk Won't Exit (Stuck in Fullscreen)

**From another device (SSH):**
```bash
ssh pi@192.168.1.100
sudo systemctl stop horsebox-kiosk.service
```

**From Pi terminal:**
- Press `Ctrl + Alt + F1` to switch to TTY1
- Login as `pi`
- Run: `sudo systemctl stop horsebox-kiosk.service`
- Run: `pkill chromium`
- Press `Ctrl + Alt + F7` to return to desktop

**Force reboot (last resort):**
```bash
sudo reboot now
```

---

## Maintenance

### Update Relay Names
Use Settings → Relay Names tab (password required) or edit `relay_config.json` directly.

### Change Settings Password
Edit `/home/pi/horsebox/src/api/templates/index.html`:
```javascript
// Find line ~1267:
const SETTINGS_PASSWORD = '1AmpMatter';  // Change this
```

Then restart backend:
```bash
sudo systemctl restart horsebox-control.service
```

### Backup Configuration
```bash
# Backup relay config and state
cp /home/pi/horsebox/relay_config.json ~/relay_config_backup.json
cp /home/pi/horsebox/relay_config_state.json ~/relay_config_state_backup.json
```

### View System Logs
```bash
# Backend logs
sudo journalctl -u horsebox-control.service -n 100

# Kiosk logs
sudo journalctl -u horsebox-kiosk.service -n 100

# All logs (live)
sudo journalctl -f
```

### Restart Services
```bash
# Restart backend only
sudo systemctl restart horsebox-control.service

# Restart kiosk only
sudo systemctl restart horsebox-kiosk.service

# Restart both
sudo systemctl restart horsebox-control.service horsebox-kiosk.service
```

---

## Remote Access

### SSH Access
```bash
# From another device on same network
ssh pi@192.168.1.100

# Stop kiosk for maintenance
sudo systemctl stop horsebox-kiosk.service

# Restart kiosk when done
sudo systemctl start horsebox-kiosk.service
```

### Web Access (Optional)
If you want to access the UI from another device:

1. **Open firewall:**
   ```bash
   sudo ufw allow 5000
   ```

2. **Access from browser:**
   - Open `http://192.168.1.100:5000` from any device on the network

**Warning:** This allows anyone on your network to control relays. Only enable if needed.

---

## Security Best Practices

1. **Change default password immediately**
   - Edit `SETTINGS_PASSWORD` in `index.html`
   - Use a strong password (12+ characters)

2. **Secure SSH access**
   ```bash
   # Change default pi password
   passwd

   # (Optional) Disable SSH if not needed
   sudo systemctl disable ssh
   ```

3. **Physical security**
   - Mount Pi in locked enclosure
   - Disable unused USB ports
   - Cover/block SD card slot

4. **Network security**
   - Keep relay board on isolated network
   - Don't expose port 5000 to internet
   - Use VPN for remote access

---

## Uninstallation

```bash
# Stop and disable services
sudo systemctl stop horsebox-kiosk.service horsebox-control.service
sudo systemctl disable horsebox-kiosk.service horsebox-control.service

# Remove service files
sudo rm /etc/systemd/system/horsebox-kiosk.service
sudo rm /etc/systemd/system/horsebox-control.service
sudo systemctl daemon-reload

# Remove project files
rm -rf /home/pi/horsebox
```

---

**Last Updated:** 2026-01-26
**Version:** 3.2 (Secure Kiosk Mode)
**Support:** Check CHECKPOINT.md for current status and known issues
