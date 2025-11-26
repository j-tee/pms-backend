# Dual Farmer Onboarding Strategy

**Date**: November 26, 2025  
**Change Type**: 🔴 **CRITICAL DESIGN DECISION**  
**Impact**: Affects registration, approval workflow, subscription model, and feature access

---

## 📋 Executive Summary

The platform will serve **TWO DISTINCT FARMER TYPES**:

### Type A: YEA Government Initiative Farmers 🏛️
- **Origin**: Brought online as part of government agricultural program
- **Characteristics**: Often new/small-scale, government-supported
- **Onboarding**: Via extension officers, requires multi-level approval
- **Core Platform**: FREE farm management (always accessible)
- **Marketplace**: Government-subsidized (100%) if farmer wants public visibility
- **Support**: High-touch support from extension officers
- **Procurement**: Priority access to government bulk orders

### Type B: Independent/Established Farmers 💼
- **Origin**: Self-registered, already operating farms
- **Characteristics**: Established operations, commercial farmers
- **Onboarding**: Self-service registration, minimal approval
- **Core Platform**: FREE farm management (always accessible)
- **Marketplace**: OPTIONAL GHS 100/month for public visibility & sales
- **Support**: Self-service with optional premium support
- **Procurement**: Can bid on government orders if meet requirements

---

## 🎯 Key Design Implications

### 1. Registration Source Tracking
```python
# NEW FIELD: registration_source
Farm.registration_source = [
    'government_initiative',  # YEA program farmer
    'self_registered',        # Independent farmer
    'migrated',              # Imported from external system
]
```

### 2. Approval Workflow Differentiation
- **Government Farmers**: Full 3-tier approval (Constituency → Regional → National)
- **Independent Farmers**: Simplified approval (Basic verification → Auto-approve or single review)

### 3. Subscription Model (OPTIONAL - For Marketplace Only)
- **Core Farm Management**: FREE for ALL farmers (both types)
- **Marketplace Features**: OPTIONAL GHS 100/month
- **Government Farmers**: 100% subsidized marketplace access during program
- **Independent Farmers**: Self-pay GHS 100/month if they want marketplace visibility
- **No Subscription**: Farm remains private, core features still accessible

### 4. Feature Access Levels
- **FREE for ALL Farmers**: Core farm management (flock, production, feed, medication, mortality)
- **Requires Subscription**: Public marketplace listing, product photos, order management
- **Government Farmers**: Extension officer dashboard, benefit tracking, priority procurement (FREE)
- **Independent Farmers**: Advanced analytics, bulk exports (FREE), API access (future premium)

---

## 🏗️ Technical Implementation

### Model Changes

