# Horsebox Control System - Watchdog Configuration

## Overview

This system uses **two layers of watchdog protection** to ensure high reliability:

1. **Hardware Watchdog** - Built into the Raspberry Pi, automatically reboots if software hangs
2. **Systemd Watchdog** - Monitors the Flask app, restarts it if it becomes unresponsive

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Hardware Layer (Raspberry Pi SoC)              │
│  ┌──────────────────────────────────────────┐  │
│  │  Hardware Watchdog Timer (15 seconds)    │  │
│  │  • Automatic reboot if not "petted"     │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                    ↑
                    │ Pet every 5s
                    │
┌─────────────────────────────────────────────────┐
│  OS Layer (Systemd)                             │
│  ┌──────────────────────────────────────────┐  │
│  │  watchdog.service                        │  │
│  │  • Monitors system health                │  │
│  │  • Pets hardware watchdog                │  │
│  │  • Can monitor network, load, processes  │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  Systemd Watchdog (10 seconds)           │  │
│  │  • Monitors horsebox-control.service     │  │
│  │  • Restarts app if unresponsive          │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                    ↑
                    │ Notify every 5s
                    │
┌─────────────────────────────────────────────────┐
│  Application Layer                              │
│  ┌──────────────────────────────────────────┐  │
│  │  Flask App (app.py)                      │  │
│  │  • Background thread notifies systemd    │  │
│  │  • Proves app is responsive              │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## What Happens When Things Go Wrong

### Scenario 1: Flask App Hangs
1. Flask stops sending systemd notifications
2. After **10 seconds**, systemd detects failure
3. Systemd **restarts horsebox-control.service**
4. Flask comes back up with persisted relay states
5. Total downtime: ~10-15 seconds

### Scenario 2: Systemd/OS Hangs
1. watchdog.service stops petting hardware watchdog
2. After **15 seconds**, hardware watchdog triggers
3. **Raspberry Pi automatically reboots**
4. Both services auto-start on boot
5. Total downtime: ~60-90 seconds (full reboot)

### Scenario 3: Network/Modbus Issue (Optional)
1. If configured, watchdog monitors network ping
2. If relay board unreachable, watchdog can reboot
3. Ensures recovery from network failures

## Installation

### Step 1: Enable Hardware Watchdog
```bash
cd /home/pi/horsebox
sudo ./enable_watchdog.sh
```

This script will:
- Load bcm2835_wdt kernel module
- Install and configure watchdog daemon
- Set 15-second hardware timeout
- Enable automatic start on boot

### Step 2: Install Python Watchdog Support
```bash
cd /home/pi/horsebox
source venv/bin/activate
pip install systemd-python
```

### Step 3: Update Backend Service
```bash
# Copy updated service file
sudo cp horsebox-control.service /etc/systemd/system/

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart horsebox-control.service

# Check status
sudo systemctl status horsebox-control.service
```

You should see:
```
Active: active (running)
```

And in the logs:
```
✅ Notified systemd: Service ready
⏱️  Systemd watchdog interval: 5.0 seconds
```

## Configuration

### Hardware Watchdog Settings
Edit `/etc/watchdog.conf`:

```ini
# Basic configuration
watchdog-device = /dev/watchdog
watchdog-timeout = 15    # Hardware reboot timeout
interval = 5             # How often to pet (< timeout)

# Optional: Monitor system load
max-load-1 = 24
max-load-5 = 18

# Optional: Monitor network connectivity
# ping = 192.168.1.123   # Ping relay board
# ping-count = 3

# Optional: Monitor network interface
# interface = eth0

# Optional: Monitor Flask process
# pidfile = /var/run/horsebox-control.pid
```

### Systemd Watchdog Settings
Edit `/etc/systemd/system/horsebox-control.service`:

```ini
[Service]
Type=notify           # Enable systemd notifications
WatchdogSec=10       # App must notify within 10 seconds
NotifyAccess=main    # Allow main process to notify
```

### Flask App Settings
Edit `src/api/app.py` (already configured):

```python
# Notification interval is automatically set to half of WatchdogSec
# If WatchdogSec=10, app notifies every 5 seconds
```

## Testing

### Test 1: Verify Hardware Watchdog Active
```bash
# Check watchdog service
sudo systemctl status watchdog

# Should show: Active: active (running)
```

### Test 2: Verify Systemd Watchdog Active
```bash
# Check Flask service
sudo systemctl status horsebox-control.service

# Look for:
# ✅ Notified systemd: Service ready
# ⏱️  Systemd watchdog interval: 5.0 seconds
```

### Test 3: Trigger Systemd Watchdog (Safe Test)
```bash
# Pause Flask process (simulates hang)
sudo kill -STOP $(pgrep -f "python.*app.py")

# Wait 10-15 seconds...
# Systemd should detect failure and restart

# Check logs
sudo journalctl -u horsebox-control.service -n 50

# You should see:
# "watchdog timeout (after 10s)"
# "Restarting..."
```

### Test 4: Trigger Hardware Watchdog (WILL REBOOT PI!)
```bash
# ⚠️  WARNING: This will reboot your Pi!
sudo killall watchdog

# Pi will reboot in ~15 seconds
# After reboot, check uptime:
uptime

# Check reboot reason in logs:
sudo journalctl -b -1 | tail
```

## Monitoring

