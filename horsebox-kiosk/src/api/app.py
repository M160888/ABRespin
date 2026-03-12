from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import sys
import os
import threading
import time
import random
import json
import subprocess
import requests

# GPS support (optional — requires gpsd running and gpsd-py3 installed)
try:
    import gpsd
    GPSD_AVAILABLE = True
except ImportError:
    GPSD_AVAILABLE = False
    print("⚠️  gpsd-py3 not installed - GPS disabled")

# Systemd watchdog support (optional - won't crash if not available)
try:
    from systemd import daemon as systemd_daemon
    SYSTEMD_AVAILABLE = True
except ImportError:
    SYSTEMD_AVAILABLE = False
    print("⚠️  systemd-python not installed - watchdog notifications disabled")

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from RelayManager import RelayManager
from AutomationEngine import AutomationEngine

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# Add CORS allowed origins to fix the connection issue
socketio = SocketIO(app, cors_allowed_origins="*")

config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'relay_config.json')
user_config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'user_config.json')
relay_manager = RelayManager(config_path=config_path)

# Initialize Automation Engine
automation_engine = AutomationEngine(relay_manager, config_path=config_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/relays')
def get_relays():
    return jsonify(relay_manager.config)

@app.route('/api/zones')
def get_zones():
    """Get all zones with their assigned relays"""
    zones = relay_manager.config.get('zones', {})
    relays = relay_manager.config.get('relays', [])

    # Group relays by zone
    result = {}
    for zone_id, zone_info in zones.items():
        zone_relays = [r for r in relays if r.get('zone') == zone_id]
        result[zone_id] = {
            **zone_info,
            'relays': zone_relays,
            'relay_count': len(zone_relays)
        }

    return jsonify(result)

@app.route('/api/zone/<zone_id>')
def get_zone(zone_id):
    """Get specific zone details with relays"""
    zones = relay_manager.config.get('zones', {})
    if zone_id not in zones:
        return jsonify({'error': 'Zone not found'}), 404

    relays = relay_manager.config.get('relays', [])
    zone_relays = [r for r in relays if r.get('zone') == zone_id]

    result = {
        **zones[zone_id],
        'relays': zone_relays,
        'relay_count': len(zone_relays)
    }

    return jsonify(result)

@socketio.on('relay_toggle')
def handle_relay_toggle(data):
    relay_id = data['id']

    # Prevent manual control of popup relays - they must use popup_move for safety
    popup_config = relay_manager.config.get('popup_control', {})
    if relay_id in [popup_config.get('up_relay_id'), popup_config.get('down_relay_id')]:
        print(f"ERROR: Relay {relay_id} is a popup control relay. Use popup control slider instead.")
        return

    relay_manager.set_relay(relay_id, data['state'])

@socketio.on('popup_move')
def handle_popup_move(data):
    relay_manager.move_popup(data['direction'])

@socketio.on('update_relay_name')
def handle_update_name(data):
    relay_id = data.get('id')
    new_name = data.get('name')
    if relay_id is not None and new_name:
        relay_manager.update_relay_name(relay_id, new_name)

@socketio.on('emergency_stop')
def handle_emergency_stop():
    """Emergency stop: Turn OFF all relays immediately"""
    print("⚠️ EMERGENCY STOP ACTIVATED - Turning off all relays")
    relay_manager.emergency_stop_all()

@app.route('/api/relay/<int:relay_id>/assign', methods=['POST'])
def assign_relay_to_zone(relay_id):
    """Assign a relay to a different zone"""
    data = request.get_json()
    new_zone = data.get('zone')

    if not new_zone:
        return jsonify({'error': 'Zone parameter required'}), 400

    result = relay_manager.assign_relay_zone(relay_id, new_zone)
    if result:
        return jsonify({'success': True, 'relay_id': relay_id, 'zone': new_zone})
    else:
        return jsonify({'error': 'Failed to assign relay'}), 400

@app.route('/api/zone/<zone_id>/sensor/configure', methods=['POST'])
def configure_zone_sensor(zone_id):
    """Configure sensors for a specific zone"""
    data = request.get_json()
    sensor_type = data.get('sensor_type')  # 'temperature' or 'humidity'
    config = data.get('config')  # sensor configuration

    if not sensor_type or not config:
        return jsonify({'error': 'sensor_type and config required'}), 400

    result = relay_manager.configure_zone_sensor(zone_id, sensor_type, config)
    if result:
        return jsonify({'success': True, 'zone': zone_id, 'sensor_type': sensor_type})
    else:
        return jsonify({'error': 'Failed to configure sensor'}), 400

@app.route('/api/relay/<int:relay_id>/tag', methods=['POST'])
def manage_relay_tag(relay_id):
    """Add or remove a tag from a relay"""
    data = request.get_json()
    tag = data.get('tag')
    action = data.get('action')  # 'add' or 'remove'

    if not tag or not action:
        return jsonify({'error': 'tag and action parameters required'}), 400

    if action not in ['add', 'remove']:
        return jsonify({'error': 'action must be "add" or "remove"'}), 400

    result = relay_manager.manage_relay_tag(relay_id, tag, action)
    if result:
        return jsonify({'success': True, 'relay_id': relay_id, 'tag': tag, 'action': action})
    else:
        return jsonify({'error': 'Failed to manage tag'}), 400

# ================== Scenes API ==================

@app.route('/api/scenes')
def get_scenes():
    """Get all scenes"""
    return jsonify(automation_engine.get_scenes())

@app.route('/api/scene/<scene_id>')
def get_scene(scene_id):
    """Get a specific scene"""
    scene = automation_engine.get_scene(scene_id)
    if scene:
        return jsonify(scene)
    return jsonify({'error': 'Scene not found'}), 404

@app.route('/api/scene/<scene_id>/activate', methods=['POST'])
def activate_scene(scene_id):
    """Activate a scene and broadcast relay state changes to UI"""
    changed_relays = automation_engine.activate_scene(scene_id)
    if changed_relays is not None:
        # Broadcast each relay state change to all connected clients
        for relay_change in changed_relays:
            socketio.emit('relay_state_changed', {
                'id': relay_change['id'],
                'state': relay_change['state']
            })
        return jsonify({
            'success': True,
            'scene_id': scene_id,
            'changed_relays': changed_relays
        })
    return jsonify({'error': 'Failed to activate scene'}), 400

@app.route('/api/scene', methods=['POST'])
def create_scene():
    """Create a new scene"""
    data = request.get_json()
    result = automation_engine.create_scene(data)
    if result:
        return jsonify({'success': True, 'scene': data})
    return jsonify({'error': 'Failed to create scene'}), 400

@app.route('/api/scene/<scene_id>', methods=['PUT'])
def update_scene(scene_id):
    """Update an existing scene"""
    data = request.get_json()
    result = automation_engine.update_scene(scene_id, data)
    if result:
        return jsonify({'success': True, 'scene_id': scene_id})
    return jsonify({'error': 'Scene not found'}), 404

@app.route('/api/scene/<scene_id>', methods=['DELETE'])
def delete_scene(scene_id):
    """Delete a scene"""
    result = automation_engine.delete_scene(scene_id)
    if result:
        return jsonify({'success': True, 'scene_id': scene_id})
    return jsonify({'error': 'Failed to delete scene'}), 400

# ================== Automations API ==================

@app.route('/api/automations')
def get_automations():
    """Get all automations"""
    return jsonify(automation_engine.get_automations())

@app.route('/api/automation/<auto_id>')
def get_automation(auto_id):
    """Get a specific automation"""
    automation = automation_engine.get_automation(auto_id)
    if automation:
        return jsonify(automation)
    return jsonify({'error': 'Automation not found'}), 404

@app.route('/api/automation/<auto_id>/toggle', methods=['POST'])
def toggle_automation(auto_id):
    """Enable or disable an automation"""
    data = request.get_json()
    enabled = data.get('enabled', False)
    result = automation_engine.toggle_automation(auto_id, enabled)
    if result:
        return jsonify({'success': True, 'auto_id': auto_id, 'enabled': enabled})
    return jsonify({'error': 'Automation not found'}), 404

@app.route('/api/automation', methods=['POST'])
def create_automation():
    """Create a new automation"""
    data = request.get_json()
    result = automation_engine.create_automation(data)
    if result:
        return jsonify({'success': True, 'automation': data})
    return jsonify({'error': 'Failed to create automation'}), 400

@app.route('/api/automation/<auto_id>', methods=['PUT'])
def update_automation(auto_id):
    """Update an existing automation"""
    data = request.get_json()
    result = automation_engine.update_automation(auto_id, data)
    if result:
        return jsonify({'success': True, 'auto_id': auto_id})
    return jsonify({'error': 'Automation not found'}), 404

@app.route('/api/automation/<auto_id>', methods=['DELETE'])
def delete_automation(auto_id):
    """Delete an automation"""
    result = automation_engine.delete_automation(auto_id)
    if result:
        return jsonify({'success': True, 'auto_id': auto_id})
    return jsonify({'error': 'Failed to delete automation'}), 400

# ================== User Config API ==================

@app.route('/api/user-config')
def get_user_config():
    try:
        with open(user_config_path, 'r') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({'name': '', 'phone': '', 'address': '', 'notes': ''})

@app.route('/api/user-config', methods=['PUT'])
def update_user_config():
    data = request.get_json()
    allowed = {'name', 'phone', 'address', 'notes'}
    sanitised = {k: str(v) for k, v in data.items() if k in allowed}
    with open(user_config_path, 'w') as f:
        json.dump(sanitised, f, indent=2)
    return jsonify({'success': True})

# ================== WiFi API ==================

@app.route('/api/wifi/status')
def wifi_status():
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'device'],
            capture_output=True, text=True, timeout=10
        )
        devices = []
        for line in result.stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 4 and parts[1] == 'wifi':
                devices.append({
                    'device': parts[0],
                    'state': parts[2],
                    'connection': parts[3]
                })
        return jsonify({'devices': devices})
    except FileNotFoundError:
        return jsonify({'error': 'nmcli not available'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/wifi/scan')
def wifi_scan():
    try:
        subprocess.run(['nmcli', 'device', 'wifi', 'rescan'], timeout=10, capture_output=True)
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'device', 'wifi', 'list'],
            capture_output=True, text=True, timeout=10
        )
        networks = []
        seen = set()
        for line in result.stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 4:
                ssid = parts[0].replace('\\:', ':').strip()
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    networks.append({
                        'ssid': ssid,
                        'signal': int(parts[1]) if parts[1].isdigit() else 0,
                        'security': parts[2],
                        'in_use': parts[3].strip() == '*'
                    })
        networks.sort(key=lambda x: x['signal'], reverse=True)
        return jsonify({'networks': networks})
    except FileNotFoundError:
        return jsonify({'error': 'nmcli not available'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/wifi/connect', methods=['POST'])
def wifi_connect():
    data = request.get_json()
    ssid = data.get('ssid', '').strip()
    password = data.get('password', '').strip()
    if not ssid:
        return jsonify({'success': False, 'error': 'SSID required'}), 400
    try:
        cmd = ['nmcli', 'device', 'wifi', 'connect', ssid]
        if password:
            cmd += ['password', password]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': result.stderr.strip() or result.stdout.strip()}), 400
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'nmcli not available'}), 501
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================== Background Tasks ==================

