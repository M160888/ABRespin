# Horsebox Mobile - Architecture

Detailed technical architecture for the BLE-enabled mobile remote control app.

## 🎯 Design Goals

1. **Low Latency:** < 200ms from phone tap to Pi screen update
2. **Real-Time Sync:** All devices (phones + Pi screen) stay in sync
3. **Offline Resilience:** Graceful handling of connection loss
4. **Multi-Device:** Multiple phones can connect simultaneously
5. **User Experience:** Feels instant, no lag or jank

## 🏗️ System Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi 5                           │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Chromium    │◄──►│ Flask Server │◄──►│   Modbus     │ │
│  │  Kiosk UI    │    │  (SocketIO)  │    │  RelayManager│ │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘ │
│                             │                    │         │
│                      WebSocket                 Modbus      │
│                             │                    TCP       │
│                    ┌────────▼───────┐           │         │
│                    │   BLE Hub      │           │         │
│                    │  (Python)      │           │         │
│                    └────────┬───────┘           │         │
│                             │                    │         │
└─────────────────────────────┼────────────────────┼─────────┘
                              │                    │
                            BLE                 Ethernet
                              │                    │
                              │                    ▼
                              │            ┌──────────────┐
                              │            │  Waveshare   │
                              │            │  30-Channel  │
                              │            │  Relay Board │
                              │            └──────────────┘
                              ▼
                      ┌──────────────┐
                      │ Mobile Phone │
                      │              │
                      │  React Native│
                      │  App         │
                      │              │
                      └──────┬───────┘
                             │
                        WebSocket
                             │
                             ▼
                    (connects back to
                     Flask Server)
```

### Data Flow: Phone Toggles Relay

```
1. User taps relay button on phone
   │
   ├─ Optimistic Update: UI updates immediately (feels instant)
   │
   └─ WebSocket: emit('relay_toggle', {id: 5, state: 1})
      │
      ▼
2. Flask Server receives command
   │
   ├─ Validates relay ID and state
   │
   └─ Calls RelayManager.set_relay(5, 1)
      │
      ▼
3. RelayManager sends Modbus command to relay board
   │
   ├─ Relay 5 physically turns ON
   │
   └─ Returns success to Flask
      │
      ▼
4. Flask broadcasts to all WebSocket clients
   │
   ├─ emit('relay_state_changed', {relay_id: 5, state: 1, name: "..."})
   │
   ▼
5. All connected clients receive update
   │
   ├─ Pi Chromium kiosk: Updates relay button visually
   │
   ├─ Phone A (user who triggered): Confirms optimistic update
   │
   └─ Phone B (other user): Updates relay button visually

Total Time: ~50-200ms depending on network conditions
```

## 🔌 BLE Integration Strategy

### Why BLE + WebSocket Hybrid?

**BLE Alone:**
- ❌ High latency (100-300ms per command)
- ❌ Limited data throughput
- ❌ Complex state synchronization
- ✅ Works without WiFi
- ✅ Easy device discovery

**WebSocket Alone:**
- ✅ Low latency (20-50ms)
- ✅ High throughput
- ✅ Native broadcast support
- ❌ Requires WiFi or network discovery
- ❌ Hard to discover Pi's IP address automatically

**Hybrid (BLE + WebSocket):**
- ✅ BLE for device discovery and pairing
- ✅ BLE advertises WebSocket URL
- ✅ WebSocket for all commands (low latency)
- ✅ Best of both worlds

### BLE GATT Service Specification

**Service UUID:** `0000180A-0000-1000-8000-00805F9B34FB`
**Service Name:** "Horsebox Control"

#### Characteristics

| Characteristic | UUID | Properties | Purpose |
|---|---|---|---|
| WebSocket URL | `0000180B...34FB` | Read | Pi's WebSocket endpoint |
| Connection Token | `0000180C...34FB` | Read | Optional auth token |
| Relay State Push | `0000180D...34FB` | Notify | Push updates to phone |
| Device Name | `0000180E...34FB` | Read | Human-readable name |
| WiFi SSID | `0000180F...34FB` | Read | Pi's WiFi network |
| WiFi Password | `00001810...34FB` | Read | For auto-connect |

#### Connection Sequence Diagram

```
Phone                BLE Hub (Pi)         Flask Server
  │                       │                     │
  │   1. BLE Scan         │                     │
  ├──────────────────────►│                     │
  │                       │                     │
  │   2. Device List      │                     │
  │◄──────────────────────┤                     │
  │   (Horsebox-Alpha)    │                     │
  │                       │                     │
  │   3. Connect          │                     │
  ├──────────────────────►│                     │
  │                       │                     │
  │   4. Read WebSocket URL                     │
  ├──────────────────────►│                     │
  │   ws://192.168.1.100:5000/socket.io/        │
  │◄──────────────────────┤                     │
  │                       │                     │
  │   5. WebSocket Connect                      │
  ├─────────────────────────────────────────────►│
  │                       │                     │
  │   6. Subscribe to Events                    │
  ├─────────────────────────────────────────────►│
  │                       │                     │
  │   7. Ready to Control │                     │
  │◄────────────────────────────────────────────┤
  │                       │                     │
