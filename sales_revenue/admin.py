from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils import timezone
from .models import PlatformSettings, Customer, EggSale, BirdSale, Payment, FarmerPayout, FraudAlert


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for platform-wide settings.
    Singleton - only one instance allowed.
    """
    list_display = [
        'get_commission_summary',
        'paystack_fee_bearer',
        'paystack_settlement_schedule',
        'get_refund_policy',
        'updated_at',
        'last_modified_by'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Commission Structure', {
            'fields': (
                ('commission_tier_1_percentage', 'commission_tier_1_threshold'),
                ('commission_tier_2_percentage', 'commission_tier_2_threshold'),
                'commission_tier_3_percentage',
                'commission_minimum_amount',
            ),
            'description': 'Configure tiered commission rates. Example: 5% for sales < GHS 100, 3% for GHS 100-500, 2% for > GHS 500'
        }),
        ('Paystack Configuration', {
            'fields': (
                'paystack_fee_bearer',
                'paystack_settlement_schedule',
            ),
            'description': 'Configure who pays Paystack fees and settlement timing'
        }),
        ('Payment Retry Settings', {
            'fields': (
                'payment_retry_max_attempts',
                'payment_retry_delay_seconds',
            ),
            'description': 'Configure automatic payment retry behavior'
        }),
        ('Refund Settings', {
            'fields': (
                'refund_eligibility_hours',
                'payment_auto_refund_hours',
                'enable_refunds',
                'enable_auto_refunds',
            ),
            'description': 'Configure customer refund policies'
        }),
        ('Feature Flags', {
            'fields': (
                'enable_instant_settlements',
            ),
            'description': 'Enable or disable platform features'
        }),
        ('Metadata', {
            'fields': (
                'last_modified_by',
                'notes',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Singleton - only allow creation if no instance exists
        return not PlatformSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False
    
    def save_model(self, request, obj, form, change):
        # Track who modified the settings
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_commission_summary(self, obj):
        """Display commission tiers summary"""
        return format_html(
            '<strong>Tier 1:</strong> {}% (&lt; GHS {})<br>'
            '<strong>Tier 2:</strong> {}% (GHS {}-{})<br>'
            '<strong>Tier 3:</strong> {}% (&gt; GHS {})<br>'
            '<strong>Min:</strong> GHS {}',
            obj.commission_tier_1_percentage,
            obj.commission_tier_1_threshold,
            obj.commission_tier_2_percentage,
            obj.commission_tier_1_threshold,
            obj.commission_tier_2_threshold,
            obj.commission_tier_3_percentage,
            obj.commission_tier_2_threshold,
            obj.commission_minimum_amount
        )
    get_commission_summary.short_description = 'Commission Tiers'
    
    def get_refund_policy(self, obj):
        """Display refund policy summary"""
        if not obj.enable_refunds:
            return format_html('<span style="color: red;">❌ Disabled</span>')
        
        return format_html(
            'Request window: {} hrs<br>Auto-refund: {} hrs {}',
            obj.refund_eligibility_hours,
            obj.payment_auto_refund_hours,
            '✅' if obj.enable_auto_refunds else '❌'
        )
    get_refund_policy.short_description = 'Refund Policy'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'get_full_name',
        'business_name',
        'customer_type',
        'phone_number',
        'mobile_money_provider',
        'total_orders',
        'total_purchases',
        'is_active',
        'created_at'
    ]
    list_filter = ['customer_type', 'mobile_money_provider', 'is_active', 'created_at']
    search_fields = [
        'first_name',
        'last_name',
        'business_name',
        'phone_number',
        'mobile_money_number',
        'email'
    ]
    readonly_fields = ['total_purchases', 'total_orders', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('farm', 'customer_type', 'first_name', 'last_name', 'business_name')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'email', 'location', 'delivery_address')
        }),
        ('Payment Information', {
            'fields': (
                'mobile_money_number',
                'mobile_money_provider',
                'mobile_money_account_name'
            )
        }),
        ('Statistics', {
            'fields': ('total_purchases', 'total_orders', 'is_active')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EggSale)
class EggSaleAdmin(admin.ModelAdmin):
    list_display = [
        'sale_date',
        'get_customer_name',
        'quantity',
        'unit',
        'price_per_unit',
        'total_amount',
        'platform_commission',
        'farmer_payout',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'unit', 'sale_date', 'created_at']
    search_fields = [
        'customer__first_name',
        'customer__last_name',
        'customer__business_name',
        'notes'
    ]
    readonly_fields = [
        'subtotal',
        'platform_commission',
        'paystack_fee',
        'farmer_payout',
        'total_amount',
        'created_at',
        'updated_at'
    ]
    date_hierarchy = 'sale_date'
    
    fieldsets = (
        ('Sale Information', {
            'fields': (
                'farm',
                'customer',
                'daily_production',
                'sale_date',
                'status'
            )
        }),
        ('Product Details', {
            'fields': ('quantity', 'unit', 'price_per_unit')
        }),
        ('Calculated Amounts', {
            'fields': (
                'subtotal',
                'platform_commission',
                'paystack_fee',
                'farmer_payout',
                'total_amount'
            ),
            'classes': ('collapse',)
        }),
        ('Payment', {
            'fields': ('payment',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer_name(self, obj):
        return obj.customer.get_full_name()
    get_customer_name.short_description = 'Customer'


@admin.register(BirdSale)
class BirdSaleAdmin(admin.ModelAdmin):
    list_display = [
        'sale_date',
        'get_customer_name',
        'bird_type',
        'quantity',
        'price_per_bird',
        'total_amount',
        'platform_commission',
        'farmer_payout',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'bird_type', 'sale_date', 'created_at']
    search_fields = [
        'customer__first_name',
        'customer__last_name',
        'customer__business_name',
        'notes'
    ]
    readonly_fields = [
        'subtotal',
        'platform_commission',
        'paystack_fee',
        'farmer_payout',
        'total_amount',
        'created_at',
        'updated_at'
    ]
    date_hierarchy = 'sale_date'
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('farm', 'customer', 'flock', 'sale_date', 'status')
        }),
        ('Product Details', {
            'fields': ('bird_type', 'quantity', 'price_per_bird')
        }),
        ('Calculated Amounts', {
            'fields': (
                'subtotal',
                'platform_commission',
                'paystack_fee',
                'farmer_payout',
                'total_amount'
            ),
            'classes': ('collapse',)
        }),
        ('Payment', {
            'fields': ('payment',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer_name(self, obj):
        return obj.customer.get_full_name()
    get_customer_name.short_description = 'Customer'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'paystack_reference',
        'get_customer_name',
        'amount',
        'payment_method',
        'status',
        'retry_count',
        'refund_requested',
        'created_at'
    ]
    list_filter = [
        'status',
        'payment_method',
        'refund_requested',
        'created_at'
    ]
    search_fields = [
        'paystack_reference',
        'paystack_transaction_id',
        'customer__first_name',
        'customer__last_name',
        'customer__business_name'
    ]
    readonly_fields = [
        'paystack_reference',
        'paystack_access_code',
        'paystack_transaction_id',
        'payment_response',
        'created_at',
        'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'farm',
                'customer',
                'amount',
                'payment_method',
                'status'
            )
        }),
        ('Paystack Integration', {
            'fields': (
                'paystack_reference',
                'paystack_access_code',
                'paystack_transaction_id',
                'payment_response'
            )
        }),
        ('Retry Mechanism', {
            'fields': (
                'retry_count',
                'last_retry_at',
                'next_retry_at'
            ),
            'classes': ('collapse',)
        }),
        ('Refund Information', {
            'fields': (
                'refund_requested',
                'refund_requested_at',
                'refund_reason',
                'refunded_amount',
                'refunded_at'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer_name(self, obj):
        return obj.customer.get_full_name()
    get_customer_name.short_description = 'Customer'
    
    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'success': 'green',
            'failed': 'red',
            'refunded': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'


@admin.register(FarmerPayout)
class FarmerPayoutAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_name',
        'amount',
        'mobile_money_provider',
        'status',
        'retry_count',
        'settlement_date',
        'created_at'
    ]
    list_filter = ['status', 'mobile_money_provider', 'created_at', 'settlement_date']
    search_fields = [
        'recipient_name',
        'recipient_mobile_number',
        'paystack_transfer_code',
        'current_hash'
    ]
    readonly_fields = [
        'paystack_transfer_code',
        'paystack_transfer_id',
        'previous_hash',
        'current_hash',
        'payout_response',
        'created_at',
        'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Payout Information', {
            'fields': ('farm', 'egg_sale', 'bird_sale', 'amount', 'status')
        }),
        ('Recipient Details', {
            'fields': (
                'recipient_name',
                'recipient_mobile_number',
                'mobile_money_provider'
            )
        }),
        ('Paystack Transfer', {
            'fields': (
                'paystack_transfer_code',
                'paystack_transfer_id',
                'settlement_date',
                'payout_response'
            )
        }),
        ('Retry Mechanism', {
            'fields': ('retry_count', 'last_retry_at'),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('previous_hash', 'current_hash'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'success': 'green',
            'failed': 'red',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'




@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    """Admin interface for fraud detection alerts"""
    
    list_display = [
        'farm', 'detected_at', 'risk_level_badge', 
        'risk_score', 'alert_count', 'status', 'reviewed_by'
    ]
    list_filter = ['risk_level', 'status', 'detected_at']
    search_fields = ['farm__name', 'farm__owner__phone', 'reviewed_by__username']
    readonly_fields = [
        'farm', 'detected_at', 'risk_score', 'risk_level',
        'alerts', 'analysis_period_days', 'formatted_alerts'
    ]
    date_hierarchy = 'detected_at'
    
    fieldsets = [
        ('Detection Info', {
            'fields': [
                'farm', 'detected_at', 'analysis_period_days',
                'risk_score', 'risk_level', 'alert_count'
            ]
        }),
        ('Alert Details', {
            'fields': ['formatted_alerts'],
            'classes': ['collapse'],
        }),
        ('Review', {
            'fields': [
                'status', 'reviewed_by', 'reviewed_at', 
                'review_notes', 'action_taken'
            ]
        }),
    ]
    
    actions = ['mark_as_false_positive', 'mark_as_confirmed', 'schedule_audit']
    
    def risk_level_badge(self, obj):
        """Display risk level with color coding"""
        colors = {
            'CLEAN': '#28a745',      # Green
            'LOW': '#ffc107',        # Yellow
            'MEDIUM': '#fd7e14',     # Orange
            'HIGH': '#dc3545',       # Red
            'CRITICAL': '#721c24',   # Dark red
        }
        color = colors.get(obj.risk_level, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.risk_level
        )
    risk_level_badge.short_description = 'Risk Level'
    
    def alert_count(self, obj):
        """Number of fraud indicators detected"""
        return len(obj.alerts) if obj.alerts else 0
    alert_count.short_description = '# Alerts'
    
    def formatted_alerts(self, obj):
        """Display alerts in a formatted, readable way"""
        if not obj.alerts:
            return format_html('<p style="color: #28a745;">No fraud indicators detected</p>')
        
        html = '<div style="font-family: monospace;">'
        
        for i, alert in enumerate(obj.alerts, 1):
            severity = alert.get('severity', 'MEDIUM')
            alert_type = alert.get('type', 'Unknown')
            message = alert.get('message', 'No details')
            details = alert.get('details', {})
            
            # Color code by severity
            severity_colors = {
                'LOW': '#ffc107',
                'MEDIUM': '#fd7e14',
                'HIGH': '#dc3545',
                'CRITICAL': '#721c24',
            }
            color = severity_colors.get(severity, '#6c757d')
            
            html += f'''
            <div style="margin-bottom: 15px; padding: 10px; 
                        border-left: 4px solid {color}; 
                        background-color: #f8f9fa;">
                <strong style="color: {color};">Alert #{i}: {alert_type}</strong><br/>
                <em>{message}</em><br/>
            '''
            
            if details:
                html += '<ul style="margin-top: 5px;">'
                for key, value in details.items():
                    if isinstance(value, float):
                        html += f'<li><strong>{key}:</strong> {value:.2f}</li>'
                    else:
                        html += f'<li><strong>{key}:</strong> {value}</li>'
                html += '</ul>'
            
            html += '</div>'
        
        html += '</div>'
        return format_html(html)
    formatted_alerts.short_description = 'Alert Details'
    
    # Admin actions
    def mark_as_false_positive(self, request, queryset):
        """Mark selected alerts as false positives"""
        updated = queryset.update(
            status='false_positive',
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            review_notes='Marked as false positive by admin',
        )
        self.message_user(
            request,
            f'{updated} alert(s) marked as false positive.',
            messages.SUCCESS
        )
    mark_as_false_positive.short_description = 'Mark as false positive'
    
    def mark_as_confirmed(self, request, queryset):
        """Mark selected alerts as confirmed fraud"""
        updated = queryset.update(
            status='confirmed',
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(
            request,
            f'{updated} alert(s) confirmed as fraud. Consider scheduling audits.',
            messages.WARNING
        )
    mark_as_confirmed.short_description = 'Confirm as fraud'
    
    def schedule_audit(self, request, queryset):
        """Mark alerts as needing physical audit"""
        updated = queryset.update(
            status='under_review',
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            review_notes='Physical audit scheduled',
            action_taken='Audit scheduled by admin',
            audit_scheduled=True,
        )
        self.message_user(
            request,
            f'{updated} alert(s) scheduled for physical audit.',
            messages.INFO
        )
    schedule_audit.short_description = 'Schedule physical audit'
