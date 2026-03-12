import threading
import time
import json
from datetime import datetime, timedelta


class AutomationEngine:
    """
    Automation Engine for Horsebox Control System

    Features:
    - Scene activation (preset relay configurations)
    - Time-based automations (trigger at specific times)
    - Sensor-based automations (trigger on temperature/humidity)
    - Cooldown periods to prevent rapid re-triggering
    """

    def __init__(self, relay_manager, config_path='relay_config.json'):
        self.relay_manager = relay_manager
        self.config_path = config_path
        self.config = self.load_config()
        self.scenes = self.config.get('scenes', [])
        self.automations = self.config.get('automations', [])

        # Track last trigger time for cooldowns
        self.last_trigger = {}

        # Sensor data cache (populated by Flask app)
        self.sensor_data = {
            'living': {'temperature': None, 'humidity': None},
            'bedroom': {'temperature': None, 'humidity': None},
            'horse_outside': {'temperature': None, 'humidity': None}
        }

        # Start automation evaluation thread
        self.running = True
        self.automation_thread = threading.Thread(target=self.automation_loop, daemon=True)
        self.automation_thread.start()

        print("🤖 Automation Engine started")
        print(f"   Scenes loaded: {len(self.scenes)}")
        print(f"   Automations loaded: {len(self.automations)}")
        print(f"   Enabled automations: {len([a for a in self.automations if a.get('enabled', False)])}")

    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_sensor_data(self, zone, sensor_type, value):
        """Update sensor data cache (called by Flask app)"""
        if zone in self.sensor_data and sensor_type in ['temperature', 'humidity']:
            self.sensor_data[zone][sensor_type] = value

    def get_relays_by_tag(self, tag):
        """Get all relay IDs that have a specific tag"""
        matching_relays = []
        for relay in self.relay_manager.relays:
            tags = relay.get('tags', [])
            if tag in tags:
                matching_relays.append(relay['id'])
        return matching_relays

    def activate_scene(self, scene_id):
        """Activate a scene by ID - returns list of changed relays"""
        scene = next((s for s in self.scenes if s['id'] == scene_id), None)
        if not scene:
            print(f"❌ Scene not found: {scene_id}")
            return None

        print(f"🎬 Activating scene: {scene['name']}")

        # Get explicit relay states
        relay_states = scene.get('relay_states', {})

        # Get tag-based states and resolve to relay IDs
        tagged_states = scene.get('tagged_states', {})

        # Build a merged dictionary of relay ID -> state
        merged_states = {}

        # First, add explicit relay states
        for relay_id_str, state in relay_states.items():
            merged_states[int(relay_id_str)] = state

        # Then, resolve tags to relay IDs and add them
        for tag, state in tagged_states.items():
            matching_relay_ids = self.get_relays_by_tag(tag)
            print(f"   🏷️  Tag '{tag}' matched {len(matching_relay_ids)} relay(s): {matching_relay_ids}")
            for relay_id in matching_relay_ids:
                # Tagged states are overridden by explicit states
                if relay_id not in merged_states:
                    merged_states[relay_id] = state

        changed_relays = []

        # Special case: "All Off" scene with no states
        if not merged_states and scene_id == 'all_off':
            # Turn off all relays except popup (1 & 2)
            for relay in self.relay_manager.relays:
                if relay['id'] not in [1, 2]:
                    self.relay_manager.set_relay(relay['id'], 0)
                    changed_relays.append({'id': relay['id'], 'state': 0})
            print(f"   ✅ All relays turned off (except popup)")
            return changed_relays

        # Apply all merged relay states
        for relay_id, state in merged_states.items():
            # Skip popup relays (safety)
            if relay_id in [1, 2]:
                print(f"   ⚠️  Skipping popup relay {relay_id} (safety)")
                continue

            self.relay_manager.set_relay(relay_id, state)
            changed_relays.append({'id': relay_id, 'state': state})
            print(f"   Relay {relay_id} → {'ON' if state else 'OFF'}")

        print(f"   ✅ Scene '{scene['name']}' activated")
        return changed_relays

    def evaluate_condition(self, condition):
        """Evaluate a single condition"""
        cond_type = condition.get('type')

        if cond_type == 'time':
            # Time-based condition: Check if current time matches
            target_time = condition.get('time', '00:00')
            current_time = datetime.now().strftime('%H:%M')
            return current_time == target_time

        elif cond_type == 'sensor':
            # Sensor-based condition: Check sensor value against threshold
            zone = condition.get('zone')
            sensor = condition.get('sensor')  # 'temperature' or 'humidity'
            operator = condition.get('operator')  # '>', '<', '>=', '<=', '=='
            value = condition.get('value')

            # Get sensor data
            if zone not in self.sensor_data:
                return False

            sensor_value = self.sensor_data[zone].get(sensor)
            if sensor_value is None:
                return False

            # Evaluate operator
            if operator == '>':
                return sensor_value > value
            elif operator == '<':
                return sensor_value < value
            elif operator == '>=':
                return sensor_value >= value
            elif operator == '<=':
                return sensor_value <= value
            elif operator == '==':
                return sensor_value == value
            else:
                return False

        elif cond_type == 'relay_state':
            # Relay state condition: Check if relay is in specific state
            relay_id = condition.get('relay_id')
            state = condition.get('state')
            # TODO: Track relay states in relay_manager
            return False

        return False

    def evaluate_automation(self, automation):
        """Evaluate all conditions for an automation (AND logic)"""
        conditions = automation.get('conditions', [])
        if not conditions:
            return False

        # All conditions must be true (AND logic)
        return all(self.evaluate_condition(cond) for cond in conditions)

    def execute_action(self, action):
        """Execute a single action"""
        action_type = action.get('type')

        if action_type == 'set_relay':
            # Set a specific relay state
            relay_id = action.get('relay_id')
            state = action.get('state')
            # Skip popup relays (safety)
            if relay_id in [1, 2]:
                print(f"   ⚠️  Skipping popup relay {relay_id} (safety)")
                return
            self.relay_manager.set_relay(relay_id, state)
            print(f"   Action: Relay {relay_id} → {'ON' if state else 'OFF'}")

        elif action_type == 'set_tag':
            # Set all relays with a specific tag to a state
            tag = action.get('tag')
            state = action.get('state')
            matching_relay_ids = self.get_relays_by_tag(tag)
            print(f"   Action: Set tag '{tag}' → {'ON' if state else 'OFF'} ({len(matching_relay_ids)} relays)")
            for relay_id in matching_relay_ids:
                # Skip popup relays (safety)
                if relay_id in [1, 2]:
                    print(f"     ⚠️  Skipping popup relay {relay_id} (safety)")
                    continue
                self.relay_manager.set_relay(relay_id, state)
                print(f"     Relay {relay_id} → {'ON' if state else 'OFF'}")

        elif action_type == 'activate_scene':
            # Activate a scene
            scene_id = action.get('scene_id')
            print(f"   Action: Activate scene '{scene_id}'")
            self.activate_scene(scene_id)

    def trigger_automation(self, automation):
        """Trigger an automation (check cooldown and execute actions)"""
        auto_id = automation['id']
        cooldown = automation.get('cooldown', 60)  # Default 60 seconds

        # Check cooldown
        now = time.time()
        last_time = self.last_trigger.get(auto_id, 0)
        if now - last_time < cooldown:
            # Still in cooldown period
            return

        # Execute actions
        print(f"🔔 Triggering automation: {automation['name']}")
        actions = automation.get('actions', [])
        for action in actions:
            self.execute_action(action)

        # Update last trigger time
        self.last_trigger[auto_id] = now
        print(f"   ✅ Automation complete (cooldown: {cooldown}s)")

    def automation_loop(self):
        """Main automation evaluation loop"""
        print("🔄 Automation loop started")

        while self.running:
            try:
                # Evaluate all enabled automations
                for automation in self.automations:
                    if not automation.get('enabled', False):
                        continue

                    # Evaluate conditions
                    if self.evaluate_automation(automation):
                        self.trigger_automation(automation)

                # Sleep for 10 seconds before next evaluation
                time.sleep(10)

            except Exception as e:
                print(f"❌ Error in automation loop: {e}")
                time.sleep(10)

    def stop(self):
        """Stop the automation engine"""
        self.running = False
        print("🛑 Automation Engine stopped")

    # API Methods for managing scenes and automations

    def get_scenes(self):
        """Get all scenes"""
        return self.scenes

    def get_scene(self, scene_id):
        """Get a specific scene"""
        return next((s for s in self.scenes if s['id'] == scene_id), None)

    def create_scene(self, scene_data):
        """Create a new scene"""
        self.scenes.append(scene_data)
        self.config['scenes'] = self.scenes
        self.save_config()
        return True

    def update_scene(self, scene_id, scene_data):
        """Update an existing scene"""
        for i, scene in enumerate(self.scenes):
            if scene['id'] == scene_id:
                self.scenes[i] = scene_data
                self.config['scenes'] = self.scenes
                self.save_config()
                return True
        return False

    def delete_scene(self, scene_id):
        """Delete a scene"""
        self.scenes = [s for s in self.scenes if s['id'] != scene_id]
        self.config['scenes'] = self.scenes
        self.save_config()
        return True

    def get_automations(self):
        """Get all automations"""
        return self.automations

    def get_automation(self, auto_id):
        """Get a specific automation"""
        return next((a for a in self.automations if a['id'] == auto_id), None)

    def create_automation(self, auto_data):
        """Create a new automation"""
        self.automations.append(auto_data)
        self.config['automations'] = self.automations
        self.save_config()
        return True

    def update_automation(self, auto_id, auto_data):
        """Update an existing automation"""
        for i, auto in enumerate(self.automations):
            if auto['id'] == auto_id:
                self.automations[i] = auto_data
                self.config['automations'] = self.automations
                self.save_config()
                return True
        return False

    def delete_automation(self, auto_id):
        """Delete an automation"""
        self.automations = [a for a in self.automations if a['id'] != auto_id]
        self.config['automations'] = self.automations
        self.save_config()
        return True

    def toggle_automation(self, auto_id, enabled):
        """Enable or disable an automation"""
        for auto in self.automations:
            if auto['id'] == auto_id:
                auto['enabled'] = enabled
                self.config['automations'] = self.automations
                self.save_config()
                print(f"{'✅ Enabled' if enabled else '⏸️  Disabled'} automation: {auto['name']}")
                return True
        return False
