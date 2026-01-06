"""
CMS Django Admin Configuration
"""
from django.contrib import admin
from .models import ContentPage, ContentPageRevision, CompanyProfile


@admin.register(ContentPage)
class ContentPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'page_type', 'status', 'version', 'published_at', 'updated_at']
    list_filter = ['status', 'page_type', 'created_at']
    search_fields = ['title', 'content', 'slug']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'version']
    
    fieldsets = (
        ('Page Information', {
            'fields': ('page_type', 'title', 'slug', 'status')
        }),
        ('Content', {
            'fields': ('content', 'excerpt')
        }),
        ('SEO', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Publishing', {
            'fields': ('published_at', 'version')
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ContentPageRevision)
class ContentPageRevisionAdmin(admin.ModelAdmin):
    list_display = ['page', 'version', 'changed_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['page__title', 'change_summary']
    readonly_fields = ['page', 'version', 'changed_by', 'created_at']


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'email', 'phone', 'updated_at']
    readonly_fields = ['updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'tagline', 'description', 'logo_url')
        }),
        ('Contact Details', {
            'fields': ('email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'region', 'country', 'postal_code')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'twitter_url', 'linkedin_url', 'instagram_url'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Only allow one company profile."""
        return not CompanyProfile.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Don't allow deletion of company profile."""
        return False
