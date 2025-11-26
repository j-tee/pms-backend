"""
Django Admin Configuration for Farm Models
"""

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html
from django.utils import timezone
from core.admin_site import yea_admin_site
from .models import (
    Farm, FarmLocation, PoultryHouse, Equipment,
    Utilities, Biosecurity, SupportNeeds, FarmDocument,
    FarmReviewAction, FarmApprovalQueue, FarmNotification
)


class FarmLocationInline(admin.StackedInline):
    model = FarmLocation
    extra = 0
    fields = (
        'gps_address_string', 'location', 'region', 'district',
        'constituency', 'community', 'land_size_acres',
        'land_ownership_status', 'is_primary_location'
    )


class PoultryHouseInline(admin.TabularInline):
    model = PoultryHouse
    extra = 0
    fields = (
        'house_number', 'house_type', 'house_capacity',
        'current_occupancy', 'estimated_house_value_ghs'
    )


class EquipmentInline(admin.StackedInline):
    model = Equipment
    extra = 0


class UtilitiesInline(admin.StackedInline):
    model = Utilities
    extra = 0


class BiosecurityInline(admin.StackedInline):
    model = Biosecurity
    extra = 0


class FarmDocumentInline(admin.TabularInline):
    model = FarmDocument
    extra = 0
    fields = ('document_type', 'file', 'is_verified', 'verified_by')
    readonly_fields = ('uploaded_at',)



class FarmAdmin(admin.ModelAdmin):
    list_display = [
        'application_id', 'farm_name', 'user', 'primary_phone',
        'application_status', 'farm_status', 'created_at'
    ]
    list_filter = [
        'application_status', 'farm_status', 'primary_production_type',
        'ownership_type', 'experience_level'
    ]
    search_fields = [
        'application_id', 'farm_id', 'farm_name', 'ghana_card_number',
        'tin', 'primary_phone', 'first_name', 'last_name'
    ]
    readonly_fields = [
        'application_id', 'farm_id', 'application_date', 'created_at',
        'updated_at', 'capacity_utilization', 'experience_level',
        'farm_readiness_score', 'biosecurity_score', 'financial_health_score'
    ]
    
    fieldsets = (
        ('Application Info', {
            'fields': (
                'application_id', 'farm_id', 'application_status',
                'farm_status', 'user'
            )
        }),
        ('Personal Identity', {
            'fields': (
                'first_name', 'middle_name', 'last_name', 'date_of_birth',
                'gender', 'ghana_card_number', 'marital_status',
                'number_of_dependents'
            )
        }),
        ('Contact Information', {
            'fields': (
                'primary_phone', 'alternate_phone', 'email',
                'preferred_contact_method', 'residential_address'
            )
        }),
        ('Next of Kin', {
            'fields': (
                'nok_full_name', 'nok_relationship', 'nok_phone',
                'nok_residential_address'
            )
        }),
        ('Education & Experience', {
            'fields': (
                'education_level', 'literacy_level', 'years_in_poultry',
                'experience_level', 'previous_training', 'farming_full_time',
                'other_occupation'
            )
        }),
        ('Business Information', {
            'fields': (
                'farm_name', 'ownership_type', 'tin',
                'business_registration_number', 'business_registration_date'
            )
        }),
        ('Banking Details', {
            'fields': (
                'bank_name', 'account_number', 'account_name',
                'mobile_money_provider', 'mobile_money_number'
            )
        }),
        ('Infrastructure', {
            'fields': (
                'number_of_poultry_houses', 'total_bird_capacity',
                'current_bird_count', 'capacity_utilization',
                'housing_type', 'total_infrastructure_value_ghs'
            )
        }),
        ('Production Planning', {
            'fields': (
                'primary_production_type', 'layer_breed',
                'planned_monthly_egg_production', 'broiler_breed',
                'planned_monthly_bird_sales', 'planned_production_start_date',
                'hatchery_operation', 'feed_formulation'
            )
        }),
        ('Financial Information', {
            'fields': (
                'initial_investment_amount', 'funding_source',
                'monthly_operating_budget', 'expected_monthly_revenue',
                'has_outstanding_debt', 'debt_amount', 'debt_purpose',
                'monthly_debt_payment', 'financial_health_score',
                'total_investment_value'
            )
        }),
        ('Application Workflow', {
            'fields': (
                'assigned_extension_officer', 'assigned_reviewer',
                'review_comments', 'site_visit_required', 'site_visit_date',
                'site_visit_notes', 'rejection_reason', 'more_info_requested'
            )
        }),
        ('Approval', {
            'fields': (
                'approval_date', 'approved_by', 'activation_date',
                'benefit_package_assigned'
            )
        }),
        ('Calculated Metrics', {
            'fields': (
                'farm_readiness_score', 'biosecurity_score',
                'support_priority_score'
            )
        }),
        ('Timestamps', {
            'fields': ('application_date', 'created_at', 'updated_at')
        }),
    )
    
    inlines = [
        FarmLocationInline, PoultryHouseInline, EquipmentInline,
        UtilitiesInline, BiosecurityInline, FarmDocumentInline
    ]



