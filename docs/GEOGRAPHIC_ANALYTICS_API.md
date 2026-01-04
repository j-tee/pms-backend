# Geographic Analytics API Documentation

> **Version:** 1.0  
> **Last Updated:** January 4, 2026  
> **Status:** ✅ Implemented | 🚧 Planned | ❌ Not Implementing

## Overview

This document provides comprehensive API documentation for the geographic analytics endpoints, including what has been implemented, what matches the frontend team's requirements, and any gaps or differences.

---

## Implementation Status Summary

| Feature | Frontend Request | Status | Notes |
|---------|------------------|--------|-------|
| Geographic Breakdown | ✅ | ✅ Implemented | Available at `/geographic/breakdown/` |
| Mortality Breakdown | ✅ | ✅ Implemented | Includes trends and risk levels |
| Production Comparison | ✅ | ✅ Implemented | Rankings with statistics |
| Farm Performance Ranking | ✅ | ✅ Implemented | Individual farm rankings |
| Geographic Hierarchy | ✅ | ✅ Implemented | Drill-down navigation structure |
| Drill-down Endpoint | ✅ | ✅ Use hierarchy + filters | Combine hierarchy with parent filter |
| Mortality Causes | ✅ | 🚧 Future | Requires DailyProduction model enhancement |
| Weekly Breakdown | ✅ | 🚧 Future | Can be added |
| Alerts System | ✅ | 🚧 Future | High-mortality alerts |
| Percentile Rankings | ✅ | 🚧 Future | Can be added to comparison |
| Geographic Filters on Existing Endpoints | ✅ | ❌ Use dedicated endpoints | Use geographic endpoints instead |

---

## Base URL

```
/api/admin/analytics/geographic/
```

**Authentication:** Bearer token (JWT)  
**Required Role:** YEA_OFFICIAL, NATIONAL_ADMIN, REGIONAL_COORDINATOR, or SUPER_ADMIN

---

## Endpoints

### 1. Geographic Breakdown

**Endpoint:** `GET /api/admin/analytics/geographic/breakdown/`

Provides comprehensive metrics breakdown by geographic level (region, district, or constituency).

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `level` | string | No | `region` | Geographic level: `region`, `district`, `constituency` |
| `parent` | string | No | null | Parent filter for drill-down (e.g., region name when level=district) |
| `days` | integer | No | 30 | Period in days for production data |

#### Request Examples

```bash
# Get all regions
GET /api/admin/analytics/geographic/breakdown/?level=region&days=30

# Get districts within Greater Accra
GET /api/admin/analytics/geographic/breakdown/?level=district&parent=Greater Accra&days=30

# Get constituencies within Accra Metropolitan
GET /api/admin/analytics/geographic/breakdown/?level=constituency&parent=Accra Metropolitan&days=30
```

#### Response

```json
{
  "level": "region",
  "parent_filter": null,
  "period_days": 30,
  "data": [
    {
      "name": "Greater Accra",
      "level": "region",
      "farms": 45,
      "farmers": 42,
      "total_birds": 125000,
      "eggs_produced": 2500000,
      "good_eggs": 2375000,
      "mortality_count": 1250,
      "mortality_rate": 1.0,
      "avg_production_rate": 85.5,
      "period_days": 30
    },
    {
      "name": "Ashanti",
      "level": "region",
      "farms": 38,
      "farmers": 35,
      "total_birds": 98000,
      "eggs_produced": 1850000,
      "good_eggs": 1757500,
      "mortality_count": 980,
      "mortality_rate": 1.0,
      "avg_production_rate": 82.3,
      "period_days": 30
    }
  ],
  "summary": {
    "total_locations": 16,
    "total_farms": 156,
    "total_birds": 450000,
    "total_eggs": 8500000,
    "total_mortality": 5400
  }
}
```

#### Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Geographic unit name |
| `level` | string | Geographic level |
| `farms` | integer | Number of farms in this area |
| `farmers` | integer | Number of unique farmers |
| `total_birds` | integer | Current bird population |
| `eggs_produced` | integer | Total eggs collected in period |
| `good_eggs` | integer | Grade A eggs collected |
| `mortality_count` | integer | Birds died in period |
| `mortality_rate` | float | Mortality rate as percentage |
| `avg_production_rate` | float | Average production rate percentage |

---

### 2. Mortality Breakdown

**Endpoint:** `GET /api/admin/analytics/geographic/mortality/`

Detailed mortality analysis with trends and risk classification.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `level` | string | No | `region` | Geographic level |
| `parent` | string | No | null | Parent filter for drill-down |
| `days` | integer | No | 30 | Current period days |
| `comparison_days` | integer | No | 30 | Previous period for trend comparison |

#### Request Examples

```bash
# Regional mortality with 30-day trend
GET /api/admin/analytics/geographic/mortality/?level=region&days=30

# District mortality within Ashanti
GET /api/admin/analytics/geographic/mortality/?level=district&parent=Ashanti&days=30&comparison_days=30
```

#### Response

```json
{
  "level": "region",
  "parent_filter": null,
  "data": [
    {
      "name": "Northern",
      "level": "region",
      "total_birds": 45000,
      "current_period": {
        "mortality_count": 2250,
        "mortality_rate": 5.0,
        "days": 30
      },
      "previous_period": {
        "mortality_count": 1800,
        "mortality_rate": 4.0,
        "days": 30
      },
      "trend": {
        "direction": "up",
        "change_percent": 25.0,
        "is_improving": false
      },
      "risk_level": "critical"
    },
    {
      "name": "Greater Accra",
      "level": "region",
      "total_birds": 125000,
      "current_period": {
        "mortality_count": 1250,
        "mortality_rate": 1.0,
        "days": 30
      },
      "previous_period": {
        "mortality_count": 1500,
        "mortality_rate": 1.2,
        "days": 30
      },
      "trend": {
        "direction": "down",
        "change_percent": -16.7,
        "is_improving": true
      },
      "risk_level": "medium"
    }
  ],
  "summary": {
    "total_locations": 16,
    "current_total_mortality": 5400,
    "previous_total_mortality": 5100,
    "overall_trend": "worsening",
    "critical_areas": 2,
    "high_risk_areas": 3
  }
}
```

#### Risk Level Classification

| Risk Level | Mortality Rate | Color Suggestion |
|------------|---------------|------------------|
| `low` | < 1% | 🟢 Green |
| `medium` | 1% - 2.99% | 🟡 Yellow |
| `high` | 3% - 4.99% | 🟠 Orange |
| `critical` | ≥ 5% | 🔴 Red |

---

### 3. Production Comparison

**Endpoint:** `GET /api/admin/analytics/geographic/comparison/`

Compare production metrics across geographic units with rankings.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `level` | string | No | `region` | Geographic level |
| `parent` | string | No | null | Parent filter for drill-down |
| `days` | integer | No | 30 | Period for data |
| `metric` | string | No | `eggs` | Ranking metric: `eggs`, `mortality`, `production_rate`, `birds`, `farms` |

#### Request Examples

```bash
# Rank regions by eggs produced
GET /api/admin/analytics/geographic/comparison/?level=region&metric=eggs&days=30

# Rank districts in Greater Accra by production rate
GET /api/admin/analytics/geographic/comparison/?level=district&parent=Greater Accra&metric=production_rate

# Rank regions by mortality (lower is better)
GET /api/admin/analytics/geographic/comparison/?level=region&metric=mortality
```

#### Response

