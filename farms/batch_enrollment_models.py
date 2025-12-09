"""
YEA Poultry Program Batch/Cohort Management Models

Manages batches, cohorts, and intakes of the YEA Poultry Development Program.
Each batch represents a recruitment cycle where existing farmers apply to join
the YEA Poultry Program.

Key Concepts:
- **Batch**: A recruitment cycle (e.g., "2025 Q1 Batch - Greater Accra")
- **Batch**: Group of farmers enrolled together, trained together, receive support together
- **Cohort**: Same as batch, used interchangeably
- **Intake**: The application/enrollment period for a batch

Scenarios:
1. Independent farmer (already on platform) applies to join YEA Batch
2. Private farmer applies for government support in active intake
3. Farmer enrolled in previous batch can apply to new regional batch

Flow:
1. Admin creates new batch (e.g., "2025 Q1 Greater Accra Intake")
2. Existing farmers submit applications to join the batch
3. Applications screened through constituency → regional → national review
4. Approved farmers enrolled in batch:
   - Farm status updated to 'government_initiative'
   - Extension officer assigned
   - Support package allocated
   - Training scheduled with cohort
   - Chicks/feed distribution coordinated
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from accounts.models import User
import uuid
from datetime import timedelta


class Batch(models.Model):
    """
    YEA Poultry Program Batches/Cohorts/Intakes.
    
    Represents a recruitment cycle where farmers apply to join the YEA Poultry Program.
    Examples:
    - "2025 Q1 Batch - Greater Accra"
    - "2025 Northern Region Cohort"
    - "January 2025 National Intake"
    
    Each batch has:
    - Limited slots (e.g., 100 farmers)
    - Application period (e.g., Jan 1 - Mar 31)
    - Regional/constituency focus
    - Shared training schedule
    - Coordinated chick distribution
    """
    
    BATCH_STATUS_CHOICES = [
        ('active', 'Active - Accepting Applications'),
        ('full', 'Full - Applications Closed'),
        ('inactive', 'Inactive/Ended'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    batch_name = models.CharField(
        max_length=200,
        unique=True,
        help_text="E.g., '2025 Q1 Batch - Greater Accra', '2025 Northern Cohort'"
    )
    batch_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="E.g., 'YEA-2025-Q1-ACCRA', '2025-BATCH-01'"
    )
    
    # Regional Targeting (Optional)
    target_region = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Primary target region (e.g., 'Greater Accra', 'Ashanti'). Leave empty for national batches."
    )
    target_constituencies = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="Specific target constituencies. Leave empty if targeting entire region or national."
    )
    
    # Program Details
    description = models.TextField()
    long_description = models.TextField(
        blank=True,
        help_text="Detailed program description with objectives, implementation plan"
    )
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
    early_application_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Early application deadline for priority processing"
    )
    
    # Eligibility Criteria (Basic)
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
    
    # Eligibility Criteria (Extended - JSON for flexibility)
    eligibility_criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Extended eligibility criteria:
        {
            'citizenship': 'Ghanaian',
            'educational_level': 'Any',
            'employment_status': ['Unemployed', 'Underemployed'],
            'restrictions': ['No prior government support'],
            'preferred_qualifications': ['Prior poultry experience']
        }
        """
    )
    
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
    support_package_value_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total value of support package in GHS"
    )
    beneficiary_contribution_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Amount beneficiary must contribute"
    )
    
    # Document Requirements
    document_requirements = models.JSONField(
        default=list,
        blank=True,
        help_text="""
        Required documents for application:
        [
            {'document_type': 'Ghana Card', 'is_mandatory': true, 'description': '...'},
            {'document_type': 'Land proof', 'is_mandatory': true, 'description': '...'}
        ]
        """
    )
    
    # Batch Information
    batch_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Batch/cohort information:
        {
            'batch_code': '2025-Batch-01',
            'cohort_number': 1,
            'orientation_date': '2025-01-15',
            'distribution_dates': ['2025-02-01', '2025-03-01']
        }
        """
    )
    
    # Regional Allocation
    regional_allocation = models.JSONField(
        default=list,
        blank=True,
        help_text="""
        Slot allocation by region:
        [
            {'region': 'Greater Accra', 'allocated_slots': 20},
            {'region': 'Ashanti', 'allocated_slots': 15}
        ]
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
    allow_overbooking = models.BooleanField(
        default=False,
        help_text="Allow applications beyond total_slots"
    )
    overbooking_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Percentage overbooking allowed (e.g., 10 for 10%)"
    )
    
    # Approval Workflow
    requires_constituency_approval = models.BooleanField(
        default=True,
        help_text="Applications need constituency review"
    )
    requires_regional_approval = models.BooleanField(
        default=True,
        help_text="Applications need regional review"
    )
    requires_national_approval = models.BooleanField(
        default=True,
        help_text="Applications need national review"
    )
    approval_sla_days = models.PositiveIntegerField(
        default=30,
        help_text="Target days for application review"
    )
    
    # Funding
    funding_source = models.CharField(
        max_length=200,
        blank=True,
        help_text="E.g., 'Government of Ghana - YEA'"
    )
    budget_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="E.g., 'YEA-2025-POULTRY'"
    )
    total_budget_ghs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total budget for program in GHS"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=BATCH_STATUS_CHOICES,
        default='active',
        db_index=True
    )
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Program is active and visible"
    )
    is_accepting_applications_override = models.BooleanField(
        default=True,
        help_text="Manual override for accepting applications"
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Program is published and visible to farmers"
    )
    archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Program is archived (soft delete)"
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
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='programs_modified'
    )
    
    class Meta:
        db_table = 'farms_batch'  # Keep existing table name for backward compatibility
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status', 'application_deadline']),
            models.Index(fields=['batch_code']),
        ]
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'
    
    def __str__(self):
        return f"{self.batch_name} ({self.batch_code})"
    
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
        if not self.is_active:
            return False
        if not self.is_accepting_applications_override:
            return False
        if self.status != 'active':
            return False
        if not self.allow_overbooking and self.slots_available <= 0:
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
    
    @property
    def application_window_is_open(self):
        """Check if application window is currently open"""
        today = timezone.now().date()
        if self.start_date > today:
            return False
        if self.application_deadline and today > self.application_deadline:
            return False
        return True


class BatchEnrollmentApplication(models.Model):
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
        related_name='batch_applications',
        help_text="Existing farm applying to batch"
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='applications',
        help_text="YEA Poultry Batch/cohort farmer is applying to"
    )
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='batch_applications',
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
        unique_together = [['farm', 'batch']]  # One application per farm per batch
        indexes = [
            models.Index(fields=['status', 'priority_score']),
            models.Index(fields=['batch', 'status']),
            models.Index(fields=['applicant', 'status']),
            models.Index(fields=['current_review_level', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.application_number} - {self.farm.farm_name} → {self.batch.batch_code}"
    
    def save(self, *args, **kwargs):
        """Generate application number on first save"""
        if not self.application_number:
            year = timezone.now().year
            count = BatchEnrollmentApplication.objects.filter(
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
        if self.batch.days_until_deadline:
            if self.batch.days_until_deadline < 7:
                score += 30
            elif self.batch.days_until_deadline < 30:
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


class BatchEnrollmentReview(models.Model):
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
        BatchEnrollmentApplication,
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


class BatchEnrollmentQueue(models.Model):
    """
    Queue management for program enrollment screening.
    Similar to ApplicationQueue but for existing farmer program enrollment.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    application = models.ForeignKey(
        BatchEnrollmentApplication,
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
        related_name='assigned_batch_applications'
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

