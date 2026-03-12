# Horsebox Control System - Monorepo

Complete control system for horsebox (horse trailer) with 30-relay Modbus control, real-time synchronization, and multi-device support.

## 🏗️ Project Structure

```
AB/
├── horsebox-kiosk/          # Raspberry Pi 5 kiosk application
│   ├── src/                 # Flask backend + HTML/CSS/JS frontend
│   ├── relay_config.json    # System configuration
│   ├── requirements.txt     # Python dependencies
│   └── DEPLOYMENT.md        # Pi deployment guide
│
├── horsebox-mobile/         # Mobile app (BLE remote control)
│   ├── docs/                # Mobile app documentation
│   ├── architecture/        # Architecture diagrams & specs
│   └── README.md            # Mobile app guide
│
└── shared-docs/             # Shared documentation
    ├── CHECKPOINT.md        # Project status & phase history
    ├── CLAUDE_CONTEXT.md    # Context for future Claude sessions
    └── API_DOCUMENTATION.md # Complete API reference
```

## 📱 Components

### Horsebox Kiosk (Raspberry Pi 5)
- **Purpose:** Primary control interface with touchscreen
- **Hardware:** Raspberry Pi 5 + Waveshare 30-Channel Modbus Relay Board
- **Features:**
  - 6-page touch interface (Overview, Living, Bedroom, Horse, Scenes, Settings)
  - Zone-based relay control (30 relays)
  - H-bridge popup motor control with safety
  - Visual scene editor (no password required)
  - WebSocket real-time updates
  - Emergency stop button
  - State persistence (survives reboots)
  - Watchdog support (auto-recovery)

### Horsebox Mobile (Smartphone)
- **Purpose:** Remote control via Bluetooth Low Energy (BLE)
- **Platform:** Cross-platform (React Native / Flutter / PWA - TBD)
- **Features:**
  - BLE connection to Raspberry Pi
  - Mirror kiosk interface on phone
  - Real-time bidirectional sync (phone ↔ Pi screen ↔ all connected devices)
  - Low latency relay control
  - Scene activation from phone
  - Connection status indicator
  - Works alongside Pi screen simultaneously

## 🔄 Real-Time Synchronization

All devices sync in real-time using WebSocket (SocketIO):

```
┌─────────────┐      WebSocket      ┌─────────────┐
│  Pi Screen  │ ←──────────────────→ │ Flask Server│
└─────────────┘                      └─────────────┘
                                            ↕
                                       WebSocket
                                            ↕
                                     ┌─────────────┐
                                     │   BLE Hub   │
                                     └─────────────┘
                                            ↕
                                         BLE
                                            ↕
                                     ┌─────────────┐
                                     │   Phone     │
                                     └─────────────┘
```

**How it works:**
1. User toggles relay on phone
2. Phone sends command via BLE to Pi
3. Pi forwards to Flask backend via WebSocket
4. Flask updates relay state via Modbus
5. Flask broadcasts `relay_state_changed` event to all connected clients
6. Pi screen updates instantly
7. All other connected phones update instantly

**Latency Target:** < 200ms from phone tap to Pi screen update

## 🚀 Quick Start

### Kiosk Setup
```bash
cd horsebox-kiosk
pip install -r requirements.txt
python src/api/app.py
```

### Mobile Development
```bash
cd horsebox-mobile
# See horsebox-mobile/README.md for setup
```

## 📚 Documentation

- **[CHECKPOINT.md](shared-docs/CHECKPOINT.md)** - Current project status, phase history
- **[API_DOCUMENTATION.md](shared-docs/API_DOCUMENTATION.md)** - Complete REST & WebSocket API reference
- **[CLAUDE_CONTEXT.md](shared-docs/CLAUDE_CONTEXT.md)** - Context for future development sessions
- **[Kiosk Deployment](horsebox-kiosk/DEPLOYMENT.md)** - Raspberry Pi setup guide
- **[Mobile Architecture](horsebox-mobile/docs/ARCHITECTURE.md)** - Mobile app design & BLE protocol

## 🏷️ Current Version

- **Kiosk:** v5.0 (Visual Scene Editor)
- **Mobile:** v0.1 (In Development)
- **Last Updated:** 2026-01-27

## 🔑 Key Features

### Implemented ✅
- 30-relay Modbus TCP control
- Zone-based organization (Living, Bedroom, Horse & Outside)
- Visual scene editor (create/edit/delete scenes)
- Tag-based relay grouping (future-proof automation)
- H-bridge motor safety (popup control)
- Emergency stop (kills all relays)
- State persistence (survives reboots/crashes)
- Real-time WebSocket updates
- Password-protected admin settings
- Automation engine (time & sensor triggers)
- Hardware & systemd watchdog

### In Development 🚧
- Mobile app (BLE remote control)
- Real-time sync across all devices

### Planned 📋
- Real sensor integration (temperature, humidity)
- Activity log (relay changes, scene activations)
- Usage statistics (runtime tracking)
- Weather API integration
- Automation editor UI

## ⚠️ Safety Features

- **H-Bridge Protection:** Popup motor relays (1 & 2) never both ON simultaneously
- **Emergency Stop:** Floating red button on all screens
- **State Persistence Safety:** Popup relays always start OFF
- **UI-Level Blocking:** Popup relays cannot be manually toggled
- **Watchdog Recovery:** Auto-reboot on system hang

## 👥 Target Users

1. **Manufacturer/Assembler:** Installing system in multiple horseboxes
2. **End Customer:** Truck builder/installer
3. **Final User:** Horse owner (daily use)

## 🔧 Hardware Requirements

- **Kiosk:**
  - Raspberry Pi 5 (4GB+ RAM)
  - Waveshare 30-Channel Modbus TCP Relay Board
  - Touchscreen display (7-10 inch recommended)
  - Ethernet cable (Pi to relay board)

- **Mobile:**
  - Smartphone with BLE 4.0+ support
  - iOS 13+ or Android 8+

## 📝 License

Proprietary - Internal use only

## 🤝 Contributing

This is a monorepo. When making changes:
1. Work in appropriate subdirectory (`horsebox-kiosk` or `horsebox-mobile`)
2. Update shared documentation in `shared-docs/`
3. Test cross-component integration (kiosk ↔ mobile sync)
4. Update version numbers in both projects if needed

---

**Repository Structure:** Monorepo (Phase 6)
**Status:** Kiosk Production-Ready, Mobile In Development
