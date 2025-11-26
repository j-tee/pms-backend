"""
Farm Application Model

Handles anonymous applications from prospective farmers.
Applications go through screening BEFORE account creation.

Flow:
1. Prospective farmer fills application form (no login required)
2. Application goes through 3-tier screening
3. Upon approval → invitation sent to create account
4. Farmer creates account → Farm profile created
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from accounts.models import User
import uuid
from datetime import timedelta


class FarmApplication(models.Model):
    """
    Anonymous farm application submitted by prospective farmers.
    Goes through screening before account creation.
    """
    
    APPLICATION_TYPE_CHOICES = [
        ('government_program', 'YEA Government Program'),
        ('independent', 'Independent Farmer'),
    ]
    
    STATUS_CHOICES = [
        ('submitted', 'Submitted - Awaiting Assignment'),
        ('constituency_review', 'Under Constituency Review'),
        ('regional_review', 'Under Regional Review'),
        ('national_review', 'Under National Review'),
        ('changes_requested', 'Changes Requested'),
        ('approved', 'Approved - Invitation Sent'),
        ('rejected', 'Rejected'),
        ('account_created', 'Account Created - Farm Active'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Application Tracking
    application_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Format: APP-YYYY-XXXXX"
    )
    application_type = models.CharField(
        max_length=30,
        choices=APPLICATION_TYPE_CHOICES,
        db_index=True,
        help_text="Type of farmer application"
    )
    
    # ===================================================================
    # SECTION 1: APPLICANT INFORMATION (NO ACCOUNT YET)
    # ===================================================================
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=20,
        choices=[
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Other', 'Other'),
        ]
    )
    ghana_card_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Format: GHA-XXXXXXXXX-X"
    )
    
    # Contact Information
    primary_phone = PhoneNumberField(region='GH')
    alternate_phone = PhoneNumberField(region='GH', blank=True)
    email = models.EmailField(blank=True, help_text="Optional - for notifications")
    residential_address = models.TextField()
    
    # Location
    primary_constituency = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Constituency where farm will be located"
    )
    region = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    
    # ===================================================================
    # SECTION 2: FARM INFORMATION (BASIC)
    # ===================================================================
    
    proposed_farm_name = models.CharField(max_length=200)
    farm_location_description = models.TextField(
        help_text="Describe farm location (community, landmarks, etc.)"
    )
    land_size_acres = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Approximate land size"
    )
    
    # Production Plans
    primary_production_type = models.CharField(
        max_length=20,
        choices=[
            ('Layers', 'Layers (Egg Production)'),
            ('Broilers', 'Broilers (Meat Production)'),
            ('Both', 'Both Layers and Broilers')
        ]
    )
    planned_bird_capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="How many birds do you plan to raise?"
    )
    
    # Experience
    years_in_poultry = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        help_text="Years of experience in poultry farming"
    )
    has_existing_farm = models.BooleanField(
        default=False,
        help_text="Do you already have an operational farm?"
    )
    
    # For Government Program Applications
    yea_program_batch = models.CharField(
        max_length=50,
        blank=True,
        help_text="YEA batch/cohort (if applicable)"
    )
    referral_source = models.CharField(
        max_length=100,
        blank=True,
        help_text="How did you hear about this program?"
    )
    
    # ===================================================================
    # SECTION 3: SCREENING WORKFLOW
    # ===================================================================
    
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='submitted',
        db_index=True
    )
    current_review_level = models.CharField(
        max_length=20,
        choices=[
            ('constituency', 'Constituency Level'),
            ('regional', 'Regional Level'),
            ('national', 'National Level'),
        ],
        null=True,
        blank=True
    )
    
    # Approval Tracking
    constituency_approved_at = models.DateTimeField(null=True, blank=True)
    constituency_approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='constituency_approved_applications'
    )
    
    regional_approved_at = models.DateTimeField(null=True, blank=True)
    regional_approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='regional_approved_applications'
    )
    
    final_approved_at = models.DateTimeField(null=True, blank=True)
    final_approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='final_approved_applications'
    )
    
    # Rejection
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_applications'
    )
    rejection_reason = models.TextField(blank=True)
    
    # Changes Requested
    changes_requested = models.TextField(blank=True)
    changes_deadline = models.DateTimeField(null=True, blank=True)
    
    # Assignment
    assigned_extension_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_applications'
    )
    
    # ===================================================================
    # SECTION 4: POST-APPROVAL (Account Creation)
    # ===================================================================
    
    # Invitation sent after approval
    invitation = models.OneToOneField(
        'FarmInvitation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_application',
        help_text="Invitation sent after approval"
    )
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Account created by farmer
    user_account = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='farm_application',
        help_text="User account created after approval"
    )
    account_created_at = models.DateTimeField(null=True, blank=True)
    
    # Farm profile created
    farm_profile = models.OneToOneField(
        'Farm',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application',
        help_text="Farm profile created from application"
    )
    farm_created_at = models.DateTimeField(null=True, blank=True)
    
    # ===================================================================
    # SECTION 5: VERIFICATION & SPAM PREVENTION
    # ===================================================================
    
    # Email/Phone Verification
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Spam Detection
    spam_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Automated spam score (0-100)"
    )
    spam_flags = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="Spam indicators detected"
    )
    
    # Rate Limiting
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Priority Score
    priority_score = models.IntegerField(
        default=0,
        help_text="Higher = reviewed first"
    )
    
    # ===================================================================
    # SECTION 6: TIMESTAMPS
    # ===================================================================
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farm_applications'
        ordering = ['-priority_score', '-submitted_at']
        indexes = [
            models.Index(fields=['application_number']),
            models.Index(fields=['ghana_card_number']),
            models.Index(fields=['primary_phone']),
            models.Index(fields=['status', 'current_review_level']),
            models.Index(fields=['application_type', 'status']),
            models.Index(fields=['primary_constituency', 'status']),
            models.Index(fields=['-priority_score', '-submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.application_number} - {self.first_name} {self.last_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Generate application number
        if not self.application_number:
            from datetime import datetime
            year = datetime.now().year
            
            last_app = FarmApplication.objects.filter(
                application_number__startswith=f'APP-{year}-'
            ).order_by('-application_number').first()
            
            if last_app:
                last_num = int(last_app.application_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.application_number = f'APP-{year}-{new_num:05d}'
        
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        """Get applicant's full name"""
        return f"{self.first_name} {self.middle_name} {self.last_name}".replace('  ', ' ').strip()
    
    @property
    def is_verified(self):
        """Check if email and phone are both verified"""
        return self.email_verified and self.phone_verified
    
    @property
    def is_approved(self):
        """Check if application is approved"""
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        """Check if application is rejected"""
        return self.status == 'rejected'
    
    @property
    def is_in_screening(self):
        """Check if application is currently in screening process"""
        return self.status in [
            'submitted',
            'constituency_review',
            'regional_review',
            'national_review',
            'changes_requested'
        ]
    
    @property
    def days_since_submission(self):
        """Calculate days since application submitted"""
        if self.submitted_at:
            return (timezone.now() - self.submitted_at).days
        return 0
    
    def calculate_priority_score(self):
        """
        Calculate priority score for review queue.
        Higher score = reviewed first.
        """
        score = 0
        
        # Government program applications get priority
        if self.application_type == 'government_program':
            score += 50
        
        # Verified email/phone
        if self.email_verified:
            score += 25
        if self.phone_verified:
            score += 25
        
        # Low spam score
        if self.spam_score < 20:
            score += 30
        elif self.spam_score < 50:
            score += 15
        
        # Experience bonus
        if self.years_in_poultry >= 2:
            score += 10
        
        # Existing farm bonus
        if self.has_existing_farm:
            score += 10
        
        # Age of application (waiting time)
        days_waiting = self.days_since_submission
        score += min(days_waiting, 30)  # Max 30 points for waiting
        
        self.priority_score = score
        self.save()
        return score


