import uuid
from decimal import Decimal
from datetime import timedelta
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """
    OPTIONAL subscription plans for marketplace & sales features.
    Core farm management is FREE for all farmers.
    Currently: GHS 100/month for marketplace access.
    ALL farmers (government and independent) pay the same price for marketplace features.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(
        help_text="Subscription unlocks PUBLIC MARKETPLACE visibility and sales features"
    )
    
    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text="Monthly subscription fee (GHS)"
    )
    
    # Features
    max_product_images = models.PositiveIntegerField(
        default=20,
        help_text="Maximum product images allowed"
    )
    max_image_size_mb = models.PositiveIntegerField(
        default=5,
        help_text="Maximum size per image (MB)"
    )
    marketplace_listing = models.BooleanField(
        default=True,
        help_text="Can list products on public marketplace"
    )
    sales_tracking = models.BooleanField(
        default=True,
        help_text="Can use sales tracking features"
    )
    analytics_dashboard = models.BooleanField(
        default=True,
        help_text="Access to analytics dashboard"
    )
    api_access = models.BooleanField(
        default=False,
        help_text="API access for third-party integrations"
    )
    
    # Trial Period
    trial_period_days = models.PositiveIntegerField(
        default=14,
        help_text="Free trial period in days (0 = no trial)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_plans'
        ordering = ['display_order', 'price_monthly']
    
    def __str__(self):
        return f"{self.name} - GHS {self.price_monthly}/month"


class Subscription(models.Model):
    """
    OPTIONAL subscription for marketplace & sales features.
    Farmers without subscription can still use core farm management (FREE).
    Only subscribed farms appear on public marketplace.
    ALL farmers (government and independent) pay GHS 100/month for marketplace access.
    """
    STATUS_CHOICES = [
        ('trial', 'Trial Period'),
        ('active', 'Active'),
        ('past_due', 'Past Due (Grace Period)'),
        ('suspended', 'Suspended - Marketplace Hidden'),
        ('cancelled', 'Cancelled - Marketplace Hidden'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    farm = models.OneToOneField(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='subscription',
        null=True,
        blank=True
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='trial',
        db_index=True
    )
    
    # Billing Cycle
    start_date = models.DateField(help_text="Subscription start date")
    current_period_start = models.DateField(help_text="Current billing period start")
    current_period_end = models.DateField(help_text="Current billing period end")
    next_billing_date = models.DateField(help_text="Next payment due date")
    
    # Trial
    trial_start = models.DateField(null=True, blank=True)
    trial_end = models.DateField(null=True, blank=True)
    
    # Payment
    last_payment_date = models.DateField(null=True, blank=True)
    last_payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Grace Period
    grace_period_days = models.PositiveIntegerField(
        default=5,
        help_text="Days after due date before suspension"
    )
    suspension_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date subscription was suspended"
    )
    
    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_subscriptions'
    )
    
    # Reminders
    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last payment reminder sent"
    )
    reminder_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of payment reminders sent"
    )
    
    # Auto-renewal
    auto_renew = models.BooleanField(
        default=True,
        help_text="Automatically renew subscription"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'next_billing_date']),
            models.Index(fields=['farm']),
        ]
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.plan.name} ({self.status})"
    
    @property
    def is_active(self):
        """Check if subscription is active (trial or paid)"""
        return self.status in ['trial', 'active']
    
    @property
    def is_in_grace_period(self):
        """Check if subscription is past due but still in grace period"""
        return self.status == 'past_due'
    
    @property
    def days_until_suspension(self):
        """Days remaining before suspension"""
        if self.status != 'past_due':
            return None
        
        grace_end = self.next_billing_date + timedelta(days=self.grace_period_days)
        delta = grace_end - timezone.now().date()
        return max(0, delta.days)
    
    def suspend(self, reason="Non-payment"):
        """Suspend subscription due to non-payment"""
        self.status = 'suspended'
        self.suspension_date = timezone.now().date()
        self.save()
        
        # TODO: Send suspension notification
        # TODO: Disable farm marketplace listings
    
    def reactivate(self):
        """Reactivate suspended subscription after payment"""
        self.status = 'active'
        self.suspension_date = None
        
        # Extend billing period
        from dateutil.relativedelta import relativedelta
        self.current_period_start = timezone.now().date()
        self.current_period_end = self.current_period_start + relativedelta(months=1)
        self.next_billing_date = self.current_period_end
        
        self.save()
        
        # TODO: Re-enable farm marketplace listings


class SubscriptionPayment(models.Model):
    """
    Record of subscription payments (manual or automated).
    All farmers pay the same price for marketplace access.
    """
    PAYMENT_METHOD_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('card', 'Card Payment'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    payment_reference = models.CharField(
        max_length=200,
        blank=True,
        help_text="Transaction reference/receipt number"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Period Covered
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Payment Gateway (if used)
    gateway_provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="Paystack, Flutterwave, etc."
    )
    gateway_transaction_id = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Verification
    verified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
        help_text="Admin who verified manual payment"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    payment_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'subscription_payments'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['subscription', '-payment_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        method_display = dict(self.PAYMENT_METHOD_CHOICES).get(self.payment_method, self.payment_method)
        return f"Payment GHS {self.amount} - {self.subscription.farm.farm_name} ({method_display})"


class SubscriptionInvoice(models.Model):
    """
    Monthly invoices generated for subscriptions.
    All farmers receive invoices for marketplace subscription payments.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(
        max_length=30,
        unique=True,
        help_text="Format: SUB-INV-YYYY-MM-XXXXX"
    )
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    
    # Invoice Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    
    # Period
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    
    # Dates
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    
    # Payment Link
    payment = models.OneToOneField(
        SubscriptionPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_invoices'
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"{self.invoice_number} - GHS {self.amount}"
