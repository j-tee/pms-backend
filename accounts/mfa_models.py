"""
Multi-Factor Authentication Models

Provides enhanced security through:
- TOTP (Time-based One-Time Password) via authenticator apps
- SMS-based verification codes
- Backup recovery codes
- Trusted device management
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinLengthValidator
import pyotp
import secrets
import hashlib
import uuid
from datetime import timedelta

User = get_user_model()


class MFAMethod(models.Model):
    """
    Multi-Factor Authentication method configuration for a user.
    Users can have multiple methods (TOTP + SMS).
    """
    
    METHOD_CHOICES = [
        ('totp', 'Authenticator App (TOTP)'),
        ('sms', 'SMS Verification'),
        ('email', 'Email Verification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mfa_methods'
    )
    method_type = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        db_index=True
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary method used by default"
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether this method is currently active"
    )
    
    # TOTP-specific fields
    totp_secret = models.CharField(
        max_length=64,
        blank=True,
        help_text="Base32 encoded secret for TOTP"
    )
    
    # SMS/Email-specific fields
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Phone number for SMS verification"
    )
    email_address = models.EmailField(
        blank=True,
        help_text="Email for email verification"
    )
    
    # Verification tracking
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether user has successfully verified this method"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    use_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_primary', '-is_enabled', '-created_at']
        unique_together = [['user', 'method_type']]
        indexes = [
            models.Index(fields=['user', 'is_enabled']),
            models.Index(fields=['method_type', 'is_enabled']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_method_type_display()}"
    
    def generate_totp_secret(self):
        """Generate a new TOTP secret"""
        if self.method_type == 'totp':
            self.totp_secret = pyotp.random_base32()
            self.save()
            return self.totp_secret
        return None
    
    def get_totp_uri(self, issuer_name='PMS Platform'):
        """Get provisioning URI for QR code generation"""
        if self.method_type == 'totp' and self.totp_secret:
            totp = pyotp.TOTP(self.totp_secret)
            return totp.provisioning_uri(
                name=self.user.email,
                issuer_name=issuer_name
            )
        return None
    
    def verify_totp_code(self, code):
        """Verify a TOTP code"""
        if self.method_type != 'totp' or not self.totp_secret:
            return False
        
        totp = pyotp.TOTP(self.totp_secret)
        # Allow 1 interval before and after for clock skew
        return totp.verify(code, valid_window=1)
    
    def mark_verified(self):
        """Mark this method as verified"""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()
    
    def mark_used(self):
        """Record that this method was used"""
        self.last_used_at = timezone.now()
        self.use_count += 1
        self.save(update_fields=['last_used_at', 'use_count'])


class MFABackupCode(models.Model):
    """
    Backup codes for account recovery when MFA device is lost.
    Each code is single-use.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mfa_backup_codes'
    )
    
    # Store hashed code for security
    code_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA256 hash of the backup code"
    )
    
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    used_from_ip = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['user', 'is_used']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - Backup Code {'(Used)' if self.is_used else '(Available)'}"
    
    @staticmethod
    def generate_code():
        """Generate a random 8-character backup code"""
        # Generate code in format: XXXX-XXXX
        code = secrets.token_hex(4).upper()
        return f"{code[:4]}-{code[4:]}"
    
    @staticmethod
    def hash_code(code):
        """Hash a backup code"""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def verify_code(self, code):
        """Verify a backup code"""
        if self.is_used:
            return False
        
        code_hash = self.hash_code(code)
        return code_hash == self.code_hash
    
    def mark_used(self, ip_address=None):
        """Mark this code as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.used_from_ip = ip_address
        self.save()


class MFAVerificationCode(models.Model):
    """
    Temporary verification codes for SMS/Email MFA.
    Short-lived codes with limited attempts.
    """
    
    CODE_TYPE_CHOICES = [
        ('login', 'Login Verification'),
        ('setup', 'MFA Setup'),
        ('disable', 'MFA Disable'),
        ('recovery', 'Account Recovery'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mfa_verification_codes'
    )
    mfa_method = models.ForeignKey(
        MFAMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='verification_codes'
    )
    
    code_type = models.CharField(
        max_length=20,
        choices=CODE_TYPE_CHOICES,
        default='login'
    )
    
    # Code (6 digits)
    code = models.CharField(
        max_length=6,
        validators=[MinLengthValidator(6)]
    )
    
    # Delivery tracking
    sent_to = models.CharField(
        max_length=200,
        help_text="Phone number or email where code was sent"
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    
    # Expiration
    expires_at = models.DateTimeField(
        help_text="Code expires after 10 minutes"
    )
    
    # Usage tracking
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Attempt tracking
    verification_attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'code_type', 'is_used']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.code_type} - {'Used' if self.is_used else 'Active'}"
    
    def save(self, *args, **kwargs):
        """Set expiration on creation"""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if code has expired"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if code can still be used"""
        return (
            not self.is_used and
            not self.is_expired and
            self.verification_attempts < self.max_attempts
        )
    
    def verify(self, code):
        """Verify the code"""
        self.verification_attempts += 1
        self.save(update_fields=['verification_attempts'])
        
        if not self.is_valid:
            return False
        
        if self.code == code:
            self.is_used = True
            self.used_at = timezone.now()
            self.save(update_fields=['is_used', 'used_at'])
            return True
        
        return False


