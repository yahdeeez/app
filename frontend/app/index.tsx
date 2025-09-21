import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const API_BASE = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';

interface Teen {
  id: string;
  name: string;
  device_id: string;
  phone_number?: string;
  age?: number;
  created_at: string;
}

interface DashboardData {
  teen: Teen;
  screen_time_today: number;
  app_usage_today: Array<{
    app_name: string;
    usage_time: number;
  }>;
  recent_locations: Array<{
    latitude: number;
    longitude: number;
    address?: string;
    timestamp: string;
  }>;
  recent_web_history: Array<{
    url: string;
    title: string;
    visit_count: number;
    timestamp: string;
  }>;
  unread_alerts: Array<{
    type: string;
    message: string;
    created_at: string;
  }>;
}

export default function ParentDashboard() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [teens, setTeens] = useState<Teen[]>([]);
  const [selectedTeen, setSelectedTeen] = useState<Teen | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<'dashboard' | 'location' | 'apps' | 'alerts'>('dashboard');
  
  // Login form state
  const [email, setEmail] = useState('demo@parent.com');
  const [password, setPassword] = useState('password123');
  const [name, setName] = useState('Demo Parent');
  const [isRegistering, setIsRegistering] = useState(false);

  useEffect(() => {
    if (isLoggedIn && token) {
      loadTeens();
    }
  }, [isLoggedIn, token]);

  useEffect(() => {
    if (selectedTeen && token) {
      loadDashboardData(selectedTeen.id);
      // Set up polling for real-time updates
      const interval = setInterval(() => {
        loadDashboardData(selectedTeen.id);
      }, 30000); // Update every 30 seconds

      return () => clearInterval(interval);
    }
  }, [selectedTeen, token]);

  const handleAuth = async () => {
    setLoading(true);
    try {
      const endpoint = isRegistering ? '/auth/register' : '/auth/login';
      const body = isRegistering ? { email, password, name } : { email, password };
      
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();
      
      if (response.ok) {
        setToken(data.token);
        setIsLoggedIn(true);
        Alert.alert('Success', `${isRegistering ? 'Registered' : 'Logged in'} successfully!`);
      } else {
        Alert.alert('Error', data.detail || 'Authentication failed');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error. Please try again.');
      console.error('Auth error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTeens = async () => {
    try {
      const response = await fetch(`${API_BASE}/teens`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const teensData = await response.json();
        setTeens(teensData);
        if (teensData.length > 0) {
          setSelectedTeen(teensData[0]);
        }
      }
    } catch (error) {
      console.error('Error loading teens:', error);
    }
  };

  const loadDashboardData = async (teenId: string) => {
    try {
      const response = await fetch(`${API_BASE}/dashboard/${teenId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    }
  };

  const addDemoTeen = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/teens`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: 'Demo Teen',
          device_id: `device_${Date.now()}`,
          phone_number: '+1234567890',
          age: 16,
        }),
      });

      if (response.ok) {
        Alert.alert('Success', 'Demo teen added successfully!');
        await loadTeens();
      } else {
        const data = await response.json();
        Alert.alert('Error', data.detail || 'Failed to add teen');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to add teen');
      console.error('Error adding teen:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  if (!isLoggedIn) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loginContainer}>
          <View style={styles.loginHeader}>
            <Ionicons name="shield-checkmark" size={60} color="#4A90E2" />
            <Text style={styles.appTitle}>FamilyGuard</Text>
            <Text style={styles.appSubtitle}>Parental Monitoring Dashboard</Text>
          </View>

          <View style={styles.loginForm}>
            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Email</Text>
              <View style={styles.inputWrapper}>
                <Ionicons name="mail" size={20} color="#666" style={styles.inputIcon} />
                <Text style={styles.inputText}>{email}</Text>
              </View>
            </View>

            {isRegistering && (
              <View style={styles.inputContainer}>
                <Text style={styles.inputLabel}>Name</Text>
                <View style={styles.inputWrapper}>
                  <Ionicons name="person" size={20} color="#666" style={styles.inputIcon} />
                  <Text style={styles.inputText}>{name}</Text>
                </View>
              </View>
            )}

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Password</Text>
              <View style={styles.inputWrapper}>
                <Ionicons name="lock-closed" size={20} color="#666" style={styles.inputIcon} />
                <Text style={styles.inputText}>••••••••</Text>
              </View>
            </View>

            <TouchableOpacity
              style={styles.authButton}
              onPress={handleAuth}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.authButtonText}>
                  {isRegistering ? 'Create Account' : 'Sign In'}
                </Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.switchModeButton}
              onPress={() => setIsRegistering(!isRegistering)}
            >
              <Text style={styles.switchModeText}>
                {isRegistering ? 'Already have an account? Sign In' : 'Need an account? Register'}
              </Text>
            </TouchableOpacity>

            <View style={styles.demoInfo}>
              <Text style={styles.demoText}>
                Demo credentials are pre-filled. Click "Create Account" to get started!
              </Text>
            </View>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  if (teens.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.emptyState}>
          <Ionicons name="people" size={80} color="#ccc" />
          <Text style={styles.emptyTitle}>No Teens Added</Text>
          <Text style={styles.emptySubtitle}>
            Add a teen to start monitoring their device activity and location.
          </Text>
          
          <TouchableOpacity
            style={styles.addTeenButton}
            onPress={addDemoTeen}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <Ionicons name="add" size={24} color="#fff" />
                <Text style={styles.addTeenButtonText}>Add Demo Teen</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.logoutButton}
            onPress={() => {
              setIsLoggedIn(false);
              setToken(null);
              setTeens([]);
              setSelectedTeen(null);
              setDashboardData(null);
            }}
          >
            <Text style={styles.logoutButtonText}>Logout</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>FamilyGuard</Text>
        <TouchableOpacity
          onPress={() => {
            setIsLoggedIn(false);
            setToken(null);
            setTeens([]);
            setSelectedTeen(null);
            setDashboardData(null);
          }}
        >
          <Ionicons name="log-out" size={24} color="#666" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {/* Teen Selector */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Monitoring</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {teens.map((teen) => (
              <TouchableOpacity
                key={teen.id}
                style={[
                  styles.teenCard,
                  selectedTeen?.id === teen.id && styles.selectedTeenCard,
                ]}
                onPress={() => setSelectedTeen(teen)}
              >
                <Ionicons 
                  name="person-circle" 
                  size={40} 
                  color={selectedTeen?.id === teen.id ? '#4A90E2' : '#666'} 
                />
                <Text style={[
                  styles.teenName,
                  selectedTeen?.id === teen.id && styles.selectedTeenName,
                ]}>
                  {teen.name}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {selectedTeen && dashboardData && (
          <>
            {/* Screen Time Summary */}
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="time" size={24} color="#4A90E2" />
                <Text style={styles.cardTitle}>Screen Time Today</Text>
              </View>
              <Text style={styles.screenTimeValue}>
                {formatTime(dashboardData.screen_time_today)}
              </Text>
              
              {dashboardData.app_usage_today.length > 0 && (
                <View style={styles.appUsageList}>
                  <Text style={styles.sectionTitle}>Top Apps</Text>
                  {dashboardData.app_usage_today
                    .sort((a, b) => b.usage_time - a.usage_time)
                    .slice(0, 5)
                    .map((app, index) => (
                    <View key={index} style={styles.appUsageItem}>
                      <Text style={styles.appName}>{app.app_name}</Text>
                      <Text style={styles.appTime}>{formatTime(app.usage_time)}</Text>
                    </View>
                  ))}
                </View>
              )}
            </View>

            {/* Location Status */}
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="location" size={24} color="#4A90E2" />
                <Text style={styles.cardTitle}>Location</Text>
              </View>
              
              {dashboardData.recent_locations.length > 0 ? (
                <View>
                  <View style={styles.locationItem}>
                    <Text style={styles.locationLabel}>Current Location:</Text>
                    <Text style={styles.locationValue}>
                      {dashboardData.recent_locations[0].address || 
                       `${dashboardData.recent_locations[0].latitude.toFixed(4)}, ${dashboardData.recent_locations[0].longitude.toFixed(4)}`}
                    </Text>
                    <Text style={styles.locationTime}>
                      Last updated: {formatDate(dashboardData.recent_locations[0].timestamp)}
                    </Text>
                  </View>
                </View>
              ) : (
                <Text style={styles.noDataText}>No location data available</Text>
              )}
            </View>

            {/* Recent Web Activity */}
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="globe" size={24} color="#4A90E2" />
                <Text style={styles.cardTitle}>Recent Web Activity</Text>
              </View>
              
              {dashboardData.recent_web_history.length > 0 ? (
                <View style={styles.webHistoryList}>
                  {dashboardData.recent_web_history.slice(0, 5).map((item, index) => (
                    <View key={index} style={styles.webHistoryItem}>
                      <Text style={styles.webTitle} numberOfLines={1}>
                        {item.title}
                      </Text>
                      <Text style={styles.webUrl} numberOfLines={1}>
                        {item.url}
                      </Text>
                      <View style={styles.webMeta}>
                        <Text style={styles.webTime}>
                          {formatDate(item.timestamp)}
                        </Text>
                        <Text style={styles.webVisits}>
                          {item.visit_count} visit{item.visit_count > 1 ? 's' : ''}
                        </Text>
                      </View>
                    </View>
                  ))}
                </View>
              ) : (
                <Text style={styles.noDataText}>No web activity recorded</Text>
              )}
            </View>

            {/* Alerts */}
            {dashboardData.unread_alerts.length > 0 && (
              <View style={styles.card}>
                <View style={styles.cardHeader}>
                  <Ionicons name="warning" size={24} color="#FF6B6B" />
                  <Text style={styles.cardTitle}>Recent Alerts</Text>
                </View>
                
                <View style={styles.alertsList}>
                  {dashboardData.unread_alerts.slice(0, 3).map((alert, index) => (
                    <View key={index} style={styles.alertItem}>
                      <Text style={styles.alertMessage}>{alert.message}</Text>
                      <Text style={styles.alertTime}>
                        {formatDate(alert.created_at)}
                      </Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {/* Demo Data Notice */}
            <View style={styles.demoNotice}>
              <Ionicons name="information-circle" size={20} color="#4A90E2" />
              <Text style={styles.demoNoticeText}>
                This is a demo dashboard. In a real deployment, data would be collected from the teen's device.
              </Text>
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginLeft: 8,
  },
  teenCard: {
    alignItems: 'center',
    padding: 12,
    marginRight: 12,
    borderRadius: 8,
    minWidth: 80,
  },
  selectedTeenCard: {
    backgroundColor: '#E3F2FD',
  },
  teenName: {
    marginTop: 4,
    fontSize: 14,
    color: '#666',
  },
  selectedTeenName: {
    color: '#4A90E2',
    fontWeight: '600',
  },
  screenTimeValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#4A90E2',
    textAlign: 'center',
    marginVertical: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginTop: 16,
    marginBottom: 8,
  },
  appUsageList: {
    marginTop: 8,
  },
  appUsageItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  appName: {
    fontSize: 14,
    color: '#333',
    flex: 1,
  },
  appTime: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  locationItem: {
    marginBottom: 8,
  },
  locationLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  locationValue: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  locationTime: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  webHistoryList: {
    marginTop: 8,
  },
  webHistoryItem: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  webTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  webUrl: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  webMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  webTime: {
    fontSize: 12,
    color: '#999',
  },
  webVisits: {
    fontSize: 12,
    color: '#4A90E2',
  },
  alertsList: {
    marginTop: 8,
  },
  alertItem: {
    backgroundColor: '#FFF3E0',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  alertMessage: {
    fontSize: 14,
    color: '#333',
  },
  alertTime: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  noDataText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    fontStyle: 'italic',
    marginTop: 8,
  },
  demoNotice: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E3F2FD',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  demoNoticeText: {
    fontSize: 12,
    color: '#1976D2',
    marginLeft: 8,
    flex: 1,
  },
  // Login styles
  loginContainer: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  loginHeader: {
    alignItems: 'center',
    marginBottom: 40,
  },
  appTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#4A90E2',
    marginTop: 16,
  },
  appSubtitle: {
    fontSize: 16,
    color: '#666',
    marginTop: 8,
    textAlign: 'center',
  },
  loginForm: {
    width: '100%',
  },
  inputContainer: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 16,
    borderWidth: 1,
    borderColor: '#e9ecef',
  },
  inputIcon: {
    marginRight: 12,
  },
  inputText: {
    flex: 1,
    fontSize: 16,
    color: '#333',
  },
  authButton: {
    backgroundColor: '#4A90E2',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  authButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  switchModeButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  switchModeText: {
    color: '#4A90E2',
    fontSize: 14,
  },
  demoInfo: {
    marginTop: 24,
    padding: 16,
    backgroundColor: '#E3F2FD',
    borderRadius: 8,
  },
  demoText: {
    fontSize: 14,
    color: '#1976D2',
    textAlign: 'center',
  },
  // Empty state styles
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 16,
  },
  emptySubtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 24,
  },
  addTeenButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4A90E2',
    padding: 16,
    borderRadius: 8,
    marginTop: 24,
  },
  addTeenButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  logoutButton: {
    marginTop: 16,
    padding: 12,
  },
  logoutButtonText: {
    color: '#666',
    fontSize: 14,
  },
});