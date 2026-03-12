# CHECKPOINT - Horsebox Control System

## Status: Phase 6 Complete - Monorepo + Mobile Architecture ✓

## Current Implementation

### UI Design (Complete Redesign)
- **Professional industrial dark theme** with orange/teal accents
- **6-page layout:**
  - Page 0: Overview dashboard with zone cards and quick scene buttons
  - Page 1: Living Area zone relays
  - Page 2: Bedroom zone relays
  - Page 3: Horse & Outside zone with popup motor control
  - Page 4: Scenes Editor (visual scene creation/editing - no password)
  - Page 5: Settings (6 tabs: System, Names, Zones, Sensors, Automations, Tags)
- **3-button popup control** - UP (momentary), STOP, DOWN (momentary) with H-bridge safety
- **Zone-based relay organization** - dynamically loaded from API
- **Scenes & Automations** - Quick access on Overview, full management in Settings
- **Tag-based relay grouping** - Future-proof scenes and automations
- **Logo spaces** in header (left and right corners)
- **Real-time updates** via WebSocket (SocketIO) including scene activations
- **Touch-optimized** controls with visual feedback
- **Password-protected Settings** (password: `1AmpMatter`)

### Backend Architecture
- **Flask + Flask-SocketIO** for real-time communication
- **Modbus TCP** communication with Waveshare 30-channel relay board
- **Terminal log mode** fallback when Modbus unavailable
- **Threaded background tasks** for sensor and weather data
- **Editable relay names** with persistent storage

### Critical Safety Features ⚠️
1. **H-Bridge Motor Safety (Popup Control)**
   - Relays 1 & 2 control motor direction via H-bridge
   - **NEVER both on simultaneously** - prevents short-circuit
   - 50ms safety delay between direction changes
   - Opposite relay turns OFF before new relay turns ON
   - 3-button control: UP (momentary), STOP (immediate), DOWN (momentary)

2. **Emergency Stop Button (NEW - Phase 1)**
   - Floating red button on all pages (bottom-right)
   - Kills ALL 30 relays immediately
   - Confirmation dialog prevents accidental activation
   - Visual feedback + UI state reset

3. **State Persistence (NEW - Phase 1)**
   - Saves relay states after every change
   - Restores states on reboot (if < 24 hours old)
   - NEVER restores popup relays (safety first)
   - Survives power outages / crashes

4. **UI-Level Protection**
   - Popup relays (1 & 2) **cannot be manually toggled** from relay cards
   - Must use button controls which enforce safety logic
   - Backend rejects manual toggle attempts on popup relays

5. **Modbus Error Handling**
   - Auto-reconnect on connection loss
   - Graceful fallback to terminal log mode
   - Connection status indicator in UI

### Files Structure
```
AB/
├── src/
│   ├── api/
│   │   ├── app.py                  # Flask app with SocketIO + API endpoints
│   │   └── templates/
│   │       └── index.html          # Complete UI (single file)
│   ├── RelayManager.py             # Modbus control + safety logic
│   └── AutomationEngine.py         # Scenes & automation engine (NEW)
├── relay_config.json               # Relay + zone + scene + automation config
├── relay_config_state.json         # Relay state persistence (auto-created)
├── requirements.txt                # Python dependencies
├── DEPLOYMENT.md                   # Raspberry Pi deployment guide
├── WATCHDOG.md                     # Watchdog configuration guide
├── system_check.py                 # Pre-deployment verification script
└── CHECKPOINT.md                   # This file
```

### Configuration (relay_config.json)
- **Modbus IP:** 192.168.1.123 (Waveshare relay board)
- **Modbus Port:** 502 (TCP)
- **Popup Control:** Relays 1 (up) and 2 (down)
- **30 Relays:** Addresses 0-29, IDs 1-30

### Dependencies
- Flask >= 3.0.0
- Flask-SocketIO >= 5.3.0
- pymodbus >= 3.5.0
- eventlet >= 0.33.0 (production socket server)

