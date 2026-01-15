# Test Suite for YEA Poultry Management System

This directory contains the centralized test suite for the PMS backend application.

## Directory Structure

```
tests/
├── __init__.py
├── integration/          # API integration tests (5 pytest test files)
│   ├── __init__.py
│   ├── test_adsense_integration.py
│   ├── test_institutional_access.py
│   ├── test_marketplace_monetization.py
│   ├── test_returns_refunds.py
│   └── test_returns_refunds_simple.py
└── scripts/             # Utility test scripts for development (31 files)
    ├── __init__.py
    ├── test_auth.py
    ├── test_database.py
    ├── test_email.py
    ├── test_sms.py
    ├── test_staff_invitation.py (standalone script)
    ├── test_permission_system.py (standalone script)
    └── ... (and 24 more utility scripts)
```

## Test Organization

### Integration Tests (`tests/integration/`)
Full API integration tests that test endpoints, permissions, and cross-app functionality. These are the main test suite run in CI/CD.

**Current test files (5):**
- `test_adsense_integration.py` - AdSense integration and monetization
- `test_institutional_access.py` - Institutional subscriber access control
- `test_marketplace_monetization.py` - Platform settings and marketplace fees
- `test_returns_refunds.py` - Returns and refunds workflow
- `test_returns_refunds_simple.py` - Simplified returns tests

**Run integration tests:**
```bash
pytest tests/integration/
```

**Run specific integration test:**

**These scripts should be run manually:**
- `test_staff_invitation.py` - Standalone staff invitation flow test
- `test_permission_system.py` - Permission system verification
- `test_email.py` - Email delivery testing
- `test_sms.py` - SMS integration testing
- `test_database.py` - Database connection testing
- `test_auth.py` - Authentication flow testing
- And 25+ more utility scripts...
```bash
pytest tests/integration/test_staff_invitation.py
pytest tests/integration/test_returns_refunds.py -v
```

### Utility Scripts (`tests/scripts/`)
Development and debugging scripts for testing specific components like email, SMS, database connections, etc. These are NOT run in CI/CD.

**Run utility scripts individually:**
```bash
python tests/scripts/test_email.py
python tests/scripts/test_sms.py
bash tests/scripts/test_celery.sh
```

### App-Specific Tests
Each Django app may contain its own `tests.py` or `test_*.py` files:
- `accounts/tests.py`
- `accounts/test_permission_system.py`
- `farms/tests.py`
- `subscriptions/test_institutional_comprehensive.py`
- etc.

**Run all app tests:**
```bash
pytest accounts/
pytest farms/
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run by Category
```bash
# All integration tests
pytest tests/integration/

# All accounts tests (app + integration)
pytest accounts/ tests/integration/test_staff_invitation.py tests/integration/test_permission_system.py

# All sales/revenue tests
pytest sales_revenue/ tests/integration/test_marketplace_monetization.py tests/integration/test_returns_refunds.py
```

### Run by Pattern
```bash
# All tests with "marketplace" in the name
pytest -k "marketplace"

# All tests with "permission" or "access" in the name
pytest -k "permission or access"

# Exclude slow tests
pytest -m "not slow"
```

### Verbose Output
```bash
pytest -v                    # Verbose test names
pytest --tb=short           # Short traceback
pytest --tb=line            # One-line traceback
pytest -vv --tb=short       # Very verbose with short traceback
```

### Run Specific Test
```bash
# By file
pytest tests/integration/test_staff_invitation.py

# By class
pytest tests/integration/test_staff_invitation.py::TestStaffInvitationFlow

# By method
pytest tests/integration/test_staff_invitation.py::TestStaffInvitationFlow::test_complete_invitation_workflow
```

## Pytest Configuration

Configuration is in [`pytest.ini`](../pytest.ini):

```ini
[pytest]
DJANGO_SETTINGS_MODULE = core.settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
addopts = --tb=short --strict-markers --no-cov-on-fail
testpaths = tests accounts dashboards farms feed_inventory flock_management medication_management procurement sales_revenue subscriptions
norecursedirs = tests/scripts media staticfiles __pycache__ .git venv
```

**Key Points:**
- Tests use Django settings from `core.settings`
- Test files must match: `tests.py`, `test_*.py`, or `*_tests.py`
- Test classes must start with `Test`
- Test functions must start with `test_`
- Utility scripts in `tests/scripts/` are excluded from test discovery

## Writing Tests

### Integration Test Template
```python
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from farms.models import Farm

class TestMyFeature(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='FARMER'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_my_endpoint(self):
        """Test description"""
        response = self.client.get('/api/my-endpoint/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('expected_field', response.data)
```

### Key Testing Utilities
- `APIClient()` - Django REST framework test client
- `force_authenticate(user=...)` - Skip JWT authentication
- `assertEqual()`, `assertTrue()`, `assertIn()` - Standard assertions
- `@pytest.mark.django_db` - Allow database access (pytest)
- `TestCase` - Django test case with database transaction support

## Best Practices

1. **Test Naming**: Use descriptive names that explain what's being tested
   - ✅ `test_farmer_cannot_access_admin_dashboard`
   - ❌ `test_dashboard`

2. **Test Isolation**: Each test should be independent
   - Use `setUp()` to create fresh test data
   - Don't rely on test execution order
   - Clean up after yourself (or use transactions)

3. **Use Fixtures**: Create reusable test data
   ```python
   @pytest.fixture
   def farmer_user():
       return User.objects.create_user(email='farmer@test.com', role='FARMER')
   ```

4. **Test One Thing**: Each test should verify one specific behavior
   - ✅ Multiple assertions about the same response
   - ❌ Testing multiple API endpoints in one test

5. **Clear Assertions**: Use specific assertions with clear messages
   ```python
   self.assertEqual(response.status_code, 403, "Farmer should not access admin endpoint")
   ```

## Coverage

Run tests with coverage report:
```bash
# Generate coverage report
pytest --cov=. --cov-report=html

# View report
open htmlcov/index.html
```

## Continuous Integration

Tests run automatically on:
- Pull requests to `main` or `development` branches
- Commits to `main` or `development` branches
- Manual workflow dispatch

**CI Command:**
```bash
pytest tests/integration/ accounts/ farms/ sales_revenue/ --tb=short -v
```

## Troubleshooting

### Import Errors
If you see import errors after moving tests, ensure:
1. You're in the project root directory
2. Django settings module is configured: `export DJANGO_SETTINGS_MODULE=core.settings`
3. Virtual environment is activated: `source venv/bin/activate`

### Database Errors
If tests fail with database errors:
```bash
# Run migrations
python manage.py migrate

# Reset test database
python manage.py migrate --run-syncdb
```

### Path Issues
All imports should use absolute imports from the project root:
```python
# ✅ Correct
from accounts.models import User
from sales_revenue.marketplace_models import Product

# ❌ Incorrect
from ..accounts.models import User
from .models import Product
```

## Adding New Tests

1. **Integration tests** → Add to `tests/integration/`
2. **App-specific tests** → Add to the app's directory (e.g., `accounts/tests.py`)
3. **Utility scripts** → Add to `tests/scripts/` (excluded from pytest)

Example:
```bash
# Create new integration test
touch tests/integration/test_my_new_feature.py

# Run it
pytest tests/integration/test_my_new_feature.py -v
```

## Resources

- [Django Testing Documentation](https://docs.djangoproject.com/en/5.2/topics/testing/)
- [Django REST Framework Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Project README](../README.md)
