"""
Expense Tracking Models

Comprehensive expense tracking for poultry farm operations.
Tracks all cost elements that affect profitability:

TRACKED EXPENSE CATEGORIES:
===========================
1. LABOR - Staff wages, casual workers, overtime
2. UTILITIES - Electricity, water, gas/fuel
3. BEDDING - Litter, wood shavings, sawdust
4. TRANSPORT - Feed delivery, bird transport, market trips
5. MAINTENANCE - Equipment repairs, building maintenance
6. OVERHEAD - Insurance, licenses, admin, rent
7. MORTALITY_LOSS - Economic value of dead birds
8. MISCELLANEOUS - Other operational expenses

Each expense can be:
- Linked to a specific flock (for per-flock costing)
- Farm-level (general overhead)
- Recurring or one-time
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class ExpenseCategory(models.TextChoices):
    """Predefined expense categories for standardized tracking."""
    LABOR = 'LABOR', 'Labor & Wages'
    UTILITIES = 'UTILITIES', 'Utilities (Electricity, Water)'
    BEDDING = 'BEDDING', 'Litter & Bedding'
    TRANSPORT = 'TRANSPORT', 'Transport & Delivery'
    MAINTENANCE = 'MAINTENANCE', 'Equipment & Maintenance'
    OVERHEAD = 'OVERHEAD', 'Overhead & Administration'
    MORTALITY_LOSS = 'MORTALITY_LOSS', 'Mortality Loss'
    MISCELLANEOUS = 'MISCELLANEOUS', 'Miscellaneous'


class ExpenseFrequency(models.TextChoices):
    """Frequency of recurring expenses."""
    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    BIWEEKLY = 'BIWEEKLY', 'Bi-Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'
    QUARTERLY = 'QUARTERLY', 'Quarterly'
    ANNUAL = 'ANNUAL', 'Annual'
    ONE_TIME = 'ONE_TIME', 'One-Time'


class ExpenseSubCategory(models.Model):
    """
    Custom sub-categories for detailed expense tracking.
    Allows farms to create their own expense types within main categories.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='expense_subcategories',
        help_text="Farm that created this subcategory"
    )
    
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        help_text="Parent expense category"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Subcategory name (e.g., 'Caretaker Salary', 'Electricity Bill')"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of what this subcategory covers"
    )
    
    default_unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Default unit of measurement (e.g., 'hours', 'kWh', 'trips')"
    )
    
    default_unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Default cost per unit (GHS)"
    )
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Expense Sub-Category'
        verbose_name_plural = 'Expense Sub-Categories'
        unique_together = ['farm', 'category', 'name']
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"


