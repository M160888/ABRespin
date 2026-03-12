# Horsebox Mobile - Setup Guide

Quick start guide to get the mobile app running on your phone **without the Pi**.

## 🚀 Quick Start (5 minutes)

### Step 1: Find Your Laptop's IP Address

**Mac/Linux:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Windows:**
```cmd
ipconfig
```

Look for your IPv4 address, example: `192.168.1.100`

### Step 2: Update Config

Edit `src/config.js` and update the IP address:

```javascript
MOCK_WEBSOCKET_URL: 'ws://192.168.1.100:5000/socket.io/',
//                        ^^^^^^^^^^^^^^^^
//                        YOUR LAPTOP'S IP
```

### Step 3: Start Flask Backend

```bash
# In another terminal
cd horsebox-kiosk
python src/api/app.py
```

You should see:
```
🔄 Automation loop started
Starting Flask server...
 * Running on http://0.0.0.0:5000
```

### Step 4: Install Dependencies

```bash
cd horsebox-mobile
npm install
```

### Step 5: Run on Your Phone

**iOS (requires Mac + Xcode):**
```bash
cd ios
pod install
cd ..
npx react-native run-ios
```

**Android:**
```bash
npx react-native run-android
```

### Step 6: Test!

1. App should connect automatically
2. You'll see "🔷 Connected" banner (green)
3. List of 30 relays appears
4. Tap a relay to toggle it
5. Flask terminal shows: `[LOG MODE] Relay X set to ON`
6. Relay card changes color (orange border when ON)

---

## 📱 What You Should See

### Connection Screen
```
┌─────────────────────────┐
│   Horsebox Mobile       │
│   Connecting...         │
│   🔧 Mock Mode (No BLE) │
│   ws://192.168.1.100:.. │
└─────────────────────────┘
```

### Main Screen
```
┌────────────────────────────────┐
│ Horsebox Control     [STOP]    │ ← Header with emergency stop
├────────────────────────────────┤
│ 🔷 Connected                   │ ← Green status banner
├────────────────────────────────┤
│ ┌──────────────────────────┐   │
│ │ Bathroom Light     [ON]  │   │ ← Relay card (orange if ON)
│ │ ID: 1 • Zone: living     │   │
│ └──────────────────────────┘   │
│                                │
│ ┌──────────────────────────┐   │
│ │ Hallway Light     [OFF]  │   │
│ │ ID: 2 • Zone: living     │   │
│ └──────────────────────────┘   │
│                                │
│ ... (scrollable list)          │
│                                │
├────────────────────────────────┤
│ 🔧 Mock Mode - No BLE          │ ← Footer
└────────────────────────────────┘
```

### When You Toggle a Relay

1. **Tap relay card**
2. Card border turns orange (ON) or gray (OFF) **immediately**
3. Flask terminal logs: `[LOG MODE] Relay 5 (Horse Area Light) set to ON`
4. If you had the Pi kiosk open, it would update too!

---

## 🔧 Troubleshooting

### "Cannot connect to Flask server"

**Problem:** App shows connection error alert

**Solutions:**

1. **Check Flask is running:**
   ```bash
   cd horsebox-kiosk
   python src/api/app.py
   ```
   Should show "Running on http://0.0.0.0:5000"

2. **Check phone and laptop are on same WiFi:**
   - Phone: Settings → WiFi → Check network name
   - Laptop: Same network

3. **Check IP address is correct:**
   - Get laptop IP: `ifconfig` (Mac/Linux) or `ipconfig` (Windows)
   - Update `src/config.js` with correct IP
   - Rebuild app: Kill and restart `npx react-native run-ios/android`

4. **Check firewall:**
   - macOS: System Preferences → Security & Privacy → Firewall → Allow Python
   - Windows: Allow Python through Windows Firewall

### "No relays found"

**Problem:** Empty list or "No relays found"

**Solution:** Flask needs `relay_config.json` file

```bash
cd horsebox-kiosk
ls relay_config.json
# Should exist. If not, copy from backup or recreate.
```

### "Connection timeout"

**Problem:** App hangs on "Connecting..."

**Try:**

1. Check Flask terminal for errors
2. Try pinging Flask from phone's browser: `http://192.168.1.100:5000`
3. Should see HTML page
4. Check ports not blocked (5000, 5001 might be used by other apps)

### Build Errors

**iOS - "Command PhaseScriptExecution failed":**
```bash
cd ios
pod install
cd ..
npx react-native run-ios --reset-cache
```

**Android - "SDK location not found":**
```bash
# Create local.properties
echo "sdk.dir=/Users/YOUR_USERNAME/Library/Android/sdk" > android/local.properties
```

---

## 📊 Testing Checklist

