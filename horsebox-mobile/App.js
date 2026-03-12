/**
 * Horsebox Mobile App
 * Main entry point
 */

import React, { useEffect, useState } from 'react';
import {
  SafeAreaView,
  StyleSheet,
  StatusBar,
  View,
  Text,
  TouchableOpacity,
  Alert
} from 'react-native';
import RelayListScreen from './src/screens/RelayListScreen';
import webSocketService from './src/services/WebSocketService';
import config from './src/config';

const App = () => {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(true);

  useEffect(() => {
    // Connect to WebSocket on app launch
    console.log('[App] Starting Horsebox Mobile...');
    console.log('[App] Mock Mode:', config.MOCK_MODE);

    if (config.MOCK_MODE) {
      console.log('[App] Connecting to Flask server at:', config.MOCK_WEBSOCKET_URL);
      console.log('[App] ⚠️  Make sure to update the IP in src/config.js!');
    }

    // Connect to WebSocket
    webSocketService.connect();

    // Listen for connection events
    webSocketService.on('connect', handleConnect);
    webSocketService.on('disconnect', handleDisconnect);

    // Initial connection check after 2 seconds
    setTimeout(() => {
      if (!webSocketService.isConnected()) {
        setConnecting(false);
        showConnectionError();
      }
    }, 2000);

    return () => {
      webSocketService.off('connect', handleConnect);
      webSocketService.off('disconnect', handleDisconnect);
      webSocketService.disconnect();
    };
  }, []);

  const handleConnect = () => {
    console.log('[App] Connected to server!');
    setConnected(true);
    setConnecting(false);
  };

  const handleDisconnect = () => {
    console.log('[App] Disconnected from server');
    setConnected(false);
  };

  const showConnectionError = () => {
    Alert.alert(
      'Connection Error',
      `Cannot connect to Flask server.\n\n` +
      `Make sure:\n` +
      `1. Flask is running (cd horsebox-kiosk && python src/api/app.py)\n` +
      `2. Your phone and laptop are on the same WiFi\n` +
      `3. Update IP in src/config.js to your laptop's IP\n\n` +
      `Current URL: ${config.MOCK_WEBSOCKET_URL}`,
      [
        {
          text: 'Retry',
          onPress: () => {
            setConnecting(true);
            webSocketService.connect();
            setTimeout(() => {
              if (!webSocketService.isConnected()) {
                setConnecting(false);
                showConnectionError();
              }
            }, 2000);
          }
        },
        { text: 'Cancel', style: 'cancel' }
      ]
    );
  };

  const handleEmergencyStop = () => {
    Alert.alert(
      'Emergency Stop',
      'This will turn OFF all 30 relays immediately!\n\nAre you sure?',
      [
        {
          text: 'Cancel',
          style: 'cancel'
        },
        {
          text: 'STOP ALL',
          style: 'destructive',
          onPress: () => {
            webSocketService.emergencyStop();
          }
        }
      ]
    );
  };

  if (connecting) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#0a0e17" />
        <View style={styles.centerContainer}>
          <Text style={styles.title}>Horsebox Mobile</Text>
          <Text style={styles.subtitle}>Connecting...</Text>
          <Text style={styles.infoText}>
            {config.MOCK_MODE ? 'Mock Mode (No BLE)' : 'BLE Mode'}
          </Text>
          <Text style={styles.urlText}>
            {config.MOCK_WEBSOCKET_URL}
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0e17" />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Horsebox Control</Text>
        <TouchableOpacity
          style={styles.emergencyButton}
          onPress={handleEmergencyStop}
        >
          <Text style={styles.emergencyButtonText}>STOP</Text>
        </TouchableOpacity>
      </View>

      {/* Main content */}
      <RelayListScreen route={{ params: { zoneName: 'All Relays' } }} />

      {/* Footer info */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>
          {config.MOCK_MODE ? '🔧 Mock Mode - No BLE' : '📱 BLE Mode'}
        </Text>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0e17'
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 8
  },
  subtitle: {
    fontSize: 18,
    color: '#a0aec0',
    marginBottom: 16
  },
  infoText: {
    fontSize: 14,
    color: '#00d4ff',
    marginTop: 8
  },
  urlText: {
    fontSize: 12,
    color: '#a0aec0',
    marginTop: 8,
    textAlign: 'center'
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#141b2d',
    borderBottomWidth: 2,
    borderBottomColor: '#2d3748'
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#ffffff'
  },
  emergencyButton: {
    backgroundColor: '#f56565',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#ffffff'
  },
  emergencyButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700'
  },
  footer: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    backgroundColor: '#141b2d',
    borderTopWidth: 1,
    borderTopColor: '#2d3748',
    alignItems: 'center'
  },
  footerText: {
    color: '#a0aec0',
    fontSize: 12
  }
});

export default App;
