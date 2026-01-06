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


@shared_task
def aggregate_system_metrics():
    """
    Aggregate system-wide metrics for monitoring dashboards.
    
    Runs periodically to cache key system stats.
    """
    from django.core.cache import cache
    from accounts.models import User
    from farms.models import Farm
    
    logger.info("Aggregating system metrics...")
    
    try:
        metrics = {
            'users': {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
                'farmers': User.objects.filter(role='FARMER').count(),
                'staff': User.objects.exclude(role='FARMER').count(),
            },
            'farms': {
                'total': Farm.objects.count(),
                'approved': Farm.objects.filter(application_status='Approved').count(),
                'active': Farm.objects.filter(farm_status='Active').count(),
            },
            'aggregated_at': timezone.now().isoformat()
        }
        
        cache.set('system:metrics', metrics, timeout=3600)
        logger.info(f"System metrics aggregated: {metrics['users']['total']} users, {metrics['farms']['total']} farms")
        return metrics
    except Exception as exc:
        logger.error(f"Failed to aggregate system metrics: {exc}")
        return {'status': 'error', 'error': str(exc)}


@shared_task
def backup_critical_data():
    """
    Create backup records for critical configuration data.
    
    This is a safety task that logs current critical settings.
    Actual database backups should be handled at infrastructure level.
    """
    from sales_revenue.models import PlatformSettings
    from django.core.cache import cache
    import json
    
    logger.info("Creating critical data backup record...")
    
    try:
        settings = PlatformSettings.get_settings()
        
        backup_record = {
            'timestamp': timezone.now().isoformat(),
            'platform_settings': {
                'commission_tier_1': float(settings.commission_tier_1_percentage),
                'commission_tier_2': float(settings.commission_tier_2_percentage),
                'commission_tier_3': float(settings.commission_tier_3_percentage),
                'marketplace_activation_fee': float(settings.marketplace_activation_fee),
                'marketplace_trial_days': settings.marketplace_trial_days,
            }
        }
        
        # Store backup in cache (would be stored in S3/backup storage in production)
        cache.set('backup:platform_settings:latest', json.dumps(backup_record), timeout=604800)  # 7 days
        
        logger.info("Critical data backup record created")
        return backup_record
    except Exception as exc:
        logger.error(f"Failed to create backup record: {exc}")
        return {'status': 'error', 'error': str(exc)}


@shared_task
def purge_stale_cache():
    """
    Purge stale cache entries.
    
    Clears old cached data that may be outdated.
    """
    from django.core.cache import cache
    
    logger.info("Purging stale cache entries...")
    
    stale_patterns = [
        'dashboard:production_trend_*',
        'report:*:daily',
    ]
    
    # Note: Django's cache doesn't support pattern deletion natively
    # This is a placeholder - in production with Redis, use scan_iter
    
    logger.info("Stale cache purge completed (placeholder)")
    return {'status': 'completed'}


@shared_task
def send_admin_notification(notification_type: str, context: dict = None):
    """
    Send notification to admin users.
    
    Usage:
        from core.tasks import send_admin_notification
        send_admin_notification.delay('new_lead', {'company': 'ABC'})
    """
    from accounts.models import User
    
    logger.info(f"Sending admin notification: {notification_type}")
    
    context = context or {}
    
    notification_templates = {
        'new_lead': {
            'subject': "New Advertiser Lead",
            'message': "A new advertiser lead has been submitted. Check the admin panel.",
        },
        'high_mortality': {
            'subject': "High Mortality Alert",
            'message': f"High mortality detected at farm. Please investigate.",
        },
        'system_error': {
            'subject': "System Error Alert",
            'message': f"A system error occurred: {context.get('error', 'Unknown')}",
        },
        'security_alert': {
            'subject': "Security Alert",
            'message': f"Security event: {context.get('event', 'Unknown')}",
        }
    }
    
    template = notification_templates.get(notification_type, {
        'subject': f"Admin Notification: {notification_type}",
        'message': f"Notification details: {context}"
    })
    
    admin_emails = list(User.objects.filter(
        role__in=['SUPER_ADMIN', 'YEA_OFFICIAL'],
        is_active=True,
        email__isnull=False
    ).exclude(email='').values_list('email', flat=True)[:5])
    
    if admin_emails:
        send_email_async.delay(
            subject=f"[YEA PMS] {template['subject']}",
            message=template['message'],
            recipient_list=admin_emails
        )
        logger.info(f"Admin notification sent to {len(admin_emails)} admins")
        return {'status': 'sent', 'recipients': len(admin_emails)}
    
    logger.warning("No admin emails found for notification")
    return {'status': 'no_recipients'}


@shared_task
def process_bulk_sms(phone_numbers: list, message: str, batch_size: int = 50):
    """
    Send SMS to multiple recipients in batches.
    
    Prevents overwhelming the SMS service.
    
    Usage:
        from core.tasks import process_bulk_sms
        process_bulk_sms.delay(['+233...', '+233...'], 'Your message')
    """
    import time
    
    logger.info(f"Processing bulk SMS to {len(phone_numbers)} recipients")
    
    sent = 0
    failed = 0
    
    for i, phone in enumerate(phone_numbers):
        try:
            send_sms_async.delay(phone, message)
            sent += 1
            
            # Rate limiting: pause every batch_size messages
            if (i + 1) % batch_size == 0:
                time.sleep(2)  # 2 second pause between batches
        except Exception as exc:
            logger.error(f"Failed to queue SMS for {phone}: {exc}")
            failed += 1
    
    logger.info(f"Bulk SMS complete: {sent} sent, {failed} failed")
    return {'sent': sent, 'failed': failed, 'total': len(phone_numbers)}


@shared_task
def clear_session_data(user_id: str = None):
    """
    Clear session data for a user or all users.
    
    Useful for forcing re-authentication after security events.
    """
    from django.contrib.sessions.models import Session
    from django.contrib.auth import get_user_model
    
    logger.info(f"Clearing session data for {'user ' + user_id if user_id else 'all users'}")
    
    if user_id:
        # Clear sessions for specific user (requires custom session storage)
        # This is a simplified version
        deleted = 0
        for session in Session.objects.all():
            try:
                data = session.get_decoded()
                if str(data.get('_auth_user_id')) == user_id:
                    session.delete()
                    deleted += 1
            except Exception:
                pass
        return {'deleted_sessions': deleted, 'user_id': user_id}
    else:
        # Clear all expired sessions
        Session.objects.filter(expire_date__lt=timezone.now()).delete()
        return {'status': 'expired_sessions_cleared'}
