#!/usr/bin/env python
"""
Test script for email configuration.
Tests sending emails via configured SMTP server.

Usage:
    python test-scripts/test_email.py
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings


def test_email_configuration():
    """Test email configuration and send a test email."""
    
    print('=' * 60)
    print('EMAIL CONFIGURATION TEST')
    print('=' * 60)
    print()
    
    print('Current Configuration:')
    print(f'  Backend:    {settings.EMAIL_BACKEND}')
    print(f'  Host:       {settings.EMAIL_HOST}')
    print(f'  Port:       {settings.EMAIL_PORT}')
    print(f'  Use TLS:    {settings.EMAIL_USE_TLS}')
    print(f'  User:       {settings.EMAIL_HOST_USER}')
    print(f'  From Email: {settings.DEFAULT_FROM_EMAIL}')
    print(f'  Timeout:    {settings.EMAIL_TIMEOUT}s')
    print()
    
    # Check if email is properly configured
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        print('⚠️  WARNING: Using console backend - emails will be printed to console')
        print()
    
    # Send test email
    recipient = input('Enter recipient email address (or press Enter to use configured email): ').strip()
    if not recipient:
        recipient = settings.EMAIL_HOST_USER
    
    print()
    print(f'Sending test email to: {recipient}')
    print('Please wait...')
    print()
    
    try:
        send_mail(
            subject='YEA PMS - Email Configuration Test',
            message='''
Hello,

This is a test email from the YEA Poultry Management System.

If you receive this email, your email configuration is working correctly!

System Details:
- Backend: {}
- Host: {}
- Port: {}
- From: {}

Best regards,
YEA PMS Team
            '''.format(
                settings.EMAIL_BACKEND,
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                settings.DEFAULT_FROM_EMAIL
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        
        print('✅ SUCCESS: Test email sent successfully!')
        print()
        print(f'Check your inbox at: {recipient}')
        
    except Exception as e:
        print('❌ ERROR: Failed to send email')
        print()
        print(f'Error details: {str(e)}')
        print()
        print('Common issues:')
        print('  1. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env.development')
        print('  2. Verify SMTP settings (host, port, TLS)')
        print('  3. For Gmail: Enable "App Passwords" in Google Account settings')
        print('  4. Check firewall/network settings')
        return False
    
    print()
    print('=' * 60)
    return True


if __name__ == '__main__':
    test_email_configuration()
