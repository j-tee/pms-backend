# Complete Program → Batch Refactoring Summary

**Date:** November 27, 2025  
**Type:** **BREAKING CHANGE** - No Backward Compatibility  

---

## Overview

Complete, comprehensive refactoring from "program" terminology to "batch" terminology throughout the entire codebase. This was a clean break with NO backward compatibility maintained.

---

## Changes Made

### 1. Model Changes

#### Files Renamed:
- `farms/program_enrollment_models.py` → `farms/batch_enrollment_models.py`

#### Classes Renamed:
- `ProgramBatch` → `Batch`
- `ProgramEnrollmentApplication` → `BatchEnrollmentApplication`
- `ProgramEnrollmentReview` → `BatchEnrollmentReview`
- `ProgramEnrollmentQueue` → `BatchEnrollmentQueue`

#### Field Renam:
- `program_batch` → `batch` (ForeignKey in BatchEnrollmentApplication)
- `program_applications` → `batch_applications` (related_name on Farm model)

#### Database Table:
- Changed from `farms_governmentprogram` to `farms_batch`
- **Note:** Database was completely dropped and recreated

#### Removed:
- ❌ `GovernmentProgram` model alias (no backward compatibility)
- ❌ `program_type` field (always poultry)

---

### 2. View Files

#### Files Renamed:
- `accounts/program_admin_views.py` → `accounts/batch_admin_views.py`
- `accounts/program_action_views.py` → `accounts/batch_action_views.py`

#### Classes Renamed:
- `AdminProgramListView` → `AdminBatchListView`
- `AdminProgramDetailView` → `AdminBatchDetailView`
- `AdminProgramCreateView` → `AdminBatchCreateView`
- `AdminProgramUpdateView` → `AdminBatchUpdateView`
- `AdminProgramDeleteView` → `AdminBatchDeleteView`
- `AdminProgramToggleActiveView` → `AdminBatchToggleActiveView`
- `AdminProgramCloseApplicationsView` → `AdminBatchCloseApplicationsView`
- `AdminProgramExtendDeadlineView` → `AdminBatchExtendDeadlineView`
- `AdminProgramParticipantsView` → `AdminBatchParticipantsView`
- `AdminProgramStatisticsView` → `AdminBatchStatisticsView`
- `AdminProgramDuplicateView` → `AdminBatchDuplicateView`

#### Parameters Updated:
- All view methods: `program_id` → `batch_id`

#### Code Updates:
- 196 replacements made across 4 key files
- All query filters updated (batch_name, batch_code)
- All response fields updated
- All variable names updated

---

### 3. Policy Files

#### Files Renamed:
- `accounts/policies/program_policy.py` → `accounts/policies/batch_policy.py`

#### Classes Updated:
- `ProgramPolicy` → `BatchPolicy`
- Updated all docstrings and comments to reference "batches"

#### Policy Registry Updated:
```python
# OLD
'GovernmentProgram': ProgramPolicy,
'ProgramEnrollmentApplication': ProgramPolicy,

# NEW
'Batch': BatchPolicy,
'BatchEnrollmentApplication': BatchPolicy,
```

---

### 4. URL Configuration

#### Removed:
- ❌ All `/api/admin/programs/` URLs
- ❌ All backward compatibility aliases

#### New URLs:
```
GET  /api/admin/batches/
POST /api/admin/batches/
GET  /api/admin/batches/{batch_id}/
PUT  /api/admin/batches/{batch_id}/
DELETE /api/admin/batches/{batch_id}/
POST /api/admin/batches/{batch_id}/toggle-active/
POST /api/admin/batches/{batch_id}/close-applications/
POST /api/admin/batches/{batch_id}/extend-deadline/
POST /api/admin/batches/{batch_id}/duplicate/
GET  /api/admin/batches/{batch_id}/participants/
GET  /api/admin/batches/{batch_id}/statistics/
```

---

### 5. Database Changes

#### Actions Taken:
1. ✅ Deleted SQLite database (`db.sqlite3`)
2. ✅ Dropped PostgreSQL database (`poultry_db`)
3. ✅ Deleted ALL migration files (kept only `__init__.py`)
4. ✅ Created fresh migrations with new schema
5. ✅ Applied migrations successfully

#### New Table:
- `farms_batch` (was `farms_governmentprogram`)

