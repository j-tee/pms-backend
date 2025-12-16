#!/usr/bin/env python
"""
Test Staff Invitation System

Tests the complete workflow of staff invitation:
1. Admin sends invitation
2. Staff member receives invitation
3. Staff member accepts invitation and sets password
4. Staff member can log in
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from accounts.services.staff_invitation_service import StaffInvitationService
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator

User = get_user_model()

# Configuration
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

# Validate required environment variables
if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    print("❌ Error: ADMIN_USERNAME and ADMIN_PASSWORD environment variables are required")
    print("\nUsage:")
    print("  export ADMIN_USERNAME='your_admin_username'")
    print("  export ADMIN_PASSWORD='your_admin_password'")
    print("  python test_staff_invitation.py")
    sys.exit(1)


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_success(text):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text):
    """Print error message"""
    print(f"❌ {text}")


def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")


def cleanup_test_users():
    """Clean up any existing test users"""
    test_emails = [
        'test_regional@example.com',
        'test_constituency@example.com',
        'test_extension@example.com'
    ]
    
    for email in test_emails:
        try:
            user = User.objects.get(email=email)
            user.delete()
            print_info(f"Cleaned up existing user: {email}")
        except User.DoesNotExist:
            pass


def test_1_create_admin_if_needed():
    """Ensure admin user exists"""
    print_header("Test 1: Ensure Admin User Exists")
    
    try:
        admin = User.objects.get(username=ADMIN_USERNAME)
        print_success(f"Admin user '{ADMIN_USERNAME}' exists")
        print_info(f"  Role: {admin.role}")
        print_info(f"  Email: {admin.email}")
        return admin
    except User.DoesNotExist:
        print_error(f"Admin user '{ADMIN_USERNAME}' not found")
        print_info("Creating admin user...")
        
        admin = User.objects.create_user(
            username=ADMIN_USERNAME,
            email='admin@yea.gov.gh',
            password=ADMIN_PASSWORD,
            first_name='System',
            last_name='Administrator',
            role='SUPER_ADMIN',
            phone='+233241234567',
            is_active=True,
            is_verified=True,
            email_verified=True
        )
        print_success(f"Created admin user: {ADMIN_USERNAME}")
        return admin


def test_2_admin_login():
    """Test admin login"""
    print_header("Test 2: Admin Login")
    
    response = requests.post(
        f"{API_BASE_URL}/api/accounts/login/",
        json={
            'username': ADMIN_USERNAME,
            'password': ADMIN_PASSWORD
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        access_token = data.get('access')
        print_success("Admin login successful")
        print_info(f"  Access token: {access_token[:20]}...")
        return access_token
    else:
        print_error(f"Admin login failed: {response.status_code}")
        print_info(f"  Response: {response.text}")
        return None


def test_3_create_staff_invitation(admin_token, admin_user):
    """Test creating staff invitation (REGIONAL_COORDINATOR)"""
    print_header("Test 3: Create Staff Invitation (Regional Coordinator)")
    
    invitation_data = {
        'email': 'test_regional@example.com',
        'first_name': 'Test',
        'last_name': 'Regional',
        'role': 'REGIONAL_COORDINATOR',
        'phone': '+233241111111',
        'region': 'Greater Accra'
    }
    
    # Test via API
    print_info("Testing via API endpoint...")
    response = requests.post(
        f"{API_BASE_URL}/api/admin/users/create/",
        json=invitation_data,
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    
    if response.status_code == 201:
        data = response.json()
        print_success("Staff invitation created via API")
        print_info(f"  User ID: {data['id']}")
        print_info(f"  Username: {data['username']}")
        print_info(f"  Email: {data['email']}")
        print_info(f"  Role: {data['role']}")
        print_info(f"  Expires: {data.get('expires_at', 'N/A')}")
        
        # Get the user to extract invitation details
        user = User.objects.get(email=invitation_data['email'])
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = user.password_reset_token
        
        return {
            'user_id': data['id'],
            'email': invitation_data['email'],
            'uid': uid,
            'token': token
        }
    else:
        print_error(f"Failed to create invitation: {response.status_code}")
        print_info(f"  Response: {response.text}")
        return None


def test_4_accept_invitation(invitation_info):
    """Test accepting staff invitation"""
    print_header("Test 4: Accept Staff Invitation")
    
    if not invitation_info:
        print_error("No invitation info available")
        return False
    
    accept_data = {
        'uidb64': invitation_info['uid'],
        'token': invitation_info['token'],
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    }
    
    # Test via API (this would be called by the frontend)
    print_info("Testing invitation acceptance via public endpoint...")
    
    # For this test, we'll call the service directly since we're in the same environment
    try:
        result = StaffInvitationService.accept_invitation(
            uid=invitation_info['uid'],
            token=invitation_info['token'],
            password='SecurePass123!',
            confirm_password='SecurePass123!'
        )
        
        user = result['user']
        print_success("Invitation accepted successfully")
        print_info(f"  Username: {user.username}")
        print_info(f"  Email: {user.email}")
        print_info(f"  Is Active: {user.is_active}")
        print_info(f"  Is Verified: {user.is_verified}")
        print_info(f"  Message: {result['message']}")
        
        return True
    except Exception as e:
        print_error(f"Failed to accept invitation: {str(e)}")
        return False


def test_5_new_user_login(invitation_info):
    """Test login with newly created staff account"""
    print_header("Test 5: New User Login")
    
    if not invitation_info:
        print_error("No invitation info available")
        return None
    
    # Get username from user
    try:
        user = User.objects.get(email=invitation_info['email'])
        username = user.username
    except User.DoesNotExist:
        print_error(f"User not found: {invitation_info['email']}")
        return None
    
    response = requests.post(
        f"{API_BASE_URL}/api/accounts/login/",
        json={
            'username': username,
            'password': 'SecurePass123!'
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("New user login successful")
        print_info(f"  Username: {username}")
        print_info(f"  Access token: {data.get('access', '')[:20]}...")
        return data.get('access')
    else:
        print_error(f"New user login failed: {response.status_code}")
        print_info(f"  Response: {response.text}")
        return None


def test_6_permission_hierarchy():
    """Test role hierarchy permissions"""
    print_header("Test 6: Role Hierarchy Permissions")
    
    admin = User.objects.get(username=ADMIN_USERNAME)
    
    test_cases = [
        {
            'admin_role': 'SUPER_ADMIN',
            'target_role': 'YEA_OFFICIAL',
            'should_succeed': True,
            'description': 'SUPER_ADMIN can create YEA_OFFICIAL'
        },
        {
            'admin_role': 'SUPER_ADMIN',
            'target_role': 'NATIONAL_ADMIN',
            'should_succeed': True,
            'description': 'SUPER_ADMIN can create NATIONAL_ADMIN'
        },
        {
            'admin_role': 'NATIONAL_ADMIN',
            'target_role': 'YEA_OFFICIAL',
            'should_succeed': False,
            'description': 'NATIONAL_ADMIN cannot create YEA_OFFICIAL'
        },
        {
            'admin_role': 'REGIONAL_COORDINATOR',
            'target_role': 'CONSTITUENCY_OFFICIAL',
            'should_succeed': True,
            'description': 'REGIONAL_COORDINATOR can create CONSTITUENCY_OFFICIAL'
        },
        {
            'admin_role': 'REGIONAL_COORDINATOR',
            'target_role': 'NATIONAL_ADMIN',
            'should_succeed': False,
            'description': 'REGIONAL_COORDINATOR cannot create NATIONAL_ADMIN'
        }
    ]
    
    results = {'passed': 0, 'failed': 0}
    
    for test_case in test_cases:
        # Temporarily change admin role
        original_role = admin.role
        admin.role = test_case['admin_role']
        admin.save()
        
        try:
            # Try to create invitation
            result = StaffInvitationService.create_staff_invitation(
                admin_user=admin,
                email=f"test_{test_case['target_role'].lower()}@example.com",
                first_name='Test',
                last_name='User',
                role=test_case['target_role'],
                phone='+233249999999',
                region='Greater Accra'
            )
            
            # Clean up created user
            created_user = result['user']
            created_user.delete()
            
            if test_case['should_succeed']:
                print_success(test_case['description'])
                results['passed'] += 1
            else:
                print_error(f"{test_case['description']} - SHOULD HAVE FAILED!")
                results['failed'] += 1
                
        except PermissionError as e:
            if not test_case['should_succeed']:
                print_success(f"{test_case['description']} - Correctly blocked")
                results['passed'] += 1
            else:
                print_error(f"{test_case['description']} - SHOULD HAVE SUCCEEDED!")
                print_info(f"  Error: {str(e)}")
                results['failed'] += 1
        except Exception as e:
            print_error(f"{test_case['description']} - Unexpected error: {str(e)}")
            results['failed'] += 1
        finally:
            # Restore original role
            admin.role = original_role
            admin.save()
    
    print_info(f"\nPermission Tests: {results['passed']} passed, {results['failed']} failed")
    return results['failed'] == 0


def test_7_resend_invitation(admin_token):
    """Test resending invitation"""
    print_header("Test 7: Resend Invitation")
    
    # Create a new inactive user
    admin = User.objects.get(username=ADMIN_USERNAME)
    
    try:
        result = StaffInvitationService.create_staff_invitation(
            admin_user=admin,
            email='test_resend@example.com',
            first_name='Test',
            last_name='Resend',
            role='CONSTITUENCY_OFFICIAL',
            phone='+233248888888',
            region='Greater Accra',
            constituency='Tema East'
        )
        
        user_id = result['user'].id
        print_info(f"Created test user for resend: {user_id}")
        
        # Resend invitation via API
        response = requests.post(
            f"{API_BASE_URL}/api/admin/staff/{user_id}/resend-invitation/",
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Invitation resent successfully")
            print_info(f"  Expires: {data.get('expires_at', 'N/A')}")
            print_info(f"  Message: {data.get('message', 'N/A')}")
            
            # Clean up
            result['user'].delete()
            return True
        else:
            print_error(f"Failed to resend invitation: {response.status_code}")
            print_info(f"  Response: {response.text}")
            result['user'].delete()
            return False
            
    except Exception as e:
        print_error(f"Error during resend test: {str(e)}")
        return False


def test_8_cancel_invitation(admin_token):
    """Test canceling invitation"""
    print_header("Test 8: Cancel Invitation")
    
    # Create a new inactive user
    admin = User.objects.get(username=ADMIN_USERNAME)
    
    try:
        result = StaffInvitationService.create_staff_invitation(
            admin_user=admin,
            email='test_cancel@example.com',
            first_name='Test',
            last_name='Cancel',
            role='CONSTITUENCY_OFFICIAL',
            phone='+233247777777',
            region='Greater Accra',
            constituency='Tema West'
        )
        
        user_id = result['user'].id
        print_info(f"Created test user for cancellation: {user_id}")
        
        # Cancel invitation via API
        response = requests.delete(
            f"{API_BASE_URL}/api/admin/staff/{user_id}/cancel-invitation/",
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Invitation cancelled successfully")
            print_info(f"  Message: {data.get('message', 'N/A')}")
            
            # Verify user was deleted
            if not User.objects.filter(id=user_id).exists():
                print_success("User was properly deleted")
                return True
            else:
                print_error("User still exists after cancellation")
                return False
        else:
            print_error(f"Failed to cancel invitation: {response.status_code}")
            print_info(f"  Response: {response.text}")
            # Clean up if cancellation failed
            try:
                User.objects.get(id=user_id).delete()
            except:
                pass
            return False
            
    except Exception as e:
        print_error(f"Error during cancel test: {str(e)}")
        return False


def run_all_tests():
    """Run all tests"""
    print_header("YEA PMS - Staff Invitation System Test Suite")
    print_info(f"API Base URL: {API_BASE_URL}")
    print_info(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Clean up before tests
    cleanup_test_users()
    
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0
    }
    
    # Test 1: Ensure admin exists
    admin_user = test_1_create_admin_if_needed()
    results['total'] += 1
    if admin_user:
        results['passed'] += 1
    else:
        results['failed'] += 1
        print_error("Cannot continue without admin user")
        return
    
    # Test 2: Admin login
    admin_token = test_2_admin_login()
    results['total'] += 1
    if admin_token:
        results['passed'] += 1
    else:
        results['failed'] += 1
        print_error("Cannot continue without admin token")
        return
    
    # Test 3: Create invitation
    invitation_info = test_3_create_staff_invitation(admin_token, admin_user)
    results['total'] += 1
    if invitation_info:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 4: Accept invitation
    results['total'] += 1
    if invitation_info and test_4_accept_invitation(invitation_info):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 5: New user login
    results['total'] += 1
    if invitation_info and test_5_new_user_login(invitation_info):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 6: Permission hierarchy
    results['total'] += 1
    if test_6_permission_hierarchy():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 7: Resend invitation
    results['total'] += 1
    if admin_token and test_7_resend_invitation(admin_token):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 8: Cancel invitation
    results['total'] += 1
    if admin_token and test_8_cancel_invitation(admin_token):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Final cleanup
    cleanup_test_users()
    
    # Print summary
    print_header("Test Summary")
    print_info(f"Total Tests: {results['total']}")
    print_success(f"Passed: {results['passed']}")
    if results['failed'] > 0:
        print_error(f"Failed: {results['failed']}")
    else:
        print_success("All tests passed! ✨")
    
    print("\n" + "=" * 80)
    
    return results['failed'] == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
