#!/usr/bin/env python3
"""
System Check Script for Horsebox Control System
Verifies all components are working correctly before deployment
"""

import sys
import json
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

def print_status(check_name, passed, message=""):
    status = "✓ PASS" if passed else "✗ FAIL"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} - {check_name}")
    if message:
        print(f"      {message}")
    return passed

def check_config_file():
    """Check if relay_config.json exists and is valid"""
    try:
        with open('relay_config.json', 'r') as f:
            config = json.load(f)

        required_keys = ['modbus_ip', 'modbus_port', 'popup_control', 'relays']
        missing = [key for key in required_keys if key not in config]

        if missing:
            return print_status("Config File", False, f"Missing keys: {missing}")

        if len(config['relays']) != 30:
            return print_status("Config File", False, f"Expected 30 relays, found {len(config['relays'])}")

        return print_status("Config File", True, f"Found {len(config['relays'])} relays")
    except FileNotFoundError:
        return print_status("Config File", False, "relay_config.json not found")
    except json.JSONDecodeError:
        return print_status("Config File", False, "Invalid JSON in relay_config.json")

def check_modbus_connection(config):
    """Test connection to Modbus relay board"""
    try:
        ip = config['modbus_ip']
        port = config.get('modbus_port', 502)

        client = ModbusTcpClient(ip, port=port, timeout=3)

        if not client.connect():
            return print_status("Modbus Connection", False, f"Could not connect to {ip}:{port}")

        # Try to read a coil to verify communication
        try:
            result = client.read_coils(0, 1, unit=1)
            if result.isError():
                client.close()
                return print_status("Modbus Connection", False, "Connected but cannot read coils")
        except Exception as e:
            client.close()
            return print_status("Modbus Connection", False, f"Read error: {e}")

        client.close()
        return print_status("Modbus Connection", True, f"Connected to {ip}:{port}")

    except Exception as e:
        return print_status("Modbus Connection", False, f"Error: {e}")

def check_popup_safety(config):
    """Verify popup control safety configuration"""
    popup = config.get('popup_control', {})

    if not popup:
        return print_status("Popup Safety", False, "Popup control not configured")

    up_id = popup.get('up_relay_id')
    down_id = popup.get('down_relay_id')

    if up_id is None or down_id is None:
        return print_status("Popup Safety", False, "Popup relay IDs not set")

    if up_id == down_id:
        return print_status("Popup Safety", False, "Up and Down relays cannot be the same!")

    # Verify these relays exist in config
    relay_ids = [r['id'] for r in config['relays']]
    if up_id not in relay_ids:
        return print_status("Popup Safety", False, f"Up relay {up_id} not found in relay list")
    if down_id not in relay_ids:
        return print_status("Popup Safety", False, f"Down relay {down_id} not found in relay list")

    return print_status("Popup Safety", True, f"Up={up_id}, Down={down_id}")

def check_relay_addresses(config):
    """Verify relay addresses are sequential and valid"""
    relays = config['relays']

    # Check for duplicate addresses
    addresses = [r['address'] for r in relays]
    if len(addresses) != len(set(addresses)):
        return print_status("Relay Addresses", False, "Duplicate addresses found")

    # Check for duplicate IDs
    ids = [r['id'] for r in relays]
    if len(ids) != len(set(ids)):
        return print_status("Relay Addresses", False, "Duplicate relay IDs found")

    # Check address range (should be 0-29 for 30 relays)
    if min(addresses) != 0 or max(addresses) != 29:
        return print_status("Relay Addresses", False, f"Address range invalid: {min(addresses)}-{max(addresses)}")

    return print_status("Relay Addresses", True, "All addresses valid (0-29)")

def check_python_dependencies():
    """Check if required Python packages are installed"""
    try:
        import flask
        import flask_socketio
        import pymodbus

        versions = [
            f"Flask {flask.__version__}",
            f"Flask-SocketIO {flask_socketio.__version__}",
            f"pymodbus {pymodbus.__version__}"
        ]

        return print_status("Python Dependencies", True, ", ".join(versions))
    except ImportError as e:
        return print_status("Python Dependencies", False, f"Missing: {e.name}")

def main():
    print("\n" + "="*60)
    print("  HORSEBOX CONTROL SYSTEM - PRE-DEPLOYMENT CHECK")
    print("="*60 + "\n")

    all_passed = True

    # Check 1: Python dependencies
    all_passed &= check_python_dependencies()

    # Check 2: Config file
    config_ok = check_config_file()
    all_passed &= config_ok

    if not config_ok:
        print("\n⚠ Cannot continue checks without valid config file")
        sys.exit(1)

    # Load config for remaining checks
    with open('relay_config.json', 'r') as f:
        config = json.load(f)

    # Check 3: Relay addresses
    all_passed &= check_relay_addresses(config)

    # Check 4: Popup safety
    all_passed &= check_popup_safety(config)

    # Check 5: Modbus connection
    all_passed &= check_modbus_connection(config)

    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL CHECKS PASSED - System ready for deployment")
        print("="*60 + "\n")
        sys.exit(0)
    else:
        print("✗ SOME CHECKS FAILED - Please fix issues before deployment")
        print("="*60 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
