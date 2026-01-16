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

ATOMICITY & IDEMPOTENCY:
- All mutating operations use @transaction.atomic
- Critical operations use select_for_update() to prevent race conditions
- State machine validation ensures valid status transitions
- Audit logging provides full traceability
- Idempotency checks prevent duplicate refunds and stock restorations
"""

from django.db import models, transaction
from django.db.models import F
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import logging

logger = logging.getLogger(__name__)


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
    
    @transaction.atomic
    def approve_return(self, approved_by=None, reviewed_by=None, notes='', admin_notes=''):
        """
        Approve return request.
        
        Atomicity: Uses select_for_update to prevent concurrent modifications
        State Validation: Validates pending -> approved transition
        """
        from .returns_safety import (
            validate_return_status_transition, ReturnLock, ReturnStatusTransitionError
        )
        
        # Lock the return request
        locked_self = ReturnRequest.objects.select_for_update().get(pk=self.pk)
        
        # Validate state transition
        validate_return_status_transition(locked_self.status, 'approved')
        
        previous_status = locked_self.status
        locked_self.status = 'approved'
        locked_self.reviewed_by = approved_by or reviewed_by
        locked_self.reviewed_at = timezone.now()
        locked_self.review_notes = notes or admin_notes
        locked_self.save()
        
        # Update self with new values
        self.status = locked_self.status
        self.reviewed_by = locked_self.reviewed_by
        self.reviewed_at = locked_self.reviewed_at
        self.review_notes = locked_self.review_notes
        
        # Audit log
        ReturnAuditLog.log(
            operation='approve_return',
            return_request=self,
            user=approved_by or reviewed_by,
            previous_state={'status': previous_status},
            new_state={'status': 'approved'},
        )
        
        logger.info(f"Return {self.return_number} approved by {approved_by or reviewed_by}")
    
    @transaction.atomic
    def reject_return(self, rejected_by=None, reviewed_by=None, reason='', notes='', admin_notes=''):
        """
        Reject return request.
        
        Atomicity: Uses select_for_update to prevent concurrent modifications
        State Validation: Validates pending -> rejected transition
        """
        from .returns_safety import validate_return_status_transition
        
        # Lock the return request
        locked_self = ReturnRequest.objects.select_for_update().get(pk=self.pk)
        
        # Validate state transition
        validate_return_status_transition(locked_self.status, 'rejected')
        
        previous_status = locked_self.status
        locked_self.status = 'rejected'
        locked_self.reviewed_by = rejected_by or reviewed_by
        locked_self.reviewed_at = timezone.now()
        locked_self.review_notes = reason or notes or admin_notes
        locked_self.save()
        
        # Update self with new values
        self.status = locked_self.status
        self.reviewed_by = locked_self.reviewed_by
        self.reviewed_at = locked_self.reviewed_at
        self.review_notes = locked_self.review_notes
        
        # Audit log
        ReturnAuditLog.log(
            operation='reject_return',
            return_request=self,
            user=rejected_by or reviewed_by,
            previous_state={'status': previous_status},
            new_state={'status': 'rejected', 'reason': reason or notes or admin_notes},
        )
        
        logger.info(f"Return {self.return_number} rejected by {rejected_by or reviewed_by}")
    
    @transaction.atomic
    def mark_items_received(self, items_conditions=None, quality_acceptable=True, 
                           condition_notes='', admin_notes='', received_by=None):
        """
        Mark return items as received by farmer.
        
        Atomicity: Uses select_for_update and distributed lock
        State Validation: Validates approved -> items_received transition
        
        Args:
            items_conditions: List of dicts with item conditions
                [{'id': uuid, 'condition_on_arrival': 'good'|'damaged', 'quality_notes': '...'}]
            quality_acceptable: Overall quality assessment (legacy parameter)
            condition_notes: Notes about items condition (legacy parameter)
            admin_notes: Admin notes about receipt
            received_by: User who received the items
        """
        from .returns_safety import validate_return_status_transition, ReturnLock
        
        # Use distributed lock to prevent concurrent item processing
        with ReturnLock(f"return:{self.id}:receive", ttl_seconds=60):
            # Lock the return request
            locked_self = ReturnRequest.objects.select_for_update().get(pk=self.pk)
            
            # Validate state transition
            validate_return_status_transition(locked_self.status, 'items_received')
            
            previous_status = locked_self.status
            locked_self.status = 'items_received'
            locked_self.items_received_at = timezone.now()
            locked_self.items_condition = condition_notes or admin_notes
            
            items_processed = []
            
            # Process individual item conditions
            if items_conditions:
                all_good = True
                for item_data in items_conditions:
                    item_id = item_data.get('id')
                    condition = item_data.get('condition_on_arrival', 'good')
                    quality_notes = item_data.get('quality_notes', '')
                    
                    try:
                        # Lock each return item
                        return_item = ReturnItem.objects.select_for_update().get(
                            id=item_id, return_request=locked_self
                        )
                        return_item.returned_in_good_condition = (condition == 'good')
                        return_item.item_notes = quality_notes
                        return_item.save(update_fields=['returned_in_good_condition', 'item_notes'])
                        
                        items_processed.append({
                            'id': str(item_id),
                            'condition': condition,
                            'good': condition == 'good'
                        })
                        
                        if condition != 'good':
                            all_good = False
                    except ReturnItem.DoesNotExist:
                        logger.warning(f"ReturnItem {item_id} not found for return {self.return_number}")
                
                locked_self.return_quality_acceptable = all_good
            else:
                locked_self.return_quality_acceptable = quality_acceptable
            
            locked_self.save()
            
            # Update self with new values
            self.status = locked_self.status
            self.items_received_at = locked_self.items_received_at
            self.items_condition = locked_self.items_condition
            self.return_quality_acceptable = locked_self.return_quality_acceptable
            
            # Audit log
            ReturnAuditLog.log(
                operation='mark_items_received',
                return_request=self,
                user=received_by,
                previous_state={'status': previous_status},
                new_state={
                    'status': 'items_received',
                    'quality_acceptable': locked_self.return_quality_acceptable,
                    'items_processed': len(items_processed)
                },
            )
            
            # Restore stock for items in good condition
            self._restore_inventory()
        
        logger.info(f"Return {self.return_number} items received, {len(items_processed)} items processed")
    
    @transaction.atomic
    def issue_refund(self, initiated_by=None, processed_by=None, payment_method='', 
                      refund_method='', payment_provider='', transaction_id='', notes=''):
        """
        Issue refund and create RefundTransaction record.
        
        Atomicity: Uses select_for_update and distributed lock
        State Validation: Validates items_received -> refund_issued transition
        Idempotency: Checks for existing refund transaction before creating
        
        Args:
            initiated_by/processed_by: User issuing the refund
            payment_method/refund_method: Method of refund (mobile_money, cash, etc.)
            payment_provider: e.g., MTN MoMo, Paystack
            transaction_id: External reference if any
            notes: Additional notes
            
        Returns:
            RefundTransaction instance
        """
        from .returns_safety import (
            validate_return_status_transition, ReturnLock,
            check_refund_idempotency, mark_refund_issued
        )
        
        user = initiated_by or processed_by
        
        # Use distributed lock to prevent duplicate refunds
        with ReturnLock(f"return:{self.id}:refund", ttl_seconds=60):
            # Check idempotency - has refund already been issued?
            existing_refund = check_refund_idempotency(str(self.id))
            if existing_refund:
                logger.warning(f"Duplicate refund attempt for return {self.return_number}")
                # Return existing refund transaction
                try:
                    return RefundTransaction.objects.get(
                        id=existing_refund['refund_transaction_id']
                    )
                except RefundTransaction.DoesNotExist:
                    pass  # Proceed with new refund if cache entry is stale
            
            # Lock the return request
            locked_self = ReturnRequest.objects.select_for_update().get(pk=self.pk)
            
            # Check if refund already exists in database
            if locked_self.status == 'refund_issued':
                existing = locked_self.refund_transactions.filter(status='completed').first()
                if existing:
                    logger.info(f"Refund already issued for return {self.return_number}")
                    return existing
            
            # Validate state transition
            validate_return_status_transition(locked_self.status, 'refund_issued')
            
            previous_status = locked_self.status
            refund_amount = locked_self.total_refund_amount or locked_self.calculate_refund_amount()
            
            # Create refund transaction
            refund_transaction = RefundTransaction.objects.create(
                return_request=locked_self,
                amount=refund_amount,
                refund_method=payment_method or refund_method or 'mobile_money',
                status='completed',
                transaction_id=transaction_id,
                payment_provider=payment_provider,
                processed_by=user,
                processed_at=timezone.now(),
                notes=notes
            )
            
            # Update return request status
            locked_self.status = 'refund_issued'
            locked_self.refund_issued_at = timezone.now()
            locked_self.refund_transaction_id = transaction_id
            locked_self.refund_notes = notes
            locked_self.save()
            
            # Update order payment status atomically
            from .marketplace_models import MarketplaceOrder
            MarketplaceOrder.objects.filter(pk=locked_self.order_id).update(
                payment_status='refunded',
                updated_at=timezone.now()
            )
            
            # Update self with new values
            self.status = locked_self.status
            self.refund_issued_at = locked_self.refund_issued_at
            self.refund_transaction_id = locked_self.refund_transaction_id
            self.refund_notes = locked_self.refund_notes
            
            # Mark in cache for idempotency
            mark_refund_issued(
                str(self.id), 
                str(refund_transaction.id), 
                str(refund_amount)
            )
            
            # Audit log
            ReturnAuditLog.log(
                operation='issue_refund',
                return_request=self,
                user=user,
                previous_state={'status': previous_status},
                new_state={
                    'status': 'refund_issued',
                    'refund_transaction_id': str(refund_transaction.id),
                    'amount': str(refund_amount),
                    'payment_method': payment_method or refund_method,
                },
            )
        
        logger.info(f"Refund {refund_transaction.id} issued for return {self.return_number}: GHS {refund_amount}")
        return refund_transaction
    
    @transaction.atomic
    def complete_return(self, completed_by=None):
        """
        Mark return as completed.
        
        Atomicity: Uses select_for_update to prevent concurrent modifications
        State Validation: Validates refund_issued -> completed transition
        """
        from .returns_safety import validate_return_status_transition
        
        # Lock the return request
        locked_self = ReturnRequest.objects.select_for_update().get(pk=self.pk)
        
        # Validate state transition
        validate_return_status_transition(locked_self.status, 'completed')
        
        previous_status = locked_self.status
        locked_self.status = 'completed'
        locked_self.completed_at = timezone.now()
        locked_self.save()
        
        # Update self with new values
        self.status = locked_self.status
        self.completed_at = locked_self.completed_at
        
        # Adjust revenue metrics
        self._adjust_revenue_metrics()
        
        # Audit log
        ReturnAuditLog.log(
            operation='complete_return',
            return_request=self,
            user=completed_by,
            previous_state={'status': previous_status},
            new_state={'status': 'completed'},
        )
        
        logger.info(f"Return {self.return_number} completed")
    
    def _restore_inventory(self):
        """
        Restore returned items to inventory.
        
        Called within transaction from mark_items_received().
        Each item's restore_to_inventory() handles its own idempotency check.
        """
        restored_count = 0
        for return_item in self.return_items.all():
            if return_item.restore_to_inventory():
                restored_count += 1
        
        logger.info(f"Restored {restored_count} items to inventory for return {self.return_number}")
        return restored_count
    
    @transaction.atomic
    def _adjust_revenue_metrics(self):
        """
        Adjust product and farm revenue statistics.
        
        Uses F() expressions for atomic updates.
        """
        from .marketplace_models import Product
        
        adjusted_products = []
        
        # Adjust product metrics atomically
        for return_item in self.return_items.select_related('product').all():
            if return_item.product_id:
                Product.objects.filter(pk=return_item.product_id).update(
                    total_sold=F('total_sold') - return_item.quantity,
                    total_revenue=F('total_revenue') - return_item.refund_amount
                )
                adjusted_products.append({
                    'product_id': str(return_item.product_id),
                    'quantity_adjusted': return_item.quantity,
                    'revenue_adjusted': str(return_item.refund_amount)
                })
        
        logger.info(f"Adjusted revenue metrics for {len(adjusted_products)} products from return {self.return_number}")


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
        # Validate return quantity doesn't exceed ordered quantity
        if self.order_item:
            ordered_qty = self.order_item.quantity
            # Calculate already returned quantity (excluding this item if updating)
            existing_returns = ReturnItem.objects.filter(
                order_item=self.order_item
            ).exclude(pk=self.pk).aggregate(
                total_returned=models.Sum('quantity')
            )['total_returned'] or 0
            
            max_returnable = ordered_qty - existing_returns
            if self.quantity > max_returnable:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"Cannot return {self.quantity} items. Maximum returnable: {max_returnable} "
                    f"(ordered: {ordered_qty}, already returned: {existing_returns})"
                )
        
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
        """
        Add returned items back to inventory.
        
        Idempotency: Checks stock_restored flag and uses cache lock
        Atomicity: Uses transaction.atomic and select_for_update
        
        Returns:
            bool: True if stock was restored, False if skipped
        """
        from .returns_safety import (
            check_stock_restoration_idempotency,
            mark_stock_restored,
            ReturnLock
        )
        
        # Quick check - already restored?
        if self.stock_restored:
            logger.debug(f"ReturnItem {self.id}: Stock already restored, skipping")
            return False
        
        # Cannot restock damaged items
        if not self.returned_in_good_condition:
            logger.info(f"ReturnItem {self.id}: Not in good condition, skipping inventory restoration")
            return False
        
        # Idempotency check via cache
        if check_stock_restoration_idempotency(str(self.id)):
            logger.warning(f"ReturnItem {self.id}: Stock restoration already processed (idempotency check)")
            return False
        
        # Acquire distributed lock
        with ReturnLock(f"return_item:{self.id}:restore"):
            # Double-check within lock (another process might have just completed)
            self.refresh_from_db()
            if self.stock_restored:
                return False
            
            with transaction.atomic():
                # Lock this return item row
                locked_item = ReturnItem.objects.select_for_update().get(pk=self.pk)
                
                if locked_item.stock_restored:
                    return False
                
                # Add to FarmInventory
                from sales_revenue.inventory_models import FarmInventory, StockMovementType
                
                farm = self.return_request.order.farm
                
                # Find or create inventory record with lock
                inventory, created = FarmInventory.objects.select_for_update().get_or_create(
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
                locked_item.stock_restored = True
                locked_item.stock_restored_at = timezone.now()
                if movement:
                    locked_item.stock_movement_id = movement.id
                locked_item.save(update_fields=['stock_restored', 'stock_restored_at', 'stock_movement_id'])
                
                # Update self
                self.stock_restored = True
                self.stock_restored_at = locked_item.stock_restored_at
                self.stock_movement_id = locked_item.stock_movement_id
                
                # Update product stock if linked
                if self.product:
                    from .marketplace_models import Product
                    Product.objects.filter(pk=self.product_id).update(
                        stock_quantity=F('stock_quantity') + self.quantity
                    )
                
                # Mark in cache for idempotency
                mark_stock_restored(str(self.id))
                
                logger.info(
                    f"ReturnItem {self.id}: Restored {self.quantity} units of {self.product_name} "
                    f"to inventory (movement: {movement.id if movement else 'N/A'})"
                )
                
                return True


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
    
    @transaction.atomic
    def mark_completed(self, transaction_id='', processed_by=None):
        """
        Mark refund as completed.
        
        Atomicity: Uses select_for_update to prevent concurrent modifications
        State Validation: Validates pending/processing -> completed transition
        """
        from .returns_safety import validate_refund_status_transition
        
        # Lock the refund transaction
        locked_self = RefundTransaction.objects.select_for_update().get(pk=self.pk)
        
        # Validate state transition
        validate_refund_status_transition(locked_self.status, 'completed')
        
        previous_status = locked_self.status
        locked_self.status = 'completed'
        locked_self.transaction_id = transaction_id
        locked_self.processed_by = processed_by
        locked_self.processed_at = timezone.now()
        locked_self.save()
        
        # Update self with new values
        self.status = locked_self.status
        self.transaction_id = locked_self.transaction_id
        self.processed_by = locked_self.processed_by
        self.processed_at = locked_self.processed_at
        
        # Audit log
        ReturnAuditLog.log(
            operation='refund_completed',
            return_request=self.return_request,
            user=processed_by,
            previous_state={'status': previous_status},
            new_state={
                'status': 'completed',
                'transaction_id': transaction_id,
                'amount': str(self.amount),
            },
            details={'refund_transaction_id': str(self.id)}
        )
        
        logger.info(f"RefundTransaction {self.id} marked completed (external ref: {transaction_id})")
    
    @transaction.atomic
    def mark_failed(self, reason='', failed_by=None):
        """
        Mark refund as failed.
        
        Atomicity: Uses select_for_update to prevent concurrent modifications
        State Validation: Validates pending/processing -> failed transition
        """
        from .returns_safety import validate_refund_status_transition
        
        # Lock the refund transaction
        locked_self = RefundTransaction.objects.select_for_update().get(pk=self.pk)
        
        # Validate state transition
        validate_refund_status_transition(locked_self.status, 'failed')
        
        previous_status = locked_self.status
        locked_self.status = 'failed'
        locked_self.failure_reason = reason
        locked_self.save()
        
        # Update self with new values
        self.status = locked_self.status
        self.failure_reason = locked_self.failure_reason
        
        # Audit log
        ReturnAuditLog.log(
            operation='refund_failed',
            return_request=self.return_request,
            user=failed_by,
            previous_state={'status': previous_status},
            new_state={
                'status': 'failed',
                'failure_reason': reason,
            },
            details={'refund_transaction_id': str(self.id)}
        )
        
        logger.warning(f"RefundTransaction {self.id} marked failed: {reason}")


class ReturnAuditLog(models.Model):
    """
    Audit log for return/refund operations.
    
    Provides complete audit trail of all state changes and operations
    for returns and refunds. Essential for:
    - Debugging issues
    - Compliance and accountability
    - Dispute resolution
    - Forensic analysis
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # What operation was performed
    operation = models.CharField(
        max_length=50,
        db_index=True,
        help_text='e.g., approve_return, reject_return, issue_refund, restore_stock'
    )
    
    # The return request (central reference)
    return_request = models.ForeignKey(
        ReturnRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    
    # Who performed the action
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    
    # State before operation (JSON)
    previous_state = models.JSONField(default=dict, blank=True)
    
    # State after operation (JSON)
    new_state = models.JSONField(default=dict, blank=True)
    
    # Additional details (JSON)
    details = models.JSONField(default=dict, blank=True)
    
    # Error information if operation failed
    error_message = models.TextField(blank=True)
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'return_audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['return_request', '-created_at']),
            models.Index(fields=['operation', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.operation} on {self.return_request_id} at {self.created_at}"
    
    @classmethod
    def log(
        cls,
        operation: str,
        return_request=None,
        user=None,
        previous_state: dict = None,
        new_state: dict = None,
        details: dict = None,
        error_message: str = '',
        ip_address: str = None,
        user_agent: str = '',
    ):
        """
        Create an audit log entry.
        
        This method is designed to be safe - it won't raise exceptions
        even if logging fails, to avoid disrupting the main operation.
        """
        try:
            return cls.objects.create(
                operation=operation,
                return_request=return_request,
                user=user,
                previous_state=previous_state or {},
                new_state=new_state or {},
                details=details or {},
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as e:
            # Log but don't raise - audit logging should never break operations
            logger.error(f"Failed to create ReturnAuditLog: {e}")
            return None
