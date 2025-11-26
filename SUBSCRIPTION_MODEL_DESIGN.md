# Subscription Business Model Design & Implementation Plan

**Date**: November 26, 2025  
**Change Type**: 🔴 **CRITICAL BUSINESS MODEL TRANSFORMATION**  
**Impact**: Complete overhaul of monetization strategy

---

## 📋 Executive Summary

### Current Model (Commission-Based) ❌
- Platform takes 2-5% commission per sale
- Complex Paystack subaccount system
- Farmer payouts after each transaction
- Platform handles payment processing
- Revenue dependent on transaction volume

### New Model (Optional Subscription for Marketplace) ✅
- **Core farm management**: FREE (flock tracking, production, inventory, medication)
- **Marketplace & Sales features**: GHS 100/month (OPTIONAL)
- Farmers choose: Private farm management OR public marketplace visibility
- No commission on sales
- **Offline payments** between buyer and seller
- Farmers optionally record sales in system
- Predictable recurring revenue from farmers who want marketplace exposure

---

## 🎯 New Features Required

### 1. **Free Tier (Core Farm Management)**
- Flock management and tracking
- Daily production recording
- Feed inventory management
- Medication and vaccination tracking
- Mortality recording
- Basic analytics and reports
- **Farm remains PRIVATE** - not visible on public marketplace

### 2. **Subscription System (Optional - GHS 100/month)**
- **UNLOCKS**: Marketplace and sales features
- Monthly subscription plans (GHS 100/month)
- Trial periods (optional: 14-day free trial)
- Grace periods (3-5 days after payment due)
- Automatic suspension of marketplace features after non-payment
- Core farm management always remains accessible
- Renewal reminders via email/SMS

### 3. **Public Marketplace (Requires Subscription)**
- Browse farms without authentication
- View products (eggs, birds, etc.) with photos
- See pricing and availability
- Place orders (contact farmer directly)
- **Offline payment** - No payment gateway integration
- **Only subscribed farms are visible**

### 4. **Product Listings (Requires Subscription)**
- Farmers upload products with photos (max 20 images)
- Each image max 5MB
- Product name, description, price, availability
- Stock management (optional)
- Public farm profile page

### 5. **Multi-Factor Authentication (MFA)** - Free for All
- TOTP-based 2FA (Google Authenticator, Authy)
- SMS-based OTP as backup
- Recovery codes
- Enforced for all users or optional by role

### 6. **Email Verification** - Free for All
- Required before account activation
- Email verification link with expiration (24 hours)
- Resend capability
- Block unverified users from accessing system

### 7. **Sales Recording (Optional)**
- Available to ALL farmers (free tier included)
- Farmers can log sales made offline
- No payment processing
- Inventory tracking
- Revenue analytics
- Useful for private sales tracking without marketplace exposure

---

## 🏗️ Architecture Changes

### Models to ADD

```
subscriptions/
├── SubscriptionPlan (GHS 100/month plan)
├── Subscription (farmer's active subscription)
├── SubscriptionPayment (payment records)
├── SubscriptionInvoice (monthly invoices)

marketplace/
├── ProductCategory (Eggs, Live Birds, Meat, etc.)
├── ProductListing (farmer's products)
├── ProductImage (max 20 per farm, 5MB each)
├── PublicOrder (buyer orders)
├── OrderItem (order line items)

accounts/
├── MFADevice (TOTP/SMS 2FA)
├── RecoveryCode (backup codes)
├── EmailVerificationToken (verification tokens)
```

### Models to REMOVE/DEPRECATE

```
sales_revenue/
├── ❌ PlatformSettings (commission tiers)
├── ❌ EggSale (now optional recording only)
├── ❌ BirdSale (now optional recording only)
├── ❌ Payment (Paystack integration)
├── ❌ FarmerPayout (subaccount settlements)
├── ⚠️ Customer (keep but repurpose for orders)
├── ⚠️ FraudAlert (keep but adapt for subscriptions)
```

### Models to MODIFY

