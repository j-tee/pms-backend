"""
Advertising Models

Phase 1: Curated Partner Offers
- PartnerOffer: Manually curated offers from agricultural partners
- AdvertiserLead: Leads from "Advertise With Us" page

Phase 2 (Future): Full self-service ad platform
- Advertiser accounts
- Campaign management
- Targeting rules
- Billing integration
"""

import uuid
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
