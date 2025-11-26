"""
Farm Registration Models

Based on comprehensive FARM_REGISTRATION_MODEL.md specification.
Implements multi-model structure for farm registration with:
- Farm owner/operator details
- Business information (TIN mandatory)
- Multiple farm locations with GPS
- Infrastructure and equipment inventory
- Production planning
- Support needs assessment
- Document management
- Financial tracking
- Application workflow
- Invitation system and spam prevention
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.utils import timezone
from decimal import Decimal
from phonenumber_field.modelfields import PhoneNumberField
from accounts.models import User
import uuid
import re

# Import invitation and spam prevention models
from .invitation_models import (
    FarmInvitation,
    RegistrationApproval,
    VerificationToken,
    RegistrationRateLimit
)

# Import application models (apply-first workflow)
from .application_models import (
    FarmApplication,
    ApplicationReviewAction,
    ApplicationQueue
)

# Import program enrollment models (existing farmers joining government programs)
from .program_enrollment_models import (
    GovernmentProgram,
    ProgramEnrollmentApplication,
    ProgramEnrollmentReview,
    ProgramEnrollmentQueue
)


# =============================================================================
# VALIDATORS
# =============================================================================

def validate_ghana_card(value):
    """Validate Ghana Card format: GHA-XXXXXXXXX-X"""
    pattern = r'^GHA-\d{9}-\d$'
    if not re.match(pattern, value):
        raise models.ValidationError(
            f'{value} is not a valid Ghana Card number. Format: GHA-XXXXXXXXX-X'
        )


def validate_tin(value):
    """Validate TIN format (assuming 10-11 digit format for Ghana)"""
    pattern = r'^\d{10,11}$'
    if not re.match(pattern, value):
        raise models.ValidationError(
            f'{value} is not a valid TIN. Must be 10-11 digits.'
        )


def validate_age_range(dob):
    """Validate farmer is between 18-65 years old"""
    from datetime import date
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18 or age > 65:
        raise models.ValidationError(
            f'Farmer must be between 18 and 65 years old. Current age: {age}'
        )


# =============================================================================
# FARM MODEL (Main Registration)
# =============================================================================

class Farm(models.Model):
    """
    Main farm registration model.
    One farm per user (farmer account).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Application Tracking
    application_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        help_text="Format: APP-YYYY-XXXXX"
    )
    farm_id = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Format: YEA-REG-CONST-XXXX (assigned on approval)"
    )
    
    # Owner/Operator
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='farm'
    )
    
    # SECTION 1: PERSONAL IDENTITY
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(validators=[validate_age_range])
    gender = models.CharField(
        max_length=20,
        choices=[
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Other', 'Other'),
            ('Prefer not to say', 'Prefer not to say')
        ]
    )
    ghana_card_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[validate_ghana_card],
        help_text="Format: GHA-XXXXXXXXX-X"
    )
    marital_status = models.CharField(
        max_length=20,
        choices=[
            ('Single', 'Single'),
            ('Married', 'Married'),
            ('Divorced', 'Divorced'),
            ('Widowed', 'Widowed')
        ],
        blank=True
    )
    number_of_dependents = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(50)]
    )
    
    # SECTION 1.2: CONTACT INFORMATION
    primary_phone = PhoneNumberField(region='GH', unique=True)
    alternate_phone = PhoneNumberField(region='GH', blank=True)
    email = models.EmailField(blank=True)
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[
            ('Phone Call', 'Phone Call'),
            ('SMS', 'SMS'),
            ('WhatsApp', 'WhatsApp'),
            ('Email', 'Email')
        ],
        default='Phone Call'
    )
    residential_address = models.TextField()
    
    # Constituency (UNIVERSAL REQUIREMENT for all farmers)
    primary_constituency = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Constituency where farm is located - REQUIRED for ALL farmers (government and independent)"
    )
    
    # SECTION 1.3: NEXT OF KIN
    nok_full_name = models.CharField(max_length=200, verbose_name="Next of Kin Full Name")
    nok_relationship = models.CharField(max_length=100, verbose_name="Next of Kin Relationship")
    nok_phone = PhoneNumberField(region='GH', verbose_name="Next of Kin Phone")
    nok_residential_address = models.TextField(verbose_name="Next of Kin Address", blank=True)
    
    # SECTION 1.4: EDUCATION & EXPERIENCE
    education_level = models.CharField(
        max_length=50,
        choices=[
            ('No Formal Education', 'No Formal Education'),
            ('Primary', 'Primary'),
            ('JHS', 'JHS'),
            ('SHS/Technical', 'SHS/Technical'),
            ('Tertiary', 'Tertiary'),
            ('Postgraduate', 'Postgraduate')
        ]
    )
    literacy_level = models.CharField(
        max_length=50,
        choices=[
            ('Cannot Read/Write', 'Cannot Read/Write'),
            ('Can Read Only', 'Can Read Only'),
            ('Can Read & Write', 'Can Read & Write')
        ]
    )
    years_in_poultry = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    previous_training = models.TextField(blank=True, help_text="Previous poultry training received")
    farming_full_time = models.BooleanField(default=False)
    other_occupation = models.CharField(max_length=200, blank=True)
    
    # SECTION 2: BUSINESS INFORMATION
    farm_name = models.CharField(max_length=200, unique=True)
    ownership_type = models.CharField(
        max_length=50,
        choices=[
            ('Sole Proprietorship', 'Sole Proprietorship'),
            ('Partnership', 'Partnership'),
            ('Family Business', 'Family Business'),
            ('Cooperative', 'Cooperative'),
            ('Limited Company', 'Limited Company')
        ]
    )
    
    # TIN is MANDATORY
    tin = models.CharField(
        max_length=11,
        unique=True,
        validators=[validate_tin],
        help_text="Tax Identification Number (MANDATORY)"
    )
    
    # Business Registration (Encouraged with Incentives)
    business_registration_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Strongly encouraged for procurement priority"
    )
    business_registration_date = models.DateField(null=True, blank=True)
    
    # Banking Details
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    mobile_money_provider = models.CharField(
        max_length=50,
        choices=[
            ('MTN Mobile Money', 'MTN Mobile Money'),
            ('Vodafone Cash', 'Vodafone Cash'),
            ('AirtelTigo Money', 'AirtelTigo Money'),
            ('Telecel Cash', 'Telecel Cash')
        ],
        blank=True
    )
    mobile_money_number = PhoneNumberField(region='GH', blank=True)
    
    # Paystack Subaccount (for direct farmer settlements)
    paystack_subaccount_code = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        db_index=True,
        help_text="Paystack subaccount code for direct settlements"
    )
    paystack_subaccount_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Paystack subaccount ID"
    )
    paystack_settlement_account = models.CharField(
        max_length=50,
        blank=True,
        help_text="Account number used for Paystack settlements"
    )
    subaccount_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When Paystack subaccount was created"
    )
    subaccount_active = models.BooleanField(
        default=False,
        help_text="Whether Paystack subaccount is active"
    )
    
    # SECTION 4: INFRASTRUCTURE
    number_of_poultry_houses = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total_bird_capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    current_bird_count = models.PositiveIntegerField(default=0)
    housing_type = models.CharField(
        max_length=50,
        choices=[
            ('Deep Litter', 'Deep Litter'),
            ('Battery Cage', 'Battery Cage'),
            ('Free Range', 'Free Range'),
            ('Semi-Intensive', 'Semi-Intensive'),
            ('Mixed', 'Mixed')
        ]
    )
    total_infrastructure_value_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total value of infrastructure for ROI tracking"
    )
    
    # SECTION 5: PRODUCTION PLANNING
    primary_production_type = models.CharField(
        max_length=20,
        choices=[
            ('Layers', 'Layers (Egg Production)'),
            ('Broilers', 'Broilers (Meat Production)'),
            ('Both', 'Both Layers and Broilers')
        ]
    )
    
    # Layers Production
    layer_breed = models.CharField(
        max_length=100,
        blank=True,
        help_text="Required if primary_production_type includes Layers"
    )
    planned_monthly_egg_production = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="REQUIRED if Layers"
    )
    
    # Broilers Production
    broiler_breed = models.CharField(
        max_length=100,
        blank=True,
        help_text="Required if primary_production_type includes Broilers"
    )
    planned_monthly_bird_sales = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="REQUIRED if Broilers"
    )
    
    # Common Production Fields
    planned_production_start_date = models.DateField(
        help_text="MANDATORY - When will commercial production begin"
    )
    hatchery_operation = models.BooleanField(default=False)
    feed_formulation = models.BooleanField(default=False)
    
    # SECTION 7: FINANCIAL INFORMATION (ALL MANDATORY)
    initial_investment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(10000000)],
        help_text="Farmer's capital invested (MANDATORY)"
    )
    funding_source = ArrayField(
        models.CharField(max_length=50),
        help_text="Multi-select: Personal Savings, Family, Loan, Grant, Other"
    )
    monthly_operating_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1000000)],
        help_text="Estimated monthly expenses (MANDATORY)"
    )
    expected_monthly_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1000000)],
        help_text="Revenue projection (MANDATORY)"
    )
    has_outstanding_debt = models.BooleanField(default=False)
    debt_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10000000)],
        help_text="Required if has_outstanding_debt = True"
    )
    debt_purpose = models.CharField(max_length=200, blank=True)
    monthly_debt_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100000)]
    )
    
    # SECTION 9: APPLICATION WORKFLOW
    application_status = models.CharField(
        max_length=30,
        choices=[
            ('Draft', 'Draft'),
            ('Submitted', 'Submitted - Pending Assignment'),
            ('Constituency Review', 'Under Constituency Review'),
            ('Regional Review', 'Under Regional Review'),
            ('National Review', 'Under National Review'),
            ('Changes Requested', 'Changes Requested by Reviewer'),
            ('Approved', 'Approved - Farm ID Assigned'),
            ('Rejected', 'Rejected'),
        ],
        default='Draft',
        db_index=True
    )
    farm_status = models.CharField(
        max_length=20,
        choices=[
            ('Active', 'Active'),
            ('Inactive', 'Inactive'),
            ('Suspended', 'Suspended')
        ],
        null=True,
        blank=True
    )
    
    # Current Review Level Tracking
    current_review_level = models.CharField(
        max_length=20,
        choices=[
            ('constituency', 'Constituency Level'),
            ('regional', 'Regional Level'),
            ('national', 'National Level'),
        ],
        null=True,
        blank=True,
        help_text="Current stage in approval workflow"
    )
    
    # Approval Dates (for tracking progress)
    constituency_approved_at = models.DateTimeField(null=True, blank=True)
    regional_approved_at = models.DateTimeField(null=True, blank=True)
    final_approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    
    # Review & Approval
    assigned_extension_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_farms_as_extension_officer'
    )
    assigned_reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_farms_as_reviewer'
    )
    review_comments = models.TextField(blank=True)
    site_visit_required = models.BooleanField(default=False)
    site_visit_date = models.DateField(null=True, blank=True)
    site_visit_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    more_info_requested = models.TextField(blank=True)
    
    approval_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_farms'
    )
    activation_date = models.DateTimeField(null=True, blank=True)
    
    # Benefit Package (JSON)
    benefit_package_assigned = models.JSONField(null=True, blank=True)
    
    # ============================================================================
    # SECTION 9B: DUAL FARMER ONBOARDING (Government vs Independent)
    # ============================================================================
    
    REGISTRATION_SOURCE_CHOICES = [
        ('government_initiative', 'YEA Government Initiative'),
        ('self_registered', 'Self-Registered/Independent'),
        ('migrated', 'Migrated from External System'),
    ]
    
    registration_source = models.CharField(
        max_length=30,
        choices=REGISTRATION_SOURCE_CHOICES,
        default='self_registered',
        db_index=True,
        help_text="How the farmer joined the platform"
    )
    
    # Government Initiative Specific Fields
    yea_program_batch = models.CharField(
        max_length=50,
        blank=True,
        help_text="YEA batch/cohort (e.g., 'YEA-2025-Q1')"
    )
    yea_program_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When farmer joined government program"
    )
    yea_program_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected program completion date"
    )
    government_support_package = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Details of government support received:
        {
            'day_old_chicks': 500,
            'feed_bags': 100,
            'training_sessions': 5,
            'extension_visits': 12,
            'subsidy_amount': 5000.00
        }
        """
    )
    extension_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_farms',
        help_text="Extension officer assigned to farmer. REQUIRED for government farmers, OPTIONAL (but recommended) for independent farmers based on constituency."
    )
    
    # Independent Farmer Specific Fields
    established_since = models.DateField(
        null=True,
        blank=True,
        help_text="For established farmers: when farm was originally established"
    )
    previous_management_system = models.CharField(
        max_length=100,
        blank=True,
        help_text="Manual/Excel/Other system used before joining platform"
    )
    referral_source = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('search_engine', 'Google/Search Engine'),
            ('social_media', 'Facebook/Instagram/Twitter'),
            ('farmer_referral', 'Referred by Another Farmer'),
            ('industry_event', 'Agricultural Fair/Conference'),
            ('advertisement', 'Advertisement'),
            ('other', 'Other'),
        ],
        help_text="How independent farmer heard about platform"
    )
    
    # Fast-Track Approval for Established Farmers
    fast_track_eligible = models.BooleanField(
        default=False,
        help_text="Eligible for simplified approval (established farmers with documentation)"
    )
    fast_track_criteria_met = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Criteria for fast-track approval:
        {
            'business_registered': True,
            'tin_verified': True,
            'existing_operations': True,
            'documentation_complete': True,
            'references_provided': True
        }
        """
    )
    
    # Approval Workflow Type
    APPROVAL_WORKFLOW_CHOICES = [
        ('full_government', 'Full 3-Tier Government Review'),
        ('simplified', 'Simplified Verification'),
        ('auto_approve', 'Auto-Approve with Basic Checks'),
    ]
    
    approval_workflow = models.CharField(
        max_length=30,
        choices=APPROVAL_WORKFLOW_CHOICES,
        blank=True,
        help_text="Auto-set based on registration_source and fast_track_eligible"
    )
    
    # ============================================================================
    # SECTION 9C: MARKETPLACE SUBSCRIPTION (OPTIONAL)
    # ============================================================================
    
    SUBSCRIPTION_TYPE_CHOICES = [
        ('none', 'No Subscription (Free Core Platform)'),
        ('government_subsidized', 'Government-Subsidized Marketplace (Free/Reduced)'),
        ('standard', 'Standard Marketplace Subscription (GHS 100/month)'),
        ('premium', 'Premium Subscription (Future)'),
    ]
    
    subscription_type = models.CharField(
        max_length=30,
        choices=SUBSCRIPTION_TYPE_CHOICES,
        default='none',
        help_text="Type of marketplace subscription"
    )
    
    marketplace_enabled = models.BooleanField(
        default=False,
        help_text="Is marketplace access enabled (requires subscription)"
    )
    
    product_images_count = models.PositiveIntegerField(
        default=0,
        help_text="Current number of product images (max 20 with subscription)"
    )
    
    # Government Subsidy Tracking
    government_subsidy_active = models.BooleanField(
        default=False,
        help_text="Is farmer receiving government marketplace subscription subsidy"
    )
    government_subsidy_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When government marketplace subsidy started"
    )
    government_subsidy_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When government marketplace subsidy expires"
    )
    
    # SECTION 10: CALCULATED METRICS
    farm_readiness_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Auto-calculated based on infrastructure checklist"
    )
    biosecurity_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Count of biosecurity measures / total × 100"
    )
    capacity_utilization = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="(current_birds / total_capacity) × 100"
    )
    experience_level = models.CharField(
        max_length=20,
        choices=[
            ('Beginner', 'Beginner (0-1 years)'),
            ('Intermediate', 'Intermediate (2-5 years)'),
            ('Expert', 'Expert (5+ years)')
        ],
        blank=True
    )
    support_priority_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Based on needs, readiness, location"
    )
    financial_health_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Revenue vs Expenses, Debt-to-Asset ratio"
    )
    total_investment_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Auto-calculated: infrastructure + equipment + initial capital"
    )
    
    # Timestamps
    application_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farms'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application_id']),
            models.Index(fields=['farm_id']),
            models.Index(fields=['ghana_card_number']),
            models.Index(fields=['tin']),
            models.Index(fields=['application_status']),
            models.Index(fields=['farm_status']),
            # New indexes for dual farmer onboarding
            models.Index(fields=['registration_source']),
            models.Index(fields=['approval_workflow']),
            models.Index(fields=['subscription_type']),
            models.Index(fields=['marketplace_enabled']),
            models.Index(fields=['extension_officer']),
            models.Index(fields=['fast_track_eligible']),
            models.Index(fields=['primary_constituency']),
            models.Index(fields=['registration_source', 'primary_constituency']),
        ]
    
    def __str__(self):
        return f"{self.farm_name} ({self.application_id})"
    
    def save(self, *args, **kwargs):
        # Generate application ID on first save
        if not self.application_id:
            from datetime import datetime
            year = datetime.now().year
            # Get last application number for this year
            last_app = Farm.objects.filter(
                application_id__startswith=f'APP-{year}-'
            ).order_by('-application_id').first()
            
            if last_app:
                last_num = int(last_app.application_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.application_id = f'APP-{year}-{new_num:05d}'
        
        # Auto-determine approval workflow based on farmer type
        if not self.approval_workflow:
            self.approval_workflow = self._determine_approval_workflow()
        
        # Auto-determine subscription type based on farmer type
        if not self.subscription_type or self.subscription_type == 'none':
            self.subscription_type = self._determine_subscription_type()
        
        # Auto-calculate capacity utilization
        if self.total_bird_capacity > 0:
            self.capacity_utilization = (
                Decimal(self.current_bird_count) / Decimal(self.total_bird_capacity)
            ) * 100
        
        # Auto-calculate experience level
        if self.years_in_poultry <= 1:
            self.experience_level = 'Beginner'
        elif self.years_in_poultry <= 5:
            self.experience_level = 'Intermediate'
        else:
            self.experience_level = 'Expert'
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate business logic"""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # Validate current birds <= capacity
        if self.current_bird_count > self.total_bird_capacity:
            errors['current_bird_count'] = 'Current bird count cannot exceed total capacity'
        
        # Validate production type requirements
        if self.primary_production_type in ['Layers', 'Both']:
            if not self.layer_breed:
                errors['layer_breed'] = 'Layer breed is required for Layers production'
            if not self.planned_monthly_egg_production:
                errors['planned_monthly_egg_production'] = 'Monthly egg production is required for Layers'
        
        if self.primary_production_type in ['Broilers', 'Both']:
            if not self.broiler_breed:
                errors['broiler_breed'] = 'Broiler breed is required for Broilers production'
            if not self.planned_monthly_bird_sales:
                errors['planned_monthly_bird_sales'] = 'Monthly bird sales is required for Broilers'
        
        # Validate debt information
        if self.has_outstanding_debt and not self.debt_amount:
            errors['debt_amount'] = 'Debt amount is required when outstanding debt exists'
        
        # Validate government farmers have required fields
        if self.registration_source == 'government_initiative':
            if not self.extension_officer:
                errors['extension_officer'] = 'Extension officer is REQUIRED for government initiative farmers'
            if not self.yea_program_batch:
                errors['yea_program_batch'] = 'YEA program batch is required for government farmers'
        
        # Validate constituency is provided (universal requirement)
        if not self.primary_constituency:
            errors['primary_constituency'] = 'Constituency is REQUIRED for all farmers'
        
        if errors:
            raise ValidationError(errors)
    
    # ============================================================================
    # DUAL FARMER ONBOARDING METHODS
    # ============================================================================
    
    def _determine_approval_workflow(self):
        """
        Auto-determine approval workflow based on registration source.
        Called automatically in save() method.
        
        Rules:
        - Government farmers → full_government (3-tier review)
        - Independent farmers → auto_approve (instant access)
        - Migrated farms → simplified (single verification)
        """
        if self.registration_source == 'government_initiative':
            # Government farmers always get full 3-tier review
            return 'full_government'
        
        elif self.registration_source == 'self_registered':
            # ALL independent farmers get automatic approval
            return 'auto_approve'
        
        # Migrated farms from external systems get simplified review
        return 'simplified'
    
    def _meets_auto_approve_criteria(self):
        """
        Check if farmer meets enhanced verification criteria.
        Currently not used for workflow determination (all independent farmers auto-approved),
        but kept for potential fast-track marketplace access or priority support.
        
        Criteria:
        - TIN provided and valid
        - Business registration provided
        - Bank account information provided
        - No prior rejections
        """
        criteria = [
            bool(self.tin),
            bool(self.business_registration_number),
            bool(self.bank_name and self.account_number),
            not bool(self.rejection_reason),
        ]
        return all(criteria)
    
    def _determine_subscription_type(self):
        """
        Auto-determine subscription type based on registration source.
        Called automatically in save() method.
        """
        if self.registration_source == 'government_initiative':
            # Government farmers get subsidized marketplace if they opt in
            if self.government_subsidy_active:
                return 'government_subsidized'
            return 'none'  # Core platform only until they opt into marketplace
        
        elif self.registration_source == 'self_registered':
            # Independent farmers default to no subscription (free core)
            # They can upgrade to marketplace subscription later
            return self.subscription_type if self.subscription_type else 'none'
        
        return 'none'
    
    @property
    def is_government_farmer(self):
        """Check if farmer is part of government initiative"""
        return self.registration_source == 'government_initiative'
    
    @property
    def is_independent_farmer(self):
        """Check if farmer is independent/self-registered"""
        return self.registration_source == 'self_registered'
    
    @property
    def requires_extension_officer(self):
        """
        Check if farmer REQUIRES extension officer supervision.
        
        Returns:
        - True: Government farmers (mandatory supervision)
        - False: Independent farmers (optional but recommended)
        
        Note: Independent farmers CAN have extension officers assigned based on
        constituency, but it's not mandatory for their registration.
        """
        return self.is_government_farmer
    
    @property
    def has_marketplace_access(self):
        """Check if farmer has active marketplace access"""
        return self.marketplace_enabled and self.subscription_type in [
            'government_subsidized',
            'standard',
            'premium'
        ]
    
    @property
    def eligible_for_government_procurement(self):
        """Check if eligible for government bulk orders"""
        return (
            self.application_status == 'Approved' and
            self.farm_status == 'Active' and
            (self.is_government_farmer or bool(self.business_registration_number))
        )
    
    @property
    def core_platform_accessible(self):
        """
        Core farm management is ALWAYS accessible regardless of subscription.
        Returns True for all approved farmers.
        """
        return self.application_status == 'Approved'


# =============================================================================
# FARM LOCATION MODEL
# =============================================================================

class FarmLocation(gis_models.Model):
    """
    Farm location with GPS coordinates.
    Multiple locations per farm supported.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='locations')
    
    # GPS Data
    gps_address_string = models.CharField(
        max_length=200,
        help_text="From Ghana GPS app (e.g., AK-0123-4567)"
    )
    location = gis_models.PointField(
        help_text="Auto-extracted from GPS address string"
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7, editable=False)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, editable=False)
    
    # Administrative Divisions
    region = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    constituency = models.CharField(max_length=100)
    community = models.CharField(max_length=200)
    
    # Location Details
    nearest_landmark = models.CharField(max_length=200, blank=True)
    distance_from_main_road_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    road_accessibility = models.CharField(
        max_length=50,
        choices=[
            ('All Year', 'Accessible All Year'),
            ('Dry Season Only', 'Dry Season Only'),
            ('Limited', 'Limited Access')
        ]
    )
    
    # Land Information
    land_size_acres = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    land_ownership_status = models.CharField(
        max_length=50,
        choices=[
            ('Owned', 'Owned'),
            ('Leased', 'Leased'),
            ('Family Land', 'Family Land'),
            ('Government Allocation', 'Government Allocation')
        ]
    )
    lease_expiry_date = models.DateField(null=True, blank=True)
    
    # Validation
    is_primary_location = models.BooleanField(default=False)
    gps_verified = models.BooleanField(
        default=False,
        help_text="GPS within Ghana boundaries verified"
    )
    constituency_match_verified = models.BooleanField(
        default=False,
        help_text="Stated constituency matches GPS location"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farm_locations'
        ordering = ['-is_primary_location', 'created_at']
        unique_together = [('farm', 'gps_address_string')]
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.community}, {self.constituency}"
    
    def save(self, *args, **kwargs):
        # Extract lat/long from Point
        if self.location:
            self.longitude = self.location.x
            self.latitude = self.location.y
        
        super().save(*args, **kwargs)