## Deployment Platform
- **Target:** Raspberry Pi 5
- **Hardware:** Waveshare 30-Channel Modbus TCP Relay Board
- **Connection:** Ethernet cable (Modbus TCP)
- **Display:** Chromium kiosk mode (fullscreen)

## Testing Checklist
- [x] UI responsive design
- [x] WebSocket real-time updates
- [x] Popup slider control (left/right/release)
- [x] Relay toggle functionality
- [x] Editable relay names with persistence
- [x] H-bridge safety logic (never both on)
- [x] Manual popup relay toggle blocked
- [x] Modbus TCP communication
- [x] Terminal log mode fallback
- [x] Multi-page navigation with swipe support
- [x] Header clock and status indicators

## Pre-Deployment Steps
1. Run system check: `python3 system_check.py`
2. Verify Modbus IP matches Waveshare board
3. Test relay board connection
4. Configure Pi for kiosk mode
5. Set up systemd service for auto-start
6. Test popup motor safety (verify only one relay active)

## Known Limitations
- Mock sensor data (not connected to real sensors yet)
- Mock weather data (needs API integration)
- No limit switches for popup motor (manual monitoring required)
- Automation creation UI not yet implemented (manual JSON editing required for automations)
- No runtime tracking or usage statistics
- No activity log (relay changes, scene activations, automation triggers)

## Future Enhancements
- **Automation Editor UI**: Visual creation and editing (currently manual JSON)
- **Real Sensor Integration**: Temperature, humidity sensors via I2C or Modbus
- **Weather API Integration**: Live weather data
- **Activity Log**: Historical view of relay state changes, scene activations, automation triggers
- **Usage Statistics**: Runtime tracking per relay, energy consumption estimates
- **Advanced Automations**: OR logic, relay state conditions, nested conditions
- **Scheduling**: Weekly schedules, sunrise/sunset triggers
- **Remote Access**: Secure VPN or cloud integration
- **Mobile App**: Native iOS/Android app
- **Voice Control**: Integration with Alexa/Google Home

## Safety Notes
⚠️ **CRITICAL:** Never modify popup relay IDs (1 & 2) without updating wiring
⚠️ **CRITICAL:** Always test popup motor control in both directions before full load
⚠️ **WARNING:** No hardware limit switches - operator must monitor motor travel
⚠️ **WARNING:** Ensure adequate motor cooling during extended operation

## Maintenance
- Backup `relay_config.json` regularly (contains custom relay names)
- Monitor system logs: `sudo journalctl -u horsebox-kiosk -f`
- Check Modbus connection health periodically
- Update relay names as equipment changes

---

## Phase 1 Completion Notes (Jan 26, 2026)

**Implemented:**
- ✅ Emergency Stop button (floating, all pages)
- ✅ State Persistence (automatic save/restore)
- ✅ 3-Button Popup Control (replaced slider)

**Files Changed:**
- `src/api/templates/index.html` - Emergency stop button + 3-button control
- `src/api/app.py` - Emergency stop SocketIO handler
- `src/RelayManager.py` - State persistence + emergency_stop_all()
- `relay_config_state.json` - Auto-created state file (not in git)

**Breaking Changes:** None - fully backward compatible

## Phase 2 Completion Notes (Jan 26, 2026)

**Implemented:**
- ✅ Zone-based configuration structure
- ✅ 4 zones defined: Living Area, Bedroom, Horse & Outside, Unassigned
- ✅ All 30 relays assigned to zones (18 active, 12 unassigned)
- ✅ Sensor configuration structure per zone
- ✅ Backend APIs for zone management
- ✅ Relay icons added for better visual identification

**Zone Breakdown:**
- **Living Area** (7 relays): Bathroom Light, Hallway Light, Kitchen Strip, Main Power, Fridge, Water Pump, X Strip
- **Bedroom** (3 relays): Skylight, Light Above Bed, Popup Strip Light
- **Horse & Outside** (6 relays): Horse Area Light, Outside Light, Front Fan, Back Fan, Popup Control (2 relays)
- **Unassigned** (14 relays): Ready for future deployment

