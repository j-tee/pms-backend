"""
Contact Management Models

Database schema for contact form submissions and replies.
"""
import uuid
from django.db import models
from django.core.validators import MinLengthValidator, EmailValidator
from django.utils import timezone
from accounts.models import User


class ContactMessage(models.Model):
    """
    Contact form submissions from public pages.
    
    Stores inquiries from About Us, Contact Us, and Privacy Policy pages.
    """
    
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('support', 'Technical Support'),
        ('partnership', 'Partnership Opportunity'),
        ('marketplace', 'Marketplace Question'),
        ('billing', 'Billing & Payments'),
        ('feedback', 'Feedback & Suggestions'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Contact Information
    name = models.CharField(
        max_length=100,
        help_text="Name of the person contacting us"
    )
    
    email = models.EmailField(
        max_length=255,
        validators=[EmailValidator()],
        help_text="Email address for follow-up"
    )
    
    # Message Details
    subject = models.CharField(
        max_length=50,
        choices=SUBJECT_CHOICES,
        help_text="Category of the inquiry"
    )
    
    message = models.TextField(
        validators=[MinLengthValidator(10)],
        help_text="The actual message content (min 10 characters)"
    )
    
    # Status and Assignment
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        db_index=True,
        help_text="Current status of the message"
    )
    
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_contact_messages',
        help_text="Staff member assigned to handle this message"
    )
    
    # Security and Tracking
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the submitter (for spam prevention)"
    )
    
    user_agent = models.TextField(
        blank=True,
        default='',
        help_text="Browser user agent (for spam prevention)"
    )
    
    # Additional Notes (for staff use)
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Internal notes from staff"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the message was submitted"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the message was last updated"
    )
    
    # Soft delete
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )
    
    class Meta:
        db_table = 'contact_messages'
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_subject_display()} ({self.status})"
    
    @property
    def ticket_id(self):
        """Generate a readable ticket ID."""
        return f"CNT-{str(self.id)[:8].upper()}"
    
    def assign_to(self, user):
        """Assign message to a staff member."""
        self.assigned_to = user
        if self.status == 'new':
            self.status = 'assigned'
        self.save()
    
    def mark_resolved(self):
        """Mark message as resolved."""
        self.status = 'resolved'
        self.save()
    
    def mark_closed(self):
        """Mark message as closed."""
        self.status = 'closed'
        self.save()


class ContactMessageReply(models.Model):
    """
    Replies to contact messages from staff.
    
    Maintains a history of all responses to contact inquiries.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    message = models.ForeignKey(
        ContactMessage,
        on_delete=models.CASCADE,
        related_name='replies',
        help_text="The contact message being replied to"
    )
    
    staff = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='contact_replies',
        help_text="Staff member who sent the reply"
    )
    
    reply_message = models.TextField(
        help_text="The reply message content"
    )
    
    sent_via_email = models.BooleanField(
        default=True,
        help_text="Whether this reply was sent via email"
    )
    
    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the email was successfully sent"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the reply was created"
    )
    
    class Meta:
        db_table = 'contact_message_replies'
        ordering = ['created_at']
        verbose_name = 'Contact Message Reply'
        verbose_name_plural = 'Contact Message Replies'
        indexes = [
            models.Index(fields=['message', 'created_at']),
        ]
    
    def __str__(self):
        staff_name = self.staff.get_full_name() if self.staff else 'Unknown'
        return f"Reply by {staff_name} to {self.message.ticket_id}"


class ContactFormRateLimit(models.Model):
    """
    Rate limiting tracker for contact form submissions.
    
    Prevents spam by tracking submissions per IP and email.
    """
    
    identifier = models.CharField(
        max_length=255,
        db_index=True,
        help_text="IP address or email"
    )
    
    identifier_type = models.CharField(
        max_length=10,
        choices=[('ip', 'IP Address'), ('email', 'Email')],
        help_text="Type of identifier"
    )
    
    count = models.IntegerField(
        default=0,
        help_text="Number of submissions"
    )
    
    window_start = models.DateTimeField(
        help_text="Start of the rate limit window"
    )
    
    last_submission = models.DateTimeField(
        auto_now=True,
        help_text="Last submission time"
    )
    
    class Meta:
        db_table = 'contact_form_rate_limits'
        unique_together = [['identifier', 'identifier_type']]
        verbose_name = 'Contact Form Rate Limit'
        verbose_name_plural = 'Contact Form Rate Limits'
    
    def __str__(self):
        return f"{self.identifier_type}: {self.identifier} ({self.count} submissions)"
