"""
Institutional Data Subscription Models

B2B API access for banks, insurers, agribusinesses, and other institutions
that want to access aggregated/anonymized poultry sector data.

Use Cases:
- Banks: Farm creditworthiness, production history for loan decisions
- Insurers: Flock size, mortality rates for livestock insurance pricing
- Agribusinesses: Market demand, regional production volumes
- Feed Companies: Flock sizes by region for sales targeting
- NGOs/Researchers: Anonymized sector trends, food security data
"""

import uuid
import secrets
import hashlib
from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class InstitutionalPlan(models.Model):
    """
    Subscription tiers for institutional data access.
    Different tiers offer different data access levels and API quotas.
    """
    TIER_CHOICES = [
        ('basic', 'Basic - Aggregated Regional Data'),
        ('professional', 'Professional - Detailed Analytics'),
        ('enterprise', 'Enterprise - Full API Access'),
        ('research', 'Research/NGO - Academic Access'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, unique=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    description = models.TextField()
    
    # Pricing (Monthly)
    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Monthly subscription fee (GHS)"
    )
    
    # Annual discount
    price_annually = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Annual subscription fee (GHS) - typically discounted"
    )
    
    # API Quotas
    requests_per_day = models.PositiveIntegerField(
        default=100,
        help_text="Maximum API requests per day"
    )
    requests_per_month = models.PositiveIntegerField(
        default=3000,
        help_text="Maximum API requests per month"
    )
    
    # Data Access Levels
    access_regional_aggregates = models.BooleanField(
        default=True,
        help_text="Access to regional production aggregates"
    )
    access_constituency_data = models.BooleanField(
        default=False,
        help_text="Access to constituency-level breakdown"
    )
    access_production_trends = models.BooleanField(
        default=True,
        help_text="Access to historical production trends"
    )
    access_market_prices = models.BooleanField(
        default=True,
        help_text="Access to average market prices"
    )
    access_mortality_data = models.BooleanField(
        default=False,
        help_text="Access to mortality/health statistics"
    )
    access_supply_forecasts = models.BooleanField(
        default=False,
        help_text="Access to supply forecasting models"
    )
    access_individual_farm_data = models.BooleanField(
        default=False,
        help_text="Access to anonymized individual farm performance (Enterprise only)"
    )
    
    # Data Export
    max_export_records = models.PositiveIntegerField(
        default=1000,
        help_text="Maximum records per export request"
    )
    export_formats = ArrayField(
        models.CharField(max_length=10),
        default=list,
        help_text="Allowed export formats: json, csv, excel"
    )
    
    # Support
    support_level = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email Support'),
            ('priority', 'Priority Email Support'),
            ('dedicated', 'Dedicated Account Manager'),
        ],
        default='email'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'institutional_plans'
        ordering = ['display_order', 'price_monthly']
    
    def __str__(self):
        return f"{self.name} - GHS {self.price_monthly}/month"