**New API Endpoints:**
- `GET /api/zones` - All zones with relays
- `GET /api/zone/<zone_id>` - Specific zone details
- `POST /api/relay/<relay_id>/assign` - Reassign relay to zone
- `POST /api/zone/<zone_id>/sensor/configure` - Configure zone sensors

**Files Changed:**
- `relay_config.json` - Added zones structure, zone field per relay, icons
- `src/api/app.py` - New zone management endpoints
- `src/RelayManager.py` - Zone assignment and sensor config methods

**Breaking Changes:** None - fully backward compatible with Phase 1

## Phase 3 Completion Notes (Jan 26, 2026)

**Implemented:**
- ✅ Complete UI transformation to zone-based architecture
- ✅ 5-page layout (Overview, Living, Bedroom, Horse, Settings)
- ✅ Settings page with 4 tabs
- ✅ Overview dashboard with zone cards
- ✅ Dynamic zone page generation from API
- ✅ Relay name editing in Settings
- ✅ Zone assignment visualization

**UI Structure:**
- **Page 0: Overview** - Dashboard with all zones, click to navigate
- **Page 1: Living Area** - Bathroom, Hallway, Kitchen lights, Main Power, Fridge, Water Pump, X Strip
- **Page 2: Bedroom** - Skylight, Light Above Bed, Popup Strip
- **Page 3: Horse & Outside** - Horse Light, Outside Light, Fans, Popup Control
- **Page 4: Settings** - System Info, Relay Names, Zone Assignment, Sensor Config

**Settings Page Tabs:**
1. **System Info**: Modbus IP/Port, relay counts, manufacturer info
2. **Relay Names**: Bulk edit interface for all 30 relays
3. **Zone Assignment**: Visual display of relays grouped by zone
4. **Sensor Config**: Placeholder for Phase 4 (API instructions)

**Files Changed:**
- `src/api/templates/index.html` - Complete HTML/CSS/JS rewrite (500+ lines changed)
  - New page structure (5 pages instead of 4)
  - Settings page CSS (tabs, grids, inputs)
  - Overview dashboard CSS
  - JavaScript rewrite for zone-based loading
  - Settings tab switching logic

**Breaking Changes:** None - backward compatible with Phase 1 & 2

## Phase 3.1 Completion Notes (Jan 26, 2026)

**Implemented:**
- ✅ Removed inline name editing from relay cards (Settings-only now)
- ✅ Fixed Active Relays count to show ON relays (not assigned relays)
- ✅ Full drag-and-drop zone assignment implementation
- ✅ Real-time active relay counter in System Info

**Issues Fixed:**
- Name editing was on cards AND settings (now only in settings)
- "Active Relays" counted assigned relays instead of ON relays
- Zone assignment said "coming soon" (now fully functional)

**Files Changed:**
- `src/api/templates/index.html` - Removed contenteditable, drag-and-drop implementation
- `CLAUDE_CONTEXT.md` - Added Phase 3.1 section

**User Feedback:**
"name edit it's still on the card itself, it's not in settings"
"Active relays in settings doesn't update when i turn 1 or more relays on"
"how soon?" (drag-and-drop)

## Phase 3.2 Completion Notes (Jan 26, 2026)

**Implemented:**
- ✅ Password-protected Settings page (password: `1AmpMatter`)
- ✅ Active Relays counter moved to Overview page
- ✅ Emergency stop now resets active relay counter
- ✅ Kiosk exit button in Settings (with manual instructions)
- ✅ Secure kiosk mode (keyboard shortcuts disabled)
- ✅ Hardware watchdog support (auto-reboot on hang)
- ✅ Systemd watchdog support (auto-restart Flask on hang)

