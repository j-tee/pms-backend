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
    # ==========================================================================
    # DASHBOARD & ANALYTICS (Daily)
    # ==========================================================================
    
    # Daily dashboard data aggregation (run at 1 AM)
    'aggregate-dashboard-data': {
        'task': 'dashboards.tasks.aggregate_daily_metrics',
        'schedule': crontab(hour=1, minute=0),
    },
    
    # Aggregate regional metrics (run at 1:30 AM)
    'aggregate-regional-metrics': {
        'task': 'dashboards.tasks.aggregate_regional_metrics',
        'schedule': crontab(hour=1, minute=30),
    },
    
    # Generate weekly reports (run Monday 6 AM)
    'generate-weekly-reports': {
        'task': 'dashboards.tasks.generate_weekly_report',
        'schedule': crontab(hour=6, minute=0, day_of_week=1),
    },
    
    # Calculate daily platform revenue (run at 2 AM)
    'calculate-daily-revenue': {
        'task': 'sales_revenue.tasks.calculate_daily_platform_revenue',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # ==========================================================================
    # MARKETPLACE & SUBSCRIPTIONS (Every 6 hours)
    # ==========================================================================
    
    # Check expired marketplace activations (run every 6 hours)
    'check-marketplace-activations': {
        'task': 'sales_revenue.tasks.check_expired_activations',
        'schedule': crontab(hour='*/6', minute=0),
    },
    
    # Send expiration warnings (run at 8 AM daily)
    'send-expiration-warnings': {
        'task': 'sales_revenue.tasks.send_expiration_warnings',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Sync order commissions (run every 4 hours)
    'sync-order-commissions': {
        'task': 'sales_revenue.tasks.sync_order_commissions',
        'schedule': crontab(hour='*/4', minute=15),
    },
    
    # ==========================================================================
    # FARMS & ENROLLMENT (Weekday mornings)
    # ==========================================================================
    
    # Send batch enrollment reminders (run at 9 AM on weekdays)
    'batch-enrollment-reminders': {
        'task': 'farms.tasks.send_enrollment_reminders',
        'schedule': crontab(hour=9, minute=0, day_of_week='1-5'),
    },
    
    # Check stale pending applications (run at 10 AM weekdays)
    'check-pending-applications': {
        'task': 'farms.tasks.check_pending_applications',
        'schedule': crontab(hour=10, minute=0, day_of_week='1-5'),
    },
    
    # Calculate farm scores (run at 3 AM daily)
    'calculate-farm-scores': {
        'task': 'farms.tasks.calculate_farm_scores',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # Sync farmer locations (run at 3:30 AM daily)
    'sync-farmer-locations': {
        'task': 'farms.tasks.sync_farmer_locations',
        'schedule': crontab(hour=3, minute=30),
    },
    
    # ==========================================================================
    # ADVERTISING (Daily)
    # ==========================================================================
    
    # Aggregate advertising analytics (run at 4 AM)
    'aggregate-advertising-analytics': {
        'task': 'advertising.tasks.aggregate_advertising_analytics',
        'schedule': crontab(hour=4, minute=0),
    },
    
    # Check expiring offers (run at 8:30 AM)
    'check-expiring-offers': {
        'task': 'advertising.tasks.check_expiring_offers',
        'schedule': crontab(hour=8, minute=30),
    },
    
    # Deactivate expired offers (run at midnight)
    'deactivate-expired-offers': {
        'task': 'advertising.tasks.deactivate_expired_offers',
        'schedule': crontab(hour=0, minute=5),
    },
    
    # Calculate partner earnings (run weekly on Sunday)
    'calculate-partner-earnings': {
        'task': 'advertising.tasks.calculate_partner_earnings',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),
    },
    
    # ==========================================================================
    # ACCOUNTS & SECURITY (Regular intervals)
    # ==========================================================================
    
    # Cleanup expired tokens (run every 12 hours)
    'cleanup-expired-tokens': {
        'task': 'accounts.tasks.cleanup_expired_tokens',
        'schedule': crontab(hour='*/12', minute=45),
    },
    
    # Check for dormant accounts (run weekly on Sunday)
    'check-dormant-accounts': {
        'task': 'accounts.tasks.deactivate_dormant_accounts',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
    },
    
    # ==========================================================================
    # SYSTEM MAINTENANCE (Various intervals)
    # ==========================================================================
    
    # Database cleanup - old notifications (run weekly on Sunday 2 AM)
    'cleanup-old-notifications': {
        'task': 'core.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
    },
    
    # System health check (run every 30 minutes)
    'system-health-check': {
        'task': 'core.tasks.generate_system_health_report',
        'schedule': crontab(minute='*/30'),
    },
    
    # Aggregate system metrics (run every hour)
    'aggregate-system-metrics': {
        'task': 'core.tasks.aggregate_system_metrics',
        'schedule': crontab(minute=5),  # Every hour at :05
    },
    
    # Backup critical data (run daily at 5 AM)
    'backup-critical-data': {
        'task': 'core.tasks.backup_critical_data',
        'schedule': crontab(hour=5, minute=0),
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
