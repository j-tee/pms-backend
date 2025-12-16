# Backend Batch CRUD API Documentation

**Date:** December 16, 2025  
**Version:** 1.1  
**Status:** Production Ready  
**Base URL (Production):** `https://pms.alphalogictech.com`  
**Base URL (Development):** `http://localhost:8000`

---

## 📚 Understanding Batch Status Fields

### **`is_active` vs `is_published` - What's the Difference?**

The system uses **two separate boolean fields** to control batch visibility and operational status:

#### **`is_active`** - Internal Operational Status
- **Purpose**: Controls whether the batch is operationally active or paused
- **Use Case**: Temporarily pause a batch without hiding it from public view
- **Examples**:
  - Pause during policy review or system maintenance
  - Temporarily stop accepting applications while reviewing existing ones
  - Deactivate when slots are full
- **Visibility**: Inactive batches can still be visible if `is_published=true`

#### **`is_published`** - Public Visibility Control
- **Purpose**: Controls whether the batch is published and visible to farmers/public
- **Use Case**: Draft batches that aren't ready for public view
- **Examples**:
  - Create batch early but don't publish until launch date
  - Unpublish temporarily while making major edits
  - Hide completed batches from public view
- **Visibility**: Unpublished batches are **never** visible to public, regardless of `is_active`

#### **Why Both Are Needed - Workflow Example**

```
1. Draft Phase:        is_active=false, is_published=false
   → Batch created but not visible to anyone except admins

2. Ready to Launch:    is_active=true,  is_published=true
   → Batch is live and accepting applications

3. Temporarily Pause:  is_active=false, is_published=true
   → Batch visible but not accepting applications

4. Permanently Close:  is_active=false, is_published=false
   → Batch hidden from public, archived
```

#### **Public API Query Behavior**

```bash
# This query requires BOTH is_active=true AND is_published=true
GET /api/public/batches/?is_active=true&is_published=true

# If a batch has is_published=false, it will return 0 results
# even if the batch exists and is_active=true
```

**⚠️ Common Pitfall**: Creating a batch with `is_active=true` but `is_published=false` will result in the batch not appearing in public queries. Always set **both** fields to `true` for public visibility.

---

## 🔴 Critical Issues Fixed

### **Issue #1: Public Batch Query Returning 0 Records** ✅ RESOLVED

**Root Cause:**  
The public batch endpoint was attempting to filter on `accepts_applications` field, which is a model property, not a database field. Django cannot filter QuerySets using properties.

**Fix Applied:**
```python
# ❌ OLD CODE (BROKEN)
if accepts_applications:
    queryset = queryset.filter(accepts_applications=True)  # Field doesn't exist!

# ✅ NEW CODE (FIXED)
# Filter after retrieval using the property
for batch in queryset:
    accepts_apps = batch.is_accepting_applications  # Uses property
    if accepts_applications and not accepts_apps:
        continue  # Skip batches that don't accept applications
```

**Impact:** This was causing the "No active program batches available" message in production.

---

### **Issue #2: Admin CRUD Operations Failing** ✅ RESOLVED

**Root Cause:**  
Django URL routing conflict - three separate views were registered for the same URL pattern `batches/<uuid:batch_id>/`. Django only matches the first pattern, so PUT, PATCH, and DELETE requests were being handled by the GET view.

**Fix Applied:**
```python
# ❌ OLD CODE (BROKEN) - Only GET worked
path('batches/<uuid:batch_id>/', AdminBatchDetailView.as_view()),  # GET
path('batches/<uuid:batch_id>/', AdminBatchUpdateView.as_view()),  # PUT/PATCH - NEVER REACHED
path('batches/<uuid:batch_id>/', AdminBatchDeleteView.as_view()),  # DELETE - NEVER REACHED

# ✅ NEW CODE (FIXED) - All methods route correctly
path('batches/<uuid:batch_id>/', AdminBatchDetailUpdateDeleteView.as_view())  # GET, PUT, PATCH, DELETE
```

**Impact:** Edit, Update, and Delete operations were silently failing in production.

---

## 📍 API Endpoint Overview

### **Correct Endpoint Pattern**

