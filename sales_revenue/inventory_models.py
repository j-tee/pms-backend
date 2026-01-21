"""
Farm Inventory Models

Bridges the gap between production and sales by tracking:
- Eggs collected and available for sale
- Birds ready for market
- Inventory aging and spoilage
- Stock movements (additions, sales, losses)

Flow:
1. Production (DailyProduction) → Adds to FarmInventory
2. FarmInventory → Syncs with Marketplace Product stock
3. Sales (EggSale/BirdSale) → Deducts from FarmInventory
4. Analytics → Government visibility into unsold inventory
"""

from django.db import models
from django.db.models import Sum, F, Count, Avg, Q
from django.db.models.functions import Coalesce
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from datetime import timedelta


class InventoryCategory(models.TextChoices):
    """Categories for inventory items"""
    EGGS = 'eggs', 'Eggs'
    BIRDS = 'birds', 'Live Birds'
    PROCESSED = 'processed', 'Processed Products'
    CHICKS = 'chicks', 'Day Old Chicks'


class StockMovementType(models.TextChoices):
    """Types of stock movements"""
    # Additions
    PRODUCTION = 'production', 'Production (Eggs Collected)'
    MARKET_READY = 'market_ready', 'Birds Ready for Market'
    PURCHASE = 'purchase', 'Purchased Stock'
    TRANSFER_IN = 'transfer_in', 'Transfer In'
    ADJUSTMENT_ADD = 'adjustment_add', 'Inventory Adjustment (Add)'
    PROCESSING = 'processing', 'From Processing Batch'  # NEW: Processed products added to inventory
    RETURN = 'return', 'Customer Return'  # NEW: Items returned by customers
    
    # Deductions
    SALE = 'sale', 'Sold'
    SPOILAGE = 'spoilage', 'Spoiled/Expired'
    BREAKAGE = 'breakage', 'Breakage/Loss'
    PERSONAL_USE = 'personal_use', 'Personal/Farm Use'
    TRANSFER_OUT = 'transfer_out', 'Transfer Out'
    ADJUSTMENT_REMOVE = 'adjustment_remove', 'Inventory Adjustment (Remove)'
    SENT_TO_PROCESSING = 'sent_to_processing', 'Sent to Processing'  # NEW: Birds taken for processing


