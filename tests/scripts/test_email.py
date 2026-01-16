import os
import sys
import django

# Setup Django environment FIRST
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email_sending():
    print("Testing Email Configuration...")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    try:
        print("Attempting to send test email...")
        send_mail(
            subject='Test Email - YEA PMS',
            message='This is a test email from the YEA Poultry Management System.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['test@example.com'],
            fail_silently=False,
        )
        print("SUCCESS: Email sent successfully!")
        print("Check your console output or email inbox depending on EMAIL_BACKEND setting.")
    except Exception as e:
        print(f"FAILURE: Error sending email: {e}")

if __name__ == "__main__":
    test_email_sending()