The backend uses **`/api/admin/batches/`** (NOT `/api/admin/programs/`)

```
✅ /api/public/batches/                          (Public - No Auth)
✅ /api/admin/batches/                            (Admin - Auth Required)
✅ /api/admin/batches/{batchId}/
✅ /api/admin/batches/{batchId}/toggle-active/
✅ /api/admin/batches/{batchId}/close-applications/
✅ /api/admin/batches/{batchId}/extend-deadline/
✅ /api/admin/batches/{batchId}/participants/
✅ /api/admin/batches/{batchId}/statistics/
```
✅ /api/public/batches/                          (Public - No Auth)
✅ /api/admin/batches/                            (Admin - Auth Required)
✅ /api/admin/batches/{batchId}/
✅ /api/admin/batches/{batchId}/toggle-active/
✅ /api/admin/batches/{batchId}/toggle-publish/
✅ /api/admin/batches/{batchId}/close-applications/
✅ /api/admin/batches/{batchId}/extend-deadline/
✅ /api/admin/batches/{batchId}/participants/
✅ /api/admin/batches/{batchId}/statistics/
✅ /api/admin/batches/{batchId}/duplicate/
```

---

## 🔐 Authentication

All admin endpoints require JWT authentication:

```http
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Permissions Required:**
- **Super Admin**: Full access to all operations
- **National Admin**: Can view, create, edit batches
- **Regional Admin**: Can view batches in their region
- **Constituency Admin**: Can view batches in their constituency

---

## 📋 API Endpoints

### 1. List Batches (Public)

Get publicly available batches for application selection.

```http
GET /api/public/batches/
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `is_active` | boolean | No | Filter by active status |
| `is_published` | boolean | No | Filter by published status |
| `accepts_applications` | boolean | No | Filter by accepting applications |

**Example Request:**
```bash
curl -X GET "https://pms.alphalogictech.com/api/public/batches/?is_active=true&is_published=true"
```

**Example Response:**
```json
{
  "count": 2,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "batch_name": "YEA Poultry Program 2025 - Cohort 1",
      "batch_code": "YEA-2025-C1",
      "description": "First cohort of the 2025 YEA Poultry Development Program",
      "long_description": "Comprehensive support program...",
      "target_region": "Greater Accra",
      "implementing_agency": "Youth Employment Agency",
      "total_slots": 100,
      "slots_filled": 1,
      "slots_available": 99,
      "start_date": "2025-11-27",
      "end_date": "2026-11-26",
      "application_deadline": "2026-01-26",
      "early_application_deadline": null,
      "is_active": true,
      "is_published": true,
      "accepts_applications": false,
      "status": "active",
      "support_package_details": {
        "day_old_chicks": 1000,
        "starter_feed_bags": 3
      },
      "support_package_value_ghs": "15000.00",
      "beneficiary_contribution_ghs": "0.00",
      "min_bird_capacity": null,
      "max_bird_capacity": null,
      "eligible_farmer_age_min": 18,
      "eligible_farmer_age_max": 35
    }
  ]
}
```

---

### 2. List Batches (Admin)

Get all batches with filtering, search, and pagination.

```http
GET /api/admin/batches/
Authorization: Bearer {jwt_token}
```

**Query Parameters:**
| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `page` | integer | No | Page number | 1 |
| `page_size` | integer | No | Items per page (max: 100) | 20 |
| `is_active` | boolean | No | Filter by active status | - |
| `status` | string | No | Filter by status: `active`, `full`, `inactive` | - |
| `search` | string | No | Search by name, code, or description | - |
| `sort_by` | string | No | Sort field (see below) | `-created_at` |

**Valid Sort Fields:**
- `created_at`, `-created_at` (descending)
- `batch_name`, `-batch_name`
- `application_deadline`, `-application_deadline`
- `start_date`, `-start_date`
- `total_slots`, `-total_slots`

**Example Request:**
```bash
curl -X GET "https://pms.alphalogictech.com/api/admin/batches/?page=1&page_size=20&is_active=true&sort_by=-created_at" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Example Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "batch_code": "YEA-2025-C1",
      "batch_name": "YEA Poultry Program 2025 - Cohort 1",
      "description": "First cohort of the 2025 YEA Poultry Development Program",
      "target_region": "Greater Accra",
      "implementing_agency": "Youth Employment Agency",
      "is_active": true,
      "is_accepting_applications": false,
      "is_published": true,
      "status": "active",
      "slot_allocation": {
        "total_slots": 100,
        "slots_filled": 1,
        "slots_available": 99,
        "utilization_rate": 1.0
      },
      "application_window": {
        "opens_at": "2025-11-27",
        "closes_at": "2026-01-26",
        "early_deadline": null,
        "is_open": false,
        "days_remaining": 41
      },
      "statistics": {
        "applications_total": 0,
        "applications_approved": 0,
        "applications_rejected": 0,
        "applications_pending": 0,
        "approval_rate": 0,
        "avg_review_days": null
      },
      "regional_breakdown": [
        {
          "region": "Greater Accra",
          "allocated_slots": 50,
          "filled_slots": 0,
          "available_slots": 50,
          "pending_slots": 0
        }
      ],
      "created_at": "2025-11-27T12:00:00Z",
      "updated_at": "2025-12-16T20:00:00Z"
    }
  ]
}
```

---

### 3. Get Batch Detail

Get detailed information about a specific batch.

```http
GET /api/admin/batches/{batchId}/
Authorization: Bearer {jwt_token}
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `batchId` | UUID | The unique identifier of the batch |