```python
# farms/models.py

class Farm(models.Model):
    """
    Main farm registration model.
    Now supports dual onboarding pathways.
    """
    
    # ... existing fields ...
    
    # ============================================
    # NEW SECTION: REGISTRATION SOURCE TRACKING
    # ============================================
    
    REGISTRATION_SOURCE_CHOICES = [
        ('government_initiative', 'YEA Government Initiative'),
        ('self_registered', 'Self-Registered/Independent'),
        ('migrated', 'Migrated from External System'),
    ]
    
    registration_source = models.CharField(
        max_length=30,
        choices=REGISTRATION_SOURCE_CHOICES,
        default='self_registered',
        db_index=True,
        help_text="How the farmer joined the platform"
    )
    
    # Government Initiative Specific Fields
    yea_program_batch = models.CharField(
        max_length=50,
        blank=True,
        help_text="YEA batch/cohort (e.g., 'YEA-2025-Q1')"
    )
    yea_program_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When farmer joined government program"
    )
    yea_program_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected program completion date"
    )
    government_support_package = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Details of government support received:
        {
            'day_old_chicks': 500,
            'feed_bags': 100,
            'training_sessions': 5,
            'extension_visits': 12,
            'subsidy_amount': 5000.00
        }
        """
    )
    extension_officer = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_farms',
        limit_choices_to={'role__name': 'Extension Officer'},
        help_text="Primary extension officer for government program farmers"
    )
    
    # Independent Farmer Specific Fields
    established_since = models.DateField(
        null=True,
        blank=True,
        help_text="For established farmers: when farm was originally established"
    )
    previous_management_system = models.CharField(
        max_length=100,
        blank=True,
        help_text="Manual/Excel/Other system used before joining platform"
    )
    referral_source = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('search_engine', 'Google/Search Engine'),
            ('social_media', 'Facebook/Instagram/Twitter'),
            ('farmer_referral', 'Referred by Another Farmer'),
            ('industry_event', 'Agricultural Fair/Conference'),
            ('advertisement', 'Advertisement'),
            ('other', 'Other'),
        ],
        help_text="How independent farmer heard about platform"
    )
    
    # Fast-Track Approval for Established Farmers
    fast_track_eligible = models.BooleanField(
        default=False,
        help_text="Eligible for simplified approval (established farmers with documentation)"
    )
    fast_track_criteria_met = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Criteria for fast-track approval:
        {
            'business_registered': True,
            'tin_verified': True,
            'existing_operations': True,
            'documentation_complete': True,
            'references_provided': True
        }
        """
    )
    
    # ============================================
    # MODIFIED: APPLICATION WORKFLOW
    # ============================================
    
    application_status = models.CharField(
        max_length=30,
        choices=[
            # Common to both
            ('Draft', 'Draft'),
            ('Submitted', 'Submitted - Pending Review'),
            
            # Government Initiative Workflow
            ('Constituency Review', 'Under Constituency Review'),
            ('Regional Review', 'Under Regional Review'),
            ('National Review', 'Under National Review'),
            
            # Independent Farmer Workflow
            ('Auto Review', 'Automatic Verification in Progress'),
            ('Basic Verification', 'Basic Information Verification'),
            
            # Common continuation
            ('Changes Requested', 'Changes Requested by Reviewer'),
            ('Approved', 'Approved - Farm ID Assigned'),
            ('Rejected', 'Rejected'),
        ],
        default='Draft',
        db_index=True
    )
    
    # Approval workflow type (auto-determined from registration_source)
    approval_workflow = models.CharField(
        max_length=30,
        choices=[
            ('full_government', 'Full 3-Tier Government Review'),
            ('simplified', 'Simplified Verification'),
            ('auto_approve', 'Auto-Approve with Basic Checks'),
        ],
        blank=True,
        help_text="Auto-set based on registration_source and fast_track_eligible"
    )
    
    # ============================================
    # MODIFIED: SUBSCRIPTION TRACKING
    # ============================================
    
    subscription_type = models.CharField(
        max_length=30,
        choices=[
            ('government_subsidized', 'Government-Subsidized (Free/Reduced)'),
            ('standard', 'Standard Subscription (GHS 100/month)'),
            ('premium', 'Premium Subscription (Future)'),
        ],
        default='standard',
        help_text="Type of subscription based on farmer type"
    )
    
    government_subsidy_active = models.BooleanField(
        default=False,
        help_text="Is farmer receiving government subscription subsidy"
    )
    government_subsidy_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When government subsidy started"
    )
    government_subsidy_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When government subsidy expires"
    )
    
    # ============================================
    # EXISTING FIELDS (unchanged)
    # ============================================
    
    # ... all existing Farm model fields remain ...
    
    class Meta:
        db_table = 'farms'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application_status']),
            models.Index(fields=['registration_source']),  # NEW
            models.Index(fields=['approval_workflow']),     # NEW
            models.Index(fields=['subscription_type']),     # NEW
            models.Index(fields=['extension_officer']),     # NEW
            models.Index(fields=['fast_track_eligible']),   # NEW
        ]
    
    def save(self, *args, **kwargs):
        """Override save to auto-determine approval workflow"""
        
        # Auto-set approval workflow based on registration source
        if self.registration_source == 'government_initiative':
            self.approval_workflow = 'full_government'
            self.subscription_type = 'government_subsidized'
        
        elif self.registration_source == 'self_registered':
            if self.fast_track_eligible:
                self.approval_workflow = 'simplified'
            else:
                # Check if meets auto-approve criteria
                if self._meets_auto_approve_criteria():
                    self.approval_workflow = 'auto_approve'
                else:
                    self.approval_workflow = 'simplified'
            
            self.subscription_type = 'standard'
        
        super().save(*args, **kwargs)
    
    def _meets_auto_approve_criteria(self):
        """
        Check if independent farmer meets auto-approve criteria:
        - TIN provided and verified
        - Business registration provided
        - Bank account verified
        - No red flags in documentation
        """
        criteria = [
            bool(self.tin),
            bool(self.business_registration_number),
            bool(self.bank_name and self.account_number),
            not bool(self.rejection_reason),  # No prior rejections
        ]
        return all(criteria)
    
    @property
    def is_government_farmer(self):
        """Check if farmer is part of government initiative"""
        return self.registration_source == 'government_initiative'
    
    @property
    def is_independent_farmer(self):
        """Check if farmer is independent/self-registered"""
        return self.registration_source == 'self_registered'
    
    @property
    def requires_extension_officer(self):
        """Check if farmer requires extension officer supervision"""
        return self.is_government_farmer
    
    @property
    def eligible_for_government_procurement(self):
        """Check if eligible for government bulk orders"""
        return (
            self.application_status == 'Approved' and
            self.farm_status == 'Active' and
            (self.is_government_farmer or self.business_registration_number)
        )
```

