# Horsebox BLE Protocol Specification

Complete specification for Bluetooth Low Energy (BLE) communication between the mobile app and Raspberry Pi.

## 📋 Overview

The Horsebox BLE protocol uses GATT (Generic Attribute Profile) to advertise the Pi's WebSocket URL and device information. BLE is used **only for discovery and connection setup**, not for relay commands (WebSocket is used for commands due to lower latency).

## 🔷 BLE Service

### Horsebox Control Service

**UUID:** `0000180A-0000-1000-8000-00805F9B34FB`
**Name:** "Horsebox Control"
**Description:** Primary service for Horsebox system discovery and connection

## 📡 Characteristics

### 1. WebSocket URL Characteristic

**UUID:** `0000180B-0000-1000-8000-00805F9B34FB`
**Properties:** Read
**Size:** Variable (max 256 bytes)
**Encoding:** UTF-8 string

**Purpose:** Provides the WebSocket endpoint URL for the mobile app to connect to.

**Example Values:**
```
ws://192.168.4.1:5000/socket.io/         # Pi hotspot mode
ws://192.168.1.100:5000/socket.io/       # Home WiFi mode
```

**Read Flow:**
```javascript
// React Native (react-native-ble-plx)
const url = await device.readCharacteristicForService(
  '0000180A-0000-1000-8000-00805F9B34FB',
  '0000180B-0000-1000-8000-00805F9B34FB'
);
const websocketUrl = Buffer.from(url.value, 'base64').toString('utf-8');
console.log(websocketUrl); // "ws://192.168.4.1:5000/socket.io/"
```

**Python (Raspberry Pi - Bleak):**
```python
async def advertise_websocket_url():
    server = await BleakServer.create()

    # Get local IP
    local_ip = get_local_ip()
    url = f"ws://{local_ip}:5000/socket.io/"

    # Create characteristic
    char = BleakGATTCharacteristic(
        uuid="0000180B-0000-1000-8000-00805F9B34FB",
        properties=["read"],
        value=url.encode('utf-8')
    )

    service.add_characteristic(char)
```

---

### 2. Connection Token Characteristic (Optional)

**UUID:** `0000180C-0000-1000-8000-00805F9B34FB`
**Properties:** Read
**Size:** 32 bytes (fixed)
**Encoding:** Hex string

**Purpose:** Authentication token for WebSocket connection (optional, for future security).

**Example Value:**
```
a1b2c3d4e5f6789012345678901234567890abcd
```

**Usage:**
```javascript
// Mobile app reads token
const tokenChar = await device.readCharacteristicForService(
  '0000180A-0000-1000-8000-00805F9B34FB',
  '0000180C-0000-1000-8000-00805F9B34FB'
);
const token = Buffer.from(tokenChar.value, 'base64').toString('utf-8');

// Include token in WebSocket auth
const socket = io(websocketUrl, {
  auth: { token: token }
});
```

**Pi generates token:**
```python
import secrets

def generate_token():
    return secrets.token_hex(16)  # 32-char hex string
```

---

### 3. Relay State Push Characteristic (Optional)

**UUID:** `0000180D-0000-1000-8000-00805F9B34FB`
**Properties:** Notify
**Size:** Variable (max 128 bytes)
**Encoding:** JSON string

**Purpose:** Push relay state changes to phone via BLE (backup channel if WebSocket fails).

**Not Implemented in MVP** - WebSocket is primary channel, this is backup.

**Example Value:**
```json
{"relay_id": 5, "state": 1}
```

---

### 4. Device Name Characteristic

**UUID:** `0000180E-0000-1000-8000-00805F9B34FB`
**Properties:** Read
**Size:** Variable (max 64 bytes)
**Encoding:** UTF-8 string

**Purpose:** Human-readable name for the horsebox (useful when multiple horseboxes exist).

**Example Values:**
```
Horsebox-Alpha
Horsebox-Beta
John's Horsebox
```

**Configuration:**
User can set this in Settings page on Pi kiosk. Stored in `relay_config.json`:

```json
{
  "device_name": "Horsebox-Alpha",
  ...
}
```

---

### 5. WiFi SSID Characteristic (Future)

**UUID:** `0000180F-0000-1000-8000-00805F9B34FB`
**Properties:** Read
**Size:** Variable (max 32 bytes)
**Encoding:** UTF-8 string

**Purpose:** Pi's WiFi network name (for auto-connect feature).

**Example Value:**
```
Horsebox-Alpha
```

---

### 6. WiFi Password Characteristic (Future)

**UUID:** `00001810-0000-1000-8000-00805F9B34FB`
**Properties:** Read (with pairing)
**Size:** Variable (max 64 bytes)
**Encoding:** UTF-8 string

