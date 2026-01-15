#!/bin/bash
# =============================================================================
# YEA Poultry Management System - Celery Test Script
# =============================================================================
# This script helps verify Celery and Redis are working correctly.
#
# Usage:
#   chmod +x test_celery.sh
#   ./test_celery.sh
# =============================================================================

set -e

echo "=========================================="
echo "YEA PMS - Celery & Redis Verification"
echo "=========================================="
echo ""

# Check if Redis is running
echo "1. Checking Redis connection..."
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "   ✓ Redis is running"
else
    echo "   ✗ Redis is not running. Start with: sudo systemctl start redis"
    echo "   Or install with: sudo apt install redis-server"
    exit 1
fi

# Check Redis connection from Python
echo ""
echo "2. Testing Redis from Python..."
python -c "
import redis
try:
    r = redis.Redis.from_url('redis://localhost:6379/0')
    r.ping()
    print('   ✓ Python can connect to Redis')
except Exception as e:
    print(f'   ✗ Redis connection failed: {e}')
    exit(1)
"

# Test Celery app import
echo ""
echo "3. Testing Celery app import..."
python -c "
from core.celery import app
print('   ✓ Celery app imported successfully')
print(f'   - App name: {app.main}')
print(f'   - Broker: {app.conf.broker_url}')
print(f'   - Result backend: {app.conf.result_backend}')
"

# Test task discovery
echo ""
echo "4. Testing task discovery..."
python -c "
from core.celery import app
app.autodiscover_tasks()
tasks = [t for t in app.tasks.keys() if not t.startswith('celery.')]
print(f'   ✓ Discovered {len(tasks)} tasks:')
for t in sorted(tasks)[:20]:
    print(f'     - {t}')
if len(tasks) > 20:
    print(f'     ... and {len(tasks) - 20} more')
"

# Test individual task imports
echo ""
echo "5. Testing task imports..."
python -c "
from core.tasks import send_sms_async, send_email_async, generate_system_health_report
print('   ✓ core.tasks imported')
from dashboards.tasks import aggregate_daily_metrics, generate_weekly_report
print('   ✓ dashboards.tasks imported')
from sales_revenue.tasks import check_expired_activations, calculate_daily_platform_revenue
print('   ✓ sales_revenue.tasks imported')
from farms.tasks import send_enrollment_reminders, notify_application_status_change
print('   ✓ farms.tasks imported')
from accounts.tasks import send_welcome_notification, cleanup_expired_tokens
print('   ✓ accounts.tasks imported')
from advertising.tasks import aggregate_advertising_analytics, process_new_advertiser_lead
print('   ✓ advertising.tasks imported')
"

# Test beat schedule
echo ""
echo "6. Testing Celery Beat schedule..."
python -c "
from core.celery import app
beat_tasks = app.conf.beat_schedule
print(f'   ✓ Celery Beat configured with {len(beat_tasks)} scheduled tasks:')
for name in sorted(beat_tasks.keys())[:15]:
    task = beat_tasks[name]
    print(f'     - {name}: {task[\"task\"]}')
if len(beat_tasks) > 15:
    print(f'     ... and {len(beat_tasks) - 15} more')
"

# Test synchronous task execution (optional)
echo ""
echo "7. Testing synchronous task execution..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()
from core.tasks import generate_system_health_report
result = generate_system_health_report()
print('   ✓ Health check task executed:')
print(f'     - Database: {result.get(\"database\", \"unknown\")}')
print(f'     - Cache: {result.get(\"cache\", \"unknown\")}')
"

echo ""
echo "=========================================="
echo "All tests passed! Celery is configured correctly."
echo "=========================================="
echo ""
echo "To start Celery worker:"
echo "  celery -A core worker -l INFO"
echo ""
echo "To start Celery Beat (scheduler):"
echo "  celery -A core beat -l INFO"
echo ""
echo "To start both in one terminal (development only):"
echo "  celery -A core worker --beat -l INFO"
echo ""
echo "For production, use the systemd services in deployment/systemd/"
echo "=========================================="