class InstitutionalSubscriber(models.Model):
    """
    Institutional customers (B2B) subscribed to data access.
    """
    CATEGORY_CHOICES = [
        ('bank', 'Bank / Financial Institution'),
        ('microfinance', 'Microfinance Institution'),
        ('insurance', 'Insurance Provider'),
        ('agribusiness', 'Agribusiness / Aggregator'),
        ('feed_company', 'Feed / Input Supplier'),
        ('processor', 'Food Processor'),
        ('ngo', 'NGO / Development Organization'),
        ('research', 'Research Institution'),
        ('government', 'Government Agency'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('trial', 'Trial Period'),
        ('active', 'Active'),
        ('past_due', 'Payment Past Due'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Organization Details
    organization_name = models.CharField(max_length=200)
    organization_category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )
    registration_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Company registration number"
    )
    website = models.URLField(blank=True)
    
    # Primary Contact
    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    contact_position = models.CharField(max_length=100, blank=True)
    
    # Technical Contact (for API issues)
    tech_contact_name = models.CharField(max_length=100, blank=True)
    tech_contact_email = models.EmailField(blank=True)
    
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    
    # Subscription
    plan = models.ForeignKey(
        InstitutionalPlan,
        on_delete=models.PROTECT,
        related_name='subscribers'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=[('monthly', 'Monthly'), ('annually', 'Annually')],
        default='monthly'
    )
    
    # Billing Dates
    subscription_start = models.DateField(null=True, blank=True)
    current_period_start = models.DateField(null=True, blank=True)
    current_period_end = models.DateField(null=True, blank=True)
    next_billing_date = models.DateField(null=True, blank=True)
    
    # Trial
    trial_start = models.DateField(null=True, blank=True)
    trial_end = models.DateField(null=True, blank=True)
    trial_days = models.PositiveIntegerField(
        default=14,
        help_text="Trial period in days"
    )
    
    # Data Access Preferences
    preferred_regions = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="Regions of interest (empty = all regions)"
    )
    data_use_purpose = models.TextField(
        help_text="Description of intended data use"
    )
    
    # Verification
    is_verified = models.BooleanField(
        default=False,
        help_text="Organization verified by YEA admin"
    )
    verified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_institutions'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes (not visible to subscriber)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'institutional_subscribers'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.organization_name} ({self.get_organization_category_display()})"
    
    @property
    def is_active(self):
        """Check if subscription is active"""
        return self.status in ['trial', 'active']
    
    def start_trial(self):
        """Start trial period"""
        self.status = 'trial'
        self.trial_start = timezone.now().date()
        self.trial_end = self.trial_start + timedelta(days=self.trial_days)
        self.save()
    
    def activate(self):
        """Activate subscription after payment"""
        from dateutil.relativedelta import relativedelta
        
        today = timezone.now().date()
        self.status = 'active'
        self.subscription_start = self.subscription_start or today
        self.current_period_start = today
        
        if self.billing_cycle == 'monthly':
            self.current_period_end = today + relativedelta(months=1)
        else:
            self.current_period_end = today + relativedelta(years=1)
        
        self.next_billing_date = self.current_period_end
        self.save()


class InstitutionalAPIKey(models.Model):
    """
    API keys for institutional subscribers.
    Each subscriber can have multiple API keys (e.g., production, staging).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    subscriber = models.ForeignKey(
        InstitutionalSubscriber,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Key name (e.g., 'Production', 'Development')"
    )
    
    # Key Storage (hashed)
    key_prefix = models.CharField(
        max_length=8,
        help_text="First 8 chars for identification"
    )
    key_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of the full key"
    )
    
    # Permissions
    is_active = models.BooleanField(default=True)
    is_readonly = models.BooleanField(
        default=True,
        help_text="Read-only access (always True for now)"
    )
    
    # IP Restrictions (optional)
    allowed_ips = ArrayField(
        models.GenericIPAddressField(),
        default=list,
        blank=True,
        help_text="Whitelisted IP addresses (empty = all allowed)"
    )
    
    # Usage Tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    total_requests = models.PositiveIntegerField(default=0)
    
    # Expiration
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Key expiration date (null = never expires)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_institutional_keys'
    )
    
    class Meta:
        db_table = 'institutional_api_keys'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subscriber.organization_name} - {self.name} ({self.key_prefix}...)"
    
    @classmethod
    def generate_key(cls, subscriber, name, created_by=None, expires_at=None):
        """
        Generate a new API key for a subscriber.
        Returns the full key (only shown once during creation).
        """
        # Generate a secure random key
        full_key = f"yea_{secrets.token_urlsafe(32)}"
        key_prefix = full_key[:8]
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        api_key = cls.objects.create(
            subscriber=subscriber,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            created_by=created_by,
            expires_at=expires_at
        )
        
        # Return full key (this is the only time it's available)
        return api_key, full_key
    
    @classmethod
    def verify_key(cls, full_key):
        """
        Verify an API key and return the associated subscriber.
        Returns (api_key, subscriber) or (None, None) if invalid.
        """
        if not full_key or not full_key.startswith('yea_'):
            return None, None
        
        key_prefix = full_key[:8]
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        try:
            api_key = cls.objects.select_related(
                'subscriber', 'subscriber__plan'
            ).get(
                key_prefix=key_prefix,
                key_hash=key_hash,
                is_active=True
            )
            
            # Check expiration
            if api_key.expires_at and api_key.expires_at < timezone.now():
                return None, None
            
            # Check subscriber status
            if not api_key.subscriber.is_active:
                return None, None
            
            return api_key, api_key.subscriber
            
        except cls.DoesNotExist:
            return None, None
    
    def record_usage(self, ip_address=None):
        """Record API key usage"""
        self.last_used_at = timezone.now()
        self.last_used_ip = ip_address
        self.total_requests += 1
        self.save(update_fields=['last_used_at', 'last_used_ip', 'total_requests'])


class InstitutionalAPIUsage(models.Model):
    """
    Detailed API usage tracking for billing and rate limiting.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    subscriber = models.ForeignKey(
        InstitutionalSubscriber,
        on_delete=models.CASCADE,
        related_name='api_usage_records'
    )
    api_key = models.ForeignKey(
        InstitutionalAPIKey,
        on_delete=models.SET_NULL,
        null=True,
        related_name='usage_records'
    )
    
    # Request Details
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10, default='GET')
    status_code = models.PositiveIntegerField()
    response_time_ms = models.PositiveIntegerField(
        help_text="Response time in milliseconds"
    )
    
    # Request Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    # Date for aggregation
    date = models.DateField(db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'institutional_api_usage'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['subscriber', 'date']),
            models.Index(fields=['api_key', 'date']),
            models.Index(fields=['endpoint', 'date']),
        ]
    
    def __str__(self):
        return f"{self.subscriber.organization_name} - {self.endpoint} ({self.timestamp})"