def send_sensor_data():
    """Mock sensor data - also feeds data to automation engine"""
    while True:
        # Generate mock sensor data for each zone
        living_temp = 20 + random.uniform(-1, 1)
        living_humidity = 50 + random.uniform(-5, 5)

        bedroom_temp = 21 + random.uniform(-1, 1)
        bedroom_humidity = 52 + random.uniform(-5, 5)

        horse_temp = 18 + random.uniform(-2, 2)
        horse_humidity = 60 + random.uniform(-10, 10)

        # Send to UI (for display)
        data = {
            "temperature": living_temp,
            "humidity": living_humidity,
            "pressure": 1013 + random.uniform(-2, 2)
        }
        socketio.emit('sensor_data', data)

        # Feed sensor data to automation engine (for automation evaluation)
        automation_engine.update_sensor_data('living', 'temperature', living_temp)
        automation_engine.update_sensor_data('living', 'humidity', living_humidity)
        automation_engine.update_sensor_data('bedroom', 'temperature', bedroom_temp)
        automation_engine.update_sensor_data('bedroom', 'humidity', bedroom_humidity)
        automation_engine.update_sensor_data('horse_outside', 'temperature', horse_temp)
        automation_engine.update_sensor_data('horse_outside', 'humidity', horse_humidity)

        time.sleep(5)


