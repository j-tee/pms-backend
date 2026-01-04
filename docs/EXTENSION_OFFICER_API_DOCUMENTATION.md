# Extension Officer / Field Officer API Documentation

**Date:** January 4, 2026  
**Version:** 1.0  
**Status:** Production Ready  
**Base URL:** `https://pms.alphalogictech.com`

---

## 📋 Overview

This document provides API integration details for the **Extension Officer / Field Officer** module. These endpoints enable field officers to register farmers, manage farms in their jurisdiction, and conduct extension duties.

### Terminology

| Term | Description |
|------|-------------|
| **Field Officer** | Generic term for officers who work in the field |
| **Extension Officer** | Primary field officer role (synonymous with Field Officer) |
| **Veterinary Officer** | Field officer with animal health focus |
| **Constituency Official** | Senior field officer who can assign officers to farms |

All three roles have access to `/api/extension/` endpoints.

---

## 🔐 Authentication

All endpoints require JWT authentication:

```http
Authorization: Bearer {jwt_token}
```

### Role Requirements

| Role | Access Level |
|------|-------------|
| `EXTENSION_OFFICER` | Can register farmers, update assigned farms |
| `VETERINARY_OFFICER` | Same as Extension Officer |
| `CONSTITUENCY_OFFICIAL` | All above + assign officers to farms, manage all farms in constituency |

---

## 📊 Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extension/dashboard/` | GET | Field officer dashboard stats |
| `/api/extension/farms/` | GET | List farms in jurisdiction |
| `/api/extension/farms/{farm_id}/` | GET, PUT | View/update farm details |
| `/api/extension/farms/{farm_id}/assign-officer/` | POST | Assign extension officer |
| `/api/extension/farms/bulk-update/` | POST | Bulk update multiple farms |
| `/api/extension/register-farmer/` | POST | Register new farmer |
| `/api/extension/officers/` | GET | List extension officers |

---

## 1. Dashboard

### GET `/api/extension/dashboard/`

Get an overview of the field officer's workload and stats.

**Response:**
```json
{
    "summary": {
        "total_farms": 45,
        "active_farms": 38,
        "pending_approval": 3,
        "recent_registrations": 8,
        "farms_needing_update": 5
    },
    "recent_visits": [
        {
            "id": "visit-uuid",
            "farm_name": "Alpha Poultry Farm",
            "visit_date": "2026-01-03T10:30:00Z",
            "purpose": "Monthly check-in"
        }
    ],
    "officer": {
        "name": "John Mensah",
        "role": "Extension Officer",
        "constituency": "Ayawaso Central",
        "region": "Greater Accra"
    }
}
```

**Frontend Usage:**
```jsx
function FieldOfficerDashboard() {
    const [stats, setStats] = useState(null);
    
    useEffect(() => {
        fetch('/api/extension/dashboard/', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(data => setStats(data));
    }, []);
    
    return (
        <div>
            <h1>Welcome, {stats?.officer?.name}</h1>
            <StatCard title="Total Farms" value={stats?.summary?.total_farms} />
            <StatCard title="Active Farms" value={stats?.summary?.active_farms} />
            <StatCard title="Pending Approval" value={stats?.summary?.pending_approval} />
            <StatCard title="Recent Registrations" value={stats?.summary?.recent_registrations} />
            <StatCard title="Need Update" value={stats?.summary?.farms_needing_update} color="warning" />
        </div>
    );
}
```

---

## 2. Farm List

### GET `/api/extension/farms/`

List farms in the field officer's jurisdiction.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by farm_status: `Active`, `Inactive`, `Suspended` |
| `application_status` | string | Filter: `Pending`, `Approved`, `Rejected` |
| `search` | string | Search by farm name, farmer name, phone, farm ID |
| `page` | number | Page number (default: 1) |
| `page_size` | number | Items per page (default: 20) |

**Example Request:**
```http
GET /api/extension/farms/?status=Active&search=alpha&page=1
Authorization: Bearer {token}
```

**Response:**
```json
{
    "count": 45,
    "page": 1,
    "page_size": 20,
    "total_pages": 3,
    "results": [
        {
            "id": "farm-uuid",
            "farm_id": "YEA-GAR-2026-0001",
            "farm_name": "Alpha Poultry Farm",
            "farmer_name": "Kwame Asante",
            "farmer_phone": "+233244123456",
            "constituency": "Ayawaso Central",
            "district": "Ayawaso Central Municipal",
            "farm_status": "Active",
            "application_status": "Approved",
            "production_type": "Layers",
            "bird_capacity": 5000,
            "current_birds": 4200,
            "has_extension_officer": true,
            "created_at": "2026-01-01T10:30:00Z",
            "last_updated": "2026-01-03T14:20:00Z"
        }
    ]
}
```