```json
{
  "level": "region",
  "parent_filter": null,
  "metric": "eggs",
  "period_days": 30,
  "data": [
    {
      "name": "Greater Accra",
      "level": "region",
      "farms": 45,
      "farmers": 42,
      "total_birds": 125000,
      "eggs_produced": 2500000,
      "good_eggs": 2375000,
      "mortality_count": 1250,
      "mortality_rate": 1.0,
      "avg_production_rate": 85.5,
      "period_days": 30,
      "rank": 1
    },
    {
      "name": "Ashanti",
      "level": "region",
      "farms": 38,
      "farmers": 35,
      "total_birds": 98000,
      "eggs_produced": 1850000,
      "good_eggs": 1757500,
      "mortality_count": 980,
      "mortality_rate": 1.0,
      "avg_production_rate": 82.3,
      "period_days": 30,
      "rank": 2
    }
  ],
  "statistics": {
    "average": 531250.0,
    "highest": 2500000,
    "lowest": 125000,
    "top_performer": "Greater Accra",
    "bottom_performer": "Upper East"
  }
}
```

---

### 4. Farm Performance Ranking

**Endpoint:** `GET /api/admin/analytics/geographic/farms/`

Individual farm rankings with geographic filtering.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `region` | string | No | null | Filter by region |
| `district` | string | No | null | Filter by district |
| `constituency` | string | No | null | Filter by constituency |
| `metric` | string | No | `eggs` | Ranking metric: `eggs`, `production_rate`, `mortality`, `birds` |
| `days` | integer | No | 30 | Period for data |
| `limit` | integer | No | 50 | Maximum farms to return |

#### Request Examples

```bash
# Top 50 farms nationally by eggs
GET /api/admin/analytics/geographic/farms/?metric=eggs&days=30&limit=50

# Top farms in Greater Accra by production rate
GET /api/admin/analytics/geographic/farms/?region=Greater Accra&metric=production_rate

# Farms with lowest mortality in Ashanti
GET /api/admin/analytics/geographic/farms/?region=Ashanti&metric=mortality&limit=20

# Farms in specific constituency
GET /api/admin/analytics/geographic/farms/?constituency=Ablekuma South&metric=eggs
```

#### Response

```json
{
  "filters": {
    "region": "Greater Accra",
    "district": null,
    "constituency": null
  },
  "metric": "eggs",
  "period_days": 30,
  "total_farms": 45,
  "data": [
    {
      "farm_id": "2e21468e-da22-4549-875b-12f50f286e66",
      "farm_name": "Alpha Farms",
      "region": "Greater Accra",
      "district": "Accra Metropolitan",
      "constituency": "Odododiodio",
      "total_birds": 15000,
      "eggs_produced": 285000,
      "good_eggs": 270750,
      "mortality_count": 75,
      "mortality_rate": 0.5,
      "avg_production_rate": 92.5,
      "days_recorded": 28,
      "rank": 1
    },
    {
      "farm_id": "3f32579f-eb33-4650-986c-23f61397f77",
      "farm_name": "Sunrise Poultry",
      "region": "Greater Accra",
      "district": "Tema Metropolitan",
      "constituency": "Tema Central",
      "total_birds": 12000,
      "eggs_produced": 216000,
      "good_eggs": 205200,
      "mortality_count": 60,
      "mortality_rate": 0.5,
      "avg_production_rate": 88.3,
      "days_recorded": 30,
      "rank": 2
    }
  ]
}
```

---

### 5. Geographic Hierarchy

**Endpoint:** `GET /api/admin/analytics/geographic/hierarchy/`

Get the complete geographic hierarchy for building drill-down navigation.

#### Request

```bash
GET /api/admin/analytics/geographic/hierarchy/
```

#### Response

```json
{
  "regions": [
    {
      "name": "Greater Accra",
      "farm_count": 45,
      "districts": [
        {
          "name": "Accra Metropolitan",
          "farm_count": 15,
          "constituencies": [
            "Ablekuma Central",
            "Ablekuma North",
            "Ablekuma South",
            "Ablekuma West",
            "Odododiodio"
          ]
        },
        {
          "name": "Tema Metropolitan",
          "farm_count": 12,
          "constituencies": [
            "Tema Central",
            "Tema East",
            "Tema West"
          ]
        }
      ]
    },
    {
      "name": "Ashanti",
      "farm_count": 38,
      "districts": [
        {
          "name": "Kumasi Metropolitan",
          "farm_count": 18,
          "constituencies": [
            "Bantama",
            "Manhyia North",
            "Manhyia South",
            "Subin"
          ]
        }
      ]
    }
  ],
  "total_regions": 16,
  "total_districts": 261,
  "total_constituencies": 275
}
```