```
farms/
├── Farm
    ├── ADD: subscription (FK to Subscription, NULLABLE)
    ├── ADD: marketplace_enabled (boolean, requires subscription)
    ├── ADD: product_images_count (track 20 image limit)
    ├── KEEP: All core farm management fields (always accessible)
    ├── REMOVE: paystack_subaccount_code
    ├── REMOVE: paystack_subaccount_id
    ├── REMOVE: paystack_settlement_account

accounts/
├── User
    ├── ADD: mfa_enabled (boolean)
    ├── ADD: mfa_method (totp/sms/none)
    ├── MODIFY: email_verified (required for login)
    ├── ADD: marketplace_access_requested (date)
```

---

## 📦 Detailed Model Designs

### 1. Subscription Models

```python
# subscriptions/models.py

class SubscriptionPlan(models.Model):
    """
    OPTIONAL subscription plans for marketplace & sales features.
    Core farm management is FREE for all farmers.
    Currently: GHS 100/month for marketplace access.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
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
    """
    STATUS_CHOICES = [
        ('trial', 'Trial Period'),
        ('active', 'Active'),
        ('past_due', 'Past Due (Grace Period)'),
        ('suspended', 'Suspended - Marketplace Hidden'),
        ('cancelled', 'Cancelled - Marketplace Hidden'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
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
        
        from django.utils import timezone
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
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
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
        return f"Payment GHS {self.amount} - {self.subscription.farm.farm_name}"


class SubscriptionInvoice(models.Model):
    """
    Monthly invoices generated for subscriptions.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
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
        max_length=20,
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
```

---

### 2. Public Marketplace Models