**Example Request:**
```bash
curl -X GET "https://pms.alphalogictech.com/api/admin/batches/550e8400-e29b-41d4-a716-446655440000/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_code": "YEA-2025-C1",
  "batch_name": "YEA Poultry Program 2025 - Cohort 1",
  "description": "First cohort of the 2025 YEA Poultry Development Program",
  "long_description": "Comprehensive support program providing day-old chicks...",
  "target_region": "Greater Accra",
  "target_constituencies": ["Tema East", "Tema West", "Ashaiman"],
  "implementing_agency": "Youth Employment Agency",
  "start_date": "2025-11-27",
  "end_date": "2026-11-26",
  "application_deadline": "2026-01-26",
  "early_application_deadline": null,
  "total_slots": 100,
  "slots_filled": 1,
  "slots_available": 99,
  "allow_overbooking": false,
  "overbooking_percentage": 0,
  "is_active": true,
  "is_published": true,
  "is_accepting_applications_override": true,
  "status": "active",
  "eligibility_criteria": {
    "citizenship": "Ghanaian",
    "educational_level": "Any",
    "employment_status": ["Unemployed", "Underemployed"]
  },
  "support_package_details": {
    "day_old_chicks": 1000,
    "starter_feed_bags": 3,
    "training_sessions": 12,
    "extension_visits_per_month": 2
  },
  "support_package_value_ghs": "15000.00",
  "beneficiary_contribution_ghs": "0.00",
  "document_requirements": [
    {
      "document_type": "Ghana Card",
      "is_mandatory": true,
      "description": "Valid national identification card"
    }
  ],
  "regional_allocation": [
    {
      "region": "Greater Accra",
      "allocated_slots": 50,
      "filled_slots": 0,
      "available_slots": 50,
      "pending_slots": 0
    }
  ],
  "min_farm_age_months": 0,
  "max_farm_age_years": null,
  "min_bird_capacity": null,
  "max_bird_capacity": null,
  "eligible_farmer_age_min": 18,
  "eligible_farmer_age_max": 35,
  "statistics": {
    "applications_total": 0,
    "applications_approved": 0,
    "applications_rejected": 0,
    "applications_pending": 0,
    "enrolled_count": 0,
    "approval_rate": 0
  },
  "created_at": "2025-11-27T12:00:00Z",
  "updated_at": "2025-12-16T20:00:00Z",
  "created_by": {
    "id": "user-uuid",
    "full_name": "John Doe",
    "email": "admin@yea.gov.gh"
  }
}
```

---

### 4. Create Batch

Create a new batch/program.