class ApplicationReviewAction(models.Model):
    """
    Audit trail for application review actions.
    Similar to FarmReviewAction but for applications.
    """
    
    REVIEW_LEVEL_CHOICES = [
        ('constituency', 'Constituency Level'),
        ('regional', 'Regional Level'),
        ('national', 'National Level'),
    ]
    
    ACTION_CHOICES = [
        ('claimed', 'Claimed for Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('request_changes', 'Request Changes'),
        ('changes_submitted', 'Changes Submitted'),
        ('note_added', 'Note Added'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        FarmApplication,
        on_delete=models.CASCADE,
        related_name='review_actions'
    )
    
    # Reviewer
    reviewer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='application_reviews'
    )
    review_level = models.CharField(
        max_length=20,
        choices=REVIEW_LEVEL_CHOICES
    )
    
    # Action
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )
    notes = models.TextField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'application_review_actions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'review_level']),
            models.Index(fields=['reviewer', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.application.application_number} - {self.get_action_display()} by {self.reviewer.get_full_name()}"


class ApplicationQueue(models.Model):
    """
    Queue management for application reviews.
    Similar to FarmApprovalQueue but for applications.
    """
    
    REVIEW_LEVEL_CHOICES = ApplicationReviewAction.REVIEW_LEVEL_CHOICES
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('claimed', 'Claimed by Officer'),
        ('in_progress', 'Under Review'),
        ('completed', 'Review Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        FarmApplication,
        on_delete=models.CASCADE,
        related_name='queue_items'
    )
    
    # Queue Details
    review_level = models.CharField(
        max_length=20,
        choices=REVIEW_LEVEL_CHOICES,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_application_reviews'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    auto_assigned = models.BooleanField(default=False)
    
    # Priority & Timing
    priority = models.IntegerField(default=0)
    entered_queue_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # SLA Tracking
    sla_due_date = models.DateTimeField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        db_table = 'application_queue'
        ordering = ['-priority', 'entered_queue_at']
        indexes = [
            models.Index(fields=['review_level', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['is_overdue', 'sla_due_date']),
        ]
        unique_together = [['application', 'review_level']]
    
    def __str__(self):
        return f"{self.application.application_number} - {self.get_review_level_display()} ({self.status})"
    
    def claim(self, officer):
        """Officer claims this application for review"""
        self.assigned_to = officer
        self.assigned_at = timezone.now()
        self.claimed_at = timezone.now()
        self.status = 'claimed'
        self.save()
        
        # Create review action
        ApplicationReviewAction.objects.create(
            application=self.application,
            reviewer=officer,
            review_level=self.review_level,
            action='claimed',
            notes=f'Claimed from queue by {officer.get_full_name()}'
        )