```

## 🔄 State Management (Mobile App)

### Redux / Context Architecture

```javascript
// State Structure
const AppState = {
  connection: {
    bleConnected: false,
    bleDeviceName: null,
    websocketConnected: false,
    websocketUrl: null,
    reconnecting: false,
    lastSeen: Date.now()
  },
  relays: [
    { id: 1, name: "Bathroom Light", state: 0, zone: "living", ... },
    { id: 2, name: "Hallway Light", state: 1, zone: "living", ... },
    // ... 30 relays
  ],
  scenes: [
    { id: "night_mode", name: "Night Mode", ... },
    // ... all scenes
  ],
  zones: {
    living: { id: "living", name: "Living Area", ... },
    bedroom: { ... },
    horse_outside: { ... }
  },
  sensors: {
    temperature: 21.5,
    humidity: 52.0,
    pressure: 1013.2
  },
  optimisticUpdates: new Map() // Track pending updates
};
```

### Actions

```javascript
// Connection Actions
CONNECT_BLE_START
CONNECT_BLE_SUCCESS
CONNECT_BLE_FAILURE
DISCONNECT_BLE
CONNECT_WEBSOCKET_SUCCESS
DISCONNECT_WEBSOCKET

// Relay Actions
TOGGLE_RELAY_OPTIMISTIC  // Immediate UI update
TOGGLE_RELAY_REQUEST     // Send to server
RELAY_STATE_CHANGED      // Server confirmation
RELAY_STATE_SYNC         // Periodic full sync

// Scene Actions
ACTIVATE_SCENE
CREATE_SCENE
UPDATE_SCENE
DELETE_SCENE

// Sensor Actions
UPDATE_SENSOR_DATA
UPDATE_WEATHER_DATA
```

### Optimistic Updates Flow

```javascript
// 1. User taps relay button
dispatch({ type: 'TOGGLE_RELAY_OPTIMISTIC', payload: { id: 5 } });
// UI updates immediately (state flips)

// 2. Send command to server
dispatch({ type: 'TOGGLE_RELAY_REQUEST', payload: { id: 5, state: 1 } });
// WebSocket: emit('relay_toggle', ...)

// 3. Add to pending map
optimisticUpdates.set(5, { state: 1, timestamp: Date.now() });

// 4. Wait for server confirmation
socket.on('relay_state_changed', (data) => {
  if (data.relay_id === 5) {
    const pending = optimisticUpdates.get(5);
    if (pending && data.state === pending.state) {
      // Success: remove from pending
      optimisticUpdates.delete(5);
    } else {
      // Conflict: server state differs
      // Revert optimistic update, use server state
      dispatch({ type: 'RELAY_STATE_CHANGED', payload: data });
    }
  }
});

// 5. Timeout handler (if server doesn't respond in 3s)
setTimeout(() => {
  if (optimisticUpdates.has(5)) {
    // Server didn't confirm, revert optimistic update
    dispatch({ type: 'RELAY_STATE_SYNC', payload: { id: 5 } });
    optimisticUpdates.delete(5);
    showError("Failed to toggle relay");
  }
}, 3000);
```

## 🌐 Network Topology

### Local Network Mode (Default)

```
Pi creates WiFi hotspot: "Horsebox-Alpha"
Password: "horsebox2024" (or auto-generated)

Phone connects to "Horsebox-Alpha"
Phone gets IP: 192.168.4.2
Pi IP: 192.168.4.1

BLE: Phone discovers Pi
WebSocket: ws://192.168.4.1:5000/socket.io/

Advantages:
✅ Works anywhere (no external WiFi needed)
✅ Low latency (direct connection)
✅ Private network (secure)

Disadvantages:
❌ Phone loses internet access while connected
❌ Single network only
```

### Home Network Mode (Alternative)

```
Pi connects to existing WiFi: "Home-WiFi"
Pi IP: 192.168.1.100 (DHCP)

Phone connects to same "Home-WiFi"
Phone IP: 192.168.1.101

BLE: Phone discovers Pi
BLE advertises: ws://192.168.1.100:5000/socket.io/
Phone connects to WebSocket

Advantages:
✅ Phone keeps internet access
✅ Can have multiple devices on same network
✅ Remote access possible (with port forwarding)

