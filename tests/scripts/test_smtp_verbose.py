import os
import sys
import django
import logging

# Setup Django environment FIRST
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

# Enable verbose logging for email
logging.basicConfig(level=logging.DEBUG)

def test_smtp_verbose():
    print("=" * 70)
    print("VERBOSE SMTP EMAIL TEST")
    print("=" * 70)
    print()
    print("Email Configuration:")
    print(f"  Backend: {settings.EMAIL_BACKEND}")
    print(f"  Host: {settings.EMAIL_HOST}")
    print(f"  Port: {settings.EMAIL_PORT}")
    print(f"  Use TLS: {settings.EMAIL_USE_TLS}")
    print(f"  Username: {settings.EMAIL_HOST_USER}")
    print(f"  From: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    recipient = "juliustetteh@gmail.com"
    
    print(f"Attempting to send email to: {recipient}")
    print("Watch for SMTP transaction details below...")
    print("-" * 70)
    
    try:
        result = send_mail(
            subject='Password Reset Test - YEA PMS',
            message='''
Hello,

This is a test email to verify password reset functionality.

If you receive this email, it means the SMTP configuration is working correctly.

Best regards,
YEA PMS Team
            ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        
        print("-" * 70)
        print(f"\nSUCCESS: Email sent! Return value: {result}")
        print()
        print("Next Steps:")
        print("1. Check inbox for juliustetteh@gmail.com")
        print("2. Check spam/junk folder")
        print("3. Check Gmail's 'All Mail' folder")
        print("4. If still not received, check Gmail security settings:")
        print("   - Go to https://myaccount.google.com/security")
        print("   - Check for blocked sign-in attempts")
        print("   - Consider using an App Password instead")
        print()
        
    except Exception as e:
        print("-" * 70)
        print(f"\nFAILURE: Error sending email")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        print()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_smtp_verbose()
