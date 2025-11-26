"""
Admin interface for flock management and production tracking.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Flock, DailyProduction, MortalityRecord


# =============================================================================
# FLOCK ADMIN
# =============================================================================

@admin.register(Flock)
class FlockAdmin(admin.ModelAdmin):
    """
    Admin interface for flock/batch management.
    """
    
    list_display = [
        'flock_number', 'farm_name', 'flock_type', 'breed', 'status',
        'current_count', 'mortality_rate_badge', 'age_weeks',
        'is_currently_producing', 'arrival_date'
    ]
    
    list_filter = [
        'status', 'flock_type', 'source', 'is_currently_producing',
        'arrival_date'
    ]
    
    search_fields = [
        'flock_number', 'breed', 'farm__farm_name', 'farm__owner__email',
        'supplier_name'
    ]
    
    readonly_fields = [
        'id', 'total_mortality', 'mortality_rate_percent', 
        'average_daily_mortality', 'total_eggs_produced',
        'average_eggs_per_bird', 'feed_conversion_ratio',
        'total_feed_cost', 'total_medication_cost',
        'total_vaccination_cost', 'total_acquisition_cost',
        'created_at', 'updated_at', 'current_age_display',
        'survival_rate_display'
    ]
    
    fieldsets = [
        ('Flock Identification', {
            'fields': [
                'id', 'farm', 'flock_number', 'flock_type', 'breed'
            ]
        }),
        ('Acquisition Details', {
            'fields': [
                'source', 'supplier_name', 'arrival_date',
                'initial_count', 'age_at_arrival_weeks',
                'purchase_price_per_bird', 'total_acquisition_cost'
            ]
        }),
        ('Current Status', {
            'fields': [
                'current_count', 'status', 'housed_in'
            ],
            'classes': ['wide']
        }),
        ('Production Phase (Layers Only)', {
            'fields': [
                'production_start_date', 'expected_production_end_date',
                'is_currently_producing'
            ],
            'classes': ['collapse']
        }),
        ('Mortality Metrics (Auto-Calculated)', {
            'fields': [
                'total_mortality', 'mortality_rate_percent',
                'average_daily_mortality', 'survival_rate_display',
                'current_age_display'
            ],
            'classes': ['collapse']
        }),
        ('Production Metrics (Auto-Calculated)', {
            'fields': [
                'total_eggs_produced', 'average_eggs_per_bird'
            ],
            'classes': ['collapse']
        }),
        ('Feed & Financial Tracking (Auto-Calculated)', {
            'fields': [
                'total_feed_consumed_kg', 'feed_conversion_ratio',
                'total_feed_cost', 'total_medication_cost',
                'total_vaccination_cost'
            ],
            'classes': ['collapse']
        }),
        ('Notes & Timestamps', {
            'fields': ['notes', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    date_hierarchy = 'arrival_date'
    
    def farm_name(self, obj):
        return obj.farm.farm_name
    farm_name.short_description = 'Farm'
    farm_name.admin_order_field = 'farm__farm_name'
    
    def mortality_rate_badge(self, obj):
        """Color-coded mortality rate badge"""
        rate = obj.mortality_rate_percent
        if rate < 5:
            color = 'green'
        elif rate < 10:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{:.2f}%</span>',
            color, rate
        )
    mortality_rate_badge.short_description = 'Mortality Rate'
    mortality_rate_badge.admin_order_field = 'mortality_rate_percent'
    
    def age_weeks(self, obj):
        """Display current age in weeks"""
        age = obj.current_age_weeks
        return f"{age:.1f} weeks" if age else "N/A"
    age_weeks.short_description = 'Current Age'
    
    def current_age_display(self, obj):
        """Display current age in weeks (readonly)"""
        age = obj.current_age_weeks
        return f"{age:.1f} weeks" if age else "N/A"
    current_age_display.short_description = 'Current Age'
    
    def survival_rate_display(self, obj):
        """Display survival rate percentage"""
        return f"{obj.survival_rate_percent:.2f}%"
    survival_rate_display.short_description = 'Survival Rate'
    
    actions = ['mark_as_sold', 'mark_as_active', 'calculate_metrics']
    
    def mark_as_sold(self, request, queryset):
        """Mark selected flocks as sold"""
        count = queryset.update(status='Sold')
        self.message_user(request, f'{count} flock(s) marked as Sold.')
    mark_as_sold.short_description = 'Mark selected flocks as Sold'
    
    def mark_as_active(self, request, queryset):
        """Mark selected flocks as active"""
        count = queryset.update(status='Active')
        self.message_user(request, f'{count} flock(s) marked as Active.')
    mark_as_active.short_description = 'Mark selected flocks as Active'
    
    def calculate_metrics(self, request, queryset):
        """Recalculate metrics for selected flocks"""
        for flock in queryset:
            flock.save()  # Triggers auto-calculation
        self.message_user(request, f'Recalculated metrics for {queryset.count()} flock(s).')
    calculate_metrics.short_description = 'Recalculate metrics for selected flocks'


# =============================================================================
# DAILY PRODUCTION ADMIN
# =============================================================================

@admin.register(DailyProduction)
class DailyProductionAdmin(admin.ModelAdmin):
    """
    Admin interface for daily production records.
    """
    
    list_display = [
        'production_date', 'flock_link', 'farm_name',
        'eggs_collected', 'production_rate_badge',
        'birds_died', 'feed_consumed_kg', 'health_badge'
    ]
    
    list_filter = [
        'production_date', 'general_health', 'signs_of_disease',
        'vaccination_given', 'medication_given', 'flock__flock_type'
    ]
    
    search_fields = [
        'flock__flock_number', 'farm__farm_name',
        'mortality_reason', 'disease_symptoms'
    ]
    
    readonly_fields = [
        'id', 'production_rate_percent', 'recorded_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Record Information', {
            'fields': [
                'id', 'farm', 'flock', 'production_date', 'recorded_by'
            ]
        }),
        ('Egg Production (Layers Only)', {
            'fields': [
                'eggs_collected', 'good_eggs', 'broken_eggs',
                'dirty_eggs', 'small_eggs', 'soft_shell_eggs',
                'production_rate_percent'
            ],
            'classes': ['wide']
        }),
        ('Mortality', {
            'fields': [
                'birds_died', 'mortality_reason', 'mortality_notes'
            ],
            'classes': ['wide']
        }),
        ('Feed Consumption', {
            'fields': [
                'feed_consumed_kg', 'feed_type', 'feed_cost_today'
            ],
            'classes': ['collapse']
        }),
        ('Birds Sold', {
            'fields': [
                'birds_sold', 'birds_sold_revenue'
            ],
            'classes': ['collapse']
        }),
        ('Health Observations', {
            'fields': [
                'general_health', 'unusual_behavior',
                'signs_of_disease', 'disease_symptoms'
            ],
            'classes': ['collapse']
        }),
        ('Medication & Vaccination', {
            'fields': [
                'vaccination_given', 'vaccination_type',
                'medication_given', 'medication_type',
                'medication_cost_today'
            ],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['recorded_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    date_hierarchy = 'production_date'
    
    def farm_name(self, obj):
        return obj.farm.farm_name
    farm_name.short_description = 'Farm'
    farm_name.admin_order_field = 'farm__farm_name'
    
    def flock_link(self, obj):
        """Clickable link to flock"""
        return format_html(
            '<a href="/admin/flock_management/flock/{}/change/">{}</a>',
            obj.flock.id, obj.flock.flock_number
        )
    flock_link.short_description = 'Flock'
    flock_link.admin_order_field = 'flock__flock_number'
    
    def production_rate_badge(self, obj):
        """Color-coded production rate badge"""
        rate = obj.production_rate_percent
        if obj.flock.flock_type not in ['Layers', 'Breeders']:
            return 'N/A'
        
        if rate >= 80:
            color = 'green'
        elif rate >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{:.1f}%</span>',
            color, rate
        )
    production_rate_badge.short_description = 'Production Rate'
    production_rate_badge.admin_order_field = 'production_rate_percent'
    
    def health_badge(self, obj):
        """Color-coded health status"""
        health_colors = {
            'Excellent': 'green',
            'Good': 'lightgreen',
            'Fair': 'orange',
            'Poor': 'red',
            'Critical': 'darkred'
        }
        color = health_colors.get(obj.general_health, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.general_health
        )
    health_badge.short_description = 'Health'
    health_badge.admin_order_field = 'general_health'
    
    actions = ['flag_for_inspection']
    
    def flag_for_inspection(self, request, queryset):
        """Flag records with disease symptoms for inspection"""
        count = queryset.update(signs_of_disease=True)
        self.message_user(request, f'{count} record(s) flagged for disease inspection.')
    flag_for_inspection.short_description = 'Flag selected records for disease inspection'


# =============================================================================
# MORTALITY RECORD ADMIN
# =============================================================================

@admin.register(MortalityRecord)
class MortalityRecordAdmin(admin.ModelAdmin):
    """
    Admin interface for detailed mortality tracking.
    """
    
    list_display = [
        'date_discovered', 'flock_link', 'farm_name',
        'number_of_birds', 'probable_cause', 'vet_status_badge',
        'compensation_badge', 'total_estimated_loss'
    ]
    
    list_filter = [
        'date_discovered', 'probable_cause', 'disease_suspected',
        'vet_inspection_required', 'vet_inspected',
        'compensation_claimed', 'compensation_status',
        'disposal_method'
    ]
    
    search_fields = [
        'flock__flock_number', 'farm__farm_name',
        'disease_suspected', 'vet_diagnosis',
        'symptoms_description'
    ]
    
    readonly_fields = [
        'id', 'total_estimated_loss', 'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Incident Details', {
            'fields': [
                'id', 'farm', 'flock', 'daily_production',
                'date_discovered', 'number_of_birds', 'reported_by'
            ]
        }),
        ('Cause Analysis', {
            'fields': [
                'probable_cause', 'disease_suspected',
                'symptoms_observed', 'symptoms_description'
            ],
            'classes': ['wide']
        }),
        ('Veterinary Investigation', {
            'fields': [
                'vet_inspection_required', 'vet_inspection_requested_date',
                'vet_inspected', 'vet_inspection_date', 'vet_inspector',
                'vet_diagnosis', 'lab_test_conducted', 'lab_test_results'
            ],
            'classes': ['collapse']
        }),
        ('Disposal', {
            'fields': [
                'disposal_method', 'disposal_location', 'disposal_date'
            ],
            'classes': ['collapse']
        }),
        ('Financial Impact', {
            'fields': [
                'estimated_value_per_bird', 'total_estimated_loss'
            ],
            'classes': ['collapse']
        }),
        ('Compensation Claim', {
            'fields': [
                'compensation_claimed', 'compensation_amount',
                'compensation_status'
            ],
            'classes': ['collapse']
        }),
        ('Evidence Documentation', {
            'fields': [
                'photo_1', 'photo_2', 'photo_3'
            ],
            'classes': ['collapse']
        }),
        ('Notes & Timestamps', {
            'fields': ['notes', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    date_hierarchy = 'date_discovered'
    
    def farm_name(self, obj):
        return obj.farm.farm_name
    farm_name.short_description = 'Farm'
    farm_name.admin_order_field = 'farm__farm_name'
    
    def flock_link(self, obj):
        """Clickable link to flock"""
        return format_html(
            '<a href="/admin/flock_management/flock/{}/change/">{}</a>',
            obj.flock.id, obj.flock.flock_number
        )
    flock_link.short_description = 'Flock'
    flock_link.admin_order_field = 'flock__flock_number'
    
    def vet_status_badge(self, obj):
        """Veterinary inspection status badge"""
        if not obj.vet_inspection_required:
            return format_html('<span style="color: gray;">Not Required</span>')
        elif obj.vet_inspected:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 8px; border-radius: 3px;">✓ Inspected</span>'
            )
        else:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 3px 8px; border-radius: 3px;">⚠ Pending</span>'
            )
    vet_status_badge.short_description = 'Vet Status'
    
    def compensation_badge(self, obj):
        """Compensation claim status badge"""
        status_colors = {
            'Not Claimed': 'gray',
            'Pending': 'orange',
            'Approved': 'blue',
            'Rejected': 'red',
            'Paid': 'green'
        }
        color = status_colors.get(obj.compensation_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.compensation_status
        )
    compensation_badge.short_description = 'Compensation'
    compensation_badge.admin_order_field = 'compensation_status'
    
    actions = [
        'request_vet_inspection', 'mark_inspected',
        'approve_compensation', 'reject_compensation'
    ]
    
    def request_vet_inspection(self, request, queryset):
        """Request veterinary inspection for selected records"""
        from django.utils import timezone
        count = queryset.update(
            vet_inspection_required=True,
            vet_inspection_requested_date=timezone.now().date()
        )
        self.message_user(request, f'Requested vet inspection for {count} record(s).')
    request_vet_inspection.short_description = 'Request vet inspection'
    
    def mark_inspected(self, request, queryset):
        """Mark selected records as inspected"""
        from django.utils import timezone
        count = queryset.update(
            vet_inspected=True,
            vet_inspection_date=timezone.now().date()
        )
        self.message_user(request, f'Marked {count} record(s) as inspected.')
    mark_inspected.short_description = 'Mark as inspected'
    
    def approve_compensation(self, request, queryset):
        """Approve compensation claims"""
        count = queryset.update(compensation_status='Approved')
        self.message_user(request, f'Approved compensation for {count} claim(s).')
    approve_compensation.short_description = 'Approve compensation'
    
    def reject_compensation(self, request, queryset):
        """Reject compensation claims"""
        count = queryset.update(compensation_status='Rejected')
        self.message_user(request, f'Rejected {count} compensation claim(s).')
    reject_compensation.short_description = 'Reject compensation'