### View Watchdog Status
```bash
# Hardware watchdog daemon
sudo systemctl status watchdog

# Flask service with systemd watchdog
sudo systemctl status horsebox-control.service

# Live logs
sudo journalctl -u watchdog -u horsebox-control.service -f
```

### Check Watchdog Notifications
```bash
# Enable debug logging in app.py
# Uncomment line in systemd_watchdog_notify():
# print(f"🐕 Watchdog notification sent at {time.strftime('%H:%M:%S')}")

# Then watch logs
sudo journalctl -u horsebox-control.service -f
```

You should see periodic notifications:
```
🐕 Watchdog notification sent at 14:32:15
🐕 Watchdog notification sent at 14:32:20
🐕 Watchdog notification sent at 14:32:25
```

### Check Reboot History
```bash
# See all reboots
last reboot

# Check if last reboot was from watchdog
sudo journalctl -b -1 | grep -i watchdog
```

## Troubleshooting

### Problem: Watchdog Service Won't Start
```bash
# Check kernel module loaded
lsmod | grep bcm2835_wdt

# If not loaded:
sudo modprobe bcm2835_wdt

# Check watchdog device exists
ls -l /dev/watchdog

# Should show: crw------- 1 root root 10, 130
```

### Problem: Flask Not Sending Notifications
```bash
# Check if systemd-python installed
python3 -c "from systemd import daemon; print('OK')"

# If error, install:
pip install systemd-python

# Check service type is 'notify'
systemctl cat horsebox-control.service | grep Type=

# Should show: Type=notify
```

### Problem: Pi Rebooting Too Often
```bash
# Check watchdog timeout settings
cat /etc/watchdog.conf | grep timeout

# Increase timeout if needed (default 15s)
sudo nano /etc/watchdog.conf
# Change: watchdog-timeout = 30

# Restart watchdog
sudo systemctl restart watchdog
```

### Problem: Watchdog Not Triggering on Hang
```bash
# Verify watchdog is actually running
sudo systemctl is-active watchdog
sudo systemctl is-active horsebox-control.service

# Check for errors
sudo journalctl -u watchdog -xe
sudo journalctl -u horsebox-control.service -xe

# Verify hardware watchdog device
cat /dev/watchdog
# Should cause immediate reboot!
```

## Disabling Watchdog

### Temporary (Until Reboot)
```bash
# Stop hardware watchdog daemon
sudo systemctl stop watchdog

# This disables automatic reboots temporarily
```

### Permanent
```bash
# Disable hardware watchdog
sudo systemctl disable watchdog
sudo systemctl stop watchdog

# Remove systemd watchdog from service
sudo nano /etc/systemd/system/horsebox-control.service
# Remove or comment out:
# WatchdogSec=10
# Type=notify

# Reload
sudo systemctl daemon-reload
sudo systemctl restart horsebox-control.service
```

## Best Practices

1. **Test thoroughly before production**
   - Run for 24 hours in test environment
   - Trigger both watchdogs intentionally
   - Verify recovery behavior

2. **Monitor reboot frequency**
   - Frequent reboots indicate underlying issues
   - Check logs to find root cause
   - Don't rely on watchdog to mask problems

3. **Keep logs**
   - Watchdog triggers are important events
   - Review logs regularly
   - Set up alerts for unexpected reboots

4. **Adjust timeouts carefully**
   - Hardware watchdog: 15-30 seconds typical
   - Systemd watchdog: 10-20 seconds typical
   - Notification interval: Half of watchdog timeout

5. **Network monitoring (optional)**
   - Add ping monitoring to watchdog.conf
   - Ensures recovery from network issues
   - Use relay board IP (192.168.1.123)

## Recovery Time Expectations

| Failure Type | Detection Time | Recovery Time | Total Downtime |
|--------------|----------------|---------------|----------------|
| Flask hangs | 10 seconds | 5 seconds | ~15 seconds |
| OS hangs | 15 seconds | 60 seconds | ~75 seconds |
| Network loss | 30 seconds (ping timeout) | 60 seconds | ~90 seconds |
| Power loss | Immediate | 60 seconds | ~60 seconds |

## Safety Considerations

### Relay States During Recovery
- **State persistence** ensures relays restore after reboot
- **Popup relays (1 & 2)** are NEVER restored (safety)
- States older than 24 hours are not restored

### Emergency Stop Availability
- Emergency stop button works during recovery
- Requires UI to be accessible
- If UI down, use SSH: `sudo systemctl stop horsebox-control.service`

### Manual Intervention
If watchdog triggers repeatedly:
1. SSH into Pi
2. Stop services: `sudo systemctl stop horsebox-control watchdog`
3. Investigate logs
4. Fix root cause
5. Re-enable watchdog

## FAQ

**Q: Will the watchdog reboot my Pi during debugging?**
A: Only if you stop the watchdog service. During normal debugging with the service running, the Pi won't reboot.

**Q: What if I need to do long maintenance?**
A: Stop the watchdog first: `sudo systemctl stop watchdog`

**Q: Can I test watchdog without rebooting?**
A: Yes, test systemd watchdog (restarts app only). Hardware watchdog test will reboot.

**Q: How do I know if watchdog caused a reboot?**
A: Check logs: `sudo journalctl -b -1 | grep -i watchdog`

**Q: Should I enable network ping monitoring?**
A: Optional. Useful if network connectivity is critical. Can cause false reboots if network is flaky.

---

**Last Updated:** 2026-01-26
**Version:** 1.0
**Recommended:** Yes - Enable for production deployments
