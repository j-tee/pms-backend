"""
Farm Invitation and Spam Prevention Models

Implements hybrid registration system:
1. Officer-initiated invitations (government farmers)
2. Self-registration with approval queue (independent farmers)
3. Multi-layered spam prevention (email/phone verification, rate limiting, officer approval)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from phonenumber_field.modelfields import PhoneNumberField
from accounts.models import User
import uuid
import secrets
from datetime import timedelta


# =============================================================================
# FARM INVITATION MODEL (Officer-initiated)
# =============================================================================

class FarmInvitation(models.Model):
    """
    Invitation sent by constituency officers to farmers.
    Can be used for both government and independent farmers.
    """
    
    INVITATION_TYPE_CHOICES = [
        ('government_farmer', 'Government Initiative Farmer'),
        ('independent_farmer', 'Independent/Established Farmer'),
        ('general', 'General Invitation (Type determined during registration)'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending - Not Yet Used'),
        ('sent', 'Sent via Email/SMS'),
        ('accepted', 'Accepted - Registration Completed'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked by Officer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Invitation Details
    invitation_code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Unique invitation code/token"
    )
    invitation_type = models.CharField(
        max_length=30,
        choices=INVITATION_TYPE_CHOICES,
        default='general',
        help_text="Type of farmer this invitation is for"
    )
    
    # Issuing Officer
    issued_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='issued_invitations',
        help_text="Constituency officer who issued the invitation"
    )
    constituency = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Constituency this invitation is valid for"
    )
    
    # Recipient Information (Optional - can be pre-assigned)
    recipient_email = models.EmailField(
        blank=True,
        help_text="Pre-assigned email (optional)"
    )
    recipient_phone = PhoneNumberField(
        region='GH',
        blank=True,
        help_text="Pre-assigned phone number (optional)"
    )
    recipient_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Pre-assigned farmer name (optional)"
    )
    
    # Usage Constraints
    is_single_use = models.BooleanField(
        default=True,
        help_text="True = one-time use, False = reusable (e.g., for workshops)"
    )
    max_uses = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Maximum number of times this code can be used (for reusable codes)"
    )
    current_uses = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this code has been used"
    )
    
    # Validity Period
    expires_at = models.DateTimeField(
        help_text="Expiration date/time for this invitation"
    )
    
    # Status Tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Email/SMS Delivery
    sent_via_email = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    sent_via_sms = models.BooleanField(default=False)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Registration Tracking
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_invitations',
        help_text="User who registered using this invitation"
    )
    
    # Revocation
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.TextField(blank=True)
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Officer notes about this invitation"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farm_invitations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invitation_code']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['issued_by', 'status']),
            models.Index(fields=['constituency', 'status']),
            models.Index(fields=['recipient_email']),
            models.Index(fields=['recipient_phone']),
        ]
    
    def __str__(self):
        return f"Invitation {self.invitation_code} - {self.constituency} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Generate invitation code if not provided
        if not self.invitation_code:
            self.invitation_code = self.generate_invitation_code()
        
        # Set default expiration (30 days from now)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_invitation_code():
        """Generate a secure random invitation code"""
        return secrets.token_urlsafe(24)
    
    @property
    def is_valid(self):
        """Check if invitation is still valid"""
        if self.status in ['expired', 'revoked']:
            return False
        
        if timezone.now() > self.expires_at:
            self.status = 'expired'
            self.save()
            return False
        
        if self.is_single_use and self.current_uses >= 1:
            return False
        
        if not self.is_single_use and self.current_uses >= self.max_uses:
            return False
        
        return True
    
    @property
    def remaining_uses(self):
        """Get remaining uses for this invitation"""
        return max(0, self.max_uses - self.current_uses)
    
    def use(self, user):
        """Mark invitation as used by a user"""
        self.current_uses += 1
        self.accepted_by_user = user
        self.accepted_at = timezone.now()
        
        if self.is_single_use or self.current_uses >= self.max_uses:
            self.status = 'accepted'
        
        self.save()
    
    def revoke(self, reason=""):
        """Revoke the invitation"""
        self.status = 'revoked'
        self.revoked_at = timezone.now()
        self.revocation_reason = reason
        self.save()


# =============================================================================
# REGISTRATION APPROVAL QUEUE (Self-registrations)
# =============================================================================

class RegistrationApproval(models.Model):
    """
    Approval queue for self-registered farmers.
    Officers review and approve/reject applications.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Officer Review'),
        ('approved', 'Approved by Officer'),
        ('rejected', 'Rejected by Officer'),
        ('flagged_spam', 'Flagged as Spam/Bot'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Applicant
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='registration_approval',
        help_text="User awaiting registration approval"
    )
    
    # Application Details
    farm_name = models.CharField(max_length=200)
    primary_constituency = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Constituency where farm is located"
    )
    ghana_card_number = models.CharField(max_length=20, unique=True)
    phone_number = PhoneNumberField(region='GH')
    email = models.EmailField(blank=True)
    
    # Verification Status
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Spam Detection Scores
    spam_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Automated spam detection score (0-100, higher = more likely spam)"
    )
    spam_flags = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="List of spam indicators detected"
    )
    
    # Officer Review
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_registrations',
        help_text="Officer assigned to review this registration"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_registrations',
        help_text="Officer who approved/rejected this registration"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Priority
    priority = models.IntegerField(
        default=0,
        help_text="Higher number = higher priority (verified applicants get higher priority)"
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'registration_approvals'
        ordering = ['-priority', 'submitted_at']
        indexes = [
            models.Index(fields=['status', 'primary_constituency']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['spam_score']),
            models.Index(fields=['-priority', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.farm_name} - {self.primary_constituency} ({self.status})"
    
    def approve(self, officer, notes=""):
        """Approve the registration"""
        self.status = 'approved'
        self.reviewed_by = officer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
    
    def reject(self, officer, reason):
        """Reject the registration"""
        self.status = 'rejected'
        self.reviewed_by = officer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    def flag_as_spam(self, officer, reason):
        """Flag as spam"""
        self.status = 'flagged_spam'
        self.reviewed_by = officer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    def calculate_priority(self):
        """
        Calculate priority score for review queue.
        Higher score = reviewed first.
        """
        priority = 0
        
        # Email verified: +50 points
        if self.email_verified:
            priority += 50
        
        # Phone verified: +50 points
        if self.phone_verified:
            priority += 50
        
        # Low spam score: +30 points
        if self.spam_score < 20:
            priority += 30
        elif self.spam_score < 50:
            priority += 15
        
        # Older applications: +1 point per day waiting
        days_waiting = (timezone.now() - self.submitted_at).days
        priority += min(days_waiting, 30)  # Cap at 30 days
        
        self.priority = priority
        self.save()
        return priority


# =============================================================================
# VERIFICATION TOKENS (Email/Phone)
# =============================================================================

class VerificationToken(models.Model):
    """
    Tokens for email/phone verification during registration.
    """
    
    TOKEN_TYPE_CHOICES = [
        ('email', 'Email Verification'),
        ('phone', 'Phone/SMS Verification'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='verification_tokens'
    )
    
    # Token Details
    token_type = models.CharField(
        max_length=10,
        choices=TOKEN_TYPE_CHOICES
    )
    token = models.CharField(
        max_length=10,
        help_text="6-digit verification code"
    )
    
    # Target (email or phone to verify)
    target_value = models.CharField(
        max_length=100,
        help_text="Email address or phone number being verified"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Validity
    expires_at = models.DateTimeField()
    
    # Attempt Tracking
    verification_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of failed verification attempts"
    )
    max_attempts = models.PositiveIntegerField(default=5)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'verification_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'token_type', 'status']),
            models.Index(fields=['token']),
        ]
    
    def __str__(self):
        return f"{self.get_token_type_display()} for {self.user.email}"
    
    def save(self, *args, **kwargs):
        # Generate token if not provided
        if not self.token:
            self.token = self.generate_token()
        
        # Set expiration (10 minutes from now)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_token():
        """Generate a 6-digit verification code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    @property
    def is_valid(self):
        """Check if token is still valid"""
        if self.status != 'pending':
            return False
        
        if timezone.now() > self.expires_at:
            self.status = 'expired'
            self.save()
            return False
        
        if self.verification_attempts >= self.max_attempts:
            self.status = 'expired'
            self.save()
            return False
        
        return True
    
    def verify(self, submitted_token):
        """
        Verify the token.
        Returns (success: bool, message: str)
        """
        if not self.is_valid:
            return False, "Token has expired or is no longer valid"
        
        self.verification_attempts += 1
        self.save()
        
        if submitted_token == self.token:
            self.status = 'verified'
            self.verified_at = timezone.now()
            self.save()
            return True, "Verification successful"
        else:
            remaining = self.max_attempts - self.verification_attempts
            if remaining > 0:
                return False, f"Invalid code. {remaining} attempts remaining"
            else:
                self.status = 'expired'
                self.save()
                return False, "Maximum attempts exceeded. Please request a new code"


# =============================================================================
# RATE LIMITING MODEL
# =============================================================================

class RegistrationRateLimit(models.Model):
    """
    Track registration attempts to prevent spam/abuse.
    Rate limits based on IP address.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identifier
    ip_address = models.GenericIPAddressField(db_index=True)
    
    # Tracking
    registration_attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(auto_now=True)
    
    # Blocking
    is_blocked = models.BooleanField(default=False)
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_until = models.DateTimeField(null=True, blank=True)
    block_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'registration_rate_limits'
        indexes = [
            models.Index(fields=['ip_address', 'is_blocked']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} - {self.registration_attempts} attempts"
    
    def increment_attempts(self):
        """Increment registration attempts"""
        self.registration_attempts += 1
        self.last_attempt_at = timezone.now()
        
        # Block if too many attempts (max 3 per day)
        if self.registration_attempts >= 3:
            self.is_blocked = True
            self.blocked_at = timezone.now()
            self.blocked_until = timezone.now() + timedelta(hours=24)
            self.block_reason = f"Exceeded daily registration limit ({self.registration_attempts} attempts)"
        
        self.save()
    
    def reset_if_expired(self):
        """Reset rate limit if 24 hours have passed"""
        if self.is_blocked and timezone.now() > self.blocked_until:
            self.is_blocked = False
            self.registration_attempts = 0
            self.blocked_at = None
            self.blocked_until = None
            self.block_reason = ""
            self.save()
    
    @property
    def is_currently_blocked(self):
        """Check if currently blocked"""
        if self.is_blocked:
            if timezone.now() > self.blocked_until:
                self.reset_if_expired()
                return False
            return True
        return False
