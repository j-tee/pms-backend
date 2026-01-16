"""
Government Procurement Models

Manages government bulk orders from approved farms:
- Procurement officers create orders (bulk quantity needed)
- System recommends farms based on inventory + capacity
- Multiple farms assigned to fulfill one order
- Delivery tracking per farm assignment
- Payment/invoice generation per farm

Example Flow:
1. Officer needs 10,000 broilers
2. System finds 5 farms with combined capacity
3. Farm A: 3,000 birds, Farm B: 2,500, Farm C: 2,000, Farm D: 1,500, Farm E: 1,000
4. Each farm delivers separately, tracked individually
5. Each farm gets separate payment/invoice
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from farms.models import Farm
from accounts.models import User
import uuid


class ProcurementOrder(models.Model):
    """
    Main procurement order created by government officer.
    One order can be fulfilled by multiple farms.
    """
    
    PRODUCTION_TYPE_CHOICES = [
        ('Broilers', 'Broilers (Meat)'),
        ('Layers', 'Layers (Eggs)'),
        ('Both', 'Both'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published - Accepting Bids'),
        ('assigning', 'Assigning to Farms'),
        ('assigned', 'Assigned to Farms'),
        ('in_progress', 'In Progress - Farms Preparing'),
        ('partially_delivered', 'Partially Delivered'),
        ('fully_delivered', 'Fully Delivered'),
        ('completed', 'Completed - Payments Processed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('normal', 'Normal'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Format: ORD-YYYY-XXXXX"
    )
    
    # Order Details
    title = models.CharField(
        max_length=200,
        help_text="Brief description of order"
    )
    description = models.TextField(help_text="Detailed requirements")
    production_type = models.CharField(
        max_length=20,
        choices=PRODUCTION_TYPE_CHOICES
    )
    
    # Quantities (for broilers - birds, for layers - eggs)
    quantity_needed = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Total quantity needed (birds or crates of eggs)"
    )
    unit = models.CharField(
        max_length=20,
        choices=[
            ('birds', 'Birds (for broilers)'),
            ('crates', 'Crates of Eggs (30 eggs each)'),
            ('kg', 'Kilograms (dressed weight)'),
        ],
        default='birds'
    )
    quantity_assigned = models.PositiveIntegerField(
        default=0,
        help_text="Total quantity assigned to farms"
    )
    quantity_delivered = models.PositiveIntegerField(
        default=0,
        help_text="Total quantity delivered so far"
    )
    
    # Quality Requirements
    min_weight_per_bird_kg = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.5), MaxValueValidator(10)],
        help_text="Minimum average weight per bird (for broilers)"
    )
    quality_requirements = models.TextField(
        blank=True,
        help_text="Any specific quality/health requirements"
    )
    
    # Pricing
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price per bird or crate (GHS)"
    )
    total_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total budget allocated (GHS)"
    )
    total_cost_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Actual total cost from all farm assignments"
    )
    
    # Delivery
    delivery_location = models.TextField(help_text="Where products should be delivered")
    delivery_location_gps = models.CharField(max_length=100, blank=True)
    delivery_deadline = models.DateField(
        help_text="Farms must deliver by this date"
    )
    delivery_instructions = models.TextField(
        blank=True,
        help_text="Special delivery instructions"
    )
    
    # Assignment Strategy
    auto_assign = models.BooleanField(
        default=True,
        help_text="Auto-assign to closest farms with capacity"
    )
    preferred_region = models.CharField(
        max_length=100,
        blank=True,
        help_text="Prefer farms from this region"
    )
    max_farms = models.PositiveIntegerField(
        default=10,
        validators=[MaxValueValidator(50)],
        help_text="Maximum number of farms to assign"
    )
    
    # Management
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_procurement_orders'
    )
    assigned_procurement_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_procurement_orders',
        help_text="Officer managing this order"
    )
    
    # Status & Priority
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    # Notes
    internal_notes = models.TextField(
        blank=True,
        help_text="Internal notes (not visible to farmers)"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['delivery_deadline']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Calculate total budget if not set
        if self.total_budget is None or self.total_budget == 0:
            self.total_budget = self.quantity_needed * self.price_per_unit
        
        if not self.order_number:
            # Generate order number: ORD-2025-00001
            year = timezone.now().year
            prefix = f'ORD-{year}-'
            last_order = ProcurementOrder.objects.filter(
                order_number__startswith=prefix
            ).order_by('order_number').last()
            
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.order_number = f'{prefix}{new_num:05d}'
        
        super().save(*args, **kwargs)
    
    @property
    def fulfillment_percentage(self):
        """Percentage of order fulfilled"""
        if self.quantity_needed == 0:
            return 0
        return round((self.quantity_delivered / self.quantity_needed) * 100, 2)
    
    @property
    def assignment_percentage(self):
        """Percentage of order assigned to farms"""
        if self.quantity_needed == 0:
            return 0
        return round((self.quantity_assigned / self.quantity_needed) * 100, 2)
    
    @property
    def is_overdue(self):
        """Check if delivery deadline has passed"""
        return timezone.now().date() > self.delivery_deadline
    
    @property
    def days_until_deadline(self):
        """Days until delivery deadline"""
        delta = self.delivery_deadline - timezone.now().date()
        return delta.days


class OrderAssignment(models.Model):
    """
    Assignment of part of an order to a specific farm.
    One order can have multiple assignments to different farms.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Farm Response'),
        ('accepted', 'Accepted by Farm'),
        ('rejected', 'Rejected by Farm'),
        ('preparing', 'Farm Preparing Order'),
        ('ready', 'Ready for Delivery'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('verified', 'Verified & Accepted'),
        ('paid', 'Payment Processed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment_number = models.CharField(
        max_length=25,
        unique=True,
        editable=False,
        help_text="Format: ORD-YYYY-XXXXX-A01"
    )
    
    # Relationships
    order = models.ForeignKey(
        ProcurementOrder,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name='procurement_assignments'
    )
    
    # Assignment Details
    quantity_assigned = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity assigned to this farm"
    )
    quantity_delivered = models.PositiveIntegerField(
        default=0,
        help_text="Quantity actually delivered"
    )
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Agreed price per unit for this farm"
    )
    total_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total value of this assignment (auto-calculated)"
    )
    
    # Farm Response
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Status & Timeline
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    expected_ready_date = models.DateField(
        null=True,
        blank=True,
        help_text="When farm expects to have order ready"
    )
    actual_ready_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    payment_processed_at = models.DateTimeField(null=True, blank=True)
    
    # Quality Tracking
    average_weight_per_bird = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual average weight delivered"
    )
    quality_passed = models.BooleanField(
        default=False,
        help_text="Whether delivery passed quality inspection"
    )
    quality_notes = models.TextField(blank=True)
    
    # Notes
    farm_notes = models.TextField(
        blank=True,
        help_text="Notes from farm about this assignment"
    )
    officer_notes = models.TextField(
        blank=True,
        help_text="Notes from procurement officer"
    )
    
    # =========================================================================
    # DISTRESS TRACKING (Captured at assignment time for impact measurement)
    # =========================================================================
    
    SELECTION_REASON_CHOICES = [
        ('DISTRESS_PRIORITY', 'Selected due to high distress score'),
        ('CAPACITY_MATCH', 'Selected based on capacity availability'),
        ('LOCATION_MATCH', 'Selected based on geographic proximity'),
        ('OFFICER_SELECTED', 'Manually selected by procurement officer'),
        ('AUTO_ASSIGNED', 'Auto-assigned by system'),
    ]
    
    farmer_distress_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Farmer's distress score at time of assignment (0-100)"
    )
    farmer_distress_level = models.CharField(
        max_length=20,
        choices=[
            ('STABLE', 'Stable'),
            ('LOW', 'Low'),
            ('MODERATE', 'Moderate'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical'),
        ],
        blank=True,
        help_text="Farmer's distress level at time of assignment"
    )
    selection_reason = models.CharField(
        max_length=50,
        choices=SELECTION_REASON_CHOICES,
        default='CAPACITY_MATCH',
        help_text="Why this farm was selected for assignment"
    )
    
    class Meta:
        ordering = ['order', 'assigned_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.assignment_number} - {self.farm.farm_name}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total value
        self.total_value = Decimal(str(self.quantity_assigned)) * self.price_per_unit
        
        if not self.assignment_number:
            # Generate: ORD-2025-00001-A01
            base = self.order.order_number
            count = OrderAssignment.objects.filter(order=self.order).count() + 1
            self.assignment_number = f'{base}-A{count:02d}'
        
        super().save(*args, **kwargs)
    
    @property
    def fulfillment_percentage(self):
        """Percentage of assigned quantity delivered"""
        if self.quantity_assigned == 0:
            return 0
        return round((self.quantity_delivered / self.quantity_assigned) * 100, 2)
    
    @property
    def is_fully_delivered(self):
        """Check if full quantity delivered"""
        return self.quantity_delivered >= self.quantity_assigned


class DeliveryConfirmation(models.Model):
    """
    Records delivery events for order assignments.
    Supports partial deliveries - one assignment can have multiple delivery events.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        help_text="Format: DEL-YYYY-XXXXX"
    )
    
    assignment = models.ForeignKey(
        OrderAssignment,
        on_delete=models.CASCADE,
        related_name='deliveries'
    )
    
    # Delivery Details
    quantity_delivered = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity in this delivery"
    )
    delivery_date = models.DateField()
    delivery_time = models.TimeField()
    
    # Verification
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_deliveries',
        help_text="Officer who received delivery"
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_deliveries',
        help_text="Officer who verified quality"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Quality Inspection
    quality_passed = models.BooleanField(default=True)
    average_weight_per_bird = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )
    mortality_count = models.PositiveIntegerField(
        default=0,
        help_text="Dead on arrival"
    )
    quality_issues = models.TextField(blank=True)
    quality_photos = models.JSONField(
        default=list,
        blank=True,
        help_text="URLs to uploaded quality inspection photos"
    )
    
    # Documentation
    delivery_note_number = models.CharField(max_length=100, blank=True)
    vehicle_registration = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=200, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    
    # Signatures/Confirmation
    delivery_confirmed = models.BooleanField(default=False)
    confirmation_signature = models.TextField(
        blank=True,
        help_text="Base64 encoded signature"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-delivery_date', '-delivery_time']
        indexes = [
            models.Index(fields=['assignment']),
            models.Index(fields=['delivery_date']),
        ]
    
    def __str__(self):
        return f"{self.delivery_number} - {self.quantity_delivered} units"
    
    def save(self, *args, **kwargs):
        if not self.delivery_number:
            year = timezone.now().year
            prefix = f'DEL-{year}-'
            last_del = DeliveryConfirmation.objects.filter(
                delivery_number__startswith=prefix
            ).order_by('delivery_number').last()
            
            if last_del:
                last_num = int(last_del.delivery_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.delivery_number = f'{prefix}{new_num:05d}'
        
        super().save(*args, **kwargs)


class ProcurementInvoice(models.Model):
    """
    Invoice generated for farm payment.
    One invoice per order assignment.
    """
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved for Payment'),
        ('processing', 'Payment Processing'),
        ('paid', 'Paid'),
        ('failed', 'Payment Failed'),
        ('disputed', 'Disputed'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('paystack', 'Paystack Subaccount'),
        ('cheque', 'Cheque'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Format: INV-YYYY-XXXXX"
    )
    
    assignment = models.OneToOneField(
        OrderAssignment,
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name='procurement_invoices'
    )
    order = models.ForeignKey(
        ProcurementOrder,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    
    # Invoice Details
    quantity_invoiced = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Deductions
    quality_deduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Deduction for quality issues"
    )
    mortality_deduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Deduction for dead on arrival"
    )
    other_deductions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    deduction_notes = models.TextField(blank=True)
    
    # Total
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Subtotal - All Deductions"
    )
    
    # Payment
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True
    )
    payment_reference = models.CharField(
        max_length=200,
        blank=True,
        help_text="Bank reference or transaction ID"
    )
    payment_date = models.DateField(null=True, blank=True)
    paid_to_account = models.CharField(
        max_length=100,
        blank=True,
        help_text="Account number payment was made to"
    )
    
    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_invoices'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    invoice_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(
        help_text="Payment due by this date"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['payment_status']),
            models.Index(fields=['farm']),
            models.Index(fields=['order']),
            models.Index(fields=['invoice_date']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.farm.farm_name} - GHS {self.total_amount}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate totals
        self.subtotal = Decimal(str(self.quantity_invoiced)) * self.unit_price
        self.total_amount = self.subtotal - self.quality_deduction - self.mortality_deduction - self.other_deductions
        
        if not self.invoice_number:
            year = timezone.now().year
            prefix = f'INV-{year}-'
            last_inv = ProcurementInvoice.objects.filter(
                invoice_number__startswith=prefix
            ).order_by('invoice_number').last()
            
            if last_inv:
                last_num = int(last_inv.invoice_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.invoice_number = f'{prefix}{new_num:05d}'
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        if self.payment_status == 'paid':
            return False
        return timezone.now().date() > self.due_date


# ==============================================================================
# IDEMPOTENCY AND AUDIT MODELS
# ==============================================================================

class IdempotencyKey(models.Model):
    """
    Stores idempotency keys to prevent duplicate operations.
    
    Usage:
        - Client sends unique idempotency_key header with request
        - Server checks if key exists before processing
        - If key exists, return cached response
        - If not, process request and store response
        
    Cleanup:
        - Run IdempotencyKey.cleanup_expired() periodically via Celery
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=255, unique=True, db_index=True)
    
    # Request context
    user_id = models.UUIDField(null=True, blank=True)
    operation = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Response caching
    response_status = models.IntegerField(null=True)
    response_data = models.JSONField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='processing'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'procurement_idempotency_keys'
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['user_id', 'operation']),
        ]
    
    def __str__(self):
        return f"{self.operation} - {self.status} - {self.key[:16]}..."
    
    @classmethod
    def generate_key(cls, user_id: str, operation: str, **kwargs) -> str:
        """Generate a deterministic idempotency key based on operation parameters."""
        import hashlib
        key_parts = [str(user_id), operation]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    @classmethod
    def get_if_exists(cls, key: str):
        """Check if idempotency key exists and return cached response if completed."""
        try:
            record = cls.objects.get(key=key)
            if record.status == 'completed' and record.response_data:
                return record.response_data
            elif record.status == 'processing':
                # Request is still being processed
                raise ValueError("Request is already being processed")
            return None
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def store(cls, key: str, response_data: dict, ttl_hours: int = 24):
        """Store completed response for idempotency key."""
        from datetime import timedelta
        record, _ = cls.objects.update_or_create(
            key=key,
            defaults={
                'status': 'completed',
                'response_data': response_data,
                'completed_at': timezone.now(),
                'expires_at': timezone.now() + timedelta(hours=ttl_hours)
            }
        )
        return record
    
    @classmethod
    def cleanup_expired(cls):
        """Remove expired idempotency keys. Run periodically via Celery."""
        deleted, _ = cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return deleted


