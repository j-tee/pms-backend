"""
Contact Management Email Tasks

Celery tasks for sending contact-related emails.
"""
from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import ContactMessage, ContactMessageReply


@shared_task(bind=True, max_retries=3)
def send_contact_auto_reply(self, message_id):
    """
    Send auto-reply email to contact form submitter.
    
    Args:
        message_id: UUID of the ContactMessage
    """
    try:
        message = ContactMessage.objects.get(id=message_id)
        
        subject = "We've received your message - YEA PMS Support"
        
        # Plain text version
        text_content = f"""Dear {message.name},

Thank you for contacting YEA Poultry Management System.

We have received your message regarding: {message.get_subject_display()}

Our support team will review your inquiry and respond within 24-48 hours.

Your reference number: {message.ticket_id}

For urgent matters, please call us at +233 (0) 123-456-789 during business hours:
Monday - Friday: 8:00 AM - 6:00 PM
Saturday: 9:00 AM - 2:00 PM

Best regards,
YEA PMS Support Team

---
This is an automated message. Please do not reply directly to this email.
"""
        
        # HTML version (if template exists)
        try:
            html_content = render_to_string('contact/emails/auto_reply.html', {
                'name': message.name,
                'subject': message.get_subject_display(),
                'ticket_id': message.ticket_id,
                'message': message.message,
            })
        except:
            html_content = None
        
        # Send email
        if html_content:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(settings, 'CONTACT_EMAIL_FROM', settings.DEFAULT_FROM_EMAIL),
                to=[message.email],
                reply_to=[getattr(settings, 'CONTACT_EMAIL_REPLY_TO', 'support@yeapms.com')]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
        else:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=getattr(settings, 'CONTACT_EMAIL_FROM', settings.DEFAULT_FROM_EMAIL),
                recipient_list=[message.email],
                fail_silently=False
            )
        
        return f"Auto-reply sent to {message.email}"
    
    except ContactMessage.DoesNotExist:
        return f"Contact message {message_id} not found"
    
    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_staff_notification(self, message_id):
    """
    Send notification email to staff about new contact submission.
    
    Args:
        message_id: UUID of the ContactMessage
    """
    try:
        message = ContactMessage.objects.get(id=message_id)
        
        subject = f"New Contact Form Submission - {message.get_subject_display()}"
        
        admin_url = getattr(settings, 'ADMIN_URL', 'http://localhost:3000')
        
        # Plain text version
        text_content = f"""New contact form submission received:

From: {message.name} ({message.email})
Subject: {message.get_subject_display()}
Reference: {message.ticket_id}
Received: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}
IP Address: {message.ip_address or 'Unknown'}

Message:
{message.message}

---

View and respond: {admin_url}/admin/contact-messages/{message.id}
"""
        
        # HTML version (if template exists)
        try:
            html_content = render_to_string('contact/emails/staff_notification.html', {
                'message': message,
                'admin_url': admin_url,
            })
        except:
            html_content = None
        
        # Send to support team
        support_email = getattr(settings, 'CONTACT_EMAIL_TO', 'support@yeapms.com')
        
        if html_content:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(settings, 'CONTACT_EMAIL_FROM', settings.DEFAULT_FROM_EMAIL),
                to=[support_email],
                reply_to=[message.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
        else:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=getattr(settings, 'CONTACT_EMAIL_FROM', settings.DEFAULT_FROM_EMAIL),
                recipient_list=[support_email],
                fail_silently=False
            )
        
        return f"Staff notification sent for {message.ticket_id}"
    
    except ContactMessage.DoesNotExist:
        return f"Contact message {message_id} not found"
    
    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_reply_email(self, reply_id):
    """
    Send reply email to contact form submitter.
    
    Args:
        reply_id: UUID of the ContactMessageReply
    """
    try:
        reply = ContactMessageReply.objects.select_related('message', 'staff').get(id=reply_id)
        message = reply.message
        
        subject = f"Re: {message.get_subject_display()} - {message.ticket_id}"
        
        staff_name = reply.staff.get_full_name() if reply.staff else 'YEA PMS Support'
        
        # Plain text version
        text_content = f"""Dear {message.name},

Thank you for your patience. We have reviewed your inquiry.

---
{reply.reply_message}
---

If you have any additional questions, please reply to this email or submit a new inquiry through our contact form.

Reference: {message.ticket_id}

Best regards,
{staff_name}
YEA PMS Support Team
"""
        
        # HTML version (if template exists)
        try:
            html_content = render_to_string('contact/emails/reply.html', {
                'message': message,
                'reply': reply,
                'staff_name': staff_name,
            })
        except:
            html_content = None
        
        # Send email
        if html_content:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(settings, 'CONTACT_EMAIL_FROM', settings.DEFAULT_FROM_EMAIL),
                to=[message.email],
                reply_to=[getattr(settings, 'CONTACT_EMAIL_REPLY_TO', 'support@yeapms.com')]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
        else:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=getattr(settings, 'CONTACT_EMAIL_FROM', settings.DEFAULT_FROM_EMAIL),
                recipient_list=[message.email],
                fail_silently=False
            )
        
        # Mark email as sent
        reply.email_sent_at = timezone.now()
        reply.save()
        
        return f"Reply sent to {message.email}"
    
    except ContactMessageReply.DoesNotExist:
        return f"Contact reply {reply_id} not found"
    
    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc, countdown=60)
