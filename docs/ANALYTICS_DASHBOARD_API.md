# YEA Admin Analytics Dashboard - API Documentation

## Overview

The Analytics Dashboard provides comprehensive program insights for YEA administrators. Endpoints are geographically filtered based on user role:

| Role | Data Scope |
|------|------------|
| SUPER_ADMIN | National (all data) + Platform Revenue |
| YEA_OFFICIAL | National (all data) + Platform Revenue |
| NATIONAL_ADMIN | National (all data) |
| REGIONAL_COORDINATOR | Region-filtered data |
| CONSTITUENCY_OFFICIAL | Constituency-filtered data |

**Base URL:** `/api/admin/analytics/`

---

## Authentication

All endpoints require JWT authentication:
```
Authorization: Bearer <access_token>
```

---

## YEA Admin Endpoints

### 1. Full Dashboard

**GET** `/api/admin/analytics/`

Returns all analytics data in a single call. Use for initial dashboard load.

**Response:**
```json
{
  "overview": { /* see Overview endpoint */ },
  "application_pipeline": { /* see Program endpoint */ },
  "production": { /* see Production endpoint */ },
  "marketplace": { /* see Marketplace endpoint */ },
  "alerts": { /* see Alerts endpoint */ }
}
```

---

### 2. Executive Overview

**GET** `/api/admin/analytics/overview/`

Quick-loading overview metrics for dashboard cards.

**Response:**
```json
{
  "farmers": {
    "total": 1250,
    "active": 980,
    "new_this_month": 45
  },
  "farms": {
    "total": 1250,
    "approved": 1100,
    "operational": 980,
    "pending_setup": 120
  },
  "birds": {
    "total": 125000,
    "capacity": 200000,
    "utilization_percent": 62.5
  },
  "production": {
    "eggs_this_month": 1250000,
    "good_eggs_this_month": 1187500,
    "mortality_this_month": 1250
  },
  "applications": {
    "pending": 85,
    "submitted": 30,
    "constituency_review": 25,
    "regional_review": 20,
    "national_review": 10
  },
  "marketplace": {
    "orders_this_month": 340,
    "transaction_volume_ghs": 45600.00
  },
  "as_of": "2026-01-04T19:45:00Z"
}
```

---

### 3. Program Metrics

**GET** `/api/admin/analytics/program/`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| months | int | 6 | Number of months for trend data |

**Response:**
```json
{
  "application_pipeline": {
    "pipeline": {
      "Submitted": 30,
      "Constituency Review": 25,
      "Regional Review": 20,
      "National Review": 10,
      "Approved": 1100,
      "Rejected": 50,
      "Account Created": 980
    },
    "summary": {
      "total": 2215,
      "pending": 85,
      "approved": 2080,
      "rejected": 50,
      "approval_rate": 97.6
    }
  },
  "registration_trend": [
    {"month": "2025-08", "registrations": 120},
    {"month": "2025-09", "registrations": 135},
    {"month": "2025-10", "registrations": 110},
    {"month": "2025-11", "registrations": 145},
    {"month": "2025-12", "registrations": 160},
    {"month": "2026-01", "registrations": 45}
  ],
  "farms_by_region": [
    {"region": "Greater Accra", "farm_count": 280},
    {"region": "Ashanti", "farm_count": 245},
    {"region": "Eastern", "farm_count": 180},
    {"region": "Central", "farm_count": 165},
    {"region": "Western", "farm_count": 140}
  ],
  "batch_enrollment": {
    "active_batches": 3,
    "batches": [
      {
        "id": "uuid",
        "name": "2026 Q1 Batch - Greater Accra",
        "target_capacity": 500,
        "approved": 320,
        "pending": 45,
        "fill_rate": 64.0
      }
    ]
  }
}
```

---

### 4. Production Monitoring

**GET** `/api/admin/analytics/production/`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| days | int | 30 | Number of days for trend data |
| limit | int | 10 | Number of farms for top/bottom lists |