```http
POST /api/admin/batches/
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Required Fields:**
- `batch_code` (string, unique)
- `batch_name` (string, unique)
- `description` (string)
- `start_date` (date: YYYY-MM-DD)
- `end_date` (date: YYYY-MM-DD)
- `total_slots` (integer)
- `implementing_agency` (string)

**Example Request:**
```bash
curl -X POST "https://pms.alphalogictech.com/api/admin/batches/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "batch_code": "YEA-2026-C1",
    "batch_name": "YEA Poultry Program 2026 - Cohort 1",
    "description": "New cohort for 2026",
    "long_description": "Comprehensive support for emerging poultry farmers",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "application_deadline": "2025-12-15",
    "total_slots": 50,
    "target_region": "Ashanti",
    "target_constituencies": ["Kumasi Central", "Kumasi South"],
    "implementing_agency": "Youth Employment Agency",
    "eligibility_criteria": {
      "citizenship": "Ghanaian",
      "min_age": 18,
      "max_age": 35
    },
    "support_package_details": {
      "day_old_chicks": 1000,
      "starter_feed_bags": 3,
      "training_sessions": 12
    },
    "support_package_value_ghs": 15000.00,
    "beneficiary_contribution_ghs": 0.00,
    "eligible_farmer_age_min": 18,
    "eligible_farmer_age_max": 35,
    "is_active": true,
    "is_published": false,
    "is_accepting_applications_override": true
  }'
```

**Response:** 201 Created
```json
{
  "id": "new-batch-uuid",
  "batch_code": "YEA-2026-C1",
  "batch_name": "YEA Poultry Program 2026 - Cohort 1",
  "message": "Batch created successfully",
  "created_at": "2025-12-16T20:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request`: Missing required fields or validation errors
- `409 Conflict`: Batch code or name already exists
- `403 Forbidden`: Insufficient permissions

---

### 5. Update Batch (Partial Update)

Update specific fields of a batch.

```http
PATCH /api/admin/batches/{batchId}/
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Example Request:**
```bash
curl -X PATCH "https://pms.alphalogictech.com/api/admin/batches/550e8400-e29b-41d4-a716-446655440000/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "batch_name": "Updated Batch Name",
    "total_slots": 150,
    "application_deadline": "2026-02-28"
  }'
```

**Response:** 200 OK
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_code": "YEA-2025-C1",
  "batch_name": "Updated Batch Name",
  "total_slots": 150,
  "message": "Batch updated successfully",
  "updated_fields": ["batch_name", "total_slots", "application_deadline"],
  "updated_at": "2025-12-16T20:35:00Z"
}
```

---

### 6. Update Batch (Full Update)

Replace all fields of a batch.

```http
PUT /api/admin/batches/{batchId}/
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Note:** All required fields must be provided.

---

### 7. Delete/Archive Batch

Soft delete (archive) a batch.

```http
DELETE /api/admin/batches/{batchId}/
Authorization: Bearer {jwt_token}
```

**Example Request:**
```bash
curl -X DELETE "https://pms.alphalogictech.com/api/admin/batches/550e8400-e29b-41d4-a716-446655440000/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:** 200 OK
```json
{
  "message": "Program archived successfully",
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "applications_affected": 0,
  "archived_at": "2025-12-16T20:40:00Z"
}
```

**Protection Rules:**
- ❌ Cannot delete if batch has approved applications
- ❌ Cannot delete if currently accepting applications

**Error Response (409 Conflict):**
```json
{
  "error": "Cannot delete program",
  "reason": "Program has 5 approved applications",
  "suggestion": "Set is_active=false to hide program instead",
  "applications_count": 5,
  "active_beneficiaries": 3
}
```

---

### 8. Toggle Active Status

Activate or deactivate a batch.

```http
POST /api/admin/batches/{batchId}/toggle-active/
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "is_active": false,
  "reason": "Pausing program for review"
}
```

**Example Request:**
```bash
curl -X POST "https://pms.alphalogictech.com/api/admin/batches/550e8400-e29b-41d4-a716-446655440000/toggle-active/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false,
    "reason": "Pausing for policy review"
  }'
```

