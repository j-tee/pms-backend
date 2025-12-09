"""
Authentication services for email/phone verification, password reset, and OTP.
"""

import random
import string
import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailVerificationService:
    """Handle email verification for users."""
    
    @staticmethod
    def generate_verification_token():
        """Generate a secure verification token."""
        return secrets.token_urlsafe(32)
    
    @classmethod
    def send_verification_email(cls, user):
        """Send verification email to user."""
        token = cls.generate_verification_token()
        user.email_verification_token = token
        user.save(update_fields=['email_verification_token'])
        
        # Create verification URL
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}"
        
        # Send email
        subject = 'Verify your email - YEA Poultry Management System'
        message = f"""
        Hello {user.get_full_name()},
        
        Thank you for registering with YEA Poultry Management System.
        
        Please verify your email address by clicking the link below:
        {verification_url}
        
        This link will expire in 3 days.
        
        If you did not create this account, please ignore this email.
        
        Best regards,
        YEA PMS Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return token
    
    @classmethod
    def verify_email(cls, token):
        """Verify email using token."""
        try:
            user = User.objects.get(email_verification_token=token)
            user.email_verified = True
            user.email_verification_token = None
            user.save(update_fields=['email_verified', 'email_verification_token'])
            return user, None
        except User.DoesNotExist:
            return None, "Invalid verification token"


class PhoneVerificationService:
    """Handle phone number verification via OTP."""
    
    @staticmethod
    def generate_otp(length=6):
        """Generate a random OTP code."""
        return ''.join(random.choices(string.digits, k=length))
    
    @classmethod
    def send_otp(cls, user):
        """Send OTP to user's phone number."""
        otp = cls.generate_otp()
        expiry_minutes = int(getattr(settings, 'OTP_EXPIRY_MINUTES', 10))
        
        user.phone_verification_code = otp
        user.phone_verification_code_expires = timezone.now() + timedelta(minutes=expiry_minutes)
        user.save(update_fields=['phone_verification_code', 'phone_verification_code_expires'])
        
        # Send SMS (implement your SMS provider here)
        message = f"Your YEA PMS verification code is: {otp}. Valid for {expiry_minutes} minutes."
        cls._send_sms(user.phone.as_e164, message)
        
        return otp
    
    @classmethod
    def verify_otp(cls, user, otp):
        """Verify OTP code."""
        if not user.phone_verification_code:
            return False, "No verification code sent"
        
        if user.phone_verification_code_expires < timezone.now():
            return False, "Verification code has expired"
        
        if user.phone_verification_code != otp:
            return False, "Invalid verification code"
        
        user.phone_verified = True
        user.phone_verification_code = None
        user.phone_verification_code_expires = None
        user.save(update_fields=['phone_verified', 'phone_verification_code', 'phone_verification_code_expires'])
        
        return True, "Phone number verified successfully"
    
    @staticmethod
    def _send_sms(phone_number, message):
        """Send SMS using configured provider."""
        sms_provider = getattr(settings, 'SMS_PROVIDER', 'console')
        
        if sms_provider == 'console':
            # For development: print to console
            print(f"\n{'='*50}")
            print(f"SMS to {phone_number}:")
            print(f"{message}")
            print(f"{'='*50}\n")
        elif sms_provider == 'hubtel':
            # Use Hubtel SMS service
            from core.sms_service import get_sms_service
            sms_service = get_sms_service()
            result = sms_service.send_sms(
                phone_number=phone_number,
                message=message,
                reference='AUTH-OTP'
            )
            if not result.get('success'):
                raise Exception(f"Failed to send SMS: {result.get('error')}")
        elif sms_provider == 'twilio':
            # TODO: Implement Twilio SMS integration
            pass


class PasswordResetService:
    """Handle password reset functionality."""
    
    @staticmethod
    def generate_reset_token():
        """Generate a secure password reset token."""
        return secrets.token_urlsafe(32)
    
    @classmethod
    def send_password_reset_email(cls, user):
        """Send password reset email to user."""
        token = cls.generate_reset_token()
        user.password_reset_token = token
        user.password_reset_token_expires = timezone.now() + timedelta(hours=1)
        user.save(update_fields=['password_reset_token', 'password_reset_token_expires'])
        
        # Create reset URL
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"
        
        # Send email
        subject = 'Reset your password - YEA Poultry Management System'
        message = f"""
        Hello {user.get_full_name()},
        
        We received a request to reset your password.
        
        Click the link below to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you did not request a password reset, please ignore this email.
        
        Best regards,
        YEA PMS Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return token
    
    @classmethod
    def send_password_reset_sms(cls, user):
        """Send password reset OTP via SMS."""
        otp = PhoneVerificationService.generate_otp()
        user.password_reset_token = otp
        user.password_reset_token_expires = timezone.now() + timedelta(minutes=10)
        user.save(update_fields=['password_reset_token', 'password_reset_token_expires'])
        
        message = f"Your YEA PMS password reset code is: {otp}. Valid for 10 minutes."
        PhoneVerificationService._send_sms(user.phone.as_e164, message)
        
        return otp
    
    @classmethod
    def verify_reset_token(cls, token):
        """Verify password reset token."""
        try:
            user = User.objects.get(password_reset_token=token)
            
            if user.password_reset_token_expires < timezone.now():
                return None, "Password reset token has expired"
            
            return user, None
        except User.DoesNotExist:
            return None, "Invalid password reset token"
    
    @classmethod
    def reset_password(cls, token, new_password):
        """Reset user password using token."""
        user, error = cls.verify_reset_token(token)
        
        if error:
            return False, error
        
        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.save(update_fields=['password', 'password_reset_token', 'password_reset_token_expires'])
        
        # Send confirmation email
        subject = 'Password Changed - YEA Poultry Management System'
        message = f"""
        Hello {user.get_full_name()},
        
        Your password has been successfully changed.
        
        If you did not make this change, please contact us immediately.
        
        Best regards,
        YEA PMS Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
        
        return True, "Password reset successfully"
