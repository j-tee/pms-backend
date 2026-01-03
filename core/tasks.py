"""
Core Celery tasks for YEA Poultry Management System.

These are background tasks that should NOT block API requests.
Move I/O-bound operations (SMS, email, file processing) here.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_sms_async(self, phone_number: str, message: str, reference: str = None):
    """
    Send SMS asynchronously via Celery.
    
    Use this instead of direct SMS sending to avoid blocking requests.
    
    Usage:
        from core.tasks import send_sms_async
        send_sms_async.delay('+233244123456', 'Your message here')
    """
    try:
        from core.sms_service import SMSService
        result = SMSService.send_sms(
            phone_number=phone_number,
            message=message,
            reference=reference
        )
        logger.info(f"SMS sent to {phone_number}: {result}")
        return result
    except Exception as exc:
        logger.error(f"SMS sending failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_email_async(self, subject: str, message: str, recipient_list: list, html_message: str = None):
    """
    Send email asynchronously via Celery.
    
    Usage:
        from core.tasks import send_email_async
        send_email_async.delay(
            'Subject',
            'Plain text message',
            ['user@example.com'],
            html_message='<h1>HTML content</h1>'
        )
    """
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent to {recipient_list}: {result}")
        return result
    except Exception as exc:
        logger.error(f"Email sending failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def cleanup_old_notifications(days_old: int = 90):
    """
    Clean up old notifications and system logs.
    
    Scheduled via Celery Beat to run weekly.
    """
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    # Clean up old JWT blacklisted tokens
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        deleted_count, _ = OutstandingToken.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        logger.info(f"Cleaned up {deleted_count} old JWT tokens")
    except Exception as exc:
        logger.error(f"Failed to clean up JWT tokens: {exc}")
    
    return f"Cleanup completed for records older than {days_old} days"


@shared_task
def generate_system_health_report():
    """
    Generate a system health report for monitoring.
    
    Can be called manually or scheduled.
    """
    from django.db import connection
    from django.core.cache import cache
    
    report = {
        'timestamp': timezone.now().isoformat(),
        'database': 'healthy',
        'cache': 'healthy',
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        report['database'] = 'healthy'
    except Exception as exc:
        report['database'] = f'unhealthy: {exc}'
    
    # Check cache
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            report['cache'] = 'healthy'
        else:
            report['cache'] = 'unhealthy: cache not responding'
    except Exception as exc:
        report['cache'] = f'unhealthy: {exc}'
    
    logger.info(f"System health report: {report}")
    return report
