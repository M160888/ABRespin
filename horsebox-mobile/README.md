# Horsebox Mobile - BLE Remote Control

Mobile app for controlling the Horsebox system remotely via Bluetooth Low Energy (BLE).

## 🎯 Purpose

Allow horse owners to control relays, activate scenes, and monitor the horsebox from their phone while maintaining real-time synchronization with the Pi touchscreen and all other connected devices.

## ✨ Key Features

- **BLE Connection:** Direct Bluetooth connection to Raspberry Pi (no WiFi needed)
- **Real-Time Sync:** Changes on phone instantly appear on Pi screen and vice versa
- **Low Latency:** < 200ms from tap to screen update
- **Full Control:** All features available in kiosk (relays, scenes, zones)
- **Multi-Device:** Multiple phones can connect simultaneously
- **Connection Status:** Visual indicator of BLE and sync status
- **Offline Resilience:** Graceful handling of connection loss

## 🏗️ Architecture

### High-Level Flow

```
Phone App → BLE → Pi BLE Hub → WebSocket → Flask Server → Modbus → Relays
                                    ↓
                              WebSocket Broadcast
                                    ↓
                        All Connected Clients (Pi screen + phones)
```

### Technology Stack (To Be Decided)

**Option 1: React Native**
- Pros: Cross-platform (iOS + Android), JavaScript/TypeScript, hot reload
- Cons: BLE library stability can vary
- BLE Library: `react-native-ble-plx`

**Option 2: Flutter**
- Pros: True native performance, excellent BLE support, beautiful UI
- Cons: Dart language (new learning curve)
- BLE Library: `flutter_blue_plus`

**Option 3: Native (Swift + Kotlin)**
- Pros: Best performance, native BLE, full platform features
- Cons: Maintain two codebases
- BLE: CoreBluetooth (iOS), Android BLE API

**Recommendation:** Start with **React Native** for rapid prototyping, migrate to Flutter if performance issues arise.

## 🔌 BLE Communication Protocol

### BLE Service Structure

**Horsebox Control Service**
- UUID: `0000180A-0000-1000-8000-00805F9B34FB` (custom)

**Characteristics:**

1. **WebSocket URL** (Read)
   - UUID: `0000180B-0000-1000-8000-00805F9B34FB`
   - Purpose: Phone reads Pi's WebSocket URL
   - Value: `ws://192.168.1.100:5000/socket.io/`

2. **Connection Token** (Read)
   - UUID: `0000180C-0000-1000-8000-00805F9B34FB`
   - Purpose: Optional authentication token
   - Value: 32-char hex string

3. **Relay State** (Notify)
   - UUID: `0000180D-0000-1000-8000-00805F9B34FB`
   - Purpose: Push relay state changes to phone
   - Format: JSON `{"relay_id": 5, "state": 1}`

4. **Device Name** (Read)
   - UUID: `0000180E-0000-1000-8000-00805F9B34FB`
   - Purpose: Identify Pi (useful for multiple horseboxes)
   - Value: `Horsebox-Alpha` (user configurable)

### Connection Flow

```
1. Phone scans for BLE devices with Horsebox Control Service
2. User selects device from list (shows device name)
3. Phone connects to BLE device
4. Phone reads WebSocket URL characteristic
5. Phone connects to WebSocket at retrieved URL
6. Phone subscribes to relay_state_changed events
7. Phone sends commands via WebSocket (not BLE)
8. All devices receive updates via WebSocket broadcast
```

**Why not send commands over BLE?**
- BLE has higher latency (~100-300ms)
- WebSocket is faster (~20-50ms)
- BLE is only used for discovery and getting WebSocket URL
- This hybrid approach gives best performance

## 🔄 Real-Time Synchronization Strategy

### WebSocket Integration

The mobile app connects to the same WebSocket server as the Pi kiosk:

**Events the app listens to:**
- `sensor_data` - Temperature, humidity updates
- `weather_data` - Weather information
- `relay_state_changed` - Any relay state change from any source

**Events the app sends:**
- `relay_toggle` - Toggle a relay
- `popup_move` - Control popup motor
- `update_relay_name` - Rename relay (admin only)
- `emergency_stop` - Kill all relays

