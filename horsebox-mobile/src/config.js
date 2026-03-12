/**
 * Horsebox Mobile - Configuration
 *
 * MOCK_MODE: Set to true for development without Pi
 * When true, skips BLE and connects directly to Flask server
 */

export const config = {
  // Development mode - no BLE needed, connect directly to Flask
  MOCK_MODE: true,

  // Flask server URL (change to your laptop's IP when testing)
  // Find your IP: ifconfig (Mac/Linux) or ipconfig (Windows)
  // Example: 'ws://192.168.1.100:5000/socket.io/'
  MOCK_WEBSOCKET_URL: 'ws://192.168.1.100:5000/socket.io/',

  // BLE Service UUIDs (for real BLE mode)
  BLE: {
    SERVICE_UUID: '0000180A-0000-1000-8000-00805F9B34FB',
    WEBSOCKET_URL_UUID: '0000180B-0000-1000-8000-00805F9B34FB',
    DEVICE_NAME_UUID: '0000180E-0000-1000-8000-00805F9B34FB',
    CONNECTION_TOKEN_UUID: '0000180C-0000-1000-8000-00805F9B34FB'
  },

  // Connection settings
  CONNECTION: {
    SCAN_TIMEOUT: 10000,        // 10 seconds
    RECONNECT_DELAY: 3000,      // 3 seconds
    WEBSOCKET_TIMEOUT: 5000,    // 5 seconds
    OPTIMISTIC_UPDATE_TIMEOUT: 3000  // 3 seconds
  },

  // UI settings
  UI: {
    HAPTIC_FEEDBACK: true,
    AUTO_REFRESH: true,
    REFRESH_INTERVAL: 30000  // 30 seconds
  }
};

export default config;