**Security Features:**
- Password-protected Settings access
- Kiosk mode blocks Alt+F4, F11, Ctrl+W
- Authorized exit: UI button (password) or SSH
- No auto-restart on kiosk exit (allows debugging)

**Reliability Features:**
- Hardware watchdog: Reboots Pi if OS hangs (15s timeout)
- Systemd watchdog: Restarts Flask if app hangs (10s timeout)
- Two-layer protection for high availability

**New Files:**
- `start_kiosk.sh` - Secure kiosk launcher script
- `horsebox-control.service` - Flask backend service (with watchdog)
- `horsebox-kiosk.service` - Kiosk UI service
- `enable_watchdog.sh` - Hardware watchdog setup script
- `WATCHDOG.md` - Complete watchdog documentation

**Files Changed:**
- `src/api/templates/index.html` - Password protection, Overview counters, kiosk exit button
- `src/api/app.py` - Systemd watchdog notifications
- `requirements.txt` - Added systemd-python
- `DEPLOYMENT.md` - Complete rewrite with secure kiosk + watchdog instructions

**User Questions:**
"does alt f4 works with settings disabled?" → Led to kiosk security implementation
"that means anyone can plug a keyboard and exit kiosk mode?" → Led to proper kiosk mode
"how could we implement a watchdog that reboots pi if software hangs?" → Watchdog implementation

## Phase 4 Completion Notes (Jan 27, 2026)

**Implemented:**
- ✅ Scenes system (preset relay configurations)
- ✅ Automations engine (time and sensor-based triggers)
- ✅ AutomationEngine with background evaluation loop
- ✅ Scene activation via UI and API
- ✅ Automation enable/disable controls
- ✅ WebSocket broadcasting for relay state updates
- ✅ Frontend UI updates when scenes activate

**Scenes:**
- **Night Mode**: Security lights on, most lights off
- **Morning**: Kitchen, bathroom, water pump on
- **All Off**: Emergency shutdown (all relays off except popup)
- **Ventilation**: All fans on for maximum airflow

**Automations:**
- Time-based triggers (e.g., activate scenes at specific times)
- Sensor-based triggers (e.g., turn on fans when temp > 25°C)
- Cooldown system to prevent rapid re-triggering
- AND logic for multiple conditions

**New Features:**
- Background automation thread (evaluates every 10 seconds)
- Sensor data cache for automation conditions
- Scene quick-access buttons on Overview page
- Settings tabs for Scenes and Automations management

**API Endpoints Added:**
- `GET /api/scenes` - Get all scenes
- `GET /api/scene/<scene_id>` - Get specific scene
- `POST /api/scene/<scene_id>/activate` - Activate scene with WebSocket broadcast
- `POST /api/scene` - Create scene
- `PUT /api/scene/<scene_id>` - Update scene
- `DELETE /api/scene/<scene_id>` - Delete scene
- `GET /api/automations` - Get all automations
- `GET /api/automation/<auto_id>` - Get specific automation
- `POST /api/automation/<auto_id>/toggle` - Enable/disable automation
- `POST /api/automation` - Create automation
- `PUT /api/automation/<auto_id>` - Update automation
- `DELETE /api/automation/<auto_id>` - Delete automation

**Files Changed:**
- `relay_config.json` - Added scenes and automations sections
- `src/AutomationEngine.py` - NEW FILE - Complete automation engine
- `src/api/app.py` - 12 new API endpoints, automation engine integration
- `src/api/templates/index.html` - Scenes/automations CSS, JavaScript, UI sections

**User Feedback:**
"scenes, if i hit ventilation, wasn't it supposed to turn all the fans on and that should've reflect in active relays as well?"
→ Fixed by adding WebSocket listener for relay_state_changed events

## Phase 4.1 Completion Notes (Jan 27, 2026)

**Implemented:**
- ✅ Tag system for relay grouping
- ✅ Tag-based scene targeting (`tagged_states`)
- ✅ Tag-based automation actions (`set_tag`)
- ✅ Tag management UI in Settings
- ✅ Backend API for adding/removing tags
- ✅ Dynamic tag resolution at runtime

