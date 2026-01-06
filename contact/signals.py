"""
Contact Management Signals

Django signals for contact-related events.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ContactMessage


@receiver(post_save, sender=ContactMessage)
def contact_message_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for contact message creation/update.
    
    Can be used for additional logging, notifications, or integrations.
    """
    if created:
        # Log new contact submission
        print(f"New contact message: {instance.ticket_id} from {instance.email}")
        
        # Could integrate with Slack, Discord, etc. here
        # Example: send_slack_notification(instance)