**State Management:**
```javascript
// App maintains local state
const [relays, setRelays] = useState([]);

// Subscribes to WebSocket events
socket.on('relay_state_changed', (data) => {
  // Update local state immediately
  setRelays(prevRelays =>
    prevRelays.map(r =>
      r.id === data.relay_id
        ? { ...r, state: data.state }
        : r
    )
  );
});

// Optimistic updates for better UX
function toggleRelay(relayId) {
  // Update UI immediately (optimistic)
  setRelays(prevRelays =>
    prevRelays.map(r =>
      r.id === relayId
        ? { ...r, state: r.state === 1 ? 0 : 1 }
        : r
    )
  );

  // Send to server
  socket.emit('relay_toggle', {
    id: relayId,
    state: relays.find(r => r.id === relayId).state === 1 ? 0 : 1
  });

  // Server will broadcast, confirming the change
}
```

### Conflict Resolution

**Scenario:** User A and User B toggle the same relay simultaneously

**Solution:**
1. Both apps optimistically update their local UI
2. Server processes commands in order received
3. Server broadcasts final state to all clients
4. Apps correct their state if server state differs from optimistic state

**Implementation:**
```javascript
let optimisticUpdates = new Map();

function toggleRelay(relayId) {
  const optimisticState = relays.find(r => r.id === relayId).state === 1 ? 0 : 1;

  // Store optimistic update
  optimisticUpdates.set(relayId, {
    state: optimisticState,
    timestamp: Date.now()
  });

  // Update UI
  updateRelayState(relayId, optimisticState);

  // Send to server
  socket.emit('relay_toggle', { id: relayId, state: optimisticState });
}

socket.on('relay_state_changed', (data) => {
  const optimistic = optimisticUpdates.get(data.relay_id);

  if (optimistic && Date.now() - optimistic.timestamp < 1000) {
    // Recent optimistic update, trust it if states match
    if (optimistic.state === data.state) {
      // Confirmed, remove from map
      optimisticUpdates.delete(data.relay_id);
      return;
    }
  }

  // Server state wins, update UI
  updateRelayState(data.relay_id, data.state);
  optimisticUpdates.delete(data.relay_id);
});
```

## 📱 UI Structure

### Navigation (Same as Kiosk)

1. **Overview** - Zone cards, quick stats, scene buttons
2. **Living** - Living area relays
3. **Bedroom** - Bedroom relays
4. **Horse** - Horse & outside relays + popup control
5. **Scenes** - Create/edit/activate scenes
6. **Settings** - System settings (password protected)

### Mobile-Specific Considerations

- **Bottom Navigation Bar** (native mobile pattern)
- **Swipe Between Pages** (same as kiosk)
- **Pull to Refresh** - Refresh connection status
- **Connection Status Banner** - Shows BLE + WebSocket status
- **Haptic Feedback** - On relay toggle, scene activation
- **Dark Mode Support** - Match kiosk's dark theme

### Connection Status UI

```
┌─────────────────────────────────┐
│  🔷 Connected to Horsebox-Alpha │  ← Green banner when connected
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  ⚠️ Connecting to Horsebox...   │  ← Yellow banner when connecting
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  ❌ Connection Lost • Tap to    │  ← Red banner when disconnected
│     Reconnect                   │
└─────────────────────────────────┘
```

## 🔧 Raspberry Pi BLE Hub Implementation

A new Python service runs on the Pi to handle BLE advertising:

**File:** `horsebox-kiosk/src/ble_hub.py`

```python
import asyncio
from bleak import BleakGATTServer, BleakGATTCharacteristic
import socket

HORSEBOX_SERVICE_UUID = "0000180A-0000-1000-8000-00805F9B34FB"
WEBSOCKET_URL_CHAR_UUID = "0000180B-0000-1000-8000-00805F9B34FB"
DEVICE_NAME_CHAR_UUID = "0000180E-0000-1000-8000-00805F9B34FB"

class HorseboxBLEHub:
    def __init__(self, device_name="Horsebox-Alpha"):
        self.device_name = device_name
        self.local_ip = self.get_local_ip()
        self.websocket_url = f"ws://{self.local_ip}:5000/socket.io/"

    def get_local_ip(self):
        # Get Pi's local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    async def start(self):
        # Start BLE GATT server
        # Advertise Horsebox Control Service
        # Expose characteristics for WebSocket URL and device name
        pass

if __name__ == "__main__":
    hub = HorseboxBLEHub()
    asyncio.run(hub.start())
```