---

## 📊 Subscription Model Variations

### Government Initiative Farmers (Subsidized)

```python
# subscriptions/models.py

class GovernmentSubsidyProgram(models.Model):
    """
    Tracks government subsidy programs for farmer subscriptions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    program_name = models.CharField(
        max_length=200,
        unique=True,
        help_text="e.g., 'YEA Poultry Initiative 2025'"
    )
    program_code = models.CharField(max_length=50, unique=True)
    
    # Subsidy Details
    subsidy_type = models.CharField(
        max_length=30,
        choices=[
            ('full', 'Full Subscription (100% covered)'),
            ('partial', 'Partial Subsidy (% covered)'),
        ],
        default='full'
    )
    subsidy_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of subscription covered by government"
    )
    
    # Duration
    start_date = models.DateField()
    end_date = models.DateField()
    max_participants = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum farmers in this program"
    )
    
    # Eligibility Criteria
    eligibility_criteria = models.JSONField(
        default=dict,
        help_text="""
        {
            'age_max': 35,
            'min_education': 'JHS',
            'location': ['Greater Accra', 'Ashanti'],
            'max_farm_size': 1000
        }
        """
    )
    
    # Transition Plan
    transition_to_paid = models.BooleanField(
        default=True,
        help_text="Farmers transition to paid subscription after program ends"
    )
    grace_period_days = models.PositiveIntegerField(
        default=30,
        help_text="Days after program ends before requiring payment"
    )
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'government_subsidy_programs'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.program_name} ({self.subsidy_percentage}% subsidy)"


class Subscription(models.Model):
    """
    Modified to support government-subsidized subscriptions.
    """
    
    # ... existing fields from SUBSCRIPTION_MODEL_DESIGN.md ...
    
    # NEW: Government Subsidy Tracking
    is_subsidized = models.BooleanField(
        default=False,
        help_text="Is this subscription government-subsidized"
    )
    subsidy_program = models.ForeignKey(
        GovernmentSubsidyProgram,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subsidized_subscriptions'
    )
    subsidy_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Percentage of subscription covered by subsidy"
    )
    farmer_payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount farmer pays after subsidy (can be 0)"
    )
    government_payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount covered by government subsidy"
    )
    
    # Subsidy Expiration
    subsidy_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When government subsidy expires"
    )
    transition_to_paid_date = models.DateField(
        null=True,
        blank=True,
        help_text="When farmer must start paying full amount"
    )
    subsidy_transition_notified = models.BooleanField(
        default=False,
        help_text="Has farmer been notified of upcoming transition to paid"
    )
    
    def calculate_split_payment(self):
        """
        Calculate farmer vs government payment amounts.
        """
        total_amount = self.plan.price_monthly
        
        if self.is_subsidized and self.subsidy_percentage > 0:
            self.government_payment_amount = total_amount * (self.subsidy_percentage / 100)
            self.farmer_payment_amount = total_amount - self.government_payment_amount
        else:
            self.farmer_payment_amount = total_amount
            self.government_payment_amount = Decimal('0.00')
        
        self.save()
```