class FarmInventory(models.Model):
    """
    Real-time inventory tracking for each farm.
    Maintains current stock levels and history of movements.
    
    This model aggregates stock by category and provides the 
    source of truth for what's available for sale.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Farm ownership
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    
    # Product identification
    category = models.CharField(
        max_length=20,
        choices=InventoryCategory.choices,
        db_index=True
    )
    product_name = models.CharField(
        max_length=200,
        help_text='Descriptive name (e.g., "Fresh Eggs - Grade A", "Broilers 6-8 weeks")'
    )
    sku = models.CharField(
        max_length=50,
        blank=True,
        help_text='Stock Keeping Unit for tracking'
    )
    
    # Link to marketplace product (optional)
    marketplace_product = models.OneToOneField(
        'sales_revenue.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_record',
        help_text='Linked marketplace listing'
    )
    
    # Current stock levels
    quantity_available = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Current quantity available for sale'
    )
    unit = models.CharField(
        max_length=20,
        choices=[
            ('piece', 'Piece'),
            ('crate', 'Crate (30 eggs)'),
            ('tray', 'Tray (30 eggs)'),
            ('dozen', 'Dozen'),
            ('kg', 'Kilogram'),
            ('bird', 'Bird'),
        ],
        default='piece'
    )
    
    # Value tracking
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Average cost per unit'
    )
    total_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total inventory value'
    )
    
    # Stock alerts
    low_stock_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50,
        help_text='Alert when stock falls below'
    )
    is_low_stock = models.BooleanField(default=False)
    
    # Aging and quality
    oldest_stock_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date of oldest unsold stock (for eggs: freshness tracking)'
    )
    average_age_days = models.PositiveIntegerField(
        default=0,
        help_text='Average age of current stock in days'
    )
    max_shelf_life_days = models.PositiveIntegerField(
        default=21,
        help_text='Maximum days before stock expires (21 for eggs)'
    )
    
    # Cumulative statistics
    total_added = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Total quantity ever added'
    )
    total_sold = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Total quantity ever sold'
    )
    total_lost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Total quantity lost (spoilage, breakage, etc.)'
    )
    
    # Revenue tracking
    total_revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Total revenue from sales'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_stock_update = models.DateTimeField(null=True, blank=True)
    last_sale_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'farm_inventory'
        verbose_name = 'Farm Inventory'
        verbose_name_plural = 'Farm Inventories'
        ordering = ['farm', 'category', 'product_name']
        indexes = [
            models.Index(fields=['farm', 'category']),
            models.Index(fields=['farm', 'is_low_stock']),
            models.Index(fields=['category', 'quantity_available']),
            models.Index(fields=['oldest_stock_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['farm', 'category', 'sku'],
                name='unique_inventory_sku_per_farm',
                condition=~Q(sku='')
            )
        ]
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.product_name}: {self.quantity_available} {self.unit}"
    
    def save(self, *args, **kwargs):
        # Update low stock flag
        self.is_low_stock = self.quantity_available <= self.low_stock_threshold
        
        # Calculate total value
        self.total_value = self.quantity_available * self.unit_cost
        
        # Update last stock update time
        self.last_stock_update = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Sync with marketplace product if linked
        self.sync_marketplace_product()
    
    def sync_marketplace_product(self):
        """
        Sync stock quantity and status with linked marketplace product.
        
        This ensures the marketplace product reflects the true inventory state:
        - stock_quantity is updated from inventory
        - status is set to 'out_of_stock' if no stock available
        - status is restored to 'active' when stock is replenished
        """
        if self.marketplace_product:
            from sales_revenue.marketplace_models import Product
            
            # Determine the correct status based on inventory
            new_status = 'active' if self.quantity_available > 0 else 'out_of_stock'
            
            # Only update status if transitioning between active/out_of_stock
            # Don't override draft or discontinued
            current_status = self.marketplace_product.status
            if current_status in ['active', 'out_of_stock']:
                Product.objects.filter(id=self.marketplace_product_id).update(
                    stock_quantity=int(self.quantity_available),
                    status=new_status,
                    updated_at=timezone.now()
                )
            else:
                # Just update quantity, don't change status
                Product.objects.filter(id=self.marketplace_product_id).update(
                    stock_quantity=int(self.quantity_available),
                    updated_at=timezone.now()
                )
    
    def add_stock(self, quantity, movement_type, source_record=None, 
                  unit_cost=None, notes='', recorded_by=None, stock_date=None):
        """
        Add stock to inventory with movement tracking.
        
        Args:
            quantity: Amount to add
            movement_type: StockMovementType value
            source_record: Link to source (DailyProduction, Flock, etc.)
            unit_cost: Cost per unit (updates average if provided)
            notes: Additional notes
            recorded_by: User who made the entry
            stock_date: Date of the stock (for age tracking)
        """
        quantity = Decimal(str(quantity))
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Update average cost using weighted average
        if unit_cost is not None:
            unit_cost = Decimal(str(unit_cost))
            total_old_value = self.quantity_available * self.unit_cost
            total_new_value = quantity * unit_cost
            new_total_quantity = self.quantity_available + quantity
            
            if new_total_quantity > 0:
                self.unit_cost = (total_old_value + total_new_value) / new_total_quantity
        
        # Update stock date for age tracking
        if stock_date:
            if not self.oldest_stock_date or stock_date < self.oldest_stock_date:
                self.oldest_stock_date = stock_date
        
        # Update quantities
        self.quantity_available += quantity
        self.total_added += quantity
        
        self.save()
        
        # Create movement record
        movement = StockMovement.objects.create(
            inventory=self,
            farm=self.farm,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost or self.unit_cost,
            balance_after=self.quantity_available,
            source_type=self._get_source_type(source_record),
            source_id=str(source_record.id) if source_record else None,
            notes=notes,
            recorded_by=recorded_by,
            stock_date=stock_date or timezone.now().date()
        )
        
        return movement
    
    def remove_stock(self, quantity, movement_type, reference_record=None,
                     unit_price=None, notes='', recorded_by=None):
        """
        Remove stock from inventory with movement tracking.
        
        ATOMICITY: This method should be called within a transaction.
        The caller is responsible for using @transaction.atomic and select_for_update()
        to prevent race conditions.
        
        Args:
            quantity: Amount to remove
            movement_type: StockMovementType value
            reference_record: Link to sale or other reference
            unit_price: Sale price per unit (for revenue tracking)
            notes: Additional notes
            recorded_by: User who made the entry
            
        Raises:
            ValueError: If quantity is invalid or exceeds available stock
        """
        from django.db import transaction
        
        quantity = Decimal(str(quantity))
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if quantity > self.quantity_available:
            raise ValueError(
                f"Insufficient stock. Available: {self.quantity_available}, "
                f"Requested: {quantity}"
            )
        
        # Update quantities
        self.quantity_available -= quantity
        
        # Track by movement type
        if movement_type == StockMovementType.SALE:
            self.total_sold += quantity
            self.last_sale_date = timezone.now()
            if unit_price:
                self.total_revenue += quantity * Decimal(str(unit_price))
        else:
            self.total_lost += quantity
        
        # Update oldest stock date if all stock sold
        if self.quantity_available == 0:
            self.oldest_stock_date = None
            self.average_age_days = 0
        
        # Save inventory (this also syncs marketplace product)
        self.save()
        
        # Create movement record (audit trail)
        movement = StockMovement.objects.create(
            inventory=self,
            farm=self.farm,
            movement_type=movement_type,
            quantity=-quantity,  # Negative for removals
            unit_cost=unit_price or self.unit_cost,
            balance_after=self.quantity_available,
            source_type=self._get_source_type(reference_record),
            source_id=str(reference_record.id) if reference_record else None,
            notes=notes,
            recorded_by=recorded_by,
            stock_date=timezone.now().date()
        )
        
        return movement
    
    def _get_source_type(self, source_record):
        """Determine the source type string from a record."""
        if not source_record:
            return None
        model_name = source_record.__class__.__name__
        return model_name
    
    @property
    def days_since_last_sale(self):
        """Days since last sale (indicator of selling difficulty)."""
        if not self.last_sale_date:
            return None
        return (timezone.now() - self.last_sale_date).days
    
    @property
    def turnover_rate(self):
        """Inventory turnover rate (sales / average stock)."""
        if self.total_added == 0:
            return 0
        return float(self.total_sold / self.total_added) * 100
    
    @property
    def stock_health(self):
        """
        Stock health indicator based on age and turnover.
        Returns: 'critical', 'warning', 'healthy'
        """
        if self.quantity_available == 0:
            return 'empty'
        
        # Check age-based expiry risk
        if self.average_age_days > self.max_shelf_life_days * 0.8:
            return 'critical'
        
        # Check days since last sale
        if self.days_since_last_sale and self.days_since_last_sale > 7:
            return 'warning'
        
        # Check if too much stock sitting
        if self.average_age_days > self.max_shelf_life_days * 0.5:
            return 'warning'
        
        return 'healthy'
    
    @classmethod
    def get_or_create_for_category(cls, farm, category, product_name, unit='piece'):
        """Get or create inventory record for a farm/category combo."""
        inventory, created = cls.objects.get_or_create(
            farm=farm,
            category=category,
            product_name=product_name,
            defaults={
                'unit': unit,
                'sku': f"{category.upper()[:3]}-{farm.id.hex[:6]}".upper()
            }
        )
        return inventory


class StockMovement(models.Model):
    """
    Tracks all stock movements (additions and deductions).
    Provides audit trail and history for inventory changes.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    inventory = models.ForeignKey(
        FarmInventory,
        on_delete=models.CASCADE,
        related_name='movements'
    )
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='stock_movements'
    )
    
    # Movement details
    movement_type = models.CharField(
        max_length=30,
        choices=StockMovementType.choices,
        db_index=True
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Positive for additions, negative for removals'
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Cost/price per unit at time of movement'
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Stock balance after this movement'
    )
    
    # Source tracking (polymorphic reference)
    source_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Model name of source record (DailyProduction, EggSale, etc.)'
    )
    source_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='UUID of source record'
    )
    
    # Date of the stock (for FIFO tracking)
    stock_date = models.DateField(
        help_text='Date the stock was produced/received'
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_movements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['inventory', '-created_at']),
            models.Index(fields=['farm', '-created_at']),
            models.Index(fields=['movement_type', '-created_at']),
            models.Index(fields=['source_type', 'source_id']),
        ]
    
    def __str__(self):
        action = "Added" if self.quantity > 0 else "Removed"
        return f"{action} {abs(self.quantity)} - {self.get_movement_type_display()}"


