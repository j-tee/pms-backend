"""
Processing Models for Bird Processing Operations.

This module handles the transformation of live birds into processed/packaged products.

Two Pathways for Birds:
1. LIVE BIRD SALES: Flock → BirdsReadyForMarket → BirdSale (existing)
2. PROCESSING: Flock → ProcessingBatch → ProcessingOutput → FarmInventory → Sales (new)

Key Tracking:
- Traceability: Each processed product traces back to source flock
- Aging: Track how long products have been in stock
- Government visibility: Identify stale stock for intervention
"""

import uuid
from decimal import Decimal
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


class ProcessingBatchStatus(models.TextChoices):
    """Status choices for processing batches."""
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class ProcessingType(models.TextChoices):
    """Types of processing operations."""
    SLAUGHTER = 'slaughter', 'Slaughter & Dressing'
    PORTIONING = 'portioning', 'Portioning'
    PACKAGING = 'packaging', 'Packaging'
    SMOKING = 'smoking', 'Smoking'
    FREEZING = 'freezing', 'Freezing'
    MIXED = 'mixed', 'Mixed Processing'


class ProductCategory(models.TextChoices):
    """Categories of processed bird products."""
    WHOLE_BIRD = 'whole_bird', 'Whole Dressed Bird'
    BREAST = 'breast', 'Breast'
    THIGH = 'thigh', 'Thigh'
    DRUMSTICK = 'drumstick', 'Drumstick'
    WING = 'wing', 'Wing'
    BACK = 'back', 'Back'
    GIZZARD = 'gizzard', 'Gizzard'
    LIVER = 'liver', 'Liver'
    HEART = 'heart', 'Heart'
    NECK = 'neck', 'Neck'
    FEET = 'feet', 'Feet'
    OFFAL = 'offal', 'Offal/By-products'


class ProductGrade(models.TextChoices):
    """Quality grades for processed products."""
    A = 'A', 'Grade A - Premium'
    B = 'B', 'Grade B - Standard'
    C = 'C', 'Grade C - Economy'