---

## 🔄 Registration Workflows

### Workflow A: Government Initiative Farmer

```
Step 1: Extension Officer Creates Account
├─ Officer enters basic farmer info
├─ Farmer receives SMS with account credentials
└─ registration_source = 'government_initiative'

Step 2: Farmer Completes Registration
├─ Farmer logs in via phone/web
├─ Completes personal info, farm details
├─ Officer assists with document uploads
└─ Status: 'Submitted'

Step 3: Multi-Tier Approval
├─ Constituency Level Review (Extension Officer)
│   ├─ Verify personal information
│   ├─ Schedule site visit
│   └─ Approve or request changes
│
├─ Regional Level Review (Regional Coordinator)
│   ├─ Verify infrastructure readiness
│   ├─ Assess support needs
│   └─ Approve or request changes
│
└─ National Level Review (National Office)
    ├─ Final approval
    ├─ Assign Farm ID (YEA-REG-CONST-XXXX)
    ├─ Activate government subsidy
    └─ Status: 'Approved'

Step 4: Onboarding & Support
├─ Create subsidized subscription (100% covered)
├─ Assign benefit package
├─ Schedule extension officer visits
└─ Grant access to platform
```

### Workflow B: Independent Farmer (Self-Registered)

```
Step 1: Self-Registration
├─ Farmer visits website/app
├─ Creates account with phone/email
├─ registration_source = 'self_registered'
└─ Sees subscription pricing upfront

Step 2: Farm Information
├─ Completes registration form
├─ Uploads business documents
│   ├─ TIN (mandatory)
│   ├─ Business registration (encouraged)
│   ├─ Bank account details
│   └─ Farm photos (optional)
└─ Status: 'Submitted'

Step 3: Automated/Simplified Approval
├─ Option A: Auto-Approve (if criteria met)
│   ├─ TIN verified automatically
│   ├─ Business registration verified
│   ├─ No red flags
│   └─ Instant approval → Farm ID assigned
│
└─ Option B: Basic Verification (if incomplete)
    ├─ Single admin reviews application
    ├─ Verifies key documents
    ├─ Approves within 1-2 business days
    └─ Farm ID assigned

Step 4: Choose Platform Usage
├─ Option A: FREE Core Farm Management
│   ├─ Use flock tracking, production, inventory
│   ├─ Farm remains PRIVATE
│   ├─ No marketplace visibility
│   └─ No subscription required
│
└─ Option B: Marketplace Access (GHS 100/month)
    ├─ 14-day free trial activated
    ├─ Create product listings
    ├─ Upload farm photos (max 20)
    ├─ List on public marketplace
    ├─ Payment reminder on day 12
    └─ After trial: Pay or farm hidden from marketplace

Step 5: Core Features Always Available
├─ Farm management accessible regardless of subscription
├─ Can upgrade to marketplace anytime
├─ Can downgrade to free tier anytime
└─ Optional: Bid on government procurement orders
```

---

## 📋 Comparison Matrix

