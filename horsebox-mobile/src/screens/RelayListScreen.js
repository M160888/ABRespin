/**
 * Relay List Screen
 * Displays relays for a specific zone and allows toggling
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl
} from 'react-native';
import apiService from '../services/ApiService';
import webSocketService from '../services/WebSocketService';

const RelayListScreen = ({ route }) => {
  const { zoneName = 'All Relays' } = route.params || {};

  const [relays, setRelays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [connected, setConnected] = useState(false);

  // Load relays on mount
  useEffect(() => {
    loadRelays();

    // Listen for connection status
    webSocketService.on('connect', handleConnect);
    webSocketService.on('disconnect', handleDisconnect);
    webSocketService.on('relay_state_changed', handleRelayStateChanged);

    return () => {
      webSocketService.off('connect', handleConnect);
      webSocketService.off('disconnect', handleDisconnect);
      webSocketService.off('relay_state_changed', handleRelayStateChanged);
    };
  }, []);

  const handleConnect = () => {
    console.log('[RelayListScreen] WebSocket connected');
    setConnected(true);
  };

  const handleDisconnect = () => {
    console.log('[RelayListScreen] WebSocket disconnected');
    setConnected(false);
  };

  const handleRelayStateChanged = (data) => {
    console.log('[RelayListScreen] Relay state changed:', data);
    // Update relay state in local list
    setRelays(prevRelays =>
      prevRelays.map(relay =>
        relay.id === data.relay_id
          ? { ...relay, state: data.state }
          : relay
      )
    );
  };

  const loadRelays = async () => {
    try {
      setLoading(true);
      const data = await apiService.fetchRelays();

      // Add state field to relays (default OFF)
      const relaysWithState = data.relays.map(relay => ({
        ...relay,
        state: 0 // Default OFF (will be updated by real state)
      }));

      setRelays(relaysWithState);
    } catch (error) {
      console.error('[RelayListScreen] Error loading relays:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadRelays();
    setRefreshing(false);
  };

  const toggleRelay = (relay) => {
    // Don't allow toggling popup relays (1 & 2)
    if (relay.id === 1 || relay.id === 2) {
      console.log('[RelayListScreen] Popup relays cannot be manually toggled');
      return;
    }

    const newState = relay.state === 1 ? 0 : 1;

    // Optimistic update - update UI immediately
    setRelays(prevRelays =>
      prevRelays.map(r =>
        r.id === relay.id
          ? { ...r, state: newState }
          : r
      )
    );

    // Send command to server
    const success = webSocketService.toggleRelay(relay.id, newState);

    if (!success) {
      // Revert optimistic update if send failed
      setRelays(prevRelays =>
        prevRelays.map(r =>
          r.id === relay.id
            ? { ...r, state: relay.state }
            : r
        )
      );
    }
  };

  const renderRelay = ({ item: relay }) => {
    const isOn = relay.state === 1;
    const isPopup = relay.id === 1 || relay.id === 2;

    return (
      <TouchableOpacity
        style={[
          styles.relayCard,
          isOn && styles.relayCardOn,
          isPopup && styles.relayCardDisabled
        ]}
        onPress={() => toggleRelay(relay)}
        disabled={isPopup}
        activeOpacity={0.7}
      >
        <View style={styles.relayHeader}>
          <Text style={[styles.relayName, isOn && styles.relayNameOn]}>
            {relay.name}
          </Text>
          <View style={[styles.relayToggle, isOn && styles.relayToggleOn]}>
            <Text style={styles.relayToggleText}>
              {isOn ? 'ON' : 'OFF'}
            </Text>
          </View>
        </View>

        <View style={styles.relayInfo}>
          <Text style={styles.relayInfoText}>
            ID: {relay.id} • Zone: {relay.zone || 'unassigned'}
          </Text>
        </View>

        {isPopup && (
          <Text style={styles.popupWarning}>
            Use popup controls to operate
          </Text>
        )}
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#ff6b35" />
        <Text style={styles.loadingText}>Loading relays...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Connection status banner */}
      <View style={[
        styles.statusBanner,
        connected ? styles.statusConnected : styles.statusDisconnected
      ]}>
        <Text style={styles.statusText}>
          {connected ? '🔷 Connected' : '⚠️ Disconnected'}
        </Text>
      </View>

      {/* Relay list */}
      <FlatList
        data={relays}
        renderItem={renderRelay}
        keyExtractor={item => item.id.toString()}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor="#ff6b35"
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No relays found</Text>
          </View>
        }
      />
    </View>
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
    backgroundColor: '#0a0e17'
  },
  loadingText: {
    color: '#a0aec0',
    marginTop: 16,
    fontSize: 16
  },
  statusBanner: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center'
  },
  statusConnected: {
    backgroundColor: '#48bb78'
  },
  statusDisconnected: {
    backgroundColor: '#f56565'
  },
  statusText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700'
  },
  listContent: {
    padding: 16
  },
  relayCard: {
    backgroundColor: '#1a2332',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: '#2d3748'
  },
  relayCardOn: {
    borderColor: '#ff6b35',
    backgroundColor: 'rgba(255, 107, 53, 0.1)'
  },
  relayCardDisabled: {
    opacity: 0.5
  },
  relayHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8
  },
  relayName: {
    fontSize: 18,
    fontWeight: '700',
    color: '#ffffff',
    flex: 1
  },
  relayNameOn: {
    color: '#ff6b35'
  },
  relayToggle: {
    backgroundColor: '#2d3748',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    minWidth: 60,
    alignItems: 'center'
  },
  relayToggleOn: {
    backgroundColor: '#ff6b35'
  },
  relayToggleText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '700'
  },
  relayInfo: {
    marginTop: 4
  },
  relayInfoText: {
    color: '#a0aec0',
    fontSize: 12
  },
  popupWarning: {
    color: '#ed8936',
    fontSize: 11,
    marginTop: 8,
    fontStyle: 'italic'
  },
  emptyContainer: {
    padding: 40,
    alignItems: 'center'
  },
  emptyText: {
    color: '#a0aec0',
    fontSize: 16
  }
});

export default RelayListScreen;