**Tag System Concept:**
Instead of hardcoding relay IDs in scenes/automations, you can target groups of relays by tags:
- Tag relays: `"tags": ["fan", "ventilation"]`
- Scene uses tag: `"tagged_states": {"fan": 1}` (turns on ALL relays with "fan" tag)
- Automation action: `{"type": "set_tag", "tag": "fan", "state": 1}`

**Common Tags:**
- `fan`, `light`, `critical`, `security`, `ventilation`, `heating`, `cooling`
- `kitchen`, `bedroom`, `living` (location-based)
- Custom tags supported

**Benefits:**
- **Future-proof**: Add new fan on relay 19 → Just tag it "fan" → Ventilation scene automatically includes it
- **Maintainable**: No need to manually update scenes when adding/removing relays
- **Flexible**: Mix explicit relay IDs and tags in same scene

**Settings UI Added:**
- **Tags tab** in Settings (7th tab)
- **Common tags display** with relay counts
- **Per-relay tag management** with clickable tag pills
- **Custom tag support** (add any tag name)

**API Endpoints Added:**
- `POST /api/relay/<relay_id>/tag` - Add or remove tag from relay

**Files Changed:**
- `relay_config.json` - Added tags arrays to relays, updated Ventilation scene and Hot Day Cooling automation
- `src/AutomationEngine.py` - Added `get_relays_by_tag()`, tag resolution in `activate_scene()` and `execute_action()`
- `src/RelayManager.py` - Added `manage_relay_tag()` method
- `src/api/app.py` - Added `/api/relay/<relay_id>/tag` endpoint
- `src/api/templates/index.html` - Added Tags tab, CSS, JavaScript for tag management

**Example Tag Usage:**
```json
// Relay configuration
{
    "id": 16,
    "name": "Fan Test",
    "tags": ["fan", "ventilation"]
}

// Scene using tags
{
    "id": "ventilation",
    "tagged_states": {
        "fan": 1  // Turns on ALL relays with "fan" tag
    }
}

// Automation using tags
{
    "actions": [
        {"type": "set_tag", "tag": "fan", "state": 1}
    ]
}
```

**User Request:**
"ugh I have bad news, there's more to be done... let'say we add at a later stage another fan on one of them spare relays..can we somehow tag it as fan so scenes/automations automatically adjust to turn that on as well with the other fans?"
→ Led to complete tag system implementation

## Phase 5 Completion Notes (Jan 27, 2026)

**Implemented:**
- ✅ Visual Scene Editor UI (no password required)
- ✅ Create/Edit/Delete scenes through UI
- ✅ Visual relay selector (click to select relays)
- ✅ Tag-based scene creation (select tags to control groups)
- ✅ Scene activation from editor
- ✅ 6-page navigation (added Scenes page)
- ✅ Settings moved to Page 5 (password protected)

**New UI Structure:**
- **Page 0:** Overview Dashboard
- **Page 1:** Living Area
- **Page 2:** Bedroom
- **Page 3:** Horse & Outside
- **Page 4:** **Scenes Editor** (NEW - No password, user-friendly)
- **Page 5:** Settings (Password protected - admin features)

**Scene Editor Features:**
- Visual scene builder with relay selection grid
- Tag selector for group control (e.g., all "fan" relays)
- Scene card list with activate/edit/delete actions
- Empty state for new users
- Form validation (name required, at least one relay/tag)
- Excludes popup relays (1 & 2) from selection for safety
- Professional dark theme matching existing UI

**API Integration:**
- Uses existing `/api/scene` endpoints (GET, POST, PUT, DELETE)
- Uses existing `/api/scene/<id>/activate` endpoint
- Loads relays from `/api/relays` for selector
- Extracts available tags from relay configurations
- Real-time scene activation with WebSocket updates

