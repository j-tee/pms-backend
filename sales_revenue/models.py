from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
import uuid
import hashlib
import json
from datetime import timedelta


class PlatformSettings(models.Model):
    """
    Platform-wide settings for commission rates, fees, and payment configuration.
    Admin can adjust these settings without code changes.
    
    Singleton model - only one instance should exist.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Commission Tiers (Percentage-based)
    commission_tier_1_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Commission for sales < GHS 100 (in percentage)"
    )
    commission_tier_1_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100.0,
        validators=[MinValueValidator(0)],
        help_text="Maximum amount for Tier 1 (GHS)"
    )
    
    commission_tier_2_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Commission for sales GHS 100-500 (in percentage)"
    )
    commission_tier_2_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500.0,
        validators=[MinValueValidator(0)],
        help_text="Maximum amount for Tier 2 (GHS)"
    )
    
    commission_tier_3_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Commission for sales > GHS 500 (in percentage)"
    )
    
    # Minimum Commission
    commission_minimum_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=2.0,
        validators=[MinValueValidator(0)],
        help_text="Minimum commission per transaction (GHS)"
    )
    
    # Paystack Configuration
    paystack_fee_bearer = models.CharField(
        max_length=20,
        choices=[
            ('account', 'Platform Pays Fees'),
            ('subaccount', 'Farmer Pays Fees'),
        ],
        default='account',
        help_text="Who pays Paystack transaction fees"
    )
    
    paystack_settlement_schedule = models.CharField(
        max_length=20,
        choices=[
            ('auto', 'Auto (24 hours)'),
            ('instant', 'Instant (2 minutes)'),
        ],
        default='auto',
        help_text="How quickly farmers receive settlements"
    )
    
    # Payment Retry Configuration
    payment_retry_max_attempts = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Maximum payment retry attempts"
    )
    
    payment_retry_delay_seconds = models.PositiveIntegerField(
        default=300,
        validators=[MinValueValidator(60), MaxValueValidator(3600)],
        help_text="Delay between retry attempts (seconds)"
    )
    
    # Refund Configuration
    refund_eligibility_hours = models.PositiveIntegerField(
        default=48,
        validators=[MinValueValidator(1), MaxValueValidator(168)],
        help_text="Hours within which customers can request refunds"
    )
    
    payment_auto_refund_hours = models.PositiveIntegerField(
        default=72,
        validators=[MinValueValidator(24), MaxValueValidator(336)],
        help_text="Hours after which failed payments are auto-refunded"
    )
    
    # Feature Flags
    enable_instant_settlements = models.BooleanField(
        default=False,
        help_text="Allow instant settlements (with extra fee)"
    )
    
    enable_refunds = models.BooleanField(
        default=True,
        help_text="Allow customer refund requests"
    )
    
    enable_auto_refunds = models.BooleanField(
        default=True,
        help_text="Automatically refund failed payments after timeout"
    )
    
    # Metadata
    last_modified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_settings_modifications'
    )
    notes = models.TextField(
        blank=True,
        help_text="Admin notes about setting changes"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'platform_settings'
        verbose_name = 'Platform Settings'
        verbose_name_plural = 'Platform Settings'
    
    def __str__(self):
        return f"Platform Settings (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        # Ensure only one settings instance exists (singleton pattern)
        if not self.pk and PlatformSettings.objects.exists():
            raise ValueError("Platform settings already exist. Please edit the existing settings.")
        
        # Clear cache when settings change
        cache.delete('platform_settings')
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """
        Get platform settings (cached for performance).
        Creates default settings if none exist.
        """
        # Try cache first
        settings = cache.get('platform_settings')
        if settings:
            return settings
        
        # Get from database
        settings = cls.objects.first()
        
        # Create default if doesn't exist
        if not settings:
            settings = cls.objects.create()
        
        # Cache for 1 hour
        cache.set('platform_settings', settings, 3600)
        
        return settings
    
    def calculate_commission(self, amount):
        """
        Calculate commission based on tiered structure.
        
        Args:
            amount: Sale amount (Decimal)
            
        Returns:
            Commission amount (Decimal)
        """
        amount = Decimal(str(amount))
        
        # Tier 1: Below first threshold
        if amount < self.commission_tier_1_threshold:
            commission = amount * (Decimal(str(self.commission_tier_1_percentage)) / Decimal('100'))
        # Tier 2: Between first and second threshold
        elif amount < self.commission_tier_2_threshold:
            commission = amount * (Decimal(str(self.commission_tier_2_percentage)) / Decimal('100'))
        # Tier 3: Above second threshold
        else:
            commission = amount * (Decimal(str(self.commission_tier_3_percentage)) / Decimal('100'))
        
        # Apply minimum commission
        return max(commission, self.commission_minimum_amount)


class Customer(models.Model):
    """
    Customer model for tracking buyers of eggs and birds.
    Supports both individual and business customers with mobile money integration.
    """
    CUSTOMER_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('business', 'Business'),
        ('retailer', 'Retailer'),
        ('wholesaler', 'Wholesaler'),
    ]
    
    MOBILE_MONEY_PROVIDER_CHOICES = [
        ('mtn', 'MTN Mobile Money'),
        ('vodafone', 'Vodafone Cash'),
        ('airteltigo', 'AirtelTigo Money'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey('farms.Farm', on_delete=models.CASCADE, related_name='customers')
    
    # Basic Information
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, default='individual')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Contact Information
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?233\d{9}$', message='Enter a valid Ghana phone number')]
    )
    email = models.EmailField(blank=True, null=True)
    
    # Payment Information (Mobile Money)
    mobile_money_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?233\d{9}$', message='Enter a valid Ghana phone number')],
        help_text='Mobile money number for payments'
    )
    mobile_money_provider = models.CharField(
        max_length=20,
        choices=MOBILE_MONEY_PROVIDER_CHOICES,
        help_text='Mobile money provider'
    )
    mobile_money_account_name = models.CharField(
        max_length=200,
        help_text='Account holder name for mobile money'
    )
    
    # Location
    location = models.CharField(max_length=255, blank=True)
    delivery_address = models.TextField(blank=True)
    
    # Metadata
    total_purchases = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    total_orders = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text='Additional notes about the customer')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', 'phone_number']),
            models.Index(fields=['mobile_money_number']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        if self.business_name:
            return f"{self.business_name} ({self.get_full_name()})"
        return self.get_full_name()
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class EggSale(models.Model):
    """
    Egg sales with automatic commission calculation and Paystack payment integration.
    Tracks sales from production through payment to farmer payout.
    """
    UNIT_CHOICES = [
        ('crate', 'Crate (30 eggs)'),
        ('piece', 'Individual Eggs'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Payment Received'),
        ('processing', 'Processing Payout'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey('farms.Farm', on_delete=models.CASCADE, related_name='egg_sales')
    customer = models.ForeignKey('Customer', on_delete=models.PROTECT, related_name='egg_purchases')
    daily_production = models.ForeignKey(
        'flock_management.DailyProduction',
        on_delete=models.PROTECT,
        related_name='egg_sales',
        help_text='Link to the production record'
    )
    
    # Sale Details
    sale_date = models.DateField(default=timezone.now)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='crate')
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text='Price per crate or per egg'
    )
    
    # Calculated Amounts (auto-populated)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='quantity × price_per_unit'
    )
    platform_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Platform commission (percentage-based)'
    )
    paystack_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Paystack transaction fee (paid by platform)'
    )
    farmer_payout = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Amount to be paid to farmer (subtotal - commission)'
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Total amount customer pays (same as subtotal)'
    )
    
    # Status and Payment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment = models.OneToOneField(
        'Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='egg_sale'
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sale_date', '-created_at']
        indexes = [
            models.Index(fields=['farm', '-sale_date']),
            models.Index(fields=['customer', '-sale_date']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Egg Sale: {self.quantity} {self.unit}(s) - {self.customer.get_full_name()} - GHS {self.total_amount}"
    
    def calculate_amounts(self):
        """Calculate all monetary amounts based on commission tier"""
        # Subtotal
        self.subtotal = self.quantity * self.price_per_unit
        self.total_amount = self.subtotal
        
        # Platform commission (from PlatformSettings)
        settings = PlatformSettings.get_settings()
        self.platform_commission = settings.calculate_commission(self.subtotal)
        
        # Paystack fee (1.5% + GHS 0.10) - platform pays this
        self.paystack_fee = (self.subtotal * Decimal('0.015')) + Decimal('0.10')
        
        # Farmer receives: subtotal - commission
        self.farmer_payout = self.subtotal - self.platform_commission
    
    def save(self, *args, **kwargs):
        # Auto-calculate amounts before saving
        if not self.subtotal or self.subtotal == 0:
            self.calculate_amounts()
        super().save(*args, **kwargs)


class BirdSale(models.Model):
    """
    Bird sales (chickens) with commission calculation and payment tracking.
    """
    BIRD_TYPE_CHOICES = [
        ('layer', 'Layer'),
        ('broiler', 'Broiler'),
        ('cockerel', 'Cockerel'),
        ('spent_hen', 'Spent Hen'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Payment Received'),
        ('processing', 'Processing Payout'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey('farms.Farm', on_delete=models.CASCADE, related_name='bird_sales')
    customer = models.ForeignKey('Customer', on_delete=models.PROTECT, related_name='bird_purchases')
    flock = models.ForeignKey(
        'flock_management.Flock',
        on_delete=models.PROTECT,
        related_name='bird_sales',
        help_text='Flock from which birds are sold'
    )
    
    # Sale Details
    sale_date = models.DateField(default=timezone.now)
    bird_type = models.CharField(max_length=20, choices=BIRD_TYPE_CHOICES)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price_per_bird = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    
    # Calculated Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paystack_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    farmer_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Status and Payment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment = models.OneToOneField(
        'Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bird_sale'
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sale_date', '-created_at']
        indexes = [
            models.Index(fields=['farm', '-sale_date']),
            models.Index(fields=['customer', '-sale_date']),
            models.Index(fields=['flock']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Bird Sale: {self.quantity} {self.bird_type}(s) - {self.customer.get_full_name()} - GHS {self.total_amount}"
    
    def calculate_amounts(self):
        """Calculate all monetary amounts"""
        self.subtotal = self.quantity * self.price_per_bird
        self.total_amount = self.subtotal
        
        # Platform commission (from PlatformSettings)
        settings = PlatformSettings.get_settings()
        self.platform_commission = settings.calculate_commission(self.subtotal)
        
        self.paystack_fee = (self.subtotal * Decimal('0.015')) + Decimal('0.10')
        self.farmer_payout = self.subtotal - self.platform_commission
    
    def save(self, *args, **kwargs):
        if not self.subtotal or self.subtotal == 0:
            self.calculate_amounts()
        super().save(*args, **kwargs)


class Payment(models.Model):
    """
    Payment tracking with Paystack integration, retry mechanism, and refund support.
    """
    PAYMENT_METHOD_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partial_refund', 'Partially Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey('farms.Farm', on_delete=models.CASCADE, related_name='payments')
    customer = models.ForeignKey('Customer', on_delete=models.PROTECT, related_name='payments')
    
    # Payment Details
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Paystack Integration
    paystack_reference = models.CharField(max_length=100, unique=True, db_index=True)
    paystack_access_code = models.CharField(max_length=100, blank=True)
    paystack_transaction_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Retry Mechanism
    retry_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_retry_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    # Refund Information
    refund_requested = models.BooleanField(default=False)
    refund_requested_at = models.DateTimeField(null=True, blank=True)
    refund_reason = models.TextField(blank=True)
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    payment_response = models.JSONField(default=dict, blank=True, help_text='Raw Paystack API response')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', '-created_at']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['paystack_reference']),
        ]

    def __str__(self):
        return f"Payment {self.paystack_reference} - GHS {self.amount} - {self.status}"
    
    def is_refund_eligible(self):
        """Check if payment is eligible for refund (from PlatformSettings)"""
        if self.status != 'success':
            return False
        
        settings = PlatformSettings.get_settings()
        eligibility_hours = settings.refund_eligibility_hours
        cutoff_time = timezone.now() - timedelta(hours=eligibility_hours)
        
        return self.created_at >= cutoff_time
    
    def should_auto_refund(self):
        """Check if payment should be auto-refunded (from PlatformSettings)"""
        if self.status != 'failed':
            return False
        
        settings = PlatformSettings.get_settings()
        
        # Check if auto-refunds are enabled
        if not settings.enable_auto_refunds:
            return False
        
        auto_refund_hours = settings.payment_auto_refund_hours
        cutoff_time = timezone.now() - timedelta(hours=auto_refund_hours)
        
        return self.created_at <= cutoff_time


class FarmerPayout(models.Model):
    """
    Farmer payout tracking with Paystack subaccount settlement.
    Tracks money transferred to farmers' mobile money accounts.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey('farms.Farm', on_delete=models.CASCADE, related_name='farmer_payouts')
    
    # Related Sale (polymorphic - either egg or bird sale)
    egg_sale = models.ForeignKey(
        'EggSale',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payouts'
    )
    bird_sale = models.ForeignKey(
        'BirdSale',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payouts'
    )
    
    # Payout Details
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Paystack Subaccount Settlement
    paystack_transfer_code = models.CharField(max_length=100, blank=True, db_index=True)
    paystack_transfer_id = models.CharField(max_length=100, blank=True)
    settlement_date = models.DateTimeField(null=True, blank=True)
    
    # Mobile Money Details
    recipient_mobile_number = models.CharField(max_length=15)
    recipient_name = models.CharField(max_length=200)
    mobile_money_provider = models.CharField(max_length=20)
    
    # Retry Mechanism
    retry_count = models.IntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    # Audit Trail (blockchain-like)
    previous_hash = models.CharField(max_length=64, blank=True)
    current_hash = models.CharField(max_length=64, blank=True, db_index=True)
    
    # Metadata
    payout_response = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Payout to {self.recipient_name} - GHS {self.amount} - {self.status}"
    
    def calculate_hash(self):
        """Calculate cryptographic hash for audit trail"""
        data = {
            'id': str(self.id),
            'farm_id': str(self.farm.id),
            'amount': str(self.amount),
            'recipient': self.recipient_mobile_number,
            'created_at': self.created_at.isoformat() if self.created_at else '',
            'previous_hash': self.previous_hash,
        }
        hash_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def save(self, *args, **kwargs):
        # Calculate hash for audit trail
        if not self.current_hash:
            # Get the previous payout's hash
            last_payout = FarmerPayout.objects.filter(farm=self.farm).order_by('-created_at').first()
            if last_payout:
                self.previous_hash = last_payout.current_hash
            self.current_hash = self.calculate_hash()
        
        super().save(*args, **kwargs)


