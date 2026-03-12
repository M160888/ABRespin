# Horsebox Control System - API Documentation

## Overview
This document describes the REST and WebSocket APIs for the Horsebox Control System.

---

## REST API Endpoints

### Configuration & Status

#### `GET /`
Returns the main UI (HTML page)

#### `GET /api/relays`
Returns complete configuration including all relays, zones, and settings.

**Response:**
```json
{
  "modbus_ip": "192.168.1.123",
  "modbus_port": 502,
  "popup_control": { ... },
  "zones": { ... },
  "relays": [ ... ]
}
```

---

### Zone Management (Phase 2)

#### `GET /api/zones`
Returns all zones with their assigned relays.

**Response:**
```json
{
  "living": {
    "id": "living",
    "name": "Living Area",
    "icon": "fa-couch",
    "description": "Living area, bathroom, and kitchen",
    "relay_count": 7,
    "relays": [
      {
        "id": 1,
        "name": "Bathroom Light",
        "address": 0,
        "zone": "living",
        "icon": "fa-lightbulb"
      },
      ...
    ],
    "sensors": {
      "temperature": {
        "enabled": false,
        "type": "",
        "address": "",
        "unit": "°C"
      },
      "humidity": { ... }
    }
  },
  "bedroom": { ... },
  "horse_outside": { ... },
  "unassigned": { ... }
}
```

#### `GET /api/zone/<zone_id>`
Returns details for a specific zone.

**Parameters:**
- `zone_id` (string): Zone identifier (living, bedroom, horse_outside, unassigned)

**Response:**
```json
{
  "id": "bedroom",
  "name": "Bedroom",
  "icon": "fa-bed",
  "description": "Sleeping area",
  "relay_count": 3,
  "relays": [ ... ],
  "sensors": { ... }
}
```

#### `POST /api/relay/<relay_id>/assign`
Assign a relay to a different zone.

**Parameters:**
- `relay_id` (int): Relay ID (1-30)

**Request Body:**
```json
{
  "zone": "bedroom"
}
```

**Response:**
```json
{
  "success": true,
  "relay_id": 10,
  "zone": "bedroom"
}
```

**Error Response:**
```json
{
  "error": "Zone parameter required"
}
```

#### `POST /api/zone/<zone_id>/sensor/configure`
Configure sensors for a specific zone.

**Parameters:**
- `zone_id` (string): Zone identifier

**Request Body:**
```json
{
  "sensor_type": "temperature",
  "config": {
    "enabled": true,
    "type": "i2c",
    "address": "0x48",
    "unit": "°C"
  }
}
```

**Response:**
```json
{
  "success": true,
  "zone": "living",
  "sensor_type": "temperature"
}
```

**Sensor Types:**
- `temperature`
- `humidity`

**Sensor Config Fields:**
- `enabled` (boolean): Whether sensor is active
- `type` (string): Sensor bus type (i2c, gpio, ble, usb, modbus)
- `address` (string): Hardware address or GPIO pin
- `unit` (string): Unit of measurement

---

### Scenes Management (Phase 4 & 5)

#### `GET /api/scenes`
Returns all available scenes.

**Response:**
```json
{
  "scenes": [
    {
      "id": "night_mode",
      "name": "Night Mode",
      "description": "Security lights on, interior lights off",
      "icon": "moon",
      "relay_states": {
        "5": 1,
        "6": 1,
        "1": 0,
        "2": 0
      },
      "tagged_states": {
        "security": 1
      }
    }
  ]
}
```

#### `GET /api/scene/<scene_id>`
Returns details for a specific scene.

**Parameters:**
- `scene_id` (string): Scene identifier (e.g., "night_mode")

**Response:**
```json
{
  "scene": {
    "id": "night_mode",
    "name": "Night Mode",
    "description": "Security lights on, interior lights off",
    "icon": "moon",
    "relay_states": {
      "5": 1,
      "6": 1
    },
    "tagged_states": {
      "security": 1
    }
  }
}
```

#### `POST /api/scene/<scene_id>/activate`
Activates a scene (sets all configured relays to specified states).

**Parameters:**
- `scene_id` (string): Scene identifier

**Response:**
```json
{
  "success": true,
  "scene": "night_mode",
  "relays_changed": 8
}
```

**WebSocket Event:** Broadcasts `relay_state_changed` for each relay modified

#### `POST /api/scene`
Creates a new scene.

**Request Body:**
```json
{
  "id": "my_custom_scene",
  "name": "My Custom Scene",
  "description": "Optional description",
  "icon": "lightbulb",
  "relay_states": {
    "3": 1,
    "4": 1,
    "5": 0
  },
  "tagged_states": {
    "fan": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "scene_id": "my_custom_scene"
}
```

**Notes:**
- `relay_states`: Explicit relay IDs and their states (0 or 1)
- `tagged_states`: Tag names and their states - applies to ALL relays with that tag
- At least one of `relay_states` or `tagged_states` must be provided
- Popup relays (1 & 2) should not be included in scenes

#### `PUT /api/scene/<scene_id>`
Updates an existing scene.

