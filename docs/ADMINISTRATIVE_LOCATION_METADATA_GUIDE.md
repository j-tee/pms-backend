# Administrative Location Metadata Guide
## Region → District → Constituency → Community

**Last Updated:** November 26, 2025  
**Applies To:** Farmer onboarding Step 3 – Location Details  
**Audience:** Frontend engineers, backend engineers, product ops

---

## 1. Purpose & Scope

The administrative metadata stack (region, district, constituency, community) powers the Location Details step and several downstream dashboards. This document explains:

- How each level is represented in the backend
- API endpoints for listing, searching, creating, and updating entries
- Frontend interaction patterns (async selects, dependent resets, inline creation)
- Validation, caching, and audit considerations

Use this guide whenever you need to populate dropdowns, allow applicants to add missing communities, or sync new government boundary updates.

---

## 2. Data Hierarchy Overview

```
Region (16 total)
 └─ District (261 total; filtered by region)
     └─ Constituency (275 total; filtered by district)
         └─ Community (open-ended; filtered by constituency/district)
```

Key rules:

- Region, district, and constituency lists come from authoritative MoFA datasets and are read-only for applicants.
- Communities are semi-open: applicants can request additions, but each community must be associated with a parent district and constituency.
- Each `FarmLocation` stores the IDs (or names) for all four levels, so UI edits must keep them in sync.

---

## 3. API Surface

| Operation | Endpoint | Method | Notes |
|-----------|----------|--------|-------|
| List regions | `/api/geo/regions/` | GET | Returns `{ id, name, code }[]` |
| List districts by region | `/api/geo/districts/?region={region_code}` | GET | Returns `{ id, name, code, region_code }[]` |
| List constituencies by district | `/api/geo/constituencies/?district={district_code}` | GET | Returns `{ id, name, code, district_code }[]` |
| Search communities | `/api/geo/communities/?district={district_code}&q={term}` | GET | Paginated, supports `q` for partial matches |
| Create custom community | `/api/geo/communities/` | POST | Restricted to applicants and ops; requires approval flag |
| Update metadata (ops portal) | `/api/geo/communities/{id}/` | PATCH | Ops-only; toggles approval or fixes spelling |

### 3.1 Example Payloads

**Create Community**

```http
POST /api/geo/communities/
Content-Type: application/json
X-Application-ID: APP-2025-00123
```

```json
{
  "name": "Fountain School",
  "district_code": "DA010",
  "constituency_code": "CA022",
  "source": "applicant",
  "submitted_by": "APP-2025-00123",
  "notes": "New peri-urban area along the main road"
}
```

**Response**

```json
{
  "id": "COMM-8842",
  "name": "Fountain School",
  "district_code": "DA010",
  "constituency_code": "CA022",
  "approved": false,
  "approved_by": null,
  "created_at": "2025-11-26T16:32:00Z"
}
```

Frontend should optimistically insert the new community into the combobox with a "Pending Approval" badge.

---

## 4. Frontend Interaction Model

### 4.1 Async Selects

- **Region Select**: loads once on mount. Cache in local storage (`geo_regions_v1`) for 24 hours.
- **District Select**: fetch triggered when region changes. Clear selected district, constituency, and community when region updates.
- **Constituency Select**: fetch triggered when district changes. Clear community selection.
- **Community Combobox**: supports search-as-you-type (debounce 300 ms) within the chosen district/constituency.

### 4.2 Inline Creation Flow

1. User clicks the `➕` icon beside District/Constituency/Community.
2. Modal/drawer opens with parent context pre-filled.
3. Form collects minimal data (`name`, optional `description`).
4. Submit hits the respective create endpoint.
5. On success, the modal closes, toast displays success, and the new entry is injected into the select options.
6. On failure, inline error surfaces (e.g., duplicate name).

> Only communities are applicant-creatable today. The plus icons for region/district/constituency route users to support docs explaining how to request official changes via MoFA.

### 4.3 Editing Existing Locations

- When an applicant edits a saved location card, the app reruns the fetch chain to ensure dropdowns contain the correct values even if metadata changed since the last save.
- Changes are stored in local state immediately and flagged as `isDirty` until `saveDraft` succeeds.
- If a parent value changes, downstream fields reset and show a warning tooltip: "Updating the region clears district, constituency, and community."

### 4.4 Status Indicators

- Newly created communities show `Pending approval` chip until backend `approved=true`.
- Disabled selects display skeleton loaders while fetching.
- Error states show next to the label with backend message (e.g., "Community already exists in this district").

---

## 5. Validation Matrix

| Field | Frontend Validation | Backend Validation |
|-------|---------------------|--------------------|
| Region | Required, must match API list | Same as frontend |
| District | Required, parent region must match | Cross-check region/district relationship |
| Constituency | Required, parent district must match | Cross-check district/constituency relationship |
| Community | Required, 3–120 chars, no emojis | Deduplicate within the same district + slugify |

Backend rejects mismatched parent-child combos with error codes like `invalid_relationship`. Surface these next to the offending field.

---

## 6. Caching & Sync Strategy

- Cache region/district/constituency lists for 24 hours using `localStorage` keys `geo_regions_v1`, `geo_districts_{region}`, etc.
- Communities should not be cached aggressively because additions happen frequently. Store the last search result set for 10 minutes at most.
- Provide a "Refresh list" action that clears caches and refetches; useful when ops pushes new metadata via admin portal.

---

## 7. Ops Review Workflow (Communities)

1. Applicant submits new community.
2. Entry enters `pending` state and is visible to ops dashboard (`/ops/communities`).
3. Ops verifies details, optionally edits spelling, and clicks Approve/Reject.
4. Approval flips `approved=true`, which immediately removes the pending badge for all applicants referencing that community.
5. Rejection notifies the applicant via inbox + banner in Step 3 prompting them to pick an existing community.

Audit fields (`created_by`, `approved_by`, timestamps) are stored for compliance.

---

## 8. Testing Checklist

- [ ] Region select loads 16 entries and caches them.
- [ ] Switching region clears downstream fields and refetches district list.
- [ ] Constituency select respects selected district and prevents mismatched data.
- [ ] Community combobox supports typeahead and displays "Add new" CTA when no matches found.
- [ ] Attempting to add duplicate community shows backend error inline.
- [ ] Pending community displays badge and persists across reloads.
- [ ] Editing an existing location rehydrates dropdowns correctly even after metadata updates.
- [ ] Clearing cache and refetching works via the Refresh action.

---

## 9. Future Enhancements

- Integrate Ghana Post API to auto-suggest community based on GPS code response.
- Allow ops to bulk-import new communities via CSV.
- Add analytics event tracking for missing community submissions to prioritize official updates.

---

For questions reach out to `#pms-admin-geo` Slack channel or consult the ops portal handbook.
