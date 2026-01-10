# YEA Poultry Management System - AI Coding Instructions

## Project Overview
Django 5.2 REST API for Ghana's Youth Employment Agency (YEA) Poultry Development Program. Uses PostgreSQL with PostGIS for geospatial data, JWT authentication via SimpleJWT, and a hierarchical role-based access system.

## Architecture

### App Structure
- **accounts/**: User auth, roles, MFA, staff invitations, policies (CanCanCan-style authorization)
- **farms/**: Farm registration, applications, batch enrollment, invitation system
- **flock_management/**: Bird batches, daily production, mortality tracking
- **feed_inventory/**: Feed purchases and stock management
- **sales_revenue/**: Marketplace, orders, inventory, processing (birds → products)
- **dashboards/**: Role-based dashboards with service layer pattern
- **procurement/**: Government orders and assignments

### Key Patterns

**Authorization Policy Pattern** (`accounts/policies/`):
```python
# Every model has a corresponding policy class
from accounts.policies import get_policy_for_resource, authorize
authorize(user, 'edit', farm_instance)  # Returns bool
```

**Farm-Scoped Data Access** (`FarmScopedMixin` in views):
```python
class MyView(FarmScopedMixin, generics.ListAPIView):
    # Automatically filters queryset to request.user.farm
    # Use this for ALL farmer-facing views to prevent cross-farm data access
```

**Service Layer** (e.g., `dashboards/services/`):
- Views delegate business logic to service classes
- Services aggregate data from multiple models

**Role Hierarchy** (defined in `accounts/models.py`):
```
SUPER_ADMIN (Platform Owner - Alphalogique)
    ↓
NATIONAL_ADMIN / NATIONAL_STAFF (National Level)
  - NATIONAL_ADMIN: Full national access, manages NATIONAL_STAFF permissions
  - NATIONAL_STAFF: Limited national access, permissions controlled by admin
    ↓
REGIONAL_ADMIN / REGIONAL_STAFF (Regional Level)
  - REGIONAL_ADMIN: Full regional access, manages REGIONAL_STAFF permissions
  - REGIONAL_STAFF: Limited regional access, permissions controlled by admin
  - [REGIONAL_COORDINATOR: Legacy alias for REGIONAL_ADMIN]
    ↓
CONSTITUENCY_ADMIN / CONSTITUENCY_STAFF (Constituency Level)
  - CONSTITUENCY_ADMIN: Full constituency access, manages CONSTITUENCY_STAFF permissions
  - CONSTITUENCY_STAFF: Limited constituency access, permissions controlled by admin
  - [CONSTITUENCY_OFFICIAL: Legacy alias for CONSTITUENCY_ADMIN]
    ↓
Field Officers (all at same level, geographically scoped):
├── EXTENSION_OFFICER
├── VETERINARY_OFFICER
└── YEA_OFFICIAL (general YEA field support staff)
    ↓
FARMER (End User)
```

**IMPORTANT - Platform vs Client Separation**:
- **SUPER_ADMIN**: Platform staff (Alphalogique) - has access to ALL data including institutional subscriptions
- **NATIONAL_ADMIN and below**: YEA government officials - are CLIENTS, should NOT see institutional subscription data
- **INSTITUTIONAL_SUBSCRIBER**: B2B clients (universities, research institutions) - separate data access tier

**Institutional Data Access** (CRITICAL SECURITY RULE):
```python
# ❌ WRONG - YEA government should NOT see institutional data
if user.role in ['SUPER_ADMIN', 'NATIONAL_ADMIN']:
    # Access institutional subscriptions

# ✅ CORRECT - Only platform staff
if UserPolicy.is_platform_staff(user):  # Only SUPER_ADMIN
    # Access institutional subscriptions
```

**Permission System** (`accounts/permissions_config.py`, `accounts/roles.py`):
```python
# Admins have implicit permissions for their level
# Staff have configurable permissions managed by their admin
# Use has_permission() for fine-grained access control

from accounts.policies import UserPolicy

# Check if user has specific permission
if user.has_permission('view_all_farms'):
    ...

# Or via policy
if UserPolicy.has_permission(user, 'create_batch'):
    ...

# Permission management (admin only)
from accounts.services.permission_management_service import PermissionManagementService
service = PermissionManagementService(admin_user)
service.grant_permission(staff_user, 'view_regional_analytics')
service.revoke_permission(staff_user, 'edit_farm')
```

**Permission Categories** (see `permissions_config.py` for full list):
- `user_management`: view_all_users, create_staff, edit_user, suspend_user
- `farm_management`: view_all_farms, edit_farm, assign_extension_officer
- `batch_management`: view_batches, create_batch, publish_batch
- `analytics`: view_national_analytics, view_regional_analytics
- `financial`: view_revenue, process_payments
- `system`: manage_permissions, system_config

Check roles via `UserPolicy.is_*()` methods or `user.role` directly.

**Field Officers** (synonymous terms - all access `/api/extension/` endpoints):
- **Extension Officer** = Field Officer (primary term, used interchangeably)
- **Veterinary Officer** = Field Officer with animal health focus
- **YEA Official** = General YEA field staff (data collection, farmer support)
- **Constituency Official** = Senior field officer with officer assignment privileges

**Field Officer Capabilities:**
- Register farmers on behalf via `/api/extension/register-farmer/`
- Update farm information in their jurisdiction
- View assigned farms and farmer data
- Conduct extension duties and record visits
- Help farmers learn to use the platform
- Collect field data on behalf of farmers
- Constituency Officials can also assign Extension Officers to farms

### Batch/Program Enrollment System

**Terminology** (used interchangeably, "batch" is canonical):
- **Batch** = Recruitment cycle (e.g., "2025 Q1 Batch - Greater Accra")
- **Cohort** = Same as batch
- **Program** = Legacy term (deprecated in URLs, use `/batches/` not `/programs/`)
- **Intake** = Application period for a batch


**Two-Flag Visibility Pattern** (CRITICAL):
```python
# Both flags must be True for public visibility
is_active=True   # Operationally active (accepting applications)
is_published=True  # Visible to farmers/public

# Common mistake: is_active=True but is_published=False → invisible to public!
```

| `is_active` | `is_published` | Result |
|-------------|----------------|--------|
| `false` | `false` | Draft (admin only) |
| `true` | `true` | **Live** - accepting applications |
| `false` | `true` | Visible but paused |

**Two Application Types** (don't confuse):
- `FarmApplication` (`farms/application_models.py`) → **New farmers** registering on platform
- `BatchEnrollmentApplication` (`farms/batch_enrollment_models.py`) → **Existing farmers** joining a batch

## API Structure

| Prefix | Purpose |
|--------|---------|
| `/api/auth/` | Authentication, MFA, profile |
| `/api/admin/` | Staff management, batches, analytics |
| `/api/admin/batches/` | Batch CRUD (NOT `/programs/`) |
| `/api/admin/permissions/` | Permission management (list all, manageable users) |
| `/api/admin/users/{id}/permissions/` | User permission CRUD (view, grant, revoke) |
| `/api/admin/platform-settings/` | Platform monetization settings (Super Admin) |
| `/api/admin/advertising/` | Advertising partner/offer management |
| `/api/extension/` | Field officer endpoints (register farmers, update farms) |
| `/api/public/batches/` | Public batch discovery (no auth) |
| `/api/public/platform-settings/` | Public platform settings (pricing info) |
| `/api/public/advertise/` | Advertiser lead capture |
| `/api/farms/` | Farm management (authenticated) |
| `/api/flocks/` | Flock/production tracking |
| `/api/marketplace/` | Farmer marketplace (farm-scoped) |
| `/api/public/marketplace/` | Public marketplace (no auth) |
| `/api/advertising/` | Partner offers for farmers |

## Development Commands

```bash
# Environment setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.development  # Configure DB, secrets

# Database (requires PostgreSQL with PostGIS)
python manage.py migrate
python manage.py createsuperuser  # Or use create_admin.py

# Run tests
pytest                           # All tests
pytest accounts/                 # Single app
pytest -k "test_staff"           # By name pattern
pytest --tb=short -v             # Verbose with short traceback

# Server
python manage.py runserver
```

## Conventions

**Models**: UUID primary keys, `created_at`/`updated_at` timestamps, extensive `help_text`

**Serializers**: Separate `*ListSerializer` and `*DetailSerializer` for list vs detail views

**Permissions**: Custom classes in `*/permissions.py` (e.g., `IsExecutive`, `IsFarmer`)

**Geographic Scoping**: Regional coordinators and constituency officials see only their jurisdiction via `UserPolicy` checks

**Phone Numbers**: Use `phonenumber_field` with Ghana format (`+233XXXXXXXXX`)

**Error Response Format** (consistent across API):
```python
# Standard error structure
{'error': 'Human-readable message', 'code': 'ERROR_CODE'}
# With details
{'error': 'Authorization check failed', 'code': 'AUTH_CHECK_ERROR', 'detail': '...'}
```

**Pagination**: Default 20 items per page via `PageNumberPagination`

## External Integrations

**SMS (Hubtel)** - Ghana SMS gateway:
```bash
# .env settings
SMS_ENABLED=True
HUBTEL_CLIENT_ID=your_client_id
HUBTEL_CLIENT_SECRET=your_secret
HUBTEL_SENDER_ID=YEA-PMS
```
Service: `core/sms_service.py` - Falls back to console logging if disabled

**Social Auth** (Google, Facebook, GitHub):
- Configured via `django-allauth` in `core/settings.py`
- Set provider keys in `.env`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, etc.

**PostGIS** - Required for geospatial features:
- Database engine: `django.contrib.gis.db.backends.postgis`
- Install: `sudo apt install postgis postgresql-*-postgis-*`

## Deployment

**Stack**: Gunicorn → Nginx (reverse proxy) → systemd services → Redis (cache/broker) → Celery (background tasks)

**Config files** in `deployment/`:
- `nginx/pms-backend.conf` - Nginx site config
- `systemd/pms-backend.service` - Django/Gunicorn service
- `systemd/celery-pms.service` - Celery worker service
- `gunicorn/gunicorn_config.py` - Gunicorn settings

**Quick deploy**:
```bash
sudo cp deployment/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pms-backend celery-pms redis
sudo systemctl start redis pms-backend celery-pms
```

## Scaling & Background Tasks

**Celery Configuration** (`core/celery.py`):
- Background task processing for SMS, email, reports
- Periodic tasks via Celery Beat (scheduled in `core/celery.py`)
- Broker: Redis at `CELERY_BROKER_URL`

**When to use Celery tasks**:
```python
# ❌ WRONG - blocks API response
from core.sms_service import SMSService
SMSService.send_sms(phone, message)  # Waits for HTTP call to Hubtel

