"""
Advertising Models

Phase 1: Curated Partner Offers
- Partner: Advertising partner/company profile
- PartnerOffer: Manually curated offers from agricultural partners
- OfferVariant: A/B testing variants for offers
- OfferInteraction: Track farmer interactions with offers
- AdvertiserLead: Leads from "Advertise With Us" page
- PartnerPayment: Track advertising revenue from partners
- ConversionEvent: Track farmer conversions after clicking offers

Phase 2 (Future): Full self-service ad platform
- Advertiser accounts
- Campaign management
- Targeting rules
- Billing integration
"""

import uuid
import secrets
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class PartnerCategory(models.TextChoices):
    """Categories of advertising partners"""
    FEED_SUPPLIER = 'feed_supplier', 'Feed & Nutrition Supplier'
    EQUIPMENT = 'equipment', 'Equipment & Infrastructure'
    VETERINARY = 'veterinary', 'Veterinary Services'
    CHICKS_SUPPLIER = 'chicks_supplier', 'Day-Old Chicks Supplier'
    FINANCIAL = 'financial', 'Banks & Financial Services'
    INSURANCE = 'insurance', 'Insurance Provider'
    AGGREGATOR = 'aggregator', 'Aggregator / Offtaker'
    TRAINING = 'training', 'Training & Education'
    LOGISTICS = 'logistics', 'Logistics & Delivery'
    OTHER = 'other', 'Other Agricultural Service'


class TargetingCriteria(models.TextChoices):
    """Targeting options for partner offers"""
    ALL_FARMERS = 'all', 'All Farmers'
    BY_REGION = 'region', 'Specific Regions'
    BY_FLOCK_SIZE = 'flock_size', 'By Flock Size'
    BY_EXPERIENCE = 'experience', 'By Experience Level'
    BY_PRODUCTION = 'production', 'By Production Volume'
    MARKETPLACE_ACTIVE = 'marketplace', 'Marketplace Active Farmers'
    GOVERNMENT_FARMERS = 'government', 'Government Program Farmers'