**Purpose:** Pi's WiFi password (requires BLE pairing for security).

**Security:**
- Only readable after BLE pairing
- Used for automatic WiFi connection

---

## 🔄 Connection Flow

### Step-by-Step Process

```
1. Mobile App Scans for BLE Devices
   ├─ Filters for devices advertising Horsebox Control Service
   └─ Displays list of found devices with names

2. User Selects Device
   ├─ App connects to BLE device
   └─ Connection established

3. App Reads Device Name (Optional)
   ├─ Read characteristic 0000180E...
   └─ Display "Connected to Horsebox-Alpha"

4. App Reads WebSocket URL
   ├─ Read characteristic 0000180B...
   └─ Parse URL: ws://192.168.4.1:5000/socket.io/

5. App Reads Connection Token (Optional)
   ├─ Read characteristic 0000180C...
   └─ Store token for WebSocket auth

6. App Disconnects from BLE (Optional)
   └─ BLE job is done, can disconnect to save battery

7. App Connects to WebSocket
   ├─ Connect to URL from step 4
   ├─ Include token from step 5 in auth
   └─ WebSocket connection established

8. App Subscribes to Events
   ├─ sensor_data
   ├─ weather_data
   └─ relay_state_changed

9. Ready to Control
   └─ User can toggle relays, activate scenes, etc.
```

### Code Example (React Native)

```javascript
import { BleManager } from 'react-native-ble-plx';
import io from 'socket.io-client';

const HORSEBOX_SERVICE_UUID = '0000180A-0000-1000-8000-00805F9B34FB';
const WEBSOCKET_URL_UUID = '0000180B-0000-1000-8000-00805F9B34FB';
const DEVICE_NAME_UUID = '0000180E-0000-1000-8000-00805F9B34FB';

class HorseboxBLEClient {
  constructor() {
    this.manager = new BleManager();
    this.device = null;
    this.socket = null;
  }

  async scan() {
    return new Promise((resolve) => {
      const devices = [];

      this.manager.startDeviceScan(
        [HORSEBOX_SERVICE_UUID],
        null,
        (error, device) => {
          if (error) {
            console.error(error);
            return;
          }

          if (device && !devices.find(d => d.id === device.id)) {
            devices.push(device);
          }
        }
      );

      // Stop scan after 10 seconds
      setTimeout(() => {
        this.manager.stopDeviceScan();
        resolve(devices);
      }, 10000);
    });
  }

  async connect(deviceId) {
    // Connect to BLE device
    this.device = await this.manager.connectToDevice(deviceId);
    await this.device.discoverAllServicesAndCharacteristics();

    // Read device name
    const nameChar = await this.device.readCharacteristicForService(
      HORSEBOX_SERVICE_UUID,
      DEVICE_NAME_UUID
    );
    const deviceName = Buffer.from(nameChar.value, 'base64').toString('utf-8');
    console.log('Device name:', deviceName);

    // Read WebSocket URL
    const urlChar = await this.device.readCharacteristicForService(
      HORSEBOX_SERVICE_UUID,
      WEBSOCKET_URL_UUID
    );
    const websocketUrl = Buffer.from(urlChar.value, 'base64').toString('utf-8');
    console.log('WebSocket URL:', websocketUrl);

    // Disconnect from BLE (optional, save battery)
    await this.device.cancelConnection();

    // Connect to WebSocket
    this.socket = io(websocketUrl);

    return {
      deviceName,
      websocketUrl,
      socket: this.socket
    };
  }
}

// Usage
const client = new HorseboxBLEClient();
const devices = await client.scan();
console.log('Found devices:', devices.map(d => d.name));

const connection = await client.connect(devices[0].id);
console.log('Connected to', connection.deviceName);

// Now control relays via WebSocket
connection.socket.emit('relay_toggle', { id: 5, state: 1 });
```

---

## 🛠️ Raspberry Pi Implementation

### BLE Hub Service (`horsebox-kiosk/src/ble_hub.py`)

