import os
import sys
import django

# Setup Django environment FIRST
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from accounts.auth_services import PasswordResetService

User = get_user_model()

def test_frontend_url():
    print("=" * 70)
    print("FRONTEND_URL Configuration Test")
    print("=" * 70)
    print()
    
    print(f"FRONTEND_URL from settings: {settings.FRONTEND_URL}")
    print()
    
    # Create a test user
    email = "url_test@example.com"
    User.objects.filter(email=email).delete()
    user = User.objects.create_user(
        username="url_test",
        email=email,
        password="TestPassword123!",
        first_name="URL",
        last_name="Test",
        phone="+233244999888"
    )
    
    # Generate password reset token
    print("Generating password reset token...")
    token = PasswordResetService.generate_reset_token()
    
    # Build the reset URL (same logic as in auth_services.py)
    reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"
    
    print(f"Password reset URL: {reset_url}")
    print()
    
    # Verify it uses the correct port
    if "localhost:5175" in reset_url or "localhost:5173" in reset_url:
        print("✅ SUCCESS: URL uses correct frontend port (5175 or 5173)")
    elif "localhost:3000" in reset_url:
        print("❌ FAILURE: URL still uses old port 3000")
        print("   Please restart the Django server to pick up environment changes")
    else:
        print(f"⚠️  WARNING: URL uses unexpected host: {reset_url}")
    
    print()
    print("Note: If you just changed .env.development, you need to restart")
    print("      the Django development server for changes to take effect.")
    
    # Clean up
    user.delete()

if __name__ == "__main__":
    test_frontend_url()
