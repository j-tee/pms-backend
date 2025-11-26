import uuid
from decimal import Decimal
from datetime import timedelta
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class GovernmentSubsidyProgram(models.Model):
    """
    Government subsidy programs (YEA) that provide 100% marketplace subscription coverage.
    Government-registered farmers get FREE marketplace access through these programs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Program Details
    program_name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Name of the government program (e.g., 'YEA Poultry Module 2025')"
    )
    program_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Short code for the program (e.g., 'YEA-2025')"
    )
    description = models.TextField(help_text="Program description and objectives")
    
    # Program Period
    start_date = models.DateField(help_text="Program start date")
    end_date = models.DateField(help_text="Program end date")
    
    # Subsidy Details
    subsidy_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Percentage of subscription cost covered (100% for government programs)"
    )
    max_farmers = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of farmers covered by program (null = unlimited)"
    )
    current_farmers_count = models.PositiveIntegerField(
        default=0,
        help_text="Current number of farmers enrolled"
    )
    
    # Administering Organization
    implementing_agency = models.CharField(
        max_length=200,
        help_text="Agency implementing the program (e.g., 'Ministry of Youth and Sports')"
    )
    contact_person = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether program is currently accepting new farmers"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'government_subsidy_programs'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['is_active', 'start_date']),
            models.Index(fields=['program_code']),
        ]
    
    def __str__(self):
        return f"{self.program_name} ({self.program_code})"
    
    @property
    def is_currently_active(self):
        """Check if program is within active date range"""
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date
    
    @property
    def has_capacity(self):
        """Check if program can accept more farmers"""
        if self.max_farmers is None:
            return True
        return self.current_farmers_count < self.max_farmers
    
    def can_enroll_farmer(self):
        """Check if program can currently enroll new farmers"""
        return self.is_currently_active and self.has_capacity


class SubscriptionPlan(models.Model):
    """
    OPTIONAL subscription plans for marketplace & sales features.
    Core farm management is FREE for all farmers.
    Currently: GHS 100/month for marketplace access.
    Government farmers get this subsidized through GovernmentSubsidyProgram.
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
    Government farmers have is_subsidized=True with subsidy_program FK.
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
    
    # Government Subsidy Support
    is_subsidized = models.BooleanField(
        default=False,
        help_text="True if subscription cost is subsidized by government program"
    )
    subsidy_program = models.ForeignKey(
        GovernmentSubsidyProgram,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subsidized_subscriptions',
        help_text="Government program covering subscription costs"
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
            models.Index(fields=['is_subsidized']),
            models.Index(fields=['subsidy_program']),
        ]
    
    def __str__(self):
        subsidy_tag = " [GOVERNMENT SUBSIDIZED]" if self.is_subsidized else ""
        return f"{self.farm.farm_name} - {self.plan.name} ({self.status}){subsidy_tag}"
    
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
    
    @property
    def requires_payment(self):
        """Check if subscription requires farmer to make payment (not subsidized)"""
        return not self.is_subsidized
    
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
    Government-subsidized subscriptions don't require farmer payments.
    """
    PAYMENT_METHOD_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('card', 'Card Payment'),
        ('government_subsidy', 'Government Subsidy (No Farmer Payment)'),
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
    Government-subsidized subscriptions generate invoices but marked as PAID automatically.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
        ('government_covered', 'Government Subsidy - No Payment Required'),
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
        subsidy_tag = " [GOVERNMENT]" if self.status == 'government_covered' else ""
        return f"{self.invoice_number} - GHS {self.amount}{subsidy_tag}"