#### Constraints Updated:
- `unique_together = [['farm', 'batch']]` (was `[['farm', 'program']]`)

---

### 6. Import Updates

#### All Updated Imports:
```python
# In farms/models.py
from .batch_enrollment_models import (
    Batch,
    BatchEnrollmentApplication,
    BatchEnrollmentReview,
    BatchEnrollmentQueue
)

# In view files
from farms.batch_enrollment_models import Batch, BatchEnrollmentApplication
from accounts.policies.batch_policy import BatchPolicy
```

---

## API Breaking Changes

### Request Body Changes:

**OLD:**
```json
{
  "program_name": "YEA Poultry Program 2025",
  "program_code": "YEA-2025-Q1",
  "program_type": "comprehensive"
}
```

**NEW:**
```json
{
  "batch_name": "2025 Q1 Batch - Greater Accra",
  "batch_code": "YEA-2025-Q1-ACCRA",
  "target_region": "Greater Accra",
  "target_constituencies": ["Tema East", "Tema West"]
}
```

### Response Field Changes:

- `program_name` → `batch_name`
- `program_code` → `batch_code`
- `program_type` → ❌ REMOVED
- `program_id` → `batch_id`
- Added: `target_region`
- Added: `target_constituencies`

---

## Testing Checklist

### Backend:
- [x] Django check passes with no errors
- [x] Database created and migrated successfully
- [x] All models renamed correctly
- [x] All views renamed correctly
- [x] All URLs updated correctly
- [ ] Test GET /api/admin/batches/
- [ ] Test POST /api/admin/batches/
- [ ] Test batch detail endpoints
- [ ] Test batch action endpoints

### Frontend Required Changes:
- [ ] Update all API endpoints from `/programs/` to `/batches/`
- [ ] Update all TypeScript interfaces (Program → Batch)
- [ ] Update all request body fields
- [ ] Update all response field references
- [ ] Update all UI labels
- [ ] Update all form validation
- [ ] Remove program_type dropdown
- [ ] Add target_region dropdown
- [ ] Add target_constituencies multiselect

---

## Migration Guide for Frontend

### Step 1: Update API Endpoints
```typescript
// OLD
const response = await api.get('/api/admin/programs/');

// NEW
const response = await api.get('/api/admin/batches/');
```

### Step 2: Update Interfaces
```typescript
// OLD
interface Program {
  program_name: string;
  program_code: string;
  program_type: string;
}

// NEW
interface Batch {
  batch_name: string;
  batch_code: string;
  target_region?: string;
  target_constituencies?: string[];
}
```

### Step 3: Update Form Fields
```typescript
// Remove program_type field
// Add target_region field
// Add target_constituencies field
```

### Step 4: Update All Labels
```
"Programs" → "Batches"
"Program Name" → "Batch Name"
"Program Code" → "Batch Code"
```

---

## Files Modified

### Python Files:
- `farms/batch_enrollment_models.py` (renamed + updated)
- `farms/models.py` (imports updated)
- `accounts/batch_admin_views.py` (renamed + 68 replacements)
- `accounts/batch_action_views.py` (renamed + 40 replacements)
- `accounts/admin_views.py` (4 replacements)
- `accounts/admin_urls.py` (URLs updated)
- `accounts/policies/batch_policy.py` (renamed + updated)
- `accounts/policies/__init__.py` (registry updated)
- `farms/services/program_enrollment_service.py` (5 replacements)

### Migrations:
- Deleted ALL old migrations
- Created fresh migrations for all apps
- Applied successfully to new database

---

## Rollback

**⚠️ WARNING:** This refactoring is NOT reversible.

To rollback, you would need to:
1. Restore from backup (if available)
2. OR manually reverse all changes
3. OR use version control to revert commits

---

## Success Criteria

✅ All models renamed  
✅ All views renamed  
✅ All URLs updated  
✅ All imports updated  
✅ Database dropped and recreated  
✅ Fresh migrations created and applied  
✅ Django check passes with no errors  
✅ No backward compatibility aliases remain  

---

## Next Steps

1. Test all API endpoints manually
2. Update frontend code
3. Run integration tests
4. Update API documentation
5. Notify frontend team of breaking changes
6. Deploy to staging environment for testing

---

**IMPORTANT:** This is a BREAKING CHANGE. All frontend code must be updated simultaneously when this is deployed.

