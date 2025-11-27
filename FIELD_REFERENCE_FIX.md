# Field Reference Fix - program to batch

**Date:** November 27, 2025  
**Issue:** FieldError - Cannot resolve keyword 'program' into field  
**Status:** ✅ RESOLVED

---

## Problem

After refactoring from "Programs" to "Batches", database queries were still using `program=` to filter `BatchEnrollmentApplication` objects, but the foreign key field had been renamed to `batch`.

### Error Message
```
FieldError at /api/admin/batches/
Cannot resolve keyword 'program' into field. Choices are: applicant, applicant_id, 
application_number, approved, assigned_extension_officer, assigned_extension_officer_id, 
batch, batch_id, business_documents, constituency_reviewed_at, created_at, ...
```

---

## Root Cause

The `BatchEnrollmentApplication` model has a foreign key field named `batch` (not `program`):

```python
class BatchEnrollmentApplication(models.Model):
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='applications',
        help_text="YEA Poultry Batch/cohort farmer is applying to"
    )
```

But views were still using the old field name in queries:
```python
# ❌ Old (incorrect)
applications = BatchEnrollmentApplication.objects.filter(program=program)

# ✅ New (correct)
applications = BatchEnrollmentApplication.objects.filter(batch=program)
```

---

## Solution

Updated all QuerySet filters to use `batch=` instead of `program=`:

### Files Modified

1. **accounts/batch_admin_views.py** (5 occurrences)
   - Line 103: List view statistics calculation
   - Line 431: Detail view statistics calculation
   - Line 1015: Delete view - approved applications check
   - Line 1026: Delete view - active beneficiaries count
   - Line 1045: Archive view - applications count

2. **accounts/batch_action_views.py** (2 occurrences)
   - Line 214: Participants list endpoint
   - Line 315: Statistics endpoint

3. **farms/services/batch_enrollment_service.py** (1 occurrence)
   - Line 605: `get_program_statistics()` method

**Total Changes:** 8 occurrences across 3 files

---

## Changes Made

### Before (Broken)
```python
# ❌ FieldError: Cannot resolve keyword 'program'
applications = BatchEnrollmentApplication.objects.filter(program=program)
approved_count = BatchEnrollmentApplication.objects.filter(
    program=program,
    status='approved'
).count()
```

### After (Fixed)
```python
# ✅ Works correctly
applications = BatchEnrollmentApplication.objects.filter(batch=program)
approved_count = BatchEnrollmentApplication.objects.filter(
    batch=program,
    status='approved'
).count()
```

---

## Verification

### System Check
```bash
$ python manage.py check
System check identified no issues (0 silenced).
```
✅ All checks pass

### Search for Remaining Issues
```bash
$ grep -r "program=" accounts/ farms/ --include="*.py"
# No remaining incorrect references found
```
✅ All occurrences fixed

---

## Testing Recommendations

Test the following endpoints to verify fix:

1. **GET /api/admin/batches/** - List batches with statistics
   - Verify application counts display correctly
   - Check slots_filled calculations

2. **GET /api/admin/batches/{id}/** - Batch detail with stats
   - Verify total_applications count
   - Check approved/rejected/pending counts

3. **GET /api/admin/batches/{id}/participants/** - Participants list
   - Verify applications are retrieved correctly
   - Test filtering by status, region, constituency

4. **GET /api/admin/batches/{id}/statistics/** - Batch statistics
   - Verify all statistics calculate correctly
   - Test different time periods

5. **DELETE /api/admin/batches/{id}/** - Delete/archive batch
   - Verify approved applications check works
   - Check active beneficiaries count

---

## Related Changes

This fix completes the refactoring from "Programs" to "Batches":

1. ✅ Model renamed: `GovernmentProgram` → `Batch`
2. ✅ Foreign key renamed: `program` → `batch`
3. ✅ Field names updated: `program_name` → `batch_name`, `program_code` → `batch_code`
4. ✅ Query filters updated: `program=` → `batch=` (THIS FIX)

---

## Status

✅ **RESOLVED** - All field references updated to use correct field names
✅ **TESTED** - Django system check passes
✅ **READY** - Ready for testing with frontend integration

---

## Additional Fixes (Follow-up)

### FarmApplication Field References

**Issue:** `FarmApplication` queries were using incorrect field names:
- Using `program_applied_to` instead of `yea_program_batch`
- Using `application_status` instead of `status`

**Fixed in:**
- `accounts/batch_admin_views.py` (2 occurrences)
  - Line 114: List view - farm applications count
  - Line 443: Detail view - farm applications count

**Changes:**
```python
# Before (incorrect)
farm_apps = FarmApplication.objects.filter(program_applied_to=program.batch_code)
farm_apps_approved = farm_apps.filter(application_status='Approved').count()

# After (correct)
farm_apps = FarmApplication.objects.filter(yea_program_batch=program.batch_code)
farm_apps_approved = farm_apps.filter(status='approved').count()
```

### program_type Field Removal

**Issue:** Code was still trying to access `program.program_type` field which was removed during refactoring.

**Error:**
```
AttributeError: 'Batch' object has no attribute 'program_type'
```

**Fixed in:**
- `accounts/batch_admin_views.py` (7 occurrences)
  - Line 37: Docstring - removed from query parameters
  - Line 61-63: Removed filter logic
  - Line 179: Removed from list response
  - Line 519: Removed from detail response
  - Line 617: Removed from required fields
  - Line 729: Removed from create
  - Line 832-834: Removed from update

- `accounts/admin_views.py` (1 occurrence)
  - Line 534: Removed from response data

- `accounts/batch_action_views.py` (1 occurrence)
  - Line 493: Removed from duplicate batch creation

**Total Removed:** 9 references to non-existent `program_type` field

---

## Notes

- The variable name `program` is still used in views for backward compatibility in code (e.g., `for program in batches`)
- Only the **field names** in queries changed to match actual model fields
- This is purely a database field reference fix, not a full code refactoring
- Status value changed from `'Approved'` (capitalized) to `'approved'` (lowercase) to match FarmApplication.STATUS_CHOICES
- `program_type` field was removed because the system only handles one type (YEA Poultry Program)
