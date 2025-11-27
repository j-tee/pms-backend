# 🔄 Critical Update: Programs → Batches/Cohorts Terminology Change

**Date:** November 27, 2025  
**Impact:** Frontend, API Documentation, UI Labels  
**Status:** ⚠️ **ACTION REQUIRED**

---

## 📋 Executive Summary

The backend has been refactored to correctly reflect that this platform manages **batches/cohorts/intakes** of the **YEA Poultry Development Program**, not different types of programs.

### What Changed:
- ❌ **OLD**: Multiple "programs" (YEA Poultry, YEA Goat, etc.)
- ✅ **NEW**: Multiple "batches" of the single YEA Poultry Program

### Impact on Frontend:
- ✅ **API remains backward compatible** - no immediate breaking changes
- ⚠️ **UI/UX updates recommended** - update labels and terminology
- 📝 **Field name changes** - some response field names have changed
- 🎨 **Design considerations** - update copy to reflect batch/cohort concept

---

## 🎯 Core Concept Change

### Before (Incorrect)
```
System managed different government programs:
├── YEA Poultry Program 2025
├── YEA Goat Farming Program 2026  ❌ (We only do poultry!)
└── Planting for Food & Jobs        ❌ (Not relevant)
```

### After (Correct)
```
System manages YEA Poultry Program batches/cohorts:
├── 2025 Q1 Batch - Greater Accra (100 farmers, Jan-Mar)
├── 2025 Q2 Batch - Ashanti (150 farmers, Apr-Jun)
├── 2025 Northern Region Cohort (80 farmers, Jul-Sep)
└── 2026 Q1 National Intake (120 farmers, Jan-Mar)
```

### What is a Batch/Cohort?
A **batch** (or **cohort**) is a group of farmers who:
- Apply during the same recruitment period
- Are trained together
- Receive chicks/feed at the same time
- Graduate from the program together
- Have shared orientation and distribution dates

---

## 🔧 Backend Changes

### Model Renamed
```python
# OLD
class GovernmentProgram(models.Model):
    program_name = models.CharField(...)
    program_code = models.CharField(...)
    program_type = models.CharField(...)  # Removed - always poultry!

# NEW
class ProgramBatch(models.Model):
    batch_name = models.CharField(...)
    batch_code = models.CharField(...)
    # program_type removed
    target_region = models.CharField(...)  # NEW
    target_constituencies = ArrayField(...)  # NEW
```

### Key Field Changes

| Old Field Name | New Field Name | Notes |
|---------------|----------------|-------|
| `program_name` | `batch_name` | E.g., "2025 Q1 Batch - Greater Accra" |
| `program_code` | `batch_code` | E.g., "YEA-2025-Q1-ACCRA" |
| `program_type` | ❌ **REMOVED** | Always poultry - field no longer exists |
| N/A | `target_region` | **NEW** - Primary region for batch |
| N/A | `target_constituencies` | **NEW** - Specific constituencies |

### Database Table
- **Table name unchanged**: `farms_governmentprogram` (for backward compatibility)
- **Model alias added**: `GovernmentProgram = ProgramBatch` (imports still work)

---

## 📡 API Changes

### ✅ URLs Unchanged (Backward Compatible)
All existing API endpoints continue to work:
```
GET  /api/admin/programs/
POST /api/admin/programs/
GET  /api/admin/programs/{id}/
PUT  /api/admin/programs/{id}/
DELETE /api/admin/programs/{id}/
POST /api/admin/programs/{id}/toggle-active/
POST /api/admin/programs/{id}/close-applications/
POST /api/admin/programs/{id}/extend-deadline/
GET  /api/admin/programs/{id}/participants/
GET  /api/admin/programs/{id}/statistics/
POST /api/admin/programs/{id}/duplicate/
```

### 📝 Response Field Changes

#### List/Detail Responses - Field Name Updates

**OLD Response Structure:**
```json
{
  "id": "uuid",
  "program_name": "YEA Poultry Support Program 2025",
  "program_code": "YEA-2025-Q1",
  "program_type": "comprehensive",  // ❌ REMOVED
  "description": "...",
  // ... rest of fields
}
```