# =============================================================================
# POULTRY HOUSE MODEL
# =============================================================================

class PoultryHouse(models.Model):
    """Individual poultry house details"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='poultry_houses')
    
    house_number = models.CharField(max_length=50)
    house_type = models.CharField(
        max_length=50,
        choices=[
            ('Deep Litter', 'Deep Litter'),
            ('Battery Cage', 'Battery Cage'),
            ('Free Range Shelter', 'Free Range Shelter'),
            ('Brooder House', 'Brooder House'),
            ('Layer House', 'Layer House'),
            ('Grower House', 'Grower House')
        ]
    )
    house_capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    current_occupancy = models.PositiveIntegerField(default=0)
    
    # Dimensions
    length_meters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    width_meters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    height_meters = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Construction
    construction_material = models.CharField(
        max_length=100,
        help_text="e.g., Concrete blocks, Wood, Bamboo"
    )
    roofing_material = models.CharField(
        max_length=100,
        help_text="e.g., Aluminum sheets, Thatch"
    )
    flooring_type = models.CharField(max_length=100)
    year_built = models.PositiveIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )
    
    # Ventilation
    ventilation_system = models.CharField(
        max_length=50,
        choices=[
            ('Natural', 'Natural'),
            ('Mechanical (Fans)', 'Mechanical (Fans)'),
            ('Both', 'Both Natural and Mechanical')
        ]
    )
    number_of_fans = models.PositiveIntegerField(default=0)
    
    # Valuation
    estimated_house_value_ghs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="For investment tracking"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'poultry_houses'
        ordering = ['house_number']
        unique_together = [('farm', 'house_number')]
    
    def __str__(self):
        return f"{self.farm.farm_name} - House {self.house_number}"


# =============================================================================
# EQUIPMENT MODEL
# =============================================================================

class Equipment(models.Model):
    """Farm equipment inventory"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='equipment')
    
    # Feeders
    manual_feeders_count = models.PositiveIntegerField(default=0)
    manual_feeders_value_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    automatic_feeders_count = models.PositiveIntegerField(default=0)
    automatic_feeders_value_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Drinkers
    manual_drinkers_count = models.PositiveIntegerField(default=0)
    manual_drinkers_value_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    nipple_drinkers_count = models.PositiveIntegerField(default=0)
    nipple_drinkers_value_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Incubation
    has_incubator = models.BooleanField(default=False)
    incubator_capacity = models.PositiveIntegerField(default=0)
    incubator_value_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Power Backup
    has_generator = models.BooleanField(default=False)
    generator_capacity_kva = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    generator_value_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Storage
    feed_storage_capacity_kg = models.PositiveIntegerField(default=0)
    feed_storage_value_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    cold_storage_available = models.BooleanField(default=False)
    cold_storage_value_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Other Equipment
    weighing_scale = models.BooleanField(default=False)
    egg_tray_count = models.PositiveIntegerField(default=0)
    cages_count = models.PositiveIntegerField(default=0)
    cages_value_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farm_equipment'
    
    def __str__(self):
        return f"{self.farm.farm_name} - Equipment"
    
    @property
    def total_equipment_value(self):
        """Calculate total equipment value"""
        return (
            self.manual_feeders_value_ghs +
            self.automatic_feeders_value_ghs +
            self.manual_drinkers_value_ghs +
            self.nipple_drinkers_value_ghs +
            self.incubator_value_ghs +
            self.generator_value_ghs +
            self.feed_storage_value_ghs +
            self.cold_storage_value_ghs +
            self.cages_value_ghs
        )


