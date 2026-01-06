from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
import uuid
from .roles import RoleMixin, Role, UserRole as UserRoleAssignment, Permission, RolePermission


class User(AbstractUser, RoleMixin):
    """
    Custom User model extending Django's AbstractUser with RoleMixin.
    Supports multiple user roles for the YEA Poultry Management System.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class UserRole(models.TextChoices):
        # System Administration (Highest Level)
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Administrator'
        # YEA Officials (Elevated Administrators)
        YEA_OFFICIAL = 'YEA_OFFICIAL', 'YEA Official'
        # Standard Administrative Roles
        NATIONAL_ADMIN = 'NATIONAL_ADMIN', 'National Administrator'
        REGIONAL_COORDINATOR = 'REGIONAL_COORDINATOR', 'Regional Coordinator'
        CONSTITUENCY_OFFICIAL = 'CONSTITUENCY_OFFICIAL', 'Constituency Official'
        # Specialized Roles
        PROCUREMENT_OFFICER = 'PROCUREMENT_OFFICER', 'Procurement Officer'
        VETERINARY_OFFICER = 'VETERINARY_OFFICER', 'Veterinary Officer'
        EXTENSION_OFFICER = 'EXTENSION_OFFICER', 'Extension Officer'
        FINANCE_OFFICER = 'FINANCE_OFFICER', 'Finance Officer'
        AUDITOR = 'AUDITOR', 'Auditor'
        # End User
        FARMER = 'FARMER', 'Farmer'
    
    class PreferredContactMethod(models.TextChoices):
        EMAIL = 'EMAIL', 'Email'
        PHONE = 'PHONE', 'Phone'
        SMS = 'SMS', 'SMS'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
    
    # Core user fields
    role = models.CharField(
        max_length=50,
        choices=UserRole.choices,
        default=UserRole.FARMER,
        db_index=True,
        help_text="User's primary role in the system"
    )
    
    # Additional contact information with proper validation
    phone = PhoneNumberField(
        region='GH',  # Ghana
        unique=True,
        db_index=True,
        help_text="Phone number (Ghana format: +233XXXXXXXXX)"
    )
    
    phone_verified = models.BooleanField(
        default=False,
        help_text="Whether the phone number has been verified"
    )
    
    phone_verification_code = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        help_text="OTP code for phone verification"
    )
    
    phone_verification_code_expires = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration time for phone verification code"
    )
    
    # Email verification
    email_verified = models.BooleanField(
        default=False,
        help_text="Whether the email has been verified"
    )
    
    email_verification_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Token for email verification"
    )
    
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=PreferredContactMethod.choices,
        default=PreferredContactMethod.EMAIL,
        help_text="Preferred method of contact"
    )
    
    # Geographic assignment (for officials and farmers)
    region = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Assigned region (for officials) or farm region (for farmers)"
    )
    
    district = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="District (for farmers - synced from farm registration)"
    )
    
    constituency = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Assigned constituency (for officials) or farm constituency (for farmers)"
    )
    
    # Account status
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether the user account is fully verified"
    )
    
    # ========================================
    # Suspension Management
    # ========================================
    is_suspended = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the user account is currently suspended"
    )
    
    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the account was suspended"
    )
    
    suspended_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the suspension expires (null = indefinite)"
    )
    
    suspended_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='suspended_users',
        help_text="Admin who suspended this account"
    )
    
    suspension_reason = models.TextField(
        blank=True,
        help_text="Reason for account suspension"
    )
    
    # ========================================
    # Token Versioning (for force logout)
    # ========================================
    token_version = models.IntegerField(
        default=0,
        help_text="Increment to invalidate all existing tokens"
    )
    
    # ========================================
    # Login attempt tracking (for security)
    # ========================================
    failed_login_attempts = models.IntegerField(
        default=0,
        help_text="Number of consecutive failed login attempts"
    )
    
    account_locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Account locked until this time due to failed login attempts"
    )
    
    last_failed_login_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last failed login attempt"
    )
    
    # Password reset
    password_reset_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Token for password reset"
    )
    
    password_reset_token_expires = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration time for password reset token"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['region', 'constituency']),
            models.Index(fields=['email_verified', 'phone_verified']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def get_full_name(self):
        """Return the user's full name or username if name is not set."""
        full_name = super().get_full_name()
        return full_name if full_name else self.username
    
    def is_account_locked(self):
        """Check if account is locked due to failed login attempts."""
        if self.account_locked_until:
            from django.utils import timezone
            if timezone.now() < self.account_locked_until:
                return True
            else:
                # Lock period expired, reset
                self.account_locked_until = None
                self.failed_login_attempts = 0
                self.save(update_fields=['account_locked_until', 'failed_login_attempts'])
        return False
    
    def record_failed_login(self):
        """Record a failed login attempt and lock account if threshold exceeded."""
        from django.utils import timezone
        from datetime import timedelta
        
        self.failed_login_attempts += 1
        self.last_failed_login_at = timezone.now()
        
        # Lock account for 15 minutes after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.account_locked_until = timezone.now() + timedelta(minutes=15)
        
        self.save(update_fields=['failed_login_attempts', 'account_locked_until', 'last_failed_login_at'])
    
    def record_successful_login(self):
        """Reset failed login attempts on successful login."""
        from django.utils import timezone
        
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.last_login_at = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'account_locked_until', 'last_login_at'])
    
    def unlock_account(self):
        """Manually unlock account (admin action)."""
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])
    
    def suspend(self, suspended_by, reason, duration_days=None):
        """
        Suspend this user account.
        
        Args:
            suspended_by: User who is performing the suspension
            reason: Reason for the suspension
            duration_days: Number of days to suspend (None = indefinite)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        self.is_suspended = True
        self.suspended_at = timezone.now()
        self.suspended_by = suspended_by
        self.suspension_reason = reason
        
        if duration_days:
            self.suspended_until = timezone.now() + timedelta(days=duration_days)
        else:
            self.suspended_until = None  # Indefinite
        
        # Increment token version to invalidate all existing tokens
        self.token_version += 1
        
        self.save(update_fields=[
            'is_suspended', 'suspended_at', 'suspended_by',
            'suspension_reason', 'suspended_until', 'token_version'
        ])
    
    def unsuspend(self):
        """Remove suspension from this user account."""
        self.is_suspended = False
        self.suspended_at = None
        self.suspended_by = None
        self.suspension_reason = ''
        self.suspended_until = None
        self.save(update_fields=[
            'is_suspended', 'suspended_at', 'suspended_by',
            'suspension_reason', 'suspended_until'
        ])
    
    def is_suspension_expired(self):
        """Check if a time-limited suspension has expired."""
        if not self.is_suspended:
            return False
        if self.suspended_until is None:
            return False  # Indefinite suspension
        from django.utils import timezone
        return timezone.now() >= self.suspended_until
    
    def check_and_clear_expired_suspension(self):
        """Auto-clear suspension if expired. Returns True if was cleared."""
        if self.is_suspension_expired():
            self.unsuspend()
            return True
        return False
    
    def force_logout(self):
        """Invalidate all existing tokens for this user."""
        self.token_version += 1
        self.save(update_fields=['token_version'])
    
    def has_role(self, role_name, resource=None):
        """
        Override has_role to check both primary role field and role system.
        
        Args:
            role_name: Name of the role to check
            resource: Optional resource object if role is scoped
        
        Returns:
            Boolean indicating if user has the role
        """
        # First check the primary role field
        if self.role == role_name:
            return True
        
        # Then check the role system (from RoleMixin)
        return super().has_role(role_name, resource)


# Import MFA models to register them with Django
from .mfa_models import (
    MFAMethod,
    MFABackupCode,
    MFAVerificationCode,
    TrustedDevice,
    MFASettings
)
