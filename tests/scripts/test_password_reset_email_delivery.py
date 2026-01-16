import os
import sys
import django

# Setup Django environment FIRST
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.auth_services import PasswordResetService
from django.conf import settings

User = get_user_model()

def test_password_reset_email():
    print("Testing Password Reset Email Delivery...")
    print(f"Email Backend: {settings.EMAIL_BACKEND}")
    print(f"Email Host: {settings.EMAIL_HOST}")
    print(f"Email From: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    email = "juliustetteh@gmail.com"
    
    # Check if user exists
    print(f"Checking if user with email '{email}' exists...")
    try:
        user = User.objects.get(email=email)
        print(f"SUCCESS: User found - {user.username} ({user.get_full_name()})")
        print(f"User ID: {user.id}")
        print(f"User is active: {user.is_active}")
        print()
    except User.DoesNotExist:
        print(f"FAILURE: No user found with email '{email}'")
        print("Creating a test user...")
        user = User.objects.create_user(
            username="julius_test",
            email=email,
            password="TestPassword123!",
            first_name="Julius",
            last_name="Tetteh",
            phone="+233244567890"
        )
        print(f"SUCCESS: Test user created - {user.username}")
        print()
    
    # Send password reset email
    print(f"Sending password reset email to {email}...")
    try:
        token = PasswordResetService.send_password_reset_email(user)
        print(f"SUCCESS: Password reset email sent!")
        print(f"Token generated: {token}")
        print()
        
        # Refresh user to check token was saved
        user.refresh_from_db()
        print(f"Token saved on user: {user.password_reset_token}")
        print(f"Token expires at: {user.password_reset_token_expires}")
        print()
        
        print("=" * 70)
        print("IMPORTANT: Check the following:")
        print("1. Check your email inbox for juliustetteh@gmail.com")
        print("2. Check spam/junk folder")
        print("3. If using Gmail SMTP, ensure 'Less secure app access' is enabled")
        print("   OR use an App Password instead of your regular password")
        print("4. Check if Gmail is blocking the email due to security settings")
        print("=" * 70)
        
    except Exception as e:
        print(f"FAILURE: Error sending email: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_password_reset_email()