**Response:** 200 OK
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_code": "YEA-2025-C1",
  "is_active": false,
  "status": "inactive",
  "reason": "Pausing for policy review",
  "message": "Program deactivated successfully",
  "updated_at": "2025-12-16T20:45:00Z"
}
```

---

### 9. Toggle Publish Status

Publish or unpublish a batch to control public visibility.

```http
POST /api/admin/batches/{batchId}/toggle-publish/
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "is_published": true,
  "reason": "Making batch visible to farmers"
}
```

**Example Request:**
```bash
curl -X POST "https://pms.alphalogictech.com/api/admin/batches/550e8400-e29b-41d4-a716-446655440000/toggle-publish/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "is_published": true,
    "reason": "Launching batch to public"
  }'
```

**Response:** 200 OK
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_code": "YEA-2025-C1",
  "batch_name": "YEA Poultry Program 2025 - Cohort 1",
  "is_published": true,
  "is_active": true,
  "reason": "Launching batch to public",
  "message": "Batch published successfully",
  "note": "Batch must be both published AND active to be visible to farmers",
  "updated_at": "2025-12-16T21:00:00Z"
}
```

**Important Notes:**
- For a batch to appear in public queries, **both** `is_published=true` AND `is_active=true` must be set
- Unpublishing a batch immediately hides it from public API endpoints
- Only Super Admin and National Admin can publish/unpublish batches

---

### 11. Close Applications

Close applications early for a batch.

```http
POST /api/admin/batches/{batchId}/close-applications/
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "reason": "Applications closed early due to high demand",
  "send_notification": true
}
```

**Response:** 200 OK
```json
{
  "message": "Applications closed successfully",
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "previous_deadline": "2026-01-26",
  "new_deadline": "2025-12-16",
  "notifications_sent": true
}
```

---

### 12. Extend Deadline

Extend the application deadline for a batch.

```http
POST /api/admin/batches/{batchId}/extend-deadline/
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "new_deadline": "2026-02-28",
  "reason": "Extending deadline to allow more applications",
  "send_notification": true
}
```

**Response:** 200 OK
```json
{
  "message": "Deadline extended successfully",
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "previous_deadline": "2026-01-26",
  "new_deadline": "2026-02-28",
  "days_extended": 33,
  "notifications_sent": true
}
```

---

### 13. Get Batch Participants

Get list of participants/applicants for a batch.

```http
GET /api/admin/batches/{batchId}/participants/
Authorization: Bearer {jwt_token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by application status |
| `region` | string | Filter by region |
| `page` | integer | Page number |
| `page_size` | integer | Items per page |

**Example Request:**
```bash
curl -X GET "https://pms.alphalogictech.com/api/admin/batches/550e8400-e29b-41d4-a716-446655440000/participants/?status=approved&page=1" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:** 200 OK
```json
{
  "batch": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "batch_code": "YEA-2025-C1",
    "batch_name": "YEA Poultry Program 2025 - Cohort 1"
  },
  "count": 1,
  "page": 1,
  "page_size": 20,
  "participants": [
    {
      "application_id": "app-uuid",
      "application_number": "PROG-2025-00001",
      "applicant": {
        "id": "user-uuid",
        "full_name": "John Doe",
        "email": "john@example.com",
        "phone": "+233241234567"
      },
      "farm": {
        "id": "farm-uuid",
        "farm_name": "Doe Farms",
        "primary_region": "Greater Accra",
        "primary_constituency": "Tema East"
      },
      "status": "approved",
      "application_date": "2025-11-28T10:00:00Z",
      "approval_date": "2025-12-01T14:30:00Z",
      "enrollment_completed": false
    }
  ]
}
```

---

### 14. Get Batch Statistics

Get comprehensive statistics for a batch.

```http
GET /api/admin/batches/{batchId}/statistics/
Authorization: Bearer {jwt_token}
```

