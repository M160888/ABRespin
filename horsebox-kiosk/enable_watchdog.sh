#!/bin/bash
# Enable Raspberry Pi Hardware Watchdog
# This script configures the built-in hardware watchdog to automatically reboot
# the Pi if software hangs or becomes unresponsive

echo "================================"
echo "Raspberry Pi Hardware Watchdog Setup"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root"
    echo "   Usage: sudo ./enable_watchdog.sh"
    exit 1
fi

# 1. Load the watchdog kernel module
echo "📦 Loading watchdog kernel module..."
modprobe bcm2835_wdt
echo "bcm2835_wdt" >> /etc/modules

# 2. Install watchdog daemon
echo "📦 Installing watchdog daemon..."
apt-get update
apt-get install -y watchdog

# 3. Configure watchdog daemon
echo "⚙️  Configuring watchdog daemon..."
cat > /etc/watchdog.conf << 'EOF'
# Raspberry Pi Hardware Watchdog Configuration
# This daemon "pets" the hardware watchdog to prevent automatic reboots
# If the daemon stops running, the Pi will reboot automatically

# Hardware watchdog device
watchdog-device = /dev/watchdog
watchdog-timeout = 15

# How often to pet the watchdog (must be < timeout)
interval = 5

# Maximum load average before triggering reboot (optional)
# Uncomment to enable load monitoring
# max-load-1 = 24
# max-load-5 = 18
# max-load-15 = 12

# Monitor critical processes (optional)
# If Flask stops, watchdog will reboot
# Uncomment after testing:
# pidfile = /var/run/horsebox-control.pid

# Test if network interface is up (optional)
# interface = eth0

# Ping test to ensure network connectivity (optional)
# Uncomment to enable network monitoring
# ping = 192.168.1.123
# ping-count = 3

# Repair actions before reboot (optional)
# repair-binary = /usr/local/bin/watchdog-repair.sh
# repair-timeout = 60

# Logging
log-dir = /var/log/watchdog
EOF

# 4. Create log directory
mkdir -p /var/log/watchdog

# 5. Enable and start watchdog service
echo "🚀 Enabling watchdog service..."
systemctl enable watchdog
systemctl start watchdog

# 6. Verify watchdog is active
sleep 2
if systemctl is-active --quiet watchdog; then
    echo ""
    echo "✅ Hardware watchdog is now ACTIVE"
    echo ""
    echo "Configuration:"
    echo "  - Watchdog timeout: 15 seconds"
    echo "  - Pet interval: 5 seconds"
    echo "  - Device: /dev/watchdog"
    echo ""
    echo "⚠️  WARNING: If the watchdog daemon stops, the Pi will"
    echo "    automatically reboot in 15 seconds!"
    echo ""
    echo "Testing:"
    echo "  - To test, run: sudo killall watchdog"
    echo "  - Pi should reboot in ~15 seconds"
    echo ""
    echo "Monitoring:"
    echo "  - Status: sudo systemctl status watchdog"
    echo "  - Logs: sudo journalctl -u watchdog -f"
    echo ""
else
    echo ""
    echo "❌ Watchdog failed to start"
    echo "   Check logs: sudo journalctl -u watchdog -xe"
    echo ""
    exit 1
fi
