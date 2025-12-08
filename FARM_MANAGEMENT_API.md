# Farm Management API Guide

This guide documents the authenticated endpoints for farmers to manage their farm profiles.

## Authentication
All endpoints require JWT authentication with the `FARMER` role.

```typescript
headers: {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
}
```

## Base URL
```
http://localhost:8000/api/farms/
```

## Endpoints

### 1. Farm Profile

#### Get Farm Profile
```
GET /api/farms/profile/
```

**Response:**
```json
{
  "id": "2e21468e-da22-4549-875b-12f50f286e66",
  "farm_name": "Alpha Farms",
  "farm_id": null,
  "primary_production_type": "Both",
  "total_bird_capacity": 1000,
  "current_bird_count": 0,
  "farm_status": "Pending Setup",
  "application_status": "Approved",
  "primary_constituency": "Odododiodoo",
  "primary_phone": "+233244123456",
  "alternate_phone": "",
  "email": "juliustetteh@gmail.com",
  "residential_address": "123 Main St, Accra",
  "ownership_type": "Sole Proprietorship",
  "tin": "1234567890",
  "business_registration_number": "",
  "number_of_poultry_houses": 1,
  "housing_type": "Deep Litter",
  "total_infrastructure_value_ghs": 0.0,
  "layer_breed": "",
  "broiler_breed": "",
  "planned_production_start_date": "2025-12-05",
  "initial_investment_amount": 0.0,
  "funding_source": ["YEA Program"],
  "monthly_operating_budget": 0.0,
  "expected_monthly_revenue": 0.0,
  "first_name": "Julius",
  "last_name": "Tetteh",
  "middle_name": "",
  "years_in_poultry": 5.0,
  "education_level": "JHS",
  "literacy_level": "Can Read & Write",
  "farming_full_time": true
}
```

#### Update Farm Profile
```
PUT /api/farms/profile/
Content-Type: application/json
```

**Request Body (partial update allowed):**
```json
{
  "alternate_phone": "+233501234567",
  "email": "newemail@example.com",
  "residential_address": "New address",
  "business_registration_number": "BN123456",
  "layer_breed": "Lohmann Brown",
  "broiler_breed": "Ross 308",
  "bank_name": "GCB Bank",
  "account_number": "1234567890",
  "account_name": "Alpha Farms",
  "monthly_operating_budget": 5000.00,
  "expected_monthly_revenue": 8000.00
}
```

**Response:**
```json
{
  "success": true,
  "message": "Farm profile updated successfully"
}
```

**Updatable Fields:**
- Contact: `alternate_phone`, `email`, `residential_address`
- Business: `business_registration_number`
- Production: `layer_breed`, `broiler_breed`
- Banking: `bank_name`, `account_number`, `account_name`, `mobile_money_provider`, `mobile_money_number`
- Financial: `monthly_operating_budget`, `expected_monthly_revenue`

---

### 2. Farm Locations

#### Get All Locations
```
GET /api/farms/locations/
```

**Response:**
```json
[
  {
    "id": "abc-123-def",
    "gps_address_string": "AK-0123-4567",
    "latitude": 5.6037,
    "longitude": -0.1870,
    "region": "Greater Accra",
    "district": "Accra Metro",
    "constituency": "Odododiodoo",
    "community": "James Town",
    "land_size_acres": 2.5,
    "land_ownership_status": "Owned",
    "is_primary_location": true,
    "road_accessibility": "All Year",
    "nearest_landmark": "Near Police Station"
  }
]
```

#### Add New Location
```
POST /api/farms/locations/
Content-Type: application/json
```

**Request Body:**
```json
{
  "gps_address_string": "AK-0123-4567",
  "region": "Greater Accra",
  "district": "Accra Metro",
  "constituency": "Odododiodoo",
  "community": "James Town",
  "land_size_acres": 2.5,
  "land_ownership_status": "Owned",
  "road_accessibility": "All Year",
  "nearest_landmark": "Near Police Station"
}
```

**Required Field:**
- `gps_address_string` - Ghana Post GPS address (e.g., "AK-0123-4567")

**Optional Fields:**
- `region` - Region name
- `district` - District name
- `constituency` - Constituency name
- `community` - Community/village name
- `land_size_acres` - Size of land in acres (default: 0)
- `land_ownership_status` - "Owned", "Leased", "Family Land", or "Government Allocation" (default: "Owned")
- `road_accessibility` - "All Year", "Dry Season Only", or "Limited" (default: "All Year")
- `nearest_landmark` - Nearby landmark for directions

**Note:** The system automatically extracts latitude and longitude from the Ghana Post GPS address. No need to provide coordinates manually.

**Response:**
```json
{
  "success": true,
  "message": "Location added successfully",
  "location_id": "abc-123-def"
}
```

---

### 3. Infrastructure (Poultry Houses)

#### Get All Poultry Houses
```
GET /api/farms/infrastructure/
```

**Response:**
```json
[
  {
    "id": "xyz-789-abc",
    "house_number": "House 1",
    "house_type": "Deep Litter",
    "house_capacity": 500,
    "current_occupancy": 0,
    "length_meters": 20.0,
    "width_meters": 10.0,
    "height_meters": 3.5
  }
]
```

#### Add New Poultry House
```
POST /api/farms/infrastructure/
Content-Type: application/json
```

**Request Body:**
```json
{
  "house_number": "House 2",
  "house_type": "Battery Cage",
  "house_capacity": 1000,
  "current_occupancy": 0,
  "length_meters": 25.0,
  "width_meters": 12.0,
  "height_meters": 4.0
}
```

