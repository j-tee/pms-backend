#!/usr/bin/env python
"""
Test script for SMS/OTP functionality.
Tests sending SMS via configured SMS provider.

Usage:
    python test-scripts/test_sms.py
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from accounts.services import PhoneVerificationService


def test_sms_configuration():
    """Test SMS configuration and send a test OTP."""
    
    print('=' * 60)
    print('SMS/OTP CONFIGURATION TEST')
    print('=' * 60)
    print()
    
    print('Current Configuration:')
    sms_provider = getattr(settings, 'SMS_PROVIDER', 'console')
    print(f'  Provider: {sms_provider}')
    
    if sms_provider == 'console':
        print('  ⚠️  Using console output (development mode)')
    elif sms_provider == 'hubtel':
        print(f'  API Key: {getattr(settings, "SMS_API_KEY", "Not set")[:10]}...')
        print(f'  Sender ID: {getattr(settings, "SMS_SENDER_ID", "Not set")}')
    elif sms_provider == 'twilio':
        print(f'  API Key: {getattr(settings, "SMS_API_KEY", "Not set")[:10]}...')
        print(f'  Sender ID: {getattr(settings, "SMS_SENDER_ID", "Not set")}')
    
    print()
    
    # Get phone number
    phone = input('Enter phone number to test (Ghana format: +233XXXXXXXXX or 0XXXXXXXXX): ').strip()
    if not phone:
        print('❌ Phone number is required')
        return False
    
    print()
    print(f'Generating OTP for: {phone}')
    
    try:
        # Generate OTP
        otp = PhoneVerificationService.generate_otp()
        print(f'Generated OTP: {otp}')
        print()
        
        # Send SMS
        message = f"Your YEA PMS verification code is: {otp}. Valid for 10 minutes."
        print('Sending SMS...')
        PhoneVerificationService._send_sms(phone, message)
        
        print()
        print('✅ SUCCESS: OTP sent successfully!')
        
        if sms_provider == 'console':
            print()
            print('NOTE: In console mode, SMS is printed above.')
            print('Configure SMS_PROVIDER in .env.development for real SMS delivery.')
        
    except Exception as e:
        print('❌ ERROR: Failed to send SMS')
        print()
        print(f'Error details: {str(e)}')
        print()
        print('Check your SMS provider configuration in .env.development')
        return False
    
    print()
    print('=' * 60)
    return True


if __name__ == '__main__':
    test_sms_configuration()