class TrustedDevice(models.Model):
    """
    Trusted devices that don't require MFA for a period.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trusted_devices'
    )
    
    # Device identification
    device_name = models.CharField(
        max_length=200,
        help_text="User-provided device name or auto-detected"
    )
    device_fingerprint = models.CharField(
        max_length=64,
        unique=True,
        help_text="Hash of user agent + IP or device token"
    )
    
    # Device info
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    
    # Trust management
    is_trusted = models.BooleanField(default=True)
    trust_expires_at = models.DateTimeField(
        help_text="Trust expires after 30 days by default"
    )
    
    # Usage tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    use_count = models.PositiveIntegerField(default=0)
    
    # Security
    revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(max_length=200, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_used_at', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_trusted', 'revoked']),
            models.Index(fields=['device_fingerprint']),
            models.Index(fields=['trust_expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.device_name}"
    
    def save(self, *args, **kwargs):
        """Set trust expiration on creation"""
        if not self.trust_expires_at:
            self.trust_expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        """Check if device trust is still valid"""
        return (
            self.is_trusted and
            not self.revoked and
            timezone.now() < self.trust_expires_at
        )
    
    def mark_used(self):
        """Record device usage"""
        self.last_used_at = timezone.now()
        self.use_count += 1
        self.save(update_fields=['last_used_at', 'use_count'])
    
    def revoke(self, reason=''):
        """Revoke trust for this device"""
        self.revoked = True
        self.revoked_at = timezone.now()
        self.revoke_reason = reason
        self.is_trusted = False
        self.save()
    
    def extend_trust(self, days=30):
        """Extend trust period"""
        self.trust_expires_at = timezone.now() + timedelta(days=days)
        self.save(update_fields=['trust_expires_at'])
    
    @staticmethod
    def generate_fingerprint(user_agent, ip_address):
        """Generate device fingerprint"""
        data = f"{user_agent}:{ip_address}"
        return hashlib.sha256(data.encode()).hexdigest()


class MFASettings(models.Model):
    """
    User's MFA configuration and preferences.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='mfa_settings',
        primary_key=True
    )
    
    # MFA Status
    is_enabled = models.BooleanField(
        default=False,
        help_text="Whether MFA is enabled for this user"
    )
    is_enforced = models.BooleanField(
        default=False,
        help_text="Whether MFA is enforced by admin (cannot be disabled)"
    )
    
    # Setup tracking
    enabled_at = models.DateTimeField(null=True, blank=True)
    disabled_at = models.DateTimeField(null=True, blank=True)
    
    # Preferences
    require_for_sensitive_actions = models.BooleanField(
        default=True,
        help_text="Require MFA for sensitive actions (password change, etc.)"
    )
    remember_device_enabled = models.BooleanField(
        default=True,
        help_text="Allow remembering trusted devices"
    )
    remember_device_days = models.PositiveIntegerField(
        default=30,
        help_text="Days to remember trusted devices"
    )
    
    # Backup codes
    backup_codes_generated = models.BooleanField(default=False)
    backup_codes_generated_at = models.DateTimeField(null=True, blank=True)
    backup_codes_remaining = models.PositiveIntegerField(default=0)
    
    # Security tracking
    last_successful_verification = models.DateTimeField(null=True, blank=True)
    failed_verification_attempts = models.PositiveIntegerField(default=0)
    last_failed_attempt = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'MFA Settings'
        verbose_name_plural = 'MFA Settings'
    
    def __str__(self):
        return f"{self.user.email} - MFA {'Enabled' if self.is_enabled else 'Disabled'}"
    
    def enable_mfa(self):
        """Enable MFA for user"""
        self.is_enabled = True
        self.enabled_at = timezone.now()
        self.disabled_at = None
        self.save()
    
    def disable_mfa(self):
        """Disable MFA for user (if not enforced)"""
        if not self.is_enforced:
            self.is_enabled = False
            self.disabled_at = timezone.now()
            self.save()
            
            # Revoke all trusted devices
            self.user.trusted_devices.filter(revoked=False).update(
                revoked=True,
                revoked_at=timezone.now(),
                revoke_reason='MFA disabled'
            )
    
    def record_successful_verification(self):
        """Record successful MFA verification"""
        self.last_successful_verification = timezone.now()
        self.failed_verification_attempts = 0
        self.save(update_fields=['last_successful_verification', 'failed_verification_attempts'])
    
    def record_failed_verification(self):
        """Record failed MFA verification"""
        self.failed_verification_attempts += 1
        self.last_failed_attempt = timezone.now()
        self.save(update_fields=['failed_verification_attempts', 'last_failed_attempt'])
    
    @property
    def has_active_methods(self):
        """Check if user has any active MFA methods"""
        return self.user.mfa_methods.filter(is_enabled=True, is_verified=True).exists()
    
    @property
    def primary_method(self):
        """Get user's primary MFA method"""
        return self.user.mfa_methods.filter(
            is_enabled=True,
            is_verified=True,
            is_primary=True
        ).first()
    
    @property
    def available_methods(self):
        """Get all available MFA methods"""
        return self.user.mfa_methods.filter(is_enabled=True, is_verified=True)
