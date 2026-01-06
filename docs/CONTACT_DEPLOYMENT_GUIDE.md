# Contact Management System - Deployment Guide

## Quick Start

### 1. Database Migration
```bash
cd /home/teejay/Documents/Projects/YEA/PMS/pms-backend
python manage.py migrate
```

✅ **COMPLETED** - Tables created successfully

### 2. Environment Configuration

Add to `.env.production` or `.env.development`:

```bash
# ========================================
# CONTACT FORM SETTINGS
# ========================================

# Email address to receive contact form notifications
CONTACT_NOTIFICATION_EMAIL=support@yeapoultry.gov.gh

# Enable/disable auto-reply emails to form submitters
CONTACT_AUTO_REPLY_ENABLED=True

# Rate limiting settings
CONTACT_RATE_LIMIT_PER_HOUR=5
CONTACT_RATE_LIMIT_PER_DAY=20
CONTACT_MAX_MESSAGE_LENGTH=5000

# ========================================
# EMAIL SETTINGS (Required for notifications)
# ========================================

# Gmail SMTP Example (recommended for development/small scale)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
DEFAULT_FROM_EMAIL=YEA Poultry <noreply@yeapoultry.gov.gh>

# OR Production SMTP (e.g., SendGrid, AWS SES)
# EMAIL_HOST=smtp.sendgrid.net
# EMAIL_HOST_USER=apikey
# EMAIL_HOST_PASSWORD=SG.xxx
# EMAIL_PORT=587

# ========================================
# CELERY SETTINGS (Required for async emails)
# ========================================

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_ACCEPT_CONTENT=['json']
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_TIMEZONE=Africa/Accra

# ========================================
# REDIS SETTINGS (Required for rate limiting & Celery)
# ========================================

REDIS_ENABLED=True
REDIS_URL=redis://localhost:6379/1
```

### 3. Create Gmail App Password (for Gmail SMTP)

1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Search for "App passwords"
4. Create new app password for "Mail"
5. Copy the 16-character password
6. Use this as `EMAIL_HOST_PASSWORD` in `.env`

### 4. Install & Start Redis

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Verify Redis is running
redis-cli ping  # Should return "PONG"
```

#### macOS:
```bash
brew install redis
brew services start redis

# Verify
redis-cli ping
```

#### Docker:
```bash
docker run -d -p 6379:6379 --name redis redis:alpine
```

### 5. Start Celery Worker

#### Development:
```bash
cd /home/teejay/Documents/Projects/YEA/PMS/pms-backend
celery -A core worker -l info
```

**Keep this terminal running** - it processes email tasks in the background.

#### Production (systemd):
Create `/etc/systemd/system/celery-pms.service`:

```ini
[Unit]
Description=Celery Worker for PMS Backend
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/pms-backend
Environment="PATH=/var/www/pms-backend/venv/bin"
ExecStart=/var/www/pms-backend/venv/bin/celery -A core worker \
    --detach \
    --loglevel=info \
    --logfile=/var/log/celery/pms-worker.log \
    --pidfile=/var/run/celery/pms-worker.pid

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable celery-pms
sudo systemctl start celery-pms
sudo systemctl status celery-pms
```

---

## Testing the System

### Test 1: Contact Form Submission (Public API)

```bash
curl -X POST http://localhost:8000/api/contact/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "support",
    "message": "This is a test message to verify the contact form is working correctly."
  }'
```

**Expected Response (201 Created):**
```json
{
  "success": true,
  "message": "Thank you for contacting us. We'll get back to you soon.",
  "ticket_id": "CNT-20250115"
}
```

**What Happens:**
1. ✅ Message saved to database
2. ✅ Auto-reply email sent to test@example.com (via Celery)
3. ✅ Notification email sent to support team (CONTACT_NOTIFICATION_EMAIL)
4. ✅ Rate limit record created

**Check Celery Logs:**
```bash
# You should see tasks being executed
[2025-01-15 10:30:15,123: INFO/MainProcess] Task contact.tasks.send_contact_auto_reply[xxx] received
[2025-01-15 10:30:16,456: INFO/MainProcess] Task contact.tasks.send_staff_notification[xxx] received
```

### Test 2: Rate Limiting

Submit the same form 6 times rapidly:

```bash
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/contact/submit \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"Test User $i\",
      \"email\": \"test$i@example.com\",
      \"subject\": \"support\",
      \"message\": \"Test message number $i to verify rate limiting works.\"
    }"
  echo ""
done
```

**Expected:**
- First 5 submissions: `201 Created`
- 6th submission: `429 Too Many Requests`

```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

### Test 3: Admin List Messages (Requires Auth Token)

