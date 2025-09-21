#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Parental Monitoring System
Tests all core functionality including authentication, teen management, 
location tracking, app usage, web history, geofencing, and alerts.
"""

import requests
import json
import time
from datetime import datetime, timedelta
import uuid

# Configuration
BASE_URL = "https://incognito-eye-1.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class ParentalMonitoringTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS.copy()
        self.auth_token = None
        self.parent_id = None
        self.teen_id = None
        self.test_results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def make_request(self, method, endpoint, data=None, auth_required=True):
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()
        
        if auth_required and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except requests.exceptions.RequestException as e:
            return None, str(e)
    
    def test_parent_registration(self):
        """Test parent registration functionality"""
        test_email = f"parent_{uuid.uuid4().hex[:8]}@example.com"
        test_data = {
            "email": test_email,
            "password": "SecurePassword123!",
            "name": "John Smith"
        }
        
        response = self.make_request("POST", "/auth/register", test_data, auth_required=False)
        
        if response is None:
            self.log_result("Parent Registration", False, "Request failed - server not responding")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "parent" in data:
                self.auth_token = data["token"]
                self.parent_id = data["parent"]["id"]
                self.log_result("Parent Registration", True, f"Successfully registered parent: {data['parent']['name']}")
                return True
            else:
                self.log_result("Parent Registration", False, "Missing token or parent data in response", data)
                return False
        else:
            self.log_result("Parent Registration", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_parent_login(self):
        """Test parent login functionality"""
        if not self.parent_id:
            self.log_result("Parent Login", False, "No parent registered to test login")
            return False
        
        # First register a new parent for login test
        test_email = f"login_test_{uuid.uuid4().hex[:8]}@example.com"
        register_data = {
            "email": test_email,
            "password": "LoginTest123!",
            "name": "Jane Doe"
        }
        
        # Register
        register_response = self.make_request("POST", "/auth/register", register_data, auth_required=False)
        if register_response.status_code != 200:
            self.log_result("Parent Login", False, "Failed to register test parent for login")
            return False
        
        # Now test login
        login_data = {
            "email": test_email,
            "password": "LoginTest123!"
        }
        
        response = self.make_request("POST", "/auth/login", login_data, auth_required=False)
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "parent" in data:
                self.log_result("Parent Login", True, f"Successfully logged in parent: {data['parent']['name']}")
                return True
            else:
                self.log_result("Parent Login", False, "Missing token or parent data in response", data)
                return False
        else:
            self.log_result("Parent Login", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_create_teen(self):
        """Test creating a teen profile"""
        if not self.auth_token:
            self.log_result("Create Teen", False, "No authentication token available")
            return False
        
        teen_data = {
            "name": "Alex Johnson",
            "device_id": f"device_{uuid.uuid4().hex[:12]}",
            "phone_number": "+1234567890",
            "age": 16
        }
        
        response = self.make_request("POST", "/teens", teen_data)
        
        if response.status_code == 200:
            data = response.json()
            if "id" in data and "name" in data:
                self.teen_id = data["id"]
                self.log_result("Create Teen", True, f"Successfully created teen: {data['name']}")
                return True
            else:
                self.log_result("Create Teen", False, "Missing required fields in response", data)
                return False
        else:
            self.log_result("Create Teen", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_get_teens(self):
        """Test retrieving teens for a parent"""
        if not self.auth_token:
            self.log_result("Get Teens", False, "No authentication token available")
            return False
        
        response = self.make_request("GET", "/teens")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                self.log_result("Get Teens", True, f"Successfully retrieved {len(data)} teens")
                return True
            else:
                self.log_result("Get Teens", False, "Response is not a list", data)
                return False
        else:
            self.log_result("Get Teens", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_get_individual_teen(self):
        """Test retrieving individual teen"""
        if not self.teen_id:
            self.log_result("Get Individual Teen", False, "No teen ID available")
            return False
        
        response = self.make_request("GET", f"/teens/{self.teen_id}")
        
        if response.status_code == 200:
            data = response.json()
            if "id" in data and data["id"] == self.teen_id:
                self.log_result("Get Individual Teen", True, f"Successfully retrieved teen: {data['name']}")
                return True
            else:
                self.log_result("Get Individual Teen", False, "Teen ID mismatch or missing data", data)
                return False
        else:
            self.log_result("Get Individual Teen", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_location_tracking(self):
        """Test location tracking functionality"""
        if not self.teen_id:
            self.log_result("Location Tracking", False, "No teen ID available")
            return False
        
        # Create location
        location_data = {
            "teen_id": self.teen_id,
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 10.0,
            "address": "San Francisco, CA"
        }
        
        response = self.make_request("POST", "/locations", location_data, auth_required=False)
        
        if response.status_code == 200:
            data = response.json()
            if "status" in data and data["status"] == "success":
                self.log_result("Create Location", True, "Successfully created location record")
                
                # Now test retrieving locations
                time.sleep(1)  # Brief delay
                get_response = self.make_request("GET", f"/teens/{self.teen_id}/locations")
                
                if get_response.status_code == 200:
                    locations = get_response.json()
                    if isinstance(locations, list) and len(locations) > 0:
                        self.log_result("Get Locations", True, f"Successfully retrieved {len(locations)} location records")
                        return True
                    else:
                        self.log_result("Get Locations", False, "No locations found or invalid response", locations)
                        return False
                else:
                    self.log_result("Get Locations", False, f"HTTP {get_response.status_code}", get_response.text)
                    return False
            else:
                self.log_result("Create Location", False, "Unexpected response format", data)
                return False
        else:
            self.log_result("Create Location", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_geofencing(self):
        """Test geofencing functionality"""
        if not self.teen_id:
            self.log_result("Geofencing", False, "No teen ID available")
            return False
        
        # Create geofence
        geofence_data = {
            "teen_id": self.teen_id,
            "name": "Home",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "radius": 100.0,
            "type": "safe",
            "notify_on_enter": True,
            "notify_on_exit": True
        }
        
        response = self.make_request("POST", "/geofences", geofence_data)
        
        if response.status_code == 200:
            data = response.json()
            if "id" in data and "name" in data:
                self.log_result("Create Geofence", True, f"Successfully created geofence: {data['name']}")
                
                # Test retrieving geofences
                get_response = self.make_request("GET", f"/teens/{self.teen_id}/geofences")
                
                if get_response.status_code == 200:
                    geofences = get_response.json()
                    if isinstance(geofences, list) and len(geofences) > 0:
                        self.log_result("Get Geofences", True, f"Successfully retrieved {len(geofences)} geofences")
                        return True
                    else:
                        self.log_result("Get Geofences", False, "No geofences found", geofences)
                        return False
                else:
                    self.log_result("Get Geofences", False, f"HTTP {get_response.status_code}", get_response.text)
                    return False
            else:
                self.log_result("Create Geofence", False, "Missing required fields", data)
                return False
        else:
            self.log_result("Create Geofence", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_app_usage_tracking(self):
        """Test app usage tracking functionality"""
        if not self.teen_id:
            self.log_result("App Usage Tracking", False, "No teen ID available")
            return False
        
        # Create app usage record
        usage_data = {
            "teen_id": self.teen_id,
            "app_name": "Instagram",
            "package_name": "com.instagram.android",
            "usage_time": 45,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        response = self.make_request("POST", "/app-usage", usage_data, auth_required=False)
        
        if response.status_code == 200:
            data = response.json()
            if "status" in data and data["status"] in ["created", "updated"]:
                self.log_result("Create App Usage", True, f"Successfully {data['status']} app usage record")
                
                # Test retrieving app usage
                get_response = self.make_request("GET", f"/teens/{self.teen_id}/app-usage")
                
                if get_response.status_code == 200:
                    usage_records = get_response.json()
                    if isinstance(usage_records, list) and len(usage_records) > 0:
                        self.log_result("Get App Usage", True, f"Successfully retrieved {len(usage_records)} usage records")
                        return True
                    else:
                        self.log_result("Get App Usage", False, "No usage records found", usage_records)
                        return False
                else:
                    self.log_result("Get App Usage", False, f"HTTP {get_response.status_code}", get_response.text)
                    return False
            else:
                self.log_result("Create App Usage", False, "Unexpected response format", data)
                return False
        else:
            self.log_result("Create App Usage", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_web_history_tracking(self):
        """Test web history tracking functionality"""
        if not self.teen_id:
            self.log_result("Web History Tracking", False, "No teen ID available")
            return False
        
        # Create web history record
        history_data = {
            "teen_id": self.teen_id,
            "url": "https://www.youtube.com/watch?v=example",
            "title": "Educational Video - Science Explained"
        }
        
        response = self.make_request("POST", "/web-history", history_data, auth_required=False)
        
        if response.status_code == 200:
            data = response.json()
            if "status" in data and data["status"] in ["created", "updated"]:
                self.log_result("Create Web History", True, f"Successfully {data['status']} web history record")
                
                # Test retrieving web history
                get_response = self.make_request("GET", f"/teens/{self.teen_id}/web-history")
                
                if get_response.status_code == 200:
                    history_records = get_response.json()
                    if isinstance(history_records, list) and len(history_records) > 0:
                        self.log_result("Get Web History", True, f"Successfully retrieved {len(history_records)} history records")
                        return True
                    else:
                        self.log_result("Get Web History", False, "No history records found", history_records)
                        return False
                else:
                    self.log_result("Get Web History", False, f"HTTP {get_response.status_code}", get_response.text)
                    return False
            else:
                self.log_result("Create Web History", False, "Unexpected response format", data)
                return False
        else:
            self.log_result("Create Web History", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_alerts_system(self):
        """Test alerts system functionality"""
        if not self.auth_token:
            self.log_result("Alerts System", False, "No authentication token available")
            return False
        
        # Get alerts
        response = self.make_request("GET", "/alerts")
        
        if response.status_code == 200:
            alerts = response.json()
            if isinstance(alerts, list):
                self.log_result("Get Alerts", True, f"Successfully retrieved {len(alerts)} alerts")
                
                # Test unread alerts filter
                unread_response = self.make_request("GET", "/alerts?unread_only=true")
                if unread_response.status_code == 200:
                    unread_alerts = unread_response.json()
                    self.log_result("Get Unread Alerts", True, f"Successfully retrieved {len(unread_alerts)} unread alerts")
                    return True
                else:
                    self.log_result("Get Unread Alerts", False, f"HTTP {unread_response.status_code}", unread_response.text)
                    return False
            else:
                self.log_result("Get Alerts", False, "Response is not a list", alerts)
                return False
        else:
            self.log_result("Get Alerts", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def test_dashboard_data(self):
        """Test dashboard data retrieval"""
        if not self.teen_id:
            self.log_result("Dashboard Data", False, "No teen ID available")
            return False
        
        response = self.make_request("GET", f"/dashboard/{self.teen_id}")
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["teen", "screen_time_today", "app_usage_today", "recent_locations", 
                             "recent_web_history", "geofences", "unread_alerts"]
            
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                self.log_result("Dashboard Data", True, "Successfully retrieved complete dashboard data")
                return True
            else:
                self.log_result("Dashboard Data", False, f"Missing fields: {missing_fields}", data)
                return False
        else:
            self.log_result("Dashboard Data", False, f"HTTP {response.status_code}", response.text)
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Parental Monitoring API Tests")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Authentication tests
        self.test_parent_registration()
        self.test_parent_login()
        
        # Teen management tests
        self.test_create_teen()
        self.test_get_teens()
        self.test_get_individual_teen()
        
        # Core monitoring tests
        self.test_location_tracking()
        self.test_app_usage_tracking()
        self.test_web_history_tracking()
        
        # Real-time features
        self.test_geofencing()
        self.test_alerts_system()
        
        # Dashboard
        self.test_dashboard_data()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['message']}")
        
        print("\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result["success"]:
                print(f"  • {result['test']}: {result['message']}")

if __name__ == "__main__":
    tester = ParentalMonitoringTester()
    tester.run_all_tests()