class Expense(models.Model):
    """
    Individual expense record.
    
    Can be:
    - Flock-specific (linked to flock for per-flock costing)
    - Farm-level (general overhead, not tied to specific flock)
    
    Examples:
    - Daily caretaker wage: LABOR, flock-linked, daily
    - Monthly electricity: UTILITIES, farm-level, monthly
    - Wood shavings purchase: BEDDING, flock-linked, one-time
    - Bird mortality: MORTALITY_LOSS, flock-linked, as-needed
    """
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partially Paid'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Ownership
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='expenses',
        help_text="Farm incurring this expense"
    )
    
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        help_text="Specific flock (leave blank for farm-level expenses)"
    )
    
    # Category
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        db_index=True,
        help_text="Main expense category"
    )
    
    subcategory = models.ForeignKey(
        ExpenseSubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        help_text="Optional subcategory for detailed tracking"
    )
    
    # Expense Details
    description = models.CharField(
        max_length=255,
        help_text="Brief description of the expense"
    )
    
    expense_date = models.DateField(
        db_index=True,
        help_text="Date expense was incurred"
    )
    
    # Quantity & Cost
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity (hours, units, kWh, etc.)"
    )
    
    unit = models.CharField(
        max_length=50,
        default='unit',
        help_text="Unit of measurement"
    )
    
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost per unit (GHS)"
    )
    
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total expense amount (auto-calculated)"
    )
    
    # Frequency (for recurring expenses)
    frequency = models.CharField(
        max_length=20,
        choices=ExpenseFrequency.choices,
        default=ExpenseFrequency.ONE_TIME,
        help_text="How often this expense recurs"
    )
    
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this expense repeats"
    )
    
    # Payment
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='PAID',
        help_text="Payment status"
    )
    
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Payment method (Cash, Mobile Money, Bank, etc.)"
    )
    
    receipt_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Receipt or reference number"
    )
    
    # Vendor/Payee
    payee_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of person/company paid"
    )
    
    payee_contact = models.CharField(
        max_length=100,
        blank=True,
        help_text="Contact info of payee"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses_created',
        help_text="User who recorded this expense"
    )
    
    class Meta:
        ordering = ['-expense_date', '-created_at']
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'
        indexes = [
            models.Index(fields=['farm', 'expense_date']),
            models.Index(fields=['farm', 'category']),
            models.Index(fields=['flock', 'expense_date']),
            models.Index(fields=['category', 'expense_date']),
            models.Index(fields=['-expense_date']),
        ]
    
    def __str__(self):
        flock_info = f" ({self.flock.flock_number})" if self.flock else ""
        return f"{self.get_category_display()}{flock_info}: GHS {self.total_amount} - {self.expense_date}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate total amount before saving."""
        self.total_amount = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
        
        # Update flock accumulated costs if linked to a flock
        if self.flock:
            self._update_flock_costs()
    
    def _update_flock_costs(self):
        """Update accumulated costs on the flock."""
        from django.db.models import Sum
        
        if not self.flock:
            return
        
        # Map categories to flock fields
        category_field_map = {
            ExpenseCategory.LABOR: 'total_labor_cost',
            ExpenseCategory.UTILITIES: 'total_utilities_cost',
            ExpenseCategory.BEDDING: 'total_bedding_cost',
            ExpenseCategory.TRANSPORT: 'total_transport_cost',
            ExpenseCategory.MAINTENANCE: 'total_maintenance_cost',
            ExpenseCategory.OVERHEAD: 'total_overhead_cost',
            ExpenseCategory.MORTALITY_LOSS: 'total_mortality_loss_value',
            ExpenseCategory.MISCELLANEOUS: 'total_miscellaneous_cost',
        }
        
        field_name = category_field_map.get(self.category)
        if field_name and hasattr(self.flock, field_name):
            # Calculate sum of all expenses in this category for this flock
            total = Expense.objects.filter(
                flock=self.flock,
                category=self.category
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            setattr(self.flock, field_name, total)
            self.flock.save(update_fields=[field_name, 'updated_at'])


class LaborRecord(models.Model):
    """
    Detailed labor/wage tracking.
    
    Tracks:
    - Permanent staff (monthly salaries)
    - Casual workers (daily wages)
    - Overtime payments
    - Task-specific labor (cleaning, vaccinating, etc.)
    """
    
    WORKER_TYPE_CHOICES = [
        ('PERMANENT', 'Permanent Staff'),
        ('CASUAL', 'Casual Worker'),
        ('CONTRACT', 'Contract Worker'),
        ('FAMILY', 'Family Labor'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('GENERAL', 'General Farm Work'),
        ('FEEDING', 'Feeding'),
        ('CLEANING', 'Cleaning & Sanitation'),
        ('VACCINATION', 'Vaccination Assistance'),
        ('MEDICATION', 'Medication Administration'),
        ('EGG_COLLECTION', 'Egg Collection'),
        ('PROCESSING', 'Processing'),
        ('MAINTENANCE', 'Maintenance Work'),
        ('SECURITY', 'Security'),
        ('SUPERVISION', 'Supervision'),
        ('OTHER', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to expense (for financial tracking)
    expense = models.OneToOneField(
        Expense,
        on_delete=models.CASCADE,
        related_name='labor_details',
        help_text="Associated expense record"
    )
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='labor_records',
        help_text="Farm"
    )
    
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='labor_records',
        help_text="Specific flock (if applicable)"
    )
    
    # Worker Details
    worker_name = models.CharField(
        max_length=200,
        help_text="Name of worker"
    )
    
    worker_type = models.CharField(
        max_length=20,
        choices=WORKER_TYPE_CHOICES,
        help_text="Type of worker"
    )
    
    worker_contact = models.CharField(
        max_length=100,
        blank=True,
        help_text="Worker contact (phone)"
    )
    
    # Work Details
    work_date = models.DateField(
        help_text="Date of work"
    )
    
    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
        default='GENERAL',
        help_text="Type of task performed"
    )
    
    hours_worked = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Hours worked"
    )
    
    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Rate per hour (GHS)"
    )
    
    overtime_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Overtime hours"
    )
    
    overtime_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Overtime rate per hour (GHS)"
    )
    
    # Calculated
    base_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base pay (auto-calculated)"
    )
    
    overtime_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Overtime pay (auto-calculated)"
    )
    
    total_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total pay (auto-calculated)"
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-work_date', '-created_at']
        verbose_name = 'Labor Record'
        verbose_name_plural = 'Labor Records'
        indexes = [
            models.Index(fields=['farm', 'work_date']),
            models.Index(fields=['worker_name', 'work_date']),
        ]
    
    def __str__(self):
        return f"{self.worker_name} - {self.get_task_type_display()} - {self.work_date}"
    
    def save(self, *args, **kwargs):
        """Calculate pay before saving."""
        self.base_pay = self.hours_worked * self.hourly_rate
        self.overtime_pay = self.overtime_hours * self.overtime_rate
        self.total_pay = self.base_pay + self.overtime_pay
        super().save(*args, **kwargs)


