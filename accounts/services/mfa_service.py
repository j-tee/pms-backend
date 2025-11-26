"""
Multi-Factor Authentication Service

Handles MFA operations:
- Enable/disable MFA
- Generate and verify TOTP codes
- Send and verify SMS/Email codes
- Generate and manage backup codes
- Trusted device management
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from accounts.mfa_models import (
    MFASettings,
    MFAMethod,
    MFABackupCode,
    MFAVerificationCode,
    TrustedDevice
)
from core.sms_service import SMSService
import secrets
import qrcode
import io
import base64


class MFAService:
    """Service for managing Multi-Factor Authentication"""
    
    # Number of backup codes to generate
    BACKUP_CODES_COUNT = 10
    
    @classmethod
    def get_or_create_settings(cls, user):
        """Get or create MFA settings for user"""
        settings, created = MFASettings.objects.get_or_create(user=user)
        return settings
    
    @classmethod
    @transaction.atomic
    def enable_totp(cls, user):
        """
        Enable TOTP (authenticator app) MFA for user.
        Returns secret and QR code for setup.
        """
        # Get or create MFA settings
        mfa_settings = cls.get_or_create_settings(user)
        
        # Check if TOTP already enabled
        existing_totp = MFAMethod.objects.filter(
            user=user,
            method_type='totp',
            is_enabled=True
        ).first()
        
        if existing_totp and existing_totp.is_verified:
            raise ValidationError("TOTP MFA is already enabled for this user")
        
        # Create or get TOTP method
        if existing_totp:
            totp_method = existing_totp
        else:
            totp_method = MFAMethod.objects.create(
                user=user,
                method_type='totp',
                is_primary=not user.mfa_methods.filter(is_verified=True).exists()
            )
        
        # Generate secret
        secret = totp_method.generate_totp_secret()
        
        # Get provisioning URI
        provisioning_uri = totp_method.get_totp_uri()
        
        # Generate QR code
        qr_code_base64 = cls._generate_qr_code(provisioning_uri)
        
        return {
            'secret': secret,
            'provisioning_uri': provisioning_uri,
            'qr_code': qr_code_base64,
            'method_id': str(totp_method.id),
            'message': 'Scan the QR code with your authenticator app and verify with a code to complete setup'
        }
    
    @classmethod
    def verify_totp_setup(cls, user, code, method_id):
        """
        Verify TOTP code during setup to complete MFA enablement.
        """
        try:
            totp_method = MFAMethod.objects.get(
                id=method_id,
                user=user,
                method_type='totp'
            )
        except MFAMethod.DoesNotExist:
            raise ValidationError("Invalid TOTP method")
        
        # Verify the code
        if not totp_method.verify_totp_code(code):
            raise ValidationError("Invalid verification code")
        
        # Mark method as verified
        totp_method.mark_verified()
        
        # Enable MFA
        mfa_settings = cls.get_or_create_settings(user)
        mfa_settings.enable_mfa()
        
        # Generate backup codes
        backup_codes = cls.generate_backup_codes(user)
        
        return {
            'success': True,
            'message': 'TOTP MFA enabled successfully',
            'backup_codes': backup_codes,
            'warning': 'Save these backup codes in a safe place. You will need them if you lose access to your authenticator app.'
        }
    
    @classmethod
    @transaction.atomic
    def enable_sms(cls, user, phone_number):
        """
        Enable SMS MFA for user.
        Sends verification code to phone.
        """
        # Get or create MFA settings
        mfa_settings = cls.get_or_create_settings(user)
        
        # Check if SMS already enabled
        existing_sms = MFAMethod.objects.filter(
            user=user,
            method_type='sms',
            is_enabled=True,
            is_verified=True
        ).first()
        
        if existing_sms:
            raise ValidationError("SMS MFA is already enabled for this user")
        
        # Create or update SMS method
        sms_method, created = MFAMethod.objects.update_or_create(
            user=user,
            method_type='sms',
            defaults={
                'phone_number': phone_number,
                'is_primary': not user.mfa_methods.filter(is_verified=True).exists(),
                'is_enabled': True
            }
        )
        
        # Send verification code
        code = cls._send_verification_code(user, sms_method, 'setup')
        
        return {
            'method_id': str(sms_method.id),
            'phone_number': phone_number,
            'message': f'Verification code sent to {phone_number}. Code expires in 10 minutes.'
        }
    
    @classmethod
    def verify_sms_setup(cls, user, code, method_id):
        """
        Verify SMS code during setup to complete MFA enablement.
        """
        # Get verification code
        verification = MFAVerificationCode.objects.filter(
            user=user,
            code_type='setup',
            is_used=False
        ).order_by('-created_at').first()
        
        if not verification:
            raise ValidationError("No verification code found. Please request a new code.")
        
        if not verification.verify(code):
            raise ValidationError("Invalid or expired verification code")
        
        # Get SMS method
        try:
            sms_method = MFAMethod.objects.get(
                id=method_id,
                user=user,
                method_type='sms'
            )
        except MFAMethod.DoesNotExist:
            raise ValidationError("Invalid SMS method")
        
        # Mark method as verified
        sms_method.mark_verified()
        
        # Enable MFA
        mfa_settings = cls.get_or_create_settings(user)
        mfa_settings.enable_mfa()
        
        # Generate backup codes
        backup_codes = cls.generate_backup_codes(user)
        
        return {
            'success': True,
            'message': 'SMS MFA enabled successfully',
            'backup_codes': backup_codes,
            'warning': 'Save these backup codes in a safe place.'
        }
    
    @classmethod
    @transaction.atomic
    def disable_mfa(cls, user, password=None):
        """
        Disable MFA for user (if not enforced).
        Requires password confirmation.
        """
        mfa_settings = cls.get_or_create_settings(user)
        
        if mfa_settings.is_enforced:
            raise ValidationError("MFA is enforced by administrator and cannot be disabled")
        
        # Verify password if provided
        if password and not user.check_password(password):
            raise ValidationError("Invalid password")
        
        # Disable MFA
        mfa_settings.disable_mfa()
        
        # Disable all MFA methods
        user.mfa_methods.update(is_enabled=False)
        
        # Invalidate backup codes
        user.mfa_backup_codes.filter(is_used=False).delete()
        
        return {
            'success': True,
            'message': 'MFA disabled successfully'
        }
    
    @classmethod
    def generate_backup_codes(cls, user):
        """
        Generate new backup codes for user.
        Returns plaintext codes (only shown once).
        """
        # Delete existing unused codes
        user.mfa_backup_codes.filter(is_used=False).delete()
        
        codes = []
        for _ in range(cls.BACKUP_CODES_COUNT):
            # Generate code
            code = MFABackupCode.generate_code()
            codes.append(code)
            
            # Store hashed code
            MFABackupCode.objects.create(
                user=user,
                code_hash=MFABackupCode.hash_code(code)
            )
        
        # Update settings
        mfa_settings = cls.get_or_create_settings(user)
        mfa_settings.backup_codes_generated = True
        mfa_settings.backup_codes_generated_at = timezone.now()
        mfa_settings.backup_codes_remaining = cls.BACKUP_CODES_COUNT
        mfa_settings.save()
        
        return codes
    
    @classmethod
    def verify_backup_code(cls, user, code):
        """
        Verify and consume a backup code.
        """
        # Get unused backup codes
        backup_codes = user.mfa_backup_codes.filter(is_used=False)
        
        for backup_code in backup_codes:
            if backup_code.verify_code(code):
                # Mark as used
                backup_code.mark_used()
                
                # Update remaining count
                mfa_settings = cls.get_or_create_settings(user)
                mfa_settings.backup_codes_remaining = user.mfa_backup_codes.filter(is_used=False).count()
                mfa_settings.record_successful_verification()
                
                return {
                    'success': True,
                    'message': 'Backup code verified',
                    'remaining_codes': mfa_settings.backup_codes_remaining,
                    'warning': 'You have {} backup codes remaining'.format(mfa_settings.backup_codes_remaining) if mfa_settings.backup_codes_remaining < 3 else None
                }
        
        # Record failed attempt
        mfa_settings = cls.get_or_create_settings(user)
        mfa_settings.record_failed_verification()
        
        raise ValidationError("Invalid backup code")
    
    @classmethod
    def verify_mfa(cls, user, code, method_type=None):
        """
        Verify MFA code for login or sensitive action.
        """
        mfa_settings = cls.get_or_create_settings(user)
        
        if not mfa_settings.is_enabled:
            raise ValidationError("MFA is not enabled for this user")
        
        # Try backup code first
        if code and len(code) == 9 and '-' in code:  # Format: XXXX-XXXX
            try:
                return cls.verify_backup_code(user, code)
            except ValidationError:
                pass  # Continue to other methods
        
        # Determine method to use
        if method_type:
            method = user.mfa_methods.filter(
                method_type=method_type,
                is_enabled=True,
                is_verified=True
            ).first()
        else:
            method = mfa_settings.primary_method
        
        if not method:
            raise ValidationError("No active MFA method found")
        
        # Verify based on method type
        if method.method_type == 'totp':
            if method.verify_totp_code(code):
                method.mark_used()
                mfa_settings.record_successful_verification()
                return {
                    'success': True,
                    'message': 'MFA verification successful',
                    'method': 'totp'
                }
        
        elif method.method_type == 'sms':
            # Get latest verification code
            verification = MFAVerificationCode.objects.filter(
                user=user,
                mfa_method=method,
                code_type='login',
                is_used=False
            ).order_by('-created_at').first()
            
            if verification and verification.verify(code):
                method.mark_used()
                mfa_settings.record_successful_verification()
                return {
                    'success': True,
                    'message': 'MFA verification successful',
                    'method': 'sms'
                }
        
        # Failed verification
        mfa_settings.record_failed_verification()
        raise ValidationError("Invalid verification code")
    
    @classmethod
    def send_login_code(cls, user):
        """
        Send MFA code for login (SMS/Email methods only).
        """
        mfa_settings = cls.get_or_create_settings(user)
        
        if not mfa_settings.is_enabled:
            raise ValidationError("MFA is not enabled for this user")
        
        # Get primary method
        method = mfa_settings.primary_method
        
        if not method:
            raise ValidationError("No active MFA method found")
        
        if method.method_type == 'totp':
            return {
                'method': 'totp',
                'message': 'Enter code from your authenticator app'
            }
        
        elif method.method_type in ['sms', 'email']:
            cls._send_verification_code(user, method, 'login')
            return {
                'method': method.method_type,
                'message': f'Verification code sent to {method.phone_number if method.method_type == "sms" else method.email_address}'
            }
        
        raise ValidationError("Invalid MFA method")
    
    @classmethod
    def _send_verification_code(cls, user, mfa_method, code_type):
        """
        Send verification code via SMS or Email.
        """
        # Generate 6-digit code
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Create verification code record
        verification = MFAVerificationCode.objects.create(
            user=user,
            mfa_method=mfa_method,
            code_type=code_type,
            code=code,
            sent_to=mfa_method.phone_number if mfa_method.method_type == 'sms' else mfa_method.email_address
        )
        
        # Send code
        if mfa_method.method_type == 'sms':
            message = f"Your PMS verification code is: {code}. Valid for 10 minutes."
            SMSService.send_sms(mfa_method.phone_number, message)
        
        elif mfa_method.method_type == 'email':
            # TODO: Implement email sending
            pass
        
        return code
    
    @classmethod
    def _generate_qr_code(cls, data):
        """
        Generate QR code as base64 encoded image.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @classmethod
    @transaction.atomic
    def add_trusted_device(cls, user, device_name, user_agent, ip_address):
        """
        Add device to trusted devices list.
        """
        mfa_settings = cls.get_or_create_settings(user)
        
        if not mfa_settings.remember_device_enabled:
            raise ValidationError("Device remembering is not enabled")
        
        # Generate fingerprint
        fingerprint = TrustedDevice.generate_fingerprint(user_agent, ip_address)
        
        # Check if device already trusted
        existing = TrustedDevice.objects.filter(
            user=user,
            device_fingerprint=fingerprint,
            revoked=False
        ).first()
        
        if existing:
            # Extend trust
            existing.extend_trust(days=mfa_settings.remember_device_days)
            existing.mark_used()
            return existing
        
        # Create new trusted device
        device = TrustedDevice.objects.create(
            user=user,
            device_name=device_name,
            device_fingerprint=fingerprint,
            user_agent=user_agent,
            ip_address=ip_address
        )
        device.extend_trust(days=mfa_settings.remember_device_days)
        
        return device
    
    @classmethod
    def is_trusted_device(cls, user, user_agent, ip_address):
        """
        Check if current device is trusted.
        """
        fingerprint = TrustedDevice.generate_fingerprint(user_agent, ip_address)
        
        device = TrustedDevice.objects.filter(
            user=user,
            device_fingerprint=fingerprint,
            revoked=False
        ).first()
        
        if device and device.is_valid:
            device.mark_used()
            return True
        
        return False
    
    @classmethod
    def revoke_trusted_device(cls, user, device_id, reason=''):
        """
        Revoke trust for a specific device.
        """
        try:
            device = TrustedDevice.objects.get(id=device_id, user=user)
            device.revoke(reason)
            return {
                'success': True,
                'message': f'Device "{device.device_name}" has been revoked'
            }
        except TrustedDevice.DoesNotExist:
            raise ValidationError("Device not found")
    
    @classmethod
    def get_user_mfa_status(cls, user):
        """
        Get comprehensive MFA status for user.
        """
        mfa_settings = cls.get_or_create_settings(user)
        
        methods = []
        for method in user.mfa_methods.filter(is_enabled=True):
            methods.append({
                'id': str(method.id),
                'type': method.method_type,
                'is_primary': method.is_primary,
                'is_verified': method.is_verified,
                'last_used': method.last_used_at,
                'use_count': method.use_count
            })
        
        trusted_devices = []
        for device in user.trusted_devices.filter(revoked=False):
            trusted_devices.append({
                'id': str(device.id),
                'name': device.device_name,
                'last_used': device.last_used_at,
                'expires_at': device.trust_expires_at,
                'is_valid': device.is_valid
            })
        
        return {
            'mfa_enabled': mfa_settings.is_enabled,
            'mfa_enforced': mfa_settings.is_enforced,
            'methods': methods,
            'backup_codes_remaining': mfa_settings.backup_codes_remaining,
            'trusted_devices': trusted_devices,
            'remember_device_enabled': mfa_settings.remember_device_enabled
        }