**Parameters:**
- `scene_id` (string): Scene identifier

**Request Body:** Same as `POST /api/scene` (without `id` field)

**Response:**
```json
{
  "success": true,
  "scene_id": "night_mode"
}
```

#### `DELETE /api/scene/<scene_id>`
Deletes a scene.

**Parameters:**
- `scene_id` (string): Scene identifier

**Response:**
```json
{
  "success": true,
  "deleted": "night_mode"
}
```

---

### Automations Management (Phase 4)

#### `GET /api/automations`
Returns all automations.

**Response:**
```json
{
  "automations": [
    {
      "id": "morning_lights",
      "name": "Morning Lights",
      "enabled": true,
      "conditions": [
        {
          "type": "time",
          "hour": 7,
          "minute": 0
        }
      ],
      "actions": [
        {
          "type": "activate_scene",
          "scene_id": "morning"
        }
      ],
      "cooldown_minutes": 60
    }
  ]
}
```

#### `GET /api/automation/<auto_id>`
Returns details for a specific automation.

**Parameters:**
- `auto_id` (string): Automation identifier

**Response:**
```json
{
  "automation": {
    "id": "morning_lights",
    "name": "Morning Lights",
    "enabled": true,
    "conditions": [ ... ],
    "actions": [ ... ],
    "cooldown_minutes": 60
  }
}
```

#### `POST /api/automation/<auto_id>/toggle`
Enables or disables an automation.

**Parameters:**
- `auto_id` (string): Automation identifier

**Response:**
```json
{
  "success": true,
  "automation_id": "morning_lights",
  "enabled": true
}
```

#### `POST /api/automation`
Creates a new automation.

**Request Body:**
```json
{
  "id": "my_automation",
  "name": "My Automation",
  "enabled": true,
  "conditions": [
    {
      "type": "sensor",
      "sensor": "temperature",
      "operator": ">",
      "value": 25
    }
  ],
  "actions": [
    {
      "type": "set_relay",
      "relay_id": 17,
      "state": 1
    }
  ],
  "cooldown_minutes": 15
}
```

**Condition Types:**
- `time`: Trigger at specific time (`hour`, `minute` fields)
- `sensor`: Trigger based on sensor value (`sensor`, `operator`, `value` fields)

**Action Types:**
- `activate_scene`: Activate a scene (`scene_id` field)
- `set_relay`: Control single relay (`relay_id`, `state` fields)
- `set_tag`: Control all relays with tag (`tag`, `state` fields)

**Response:**
```json
{
  "success": true,
  "automation_id": "my_automation"
}
```

#### `PUT /api/automation/<auto_id>`
Updates an existing automation.

**Parameters:**
- `auto_id` (string): Automation identifier

**Request Body:** Same as `POST /api/automation` (without `id` field)

**Response:**
```json
{
  "success": true,
  "automation_id": "my_automation"
}
```

#### `DELETE /api/automation/<auto_id>`
Deletes an automation.

**Parameters:**
- `auto_id` (string): Automation identifier

**Response:**
```json
{
  "success": true,
  "deleted": "my_automation"
}
```

---

### Tag Management (Phase 4.1)

#### `POST /api/relay/<relay_id>/tag`
Adds or removes a tag from a relay.

**Parameters:**
- `relay_id` (int): Relay ID (1-30)

**Request Body:**
```json
{
  "tag": "fan",
  "action": "add"
}
```

- `tag` (string): Tag name (e.g., "fan", "light", "critical")
- `action` (string): "add" or "remove"

**Response:**
```json
{
  "success": true,
  "relay_id": 17,
  "tag": "fan",
  "action": "add",
  "tags": ["fan", "ventilation"]
}
```

**Common Tags:**
- `fan`, `light`, `critical`, `security`, `ventilation`
- `heating`, `cooling`, `kitchen`, `bedroom`, `living`

**Use Cases:**
- Tag multiple relays with "fan" → Scene can turn on all fans with one `tagged_states` entry
- Tag relays with "critical" → Exclude from "All Off" scene
- Tag location-based groups → "kitchen", "bedroom" for zone-independent grouping

---

## WebSocket API (Socket.IO)

### Events from Client to Server

#### `relay_toggle`
Toggle a relay on/off.

**Payload:**
```json
{
  "id": 5,
  "state": 1
}
```

- `id` (int): Relay ID (1-30)
- `state` (int): 0 = OFF, 1 = ON

**Note:** Relays 1 & 2 (popup control) will be rejected. Use `popup_move` instead.

#### `popup_move`
Control popup motor (H-bridge safety enforced).

**Payload:**
```json
{
  "direction": "up"
}
```

- `direction` (string): "up", "down", or "release"

**Safety:**
- Opposite relay turns OFF first
- 50ms delay
- Then desired relay turns ON
- "release" turns both OFF

#### `update_relay_name`
Change a relay's display name.

**Payload:**
```json
{
  "id": 5,
  "name": "Horse Area Light"
}
```

**Note:** Name is saved to relay_config.json permanently.