**NEW Response Structure:**
```json
{
  "id": "uuid",
  "batch_name": "2025 Q1 Batch - Greater Accra",  // ✅ RENAMED
  "batch_code": "YEA-2025-Q1-ACCRA",  // ✅ RENAMED
  "target_region": "Greater Accra",  // ✅ NEW
  "target_constituencies": ["Tema East", "Tema West"],  // ✅ NEW
  "description": "First quarter recruitment for Greater Accra region",
  // ... rest of fields
}
```

#### Request Body Changes

**Creating a New Batch (POST /api/admin/programs/):**

**OLD Request:**
```json
{
  "program_name": "YEA Poultry Program 2026",
  "program_code": "YEA-2026-Q1",
  "program_type": "comprehensive",  // ❌ No longer needed
  "description": "..."
}
```

**NEW Request:**
```json
{
  "batch_name": "2026 Q1 Batch - Greater Accra",  // ✅ Use batch_name
  "batch_code": "YEA-2026-Q1-ACCRA",  // ✅ Use batch_code
  "target_region": "Greater Accra",  // ✅ NEW FIELD
  "target_constituencies": ["Tema East", "Tema West"],  // ✅ NEW FIELD
  "description": "First quarter recruitment for Greater Accra region"
}
```

### ⚠️ Filter Parameter Changes

**List Endpoint Query Parameters:**

| Parameter | Status | Notes |
|-----------|--------|-------|
| `is_active` | ✅ **Still works** | No change |
| `status` | ✅ **Still works** | No change |
| `search` | ✅ **Still works** | Searches batch_name and batch_code |
| `program_type` | ⚠️ **DEPRECATED** | Will be removed - always returns all (poultry only) |
| `sort_by` | ✅ **Still works** | Can sort by batch_name, batch_code, etc. |

---

## 🎨 Frontend UI/UX Recommendations

### 1. Update All Labels and Copy

#### Navigation & Page Titles
```diff
- Programs
+ Batches

- Programs Management
+ Batch Management / Cohort Management

- Create New Program
+ Create New Batch / Launch New Cohort

- Program Details
+ Batch Details / Cohort Details
```

#### Table Headers
```diff
- Program Name | Program Code | Type | Status
+ Batch Name   | Batch Code   | Region | Status

- YEA Poultry Program 2025 | YEA-2025-Q1 | Comprehensive | Active
+ 2025 Q1 Batch - Accra    | YEA-2025-Q1-ACCRA | Greater Accra | Active
```

#### Form Labels
```diff
- Program Name *
+ Batch/Cohort Name *

- Program Code *
+ Batch Code *

- Program Type *  (Remove this field entirely)

+ Target Region (NEW field)
+ Target Constituencies (NEW field - multiselect)
```

### 2. Update UI Component Names

```typescript
// OLD
<ProgramsList />
<ProgramDetailPage />
<CreateProgramForm />
<ProgramCard />

// NEW
<BatchesList />
<BatchDetailPage />
<CreateBatchForm />
<BatchCard />
```

### 3. Update Form Validation

```typescript
// OLD validation
const schema = {
  program_name: Yup.string().required('Program name is required'),
  program_code: Yup.string().required('Program code is required'),
  program_type: Yup.string().required('Program type is required'),
};

// NEW validation
const schema = {
  batch_name: Yup.string().required('Batch name is required'),
  batch_code: Yup.string().required('Batch code is required'),
  target_region: Yup.string().nullable(),
  target_constituencies: Yup.array().of(Yup.string()).nullable(),
  // Remove program_type validation
};
```

### 4. Update TypeScript Interfaces

```typescript
// OLD
interface Program {
  id: string;
  program_name: string;
  program_code: string;
  program_type: 'comprehensive' | 'input_subsidy' | 'financial_grant';
  description: string;
  // ...
}

// NEW
interface ProgramBatch {
  id: string;
  batch_name: string;  // ✅ RENAMED
  batch_code: string;  // ✅ RENAMED
  target_region?: string;  // ✅ NEW
  target_constituencies?: string[];  // ✅ NEW
  description: string;
  // program_type removed
  // ...
}

// Backward compatibility alias
type Program = ProgramBatch;
```