class InstitutionalPayment(models.Model):
    """
    Payment records for institutional subscriptions.
    
    Supports multiple payment methods:
    - Mobile Money via Paystack (MTN, Vodafone, AirtelTigo, Telecel)
    - Bank Transfer
    - Cheque
    - Invoice (Net 30 for enterprise customers)
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('paystack', 'Paystack Online'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('invoice', 'Invoice (Net 30)'),
    ]
    
    MOMO_PROVIDER_CHOICES = [
        ('mtn', 'MTN Mobile Money'),
        ('vodafone', 'Vodafone Cash'),
        ('airteltigo', 'AirtelTigo Money'),
        ('telecel', 'Telecel Cash'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    subscriber = models.ForeignKey(
        InstitutionalSubscriber,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment Details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='GHS')
    
    # Period covered
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Payment Info
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique payment reference (format: INST-YYYYMMDD-XXXXXXXX)"
    )
    paystack_reference = models.CharField(max_length=100, blank=True)
    
    # Mobile Money Details
    momo_phone = models.CharField(
        max_length=15,
        blank=True,
        help_text="Mobile money phone number used for payment"
    )
    momo_provider = models.CharField(
        max_length=20,
        choices=MOMO_PROVIDER_CHOICES,
        blank=True,
        help_text="Mobile money provider"
    )
    
    # Payment Gateway Details (Paystack)
    gateway_provider = models.CharField(
        max_length=50,
        default='paystack',
        blank=True,
        help_text="Payment gateway provider"
    )
    gateway_transaction_id = models.CharField(
        max_length=200,
        blank=True,
        db_index=True
    )
    gateway_access_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="Paystack access code for authorization"
    )
    gateway_authorization_url = models.URLField(
        blank=True,
        help_text="URL for payment authorization (if applicable)"
    )
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full gateway response for debugging"
    )
    gateway_fees = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Payment gateway fees (pesewas converted to GHS)"
    )
    failure_reason = models.TextField(
        blank=True,
        help_text="Reason for payment failure"
    )
    
    # Invoice (optional for MoMo payments, required for invoice method)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    invoice_date = models.DateField(null=True, blank=True)
    invoice_due_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Admin
    recorded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_institutional_payments'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'institutional_payments'
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"{self.subscriber.organization_name} - {self.invoice_number}"
    
    def generate_invoice_number(self):
        """Generate unique invoice number"""
        year = timezone.now().year
        count = InstitutionalPayment.objects.filter(
            invoice_date__year=year
        ).count() + 1
        self.invoice_number = f"INV-{year}-{count:04d}"
        return self.invoice_number
    
    @classmethod
    def generate_reference(cls) -> str:
        """
        Generate unique payment reference
        Format: INST-YYYYMMDD-XXXXXXXX
        """
        date_str = timezone.now().strftime('%Y%m%d')
        random_part = secrets.token_hex(4).upper()
        return f"INST-{date_str}-{random_part}"
    
    def mark_as_completed(self, gateway_response: dict = None):
        """
        Mark payment as completed and activate subscriber
        """
        from dateutil.relativedelta import relativedelta
        
        self.payment_status = 'completed'
        self.paid_at = timezone.now()
        if gateway_response:
            self.gateway_response = gateway_response
            if 'id' in gateway_response:
                self.gateway_transaction_id = str(gateway_response['id'])
            if 'fees' in gateway_response:
                # Convert pesewas to GHS
                self.gateway_fees = Decimal(gateway_response['fees']) / 100
        
        self.save()
        
        # Activate subscriber and extend subscription period
        subscriber = self.subscriber
        subscriber.status = 'active'
        subscriber.current_period_start = self.period_start
        subscriber.current_period_end = self.period_end
        subscriber.save(update_fields=['status', 'current_period_start', 'current_period_end'])
    
    def mark_as_failed(self, reason: str = None, gateway_response: dict = None):
        """Mark payment as failed"""
        self.payment_status = 'failed'
        if reason:
            self.failure_reason = reason
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()


class InstitutionalInquiry(models.Model):
    """
    Inquiries from potential institutional subscribers.
    Captured from the public "Data Subscriptions" landing page.
    """
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('demo_scheduled', 'Demo Scheduled'),
        ('converted', 'Converted to Subscriber'),
        ('declined', 'Declined'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Organization
    organization_name = models.CharField(max_length=200)
    organization_category = models.CharField(
        max_length=20,
        choices=InstitutionalSubscriber.CATEGORY_CHOICES
    )
    website = models.URLField(blank=True)
    
    # Contact
    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    contact_position = models.CharField(max_length=100, blank=True)
    
    # Interest
    interested_plan = models.ForeignKey(
        InstitutionalPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inquiries'
    )
    data_use_purpose = models.TextField(
        help_text="How they plan to use the data"
    )
    message = models.TextField(blank=True)
    
    # Lead Source
    source = models.CharField(
        max_length=50,
        blank=True,
        help_text="How they found us (referral, website, etc.)"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    
    # Follow-up
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_institutional_inquiries'
    )
    follow_up_notes = models.TextField(blank=True)
    next_follow_up = models.DateField(null=True, blank=True)
    
    # Conversion
    converted_subscriber = models.OneToOneField(
        InstitutionalSubscriber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_inquiry'
    )
    converted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'institutional_inquiries'
        verbose_name_plural = 'Institutional Inquiries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contact_email', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.organization_name} - {self.contact_name}"
    
    @classmethod
    def check_recent_inquiry(cls, email, days=7):
        """
        Check if email has submitted inquiry within specified days.
        Used for duplicate prevention.
        
        Returns:
            tuple: (has_recent_inquiry: bool, days_remaining: int)
        """
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        
        recent_inquiry = cls.objects.filter(
            contact_email__iexact=email,
            created_at__gte=cutoff_date
        ).order_by('-created_at').first()
        
        if recent_inquiry:
            days_since = (timezone.now() - recent_inquiry.created_at).days
            days_remaining = days - days_since
            return True, max(0, days_remaining)
        
        return False, 0