**Response:**
```json
{
  "overview": {
    "weekly": {
      "eggs_collected": 312500,
      "good_eggs": 296875,
      "mortality": 312,
      "avg_production_rate": 78.5
    },
    "monthly": {
      "eggs_collected": 1250000,
      "good_eggs": 1187500,
      "mortality": 1250
    },
    "population": {
      "total_birds": 125000,
      "mortality_rate_weekly": 0.25
    }
  },
  "trend": [
    {"date": "2025-12-05", "eggs": 42000, "good_eggs": 39900, "mortality": 42},
    {"date": "2025-12-06", "eggs": 43500, "good_eggs": 41325, "mortality": 38}
  ],
  "by_region": [
    {"region": "Greater Accra", "eggs_this_month": 350000},
    {"region": "Ashanti", "eggs_this_month": 310000},
    {"region": "Eastern", "eggs_this_month": 220000}
  ],
  "top_farms": [
    {
      "farm_id": "uuid",
      "farm_name": "Kofi Poultry Enterprise",
      "constituency": "Ablekuma South",
      "eggs_this_month": 45000,
      "avg_production_rate": 92.5
    }
  ],
  "underperforming": [
    {
      "farm_id": "uuid",
      "farm_name": "Troubled Farm",
      "issue": "High Mortality",
      "mortality_count": 120,
      "mortality_rate": 8.5,
      "eggs_produced": 2500
    }
  ]
}
```

---

### 5. Marketplace Activity

**GET** `/api/admin/analytics/marketplace/`

> **Note:** This shows farmer transaction volume, NOT platform revenue.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Number of top sellers |

**Response:**
```json
{
  "activity": {
    "this_month": {
      "marketplace_orders": 280,
      "marketplace_volume_ghs": 38500.00,
      "guest_orders": 60,
      "guest_volume_ghs": 7100.00,
      "total_orders": 340,
      "total_volume_ghs": 45600.00,
      "avg_order_value_ghs": 134.12
    },
    "sellers": {
      "active_this_month": 145,
      "total_with_products": 320
    },
    "products": {
      "active_listings": 890
    }
  },
  "sales_by_region": [
    {"region": "Greater Accra", "volume_ghs": 18500.00, "order_count": 135},
    {"region": "Ashanti", "volume_ghs": 12300.00, "order_count": 95}
  ],
  "top_sellers": [
    {
      "farm_id": "uuid",
      "farm_name": "Kofi Poultry Enterprise",
      "farmer_name": "Kofi Mensah",
      "sales_volume_ghs": 4500.00,
      "order_count": 32
    }
  ]
}
```

---

### 6. Alerts & Watchlist

**GET** `/api/admin/analytics/alerts/`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 20 | Max watchlist items |

**Response:**
```json
{
  "alerts": {
    "critical": [
      {
        "type": "high_mortality",
        "message": "Troubled Farm has 8.5% mortality rate",
        "farm_id": "uuid"
      }
    ],
    "warning": [
      {
        "type": "aging_applications",
        "message": "12 applications pending review for over 14 days",
        "count": 12
      },
      {
        "type": "inactive_farms",
        "message": "8 operational farms with no production logged in 30 days",
        "count": 8
      }
    ],
    "info": [
      {
        "type": "pending_assignment",
        "message": "30 applications awaiting review assignment",
        "count": 30
      }
    ]
  },
  "watchlist": [
    {
      "farm_id": "uuid",
      "farm_name": "Troubled Farm",
      "reason": "High Mortality",
      "details": "Mortality: 8.5%",
      "severity": "high"
    }
  ]
}
```

---

## Platform Revenue Endpoints (SUPER_ADMIN Only)

These endpoints return platform monetization data and are **only accessible to SUPER_ADMIN and YEA_OFFICIAL** roles.

### 1. Revenue Overview