| Feature | Government Initiative Farmers | Independent Farmers |
|---------|-------------------------------|---------------------|
| **Registration** | Officer-assisted | Self-service |
| **Approval Time** | 7-14 days (3-tier) | 1-2 days or instant |
| **Core Farm Management** | FREE (always) | FREE (always) |
| **Marketplace Subscription** | FREE (100% subsidized) | OPTIONAL (GHS 100/month) |
| **Trial Period** | Not applicable | 14 days for marketplace |
| **Extension Officer** | Required (assigned) | Optional support |
| **Site Visits** | Mandatory | Not required |
| **Priority Procurement** | Yes (automatic) | Yes (if business registered) |
| **Support Package** | Government-provided (tracked) | Self-funded |
| **Training** | Free government training | Pay-per-course or self-learn |
| **Benefit Tracking** | Full tracking dashboard | Not applicable |
| **Farm Visibility** | Public (if want marketplace) | Private OR Public (farmer choice) |
| **Analytics Dashboard** | Basic (free) | Advanced (free) |
| **API Access** | No | Optional (future premium) |
| **Transition to Paid** | After program ends (grace period) | Can subscribe/unsubscribe anytime |

---

## 🔐 Access Control & Permissions

### Government Farmers - Feature Access

```python
# dashboards/permissions.py

class GovernmentFarmerFeatureAccess:
    """
    Features accessible to government initiative farmers.
    Core features FREE, marketplace 100% subsidized by government.
    """
    
    FEATURES = {
        # Core Features (FREE - Always Available)
        'farm_management': True,
        'flock_tracking': True,
        'daily_production': True,
        'feed_inventory': True,
        'medication_tracking': True,
        'mortality_recording': True,
        'sales_tracking': True,  # Can track private sales
        
        # Government-Specific Features (FREE)
        'extension_officer_dashboard': True,
        'benefit_package_tracking': True,
        'government_support_log': True,
        'training_schedule': True,
        'site_visit_calendar': True,
        'compliance_checklist': True,
        
        # Marketplace Features (100% Government-Subsidized)
        'view_marketplace': True,
        'list_products': True,  # If farmer opts in + has subscription
        'product_photos': 20,   # Full 20 images when subscribed
        'public_farm_profile': True,  # If subscribed
        'receive_orders': True,  # If subscribed
        
        # Procurement (FREE)
        'government_procurement': True,  # Priority access
        'procurement_notifications': True,
        
        # Analytics (FREE)
        'basic_analytics': True,
        'production_reports': True,
        'financial_reports': True,
        'advanced_analytics': True,
        
        # Premium Features (Not Included)
        'api_access': False,
        'bulk_exports': True,
        'custom_reports': False,
    }


class IndependentFarmerFeatureAccess:
    """
    Features accessible to independent/established farmers.
    Core features FREE, marketplace requires GHS 100/month (OPTIONAL).
    """
    
    FEATURES = {
        # Core Features (FREE - Always Available)
        'farm_management': True,
        'flock_tracking': True,
        'daily_production': True,
        'feed_inventory': True,
        'medication_tracking': True,
        'mortality_recording': True,
        'sales_tracking': True,  # Can track private sales
        
        # Government-Specific Features (Not Applicable)
        'extension_officer_dashboard': False,
        'benefit_package_tracking': False,
        'government_support_log': False,
        'training_schedule': False,  # Unless enrolled in paid training
        'site_visit_calendar': False,
        'compliance_checklist': False,
        
        # Marketplace Features (Requires GHS 100/month Subscription)
        'view_marketplace': True,  # Can browse even without subscription
        'list_products': 'REQUIRES_SUBSCRIPTION',  # GHS 100/month
        'product_photos': 20,  # When subscribed
        'public_farm_profile': 'REQUIRES_SUBSCRIPTION',
        'receive_orders': 'REQUIRES_SUBSCRIPTION',
        'featured_listings': 'REQUIRES_SUBSCRIPTION',
        
        # Procurement (FREE if business registered)
        'government_procurement': True,  # If business registered
        'procurement_notifications': True,
        
        # Analytics (FREE)
        'basic_analytics': True,
        'production_reports': True,
        'financial_reports': True,
        'advanced_analytics': True,
        'custom_reports': True,
        
        # Premium Features
        'api_access': False,  # Future premium tier
        'bulk_exports': True,
        'custom_integrations': False,  # Future
    }
```

