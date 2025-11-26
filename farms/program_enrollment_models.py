"""
Government Program Enrollment Models

Handles applications from EXISTING farmers who want to join YEA or other
government support programs.

Scenarios:
1. Independent farmer (already on platform) wants to join YEA
2. Private farmer wants to access government subsidies/support
3. Government farmer wants to join additional programs

Flow:
1. Farmer submits program enrollment application
2. Application goes through screening (similar to new farmer screening)
3. Upon approval:
   - Farm registration_source updated to 'government_initiative'
   - Extension officer assigned
   - YEA program details added
   - Support package allocated
   - Government subsidies activated
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from accounts.models import User
import uuid
from datetime import timedelta


class GovernmentProgram(models.Model):
    """
    Master list of available government support programs.
    YEA, PLANTING FOR FOOD AND JOBS (Poultry), etc.
    """
    
    PROGRAM_STATUS_CHOICES = [
        ('active', 'Active - Accepting Applications'),
        ('full', 'Full - Applications Closed'),
        ('inactive', 'Inactive/Ended'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    program_name = models.CharField(
        max_length=200,
        unique=True,
        help_text="E.g., 'YEA Poultry Support Program 2025'"
    )
    program_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="E.g., 'YEA-2025-Q1'"
    )
    program_type = models.CharField(
        max_length=50,
        choices=[
            ('training_support', 'Training & Extension Support'),
            ('input_subsidy', 'Input Subsidy (Feed, Chicks, etc.)'),
            ('financial_grant', 'Financial Grant/Loan'),
            ('infrastructure', 'Infrastructure Development'),
            ('comprehensive', 'Comprehensive Support Package'),
        ],
        db_index=True
    )
    
    # Program Details
    description = models.TextField()
    implementing_agency = models.CharField(
        max_length=200,
        help_text="E.g., 'Youth Employment Agency'"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    application_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Last date to accept new applications"
    )
    
    # Eligibility Criteria
    min_farm_age_months = models.PositiveIntegerField(
        default=0,
        help_text="Minimum months farm must be operational (0 for new farms)"
    )
    max_farm_age_years = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum farm age (e.g., only for new farms < 2 years)"
    )
    min_bird_capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minimum bird capacity required"
    )
    max_bird_capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum bird capacity (if targeting small-scale)"
    )
    eligible_farmer_age_min = models.PositiveIntegerField(default=18)
    eligible_farmer_age_max = models.PositiveIntegerField(default=65)
    eligible_constituencies = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="Leave empty for all constituencies"
    )
    requires_extension_officer = models.BooleanField(default=True)
    
    # Support Package Details
    support_package_details = models.JSONField(
        default=dict,
        help_text="""
        What beneficiaries receive:
        {
            'day_old_chicks': 500,
            'feed_bags_per_cycle': 100,
            'training_sessions': 12,
            'extension_visits_per_month': 2,
            'monetary_grant': 5000.00,
            'infrastructure_support': 'Cage construction',
            'marketplace_subsidy_months': 12
        }
        """
    )
    
    # Program Capacity
    total_slots = models.PositiveIntegerField(
        help_text="Total number of farmers program can support"
    )
    slots_filled = models.PositiveIntegerField(default=0)
    slots_available = models.PositiveIntegerField(
        editable=False,
        help_text="Auto-calculated"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=PROGRAM_STATUS_CHOICES,
        default='active',
        db_index=True
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='programs_created'
    )
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status', 'application_deadline']),
            models.Index(fields=['program_code']),
        ]
    
    def __str__(self):
        return f"{self.program_name} ({self.program_code})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate available slots"""
        self.slots_available = max(0, self.total_slots - self.slots_filled)
        
        # Auto-update status based on slots
        if self.slots_available == 0:
            self.status = 'full'
        
        super().save(*args, **kwargs)
    
    @property
    def is_accepting_applications(self):
        """Check if program is currently accepting applications"""
        if self.status != 'active':
            return False
        if self.slots_available <= 0:
            return False
        if self.application_deadline and timezone.now().date() > self.application_deadline:
            return False
        return True
    
    @property
    def days_until_deadline(self):
        """Days remaining until application deadline"""
        if not self.application_deadline:
            return None
        delta = self.application_deadline - timezone.now().date()
        return max(0, delta.days)