First, get an admin token:
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "your-admin-password"
  }'
```

Then list messages:
```bash
curl http://localhost:8000/api/admin/contact-messages/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "ticket_id": "CNT-20250115",
      "name": "Test User",
      "email": "test@example.com",
      "subject": "support",
      "status": "new",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### Test 4: Update Message Status

```bash
curl -X PATCH http://localhost:8000/api/admin/contact-messages/{MESSAGE_ID}/update/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress"
  }'
```

### Test 5: Reply to Message

```bash
curl -X POST http://localhost:8000/api/admin/contact-messages/{MESSAGE_ID}/reply/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Thank you for your inquiry. We have reviewed your request and here is our response...",
    "send_email": true
  }'
```

**What Happens:**
1. ✅ Reply saved to database
2. ✅ Email sent to original sender (test@example.com)
3. ✅ Message status updated to 'resolved'

---

## Verify Email Delivery

### Check Django Logs
```bash
tail -f logs/django.log  # Or wherever your logs are

# Look for:
# Email sent successfully to test@example.com
```

### Check Celery Logs
```bash
celery -A core worker -l debug  # Restart with debug logging

# Look for:
# [2025-01-15 10:30:16,789: INFO] Email delivered: contact.tasks.send_contact_auto_reply
```

### Test Email Configuration
```bash
python manage.py shell

>>> from django.core.mail import send_mail
>>> send_mail(
...     'Test Email',
...     'This is a test message.',
...     'noreply@yeapoultry.gov.gh',
...     ['your-email@example.com'],
...     fail_silently=False,
... )
1  # Success!
```

---

## Django Admin Interface

### Access Admin Panel
http://localhost:8000/admin/contact/contactmessage/

**Login with superuser credentials**

### Features Available:
- View all contact messages
- Filter by status, subject, assigned staff
- Search by name, email, message
- Bulk status updates
- Assign messages to staff
- View message details with replies
- Soft delete (mark as deleted without removing from DB)

---

## Frontend Integration

### CORS Configuration

Add frontend domain to `core/settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # React dev server
    "https://pms.yeapoultry.gov.gh",  # Production frontend
]
```

### API Endpoints for Frontend

**Public (No Auth Required):**
- `POST /api/contact/submit` - Submit contact form

**Admin (Requires JWT Token):**
- `GET /api/admin/contact-messages/` - List all messages
- `GET /api/admin/contact-messages/{id}/` - Get message details
- `PATCH /api/admin/contact-messages/{id}/update/` - Update message
- `POST /api/admin/contact-messages/{id}/reply/` - Reply to message
- `GET /api/admin/contact-stats/` - Get statistics

### Sample React Integration

See `docs/CONTACT_SYSTEM_DOCS.md` for complete React examples.

---

## Production Deployment Checklist

### 1. Security
- [ ] Enable HTTPS (SSL certificate)
- [ ] Set `DEBUG=False` in production
- [ ] Use strong `SECRET_KEY`
- [ ] Configure ALLOWED_HOSTS properly
- [ ] Enable CSRF protection
- [ ] Add reCAPTCHA (optional, future enhancement)

### 2. Email
- [ ] Use production SMTP service (SendGrid, AWS SES, etc.)
- [ ] Configure SPF, DKIM, DMARC records for email domain
- [ ] Test email delivery to various providers (Gmail, Yahoo, Outlook)
- [ ] Set up email bounce handling
- [ ] Monitor email delivery rates

### 3. Performance
- [ ] Redis running and optimized
- [ ] Celery workers running (multiple workers for high traffic)
- [ ] Database connection pooling (PgBouncer)
- [ ] Enable database query caching
- [ ] Add Nginx rate limiting (additional layer)

### 4. Monitoring
- [ ] Set up error tracking (Sentry, Rollbar)
- [ ] Monitor Celery task queue length
- [ ] Monitor email delivery failures
- [ ] Set up alerts for high rate limit violations
- [ ] Log aggregation (ELK stack, CloudWatch)

### 5. Backup
- [ ] Regular database backups
- [ ] Backup email templates
- [ ] Backup environment variables

---

## Troubleshooting

### Issue: Emails Not Sending

**Symptoms:** Contact form works but no emails received.

**Diagnosis:**
```bash
# Check Celery is running
ps aux | grep celery

# Check Celery logs
tail -f /var/log/celery/pms-worker.log

# Check Redis connection
redis-cli ping

# Test email config
python manage.py shell
>>> from contact.tasks import send_contact_auto_reply
>>> send_contact_auto_reply.delay('test@example.com', 'Test', 'CNT-12345678', 'Test')
```