---

## 🎯 User Interface Differentiation

### Dashboard Layouts

#### Government Farmer Dashboard
```
┌─────────────────────────────────────────────────┐
│ 👨‍🌾 Welcome, [Farmer Name]                        │
│ 🏛️ YEA Poultry Initiative 2025 - Batch Q1       │
│ 📍 Extension Officer: [Officer Name]             │
└─────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 📦 Support      │  │ 📅 Upcoming     │  │ 📊 Production   │
│ Package         │  │ Site Visit      │  │ This Week       │
│                 │  │                 │  │                 │
│ Chicks: 500     │  │ Dec 2, 2025     │  │ Eggs: 1,250     │
│ Feed: 100 bags  │  │ 10:00 AM        │  │ Mortality: 2    │
│ Training: 3/5   │  │ w/ Officer      │  │ Feed: 45 bags   │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────────────────────────────────────┐
│ 📚 Training & Resources                         │
│ ✅ Biosecurity Basics (Completed)               │
│ 🔄 Feed Management (In Progress - 60%)          │
│ ⏳ Disease Prevention (Upcoming)                │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 📋 Daily Tasks                                  │
│ • Record morning production                      │
│ • Check feed inventory                           │
│ • Update mortality records                       │
│ • Complete biosecurity checklist                 │
└─────────────────────────────────────────────────┘
```

#### Independent Farmer Dashboard
```
┌─────────────────────────────────────────────────┐
│ 👨‍💼 Welcome, [Farm Name]                          │
│ 💳 Subscription: Active (Renews Dec 26)         │
│ 🏪 Marketplace Listings: 5 Active               │
└─────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 💰 Revenue      │  │ 📦 Orders       │  │ 📊 Production   │
│ This Month      │  │ Pending         │  │ This Week       │
│                 │  │                 │  │                 │
│ GHS 15,420      │  │ 8 Orders        │  │ Eggs: 12,500    │
│ +12% vs last    │  │ 3 New Today     │  │ Birds: 450      │
│ Target: 78%     │  │ 2 Deliveries    │  │ Efficiency: 94% │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────────────────────────────────────┐
│ 🏪 Marketplace Performance                      │
│ Product Views: 1,245                            │
│ Orders Placed: 23                               │
│ Conversion Rate: 1.8%                           │
│ Average Order: GHS 670                          │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 📈 Advanced Analytics                           │
│ [Production Trends] [Cost Analysis] [Forecasts] │
└─────────────────────────────────────────────────┘
```

---

## 🔄 Transition Planning

### Government Farmers Transitioning to Paid Subscriptions

**Scenario**: YEA program ends after 2 years, farmers must transition to paid subscriptions.