Disadvantages:
❌ Requires existing WiFi in horsebox
❌ WiFi password needed
❌ Potential latency if network is congested
```

**Recommendation:** Use **Local Network Mode** for simplicity and reliability. Pi creates its own hotspot.

## 🔐 Security Model

### Phase 1 (MVP - Current)
- BLE: No pairing required (open connection)
- WebSocket: Unencrypted (ws://)
- Authentication: None (trusted local network)

**Risk:** Anyone in BLE range can connect
**Mitigation:** Physical access required (vehicle interior)

### Phase 2 (Production)
- BLE: Pairing with 6-digit PIN code
- WebSocket: TLS encryption (wss://)
- Authentication: Token-based (token from BLE characteristic)
- Settings page: Password required (already implemented: `1AmpMatter`)

**Implementation:**
```javascript
// Phone reads token from BLE
const token = await bleDevice.readCharacteristic(CONNECTION_TOKEN_UUID);

// Include token in WebSocket connection
const socket = io(websocketUrl, {
  auth: { token: token }
});

// Server validates token
io.on('connection', (socket) => {
  const token = socket.handshake.auth.token;
  if (!isValidToken(token)) {
    socket.disconnect();
    return;
  }
  // Connection allowed
});
```

## 📊 Performance Targets

### Latency Benchmarks

| Action | Target | Acceptable | Unacceptable |
|---|---|---|---|
| Relay toggle (phone → Pi screen) | < 100ms | < 200ms | > 500ms |
| Scene activation | < 200ms | < 500ms | > 1000ms |
| Connection establishment | < 3s | < 5s | > 10s |
| UI responsiveness | < 16ms | < 50ms | > 100ms |

### Network Requirements

- **BLE Range:** 10-30 meters (typical vehicle size)
- **WebSocket:** 1-2 concurrent connections per phone
- **Bandwidth:** ~1-10 KB/s per connection (very low)
- **Packet Loss Tolerance:** Up to 5% (WebSocket has built-in retry)

## 🧪 Testing Strategy

### Unit Tests
- Redux reducers (state transitions)
- Action creators
- WebSocket event handlers
- BLE characteristic parsing

### Integration Tests
- BLE connection flow (scan → connect → read → disconnect)
- WebSocket connection (connect → subscribe → send → receive)
- Optimistic update flow (request → confirm → timeout)

### E2E Tests (Manual)
1. **Single Device Test:**
   - Phone connects to Pi
   - Toggle relay on phone
   - Verify relay state on Pi screen
   - Toggle relay on Pi screen
   - Verify relay state on phone

2. **Multi-Device Test:**
   - Phone A and Phone B connect
   - Toggle relay on Phone A
   - Verify update on Phone B and Pi screen
   - Measure latency with timer

3. **Connection Loss Test:**
   - Phone connected and working
   - Turn off Pi WiFi
   - Verify app shows "disconnected" state
   - Turn on Pi WiFi
   - Verify app reconnects automatically

4. **Range Test:**
   - Start with phone next to Pi (working)
   - Walk away slowly
   - Measure distance when BLE disconnects
   - Verify WebSocket stays connected (if on WiFi)

5. **Stress Test:**
   - Toggle 10 relays rapidly in succession
   - Verify all states sync correctly
   - No UI jank or freezing

## 🚀 Deployment Architecture

### Pi Setup (Production)

```
/home/pi/horsebox-control/
├── horsebox-kiosk/
│   ├── src/
│   │   ├── api/app.py              # Flask server
│   │   ├── RelayManager.py
│   │   ├── AutomationEngine.py
│   │   └── ble_hub.py              # BLE hub (NEW)
│   └── relay_config.json
│
└── systemd services:
    ├── horsebox-control.service    # Flask server
    ├── horsebox-kiosk.service      # Chromium kiosk
    └── horsebox-ble-hub.service    # BLE advertising (NEW)
```

### Mobile App (Production)

```
App Store / Google Play
├── iOS .ipa bundle
└── Android .apk bundle

App Data (on device):
├── Paired Devices (AsyncStorage)
│   └── [{ id: "...", name: "Horsebox-Alpha", lastSeen: ... }]
├── User Preferences
│   └── { theme: "dark", haptics: true, ... }
└── Cached State (offline resilience)
    └── Last known relay states
```

## 📈 Future Enhancements

### Phase 3 Features
- **Multiple Horsebox Support:** Save and switch between paired devices
- **Push Notifications:** Alert when automations trigger
- **Voice Control:** "Hey Siri, turn on the lights"
- **Widgets:** Quick relay control from home screen

### Phase 4 Features
- **Remote Access:** Control via internet (with VPN or cloud relay)
- **Activity Log:** See all relay changes with timestamps
- **Usage Statistics:** Track relay runtime, energy consumption
- **Scene Scheduling:** Time-based scene activation

---

**Document Version:** 1.0
**Last Updated:** 2026-01-27
**Status:** Architecture Complete, Implementation Pending
