#!/bin/bash
# Horsebox Kiosk - Chromium launcher
# Requires Pi to be set to X11 mode (raspi-config → Advanced → Wayland → X11)

# Disable screen blanking and power saving
xset s off
xset s noblank
xset -dpms

# Hide cursor immediately when idle (touchscreen kiosk — no mouse needed)
unclutter -idle 0.5 -root &

# Wait for Flask backend to be available (max 40 seconds)
echo "Waiting for Flask backend..."
for i in $(seq 1 40); do
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo "Backend ready after ${i}s."
        break
    fi
    sleep 1
done

# Launch Chromium in kiosk mode
# NOTE: no --incognito — localStorage is used to persist theme selection
exec chromium-browser \
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
    --touch-events=enabled \
    --check-for-update-interval=31536000 \
    --disable-popup-blocking \
    --disable-prompt-on-repost \
    http://localhost:5000

echo "Kiosk exited"