class FraudAlert(models.Model):
    """
    Fraud detection alerts for potential off-platform sales.
    
    Stores results of automated fraud detection analysis.
    """
    RISK_LEVEL_CHOICES = [
        ('CLEAN', 'Clean (No Issues)'),
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical Risk'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('under_review', 'Under Review'),
        ('false_positive', 'False Positive'),
        ('confirmed', 'Confirmed Fraud'),
        ('resolved', 'Resolved'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey('farms.Farm', on_delete=models.CASCADE, related_name='fraud_alerts')
    
    # Analysis Results
    risk_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Calculated risk score (0-100)'
    )
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, db_index=True)
    
    # Alert Details
    alerts = models.JSONField(
        default=list,
        help_text='List of specific alerts detected'
    )
    analysis_period_days = models.IntegerField(default=30)
    
    # Review Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_fraud_alerts'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Actions Taken
    action_taken = models.TextField(
        blank=True,
        help_text='Actions taken in response to this alert'
    )
    audit_scheduled = models.BooleanField(default=False)
    audit_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    detected_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fraud_alerts'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['farm', '-detected_at']),
            models.Index(fields=['risk_level', 'status']),
            models.Index(fields=['-detected_at']),
        ]
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.risk_level} ({self.risk_score})"
    
    def get_alert_summary(self):
        """Get human-readable summary of alerts"""
        if not self.alerts:
            return "No alerts detected"
        
        summary = []
        for alert in self.alerts:
            summary.append(f"{alert.get('severity', 'UNKNOWN')}: {alert.get('message', 'No message')}")
        
        return "\n".join(summary)
    
    def mark_reviewed(self, user, status, notes=''):
        """Mark alert as reviewed"""
        self.status = status
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes', 'updated_at'])
    
    def schedule_audit(self, audit_date):
        """Schedule physical farm audit"""
        self.audit_scheduled = True
        self.audit_date = audit_date
        self.save(update_fields=['audit_scheduled', 'audit_date', 'updated_at'])
