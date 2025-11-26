"""
Medication & Vaccination Management Admin Configuration

Admin interface for managing medications, vaccinations, schedules,
treatment records, and veterinary visits.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    MedicationType,
    VaccinationSchedule,
    MedicationRecord,
    VaccinationRecord,
    VetVisit
)


@admin.register(MedicationType)
class MedicationTypeAdmin(admin.ModelAdmin):
    """Admin interface for Medication Types."""
    
    list_display = [
        'name',
        'category_badge',
        'administration_route',
        'withdrawal_period_days',
        'active_status',
    ]
    
    list_filter = [
        'category',
        'administration_route',
        'is_active',
        'requires_prescription',
    ]
    
    search_fields = [
        'name',
        'generic_name',
        'active_ingredient',
        'manufacturer',
    ]
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'generic_name', 'category', 'manufacturer')
        }),
        ('Active Ingredients', {
            'fields': ('active_ingredient', 'strength')
        }),
        ('Administration', {
            'fields': ('administration_route', 'dosage', 'indication', 'contraindications')
        }),
        ('Withdrawal Periods', {
            'fields': ('withdrawal_period_days', 'egg_withdrawal_days', 'meat_withdrawal_days')
        }),
        ('Pricing', {
            'fields': ('unit_price', 'unit_measure')
        }),
        ('Regulatory Information', {
            'fields': ('registration_number', 'requires_prescription'),
            'classes': ('collapse',)
        }),
        ('Storage', {
            'fields': ('storage_conditions', 'shelf_life_months'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def category_badge(self, obj):
        """Display category with color-coded badge."""
        colors = {
            'ANTIBIOTIC': '#dc3545',
            'VACCINE': '#28a745',
            'VITAMIN': '#ffc107',
            'DEWORMER': '#17a2b8',
            'COCCIDIOSTAT': '#6f42c1',
            'PROBIOTIC': '#20c997',
            'DISINFECTANT': '#fd7e14',
            'OTHER': '#6c757d',
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
            return format_html('<span style="color: green;">●</span> Active')
        return format_html('<span style="color: red;">●</span> Inactive')
    active_status.short_description = 'Status'


@admin.register(VaccinationSchedule)
class VaccinationScheduleAdmin(admin.ModelAdmin):
    """Admin interface for Vaccination Schedules."""
    
    list_display = [
        'medication_type',
        'flock_type',
        'age_display',
        'priority',
        'mandatory_badge',
        'disease_prevented',
        'active_status',
    ]
    
    list_filter = [
        'flock_type',
        'is_mandatory',
        'is_active',
        'frequency',
    ]
    
    search_fields = [
        'medication_type__name',
        'disease_prevented',
    ]
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'medication_type', 'flock_type')
        }),
        ('Schedule Details', {
            'fields': ('age_in_weeks', 'age_in_days', 'frequency', 'dosage_per_bird')
        }),
        ('Priority and Compliance', {
            'fields': ('is_mandatory', 'priority')
        }),
        ('Disease Information', {
            'fields': ('disease_prevented', 'symptoms_to_watch')
        }),
        ('Status', {
            'fields': ('is_active', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def age_display(self, obj):
        """Display age in appropriate format."""
        if obj.age_in_days:
            return f"{obj.age_in_days} days"
        return f"{obj.age_in_weeks} weeks"
    age_display.short_description = 'Age'
    
    def mandatory_badge(self, obj):
        """Display mandatory status."""
        if obj.is_mandatory:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">MANDATORY</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">Optional</span>'
        )
    mandatory_badge.short_description = 'Compliance'
    
    def active_status(self, obj):
        """Display active status with badge."""
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Active')
        return format_html('<span style="color: red;">●</span> Inactive')
    active_status.short_description = 'Status'


@admin.register(MedicationRecord)
class MedicationRecordAdmin(admin.ModelAdmin):
    """Admin interface for Medication Records."""
    
    list_display = [
        'administered_date',
        'flock_link',
        'medication_type',
        'reason_badge',
        'birds_treated',
        'total_cost',
        'withdrawal_end_date',
    ]
    
    list_filter = [
        'reason',
        'administered_date',
    ]
    
    search_fields = [
        'flock__name',
        'farm__name',
        'medication_type__name',
    ]
    
    readonly_fields = ['id', 'farm', 'end_date', 'withdrawal_end_date', 'total_cost', 'created_at', 'updated_at', 'created_by']
    
    date_hierarchy = 'administered_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'flock', 'farm', 'medication_type', 'administered_date', 'reason')
        }),
        ('Dosage', {
            'fields': ('dosage_given', 'birds_treated', 'treatment_days', 'end_date')
        }),
        ('Cost', {
            'fields': ('quantity_used', 'unit_cost', 'total_cost')
        }),
        ('Withdrawal Period', {
            'fields': ('withdrawal_end_date',)
        }),
        ('Administration Details', {
            'fields': ('administered_by', 'batch_number'),
            'classes': ('collapse',)
        }),
        ('Outcome Tracking', {
            'fields': ('symptoms_before', 'effectiveness_rating', 'side_effects'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def flock_link(self, obj):
        """Display clickable flock link."""
        url = reverse('admin:flock_management_flock_change', args=[obj.flock.id])
        return format_html('<a href="{}">{}</a>', url, obj.flock.name)
    flock_link.short_description = 'Flock'
    
    def reason_badge(self, obj):
        """Display reason with color-coded badge."""
        colors = {
            'TREATMENT': '#dc3545',
            'PREVENTION': '#28a745',
            'GROWTH': '#17a2b8',
            'STRESS': '#ffc107',
            'OTHER': '#6c757d',
        }
        color = colors.get(obj.reason, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_reason_display()
        )
    reason_badge.short_description = 'Reason'
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by on save."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VaccinationRecord)
class VaccinationRecordAdmin(admin.ModelAdmin):
    """Admin interface for Vaccination Records."""
    
    list_display = [
        'vaccination_date',
        'flock_link',
        'medication_type',
        'birds_vaccinated',
        'compliance_badge',
        'batch_number',
        'total_cost',
    ]
    
    list_filter = [
        'is_mandatory_compliance',
        'vaccination_date',
    ]
    
    search_fields = [
        'flock__name',
        'farm__name',
        'medication_type__name',
        'batch_number',
    ]
    
    readonly_fields = ['id', 'farm', 'total_cost', 'created_at', 'updated_at', 'created_by']
    
    date_hierarchy = 'vaccination_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'flock', 'farm', 'medication_type', 'vaccination_schedule', 'vaccination_date')
        }),
        ('Vaccination Details', {
            'fields': ('birds_vaccinated', 'flock_age_weeks', 'dosage_per_bird', 'administration_route')
        }),
        ('Batch Tracking', {
            'fields': ('batch_number', 'expiry_date', 'manufacturer')
        }),
        ('Cost', {
            'fields': ('quantity_used', 'unit_cost', 'total_cost')
        }),
        ('Administration Personnel', {
            'fields': ('administered_by', 'vet_license_number'),
            'classes': ('collapse',)
        }),
        ('Compliance', {
            'fields': ('is_mandatory_compliance', 'next_vaccination_due')
        }),
        ('Reaction Tracking', {
            'fields': ('adverse_reactions', 'mortality_within_24hrs'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def flock_link(self, obj):
        """Display clickable flock link."""
        url = reverse('admin:flock_management_flock_change', args=[obj.flock.id])
        return format_html('<a href="{}">{}</a>', url, obj.flock.name)
    flock_link.short_description = 'Flock'
    
    def compliance_badge(self, obj):
        """Display compliance status."""
        if obj.is_mandatory_compliance:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">COMPLIANT</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">Routine</span>'
        )
    compliance_badge.short_description = 'Compliance'
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by on save."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VetVisit)
class VetVisitAdmin(admin.ModelAdmin):
    """Admin interface for Veterinary Visits."""
    
    list_display = [
        'visit_date',
        'farm_link',
        'visit_type_badge',
        'veterinarian_name',
        'status_badge',
        'compliance_status_badge',
        'follow_up_required',
    ]
    
    list_filter = [
        'visit_type',
        'status',
        'compliance_status',
        'follow_up_required',
        'visit_date',
    ]
    
    search_fields = [
        'farm__name',
        'flock__name',
        'veterinarian_name',
        'vet_license_number',
    ]
    
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    date_hierarchy = 'visit_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'farm', 'flock', 'visit_date', 'visit_type', 'status')
        }),
        ('Veterinarian Information', {
            'fields': ('veterinarian_name', 'vet_license_number', 'vet_phone', 'vet_organization')
        }),
        ('Visit Purpose and Findings', {
            'fields': ('purpose', 'findings', 'diagnosis')
        }),
        ('Recommendations', {
            'fields': ('recommendations', 'medications_prescribed', 'follow_up_required', 'follow_up_date')
        }),
        ('Compliance and Certification', {
            'fields': ('compliance_status', 'issues_identified', 'certificate_issued', 'certificate_number')
        }),
        ('Cost', {
            'fields': ('visit_fee',)
        }),
        ('Supporting Documents', {
            'fields': ('report_file',),
            'classes': ('collapse',)
        }),
        ('Notes', {
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
    
    def visit_type_badge(self, obj):
        """Display visit type with color-coded badge."""
        colors = {
            'ROUTINE': '#28a745',
            'EMERGENCY': '#dc3545',
            'VACCINATION': '#17a2b8',
            'DISEASE_INVESTIGATION': '#ffc107',
            'COMPLIANCE_CHECK': '#6f42c1',
            'FOLLOW_UP': '#fd7e14',
            'OTHER': '#6c757d',
        }
        color = colors.get(obj.visit_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_visit_type_display()
        )
    visit_type_badge.short_description = 'Visit Type'
    
    def status_badge(self, obj):
        """Display status with color-coded badge."""
        colors = {
            'SCHEDULED': '#ffc107',
            'COMPLETED': '#28a745',
            'CANCELLED': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def compliance_status_badge(self, obj):
        """Display compliance status with color-coded badge."""
        colors = {
            'COMPLIANT': '#28a745',
            'NON_COMPLIANT': '#dc3545',
            'PARTIAL': '#ffc107',
            'N/A': '#6c757d',
        }
        color = colors.get(obj.compliance_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.compliance_status
        )
    compliance_status_badge.short_description = 'Compliance'
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by on save."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
