# Admin Dashboard Overview API

This guide shows how the frontend should consume the admin dashboard overview endpoint.

## Endpoint
- `GET /api/admin/dashboard/overview/`
- Auth required. Allowed roles: `SUPER_ADMIN`, `NATIONAL_ADMIN`, `REGIONAL_COORDINATOR`, `CONSTITUENCY_OFFICIAL` (others get 403).

## Response Shape (superset)
```json
{
  "farms": {
    "total": 0,
    "active": 0,
    "approved": 0,
    "approval_rate": 0.0
  },
  "applications": {
    "total": 0,
    "pending": 0,          // constituency_review + regional_review + national_review
    "approved": 0,
    "rejected": 0,
    "recent_7_days": 0
  },
  "users": {
    "total": 0,
    "active": 0,
    "verified": 0,
    "verification_rate": 0.0
  },
  "pending_actions": {
    "constituency_screening": 0,
    "regional_approval": 0,
    "national_approval": 0,
    "total": 0             // sum of the above
  },
  "pending_applications": [
    {
      "id": "uuid",
      "application_number": "APP-2025-00007",
      "first_name": "Julius",
      "middle_name": "",
      "last_name": "Tetteh",
      "status": "constituency_review",
      "submitted_at": "2025-12-04T19:21:06.598557+00:00",
      "primary_constituency": "Odododiodio",
      "region": "Greater Accra",
      "primary_production_type": "Both",
      "planned_bird_capacity": 1000
    }
  ],
  "approved_applications": [
    {
      "id": "uuid",
      "application_number": "APP-2025-00007",
      "first_name": "Julius",
      "middle_name": "",
      "last_name": "Tetteh",
      "status": "approved",
      "submitted_at": "2025-12-04T19:21:06.598557+00:00",
      "final_approved_at": "2025-12-05T20:52:10.000000+00:00",
      "primary_constituency": "Odododiodio",
      "region": "Greater Accra",
      "primary_production_type": "Both",
      "planned_bird_capacity": 1000
    }
  ],
  "jurisdiction": {
    "level": "NATIONAL_ADMIN",
    "region": "All Regions",
    "constituency": "All Constituencies"
  }
}
```

### Fields the cards should read (minimal set)
- Total Farms: `farms.total`
- Active Users: `users.active`
- Pending Actions: `pending_actions.total` (review statuses only)
- Recent Applications (7d): `applications.recent_7_days`
- Pending Applications table: `pending_applications` array
 - Approved Applications table (management page): `approved_applications` array

## Sample Request (frontend service)
```ts
async function getDashboardOverview() {
  const res = await httpClient.get('/admin/dashboard/overview/');
  return res.data;
}
```

## Sample Response (illustrative)
```json
{
  "farms": { "total": 156, "active": 142 },
  "applications": { "total": 245, "pending": 23, "recent_7_days": 12 },
  "users": { "total": 198, "active": 187 },
  "pending_actions": { "total": 23 },
  "pending_applications": [
    {
      "id": "uuid",
      "application_number": "APP-2025-00007",
      "first_name": "Julius",
      "middle_name": "",
      "last_name": "Tetteh",
      "status": "constituency_review",
      "submitted_at": "2025-12-04T19:21:06.598557+00:00",
      "primary_constituency": "Odododiodio",
      "region": "Greater Accra",
      "primary_production_type": "Both",
      "planned_bird_capacity": 1000
    }
  ]
}
```

## Notes
- Pending is limited to review statuses: `constituency_review`, `regional_review`, `national_review`.
- Jurisdiction: data is auto-scoped for regional/constituency roles; national/super see all.
- Endpoint is already wired via `accounts/admin_urls.py` and included under `api/admin/`.

## Frontend Integration: Approved Applications
- Use `approved_applications` for the Applications Management page (approved tab).
- Each item includes: `application_number`, `first_name`, `middle_name`, `last_name`, `status`, `submitted_at`, `final_approved_at`, `primary_constituency`, `region`, `primary_production_type`, `planned_bird_capacity`.
- Sort order delivered is newest approvals first (`final_approved_at` then `submitted_at`); apply client-side filters/search as needed.
- API call is unchanged: `GET /api/admin/dashboard/overview/`.
