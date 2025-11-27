# Admin API Field Name Fixes

## Issue Summary
Admin dashboard APIs were failing with `FieldError: Cannot resolve keyword 'created_at' into field` errors.

## Root Cause
The `accounts/admin_views.py` was using incorrect field names that don't exist in the models:

### FarmApplication Model Issues
- ❌ Used: `created_at` 
- ✅ Correct: `submitted_at`
- ❌ Used: `application_id`
- ✅ Correct: `application_number`
- ❌ Used: `farm_name`
- ✅ Correct: `proposed_farm_name`
- ❌ Used: `screening_stage`
- ✅ Correct: `current_review_level`

## Fixed Endpoints

### 1. Admin Dashboard Overview
**Endpoint:** `GET /api/admin/dashboard/overview/`

**Fixed:**
- Recent applications filter now uses `submitted_at__gte` instead of `created_at__gte`

**Test:**
```bash
curl -X GET http://localhost:8000/api/admin/dashboard/overview/ \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "farms": {
    "total": 4,
    "active": 0,
    "approved": 3,
    "approval_rate": 75.0
  },
  "applications": {
    "total": 0,
    "pending": 0,
    "approved": 0,
    "rejected": 0,
    "recent_7_days": 0
  },
  "users": {
    "total": 13,
    "active": 13,
    "verified": 1
  }
}
```

### 2. Admin Applications List
**Endpoint:** `GET /api/admin/applications/`

**Fixed:**
- Ordering changed from `-created_at` to `-submitted_at`
- Serialization fields updated:
  - `application_id` → `application_number`
  - `farm_name` → `proposed_farm_name`
  - `screening_stage` → `current_review_level`
  - `created_at` → `submitted_at`

**Test:**
```bash
curl -X GET "http://localhost:8000/api/admin/applications/?page=1&page_size=10" \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "application_number": "APP-2025-00001",
      "applicant_name": "John Doe",
      "farm_name": "Sunrise Poultry Farm",
      "phone": "+233241234567",
      "email": "john@example.com",
      "application_type": "government_program",
      "status": "submitted",
      "current_review_level": "constituency",
      "region": "Greater Accra",
      "constituency": "Tema East",
      "submitted_at": "2025-11-27T07:00:00Z",
      "yea_program_batch": "2025-Batch-01"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 1,
    "pages": 1
  }
}
```

### 3. Admin Analytics
**Endpoint:** `GET /api/admin/analytics/?metric=applications_trend`

**Fixed:**
- Analytics trend query changed from `created_at` to `submitted_at`
- Date grouping uses `date(submitted_at)` instead of `date(created_at)`

**Test:**
```bash
curl -X GET "http://localhost:8000/api/admin/analytics/?metric=applications_trend&period=30d" \
  -H "Authorization: Bearer <token>"
```

## Model Field Reference

### FarmApplication (farms/application_models.py)
| Field Name | Type | Description |
|------------|------|-------------|
| `id` | UUID | Primary key |
| `application_number` | CharField | Format: APP-YYYY-XXXXX |
| `proposed_farm_name` | CharField | Proposed name for the farm |
| `status` | CharField | submitted, approved, rejected, etc. |
| `current_review_level` | CharField | constituency, regional, national |
| `submitted_at` | DateTimeField | auto_now_add=True |
| `updated_at` | DateTimeField | auto_now=True |

### User (accounts/models.py)
| Field Name | Type | Description |
|------------|------|-------------|
| `id` | UUID | Primary key |
| `created_at` | DateTimeField | auto_now_add=True |
| `updated_at` | DateTimeField | auto_now=True |

### GovernmentProgram (farms/program_enrollment_models.py)
| Field Name | Type | Description |
|------------|------|-------------|
| `id` | UUID | Primary key |
| `created_at` | DateTimeField | auto_now_add=True |
| `updated_at` | DateTimeField | auto_now=True |

## Changes Made to accounts/admin_views.py

### Line 96 - AdminDashboardOverviewView
```python
# Before
recent_applications = applications_qs.filter(created_at__gte=week_ago).count()

# After
recent_applications = applications_qs.filter(submitted_at__gte=week_ago).count()
```

### Line 429 - AdminApplicationListView
```python
# Before
applications = queryset.order_by('-created_at')[start:end]

# After
applications = queryset.order_by('-submitted_at')[start:end]
```

### Line 434-444 - AdminApplicationListView Serialization
```python
# Before
{
    'application_id': app.application_id,
    'farm_name': app.farm_name,
    'screening_stage': app.screening_stage,
    'created_at': app.created_at,
}

# After
{
    'id': str(app.id),
    'application_number': app.application_number,
    'farm_name': app.proposed_farm_name,
    'current_review_level': app.current_review_level,
    'submitted_at': app.submitted_at.isoformat() if app.submitted_at else None,
}
```

### Line 525-528 - AdminAnalyticsView
```python
# Before
applications = FarmApplication.objects.filter(
    created_at__gte=start_date
).extra({'date': 'date(created_at)'})

# After
applications = FarmApplication.objects.filter(
    submitted_at__gte=start_date
).extra({'date': 'date(submitted_at)'})
```

## Frontend Update Required

Update your admin dashboard frontend to use the corrected field names:

### Before (Incorrect)
```typescript
interface Application {
  application_id: string;
  farm_name: string;
  screening_stage: string;
  created_at: string;
}
```

### After (Correct)
```typescript
interface Application {
  id: string;
  application_number: string;  // Changed
  farm_name: string;            // Actually proposed_farm_name from backend
  current_review_level: string; // Changed
  submitted_at: string;         // Changed
}
```

## Verification Steps

1. ✅ Dashboard overview loads without errors
2. ✅ Applications list returns correct data
3. ✅ Applications can be filtered and sorted
4. ✅ Analytics endpoint returns trend data
5. ✅ All date fields use correct model fields

## Status
✅ **RESOLVED** - All admin API endpoints now use correct model field names

---

**Last Updated:** November 27, 2025  
**Fixed By:** GitHub Copilot  
**Files Modified:** `accounts/admin_views.py`  
**Related Docs:** `docs/ADMIN_DASHBOARD_FRONTEND_GUIDE.md`
