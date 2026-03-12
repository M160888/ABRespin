/**
 * WebSocket Service
 * Handles Socket.IO connection to Flask backend
 */

import io from 'socket.io-client';
import config from '../config';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.listeners = {
      connect: [],
      disconnect: [],
      relay_state_changed: [],
      sensor_data: [],
      weather_data: []
    };
  }

  /**
   * Connect to WebSocket server
   * @param {string} url - WebSocket URL (optional, uses config if not provided)
   */
  connect(url = null) {
    const websocketUrl = url || config.MOCK_WEBSOCKET_URL;

    console.log('[WebSocket] Connecting to:', websocketUrl);

    this.socket = io(websocketUrl, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: config.CONNECTION.RECONNECT_DELAY,
      reconnectionAttempts: 10
    });

    // Connection events
    this.socket.on('connect', () => {
      console.log('[WebSocket] Connected!');
      this.connected = true;
      this._emit('connect');
    });

    this.socket.on('disconnect', (reason) => {
      console.log('[WebSocket] Disconnected:', reason);
      this.connected = false;
      this._emit('disconnect', reason);
    });

    this.socket.on('connect_error', (error) => {
      console.error('[WebSocket] Connection error:', error.message);
    });

    // Relay state changes
    this.socket.on('relay_state_changed', (data) => {
      console.log('[WebSocket] Relay state changed:', data);
      this._emit('relay_state_changed', data);
    });

    // Sensor data
    this.socket.on('sensor_data', (data) => {
      console.log('[WebSocket] Sensor data:', data);
      this._emit('sensor_data', data);
    });

    // Weather data
    this.socket.on('weather_data', (data) => {
      console.log('[WebSocket] Weather data:', data);
      this._emit('weather_data', data);
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.socket) {
      console.log('[WebSocket] Disconnecting...');
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
    }
  }

  /**
   * Toggle a relay
   * @param {number} relayId - Relay ID (1-30)
   * @param {number} state - State (0 or 1)
   */
  toggleRelay(relayId, state) {
    if (!this.socket || !this.connected) {
      console.error('[WebSocket] Not connected, cannot toggle relay');
      return false;
    }

    console.log(`[WebSocket] Toggling relay ${relayId} to ${state}`);
    this.socket.emit('relay_toggle', { id: relayId, state });
    return true;
  }

  /**
   * Control popup motor
   * @param {string} direction - 'up', 'down', or 'release'
   */
  movePopup(direction) {
    if (!this.socket || !this.connected) {
      console.error('[WebSocket] Not connected, cannot move popup');
      return false;
    }

    console.log(`[WebSocket] Moving popup: ${direction}`);
    this.socket.emit('popup_move', { direction });
    return true;
  }

  /**
   * Activate a scene
   * @param {string} sceneId - Scene ID
   */
  activateScene(sceneId) {
    if (!this.socket || !this.connected) {
      console.error('[WebSocket] Not connected, cannot activate scene');
      return false;
    }

    console.log(`[WebSocket] Activating scene: ${sceneId}`);
    // Scene activation is done via HTTP API, not WebSocket
    // But we can listen for the relay_state_changed events that follow
    return true;
  }

  /**
   * Emergency stop - kill all relays
   */
  emergencyStop() {
    if (!this.socket || !this.connected) {
      console.error('[WebSocket] Not connected, cannot emergency stop');
      return false;
    }

    console.log('[WebSocket] EMERGENCY STOP!');
    this.socket.emit('emergency_stop');
    return true;
  }

  /**
   * Register an event listener
   * @param {string} event - Event name
   * @param {function} callback - Callback function
   */
  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  /**
   * Remove an event listener
   * @param {string} event - Event name
   * @param {function} callback - Callback function
   */
  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  /**
   * Emit event to all listeners
   * @private
   */
  _emit(event, data = null) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`[WebSocket] Error in ${event} listener:`, error);
        }
      });
    }
  }

  /**
   * Check if connected
   */
  isConnected() {
    return this.connected;
  }
}

// Singleton instance
const webSocketService = new WebSocketService();

export default webSocketService;
