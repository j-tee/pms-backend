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