```python
# marketplace/models.py

class ProductCategory(models.Model):
    """
    Product categories for marketplace.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class or emoji")
    
    # For multi-species support
    bird_species = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Bird species this category applies to"
    )
    
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_categories'
        verbose_name_plural = 'Product Categories'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class ProductListing(models.Model):
    """
    Products listed by farmers on marketplace.
    """
    PRODUCT_TYPE_CHOICES = [
        ('eggs', 'Eggs'),
        ('live_birds', 'Live Birds'),
        ('dressed_meat', 'Dressed/Processed Meat'),
        ('day_old_chicks', 'Day-old Chicks/Poults'),
        ('feed', 'Feed (Surplus)'),
        ('manure', 'Manure/Compost'),
        ('other', 'Other Products'),
    ]
    
    UNIT_CHOICES = [
        # Eggs
        ('piece', 'Per Egg'),
        ('dozen', 'Per Dozen (12 eggs)'),
        ('crate_30', 'Per Crate (30 eggs)'),
        ('tray_36', 'Per Tray (36 eggs) - Quail'),
        
        # Birds
        ('bird', 'Per Bird'),
        ('kg', 'Per Kilogram'),
        ('bag', 'Per Bag'),
        ('tonne', 'Per Tonne'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('out_of_stock', 'Out of Stock'),
        ('inactive', 'Inactive'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='product_listings'
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products'
    )
    
    # Product Details
    product_type = models.CharField(max_length=30, choices=PRODUCT_TYPE_CHOICES)
    bird_species = models.CharField(
        max_length=50,
        blank=True,
        help_text="For bird/egg products"
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per unit"
    )
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    
    # Availability
    in_stock = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional stock tracking"
    )
    minimum_order = models.PositiveIntegerField(
        default=1,
        help_text="Minimum order quantity"
    )
    
    # Product Specifications
    specifications = models.JSONField(
        default=dict,
        help_text="""
        Product-specific attributes:
        Eggs: {'size': 'Large', 'color': 'Brown', 'organic': True}
        Birds: {'weight_kg': 2.5, 'age_weeks': 16, 'breed': 'Sasso'}
        """
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    
    # SEO & Discovery
    tags = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Tags for search (e.g., 'organic', 'free-range')"
    )
    
    # Metrics
    views_count = models.PositiveIntegerField(default=0)
    orders_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_listings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['bird_species']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.farm.farm_name}"
    
    def clean(self):
        """Validate product listing"""
        from django.core.exceptions import ValidationError
        
        # Check subscription status
        if not self.farm.subscription or not self.farm.subscription.is_active:
            raise ValidationError("Farm must have active subscription to list products")
        
        # Check image limit
        if self.farm.product_images_count >= self.farm.subscription.plan.max_product_images:
            raise ValidationError(
                f"Farm has reached maximum of {self.farm.subscription.plan.max_product_images} images"
            )


class ProductImage(models.Model):
    """
    Product images (max 20 per farm, 5MB each).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    product = models.ForeignKey(
        ProductListing,
        on_delete=models.CASCADE,
        related_name='images'
    )
    
    image = models.ImageField(
        upload_to='marketplace/products/%Y/%m/',
        help_text="Product image (max 5MB)"
    )
    
    # Image Details
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    file_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # Ordering
    display_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    
    caption = models.CharField(max_length=200, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        ordering = ['product', 'display_order', '-is_primary']
        indexes = [
            models.Index(fields=['product', 'display_order']),
        ]
    
    def __str__(self):
        return f"Image for {self.product.title}"
    
    def clean(self):
        """Validate image upload"""
        from django.core.exceptions import ValidationError
        
        # Check file size (5MB = 5 * 1024 * 1024 bytes)
        max_size = 5 * 1024 * 1024
        if self.image and self.image.size > max_size:
            raise ValidationError(
                f'Image size ({self.image.size / 1024 / 1024:.2f}MB) exceeds maximum 5MB'
            )
        
        # Check farm's total image count
        farm = self.product.farm
        if farm.product_images_count >= farm.subscription.plan.max_product_images:
            raise ValidationError(
                f'Farm has reached maximum of {farm.subscription.plan.max_product_images} images'
            )


class PublicOrder(models.Model):
    """
    Orders placed by public buyers (no payment processing).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Farmer Response'),
        ('confirmed', 'Confirmed by Farmer'),
        ('rejected', 'Rejected by Farmer'),
        ('completed', 'Completed (Offline Payment)'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    order_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Format: ORD-YYYY-XXXXX"
    )
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='public_orders'
    )
    
    # Buyer Information (no user account required)
    buyer_name = models.CharField(max_length=200)
    buyer_phone = models.CharField(max_length=20)
    buyer_email = models.EmailField(blank=True)
    buyer_location = models.CharField(max_length=255, blank=True)
    
    # Order Details
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total order value (for farmer's reference)"
    )
    
    # Delivery/Pickup
    delivery_method = models.CharField(
        max_length=20,
        choices=[
            ('pickup', 'Pickup from Farm'),
            ('delivery', 'Delivery to Buyer'),
        ],
        default='pickup'
    )
    delivery_address = models.TextField(blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Farmer Response
    farmer_notes = models.TextField(
        blank=True,
        help_text="Farmer's response/notes to buyer"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Completion (offline payment)
    completed_at = models.DateTimeField(null=True, blank=True)
    payment_method_used = models.CharField(
        max_length=50,
        blank=True,
        help_text="How buyer paid (cash, mobile money, etc.) - for farmer's record"
    )
    
    # Special Instructions
    special_instructions = models.TextField(
        blank=True,
        help_text="Buyer's special requests"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'public_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.buyer_name}"


class OrderItem(models.Model):
    """
    Line items in a public order.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    order = models.ForeignKey(
        PublicOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        ProductListing,
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    
    # Order Details
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per unit at time of order"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="quantity × unit_price"
    )
    
    # Product Snapshot (in case product deleted)
    product_title = models.CharField(max_length=200)
    product_description = models.TextField()
    unit = models.CharField(max_length=20)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_items'
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.product_title}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate subtotal
        self.subtotal = Decimal(str(self.quantity)) * self.unit_price
        
        # Snapshot product details
        if self.product_id:
            self.product_title = self.product.title
            self.product_description = self.product.description
            self.unit = self.product.unit
        
        super().save(*args, **kwargs)
```

---

### 3. MFA Models