**Example Request:**
```bash
curl -X GET "https://pms.alphalogictech.com/api/admin/batches/550e8400-e29b-41d4-a716-446655440000/statistics/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:** 200 OK
```json
{
  "batch": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "batch_code": "YEA-2025-C1",
    "batch_name": "YEA Poultry Program 2025 - Cohort 1"
  },
  "overview": {
    "total_applications": 50,
    "approved": 30,
    "rejected": 5,
    "pending": 15,
    "withdrawn": 0,
    "enrolled": 25,
    "approval_rate": 60.0,
    "enrollment_rate": 83.3
  },
  "slot_utilization": {
    "total_slots": 100,
    "filled_slots": 30,
    "available_slots": 70,
    "utilization_percentage": 30.0
  },
  "regional_breakdown": [
    {
      "region": "Greater Accra",
      "applications": 30,
      "approved": 20,
      "rejected": 3,
      "pending": 7,
      "slots_allocated": 50,
      "slots_filled": 20,
      "slots_available": 30
    }
  ],
  "timeline": {
    "applications_by_month": {
      "2025-11": 20,
      "2025-12": 30
    },
    "approvals_by_month": {
      "2025-12": 30
    }
  },
  "avg_review_time_days": 5.2,
  "generated_at": "2025-12-16T20:50:00Z"
}
```

---

### 15. Duplicate Batch

Create a copy of an existing batch.

```http
POST /api/admin/batches/{batchId}/duplicate/
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "new_batch_code": "YEA-2026-C2",
  "new_batch_name": "YEA Poultry Program 2026 - Cohort 2",
  "adjust_dates": true,
  "date_offset_days": 365
}
```

**Response:** 201 Created
```json
{
  "message": "Batch duplicated successfully",
  "original_batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "new_batch_id": "new-batch-uuid",
  "new_batch_code": "YEA-2026-C2",
  "new_batch_name": "YEA Poultry Program 2026 - Cohort 2"
}
```

---

## 🔒 Permission Matrix

| Operation | Super Admin | National Admin | Regional Admin | Constituency Admin |
|-----------|-------------|----------------|----------------|-------------------|
| List batches | ✅ | ✅ | ✅ (region only) | ✅ (constituency only) |
| View batch detail | ✅ | ✅ | ✅ (region only) | ✅ (constituency only) |
| Create batch | ✅ | ✅ | ❌ | ❌ |
| Update batch | ✅ | ✅ | ❌ | ❌ |
| Delete batch | ✅ | ❌ | ❌ | ❌ |
| Toggle active | ✅ | ✅ | ❌ | ❌ |
| **Toggle publish** | ✅ | ✅ | ❌ | ❌ |
| Close applications | ✅ | ✅ | ❌ | ❌ |
| Extend deadline | ✅ | ✅ | ❌ | ❌ |
| View participants | ✅ | ✅ | ✅ (region only) | ✅ (constituency only) |
| View statistics | ✅ | ✅ | ✅ (region only) | ✅ (constituency only) |
| Duplicate batch | ✅ | ✅ | ❌ | ❌ |

---

## 🚨 Error Codes

| Status Code | Description | Example |
|-------------|-------------|---------|
| `200` | Success | Request completed successfully |
| `201` | Created | Resource created successfully |
| `400` | Bad Request | Missing required fields, validation errors |
| `401` | Unauthorized | Invalid or missing authentication token |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Batch not found or archived |
| `409` | Conflict | Duplicate batch code/name, cannot delete |
| `500` | Server Error | Internal server error |

---

## 🚀 Deployment Guide

### **Prerequisites**
- SSH access to production server (68.66.251.79)
- Git repository access
- Root or sudo privileges

### **Step 1: Verify Current State**

```bash
# SSH to production
ssh root@68.66.251.79

# Check current version
cd /var/www/YEA/PMS/pms-backend
git log --oneline -3
git status
```

### **Step 2: Pull Latest Code**

```bash
# Pull from main branch
git checkout main
git pull origin main

# Verify commit includes fixes
git log --oneline -1
# Should show: "Fix critical batch API issues"
```

### **Step 3: Restart Services**

```bash
# Use restart script
cd /var/www/YEA/PMS/pms-backend
./restart_services.sh

# Or manually restart
sudo systemctl restart gunicorn-pms
sudo systemctl restart nginx
```

### **Step 4: Verify Deployment**

```bash
# Test public endpoint
curl -X GET "http://localhost:8000/api/public/batches/?is_active=true&is_published=true" | jq .

# Should return batch records, not empty results

# Check logs
sudo journalctl -u gunicorn-pms -n 50 --no-pager
```

### **Step 5: Test Admin Endpoints**

```bash
# Get auth token (replace with valid credentials)
TOKEN=$(curl -X POST "http://localhost:8000/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yea.gov.gh","password":"your-password"}' | jq -r .access)

