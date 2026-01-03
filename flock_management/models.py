"""
Flock Management & Production Tracking Models

Handles:
- Flock/batch tracking (birds grouped by arrival date and type)
- Daily production records (eggs, mortality, feed consumption)
- Detailed mortality tracking for disease surveillance
- Production performance metrics
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from farms.models import Farm, Infrastructure
from accounts.models import User
import uuid


# =============================================================================
# FLOCK MODEL - Track Bird Batches
# =============================================================================

class Flock(models.Model):
    """
    Represents a batch/group of birds managed together.
    Birds are not tracked individually but as cohorts.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Farm Association
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='flocks')
    
    # Flock Identification
    flock_number = models.CharField(
        max_length=50,
        help_text="Unique flock identifier (e.g., FLOCK-2025-001)"
    )
    flock_type = models.CharField(
        max_length=20,
        choices=[
            ('Layers', 'Layers (Egg Production)'),
            ('Broilers', 'Broilers (Meat Production)'),
            ('Breeders', 'Breeders (Hatching)'),
            ('Pullets', 'Pullets (Young Layers)'),
            ('Mixed', 'Mixed Purpose')
        ],
        db_index=True
    )
    breed = models.CharField(
        max_length=100,
        help_text="Bird breed (e.g., Isa Brown, Cobb 500, Sasso)"
    )
    
    # Acquisition Details
    source = models.CharField(
        max_length=30,
        choices=[
            ('YEA Program', 'YEA Program (Government Support)'),
            ('Purchased', 'Purchased from Supplier'),
            ('Hatched On-Farm', 'Hatched On-Farm'),
            ('Donated', 'Donated/Gift')
        ],
        default='YEA Program'
    )
    supplier_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Hatchery or supplier name"
    )
    arrival_date = models.DateField(
        help_text="Date birds arrived at farm"
    )
    initial_count = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of birds at arrival"
    )
    age_at_arrival_weeks = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(200)],
        help_text="Age in weeks when birds arrived"
    )
    
    # Financial Tracking
    purchase_price_per_bird = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cost per bird (GHS)"
    )
    total_acquisition_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total cost for this flock (GHS)"
    )
    
    # Current Status
    current_count = models.PositiveIntegerField(
        help_text="Current number of live birds"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('Active', 'Active'),
            ('Sold', 'Sold/Completed'),
            ('Culled', 'Culled'),
            ('Depleted', 'Fully Depleted (All Dead)')
        ],
        default='Active',
        db_index=True
    )
    
    # Production Phase (for layers)
    production_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when layers started producing eggs (18-20 weeks)"
    )
    expected_production_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected date to cull/sell (70-80 weeks for layers)"
    )
    is_currently_producing = models.BooleanField(
        default=False,
        help_text="True if flock is actively laying eggs"
    )
    
    # Housing
    housed_in = models.ForeignKey(
        Infrastructure,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='flocks',
        limit_choices_to={'infrastructure_type': 'Accommodation'},
        help_text="Current housing location (must be Accommodation type)"
    )
    
    # Accumulated Costs (updated from daily records)
    total_feed_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total feed cost accumulated (GHS)"
    )
    total_medication_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total medication cost accumulated (GHS)"
    )
    total_vaccination_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total vaccination cost accumulated (GHS)"
    )
    
    # Performance Metrics (auto-calculated)
    total_mortality = models.PositiveIntegerField(
        default=0,
        help_text="Total birds died since arrival"
    )
    mortality_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="(Total mortality / initial count) × 100"
    )
    average_daily_mortality = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Average birds dying per day"
    )
    
    # Production Metrics (for layers)
    total_eggs_produced = models.PositiveIntegerField(
        default=0,
        help_text="Total eggs produced by this flock"
    )
    average_eggs_per_bird = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Total eggs / initial count"
    )
    
    # Feed Efficiency
    total_feed_consumed_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total feed consumed in kilograms"
    )
    feed_conversion_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Feed consumed (kg) / Production (kg eggs or meat)"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="General notes about this flock"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'flocks'
        ordering = ['-arrival_date', 'flock_number']
        unique_together = [('farm', 'flock_number')]
        indexes = [
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['flock_type', 'status']),
            models.Index(fields=['arrival_date']),
        ]
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.flock_number} ({self.flock_type})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total acquisition cost
        if self.initial_count and self.purchase_price_per_bird:
            self.total_acquisition_cost = Decimal(str(self.initial_count)) * Decimal(str(self.purchase_price_per_bird))
        
        # Set current count to initial count on first save
        if not self.pk and not self.current_count:
            self.current_count = self.initial_count
        
        # Calculate mortality metrics
        self.total_mortality = self.initial_count - self.current_count
        if self.initial_count > 0:
            self.mortality_rate_percent = (Decimal(str(self.total_mortality)) / Decimal(str(self.initial_count))) * Decimal('100')
        
        # Calculate average daily mortality
        if self.arrival_date:
            days_since_arrival = (timezone.now().date() - self.arrival_date).days
            if days_since_arrival > 0:
                self.average_daily_mortality = Decimal(str(self.total_mortality)) / Decimal(str(days_since_arrival))
        
        # Track old housed_in and current_count for occupancy updates
        old_housed_in = None
        old_current_count = 0
        if self.pk:
            try:
                old_instance = Flock.objects.get(pk=self.pk)
                old_housed_in = old_instance.housed_in
                old_current_count = old_instance.current_count
            except Flock.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Auto-update infrastructure occupancy when flock counts or housing changes
        self._update_infrastructure_occupancy(old_housed_in, old_current_count)
    
    def clean(self):
        """Validate business logic"""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # ===== BIRD COUNT VALIDATION =====
        # Current count cannot exceed initial count
        if self.current_count > self.initial_count:
            errors['current_count'] = (
                f'Current count ({self.current_count}) cannot exceed initial count ({self.initial_count})'
            )
        
        # Current count cannot be negative
        if self.current_count < 0:
            errors['current_count'] = 'Current count cannot be negative'
        
        # ===== DATE VALIDATION =====
        # Arrival date cannot be in the future
        if self.arrival_date and self.arrival_date > timezone.now().date():
            errors['arrival_date'] = 'Arrival date cannot be in the future'
        
        # Production dates validation for layers/breeders
        if self.flock_type in ['Layers', 'Breeders']:
            if self.production_start_date and self.arrival_date:
                if self.production_start_date < self.arrival_date:
                    errors['production_start_date'] = (
                        'Production start date cannot be before arrival date'
                    )
            
            # Expected end date should be after start date
            if self.production_start_date and self.expected_production_end_date:
                if self.expected_production_end_date <= self.production_start_date:
                    errors['expected_production_end_date'] = (
                        'Expected production end date must be after production start date'
                    )
        
        # ===== HOUSING VALIDATION =====
        # Validate housed_in belongs to same farm
        if self.housed_in_id and self.farm_id:
            if self.housed_in.farm != self.farm:
                errors['housed_in'] = (
                    f'Infrastructure ({self.housed_in.infrastructure_name}) does not belong to '
                    f'this farm ({self.farm.farm_name})'
                )
        
        # Validate housed_in is Accommodation type
        if self.housed_in and self.housed_in.infrastructure_type != 'Accommodation':
            errors['housed_in'] = (
                f'Flocks can only be housed in Accommodation infrastructure. '
                f'{self.housed_in.infrastructure_name} is type {self.housed_in.infrastructure_type}'
            )
        
        # Validate flock doesn't exceed house capacity
        if self.housed_in and self.housed_in.bird_capacity:
            # Calculate total occupancy if this flock is housed here
            other_flocks_count = Flock.objects.filter(
                housed_in=self.housed_in,
                status='Active'
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('current_count')
            )['total'] or 0
            
            total_occupancy = other_flocks_count + self.current_count
            
            if total_occupancy > self.housed_in.bird_capacity:
                errors['housed_in'] = (
                    f'Capacity exceeded: {self.housed_in.infrastructure_name} has capacity '
                    f'{self.housed_in.bird_capacity}, but would house {total_occupancy} birds '
                    f'(current: {other_flocks_count}, this flock: {self.current_count})'
                )
        
        # ===== FINANCIAL VALIDATION =====
        # Validate costs are non-negative
        if self.purchase_price_per_bird < 0:
            errors['purchase_price_per_bird'] = 'Purchase price cannot be negative'
        
        if self.total_feed_cost < 0:
            errors['total_feed_cost'] = 'Total feed cost cannot be negative'
        
        if self.total_medication_cost < 0:
            errors['total_medication_cost'] = 'Total medication cost cannot be negative'
        
        # ===== PRODUCTION VALIDATION =====
        # Only layers/breeders should have egg production
        if self.flock_type not in ['Layers', 'Breeders'] and self.total_eggs_produced > 0:
            errors['total_eggs_produced'] = (
                f'{self.flock_type} flocks should not have egg production. '
                f'Only Layers and Breeders produce eggs.'
            )
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def current_age_weeks(self):
        """Calculate current age in weeks"""
        if not self.arrival_date:
            return None
        days_since_arrival = (timezone.now().date() - self.arrival_date).days
        weeks_since_arrival = Decimal(days_since_arrival) / 7
        return self.age_at_arrival_weeks + weeks_since_arrival
    
    @property
    def days_in_production(self):
        """Days since production started (for layers)"""
        if not self.production_start_date:
            return 0
        return (timezone.now().date() - self.production_start_date).days
    
    @property
    def survival_rate_percent(self):
        """Percentage of birds still alive"""
        if self.initial_count == 0:
            return 0
        return (Decimal(self.current_count) / Decimal(self.initial_count)) * 100
    
    @property
    def house_name(self):
        """Backward compatibility: Get infrastructure name as house_name"""
        if self.housed_in:
            return self.housed_in.infrastructure_name
        return None
    
    @property
    def capacity(self):
        """Backward compatibility: Get bird_capacity as capacity"""
        if self.housed_in:
            return self.housed_in.bird_capacity
        return None
    
    def get_current_bird_count(self, as_of_date=None):
        """
        Calculate current bird count: initial_count - mortalities - culls + transfers
        
        Args:
            as_of_date: Calculate bird count as of specific date (default: today)
        
        Returns:
            int: Current bird count
        """
        if as_of_date is None:
            as_of_date = timezone.now().date()
        
        # Start with initial count
        bird_count = self.initial_count
        
        # Subtract mortalities up to the date (field is 'birds_died' not 'mortality_count')
        mortalities = self.daily_productions.filter(
            production_date__lte=as_of_date
        ).aggregate(
            total=models.Sum('birds_died')
        )['total'] or 0
        
        bird_count -= mortalities
        
        # Subtract sales up to the date (field is 'birds_sold' not 'culls_count')
        sales = self.daily_productions.filter(
            production_date__lte=as_of_date
        ).aggregate(
            total=models.Sum('birds_sold')
        )['total'] or 0
        
        bird_count -= sales
        
        # TODO: Add transfers in/out when transfer model is implemented
        # For now, we'll use current_count as the source of truth
        # which is manually updated or calculated from daily production records
        
        return max(bird_count, 0)  # Ensure non-negative
    
    def _update_infrastructure_occupancy(self, old_housed_in, old_current_count):
        """Update infrastructure current_occupancy when flock counts or housing changes"""
        # Update old infrastructure if flock moved or count changed
        if old_housed_in and old_housed_in != self.housed_in:
            self._recalculate_infrastructure_occupancy(old_housed_in)
        
        # Update new infrastructure
        if self.housed_in:
            self._recalculate_infrastructure_occupancy(self.housed_in)
    
    def _recalculate_infrastructure_occupancy(self, infrastructure):
        """Recalculate and update infrastructure's current_occupancy"""
        if not infrastructure or infrastructure.infrastructure_type != 'Accommodation':
            return
        
        # Calculate total occupancy from all active flocks in this infrastructure
        total_occupancy = Flock.objects.filter(
            housed_in=infrastructure,
            status='Active'
        ).aggregate(total=models.Sum('current_count'))['total'] or 0
        
        # Update the infrastructure
        infrastructure.current_occupancy = total_occupancy
        infrastructure.save(update_fields=['current_occupancy'])


