"""
Feed Inventory Admin Configuration

Admin interface for managing feed types, suppliers, purchases,
inventory levels, and consumption tracking.
"""

from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    FeedType,
    FeedPurchase,
    FeedInventory,
    FeedConsumption
)


@admin.register(FeedType)
class FeedTypeAdmin(admin.ModelAdmin):
    """Admin interface for Feed Types."""
    
    list_display = [
        'name',
        'category_badge',
        'form',
        'protein_content',
        'manufacturer',
        'active_status',
        'standard_price_per_kg',
    ]
    
    list_filter = [
        'category',
        'form',
        'is_active',
    ]
    
    search_fields = [
        'name',
        'manufacturer',
    ]
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'category', 'form', 'manufacturer', 'description')
        }),
        ('Nutritional Information', {
            'fields': (
                'protein_content',
                'energy_content',
                'calcium_content',
                'phosphorus_content',
            )
        }),
        ('Usage Guidelines', {
            'fields': (
                'recommended_age_weeks_min',
                'recommended_age_weeks_max',
                'daily_consumption_per_bird_grams',
            )
        }),
        ('Pricing', {
            'fields': ('standard_price_per_kg',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def category_badge(self, obj):
        """Display category with color-coded badge."""
        colors = {
            'STARTER': '#28a745',
            'GROWER': '#007bff',
            'LAYER': '#ffc107',
            'BROILER_STARTER': '#17a2b8',
            'BROILER_FINISHER': '#dc3545',
            'BREEDER': '#6f42c1',
            'SUPPLEMENT': '#fd7e14',
            'MEDICATION': '#e83e8c',
        }
        color = colors.get(obj.category, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_badge.short_description = 'Category'
    
    def active_status(self, obj):
        """Display active status with badge."""
        if obj.is_active:
            return format_html(
                '<span style="color: green;">●</span> Active'
            )
        return format_html(
            '<span style="color: red;">●</span> Inactive'
        )
    active_status.short_description = 'Status'


@admin.register(FeedPurchase)
class FeedPurchaseAdmin(admin.ModelAdmin):
    """Admin interface for Feed Purchases."""
    
    list_display = [
        'batch_number',
        'purchase_date',
        'farm_link',
        'supplier',
        'feed_type',
        'quantity_kg',
        'stock_balance_kg',
        'total_cost',
        'payment_status_badge',
        'delivery_date',
    ]
    
    list_filter = [
        'payment_status',
        'purchase_date',
    ]
    
    search_fields = [
        'farm__name',
        'supplier',
        'feed_type__name',
        'invoice_number',
    ]
    
    readonly_fields = ['id', 'batch_number', 'quantity_kg', 'unit_price', 'stock_balance_kg', 'total_cost', 'created_at', 'updated_at', 'created_by']
    
    date_hierarchy = 'purchase_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'batch_number', 'farm', 'supplier', 'supplier_contact', 'feed_type', 'brand', 'purchase_date', 'invoice_number', 'receipt_number')
        }),
        ('Quantity and Pricing', {
            'fields': ('quantity_bags', 'bag_weight_kg', 'quantity_kg', 'unit_cost_ghs', 'unit_price', 'total_cost')
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'payment_method', 'amount_paid', 'payment_due_date')
        }),
        ('Delivery Information', {
            'fields': ('delivery_date', 'received_by')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def farm_link(self, obj):
        """Display clickable farm link."""
        url = reverse('admin:farms_farm_change', args=[obj.farm.id])
        return format_html('<a href="{}">{}</a>', url, obj.farm.name)
    farm_link.short_description = 'Farm'
    
    def payment_status_badge(self, obj):
        """Display payment status with color-coded badge."""
        colors = {
            'PENDING': '#ffc107',
            'PARTIAL': '#17a2b8',
            'PAID': '#28a745',
            'OVERDUE': '#dc3545',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment Status'
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by on save."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FeedInventory)
class FeedInventoryAdmin(admin.ModelAdmin):
    """Admin interface for Feed Inventory."""
    
    list_display = [
        'farm_link',
        'feed_type',
        'current_stock_kg',
        'stock_status',
        'total_value',
        'last_purchase_date',
        'last_consumption_date',
    ]
    
    list_filter = [
        'low_stock_alert',
    ]
    
    search_fields = [
        'farm__name',
        'feed_type__name',
    ]
    
    readonly_fields = ['id', 'total_value', 'low_stock_alert', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'farm', 'feed_type', 'storage_location')
        }),
        ('Stock Levels', {
            'fields': (
                'current_stock_kg',
                'min_stock_level',
                'max_stock_level',
                'low_stock_alert',
            )
        }),
        ('Stock Value', {
            'fields': ('average_cost_per_kg', 'total_value')
        }),
        ('Stock Movement', {
            'fields': ('last_purchase_date', 'last_consumption_date'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def farm_link(self, obj):
        """Display clickable farm link."""
        url = reverse('admin:farms_farm_change', args=[obj.farm.id])
        return format_html('<a href="{}">{}</a>', url, obj.farm.name)
    farm_link.short_description = 'Farm'
    
    def stock_status(self, obj):
        """Display stock status with visual indicator."""
        percentage = (obj.current_stock_kg / obj.max_stock_level * 100) if obj.max_stock_level > 0 else 0
        
        if obj.low_stock_alert:
            color = '#dc3545'
            status = 'LOW'
        elif percentage > 80:
            color = '#28a745'
            status = 'GOOD'
        elif percentage > 50:
            color = '#ffc107'
            status = 'OK'
        else:
            color = '#fd7e14'
            status = 'MEDIUM'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span> {:.0f}%',
            color,
            status,
            percentage
        )
    stock_status.short_description = 'Stock Status'


@admin.register(FeedConsumption)
class FeedConsumptionAdmin(admin.ModelAdmin):
    """Admin interface for Feed Consumption."""
    
    list_display = [
        'date',
        'farm_link',
        'flock_link',
        'feed_type',
        'quantity_consumed_kg',
        'consumption_per_bird_grams',
        'total_cost',
    ]
    
    list_filter = [
        'date',
    ]
    
    search_fields = [
        'farm__name',
        'flock__name',
        'feed_type__name',
    ]
    
    readonly_fields = [
        'id',
        'date',
        'farm',
        'flock',
        'total_cost',
        'consumption_per_bird_grams',
        'created_at',
        'updated_at'
    ]
    
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'daily_production', 'farm', 'flock', 'feed_type', 'date')
        }),
        ('Consumption Details', {
            'fields': (
                'quantity_consumed_kg',
                'birds_count_at_consumption',
                'consumption_per_bird_grams',
            )
        }),
        ('Cost Tracking', {
            'fields': ('cost_per_kg', 'total_cost')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def farm_link(self, obj):
        """Display clickable farm link."""
        url = reverse('admin:farms_farm_change', args=[obj.farm.id])
        return format_html('<a href="{}">{}</a>', url, obj.farm.name)
    farm_link.short_description = 'Farm'
    
    def flock_link(self, obj):
        """Display clickable flock link."""
        url = reverse('admin:flock_management_flock_change', args=[obj.flock.id])
        return format_html('<a href="{}">{}</a>', url, obj.flock.name)
    flock_link.short_description = 'Flock'