# Test list batches
curl -X GET "http://localhost:8000/api/admin/batches/" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Test toggle active (replace with actual batch ID)
curl -X POST "http://localhost:8000/api/admin/batches/{batch-id}/toggle-active/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active":false,"reason":"Testing"}' | jq .
```

---

## 📊 Testing Checklist

After deployment, verify these operations:

- [ ] Public batch list returns records
- [ ] Admin batch list loads
- [ ] View batch detail works
- [ ] Create new batch works
- [ ] Edit batch (PATCH) works
- [ ] Toggle active/pause works
- [ ] **Toggle publish/unpublish works**
- [ ] Delete batch works (with proper validation)
- [ ] View participants loads
- [ ] View statistics loads
- [ ] Duplicate batch works

---

## 🔧 Troubleshooting

### **Problem: Public batches returning 0 records**

**Possible Causes:**
1. Batch has `is_published=false` (most common)
2. Batch has `is_active=false`
3. No batches exist in database

**Solution:**
```bash
# Check if batches exist and their status
cd /var/www/YEA/PMS/pms-backend
python manage.py shell -c "
from farms.batch_enrollment_models import Batch
batches = Batch.objects.all()
print(f'Total batches: {batches.count()}')
for b in batches:
    print(f'{b.batch_code}: active={b.is_active}, published={b.is_published}, archived={b.archived}')
"

# If batch exists but is_published=false, publish it:
python manage.py shell -c "
from farms.batch_enrollment_models import Batch
batch = Batch.objects.get(batch_code='YEA-0001')  # Replace with your batch code
batch.is_published = True
batch.is_active = True  # Also ensure it's active
batch.save()
print(f'✅ Batch {batch.batch_code} is now published and active!')
"
```

### **Problem: Edit/Delete operations not working**

**Cause:** URL routing conflict (fixed in latest deployment)

**Verify Fix:**
```bash
# Check URL configuration
cd /var/www/YEA/PMS/pms-backend
grep -A 3 "batches/<uuid:batch_id>/" accounts/admin_urls.py
# Should show single combined view, not three separate views
```

### **Problem: 403 Forbidden on admin operations**

**Cause:** Insufficient permissions

**Solution:** Verify user role:
```bash
python manage.py shell -c "
from accounts.models import User
user = User.objects.get(email='your-email@example.com')
print(f'Role: {user.role}')
print(f'Is staff: {user.is_staff}')
"
```

---

## 📝 Change Log

### **Version 1.1 - December 16, 2025**

**Added:**
- ✅ New endpoint: `/api/admin/batches/{batchId}/toggle-publish/` for publish/unpublish control
- ✅ Comprehensive documentation explaining `is_active` vs `is_published` fields
- ✅ Troubleshooting guide for `is_published=false` causing 0 results
- ✅ Updated permission matrix with toggle-publish operation

**Improved:**
- Enhanced understanding of batch visibility workflow
- Clearer examples of when to use each status field
- Better error diagnostics for production issues

**Files Modified:**
- `accounts/batch_action_views.py` - Added AdminBatchTogglePublishView
- `accounts/admin_urls.py` - Added toggle-publish URL route
- `docs/BATCH_API_DOCUMENTATION.md` - Added comprehensive status field guide

### **Version 1.0 - December 16, 2025**

**Fixed:**
- ✅ Public batch query filter on non-existent field
- ✅ Admin CRUD URL routing conflict
- ✅ Edit/Update operations failing
- ✅ Delete operations failing

**Added:**
- Combined view for batch detail/update/delete operations
- Proper property filtering after query execution
- Comprehensive error handling

**Files Modified:**
- `farms/public_views.py`
- `accounts/batch_admin_views.py`
- `accounts/admin_urls.py`

---

## 📞 Support

For technical support or questions about this API:

- **Backend Team Lead:** [Contact Information]
- **Repository:** https://github.com/j-tee/pms-backend
- **Production Server:** 68.66.251.79
- **Development Server:** localhost:8000

---

**Document Version:** 1.1  
**Last Updated:** December 16, 2025  
**Status:** ✅ Production Ready