**User Experience:**
- **End Users (Horse Owners):** Can create and manage scenes without Settings password
- **Admins:** Automations and system configuration remain password-protected in Settings
- Clear separation between user features and admin features

**Files Changed:**
- `src/api/templates/index.html` - Added 6th page, Scene Editor UI, JavaScript logic
  - New CSS: Scene cards, form, relay selector, tag selector (~400 lines)
  - New HTML: Scene Editor page structure (~100 lines)
  - New JavaScript: Scene CRUD operations, form handling (~350 lines)
  - Updated navigation: 6 tabs instead of 5
  - Updated transforms: 16.67% instead of 20% for 6 pages
  - Updated password protection: Page 5 instead of Page 4
  - Removed: Scenes tab from Settings (now separate page)

**Breaking Changes:** None - fully backward compatible with Phase 4.1
- Existing scenes work immediately
- API unchanged
- Settings password still works
- All previous features intact

**User Request:**
"one of them should not be in settings because settings is password protected and we want the user to be able to configure scenes without me giving him access to the settings page"
→ Led to Scene Editor as separate page (Page 4)

---

**Last Updated:** 2026-01-27 (Phase 5 Complete)
**Version:** 5.0 (Visual Scene Editor)
**Status:** Production-Ready with Full Scene Management UI
**Next Steps:** Real sensors integration, Activity Log, Usage Statistics

## Phase 6 Completion Notes (Jan 27, 2026)

**Implemented:**
- ✅ Monorepo structure (kiosk + mobile + shared docs)
- ✅ Mobile app architecture design
- ✅ BLE + WebSocket hybrid protocol
- ✅ Real-time sync strategy (optimistic updates)
- ✅ Comprehensive documentation (3 docs, 1500+ lines)

**Repository Structure:**
```
AB/
├── horsebox-kiosk/          # Raspberry Pi kiosk (existing)
├── horsebox-mobile/         # Mobile app (new)
└── shared-docs/             # Shared documentation
```

**Mobile App Architecture:**
- **Platform:** React Native (iOS + Android)
- **Connection:** BLE for discovery → WebSocket for commands
- **Sync:** Real-time bidirectional (phone ↔ Pi screen ↔ all devices)
- **Latency Target:** < 200ms from phone tap to Pi screen update
- **Features:** Full kiosk parity (6 pages, scenes, relays, emergency stop)

**BLE Protocol Design:**
- BLE advertises WebSocket URL via GATT characteristic
- Phone reads URL and connects to WebSocket directly
- WebSocket handles all commands (lower latency than BLE)
- BLE only used for discovery and connection setup

**Documentation Created:**
- `horsebox-mobile/README.md` - Mobile app overview and getting started
- `horsebox-mobile/docs/ARCHITECTURE.md` - Detailed technical architecture (50+ sections)
- `horsebox-mobile/docs/BLE_PROTOCOL.md` - Complete BLE protocol spec with code examples
- Root `README.md` - Monorepo structure and overview

**User Request:**
"can you create a new directory for an app that will 'pull' the kiosk screen via ble from pi to a phone that paired via bluetooth to pi. of course I want changes done on one screen to reflect to all other"
→ Led to complete mobile app architecture and monorepo structure

**Status:**
- Kiosk: Production-ready (v5.0)
- Mobile: Architecture complete, implementation pending
- BLE Hub: Python implementation spec complete
- Documentation: Complete and comprehensive

**Next Steps:**
1. Implement BLE Hub on Pi (`src/ble_hub.py`)
2. Set up React Native project
3. Implement BLE scanning and connection
4. Build WebSocket integration
5. Replicate kiosk UI on mobile
6. Test real-time sync with multiple devices

---

**Last Updated:** 2026-01-27 (Phase 6 Complete)
**Version:** 6.0 (Monorepo + Mobile Architecture)
**Status:** Kiosk Production-Ready, Mobile Architecture Complete
**Repository:** Now monorepo with kiosk and mobile projects
