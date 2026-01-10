# Production Secret Rotation Guide

**Date:** January 10, 2026  
**Purpose:** Rotate production secrets following security hardening in commit cf896a2

## Overview

As part of our security improvements, we removed hardcoded fallback values from `core/settings.py`. All secrets must now be explicitly set in environment variables.

## Critical Change

**Before (commit ffd6bab and earlier):**
```python
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-...')  # Had fallback
```

**After (commit cf896a2):**
```python
SECRET_KEY = os.getenv('SECRET_KEY')  # No fallback - REQUIRED
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")
```

## Required Actions

### 1. Generate New SECRET_KEY

On your server, generate a new Django secret key:

```bash
# SSH into your production server
ssh user@your-server

# Activate virtual environment
cd /path/to/pms-backend
source venv/bin/activate

# Generate new secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Example output:**
```
dt5@@x-m@-!fco)w!_$6l9$%9814@d91+^9u=td2mv_f8bpyjv
```

### 2. Update Production Environment File

Edit your production `.env.production` file:

```bash
nano .env.production
```

Update the SECRET_KEY line:
```bash
# OLD (placeholder - MUST be changed)
SECRET_KEY=CHANGE_THIS_TO_A_RANDOM_SECRET_KEY_IN_PRODUCTION

# NEW (use your generated key)
SECRET_KEY=dt5@@x-m@-!fco)w!_$6l9$%9814@d91+^9u=td2mv_f8bpyjv
```

### 3. Verify Required Environment Variables

Ensure ALL of these are set in `.env.production`:

```bash
# CRITICAL - Django will not start without these
SECRET_KEY=<your-generated-key>
DB_NAME=poultry_db
DB_USER=<your-db-user>
DB_PASSWORD=<your-db-password>
DB_HOST=localhost
DB_PORT=5432

# Production settings
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Optional but recommended
HUBTEL_CLIENT_ID=<your-hubtel-client-id>
HUBTEL_CLIENT_SECRET=<your-hubtel-secret>
PAYSTACK_SECRET_KEY=<your-paystack-key>
```

### 4. Update systemd Service (if needed)

If you're using systemd, ensure the service file loads the environment:

```bash
sudo nano /etc/systemd/system/pms-backend.service
```

Verify this line exists:
```ini
[Service]
EnvironmentFile=/path/to/pms-backend/.env.production
```

### 5. Restart Services

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Restart Django/Gunicorn
sudo systemctl restart pms-backend

# Restart Celery workers
sudo systemctl restart celery-pms

# Check status
sudo systemctl status pms-backend
sudo systemctl status celery-pms
```

### 6. Verify Deployment

Test that the application starts successfully:

```bash
# Check Django can start
cd /path/to/pms-backend
source venv/bin/activate
python manage.py check --deploy

# Check logs for any SECRET_KEY errors
sudo journalctl -u pms-backend -n 50
```

You should see NO errors like:
- ❌ `ValueError: SECRET_KEY environment variable is not set`
- ❌ `django.core.exceptions.ImproperlyConfigured: The SECRET_KEY setting must not be empty`

## Development Environment Update

### Local Development (.env.development)

Developers should also update their local `.env.development`:

```bash
# Generate a new development key (different from production!)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Add to .env.development
SECRET_KEY=<generated-development-key>
```

### Test Environment (.env.test)

The `.env.test` file already has a test key:
```bash
SECRET_KEY=test-secret-key-not-for-production-use-only-for-testing
```

This is fine for CI/CD testing environments.

## Troubleshooting

### Error: "SECRET_KEY environment variable is not set"

**Cause:** SECRET_KEY is missing from your environment file.

**Fix:**
1. Generate a new key (see step 1 above)
2. Add it to `.env.production`
3. Restart services

### Error: "No such file or directory: .env.production"

**Cause:** Environment file doesn't exist.

**Fix:**
```bash
cp .env.example .env.production
# Then edit .env.production and set all values
```

### Application runs but logs show warnings about missing secrets

**Cause:** Optional service credentials (Hubtel, Paystack) not set.

**Fix:** Add the optional credentials to `.env.production`:
```bash
HUBTEL_CLIENT_ID=your_id
HUBTEL_CLIENT_SECRET=your_secret
PAYSTACK_SECRET_KEY=sk_live_your_key
```

## Security Best Practices

1. ✅ **NEVER commit** `.env.production` or `.env.development` to git
2. ✅ **Use different keys** for production, development, and testing
3. ✅ **Rotate SECRET_KEY** if you suspect it was compromised
4. ✅ **Limit access** to production environment files (use `chmod 600`)
5. ✅ **Use secrets manager** in production (AWS Secrets Manager, Azure Key Vault, etc.)

## Emergency Secret Rotation

If you suspect your production SECRET_KEY was compromised:

1. Generate a new key immediately
2. Update `.env.production` with new key
3. Restart all services
4. **Important:** This will invalidate all existing sessions and JWT tokens
5. All users will need to log in again

## Checklist

- [ ] Generated new SECRET_KEY for production
- [ ] Updated `.env.production` file
- [ ] Verified all required environment variables are set
- [ ] Restarted pms-backend service
- [ ] Restarted celery-pms service
- [ ] Checked application logs (no errors)
- [ ] Tested login functionality
- [ ] Verified API endpoints respond correctly
- [ ] Updated development environment (.env.development)
- [ ] Notified team about SECRET_KEY requirement

## Additional Resources

- Django SECRET_KEY documentation: https://docs.djangoproject.com/en/5.2/ref/settings/#secret-key
- Django deployment checklist: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- Project README: `/home/teejay/Documents/Projects/YEA/PMS/pms-backend/README.md`

## Support

If you encounter issues during deployment:
1. Check application logs: `sudo journalctl -u pms-backend -n 100`
2. Verify environment file: `cat .env.production | grep SECRET_KEY`
3. Test Django check: `python manage.py check --deploy`
4. Contact DevOps team with error logs

---

**Last Updated:** January 10, 2026  
**Related Commits:** cf896a2 (secret removal), ffd6bab (RBAC system)
