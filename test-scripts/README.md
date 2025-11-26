# Test Scripts

This folder contains test scripts for verifying various components of the YEA Poultry Management System.

## Available Tests

### 1. Database Connection Test
**File:** `test_database.py`

Tests PostgreSQL database connection, PostGIS extension, and lists all tables.

```bash
python test-scripts/test_database.py
```

**What it tests:**
- Database connection
- PostgreSQL version
- PostGIS extension installation
- List of all tables
- User count

---

### 2. Email Configuration Test
**File:** `test_email.py`

Tests email sending via configured SMTP server (Gmail).

```bash
python test-scripts/test_email.py
```

**What it tests:**
- Email backend configuration
- SMTP connection
- Sending test emails
- Email timeout settings

**Configuration required:**
- `EMAIL_HOST_USER` in `.env.development`
- `EMAIL_HOST_PASSWORD` in `.env.development`
- For Gmail: Use App Password (not regular password)

---

### 3. SMS/OTP Test
**File:** `test_sms.py`

Tests SMS sending and OTP generation.

```bash
python test-scripts/test_sms.py
```

**What it tests:**
- SMS provider configuration
- OTP generation
- SMS sending (console/Hubtel/Twilio)

**Configuration required:**
- `SMS_PROVIDER` in `.env.development`
- `SMS_API_KEY` (for Hubtel/Twilio)
- `SMS_API_SECRET` (for Hubtel/Twilio)

---

### 4. Role Management System Test
**File:** `test_roles.py`

Tests the Rolify-equivalent role management system.

```bash
python test-scripts/test_roles.py
```

**What it tests:**
- Creating users
- Creating roles (system and resource-scoped)
- Creating permissions
- Assigning roles to users
- Checking role membership
- Checking permissions
- Role removal

**Features demonstrated:**
- `user.add_role('admin')`
- `user.has_role('admin')`
- `user.has_any_role('admin', 'moderator')`
- `user.has_all_roles('admin', 'moderator')`
- `user.has_permission('can_approve_farms')`
- `user.get_roles()`
- `user.get_permissions()`
- `user.remove_role('admin')`

---

## Prerequisites

All tests require:
1. Virtual environment activated
2. Django project properly configured
3. Database connection working
4. Environment variables set in `.env.development`

## Running Tests

### Individual Test
```bash
python test-scripts/test_<name>.py
```

### All Tests (in sequence)
```bash
python test-scripts/test_database.py && \
python test-scripts/test_email.py && \
python test-scripts/test_sms.py && \
python test-scripts/test_roles.py
```

## Troubleshooting

### Database Connection Fails
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify credentials in `.env.development`
- Ensure database exists: `psql -U teejay -l`

### Email Test Fails
- For Gmail: Enable 2FA and create App Password
- Check firewall allows port 587
- Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD

### SMS Test Always Uses Console
- Set `SMS_PROVIDER=hubtel` or `SMS_PROVIDER=twilio` in `.env.development`
- Provide API credentials for chosen provider

### Role Test Creates Duplicates
- Run cleanup at end of test (option 'y')
- Or manually delete: `python manage.py shell` and run cleanup commands

## Adding New Tests

1. Create new file: `test_<feature>.py`
2. Follow the template structure:
   ```python
   #!/usr/bin/env python
   import os, sys, django
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
   django.setup()
   
   def test_<feature>():
       # Your test code
       pass
   
   if __name__ == '__main__':
       test_<feature>()
   ```
3. Document it in this README
4. Make it executable: `chmod +x test-scripts/test_<feature>.py`

## Notes

- Tests are safe to run multiple times
- Most tests create temporary data (offer cleanup option)
- Tests output detailed information for debugging
- Use tests to verify configuration before deploying