```python
# subscriptions/services.py

class SubsidyTransitionService:
    """
    Manages transition from subsidized to paid subscriptions.
    """
    
    @staticmethod
    def check_expiring_subsidies():
        """
        Daily task: Check for subsidies expiring in next 60 days.
        Send notifications to farmers.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        sixty_days_ahead = timezone.now().date() + timedelta(days=60)
        
        expiring_subscriptions = Subscription.objects.filter(
            is_subsidized=True,
            subsidy_end_date__lte=sixty_days_ahead,
            subsidy_transition_notified=False
        )
        
        for subscription in expiring_subscriptions:
            # Calculate days remaining
            days_remaining = (subscription.subsidy_end_date - timezone.now().date()).days
            
            # Send notification
            if days_remaining in [60, 30, 14, 7, 3, 1]:
                SubsidyTransitionService.send_transition_notification(
                    subscription, 
                    days_remaining
                )
    
    @staticmethod
    def send_transition_notification(subscription, days_remaining):
        """
        Notify farmer of upcoming transition to paid subscription.
        """
        farm = subscription.farm
        farmer = farm.user
        
        message = f"""
        Dear {farmer.get_full_name()},
        
        Your YEA Government Initiative program is ending in {days_remaining} days.
        
        After {subscription.subsidy_end_date.strftime('%B %d, %Y')}, 
        you will need to pay GHS {subscription.plan.price_monthly}/month 
        to continue using the platform.
        
        IMPORTANT: 
        - You will have a {subscription.subsidy_program.grace_period_days}-day grace period
        - Payment options: Mobile Money, Bank Transfer, Card
        - Your data and marketplace listings will be preserved
        
        Need help? Contact your extension officer or our support team.
        
        YEA Poultry Management Team
        """
        
        # Send via email
        send_mail(
            subject=f'Action Required: Subscription Payment Starts in {days_remaining} Days',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[farmer.email],
        )
        
        # Send via SMS
        sms_service.send(
            farmer.primary_phone,
            f"YEA Program ends in {days_remaining} days. "
            f"Subscription payment GHS {subscription.plan.price_monthly}/month starts after. "
            f"Check your email for details."
        )
        
        # Mark as notified
        subscription.subsidy_transition_notified = True
        subscription.save()
    
    @staticmethod
    def transition_to_paid(subscription):
        """
        Transition farmer from subsidized to paid subscription.
        """
        from django.utils import timezone
        
        # Update subscription
        subscription.is_subsidized = False
        subscription.subsidy_program = None
        subscription.subsidy_percentage = Decimal('0.00')
        subscription.farmer_payment_amount = subscription.plan.price_monthly
        subscription.government_payment_amount = Decimal('0.00')
        
        # Set new billing date (after grace period)
        grace_days = subscription.subsidy_program.grace_period_days if subscription.subsidy_program else 30
        subscription.next_billing_date = timezone.now().date() + timedelta(days=grace_days)
        
        # Update farm
        farm = subscription.farm
        farm.subscription_type = 'standard'
        farm.government_subsidy_active = False
        farm.save()
        
        subscription.save()
        
        # Send confirmation
        SubsidyTransitionService.send_transition_complete_notification(subscription)
```

---

## 📊 Reporting & Analytics

### Government Initiative Reports

**Required Reports for Program Management**:

1. **Farmer Enrollment Report**
   - Total farmers onboarded per batch/cohort
   - Geographic distribution (region, constituency)
   - Demographics (age, education, gender)
   - Onboarding completion rate

2. **Program Participation Report**
   - Active farmers vs inactive
   - Extension officer visit frequency
   - Training completion rates
   - Site visit compliance

3. **Production Performance Report**
   - Aggregate production per batch
   - Success rate (farms meeting targets)
   - Mortality rates comparison
   - Feed efficiency metrics

4. **Financial Tracking Report**
   - Total subsidy disbursed
   - Benefit package utilization
   - Cost per farmer
   - ROI projections

5. **Transition Readiness Report**
   - Farmers approaching program end
   - Transition success rate
   - Payment adoption post-subsidy
   - Retention rate

### Independent Farmer Analytics

**Self-Service Analytics Dashboard**:

1. **Revenue Analytics**
   - Sales trends (daily/weekly/monthly)
   - Revenue by product category
   - Marketplace vs offline sales
   - Seasonal patterns

2. **Production Efficiency**
   - Feed conversion ratios
   - Egg production rates
   - Mortality trends
   - Cost per unit production

3. **Marketplace Performance**
   - Product view metrics
   - Conversion rates
   - Order fulfillment times
   - Customer repeat rate

4. **Financial Health**
   - Profit/loss statements
   - Cash flow projections
   - Expense breakdowns
   - Break-even analysis

---

## 🎓 Key Recommendations

### Priority 1: Clear Differentiation

1. **Explicit Registration Paths**
   - Separate landing pages for each farmer type
   - Clear communication of requirements and benefits
   - Guided onboarding flows