class UtilityRecord(models.Model):
    """
    Utility expense tracking (electricity, water, gas).
    """
    
    UTILITY_TYPE_CHOICES = [
        ('ELECTRICITY', 'Electricity'),
        ('WATER', 'Water'),
        ('GAS', 'Gas/LPG'),
        ('FUEL', 'Fuel (Generator/Vehicle)'),
        ('INTERNET', 'Internet'),
        ('OTHER', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    expense = models.OneToOneField(
        Expense,
        on_delete=models.CASCADE,
        related_name='utility_details',
        help_text="Associated expense record"
    )
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='utility_records'
    )
    
    # Utility Details
    utility_type = models.CharField(
        max_length=20,
        choices=UTILITY_TYPE_CHOICES,
        help_text="Type of utility"
    )
    
    provider = models.CharField(
        max_length=200,
        blank=True,
        help_text="Utility provider (ECG, GWCL, etc.)"
    )
    
    account_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Account/meter number"
    )
    
    # Billing Period
    billing_period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Start of billing period"
    )
    
    billing_period_end = models.DateField(
        null=True,
        blank=True,
        help_text="End of billing period"
    )
    
    # Usage
    previous_reading = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Previous meter reading"
    )
    
    current_reading = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current meter reading"
    )
    
    units_consumed = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Units consumed (kWh, gallons, liters)"
    )
    
    unit_of_measure = models.CharField(
        max_length=20,
        default='kWh',
        help_text="Unit of measurement"
    )
    
    rate_per_unit = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Rate per unit (GHS)"
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-billing_period_end', '-created_at']
        verbose_name = 'Utility Record'
        verbose_name_plural = 'Utility Records'
    
    def __str__(self):
        return f"{self.get_utility_type_display()} - {self.billing_period_end or self.expense.expense_date}"
    
    def save(self, *args, **kwargs):
        """Calculate units consumed from readings."""
        if self.previous_reading and self.current_reading:
            self.units_consumed = self.current_reading - self.previous_reading
        super().save(*args, **kwargs)