# ✅ CORRECT - returns immediately
from core.tasks import send_sms_async
send_sms_async.delay(phone, message)  # Queued for background processing
```

**Redis Cache** (enabled via `REDIS_ENABLED=True`):
- Cross-worker caching (required for multiple Gunicorn workers)
- Session storage for faster auth
- Cache expensive dashboard queries

**Production .env for scaling**:
```bash
REDIS_ENABLED=True
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

**High-Traffic Recommendations** (5M+ users/day):
1. Multiple Gunicorn workers: `workers = (2 * CPU cores) + 1`
2. Database read replicas with `DATABASE_REPLICA_URL`
3. Connection pooling via PgBouncer
4. CDN for static/media files
5. Consider async views for I/O-bound endpoints

## Testing
- pytest-django configured in `pytest.ini`
- Test files: `test_*.py` in root or app `tests.py`
- Integration tests use real API calls (see `test_staff_invitation.py` pattern)

## Marketplace Monetization

**Terminology Clarification**:
- "Marketplace Activation Fee" = "Marketplace Subscription Fee" (same thing)
- The activation fee is a **recurring monthly payment** for continued marketplace access
- Farmers pay the same amount every month they wish to continue selling on the platform
- ✅ Use: "Marketplace Activation Fee", "Monthly Marketplace Fee", "Seller Access Fee"

