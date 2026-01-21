# YEA Poultry Management System - AI Coding Instructions

Django 5.2 REST API for Ghana's YEA Poultry Development Program. PostgreSQL with PostGIS, JWT auth (SimpleJWT), hierarchical role-based access.

## Critical Security Patterns

**Farm-Scoped Data Access** - ALL farmer-facing views MUST use `FarmScopedMixin` ([sales_revenue/marketplace_views.py](../sales_revenue/marketplace_views.py#L62)):
```python
class MyView(FarmScopedMixin, generics.ListAPIView):
    # Automatically filters queryset to request.user.farm - prevents cross-farm data leaks
```

**Platform vs Client Separation** - SUPER_ADMIN (Alphalogique) ≠ NATIONAL_ADMIN (YEA government):
```python
# ❌ WRONG - YEA officials should NOT see institutional/platform data
if user.role in ['SUPER_ADMIN', 'NATIONAL_ADMIN']: ...
# ✅ CORRECT - Platform staff only
if UserPolicy.is_platform_staff(user): ...  # Only SUPER_ADMIN
```

**Authorization Policies** ([accounts/policies/](../accounts/policies/__init__.py)) - CanCanCan-style:
```python
from accounts.policies import authorize
authorize(user, 'edit', farm_instance)  # Returns bool
```

## Role Hierarchy

`SUPER_ADMIN` → `NATIONAL_ADMIN/STAFF` → `REGIONAL_ADMIN/STAFF` → `CONSTITUENCY_ADMIN/STAFF` → `EXTENSION_OFFICER/VETERINARY_OFFICER/YEA_OFFICIAL` → `FARMER`

- Admins have implicit permissions; Staff have configurable permissions via `user.has_permission('codename')`
- Geographic scoping: officials only see data in their jurisdiction via `UserPolicy` checks
- **Legacy aliases** (still supported): `REGIONAL_COORDINATOR` → `REGIONAL_ADMIN`, `CONSTITUENCY_OFFICIAL` → `CONSTITUENCY_ADMIN`

## Field Officers (`/api/extension/`)

Three roles with field officer access ([farms/extension_views.py](../farms/extension_views.py)):
- `EXTENSION_OFFICER` - Agricultural technical support
- `VETERINARY_OFFICER` - Animal health focus  
- `YEA_OFFICIAL` - Data collection, farmer onboarding

**Use the constants** defined in `extension_views.py`:
```python
FIELD_OFFICER_ROLES = ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL']
EXTENSION_ACCESS_ROLES = FIELD_OFFICER_ROLES + ['CONSTITUENCY_ADMIN', 'CONSTITUENCY_OFFICIAL']
```

Only `EXTENSION_OFFICER` and `VETERINARY_OFFICER` can be assigned to farms (not YEA_OFFICIAL).

## Key Patterns

**Service Layer** - Views delegate to services in `dashboards/services/`, `accounts/services/`

**Two-Flag Visibility** - Batches need BOTH flags for public visibility:
```python
is_active=True   # Operationally active
is_published=True  # Visible to public (BOTH required for farmers to see!)
```

**Serializer Naming** - Use `*ListSerializer` and `*DetailSerializer` for list vs detail views

**Error Format**: `{'error': 'Message', 'code': 'ERROR_CODE'}`

## API Routing ([core/urls.py](../core/urls.py))

| Prefix | Purpose |
|--------|---------|
| `/api/auth/` | Authentication, MFA, profile |
| `/api/admin/` | Staff management, batches, analytics |
| `/api/extension/` | Field officer endpoints (register farmers) |
| `/api/farms/` | Farm management (authenticated) |
| `/api/marketplace/` | Farmer marketplace (farm-scoped) |
| `/api/public/marketplace/` | Public marketplace (no auth) |

## Development

```bash
# Setup (requires PostgreSQL with PostGIS)
cp .env.example .env.development && pip install -r requirements.txt
python manage.py migrate && python manage.py runserver

# Tests
pytest                    # All tests
pytest tests/integration/ # API integration tests
pytest -k "marketplace"   # By pattern
```

## Background Tasks

Use Celery for I/O (SMS, email, reports) - never block API responses:
```python
# ❌ WRONG: send_sms(phone, msg)  # Blocks
# ✅ CORRECT: send_sms_async.delay(phone, msg)  # Queued
```

## Marketplace Rules

**Access vs Visibility Separation** (Jan 2026):
- **ALL farmers** can use marketplace features (list products, track sales, analytics)
- **ONLY subscribed farmers** appear in public marketplace searches
- This ensures accurate industry statistics while incentivizing subscriptions

**Subscription Requirements**:
- **Only ONE fee**: GHS 50/month Marketplace Activation Fee (no transaction commissions)
- Payments happen OFF-PLATFORM (cash, MoMo to farmer) - platform only tracks sales
- Use `PlatformSettings.get_settings()` - never hardcode fees

**Public Search Visibility** (in `public_marketplace_views.py`):
```python
# Public views filter by subscription status:
queryset = Product.objects.filter(
    status='active',
    farm__farm_status='Active',
    farm__marketplace_enabled=True,
    farm__subscription__status__in=['trial', 'active']  # VISIBILITY FILTER
)
```

**Farmer Dashboard** shows visibility status in `MarketplaceDashboardView.visibility` field.

## Key Files

- [accounts/policies/](../accounts/policies/) - Authorization policies
- [accounts/permissions_config.py](../accounts/permissions_config.py) - All permission codenames
- [sales_revenue/marketplace_views.py](../sales_revenue/marketplace_views.py) - FarmScopedMixin example
- [dashboards/services/](../dashboards/services/) - Service layer pattern

## Documentation Policy

Only `README.md` should be committed. Other docs are gitignored and local-only.