class MortalityLossRecord(models.Model):
    """
    Economic loss tracking from bird mortality.
    Links to MortalityRecord to calculate financial impact.
    
    This helps farmers understand the true cost of mortality
    beyond just the count - including:
    - Original acquisition cost
    - Feed invested in dead birds (auto-calculated from FeedConsumption data)
    - Medication/vaccination costs invested (auto-calculated)
    - Potential revenue lost
    
    SMART AUTO-CALCULATION:
    When feed_cost_invested or other_costs_invested are not provided (or set to 0),
    the save() method will automatically calculate these values using:
    - FeedConsumption records to determine actual feed cost per bird
    - MedicationRecord/VaccinationRecord to determine medication costs per bird
    
    This uses the BirdInvestmentCalculator service for accurate calculations.
    
    Frontend Integration:
    - Use GET /api/expenses/mortality-loss/preview/ to preview calculations
    - Pass `auto_calculate=True` in POST to let the system calculate costs
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    expense = models.OneToOneField(
        Expense,
        on_delete=models.CASCADE,
        related_name='mortality_loss_details',
        help_text="Associated expense record"
    )
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='mortality_loss_records'
    )
    
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.CASCADE,
        related_name='mortality_loss_records',
        help_text="Flock that experienced mortality"
    )
    
    mortality_record = models.ForeignKey(
        'flock_management.MortalityRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loss_records',
        help_text="Link to mortality record"
    )
    
    # Loss Details
    mortality_date = models.DateField(
        help_text="Date of mortality"
    )
    
    birds_lost = models.PositiveIntegerField(
        help_text="Number of birds lost"
    )
    
    cause_of_death = models.CharField(
        max_length=100,
        blank=True,
        help_text="Cause of death"
    )
    
    # Cost Calculation
    acquisition_cost_per_bird = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Original cost per bird (GHS)"
    )
    
    feed_cost_invested = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Feed cost invested in dead birds (GHS). Auto-calculated from tracked data if not provided."
    )
    
    other_costs_invested = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Other costs invested - vaccination, medication (GHS). Auto-calculated from tracked data if not provided."
    )
    
    # Flag to indicate if costs were auto-calculated
    costs_auto_calculated = models.BooleanField(
        default=False,
        help_text="True if feed_cost_invested and other_costs_invested were auto-calculated from tracked data"
    )
    
    potential_revenue_lost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Potential revenue if birds had been sold"
    )
    
    total_loss_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total economic loss including acquisition (for insurance claims, analysis)"
    )
    
    # Separate field for expense tracking (excludes acquisition to avoid double-counting)
    additional_investment_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Investment loss excluding acquisition (feed + medication only) - used for expense tracking to avoid double-counting"
    )
    
    # Age at death (for loss calculation)
    age_at_death_weeks = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Age of birds at death (weeks)"
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-mortality_date', '-created_at']
        verbose_name = 'Mortality Loss Record'
        verbose_name_plural = 'Mortality Loss Records'
    
    def __str__(self):
        return f"{self.flock.flock_number} - {self.birds_lost} birds - GHS {self.total_loss_value}"
    
    def save(self, *args, **kwargs):
        """
        Calculate total loss value, auto-calculating feed/medication costs if not provided.
        
        Auto-calculation happens when:
        - auto_calculate=True is passed as kwarg, OR
        - Both feed_cost_invested AND other_costs_invested are 0 (default)
        
        This uses the BirdInvestmentCalculator service to pull actual tracked data
        from FeedConsumption, MedicationRecord, and VaccinationRecord models.
        """
        # Check if auto-calculation is requested or needed
        auto_calculate = kwargs.pop('auto_calculate', False)
        should_auto_calculate = (
            auto_calculate or 
            (self.feed_cost_invested == Decimal('0.00') and 
             self.other_costs_invested == Decimal('0.00') and
             not self.pk)  # Only on creation, not updates
        )
        
        if should_auto_calculate:
            try:
                from .services import BirdInvestmentCalculator
                
                calculator = BirdInvestmentCalculator(self.flock)
                loss_data = calculator.calculate_mortality_loss(
                    mortality_date=self.mortality_date,
                    birds_lost=self.birds_lost,
                    acquisition_cost_per_bird=self.acquisition_cost_per_bird
                )
                
                # Update fields with calculated values
                self.feed_cost_invested = loss_data['feed_cost_invested']
                self.other_costs_invested = loss_data['other_costs_invested']
                self.costs_auto_calculated = True
                
                # Also set age_at_death_weeks if not provided
                if not self.age_at_death_weeks:
                    self.age_at_death_weeks = loss_data['age_at_death_weeks']
                    
            except Exception as e:
                # Log but don't fail - allow manual values
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Auto-calculation failed for mortality loss: {e}")
                self.costs_auto_calculated = False
        
        # Calculate total loss value (acquisition + feed + other) - full economic loss
        acquisition_loss = self.acquisition_cost_per_bird * self.birds_lost
        self.total_loss_value = (
            acquisition_loss + 
            self.feed_cost_invested + 
            self.other_costs_invested
        )
        
        # Calculate additional investment value (feed + medication only)
        # This EXCLUDES acquisition cost to avoid double-counting in expense tracking
        # since acquisition was already recorded when the flock was purchased
        self.additional_investment_value = (
            self.feed_cost_invested + 
            self.other_costs_invested
        )
        
        super().save(*args, **kwargs)


class RecurringExpenseTemplate(models.Model):
    """
    Templates for recurring expenses.
    Automatically generates expense records based on schedule.
    
    Examples:
    - Monthly electricity bill
    - Weekly caretaker wage
    - Annual insurance premium
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='recurring_expense_templates'
    )
    
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recurring_expense_templates',
        help_text="Specific flock (leave blank for farm-level)"
    )
    
    # Template Details
    name = models.CharField(
        max_length=200,
        help_text="Template name (e.g., 'Monthly Caretaker Salary')"
    )
    
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        help_text="Expense category"
    )
    
    subcategory = models.ForeignKey(
        ExpenseSubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    description = models.CharField(
        max_length=255,
        help_text="Description for generated expenses"
    )
    
    # Amount
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    unit = models.CharField(max_length=50, default='unit')
    
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    estimated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Estimated recurring amount"
    )
    
    # Schedule
    frequency = models.CharField(
        max_length=20,
        choices=ExpenseFrequency.choices,
        help_text="How often this expense occurs"
    )
    
    start_date = models.DateField(
        help_text="When to start generating expenses"
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When to stop (leave blank for indefinite)"
    )
    
    last_generated_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date an expense was generated"
    )
    
    next_due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next date expense is due"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether to continue generating expenses"
    )
    
    # Payee
    payee_name = models.CharField(max_length=200, blank=True)
    payee_contact = models.CharField(max_length=100, blank=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['next_due_date', 'name']
        verbose_name = 'Recurring Expense Template'
        verbose_name_plural = 'Recurring Expense Templates'
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"
    
    def save(self, *args, **kwargs):
        """Calculate estimated amount."""
        self.estimated_amount = self.quantity * self.unit_cost
        
        # Set initial next_due_date if not set
        if not self.next_due_date and self.start_date:
            self.next_due_date = self.start_date
        
        super().save(*args, **kwargs)
    
    def generate_expense(self, user=None):
        """Generate an expense from this template."""
        if not self.is_active:
            return None
        
        if self.end_date and timezone.now().date() > self.end_date:
            self.is_active = False
            self.save()
            return None
        
        expense = Expense.objects.create(
            farm=self.farm,
            flock=self.flock,
            category=self.category,
            subcategory=self.subcategory,
            description=self.description,
            expense_date=self.next_due_date or timezone.now().date(),
            quantity=self.quantity,
            unit=self.unit,
            unit_cost=self.unit_cost,
            frequency=self.frequency,
            is_recurring=True,
            payee_name=self.payee_name,
            payee_contact=self.payee_contact,
            notes=f"Auto-generated from template: {self.name}",
            created_by=user,
        )
        
        # Update template
        self.last_generated_date = expense.expense_date
        self._calculate_next_due_date()
        self.save()
        
        return expense
    
    def _calculate_next_due_date(self):
        """Calculate next due date based on frequency."""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        if not self.last_generated_date:
            self.next_due_date = self.start_date
            return
        
        frequency_deltas = {
            ExpenseFrequency.DAILY: timedelta(days=1),
            ExpenseFrequency.WEEKLY: timedelta(weeks=1),
            ExpenseFrequency.BIWEEKLY: timedelta(weeks=2),
            ExpenseFrequency.MONTHLY: relativedelta(months=1),
            ExpenseFrequency.QUARTERLY: relativedelta(months=3),
            ExpenseFrequency.ANNUAL: relativedelta(years=1),
        }
        
        delta = frequency_deltas.get(self.frequency)
        if delta:
            self.next_due_date = self.last_generated_date + delta


class ExpenseSummary(models.Model):
    """
    Aggregated expense summary per flock and period.
    Pre-computed for dashboard/reporting performance.
    Updated via signals when expenses change.
    """
    
    PERIOD_TYPE_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('TOTAL', 'Lifetime Total'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='expense_summaries'
    )
    
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='expense_summaries',
        help_text="Specific flock (null for farm-wide summary)"
    )
    
    # Period
    period_type = models.CharField(
        max_length=10,
        choices=PERIOD_TYPE_CHOICES
    )
    
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Category Totals
    labor_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    utilities_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    bedding_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    transport_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    maintenance_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    overhead_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    mortality_loss_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    miscellaneous_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    
    # Grand Total
    grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0.00')
    )
    
    # Expense Count
    expense_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-period_end']
        verbose_name = 'Expense Summary'
        verbose_name_plural = 'Expense Summaries'
        unique_together = ['farm', 'flock', 'period_type', 'period_start', 'period_end']
    
    def __str__(self):
        flock_info = f" - {self.flock.flock_number}" if self.flock else " (Farm-wide)"
        return f"{self.farm.farm_name}{flock_info} - {self.period_type}: GHS {self.grand_total}"
    
    def recalculate(self):
        """Recalculate summary from expenses."""
        from django.db.models import Sum, Count
        
        # Base queryset
        expenses = Expense.objects.filter(
            farm=self.farm,
            expense_date__gte=self.period_start,
            expense_date__lte=self.period_end
        )
        
        if self.flock:
            expenses = expenses.filter(flock=self.flock)
        
        # Aggregate by category
        aggregates = expenses.values('category').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        # Reset all totals
        self.labor_total = Decimal('0.00')
        self.utilities_total = Decimal('0.00')
        self.bedding_total = Decimal('0.00')
        self.transport_total = Decimal('0.00')
        self.maintenance_total = Decimal('0.00')
        self.overhead_total = Decimal('0.00')
        self.mortality_loss_total = Decimal('0.00')
        self.miscellaneous_total = Decimal('0.00')
        self.expense_count = 0
        
        # Map to fields
        category_field_map = {
            ExpenseCategory.LABOR: 'labor_total',
            ExpenseCategory.UTILITIES: 'utilities_total',
            ExpenseCategory.BEDDING: 'bedding_total',
            ExpenseCategory.TRANSPORT: 'transport_total',
            ExpenseCategory.MAINTENANCE: 'maintenance_total',
            ExpenseCategory.OVERHEAD: 'overhead_total',
            ExpenseCategory.MORTALITY_LOSS: 'mortality_loss_total',
            ExpenseCategory.MISCELLANEOUS: 'miscellaneous_total',
        }
        
        for agg in aggregates:
            field = category_field_map.get(agg['category'])
            if field:
                setattr(self, field, agg['total'] or Decimal('0.00'))
            self.expense_count += agg['count'] or 0
        
        # Calculate grand total
        self.grand_total = (
            self.labor_total +
            self.utilities_total +
            self.bedding_total +
            self.transport_total +
            self.maintenance_total +
            self.overhead_total +
            self.mortality_loss_total +
            self.miscellaneous_total
        )
        
        self.save()
