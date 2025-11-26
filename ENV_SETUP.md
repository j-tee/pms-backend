# Environment Variables Setup Guide

## Overview

All sensitive configuration data for the YEA Poultry Management System is stored in environment variables. This guide explains how to set up your environment files.

## Quick Start

1. **Copy the example file:**
   ```bash
   cp .env.example .env.development
   ```

2. **Edit `.env.development` with your actual values:**
   - Update database credentials
   - Add API keys for services you're using
   - Configure email/SMS settings

3. **NEVER commit `.env*` files to version control!**
   - These files are already in `.gitignore`
   - Only commit `.env.example` with placeholder values

## Environment Files

- **`.env.example`** - Template with all available variables (COMMIT THIS)
- **`.env.development`** - Local development settings (DO NOT COMMIT)
- **`.env.production`** - Production settings (DO NOT COMMIT)
- **`.env.local`** - Personal overrides (DO NOT COMMIT)

## Required Variables (Minimum Setup)

```bash
# Django
SECRET_KEY=generate-a-secure-random-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=poultry_db
DB_USER=your_username
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

## Generating Secure Values

### Secret Key
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Database Password
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Service-Specific Setup

### Email (Gmail Example)
```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
```

**Gmail Setup:**
1. Enable 2-Factor Authentication
2. Generate App-Specific Password: https://myaccount.google.com/apppasswords
3. Use the generated password in `EMAIL_HOST_PASSWORD`

### SMS (Hubtel - Ghana)
```bash
SMS_ENABLED=True
HUBTEL_CLIENT_ID=your-client-id
HUBTEL_CLIENT_SECRET=your-client-secret
HUBTEL_SENDER_ID=YEA-PMS
```

**Hubtel Setup:**
1. Register at https://developers.hubtel.com/
2. Create an application
3. Copy Client ID and Client Secret

### Paystack (Payment Gateway)
```bash
PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxx
PAYSTACK_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx
PAYSTACK_WEBHOOK_SECRET=your_webhook_secret
```

**Paystack Setup:**
1. Register at https://dashboard.paystack.com/
2. Go to Settings → Developers
3. Copy Test/Live keys based on environment
4. Configure webhook URL and copy secret

### Social Authentication

**Google OAuth:**
```bash
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
```

Setup: https://console.cloud.google.com/apis/credentials

**Facebook OAuth:**
```bash
FACEBOOK_CLIENT_ID=your-app-id
FACEBOOK_CLIENT_SECRET=your-secret
```

Setup: https://developers.facebook.com/apps/

**GitHub OAuth:**
```bash
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-secret
```

Setup: https://github.com/settings/developers

## Security Best Practices

### DO:
✅ Use strong, unique passwords for each environment
✅ Use different API keys for development and production
✅ Rotate secrets regularly
✅ Use test/sandbox keys for development
✅ Store production secrets in secure vault (AWS Secrets Manager, Azure Key Vault, etc.)
✅ Use environment-specific `.env` files
✅ Review `.gitignore` to ensure `.env*` files are excluded

### DON'T:
❌ Commit `.env` files to version control
❌ Share credentials via email or chat
❌ Use production keys in development
❌ Use weak or default passwords
❌ Hardcode secrets in source code
❌ Expose `.env` files via web server

## Environment-Specific Settings

### Development (`.env.development`)
```bash
DEBUG=True
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
SMS_ENABLED=False
PAYSTACK_SECRET_KEY=sk_test_xxxxx  # Use test keys
LOG_LEVEL=DEBUG
```

### Production (`.env.production`)
```bash
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
SMS_ENABLED=True
PAYSTACK_SECRET_KEY=sk_live_xxxxx  # Use live keys
LOG_LEVEL=WARNING
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Verifying Setup

Test that environment variables are loaded correctly:

```bash
python manage.py shell
```

```python
from django.conf import settings
print(f"DEBUG: {settings.DEBUG}")
print(f"DATABASE: {settings.DATABASES['default']['NAME']}")
print(f"SECRET_KEY: {'SET' if settings.SECRET_KEY else 'NOT SET'}")
```

## Troubleshooting

### Variables Not Loading
- Check file name is exactly `.env.development` or `.env`
- Ensure file is in project root (same directory as `manage.py`)
- Verify `python-dotenv` is installed: `pip list | grep dotenv`
- Check for syntax errors (no spaces around `=`)

### Database Connection Failed
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Test connection: `psql -U username -d database_name -h localhost`
- Check credentials in `.env.development`
- Ensure database exists: `createdb poultry_db`

### ImportError for python-dotenv
```bash
pip install python-dotenv
```

## Production Deployment

For production, use environment variables from your hosting platform:

**Heroku:**
```bash
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DB_PASSWORD="your-db-password"
```

**AWS Elastic Beanstalk:**
- Use AWS Systems Manager Parameter Store or Secrets Manager
- Configure in `.ebextensions` or environment properties

**Docker:**
```bash
docker run -e SECRET_KEY="your-key" -e DB_PASSWORD="your-pass" ...
```

Or use docker-compose with `env_file`:
```yaml
services:
  web:
    env_file:
      - .env.production
```

## Support

If you have questions about environment configuration:
1. Check this README
2. Review `.env.example` for all available variables
3. Consult service-specific documentation (links provided above)
4. Contact DevOps team for production secrets

## Security Incident Response

If credentials are accidentally committed:
1. **IMMEDIATELY** rotate all exposed secrets
2. Revoke API keys from service providers
3. Change database passwords
4. Generate new Django SECRET_KEY
5. Update all environments with new credentials
6. Use `git filter-branch` or BFG Repo-Cleaner to remove from history

**Prevention:**
```bash
# Add pre-commit hook to prevent commits with secrets
pip install detect-secrets
detect-secrets scan --baseline .secrets.baseline
```
