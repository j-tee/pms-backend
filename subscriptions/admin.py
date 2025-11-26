from django.contrib import admin
from django.utils.html import format_html
from .models import (
    GovernmentSubsidyProgram,
    SubscriptionPlan,
    Subscription,
    SubscriptionPayment,
    SubscriptionInvoice,
)


@admin.register(GovernmentSubsidyProgram)
class GovernmentSubsidyProgramAdmin(admin.ModelAdmin):
    list_display = [
        'program_name',
        'program_code',
        'start_date',
        'end_date',
        'current_farmers_count',
        'max_farmers',
        'subsidy_percentage',
        'is_active_display',
    ]
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['program_name', 'program_code', 'implementing_agency']
    readonly_fields = ['current_farmers_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Program Information', {
            'fields': ('program_name', 'program_code', 'description')
        }),
        ('Program Period', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Subsidy Details', {
            'fields': (
                'subsidy_percentage',
                'max_farmers',
                'current_farmers_count',
            )
        }),
        ('Administering Organization', {
            'fields': (
                'implementing_agency',
                'contact_person',
                'contact_email',
                'contact_phone',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        if obj.is_currently_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_display.short_description = 'Status'


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
        'is_subsidized_display',
        'next_billing_date',
        'created_at',
    ]
    list_filter = [
        'status',
        'is_subsidized',
        'auto_renew',
        'plan',
    ]
    search_fields = ['farm__farm_name', 'farm__owner__email']
    readonly_fields = [
        'created_at',
        'updated_at',
        'days_until_suspension',
        'requires_payment',
    ]
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('farm', 'plan', 'status')
        }),
        ('Government Subsidy', {
            'fields': ('is_subsidized', 'subsidy_program'),
            'classes': ('collapse',)
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
            'fields': ('auto_renew', 'requires_payment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_subsidized_display(self, obj):
        if obj.is_subsidized:
            return format_html(
                '<span style="color: blue;">✓ Government Subsidized</span>'
            )
        return format_html('<span style="color: gray;">Self-Paid</span>')
    is_subsidized_display.short_description = 'Subsidy Status'
    
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
