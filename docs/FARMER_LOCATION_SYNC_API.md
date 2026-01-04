# Farmer Location Data Sync - Frontend Integration Guide

## Overview

This document describes the API changes that sync farmer location data (Region, District, Constituency) from their farm registration to the User API response. Previously, these fields showed "Not synced from registration" for FARMER users.

## Problem Solved

When viewing/editing a FARMER user in Admin User Management, location fields were empty because:
1. User model didn't have a `district` field
2. Location data wasn't being pulled from the farmer's farm profile or application

## API Changes

### GET /api/admin/users/{user_id}/

The User Detail endpoint now returns computed location fields for FARMER users.

#### New/Updated Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `region` | string \| null | Region name (e.g., "Greater Accra") |
| `district` | string \| null | District name (e.g., "Accra Metropolitan") - **NEW FIELD** |
| `constituency` | string \| null | Constituency name (e.g., "Odododiodio") |
| `farm_id` | uuid \| null | Associated farm UUID (FARMER only) - **NEW FIELD** |
| `farm_name` | string \| null | Associated farm name (FARMER only) - **NEW FIELD** |
| `location_source` | string \| null | Where location data came from - **NEW FIELD** |

#### Location Source Values

| Value | Meaning |
|-------|---------|
| `user_model` | Data stored directly on User record |
| `farm_location` | Data from farm's primary FarmLocation |
| `farm_profile` | Data from Farm.primary_constituency |
| `farm_application` | Data from FarmApplication |
| `null` | No location data available |

### Example Response - FARMER User

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "julius_test",
  "email": "julius@example.com",
  "phone": "+233241234567",
  "first_name": "Julius",
  "last_name": "Test",
  "full_name": "Julius Test",
  "role": "FARMER",
  "role_display": "Farmer",
  "preferred_contact_method": "Phone Call",
  
  "region": "Greater Accra",
  "district": "Accra Metropolitan",
  "constituency": "Odododiodio",
  
  "farm_id": "660e8400-e29b-41d4-a716-446655440001",
  "farm_name": "Julius Poultry Farm",
  "location_source": "farm_location",
  
  "is_verified": true,
  "is_active": true,
  "is_suspended": false,
  "date_joined": "2025-12-15T10:30:00Z",
  "last_login_at": "2026-01-04T08:15:00Z"
}
```

### Example Response - Non-FARMER User (e.g., REGIONAL_COORDINATOR)

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "username": "regional_coord",
  "role": "REGIONAL_COORDINATOR",
  "role_display": "Regional Coordinator",
  
  "region": "Greater Accra",
  "district": null,
  "constituency": null,
  
  "farm_id": null,
  "farm_name": null,
  "location_source": "user_model"
}
```

## Frontend Implementation Notes

### 1. Display Logic for Location Fields

```typescript
interface UserDetail {
  // ... other fields
  region: string | null;
  district: string | null;
  constituency: string | null;
  farm_id: string | null;
  farm_name: string | null;
  location_source: 'user_model' | 'farm_location' | 'farm_profile' | 'farm_application' | null;
}

// Display helper
function getLocationDisplay(user: UserDetail) {
  if (user.location_source) {
    return {
      region: user.region || 'Not specified',
      district: user.district || 'Not specified',
      constituency: user.constituency || 'Not specified',
      synced: true,
      source: user.location_source
    };
  }
  return {
    region: 'Not available',
    district: 'Not available', 
    constituency: 'Not available',
    synced: false,
    source: null
  };
}
```

### 2. Location Source Badge (Optional UI Enhancement)

You may want to show a badge indicating where the data comes from:

```tsx
function LocationSourceBadge({ source }: { source: string | null }) {
  if (!source) return <Badge variant="warning">No Data</Badge>;
  
  const labels = {
    'user_model': 'User Profile',
    'farm_location': 'Farm Location',
    'farm_profile': 'Farm Profile',
    'farm_application': 'Application'
  };
  
  return <Badge variant="info">{labels[source] || source}</Badge>;
}
```

### 3. Farm Link for FARMER Users

Since we now return `farm_id` and `farm_name`, you can link to the farm detail:

```tsx
{user.role === 'FARMER' && user.farm_id && (
  <Link to={`/admin/farms/${user.farm_id}`}>
    {user.farm_name || 'View Farm'}
  </Link>
)}
```

### 4. Handling Missing Location Data

For farmers without location data (rare edge case):

```tsx
{user.role === 'FARMER' && !user.location_source && (
  <Alert variant="warning">
    Location data not available. The farmer may not have completed registration.
  </Alert>
)}
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Location Data Sources                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐ │
│  │ FarmLocation │ ──▶ │    Farm      │ ──▶ │ FarmApplication  │ │
│  │ (Primary)    │     │ (Fallback)   │     │ (Last Resort)    │ │
│  └──────────────┘     └──────────────┘     └──────────────────┘ │
│         │                    │                      │            │
│         ▼                    ▼                      ▼            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              UserDetailSerializer                           ││
│  │  - Checks FarmLocation.is_primary_location=True first       ││
│  │  - Falls back to Farm.primary_constituency                  ││
│  │  - Falls back to FarmApplication                            ││
│  │  - Returns location_source indicating data origin           ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   API Response                              ││
│  │  { region, district, constituency, location_source, ... }  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## When Location Data is Synced

1. **On Farm Approval**: When an application is finally approved (`POST /api/admin/applications/{id}/approve/`), location data is automatically synced to the User model.

2. **Existing Farmers**: A backfill was run for existing farmers. All current FARMER users now have synced location data.

3. **Real-time Computation**: Even if User model fields are empty, the serializer computes location from farm data on every request.

## Testing

### Verify Location Sync

```bash
# Get a FARMER user
curl -X GET /api/admin/users/{farmer_user_id}/ \
  -H "Authorization: Bearer {token}"

# Expected: region, district, constituency populated
# Expected: location_source = "farm_location" or similar
```

### Verify Non-Farmer Behavior

```bash
# Get a staff user (e.g., REGIONAL_COORDINATOR)
curl -X GET /api/admin/users/{staff_user_id}/ \
  -H "Authorization: Bearer {token}"

# Expected: farm_id = null, farm_name = null
# Expected: location_source = "user_model" (if they have region set)
```

## Backward Compatibility

- All existing API contracts are preserved
- New fields are additive (no breaking changes)
- `region` and `constituency` fields existed before but are now computed for farmers
- `district` is a new field (was missing from User model)

## Questions?

Contact the backend team for any clarification on these API changes.