class InventoryBatch(models.Model):
    """
    Tracks individual batches within inventory for FIFO and expiry management.
    Especially important for eggs which have limited shelf life.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    inventory = models.ForeignKey(
        FarmInventory,
        on_delete=models.CASCADE,
        related_name='batches'
    )
    
    # Batch identification
    batch_number = models.CharField(
        max_length=50,
        help_text='Auto-generated batch identifier'
    )
    
    # Source tracking
    source_flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_batches'
    )
    source_production = models.ForeignKey(
        'flock_management.DailyProduction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_batches'
    )
    
    # Quantity tracking
    initial_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    current_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Dates
    production_date = models.DateField(
        help_text='Date the items were produced/collected'
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text='Calculated expiry date'
    )
    
    # Status
    is_depleted = models.BooleanField(
        default=False,
        help_text='True when all items have been sold/used'
    )
    is_expired = models.BooleanField(
        default=False,
        help_text='True when batch has expired'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    depleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'inventory_batches'
        ordering = ['production_date']  # FIFO ordering
        indexes = [
            models.Index(fields=['inventory', 'is_depleted']),
            models.Index(fields=['production_date']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"Batch {self.batch_number}: {self.current_quantity} remaining"
    
    def save(self, *args, **kwargs):
        # Auto-generate batch number
        if not self.batch_number:
            self.batch_number = f"B-{self.production_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Calculate expiry date if not set
        if not self.expiry_date and self.production_date:
            self.expiry_date = self.production_date + timedelta(
                days=self.inventory.max_shelf_life_days
            )
        
        # Update depleted status
        if self.current_quantity <= 0:
            self.is_depleted = True
            if not self.depleted_at:
                self.depleted_at = timezone.now()
        
        # Update expired status
        if self.expiry_date and timezone.now().date() > self.expiry_date:
            self.is_expired = True
        
        super().save(*args, **kwargs)
    
    @property
    def age_days(self):
        """Age of this batch in days."""
        return (timezone.now().date() - self.production_date).days
    
    @property
    def days_until_expiry(self):
        """Days until expiry (negative if expired)."""
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days
    
    def consume(self, quantity):
        """
        Consume quantity from this batch (FIFO).
        Returns actual quantity consumed.
        """
        quantity = Decimal(str(quantity))
        consumed = min(quantity, self.current_quantity)
        self.current_quantity -= consumed
        self.save()
        return consumed


class BirdsReadyForMarket(models.Model):
    """
    Tracks birds that have reached market-ready weight/age.
    Links to flock and creates inventory entries for marketable birds.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='birds_ready_for_market'
    )
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.CASCADE,
        related_name='market_ready_records'
    )
    
    # Ready for market details
    date_ready = models.DateField(
        default=timezone.now,
        help_text='Date birds were marked as ready for market'
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Number of birds ready for market'
    )
    
    # Bird details
    bird_type = models.CharField(
        max_length=20,
        choices=[
            ('broiler', 'Broiler'),
            ('layer', 'Layer'),
            ('spent_hen', 'Spent Hen'),
            ('cockerel', 'Cockerel'),
        ]
    )
    average_weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Average weight per bird in kg'
    )
    
    # Pricing
    estimated_price_per_bird = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Expected selling price per bird'
    )
    total_estimated_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )
    
    # Stock tracking
    quantity_sold = models.PositiveIntegerField(default=0)
    quantity_remaining = models.PositiveIntegerField(default=0)
    
    # Link to inventory
    inventory_entry = models.ForeignKey(
        FarmInventory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bird_ready_records'
    )
    
    # Status
    is_fully_sold = models.BooleanField(default=False)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Audit
    recorded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='birds_ready_records'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'birds_ready_for_market'
        ordering = ['-date_ready']
        indexes = [
            models.Index(fields=['farm', '-date_ready']),
            models.Index(fields=['flock', '-date_ready']),
            models.Index(fields=['is_fully_sold']),
        ]
    
    def __str__(self):
        return f"{self.quantity} {self.bird_type}s ready - {self.farm.farm_name}"
    
    def save(self, *args, **kwargs):
        # Calculate total value
        self.total_estimated_value = self.quantity * self.estimated_price_per_bird
        
        # Set initial remaining
        if not self.pk:
            self.quantity_remaining = self.quantity
        
        # Update fully sold flag
        self.is_fully_sold = self.quantity_remaining == 0
        
        super().save(*args, **kwargs)
        
        # Create or update inventory entry
        if not self.inventory_entry:
            self._create_inventory_entry()
    
    def _create_inventory_entry(self):
        """Create inventory entry for these market-ready birds."""
        inventory = FarmInventory.get_or_create_for_category(
            farm=self.farm,
            category=InventoryCategory.BIRDS,
            product_name=f"Live {self.bird_type.title()}s",
            unit='bird'
        )
        
        # Add to inventory
        inventory.add_stock(
            quantity=self.quantity,
            movement_type=StockMovementType.MARKET_READY,
            source_record=self,
            unit_cost=self.estimated_price_per_bird,
            notes=f"From flock {self.flock.flock_number}"
        )
        
        self.inventory_entry = inventory
        self.save(update_fields=['inventory_entry'])
    
    def record_sale(self, quantity_sold):
        """Record birds sold from this batch."""
        if quantity_sold > self.quantity_remaining:
            raise ValueError(
                f"Cannot sell {quantity_sold} birds. Only {self.quantity_remaining} remaining."
            )
        
        self.quantity_sold += quantity_sold
        self.quantity_remaining -= quantity_sold
        self.save()