# =============================================================================
# UTILITIES MODEL
# =============================================================================

class Utilities(models.Model):
    """Farm utilities and services"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.OneToOneField(Farm, on_delete=models.CASCADE, related_name='utilities')
    
    # Water
    water_source = ArrayField(
        models.CharField(max_length=50),
        help_text="Multi-select: Borehole, Well, Pipe-borne, River/Stream, Rainwater"
    )
    water_availability = models.CharField(
        max_length=50,
        choices=[
            ('Year-round', 'Year-round'),
            ('Seasonal', 'Seasonal'),
            ('Unreliable', 'Unreliable')
        ]
    )
    water_storage_capacity_liters = models.PositiveIntegerField(default=0)
    
    # Electricity
    electricity_source = models.CharField(
        max_length=50,
        choices=[
            ('National Grid', 'National Grid'),
            ('Solar', 'Solar'),
            ('Generator', 'Generator Only'),
            ('Hybrid', 'Hybrid (Grid + Solar/Generator)'),
            ('None', 'No Electricity')
        ]
    )
    electricity_reliability = models.CharField(
        max_length=50,
        choices=[
            ('Stable', 'Stable'),
            ('Frequent Outages', 'Frequent Outages'),
            ('Unreliable', 'Unreliable')
        ],
        blank=True
    )
    solar_panel_installed = models.BooleanField(default=False)
    solar_capacity_watts = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farm_utilities'
        verbose_name_plural = 'Utilities'
    
    def __str__(self):
        return f"{self.farm.farm_name} - Utilities"


# =============================================================================
# BIOSECURITY MODEL
# =============================================================================

class Biosecurity(models.Model):
    """Farm biosecurity measures"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.OneToOneField(Farm, on_delete=models.CASCADE, related_name='biosecurity')
    
    # Fencing & Access Control
    perimeter_fencing = models.BooleanField(default=False)
    fencing_type = models.CharField(max_length=100, blank=True)
    controlled_entry_points = models.BooleanField(default=False)
    visitor_log_maintained = models.BooleanField(default=False)
    
    # Sanitation
    footbath_at_entry = models.BooleanField(default=False)
    disinfectant_used = models.CharField(max_length=100, blank=True)
    hand_washing_facilities = models.BooleanField(default=False)
    dedicated_farm_clothing = models.BooleanField(default=False)
    
    # Disease Prevention
    quarantine_area = models.BooleanField(default=False)
    sick_bird_isolation = models.BooleanField(default=False)
    regular_vaccination = models.BooleanField(default=False)
    vaccination_records_kept = models.BooleanField(default=False)
    
    # Waste Management
    manure_management_system = models.CharField(
        max_length=50,
        choices=[
            ('Composting', 'Composting'),
            ('Biogas', 'Biogas'),
            ('Direct Sale', 'Direct Sale'),
            ('On-farm Use', 'On-farm Use'),
            ('No System', 'No Formal System')
        ],
        blank=True
    )
    dead_bird_disposal = models.CharField(
        max_length=50,
        choices=[
            ('Burial', 'Burial'),
            ('Incineration', 'Incineration'),
            ('Composting', 'Composting'),
            ('Other', 'Other')
        ],
        blank=True
    )
    
    # Pest Control
    rodent_control_program = models.BooleanField(default=False)
    wild_bird_exclusion = models.BooleanField(default=False)
    
    # Score (auto-calculated)
    biosecurity_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Count of measures / total × 100"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farm_biosecurity'
        verbose_name_plural = 'Biosecurity'
    
    def __str__(self):
        return f"{self.farm.farm_name} - Biosecurity"
    
    def calculate_biosecurity_score(self):
        """Calculate biosecurity score based on implemented measures"""
        total_measures = 16  # Total boolean fields
        implemented = sum([
            self.perimeter_fencing,
            self.controlled_entry_points,
            self.visitor_log_maintained,
            self.footbath_at_entry,
            bool(self.disinfectant_used),
            self.hand_washing_facilities,
            self.dedicated_farm_clothing,
            self.quarantine_area,
            self.sick_bird_isolation,
            self.regular_vaccination,
            self.vaccination_records_kept,
            bool(self.manure_management_system and self.manure_management_system != 'No System'),
            bool(self.dead_bird_disposal),
            self.rodent_control_program,
            self.wild_bird_exclusion,
            bool(self.fencing_type)
        ])
        
        self.biosecurity_score = (Decimal(implemented) / Decimal(total_measures)) * 100
        return self.biosecurity_score


