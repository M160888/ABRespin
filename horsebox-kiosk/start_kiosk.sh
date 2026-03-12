#!/bin/bash
# Horsebox Control System - Secure Kiosk Startup Script
# This script launches the UI in secure kiosk mode with keyboard shortcuts disabled

# Wait for Flask server to be ready
echo "Waiting for Flask server..."
until curl -s http://localhost:5000 > /dev/null; do
    echo "Flask not ready yet, waiting..."
    sleep 2
done
echo "Flask server is ready!"

# Disable screen blanking and power management
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor after 5 seconds of inactivity (optional)
# Uncomment the line below if you want auto-hide cursor
# unclutter -idle 5 &

# Launch Chromium in secure kiosk mode
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --fast \
    --fast-start \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --disable-translate \
    --disable-features=TranslateUI \
    --disable-pinch \
    --overscroll-history-navigation=0 \
    --check-for-update-interval=31536000 \
    --disable-popup-blocking \
    --disable-prompt-on-repost \
    --incognito \
    http://localhost:5000

# Note: Chromium will exit when you click "Exit Kiosk Mode" in Settings
# or manually kill it with: pkill chromium
echo "Kiosk exited cleanly"