class FarmLocationAdmin(GISModelAdmin):
    list_display = [
        'farm', 'community', 'constituency', 'district', 'region',
        'is_primary_location', 'gps_verified'
    ]
    list_filter = ['region', 'is_primary_location', 'gps_verified', 'land_ownership_status']
    search_fields = ['farm__farm_name', 'community', 'constituency', 'district']
    readonly_fields = ['latitude', 'longitude', 'created_at', 'updated_at']



class PoultryHouseAdmin(admin.ModelAdmin):
    list_display = [
        'farm', 'house_number', 'house_type', 'house_capacity',
        'current_occupancy', 'year_built', 'estimated_house_value_ghs'
    ]
    list_filter = ['house_type', 'ventilation_system']
    search_fields = ['farm__farm_name', 'house_number']



class EquipmentAdmin(admin.ModelAdmin):
    list_display = [
        'farm', 'has_incubator', 'has_generator', 'cold_storage_available',
        'weighing_scale', 'total_equipment_value'
    ]
    search_fields = ['farm__farm_name']
    
    def total_equipment_value(self, obj):
        return f"GHS {obj.total_equipment_value:,.2f}"
    total_equipment_value.short_description = 'Total Value'



class UtilitiesAdmin(admin.ModelAdmin):
    list_display = [
        'farm', 'electricity_source', 'electricity_reliability',
        'water_availability', 'solar_panel_installed'
    ]
    list_filter = ['electricity_source', 'water_availability', 'solar_panel_installed']
    search_fields = ['farm__farm_name']



class BiosecurityAdmin(admin.ModelAdmin):
    list_display = [
        'farm', 'biosecurity_score', 'perimeter_fencing',
        'regular_vaccination', 'quarantine_area'
    ]
    list_filter = [
        'perimeter_fencing', 'regular_vaccination', 'quarantine_area',
        'rodent_control_program'
    ]
    search_fields = ['farm__farm_name']
    readonly_fields = ['biosecurity_score']
    
    actions = ['calculate_scores']
    
    def calculate_scores(self, request, queryset):
        for biosecurity in queryset:
            biosecurity.calculate_biosecurity_score()
            biosecurity.save()
        self.message_user(request, f"Calculated biosecurity scores for {queryset.count()} farms")
    calculate_scores.short_description = "Calculate biosecurity scores"



class SupportNeedsAdmin(admin.ModelAdmin):
    list_display = [
        'farm', 'assessment_date', 'assessment_type',
        'overall_priority', 'market_access_support', 'input_supply_support'
    ]
    list_filter = ['assessment_type', 'overall_priority', 'assessment_date']
    search_fields = ['farm__farm_name', 'major_challenges']
    readonly_fields = ['assessment_date', 'created_at', 'updated_at']



class FarmDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'farm', 'document_type', 'file_name', 'is_verified',
        'verified_by', 'uploaded_at'
    ]
    list_filter = ['document_type', 'is_verified', 'gps_location_verified']
    search_fields = ['farm__farm_name', 'file_name']
    readonly_fields = [
        'file_size', 'mime_type', 'uploaded_at', 'updated_at',
        'exif_gps_latitude', 'exif_gps_longitude'
    ]
    
    actions = ['verify_documents']
    
    def verify_documents(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            is_verified=True,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f"Verified {queryset.count()} documents")
    verify_documents.short_description = "Mark documents as verified"


# ===================================================================
# FARM APPROVAL WORKFLOW ADMIN
# ===================================================================


