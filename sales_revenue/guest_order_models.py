"""
Guest Order and POS Models

Enables two purchase pathways:
1. Guest Checkout - Public marketplace with phone OTP verification (no account required)
2. POS Sales - Farmers record walk-in/farm-gate sales directly

Key Design Decisions:
- NO payment processing on platform - payments happen off-platform (MoMo, cash, etc.)
- Farmer confirms payment receipt manually
- Phone OTP prevents fake/spam orders
- Rate limiting prevents abuse
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.utils.crypto import get_random_string
from decimal import Decimal
from datetime import timedelta
import uuid


# =============================================================================
# GUEST ORDER MODELS (Public Marketplace - No Login Required)
# =============================================================================

class GuestCustomer(models.Model):
    """
    Guest customer for marketplace orders.
    Only requires phone verification - no account creation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Required fields
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^\+?233\d{9}$',
            message='Enter a valid Ghana phone number (e.g., 0241234567 or +233241234567)'
        )],
        db_index=True
    )
    name = models.CharField(max_length=200)
    
    # Optional fields
    email = models.EmailField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    
    # Phone verification status
    phone_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Order statistics
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    cancelled_orders = models.PositiveIntegerField(default=0)
    
    # Anti-abuse tracking
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField(blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_order_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'guest_customers'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['phone_verified']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
    
    @classmethod
    def get_or_create_by_phone(cls, phone_number, name, email=''):
        """Get existing guest customer or create new one."""
        # Normalize phone number
        phone = cls.normalize_phone(phone_number)
        
        customer, created = cls.objects.get_or_create(
            phone_number=phone,
            defaults={
                'name': name,
                'email': email,
            }
        )
        
        if not created and customer.name != name:
            # Update name if different
            customer.name = name
            customer.save(update_fields=['name', 'updated_at'])
        
        return customer, created
    
    @staticmethod
    def normalize_phone(phone_number):
        """Normalize phone number to +233 format."""
        phone = phone_number.strip().replace(' ', '').replace('-', '')
        if phone.startswith('0'):
            phone = '+233' + phone[1:]
        elif not phone.startswith('+'):
            phone = '+' + phone
        return phone


class GuestOrderOTP(models.Model):
    """
    OTP codes for guest order verification.
    Expires after 10 minutes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    phone_number = models.CharField(max_length=15, db_index=True)
    code = models.CharField(max_length=6)
    
    # Tracking
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'guest_order_otps'
        indexes = [
            models.Index(fields=['phone_number', 'code']),
            models.Index(fields=['expires_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired and self.attempts < 5
    
    @classmethod
    def generate_for_phone(cls, phone_number):
        """Generate new OTP for phone number."""
        # Invalidate existing OTPs
        cls.objects.filter(
            phone_number=phone_number,
            is_used=False
        ).update(is_used=True)
        
        # Generate 6-digit code
        code = get_random_string(6, allowed_chars='0123456789')
        
        return cls.objects.create(
            phone_number=phone_number,
            code=code
        )
    
    @classmethod
    def verify(cls, phone_number, code):
        """Verify OTP code for phone number."""
        try:
            otp = cls.objects.get(
                phone_number=phone_number,
                code=code,
                is_used=False
            )
            
            if otp.is_expired:
                return False, "OTP has expired. Please request a new one."
            
            if otp.attempts >= 5:
                return False, "Too many attempts. Please request a new OTP."
            
            # Mark as used
            otp.is_used = True
            otp.used_at = timezone.now()
            otp.save(update_fields=['is_used', 'used_at'])
            
            return True, "Phone verified successfully."
            
        except cls.DoesNotExist:
            # Increment attempts on wrong code
            cls.objects.filter(
                phone_number=phone_number,
                is_used=False
            ).update(attempts=models.F('attempts') + 1)
            
            return False, "Invalid OTP code."


class GuestOrder(models.Model):
    """
    Guest order - placed through public marketplace without login.
    
    Order Flow:
    1. pending_verification - OTP sent, awaiting phone verification
    2. pending_confirmation - Phone verified, awaiting farmer confirmation
    3. confirmed - Farmer accepted order, awaiting payment
    4. payment_confirmed - Farmer confirmed payment received (off-platform)
    5. processing - Order is being prepared
    6. ready - Ready for pickup or delivery
    7. completed - Customer received order
    8. cancelled - Order was cancelled
    
    NOTE: Payment happens OFF-PLATFORM (MoMo, cash, etc.)
    Farmer manually confirms when payment is received.
    """
    
    STATUS_CHOICES = [
        ('pending_verification', 'Pending Phone Verification'),
        ('pending_confirmation', 'Awaiting Farmer Confirmation'),
        ('confirmed', 'Confirmed - Awaiting Payment'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('processing', 'Processing'),
        ('ready', 'Ready for Pickup/Delivery'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('pickup', 'Farm Pickup'),
        ('farmer_delivery', 'Farmer Delivers'),
        ('third_party', 'Third-Party Delivery'),
    ]
    
    CANCELLATION_REASON_CHOICES = [
        ('customer_request', 'Customer Requested'),
        ('farmer_unavailable', 'Product Unavailable'),
        ('payment_timeout', 'Payment Timeout'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Farm receiving the order
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='guest_orders'
    )
    
    # Guest customer (phone verified)
    guest_customer = models.ForeignKey(
        GuestCustomer,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    
    # Order status
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='pending_verification',
        db_index=True
    )
    
    # Contact and delivery info
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        default='pickup'
    )
    delivery_address = models.TextField(blank=True)
    delivery_gps = models.CharField(max_length=50, blank=True, help_text='GPS coordinates')
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.CharField(max_length=50, blank=True, help_text='e.g., Morning, Afternoon')
    customer_notes = models.TextField(blank=True)
    
    # Pricing (NO payment processing - just tracking)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Payment tracking (off-platform)
    payment_method_used = models.CharField(
        max_length=50,
        blank=True,
        help_text='How customer paid (e.g., MoMo, Cash, Bank Transfer)'
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text='Reference from payment (e.g., MoMo transaction ID)'
    )
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)
    payment_confirmed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_guest_payments'
    )
    
    # Farmer notes (internal)
    farmer_notes = models.TextField(blank=True)
    
    # Cancellation
    cancellation_reason = models.CharField(
        max_length=30,
        choices=CANCELLATION_REASON_CHOICES,
        blank=True
    )
    cancellation_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Order expires if not confirmed by this time'
    )
    
    class Meta:
        db_table = 'guest_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', '-created_at']),
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['guest_customer', '-created_at']),
            models.Index(fields=['order_number']),
            models.Index(fields=['status', 'expires_at']),
        ]
    
    def __str__(self):
        return f"Guest Order {self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)
    
    def _generate_order_number(self):
        """Generate unique order number: GO-YYYYMMDD-XXXXX"""
        date_part = timezone.now().strftime('%Y%m%d')
        random_part = get_random_string(5, allowed_chars='0123456789ABCDEFGHJKLMNPQRSTUVWXYZ')
        return f"GO-{date_part}-{random_part}"
    
    def calculate_totals(self):
        """Recalculate order totals from items."""
        self.subtotal = sum(item.line_total for item in self.items.all())
        self.total_amount = self.subtotal + self.delivery_fee
        self.save(update_fields=['subtotal', 'total_amount', 'updated_at'])
    
    def confirm_payment(self, user, payment_method='', reference=''):
        """Farmer confirms payment was received."""
        self.status = 'payment_confirmed'
        self.payment_method_used = payment_method
        self.payment_reference = reference
        self.payment_confirmed_at = timezone.now()
        self.payment_confirmed_by = user
        self.save()
    
    def cancel(self, reason, notes=''):
        """Cancel the order."""
        self.status = 'cancelled'
        self.cancellation_reason = reason
        self.cancellation_notes = notes
        self.cancelled_at = timezone.now()
        self.save()
        
        # Restore stock for all items
        for item in self.items.all():
            item.product.restore_stock(item.quantity)
        
        # Update guest customer stats
        self.guest_customer.cancelled_orders += 1
        self.guest_customer.save(update_fields=['cancelled_orders'])


class GuestOrderItem(models.Model):
    """Line items for guest orders."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.ForeignKey(
        GuestOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'sales_revenue.Product',
        on_delete=models.PROTECT,
        related_name='guest_order_items'
    )
    
    # Snapshot of product at time of order
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'guest_order_items'
    
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