def fetch_weather():
    """Fetch real weather from wttr.in every 15 min. Emits nothing if offline."""
    while True:
        try:
            resp = requests.get('https://wttr.in/?format=%t+%C', timeout=5)
            if resp.status_code == 200:
                socketio.emit('weather_data', {'text': resp.text.strip(), 'available': True})
        except Exception:
            socketio.emit('weather_data', {'available': False})
        time.sleep(15 * 60)


def read_gps():
    """Read GPS position from gpsd and emit to UI every 3 seconds."""
    if not GPSD_AVAILABLE:
        return
    while True:
        try:
            gpsd.connect()
            while True:
                packet = gpsd.get_current()
                if packet.mode >= 2:  # 2D or 3D fix
                    # GPS time is UTC — include it so the UI can show accurate date/time
                    gps_time = packet.time if hasattr(packet, 'time') and packet.time else None
                    socketio.emit('gps_data', {
                        'fix': True,
                        'lat': round(packet.lat, 6),
                        'lon': round(packet.lon, 6),
                        'alt': round(packet.alt, 1) if packet.mode == 3 else None,
                        'sats': packet.sats_valid if hasattr(packet, 'sats_valid') else None,
                        'mode': packet.mode,
                        'time': gps_time  # ISO8601 UTC string e.g. "2026-03-12T08:30:00.000Z"
                    })
                else:
                    socketio.emit('gps_data', {'fix': False})
                time.sleep(3)
        except Exception as e:
            print(f"GPS error: {e}")
            socketio.emit('gps_data', {'fix': False})
            time.sleep(15)