**Service File:** `horsebox-ble-hub.service`

```ini
[Unit]
Description=Horsebox BLE Hub
After=network.target horsebox-control.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/horsebox-control/horsebox-kiosk
ExecStart=/usr/bin/python3 src/ble_hub.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 📋 Development Roadmap

### Phase 1: Proof of Concept (Week 1)
- [ ] Set up React Native project
- [ ] Implement BLE scanning and connection
- [ ] Read WebSocket URL from BLE characteristic
- [ ] Connect to WebSocket
- [ ] Display relay list
- [ ] Toggle single relay (test sync with Pi screen)

### Phase 2: Full Feature Parity (Week 2-3)
- [ ] Implement all 6 pages (Overview, Living, Bedroom, Horse, Scenes, Settings)
- [ ] Scene editor (create/edit/delete)
- [ ] Popup motor control
- [ ] Emergency stop button
- [ ] Connection status indicators
- [ ] Optimistic updates
- [ ] Error handling

### Phase 3: Polish & Testing (Week 4)
- [ ] Dark theme matching kiosk
- [ ] Haptic feedback
- [ ] Pull to refresh
- [ ] Connection retry logic
- [ ] Multi-device testing (2+ phones + Pi screen)
- [ ] Latency testing and optimization
- [ ] Edge case handling (connection loss during relay toggle)

### Phase 4: Production Ready (Week 5)
- [ ] App icon and splash screen
- [ ] User onboarding flow
- [ ] Multiple horsebox support (save paired devices)
- [ ] Settings page (app preferences)
- [ ] Build iOS and Android releases
- [ ] TestFlight / Internal testing distribution

## 🧪 Testing Strategy

### BLE Testing
- Test BLE range (should work ~10-30 meters)
- Test connection stability in moving vehicle
- Test reconnection after signal loss
- Test multiple phone connections

### Sync Testing
- Two phones + Pi screen simultaneously
- Toggle relay on phone A → verify update on phone B and Pi screen
- Toggle relay on Pi screen → verify update on both phones
- Measure latency (target < 200ms)

### Edge Cases
- Phone loses WiFi/cellular (BLE-only mode)
- Pi loses internet (local network only)
- WebSocket disconnects mid-operation
- Multiple phones toggle same relay at same time
- Emergency stop from phone (must update all devices)

## 🔒 Security Considerations

### Current (MVP)
- BLE is unencrypted (acceptable for closed network)
- WebSocket is unencrypted (ws://)
- No authentication required

### Future (Production)
- BLE pairing with PIN code
- WebSocket over TLS (wss://)
- Authentication tokens via BLE characteristic
- Password required for Settings page (already implemented in kiosk)

## 📦 Dependencies

### Mobile App (React Native)
```json
{
  "react-native-ble-plx": "^3.0.0",
  "socket.io-client": "^4.5.0",
  "react-navigation": "^6.0.0",
  "@react-native-async-storage/async-storage": "^1.17.0"
}
```

### Pi BLE Hub (Python)
```txt
bleak>=0.20.0
asyncio>=3.4.3
```

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- React Native CLI
- Xcode (iOS) or Android Studio (Android)
- Physical device (BLE doesn't work well in simulators)

### Setup
```bash
cd horsebox-mobile
npm install
npx react-native run-ios   # or run-android
```

### Testing on Device
1. Pair your phone with the Raspberry Pi via BLE
2. Ensure Pi is running Flask server (`horsebox-control.service`)
3. Ensure Pi is running BLE hub (`horsebox-ble-hub.service`)
4. Launch mobile app
5. Scan for devices
6. Select "Horsebox-Alpha"
7. Start controlling!

## 📖 Further Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed architecture diagrams
- **[BLE_PROTOCOL.md](docs/BLE_PROTOCOL.md)** - Complete BLE protocol specification
- **[API_INTEGRATION.md](docs/API_INTEGRATION.md)** - WebSocket API integration guide
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions

---

**Version:** 0.1 (In Development)
**Last Updated:** 2026-01-27
**Platform:** iOS 13+ / Android 8+
**Status:** Architecture Complete, Implementation Pending