**Solutions:**
1. Verify Celery worker is running
2. Check email credentials in `.env`
3. Test SMTP connection manually
4. Check firewall rules (port 587/465)
5. Review email provider logs

### Issue: Rate Limit Not Working

**Symptoms:** Can submit unlimited forms.

**Diagnosis:**
```bash
# Check Redis
redis-cli ping

# Check rate limit records
python manage.py shell
>>> from contact.models import ContactFormRateLimit
>>> ContactFormRateLimit.objects.all()
```

**Solutions:**
1. Ensure Redis is running
2. Check REDIS_URL in settings
3. Verify rate_limiting.py is imported correctly
4. Check IP address detection (behind proxy?)

### Issue: 403 Forbidden on Admin Endpoints

**Symptoms:** Admin user cannot access `/api/admin/contact-messages/`.

**Diagnosis:**
```bash
python manage.py shell
>>> from accounts.models import User
>>> user = User.objects.get(email='admin@example.com')
>>> user.role
'FARMER'  # ❌ Wrong! Should be SUPER_ADMIN, NATIONAL_ADMIN, or REGIONAL_COORDINATOR
```

**Solution:**
```bash
python manage.py shell
>>> from accounts.models import User
>>> user = User.objects.get(email='admin@example.com')
>>> user.role = 'SUPER_ADMIN'
>>> user.save()
```

### Issue: Migration Errors

**Symptoms:** `python manage.py migrate` fails.

**Solutions:**
```bash
# Check for conflicting migrations
python manage.py showmigrations contact

# Reset contact migrations (⚠️ DESTRUCTIVE - only if no production data)
python manage.py migrate contact zero
rm contact/migrations/0001_initial.py
python manage.py makemigrations contact
python manage.py migrate contact

# OR manually fix migration dependencies
# Edit contact/migrations/0001_initial.py and check dependencies
```

---

## Maintenance Tasks

### Clean Up Old Rate Limit Records

Run daily via cron or Celery Beat:

```python
# Add to core/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from contact.models import ContactFormRateLimit

@shared_task
def cleanup_old_rate_limits():
    """Delete rate limit records older than 24 hours."""
    cutoff = timezone.now() - timedelta(hours=24)
    deleted_count = ContactFormRateLimit.objects.filter(
        window_start__lt=cutoff
    ).delete()
    return f"Deleted {deleted_count[0]} old rate limit records"
```

Add to Celery Beat schedule in `core/celery.py`:

```python
app.conf.beat_schedule = {
    'cleanup-old-rate-limits': {
        'task': 'core.tasks.cleanup_old_rate_limits',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}
```

### Archive Resolved Messages

Monthly archiving (optional):

```bash
python manage.py shell

>>> from contact.models import ContactMessage
>>> from django.utils import timezone
>>> from datetime import timedelta
>>> 
>>> # Soft delete resolved messages older than 90 days
>>> cutoff = timezone.now() - timedelta(days=90)
>>> ContactMessage.objects.filter(
...     status='resolved',
...     updated_at__lt=cutoff
... ).update(is_deleted=True)
```

---

## Performance Optimization

### Database Indexes (Already Applied)

```sql
-- Automatically created by Django migration
CREATE INDEX ON contact_contactmessage (status, created_at);
CREATE INDEX ON contact_contactmessage (assigned_to_id, status);
CREATE INDEX ON contact_contactmessage (email);
CREATE INDEX ON contact_contactmessagereply (message_id, created_at);
```

### Celery Configuration (High Traffic)

```python
# core/celery.py - Add these settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Restart workers after 1000 tasks
```

Start multiple workers:
```bash
celery -A core worker -l info --concurrency=4  # 4 concurrent tasks
```

### Nginx Rate Limiting (Additional Layer)

```nginx
# /etc/nginx/sites-available/pms-backend

http {
    limit_req_zone $binary_remote_addr zone=contactform:10m rate=5r/h;
    
    server {
        location /api/contact/submit {
            limit_req zone=contactform burst=2;
            proxy_pass http://127.0.0.1:8000;
        }
    }
}
```

---

## Next Steps

1. ✅ Migrations completed
2. ✅ Email templates created
3. ⏳ Configure `.env` with email credentials
4. ⏳ Start Redis and Celery worker
5. ⏳ Test contact form submission
6. ⏳ Test admin endpoints
7. ⏳ Integrate with frontend
8. ⏳ Deploy to production

---

## Support

For questions or issues:
- Email: support@yeapoultry.gov.gh
- Documentation: `/docs/CONTACT_SYSTEM_DOCS.md`
- Issue Tracker: GitHub repository issues

---

**Last Updated:** January 15, 2025  
**Version:** 1.0.0  
**Status:** Ready for Production ✅
