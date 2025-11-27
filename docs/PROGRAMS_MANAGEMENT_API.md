# Programs Management API Documentation

**Date:** November 27, 2025  
**Status:** ✅ **FULLY IMPLEMENTED**

---

## Overview

Complete REST API for managing government programs (YEA Poultry Program, etc.) with full CRUD operations, filtering, statistics, participants management, and program actions.

---

## Base URL

```
http://localhost:8000/api/admin/programs/
```

---

## Authentication

All endpoints require JWT authentication:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## Endpoints Summary

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/admin/programs/` | GET | List all programs with filtering | ⭐⭐⭐⭐⭐ |
| `/api/admin/programs/` | POST | Create new program | ⭐⭐⭐⭐ |
| `/api/admin/programs/{id}/` | GET | Get program details | ⭐⭐⭐⭐⭐ |
| `/api/admin/programs/{id}/` | PUT/PATCH | Update program | ⭐⭐⭐⭐ |
| `/api/admin/programs/{id}/` | DELETE | Archive program | ⭐⭐⭐ |
| `/api/admin/programs/{id}/toggle-active/` | POST | Activate/deactivate | ⭐⭐⭐⭐ |
| `/api/admin/programs/{id}/close-applications/` | POST | Close applications early | ⭐⭐⭐ |
| `/api/admin/programs/{id}/extend-deadline/` | POST | Extend deadline | ⭐⭐⭐ |
| `/api/admin/programs/{id}/participants/` | GET | List participants | ⭐⭐⭐⭐ |
| `/api/admin/programs/{id}/statistics/` | GET | Program statistics | ⭐⭐⭐⭐ |
| `/api/admin/programs/{id}/duplicate/` | POST | Duplicate program | ⭐⭐⭐ |

---

## 1. List Programs

### `GET /api/admin/programs/`

List all programs with advanced filtering, search, and pagination.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `page_size` (int, default: 20, max: 100) - Items per page
- `is_active` (boolean) - Filter by active status
- `program_type` (string) - Filter by type
- `status` (string) - Filter by status (active, full, inactive)
- `search` (string) - Search by name or code
- `sort_by` (string) - Sort field (e.g., '-created_at', 'application_deadline')

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/admin/programs/?is_active=true&page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (200 OK):**
```json
{
  "results": [
    {
      "id": "uuid-here",
      "program_code": "YEA-POULTRY-2025",
      "program_name": "YEA Poultry Development Program 2025",
      "program_type": "comprehensive",
      "description": "Support for youth entrepreneurs...",
      "eligibility_criteria": {
        "min_age": 18,
        "max_age": 35,
        "citizenship": "Ghanaian",
        "restrictions": ["No prior government support"]
      },
      "support_package": {
        "day_old_chicks": 1000,
        "starter_feed_bags": 3,
        "training_hours": 40
      },
      "support_package_value_ghs": 15000.00,
      "document_requirements": [
        {
          "document_type": "Ghana Card",
          "is_mandatory": true,
          "description": "Valid Ghana Card"
        }
      ],
      "batch_info": {
        "batch_code": "2025-Batch-01",
        "start_date": "2025-01-15"
      },
      "slot_allocation": {
        "total_slots": 100,
        "slots_filled": 45,
        "slots_available": 55,
        "slots_pending_approval": 12
      },
      "application_window": {
        "opens_at": "2025-01-01",
        "closes_at": "2025-12-31",
        "is_open": true,
        "days_remaining": 34
      },
      "regional_allocation": [
        {
          "region": "Greater Accra",
          "allocated_slots": 20,
          "filled_slots": 8,
          "available_slots": 12,
          "pending_slots": 3
        }
      ],
      "statistics": {
        "total_applications": 78,
        "approved_applications": 45,
        "rejected_applications": 21,
        "pending_review": 12,
        "approval_rate": 57.7,
        "average_review_time_days": 14
      },
      "is_active": true,
      "is_accepting_applications": true,
      "created_at": "2024-11-01T10:00:00Z",
      "updated_at": "2025-11-20T15:30:00Z",
      "created_by": {
        "id": "user-uuid",
        "username": "admin_user",
        "full_name": "John Admin"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 5,
    "pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

---

## 2. Get Program Detail

### `GET /api/admin/programs/{program_id}/`

Get comprehensive details about a specific program.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/admin/programs/UUID-HERE/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (200 OK):**
```json
{
  "id": "uuid-here",
  "program_code": "YEA-POULTRY-2025",
  "program_name": "YEA Poultry Development Program 2025",
  "program_type": "comprehensive",
  "description": "Support for youth entrepreneurs...",
  "long_description": "Detailed description with objectives...",
  "eligibility_criteria": {
    "min_age": 18,
    "max_age": 35,
    "citizenship": "Ghanaian",
    "restrictions": ["No prior government support"]
  },
  "support_package": {
    "day_old_chicks": 1000,
    "breed": "Layers",
    "starter_feed_bags": 3,
    "training_hours": 40
  },
  "support_package_value_ghs": 15000.00,
  "beneficiary_contribution_ghs": 0.00,
  "document_requirements": [...],
  "batch_info": {...},
  "slot_allocation": {...},
  "regional_allocation": [...],
  "application_window": {...},
  "approval_workflow": {
    "requires_constituency_approval": true,
    "requires_regional_approval": true,
    "requires_national_approval": true,
    "approval_sla_days": 30
  },
  "funding_source": {
    "source": "Government of Ghana - YEA",
    "budget_code": "YEA-2025-POULTRY",
    "total_budget_ghs": 1500000.00,
    "spent_ghs": 675000.00,
    "remaining_ghs": 825000.00
  },
  "participants": [
    {
      "id": "app-uuid",
      "applicant_name": "John Doe",
      "application_number": "PROG-2025-00001",
      "region": "Greater Accra",
      "status": "approved"
    }
  ],
  "statistics": {...},
  "is_active": true,
  "created_at": "2024-11-01T10:00:00Z",
  "created_by": {...},
  "last_modified_by": {...}
}
```

---

## 3. Create Program

### `POST /api/admin/programs/`

Create a new government program.

**Permissions:** Super Admin, National Admin only

**Request Body:**
```json
{
  "program_code": "YEA-GOAT-2026",
  "program_name": "YEA Goat Farming Program 2026",
  "program_type": "comprehensive",
  "description": "Support for goat farmers...",
  "long_description": "Detailed description...",
  "eligibility_criteria": {
    "min_age": 18,
    "max_age": 40,
    "citizenship": "Ghanaian",
    "restrictions": ["No prior government support"]
  },
  "support_package": {
    "breeding_goats": 10,
    "goat_breed": "Boer cross",
    "feed_bags": 20
  },
  "support_package_value_ghs": 8000.00,
  "document_requirements": [
    {
      "document_type": "Ghana Card",
      "is_mandatory": true,
      "description": "Valid Ghana Card"
    }
  ],
  "batch_info": {
    "batch_code": "2026-Batch-01",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31"
  },
  "slot_allocation": {
    "total_slots": 50
  },
  "regional_allocation": [
    {
      "region": "Northern",
      "allocated_slots": 20
    }
  ],
  "application_window": {
    "closes_at": "2026-06-30T23:59:59Z"
  },
  "approval_workflow": {
    "approval_sla_days": 21
  },
  "funding_source": {
    "source": "Government of Ghana - YEA",
    "budget_code": "YEA-2026-GOAT",
    "total_budget_ghs": 400000.00
  },
  "is_active": false,
  "is_published": false
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/admin/programs/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "program_name": "Test Program",
    "program_type": "comprehensive",
    "total_slots": 50,
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "description": "Test program description"
  }'
```

**Response (201 Created):**
```json
{
  "id": "new-uuid",
  "program_code": "YEA-GOAT-2026",
  "program_name": "YEA Goat Farming Program 2026",
  "message": "Program created successfully",
  "created_at": "2025-11-27T08:00:00Z"
}
```

**Validation Rules:**
- `program_code`: Unique, auto-generated if not provided
- `program_name`: Required, unique, 10-200 characters
- `total_slots`: Required, minimum 1
- `start_date` must be before `end_date`
- Regional slot sum should not exceed total_slots

---

## 4. Update Program

### `PUT /api/admin/programs/{program_id}/`  
### `PATCH /api/admin/programs/{program_id}/`

Update an existing program. Use PUT for full replacement, PATCH for partial updates.

**Permissions:** Super Admin, National Admin only

**Request Body (Partial Update):**
```json
{
  "application_window": {
    "closes_at": "2026-01-31T23:59:59Z"
  },
  "slot_allocation": {
    "total_slots": 120
  },
  "is_active": true
}
```

**Example Request:**
```bash
curl -X PATCH "http://localhost:8000/api/admin/programs/UUID-HERE/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": true,
    "slot_allocation": {"total_slots": 150}
  }'
```

**Response (200 OK):**
```json
{
  "id": "program-uuid",
  "program_code": "YEA-POULTRY-2025",
  "message": "Program updated successfully",
  "updated_fields": ["is_active", "total_slots"],
  "updated_at": "2025-11-27T08:30:00Z"
}
```

**Validation:**
- Cannot reduce `total_slots` below `slots_filled`
- Cannot change `program_code` if applications exist

---

## 5. Delete/Archive Program

### `DELETE /api/admin/programs/{program_id}/`

Soft delete (archive) a program.

**Permissions:** Super Admin only

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/api/admin/programs/UUID-HERE/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (200 OK):**
```json
{
  "message": "Program archived successfully",
  "program_id": "uuid",
  "applications_affected": 0,
  "archived_at": "2025-11-27T09:00:00Z"
}
```

**Error Response (409 Conflict):**
```json
{
  "error": "Cannot delete program",
  "reason": "Program has 45 approved applications",
  "suggestion": "Set is_active=false to hide program instead",
  "applications_count": 45
}
```

**Deletion Rules:**
- Cannot delete if program has approved applications
- Cannot delete if currently accepting applications
- Soft delete only (archived=true)

---

## 6. Toggle Active Status

### `POST /api/admin/programs/{program_id}/toggle-active/`

Activate or deactivate a program.

**Request Body:**
```json
{
  "is_active": true,
  "reason": "Program ready for enrollment"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/admin/programs/UUID-HERE/toggle-active/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true, "reason": "Ready"}'
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "program_code": "YEA-POULTRY-2025",
  "is_active": true,
  "status": "active",
  "message": "Program activated successfully"
}
```

---

## 7. Close Applications Early

### `POST /api/admin/programs/{program_id}/close-applications/`

Close application window before deadline.

**Request Body:**
```json
{
  "reason": "All slots filled",
  "send_notification": true
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/admin/programs/UUID-HERE/close-applications/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Slots filled"}'
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "is_accepting_applications": false,
  "closed_at": "2025-11-27T08:00:00Z",
  "reason": "All slots filled",
  "message": "Applications closed successfully"
}
```

---

## 8. Extend Deadline

### `POST /api/admin/programs/{program_id}/extend-deadline/`

Extend application deadline.

**Request Body:**
```json
{
  "new_deadline": "2026-02-28T23:59:59Z",
  "reason": "Low enrollment numbers",
  "notify_applicants": true
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/admin/programs/UUID-HERE/extend-deadline/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_deadline": "2026-02-28T23:59:59Z",
    "reason": "Low enrollment"
  }'
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "old_deadline": "2026-01-31",
  "new_deadline": "2026-02-28",
  "days_added": 28,
  "reason": "Low enrollment numbers",
  "message": "Deadline extended successfully"
}
```

**Validation:**
- New deadline must be in future
- New deadline must be before program end_date

---

## 9. List Participants

### `GET /api/admin/programs/{program_id}/participants/`

List all applicants/participants for a program.

**Query Parameters:**
- `status` - Filter by application status
- `region` - Filter by region
- `constituency` - Filter by constituency
- `page`, `page_size` - Pagination

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/admin/programs/UUID-HERE/participants/?status=approved&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (200 OK):**
```json
{
  "program": {
    "id": "uuid",
    "program_code": "YEA-POULTRY-2025",
    "program_name": "YEA Poultry Development Program 2025"
  },
  "participants": [
    {
      "application_id": "app-uuid",
      "application_number": "PROG-2025-00001",
      "applicant_name": "John Doe",
      "phone": "+233241234567",
      "email": "john@example.com",
      "region": "Greater Accra",
      "constituency": "Tema East",
      "farm_name": "Sunrise Poultry",
      "status": "approved",
      "application_date": "2025-01-15T10:00:00Z",
      "approved_date": "2025-02-01T14:30:00Z",
      "beneficiary_status": "active"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 45,
    "pages": 3
  }
}
```

---

## 10. Program Statistics

### `GET /api/admin/programs/{program_id}/statistics/`

Get detailed statistics and metrics for a program.

**Query Parameters:**
- `period` - Time period (all_time, 30d, 90d, 1y)
- `breakdown_by` - Grouping (region, constituency, month)

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/admin/programs/UUID-HERE/statistics/?period=30d&breakdown_by=region" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (200 OK):**
```json
{
  "program_id": "uuid",
  "program_name": "YEA Poultry Development Program 2025",
  "period": "30d",
  "overview": {
    "total_applications": 78,
    "approved": 45,
    "rejected": 21,
    "pending": 12,
    "approval_rate": 57.7,
    "average_review_days": 14,
    "total_budget_utilized": 675000.00
  },
  "applications_over_time": [
    {
      "month": "2025-01",
      "applications": 25,
      "approved": 18,
      "rejected": 5,
      "pending": 2
    }
  ],
  "regional_breakdown": [
    {
      "region": "Greater Accra",
      "applications": 28,
      "approved": 18,
      "approval_rate": 64.3,
      "slots_allocated": 20,
      "slots_filled": 18
    }
  ],
  "beneficiary_progress": {
    "total_beneficiaries": 45,
    "active": 38,
    "completed": 5,
    "dropouts": 2,
    "dropout_rate": 4.4
  }
}
```

---

## 11. Duplicate Program

### `POST /api/admin/programs/{program_id}/duplicate/`

Create a new program based on existing template.

**Request Body:**
```json
{
  "new_program_code": "YEA-POULTRY-2026",
  "new_program_name": "YEA Poultry Development Program 2026",
  "copy_settings": {
    "copy_eligibility": true,
    "copy_support_package": true,
    "copy_document_requirements": true,
    "copy_regional_allocation": true
  },
  "adjustments": {
    "batch_info": {
      "batch_code": "2026-Batch-01",
      "start_date": "2026-01-01"
    },
    "slot_allocation": {
      "total_slots": 150
    }
  }
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/admin/programs/UUID-HERE/duplicate/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_program_code": "YEA-POULTRY-2026",
    "new_program_name": "YEA Poultry Program 2026",
    "copy_settings": {"copy_eligibility": true}
  }'
```

**Response (201 Created):**
```json
{
  "id": "new-uuid",
  "program_code": "YEA-POULTRY-2026",
  "program_name": "YEA Poultry Development Program 2026",
  "message": "Program duplicated successfully",
  "source_program_id": "original-uuid"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Missing required field: program_name"
}
```

### 403 Forbidden
```json
{
  "error": "Permission denied. Only Super Admin and National Admin can create programs."
}
```

### 404 Not Found
```json
{
  "error": "Program not found"
}
```

### 409 Conflict
```json
{
  "error": "Cannot delete program",
  "reason": "Program has 45 approved applications",
  "suggestion": "Set is_active=false to hide program instead"
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to create program: Database connection error"
}
```

---

## Permission Matrix

| Role | List | View | Create | Update | Delete | Actions |
|------|------|------|--------|--------|--------|---------|
| Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| National Admin | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Regional Coordinator | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Constituency Official | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Extension Officer | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## Testing Checklist

### ✅ Core CRUD Operations
- [ ] List programs with filtering
- [ ] Get program detail
- [ ] Create new program
- [ ] Update program (PATCH)
- [ ] Archive program (DELETE)

### ✅ Filtering & Search
- [ ] Filter by is_active
- [ ] Filter by program_type
- [ ] Search by name/code
- [ ] Sort by various fields

### ✅ Program Actions
- [ ] Toggle active status
- [ ] Close applications early
- [ ] Extend deadline
- [ ] Duplicate program

### ✅ Data & Statistics
- [ ] List participants with filters
- [ ] Get program statistics
- [ ] Regional breakdown
- [ ] Applications over time

### ✅ Validation
- [ ] Cannot reduce slots below filled
- [ ] Unique program codes
- [ ] Date validations
- [ ] Permission checks

---

## Frontend Integration

### Example Service Methods

```typescript
// admin.service.ts

async listPrograms(filters: ProgramFilters): Promise<ProgramsResponse> {
  const params = new URLSearchParams();
  if (filters.is_active !== undefined) params.append('is_active', filters.is_active.toString());
  if (filters.program_type) params.append('program_type', filters.program_type);
  if (filters.search) params.append('search', filters.search);
  params.append('page', (filters.page || 1).toString());
  
  const response = await httpClient.get(`/api/admin/programs/?${params}`);
  return response.data;
}

async getProgramDetail(programId: string): Promise<Program> {
  const response = await httpClient.get(`/api/admin/programs/${programId}/`);
  return response.data;
}

async createProgram(data: CreateProgramData): Promise<Program> {
  const response = await httpClient.post('/api/admin/programs/', data);
  return response.data;
}

async updateProgram(programId: string, data: Partial<Program>): Promise<Program> {
  const response = await httpClient.patch(`/api/admin/programs/${programId}/`, data);
  return response.data;
}

async toggleProgramActive(programId: string, isActive: boolean, reason: string) {
  const response = await httpClient.post(
    `/api/admin/programs/${programId}/toggle-active/`,
    { is_active: isActive, reason }
  );
  return response.data;
}

async getProgramParticipants(programId: string, filters: ParticipantFilters) {
  const params = new URLSearchParams(filters as any);
  const response = await httpClient.get(
    `/api/admin/programs/${programId}/participants/?${params}`
  );
  return response.data;
}

async getProgramStatistics(programId: string, period: string = 'all_time') {
  const response = await httpClient.get(
    `/api/admin/programs/${programId}/statistics/?period=${period}`
  );
  return response.data;
}
```

---

## Implementation Status

✅ **COMPLETED**
- ✅ GovernmentProgram model updated with all required fields
- ✅ Migration created and applied
- ✅ List programs endpoint with filtering, search, pagination
- ✅ Get program detail endpoint
- ✅ Create program endpoint with validation
- ✅ Update program endpoint (PUT/PATCH)
- ✅ Delete/archive program endpoint
- ✅ Toggle active status endpoint
- ✅ Close applications endpoint
- ✅ Extend deadline endpoint
- ✅ List participants endpoint
- ✅ Program statistics endpoint
- ✅ Duplicate program endpoint
- ✅ URL routing configured
- ✅ Permission checks implemented
- ✅ Documentation completed

---

## Next Steps

1. ✅ Backend implementation complete
2. ⏳ Frontend integration
   - Programs list page
   - Program detail view
   - Create/edit forms
   - Participants management
   - Statistics dashboard
3. ⏳ Testing
   - Unit tests for views
   - Integration tests
   - Permission tests
4. ⏳ Deployment

---

## Support

For issues or questions, contact the development team or refer to:
- `farms/program_enrollment_models.py` - Program model
- `accounts/program_admin_views.py` - CRUD views
- `accounts/program_action_views.py` - Action endpoints
- `accounts/policies/program_policy.py` - Permission logic