# =============================================================================
# INVENTORY ANALYTICS FOR GOVERNMENT VISIBILITY
# =============================================================================

class InventoryAnalyticsManager(models.Manager):
    """
    Manager for generating inventory analytics across farms.
    Provides government visibility into farmers struggling to sell.
    """
    
    def farms_with_selling_challenges(self, days_threshold=7, min_stock_value=100):
        """
        Identify farms having difficulty selling products.
        
        Criteria:
        - Stock sitting for more than X days without sales
        - High stock value but low turnover
        - Expiring products
        
        Args:
            days_threshold: Days without sales to consider a challenge
            min_stock_value: Minimum stock value to consider
            
        Returns:
            QuerySet of FarmInventory with challenge indicators
        """
        threshold_date = timezone.now() - timedelta(days=days_threshold)
        
        return self.get_queryset().filter(
            is_active=True,
            quantity_available__gt=0,
            total_value__gte=min_stock_value
        ).filter(
            Q(last_sale_date__isnull=True) |  # Never sold
            Q(last_sale_date__lt=threshold_date)  # No recent sales
        ).select_related('farm').annotate(
            days_without_sale=Coalesce(
                (timezone.now() - F('last_sale_date')).days,
                (timezone.now() - F('created_at')).days
            )
        ).order_by('-total_value', '-days_without_sale')
    
    def expiring_stock_summary(self, days_until_expiry=3):
        """
        Get summary of stock expiring soon.
        Critical for intervention planning.
        """
        expiry_threshold = timezone.now().date() + timedelta(days=days_until_expiry)
        
        return InventoryBatch.objects.filter(
            is_depleted=False,
            is_expired=False,
            expiry_date__lte=expiry_threshold,
            current_quantity__gt=0
        ).select_related(
            'inventory__farm'
        ).order_by('expiry_date')
    
    def regional_stock_summary(self, region=None):
        """
        Aggregate stock summary by region.
        Useful for government regional planning.
        """
        queryset = self.get_queryset().filter(
            is_active=True,
            quantity_available__gt=0
        ).select_related('farm')
        
        if region:
            queryset = queryset.filter(farm__primary_region=region)
        
        return queryset.values(
            'farm__primary_region'
        ).annotate(
            total_farms=Count('farm', distinct=True),
            total_stock_value=Sum('total_value'),
            total_unsold_quantity=Sum('quantity_available'),
            avg_days_since_sale=Avg(
                (timezone.now() - F('last_sale_date')).days
            )
        ).order_by('farm__primary_region')


class FarmInventoryAnalytics(FarmInventory):
    """
    Proxy model with analytics manager for government reporting.
    """
    objects = InventoryAnalyticsManager()
    
    class Meta:
        proxy = True
        verbose_name = 'Inventory Analytics'
        verbose_name_plural = 'Inventory Analytics'