**IMPORTANT - Only ONE Fee for Farmers**:
- **GHS 50/month Marketplace Activation Fee** is the ONLY fee
- Transaction commissions are **NOT applied** (farmers keep 100% of sales)
- Payments happen **OFF-PLATFORM** (cash, MoMo, bank transfer direct to farmer)
- Farmers only use the platform to **record sales** for tracking
- This is intentional - Ghanaian farmers are VERY sensitive to platform fees
- NO additional tiers or premium features that cost extra money

**Current Fee Structure**:
| Fee Type | Amount | Status |
|----------|--------|--------|
| Marketplace Activation Fee | GHS 50/month | ✅ ACTIVE |
| Transaction Commission | 2-5% | ❌ REMOVED |

**Access Tiers** (`farms.Farm.subscription_type`):
| Value | Description |
|-------|-------------|
| `none` | No marketplace access |
| `government_subsidized` | Government-funded access (program beneficiaries) |
| `standard` | Self-funded marketplace access (GHS 50/month) |

**Platform Settings** (`sales_revenue.PlatformSettings` singleton):
- All monetization values are admin-configurable via `/api/admin/platform-settings/`
- Access via `PlatformSettings.get_settings()` - never hardcode fees
- Key fields: `marketplace_activation_fee`, `marketplace_trial_days`, `enable_government_subsidy`
- `enable_transaction_commission`: **False** (suspended, farmers keep 100%)

**Decorators** (`accounts/decorators.py`):
```python
from accounts.decorators import require_marketplace_activation

@require_marketplace_activation  # Checks farm has active marketplace access
def create_listing(request):
    ...
```

## Documentation Policy

**IMPORTANT**: Only `README.md` should be committed to the repository.
- ❌ Do NOT commit any other markdown documentation files to git
- ❌ Do NOT force-add ignored documentation files
- ✅ All other documentation is gitignored and should remain local only
- ✅ Use README.md for essential project information that must be in the repo

## Key Files
- [core/settings.py](core/settings.py) - All Django/DRF/JWT config
- [accounts/roles.py](accounts/roles.py) - Rolify-style dynamic role system
- [accounts/policies/](accounts/policies/) - CanCanCan-style authorization
- [farms/models.py](farms/models.py) - Core farm registration model (~2000 lines)
- [docs/](docs/) - API documentation, guides (gitignored)
