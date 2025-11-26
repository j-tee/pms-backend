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
        FARMER = 'FARMER', 'Farmer'
        CONSTITUENCY_OFFICIAL = 'CONSTITUENCY_OFFICIAL', 'Constituency Official'
        NATIONAL_ADMIN = 'NATIONAL_ADMIN', 'National Administrator'
        PROCUREMENT_OFFICER = 'PROCUREMENT_OFFICER', 'Procurement Officer'
        VETERINARY_OFFICER = 'VETERINARY_OFFICER', 'Veterinary Officer'
        AUDITOR = 'AUDITOR', 'Auditor'
    
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
    
    # Geographic assignment (for officials)
    region = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Assigned region (for officials)"
    )
    
    constituency = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Assigned constituency (for constituency officials)"
    )
    
    # Account status
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether the user account is fully verified"
    )
    
    # Login attempt tracking (for security)
    failed_login_attempts = models.IntegerField(
        default=0,
        help_text="Number of consecutive failed login attempts"
    )
    
    account_locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Account locked until this time due to failed login attempts"
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
        
        # Lock account for 15 minutes after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.account_locked_until = timezone.now() + timedelta(minutes=15)
        
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])
    
    def record_successful_login(self):
        """Reset failed login attempts on successful login."""
        from django.utils import timezone
        
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.last_login_at = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'account_locked_until', 'last_login_at'])