```python
import asyncio
import socket
import json
from typing import Optional
from bleak import BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak.backends.characteristic import GattCharacteristicsFlags

# Service and Characteristic UUIDs
HORSEBOX_SERVICE_UUID = "0000180A-0000-1000-8000-00805F9B34FB"
WEBSOCKET_URL_UUID = "0000180B-0000-1000-8000-00805F9B34FB"
CONNECTION_TOKEN_UUID = "0000180C-0000-1000-8000-00805F9B34FB"
DEVICE_NAME_UUID = "0000180E-0000-1000-8000-00805F9B34FB"

class HorseboxBLEHub:
    def __init__(self, config_path='relay_config.json'):
        self.config = self.load_config(config_path)
        self.device_name = self.config.get('device_name', 'Horsebox-Alpha')
        self.local_ip = self.get_local_ip()
        self.websocket_url = f"ws://{self.local_ip}:5000/socket.io/"

    def load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def get_local_ip(self):
        """Get Pi's local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    async def start_advertising(self):
        """Start BLE GATT server and advertise service"""

        print(f"Starting BLE Hub for {self.device_name}")
        print(f"WebSocket URL: {self.websocket_url}")

        # Create GATT service
        service = BleakGATTServiceCollection()

        # Add WebSocket URL characteristic
        websocket_char = BleakGATTCharacteristic(
            uuid=WEBSOCKET_URL_UUID,
            properties=GattCharacteristicsFlags.read,
            value=self.websocket_url.encode('utf-8')
        )
        service.add_characteristic(websocket_char)

        # Add Device Name characteristic
        name_char = BleakGATTCharacteristic(
            uuid=DEVICE_NAME_UUID,
            properties=GattCharacteristicsFlags.read,
            value=self.device_name.encode('utf-8')
        )
        service.add_characteristic(name_char)

        # Start advertising
        print("BLE Hub is now advertising...")
        print(f"Service UUID: {HORSEBOX_SERVICE_UUID}")

        # Keep running
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    hub = HorseboxBLEHub()
    asyncio.run(hub.start_advertising())
```

### Systemd Service (`horsebox-ble-hub.service`)

```ini
[Unit]
Description=Horsebox BLE Hub
After=network.target bluetooth.target horsebox-control.service
Requires=bluetooth.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/horsebox-control/horsebox-kiosk
ExecStart=/usr/bin/python3 src/ble_hub.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Bluetooth permissions
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

### Installation

```bash
# Install Bluetooth dependencies
sudo apt-get install bluez python3-bluez

# Install Python BLE library
pip3 install bleak

# Copy service file
sudo cp horsebox-ble-hub.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable horsebox-ble-hub
sudo systemctl start horsebox-ble-hub

# Check status
sudo systemctl status horsebox-ble-hub
```

---

## 🔍 Debugging & Testing

### Test BLE Advertising (from another device)

**Using nRF Connect app (iOS/Android):**
1. Open nRF Connect
2. Scan for devices
3. Look for "Horsebox-Alpha" or custom name
4. Connect to device
5. Expand "Horsebox Control" service
6. Read "WebSocket URL" characteristic
7. Verify URL is correct

**Using Python (on laptop):**
```python
from bleak import BleakScanner

async def scan():
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"{device.name}: {device.address}")
        if "0000180A" in str(device.metadata):
            print(f"  -> Found Horsebox device!")

import asyncio
asyncio.run(scan())
```

### Test Characteristic Reading

```python
from bleak import BleakClient

DEVICE_ADDRESS = "AA:BB:CC:DD:EE:FF"  # Replace with your Pi's BLE address
WEBSOCKET_URL_UUID = "0000180B-0000-1000-8000-00805F9B34FB"

async def test_read():
    async with BleakClient(DEVICE_ADDRESS) as client:
        value = await client.read_gatt_char(WEBSOCKET_URL_UUID)
        url = value.decode('utf-8')
        print(f"WebSocket URL: {url}")

asyncio.run(test_read())
```

---

## 📊 Performance Characteristics

### BLE Connection Timing

| Phase | Expected Time | Notes |
|---|---|---|
| Scan duration | 5-10 seconds | Depends on advertising interval |
| Connection establishment | 1-3 seconds | Typical BLE connection |
| Service discovery | 0.5-1 second | GATT service enumeration |
| Characteristic read | 50-200ms | Per characteristic |
| Total | 7-15 seconds | First-time connection |

### Optimization Tips

- **Reduce scan time:** Filter by service UUID (already implemented)
- **Cache connection:** Store device address, skip scan on reconnect
- **Disconnect after setup:** Save battery, WebSocket doesn't need BLE
- **Background scanning:** Scan while showing loading screen

---

## 🔐 Security Considerations

### MVP (Phase 1)
- ✅ BLE is open (no pairing)
- ✅ Anyone in range can connect
- ⚠️ Acceptable for private vehicle use

### Production (Phase 2)
- ✅ BLE pairing with PIN code
- ✅ Encrypted characteristics
- ✅ Token-based WebSocket auth
- ✅ Settings page password (already implemented)

**Pairing Implementation (Future):**
```python
# Pi generates 6-digit PIN
pin = random.randint(100000, 999999)
print(f"Pairing PIN: {pin}")

# Display PIN on Pi screen for user to enter on phone
show_pairing_dialog(pin)

# BLE pairing with PIN
# (requires BlueZ pairing agent implementation)
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-27
**Status:** Specification Complete, Implementation Pending