class ProcurementAuditLog(models.Model):
    """
    Comprehensive audit log for all procurement operations.
    
    Records every state change for:
    - Compliance and accountability
    - Debugging issues
    - Fraud detection
    - Historical analysis
    
    This is a write-only table - records should never be updated or deleted.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Operation details
    operation = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.UUIDField(db_index=True)
    
    # User who performed the action
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='procurement_audit_logs'
    )
    user_role = models.CharField(max_length=50, null=True, blank=True)
    
    # State changes
    previous_state = models.JSONField(default=dict)
    new_state = models.JSONField(default=dict)
    
    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'procurement_audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['operation', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.operation} on {self.resource_type} by {self.user} at {self.timestamp}"
    
    @classmethod
    def log(cls, operation: str, resource_type: str, resource_id, 
            user=None, previous_state: dict = None, new_state: dict = None,
            ip_address: str = None, user_agent: str = None, 
            idempotency_key: str = None):
        """
        Create an audit log entry.
        
        This method should be called within the same transaction as the operation
        it's logging to ensure atomicity.
        """
        return cls.objects.create(
            operation=operation,
            resource_type=resource_type,
            resource_id=resource_id,
            user=user,
            user_role=user.role if user else None,
            previous_state=previous_state or {},
            new_state=new_state or {},
            ip_address=ip_address,
            user_agent=user_agent,
            idempotency_key=idempotency_key,
        )
    
    @classmethod
    def get_history(cls, resource_type: str, resource_id):
        """Get complete audit history for a resource."""
        return cls.objects.filter(
            resource_type=resource_type,
            resource_id=resource_id
        ).order_by('timestamp')


# =============================================================================
# FARM DISTRESS HISTORY MODEL
# =============================================================================

class FarmDistressHistory(models.Model):
    """
    Historical record of farm distress scores.
    
    Used for:
    - Tracking distress trends over time
    - Measuring impact of interventions (procurement, training)
    - Analytics on program effectiveness
    """
    
    DISTRESS_LEVEL_CHOICES = [
        ('STABLE', 'Stable - Healthy operations'),
        ('LOW', 'Low - Minor issues'),
        ('MODERATE', 'Moderate - Some difficulties'),
        ('HIGH', 'High - Significant struggle'),
        ('CRITICAL', 'Critical - Urgent intervention needed'),
    ]
    
    INTERVENTION_TYPE_CHOICES = [
        ('PROCUREMENT', 'Government Procurement Order'),
        ('LOAN', 'Government Loan/Subsidy'),
        ('TRAINING', 'Training/Extension Visit'),
        ('EQUIPMENT', 'Equipment Support'),
        ('VETERINARY', 'Veterinary Intervention'),
        ('MARKETPLACE', 'Marketplace Activation'),
        ('OTHER', 'Other Intervention'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name='distress_history'
    )
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    # Score at time of recording
    distress_score = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Distress score at time of recording (0-100)"
    )
    distress_level = models.CharField(
        max_length=20,
        choices=DISTRESS_LEVEL_CHOICES,
        help_text="Distress level category"
    )
    
    # Detailed breakdown stored as JSON
    factors = models.JSONField(
        default=dict,
        help_text="""
        Detailed factor breakdown:
        {
            'inventory_stagnation': {'score': 85, 'detail': '...'},
            'sales_performance': {'score': 70, 'detail': '...'},
            'financial_stress': {'score': 60, 'detail': '...'},
            'production_issues': {'score': 30, 'detail': '...'},
            'market_access': {'score': 40, 'detail': '...'}
        }
        """
    )
    
    # Optional intervention tracking
    intervention_type = models.CharField(
        max_length=50,
        choices=INTERVENTION_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Type of intervention if this record follows an intervention"
    )
    intervention_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Value of intervention (e.g., procurement amount)"
    )
    intervention_reference = models.CharField(
        max_length=50,
        blank=True,
        help_text="Reference ID of intervention (e.g., order number)"
    )
    intervention_notes = models.TextField(
        blank=True,
        help_text="Notes about the intervention"
    )
    
    # Who triggered this calculation
    calculated_by = models.CharField(
        max_length=50,
        default='system',
        help_text="Who triggered: 'system' (daily task), 'officer' (on-demand), 'api'"
    )
    
    class Meta:
        db_table = 'procurement_farm_distress_history'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['farm', '-recorded_at']),
            models.Index(fields=['distress_level', '-recorded_at']),
            models.Index(fields=['intervention_type']),
        ]
    
    def __str__(self):
        return f"{self.farm.farm_name} - Score {self.distress_score} at {self.recorded_at}"
    
    @classmethod
    def record(cls, farm, assessment: dict, intervention_type=None, 
               intervention_value=None, intervention_reference=None,
               calculated_by='system'):
        """
        Record a distress score snapshot.
        
        Args:
            farm: Farm instance
            assessment: Dict from FarmerDistressService.calculate_distress_score()
            intervention_type: Optional intervention that preceded this
            intervention_value: Value of intervention
            intervention_reference: Reference ID (order number, etc.)
            calculated_by: Who triggered this calculation
            
        Returns:
            FarmDistressHistory instance
        """
        factors = {}
        if 'score_breakdown' in assessment:
            for key, data in assessment['score_breakdown'].items():
                factors[key] = {
                    'score': data.get('score', 0),
                    'detail': data.get('detail', ''),
                }
        
        return cls.objects.create(
            farm=farm,
            distress_score=assessment.get('distress_score', 0),
            distress_level=assessment.get('distress_level', 'STABLE'),
            factors=factors,
            intervention_type=intervention_type,
            intervention_value=intervention_value,
            intervention_reference=intervention_reference,
            calculated_by=calculated_by,
        )
    
    @classmethod
    def get_farm_trend(cls, farm, days=90):
        """
        Get distress score trend for a farm.
        
        Returns list of (date, score) tuples for charting.
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        records = cls.objects.filter(
            farm=farm,
            recorded_at__gte=cutoff
        ).order_by('recorded_at').values('recorded_at', 'distress_score')
        
        return [
            {
                'date': r['recorded_at'].date().isoformat(),
                'score': r['distress_score']
            }
            for r in records
        ]
