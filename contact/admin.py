"""
Contact Management Django Admin Configuration
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import ContactMessage, ContactMessageReply, ContactFormRateLimit


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """Admin interface for contact messages."""
    
    list_display = [
        'ticket_id', 'name', 'email', 'subject', 'status',
        'assigned_to', 'created_at', 'reply_count'
    ]
    
    list_filter = [
        'status', 'subject', 'created_at', 'assigned_to'
    ]
    
    search_fields = [
        'name', 'email', 'message', 'notes'
    ]
    
    readonly_fields = [
        'id', 'ticket_id', 'ip_address', 'user_agent',
        'created_at', 'updated_at', 'reply_count_display'
    ]
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('ticket_id', 'name', 'email', 'subject', 'message')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'assigned_to', 'notes')
        }),
        ('Security & Tracking', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'reply_count_display'),
            'classes': ('collapse',)
        }),
    )
    
    def reply_count(self, obj):
        """Number of replies."""
        return obj.replies.count()
    reply_count.short_description = 'Replies'
    
    def reply_count_display(self, obj):
        """Display number of replies with link."""
        count = obj.replies.count()
        if count > 0:
            return format_html(
                '<a href="?message__id__exact={}">{} replies</a>',
                obj.id, count
            )
        return '0 replies'
    reply_count_display.short_description = 'Replies'
    
    def has_delete_permission(self, request, obj=None):
        """Only super admins can delete."""
        return request.user.is_superuser


@admin.register(ContactMessageReply)
class ContactMessageReplyAdmin(admin.ModelAdmin):
    """Admin interface for contact message replies."""
    
    list_display = [
        'id', 'message_ticket_id', 'staff', 'sent_via_email',
        'email_sent_at', 'created_at'
    ]
    
    list_filter = [
        'sent_via_email', 'created_at'
    ]
    
    search_fields = [
        'reply_message', 'message__name', 'message__email'
    ]
    
    readonly_fields = [
        'id', 'message', 'staff', 'email_sent_at', 'created_at'
    ]
    
    def message_ticket_id(self, obj):
        """Display message ticket ID."""
        return obj.message.ticket_id
    message_ticket_id.short_description = 'Ticket ID'


@admin.register(ContactFormRateLimit)
class ContactFormRateLimitAdmin(admin.ModelAdmin):
    """Admin interface for rate limiting."""
    
    list_display = [
        'identifier', 'identifier_type', 'count',
        'window_start', 'last_submission'
    ]
    
    list_filter = [
        'identifier_type', 'window_start'
    ]
    
    search_fields = [
        'identifier'
    ]
    
    readonly_fields = [
        'identifier', 'identifier_type', 'count',
        'window_start', 'last_submission'
    ]
    
    def has_add_permission(self, request):
        """Disable manual creation."""
        return False
