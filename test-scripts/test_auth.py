#!/usr/bin/env python
"""
Test script for authentication and authorization endpoints
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_AUTH = f"{BASE_URL}/api/auth"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_response(response, title="Response"):
    """Pretty print response"""
    print(f"\n{title}:")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response Text: {response.text[:500]}")

# Test data
test_user = {
    "username": "testfarmer",
    "email": "testfarmer@example.com",
    "password": "TestPass123!@#",
    "password_confirm": "TestPass123!@#",
    "first_name": "Test",
    "last_name": "Farmer",
    "phone": "+233240000000",
    "role": "FARMER"
}

print_section("TESTING AUTHENTICATION & AUTHORIZATION")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Base URL: {BASE_URL}")

# Test 1: User Registration
print_section("TEST 1: User Registration")
print(f"POST {API_AUTH}/register/")
print(f"Data: {json.dumps({k: v for k, v in test_user.items() if k != 'password'}, indent=2)}")

response = requests.post(
    f"{API_AUTH}/register/",
    json=test_user,
    headers={"Content-Type": "application/json"}
)
print_response(response, "Registration Response")

# Test 2: Login with created user
print_section("TEST 2: User Login (JWT)")
login_data = {
    "username": test_user["username"],
    "password": test_user["password"]
}
print(f"POST {API_AUTH}/login/")
print(f"Data: {json.dumps({'username': login_data['username'], 'password': '***'}, indent=2)}")

response = requests.post(
    f"{API_AUTH}/login/",
    json=login_data,
    headers={"Content-Type": "application/json"}
)
print_response(response, "Login Response")

# Store tokens if login successful
access_token = None
refresh_token = None
if response.status_code == 200:
    tokens = response.json()
    access_token = tokens.get('access')
    refresh_token = tokens.get('refresh')
    print(f"\n✓ Access Token: {access_token[:50]}...")
    print(f"✓ Refresh Token: {refresh_token[:50]}...")

# Test 3: Access Profile (Authenticated)
if access_token:
    print_section("TEST 3: Get User Profile (Authenticated)")
    print(f"GET {API_AUTH}/profile/")
    print("Headers: Authorization: Bearer <token>")
    
    response = requests.get(
        f"{API_AUTH}/profile/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    print_response(response, "Profile Response")

# Test 4: Access Profile without token (Should fail)
print_section("TEST 4: Get User Profile (Unauthenticated - Should Fail)")
print(f"GET {API_AUTH}/profile/")
print("Headers: No Authorization header")

response = requests.get(
    f"{API_AUTH}/profile/",
    headers={"Content-Type": "application/json"}
)
print_response(response, "Profile Response (Should be 401 Unauthorized)")

# Test 5: Refresh Token
if refresh_token:
    print_section("TEST 5: Refresh Access Token")
    print(f"POST {API_AUTH}/token/refresh/")
    print("Data: {refresh: <refresh_token>}")
    
    response = requests.post(
        f"{API_AUTH}/token/refresh/",
        json={"refresh": refresh_token},
        headers={"Content-Type": "application/json"}
    )
    print_response(response, "Token Refresh Response")
    
    if response.status_code == 200:
        new_access = response.json().get('access')
        print(f"\n✓ New Access Token: {new_access[:50]}...")

# Test 6: Change Password
if access_token:
    print_section("TEST 6: Change Password")
    print(f"POST {API_AUTH}/change-password/")
    
    password_data = {
        "old_password": test_user["password"],
        "new_password": "NewTestPass123!@#",
        "new_password_confirm": "NewTestPass123!@#"
    }
    
    response = requests.post(
        f"{API_AUTH}/change-password/",
        json=password_data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    print_response(response, "Change Password Response")

# Test 7: Login with new password
if access_token:
    print_section("TEST 7: Login with New Password")
    print(f"POST {API_AUTH}/login/")
    
    new_login_data = {
        "username": test_user["username"],
        "password": "NewTestPass123!@#"
    }
    
    response = requests.post(
        f"{API_AUTH}/login/",
        json=new_login_data,
        headers={"Content-Type": "application/json"}
    )
    print_response(response, "Login with New Password Response")
    
    if response.status_code == 200:
        access_token = response.json().get('access')

# Test 8: Logout
if access_token:
    print_section("TEST 8: Logout")
    print(f"POST {API_AUTH}/logout/")
    
    response = requests.post(
        f"{API_AUTH}/logout/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    print_response(response, "Logout Response")

# Test 9: Try to access profile after logout
if access_token:
    print_section("TEST 9: Access Profile After Logout (Should Fail)")
    print(f"GET {API_AUTH}/profile/")
    
    response = requests.get(
        f"{API_AUTH}/profile/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    print_response(response, "Profile Response After Logout")

print_section("TEST SUMMARY")
print("✓ All authentication tests completed!")
print("\nEndpoints tested:")
print("  1. POST /api/auth/register/ - User Registration")
print("  2. POST /api/auth/login/ - User Login (JWT)")
print("  3. GET  /api/auth/profile/ - Get User Profile (Authenticated)")
print("  4. GET  /api/auth/profile/ - Unauthenticated Access")
print("  5. POST /api/auth/token/refresh/ - Refresh Access Token")
print("  6. POST /api/auth/change-password/ - Change Password")
print("  7. POST /api/auth/login/ - Login with New Password")
print("  8. POST /api/auth/logout/ - Logout")
print("  9. GET  /api/auth/profile/ - Access After Logout")
print("\n" + "=" * 70 + "\n")
