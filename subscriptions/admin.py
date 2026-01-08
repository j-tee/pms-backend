from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SubscriptionPlan,
    Subscription,
    SubscriptionPayment,
    SubscriptionInvoice,
)
from .institutional_models import (
    InstitutionalPlan,
    InstitutionalSubscriber,
    InstitutionalAPIKey,
    InstitutionalAPIUsage,
    InstitutionalPayment,
    InstitutionalInquiry,
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'price_monthly',
        'trial_period_days',
        'max_product_images',
        'is_active',
        'display_order',
    ]
    list_filter = ['is_active', 'marketplace_listing', 'sales_tracking']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'price_monthly']
    
    fieldsets = (
        ('Plan Details', {
            'fields': ('name', 'description', 'price_monthly')
        }),
        ('Features', {
            'fields': (
                'max_product_images',
                'max_image_size_mb',
                'marketplace_listing',
                'sales_tracking',
                'analytics_dashboard',
                'api_access',
            )
        }),
        ('Trial & Status', {
            'fields': ('trial_period_days', 'is_active', 'display_order')
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'farm',
        'plan',
        'status',
        'next_billing_date',
        'created_at',
    ]
    list_filter = [
        'status',
        'auto_renew',
        'plan',
    ]
    search_fields = ['farm__farm_name', 'farm__owner__email']
    readonly_fields = [
        'created_at',
        'updated_at',
        'days_until_suspension',
    ]
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('farm', 'plan', 'status')
        }),
        ('Billing Cycle', {
            'fields': (
                'start_date',
                'current_period_start',
                'current_period_end',
                'next_billing_date',
            )
        }),
        ('Trial Period', {
            'fields': ('trial_start', 'trial_end'),
            'classes': ('collapse',)
        }),
        ('Payment Information', {
            'fields': ('last_payment_date', 'last_payment_amount')
        }),
        ('Grace Period & Suspension', {
            'fields': (
                'grace_period_days',
                'suspension_date',
                'days_until_suspension',
            ),
            'classes': ('collapse',)
        }),
        ('Cancellation', {
            'fields': (
                'cancelled_at',
                'cancellation_reason',
                'cancelled_by',
            ),
            'classes': ('collapse',)
        }),
        ('Reminders', {
            'fields': ('reminder_sent_at', 'reminder_count'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('auto_renew',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['suspend_subscriptions', 'reactivate_subscriptions']
    
    def suspend_subscriptions(self, request, queryset):
        for subscription in queryset:
            subscription.suspend(reason="Admin action")
        self.message_user(request, f"{queryset.count()} subscriptions suspended.")
    suspend_subscriptions.short_description = "Suspend selected subscriptions"
    
    def reactivate_subscriptions(self, request, queryset):
        for subscription in queryset:
            subscription.reactivate()
        self.message_user(request, f"{queryset.count()} subscriptions reactivated.")
    reactivate_subscriptions.short_description = "Reactivate selected subscriptions"


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'subscription',
        'amount',
        'payment_method',
        'status',
        'payment_date',
        'verified_by',
    ]
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = [
        'subscription__farm__farm_name',
        'payment_reference',
        'gateway_transaction_id',
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Subscription', {
            'fields': ('subscription',)
        }),
        ('Payment Details', {
            'fields': (
                'amount',
                'payment_method',
                'payment_reference',
                'status',
                'payment_date',
            )
        }),
        ('Period Covered', {
            'fields': ('period_start', 'period_end')
        }),
        ('Payment Gateway', {
            'fields': (
                'gateway_provider',
                'gateway_transaction_id',
                'gateway_response',
            ),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('verified_by', 'verified_at')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number',
        'subscription',
        'amount',
        'status',
        'issue_date',
        'due_date',
        'paid_date',
    ]
    list_filter = ['status', 'issue_date']
    search_fields = [
        'invoice_number',
        'subscription__farm__farm_name',
    ]
    readonly_fields = ['created_at', 'updated_at', 'issue_date']
    date_hierarchy = 'issue_date'
    
    fieldsets = (
        ('Invoice Information', {
            'fields': (
                'invoice_number',
                'subscription',
                'status',
            )
        }),
        ('Amount & Description', {
            'fields': ('amount', 'description')
        }),
        ('Billing Period', {
            'fields': ('billing_period_start', 'billing_period_end')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date', 'paid_date')
        }),
        ('Payment', {
            'fields': ('payment',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# INSTITUTIONAL DATA SUBSCRIPTION ADMIN
# =============================================================================

@admin.register(InstitutionalPlan)
class InstitutionalPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'tier',
        'price_monthly',
        'price_annually',
        'requests_per_day',
        'is_active',
        'display_order',
    ]
    list_filter = ['tier', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'price_monthly']
    
    fieldsets = (
        ('Plan Details', {
            'fields': ('name', 'tier', 'description', 'is_active', 'display_order')
        }),
        ('Pricing', {
            'fields': ('price_monthly', 'price_annually')
        }),
        ('API Quotas', {
            'fields': ('requests_per_day', 'requests_per_month')
        }),
        ('Data Access', {
            'fields': (
                'access_regional_aggregates',
                'access_constituency_data',
                'access_production_trends',
                'access_market_prices',
                'access_mortality_data',
                'access_supply_forecasts',
                'access_individual_farm_data',
            )
        }),
        ('Export & Support', {
            'fields': ('max_export_records', 'export_formats', 'support_level')
        }),
    )


@admin.register(InstitutionalSubscriber)
class InstitutionalSubscriberAdmin(admin.ModelAdmin):
    list_display = [
        'organization_name',
        'organization_category',
        'plan',
        'status',
        'is_verified',
        'next_billing_date',
        'created_at',
    ]
    list_filter = [
        'status',
        'organization_category',
        'plan',
        'is_verified',
        'billing_cycle',
    ]
    search_fields = [
        'organization_name',
        'contact_name',
        'contact_email',
    ]
    readonly_fields = ['created_at', 'updated_at', 'verified_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Organization', {
            'fields': (
                'organization_name',
                'organization_category',
                'registration_number',
                'website',
            )
        }),
        ('Primary Contact', {
            'fields': (
                'contact_name',
                'contact_email',
                'contact_phone',
                'contact_position',
            )
        }),
        ('Technical Contact', {
            'fields': ('tech_contact_name', 'tech_contact_email'),
            'classes': ('collapse',)
        }),
        ('Address', {
            'fields': ('address', 'city', 'region'),
            'classes': ('collapse',)
        }),
        ('Subscription', {
            'fields': (
                'plan',
                'status',
                'billing_cycle',
                'subscription_start',
                'current_period_start',
                'current_period_end',
                'next_billing_date',
            )
        }),
        ('Trial', {
            'fields': ('trial_days', 'trial_start', 'trial_end'),
            'classes': ('collapse',)
        }),
        ('Data Access', {
            'fields': ('preferred_regions', 'data_use_purpose')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verified_at')
        }),
        ('Admin', {
            'fields': ('admin_notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InstitutionalAPIKey)
class InstitutionalAPIKeyAdmin(admin.ModelAdmin):
    list_display = [
        'subscriber',
        'name',
        'key_prefix',
        'is_active',
        'last_used_at',
        'total_requests',
        'created_at',
    ]
    list_filter = ['is_active', 'subscriber']
    search_fields = ['subscriber__organization_name', 'name', 'key_prefix']
    readonly_fields = ['key_prefix', 'key_hash', 'last_used_at', 'last_used_ip', 'total_requests', 'created_at']


@admin.register(InstitutionalPayment)
class InstitutionalPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number',
        'subscriber',
        'amount',
        'payment_status',
        'invoice_date',
        'paid_at',
    ]
    list_filter = ['payment_status', 'payment_method']
    search_fields = ['subscriber__organization_name', 'invoice_number']
    readonly_fields = ['created_at']
    date_hierarchy = 'invoice_date'


@admin.register(InstitutionalInquiry)
class InstitutionalInquiryAdmin(admin.ModelAdmin):
    list_display = [
        'organization_name',
        'contact_name',
        'organization_category',
        'status',
        'interested_plan',
        'assigned_to',
        'created_at',
    ]
    list_filter = ['status', 'organization_category', 'interested_plan']
    search_fields = ['organization_name', 'contact_name', 'contact_email']
    readonly_fields = ['created_at', 'updated_at', 'converted_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Organization', {
            'fields': ('organization_name', 'organization_category', 'website')
        }),
        ('Contact', {
            'fields': ('contact_name', 'contact_email', 'contact_phone', 'contact_position')
        }),
        ('Interest', {
            'fields': ('interested_plan', 'data_use_purpose', 'message', 'source')
        }),
        ('Status & Follow-up', {
            'fields': ('status', 'assigned_to', 'follow_up_notes', 'next_follow_up')
        }),
        ('Conversion', {
            'fields': ('converted_subscriber', 'converted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

