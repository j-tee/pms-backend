from django.contrib import admin
from .models import Partner, PartnerOffer, OfferInteraction, AdvertiserLead


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'category', 'is_verified', 'is_active', 'has_active_contract', 'created_at']
    list_filter = ['category', 'is_verified', 'is_active']
    search_fields = ['company_name', 'contact_name', 'contact_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Company Info', {
            'fields': ('company_name', 'category', 'logo', 'website', 'description')
        }),
        ('Contact', {
            'fields': ('contact_name', 'contact_email', 'contact_phone')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active')
        }),
        ('Contract', {
            'fields': ('contract_start_date', 'contract_end_date', 'monthly_fee')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PartnerOffer)
class PartnerOfferAdmin(admin.ModelAdmin):
    list_display = ['title', 'partner', 'offer_type', 'is_active', 'is_featured', 'impressions', 'clicks', 'start_date', 'end_date']
    list_filter = ['offer_type', 'is_active', 'is_featured', 'targeting', 'partner']
    search_fields = ['title', 'description', 'partner__company_name']
    readonly_fields = ['id', 'impressions', 'clicks', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Offer Content', {
            'fields': ('partner', 'title', 'description', 'offer_type', 'image')
        }),
        ('Call to Action', {
            'fields': ('cta_text', 'cta_url', 'promo_code')
        }),
        ('Targeting', {
            'fields': ('targeting', 'target_regions', 'min_flock_size', 'max_flock_size')
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'priority')
        }),
        ('Analytics', {
            'fields': ('impressions', 'clicks'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OfferInteraction)
class OfferInteractionAdmin(admin.ModelAdmin):
    list_display = ['offer', 'farm', 'interaction_type', 'source_page', 'created_at']
    list_filter = ['interaction_type', 'source_page', 'created_at']
    search_fields = ['offer__title', 'farm__farm_name']
    readonly_fields = ['id', 'created_at']


@admin.register(AdvertiserLead)
class AdvertiserLeadAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'contact_name', 'category', 'budget_range', 'status', 'created_at']
    list_filter = ['status', 'category', 'budget_range', 'created_at']
    search_fields = ['company_name', 'contact_name', 'contact_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Company Info', {
            'fields': ('company_name', 'category', 'website')
        }),
        ('Contact', {
            'fields': ('contact_name', 'contact_email', 'contact_phone', 'job_title')
        }),
        ('Interest', {
            'fields': ('advertising_interest', 'target_audience', 'budget_range')
        }),
        ('Lead Management', {
            'fields': ('status', 'admin_notes', 'assigned_to', 'follow_up_date')
        }),
        ('Conversion', {
            'fields': ('converted_partner',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