def systemd_watchdog_notify():
    """Background thread that notifies systemd watchdog the app is healthy"""
    if not SYSTEMD_AVAILABLE:
        return

    # Notify systemd that we're ready
    systemd_daemon.notify('READY=1')
    print("✅ Notified systemd: Service ready")

    # Get watchdog interval from systemd (or default to 5 seconds)
    watchdog_usec = os.environ.get('WATCHDOG_USEC')
    if watchdog_usec:
        # Notify at half the watchdog interval for safety margin
        interval = int(watchdog_usec) / 2 / 1000000  # Convert microseconds to seconds
        print(f"⏱️  Systemd watchdog interval: {interval} seconds")
    else:
        interval = 5  # Default to 5 seconds
        print("⏱️  Systemd watchdog not configured, using default interval")

    while True:
        time.sleep(interval)
        # Notify systemd we're still alive
        systemd_daemon.notify('WATCHDOG=1')
        # Uncomment for debugging:
        # print(f"🐕 Watchdog notification sent at {time.strftime('%H:%M:%S')}")


if __name__ == '__main__':
    sensor_thread = threading.Thread(target=send_sensor_data)
    sensor_thread.daemon = True
    sensor_thread.start()

    weather_thread = threading.Thread(target=fetch_weather, daemon=True)
    weather_thread.start()

    if GPSD_AVAILABLE:
        gps_thread = threading.Thread(target=read_gps, daemon=True)
        gps_thread.start()

    # Start systemd watchdog notification thread
    if SYSTEMD_AVAILABLE:
        watchdog_thread = threading.Thread(target=systemd_watchdog_notify)
        watchdog_thread.daemon = True
        watchdog_thread.start()

    print("Starting Flask server...")
    print("View the UI by opening the forwarded port 5000 in your browser.")
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)