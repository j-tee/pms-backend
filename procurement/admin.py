from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum
from django.contrib import admin
from core.admin_site import yea_admin_site
from .models import ProcurementOrder, OrderAssignment, DeliveryConfirmation, ProcurementInvoice


class ProcurementOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'title', 'status_badge', 'priority_badge',
        'production_type', 'quantity_progress', 'fulfillment_badge',
        'delivery_deadline_display', 'total_budget_display', 'created_by'
    ]
    list_filter = ['status', 'priority', 'production_type', 'created_at', 'delivery_deadline']
    search_fields = ['order_number', 'title', 'description']
    readonly_fields = [
        'order_number', 'created_at', 'updated_at', 'published_at',
        'assigned_at', 'completed_at', 'cancelled_at'
    ]
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'title', 'description', 'production_type', 'status', 'priority')
        }),
        ('Quantities', {
            'fields': (
                ('quantity_needed', 'unit'),
                ('quantity_assigned', 'quantity_delivered'),
                ('min_weight_per_bird_kg', 'quality_requirements')
            )
        }),
        ('Pricing', {
            'fields': (
                ('price_per_unit', 'total_budget'),
                'total_cost_actual'
            )
        }),
        ('Delivery', {
            'fields': (
                'delivery_location', 'delivery_location_gps',
                'delivery_deadline', 'delivery_instructions'
            )
        }),
        ('Assignment Strategy', {
            'fields': (
                'auto_assign', 'preferred_region', 'max_farms'
            )
        }),
        ('Management', {
            'fields': (
                ('created_by', 'assigned_procurement_officer'),
                'internal_notes'
            )
        }),
        ('Timestamps', {
            'fields': (
                ('created_at', 'updated_at'),
                ('published_at', 'assigned_at'),
                ('completed_at', 'cancelled_at'),
                'cancellation_reason'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = ['publish_orders', 'auto_assign_orders', 'cancel_orders']
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'published': 'blue',
            'assigning': 'yellow',
            'assigned': 'cyan',
            'in_progress': 'orange',
            'partially_delivered': 'purple',
            'fully_delivered': 'green',
            'completed': 'darkgreen',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def priority_badge(self, obj):
        icons = {
            'low': '⬇️',
            'normal': '➡️',
            'high': '⬆️',
            'urgent': '🔴',
        }
        return format_html('{} {}', icons.get(obj.priority, ''), obj.get_priority_display())
    priority_badge.short_description = 'Priority'
    
    def quantity_progress(self, obj):
        return format_html(
            '{} assigned / {} needed ({} delivered)',
            obj.quantity_assigned, obj.quantity_needed, obj.quantity_delivered
        )
    quantity_progress.short_description = 'Progress'
    
    def fulfillment_badge(self, obj):
        pct = obj.fulfillment_percentage
        if pct >= 100:
            color = 'green'
        elif pct >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; color: white; text-align: center; '
            'padding: 2px; border-radius: 3px; font-size: 11px;">{}%</div></div>',
            min(pct, 100), color, pct
        )
    fulfillment_badge.short_description = 'Fulfillment'
    
    def delivery_deadline_display(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ {} (Overdue by {} days)</span>',
                obj.delivery_deadline, abs(obj.days_until_deadline)
            )
        elif obj.days_until_deadline <= 7:
            return format_html(
                '<span style="color: orange;">⏰ {} ({} days left)</span>',
                obj.delivery_deadline, obj.days_until_deadline
            )
        else:
            return format_html('{} ({} days)', obj.delivery_deadline, obj.days_until_deadline)
    delivery_deadline_display.short_description = 'Deadline'
    
    def total_budget_display(self, obj):
        return format_html('GHS {:,.2f}', obj.total_budget)
    total_budget_display.short_description = 'Budget'
    
    def publish_orders(self, request, queryset):
        from procurement.services import ProcurementWorkflowService
        service = ProcurementWorkflowService()
        count = 0
        for order in queryset.filter(status='draft'):
            service.publish_order(order)
            count += 1
        self.message_user(request, f'{count} order(s) published successfully.')
    publish_orders.short_description = 'Publish selected orders'
    
    def auto_assign_orders(self, request, queryset):
        from procurement.services import ProcurementWorkflowService
        service = ProcurementWorkflowService()
        count = 0
        for order in queryset.filter(auto_assign=True, status__in=['published', 'assigning']):
            service.auto_assign_order(order)
            count += 1
        self.message_user(request, f'{count} order(s) auto-assigned to farms.')
    auto_assign_orders.short_description = 'Auto-assign selected orders'
    
    def cancel_orders(self, request, queryset):
        count = queryset.update(
            status='cancelled',
            cancelled_at=timezone.now(),
            cancellation_reason='Cancelled via admin action'
        )
        self.message_user(request, f'{count} order(s) cancelled.')
    cancel_orders.short_description = 'Cancel selected orders'


class OrderAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'assignment_number', 'order_link', 'farm_link', 'status_badge',
        'quantity_progress', 'fulfillment_bar', 'total_value_display',
        'payment_status_badge'
    ]
    list_filter = ['status', 'quality_passed', 'assigned_at']
    search_fields = ['assignment_number', 'order__order_number', 'farm__farm_name']
    readonly_fields = [
        'assignment_number', 'total_value', 'assigned_at', 'accepted_at',
        'rejected_at', 'actual_ready_date', 'delivery_date',
        'verified_at', 'payment_processed_at'
    ]
    fieldsets = (
        ('Assignment Details', {
            'fields': ('assignment_number', 'order', 'farm', 'status')
        }),
        ('Quantities & Pricing', {
            'fields': (
                ('quantity_assigned', 'quantity_delivered'),
                ('price_per_unit', 'total_value')
            )
        }),
        ('Farm Response', {
            'fields': (
                'accepted_at', 'rejected_at', 'rejection_reason'
            )
        }),
        ('Timeline', {
            'fields': (
                'assigned_at', 'expected_ready_date',
                'actual_ready_date', 'delivery_date',
                'verified_at', 'payment_processed_at'
            )
        }),
        ('Quality Tracking', {
            'fields': (
                ('average_weight_per_bird', 'quality_passed'),
                'quality_notes'
            )
        }),
        ('Notes', {
            'fields': ('farm_notes', 'officer_notes'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_verified', 'generate_invoices']
    
    def order_link(self, obj):
        url = reverse('admin:procurement_procurementorder_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_link.short_description = 'Order'
    
    def farm_link(self, obj):
        url = reverse('admin:farms_farm_change', args=[obj.farm.id])
        return format_html('<a href="{}">{}</a>', url, obj.farm.farm_name)
    farm_link.short_description = 'Farm'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'accepted': 'blue',
            'rejected': 'red',
            'preparing': 'yellow',
            'ready': 'cyan',
            'in_transit': 'orange',
            'delivered': 'purple',
            'verified': 'green',
            'paid': 'darkgreen',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def quantity_progress(self, obj):
        return format_html('{} / {}', obj.quantity_delivered, obj.quantity_assigned)
    quantity_progress.short_description = 'Delivered'
    
    def fulfillment_bar(self, obj):
        pct = obj.fulfillment_percentage
        color = 'green' if pct >= 100 else 'orange' if pct >= 50 else 'red'
        return format_html(
            '<div style="width: 80px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; color: white; text-align: center; '
            'padding: 2px; border-radius: 3px; font-size: 10px;">{}%</div></div>',
            min(pct, 100), color, pct
        )
    fulfillment_bar.short_description = '%'
    
    def total_value_display(self, obj):
        return format_html('GHS {:,.2f}', obj.total_value)
    total_value_display.short_description = 'Value'
    
    def payment_status_badge(self, obj):
        if obj.status == 'paid':
            return format_html('<span style="color: green;">✓ Paid</span>')
        elif obj.status == 'verified':
            return format_html('<span style="color: orange;">⏳ Pending Payment</span>')
        else:
            return format_html('<span style="color: gray;">-</span>')
    payment_status_badge.short_description = 'Payment'
    
    def mark_as_verified(self, request, queryset):
        count = queryset.filter(status='delivered').update(status='verified', verified_at=timezone.now())
        self.message_user(request, f'{count} assignment(s) marked as verified.')
    mark_as_verified.short_description = 'Mark as verified'
    
    def generate_invoices(self, request, queryset):
        from procurement.services import ProcurementWorkflowService
        service = ProcurementWorkflowService()
        count = 0
        for assignment in queryset.filter(status='verified'):
            try:
                service.generate_invoice(assignment)
                count += 1
            except Exception as e:
                continue
        self.message_user(request, f'{count} invoice(s) generated.')
    generate_invoices.short_description = 'Generate invoices for verified assignments'


class DeliveryConfirmationAdmin(admin.ModelAdmin):
    list_display = [
        'delivery_number', 'assignment_link', 'farm_name',
        'delivery_datetime', 'quantity_delivered', 'quality_badge',
        'verified_badge', 'received_by'
    ]
    list_filter = ['quality_passed', 'delivery_confirmed', 'delivery_date', 'verified_at']
    search_fields = ['delivery_number', 'assignment__assignment_number', 'assignment__farm__farm_name']
    readonly_fields = ['delivery_number', 'created_at', 'updated_at']
    fieldsets = (
        ('Delivery Information', {
            'fields': ('delivery_number', 'assignment', 'quantity_delivered',
                      'delivery_date', 'delivery_time')
        }),
        ('Verification', {
            'fields': (
                ('received_by', 'verified_by'),
                'verified_at', 'delivery_confirmed'
            )
        }),
        ('Quality Inspection', {
            'fields': (
                'quality_passed', 'average_weight_per_bird',
                'mortality_count', 'quality_issues', 'quality_photos'
            )
        }),
        ('Documentation', {
            'fields': (
                'delivery_note_number', 'vehicle_registration',
                'driver_name', 'driver_phone'
            )
        }),
        ('Digital Signature', {
            'fields': ('confirmation_signature',),
            'classes': ('collapse',)
        }),
        ('Notes & Timestamps', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def assignment_link(self, obj):
        url = reverse('admin:procurement_orderassignment_change', args=[obj.assignment.id])
        return format_html('<a href="{}">{}</a>', url, obj.assignment.assignment_number)
    assignment_link.short_description = 'Assignment'
    
    def farm_name(self, obj):
        return obj.assignment.farm.farm_name
    farm_name.short_description = 'Farm'
    
    def delivery_datetime(self, obj):
        return format_html('{} {}', obj.delivery_date, obj.delivery_time)
    delivery_datetime.short_description = 'Delivered At'
    
    def quality_badge(self, obj):
        if obj.quality_passed:
            badge = '<span style="color: green;">✓ Passed</span>'
        else:
            badge = '<span style="color: red;">✗ Failed</span>'
        
        if obj.average_weight_per_bird:
            badge += format_html(' (Avg: {} kg)', obj.average_weight_per_bird)
        if obj.mortality_count > 0:
            badge += format_html(' <span style="color: red;">💀 {} DOA</span>', obj.mortality_count)
        
        return format_html(badge)
    quality_badge.short_description = 'Quality'
    
    def verified_badge(self, obj):
        if obj.delivery_confirmed and obj.verified_at:
            return format_html('<span style="color: green;">✓ Verified</span>')
        elif obj.verified_at:
            return format_html('<span style="color: orange;">⏳ Pending Confirmation</span>')
        else:
            return format_html('<span style="color: gray;">Not Verified</span>')
    verified_badge.short_description = 'Status'


class ProcurementInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'farm_link', 'order_link',
        'payment_status_badge', 'total_amount_display',
        'invoice_date', 'due_date_display', 'payment_date'
    ]
    list_filter = ['payment_status', 'invoice_date', 'due_date', 'payment_date']
    search_fields = ['invoice_number', 'farm__farm_name', 'order__order_number']
    readonly_fields = [
        'invoice_number', 'assignment', 'farm', 'order',
        'subtotal', 'total_amount', 'invoice_date',
        'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Invoice Details', {
            'fields': ('invoice_number', 'assignment', 'farm', 'order', 'payment_status')
        }),
        ('Line Items', {
            'fields': (
                ('quantity_invoiced', 'unit_price'),
                'subtotal'
            )
        }),
        ('Deductions', {
            'fields': (
                'quality_deduction', 'mortality_deduction',
                'other_deductions', 'deduction_notes'
            )
        }),
        ('Total', {
            'fields': ('total_amount',)
        }),
        ('Payment Information', {
            'fields': (
                'payment_method', 'payment_reference',
                'payment_date', 'paid_to_account'
            )
        }),
        ('Approval & Dates', {
            'fields': (
                ('approved_by', 'approved_at'),
                ('invoice_date', 'due_date')
            )
        }),
        ('Notes & Timestamps', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_invoices', 'mark_as_paid']
    
    def farm_link(self, obj):
        url = reverse('admin:farms_farm_change', args=[obj.farm.id])
        return format_html('<a href="{}">{}</a>', url, obj.farm.farm_name)
    farm_link.short_description = 'Farm'
    
    def order_link(self, obj):
        url = reverse('admin:procurement_procurementorder_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_link.short_description = 'Order'
    
    def payment_status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'approved': 'blue',
            'processing': 'yellow',
            'paid': 'green',
            'failed': 'red',
            'disputed': 'orange',
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment Status'
    
    def total_amount_display(self, obj):
        deductions_total = obj.quality_deduction + obj.mortality_deduction + obj.other_deductions
        if deductions_total > 0:
            return format_html(
                'GHS {:,.2f}<br><small style="color: red;">(-{:,.2f} deductions)</small>',
                obj.total_amount, deductions_total
            )
        return format_html('GHS {:,.2f}', obj.total_amount)
    total_amount_display.short_description = 'Total'
    
    def due_date_display(self, obj):
        if obj.is_overdue and obj.payment_status != 'paid':
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ {} (Overdue)</span>',
                obj.due_date
            )
        return obj.due_date
    due_date_display.short_description = 'Due Date'
    
    def approve_invoices(self, request, queryset):
        from procurement.services import ProcurementWorkflowService
        service = ProcurementWorkflowService()
        count = 0
        for invoice in queryset.filter(payment_status='pending'):
            service.approve_invoice(invoice, request.user)
            count += 1
        self.message_user(request, f'{count} invoice(s) approved for payment.')
    approve_invoices.short_description = 'Approve selected invoices'
    
    def mark_as_paid(self, request, queryset):
        count = queryset.filter(payment_status__in=['approved', 'processing']).update(
            payment_status='paid',
            payment_date=timezone.now().date()
        )
        self.message_user(request, f'{count} invoice(s) marked as paid.')
    mark_as_paid.short_description = 'Mark as paid'


# Register with custom admin site
yea_admin_site.register(ProcurementOrder, ProcurementOrderAdmin)
yea_admin_site.register(OrderAssignment, OrderAssignmentAdmin)
yea_admin_site.register(DeliveryConfirmation, DeliveryConfirmationAdmin)
yea_admin_site.register(ProcurementInvoice, ProcurementInvoiceAdmin)