class FarmReviewActionAdmin(admin.ModelAdmin):
    """Admin for tracking all review actions on farm applications"""
    
    list_display = [
        'farm', 'review_level', 'action_badge', 'reviewer',
        'created_at', 'is_internal_note'
    ]
    list_filter = ['review_level', 'action', 'is_internal_note', 'created_at']
    search_fields = ['farm__farm_name', 'reviewer__username', 'notes']
    readonly_fields = ['farm', 'reviewer', 'review_level', 'action', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('Review Information', {
            'fields': ['farm', 'reviewer', 'review_level', 'action', 'created_at']
        }),
        ('Feedback & Notes', {
            'fields': ['notes', 'is_internal_note']
        }),
        ('Change Requests', {
            'fields': ['requested_changes', 'changes_deadline'],
            'classes': ['collapse'],
        }),
        ('Reassignment', {
            'fields': ['reassigned_to'],
            'classes': ['collapse'],
        }),
    ]
    
    def action_badge(self, obj):
        """Display action with color coding"""
        colors = {
            'claimed': '#17a2b8',       # Blue
            'approved': '#28a745',      # Green
            'rejected': '#dc3545',      # Red
            'request_changes': '#ffc107',  # Yellow
            'changes_submitted': '#6c757d',  # Gray
            'reassigned': '#fd7e14',    # Orange
            'note_added': '#6c757d',    # Gray
        }
        color = colors.get(obj.action, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'
    
    def has_add_permission(self, request):
        """Reviews are created through workflow, not directly"""
        return False



class FarmApprovalQueueAdmin(admin.ModelAdmin):
    """Admin for managing farm approval queue"""
    
    list_display = [
        'farm', 'review_level', 'status_badge', 'assigned_to',
        'priority', 'entered_queue_at', 'is_overdue_badge',
        'suggested_location'
    ]
    list_filter = [
        'review_level', 'status', 'is_overdue',
        'auto_assigned', 'suggested_region'
    ]
    search_fields = [
        'farm__farm_name', 'assigned_to__username',
        'suggested_constituency', 'suggested_region'
    ]
    readonly_fields = [
        'farm', 'review_level', 'entered_queue_at', 'claimed_at',
        'completed_at', 'suggested_constituency', 'suggested_region'
    ]
    date_hierarchy = 'entered_queue_at'
    
    fieldsets = [
        ('Queue Information', {
            'fields': [
                'farm', 'review_level', 'status', 'priority',
                'entered_queue_at'
            ]
        }),
        ('Assignment', {
            'fields': [
                'assigned_to', 'assigned_at', 'auto_assigned',
                'claimed_at'
            ]
        }),
        ('SLA & Tracking', {
            'fields': [
                'sla_due_date', 'is_overdue', 'completed_at'
            ]
        }),
        ('Location Suggestions', {
            'fields': [
                'suggested_constituency', 'suggested_region'
            ],
            'classes': ['collapse'],
        }),
    ]
    
    actions = ['mark_as_high_priority', 'clear_assignment']
    
    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': '#6c757d',      # Gray
            'claimed': '#17a2b8',      # Blue
            'in_progress': '#ffc107',  # Yellow
            'completed': '#28a745',    # Green
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def is_overdue_badge(self, obj):
        """Visual indicator for overdue items"""
        if obj.is_overdue:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠️ OVERDUE</span>'
            )
        return format_html('<span style="color: #28a745;">✓ On Time</span>')
    is_overdue_badge.short_description = 'SLA Status'
    
    def suggested_location(self, obj):
        """Show suggested constituency/region"""
        if obj.suggested_constituency:
            return f"{obj.suggested_constituency}, {obj.suggested_region}"
        return "-"
    suggested_location.short_description = 'Suggested Location'
    
    def mark_as_high_priority(self, request, queryset):
        """Mark selected items as high priority"""
        updated = queryset.update(priority=10)
        self.message_user(request, f'{updated} item(s) marked as high priority')
    mark_as_high_priority.short_description = 'Mark as high priority'
    
    def clear_assignment(self, request, queryset):
        """Clear assignment to return to unassigned queue"""
        updated = queryset.filter(
            status__in=['pending', 'claimed']
        ).update(
            assigned_to=None,
            assigned_at=None,
            claimed_at=None,
            status='pending',
            auto_assigned=False
        )
        self.message_user(request, f'{updated} item(s) returned to unassigned queue')
    clear_assignment.short_description = 'Clear assignment'