### 5. Update Service Methods

```typescript
// admin.service.ts

// OLD
async listPrograms(filters: ProgramFilters): Promise<ProgramsResponse> {
  const params = new URLSearchParams();
  if (filters.program_type) params.append('program_type', filters.program_type);
  // ...
}

async createProgram(data: CreateProgramData): Promise<Program> {
  const payload = {
    program_name: data.program_name,
    program_code: data.program_code,
    program_type: data.program_type,
    // ...
  };
  return await httpClient.post('/api/admin/programs/', payload);
}

// NEW
async listBatches(filters: BatchFilters): Promise<BatchesResponse> {
  const params = new URLSearchParams();
  // Remove program_type filter
  if (filters.target_region) params.append('target_region', filters.target_region);
  // ...
}

async createBatch(data: CreateBatchData): Promise<ProgramBatch> {
  const payload = {
    batch_name: data.batch_name,  // ✅ RENAMED
    batch_code: data.batch_code,  // ✅ RENAMED
    target_region: data.target_region,  // ✅ NEW
    target_constituencies: data.target_constituencies,  // ✅ NEW
    // Remove program_type
    // ...
  };
  return await httpClient.post('/api/admin/programs/', payload);
}

// Keep old method names as aliases for backward compatibility
async listPrograms(filters: ProgramFilters): Promise<ProgramsResponse> {
  return this.listBatches(filters);
}
```

---

## 📝 Example Use Cases

### Creating a New Batch

**Scenario**: Admin wants to create a new recruitment batch for Greater Accra region in Q1 2026.

**Frontend Form:**
```
Batch/Cohort Name: "2026 Q1 Batch - Greater Accra"
Batch Code: "YEA-2026-Q1-ACCRA"
Target Region: "Greater Accra" (dropdown)
Target Constituencies: ["Tema East", "Tema West", "Accra Central"] (multiselect)
Description: "First quarter recruitment focusing on Greater Accra region"
Start Date: 2026-01-01
End Date: 2026-03-31
Application Deadline: 2026-02-28
Total Slots: 100
```

**API Request:**
```json
POST /api/admin/programs/

{
  "batch_name": "2026 Q1 Batch - Greater Accra",
  "batch_code": "YEA-2026-Q1-ACCRA",
  "target_region": "Greater Accra",
  "target_constituencies": ["Tema East", "Tema West", "Accra Central"],
  "description": "First quarter recruitment focusing on Greater Accra region",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31",
  "application_deadline": "2026-02-28",
  "total_slots": 100,
  "regional_allocation": [
    {
      "region": "Greater Accra",
      "allocated_slots": 100
    }
  ],
  "support_package_details": {
    "day_old_chicks": 1000,
    "starter_feed_bags": 3,
    "training_hours": 40
  },
  "is_active": false,
  "is_published": false
}
```

### Displaying Batch List

**Old UI:**
```
Programs
─────────────────────────────────────────────────────
Program Name                          | Type          | Status
─────────────────────────────────────────────────────
YEA Poultry Program 2025              | Comprehensive | Active
YEA Goat Farming Program 2026         | Input Subsidy | Inactive
```

**New UI:**
```
Batches & Cohorts
─────────────────────────────────────────────────────────────
Batch Name                    | Region        | Slots  | Status
─────────────────────────────────────────────────────────────
2025 Q1 Batch - Greater Accra | Greater Accra | 45/100 | Active
2025 Q2 Batch - Ashanti       | Ashanti       | 80/150 | Active
2025 Northern Cohort          | Northern      | 12/80  | Full
2026 Q1 National Intake       | National      | 0/120  | Inactive
```

---

## 🚀 Migration Path for Frontend

### Phase 1: Immediate (Backward Compatible)
**Timeline**: This week