```python
# accounts/models.py (additions)

class MFADevice(models.Model):
    """
    Multi-Factor Authentication devices for users.
    """
    MFA_TYPE_CHOICES = [
        ('totp', 'TOTP (Google Authenticator, Authy)'),
        ('sms', 'SMS OTP'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mfa_devices'
    )
    
    # Device Type
    mfa_type = models.CharField(max_length=10, choices=MFA_TYPE_CHOICES)
    device_name = models.CharField(
        max_length=100,
        help_text="User-friendly name (e.g., 'iPhone 13', 'Work Phone')"
    )
    
    # TOTP Specific
    totp_secret = models.CharField(
        max_length=32,
        blank=True,
        help_text="Base32 encoded secret for TOTP"
    )
    
    # SMS Specific
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    verified = models.BooleanField(
        default=False,
        help_text="Device verified with successful OTP"
    )
    
    # Usage Tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mfa_devices'
        ordering = ['-is_primary', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.device_name} ({self.mfa_type})"


class RecoveryCode(models.Model):
    """
    Backup recovery codes for MFA.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recovery_codes'
    )
    
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="8-10 character recovery code"
    )
    
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'recovery_codes'
        ordering = ['created_at']
    
    def __str__(self):
        status = "Used" if self.is_used else "Active"
        return f"{self.user.username} - {self.code[:4]}**** ({status})"


class EmailVerificationToken(models.Model):
    """
    Email verification tokens.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens'
    )
    
    token = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.EmailField(help_text="Email being verified")
    
    expires_at = models.DateTimeField(help_text="Token expiration (24 hours)")
    
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'email_verification_tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.email}"
    
    @property
    def is_expired(self):
        """Check if token has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired
```

---

## 🔄 Migration Strategy

### Phase 1: Add New Models (Non-Breaking)
**Week 1-2**

1. Create new apps:
   - `subscriptions/`
   - `marketplace/`

2. Add new models:
   - SubscriptionPlan, Subscription, SubscriptionPayment, SubscriptionInvoice
   - ProductCategory, ProductListing, ProductImage
   - PublicOrder, OrderItem
   - MFADevice, RecoveryCode, EmailVerificationToken

3. Run migrations (no data loss)

### Phase 2: Update Farm Model (Additive)
**Week 2-3**

```python
# farms/models.py
class Farm(models.Model):
    # ... existing fields ...
    
    # ADD: Subscription tracking
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Subscription'),
            ('trial', 'Trial Period'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
        ],
        default='none'
    )
    
    # ADD: Image limit tracking
    product_images_count = models.PositiveIntegerField(
        default=0,
        help_text="Current number of product images"
    )
    
    # KEEP but deprecate Paystack fields (for historical data)
    paystack_subaccount_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="DEPRECATED - Keep for historical records"
    )
```

### Phase 3: Migrate Existing Farms
**Week 3-4**

```python
# Migration script
def migrate_existing_farms(apps, schema_editor):
    Farm = apps.get_model('farms', 'Farm')
    SubscriptionPlan = apps.get_model('subscriptions', 'SubscriptionPlan')
    Subscription = apps.get_model('subscriptions', 'Subscription')
    
    # Get default plan
    default_plan = SubscriptionPlan.objects.get(name='Basic Monthly')
    
    # Migrate all approved farms
    approved_farms = Farm.objects.filter(application_status='Approved')
    
    for farm in approved_farms:
        # Create subscription with 14-day trial
        Subscription.objects.create(
            farm=farm,
            plan=default_plan,
            status='trial',
            start_date=timezone.now().date(),
            trial_start=timezone.now().date(),
            trial_end=timezone.now().date() + timedelta(days=14),
            current_period_start=timezone.now().date(),
            current_period_end=timezone.now().date() + timedelta(days=14),
            next_billing_date=timezone.now().date() + timedelta(days=14),
        )
        
        farm.subscription_status = 'trial'
        farm.save()
```

### Phase 4: Deprecate Old Sales Models
**Week 4-5**

1. Keep `sales_revenue/` models for historical data
2. Add `is_legacy = True` flag to old sale records
3. Disable new records in old models
4. Redirect farmers to new marketplace system

