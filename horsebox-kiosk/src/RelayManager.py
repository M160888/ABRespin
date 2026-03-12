import json
import time
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException
import threading

class RelayManager:
    def __init__(self, config_path='relay_config.json'):
        self.config_path = config_path
        self.state_file = config_path.replace('.json', '_state.json')
        self.lock = threading.Lock()
        with self.lock:
            self.config = self.load_config()

        self.relays = self.config['relays']
        self.modbus_ip = self.config['modbus_ip']
        self.modbus_port = self.config.get('modbus_port', 502)
        self.client = None
        self.terminal_log_mode = False
        self.relay_states = {}  # Track current states
        self.connect()
        self.restore_states()  # Restore previous states on startup

    def load_config(self):
        # Assumes lock is acquired before calling
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def save_config(self):
        # Assumes lock is acquired before calling
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def save_states(self):
        """Save current relay states to disk for persistence across reboots"""
        try:
            with self.lock:
                state_data = {
                    'timestamp': time.time(),
                    'states': self.relay_states
                }
                with open(self.state_file, 'w') as f:
                    json.dump(state_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save relay states: {e}")

    def restore_states(self):
        """Restore relay states from disk on startup.

        Vehicle-safe policy: only restores relays tagged 'critical' (e.g. fridge,
        water pump) and only if the system was off for less than 1 hour.
        Lights, fans and other non-critical relays always start OFF.
        """
        try:
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)

            saved_states = state_data.get('states', {})
            saved_time = state_data.get('timestamp', 0)

            # Only restore if shutdown was recent - longer absence is likely deliberate
            age_hours = (time.time() - saved_time) / 3600
            if age_hours > 1:
                print(f"Saved state is {age_hours:.1f} hours old - not restoring")
                return

            print(f"Restoring critical relay states from {age_hours:.1f} hours ago...")

            # Build set of relay IDs tagged 'critical'
            critical_ids = {
                r['id'] for r in self.relays
                if 'critical' in r.get('tags', [])
            }

            popup_config = self.config.get('popup_control', {})
            popup_ids = {popup_config.get('up_relay_id'), popup_config.get('down_relay_id')}

            restored = 0
            for relay_id_str, state in saved_states.items():
                relay_id = int(relay_id_str)

                # Never restore popup relays
                if relay_id in popup_ids:
                    continue

                # Only restore critical relays - everything else stays OFF
                if relay_id not in critical_ids:
                    continue

                self.set_relay(relay_id, state)
                time.sleep(0.05)
                restored += 1

            print(f"Restored {restored} critical relay states ({len(saved_states) - restored} non-critical left OFF)")

        except FileNotFoundError:
            print("No saved state file found - starting fresh")
        except Exception as e:
            print(f"Warning: Could not restore relay states: {e}")

    def connect(self):
        if self.modbus_ip:
            try:
                self.client = ModbusTcpClient(self.modbus_ip, port=self.modbus_port, timeout=3)
                if not self.client.connect():
                    raise ConnectionException("Client failed to connect")
                print(f"Connected to Modbus server at {self.modbus_ip}:{self.modbus_port}")
                self.terminal_log_mode = False
            except Exception:
                print(f"Failed to connect to Modbus server. Switching to Terminal Log mode.")
                self.terminal_log_mode = True
                self.client = None
        else:
            print("No Modbus IP configured. Switching to Terminal Log mode.")
            self.terminal_log_mode = True

    def get_relay(self, relay_id):
        for relay in self.relays:
            if relay['id'] == relay_id:
                return relay
        return None

    def set_relay(self, relay_id, state):
        relay = self.get_relay(relay_id)
        if not relay:
            print(f"Relay {relay_id} not found.")
            return

        address = relay['address']
        print(f"Setting relay {relay_id} ({relay['name']}) to {'ON' if state else 'OFF'} at address {address}")

        # Track state change
        self.relay_states[relay_id] = state

        if self.terminal_log_mode:
            print(f"[LOG MODE] Relay {relay_id} ({relay['name']}) set to {'ON' if state else 'OFF'}")
            self.save_states()  # Save even in log mode
            return

        if not self.client or not self.client.is_socket_open():
            print("Modbus client not connected. Reconnecting...")
            self.connect()
            if self.terminal_log_mode:
                self.save_states()
                return

        try:
            self.client.write_coil(address, state, unit=1)
            self.save_states()  # Save state after successful write
        except Exception as e:
            print(f"Error setting relay {relay_id}: {e}")
            self.terminal_log_mode = True # fallback to log mode on error
            print("Switched to Terminal Log mode due to error.")
            self.save_states()

    def update_relay_name(self, relay_id, new_name):
        with self.lock:
            config_changed = False
            for relay in self.config['relays']:
                if relay['id'] == relay_id:
                    if relay['name'] != new_name:
                        relay['name'] = new_name
                        config_changed = True
                        print(f"Updated relay {relay_id} name to '{new_name}' in config.")
                    break
            
            if config_changed:
                self.save_config()
                # Update in-memory list as well
                self.relays = self.config['relays']

    def move_popup(self, direction):
        popup_config = self.config.get('popup_control', {})
        up_relay_id = popup_config.get('up_relay_id')
        down_relay_id = popup_config.get('down_relay_id')

        if up_relay_id is None or down_relay_id is None:
            print("Popup relays not configured.")
            return

        if direction == 'up':
            print("Moving popup up...")
            self.set_relay(down_relay_id, 0)
            time.sleep(0.05)
            self.set_relay(up_relay_id, 1)
        elif direction == 'down':
            print("Moving popup down...")
            self.set_relay(up_relay_id, 0)
            time.sleep(0.05)
            self.set_relay(down_relay_id, 1)
        elif direction == 'release':
            print("Releasing popup...")
            self.set_relay(up_relay_id, 0)
            self.set_relay(down_relay_id, 0)
        else:
            print(f"Invalid direction: {direction}")

    def emergency_stop_all(self):
        """Emergency stop: Turn OFF all relays immediately"""
        print("=" * 60)
        print("⚠️  EMERGENCY STOP - Turning OFF all relays")
        print("=" * 60)

        for relay in self.relays:
            self.set_relay(relay['id'], 0)
            time.sleep(0.01)  # Small delay to prevent bus flooding

        print("All relays turned OFF")
        print("=" * 60)

    def assign_relay_zone(self, relay_id, new_zone):
        """Assign a relay to a different zone"""
        with self.lock:
            # Check if zone exists
            if new_zone not in self.config.get('zones', {}):
                print(f"Error: Zone '{new_zone}' does not exist")
                return False

            # Find and update relay
            for relay in self.config['relays']:
                if relay['id'] == relay_id:
                    old_zone = relay.get('zone', 'unassigned')
                    relay['zone'] = new_zone
                    print(f"Moved relay {relay_id} ({relay['name']}) from '{old_zone}' to '{new_zone}'")

                    # Save updated config
                    self.save_config()
                    # Update in-memory list
                    self.relays = self.config['relays']
                    return True

    def manage_relay_tag(self, relay_id, tag, action):
        """Add or remove a tag from a relay"""
        with self.lock:
            # Find relay
            for relay in self.config['relays']:
                if relay['id'] == relay_id:
                    # Initialize tags array if it doesn't exist
                    if 'tags' not in relay:
                        relay['tags'] = []

                    if action == 'add':
                        # Add tag if not already present
                        if tag not in relay['tags']:
                            relay['tags'].append(tag)
                            print(f"Added tag '{tag}' to relay {relay_id} ({relay['name']})")
                        else:
                            print(f"Tag '{tag}' already exists on relay {relay_id}")
                    elif action == 'remove':
                        # Remove tag if present
                        if tag in relay['tags']:
                            relay['tags'].remove(tag)
                            print(f"Removed tag '{tag}' from relay {relay_id} ({relay['name']})")
                        else:
                            print(f"Tag '{tag}' not found on relay {relay_id}")

                    # Save updated config
                    self.save_config()
                    # Update in-memory list
                    self.relays = self.config['relays']
                    return True

            print(f"Error: Relay {relay_id} not found")
            return False

    def configure_zone_sensor(self, zone_id, sensor_type, sensor_config):
        """Configure a sensor for a specific zone"""
        with self.lock:
            # Check if zone exists
            if zone_id not in self.config.get('zones', {}):
                print(f"Error: Zone '{zone_id}' does not exist")
                return False

            # Check if sensor type is valid
            if sensor_type not in ['temperature', 'humidity']:
                print(f"Error: Invalid sensor type '{sensor_type}'")
                return False

            # Update sensor configuration
            zone = self.config['zones'][zone_id]
            if 'sensors' not in zone:
                zone['sensors'] = {}

            if sensor_type not in zone['sensors']:
                zone['sensors'][sensor_type] = {}

            # Update sensor config
            zone['sensors'][sensor_type].update(sensor_config)

            print(f"Updated {sensor_type} sensor for zone '{zone_id}': {sensor_config}")

            # Save updated config
            self.save_config()
            return True

    def __del__(self):
        if self.client:
            self.client.close()
