"""
Medication & Vaccination Management Models

This module handles medication and vaccination tracking for the YEA Poultry Management System.
Tracks medication types, vaccination schedules, treatment records, and veterinary visits.

Models:
    - MedicationType: Master data for medications, vaccines, and supplements
    - VaccinationSchedule: Standard vaccination schedules by flock type
    - MedicationRecord: Records of medications administered
    - VaccinationRecord: Records of vaccinations given
    - VetVisit: Veterinary officer visit records
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class MedicationType(models.Model):
    """
    Master data for medications, vaccines, and supplements.
    
    Comprehensive catalog of all drugs, vaccines, and supplements used in poultry management.
    """
    
    CATEGORY_CHOICES = [
        ('ANTIBIOTIC', 'Antibiotic'),
        ('VACCINE', 'Vaccine'),
        ('VITAMIN', 'Vitamin/Supplement'),
        ('DEWORMER', 'Dewormer/Antiparasitic'),
        ('COCCIDIOSTAT', 'Coccidiostat'),
        ('PROBIOTIC', 'Probiotic'),
        ('DISINFECTANT', 'Disinfectant'),
        ('OTHER', 'Other'),
    ]
    
    ADMINISTRATION_ROUTE_CHOICES = [
        ('ORAL', 'Oral (in water/feed)'),
        ('INJECTION_IM', 'Intramuscular Injection'),
        ('INJECTION_SC', 'Subcutaneous Injection'),
        ('EYE_DROP', 'Eye Drop'),
        ('NASAL', 'Nasal Drop'),
        ('SPRAY', 'Spray'),
        ('TOPICAL', 'Topical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=200, unique=True, help_text="Trade/commercial name of the medication")
    generic_name = models.CharField(max_length=200, blank=True, help_text="Generic/scientific name")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, help_text="Category of medication")
    manufacturer = models.CharField(max_length=100, blank=True, help_text="Manufacturer/brand")
    
    # Active Ingredients
    active_ingredient = models.CharField(max_length=200, blank=True, help_text="Main active ingredient(s)")
    strength = models.CharField(max_length=100, blank=True, help_text="Strength/concentration (e.g., '10% w/v', '250mg/ml')")
    
    # Administration
    administration_route = models.CharField(
        max_length=20,
        choices=ADMINISTRATION_ROUTE_CHOICES,
        help_text="Route of administration"
    )
    dosage = models.CharField(max_length=200, help_text="Recommended dosage (e.g., '1ml per liter water', '0.5ml per bird')")
    
    # Usage Guidelines
    indication = models.TextField(help_text="What this medication treats/prevents")
    contraindications = models.TextField(blank=True, help_text="When NOT to use this medication")
    
    # Withdrawal Period (Critical for food safety)
    withdrawal_period_days = models.PositiveSmallIntegerField(
        default=0,
        help_text="Days before slaughter/egg consumption after treatment (0 if none)"
    )
    egg_withdrawal_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Days before egg consumption after treatment (for layers)"
    )
    meat_withdrawal_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Days before slaughter after treatment (for broilers)"
    )
    
    # Pricing
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Price per unit (GHS)",
        null=True,
        blank=True
    )
    unit_measure = models.CharField(
        max_length=50,
        blank=True,
        help_text="Unit of measure (e.g., 'per 100ml bottle', 'per 1000 dose vial')"
    )
    
    # Regulatory Information
    registration_number = models.CharField(max_length=100, blank=True, help_text="Veterinary drug registration number")
    requires_prescription = models.BooleanField(default=False, help_text="Whether prescription is required")
    
    # Storage Requirements
    storage_conditions = models.TextField(blank=True, help_text="Storage temperature and conditions")
    shelf_life_months = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Shelf life in months")
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Whether this medication is currently available")
    notes = models.TextField(blank=True, help_text="Additional notes or warnings")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Medication Type'
        verbose_name_plural = 'Medication Types'
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    def clean(self):
        """Validate medication type data."""
        errors = {}
        
        # Ensure at least one withdrawal period is set if category is antibiotic or dewormer
        if self.category in ['ANTIBIOTIC', 'DEWORMER', 'COCCIDIOSTAT']:
            if self.withdrawal_period_days == 0 and not self.egg_withdrawal_days and not self.meat_withdrawal_days:
                errors['withdrawal_period_days'] = f"{self.get_category_display()} typically requires a withdrawal period"
        
        # Vaccine-specific validations
        if self.category == 'VACCINE':
            if self.withdrawal_period_days > 0:
                errors['withdrawal_period_days'] = "Vaccines typically don't have withdrawal periods"
        
        if errors:
            raise ValidationError(errors)


class VaccinationSchedule(models.Model):
    """
    Standard vaccination schedules by flock type.
    
    Defines when specific vaccinations should be administered based on
    bird type and age.
    """
    
    FLOCK_TYPE_CHOICES = [
        ('LAYER', 'Layers'),
        ('BROILER', 'Broilers'),
        ('BREEDER', 'Breeders'),
        ('ALL', 'All Types'),
    ]
    
    FREQUENCY_CHOICES = [
        ('ONCE', 'One-time'),
        ('ANNUAL', 'Annual'),
        ('BIANNUAL', 'Twice per year'),
        ('AS_NEEDED', 'As needed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    medication_type = models.ForeignKey(
        MedicationType,
        on_delete=models.PROTECT,
        related_name='vaccination_schedules',
        limit_choices_to={'category': 'VACCINE'},
        help_text="Vaccine to be administered"
    )
    
    # Schedule Details
    flock_type = models.CharField(max_length=10, choices=FLOCK_TYPE_CHOICES, help_text="Type of birds for this schedule")
    age_in_weeks = models.PositiveSmallIntegerField(
        help_text="Age of birds in weeks when vaccination should occur"
    )
    age_in_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Age in days (for day-old vaccinations, overrides weeks)"
    )
    
    # Administration
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='ONCE', help_text="How often this vaccination is needed")
    dosage_per_bird = models.CharField(max_length=100, help_text="Dosage per bird (e.g., '1 dose', '0.3ml')")
    
    # Priority and Compliance
    is_mandatory = models.BooleanField(default=False, help_text="Whether this vaccination is legally required")
    priority = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Priority level (1=lowest, 10=highest)"
    )
    
    # Disease Information
    disease_prevented = models.CharField(max_length=200, help_text="Disease(s) this vaccination prevents")
    symptoms_to_watch = models.TextField(blank=True, help_text="Symptoms farmers should monitor for")
    
    # Notes
    notes = models.TextField(blank=True, help_text="Additional notes or special instructions")
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Whether this schedule is currently in use")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['flock_type', 'age_in_weeks', 'priority']
        verbose_name = 'Vaccination Schedule'
        verbose_name_plural = 'Vaccination Schedules'
        indexes = [
            models.Index(fields=['flock_type', 'age_in_weeks']),
            models.Index(fields=['is_mandatory']),
        ]
    
    def __str__(self):
        age_str = f"{self.age_in_days} days" if self.age_in_days else f"{self.age_in_weeks} weeks"
        return f"{self.medication_type.name} - {self.get_flock_type_display()} at {age_str}"
    
    def clean(self):
        """Validate vaccination schedule data."""
        errors = {}
        
        # Ensure medication is actually a vaccine
        if self.medication_type_id and self.medication_type.category != 'VACCINE':
            errors['medication_type'] = f"Selected medication is {self.medication_type.get_category_display()}, not a vaccine"
        
        # Age validation
        if self.age_in_days and self.age_in_days > 365:
            errors['age_in_days'] = "Use age_in_weeks for birds older than 365 days"
        
        if self.age_in_weeks == 0 and not self.age_in_days:
            errors['age_in_days'] = "For day-old birds, use age_in_days field"
        
        if errors:
            raise ValidationError(errors)


class MedicationRecord(models.Model):
    """
    Records of medications administered.
    
    Tracks all non-vaccine medications given to flocks, including treatment
    details, dosages, and costs.
    """
    
    REASON_CHOICES = [
        ('TREATMENT', 'Treatment (Sick birds)'),
        ('PREVENTION', 'Prevention'),
        ('GROWTH', 'Growth promotion'),
        ('STRESS', 'Stress management'),
        ('OTHER', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.PROTECT,
        related_name='medication_records',
        help_text="Flock receiving medication"
    )
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.PROTECT,
        related_name='medication_records',
        help_text="Farm where medication was administered (denormalized)"
    )
    medication_type = models.ForeignKey(
        MedicationType,
        on_delete=models.PROTECT,
        related_name='medication_records',
        limit_choices_to={'category__in': ['ANTIBIOTIC', 'VITAMIN', 'DEWORMER', 'COCCIDIOSTAT', 'PROBIOTIC', 'OTHER']},
        help_text="Medication administered"
    )
    
    # Administration Details
    administered_date = models.DateField(help_text="Date medication was given")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, help_text="Reason for medication")
    
    # Dosage
    dosage_given = models.CharField(max_length=200, help_text="Actual dosage administered")
    birds_treated = models.PositiveIntegerField(help_text="Number of birds treated")
    
    # Duration
    treatment_days = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of days treatment will continue"
    )
    end_date = models.DateField(help_text="Expected end date of treatment (auto-calculated)")
    
    # Cost
    quantity_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity of medication used"
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost per unit (GHS)"
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total medication cost (auto-calculated)"
    )
    
    # Withdrawal Period Tracking
    withdrawal_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when withdrawal period ends (auto-calculated)"
    )
    
    # Administration Details
    administered_by = models.CharField(max_length=100, blank=True, help_text="Person who administered the medication")
    batch_number = models.CharField(max_length=50, blank=True, help_text="Medication batch/lot number")
    
    # Outcome Tracking
    symptoms_before = models.TextField(blank=True, help_text="Symptoms observed before treatment")
    effectiveness_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Treatment effectiveness (1=poor, 5=excellent)"
    )
    side_effects = models.TextField(blank=True, help_text="Any side effects observed")
    
    # Notes
    notes = models.TextField(blank=True, help_text="Additional notes about this medication")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medication_records_created',
        help_text="User who created this record"
    )
    
    class Meta:
        ordering = ['-administered_date', '-created_at']
        verbose_name = 'Medication Record'
        verbose_name_plural = 'Medication Records'
        indexes = [
            models.Index(fields=['flock', 'administered_date']),
            models.Index(fields=['farm', 'administered_date']),
            models.Index(fields=['-administered_date']),
            models.Index(fields=['withdrawal_end_date']),
        ]
    
    def __str__(self):
        return f"{self.flock.name} - {self.medication_type.name} ({self.administered_date})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate values before saving."""
        from datetime import timedelta
        
        # Calculate total cost
        self.total_cost = self.quantity_used * self.unit_cost
        
        # Calculate end date
        self.end_date = self.administered_date + timedelta(days=self.treatment_days - 1)
        
        # Calculate withdrawal end date
        if self.medication_type.withdrawal_period_days > 0:
            self.withdrawal_end_date = self.end_date + timedelta(days=self.medication_type.withdrawal_period_days)
        
        # Denormalize farm from flock
        if self.flock_id:
            self.farm = self.flock.farm
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate medication record data."""
        errors = {}
        
        # Farm consistency check
        if self.flock_id and self.farm_id:
            if self.farm != self.flock.farm:
                errors['farm'] = f"Farm must match flock's farm ({self.flock.farm.name})"
        
        # Bird count validation
        if self.flock_id and self.birds_treated > self.flock.current_count:
            errors['birds_treated'] = f"Cannot treat more birds ({self.birds_treated}) than in flock ({self.flock.current_count})"
        
        # Medication category validation
        if self.medication_type_id and self.medication_type.category == 'VACCINE':
            errors['medication_type'] = "Use VaccinationRecord for vaccines, not MedicationRecord"
        
        if errors:
            raise ValidationError(errors)


class VaccinationRecord(models.Model):
    """
    Records of vaccinations administered.
    
    Tracks all vaccinations given to flocks, including compliance with
    vaccination schedules and batch tracking.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.PROTECT,
        related_name='vaccination_records',
        help_text="Flock being vaccinated"
    )
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.PROTECT,
        related_name='vaccination_records',
        help_text="Farm where vaccination occurred (denormalized)"
    )
    medication_type = models.ForeignKey(
        MedicationType,
        on_delete=models.PROTECT,
        related_name='vaccination_records',
        limit_choices_to={'category': 'VACCINE'},
        help_text="Vaccine administered"
    )
    vaccination_schedule = models.ForeignKey(
        VaccinationSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vaccination_records',
        help_text="Schedule this vaccination follows (if any)"
    )
    
    # Vaccination Details
    vaccination_date = models.DateField(help_text="Date vaccination was given")
    birds_vaccinated = models.PositiveIntegerField(help_text="Number of birds vaccinated")
    flock_age_weeks = models.PositiveSmallIntegerField(help_text="Age of flock in weeks at vaccination")
    
    # Administration
    dosage_per_bird = models.CharField(max_length=100, help_text="Dosage per bird")
    administration_route = models.CharField(max_length=100, help_text="How vaccine was administered")
    
    # Batch Tracking (Critical for quality control)
    batch_number = models.CharField(max_length=50, help_text="Vaccine batch/lot number")
    expiry_date = models.DateField(help_text="Vaccine expiry date")
    manufacturer = models.CharField(max_length=100, blank=True, help_text="Vaccine manufacturer")
    
    # Cost
    quantity_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity of vaccine used (doses)"
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost per dose (GHS)"
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total vaccination cost (auto-calculated)"
    )
    
    # Administration Personnel
    administered_by = models.CharField(max_length=100, help_text="Person/veterinarian who administered vaccine")
    vet_license_number = models.CharField(max_length=50, blank=True, help_text="Veterinarian license number (if applicable)")
    
    # Compliance
    is_mandatory_compliance = models.BooleanField(
        default=False,
        help_text="Whether this vaccination fulfills mandatory compliance requirement"
    )
    
    # Next Vaccination (For recurring vaccines)
    next_vaccination_due = models.DateField(
        null=True,
        blank=True,
        help_text="When next dose/booster is due"
    )
    
    # Reaction Tracking
    adverse_reactions = models.TextField(blank=True, help_text="Any adverse reactions observed")
    mortality_within_24hrs = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of birds that died within 24 hours post-vaccination"
    )
    
    # Notes
    notes = models.TextField(blank=True, help_text="Additional notes about this vaccination")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vaccination_records_created',
        help_text="User who created this record"
    )
    
    class Meta:
        ordering = ['-vaccination_date', '-created_at']
        verbose_name = 'Vaccination Record'
        verbose_name_plural = 'Vaccination Records'
        indexes = [
            models.Index(fields=['flock', 'vaccination_date']),
            models.Index(fields=['farm', 'vaccination_date']),
            models.Index(fields=['-vaccination_date']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['is_mandatory_compliance']),
        ]
    
    def __str__(self):
        return f"{self.flock.name} - {self.medication_type.name} ({self.vaccination_date})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate values before saving."""
        # Calculate total cost
        self.total_cost = self.quantity_used * self.unit_cost
        
        # Denormalize farm from flock
        if self.flock_id:
            self.farm = self.flock.farm
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate vaccination record data."""
        errors = {}
        
        # Farm consistency check
        if self.flock_id and self.farm_id:
            if self.farm != self.flock.farm:
                errors['farm'] = f"Farm must match flock's farm ({self.flock.farm.name})"
        
        # Bird count validation
        if self.flock_id and self.birds_vaccinated > self.flock.current_count:
            errors['birds_vaccinated'] = f"Cannot vaccinate more birds ({self.birds_vaccinated}) than in flock ({self.flock.current_count})"
        
        # Medication category validation
        if self.medication_type_id and self.medication_type.category != 'VACCINE':
            errors['medication_type'] = f"Selected medication is {self.medication_type.get_category_display()}, not a vaccine. Use MedicationRecord instead."
        
        # Expiry date validation
        if self.expiry_date and self.vaccination_date > self.expiry_date:
            errors['expiry_date'] = "Cannot use expired vaccine"
        
        # Mortality validation
        if self.mortality_within_24hrs > self.birds_vaccinated:
            errors['mortality_within_24hrs'] = "Mortality cannot exceed number of birds vaccinated"
        
        if errors:
            raise ValidationError(errors)


class VetVisit(models.Model):
    """
    Veterinary officer visit records.
    
    Tracks all veterinary visits including routine inspections, emergency calls,
    disease investigations, and compliance checks.
    """
    
    VISIT_TYPE_CHOICES = [
        ('ROUTINE', 'Routine Inspection'),
        ('EMERGENCY', 'Emergency Call'),
        ('VACCINATION', 'Vaccination Campaign'),
        ('DISEASE_INVESTIGATION', 'Disease Investigation'),
        ('COMPLIANCE_CHECK', 'Compliance Check'),
        ('FOLLOW_UP', 'Follow-up Visit'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.PROTECT,
        related_name='vet_visits',
        help_text="Farm visited"
    )
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vet_visits',
        help_text="Specific flock inspected (if applicable)"
    )
    
    # Visit Details
    visit_date = models.DateField(help_text="Date of visit")
    visit_type = models.CharField(max_length=25, choices=VISIT_TYPE_CHOICES, help_text="Type of visit")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SCHEDULED', help_text="Visit status")
    
    # Veterinarian Information
    veterinarian_name = models.CharField(max_length=100, help_text="Name of veterinary officer")
    vet_license_number = models.CharField(max_length=50, help_text="Veterinary license number")
    vet_phone = models.CharField(max_length=20, blank=True, help_text="Veterinarian contact number")
    vet_organization = models.CharField(max_length=200, blank=True, help_text="Organization/clinic name")
    
    # Visit Purpose and Findings
    purpose = models.TextField(help_text="Purpose/reason for visit")
    findings = models.TextField(blank=True, help_text="Veterinarian's findings and observations")
    diagnosis = models.TextField(blank=True, help_text="Diagnosis (if any)")
    
    # Recommendations
    recommendations = models.TextField(blank=True, help_text="Veterinarian's recommendations")
    medications_prescribed = models.TextField(blank=True, help_text="Medications prescribed")
    follow_up_required = models.BooleanField(default=False, help_text="Whether follow-up visit is needed")
    follow_up_date = models.DateField(null=True, blank=True, help_text="Scheduled follow-up date")
    
    # Compliance and Certification
    compliance_status = models.CharField(
        max_length=20,
        choices=[
            ('COMPLIANT', 'Compliant'),
            ('NON_COMPLIANT', 'Non-Compliant'),
            ('PARTIAL', 'Partially Compliant'),
            ('N/A', 'Not Applicable'),
        ],
        default='N/A',
        help_text="Compliance status after inspection"
    )
    issues_identified = models.TextField(blank=True, help_text="Compliance issues identified")
    certificate_issued = models.BooleanField(default=False, help_text="Whether health certificate was issued")
    certificate_number = models.CharField(max_length=50, blank=True, help_text="Certificate number (if issued)")
    
    # Cost
    visit_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Veterinary visit fee (GHS)"
    )
    
    # Supporting Documents
    report_file = models.CharField(max_length=500, blank=True, help_text="Path to vet report file")
    
    # Notes
    notes = models.TextField(blank=True, help_text="Additional notes about this visit")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vet_visits_created',
        help_text="User who created this record"
    )
    
    class Meta:
        ordering = ['-visit_date', '-created_at']
        verbose_name = 'Veterinary Visit'
        verbose_name_plural = 'Veterinary Visits'
        indexes = [
            models.Index(fields=['farm', 'visit_date']),
            models.Index(fields=['flock', 'visit_date']),
            models.Index(fields=['-visit_date']),
            models.Index(fields=['status']),
            models.Index(fields=['visit_type']),
            models.Index(fields=['follow_up_required', 'follow_up_date']),
        ]
    
    def __str__(self):
        flock_str = f" - {self.flock.name}" if self.flock else ""
        return f"{self.farm.name}{flock_str} - {self.get_visit_type_display()} ({self.visit_date})"
    
    def clean(self):
        """Validate vet visit data."""
        errors = {}
        
        # Flock-farm consistency
        if self.flock_id and self.farm_id:
            if self.flock.farm != self.farm:
                errors['flock'] = f"Flock must belong to farm {self.farm.name}"
        
        # Follow-up validation
        if self.follow_up_required and not self.follow_up_date:
            errors['follow_up_date'] = "Follow-up date is required when follow-up is needed"
        
        if self.follow_up_date and self.follow_up_date <= self.visit_date:
            errors['follow_up_date'] = "Follow-up date must be after visit date"
        
        # Certificate validation
        if self.certificate_issued and not self.certificate_number:
            errors['certificate_number'] = "Certificate number is required when certificate is issued"
        
        # Status-specific validations
        if self.status == 'COMPLETED' and not self.findings:
            errors['findings'] = "Findings are required for completed visits"
        
        if errors:
            raise ValidationError(errors)