---

## Drill-Down Pattern

The frontend team requested a dedicated drill-down endpoint. Instead, the same functionality is achieved by combining the **hierarchy endpoint** with **parent filters**:

### Step 1: Get Regions
```bash
GET /api/admin/analytics/geographic/breakdown/?level=region
```

### Step 2: Click on Region → Get Districts
```bash
GET /api/admin/analytics/geographic/breakdown/?level=district&parent=Greater Accra
```

### Step 3: Click on District → Get Constituencies
```bash
GET /api/admin/analytics/geographic/breakdown/?level=constituency&parent=Accra Metropolitan
```

### Step 4: Click on Constituency → Get Farms
```bash
GET /api/admin/analytics/geographic/farms/?constituency=Ablekuma South
```

This pattern works for all geographic endpoints (breakdown, mortality, comparison).

---

## Frontend Integration Guide

### 1. GeographicFilter Component

Use the hierarchy endpoint to populate cascading dropdowns:

```javascript
// Fetch hierarchy once on component mount
const hierarchy = await fetch('/api/admin/analytics/geographic/hierarchy/');

// Region dropdown options
const regions = hierarchy.regions.map(r => ({ value: r.name, label: r.name }));

// District dropdown - filter based on selected region
const getDistricts = (regionName) => {
  const region = hierarchy.regions.find(r => r.name === regionName);
  return region?.districts.map(d => ({ value: d.name, label: d.name })) || [];
};

// Constituency dropdown - filter based on selected district
const getConstituencies = (regionName, districtName) => {
  const region = hierarchy.regions.find(r => r.name === regionName);
  const district = region?.districts.find(d => d.name === districtName);
  return district?.constituencies.map(c => ({ value: c, label: c })) || [];
};
```

### 2. Mortality Heatmap Colors

```javascript
const getRiskColor = (riskLevel) => {
  const colors = {
    'low': '#22c55e',      // Green
    'medium': '#eab308',   // Yellow
    'high': '#f97316',     // Orange
    'critical': '#ef4444'  // Red
  };
  return colors[riskLevel] || '#6b7280';
};
```

### 3. Trend Indicators

```javascript
const TrendIndicator = ({ trend }) => {
  const { direction, change_percent, is_improving } = trend;
  
  const icon = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→';
  const color = is_improving ? 'text-green-500' : 'text-red-500';
  
  return (
    <span className={color}>
      {icon} {Math.abs(change_percent)}%
    </span>
  );
};
```

### 4. Breadcrumb Navigation

```javascript
const DrilldownBreadcrumb = ({ region, district, constituency, onNavigate }) => (
  <nav className="flex items-center space-x-2">
    <button onClick={() => onNavigate(null, null, null)}>All Regions</button>
    {region && (
      <>
        <span>/</span>
        <button onClick={() => onNavigate(region, null, null)}>{region}</button>
      </>
    )}
    {district && (
      <>
        <span>/</span>
        <button onClick={() => onNavigate(region, district, null)}>{district}</button>
      </>
    )}
    {constituency && (
      <>
        <span>/</span>
        <span>{constituency}</span>
      </>
    )}
  </nav>
);
```

---

## Planned Enhancements (Future)

### 1. Mortality Causes Breakdown

**Status:** 🚧 Requires DailyProduction model enhancement

The current `DailyProduction` model has `mortality_reason` as a text field. To support cause-based breakdown, we need:

```python
# Proposed model enhancement
class DailyProduction:
    MORTALITY_CAUSES = [
        ('disease', 'Disease'),
        ('predation', 'Predation'),
        ('heat_stress', 'Heat Stress'),
        ('dehydration', 'Dehydration'),
        ('unknown', 'Unknown'),
    ]
    mortality_cause = models.CharField(choices=MORTALITY_CAUSES, ...)
```