Once everything is running:

- [ ] App connects automatically (green banner)
- [ ] Can see list of 30 relays
- [ ] Can toggle a relay (card changes color)
- [ ] Flask logs show relay toggle
- [ ] Pull to refresh works
- [ ] Emergency STOP button shows confirmation dialog
- [ ] Popup relays (1 & 2) are grayed out with warning text

---

## 🎯 What Works vs What Doesn't (Without Pi)

### ✅ Works Without Pi

- Full UI (all screens, layouts, navigation)
- WebSocket connection to Flask on laptop
- Relay toggling (Flask logs in terminal)
- Scenes activation (Flask processes, logs changes)
- Emergency stop (Flask turns off all relays in logs)
- Real-time sync (if you run kiosk in browser too!)
- State persistence (Flask saves to relay_config_state.json)

### ❌ Doesn't Work Without Pi

- Physical relays don't turn on/off (no Modbus board)
- BLE device discovery (uses mock mode)
- Real sensor data (shows mock values)

### 🔜 Needs Pi Later

- BLE scanning and pairing
- Real Modbus relay control
- Testing latency with actual hardware
- Multi-device sync with Pi touchscreen

---

## 🔄 Development Workflow

### 1. Make Code Changes

Edit files in `src/`:
- `src/config.js` - Configuration
- `src/services/WebSocketService.js` - WebSocket logic
- `src/screens/RelayListScreen.js` - UI components
- `App.js` - Main app structure

### 2. Reload App

**Fast Refresh (automatic):**
- Save file
- App reloads automatically on phone

**Manual Reload:**
- Shake phone → "Reload"
- Or press `R` in Metro terminal

### 3. View Logs

**React Native logs:**
```bash
# iOS
npx react-native log-ios

# Android
npx react-native log-android
```

**Flask logs:**
Watch Flask terminal - shows all relay commands

### 4. Debug

**Console logs:**
- All `console.log()` appear in Metro bundler terminal
- Look for `[WebSocket]`, `[API]`, `[RelayListScreen]` prefixes

**Chrome DevTools:**
- Shake phone → "Debug"
- Opens Chrome
- Use React DevTools extension

---

## 🎨 Customization

### Change Colors

Edit `styles` in `src/screens/RelayListScreen.js`:

```javascript
relayCardOn: {
  borderColor: '#ff6b35',  // Orange - change to any color
  backgroundColor: 'rgba(255, 107, 53, 0.1)'
}
```

### Change WebSocket URL

Edit `src/config.js`:
```javascript
MOCK_WEBSOCKET_URL: 'ws://YOUR_IP:5000/socket.io/'
```

### Disable Mock Mode (when you have Pi)

Edit `src/config.js`:
```javascript
MOCK_MODE: false,  // Enable real BLE
```

---

## 📦 What's Included

```
horsebox-mobile/
├── App.js                         # Main app component
├── index.js                       # Entry point
├── app.json                       # App configuration
├── package.json                   # Dependencies
├── src/
│   ├── config.js                  # Configuration (EDIT THIS!)
│   ├── services/
│   │   ├── WebSocketService.js    # Socket.IO connection
│   │   └── ApiService.js          # REST API calls
│   └── screens/
│       └── RelayListScreen.js     # Relay list UI
└── SETUP.md                       # This file
```

---

## 🚀 Next Steps

Once this works, we'll add:

1. **Navigation** - Bottom tabs for Overview, Living, Bedroom, Horse, Scenes, Settings
2. **Scenes Screen** - Create/edit/activate scenes
3. **Overview Dashboard** - Zone cards with quick stats
4. **Popup Control** - UP/STOP/DOWN buttons (like kiosk)
5. **Settings Screen** - Password protected
6. **BLE Integration** - When you get the Pi

But for now, you have a **working mobile app** that controls relays via WebSocket! 🎉

---

## 💡 Tips

- **Keep Flask running** - App needs it to work
- **Same WiFi** - Phone and laptop must be on same network
- **Check IP** - Update if laptop IP changes
- **View logs** - Flask terminal shows all commands
- **Pull to refresh** - Refreshes relay list
- **Shake for menu** - React Native debug menu

---

## 🆘 Need Help?

Check these in order:

1. Flask running? → `python src/api/app.py`
2. Same WiFi? → Check network on both devices
3. Correct IP? → Update `src/config.js`
4. Firewall? → Allow Python through firewall
5. Dependencies? → `npm install` again
6. Cache? → `npx react-native start --reset-cache`

If still stuck, check:
- Flask terminal for errors
- Metro bundler terminal for React errors
- Phone logs: `npx react-native log-ios` or `log-android`

---

**Ready to start? Run through the Quick Start at the top!** 🚀