# =============================================================================
# SUPPORT NEEDS MODEL
# =============================================================================

class SupportNeeds(models.Model):
    """
    Farmer support needs assessment.
    Updated periodically (Quarterly → Bi-annually)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='support_needs')
    
    assessment_date = models.DateField(auto_now_add=True)
    assessment_type = models.CharField(
        max_length=20,
        choices=[
            ('Initial', 'Initial (At Registration)'),
            ('Quarterly', 'Quarterly Review'),
            ('Bi-annual', 'Bi-annual Review'),
            ('Ad-hoc', 'Ad-hoc (Farmer Requested)')
        ]
    )
    
    # Support Categories (Multi-select via separate model or ArrayField)
    technical_support_needed = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text="Disease management, Feeding, Housing, etc."
    )
    
    financial_support_needed = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text="Working capital, Equipment financing, etc."
    )
    
    market_access_support = models.BooleanField(default=False)
    input_supply_support = models.BooleanField(default=False)
    
    # Priority Level
    overall_priority = models.CharField(
        max_length=20,
        choices=[
            ('Critical', 'Critical'),
            ('High', 'High'),
            ('Medium', 'Medium'),
            ('Low', 'Low')
        ],
        default='Medium'
    )
    
    # Challenges
    major_challenges = models.TextField(
        blank=True,
        max_length=1000,
        help_text="Open-ended challenges"
    )
    specific_equipment_needs = models.TextField(
        blank=True,
        max_length=500,
        help_text="What equipment is lacking"
    )
    
    # Training Interests
    training_interests = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text="Disease Management, Feed Formulation, Record Keeping, etc."
    )
    
    # Tracking
    support_provided = models.TextField(blank=True)
    effectiveness_notes = models.TextField(blank=True)
    next_assessment_due = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'support_needs'
        ordering = ['-assessment_date']
        verbose_name_plural = 'Support Needs'
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.assessment_type} ({self.assessment_date})"


# =============================================================================
# FARM DOCUMENTS MODEL
# =============================================================================

class FarmDocument(models.Model):
    """Farm-related document uploads"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='documents')
    
    document_type = models.CharField(
        max_length=50,
        choices=[
            # Required Documents
            ('Ghana Card', 'Ghana Card Photo'),
            ('Passport Photo', 'Passport Photo'),
            ('Farm Photo - Exterior', 'Farm Photo - Poultry House Exterior'),
            ('Farm Photo - Interior', 'Farm Photo - Poultry House Interior'),
            ('Farm Photo - Layout', 'Farm Photo - Overall Farm Layout'),
            
            # Recommended Documents
            ('Farm Photo - Feeding', 'Farm Photo - Feeding System'),
            ('Farm Photo - Water', 'Farm Photo - Water System'),
            ('Farm Photo - Equipment', 'Farm Photo - Equipment'),
            ('Farm Photo - Storage', 'Farm Photo - Storage Facilities'),
            ('Farm Photo - Biosecurity', 'Farm Photo - Biosecurity Measures'),
            
            # Land Documents
            ('Title Deed', 'Title Deed'),
            ('Lease Agreement', 'Lease Agreement'),
            ('Chief Letter', 'Letter from Chief/Family Head'),
            ('Survey Plan', 'Survey Plan'),
            
            # Business Documents
            ('Business Registration', 'Business Registration Certificate'),
            ('Production Records', 'Previous Production Records'),
            ('Tax Clearance', 'Tax Clearance Certificate'),
            
            # Other
            ('Other', 'Other Document')
        ]
    )
    
    file = models.FileField(upload_to='farm_documents/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    
    # Validation
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # EXIF GPS verification for farm photos
    exif_gps_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    exif_gps_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    gps_location_verified = models.BooleanField(
        default=False,
        help_text="EXIF GPS matches farm location"
    )
    
    notes = models.TextField(blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farm_documents'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.document_type}"
    
    def clean(self):
        """Validate file size and type"""
        from django.core.exceptions import ValidationError
        
        max_size = 5 * 1024 * 1024  # 5MB
        if self.file and self.file.size > max_size:
            raise ValidationError(
                f'File size ({self.file.size / 1024 / 1024:.2f}MB) exceeds maximum 5MB'
            )
        
        # Validate file types
        allowed_types = {
            'image/jpeg', 'image/jpg', 'image/png', 
            'application/pdf'
        }
        if self.mime_type not in allowed_types:
            raise ValidationError(
                f'File type {self.mime_type} not allowed. Use JPG, PNG, or PDF.'
            )


# ===================================================================
# FARM APPROVAL WORKFLOW MODELS
# ===================================================================

class FarmReviewAction(models.Model):
    """
    Tracks all review actions taken on farm applications.
    Provides complete audit trail of approval workflow.
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
        ('reassigned', 'Reassigned to Another Officer'),
        ('note_added', 'Internal Note Added'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name='review_actions'
    )
    
    # Reviewer Information
    reviewer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='farm_reviews'
    )
    review_level = models.CharField(
        max_length=20,
        choices=REVIEW_LEVEL_CHOICES,
        db_index=True
    )
    
    # Action Details
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True
    )
    notes = models.TextField(
        help_text="Reviewer comments, feedback, or reasons"
    )
    is_internal_note = models.BooleanField(
        default=False,
        help_text="If True, farmer cannot see this note"
    )
    
    # Change Requests (if action = 'request_changes')
    requested_changes = models.JSONField(
        null=True,
        blank=True,
        help_text="List of specific fields/documents that need changes"
    )
    changes_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline for farmer to submit changes"
    )
    
    # Reassignment (if action = 'reassigned')
    reassigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reassigned_farm_reviews'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'farm_review_actions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', 'review_level']),
            models.Index(fields=['reviewer', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.get_action_display()} by {self.reviewer.get_full_name()}"


class FarmApprovalQueue(models.Model):
    """
    Manages the queue of farms pending review at each level.
    Officers can claim farms from this queue.
    """
    
    REVIEW_LEVEL_CHOICES = FarmReviewAction.REVIEW_LEVEL_CHOICES
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('claimed', 'Claimed by Officer'),
        ('in_progress', 'Under Review'),
        ('completed', 'Review Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name='approval_queue_items'
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
        related_name='assigned_farm_reviews'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    auto_assigned = models.BooleanField(
        default=False,
        help_text="True if auto-assigned based on GPS location"
    )
    
    # Priority & Timing
    priority = models.IntegerField(
        default=0,
        help_text="Higher number = higher priority. Default = 0"
    )
    entered_queue_at = models.DateTimeField(auto_now_add=True, db_index=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # SLA Tracking
    sla_due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Service Level Agreement deadline"
    )
    is_overdue = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Auto-calculated based on SLA"
    )
    
    # Auto-suggestion fields (for GPS-based assignment)
    suggested_constituency = models.CharField(
        max_length=100,
        blank=True,
        help_text="Auto-detected from farm GPS location"
    )
    suggested_region = models.CharField(
        max_length=100,
        blank=True,
        help_text="Auto-detected from farm GPS location"
    )
    
    class Meta:
        db_table = 'farm_approval_queue'
        ordering = ['-priority', 'entered_queue_at']
        indexes = [
            models.Index(fields=['review_level', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['is_overdue', 'sla_due_date']),
            models.Index(fields=['suggested_constituency']),
        ]
        unique_together = [['farm', 'review_level']]
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.get_review_level_display()} ({self.status})"
    
    def claim(self, officer):
        """Officer claims this farm for review"""
        self.assigned_to = officer
        self.assigned_at = timezone.now()
        self.claimed_at = timezone.now()
        self.status = 'claimed'
        self.save()
        
        # Create review action
        FarmReviewAction.objects.create(
            farm=self.farm,
            reviewer=officer,
            review_level=self.review_level,
            action='claimed',
            notes=f'Claimed from queue by {officer.get_full_name()}'
        )
    
    def mark_in_progress(self):
        """Mark as actively being reviewed"""
        self.status = 'in_progress'
        self.save()
    
    def complete(self):
        """Mark review as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()


class FarmNotification(models.Model):
    """
    Stores notifications for farmers and officers about application status.
    Supports email, SMS, and in-app notifications.
    """
    
    NOTIFICATION_TYPE_CHOICES = [
        ('application_submitted', 'Application Submitted'),
        ('review_started', 'Review Started'),
        ('changes_requested', 'Changes Requested'),
        ('approved_next_level', 'Approved - Forwarded to Next Level'),
        ('final_approval', 'Final Approval - Farm ID Assigned'),
        ('rejected', 'Application Rejected'),
        ('reminder', 'Reminder/Alert'),
        ('assignment', 'Review Assignment'),
    ]
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('in_app', 'In-App Notification'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read (In-App only)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recipient
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='farm_notifications'
    )
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    
    # Notification Details
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES,
        db_index=True
    )
    channel = models.CharField(
        max_length=10,
        choices=CHANNEL_CHOICES,
        db_index=True
    )
    
    # Content
    subject = models.CharField(max_length=200)
    message = models.TextField()
    action_url = models.URLField(
        blank=True,
        help_text="URL for 'View Details' button in notification"
    )
    
    # Status Tracking
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    
    # SMS Specific (for future integration)
    sms_provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="Hubtel, Arkesel, etc."
    )
    sms_message_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Provider's message ID for tracking"
    )
    sms_cost = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Cost in GHS"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'farm_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['channel', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.user.get_full_name()} via {self.channel}"
    
    def mark_as_sent(self):
        """Mark notification as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_delivered(self):
        """Mark notification as delivered (for SMS/Email)"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()
    
    def mark_as_read(self):
        """Mark in-app notification as read"""
        if self.channel == 'in_app':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save()
    
    def mark_as_failed(self, reason):
        """Mark notification as failed"""
        self.status = 'failed'
        self.failed_at = timezone.now()
        self.failure_reason = reason
        self.save()