**Frontend Usage:**
```jsx
function FarmList() {
    const [farms, setFarms] = useState([]);
    const [filters, setFilters] = useState({ status: '', search: '' });
    const [page, setPage] = useState(1);
    
    useEffect(() => {
        const params = new URLSearchParams({
            page,
            ...(filters.status && { status: filters.status }),
            ...(filters.search && { search: filters.search }),
        });
        
        fetch(`/api/extension/farms/?${params}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(data => setFarms(data.results));
    }, [filters, page]);
    
    return (
        <DataTable 
            data={farms}
            columns={['farm_name', 'farmer_name', 'farm_status', 'current_birds']}
            onRowClick={(farm) => navigate(`/extension/farms/${farm.id}`)}
        />
    );
}
```

---

## 3. Farm Details

### GET `/api/extension/farms/{farm_id}/`

Get full details of a specific farm.

**Response:**
```json
{
    "id": "farm-uuid",
    "farm_id": "YEA-GAR-2026-0001",
    "farm_name": "Alpha Poultry Farm",
    
    "farmer": {
        "id": "user-uuid",
        "name": "Kwame Asante",
        "phone": "+233244123456",
        "email": "kwame@example.com",
        "ghana_card": "GHA-123456789-0"
    },
    
    "region": "Greater Accra",
    "district": "Ayawaso Central Municipal",
    "constituency": "Ayawaso Central",
    "town": "Dzorwulu",
    "residential_address": "15 Palm Street, Dzorwulu",
    
    "production_type": "Layers",
    "housing_type": "Battery Cage",
    "total_bird_capacity": 5000,
    "current_bird_count": 4200,
    "number_of_poultry_houses": 2,
    
    "farm_status": "Active",
    "application_status": "Approved",
    "is_government_farmer": true,
    
    "monthly_operating_budget": "15000.00",
    "expected_monthly_revenue": "25000.00",
    
    "farm_readiness_score": "85.00",
    "biosecurity_score": "78.50",
    
    "extension_officer": {
        "id": "officer-uuid",
        "name": "John Mensah"
    },
    
    "created_at": "2026-01-01T10:30:00Z",
    "updated_at": "2026-01-03T14:20:00Z"
}
```

---

### PUT `/api/extension/farms/{farm_id}/`

Update farm information.

**Editable Fields (Extension/Vet Officers):**
- `farm_name`
- `current_bird_count`
- `number_of_poultry_houses`
- `total_bird_capacity`
- `housing_type`
- `primary_production_type`
- `monthly_operating_budget`
- `expected_monthly_revenue`
- `residential_address`
- `town`
- `farm_readiness_score`
- `biosecurity_score`

**Additional Fields (Constituency Officials Only):**
- `farm_status`
- `extension_officer` (officer UUID)
- `assigned_extension_officer` (officer UUID)

**Example Request:**
```http
PUT /api/extension/farms/{farm_id}/
Authorization: Bearer {token}
Content-Type: application/json

{
    "current_bird_count": 4500,
    "biosecurity_score": 82.5,
    "farm_readiness_score": 88.0
}
```

**Response:**
```json
{
    "success": true,
    "message": "Farm updated successfully",
    "updated_fields": ["current_bird_count", "biosecurity_score", "farm_readiness_score"]
}
```

**Error Response:**
```json
{
    "error": "Farm not found or access denied",
    "code": "FARM_NOT_FOUND"
}
```

---

## 4. Register Farmer

### POST `/api/extension/register-farmer/`

Register a new farmer on behalf (field registration). Creates user account + farm in one step.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `first_name` | string | ✅ | Farmer's first name |
| `last_name` | string | ✅ | Farmer's last name |
| `phone` | string | ✅ | Phone number (must be unique) |
| `email` | string | ❌ | Email address |
| `ghana_card_number` | string | ❌ | Ghana Card number |
| `farm_name` | string | ✅ | Name of the farm |
| `region` | string | ✅ | Region name |
| `district` | string | ✅ | District name |
| `primary_constituency` | string | ✅ | Constituency name |
| `town` | string | ❌ | Town/village name |
| `residential_address` | string | ❌ | Full address |
| `production_type` | string | ❌ | `Layers`, `Broilers`, `Both` (default: `Layers`) |
| `housing_type` | string | ❌ | `Deep Litter`, `Battery Cage`, etc. |
| `total_bird_capacity` | number | ❌ | Maximum bird capacity |
| `current_bird_count` | number | ❌ | Current number of birds |
| `number_of_poultry_houses` | number | ❌ | Number of poultry houses |
| `is_government_farmer` | boolean | ❌ | Part of YEA program (default: true) |
| `monthly_operating_budget` | decimal | ❌ | Monthly budget in GHS |
| `expected_monthly_revenue` | decimal | ❌ | Expected revenue in GHS |
| `password` | string | ❌ | If not provided, generates temporary |

**Example Request:**
```http
POST /api/extension/register-farmer/
Authorization: Bearer {token}
Content-Type: application/json