class Partner(models.Model):
    """
    Advertising partner/company profile.
    
    Examples:
    - Olam Ghana (feed supplier)
    - Ecobank (agricultural loans)
    - GLICO (livestock insurance)
    - Veterinary clinics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Company Info
    company_name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=30,
        choices=PartnerCategory.choices,
        default=PartnerCategory.OTHER
    )
    logo = models.ImageField(
        upload_to='partners/logos/',
        null=True,
        blank=True
    )
    website = models.URLField(blank=True)
    description = models.TextField(
        blank=True,
        help_text="Brief description of the partner and their services"
    )
    
    # Contact Info
    contact_name = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    # Status
    is_verified = models.BooleanField(
        default=False,
        help_text="Has this partner been verified by YEA/admin?"
    )
    is_active = models.BooleanField(default=True)
    
    # Contract Info (for tracking)
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    monthly_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monthly advertising fee (GHS)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_partners'
    )
    
    class Meta:
        db_table = 'advertising_partners'
        ordering = ['company_name']
    
    def __str__(self):
        return f"{self.company_name} ({self.get_category_display()})"
    
    @property
    def has_active_contract(self):
        """Check if partner has an active contract"""
        if not self.contract_start_date:
            return False
        today = timezone.now().date()
        if self.contract_end_date:
            return self.contract_start_date <= today <= self.contract_end_date
        return self.contract_start_date <= today


class PartnerOffer(models.Model):
    """
    Curated promotional offer from a partner.
    
    Displayed on farmer dashboards based on targeting criteria.
    Admins create and manage these manually (Phase 1).
    
    Examples:
    - "10% off Starter Feed - Use code YEAPOULTRY"
    - "Agricultural Loan - Up to GHS 50,000 at 12% APR"
    - "Free Vaccination Campaign - Register Now"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='offers'
    )
    
    # Offer Content
    title = models.CharField(
        max_length=100,
        help_text="Short, attention-grabbing title"
    )
    description = models.TextField(
        help_text="Detailed offer description"
    )
    offer_type = models.CharField(
        max_length=30,
        choices=[
            ('discount', 'Discount / Promo Code'),
            ('loan', 'Loan / Financing'),
            ('insurance', 'Insurance Product'),
            ('service', 'Service Offering'),
            ('product', 'Product Promotion'),
            ('event', 'Event / Training'),
            ('bulk_purchase', 'Bulk Purchase Deal'),
        ],
        default='product'
    )
    
    # Visual
    image = models.ImageField(
        upload_to='partners/offers/',
        null=True,
        blank=True,
        help_text="Banner image (recommended: 600x300px)"
    )
    
    # Call to Action
    cta_text = models.CharField(
        max_length=50,
        default="Learn More",
        help_text="Button text (e.g., 'Get Quote', 'Apply Now', 'Shop Now')"
    )
    cta_url = models.URLField(
        blank=True,
        help_text="Link when farmer clicks the offer"
    )
    promo_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Promo/discount code if applicable"
    )
    
    # Targeting
    targeting = models.CharField(
        max_length=30,
        choices=TargetingCriteria.choices,
        default=TargetingCriteria.ALL_FARMERS
    )
    target_regions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of regions to target (if targeting=region)"
    )
    min_flock_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minimum flock size to show offer (if targeting=flock_size)"
    )
    max_flock_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum flock size to show offer"
    )
    
    # Scheduling
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Leave blank for indefinite"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured offers appear more prominently"
    )
    priority = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Higher priority = shown first (1-100)"
    )
    
    # Analytics (updated by background tasks)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    
    # Frequency Capping (Phase 2 Feature)
    max_impressions_per_user = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum times this offer is shown to a single farmer (null = unlimited)"
    )
    max_impressions_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum total impressions per day across all farmers (null = unlimited)"
    )
    cooldown_hours = models.PositiveIntegerField(
        default=0,
        help_text="Hours to wait before showing offer again to same farmer after click/dismiss"
    )
    
    # Scheduling (Enhanced Phase 2)
    show_on_days = models.JSONField(
        default=list,
        blank=True,
        help_text="Days of week to show (0=Monday, 6=Sunday). Empty = all days"
    )
    show_start_hour = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(23)],
        help_text="Start hour to show offer (0-23, Ghana time)"
    )
    show_end_hour = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(23)],
        help_text="End hour to show offer (0-23, Ghana time)"
    )
    
    # Budget Controls (Phase 2)
    daily_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Daily budget limit for CPC campaigns (GHS)"
    )
    daily_spend = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current day's spend (reset daily)"
    )
    cost_per_click = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost per click for CPC campaigns (GHS)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_offers'
    )
    
    class Meta:
        db_table = 'partner_offers'
        ordering = ['-is_featured', '-priority', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'start_date', 'end_date']),
            models.Index(fields=['targeting']),
            models.Index(fields=['partner']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.partner.company_name}"
    
    @property
    def is_currently_active(self):
        """Check if offer is active and within date range"""
        if not self.is_active:
            return False
        now = timezone.now()
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True
    
    @property
    def click_through_rate(self):
        """Calculate CTR as percentage"""
        if self.impressions == 0:
            return Decimal('0.00')
        return Decimal(self.clicks / self.impressions * 100).quantize(Decimal('0.01'))
    
    def record_impression(self):
        """Increment impression count (call when offer is shown)"""
        PartnerOffer.objects.filter(pk=self.pk).update(
            impressions=models.F('impressions') + 1
        )
    
    def record_click(self):
        """Increment click count (call when farmer clicks offer)"""
        PartnerOffer.objects.filter(pk=self.pk).update(
            clicks=models.F('clicks') + 1
        )
        # Track CPC spending
        if self.cost_per_click:
            PartnerOffer.objects.filter(pk=self.pk).update(
                daily_spend=models.F('daily_spend') + self.cost_per_click
            )
    
    def is_within_schedule(self):
        """Check if current time is within offer's display schedule"""
        now = timezone.now()
        
        # Check day of week (0=Monday, 6=Sunday)
        if self.show_on_days:
            if now.weekday() not in self.show_on_days:
                return False
        
        # Check hour of day (Ghana time)
        if self.show_start_hour is not None and self.show_end_hour is not None:
            current_hour = now.hour
            if self.show_start_hour <= self.show_end_hour:
                # Normal range (e.g., 9-17)
                if not (self.show_start_hour <= current_hour < self.show_end_hour):
                    return False
            else:
                # Overnight range (e.g., 22-6)
                if not (current_hour >= self.show_start_hour or current_hour < self.show_end_hour):
                    return False
        
        return True
    
    def is_within_budget(self):
        """Check if offer is within daily budget (for CPC campaigns)"""
        if self.daily_budget is None:
            return True
        return self.daily_spend < self.daily_budget
    
    def can_show_to_farm(self, farm):
        """
        Check if offer can be shown to a specific farm based on frequency capping.
        
        Returns: (can_show: bool, reason: str or None)
        """
        from datetime import timedelta
        
        # Check frequency cap
        if self.max_impressions_per_user:
            impression_count = OfferInteraction.objects.filter(
                offer=self,
                farm=farm,
                interaction_type='impression'
            ).count()
            
            if impression_count >= self.max_impressions_per_user:
                return False, 'max_impressions_reached'
        
        # Check cooldown after click/dismiss
        if self.cooldown_hours > 0:
            cooldown_cutoff = timezone.now() - timedelta(hours=self.cooldown_hours)
            recent_engagement = OfferInteraction.objects.filter(
                offer=self,
                farm=farm,
                interaction_type__in=['click', 'dismiss'],
                created_at__gte=cooldown_cutoff
            ).exists()
            
            if recent_engagement:
                return False, 'in_cooldown'
        
        return True, None
    
    def get_daily_impressions_today(self):
        """Get total impressions for today"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return OfferInteraction.objects.filter(
            offer=self,
            interaction_type='impression',
            created_at__gte=today_start
        ).count()


class OfferInteraction(models.Model):
    """
    Track individual farmer interactions with offers.
    
    Useful for:
    - Preventing repeated impressions counting
    - Analytics on which farmers engage
    - Partner reporting
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    offer = models.ForeignKey(
        PartnerOffer,
        on_delete=models.CASCADE,
        related_name='interactions'
    )
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='offer_interactions'
    )
    
    # Interaction type
    interaction_type = models.CharField(
        max_length=20,
        choices=[
            ('impression', 'Viewed'),
            ('click', 'Clicked'),
            ('dismissed', 'Dismissed'),
            ('converted', 'Converted (Completed Action)'),
        ]
    )
    
    # Context
    source_page = models.CharField(
        max_length=50,
        blank=True,
        help_text="Where the offer was shown (dashboard, marketplace, etc.)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'offer_interactions'
        indexes = [
            models.Index(fields=['offer', 'farm']),
            models.Index(fields=['created_at']),
        ]


class AdvertiserLead(models.Model):
    """
    Leads captured from "Advertise With Us" page.
    
    When a business wants to advertise on the platform,
    they fill out a form which creates this lead.
    Admin follows up manually (Phase 1).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Company Info
    company_name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=30,
        choices=PartnerCategory.choices,
        default=PartnerCategory.OTHER
    )
    website = models.URLField(blank=True)
    
    # Contact Info
    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    job_title = models.CharField(max_length=100, blank=True)
    
    # Interest
    advertising_interest = models.TextField(
        help_text="What products/services they want to advertise"
    )
    target_audience = models.TextField(
        blank=True,
        help_text="What type of farmers they want to reach"
    )
    budget_range = models.CharField(
        max_length=30,
        choices=[
            ('under_500', 'Under GHS 500/month'),
            ('500_2000', 'GHS 500 - 2,000/month'),
            ('2000_5000', 'GHS 2,000 - 5,000/month'),
            ('over_5000', 'Over GHS 5,000/month'),
            ('not_sure', 'Not Sure Yet'),
        ],
        default='not_sure'
    )
    
    # Lead Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New Lead'),
            ('contacted', 'Contacted'),
            ('meeting_scheduled', 'Meeting Scheduled'),
            ('proposal_sent', 'Proposal Sent'),
            ('negotiating', 'Negotiating'),
            ('converted', 'Converted to Partner'),
            ('declined', 'Declined'),
            ('lost', 'Lost'),
        ],
        default='new'
    )
    
    # Notes
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes about this lead"
    )
    
    # Follow-up
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads'
    )
    follow_up_date = models.DateField(null=True, blank=True)
    
    # Converted Partner (if applicable)
    converted_partner = models.ForeignKey(
        Partner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_leads'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'advertiser_leads'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company_name} - {self.contact_name} ({self.get_status_display()})"


class OfferVariant(models.Model):
    """
    A/B testing variants for partner offers.
    
    Allows testing different creatives, CTAs, or messaging
    to optimize conversion rates.
    
    Example:
    - Variant A: "Get 10% Off" with green button
    - Variant B: "Save GHS 50" with orange button
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    offer = models.ForeignKey(
        PartnerOffer,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    
    # Variant identification
    name = models.CharField(
        max_length=50,
        help_text="e.g., 'Control', 'Variant A', 'Green CTA'"
    )
    
    # Variant-specific content (overrides offer defaults)
    title = models.CharField(
        max_length=100,
        blank=True,
        help_text="Leave blank to use offer's title"
    )
    description = models.TextField(
        blank=True,
        help_text="Leave blank to use offer's description"
    )
    image = models.ImageField(
        upload_to='partners/offers/variants/',
        null=True,
        blank=True
    )
    cta_text = models.CharField(
        max_length=50,
        blank=True,
        help_text="Leave blank to use offer's CTA"
    )
    
    # Traffic allocation (percentage)
    traffic_percentage = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of traffic to receive this variant (0-100)"
    )
    
    # Variant-specific analytics
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_winner = models.BooleanField(
        default=False,
        help_text="Marked as winning variant after test completion"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'offer_variants'
        ordering = ['-traffic_percentage', 'name']
        unique_together = [['offer', 'name']]
    
    def __str__(self):
        return f"{self.offer.title} - {self.name}"
    
    @property
    def click_through_rate(self):
        """Calculate CTR as percentage"""
        if self.impressions == 0:
            return Decimal('0.00')
        return Decimal(self.clicks / self.impressions * 100).quantize(Decimal('0.01'))
    
    @property
    def conversion_rate(self):
        """Calculate conversion rate as percentage"""
        if self.clicks == 0:
            return Decimal('0.00')
        return Decimal(self.conversions / self.clicks * 100).quantize(Decimal('0.01'))
    
    def get_display_title(self):
        """Get title to display (variant or fallback to offer)"""
        return self.title or self.offer.title
    
    def get_display_description(self):
        """Get description to display (variant or fallback to offer)"""
        return self.description or self.offer.description
    
    def get_display_cta(self):
        """Get CTA text to display (variant or fallback to offer)"""
        return self.cta_text or self.offer.cta_text
    
    def get_display_image(self):
        """Get image to display (variant or fallback to offer)"""
        return self.image or self.offer.image


class ConversionEvent(models.Model):
    """
    Track conversion events when farmers complete actions after clicking offers.
    
    A conversion can be:
    - Signing up with a partner
    - Making a purchase using promo code
    - Completing a loan application
    - Registering for an event
    
    Partners can send conversion data via webhook or admin can log manually.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    offer = models.ForeignKey(
        PartnerOffer,
        on_delete=models.CASCADE,
        related_name='conversions'
    )
    variant = models.ForeignKey(
        OfferVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversion_events'
    )
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ad_conversions',
        help_text="Farm associated with conversion (may be null for unattributed conversions)"
    )
    
    # Conversion details
    conversion_type = models.CharField(
        max_length=30,
        choices=[
            ('signup', 'Partner Sign Up'),
            ('purchase', 'Purchase Made'),
            ('application', 'Application Submitted'),
            ('registration', 'Event Registration'),
            ('quote_request', 'Quote Requested'),
            ('contact', 'Contact Form Submitted'),
            ('download', 'Resource Downloaded'),
            ('other', 'Other Conversion'),
        ]
    )
    
    # Value tracking
    conversion_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Value of conversion in GHS (if applicable)"
    )
    
    # Tracking
    promo_code_used = models.CharField(
        max_length=50,
        blank=True,
        help_text="Promo code used in conversion"
    )
    external_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="External transaction/reference ID from partner"
    )
    
    # Attribution
    click_interaction = models.ForeignKey(
        OfferInteraction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversions',
        help_text="The click that led to this conversion"
    )
    attribution_window_hours = models.PositiveIntegerField(
        default=168,  # 7 days
        help_text="Hours between click and conversion"
    )
    
    # Source
    source = models.CharField(
        max_length=30,
        choices=[
            ('webhook', 'Partner Webhook'),
            ('manual', 'Manual Entry'),
            ('api', 'Partner API'),
            ('promo_code', 'Promo Code Redemption'),
        ],
        default='manual'
    )
    
    # Verification
    is_verified = models.BooleanField(
        default=False,
        help_text="Has this conversion been verified?"
    )
    verified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_conversions'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'conversion_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['offer', 'created_at']),
            models.Index(fields=['farm', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_conversion_type_display()} - {self.offer.title}"


class PartnerPayment(models.Model):
    """
    Track advertising payments received from partners.
    
    This is the revenue side of the advertising system:
    - Monthly advertising fees
    - Campaign payments
    - Performance bonuses
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='GHS')
    
    payment_type = models.CharField(
        max_length=30,
        choices=[
            ('monthly_fee', 'Monthly Advertising Fee'),
            ('campaign_fee', 'Campaign Fee'),
            ('setup_fee', 'Setup/Onboarding Fee'),
            ('performance_bonus', 'Performance Bonus'),
            ('renewal', 'Contract Renewal'),
            ('one_time', 'One-Time Payment'),
            ('other', 'Other'),
        ],
        default='monthly_fee'
    )
    
    # Period (for recurring payments)
    period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Start of billing period"
    )
    period_end = models.DateField(
        null=True,
        blank=True,
        help_text="End of billing period"
    )
    
    # Payment status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
            ('cancelled', 'Cancelled'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )
    
    # Payment method
    payment_method = models.CharField(
        max_length=30,
        choices=[
            ('bank_transfer', 'Bank Transfer'),
            ('mobile_money', 'Mobile Money'),
            ('cheque', 'Cheque'),
            ('cash', 'Cash'),
            ('online', 'Online Payment'),
        ],
        default='bank_transfer'
    )
    
    # Transaction info
    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Bank/payment reference"
    )
    invoice_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Invoice number"
    )
    
    # Dates
    invoice_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Recorded by
    recorded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_ad_payments'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'partner_payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['partner', 'status']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['paid_at']),
        ]
    
    def __str__(self):
        return f"{self.partner.company_name} - {self.amount} {self.currency} ({self.get_status_display()})"
    
    def mark_as_paid(self, user=None, reference=None):
        """Mark payment as paid"""
        self.status = 'paid'
        self.paid_at = timezone.now()
        if reference:
            self.transaction_reference = reference
        self.save(update_fields=['status', 'paid_at', 'transaction_reference', 'updated_at'])


class ConversionWebhookKey(models.Model):
    """
    API keys for partners to send conversion data via webhook.
    
    Each partner gets a unique webhook key to authenticate
    their conversion tracking requests.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    partner = models.OneToOneField(
        Partner,
        on_delete=models.CASCADE,
        related_name='webhook_key'
    )
    
    api_key = models.CharField(
        max_length=64,
        unique=True,
        editable=False
    )
    
    is_active = models.BooleanField(default=True)
    
    # Rate limiting
    daily_limit = models.PositiveIntegerField(
        default=1000,
        help_text="Maximum conversions per day"
    )
    
    # Tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    total_requests = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversion_webhook_keys'
    
    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Webhook Key - {self.partner.company_name}"
    
    def regenerate_key(self):
        """Generate a new API key"""
        self.api_key = secrets.token_urlsafe(48)
        self.save(update_fields=['api_key', 'updated_at'])
        return self.api_key
