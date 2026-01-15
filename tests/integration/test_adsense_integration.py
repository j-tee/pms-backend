#!/usr/bin/env python
"""
Google AdSense Integration Test Script
Tests the complete backend-frontend OAuth flow and all API endpoints.

Usage:
    python test_adsense_integration.py
"""

import os
import sys
import django
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

# Django setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User
from sales_revenue.models import PlatformSettings
from rest_framework_simplejwt.tokens import AccessToken


class Colors:
    """Terminal colors for pretty output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class AdSenseIntegrationTest:
    """Complete AdSense integration test suite"""
    
    def __init__(self):
        self.base_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        self.access_token = None
        self.test_results = []
        
    def print_header(self, text):
        """Print a formatted header"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")
        
    def print_test(self, name, status, message=""):
        """Print test result"""
        status_color = Colors.GREEN if status == "PASS" else Colors.RED if status == "FAIL" else Colors.YELLOW
        status_icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        
        print(f"{status_color}{status_icon} {name}{Colors.ENDC}")
        if message:
            print(f"  {Colors.CYAN}→ {message}{Colors.ENDC}")
        
        self.test_results.append({
            'name': name,
            'status': status,
            'message': message
        })
        
    def get_super_admin_token(self):
        """Get access token for SUPER_ADMIN user"""
        try:
            admin = User.objects.filter(role='SUPER_ADMIN').first()
            if not admin:
                self.print_test("Get Super Admin Token", "FAIL", "No SUPER_ADMIN user found")
                return None
                
            token = AccessToken.for_user(admin)
            self.access_token = str(token)
            self.print_test("Get Super Admin Token", "PASS", f"Token for {admin.email}")
            return self.access_token
        except Exception as e:
            self.print_test("Get Super Admin Token", "FAIL", str(e))
            return None
            
    def test_environment_variables(self):
        """Test that all required environment variables are set"""
        self.print_header("ENVIRONMENT CONFIGURATION TEST")
        
        required_vars = {
            'GOOGLE_ADSENSE_CLIENT_ID': os.getenv('GOOGLE_ADSENSE_CLIENT_ID'),
            'GOOGLE_ADSENSE_CLIENT_SECRET': os.getenv('GOOGLE_ADSENSE_CLIENT_SECRET'),
            'GOOGLE_ADSENSE_ACCOUNT_ID': os.getenv('GOOGLE_ADSENSE_ACCOUNT_ID'),
            'BACKEND_URL': os.getenv('BACKEND_URL'),
            'FRONTEND_URL': os.getenv('FRONTEND_URL'),
        }
        
        all_set = True
        for var_name, var_value in required_vars.items():
            if var_value:
                # Mask secrets
                display_value = var_value
                if 'SECRET' in var_name:
                    display_value = var_value[:10] + "..." if len(var_value) > 10 else "***"
                self.print_test(f"Environment: {var_name}", "PASS", display_value)
            else:
                self.print_test(f"Environment: {var_name}", "FAIL", "Not set")
                all_set = False
                
        return all_set
        
    def test_database_configuration(self):
        """Test that PlatformSettings model is ready"""
        self.print_header("DATABASE CONFIGURATION TEST")
        
        try:
            settings = PlatformSettings.get_settings()
            
            # Check if adsense fields exist
            has_token_field = hasattr(settings, 'adsense_oauth_token')
            has_connected_field = hasattr(settings, 'adsense_connected_at')
            
            if has_token_field and has_connected_field:
                self.print_test("Database Schema", "PASS", "PlatformSettings has AdSense fields")
            else:
                self.print_test("Database Schema", "FAIL", "Missing AdSense fields")
                return False
                
            # Check current connection status
            is_connected = bool(settings.adsense_oauth_token)
            if is_connected:
                connected_at = settings.adsense_connected_at
                self.print_test("Current Status", "PASS", 
                    f"Connected since {connected_at.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                self.print_test("Current Status", "WARN", "Not currently connected")
                
            return True
        except Exception as e:
            self.print_test("Database Configuration", "FAIL", str(e))
            return False
            
    def test_api_status_endpoint(self):
        """Test GET /api/admin/adsense/status/"""
        self.print_header("API ENDPOINT TEST: Status")
        
        if not self.access_token:
            self.print_test("Status Endpoint", "FAIL", "No access token")
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.get(f"{self.base_url}/api/admin/adsense/status/", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.print_test("Status Endpoint", "PASS", f"HTTP {response.status_code}")
                
                # Check response structure
                expected_fields = ['is_configured', 'is_connected']
                for field in expected_fields:
                    if field in data:
                        self.print_test(f"  Response field: {field}", "PASS", str(data[field]))
                    else:
                        self.print_test(f"  Response field: {field}", "FAIL", "Missing")
                        
                return True
            else:
                self.print_test("Status Endpoint", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.print_test("Status Endpoint", "FAIL", str(e))
            return False
            
    def test_api_connect_endpoint(self):
        """Test GET /api/admin/adsense/connect/"""
        self.print_header("API ENDPOINT TEST: Connect")
        
        if not self.access_token:
            self.print_test("Connect Endpoint", "FAIL", "No access token")
            return None
            
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.get(f"{self.base_url}/api/admin/adsense/connect/", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.print_test("Connect Endpoint", "PASS", f"HTTP {response.status_code}")
                
                # Check for authorization_url
                if 'authorization_url' in data:
                    auth_url = data['authorization_url']
                    self.print_test("  Authorization URL", "PASS", "Generated successfully")
                    
                    # Parse and validate URL
                    parsed = urlparse(auth_url)
                    query_params = parse_qs(parsed.query)
                    
                    # Check OAuth parameters
                    oauth_params = {
                        'response_type': 'code',
                        'client_id': os.getenv('GOOGLE_ADSENSE_CLIENT_ID'),
                        'redirect_uri': f"{self.base_url}/api/admin/adsense/callback/",
                        'scope': 'https://www.googleapis.com/auth/adsense.readonly',
                    }
                    
                    for param, expected_value in oauth_params.items():
                        if param in query_params:
                            actual_value = query_params[param][0]
                            if expected_value and actual_value == expected_value:
                                self.print_test(f"    OAuth param: {param}", "PASS", "Correct")
                            elif expected_value:
                                self.print_test(f"    OAuth param: {param}", "FAIL", 
                                    f"Expected {expected_value}, got {actual_value}")
                            else:
                                self.print_test(f"    OAuth param: {param}", "PASS", "Present")
                        else:
                            self.print_test(f"    OAuth param: {param}", "FAIL", "Missing")
                            
                    # Check state parameter
                    if 'state' in query_params:
                        state = query_params['state'][0]
                        self.print_test("    OAuth param: state", "PASS", f"Generated: {state}")
                    else:
                        self.print_test("    OAuth param: state", "FAIL", "Missing")
                        
                    return auth_url
                else:
                    self.print_test("  Authorization URL", "FAIL", "Not in response")
                    return None
            else:
                self.print_test("Connect Endpoint", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return None
        except Exception as e:
            self.print_test("Connect Endpoint", "FAIL", str(e))
            return None
            
    def test_api_disconnect_endpoint(self):
        """Test POST /api/admin/adsense/disconnect/"""
        self.print_header("API ENDPOINT TEST: Disconnect")
        
        if not self.access_token:
            self.print_test("Disconnect Endpoint", "FAIL", "No access token")
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.post(f"{self.base_url}/api/admin/adsense/disconnect/", headers=headers)
            
            if response.status_code in [200, 204]:
                self.print_test("Disconnect Endpoint", "PASS", f"HTTP {response.status_code}")
                return True
            elif response.status_code == 400:
                # Not connected is okay for testing
                data = response.json()
                self.print_test("Disconnect Endpoint", "WARN", 
                    f"Not connected (expected if testing fresh setup)")
                return True
            else:
                self.print_test("Disconnect Endpoint", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.print_test("Disconnect Endpoint", "FAIL", str(e))
            return False
            
    def test_api_earnings_endpoint(self):
        """Test GET /api/admin/adsense/earnings/"""
        self.print_header("API ENDPOINT TEST: Earnings (requires connection)")
        
        if not self.access_token:
            self.print_test("Earnings Endpoint", "FAIL", "No access token")
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.get(f"{self.base_url}/api/admin/adsense/earnings/", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.print_test("Earnings Endpoint", "PASS", f"HTTP {response.status_code}")
                
                # Check response structure
                if 'earnings' in data and data['earnings']:
                    earnings = data['earnings']
                    for period, value in earnings.items():
                        self.print_test(f"  Earnings: {period}", "PASS", str(value))
                else:
                    self.print_test("  Earnings data", "WARN", "No earnings (expected if not connected)")
                return True
            elif response.status_code == 400:
                self.print_test("Earnings Endpoint", "WARN", "Not connected (expected)")
                return True
            else:
                self.print_test("Earnings Endpoint", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.print_test("Earnings Endpoint", "FAIL", str(e))
            return False
            
    def test_callback_redirect_behavior(self):
        """Test that callback endpoint redirects to frontend"""
        self.print_header("CALLBACK REDIRECT TEST")
        
        # Test error scenarios (no authorization needed for these)
        test_cases = [
            {
                'name': 'Access Denied',
                'params': '?error=access_denied',
                'expected_redirect': f"{self.frontend_url}/admin/revenue/adsense/setup?error=access_denied"
            },
            {
                'name': 'Missing Parameters',
                'params': '',
                'expected_redirect': f"{self.frontend_url}/admin/revenue/adsense/setup?error=missing_params"
            },
        ]
        
        for test_case in test_cases:
            try:
                url = f"{self.base_url}/api/admin/adsense/callback/{test_case['params']}"
                response = requests.get(url, allow_redirects=False)
                
                if response.status_code in [301, 302, 303, 307, 308]:
                    redirect_location = response.headers.get('Location', '')
                    
                    if redirect_location.startswith(test_case['expected_redirect'].split('?')[0]):
                        self.print_test(f"Callback Redirect: {test_case['name']}", "PASS", 
                            f"Redirects to frontend")
                    else:
                        self.print_test(f"Callback Redirect: {test_case['name']}", "FAIL", 
                            f"Wrong redirect: {redirect_location}")
                else:
                    self.print_test(f"Callback Redirect: {test_case['name']}", "FAIL", 
                        f"HTTP {response.status_code} (expected 30x)")
            except Exception as e:
                self.print_test(f"Callback Redirect: {test_case['name']}", "FAIL", str(e))
                
    def test_oauth_flow_instructions(self, auth_url):
        """Print manual OAuth flow testing instructions"""
        self.print_header("MANUAL OAUTH FLOW TEST")
        
        if not auth_url:
            self.print_test("OAuth Flow", "SKIP", "No authorization URL available")
            return
            
        print(f"{Colors.CYAN}To test the complete OAuth flow:{Colors.ENDC}\n")
        print(f"{Colors.BOLD}1. Open this URL in your browser:{Colors.ENDC}")
        print(f"{Colors.BLUE}{auth_url}{Colors.ENDC}\n")
        
        print(f"{Colors.BOLD}2. Sign in with Google account: juliustetteh@gmail.com{Colors.ENDC}\n")
        
        print(f"{Colors.BOLD}3. Grant permissions{Colors.ENDC}\n")
        
        print(f"{Colors.BOLD}4. Expected flow:{Colors.ENDC}")
        print(f"   • Google redirects to: {Colors.BLUE}{self.base_url}/api/admin/adsense/callback/?code=...&state=...{Colors.ENDC}")
        print(f"   • Backend exchanges code for token")
        print(f"   • Backend redirects to: {Colors.GREEN}{self.frontend_url}/admin/revenue/adsense/setup?success=true{Colors.ENDC}\n")
        
        print(f"{Colors.BOLD}5. Frontend should:{Colors.ENDC}")
        print(f"   • Detect ?success=true in URL")
        print(f"   • Show toast: '🎉 AdSense connected successfully!'")
        print(f"   • Reload connection status")
        print(f"   • Clean URL (remove query params)\n")
        
        print(f"{Colors.YELLOW}Note: OAuth state expires in 10 minutes. Generate fresh URL if needed.{Colors.ENDC}\n")
        
    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.test_results if r['status'] == 'WARN')
        total = len(self.test_results)
        
        print(f"Total Tests: {Colors.BOLD}{total}{Colors.ENDC}")
        print(f"Passed: {Colors.GREEN}{passed}{Colors.ENDC}")
        print(f"Failed: {Colors.RED}{failed}{Colors.ENDC}")
        print(f"Warnings: {Colors.YELLOW}{warnings}{Colors.ENDC}\n")
        
        if failed == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ All critical tests passed!{Colors.ENDC}\n")
            print(f"{Colors.CYAN}Ready for OAuth testing. Use the authorization URL above.{Colors.ENDC}\n")
        else:
            print(f"{Colors.RED}{Colors.BOLD}✗ Some tests failed. Please review the errors above.{Colors.ENDC}\n")
            
    def run_all_tests(self):
        """Run all integration tests"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("╔" + "═" * 78 + "╗")
        print("║" + "Google AdSense Integration Test Suite".center(78) + "║")
        print("║" + f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(78) + "║")
        print("╚" + "═" * 78 + "╝")
        print(f"{Colors.ENDC}")
        
        # Run tests in order
        self.test_environment_variables()
        self.test_database_configuration()
        
        # Get access token
        if not self.get_super_admin_token():
            print(f"\n{Colors.RED}Cannot proceed without access token. Create SUPER_ADMIN user first.{Colors.ENDC}")
            return
            
        # Test API endpoints
        self.test_api_status_endpoint()
        auth_url = self.test_api_connect_endpoint()
        self.test_api_disconnect_endpoint()
        self.test_api_earnings_endpoint()
        
        # Test callback behavior
        self.test_callback_redirect_behavior()
        
        # Print OAuth instructions
        self.test_oauth_flow_instructions(auth_url)
        
        # Summary
        self.print_summary()
        

if __name__ == '__main__':
    tester = AdSenseIntegrationTest()
    tester.run_all_tests()