{
    "first_name": "Ama",
    "last_name": "Serwaa",
    "phone": "+233244123456",
    "email": "ama@example.com",
    "ghana_card_number": "GHA-987654321-0",
    "farm_name": "Serwaa Poultry Farm",
    "region": "Greater Accra",
    "district": "Ayawaso Central Municipal",
    "primary_constituency": "Ayawaso Central",
    "town": "Dzorwulu",
    "production_type": "Layers",
    "housing_type": "Deep Litter",
    "total_bird_capacity": 2000,
    "current_bird_count": 1500,
    "is_government_farmer": true
}
```

**Success Response:**
```json
{
    "success": true,
    "message": "Farmer registered successfully",
    "farmer": {
        "id": "user-uuid",
        "username": "farmer_a1b2c3d4",
        "name": "Ama Serwaa",
        "phone": "+233244123456"
    },
    "farm": {
        "id": "farm-uuid",
        "farm_id": "YEA-GAR-2026-0045",
        "farm_name": "Serwaa Poultry Farm"
    },
    "temporary_password": "YEA3456!"
}
```

**Note:** If no password is provided, a temporary password is generated using the pattern `YEA{last4digits}!`. The extension officer should communicate this to the farmer.

**Error Responses:**

| Code | Description |
|------|-------------|
| `MISSING_FIELDS` | Required fields not provided |
| `PHONE_EXISTS` | Phone number already registered |
| `GHANA_CARD_EXISTS` | Ghana Card already registered |
| `REGISTRATION_ERROR` | Server error during registration |

**Frontend Implementation:**
```jsx
function RegisterFarmerForm() {
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        phone: '',
        farm_name: '',
        region: '',
        district: '',
        primary_constituency: '',
        production_type: 'Layers',
    });
    const [result, setResult] = useState(null);
    
    const handleSubmit = async (e) => {
        e.preventDefault();
        
        const response = await fetch('/api/extension/register-farmer/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),
        });
        
        const data = await response.json();
        
        if (data.success) {
            setResult(data);
            // Show success modal with temporary password
            showModal({
                title: 'Farmer Registered!',
                content: (
                    <div>
                        <p>Farm ID: {data.farm.farm_id}</p>
                        <p>Username: {data.farmer.username}</p>
                        <p>Temporary Password: <strong>{data.temporary_password}</strong></p>
                        <p className="warning">Please share this password with the farmer.</p>
                    </div>
                )
            });
        } else {
            showError(data.error);
        }
    };
    
    return (
        <form onSubmit={handleSubmit}>
            {/* Form fields */}
        </form>
    );
}
```

---

## 5. Assign Extension Officer

### POST `/api/extension/farms/{farm_id}/assign-officer/`

Assign or reassign an extension officer to a farm.

**Required Role:** `CONSTITUENCY_OFFICIAL` only

**Request Body:**
```json
{
    "officer_id": "officer-uuid"
}
```

**Success Response:**
```json
{
    "success": true,
    "message": "Farm assigned to John Mensah",
    "farm_id": "farm-uuid",
    "officer": {
        "id": "officer-uuid",
        "name": "John Mensah",
        "phone": "+233244111222"
    }
}
```

**Error Responses:**

| Code | Description |
|------|-------------|
| `PERMISSION_DENIED` | Only constituency officials can assign |
| `FARM_NOT_FOUND` | Farm does not exist |
| `JURISDICTION_ERROR` | Farm not in your constituency |
| `OFFICER_NOT_FOUND` | Officer does not exist |
| `INVALID_OFFICER` | User is not an extension/vet officer |

---

## 6. List Extension Officers

### GET `/api/extension/officers/`

List extension/veterinary officers for assignment purposes.

**Required Role:** `CONSTITUENCY_OFFICIAL`, `REGIONAL_COORDINATOR`, `NATIONAL_ADMIN`, or `SUPER_ADMIN`

**Response:**
```json
{
    "count": 5,
    "results": [
        {
            "id": "officer-uuid",
            "name": "John Mensah",
            "role": "EXTENSION_OFFICER",
            "role_display": "Extension Officer",
            "phone": "+233244111222",
            "email": "john@yea.gov.gh",
            "constituency": "Ayawaso Central",
            "assigned_farms_count": 12
        },
        {
            "id": "officer-uuid-2",
            "name": "Mary Adjei",
            "role": "VETERINARY_OFFICER",
            "role_display": "Veterinary Officer",
            "phone": "+233244333444",
            "email": "mary@yea.gov.gh",
            "constituency": "Ayawaso Central",
            "assigned_farms_count": 8
        }
    ]
}
```

**Frontend Usage:**
```jsx
function AssignOfficerModal({ farmId, onClose }) {
    const [officers, setOfficers] = useState([]);
    
    useEffect(() => {
        fetch('/api/extension/officers/', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(data => setOfficers(data.results));
    }, []);
    
    const assignOfficer = async (officerId) => {
        await fetch(`/api/extension/farms/${farmId}/assign-officer/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ officer_id: officerId }),
        });
        onClose();
    };
    
    return (
        <Modal>
            <h3>Select Extension Officer</h3>
            {officers.map(officer => (
                <OfficerCard 
                    key={officer.id}
                    officer={officer}
                    onClick={() => assignOfficer(officer.id)}
                />
            ))}
        </Modal>
    );
}
```

---

## 7. Bulk Update Farms

### POST `/api/extension/farms/bulk-update/`

Update multiple farms at once (useful after field visits).

**Request Body:**
```json
{
    "updates": [
        {
            "farm_id": "farm-uuid-1",
            "current_bird_count": 4500,
            "biosecurity_score": 85.0
        },
        {
            "farm_id": "farm-uuid-2",
            "current_bird_count": 3200,
            "farm_status": "Active"
        },
        {
            "farm_id": "farm-uuid-3",
            "farm_readiness_score": 90.0
        }
    ]
}
```

**Allowed Fields:**
- `current_bird_count`
- `farm_status`
- `biosecurity_score`
- `farm_readiness_score`

**Response:**
```json
{
    "total": 3,
    "successful": 2,
    "failed": 1,
    "results": [
        { "farm_id": "farm-uuid-1", "success": true },
        { "farm_id": "farm-uuid-2", "success": true },
        { "farm_id": "farm-uuid-3", "success": false, "error": "Access denied" }
    ]
}
```

---

## 🎨 UI Components Checklist

### Field Officer Dashboard Page
- [ ] Stats cards (total farms, active, pending, etc.)
- [ ] Recent visits list
- [ ] Quick actions (Register Farmer, View Farms)
- [ ] Officer info display

### Farm List Page
- [ ] Searchable, filterable data table
- [ ] Status badges (Active, Inactive, Pending)
- [ ] Click to view details
- [ ] Pagination

### Farm Detail Page
- [ ] Full farm information display
- [ ] Edit mode for editable fields
- [ ] Farmer contact info
- [ ] Scores display/edit
- [ ] Assign officer button (Constituency Officials only)

### Register Farmer Page/Modal
- [ ] Multi-step form or single form
- [ ] Location dropdowns (Region → District → Constituency)
- [ ] Validation for required fields
- [ ] Success modal with credentials display
- [ ] Copy to clipboard for temporary password

### Officer Assignment Modal
- [ ] List of officers with workload info
- [ ] Click to assign
- [ ] Confirmation dialog

---

## 🔒 Error Handling

```javascript
// Centralized error handler
function handleApiError(response, data) {
    switch (data.code) {
        case 'PERMISSION_DENIED':
            showError('You do not have permission for this action');
            break;
        case 'FARM_NOT_FOUND':
            showError('Farm not found or you do not have access');
            break;
        case 'PHONE_EXISTS':
            showError('This phone number is already registered');
            break;
        case 'GHANA_CARD_EXISTS':
            showError('This Ghana Card is already registered');
            break;
        case 'JURISDICTION_ERROR':
            showError('This farm is not in your constituency');
            break;
        default:
            showError(data.error || 'An error occurred');
    }
}
```

---

## 📱 Mobile Considerations

Field officers often work in the field with limited connectivity:

1. **Offline Support:** Consider caching farm list for offline viewing
2. **Retry Logic:** Implement retry for failed submissions
3. **Form Drafts:** Save registration forms locally before submission
4. **Low Bandwidth:** Minimize data transfer, use pagination

---

## 📞 Support

For API issues:
- Check error response codes
- Verify JWT token is valid
- Ensure correct role permissions

For integration questions:
- Refer to [MARKETPLACE_API_DOCUMENTATION.md](./MARKETPLACE_API_DOCUMENTATION.md)
- Check `.github/copilot-instructions.md` for architecture details