class ProcessingBatch(models.Model):
    """
    Records when live birds are transformed into processed/packaged products.
    
    Flow: Flock → ProcessingBatch → ProcessingOutput → Inventory → Sales
    
    This is the critical link between live bird tracking (Flock) and 
    processed product inventory (FarmInventory).
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # Farm ownership
    farm = models.ForeignKey(
        'farms.Farm', 
        on_delete=models.CASCADE,
        related_name='processing_batches'
    )
    
    # Source birds - links to flock for traceability
    source_flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.PROTECT,
        related_name='processing_batches',
        help_text='The flock from which birds were taken for processing'
    )
    
    # Optional: Link to BirdsReadyForMarket if birds were already marked ready
    source_birds_ready = models.ForeignKey(
        'sales_revenue.BirdsReadyForMarket',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processing_batches',
        help_text='Optional link if birds came from market-ready inventory'
    )
    
    # Processing details
    batch_number = models.CharField(
        max_length=50, 
        unique=True,
        db_index=True,
        help_text='Unique identifier for this processing batch'
    )
    birds_processed = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Number of birds processed in this batch'
    )
    
    # Weight-based tracking: birds (count) → processing → products (kg)
    average_bird_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text='Average weight per bird in kg (e.g., 4.0 kg)'
    )
    expected_yield_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Expected total yield in kg (birds_processed × average_bird_weight_kg)'
    )
    actual_yield_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Actual total weight of all products produced in kg'
    )
    
    processing_date = models.DateField(
        default=timezone.localdate,
        help_text='Date when processing occurred'
    )
    processing_type = models.CharField(
        max_length=20, 
        choices=ProcessingType.choices,
        default=ProcessingType.SLAUGHTER
    )
    
    # Cost tracking - for profitability analysis
    bird_cost_per_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text='Cost per bird (auto-calculated from flock if not provided)'
    )
    labor_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text='Labor cost for this processing batch'
    )
    processing_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text='Other processing costs (equipment, utilities, etc.)'
    )
    packaging_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text='Packaging materials cost'
    )
    
    # Losses during processing
    birds_lost_in_processing = models.PositiveIntegerField(
        default=0,
        help_text='Birds lost due to processing issues'
    )
    loss_reason = models.TextField(
        blank=True,
        help_text='Reason for any losses'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20, 
        choices=ProcessingBatchStatus.choices, 
        default=ProcessingBatchStatus.PENDING
    )
    
    # Completion tracking
    completed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='When the batch was marked as completed'
    )
    inventory_updated = models.BooleanField(
        default=False,
        help_text='Whether inventory has been updated with outputs'
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text='Additional notes about this processing batch'
    )
    
    # Audit fields
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='processing_batches_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-processing_date', '-created_at']
        verbose_name = 'Processing Batch'
        verbose_name_plural = 'Processing Batches'
        indexes = [
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['processing_date']),
            models.Index(fields=['source_flock']),
        ]
    
    def __str__(self):
        return f"{self.batch_number} - {self.birds_processed} birds ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-generate batch number
        if not self.batch_number:
            self.batch_number = self._generate_batch_number()
        
        # Auto-calculate bird cost from flock if not provided
        if self.bird_cost_per_unit is None and self.source_flock:
            self.bird_cost_per_unit = self.source_flock.purchase_price_per_bird or Decimal('0.00')
        
        # Auto-calculate expected yield weight if average weight is provided
        if self.average_bird_weight_kg and not self.expected_yield_weight_kg:
            self.expected_yield_weight_kg = self.average_bird_weight_kg * self.birds_processed
        
        super().save(*args, **kwargs)
    
    def _generate_batch_number(self):
        """Generate unique batch number: PROC-FARMID-YYYYMMDD-XXXX"""
        date_str = timezone.now().strftime('%Y%m%d')
        farm_code = str(self.farm.id)[:8].upper()
        
        # Get count of batches today for this farm
        today_count = ProcessingBatch.objects.filter(
            farm=self.farm,
            created_at__date=timezone.now().date()
        ).count()
        
        return f"PROC-{farm_code}-{date_str}-{today_count + 1:04d}"
    
    @property
    def total_cost(self):
        """Calculate total processing cost."""
        bird_total = (self.bird_cost_per_unit or Decimal('0.00')) * self.birds_processed
        return bird_total + self.labor_cost + self.processing_cost + self.packaging_cost
    
    @property
    def birds_successfully_processed(self):
        """Number of birds that successfully went through processing."""
        return self.birds_processed - self.birds_lost_in_processing
    
    @property
    def loss_rate_percent(self):
        """Percentage of birds lost during processing."""
        if self.birds_processed == 0:
            return 0
        return round((self.birds_lost_in_processing / self.birds_processed) * 100, 2)
    
    @property
    def yield_efficiency_percent(self):
        """
        Yield efficiency: actual weight vs expected weight.
        Example: 100 birds × 4kg = 400kg expected, 380kg actual = 95% efficiency
        """
        if self.expected_yield_weight_kg and self.actual_yield_weight_kg:
            return round((self.actual_yield_weight_kg / self.expected_yield_weight_kg) * 100, 2)
        return None
    
    @property
    def weight_per_bird_actual(self):
        """Actual yield weight per bird successfully processed."""
        if self.birds_successfully_processed > 0 and self.actual_yield_weight_kg:
            return round(self.actual_yield_weight_kg / self.birds_successfully_processed, 3)
        return None
    
    @property
    def total_output_quantity(self):
        """Total quantity of all outputs produced (if piece tracking is used)."""
        return sum(output.quantity or 0 for output in self.outputs.all())
    
    @property
    def total_output_weight_kg(self):
        """Total weight of all outputs in kg (primary measurement)."""
        return sum(
            output.weight_kg or Decimal('0')
            for output in self.outputs.all()
        )
    
    @property
    def yield_per_bird_kg(self):
        """Average weight yield per bird processed (in kg)."""
        if self.birds_successfully_processed == 0:
            return Decimal('0')
        return round(self.total_output_weight_kg / self.birds_successfully_processed, 3)
    
    def clean(self):
        """Validate processing batch data."""
        super().clean()
        
        # Validate source flock has enough birds
        if self.source_flock and hasattr(self.source_flock, 'current_count'):
            if self.birds_processed > self.source_flock.current_count:
                raise ValidationError({
                    'birds_processed': f'Cannot process {self.birds_processed} birds. '
                                      f'Flock only has {self.source_flock.current_count} birds.'
                })
        
        # Validate losses don't exceed processed
        if self.birds_lost_in_processing > self.birds_processed:
            raise ValidationError({
                'birds_lost_in_processing': 'Birds lost cannot exceed birds processed.'
            })
    
    @transaction.atomic
    def deduct_from_flock(self):
        """
        Deduct processed birds from source flock.
        Called when batch is created or started.
        """
        if not self.source_flock:
            raise ValidationError("No source flock specified")
        
        flock = self.source_flock
        
        if self.birds_processed > flock.current_count:
            raise ValidationError(
                f'Cannot process {self.birds_processed} birds. '
                f'Flock only has {flock.current_count} birds.'
            )
        
        # Deduct from flock
        flock.current_count -= self.birds_processed
        flock.save(update_fields=['current_count'])
        
        return True
    
    @transaction.atomic
    def complete_and_update_inventory(self, user=None):
        """
        Complete the processing batch and add outputs to inventory.
        
        WEIGHT-BASED TRACKING:
        - Processed products are tracked in KILOGRAMS (kg)
        - Flow: 100 birds → processing → 400 kg products → inventory (400 kg)
        - Sales: Customer buys 200 kg → inventory remaining: 200 kg
        
        This is the critical function that creates the link between 
        processed products and the inventory system.
        """
        from .inventory_models import FarmInventory, InventoryCategory, StockMovementType
        
        if self.status == ProcessingBatchStatus.COMPLETED:
            raise ValidationError("Batch is already completed")
        
        if not self.outputs.exists():
            raise ValidationError("Cannot complete batch without any outputs defined")
        
        # Update each output to inventory (using WEIGHT in kg)
        for output in self.outputs.all():
            # Get or create inventory for this product type (UNIT = kg)
            inventory, created = FarmInventory.objects.get_or_create(
                farm=self.farm,
                category=InventoryCategory.PROCESSED,
                product_name=output.get_product_category_display(),
                defaults={
                    'unit': 'kg',  # WEIGHT-BASED: Always kg for processed products
                    'quantity_available': Decimal('0'),
                    'unit_cost': output.cost_per_kg or Decimal('0'),
                }
            )
            
            # Add stock using weight in kg (not piece count)
            inventory.add_stock(
                quantity=output.weight_kg,  # WEIGHT in kg
                movement_type=StockMovementType.PROCESSING,
                source_record=self,
                unit_cost=output.cost_per_kg,  # Cost per kg
                notes=f'From processing batch {self.batch_number} ({output.get_product_category_display()}) - {output.weight_kg} kg',
                recorded_by=user or self.processed_by
            )
            
            # AUTO-CREATE Marketplace Product if not already linked
            if not output.marketplace_product:
                from .marketplace_models import Product as MarketplaceProduct, ProductCategory as MPCategory
                
                # Try to find or create appropriate category
                try:
                    mp_category, _ = MPCategory.objects.get_or_create(
                        slug='processed-poultry',
                        defaults={
                            'name': 'Processed Poultry',
                            'description': 'Processed poultry products from farm processing'
                        }
                    )
                except:
                    mp_category = MPCategory.objects.first()  # Fallback to first category
                
                if mp_category:
                    # Create marketplace product automatically with sensible defaults
                    marketplace_product = MarketplaceProduct.objects.create(
                        farm=self.farm,
                        category=mp_category,
                        name=f"{output.get_product_category_display()} (Grade {output.grade})",
                        description=f"Fresh {output.get_product_category_display().lower()} from batch {self.batch_number}",
                        unit='kg',
                        price=output.cost_per_kg * Decimal('1.3') if output.cost_per_kg else Decimal('50.00'),  # 30% markup or default
                        status='active',
                        track_inventory=True,
                    )
                    output.marketplace_product = marketplace_product
                    output.save(update_fields=['marketplace_product'])
            
            # Link inventory to marketplace product
            if output.marketplace_product and inventory.marketplace_product is None:
                inventory.marketplace_product = output.marketplace_product
                inventory.save(update_fields=['marketplace_product'])
            
            # Mark output as inventory-updated
            output.inventory_updated = True
            output.inventory_updated_at = timezone.now()
            output.save(update_fields=['inventory_updated', 'inventory_updated_at'])
        
        # Update actual yield weight on batch
        self.actual_yield_weight_kg = self.total_output_weight_kg
        
        # Mark batch as completed
        self.status = ProcessingBatchStatus.COMPLETED
        self.completed_at = timezone.now()
        self.inventory_updated = True
        self.save(update_fields=['status', 'completed_at', 'inventory_updated', 'actual_yield_weight_kg', 'updated_at'])
        
        return True
    
    @transaction.atomic
    def cancel(self, reason=None, restore_flock=True):
        """
        Cancel the processing batch, optionally restoring birds to flock.
        """
        if self.status == ProcessingBatchStatus.COMPLETED:
            raise ValidationError("Cannot cancel a completed batch")
        
        if restore_flock and self.source_flock:
            # Restore birds to flock
            flock = self.source_flock
            flock.current_count += self.birds_processed
            flock.save(update_fields=['current_count'])
        
        self.status = ProcessingBatchStatus.CANCELLED
        if reason:
            self.notes = f"{self.notes}\nCancellation reason: {reason}".strip()
        self.save(update_fields=['status', 'notes', 'updated_at'])
        
        return True


class ProcessingOutput(models.Model):
    """
    Products produced from a processing batch.
    
    WEIGHT-BASED TRACKING:
    - Processed products are measured in KILOGRAMS (kg), not pieces
    - Flow: 100 birds → processing → 400 kg products
    - Sales: Sold 200 kg → 200 kg remaining
    
    Each output represents a specific product type (drumsticks, wings, etc.)
    with its WEIGHT and cost allocation.
    
    These outputs are added to FarmInventory when the batch is completed,
    enabling full traceability from sale back to source flock.
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    processing_batch = models.ForeignKey(
        ProcessingBatch, 
        on_delete=models.CASCADE, 
        related_name='outputs'
    )
    
    # Product details
    product_category = models.CharField(
        max_length=20, 
        choices=ProductCategory.choices
    )
    
    # PRIMARY MEASUREMENT: Weight in kilograms
    weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('0.00'),  # Default for existing records (will be updated)
        help_text='Total weight of this product output in kilograms (PRIMARY UNIT)'
    )
    
    # Optional: piece count for reference (e.g., 50 drumsticks = 25 kg)
    quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Optional: Number of pieces/units (for reference only, not primary tracking)'
    )
    unit = models.CharField(
        max_length=20, 
        default='kg',
        help_text='Unit of measurement (kg is default for processed products)'
    )
    # Keep for backward compatibility, but weight_kg is now primary
    unit_weight_kg = models.DecimalField(
        max_digits=6, 
        decimal_places=3,
        null=True, 
        blank=True,
        help_text='Weight per piece in kg (if tracking pieces: weight_kg = quantity × unit_weight_kg)'
    )
    
    # Quality grading
    grade = models.CharField(
        max_length=1, 
        choices=ProductGrade.choices, 
        default=ProductGrade.A
    )
    
    # Expiry tracking for staleness detection
    production_date = models.DateField(
        default=timezone.localdate,
        help_text='Date when this output was produced'
    )
    expiry_date = models.DateField(
        null=True, 
        blank=True,
        help_text='Expiry date for perishable products'
    )
    shelf_life_days = models.PositiveIntegerField(
        default=7,
        help_text='Expected shelf life in days (used to calculate expiry if not set)'
    )
    
    # Link to marketplace product for sales
    marketplace_product = models.ForeignKey(
        'sales_revenue.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processing_outputs',
        help_text='Link to marketplace product for selling'
    )
    
    # Cost allocation from batch
    allocated_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text='Portion of batch cost allocated to this output'
    )
    cost_allocation_method = models.CharField(
        max_length=20,
        choices=[
            ('weight', 'By Weight'),
            ('quantity', 'By Quantity'),
            ('manual', 'Manual Entry'),
        ],
        default='quantity'
    )
    
    # Inventory tracking
    inventory_updated = models.BooleanField(
        default=False,
        help_text='Whether this output has been added to inventory'
    )
    inventory_updated_at = models.DateTimeField(
        null=True, 
        blank=True
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['product_category', '-created_at']
        verbose_name = 'Processing Output'
        verbose_name_plural = 'Processing Outputs'
    
    def __str__(self):
        return f"{self.get_product_category_display()} - {self.weight_kg} kg ({self.get_grade_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate expiry date from shelf life
        if self.expiry_date is None and self.production_date and self.shelf_life_days:
            from datetime import timedelta
            self.expiry_date = self.production_date + timedelta(days=self.shelf_life_days)
        
        # Auto-calculate weight from quantity × unit_weight if weight_kg not provided
        if not self.weight_kg and self.quantity and self.unit_weight_kg:
            self.weight_kg = Decimal(str(self.quantity)) * self.unit_weight_kg
        
        super().save(*args, **kwargs)
        
        # Update parent batch's actual yield weight
        self._update_batch_actual_yield()
    
    def _update_batch_actual_yield(self):
        """Update the parent batch's actual yield weight from all outputs."""
        if self.processing_batch:
            total_weight = ProcessingOutput.objects.filter(
                processing_batch=self.processing_batch
            ).aggregate(
                total=models.Sum('weight_kg')
            )['total'] or Decimal('0')
            
            ProcessingBatch.objects.filter(
                id=self.processing_batch_id
            ).update(actual_yield_weight_kg=total_weight)
    
    @property
    def total_weight_kg(self):
        """Total weight of this output in kg (for backward compatibility)."""
        # Now weight_kg is the primary field
        return self.weight_kg
    
    @property
    def cost_per_kg(self):
        """Cost per kilogram of output."""
        if self.allocated_cost and self.weight_kg and self.weight_kg > 0:
            return self.allocated_cost / self.weight_kg
        return None
    
    @property
    def cost_per_unit(self):
        """Cost per piece/unit of output (if quantity tracked)."""
        if self.allocated_cost and self.quantity and self.quantity > 0:
            return self.allocated_cost / self.quantity
        return None
    
    @property
    def days_until_expiry(self):
        """Days until this product expires."""
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None
    
    @property
    def is_expired(self):
        """Check if product is expired."""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
    @property
    def is_near_expiry(self, threshold_days=3):
        """Check if product is near expiry (default: 3 days)."""
        days = self.days_until_expiry
        if days is not None:
            return 0 < days <= threshold_days
        return False
    
    @property
    def age_days(self):
        """How many days since production."""
        if self.production_date:
            return (timezone.now().date() - self.production_date).days
        return 0
    
    def allocate_cost_by_weight(self):
        """
        Allocate cost from batch based on weight proportion.
        """
        batch = self.processing_batch
        total_weight = batch.total_output_weight_kg
        
        if total_weight and self.total_weight_kg:
            proportion = self.total_weight_kg / total_weight
            self.allocated_cost = batch.total_cost * Decimal(str(proportion))
            self.cost_allocation_method = 'weight'
            self.save(update_fields=['allocated_cost', 'cost_allocation_method'])
    
    def allocate_cost_by_quantity(self):
        """
        Allocate cost from batch based on quantity proportion.
        """
        batch = self.processing_batch
        total_quantity = batch.total_output_quantity
        
        if total_quantity > 0:
            proportion = self.quantity / total_quantity
            self.allocated_cost = batch.total_cost * Decimal(str(proportion))
            self.cost_allocation_method = 'quantity'
            self.save(update_fields=['allocated_cost', 'cost_allocation_method'])


class ProcessingAnalytics(models.Manager):
    """
    Manager for processing analytics and government visibility.
    
    Provides methods for:
    - Stale stock detection
    - Processing efficiency analysis
    - Cost/profitability analysis
    - Government intervention triggers
    """
    
    def get_queryset(self):
        return super().get_queryset()
    
    def stale_stock_report(self, days_threshold=7):
        """
        Get report of stale/old processed stock.
        
        Government can use this to identify farms with stock that's 
        been sitting too long, potentially indicating sales issues.
        """
        from django.db.models import F, ExpressionWrapper, IntegerField
        from datetime import timedelta
        
        threshold_date = timezone.now().date() - timedelta(days=days_threshold)
        
        stale_outputs = ProcessingOutput.objects.filter(
            inventory_updated=True,
            production_date__lte=threshold_date,
            processing_batch__status=ProcessingBatchStatus.COMPLETED
        ).select_related(
            'processing_batch__farm',
            'processing_batch__source_flock'
        ).annotate(
            age_in_days=ExpressionWrapper(
                timezone.now().date() - F('production_date'),
                output_field=IntegerField()
            )
        )
        
        return stale_outputs
    
    def farms_with_stale_stock(self, days_threshold=7):
        """
        Get farms that have stale processed stock.
        For government monitoring and intervention.
        """
        from django.db.models import Count
        from datetime import timedelta
        
        threshold_date = timezone.now().date() - timedelta(days=days_threshold)
        
        return ProcessingBatch.objects.filter(
            status=ProcessingBatchStatus.COMPLETED,
            outputs__production_date__lte=threshold_date,
            outputs__inventory_updated=True
        ).values(
            'farm__id',
            'farm__farm_name',
            'farm__primary_region',
            'farm__primary_constituency'
        ).annotate(
            stale_batch_count=Count('id', distinct=True),
            stale_output_count=Count('outputs')
        ).order_by('-stale_batch_count')
    
    def processing_efficiency_by_farm(self, farm=None):
        """
        Get processing efficiency metrics.
        """
        from django.db.models import Avg, Sum
        
        queryset = ProcessingBatch.objects.filter(
            status=ProcessingBatchStatus.COMPLETED
        )
        
        if farm:
            queryset = queryset.filter(farm=farm)
        
        return queryset.aggregate(
            total_batches=Count('id'),
            total_birds_processed=Sum('birds_processed'),
            total_birds_lost=Sum('birds_lost_in_processing'),
            avg_loss_rate=Avg('birds_lost_in_processing') / Avg('birds_processed') * 100,
            total_processing_cost=Sum('processing_cost') + Sum('labor_cost') + Sum('packaging_cost'),
        )
    
    def expiring_soon(self, days=3):
        """
        Get outputs expiring within specified days.
        For proactive sales or markdown alerts.
        """
        from datetime import timedelta
        
        expiry_window = timezone.now().date() + timedelta(days=days)
        
        return ProcessingOutput.objects.filter(
            expiry_date__lte=expiry_window,
            expiry_date__gte=timezone.now().date(),
            inventory_updated=True
        ).select_related('processing_batch__farm')


# Add analytics manager as a separate model proxy
class ProcessingOutputAnalytics(ProcessingOutput):
    """Proxy model for analytics queries."""
    
    analytics = ProcessingAnalytics()
    
    class Meta:
        proxy = True
