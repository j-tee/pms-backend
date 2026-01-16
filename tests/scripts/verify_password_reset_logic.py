import os
import sys
import django
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.auth_services import PasswordResetService

User = get_user_model()

def verify_password_reset():
    print("Starting Password Reset Verification...")
    
    # 1. Create a test user
    email = "reset_test@example.com"
    password = "InitialPassword123!"
    
    # Clean up existing user if any
    User.objects.filter(email=email).delete()
    
    user = User.objects.create_user(
        username="reset_test",
        email=email,
        password=password,
        first_name="Reset",
        last_name="Test"
    )
    print(f"Created test user: {user.email}")
    
    # 2. Generate and send reset token
    print("\nTesting send_password_reset_email...")
    try:
        token = PasswordResetService.send_password_reset_email(user)
        print(f"Token generated: {token}")
        
        # Refresh user from db
        user.refresh_from_db()
        
        if user.password_reset_token == token:
            print("SUCCESS: Token stored on user.")
        else:
            print(f"FAILURE: Token mismatch. Expected {token}, got {user.password_reset_token}")
            return
            
        if user.password_reset_token_expires > timezone.now():
            print("SUCCESS: Token expiration set correctly.")
        else:
            print("FAILURE: Token already expired or not set correctly.")
            return
            
    except Exception as e:
        print(f"FAILURE: Exception during send_password_reset_email: {e}")
        return

    # 3. Verify token
    print("\nTesting verify_reset_token...")
    verified_user, error = PasswordResetService.verify_reset_token(token)
    
    if verified_user == user:
        print("SUCCESS: Token verified successfully.")
    else:
        print(f"FAILURE: Token verification failed. Error: {error}")
        return
        
    # 4. Reset password
    print("\nTesting reset_password...")
    new_password = "NewPassword456!"
    success, error = PasswordResetService.reset_password(token, new_password)
    
    if success:
        print("SUCCESS: Password reset function returned success.")
    else:
        print(f"FAILURE: Password reset failed. Error: {error}")
        return
        
    # 5. Verify new password works
    user.refresh_from_db()
    if user.check_password(new_password):
        print("SUCCESS: User can login with new password.")
    else:
        print("FAILURE: New password check failed.")
        return
        
    # 6. Verify old password fails
    if not user.check_password(password):
        print("SUCCESS: Old password no longer works.")
    else:
        print("FAILURE: Old password still works!")
        return
        
    # 7. Verify token is cleared
    if user.password_reset_token is None:
        print("SUCCESS: Token cleared after reset.")
    else:
        print("FAILURE: Token not cleared after reset.")
        return

    print("\nVERIFICATION COMPLETE: All checks passed!")

if __name__ == "__main__":
    verify_password_reset()