2. **Transparent Subscription Models**
   - Government farmers: Clearly state subsidy details and duration
   - Independent farmers: Upfront pricing, trial period benefits
   - Transition support for government farmers

3. **Appropriate Approval Workflows**
   - Government farmers: Full due diligence for program compliance
   - Independent farmers: Fast-track for established farms
   - Automated checks where possible

### Priority 2: Scalability

4. **Automated Subsidy Management**
   - Track subsidy programs and expiration dates
   - Automated notifications for transitions
   - Grace period management

5. **Extension Officer Tools**
   - Mobile app for field visits
   - Offline data collection
   - Batch farmer management

6. **Independent Farmer Self-Service**
   - Minimal manual intervention
   - Instant approval where possible
   - Self-help resources

### Priority 3: Data Integrity

7. **Separate but Unified**
   - Both farmer types use same core models
   - Clear tracking of registration source
   - Avoid data silos

8. **Audit Trail**
   - Track all subsidy payments
   - Monitor transition success rates
   - Measure program effectiveness

---

## 🚀 Implementation Roadmap

### Phase 1: Model Updates (Week 1-2)
- [ ] Add `registration_source` field to Farm model
- [ ] Add government farmer fields (YEA program tracking)
- [ ] Add independent farmer fields (referral, established date)
- [ ] Add `approval_workflow` field
- [ ] Add `subscription_type` field
- [ ] Create `GovernmentSubsidyProgram` model
- [ ] Update Subscription model with subsidy fields
- [ ] Write migrations

### Phase 2: Approval Workflows (Week 3-4)
- [ ] Implement dual workflow logic
- [ ] Auto-determine workflow on registration
- [ ] Fast-track approval service for independent farmers
- [ ] Update extension officer review interface
- [ ] Add simplified admin review for independent farmers

### Phase 3: Subscription Logic (Week 5-6)
- [ ] Implement subsidized subscription creation
- [ ] Create subsidy program management interface
- [ ] Build transition notification service
- [ ] Implement grace period handling
- [ ] Create farmer payment calculation logic

### Phase 4: UI/UX Differentiation (Week 7-8)
- [ ] Separate landing pages for farmer types
- [ ] Customize dashboard layouts
- [ ] Feature access control by farmer type
- [ ] Government farmer specific views
- [ ] Independent farmer advanced analytics

### Phase 5: Extension Officer Tools (Week 9-10)
- [ ] Extension officer dashboard
- [ ] Farmer supervision interface
- [ ] Site visit scheduling
- [ ] Training tracking
- [ ] Support package management

### Phase 6: Reporting & Analytics (Week 11-12)
- [ ] Government program reports
- [ ] Independent farmer analytics
- [ ] Transition tracking reports
- [ ] Financial reports per farmer type
- [ ] Export capabilities

### Phase 7: Testing & Deployment (Week 13-14)
- [ ] Unit tests for dual workflows
- [ ] Integration tests
- [ ] User acceptance testing (both farmer types)
- [ ] Performance testing
- [ ] Production deployment

**Total: 14 weeks (3.5 months)**

---

## 💡 Future Enhancements

### Premium Tiers for Independent Farmers

**Standard (GHS 100/month)**:
- 20 product images
- Basic marketplace
- Core farm management
- Standard analytics

**Premium (GHS 200/month)**:
- 50 product images
- Featured marketplace listings
- Priority customer support
- Advanced analytics + AI insights
- API access
- Custom integrations

### Government Program Expansion

**Potential Programs**:
1. **Youth in Poultry (18-35 years)**: 100% subsidy, 2-year duration
2. **Women in Agriculture**: 75% subsidy, 18-month duration
3. **Rural Expansion Initiative**: 50% subsidy, 12-month duration
4. **Veteran Farmer Modernization**: 25% subsidy, 6-month duration

---

**Document Version**: 1.0  
**Created**: November 26, 2025  
**Status**: 📋 DESIGN PROPOSAL  
**Estimated Timeline**: 14 weeks