# =============================================================================
# ORDER RATE LIMITING (Anti-Abuse)
# =============================================================================

class GuestOrderRateLimit(models.Model):
    """
    Track order rate limits per phone number.
    Prevents spam orders.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, db_index=True)
    date = models.DateField(db_index=True)
    
    order_count = models.PositiveIntegerField(default=0)
    otp_requests = models.PositiveIntegerField(default=0)
    failed_otps = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'guest_order_rate_limits'
        unique_together = ['phone_number', 'date']
    
    @classmethod
    def check_limit(cls, phone_number, limit_type='order', max_count=5):
        """
        Check if phone number has exceeded rate limit.
        
        Args:
            phone_number: Phone number to check
            limit_type: 'order', 'otp', or 'failed_otp'
            max_count: Maximum allowed count
        
        Returns:
            (allowed: bool, remaining: int)
        """
        today = timezone.now().date()
        record, _ = cls.objects.get_or_create(
            phone_number=phone_number,
            date=today
        )
        
        if limit_type == 'order':
            count = record.order_count
        elif limit_type == 'otp':
            count = record.otp_requests
        else:
            count = record.failed_otps
        
        remaining = max(0, max_count - count)
        return count < max_count, remaining
    
    @classmethod
    def increment(cls, phone_number, limit_type='order'):
        """Increment counter for phone number."""
        today = timezone.now().date()
        record, _ = cls.objects.get_or_create(
            phone_number=phone_number,
            date=today
        )
        
        if limit_type == 'order':
            record.order_count += 1
        elif limit_type == 'otp':
            record.otp_requests += 1
        else:
            record.failed_otps += 1
        
        record.save()


# =============================================================================
# POS SALES (Farm Gate Sales - Farmer Records Directly)
# =============================================================================

class POSSale(models.Model):
    """
    Point-of-Sale record for walk-in/farm-gate sales.
    
    For when customers come to the farm directly and pay on the spot.
    Farmer records the sale - no customer verification needed.
    
    Payment is assumed to be received at time of recording.
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('momo_mtn', 'MTN Mobile Money'),
        ('momo_voda', 'Vodafone Cash'),
        ('momo_tigo', 'AirtelTigo Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'On Credit'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Farm recording the sale
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='pos_sales'
    )
    
    # Recorded by
    recorded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='recorded_pos_sales'
    )
    
    # Customer info (optional - for walk-ins)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=15, blank=True)
    
    # Link to existing customer (if they're a known customer)
    customer = models.ForeignKey(
        'sales_revenue.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pos_sales'
    )
    
    # Payment (already received)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text='Transaction ID for mobile money payments'
    )
    
    # Totals
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Amount actually received (for credit sales, this may be 0)'
    )
    
    # Credit tracking
    is_credit_sale = models.BooleanField(default=False)
    credit_due_date = models.DateField(null=True, blank=True)
    credit_paid = models.BooleanField(default=False)
    credit_paid_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sale_date = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'pos_sales'
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['farm', '-sale_date']),
            models.Index(fields=['farm', 'is_credit_sale']),
            models.Index(fields=['sale_number']),
            models.Index(fields=['recorded_by', '-sale_date']),
        ]
    
    def __str__(self):
        return f"POS Sale {self.sale_number}"
    
    def save(self, *args, **kwargs):
        if not self.sale_number:
            self.sale_number = self._generate_sale_number()
        
        # Calculate totals
        if self.pk:  # Only if already saved (has items)
            self.calculate_totals()
        
        # Set credit sale flag
        if self.payment_method == 'credit':
            self.is_credit_sale = True
            self.amount_received = 0
        
        super().save(*args, **kwargs)
    
    def _generate_sale_number(self):
        """Generate unique sale number: POS-YYYYMMDD-XXXXX"""
        date_part = timezone.now().strftime('%Y%m%d')
        random_part = get_random_string(5, allowed_chars='0123456789')
        return f"POS-{date_part}-{random_part}"
    
    def calculate_totals(self):
        """Recalculate sale totals from items."""
        items_total = sum(item.line_total for item in self.items.all())
        self.subtotal = items_total
        self.total_amount = self.subtotal - self.discount_amount
        
        if not self.is_credit_sale:
            self.amount_received = self.total_amount
    
    def mark_credit_paid(self, payment_method='', reference=''):
        """Mark a credit sale as paid."""
        self.credit_paid = True
        self.credit_paid_at = timezone.now()
        self.amount_received = self.total_amount
        if payment_method:
            self.payment_method = payment_method
            self.payment_reference = reference
        self.save()


class POSSaleItem(models.Model):
    """Line items for POS sales."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    sale = models.ForeignKey(
        POSSale,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'sales_revenue.Product',
        on_delete=models.PROTECT,
        related_name='pos_sale_items'
    )
    
    # Product snapshot
    product_name = models.CharField(max_length=200)
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'pos_sale_items'
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Calculate line total
        self.line_total = self.unit_price * self.quantity
        
        # Snapshot product details if not set
        if not self.product_name:
            self.product_name = self.product.name
            self.unit = self.product.unit
            self.unit_price = self.product.price
        
        super().save(*args, **kwargs)
        
        # Reduce product stock
        self.product.reduce_stock(self.quantity)