### Phase 5: Update UI/UX
**Week 5-8**

1. Add subscription management dashboard
2. Add marketplace product listing interface
3. Add public marketplace browsing (no auth required)
4. Add MFA setup flow
5. Add email verification flow

---

## 🔐 Security Enhancements

### 1. Multi-Factor Authentication

**Implementation Options**:

**Option A: TOTP (Recommended)**
```python
# Using pyotp library
import pyotp

class MFAService:
    @staticmethod
    def generate_totp_secret():
        """Generate TOTP secret for user"""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp_uri(secret, username):
        """Generate QR code URI for authenticator apps"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=username,
            issuer_name='YEA Poultry Management'
        )
    
    @staticmethod
    def verify_totp(secret, code):
        """Verify TOTP code"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)  # 30-second window
```

**Option B: SMS OTP**
```python
# Using Hubtel SMS
class SMSOTPService:
    @staticmethod
    def send_otp(phone_number):
        """Send OTP via SMS"""
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store in cache (5-minute expiration)
        cache_key = f'sms_otp_{phone_number}'
        cache.set(cache_key, code, timeout=300)
        
        # Send SMS
        sms_service.send(
            phone_number,
            f"Your YEA PMS verification code is: {code}. Valid for 5 minutes."
        )
        
        return True
    
    @staticmethod
    def verify_otp(phone_number, code):
        """Verify SMS OTP"""
        cache_key = f'sms_otp_{phone_number}'
        stored_code = cache.get(cache_key)
        
        if stored_code and stored_code == code:
            cache.delete(cache_key)
            return True
        return False
```

### 2. Email Verification

```python
# accounts/services.py

class EmailVerificationService:
    @staticmethod
    def send_verification_email(user):
        """Send email verification link"""
        import secrets
        from datetime import timedelta
        
        # Generate token
        token = secrets.token_urlsafe(32)
        
        # Create verification record
        verification = EmailVerificationToken.objects.create(
            user=user,
            token=token,
            email=user.email,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Send email
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}/"
        
        send_mail(
            subject='Verify Your Email - YEA Poultry Management',
            message=f"""
            Hello {user.get_full_name()},
            
            Please verify your email address by clicking the link below:
            {verification_url}
            
            This link will expire in 24 hours.
            
            If you didn't create this account, please ignore this email.
            
            Best regards,
            YEA Poultry Management Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
        
        return verification
    
    @staticmethod
    def verify_email(token):
        """Verify email with token"""
        try:
            verification = EmailVerificationToken.objects.get(token=token)
            
            if not verification.is_valid:
                return False, "Token expired or already used"
            
            # Mark user email as verified
            user = verification.user
            user.email_verified = True
            user.save()
            
            # Mark token as used
            verification.is_used = True
            verification.used_at = timezone.now()
            verification.save()
            
            return True, "Email verified successfully"
        
        except EmailVerificationToken.DoesNotExist:
            return False, "Invalid verification token"
```

---

## 💳 Payment Integration

### Subscription Payment Options

**Option 1: Manual Payment Verification (Simpler)**
- Farmers pay via mobile money/bank transfer
- Upload payment receipt
- Admin verifies and activates subscription

**Option 2: Automated Payment Gateway (Better UX)**
- Integrate Paystack/Flutterwave for subscription billing
- Recurring payments
- Automatic activation

**Recommended: Start with Manual, Add Automation Later**

```python
# subscriptions/services.py

class SubscriptionPaymentService:
    @staticmethod
    def process_manual_payment(subscription, amount, payment_method, reference):
        """Process manual subscription payment"""
        
        # Create payment record
        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            amount=amount,
            payment_method=payment_method,
            payment_reference=reference,
            status='pending',
            period_start=subscription.next_billing_date,
            period_end=subscription.next_billing_date + timedelta(days=30),
            payment_date=timezone.now().date()
        )
        
        # Send notification to admin for verification
        # TODO: Notify admin
        
        return payment
    
    @staticmethod
    def verify_payment(payment, verified_by):
        """Admin verifies payment"""
        
        payment.status = 'completed'
        payment.verified_by = verified_by
        payment.verified_at = timezone.now()
        payment.save()
        
        # Update subscription
        subscription = payment.subscription
        subscription.reactivate()
        
        # Generate invoice
        # TODO: Create invoice
        
        return True
```