**GET** `/api/admin/analytics/platform-revenue/`

**Response:**
```json
{
  "advertising": {
    "adsense_this_month": 1250.00,
    "partner_conversions": 45,
    "partner_conversion_value": 3500.00,
    "platform_commission": 700.00,
    "partner_payments_paid": 2100.00,
    "partner_payments_pending": 700.00
  },
  "marketplace_activation": {
    "paid_farms": 280,
    "subsidized_farms": 700,
    "subscription_revenue": 14000.00
  },
  "totals": {
    "ad_revenue_this_month": 4750.00,
    "platform_fees_this_month": 14000.00,
    "net_revenue_estimate": 14700.00
  },
  "as_of": "2026-01-04T19:45:00Z"
}
```

### 2. Revenue Trend

**GET** `/api/admin/analytics/platform-revenue/trend/`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| months | int | 6 | Number of months |

**Response:**
```json
[
  {
    "month": "2025-08",
    "adsense_revenue": 980.00,
    "conversion_revenue": 2800.00,
    "conversion_count": 35,
    "total": 3780.00
  }
]
```

### 3. Advertising Performance

**GET** `/api/admin/analytics/platform-revenue/advertising/`

**Response:**
```json
{
  "summary": {
    "active_offers": 12,
    "clicks_this_month": 4500,
    "conversions_this_month": 45,
    "conversion_rate": 1.0,
    "conversion_value": 3500.00
  },
  "top_offers": [
    {
      "offer_id": "uuid",
      "title": "Premium Feeds Discount",
      "partner": "GhanaFeeds Ltd",
      "conversions": 18,
      "revenue": 1400.00
    }
  ]
}
```

### 4. Partner Payments

**GET** `/api/admin/analytics/platform-revenue/partner-payments/`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| status | string | null | Filter: pending, paid, cancelled |

**Response:**
```json
[
  {
    "id": "uuid",
    "partner": "GhanaFeeds Ltd",
    "amount": 700.00,
    "status": "pending",
    "payment_date": null,
    "created_at": "2026-01-01T10:00:00Z"
  }
]
```

### 5. Marketplace Activation Stats

**GET** `/api/admin/analytics/platform-revenue/activation/`

**Response:**
```json
{
  "breakdown": {
    "none": 170,
    "government_subsidized": 700,
    "standard": 250,
    "verified": 30
  },
  "pricing": {
    "activation_fee_ghs": 50.00
  },
  "revenue": {
    "paying_farms": 280,
    "potential_monthly_ghs": 14000.00
  }
}
```

---

## Frontend Implementation Notes

### Dashboard Cards Layout

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   Total Farmers │   Active Farms  │   Total Birds   │ Eggs This Month │
│      1,250      │       980       │    125,000      │   1,250,000     │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   Pending Apps  │ Capacity Used % │ Transaction Vol │  Orders/Month   │
│       85        │      62.5%      │  GHS 45,600     │       340       │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

### Alert Severity Colors

| Severity | Color | Use For |
|----------|-------|---------|
| critical | Red | High mortality (>5%), system failures |
| warning | Orange/Yellow | Aging applications, inactive farms |
| info | Blue | Pending assignments, general notices |

### Refresh Strategy

- **Overview cards**: Refresh every 5 minutes
- **Charts/trends**: Refresh every 15 minutes or on tab focus
- **Alerts**: Refresh every 2 minutes

### Role-Based UI

```typescript
// Check if user can see platform revenue
const canSeePlatformRevenue = ['SUPER_ADMIN', 'YEA_OFFICIAL'].includes(user.role);

// Show/hide Platform Revenue tab
{canSeePlatformRevenue && <Tab label="Platform Revenue" />}
```

---

## Error Responses

| Status | Meaning |
|--------|---------|
| 401 | Not authenticated |
| 403 | Insufficient permissions |
| 500 | Server error |

```json
{
  "detail": "You do not have permission to perform this action."
}
```
