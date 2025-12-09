"""
Feed Inventory Management Models

This module handles feed inventory tracking for the YEA Poultry Management System.
Tracks feed types, purchases, stock levels, and daily consumption.

Models:
    - FeedType: Master data for different types of poultry feed
    - FeedPurchase: Records of feed purchase transactions (includes supplier name)
    - FeedInventory: Current stock levels per farm
    - FeedConsumption: Daily feed consumption by feed type
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class FeedType(models.Model):
    """
    Master data for different types of poultry feed.
    
    Stores comprehensive information about feed types including nutritional
    content, pricing, and usage guidelines.
    """
    
    FEED_CATEGORY_CHOICES = [
        ('STARTER', 'Starter Feed (0-8 weeks)'),
        ('GROWER', 'Grower Feed (9-18 weeks)'),
        ('LAYER', 'Layer Feed (19+ weeks)'),
        ('BROILER_STARTER', 'Broiler Starter (0-3 weeks)'),
        ('BROILER_FINISHER', 'Broiler Finisher (4+ weeks)'),
        ('BREEDER', 'Breeder Feed'),
        ('SUPPLEMENT', 'Supplement/Premix'),
        ('MEDICATION', 'Medicated Feed'),
    ]
    
    FORM_CHOICES = [
        ('MASH', 'Mash'),
        ('PELLET', 'Pellet'),
        ('CRUMBLE', 'Crumble'),
        ('GRAIN', 'Whole Grain'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=100, unique=True, help_text="Name of the feed type (e.g., 'Layer Mash 16%')")
    category = models.CharField(max_length=20, choices=FEED_CATEGORY_CHOICES, help_text="Feed category based on bird age/type")
    form = models.CharField(max_length=10, choices=FORM_CHOICES, default='MASH', help_text="Physical form of the feed")
    manufacturer = models.CharField(max_length=100, blank=True, help_text="Feed manufacturer/brand")
    
    # Nutritional Information
    protein_content = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('50.00'))],
        help_text="Crude protein percentage (0-50%)"
    )
    energy_content = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Metabolizable Energy (ME) in kcal/kg",
        null=True,
        blank=True
    )
    calcium_content = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('10.00'))],
        help_text="Calcium percentage (0-10%)",
        null=True,
        blank=True
    )
    phosphorus_content = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))],
        help_text="Phosphorus percentage (0-5%)",
        null=True,
        blank=True
    )
    
    # Usage Information
    recommended_age_weeks_min = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Minimum bird age in weeks for this feed"
    )
    recommended_age_weeks_max = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Maximum bird age in weeks for this feed"
    )
    daily_consumption_per_bird_grams = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Average daily consumption per bird in grams"
    )
    
    # Pricing (Reference only - actual prices in FeedPurchase)
    standard_price_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Standard/reference price per kg (GHS)",
        null=True,
        blank=True
    )
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Whether this feed type is currently available")
    description = models.TextField(blank=True, help_text="Additional description or notes about this feed type")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Feed Type'
        verbose_name_plural = 'Feed Types'
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    def clean(self):
        """Validate feed type data."""
        errors = {}
        
        # Age range validation
        if self.recommended_age_weeks_min is not None and self.recommended_age_weeks_max is not None:
            if self.recommended_age_weeks_min > self.recommended_age_weeks_max:
                errors['recommended_age_weeks_max'] = "Maximum age must be greater than minimum age"
        
        # Category-specific validations
        if self.category == 'LAYER' and self.calcium_content:
            if self.calcium_content < Decimal('3.0'):
                errors['calcium_content'] = "Layer feed typically requires at least 3% calcium"
        
        if errors:
            raise ValidationError(errors)


class FeedPurchase(models.Model):
    """
    Records of feed purchase transactions.
    
    Tracks all feed purchases including supplier, quantity, pricing, and payment status.
    """
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Payment Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Fully Paid'),
        ('OVERDUE', 'Overdue'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Auto-generated Batch Number
    batch_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        null=True,
        blank=True,
        help_text="System-generated unique batch ID (FSTK-YYYYMMDD-####)"
    )
    
    # Relationships
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.PROTECT,
        related_name='feed_purchases',
        help_text="Farm making the purchase"
    )
    supplier = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of the supplier"
    )
    supplier_contact = models.CharField(
        max_length=100,
        blank=True,
        help_text="Supplier contact information"
    )
    feed_type = models.ForeignKey(
        FeedType,
        on_delete=models.PROTECT,
        related_name='purchases',
        help_text="Type of feed purchased"
    )
    brand = models.CharField(
        max_length=100,
        blank=True,
        help_text="Brand of the feed"
    )
    
    # Purchase Details
    purchase_date = models.DateField(help_text="Date of purchase")
    delivery_date = models.DateField(null=True, blank=True, help_text="Expected or actual delivery date")
    receipt_number = models.CharField(max_length=50, blank=True, help_text="Receipt number")
    invoice_number = models.CharField(max_length=50, blank=True, help_text="Supplier invoice number or batch number")
    
    # Quantity and Pricing
    quantity_bags = models.PositiveIntegerField(
        default=1,
        help_text="Number of bags purchased"
    )
    bag_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('50.00'),
        help_text="Weight per bag in kilograms"
    )
    quantity_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('50.00'),
        help_text="Total quantity purchased in kilograms (auto-calculated from bags × weight)"
    )
    stock_balance_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Remaining stock balance in kilograms (updated on consumption)"
    )
    unit_cost_ghs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Cost per bag (GHS)"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Price per kilogram (GHS) - auto-calculated"
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Total cost (quantity × unit_price)"
    )
    
    # Payment Information
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        help_text="Current payment status"
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Payment method (Cash, Mobile Money, Bank Transfer, etc.)"
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Amount already paid (GHS)"
    )
    payment_due_date = models.DateField(null=True, blank=True, help_text="Payment due date")
    
    # Delivery Information
    received_by = models.CharField(max_length=100, blank=True, help_text="Person who received the delivery")
    
    # Additional Information
    notes = models.TextField(blank=True, help_text="Additional notes about this purchase")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feed_purchases_created',
        help_text="User who created this record"
    )
    
    class Meta:
        ordering = ['-purchase_date', '-created_at']
        verbose_name = 'Feed Purchase'
        verbose_name_plural = 'Feed Purchases'
        indexes = [
            models.Index(fields=['farm', 'purchase_date']),
            models.Index(fields=['supplier', 'purchase_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['-purchase_date']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['stock_balance_kg']),
        ]
    
    def __str__(self):
        return f"{self.farm.name} - {self.feed_type.name} ({self.purchase_date})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate derived fields before saving."""
        # Generate batch_number if this is a new record
        if not self.batch_number:
            from django.utils import timezone
            date_str = self.purchase_date.strftime('%Y%m%d') if self.purchase_date else timezone.now().strftime('%Y%m%d')
            
            # Get the count of purchases for this date to generate sequence
            count = FeedPurchase.objects.filter(
                batch_number__startswith=f'FSTK-{date_str}'
            ).count()
            
            sequence = str(count + 1).zfill(4)
            self.batch_number = f'FSTK-{date_str}-{sequence}'
        
        # Calculate total quantity from bags and weight
        self.quantity_kg = Decimal(str(self.quantity_bags)) * self.bag_weight_kg
        
        # Initialize stock_balance_kg to quantity_kg for new purchases
        if not self.pk and self.stock_balance_kg == Decimal('0.00'):
            self.stock_balance_kg = self.quantity_kg
        
        # Calculate price per kg from cost per bag
        if self.bag_weight_kg > 0:
            self.unit_price = self.unit_cost_ghs / self.bag_weight_kg
        
        # Calculate total cost
        self.total_cost = self.quantity_kg * self.unit_price
        
        # Auto-calculate amount_paid based on payment_status if not explicitly set
        if self.payment_status == 'PAID' and self.amount_paid == Decimal('0.00'):
            self.amount_paid = self.total_cost
        elif self.payment_status == 'PENDING' and self.amount_paid > Decimal('0.00'):
            # If amount was paid but status is pending, it should be partial
            self.payment_status = 'PARTIAL'
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate purchase data."""
        errors = {}
        
        # Date validations only - let save() handle payment calculations
        if self.delivery_date and self.purchase_date and self.delivery_date < self.purchase_date:
            errors['delivery_date'] = "Delivery date cannot be before purchase date"
        
        if self.payment_due_date and self.purchase_date and self.payment_due_date < self.purchase_date:
            errors['payment_due_date'] = "Payment due date cannot be before purchase date"
        
        if errors:
            raise ValidationError(errors)


class FeedInventory(models.Model):
    """
    Current stock levels per farm.
    
    Tracks real-time feed inventory levels, reorder points, and stock alerts.
    One record per farm per feed type.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='feed_inventory',
        help_text="Farm storing the feed"
    )
    feed_type = models.ForeignKey(
        FeedType,
        on_delete=models.PROTECT,
        related_name='inventory_records',
        help_text="Type of feed in stock"
    )
    
    # Stock Levels
    current_stock_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Current stock level in kilograms"
    )
    min_stock_level = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('100.00'),
        help_text="Minimum stock level (reorder point) in kg"
    )
    max_stock_level = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('1000.00'),
        help_text="Maximum stock level (storage capacity) in kg"
    )
    
    # Stock Value (Auto-calculated based on weighted average cost)
    average_cost_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Weighted average cost per kg (GHS)"
    )
    total_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Total stock value (current_stock_kg × average_cost_per_kg)"
    )
    
    # Stock Movement Tracking
    last_purchase_date = models.DateField(null=True, blank=True, help_text="Date of last purchase")
    last_consumption_date = models.DateField(null=True, blank=True, help_text="Date of last consumption")
    
    # Alerts
    low_stock_alert = models.BooleanField(
        default=False,
        help_text="Auto-set when stock falls below minimum level"
    )
    
    # Storage Information
    storage_location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Physical storage location on farm"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['farm', 'feed_type']
        verbose_name = 'Feed Inventory'
        verbose_name_plural = 'Feed Inventories'
        unique_together = [['farm', 'feed_type']]
        indexes = [
            models.Index(fields=['farm', 'feed_type']),
            models.Index(fields=['low_stock_alert']),
        ]
    
    def __str__(self):
        return f"{self.farm.name} - {self.feed_type.name} ({self.current_stock_kg} kg)"
    
    def save(self, *args, **kwargs):
        """Auto-calculate values before saving."""
        # Calculate total value
        self.total_value = self.current_stock_kg * self.average_cost_per_kg
        
        # Check for low stock alert
        self.low_stock_alert = self.current_stock_kg < self.min_stock_level
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate inventory data."""
        errors = {}
        
        # Stock level validations
        if self.min_stock_level > self.max_stock_level:
            errors['min_stock_level'] = "Minimum stock level cannot exceed maximum stock level"
        
        if self.current_stock_kg > self.max_stock_level:
            errors['current_stock_kg'] = f"Current stock ({self.current_stock_kg} kg) exceeds maximum capacity ({self.max_stock_level} kg)"
        
        if errors:
            raise ValidationError(errors)
    
    def update_stock(self, quantity_change, new_average_cost=None):
        """
        Update stock levels after purchase or consumption.
        
        Args:
            quantity_change: Positive for purchases, negative for consumption
            new_average_cost: New weighted average cost (for purchases)
        """
        self.current_stock_kg += quantity_change
        
        if new_average_cost is not None:
            self.average_cost_per_kg = new_average_cost
        
        if quantity_change > 0:
            self.last_purchase_date = timezone.now().date()
        elif quantity_change < 0:
            self.last_consumption_date = timezone.now().date()
        
        self.save()


class FeedConsumption(models.Model):
    """
    Daily feed consumption by feed type.
    
    Provides detailed breakdown of feed usage per type, linking to DailyProduction
    records for comprehensive tracking.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    daily_production = models.ForeignKey(
        'flock_management.DailyProduction',
        on_delete=models.CASCADE,
        related_name='feed_consumption_records',
        help_text="Link to daily production record"
    )
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.PROTECT,
        related_name='feed_consumption_records',
        help_text="Farm where feed was consumed (denormalized for query performance)"
    )
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.PROTECT,
        related_name='feed_consumption_records',
        help_text="Flock that consumed the feed (denormalized for query performance)"
    )
    feed_stock = models.ForeignKey(
        FeedPurchase,
        on_delete=models.PROTECT,
        related_name='consumption_records',
        null=True,
        blank=True,
        help_text="Specific feed stock/batch being consumed"
    )
    feed_type = models.ForeignKey(
        FeedType,
        on_delete=models.PROTECT,
        related_name='consumption_records',
        null=True,
        blank=True,
        help_text="Type of feed consumed (denormalized from feed_stock)"
    )
    
    # Consumption Details
    date = models.DateField(help_text="Date of consumption (denormalized from daily_production)")
    quantity_consumed_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Quantity consumed in kilograms"
    )
    
    # Cost Tracking
    cost_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Cost per kg at time of consumption (from inventory)"
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Total cost (quantity × cost_per_kg)"
    )
    
    # Efficiency Metrics
    birds_count_at_consumption = models.PositiveIntegerField(
        help_text="Number of birds in flock at time of consumption"
    )
    consumption_per_bird_grams = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Feed consumed per bird in grams (auto-calculated)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'feed_type']
        verbose_name = 'Feed Consumption'
        verbose_name_plural = 'Feed Consumption Records'
        indexes = [
            models.Index(fields=['daily_production', 'feed_type']),
            models.Index(fields=['farm', 'date']),
            models.Index(fields=['flock', 'date']),
            models.Index(fields=['-date']),
        ]
    
    def __str__(self):
        return f"{self.flock.name} - {self.feed_type.name} ({self.date})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate values before saving."""
        is_new = not self.pk
        
        # Denormalize feed_type from feed_stock
        if self.feed_stock_id:
            self.feed_type = self.feed_stock.feed_type
            self.cost_per_kg = self.feed_stock.unit_price
        
        # Calculate total cost
        self.total_cost = self.quantity_consumed_kg * self.cost_per_kg
        
        # Calculate per-bird consumption in grams
        if self.birds_count_at_consumption > 0:
            kg_per_bird = self.quantity_consumed_kg / self.birds_count_at_consumption
            self.consumption_per_bird_grams = kg_per_bird * 1000
        else:
            self.consumption_per_bird_grams = Decimal('0.00')
        
        # Denormalize date from daily_production
        if self.daily_production_id:
            self.date = self.daily_production.production_date
            self.farm = self.daily_production.farm
            self.flock = self.daily_production.flock
        
        super().save(*args, **kwargs)
        
        # Update feed stock balance after saving (only for new records)
        if is_new and self.feed_stock_id:
            self.feed_stock.stock_balance_kg -= self.quantity_consumed_kg
            self.feed_stock.save(update_fields=['stock_balance_kg'])
    
    def clean(self):
        """Validate consumption data."""
        errors = {}
        
        # Farm consistency check
        if self.daily_production_id and self.farm_id:
            if self.farm != self.daily_production.farm:
                errors['farm'] = f"Farm must match daily production farm ({self.daily_production.farm.name})"
        
        # Flock consistency check
        if self.daily_production_id and self.flock_id:
            if self.flock != self.daily_production.flock:
                errors['flock'] = f"Flock must match daily production flock ({self.daily_production.flock.name})"
        
        # Stock balance validation - prevent negative draws
        if self.feed_stock_id and self.quantity_consumed_kg:
            if self.quantity_consumed_kg > self.feed_stock.stock_balance_kg:
                errors['quantity_consumed_kg'] = f"Insufficient stock. Available: {self.feed_stock.stock_balance_kg} kg, Requested: {self.quantity_consumed_kg} kg"
        
        # Bird count validation
        if self.birds_count_at_consumption == 0:
            errors['birds_count_at_consumption'] = "Bird count must be greater than 0"
        
        # Reasonable consumption validation (0-300g per bird per day)
        if self.birds_count_at_consumption > 0:
            grams_per_bird = (self.quantity_consumed_kg * 1000) / self.birds_count_at_consumption
            if grams_per_bird > 300:
                errors['quantity_consumed_kg'] = f"Consumption per bird ({grams_per_bird:.1f}g) exceeds reasonable limit (300g/bird/day)"
        
        if errors:
            raise ValidationError(errors)