1. ✅ **Update TypeScript interfaces** to include both old and new field names
2. ✅ **Add field aliases** in service layer to handle both formats
3. ✅ **Test existing functionality** - everything should still work
4. ⚠️ **Update tests** to use new field names

```typescript
// Service layer adapter
interface ProgramBatchResponse {
  batch_name?: string;
  program_name?: string;  // Fallback for old responses
  batch_code?: string;
  program_code?: string;  // Fallback
}

function normalizeBatch(data: ProgramBatchResponse): ProgramBatch {
  return {
    batch_name: data.batch_name || data.program_name || '',
    batch_code: data.batch_code || data.program_code || '',
    target_region: data.target_region,
    target_constituencies: data.target_constituencies || [],
    // ...
  };
}
```

### Phase 2: UI Updates (Non-Breaking)
**Timeline**: Next sprint

1. 🎨 **Update all UI labels** from "Programs" to "Batches/Cohorts"
2. 📝 **Update form labels** and help text
3. 🗑️ **Remove program_type filter** from UI
4. ➕ **Add target_region and target_constituencies** filters
5. 📊 **Update dashboard cards** and metrics display

### Phase 3: Code Refactoring (Breaking Changes)
**Timeline**: After Phase 2 is stable

1. 🔄 **Rename components** (ProgramsList → BatchesList)
2. 🔄 **Rename service methods** (listPrograms → listBatches)
3. 🔄 **Update routes** (/programs → /batches)
4. 🗑️ **Remove all references** to program_type
5. ✅ **Full regression testing**

---

## ✅ Testing Checklist

### Backend Verification
- [ ] Test GET /api/admin/programs/ returns batch_name and batch_code
- [ ] Test POST /api/admin/programs/ accepts batch_name and batch_code
- [ ] Test program_type filter is ignored (doesn't break API)
- [ ] Test target_region and target_constituencies are returned
- [ ] Test backward compatibility with GovernmentProgram imports

### Frontend Updates
- [ ] Update TypeScript interfaces with new field names
- [ ] Add field name normalization in service layer
- [ ] Update all UI labels to "Batch" or "Cohort"
- [ ] Remove program_type dropdown from create/edit forms
- [ ] Add target_region dropdown
- [ ] Add target_constituencies multiselect
- [ ] Update table columns to show Region instead of Type
- [ ] Update search placeholder text
- [ ] Update validation schemas
- [ ] Update error messages

### Integration Testing
- [ ] Test creating new batch with new field names
- [ ] Test editing existing batch
- [ ] Test listing batches with filters
- [ ] Test batch detail page
- [ ] Test participants listing for a batch
- [ ] Test statistics for a batch
- [ ] Test duplicating a batch

---

## 🆘 Support & Questions

### Common Questions

**Q: Do I need to update my API calls immediately?**  
A: No, the API is backward compatible. Existing calls will continue to work.

**Q: What if I'm still sending `program_name` in requests?**  
A: The backend will accept both `program_name` and `batch_name` during transition period.

**Q: Should I rename my component files now?**  
A: Not immediately. Phase 1 focuses on compatibility. Rename in Phase 3.

**Q: What about the URL routes?**  
A: API URLs remain `/api/admin/programs/` for now. You can update frontend routes independently.

**Q: How do I filter by region now?**  
A: Use the new `target_region` parameter: `?target_region=Greater Accra`

### Contact

For technical questions or support:
- **Backend Team**: [Backend Lead Email]
- **API Documentation**: `/docs/PROGRAMS_MANAGEMENT_API.md`
- **Model Reference**: `/farms/program_enrollment_models.py`
- **Slack Channel**: #pms-frontend-backend

---

## 📚 Additional Resources

- [Program Enrollment Models Source Code](../farms/program_enrollment_models.py)
- [API Views Implementation](../accounts/program_admin_views.py)
- [API Action Views](../accounts/program_action_views.py)
- [Permission Policies](../accounts/policies/program_policy.py)
- [Complete API Documentation](./PROGRAMS_MANAGEMENT_API.md)

---

**Last Updated**: November 27, 2025  
**Document Version**: 1.0  
**Change Type**: Non-Breaking (Backward Compatible)