#### `emergency_stop`
Immediately turn OFF all 30 relays.

**Payload:** None

**Warning:** This kills everything. Use only in emergencies.

---

### Events from Server to Client

#### `sensor_data`
Real-time sensor data (currently mock data).

**Payload:**
```json
{
  "temperature": 21.3,
  "humidity": 52.1,
  "pressure": 1013.2
}
```

**Frequency:** Every 5 seconds

#### `weather_data`
Weather information (currently mock data).

**Payload:**
```json
{
  "temperature": 18.5,
  "condition": "Partly Cloudy"
}
```

**Frequency:** Every 15 minutes

#### `relay_state_changed`
Broadcast when any relay state changes (from toggles, scenes, automations, or emergency stop).

**Payload:**
```json
{
  "relay_id": 5,
  "state": 1,
  "name": "Horse Area Light"
}
```

**Use Case:** Updates all connected clients in real-time when relay states change

---

## Zone Configuration

### Zone IDs
- `living` - Living Area (bathroom, kitchen)
- `bedroom` - Sleeping area
- `horse_outside` - Horse area and exterior
- `unassigned` - Relays not yet configured

### Zone Structure
```json
{
  "id": "zone_id",
  "name": "Display Name",
  "icon": "fa-icon-name",
  "description": "Zone description",
  "sensors": {
    "temperature": {
      "enabled": false,
      "type": "",
      "address": "",
      "unit": "°C"
    },
    "humidity": {
      "enabled": false,
      "type": "",
      "address": "",
      "unit": "%"
    }
  }
}
```

---

## Relay Configuration

### Relay Structure
```json
{
  "id": 5,
  "name": "Horse Area Light",
  "address": 4,
  "zone": "horse_outside",
  "icon": "fa-lightbulb",
  "special": "popup_control"  // Optional, only for relays 1 & 2
}
```

### Relay Icons (FontAwesome)
- Lights: `fa-lightbulb`
- Fans: `fa-fan`
- Power: `fa-power-off`
- Fridge: `fa-snowflake`
- Water: `fa-droplet`
- Popup: `fa-arrow-up`, `fa-arrow-down`
- Generic: `fa-plug`

---

## State Persistence

### State File
Location: `relay_config_state.json` (auto-created)

**Structure:**
```json
{
  "timestamp": 1737927600.0,
  "states": {
    "3": 1,
    "5": 1,
    "7": 0,
    ...
  }
}
```

**Behavior:**
- Saves after every relay state change
- Restores on startup if < 24 hours old
- **Never restores popup relays** (1 & 2) for safety
- Thread-safe with file locking

---

## Safety Features

### H-Bridge Protection
- Popup control uses relays 1 & 2
- **Never both ON simultaneously**
- Enforced in backend: `move_popup()` method
- UI-level blocking: manual toggle rejected
- 50ms safety delay between direction changes

### Emergency Stop
- Kills all 30 relays immediately
- 10ms delay between each relay (prevent bus flooding)
- Resets all UI state
- Available on all pages (floating button)

### State Persistence Safety
- Popup relays always start OFF
- Old states (>24 hours) not restored
- File corruption handled gracefully
- Falls back to fresh start if needed

---

## Error Handling

### Modbus Connection Failures
If Modbus connection fails:
1. System switches to "Terminal Log Mode"
2. All relay commands print to console instead
3. State persistence still works
4. UI remains functional
5. Auto-reconnect attempted on next command

### Invalid Requests
- Missing parameters → 400 Bad Request
- Invalid zone_id → 404 Not Found
- Invalid relay_id → Error message in response
- Popup relay manual toggle → Silently rejected (safety)

---

## Future API Endpoints (Planned)

### Activity Log
- `GET /api/activity/log` - Recent relay changes, scene activations, automation triggers
- `GET /api/activity/stats` - Usage statistics per relay

### Real Sensor Integration
- `GET /api/sensors/live` - Real sensor readings (currently mock)
- `POST /api/sensor/calibrate` - Calibrate sensor
- `GET /api/sensor/<id>/history` - Historical data

### Advanced Features
- `GET /api/relay/<id>/runtime` - Total runtime hours for relay
- `GET /api/energy/estimate` - Estimated energy consumption
- `POST /api/schedule/create` - Create time-based schedules

---

## Scene Editor UI (Phase 5)

The Visual Scene Editor is available at **Page 4** in the UI (no password required).

**Features:**
- ✅ Create new scenes visually
- ✅ Edit existing scenes
- ✅ Delete scenes (with confirmation)
- ✅ Visual relay selector (click to select)
- ✅ Tag-based selection (select all "fan" relays)
- ✅ Activate scenes with one click
- ✅ Form validation (name required, at least one relay/tag)
- ✅ Excludes popup relays (1 & 2) for safety

**Access:**
- Navigate to Scenes tab (4th tab in navigation)
- No password required (user-friendly)
- Settings page (5th tab) requires password: `1AmpMatter`

---

**Last Updated:** 2026-01-27 (Phase 5)
**API Version:** 5.0