class FarmNotificationAdmin(admin.ModelAdmin):
    """Admin for managing farm notifications"""
    
    list_display = [
        'user', 'notification_type_badge', 'channel_badge',
        'status_badge', 'subject', 'created_at', 'sent_at'
    ]
    list_filter = [
        'notification_type', 'channel', 'status',
        'created_at', 'sent_at'
    ]
    search_fields = [
        'user__username', 'user__email', 'farm__farm_name',
        'subject', 'message'
    ]
    readonly_fields = [
        'user', 'farm', 'notification_type', 'channel',
        'created_at', 'sent_at', 'delivered_at', 'read_at',
        'failed_at', 'sms_message_id'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('Recipient', {
            'fields': ['user', 'farm']
        }),
        ('Notification Details', {
            'fields': [
                'notification_type', 'channel', 'subject',
                'message', 'action_url'
            ]
        }),
        ('Status Tracking', {
            'fields': [
                'status', 'created_at', 'sent_at', 'delivered_at',
                'read_at', 'failed_at', 'failure_reason'
            ]
        }),
        ('SMS Details', {
            'fields': [
                'sms_provider', 'sms_message_id', 'sms_cost'
            ],
            'classes': ['collapse'],
        }),
    ]
    
    actions = ['resend_failed_notifications', 'mark_as_sent']
    
    def notification_type_badge(self, obj):
        """Display notification type with icon"""
        icons = {
            'application_submitted': '📝',
            'review_started': '👀',
            'changes_requested': '✏️',
            'approved_next_level': '✅',
            'final_approval': '🎉',
            'rejected': '❌',
            'reminder': '⏰',
            'assignment': '📋',
        }
        icon = icons.get(obj.notification_type, '📬')
        return format_html(
            '{} {}',
            icon,
            obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'Type'
    
    def channel_badge(self, obj):
        """Display channel with color coding"""
        colors = {
            'email': '#17a2b8',      # Blue
            'sms': '#28a745',        # Green
            'in_app': '#ffc107',     # Yellow
        }
        icons = {
            'email': '📧',
            'sms': '📱',
            'in_app': '🔔',
        }
        color = colors.get(obj.channel, '#6c757d')
        icon = icons.get(obj.channel, '📬')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px;">{} {}</span>',
            color,
            icon,
            obj.channel.upper()
        )
    channel_badge.short_description = 'Channel'
    
    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': '#6c757d',     # Gray
            'sent': '#17a2b8',        # Blue
            'delivered': '#28a745',   # Green
            'failed': '#dc3545',      # Red
            'read': '#20c997',        # Teal
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def resend_failed_notifications(self, request, queryset):
        """Resend failed notifications"""
        failed = queryset.filter(status='failed')
        count = failed.update(status='pending', failed_at=None, failure_reason='')
        self.message_user(
            request,
            f'{count} notification(s) queued for resending'
        )
    resend_failed_notifications.short_description = 'Resend failed notifications'
    
    def mark_as_sent(self, request, queryset):
        """Manually mark as sent (for testing)"""
        updated = queryset.filter(status='pending').update(
            status='sent',
            sent_at=timezone.now()
        )
        self.message_user(request, f'{updated} notification(s) marked as sent')
    mark_as_sent.short_description = 'Mark as sent (manual)'
    
    def has_add_permission(self, request):
        """Notifications are created by system, not manually"""
        return False


# Register all models with custom admin site
yea_admin_site.register(Farm, FarmAdmin)
yea_admin_site.register(FarmLocation, FarmLocationAdmin)
yea_admin_site.register(PoultryHouse, PoultryHouseAdmin)
yea_admin_site.register(Equipment, EquipmentAdmin)
yea_admin_site.register(Utilities, UtilitiesAdmin)
yea_admin_site.register(Biosecurity, BiosecurityAdmin)
yea_admin_site.register(SupportNeeds, SupportNeedsAdmin)
yea_admin_site.register(FarmDocument, FarmDocumentAdmin)
yea_admin_site.register(FarmReviewAction, FarmReviewActionAdmin)
yea_admin_site.register(FarmApprovalQueue, FarmApprovalQueueAdmin)
yea_admin_site.register(FarmNotification, FarmNotificationAdmin)
