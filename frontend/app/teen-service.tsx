import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Alert,
  AppState,
  Platform,
  Dimensions,
} from 'react-native';
import * as Location from 'expo-location';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';

interface LocationData {
  latitude: number;
  longitude: number;
  accuracy?: number;
  address?: string;
}

interface AppUsageData {
  app_name: string;
  package_name: string;
  usage_time: number;
  date: string;
}

interface TeenConfig {
  teen_id: string;
  device_id: string;
  monitoring_enabled: boolean;
  location_interval: number; // minutes
}

export default function TeenService() {
  const [config, setConfig] = useState<TeenConfig | null>(null);
  const [isSetup, setIsSetup] = useState(false);
  const [locationPermission, setLocationPermission] = useState(false);
  const [lastLocationTime, setLastLocationTime] = useState(0);
  const [isMonitoring, setIsMonitoring] = useState(false);
  
  const appState = useRef(AppState.currentState);
  const locationInterval = useRef<NodeJS.Timeout | null>(null);
  const usageTracker = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    initializeService();
    setupAppStateListener();
    return cleanup;
  }, []);

  useEffect(() => {
    if (config && config.monitoring_enabled && locationPermission) {
      startMonitoring();
    } else {
      stopMonitoring();
    }
  }, [config, locationPermission]);

  const initializeService = async () => {
    try {
      // Load configuration from storage
      const savedConfig = await AsyncStorage.getItem('teen_config');
      if (savedConfig) {
        const parsedConfig = JSON.parse(savedConfig);
        setConfig(parsedConfig);
        setIsSetup(true);
      } else {
        // Setup required - in real deployment, this would be configured during installation
        const defaultConfig: TeenConfig = {
          teen_id: 'demo-teen-id',
          device_id: `android_${Date.now()}`,
          monitoring_enabled: true,
          location_interval: 5, // 5 minutes
        };
        
        await AsyncStorage.setItem('teen_config', JSON.stringify(defaultConfig));
        setConfig(defaultConfig);
        setIsSetup(true);
      }

      // Request location permission
      await requestLocationPermission();
    } catch (error) {
      console.error('Failed to initialize service:', error);
    }
  };

  const requestLocationPermission = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      
      if (status === 'granted') {
        setLocationPermission(true);
        
        // Also request background permission for continuous tracking
        if (Platform.OS === 'android') {
          const backgroundStatus = await Location.requestBackgroundPermissionsAsync();
          console.log('Background location permission:', backgroundStatus.status);
        }
      } else {
        setLocationPermission(false);
        Alert.alert(
          'Location Permission Required',
          'This app needs location access for safety monitoring.',
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      console.error('Error requesting location permission:', error);
      setLocationPermission(false);
    }
  };

  const setupAppStateListener = () => {
    const handleAppStateChange = (nextAppState: string) => {
      if (appState.current.match(/inactive|background/) && nextAppState === 'active') {
        // App came to foreground
        console.log('App came to foreground');
        trackAppUsage('FamilyGuard Teen', 'com.familyguard.teen', 1);
      }
      
      appState.current = nextAppState;
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription?.remove();
  };

  const startMonitoring = () => {
    if (isMonitoring) return;
    
    console.log('Starting monitoring service...');
    setIsMonitoring(true);

    // Start location tracking
    if (config && config.location_interval > 0) {
      locationInterval.current = setInterval(
        trackLocation,
        config.location_interval * 60 * 1000 // Convert minutes to milliseconds
      );
      
      // Track location immediately
      trackLocation();
    }

    // Start app usage simulation (in real app, this would use Android's UsageStatsManager)
    simulateAppUsage();
  };

  const stopMonitoring = () => {
    console.log('Stopping monitoring service...');
    setIsMonitoring(false);
    
    if (locationInterval.current) {
      clearInterval(locationInterval.current);
      locationInterval.current = null;
    }
  };

  const trackLocation = async () => {
    if (!locationPermission || !config) return;

    try {
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
        timeInterval: 30000, // 30 seconds
      });

      const locationData: LocationData = {
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
        accuracy: location.coords.accuracy || undefined,
      };

      // Try to get address
      try {
        const addresses = await Location.reverseGeocodeAsync({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
        });

        if (addresses.length > 0) {
          const address = addresses[0];
          locationData.address = `${address.street || ''} ${address.city || ''} ${address.region || ''}`.trim();
        }
      } catch (geocodeError) {
        console.log('Geocoding failed:', geocodeError);
      }

      // Send location to server
      await sendLocationData(locationData);
      setLastLocationTime(Date.now());
      
    } catch (error) {
      console.error('Failed to track location:', error);
    }
  };

  const sendLocationData = async (locationData: LocationData) => {
    if (!config) return;

    try {
      const response = await fetch(`${API_BASE}/locations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          teen_id: config.teen_id,
          ...locationData,
        }),
      });

      if (response.ok) {
        console.log('Location data sent successfully');
      } else {
        console.error('Failed to send location data:', response.status);
      }
    } catch (error) {
      console.error('Error sending location data:', error);
    }
  };

  const trackAppUsage = async (appName: string, packageName: string, minutes: number) => {
    if (!config) return;

    const today = new Date().toISOString().split('T')[0];
    
    try {
      const response = await fetch(`${API_BASE}/app-usage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          teen_id: config.teen_id,
          app_name: appName,
          package_name: packageName,
          usage_time: minutes,
          date: today,
        }),
      });

      if (response.ok) {
        console.log(`App usage tracked: ${appName} - ${minutes}m`);
      }
    } catch (error) {
      console.error('Error tracking app usage:', error);
    }
  };

  const trackWebHistory = async (url: string, title: string) => {
    if (!config) return;

    try {
      const response = await fetch(`${API_BASE}/web-history`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          teen_id: config.teen_id,
          url,
          title,
        }),
      });

      if (response.ok) {
        console.log(`Web history tracked: ${title}`);
      }
    } catch (error) {
      console.error('Error tracking web history:', error);
    }
  };

  const simulateAppUsage = () => {
    // Simulate app usage data for demo purposes
    const apps = [
      { name: 'Instagram', package: 'com.instagram.android' },
      { name: 'TikTok', package: 'com.zhiliaoapp.musically' },
      { name: 'Snapchat', package: 'com.snapchat.android' },
      { name: 'WhatsApp', package: 'com.whatsapp' },
      { name: 'YouTube', package: 'com.google.android.youtube' },
      { name: 'Chrome', package: 'com.android.chrome' },
    ];

    // Track some usage every minute for demo
    const usageSimulator = setInterval(() => {
      const randomApp = apps[Math.floor(Math.random() * apps.length)];
      const randomUsage = Math.floor(Math.random() * 10) + 1; // 1-10 minutes
      trackAppUsage(randomApp.name, randomApp.package, randomUsage);

      // Also simulate some web history
      if (Math.random() > 0.7) {
        const websites = [
          { url: 'https://www.google.com/search?q=homework+help', title: 'Google Search' },
          { url: 'https://www.youtube.com/watch?v=educational', title: 'Educational Video - YouTube' },
          { url: 'https://en.wikipedia.org/wiki/Science', title: 'Science - Wikipedia' },
          { url: 'https://www.instagram.com/', title: 'Instagram' },
          { url: 'https://www.tiktok.com/', title: 'TikTok' },
        ];
        
        const randomSite = websites[Math.floor(Math.random() * websites.length)];
        trackWebHistory(randomSite.url, randomSite.title);
      }
    }, 60000); // Every minute

    // Clear after some time to avoid infinite simulation
    setTimeout(() => {
      clearInterval(usageSimulator);
    }, 300000); // Stop after 5 minutes
  };

  const cleanup = () => {
    stopMonitoring();
  };

  const formatLastUpdate = () => {
    if (lastLocationTime === 0) return 'Never';
    const minutes = Math.floor((Date.now() - lastLocationTime) / (1000 * 60));
    if (minutes < 1) return 'Just now';
    if (minutes === 1) return '1 minute ago';
    return `${minutes} minutes ago`;
  };

  if (!isSetup || !config) {
    return (
      <View style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Setting up monitoring...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.statusDot} />
        <Text style={styles.headerText}>Safety Service</Text>
      </View>

      <View style={styles.content}>
        <View style={styles.statusCard}>
          <Text style={styles.statusTitle}>Service Status</Text>
          <Text style={styles.statusValue}>
            {isMonitoring ? '🟢 Active' : '🔴 Inactive'}
          </Text>
        </View>

        <View style={styles.statusCard}>
          <Text style={styles.statusTitle}>Location Tracking</Text>
          <Text style={styles.statusValue}>
            {locationPermission ? '✅ Enabled' : '❌ Disabled'}
          </Text>
          <Text style={styles.statusDetail}>
            Last update: {formatLastUpdate()}
          </Text>
        </View>

        <View style={styles.statusCard}>
          <Text style={styles.statusTitle}>Device ID</Text>
          <Text style={styles.statusDetail}>{config.device_id}</Text>
        </View>

        <View style={styles.infoContainer}>
          <Text style={styles.infoText}>
            This service helps keep you safe by sharing your location with your family.
            It runs quietly in the background and doesn't interfere with your apps.
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 16,
    color: '#666',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#4CAF50',
    marginRight: 12,
  },
  headerText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  content: {
    flex: 1,
    padding: 20,
  },
  statusCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 8,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  statusTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  statusValue: {
    fontSize: 16,
    color: '#666',
    marginBottom: 4,
  },
  statusDetail: {
    fontSize: 12,
    color: '#999',
  },
  infoContainer: {
    backgroundColor: '#E3F2FD',
    padding: 16,
    borderRadius: 8,
    marginTop: 20,
  },
  infoText: {
    fontSize: 14,
    color: '#1976D2',
    lineHeight: 20,
    textAlign: 'center',
  },
});