---

## 📱 Public Marketplace Features

### Browse Products (No Auth Required)

```python
# marketplace/views.py

class PublicProductListView(APIView):
    """
    Public endpoint for browsing products.
    No authentication required.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        # Only show products from active subscriptions
        products = ProductListing.objects.filter(
            status='active',
            farm__subscription__status__in=['trial', 'active']
        ).select_related('farm', 'category')
        
        # Filters
        bird_species = request.query_params.get('bird_species')
        if bird_species:
            products = products.filter(bird_species=bird_species)
        
        category = request.query_params.get('category')
        if category:
            products = products.filter(category__slug=category)
        
        region = request.query_params.get('region')
        if region:
            products = products.filter(farm__region=region)
        
        # Serialize and return
        serializer = ProductListingSerializer(products, many=True)
        return Response(serializer.data)


class PublicOrderCreateView(APIView):
    """
    Place order (no auth required).
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PublicOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = serializer.save()
        
        # Notify farmer
        # TODO: Send SMS/email to farmer
        
        return Response({
            'message': 'Order placed successfully',
            'order_number': order.order_number,
            'total_amount': order.total_amount,
        }, status=status.HTTP_201_CREATED)
```

---

## 🗂️ File Structure Changes

```
pms-backend/
├── subscriptions/          # NEW APP
│   ├── __init__.py
│   ├── models.py          # SubscriptionPlan, Subscription, Payment, Invoice
│   ├── admin.py           # Subscription management interface
│   ├── serializers.py     # API serializers
│   ├── views.py           # Subscription API endpoints
│   ├── urls.py
│   ├── services.py        # Business logic
│   └── tasks.py           # Celery tasks (auto-billing, reminders)
│
├── marketplace/           # NEW APP
│   ├── __init__.py
│   ├── models.py          # ProductListing, ProductImage, Order
│   ├── admin.py           # Product/order management
│   ├── serializers.py
│   ├── views.py           # Public + farmer APIs
│   ├── urls.py
│   └── services.py        # Image processing, order management
│
├── accounts/
│   ├── models.py          # ADD: MFADevice, RecoveryCode, EmailVerificationToken
│   ├── mfa.py             # NEW: MFA logic
│   ├── views.py           # UPDATE: Add MFA endpoints
│   └── serializers.py     # UPDATE: Add MFA serializers
│
├── farms/
│   ├── models.py          # UPDATE: Add subscription fields
│   └── views.py           # UPDATE: Check subscription status
│
├── sales_revenue/         # DEPRECATE (keep for historical data)
│   ├── models.py          # MARK: is_legacy = True
│   └── README.md          # Document deprecation
│
└── core/
    └── settings.py        # ADD: Image storage, MFA settings
```

---

## 📊 Database Changes Summary

### New Tables (11)
```
subscriptions:
  - subscription_plans (1 row: GHS 100/month)
  - subscriptions (1 per farm)
  - subscription_payments
  - subscription_invoices

marketplace:
  - product_categories (~10 rows)
  - product_listings
  - product_images (max 20 per farm)
  - public_orders
  - order_items

accounts:
  - mfa_devices
  - recovery_codes
  - email_verification_tokens
```

### Modified Tables (2)
```
farms:
  - ADD: subscription_status
  - ADD: product_images_count
  - DEPRECATE: paystack_subaccount_code (keep for history)

accounts.users:
  - ADD: mfa_enabled
  - ADD: mfa_method
  - MODIFY: email_verified (required)
```

### Deprecated Tables (7)
```
sales_revenue:
  - platform_settings (commission tiers) → Remove
  - egg_sale → Optional use only
  - bird_sale → Optional use only
  - payment → Remove (Paystack integration)
  - farmer_payout → Remove (subaccounts)
  - customer → Repurpose for marketplace
  - fraud_alert → Adapt for subscription fraud
```

