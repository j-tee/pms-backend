"""
Celery configuration for YEA Poultry Management System.

This module configures Celery for background task processing.
Required for scaling to handle high traffic loads.

Tasks to run in background:
- SMS notifications (Hubtel API calls)
- Email sending
- Report generation
- Batch processing operations
- Data aggregation for dashboards
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Create Celery app
app = Celery('core')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# =============================================================================
# CELERY BEAT SCHEDULE - Periodic Tasks
# =============================================================================
app.conf.beat_schedule = {
    # Daily dashboard data aggregation (run at 1 AM)
    'aggregate-dashboard-data': {
        'task': 'dashboards.tasks.aggregate_daily_metrics',
        'schedule': crontab(hour=1, minute=0),
    },
    
    # Check expired marketplace activations (run every 6 hours)
    'check-marketplace-activations': {
        'task': 'sales_revenue.tasks.check_expired_activations',
        'schedule': crontab(hour='*/6', minute=0),
    },
    
    # Send batch enrollment reminders (run at 9 AM on weekdays)
    'batch-enrollment-reminders': {
        'task': 'farms.tasks.send_enrollment_reminders',
        'schedule': crontab(hour=9, minute=0, day_of_week='1-5'),
    },
    
    # Database cleanup - old notifications (run weekly on Sunday 2 AM)
    'cleanup-old-notifications': {
        'task': 'core.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
    },
    
    # Generate weekly reports (run Monday 6 AM)
    'generate-weekly-reports': {
        'task': 'dashboards.tasks.generate_weekly_report',
        'schedule': crontab(hour=6, minute=0, day_of_week=1),
    },
}

# Celery configuration
app.conf.update(
    # Task result expiry
    result_expires=3600,  # 1 hour
    
    # Task time limits
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Retry policy
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Prefetch multiplier (1 = fair distribution)
    worker_prefetch_multiplier=1,
    
    # Serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Timezone
    timezone='Africa/Accra',
    enable_utc=True,
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