**Future Response Addition:**
```json
{
  "causes": {
    "disease": 450,
    "predation": 120,
    "heat_stress": 280,
    "unknown": 400
  }
}
```

### 2. Weekly Breakdown

**Status:** 🚧 Can be implemented

```json
{
  "weekly_breakdown": [
    {"week": "2025-W49", "count": 280, "rate": 0.9},
    {"week": "2025-W50", "count": 320, "rate": 1.0},
    {"week": "2025-W51", "count": 350, "rate": 1.1},
    {"week": "2025-W52", "count": 300, "rate": 1.0}
  ]
}
```

### 3. High Mortality Alerts

**Status:** 🚧 Can be implemented

```json
{
  "alerts": [
    {
      "level": "critical",
      "location": "Ashanti > Kumasi > Bantama",
      "farm_id": "uuid",
      "farm_name": "Troubled Farm",
      "mortality_rate": 5.2,
      "message": "Mortality rate 5.2% is 4x above regional average"
    }
  ]
}
```

### 4. Percentile Rankings

**Status:** 🚧 Can be added to comparison endpoint

```json
{
  "metrics": {
    "production": {
      "value": 2500000,
      "rank": 1,
      "percentile": 95,
      "vs_average": "+15.2%"
    }
  }
}
```

---

## Differences from Frontend Request

| Frontend Request | Implementation | Reason |
|------------------|----------------|--------|
| `parent_region`, `parent_district`, `parent_constituency` | Single `parent` parameter | Simpler API; level determines what parent means |
| `period`: week/month/quarter/year | `days`: integer | More flexible; 7=week, 30=month, 90=quarter, 365=year |
| `start_date`, `end_date` | `days` (rolling window) | Simpler; can add date range if needed |
| `metric`: production/mortality/farms/applications | Dedicated endpoints | Cleaner separation of concerns |
| Separate drill-down endpoint | Parent filter on all endpoints | More RESTful; same result |
| `include_causes` boolean | Not implemented | Requires model enhancement |
| Location ID (slug) | Location name | Names are already unique within parent |

---

## Error Responses

### Invalid Level
```json
{
  "error": "Invalid level. Use region, district, or constituency"
}
```

### Invalid Metric
```json
{
  "error": "Invalid metric. Use eggs, mortality, production_rate, birds, or farms"
}
```

### Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

---

## Database Indexes

The following indexes are recommended for optimal performance:

```sql
-- FarmLocation indexes
CREATE INDEX idx_farm_location_region ON farms_farmlocation(region);
CREATE INDEX idx_farm_location_district ON farms_farmlocation(district);
CREATE INDEX idx_farm_location_constituency ON farms_farmlocation(constituency);
CREATE INDEX idx_farm_location_primary ON farms_farmlocation(is_primary_location);

-- DailyProduction indexes
CREATE INDEX idx_daily_production_farm_date ON flock_management_dailyproduction(farm_id, production_date);
CREATE INDEX idx_daily_production_date ON flock_management_dailyproduction(production_date);
```

---

## Quick Reference

| Use Case | Endpoint | Key Parameters |
|----------|----------|----------------|
| Regional overview | `/geographic/breakdown/?level=region` | `days` |
| Drill into region | `/geographic/breakdown/?level=district&parent=RegionName` | `days` |
| Mortality hotspots | `/geographic/mortality/?level=region` | `days`, `comparison_days` |
| Compare regions | `/geographic/comparison/?metric=eggs` | `metric`, `days` |
| Top farms | `/geographic/farms/?limit=10` | `metric`, `region`, `limit` |
| Farms in area | `/geographic/farms/?region=X&district=Y` | All filters |
| Dropdown options | `/geographic/hierarchy/` | None |

---

## Changelog

### v1.0 (January 4, 2026)
- ✅ Initial implementation of 5 geographic endpoints
- ✅ Region/district/constituency drill-down support
- ✅ Mortality trends with risk levels
- ✅ Production comparison with rankings
- ✅ Individual farm rankings
- ✅ Geographic hierarchy for navigation
