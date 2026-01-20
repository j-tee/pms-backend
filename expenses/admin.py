"""
Admin configuration for Expense Tracking models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from decimal import Decimal

from .models import (
    ExpenseSubCategory,
    Expense,
    LaborRecord,
    UtilityRecord,
    MortalityLossRecord,
    RecurringExpenseTemplate,
    ExpenseSummary,
)


class ExpenseInline(admin.TabularInline):
    """Inline for viewing expenses in related models"""
    model = Expense
    extra = 0
    readonly_fields = ['expense_date', 'category', 'description', 'total_amount', 'is_recurring']
    fields = ['expense_date', 'category', 'description', 'total_amount', 'is_recurring']
    can_delete = False
    max_num = 10
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ExpenseSubCategory)
class ExpenseSubCategoryAdmin(admin.ModelAdmin):
    """Admin for expense sub-categories"""
    list_display = ['name', 'farm', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description', 'farm__farm_name']
    list_per_page = 50
    ordering = ['farm', 'category', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('farm', 'name', 'category', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Admin for expense records"""
    list_display = [
        'expense_date', 'farm_name', 'category_badge', 'description_short',
        'amount_display', 'flock_name', 'is_recurring', 'created_at'
    ]
    list_filter = [
        'category', 'is_recurring', 'expense_date', 'payment_status'
    ]
    search_fields = [
        'description', 'notes', 'receipt_number',
        'farm__farm_name', 'flock__flock_number'
    ]
    date_hierarchy = 'expense_date'
    list_per_page = 50
    ordering = ['-expense_date', '-created_at']
    
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('farm', 'flock', 'expense_date', 'category', 'subcategory')
        }),
        ('Expense Details', {
            'fields': ('description', 'quantity', 'unit', 'unit_cost', 'total_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'payment_method', 'payee_name', 'receipt_number')
        }),
        ('Recurrence', {
            'fields': ('is_recurring', 'frequency'),
            'classes': ('collapse',),
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def farm_name(self, obj):
        return obj.farm.farm_name
    farm_name.short_description = 'Farm'
    farm_name.admin_order_field = 'farm__farm_name'
    
    def flock_name(self, obj):
        if obj.flock:
            return f"{obj.flock.flock_number}"
        return '-'
    flock_name.short_description = 'Flock'
    
    def description_short(self, obj):
        if len(obj.description) > 40:
            return f"{obj.description[:40]}..."
        return obj.description
    description_short.short_description = 'Description'
    
    def amount_display(self, obj):
        return format_html('<strong>GHS {}</strong>', f'{obj.total_amount:,.2f}')
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'total_amount'
    
    def category_badge(self, obj):
        colors = {
            'LABOR': '#3498db',
            'UTILITIES': '#9b59b6',
            'BEDDING': '#e67e22',
            'TRANSPORT': '#1abc9c',
            'MAINTENANCE': '#e74c3c',
            'OVERHEAD': '#95a5a6',
            'MORTALITY_LOSS': '#c0392b',
            'MISCELLANEOUS': '#7f8c8d',
        }
        color = colors.get(obj.category, '#34495e')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_category_display()
        )
    category_badge.short_description = 'Category'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(LaborRecord)
class LaborRecordAdmin(admin.ModelAdmin):
    """Admin for labor/wage records"""
    list_display = [
        'work_date', 'farm_name', 'worker_name', 'worker_type',
        'hours_worked', 'total_pay_display', 'task_type'
    ]
    list_filter = ['worker_type', 'task_type', 'work_date']
    search_fields = ['worker_name', 'farm__farm_name']
    date_hierarchy = 'work_date'
    list_per_page = 50
    ordering = ['-work_date']
    
    readonly_fields = ['created_at', 'updated_at', 'base_pay', 'overtime_pay', 'total_pay']
    
    fieldsets = (
        ('Farm & Worker', {
            'fields': ('expense', 'farm', 'flock', 'worker_name', 'worker_type', 'worker_contact')
        }),
        ('Work Details', {
            'fields': ('work_date', 'task_type', 'hours_worked', 'hourly_rate')
        }),
        ('Overtime', {
            'fields': ('overtime_hours', 'overtime_rate'),
            'classes': ('collapse',),
        }),
        ('Calculated', {
            'fields': ('base_pay', 'overtime_pay', 'total_pay'),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def farm_name(self, obj):
        return obj.farm.farm_name
    farm_name.short_description = 'Farm'
    
    def total_pay_display(self, obj):
        return format_html('GHS {}', f'{obj.total_pay:,.2f}')
    total_pay_display.short_description = 'Amount'
    total_pay_display.admin_order_field = 'total_pay'


@admin.register(UtilityRecord)
class UtilityRecordAdmin(admin.ModelAdmin):
    """Admin for utility (electricity, water) records"""
    list_display = [
        'billing_period_display', 'farm_name', 'utility_type_badge',
        'usage_display', 'provider'
    ]
    list_filter = ['utility_type', 'billing_period_start']
    search_fields = ['farm__farm_name', 'account_number', 'provider']
    date_hierarchy = 'billing_period_start'
    list_per_page = 50
    ordering = ['-billing_period_start']
    
    readonly_fields = ['created_at', 'updated_at', 'units_consumed']
    
    fieldsets = (
        ('Farm & Utility', {
            'fields': ('expense', 'farm', 'utility_type')
        }),
        ('Billing Period', {
            'fields': ('billing_period_start', 'billing_period_end')
        }),
        ('Usage', {
            'fields': ('previous_reading', 'current_reading', 'units_consumed', 
                      'unit_of_measure', 'rate_per_unit')
        }),
        ('Account Details', {
            'fields': ('provider', 'account_number'),
            'classes': ('collapse',),
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def farm_name(self, obj):
        return obj.farm.farm_name
    farm_name.short_description = 'Farm'
    
    def billing_period_display(self, obj):
        if obj.billing_period_start and obj.billing_period_end:
            return f"{obj.billing_period_start} to {obj.billing_period_end}"
        return obj.expense.expense_date if obj.expense else '-'
    billing_period_display.short_description = 'Billing Period'
    
    def utility_type_badge(self, obj):
        colors = {
            'ELECTRICITY': '#f1c40f',
            'WATER': '#3498db',
            'GAS': '#e74c3c',
            'FUEL': '#e67e22',
            'INTERNET': '#9b59b6',
            'OTHER': '#95a5a6',
        }
        color = colors.get(obj.utility_type, '#34495e')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_utility_type_display()
        )
    utility_type_badge.short_description = 'Utility'
    
    def usage_display(self, obj):
        if obj.units_consumed:
            return f"{obj.units_consumed:,.2f} {obj.unit_of_measure}"
        return '-'
    usage_display.short_description = 'Usage'


@admin.register(MortalityLossRecord)
class MortalityLossRecordAdmin(admin.ModelAdmin):
    """Admin for mortality economic loss records"""
    list_display = [
        'mortality_date', 'farm_name', 'flock_name', 'birds_lost',
        'loss_value_display', 'cause_of_death'
    ]
    list_filter = ['cause_of_death', 'mortality_date']
    search_fields = ['farm__farm_name', 'flock__flock_number', 'notes']
    date_hierarchy = 'mortality_date'
    list_per_page = 50
    ordering = ['-mortality_date']
    
    readonly_fields = ['created_at', 'updated_at', 'total_loss_value']
    
    fieldsets = (
        ('Farm & Flock', {
            'fields': ('expense', 'farm', 'flock', 'mortality_record')
        }),
        ('Loss Details', {
            'fields': ('mortality_date', 'birds_lost', 'cause_of_death', 'age_at_death_weeks')
        }),
        ('Cost Breakdown', {
            'fields': ('acquisition_cost_per_bird', 'feed_cost_invested', 
                      'other_costs_invested', 'potential_revenue_lost', 'total_loss_value')
        }),
        ('Notes', {
            'fields': ('notes',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def farm_name(self, obj):
        return obj.farm.farm_name
    farm_name.short_description = 'Farm'
    
    def flock_name(self, obj):
        if obj.flock:
            return obj.flock.flock_number
        return '-'
    flock_name.short_description = 'Flock'
    
    def loss_value_display(self, obj):
        return format_html('<strong style="color: #c0392b;">GHS {}</strong>', f'{obj.total_loss_value:,.2f}')
    loss_value_display.short_description = 'Loss Value'
    loss_value_display.admin_order_field = 'total_loss_value'


@admin.register(RecurringExpenseTemplate)
class RecurringExpenseTemplateAdmin(admin.ModelAdmin):
    """Admin for recurring expense templates"""
    list_display = [
        'name', 'farm_name', 'category_badge', 'amount_display',
        'frequency', 'is_active', 'next_due_date', 'last_generated_date'
    ]
    list_filter = ['category', 'frequency', 'is_active']
    search_fields = ['name', 'description', 'farm__farm_name']
    list_per_page = 50
    ordering = ['farm', '-is_active', 'name']
    
    readonly_fields = ['created_at', 'updated_at', 'last_generated_date', 'estimated_amount']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('farm', 'flock', 'name', 'category', 'subcategory', 'description')
        }),
        ('Amount', {
            'fields': ('quantity', 'unit', 'unit_cost', 'estimated_amount', 'payee_name', 'payee_contact')
        }),
        ('Schedule', {
            'fields': ('frequency', 'start_date', 'end_date', 'next_due_date')
        }),
        ('Status', {
            'fields': ('is_active', 'last_generated_date')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def farm_name(self, obj):
        return obj.farm.farm_name
    farm_name.short_description = 'Farm'
    
    def amount_display(self, obj):
        return format_html('GHS {}', f'{obj.estimated_amount:,.2f}')
    amount_display.short_description = 'Amount'
    
    def category_badge(self, obj):
        return format_html(
            '<span style="padding: 2px 8px;">{}</span>',
            obj.get_category_display()
        )
    category_badge.short_description = 'Category'


@admin.register(ExpenseSummary)
class ExpenseSummaryAdmin(admin.ModelAdmin):
    """Admin for expense summaries (read-only analytics view)"""
    list_display = [
        'period_end', 'farm_name', 'period_type', 'total_display',
        'top_category', 'expense_count'
    ]
    list_filter = ['period_type', 'period_end']
    search_fields = ['farm__farm_name']
    date_hierarchy = 'period_end'
    list_per_page = 50
    ordering = ['-period_end', 'farm']
    
    readonly_fields = [
        'farm', 'flock', 'period_start', 'period_end', 'period_type',
        'labor_total', 'utilities_total', 'bedding_total', 'transport_total',
        'maintenance_total', 'overhead_total', 'mortality_loss_total', 
        'miscellaneous_total', 'grand_total', 'expense_count', 'calculated_at'
    ]
    
    fieldsets = (
        ('Summary Info', {
            'fields': ('farm', 'flock', 'period_start', 'period_end', 'period_type')
        }),
        ('Cost Breakdown', {
            'fields': (
                'labor_total', 'utilities_total', 'bedding_total', 'transport_total',
                'maintenance_total', 'overhead_total', 'mortality_loss_total', 
                'miscellaneous_total'
            )
        }),
        ('Totals', {
            'fields': ('grand_total', 'expense_count', 'calculated_at')
        }),
    )
    
    def has_add_permission(self, request):
        # Summaries are auto-generated, not manually added
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def farm_name(self, obj):
        return obj.farm.farm_name
    farm_name.short_description = 'Farm'
    
    def total_display(self, obj):
        return format_html('<strong>GHS {}</strong>', f'{obj.grand_total:,.2f}')
    total_display.short_description = 'Total'
    total_display.admin_order_field = 'grand_total'
    
    def top_category(self, obj):
        """Show the highest expense category"""
        categories = [
            ('Labor', obj.labor_total),
            ('Utilities', obj.utilities_total),
            ('Bedding', obj.bedding_total),
            ('Transport', obj.transport_total),
            ('Maintenance', obj.maintenance_total),
            ('Overhead', obj.overhead_total),
            ('Mortality', obj.mortality_loss_total),
            ('Misc', obj.miscellaneous_total),
        ]
        top = max(categories, key=lambda x: x[1])
        if top[1] > 0:
            return f"{top[0]} (GHS {top[1]:,.2f})"
        return '-'
    top_category.short_description = 'Top Category'
