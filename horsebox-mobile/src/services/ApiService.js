/**
 * API Service
 * Handles HTTP requests to Flask REST API
 */

import config from '../config';

class ApiService {
  constructor() {
    // Extract base URL from WebSocket URL
    // ws://192.168.1.100:5000/socket.io/ -> http://192.168.1.100:5000
    const wsUrl = config.MOCK_WEBSOCKET_URL;
    this.baseUrl = wsUrl
      .replace('ws://', 'http://')
      .replace('wss://', 'https://')
      .replace('/socket.io/', '');

    console.log('[API] Base URL:', this.baseUrl);
  }

  /**
   * Fetch all relays and configuration
   */
  async fetchRelays() {
    try {
      const response = await fetch(`${this.baseUrl}/api/relays`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[API] Error fetching relays:', error);
      throw error;
    }
  }

  /**
   * Fetch all zones with relays
   */
  async fetchZones() {
    try {
      const response = await fetch(`${this.baseUrl}/api/zones`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[API] Error fetching zones:', error);
      throw error;
    }
  }

  /**
   * Fetch all scenes
   */
  async fetchScenes() {
    try {
      const response = await fetch(`${this.baseUrl}/api/scenes`);
      const data = await response.json();
      return data.scenes || [];
    } catch (error) {
      console.error('[API] Error fetching scenes:', error);
      throw error;
    }
  }

  /**
   * Activate a scene
   * @param {string} sceneId - Scene ID
   */
  async activateScene(sceneId) {
    try {
      const response = await fetch(`${this.baseUrl}/api/scene/${sceneId}/activate`, {
        method: 'POST'
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[API] Error activating scene:', error);
      throw error;
    }
  }

  /**
   * Create a new scene
   * @param {object} sceneData - Scene data
   */
  async createScene(sceneData) {
    try {
      const response = await fetch(`${this.baseUrl}/api/scene`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(sceneData)
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[API] Error creating scene:', error);
      throw error;
    }
  }

  /**
   * Update an existing scene
   * @param {string} sceneId - Scene ID
   * @param {object} sceneData - Scene data
   */
  async updateScene(sceneId, sceneData) {
    try {
      const response = await fetch(`${this.baseUrl}/api/scene/${sceneId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(sceneData)
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[API] Error updating scene:', error);
      throw error;
    }
  }

  /**
   * Delete a scene
   * @param {string} sceneId - Scene ID
   */
  async deleteScene(sceneId) {
    try {
      const response = await fetch(`${this.baseUrl}/api/scene/${sceneId}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[API] Error deleting scene:', error);
      throw error;
    }
  }

  /**
   * Update relay name
   * @param {number} relayId - Relay ID
   * @param {string} name - New name
   */
  async updateRelayName(relayId, name) {
    // This uses WebSocket, not HTTP
    // Handled by WebSocketService
    throw new Error('Use WebSocketService.updateRelayName() instead');
  }
}

// Singleton instance
const apiService = new ApiService();

export default apiService;
