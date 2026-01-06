# Celery & Redis - Background Task Processing

This document covers the background task processing infrastructure for YEA Poultry Management System.

## Overview

The system uses **Celery** with **Redis** as the message broker for:
- Asynchronous task execution (SMS, email, reports)
- Scheduled periodic tasks (analytics, cleanup, notifications)
- Background processing (heavy computations, external API calls)

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Django App    │────▶│     Redis       │────▶│  Celery Worker  │
│   (Producer)    │     │   (Broker)      │     │   (Consumer)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Celery Beat    │
                        │  (Scheduler)    │
                        └─────────────────┘
```

## Quick Start

### Development

```bash
# Start Redis (if not running)
sudo systemctl start redis

# Start Celery worker
celery -A core worker -l INFO

# Start Celery Beat (scheduler) - separate terminal
celery -A core beat -l INFO

# Or run both together (development only)
celery -A core worker --beat -l INFO
```

### Production

```bash
# Use systemd services
sudo systemctl start redis
sudo systemctl start pms-celery
sudo systemctl start pms-celery-beat
```

## Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_ENABLED=True
REDIS_URL=redis://localhost:6379/1

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Settings (core/settings.py)

```python
# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TIMEZONE = 'Africa/Accra'
```

## Available Tasks

### Core Tasks (`core/tasks.py`)

| Task | Description | Usage |
|------|-------------|-------|
| `send_sms_async` | Send SMS via Hubtel | `send_sms_async.delay(phone, message)` |
| `send_email_async` | Send email | `send_email_async.delay(subject, message, recipients)` |
| `cleanup_old_notifications` | Clean old data | Scheduled weekly |
| `generate_system_health_report` | Health check | Scheduled every 30 min |
| `aggregate_system_metrics` | System stats | Scheduled hourly |
| `send_admin_notification` | Alert admins | `send_admin_notification.delay('type', context)` |
| `process_bulk_sms` | Bulk SMS | `process_bulk_sms.delay(phones, message)` |

### Dashboard Tasks (`dashboards/tasks.py`)

| Task | Description | Schedule |
|------|-------------|----------|
| `aggregate_daily_metrics` | Cache dashboard data | Daily 1 AM |
| `aggregate_regional_metrics` | Regional stats | Daily 1:30 AM |
| `generate_weekly_report` | Weekly summary | Monday 6 AM |
| `refresh_dashboard_cache` | Manual refresh | On-demand |
| `generate_production_report` | Farm reports | On-demand |

### Farm Tasks (`farms/tasks.py`)

| Task | Description | Schedule |
|------|-------------|----------|
| `send_enrollment_reminders` | Batch reminders | Weekdays 9 AM |
| `notify_application_status_change` | Status notifications | On-demand |
| `notify_batch_enrollment_status` | Enrollment notifications | On-demand |
| `check_pending_applications` | Stale application check | Weekdays 10 AM |
| `sync_farmer_locations` | Location sync | Daily 3:30 AM |
| `calculate_farm_scores` | Score calculation | Daily 3 AM |

### Sales Revenue Tasks (`sales_revenue/tasks.py`)

| Task | Description | Schedule |
|------|-------------|----------|
| `check_expired_activations` | Marketplace expiry | Every 6 hours |
| `send_expiration_warnings` | Expiry warnings | Daily 8 AM |
| `calculate_daily_platform_revenue` | Revenue aggregation | Daily 2 AM |
| `sync_order_commissions` | Commission sync | Every 4 hours |
| `generate_seller_payout_report` | Payout reports | On-demand |

### Account Tasks (`accounts/tasks.py`)

| Task | Description | Schedule |
|------|-------------|----------|
| `send_welcome_notification` | Welcome message | On-demand |
| `send_password_reset_notification` | Password reset | On-demand |
| `send_mfa_alert` | MFA security alerts | On-demand |
| `send_login_alert` | Login notifications | On-demand |
| `cleanup_expired_tokens` | Token cleanup | Every 12 hours |
| `notify_role_change` | Role change alerts | On-demand |

### Advertising Tasks (`advertising/tasks.py`)

| Task | Description | Schedule |
|------|-------------|----------|
| `aggregate_advertising_analytics` | Ad analytics | Daily 4 AM |
| `process_new_advertiser_lead` | Lead processing | On-demand |
| `check_expiring_offers` | Offer expiry | Daily 8:30 AM |
| `deactivate_expired_offers` | Offer cleanup | Daily midnight |
| `calculate_partner_earnings` | Earnings calc | Sunday 5 AM |

## Usage Examples

### Sending SMS Asynchronously

```python
from core.tasks import send_sms_async

# Queue SMS for background sending
send_sms_async.delay('+233244123456', 'Your verification code is 123456')
```

### Sending Email

```python
from core.tasks import send_email_async

send_email_async.delay(
    subject='Welcome to YEA Poultry',
    message='Your account has been created.',
    recipient_list=['farmer@example.com'],
    html_message='<h1>Welcome!</h1><p>Your account is ready.</p>'
)
```

### Notifying Application Status

```python
from farms.tasks import notify_application_status_change

