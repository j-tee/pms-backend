# Frontend Implementation Guide: Step 3 - Location Details
## Farm Application Form

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Step:** 3 of 7  
**Purpose:** Blueprint for building the Location Details step of the apply-first workflow

---

## Table of Contents

1. [Overview](#overview)
2. [Location Data Model](#location-data-model)
3. [API Contract](#api-contract)
4. [Form Sections & Fields](#form-sections--fields)
5. [Validation Rules](#validation-rules)
6. [UI/UX Requirements](#uiux-requirements)
7. [TypeScript Types](#typescript-types)
8. [State Management & Auto-Save](#state-management--auto-save)
9. [GhanaPost Helpers](#ghanapost-helpers)
10. [Error Handling](#error-handling)
11. [Accessibility & Mobile](#accessibility--mobile)
12. [Example Implementation](#example-implementation)
13. [Testing Checklist](#testing-checklist)

---

## Overview

### Role of Step 3

This step captures **where the farm physically operates**. Regulators use this information to:

- Assign applications to the correct **region/district/constituency reviewers**
- Verify land tenure and GPS accuracy
- Drive logistics planning for extension officer visits
- Unlock government support that depends on location (e.g., flood-prone, disease surveillance zones)

At minimum, applicants must provide **one primary location**. Advanced users (multi-site farms) can add additional locations now or later inside the farmer portal.

### Workflow Context

```
Step 1: Introduction ✓
Step 2: Personal Information ✓
Step 3: Location Details ← CURRENT STEP
Step 4: Farm Plans
Step 5: Experience
Step 6: Program Details (government only)
Step 7: Review & Submit
```

### Persistence Rules

- Draft data persists via `POST /api/applications/draft/save/` (same endpoint as earlier steps) with `step: 3`.
- Backend saves location payload into the `FarmLocation` draft serializer + `FarmApplication` linkage.
- Draft auto-save still runs every 30 seconds (same messaging). If users add multiple locations, the entire array is saved.

---

## Location Data Model

The backend expects data that maps to `farms.models.FarmLocation` plus a few form-only helpers:

| Segment | Fields | Notes |
|---------|--------|-------|
| **GPS Details** | `gps_address_string`, `location_source` (always `ghana_post`) | GhanaPost GPS is the single source of truth; backend derives coordinates from the code |
| **Administrative Divisions** | `region`, `district`, `constituency`, `community` | Must match government lists (16 regions, 261 districts, 275 constituencies) |
| **Access & Landmarks** | `nearest_landmark`, `distance_from_main_road_km`, `road_accessibility` | Helps field teams plan visits |
| **Land Information** | `land_size_acres`, `land_ownership_status`, `lease_expiry_date`, `ownership_document_type`, `ownership_document_url` | Lease expiry required for leased/government land |
| **Validation Flags (read-only)** | `is_primary_location`, `gps_verified`, `constituency_match_verified` | Backend calculates flags; front-end displays status badges |

---

## API Contract

### Save Draft (Step 3)

```
POST /api/applications/draft/save/
```

**Headers**

```http
Content-Type: application/json
X-Application-ID: APP-2025-00123
```

**Request Body**

```json
{
  "step": 3,
  "application_type": "government_program",
  "data": {
    "locations": [
      {
        "id": "temp-1",                   // Frontend-generated UUID until backend assigns real ID
        "is_primary": true,                // Exactly one location must be primary
        "gps_address_string": "AK-0123-4567",
        "region": "Greater Accra",
        "district": "Tema Metropolitan",
        "constituency": "Tema East",
        "community": "Community 8",
        "nearest_landmark": "Tema General Hospital",
        "road_accessibility": "All Year",
        "distance_from_main_road_km": 1.2,
        "land_size_acres": "2.50",
        "land_ownership_status": "Leased",
        "lease_expiry_date": "2027-12-31",
        "ownership_document_type": "Lease Agreement",
        "ownership_document_url": "https://example.com/uploads/lease.pdf"
      }
    ]
  }
}
```

> The backend resolves latitude/longitude automatically from the GhanaPost code, so no coordinate fields are submitted by the frontend.

**Successful Response (200)**

```json
{
  "success": true,
  "application_id": "APP-2025-00123",
  "step_completed": 3,
  "next_step": 4,
  "locations_saved": 1,
  "auto_saved": true,
  "last_saved_at": "2025-11-26T16:48:12Z",
  "validation_errors": {}
}
```

**Validation Errors (400)**

```json
{
  "success": false,
  "validation_errors": {
    "locations[0].gps_address_string": ["Invalid GhanaPost GPS format"],
    "locations[0].lease_expiry_date": ["Required when land status is Leased"],
    "locations": ["At least one location must be marked as primary"]
  }
}
```

### Supporting Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/geo/ghana-post/resolve/` | POST | Convert GhanaPost GPS to lat/lon & region/district |
| `/api/geo/regions/` | GET | Static list of 16 regions |
| `/api/geo/districts/?region=Greater%20Accra` | GET | Region-filtered districts |
| `/api/geo/constituencies/?district=Tema%20Metropolitan` | GET | District-filtered constituencies |
| `/api/applications/location/verify/` | POST | Optional background verification (GPS vs constituency) to toggle badge |

> **Note:** Geo reference endpoints already exist for Step 2 constituency dropdown. Reuse caching/local storage to avoid repeated downloads.

---

## Form Sections & Fields

### Section A: GPS Pinpoint

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `gps_address_string` | Text (formatted) | ✓ | Pattern `^[A-Z]{2}-\d{4}-\d{4}$` |
| `location_source` | Hidden | ✓ | Always send `ghana_post`; other entry modes removed |

**UX notes**
- GhanaPost code is the only input. Optionally show a read-only map preview after backend resolution, but do not require users to interact with lat/lon values.
- When GhanaPost code is entered, auto-call `/api/geo/ghana-post/resolve/` then hydrate the rest of the form (region/district/etc.).

### Section B: Administrative Details

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `region` | Async select | ✓ | 16 options fetched from `/api/geo/regions/` |
| `district` | Async select (dependent) | ✓ | Filter by region via `/api/geo/districts/?region=<name>` |
| `constituency` | Async select (dependent) | ✓ | Filter by district via `/api/geo/constituencies/?district=<name>` |
| `community` | Async combobox | ✓ | Allow lookup and creation; 3–120 chars |

**Add/Edit/Update Behavior**

- **Add:** Each select displays a "➕" affordance (as shown in the current UI) that opens a lightweight drawer/modal where users can capture missing administrative entries. Submissions call the shared metadata service (e.g., `/api/geo/custom-communities/`) and on success the new option is injected into the select list without refreshing the page.
- **Edit:** When a location card is reopened, all four fields must preload the previously saved values and replay the dependent dropdown queries so the hierarchy stays intact (region → district → constituency → community). If the user changes a parent field, child selects reset and prompt for re-selection.
- **Update:** Persist changes immediately in the in-memory location object and push them through the normal `saveDraft` payload. The frontend should mark the location card as "Edited" until the next successful save so users know the backend version differs.
- **Validation:** Disallow saving when a user attempts to create a duplicate entry name within the same parent scope (e.g., community names unique within a district). Surface backend validation errors inline.

### Section C: Access & Infrastructure

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `nearest_landmark` | Text | Optional | <= 200 chars |
| `distance_from_main_road_km` | Number | Optional | 0–500, step 0.1 |
| `road_accessibility` | Radio | ✓ | `All Year`, `Dry Season Only`, `Limited` |

### Section D: Land & Tenure

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `land_size_acres` | Decimal | ✓ | > 0, up to 9999.99 |
| `land_ownership_status` | Select | ✓ | `Owned`, `Leased`, `Family Land`, `Government Allocation` |
| `lease_expiry_date` | Date | Conditional | Required for `Leased` or `Government Allocation`; >= today + 6 months |
| `ownership_document_type` | Select | Conditional | `Lease Agreement`, `Indenture`, `Allocation Letter`, `Customary Grant`, `Other` |
| `ownership_document_url` | File URL | Optional | Should reference file uploaded in Step 6 document bucket |

### Section E: Location List

- Display saved locations as cards with status chips (Primary, GPS Verified, Constituency Match Pending).
- Provide “Add Another Location” CTA. Maximum 3 locations during application (configurable via feature flag).
- Each card must expose **Edit** and **Remove** actions. Removing the primary location must prompt the user to select a new primary first.

---

## Validation Rules

### Frontend

1. **GPS Format** – regex `^[A-Z]{2}-\d{4}-\d{4}$` (uppercase). Auto uppercase input.
2. **GhanaPost Validation** – debounce calls to `/api/geo/ghana-post/resolve/` to ensure the code exists before save; show inline error if the lookup fails.
3. **Dependent Selects** – district/constituency cannot be blank once region chosen; reset child selects when parent changes.
4. **Distance** – numeric, 0–500 km. Display inline hint "Use decimals e.g., 1.25 km".
5. **Land Size** – >0 decimal, max 2 decimal places.
6. **Conditional Lease Fields** – show `lease_expiry_date` & document fields only when statuses require them.
7. **Primary Location** – at least one location flagged as primary; only one primary allowed.

### Server-side

Backend repeats the above and adds:
- GhanaPost GPS geofencing (ensures coordinates fall within Ghana). 
- Constituency cross-check (`constituency_match_verified`).
- Duplicate `gps_address_string` prevention per application.

Expose backend errors near the relevant card (e.g., `locations[0].field`).

---

## UI/UX Requirements

1. **Stepper Header** – keep consistent with Step 2 (progress bar showing 3/7).
2. **Map Panel** – optional sticky card that visualizes the resolved GhanaPost code. It is read-only and does not require users to adjust coordinates manually. Use color-coded marker for primary location.
3. **Status Badges** – After save, show badges:
   - `GPS Verified` (green) once backend flag true
   - `Constituency Match Pending` (amber) until verification completes
   - `Primary` (blue) for main site
4. **Add/Edit Flow** – Modal or drawer form for each location to keep main page tidy.
5. **Education Box** – Info alert reminding applicants to download GhanaPost GPS app if they do not know their code (link to Play/App Store).
6. **Auto-Save Banner** – same messaging as Step 2 (“Your progress is automatically saved every 30 seconds”).
7. **Navigation Buttons** – `← Previous` returns to Step 2, `Next →` disabled until at least one valid location exists.

---

## TypeScript Types

```typescript
export type RoadAccessibility = 'All Year' | 'Dry Season Only' | 'Limited';
export type LandOwnershipStatus = 'Owned' | 'Leased' | 'Family Land' | 'Government Allocation';
export type LocationSource = 'ghana_post';

export interface FarmLocationInput {
  id: string; // UUID string (frontend-generated until server returns real ID)
  is_primary: boolean;
  gps_address_string: string;
  location_source?: LocationSource; // default 'ghana_post'
  region: string;
  district: string;
  constituency: string;
  community: string;
  nearest_landmark?: string;
  distance_from_main_road_km?: number | null;
  road_accessibility: RoadAccessibility;
  land_size_acres: string; // keep as string to preserve decimal precision in inputs
  land_ownership_status: LandOwnershipStatus;
  lease_expiry_date?: string | null; // ISO date
  ownership_document_type?: string;
  ownership_document_url?: string;
  gps_verified?: boolean;
  constituency_match_verified?: boolean;
}

export interface LocationStepPayload {
  locations: FarmLocationInput[];
}
```

---

## State Management & Auto-Save

- Reuse the same `useFormContext` or custom step store from Step 2.
- Store unsaved edits in local state (e.g., `locationsDraft`) before pushing to global form state on save.
- Auto-save strategy:
  ```typescript
  useAutoSave({
    interval: 30000,
    data: { locations },
    enabled: locations.length > 0,
    onSave: async (payload) => {
      await saveDraft({ step: 3, data: payload });
    }
  });
  ```
- If the applicant removes all locations, prevent auto-save from sending empty array until they confirm (display warning).

---

## GhanaPost Helpers

```typescript
export async function resolveGhanaPost(code: string) {
  const response = await fetch('/api/geo/ghana-post/resolve/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ gps_address_string: code.trim().toUpperCase() })
  });
  if (!response.ok) throw await response.json();
  return response.json();
}
```

- After saving, optional background job hits `/api/applications/location/verify/` to flip badges. Frontend can poll or rely on next load.
- If the lookup fails (404/422), mark the input invalid and prevent auto-save until the user fixes the code.

---

## Error Handling

1. **Inline Errors** – highlight fields inside the modal/drawer.
2. **Card-Level Errors** – when backend returns `locations[1].field`, map to card index and show summary banner atop that card.
3. **Primary Enforcement** – show blocking toast if user attempts to proceed without a primary location.
4. **Network Failures** – show Retry snackbar. Keep unsent edits in memory.

---

## Accessibility & Mobile

- Each map marker must also be selectable via list view (for keyboard-only users).
- Provide text alternatives for map instructions (ARIA live region announcing coordinate updates).
- Inputs spaced at least 48px high on touch devices; map gestures should not interfere with page scroll (wrap map in `touch-action: pan-y`).

---

## Example Implementation

```tsx
'use client';

import { v4 as uuid } from 'uuid';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAutoSave } from '@/hooks/useAutoSave';
import type { FarmLocationInput } from '@/types/application';

const EMPTY_LOCATION: FarmLocationInput = {
  id: uuid(),
  is_primary: false,
  gps_address_string: '',
  location_source: 'ghana_post',
  region: '',
  district: '',
  constituency: '',
  community: '',
  road_accessibility: 'All Year',
  land_size_acres: '',
  land_ownership_status: 'Owned',
};

export default function LocationStep() {
  const router = useRouter();
  const [locations, setLocations] = useState<FarmLocationInput[]>(loadFromStorage());
  const [activeLocation, setActiveLocation] = useState<FarmLocationInput | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string[]>>({});

  useAutoSave({
    interval: 30000,
    data: { locations },
    enabled: locations.length > 0,
    onSave: async (data) => {
      setIsSaving(true);
      try {
        const response = await saveDraft({ step: 3, data });
        setErrors(response.validation_errors || {});
        persistLocations(data.locations);
      } finally {
        setIsSaving(false);
      }
    },
  });

  const handleAddLocation = () => {
    setActiveLocation({ ...EMPTY_LOCATION, id: uuid(), is_primary: locations.length === 0 });
  };

  const handleSaveLocation = async (location: FarmLocationInput) => {
    const next = upsertLocation(locations, location);
    setLocations(next);
    setActiveLocation(null);
  };

  const handleNext = async () => {
    if (!hasPrimaryLocation(locations)) {
      setErrors({ form: ['Please mark one farm location as primary.'] });
      return;
    }
    const response = await saveDraft({ step: 3, data: { locations }, complete_step: true });
    if (response.success) {
      persistLocations(locations);
      router.push('/apply/step-4');
    } else {
      setErrors(response.validation_errors || {});
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <StepHeader step={3} title="Location Details" description="Tell us exactly where your farm is located." />

      <AutoSaveBanner isSaving={isSaving} lastSavedKey="step3_last_saved" />

      <LocationCards
        locations={locations}
        errors={errors}
        onEdit={setActiveLocation}
        onDelete={(id) => setLocations(locations.filter((loc) => loc.id !== id))}
        onPrimaryChange={(id) => setLocations(markAsPrimary(locations, id))}
      />

      <Button variant="secondary" onClick={handleAddLocation}>
        + Add Another Location
      </Button>

      <div className="flex justify-between border-t pt-6 mt-8">
        <Button variant="outline" onClick={() => router.push('/apply/step-2')}>
          ← Previous
        </Button>
        <Button onClick={handleNext} disabled={locations.length === 0}>
          Next →
        </Button>
      </div>

      {activeLocation && (
        <LocationDrawer
          location={activeLocation}
          onClose={() => setActiveLocation(null)}
          onSave={handleSaveLocation}
        />
      )}
    </div>
  );
}
```

Helper utilities (`upsertLocation`, `markAsPrimary`, `saveDraft`, `persistLocations`) should live alongside other step utilities for reuse/testing.

---

## Testing Checklist

### Functional

- [ ] GhanaPost code auto-fills administrative divisions and validates successfully via `/api/geo/ghana-post/resolve/`
- [ ] Optional map preview centers on the resolved GhanaPost code without requiring manual coordinate entry
- [ ] At least one location required before proceeding
- [ ] Only one location can be primary
- [ ] Conditional lease fields enforced
- [ ] Backend validation errors mapped to correct cards
- [ ] Auto-save occurs every 30 seconds with unsaved changes
- [ ] Removing a location updates auto-save payload

### Cross-Browser

- [ ] Chrome / Firefox / Edge / Safari (desktop)
- [ ] Chrome Android / Safari iOS (map gestures + form inputs)

### Accessibility

- [ ] Map actions are keyboard accessible (list view fallback)
- [ ] ARIA live region announces coordinate updates
- [ ] Error summaries focus the problematic card/modal

### Performance

- [ ] Location lookup requests debounced (250 ms) to avoid rate limits
- [ ] Map component lazy-loaded to keep initial bundle small

---

**Next Step:** Once Step 3 is complete, proceed to [Step 4 – Farm Plans] to capture production and infrastructure details.
