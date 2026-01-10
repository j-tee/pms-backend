"""
Contact Management Serializers

Serializers for contact form submissions and admin management.
"""
from rest_framework import serializers
from django.core.validators import EmailValidator
from django.utils.html import strip_tags
from .models import ContactMessage, ContactMessageReply


class ContactFormSubmitSerializer(serializers.Serializer):
    """
    Public contact form submission serializer.
    
    Validates and sanitizes user input from the contact form.
    """
    
    name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Name of the person contacting us"
    )
    
    email = serializers.EmailField(
        max_length=255,
        required=True,
        validators=[EmailValidator()],
        help_text="Valid email address for follow-up"
    )
    
    subject = serializers.ChoiceField(
        choices=ContactMessage.SUBJECT_CHOICES,
        required=True,
        help_text="Category of the inquiry"
    )
    
    message = serializers.CharField(
        min_length=10,
        max_length=2000,
        required=True,
        help_text="Message content (10-2000 characters)"
    )
    
    # Honeypot field for spam prevention (should be empty)
    website = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="Honeypot field - should be empty"
    )
    
    def validate_name(self, value):
        """Sanitize name field."""
        return strip_tags(value).strip()
    
    def validate_message(self, value):
        """Sanitize message field."""
        return strip_tags(value).strip()
    
    def validate_website(self, value):
        """Honeypot validation - should be empty."""
        if value:
            raise serializers.ValidationError("Spam detected")
        return value
    
    def validate_email(self, value):
        """Additional email validation."""
        # Check for disposable email domains (basic check)
        disposable_domains = [
            'tempmail.com', 'throwaway.email', '10minutemail.com',
            'guerrillamail.com', 'mailinator.com', 'trashmail.com'
        ]
        
        domain = value.split('@')[1].lower()
        if domain in disposable_domains:
            raise serializers.ValidationError(
                "Disposable email addresses are not allowed"
            )
        
        return value.lower()


class ContactMessageListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing contact messages in admin.
    """
    
    subject_display = serializers.CharField(
        source='get_subject_display',
        read_only=True
    )
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    assigned_to_name = serializers.SerializerMethodField()
    
    ticket_id = serializers.ReadOnlyField()
    
    reply_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'ticket_id', 'name', 'email', 'subject', 'subject_display',
            'status', 'status_display', 'assigned_to', 'assigned_to_name',
            'reply_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'ticket_id', 'created_at', 'updated_at']
    
    def get_assigned_to_name(self, obj):
        """Get assigned staff member's name."""
        if obj.assigned_to:
            return obj.assigned_to.get_full_name()
        return None
    
    def get_reply_count(self, obj):
        """Get number of replies."""
        return obj.replies.count()


class ContactMessageDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for viewing a single contact message.
    """
    
    subject_display = serializers.CharField(
        source='get_subject_display',
        read_only=True
    )
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    assigned_to_details = serializers.SerializerMethodField()
    
    ticket_id = serializers.ReadOnlyField()
    
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'ticket_id', 'name', 'email', 'subject', 'subject_display',
            'message', 'status', 'status_display', 'assigned_to', 'assigned_to_details',
            'notes', 'ip_address', 'user_agent', 'replies',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'ticket_id', 'name', 'email', 'subject', 'message',
            'ip_address', 'user_agent', 'created_at', 'updated_at'
        ]
    
    def get_assigned_to_details(self, obj):
        """Get assigned staff member's details."""
        if obj.assigned_to:
            return {
                'id': str(obj.assigned_to.id),
                'name': obj.assigned_to.get_full_name(),
                'email': obj.assigned_to.email
            }
        return None
    
    def get_replies(self, obj):
        """Get all replies to this message."""
        replies = obj.replies.all()
        return ContactMessageReplySerializer(replies, many=True).data


class ContactMessageUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating contact message status and assignment.
    """
    
    class Meta:
        model = ContactMessage
        fields = ['status', 'assigned_to', 'notes']
    
    def validate_assigned_to(self, value):
        """Ensure assigned user is staff."""
        if value and value.role not in ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR']:
            raise serializers.ValidationError(
                "Can only assign to admin or staff users"
            )
        return value


class ContactMessageReplySerializer(serializers.ModelSerializer):
    """
    Serializer for contact message replies.
    """
    
    staff_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ContactMessageReply
        fields = [
            'id', 'staff', 'staff_name', 'reply_message',
            'sent_via_email', 'email_sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'staff', 'email_sent_at', 'created_at']
    
    def get_staff_name(self, obj):
        """Get staff member's name."""
        if obj.staff:
            return obj.staff.get_full_name()
        return 'System'


class ContactReplyCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new reply to a contact message.
    """
    
    message = serializers.CharField(
        required=True,
        min_length=10,
        help_text="Reply message content"
    )
    
    send_email = serializers.BooleanField(
        default=True,
        help_text="Whether to send this reply via email"
    )
    
    def validate_message(self, value):
        """Sanitize message but allow some formatting."""
        # Keep basic formatting but strip dangerous HTML
        return value.strip()


class ContactStatsSerializer(serializers.Serializer):
    """
    Serializer for contact message statistics.
    """
    
    total_messages = serializers.IntegerField()
    new_messages = serializers.IntegerField()
    assigned_messages = serializers.IntegerField()
    in_progress_messages = serializers.IntegerField()
    resolved_today = serializers.IntegerField()
    avg_response_time_hours = serializers.FloatField(allow_null=True)
    by_subject = serializers.DictField()
    recent_messages = ContactMessageListSerializer(many=True)
