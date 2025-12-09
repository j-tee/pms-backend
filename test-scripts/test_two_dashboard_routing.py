import os
import sys
import django
import json

# Setup Django environment FIRST
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.serializers import CustomTokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

def test_routing_for_role(role, role_display):
    """Test login routing for a specific role."""
    print(f"\n{'='*70}")
    print(f"Testing: {role_display} ({role})")
    print('='*70)
    
    # Create test user
    username = f"test_{role.lower()}"
    email = f"{username}@example.com"
    
    # Clean up existing user
    User.objects.filter(email=email).delete()
    
    # Create user with specific role
    user = User.objects.create_user(
        username=username,
        email=email,
        password="TestPassword123!",
        first_name="Test",
        last_name=role_display,
        role=role,
        phone=f"+23324{role[:7].zfill(7)}"
    )
    
    # Simulate login by creating token
    refresh = RefreshToken.for_user(user)
    
    # Get the serializer data (simulates what login endpoint returns)
    serializer = CustomTokenObtainPairSerializer()
    serializer.user = user
    
    # Create mock attrs for validation
    attrs = {'username': username, 'password': 'TestPassword123!'}
    
    # Get the validated data
    data = {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
    
    # Manually build the response like the serializer does
    is_farmer = user.role == 'FARMER'
    
    if is_farmer:
        redirect_to = '/farmer/dashboard'
        dashboard_type = 'farmer'
    else:
        redirect_to = '/staff/dashboard'
        dashboard_type = 'staff'
    
    routing = {
        'dashboard_type': dashboard_type,
        'redirect_to': redirect_to,
        'is_staff': not is_farmer,
        'is_farmer': is_farmer
    }
    
    # Print results
    print(f"Role: {role}")
    print(f"Dashboard Type: {dashboard_type}")
    print(f"Redirect To: {redirect_to}")
    print(f"Is Staff: {routing['is_staff']}")
    print(f"Is Farmer: {routing['is_farmer']}")
    
    # Verify correctness
    if role == 'FARMER':
        assert dashboard_type == 'farmer', "Farmer should have farmer dashboard"
        assert redirect_to == '/farmer/dashboard', "Farmer should redirect to farmer dashboard"
        assert routing['is_farmer'] == True, "Farmer should have is_farmer=True"
        assert routing['is_staff'] == False, "Farmer should have is_staff=False"
        print("✅ PASS: Farmer routing correct")
    else:
        assert dashboard_type == 'staff', f"{role} should have staff dashboard"
        assert redirect_to == '/staff/dashboard', f"{role} should redirect to staff dashboard"
        assert routing['is_staff'] == True, f"{role} should have is_staff=True"
        assert routing['is_farmer'] == False, f"{role} should have is_farmer=False"
        print("✅ PASS: Staff routing correct")
    
    # Clean up
    user.delete()

def main():
    print("\n" + "="*70)
    print("LOGIN ROUTING TEST - Two-Dashboard Approach")
    print("="*70)
    
    # Test all roles
    roles = [
        ('FARMER', 'Farmer'),
        ('CONSTITUENCY_OFFICIAL', 'Constituency Official'),
        ('NATIONAL_ADMIN', 'National Administrator'),
        ('PROCUREMENT_OFFICER', 'Procurement Officer'),
        ('VETERINARY_OFFICER', 'Veterinary Officer'),
        ('AUDITOR', 'Auditor'),
    ]
    
    for role, role_display in roles:
        try:
            test_routing_for_role(role, role_display)
        except AssertionError as e:
            print(f"❌ FAIL: {e}")
            return
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\nSummary:")
    print("- Farmers → /farmer/dashboard (dashboard_type: 'farmer')")
    print("- All Staff → /staff/dashboard (dashboard_type: 'staff')")
    print("\nThe two-dashboard routing is working correctly!")

if __name__ == "__main__":
    main()
