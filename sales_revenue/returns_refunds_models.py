"""
Returns and Refunds Models

Handles product returns and refund processing for marketplace orders.

Business Logic:
1. Customer initiates return request
2. Farmer reviews and approves/rejects
3. If approved, stock is restored to inventory
4. Refund is processed (if applicable)
5. Revenue and profit metrics are adjusted
6. Analytics reflect the return impact

Affected Features:
- Inventory: Stock levels increase when return is accepted
- Revenue: Total revenue decreases by refund amount
- Order: Order status and payment status update
- Product: total_sold and total_revenue adjust
- Statistics: Metrics recalculate to exclude returned items
- Customer: Purchase history reflects returns
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class ReturnReason(models.TextChoices):
    """Standardized return reasons"""
    DEFECTIVE = 'defective', 'Defective/Damaged Product'
    WRONG_ITEM = 'wrong_item', 'Wrong Item Delivered'
    NOT_AS_DESCRIBED = 'not_as_described', 'Not As Described'
    QUALITY_ISSUE = 'quality_issue', 'Quality Issue'
    EXPIRED = 'expired', 'Expired/Near Expiry'
    CHANGED_MIND = 'changed_mind', 'Changed Mind'
    DUPLICATE = 'duplicate', 'Duplicate Order'
    OTHER = 'other', 'Other'


class ReturnRequest(models.Model):
    """
    Customer request to return ordered items.
    
    SECURITY: Farm-scoped through order relationship
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('items_received', 'Items Received'),
        ('refund_issued', 'Refund Issued'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    REFUND_METHOD_CHOICES = [
        ('original_payment', 'Original Payment Method'),
        ('store_credit', 'Store Credit'),
        ('exchange', 'Exchange for Another Product'),
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Relationships
    order = models.ForeignKey(
        'sales_revenue.MarketplaceOrder',
        on_delete=models.CASCADE,
        related_name='return_requests'
    )
    customer = models.ForeignKey(
        'sales_revenue.Customer',
        on_delete=models.PROTECT,
        related_name='return_requests'
    )
    
    # Request Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.CharField(max_length=30, choices=ReturnReason.choices)
    detailed_reason = models.TextField(
        help_text='Detailed explanation from customer'
    )
    
    # Return Items (via ReturnItem model)
    total_items = models.PositiveIntegerField(default=0)
    total_refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Total amount to be refunded'
    )
    
    # Refund Method
    refund_method = models.CharField(
        max_length=30,
        choices=REFUND_METHOD_CHOICES,
        default='original_payment'
    )
    
    # Processing
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_returns'
    )
    review_notes = models.TextField(
        blank=True,
        help_text='Farmer notes about the return decision'
    )
    
    # Return Logistics
    items_received_at = models.DateTimeField(null=True, blank=True)
    items_condition = models.TextField(
        blank=True,
        help_text='Condition of returned items upon receipt'
    )
    
    # Refund Processing
    refund_issued_at = models.DateTimeField(null=True, blank=True)
    refund_transaction_id = models.CharField(max_length=100, blank=True)
    refund_notes = models.TextField(blank=True)
    
    # Quality Assessment
    return_quality_acceptable = models.BooleanField(
        null=True,
        blank=True,
        help_text='Whether returned items can be restocked'
    )
    restocking_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Fee deducted from refund for restocking'
    )
    
    # Images
    customer_images = models.JSONField(
        default=list,
        blank=True,
        help_text='URLs of images uploaded by customer'
    )
    farmer_images = models.JSONField(
        default=list,
        blank=True,
        help_text='URLs of images taken by farmer upon receipt'
    )
    
    # Timestamps
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'return_requests'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['order', '-requested_at']),
            models.Index(fields=['customer', '-requested_at']),
            models.Index(fields=['status', '-requested_at']),
            models.Index(fields=['return_number']),
        ]
    
    def __str__(self):
        return f"Return {self.return_number} - Order {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = self._generate_return_number()
        super().save(*args, **kwargs)
    
    def _generate_return_number(self):
        """Generate unique return number: RET-YYYYMMDD-XXXXX"""
        from django.utils.crypto import get_random_string
        date_part = timezone.now().strftime('%Y%m%d')
        random_part = get_random_string(5, allowed_chars='0123456789').upper()
        return f"RET-{date_part}-{random_part}"
    
    def calculate_refund_amount(self):
        """Calculate total refund from return items minus restocking fee"""
        items_total = sum(
            item.refund_amount for item in self.return_items.all()
        )
        self.total_refund_amount = items_total - self.restocking_fee
        return self.total_refund_amount
    
    def approve_return(self, reviewed_by, notes=''):
        """Approve return request"""
        self.status = 'approved'
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
    
    def reject_return(self, reviewed_by, notes=''):
        """Reject return request"""
        self.status = 'rejected'
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
    
    def mark_items_received(self, quality_acceptable=True, condition_notes=''):
        """Mark return items as received by farmer"""
        self.status = 'items_received'
        self.items_received_at = timezone.now()
        self.items_condition = condition_notes
        self.return_quality_acceptable = quality_acceptable
        self.save()
        
        # If quality acceptable, restore stock
        if quality_acceptable:
            self._restore_inventory()
    
    def issue_refund(self, transaction_id='', notes=''):
        """Mark refund as issued"""
        self.status = 'refund_issued'
        self.refund_issued_at = timezone.now()
        self.refund_transaction_id = transaction_id
        self.refund_notes = notes
        self.save()
        
        # Update order payment status
        self.order.payment_status = 'refunded'
        self.order.save()
    
    def complete_return(self):
        """Mark return as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Adjust revenue metrics
        self._adjust_revenue_metrics()
    
    def _restore_inventory(self):
        """Restore returned items to inventory"""
        for return_item in self.return_items.all():
            return_item.restore_to_inventory()
    
    def _adjust_revenue_metrics(self):
        """Adjust product and farm revenue statistics"""
        from django.db.models import F
        
        # Adjust product metrics
        for return_item in self.return_items.all():
            product = return_item.product
            if product:
                product.total_sold = F('total_sold') - return_item.quantity
                product.total_revenue = F('total_revenue') - return_item.refund_amount
                product.save(update_fields=['total_sold', 'total_revenue'])
                product.refresh_from_db()
        
        # Inventory metrics are already adjusted via _restore_inventory


class ReturnItem(models.Model):
    """
    Individual line item in a return request.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    return_request = models.ForeignKey(
        ReturnRequest,
        on_delete=models.CASCADE,
        related_name='return_items'
    )
    order_item = models.ForeignKey(
        'sales_revenue.OrderItem',
        on_delete=models.PROTECT,
        related_name='return_items'
    )
    product = models.ForeignKey(
        'sales_revenue.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_items'
    )
    
    # Item Details (snapshot from order)
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Return Quantity
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Quantity being returned'
    )
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Amount to refund for this item'
    )
    
    # Item-specific reason
    item_reason = models.CharField(
        max_length=30,
        choices=ReturnReason.choices,
        blank=True,
        help_text='Reason specific to this item (optional)'
    )
    item_notes = models.TextField(blank=True)
    
    # Quality on return
    returned_in_good_condition = models.BooleanField(
        null=True,
        blank=True,
        help_text='Whether this item was returned in saleable condition'
    )
    
    # Stock restoration tracking
    stock_restored = models.BooleanField(
        default=False,
        help_text='Whether this item has been added back to inventory'
    )
    stock_restored_at = models.DateTimeField(null=True, blank=True)
    stock_movement_id = models.UUIDField(
        null=True,
        blank=True,
        help_text='Reference to StockMovement record'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'return_items'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity} - {self.return_request.return_number}"
    
    def save(self, *args, **kwargs):
        # Calculate refund amount if not set
        if not self.refund_amount:
            self.refund_amount = self.unit_price * self.quantity
        
        # Snapshot from order item if not set
        if self.order_item and not self.product_name:
            self.product_name = self.order_item.product_name
            self.product_sku = self.order_item.product_sku
            self.unit = self.order_item.unit
            self.unit_price = self.order_item.unit_price
        
        super().save(*args, **kwargs)
    
    def restore_to_inventory(self):
        """Add returned items back to inventory"""
        if self.stock_restored:
            return  # Already restored
        
        if not self.returned_in_good_condition:
            return  # Cannot restock damaged items
        
        # Add to FarmInventory
        from sales_revenue.inventory_models import FarmInventory, StockMovementType
        
        farm = self.return_request.order.farm
        
        # Find or create inventory record
        inventory, created = FarmInventory.objects.get_or_create(
            farm=farm,
            category=self.product.category.name if self.product and self.product.category else 'Products',
            product_name=self.product_name,
            defaults={
                'unit': self.unit,
                'unit_cost': self.unit_price,
            }
        )
        
        # Add stock back
        movement = inventory.add_stock(
            quantity=float(self.quantity),
            movement_type=StockMovementType.RETURN,
            source_record=self.return_request,
            unit_cost=float(self.unit_price),
            notes=f"Returned from order {self.return_request.order.order_number}",
            recorded_by=self.return_request.reviewed_by
        )
        
        # Mark as restored
        self.stock_restored = True
        self.stock_restored_at = timezone.now()
        if movement:
            self.stock_movement_id = movement.id
        self.save(update_fields=['stock_restored', 'stock_restored_at', 'stock_movement_id'])
        
        # Update product stock if linked
        if self.product:
            self.product.stock_quantity += self.quantity
            self.product.save(update_fields=['stock_quantity'])


class RefundTransaction(models.Model):
    """
    Tracks refund payment transactions.
    """
    REFUND_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    return_request = models.ForeignKey(
        ReturnRequest,
        on_delete=models.PROTECT,
        related_name='refund_transactions'
    )
    
    # Transaction Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    refund_method = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='pending')
    
    # External Reference
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_provider = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g., Paystack, MTN MoMo, Cash'
    )
    
    # Processing
    processed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'refund_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['return_request', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Refund GHS {self.amount} - {self.return_request.return_number}"
    
    def mark_completed(self, transaction_id='', processed_by=None):
        """Mark refund as completed"""
        self.status = 'completed'
        self.transaction_id = transaction_id
        self.processed_by = processed_by
        self.processed_at = timezone.now()
        self.save()
    
    def mark_failed(self, reason=''):
        """Mark refund as failed"""
        self.status = 'failed'
        self.failure_reason = reason
        self.save()