class ProgramEnrollmentApplication(models.Model):
    """
    Application from EXISTING farmer to join a government program.
    Different from FarmApplication (which is for NEW farmers).
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft - Not Submitted'),
        ('submitted', 'Submitted - Awaiting Assignment'),
        ('eligibility_check', 'Eligibility Check'),
        ('constituency_review', 'Under Constituency Review'),
        ('regional_review', 'Under Regional Review'),
        ('national_review', 'Under National Review'),
        ('changes_requested', 'Changes Requested'),
        ('approved', 'Approved - Enrollment in Progress'),
        ('enrolled', 'Enrolled - Farmer Active in Program'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn by Farmer'),
    ]
    
    REJECTION_REASONS = [
        ('ineligible_age', 'Farmer age outside program range'),
        ('ineligible_capacity', 'Farm capacity outside program range'),
        ('ineligible_location', 'Farm not in eligible constituency'),
        ('farm_too_new', 'Farm not operational long enough'),
        ('farm_too_old', 'Farm too established for program'),
        ('program_full', 'Program slots filled'),
        ('deadline_passed', 'Application submitted after deadline'),
        ('already_enrolled', 'Already enrolled in similar program'),
        ('documentation_incomplete', 'Missing required documents'),
        ('failed_verification', 'Farm verification failed'),
        ('other', 'Other reason (see notes)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Application Tracking
    application_number = models.CharField(
        max_length=25,
        unique=True,
        editable=False,
        help_text="Format: PROG-YYYY-XXXXX"
    )
    
    # Links
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='program_applications',
        help_text="Existing farm applying to program"
    )
    program = models.ForeignKey(
        GovernmentProgram,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='program_applications',
        help_text="Farmer submitting application"
    )
    
    # Application Content
    motivation = models.TextField(
        help_text="Why farmer wants to join this program"
    )
    current_challenges = models.TextField(
        help_text="Current challenges farmer faces"
    )
    expected_benefits = models.TextField(
        help_text="How program will help farmer"
    )
    
    # Current Farm Status (Snapshot at Application Time)
    current_bird_count = models.PositiveIntegerField(
        help_text="Current number of birds on farm"
    )
    current_production_type = models.CharField(
        max_length=20,
        choices=[
            ('Layers', 'Layers (Egg Production)'),
            ('Broilers', 'Broilers (Meat Production)'),
            ('Both', 'Both Layers and Broilers')
        ]
    )
    monthly_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Average monthly revenue (optional)"
    )
    years_operational = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0)],
        help_text="Years farm has been operational"
    )
    
    # Supporting Documents
    farm_photos = ArrayField(
        models.URLField(),
        default=list,
        blank=True,
        help_text="URLs to uploaded farm photos"
    )
    business_documents = ArrayField(
        models.URLField(),
        default=list,
        blank=True,
        help_text="Business registration, permits, etc."
    )
    
    # Eligibility Assessment (Auto-calculated)
    eligibility_score = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Auto-calculated score (0-100)"
    )
    eligibility_flags = ArrayField(
        models.CharField(max_length=200),
        default=list,
        blank=True,
        help_text="Issues flagged during eligibility check"
    )
    meets_eligibility = models.BooleanField(
        default=False,
        help_text="Does farm meet program eligibility criteria?"
    )
    
    # Screening Workflow
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    current_review_level = models.CharField(
        max_length=20,
        choices=[
            ('eligibility', 'Automated Eligibility Check'),
            ('constituency', 'Constituency Level'),
            ('regional', 'Regional Level'),
            ('national', 'National Level'),
        ],
        null=True,
        blank=True
    )
    
    # Approval Timeline
    submitted_at = models.DateTimeField(null=True, blank=True)
    constituency_reviewed_at = models.DateTimeField(null=True, blank=True)
    regional_reviewed_at = models.DateTimeField(null=True, blank=True)
    national_reviewed_at = models.DateTimeField(null=True, blank=True)
    final_decision_at = models.DateTimeField(null=True, blank=True)
    
    # Approval/Rejection
    approved = models.BooleanField(default=False)
    rejection_reason = models.CharField(
        max_length=50,
        choices=REJECTION_REASONS,
        blank=True
    )
    rejection_notes = models.TextField(blank=True)
    reviewer_notes = models.TextField(
        blank=True,
        help_text="Internal notes from reviewers"
    )
    
    # Priority Scoring (for queue management)
    priority_score = models.PositiveIntegerField(
        default=0,
        help_text="Higher = more urgent"
    )
    
    # Enrollment (After Approval)
    enrollment_completed = models.BooleanField(default=False)
    enrolled_at = models.DateTimeField(null=True, blank=True)
    assigned_extension_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrolled_farmers'
    )
    support_package_allocated = models.JSONField(
        default=dict,
        blank=True,
        help_text="Actual support package farmer receives"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['farm', 'program']]  # One application per farm per program
        indexes = [
            models.Index(fields=['status', 'priority_score']),
            models.Index(fields=['program', 'status']),
            models.Index(fields=['applicant', 'status']),
            models.Index(fields=['current_review_level', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.application_number} - {self.farm.farm_name} → {self.program.program_code}"
    
    def save(self, *args, **kwargs):
        """Generate application number on first save"""
        if not self.application_number:
            year = timezone.now().year
            count = ProgramEnrollmentApplication.objects.filter(
                created_at__year=year
            ).count() + 1
            self.application_number = f"PROG-{year}-{count:05d}"
        
        super().save(*args, **kwargs)
    
    def calculate_priority_score(self):
        """
        Calculate priority score for queue management.
        Higher score = reviewed sooner.
        """
        score = 0
        
        # Time-based urgency (older applications = higher priority)
        if self.submitted_at:
            days_waiting = (timezone.now() - self.submitted_at).days
            score += min(days_waiting * 2, 50)  # Max 50 points
        
        # Farm size (smaller farms = higher priority for support)
        if self.current_bird_count < 100:
            score += 20
        elif self.current_bird_count < 500:
            score += 10
        
        # Eligibility score (higher eligibility = higher priority)
        score += self.eligibility_score // 10  # 0-10 points
        
        # Revenue (lower revenue = higher priority)
        if self.monthly_revenue:
            if self.monthly_revenue < 1000:
                score += 15
            elif self.monthly_revenue < 5000:
                score += 10
        
        # Program deadline approaching
        if self.program.days_until_deadline:
            if self.program.days_until_deadline < 7:
                score += 30
            elif self.program.days_until_deadline < 30:
                score += 15
        
        self.priority_score = min(score, 100)
        return self.priority_score
    
    @property
    def is_in_screening(self):
        """Check if application is currently being screened"""
        return self.status in [
            'submitted',
            'eligibility_check',
            'constituency_review',
            'regional_review',
            'national_review'
        ]
    
    @property
    def days_in_review(self):
        """Days since application was submitted"""
        if not self.submitted_at:
            return 0
        return (timezone.now() - self.submitted_at).days


class ProgramEnrollmentReview(models.Model):
    """
    Audit trail for program enrollment application reviews.
    Tracks all actions taken during screening.
    """
    
    ACTION_CHOICES = [
        ('submitted', 'Application Submitted'),
        ('eligibility_passed', 'Passed Eligibility Check'),
        ('eligibility_failed', 'Failed Eligibility Check'),
        ('assigned', 'Assigned to Reviewer'),
        ('claimed', 'Claimed for Review'),
        ('approved', 'Approved at Level'),
        ('rejected', 'Rejected'),
        ('changes_requested', 'Changes Requested'),
        ('withdrawn', 'Withdrawn by Farmer'),
        ('enrolled', 'Enrollment Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    application = models.ForeignKey(
        ProgramEnrollmentApplication,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='program_reviews'
    )
    review_level = models.CharField(
        max_length=20,
        choices=[
            ('eligibility', 'Eligibility Check'),
            ('constituency', 'Constituency'),
            ('regional', 'Regional'),
            ('national', 'National'),
        ]
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['application', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.application.application_number} ({self.review_level})"


class ProgramEnrollmentQueue(models.Model):
    """
    Queue management for program enrollment screening.
    Similar to ApplicationQueue but for existing farmer program enrollment.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    application = models.ForeignKey(
        ProgramEnrollmentApplication,
        on_delete=models.CASCADE,
        related_name='queue_entries'
    )
    review_level = models.CharField(
        max_length=20,
        choices=[
            ('eligibility', 'Eligibility Check'),
            ('constituency', 'Constituency'),
            ('regional', 'Regional'),
            ('national', 'National'),
        ]
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Assignment'),
            ('assigned', 'Assigned to Officer'),
            ('in_review', 'Under Review'),
            ('completed', 'Completed'),
        ],
        default='pending',
        db_index=True
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_program_applications'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # Priority & SLA
    priority = models.PositiveIntegerField(default=0)
    sla_deadline = models.DateTimeField(
        help_text="When this review level should be completed"
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-priority', 'sla_deadline']
        unique_together = [['application', 'review_level']]
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['review_level', 'sla_deadline']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"{self.application.application_number} - {self.review_level} ({self.status})"
    
    @property
    def is_overdue(self):
        """Check if review is past SLA deadline"""
        return timezone.now() > self.sla_deadline and self.status != 'completed'
    
    def claim(self, officer):
        """Officer claims this application for review"""
        self.assigned_to = officer
        self.assigned_at = timezone.now()
        self.status = 'in_review'
        self.save()