# =============================================================================
# DAILY PRODUCTION RECORD MODEL
# =============================================================================

class DailyProduction(models.Model):
    """
    Daily production record for a flock.
    Records eggs, mortality, feed consumption, and observations.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Associations
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='daily_productions')
    flock = models.ForeignKey(Flock, on_delete=models.CASCADE, related_name='daily_productions')
    production_date = models.DateField(
        db_index=True,
        help_text="Date of this production record"
    )
    
    # === EGG PRODUCTION (for layers) ===
    eggs_collected = models.PositiveIntegerField(
        default=0,
        help_text="Total eggs collected today"
    )
    good_eggs = models.PositiveIntegerField(
        default=0,
        help_text="Clean, sellable eggs"
    )
    broken_eggs = models.PositiveIntegerField(
        default=0,
        help_text="Eggs broken during collection"
    )
    dirty_eggs = models.PositiveIntegerField(
        default=0,
        help_text="Eggs with dirt/manure (need cleaning)"
    )
    small_eggs = models.PositiveIntegerField(
        default=0,
        help_text="Undersized eggs (below standard)"
    )
    soft_shell_eggs = models.PositiveIntegerField(
        default=0,
        help_text="Eggs with soft/thin shells"
    )
    
    # Egg Production Metrics
    production_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="(Eggs collected / current bird count) × 100"
    )
    
    # === MORTALITY ===
    birds_died = models.PositiveIntegerField(
        default=0,
        help_text="Number of birds that died today"
    )
    mortality_reason = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('Disease', 'Disease/Illness'),
            ('Predator', 'Predator Attack'),
            ('Cannibalism', 'Cannibalism/Pecking'),
            ('Heat Stress', 'Heat Stress'),
            ('Suffocation', 'Suffocation/Overcrowding'),
            ('Unknown', 'Unknown Cause'),
            ('Culled', 'Culled (Selective Removal)'),
            ('Old Age', 'Old Age/Natural')
        ]
    )
    mortality_notes = models.TextField(
        blank=True,
        help_text="Additional notes about mortality"
    )
    
    # === FEED CONSUMPTION ===
    feed_consumed_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total feed consumed today (kg)"
    )
    feed_type = models.ForeignKey(
        'feed_inventory.FeedType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_production_records',
        help_text="Type of feed given (links to Feed Inventory)"
    )
    feed_cost_today = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cost of feed consumed today (GHS)"
    )
    
    # === BIRDS SOLD ===
    birds_sold = models.PositiveIntegerField(
        default=0,
        help_text="Number of birds sold today"
    )
    birds_sold_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Revenue from birds sold (GHS)"
    )
    
    # === HEALTH OBSERVATIONS ===
    general_health = models.CharField(
        max_length=20,
        choices=[
            ('Excellent', 'Excellent'),
            ('Good', 'Good'),
            ('Fair', 'Fair'),
            ('Poor', 'Poor'),
            ('Critical', 'Critical')
        ],
        default='Good'
    )
    unusual_behavior = models.TextField(
        blank=True,
        help_text="Any unusual behavior observed (lethargy, aggression, etc.)"
    )
    signs_of_disease = models.BooleanField(
        default=False,
        help_text="Check if disease symptoms observed"
    )
    disease_symptoms = models.TextField(
        blank=True,
        help_text="Description of disease symptoms if observed"
    )
    
    # === VACCINATION/MEDICATION ===
    vaccination_given = models.BooleanField(
        default=False,
        help_text="Was vaccination administered today?"
    )
    vaccination_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of vaccine given (Newcastle, Gumboro, etc.)"
    )
    medication_given = models.BooleanField(
        default=False,
        help_text="Was medication administered today?"
    )
    medication_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of medication given"
    )
    medication_cost_today = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cost of medication/vaccination today (GHS)"
    )
    
    # === DATA ENTRY AUDIT ===
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='production_records'
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_production'
        ordering = ['-production_date']
        unique_together = [('flock', 'production_date')]
        indexes = [
            models.Index(fields=['farm', 'production_date']),
            models.Index(fields=['flock', 'production_date']),
            models.Index(fields=['-production_date']),
        ]
    
    def __str__(self):
        return f"{self.flock.flock_number} - {self.production_date}"
    
    def save(self, *args, **kwargs):
        # Track if this is an update vs create
        is_update = bool(self.pk)
        old_good_eggs = 0
        
        # Calculate production rate
        if self.flock.current_count > 0:
            self.production_rate_percent = (
                Decimal(self.eggs_collected) / Decimal(self.flock.current_count)
            ) * 100
        
        # Update flock metrics
        if is_update:
            old_record = DailyProduction.objects.filter(pk=self.pk).first()
            if old_record:
                old_good_eggs = old_record.good_eggs
                # Reverse old values
                self.flock.current_count += old_record.birds_died
                self.flock.current_count += old_record.birds_sold
                self.flock.total_eggs_produced -= old_record.eggs_collected
                self.flock.total_feed_consumed_kg -= old_record.feed_consumed_kg
                self.flock.total_feed_cost -= old_record.feed_cost_today
                self.flock.total_medication_cost -= old_record.medication_cost_today
        
        # Apply new values to flock
        self.flock.current_count -= self.birds_died
        self.flock.current_count -= self.birds_sold
        self.flock.total_eggs_produced += self.eggs_collected
        self.flock.total_feed_consumed_kg += self.feed_consumed_kg
        self.flock.total_feed_cost += self.feed_cost_today
        self.flock.total_medication_cost += self.medication_cost_today
        
        # Calculate derived flock metrics
        if self.flock.initial_count > 0:
            self.flock.average_eggs_per_bird = (
                Decimal(self.flock.total_eggs_produced) / Decimal(self.flock.initial_count)
            )
        
        self.flock.save()
        
        super().save(*args, **kwargs)
        
        # ===== UPDATE INVENTORY WITH GOOD EGGS =====
        # Only good eggs go to inventory for sale
        self._update_egg_inventory(old_good_eggs, is_update)
    
    def _update_egg_inventory(self, old_good_eggs, is_update):
        """
        Add good eggs to farm inventory when production is recorded.
        
        This bridges production tracking to sales inventory:
        - Only 'good_eggs' are added to inventory (sellable)
        - Broken, dirty, small eggs are tracked but not added to inventory
        - On update, adjusts for difference between old and new values
        """
        from sales_revenue.inventory_models import (
            FarmInventory, InventoryCategory, StockMovementType, InventoryBatch
        )
        
        # Calculate net change in good eggs
        if is_update:
            eggs_to_add = self.good_eggs - old_good_eggs
        else:
            eggs_to_add = self.good_eggs
        
        # Skip if no change
        if eggs_to_add == 0:
            return
        
        # Get or create inventory record for eggs
        inventory = FarmInventory.get_or_create_for_category(
            farm=self.farm,
            category=InventoryCategory.EGGS,
            product_name='Fresh Eggs',
            unit='piece'
        )
        
        if eggs_to_add > 0:
            # Add eggs to inventory
            inventory.add_stock(
                quantity=eggs_to_add,
                movement_type=StockMovementType.PRODUCTION,
                source_record=self,
                notes=f"From {self.flock.flock_number} on {self.production_date}",
                recorded_by=self.recorded_by,
                stock_date=self.production_date
            )
            
            # Create batch for FIFO tracking
            InventoryBatch.objects.create(
                inventory=inventory,
                source_flock=self.flock,
                source_production=self,
                initial_quantity=eggs_to_add,
                current_quantity=eggs_to_add,
                production_date=self.production_date
            )
        elif eggs_to_add < 0:
            # Handle reduction (correction) - remove from inventory
            try:
                inventory.remove_stock(
                    quantity=abs(eggs_to_add),
                    movement_type=StockMovementType.ADJUSTMENT_REMOVE,
                    reference_record=self,
                    notes=f"Correction for {self.flock.flock_number} on {self.production_date}",
                    recorded_by=self.recorded_by
                )
            except ValueError:
                # If not enough stock, just log and continue
                pass
    
    def clean(self):
        """Validate business logic"""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # ===== DATA INTEGRITY VALIDATION =====
        # Prevent farm_id mismatch (denormalization consistency)
        if self.farm_id and self.flock_id and self.farm != self.flock.farm:
            errors['farm'] = (
                f'Farm mismatch: Production farm ({self.farm.farm_name}) does not match '
                f'flock farm ({self.flock.farm.farm_name}). This indicates a data integrity issue.'
            )
        
        # ===== EGG PRODUCTION VALIDATION =====
        # Validate egg breakdown equals total
        egg_sum = (
            self.good_eggs + self.broken_eggs + self.dirty_eggs + 
            self.small_eggs + self.soft_shell_eggs
        )
        if egg_sum != self.eggs_collected:
            errors['eggs_collected'] = (
                f'Egg breakdown ({egg_sum}) must equal total eggs collected ({self.eggs_collected})'
            )
        
        # ===== MORTALITY VALIDATION =====
        # Validate mortality doesn't exceed current count
        if self.birds_died > self.flock.current_count:
            errors['birds_died'] = (
                f'Birds died ({self.birds_died}) cannot exceed current count ({self.flock.current_count})'
            )
        
        # ===== SALES VALIDATION =====
        # Validate birds sold doesn't exceed current count
        if self.birds_sold > self.flock.current_count:
            errors['birds_sold'] = (
                f'Birds sold ({self.birds_sold}) cannot exceed current count ({self.flock.current_count})'
            )
        
        # Combined mortality and sales validation
        total_removed = self.birds_died + self.birds_sold
        if total_removed > self.flock.current_count:
            errors['birds_died'] = (
                f'Total birds removed today ({total_removed}: {self.birds_died} died + '
                f'{self.birds_sold} sold) exceeds current count ({self.flock.current_count})'
            )
        
        # ===== DATE VALIDATION =====
        # Validate production date not in future
        if self.production_date > timezone.now().date():
            errors['production_date'] = 'Production date cannot be in the future'
        
        # Validate production date not before flock arrival
        if self.production_date < self.flock.arrival_date:
            errors['production_date'] = (
                f'Production date cannot be before flock arrival date ({self.flock.arrival_date})'
            )
        
        if errors:
            raise ValidationError(errors)


# =============================================================================
# MORTALITY RECORD MODEL - Detailed Death Tracking
# =============================================================================

class MortalityRecord(models.Model):
    """
    Detailed mortality tracking for disease surveillance and compensation claims.
    Links to daily production record but provides additional investigation details.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Associations
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='mortality_records')
    flock = models.ForeignKey(Flock, on_delete=models.CASCADE, related_name='mortality_records')
    daily_production = models.ForeignKey(
        DailyProduction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mortality_details'
    )
    
    # Incident Details
    date_discovered = models.DateField(
        db_index=True,
        help_text="Date mortality was discovered"
    )
    number_of_birds = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of birds that died in this incident"
    )
    
    # === CAUSE ANALYSIS ===
    probable_cause = models.CharField(
        max_length=50,
        choices=[
            ('Disease - Viral', 'Disease - Viral (Newcastle, Gumboro, etc.)'),
            ('Disease - Bacterial', 'Disease - Bacterial (E.coli, Salmonella, etc.)'),
            ('Disease - Parasitic', 'Disease - Parasitic (Worms, Coccidiosis)'),
            ('Predator', 'Predator Attack (Snake, Cat, etc.)'),
            ('Cannibalism', 'Cannibalism/Pecking'),
            ('Heat Stress', 'Heat/Environmental Stress'),
            ('Suffocation', 'Suffocation/Overcrowding'),
            ('Malnutrition', 'Malnutrition/Feed Quality'),
            ('Poisoning', 'Poisoning/Toxicity'),
            ('Unknown', 'Unknown Cause')
        ]
    )
    disease_suspected = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specific disease suspected (Newcastle Disease, Fowl Pox, etc.)"
    )
    symptoms_observed = models.JSONField(
        default=list,
        help_text="List of symptoms observed (JSON array)"
    )
    symptoms_description = models.TextField(
        blank=True,
        help_text="Detailed description of symptoms"
    )
    
    # === VETERINARY INVESTIGATION ===
    vet_inspection_required = models.BooleanField(
        default=False,
        help_text="Requires veterinary officer inspection?"
    )
    vet_inspection_requested_date = models.DateField(
        null=True,
        blank=True
    )
    vet_inspected = models.BooleanField(
        default=False,
        help_text="Has veterinary officer inspected?"
    )
    vet_inspection_date = models.DateField(
        null=True,
        blank=True
    )
    vet_inspector = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mortality_inspections',
        help_text="Veterinary officer who inspected"
    )
    vet_diagnosis = models.TextField(
        blank=True,
        help_text="Veterinary officer's diagnosis"
    )
    lab_test_conducted = models.BooleanField(
        default=False,
        help_text="Was lab test conducted?"
    )
    lab_test_results = models.TextField(
        blank=True,
        help_text="Laboratory test results"
    )
    
    # === DISPOSAL ===
    disposal_method = models.CharField(
        max_length=30,
        choices=[
            ('Burial', 'Burial'),
            ('Incineration', 'Incineration/Burning'),
            ('Composting', 'Composting'),
            ('Rendering', 'Rendering Plant'),
            ('Other', 'Other Method')
        ],
        blank=True
    )
    disposal_location = models.CharField(
        max_length=200,
        blank=True,
        help_text="GPS coordinates or description of disposal site"
    )
    disposal_date = models.DateField(
        null=True,
        blank=True
    )
    
    # === FINANCIAL IMPACT ===
    estimated_value_per_bird = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Estimated market value per bird (GHS)"
    )
    total_estimated_loss = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total financial loss (GHS)"
    )
    
    # === COMPENSATION CLAIM ===
    compensation_claimed = models.BooleanField(
        default=False,
        help_text="Has compensation been claimed?"
    )
    compensation_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Compensation amount claimed (GHS)"
    )
    compensation_status = models.CharField(
        max_length=20,
        choices=[
            ('Not Claimed', 'Not Claimed'),
            ('Pending', 'Pending Review'),
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected'),
            ('Paid', 'Paid')
        ],
        default='Not Claimed'
    )
    
    # === EVIDENCE DOCUMENTATION ===
    photo_1 = models.FileField(
        upload_to='mortality_evidence/%Y/%m/',
        null=True,
        blank=True,
        help_text="Photo evidence 1 (dead birds)"
    )
    photo_2 = models.FileField(
        upload_to='mortality_evidence/%Y/%m/',
        null=True,
        blank=True,
        help_text="Photo evidence 2"
    )
    photo_3 = models.FileField(
        upload_to='mortality_evidence/%Y/%m/',
        null=True,
        blank=True,
        help_text="Photo evidence 3"
    )
    
    # === ADDITIONAL NOTES ===
    notes = models.TextField(
        blank=True,
        help_text="Additional notes and observations"
    )
    
    # === AUDIT ===
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mortality_reports',
        help_text="Person who reported this mortality"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mortality_records'
        ordering = ['-date_discovered']
        indexes = [
            models.Index(fields=['farm', 'date_discovered']),
            models.Index(fields=['flock', 'date_discovered']),
            models.Index(fields=['probable_cause']),
            models.Index(fields=['vet_inspection_required', 'vet_inspected']),
            models.Index(fields=['compensation_claimed', 'compensation_status']),
        ]
    
    def __str__(self):
        return f"{self.flock.flock_number} - {self.date_discovered} ({self.number_of_birds} birds)"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total estimated loss
        self.total_estimated_loss = Decimal(self.number_of_birds) * self.estimated_value_per_bird
        
        # Auto-flag for vet inspection if mortality is high
        if self.number_of_birds >= 10 or self.probable_cause.startswith('Disease'):
            self.vet_inspection_required = True
            if not self.vet_inspection_requested_date:
                self.vet_inspection_requested_date = timezone.now().date()
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate business logic"""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # ===== DATA INTEGRITY VALIDATION =====
        # Prevent farm_id mismatch (denormalization consistency)
        if self.farm_id and self.flock_id and self.farm != self.flock.farm:
            errors['farm'] = (
                f'Farm mismatch: Mortality record farm ({self.farm.farm_name}) does not match '
                f'flock farm ({self.flock.farm.farm_name}). This indicates a data integrity issue.'
            )
        
        # Validate flock consistency with daily_production (if linked)
        if self.daily_production_id and self.flock_id:
            if self.flock != self.daily_production.flock:
                errors['flock'] = (
                    f'Flock mismatch: Mortality record flock ({self.flock.flock_number}) does not match '
                    f'daily production flock ({self.daily_production.flock.flock_number})'
                )
            
            # Also validate farm consistency through daily_production
            if self.farm != self.daily_production.farm:
                errors['farm'] = (
                    f'Farm mismatch: Mortality record farm does not match daily production farm. '
                    f'This indicates a data integrity issue.'
                )
        
        # ===== DATE VALIDATION =====
        # Validate date not in future
        if self.date_discovered > timezone.now().date():
            errors['date_discovered'] = 'Date cannot be in the future'
        
        # Validate date not before flock arrival
        if self.flock_id and self.date_discovered < self.flock.arrival_date:
            errors['date_discovered'] = (
                f'Date cannot be before flock arrival ({self.flock.arrival_date})'
            )
        
        # Validate vet inspection date after discovery
        if self.vet_inspection_date and self.vet_inspection_date < self.date_discovered:
            errors['vet_inspection_date'] = 'Inspection date cannot be before discovery date'
        
        # ===== BUSINESS LOGIC VALIDATION =====
        # Validate mortality count doesn't exceed flock size
        if self.flock_id and self.number_of_birds > self.flock.current_count:
            errors['number_of_birds'] = (
                f'Mortality count ({self.number_of_birds}) exceeds current flock count '
                f'({self.flock.current_count}). Please verify the numbers.'
            )
        
        # Validate vet inspection workflow
        if self.vet_inspected and not self.vet_inspection_date:
            errors['vet_inspection_date'] = (
                'Inspection date is required when marking as inspected'
            )
        
        if self.vet_inspection_date and not self.vet_inspector_id:
            errors['vet_inspector'] = (
                'Veterinary inspector must be assigned when inspection date is set'
            )
        
        # ===== COMPENSATION VALIDATION =====
        # Validate compensation claim workflow
        if self.compensation_status != 'Not Claimed' and not self.compensation_claimed:
            errors['compensation_claimed'] = (
                'compensation_claimed must be True when compensation_status is not "Not Claimed"'
            )
        
        if self.compensation_claimed and self.compensation_amount <= 0:
            errors['compensation_amount'] = (
                'Compensation amount must be greater than 0 when claim is submitted'
            )
        
        if errors:
            raise ValidationError(errors)


# =============================================================================
# HEALTH RECORD MODEL - Vaccination / Medication / Clinical Events
# =============================================================================


class HealthRecord(models.Model):
    """Tracks flock health interventions such as vaccinations, treatments, and checkups."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Associations
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='health_records')
    flock = models.ForeignKey(Flock, on_delete=models.CASCADE, related_name='health_records')

    # Event metadata
    record_date = models.DateField(db_index=True)
    record_type = models.CharField(max_length=50, default='Health Check')
    outcome = models.CharField(max_length=100, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)

    # Clinical details
    disease = models.CharField(max_length=200, blank=True)
    diagnosis = models.CharField(max_length=200, blank=True)
    symptoms = models.TextField(blank=True)
    treatment_name = models.CharField(max_length=200, blank=True)
    treatment_method = models.CharField(max_length=100, blank=True)
    dosage = models.CharField(max_length=100, blank=True)
    administering_person = models.CharField(max_length=100, blank=True)
    vet_name = models.CharField(max_length=100, blank=True)
    vet_license = models.CharField(max_length=100, blank=True)

    # Impact / cost
    birds_affected = models.PositiveIntegerField(default=0)
    cost_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Notes
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'health_records'
        ordering = ['-record_date']
        indexes = [
            models.Index(fields=['farm', 'record_date']),
            models.Index(fields=['flock', 'record_date']),
            models.Index(fields=['record_type']),
        ]

    def __str__(self):
        return f"{self.flock.flock_number} - {self.record_type} ({self.record_date})"

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        if self.farm_id and self.flock_id and self.farm != self.flock.farm:
            errors['farm'] = (
                f'Farm mismatch: Health record farm ({self.farm.farm_name}) does not match '
                f'flock farm ({self.flock.farm.farm_name}).'
            )

        if self.record_date and self.flock_id and self.record_date < self.flock.arrival_date:
            errors['record_date'] = 'Record date cannot be before flock arrival date'

        if errors:
            raise ValidationError(errors)

