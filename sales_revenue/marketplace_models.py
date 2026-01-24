"""
Marketplace Models

Provides marketplace functionality for farmers to list and sell products.
Each farmer can only see and manage their own marketplace data (products, orders, customers).

Security Model:
- All models are linked to Farm via ForeignKey
- Views filter queryset by request.user.farm to ensure data isolation
- Farmers cannot see or modify other farmers' data
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class ProductCategory(models.Model):
    """
    Product categories for marketplace listings.
    System-wide categories managed by admins.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class name")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplace_product_categories'
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Marketplace product listing.
    
    SECURITY: Each product belongs to a farm. Farmers can only manage their own products.
    The view layer filters queryset by farm to prevent unauthorized access.
    """
    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('crate', 'Crate (30 eggs)'),
        ('tray', 'Tray'),
        ('kg', 'Kilogram'),
        ('bird', 'Bird'),
        ('dozen', 'Dozen'),
        ('bag', 'Bag'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('out_of_stock', 'Out of Stock'),
        ('discontinued', 'Discontinued'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # CRITICAL: Farm ownership - enforces data isolation
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='marketplace_products',
        help_text='The farm that owns this product listing'
    )
    
    # Product Information
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(
        max_length=50,
        blank=True,
        help_text='Stock Keeping Unit - unique per farm'
    )
    
    # Pricing
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Asking price (or fixed price if not negotiable)'
    )
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Original price for showing discounts'
    )
    
    # Negotiable Pricing
    price_negotiable = models.BooleanField(
        default=False,
        help_text='Allow customers to negotiate price'
    )
    min_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Minimum acceptable price (only visible to farmer)'
    )
    price_notes = models.CharField(
        max_length=200,
        blank=True,
        help_text='Public notes about pricing (e.g., "Bulk discounts available")'
    )
    
    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text='Alert when stock falls below this level'
    )
    track_inventory = models.BooleanField(default=True)
    allow_backorder = models.BooleanField(default=False)
    
    # Status and Visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    
    # Minimum Order
    min_order_quantity = models.PositiveIntegerField(default=1)
    max_order_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum quantity per order (blank for unlimited)'
    )
    
    # Images
    primary_image = models.ImageField(
        upload_to='marketplace/products/',
        blank=True,
        null=True
    )
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    
    # Statistics (updated on orders)
    total_sold = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    review_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'marketplace_products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['farm', '-created_at']),
            models.Index(fields=['status', 'is_featured']),
        ]
        # Ensure SKU is unique per farm
        constraints = [
            models.UniqueConstraint(
                fields=['farm', 'sku'],
                name='unique_sku_per_farm',
                condition=models.Q(sku__isnull=False) & ~models.Q(sku='')
            )
        ]
    
    def __str__(self):
        return f"{self.name} - {self.farm.farm_name}"
    
    @property
    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0
    
    @property
    def is_low_stock(self):
        if not self.track_inventory:
            return False
        return self.stock_quantity <= self.low_stock_threshold
    
    def reduce_stock(self, quantity, reference_record=None, unit_price=None, 
                     notes='', recorded_by=None):
        """
        Reduce stock when an order is placed.
        
        ACCOUNTABILITY: Routes through FarmInventory when linked to ensure
        full audit trail via StockMovement. If no inventory link exists,
        auto-creates one for accountability.
        
        Args:
            quantity: Amount to deduct
            reference_record: The order/sale record for audit trail
            unit_price: Sale price per unit (for revenue tracking)
            notes: Additional context for audit log
            recorded_by: User who initiated the action
        """
        if not self.track_inventory:
            return
        
        from decimal import Decimal
        quantity = Decimal(str(quantity))
        
        # Get or create linked FarmInventory for full accountability
        inventory = self._get_or_create_inventory()
        
        if inventory:
            # Route through FarmInventory for audit trail
            from sales_revenue.inventory_models import StockMovementType
            try:
                inventory.remove_stock(
                    quantity=quantity,
                    movement_type=StockMovementType.SALE,
                    reference_record=reference_record,
                    unit_price=unit_price or self.price,
                    notes=notes or f"Sale of {self.name}",
                    recorded_by=recorded_by
                )
                # FarmInventory.save() will sync back to Product via sync_marketplace_product()
            except ValueError as e:
                # Insufficient stock in inventory - update Product directly as fallback
                self._reduce_stock_direct(quantity)
        else:
            # Fallback: no inventory system, update Product directly
            self._reduce_stock_direct(quantity)
    
    def _reduce_stock_direct(self, quantity):
        """Direct stock reduction without audit trail (fallback only)."""
        from decimal import Decimal
        quantity = int(Decimal(str(quantity)))
        self.stock_quantity = max(0, self.stock_quantity - quantity)
        if self.stock_quantity == 0:
            self.status = 'out_of_stock'
        self.save(update_fields=['stock_quantity', 'status', 'updated_at'])
    
    def restore_stock(self, quantity, reference_record=None, notes='', recorded_by=None):
        """
        Restore stock when an order is cancelled.
        
        ACCOUNTABILITY: Routes through FarmInventory when linked to ensure
        full audit trail via StockMovement.
        
        Args:
            quantity: Amount to restore
            reference_record: The order/sale record for audit trail
            notes: Additional context for audit log
            recorded_by: User who initiated the action
        """
        if not self.track_inventory:
            return
        
        from decimal import Decimal
        quantity = Decimal(str(quantity))
        
        # Get linked FarmInventory for audit trail
        inventory = self._get_linked_inventory()
        
        if inventory:
            # Route through FarmInventory for audit trail
            from sales_revenue.inventory_models import StockMovementType
            inventory.add_stock(
                quantity=quantity,
                movement_type=StockMovementType.RETURN,
                source_record=reference_record,
                notes=notes or f"Stock restored for {self.name}",
                recorded_by=recorded_by
            )
            # FarmInventory.save() will sync back to Product via sync_marketplace_product()
        else:
            # Fallback: no inventory system, update Product directly
            self._restore_stock_direct(quantity)
    
    def _restore_stock_direct(self, quantity):
        """Direct stock restoration without audit trail (fallback only)."""
        from decimal import Decimal
        quantity = int(Decimal(str(quantity)))
        self.stock_quantity += quantity
        if self.status == 'out_of_stock' and self.stock_quantity > 0:
            self.status = 'active'
        self.save(update_fields=['stock_quantity', 'status', 'updated_at'])
    
    def _get_linked_inventory(self):
        """Get linked FarmInventory if exists."""
        if hasattr(self, 'inventory_record') and self.inventory_record:
            return self.inventory_record
        return None
    
    def _get_or_create_inventory(self):
        """
        Get or create FarmInventory record for this product.
        
        Ensures every marketplace product has an inventory record for
        complete accountability and audit trail.
        """
        from sales_revenue.inventory_models import FarmInventory, InventoryCategory
        
        # Check if already linked
        if hasattr(self, 'inventory_record') and self.inventory_record:
            return self.inventory_record
        
        # Determine inventory category based on product category
        category = self._determine_inventory_category()
        
        # Get or create inventory record
        inventory, created = FarmInventory.objects.get_or_create(
            farm=self.farm,
            marketplace_product=self,
            defaults={
                'category': category,
                'product_name': self.name,
                'sku': self.sku or '',
                'unit': self.unit,
                'quantity_available': self.stock_quantity,
                'unit_cost': self.price,
                'low_stock_threshold': self.low_stock_threshold,
            }
        )
        
        if created:
            # Log the auto-creation for transparency
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Auto-created FarmInventory for Product {self.id} ({self.name}) "
                f"on farm {self.farm_id} with initial stock {self.stock_quantity}"
            )
        
        return inventory
    
    def _determine_inventory_category(self):
        """Determine inventory category based on product attributes."""
        from sales_revenue.inventory_models import InventoryCategory
        
        name_lower = self.name.lower()
        category_name = self.category.name.lower() if self.category else ''
        
        # Check eggs first
        if 'egg' in name_lower or 'egg' in category_name:
            return InventoryCategory.EGGS
        # Check processed BEFORE chicks (because "chicken" contains "chick")
        elif any(word in name_lower for word in ['processed', 'dressed', 'meat', 'frozen', 'chicken']):
            return InventoryCategory.PROCESSED
        # Check chicks (day-old chicks)
        elif 'chick' in name_lower or 'doc' in name_lower:
            return InventoryCategory.CHICKS
        else:
            return InventoryCategory.BIRDS  # Default for live birds
    
    # ==========================================
    # PROCESSING BATCH TRACEABILITY
    # ==========================================
    
    @property
    def source_batches(self):
        """
        Get all processing batches that contributed stock to this product.
        
        Returns QuerySet of ProcessingBatch objects linked via:
        1. ProcessingOutput.marketplace_product (direct link)
        2. FarmInventory.marketplace_product → StockMovement → ProcessingBatch (indirect)
        """
        from sales_revenue.processing_models import ProcessingBatch
        
        # Get batches from direct ProcessingOutput links
        batch_ids = set(
            self.processing_outputs.values_list('processing_batch_id', flat=True)
        )
        
        # Get batches from inventory stock movements
        if hasattr(self, 'inventory_record') and self.inventory_record:
            from sales_revenue.inventory_models import StockMovement, StockMovementType
            movements = StockMovement.objects.filter(
                inventory=self.inventory_record,
                movement_type=StockMovementType.PROCESSING,
                source_type='processing_batch'
            ).values_list('source_id', flat=True)
            
            for source_id in movements:
                if source_id:
                    batch_ids.add(source_id)
        
        return ProcessingBatch.objects.filter(id__in=batch_ids).order_by('-processing_date')
    
    @property
    def has_processing_source(self):
        """Check if this product has any linked processing batches."""
        return self.processing_outputs.exists() or (
            hasattr(self, 'inventory_record') and 
            self.inventory_record and
            self.inventory_record.category == 'processed'
        )
    
    @property
    def source_flocks(self):
        """Get all source flocks that contributed to this product."""
        from flock_management.models import Flock
        flock_ids = set()
        
        for batch in self.source_batches:
            if batch.source_flock_id:
                flock_ids.add(batch.source_flock_id)
        
        return Flock.objects.filter(id__in=flock_ids)
    
    def get_batch_summary(self):
        """
        Get summary of all processing batches for this product.
        
        Returns list of dicts with batch info for frontend display.
        """
        summary = []
        for batch in self.source_batches:
            # Find the output for this product in this batch
            output = batch.outputs.filter(marketplace_product=self).first()
            
            summary.append({
                'batch_id': str(batch.id),
                'batch_number': batch.batch_number,
                'processing_date': batch.processing_date.isoformat() if batch.processing_date else None,
                'birds_processed': batch.birds_processed,
                'weight_from_batch_kg': str(output.weight_kg) if output else None,
                'source_flock': {
                    'id': str(batch.source_flock.id) if batch.source_flock else None,
                    'name': batch.source_flock.name if batch.source_flock else None,
                    'breed': batch.source_flock.breed if batch.source_flock else None,
                } if batch.source_flock else None,
                'status': batch.status,
                'expiry_dates': list(batch.outputs.filter(
                    marketplace_product=self
                ).values_list('expiry_date', flat=True))
            })
        
        return summary


class ProductImage(models.Model):
    """Additional product images."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='marketplace/products/')
    alt_text = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'marketplace_product_images'
        ordering = ['display_order']