# When admin approves an application
notify_application_status_change.delay(
    str(application.id),
    'Approved',
    'Congratulations! Your farm has been approved.'
)
```

### Refreshing Dashboard Cache

```python
from dashboards.tasks import refresh_dashboard_cache

# Refresh specific cache keys
refresh_dashboard_cache.delay(['executive_overview', 'alerts'])
```

### Generating Reports

```python
from farms.tasks import generate_farm_activity_report

# Generate and email report
generate_farm_activity_report.delay(
    str(farm.id),
    days=30,
    email='farmer@example.com'
)
```

## Celery Beat Schedule

All scheduled tasks are defined in `core/celery.py`:

| Time | Tasks |
|------|-------|
| Every 30 min | System health check |
| Every hour | System metrics aggregation |
| Every 4 hours | Order commission sync |
| Every 6 hours | Marketplace activation check |
| Every 12 hours | Token cleanup |
| Daily 1 AM | Dashboard data aggregation |
| Daily 2 AM | Platform revenue calculation |
| Daily 3 AM | Farm score calculation |
| Daily 4 AM | Advertising analytics |
| Daily 8 AM | Expiration warnings |
| Weekdays 9 AM | Enrollment reminders |
| Weekdays 10 AM | Pending application check |
| Sunday 2 AM | Old data cleanup |
| Sunday 5 AM | Partner earnings |
| Monday 6 AM | Weekly reports |

## Monitoring

### Check Worker Status

```bash
# List active workers
celery -A core inspect active

# Check scheduled tasks
celery -A core inspect scheduled

# Check reserved tasks
celery -A core inspect reserved
```

### View Task Results

```python
from celery.result import AsyncResult

# Check task status
result = AsyncResult('task-id')
print(result.status)  # PENDING, STARTED, SUCCESS, FAILURE
print(result.result)  # Task return value or error
```

### Flower (Web UI)

```bash
# Install flower
pip install flower

# Start Flower
celery -A core flower --port=5555

# Access at http://localhost:5555
```

## Production Deployment

### Systemd Service for Celery Worker

Create `/etc/systemd/system/pms-celery.service`:

```ini
[Unit]
Description=YEA PMS Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/pms-backend
Environment=DJANGO_SETTINGS_MODULE=core.settings
ExecStart=/path/to/venv/bin/celery -A core worker --detach -l INFO --pidfile=/var/run/celery/worker.pid
ExecStop=/bin/kill -s TERM $MAINPID
PIDFile=/var/run/celery/worker.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

### Systemd Service for Celery Beat

Create `/etc/systemd/system/pms-celery-beat.service`:

```ini
[Unit]
Description=YEA PMS Celery Beat
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/pms-backend
Environment=DJANGO_SETTINGS_MODULE=core.settings
ExecStart=/path/to/venv/bin/celery -A core beat --detach -l INFO --pidfile=/var/run/celery/beat.pid
ExecStop=/bin/kill -s TERM $MAINPID
PIDFile=/var/run/celery/beat.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

### Enable Services

```bash
sudo mkdir -p /var/run/celery
sudo chown www-data:www-data /var/run/celery

sudo systemctl daemon-reload
sudo systemctl enable pms-celery pms-celery-beat
sudo systemctl start pms-celery pms-celery-beat
```

## Troubleshooting

### Tasks Not Executing

1. Check Redis is running: `redis-cli ping`
2. Check worker is running: `celery -A core inspect active`
3. Check broker URL in settings
4. Check worker logs: `journalctl -u pms-celery -f`

### Task Stuck in PENDING

1. Worker might be busy or crashed
2. Check worker logs for errors
3. Restart worker: `sudo systemctl restart pms-celery`

### Memory Issues

1. Add `--max-memory-per-child=300000` to worker command
2. Reduce worker concurrency
3. Check for memory leaks in tasks

### Beat Not Scheduling

1. Check Beat is running: `systemctl status pms-celery-beat`
2. Check Django Beat migrations: `python manage.py migrate django_celery_beat`
3. Check Beat logs: `journalctl -u pms-celery-beat -f`

## Testing

Run the test script:

```bash
chmod +x test_celery.sh
./test_celery.sh
```

This verifies:
- Redis connection
- Celery app import
- Task discovery
- Beat schedule configuration
- Synchronous task execution

## Best Practices

### DO

- ✅ Use `.delay()` for fire-and-forget tasks
- ✅ Use `.apply_async()` for advanced options (countdown, eta, etc.)
- ✅ Set reasonable time limits on tasks
- ✅ Use retries for external API calls
- ✅ Log task progress for debugging

### DON'T

- ❌ Don't pass Django model instances to tasks (use IDs)
- ❌ Don't run long-running tasks synchronously
- ❌ Don't assume task order (use chains if needed)
- ❌ Don't store large data in task results

### Example: Proper Task Pattern

```python
# ❌ WRONG - passing model instance
@shared_task
def process_order(order):  # Model can't be serialized properly
    order.process()

# ✅ CORRECT - passing ID and fetching in task
@shared_task
def process_order(order_id: str):
    from sales_revenue.models import Order
    order = Order.objects.get(pk=order_id)
    order.process()
```