**House Types:**
- `Deep Litter`
- `Battery Cage`
- `Free Range Shelter`
- `Brooder House`
- `Layer House`
- `Grower House`

**Response:**
```json
{
  "success": true,
  "message": "Poultry house added successfully",
  "house_id": "xyz-789-abc"
}
```

---

### 4. Equipment

#### Get All Equipment
```
GET /api/farms/equipment/
```

**Response:**
```json
[]
```

**Note:** Equipment management to be implemented. Returns empty array for now.

---

### 5. Documents

#### Get All Documents
```
GET /api/farms/documents/
```

**Response:**
```json
[
  {
    "id": "doc-123-xyz",
    "document_type": "Business Registration",
    "document_name": "business_cert.pdf",
    "file_path": "/media/farm_documents/business_cert.pdf",
    "uploaded_at": "2025-12-05T10:30:00Z",
    "status": "pending_verification"
  }
]
```

#### Upload New Document
```
POST /api/farms/documents/
Content-Type: multipart/form-data
```

**Request Body (FormData):**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('document_type', 'Business Registration');
formData.append('document_name', 'business_cert.pdf');
```

**Document Types:**
- `Business Registration`
- `TIN Certificate`
- `Land Title`
- `Lease Agreement`
- `Insurance Policy`
- `Farm Photos`
- `Other`

**Response:**
```json
{
  "success": true,
  "message": "Document uploaded successfully",
  "document_id": "doc-123-xyz"
}
```

---

## Error Responses

### 404 Not Found - No Farm Profile
```json
{
  "error": "No farm found for this user"
}
```

### 401 Unauthorized - No Token
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden - Invalid Token
```json
{
  "detail": "Given token not valid for any token type"
}
```

---

## Frontend Integration Examples

### React/TypeScript Service

```typescript
// services/farmService.ts
import httpClient from './httpClient';

export const farmService = {
  // Get farm profile
  async getProfile() {
    const response = await httpClient.get('/farms/profile/');
    return response.data;
  },

  // Update farm profile
  async updateProfile(data: Partial<FarmProfile>) {
    const response = await httpClient.put('/farms/profile/', data);
    return response.data;
  },

  // Get locations
  async getLocations() {
    const response = await httpClient.get('/farms/locations/');
    return response.data;
  },

  // Add location (only Ghana Post GPS required)
  async addLocation(gpsAddress: string, additionalInfo?: Partial<LocationInfo>) {
    const response = await httpClient.post('/farms/locations/', {
      gps_address_string: gpsAddress,
      ...additionalInfo,
    });
    return response.data;
  },

  // Get infrastructure
  async getInfrastructure() {
    const response = await httpClient.get('/farms/infrastructure/');
    return response.data;
  },

  // Add poultry house
  async addPoultryHouse(house: NewPoultryHouse) {
    const response = await httpClient.post('/farms/infrastructure/', house);
    return response.data;
  },

  // Get documents
  async getDocuments() {
    const response = await httpClient.get('/farms/documents/');
    return response.data;
  },

  // Upload document
  async uploadDocument(file: File, documentType: string, documentName: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    formData.append('document_name', documentName);

    const response = await httpClient.post('/farms/documents/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
```

### React Component Example

```tsx
// components/FarmProfile.tsx
import { useEffect, useState } from 'react';
import { farmService } from '../services/farmService';

export const FarmProfile = () => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadProfile() {
      try {
        const data = await farmService.getProfile();
        setProfile(data);
      } catch (err) {
        console.error('Failed to load farm profile:', err);
        setError(err.response?.data?.error || 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    }

    loadProfile();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!profile) return <div>No farm profile found</div>;

  return (
    <div className="farm-profile">
      <h1>{profile.farm_name}</h1>
      <div className="profile-section">
        <h2>Basic Information</h2>
        <p>Farm ID: {profile.farm_id || 'Pending'}</p>
        <p>Production Type: {profile.primary_production_type}</p>
        <p>Capacity: {profile.total_bird_capacity} birds</p>
        <p>Status: {profile.farm_status}</p>
      </div>
      
      <div className="profile-section">
        <h2>Contact Information</h2>
        <p>Phone: {profile.primary_phone}</p>
        <p>Email: {profile.email}</p>
        <p>Address: {profile.residential_address}</p>
      </div>

      {/* Add edit functionality */}
    </div>
  );
};
```

---

## Testing

You can test the endpoints using curl:

```bash
# Get farm profile
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/farms/profile/

# Update farm profile
curl -X PUT \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "newemail@example.com", "alternate_phone": "+233501234567"}' \
  http://localhost:8000/api/farms/profile/

# Get locations
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/farms/locations/

# Get infrastructure
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/farms/infrastructure/

# Get documents
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/farms/documents/
```

---

## Notes

- All endpoints return JSON responses
- File uploads use `multipart/form-data` content type
- All other requests use `application/json`
- UUIDs are returned as strings
- Dates are in ISO 8601 format (YYYY-MM-DD)
- Timestamps are in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
- Decimal/float values are returned as numbers
- Phone numbers are returned as strings with country code (+233...)

---

## Related Documentation

- **FARMER_DASHBOARD_API.md** - Dashboard overview endpoint
- **FARM_PROFILE_AUTO_CREATION.md** - How farm profiles are created
- **FRONTEND_INTEGRATION_GUIDE.md** - General frontend integration guide