class MarketplaceOrder(models.Model):
    """
    Customer orders from the marketplace.
    
    SECURITY: Each order belongs to a farm. Farmers can only view their own orders.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('ready', 'Ready for Pickup/Delivery'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('pickup', 'Farm Pickup'),
        ('farmer_delivery', 'Farmer Delivers'),
        ('third_party', 'Third-Party Delivery'),
    ]
    
    THIRD_PARTY_PROVIDER_CHOICES = [
        ('bolt', 'Bolt'),
        ('uber', 'Uber'),
        ('glovo', 'Glovo'),
        ('yango', 'Yango'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # CRITICAL: Farm ownership - enforces data isolation
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='marketplace_orders',
        help_text='The farm that receives this order'
    )
    
    # Customer Information (linked to Customer model)
    customer = models.ForeignKey(
        'sales_revenue.Customer',
        on_delete=models.PROTECT,
        related_name='marketplace_orders'
    )
    
    # Order Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    
    # Negotiated Price (if different from listed price)
    negotiated_price_applied = models.BooleanField(
        default=False,
        help_text='Whether a negotiated price was agreed upon'
    )
    negotiation_notes = models.TextField(
        blank=True,
        help_text='Notes about price negotiation'
    )
    
    # Totals
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Delivery Options
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        default='pickup'
    )
    
    # Farm Pickup Details
    pickup_date = models.DateField(null=True, blank=True)
    pickup_time_slot = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g., "9:00 AM - 12:00 PM"'
    )
    
    # Farmer Delivery Details
    farmer_delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Fee charged by farmer for delivery'
    )
    farmer_delivery_radius_km = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum delivery distance in kilometers'
    )
    
    # Third-Party Delivery Details
    third_party_provider = models.CharField(
        max_length=20,
        choices=THIRD_PARTY_PROVIDER_CHOICES,
        blank=True
    )
    third_party_tracking_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Tracking ID from delivery provider'
    )
    third_party_delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Common Delivery Fields
    delivery_address = models.TextField(blank=True)
    delivery_gps_coordinates = models.CharField(
        max_length=50,
        blank=True,
        help_text='GPS coordinates (lat,lng)'
    )
    delivery_contact_name = models.CharField(max_length=200, blank=True)
    delivery_contact_phone = models.CharField(max_length=20, blank=True)
    delivery_notes = models.TextField(blank=True)
    estimated_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    
    # Notes
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True, help_text='Internal notes (not visible to customer)')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'marketplace_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', '-created_at']),
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.customer}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)
    
    def _generate_order_number(self):
        """Generate unique order number: ORD-YYYYMMDD-XXXXX"""
        from django.utils.crypto import get_random_string
        date_part = timezone.now().strftime('%Y%m%d')
        random_part = get_random_string(5, allowed_chars='0123456789').upper()
        return f"ORD-{date_part}-{random_part}"
    
    def calculate_totals(self):
        """Recalculate order totals from line items."""
        self.subtotal = sum(item.line_total for item in self.items.all())
        self.total_amount = self.subtotal - self.discount_amount + self.delivery_fee
        self.save(update_fields=['subtotal', 'total_amount', 'updated_at'])


class OrderItem(models.Model):
    """Line items for marketplace orders."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        MarketplaceOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    
    # Snapshot of product at time of order
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Status
    fulfilled_quantity = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'marketplace_order_items'
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Calculate line total
        self.line_total = self.unit_price * self.quantity
        
        # Snapshot product details if not set
        if not self.product_name:
            self.product_name = self.product.name
            self.product_sku = self.product.sku or ''
            self.unit = self.product.unit
            self.unit_price = self.product.price
        
        super().save(*args, **kwargs)


class MarketplaceStatistics(models.Model):
    """
    Daily aggregated marketplace statistics per farm.
    
    SECURITY: Each record belongs to a farm.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='marketplace_statistics'
    )
    date = models.DateField()
    
    # Sales metrics
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    cancelled_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_items_sold = models.PositiveIntegerField(default=0)
    
    # Customer metrics
    new_customers = models.PositiveIntegerField(default=0)
    returning_customers = models.PositiveIntegerField(default=0)
    
    # Product metrics
    products_listed = models.PositiveIntegerField(default=0)
    products_out_of_stock = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplace_statistics'
        unique_together = ['farm', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['farm', '-date']),
        ]
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.date}"