---

## ⚠️ Breaking Changes

### For Farmers

1. **Payment Required**: Must pay GHS 100/month to access platform
2. **Trial Period**: 14 days free, then subscription required
3. **Image Limit**: Max 20 product images (5MB each)
4. **No Auto-Payout**: Platform no longer handles payments
5. **MFA Required**: Must set up 2FA for account security
6. **Email Verification**: Must verify email before full access

### For Buyers

1. **No Platform Payment**: All payments offline (cash, mobile money)
2. **Direct Contact**: Communicate directly with farmer
3. **No Buyer Accounts**: Can browse and order without registration

### For Admins

1. **Subscription Management**: Manually verify payments initially
2. **No Commission Tracking**: Revenue now from subscriptions only
3. **Image Moderation**: Monitor product image uploads

---

## 🎯 Implementation Roadmap

### Sprint 1-2: Foundation (2 weeks)
- [ ] Create `subscriptions/` app
- [ ] Create `marketplace/` app
- [ ] Design all models
- [ ] Write migrations
- [ ] Create basic admin interfaces

### Sprint 3-4: Subscription System (2 weeks)
- [ ] Implement subscription lifecycle
- [ ] Manual payment verification
- [ ] Billing reminders (email/SMS)
- [ ] Grace period & suspension logic
- [ ] Subscription dashboard for farmers

### Sprint 5-6: Marketplace (2 weeks)
- [ ] Product listing CRUD
- [ ] Image upload with validation
- [ ] Public browsing API
- [ ] Order placement (no payment)
- [ ] Farmer order management

### Sprint 7: MFA (1 week)
- [ ] TOTP implementation (pyotp)
- [ ] SMS OTP (Hubtel)
- [ ] Recovery codes
- [ ] MFA setup flow
- [ ] MFA login flow

### Sprint 8: Email Verification (1 week)
- [ ] Token generation
- [ ] Verification email
- [ ] Verification endpoint
- [ ] Resend functionality
- [ ] Block unverified users

### Sprint 9-10: Integration (2 weeks)
- [ ] Update farm registration flow
- [ ] Add subscription check middleware
- [ ] Update all protected endpoints
- [ ] Deprecate old sales models
- [ ] Data migration scripts

### Sprint 11-12: Testing & Deployment (2 weeks)
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests
- [ ] User acceptance testing
- [ ] Performance testing
- [ ] Production deployment

**Total: 12 weeks (3 months)**

---

## 💰 Revenue Projections

### Current Model (Commission)
- Unpredictable revenue
- Depends on transaction volume
- Complex payout management

### New Model (Subscription)
- **Predictable**: GHS 100/farm/month
- **100 farms** = GHS 10,000/month
- **500 farms** = GHS 50,000/month
- **1,000 farms** = GHS 100,000/month

---

## 🎓 Key Recommendations

### Priority 1: Critical

1. **Start with Manual Payment Verification**
   - Simpler to implement
   - Add automation later
   - Lower risk

2. **Implement MFA from Day 1**
   - Security is critical
   - Protects farmer accounts
   - Builds trust

3. **14-Day Free Trial**
   - Gives farmers time to evaluate
   - Reduces barrier to entry
   - Higher conversion rate

### Priority 2: Important

4. **Image Compression**
   - Auto-compress uploaded images
   - Reduce storage costs
   - Faster page loads

5. **Email Templates**
   - Professional email design
   - Subscription reminders
   - Order notifications

6. **Admin Dashboard**
   - Subscription overview
   - Payment verification queue
   - Revenue metrics

---

## 📝 Next Steps

1. **Review this document** with stakeholders
2. **Approve subscription pricing** (GHS 100/month)
3. **Approve trial period** (14 days recommended)
4. **Assign development team**
5. **Begin Sprint 1**: Create new apps and models

---

**Document Version**: 1.0  
**Created**: November 26, 2025  
**Status**: 📋 AWAITING APPROVAL  
**Estimated Timeline**: 12 weeks
