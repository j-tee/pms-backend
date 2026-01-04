# Egg Production Analytics API Documentation

> **Version:** 1.0  
> **Last Updated:** January 4, 2026  
> **Status:** ✅ Fully Implemented

## Overview

Comprehensive egg production analytics for YEA administrators. These endpoints provide in-depth analysis of egg production including quality breakdown, efficiency metrics, defect analysis, and geographic comparisons.

---

## Base URL

```
/api/admin/analytics/eggs/
```

**Authentication:** Bearer token (JWT)  
**Required Role:** YEA_OFFICIAL, NATIONAL_ADMIN, REGIONAL_COORDINATOR, CONSTITUENCY_OFFICIAL, or SUPER_ADMIN

---

## Endpoints Summary

| Endpoint | Description |
|----------|-------------|
| `/eggs/overview/` | Production overview with quality breakdown |
| `/eggs/trend/` | Time-series production trends |
| `/eggs/quality/` | Quality analysis by geographic level |
| `/eggs/farms/` | Farm-level production rankings |
| `/eggs/efficiency/` | Feed conversion & efficiency metrics |
| `/eggs/defects/` | Defect analysis with recommendations |
| `/eggs/comparison/` | Period-over-period comparison |

---

## 1. Egg Production Overview

**Endpoint:** `GET /api/admin/analytics/eggs/overview/`

Comprehensive overview of egg production with quality breakdown and trends.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Period for analysis |

### Response

```json
{
  "period_days": 30,
  "production": {
    "total_eggs": 2500000,
    "daily_average": 83333,
    "eggs_per_bird_per_day": 0.667,
    "avg_production_rate": 85.5,
    "farms_reporting": 156,
    "days_recorded": 30
  },
  "quality": {
    "good_eggs": 2375000,
    "good_eggs_percent": 95.0,
    "broken_eggs": 25000,
    "broken_eggs_percent": 1.0,
    "dirty_eggs": 50000,
    "dirty_eggs_percent": 2.0,
    "small_eggs": 37500,
    "small_eggs_percent": 1.5,
    "soft_shell_eggs": 12500,
    "soft_shell_eggs_percent": 0.5
  },
  "trends": {
    "production_change_percent": 5.2,
    "production_trend": "up",
    "quality_change_percent": 0.5,
    "quality_trend": "improving",
    "previous_period_eggs": 2376190
  },
  "population": {
    "total_birds": 125000,
    "laying_efficiency": 85.5
  }
}
```

### Key Metrics Explained

| Field | Description |
|-------|-------------|
| `eggs_per_bird_per_day` | Average eggs produced per bird per day |
| `avg_production_rate` | (Eggs collected / bird count) × 100 |
| `good_eggs_percent` | Percentage of Grade A sellable eggs |
| `production_trend` | `up`, `down`, or `stable` vs previous period |
| `quality_trend` | `improving`, `declining`, or `stable` |

---

## 2. Egg Production Trend

**Endpoint:** `GET /api/admin/analytics/eggs/trend/`

Time-series egg production data with quality breakdown.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Period for analysis |
| `granularity` | string | `daily` | `daily`, `weekly`, or `monthly` |

### Response

```json
{
  "period_days": 30,
  "granularity": "daily",
  "data_points": 30,
  "data": [
    {
      "period": "2025-12-05",
      "date": "2025-12-05",
      "total_eggs": 85000,
      "good_eggs": 80750,
      "good_eggs_percent": 95.0,
      "defective_eggs": 4250,
      "breakdown": {
        "broken": 850,
        "dirty": 1700,
        "small": 1275,
        "soft_shell": 425
      },
      "avg_production_rate": 85.2,
      "farms_reporting": 145,
      "moving_avg": 83500
    }
  ]
}
```

### Granularity Options

| Value | Period Format | Use Case |
|-------|--------------|----------|
| `daily` | `YYYY-MM-DD` | Short-term analysis (7-30 days) |
| `weekly` | `YYYY-Www` | Medium-term trends (1-3 months) |
| `monthly` | `YYYY-MM` | Long-term patterns (6-12 months) |

---

## 3. Egg Quality Analysis

**Endpoint:** `GET /api/admin/analytics/eggs/quality/`

Egg quality breakdown by geographic level with rankings.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Period for analysis |
| `level` | string | `region` | `region`, `district`, or `constituency` |
| `parent` | string | null | Parent filter for drill-down |

### Response

```json
{
  "level": "region",
  "parent_filter": null,
  "period_days": 30,
  "data": [
    {
      "name": "Greater Accra",
      "level": "region",
      "total_eggs": 2500000,
      "good_eggs": 2437500,
      "good_eggs_percent": 97.5,
      "defective_eggs": 62500,
      "defective_percent": 2.5,
      "breakdown": {
        "broken": {"count": 12500, "percent": 0.5},
        "dirty": {"count": 25000, "percent": 1.0},
        "small": {"count": 18750, "percent": 0.75},
        "soft_shell": {"count": 6250, "percent": 0.25}
      },
      "quality_rating": "excellent",
      "rank": 1
    }
  ],
  "summary": {
    "total_locations": 16,
    "total_eggs": 8500000,
    "good_eggs": 8075000,
    "overall_quality_percent": 95.0,
    "best_performer": "Greater Accra",
    "worst_performer": "Upper East"
  }
}
```

### Quality Ratings

| Rating | Good Eggs % | Color Suggestion |
|--------|-------------|------------------|
| `excellent` | ≥ 95% | 🟢 Green |
| `good` | 90% - 94.99% | 🔵 Blue |
| `fair` | 80% - 89.99% | 🟡 Yellow |
| `poor` | < 80% | 🔴 Red |

---

## 4. Egg Production by Farm

**Endpoint:** `GET /api/admin/analytics/eggs/farms/`

Individual farm egg production rankings with geographic filtering.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `region` | string | null | Filter by region |
| `district` | string | null | Filter by district |
| `constituency` | string | null | Filter by constituency |
| `metric` | string | `total_eggs` | Ranking metric (see below) |
| `days` | integer | 30 | Period for data |
| `limit` | integer | 50 | Max farms to return |

### Ranking Metrics

| Metric | Description | Best Is |
|--------|-------------|---------|
| `total_eggs` | Total eggs produced | Higher |
| `production_rate` | Average production rate % | Higher |
| `quality` | Good eggs percentage | Higher |
| `efficiency` | Eggs per bird | Higher |
| `daily_average` | Daily egg average | Higher |

### Response

```json
{
  "filters": {
    "region": "Greater Accra",
    "district": null,
    "constituency": null
  },
  "metric": "total_eggs",
  "period_days": 30,
  "total_farms": 45,
  "data": [
    {
      "farm_id": "2e21468e-da22-4549-875b-12f50f286e66",
      "farm_name": "Alpha Farms",
      "region": "Greater Accra",
      "district": "Accra Metropolitan",
      "constituency": "Odododiodio",
      "bird_count": 15000,
      "production": {
        "total_eggs": 285000,
        "daily_average": 9500,
        "eggs_per_bird": 19.0,
        "production_rate": 92.5
      },
      "quality": {
        "good_eggs": 270750,
        "good_percent": 95.0,
        "defective_eggs": 14250,
        "defective_percent": 5.0
      },
      "breakdown": {
        "broken": 2850,
        "dirty": 5700,
        "small": 4275,
        "soft_shell": 1425
      },
      "days_recorded": 30,
      "rank": 1
    }
  ]
}
```

---

## 5. Egg Production Efficiency

**Endpoint:** `GET /api/admin/analytics/eggs/efficiency/`

Efficiency metrics including feed conversion and cost analysis.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Period for analysis |

### Response

```json
{
  "period_days": 30,
  "birds": {
    "total": 450000,
    "layer_flocks": 125,
    "layers": 380000
  },
  "production": {
    "total_eggs": 8500000,
    "good_eggs": 8075000,
    "quality_percent": 95.0,
    "daily_average": 283333,
    "avg_production_rate": 82.3
  },
  "efficiency": {
    "eggs_per_bird_total": 18.89,
    "eggs_per_bird_per_day": 0.63,
    "eggs_per_layer_per_day": 0.74,
    "feed_per_dozen_eggs_kg": 1.85,
    "feed_cost_per_egg_ghs": 0.12,
    "feed_cost_per_dozen_ghs": 1.44
  },
  "feed": {
    "total_consumed_kg": 1310417,
    "total_cost_ghs": 1020000,
    "daily_average_kg": 43680.56
  },
  "rate_distribution": {
    "below_70_percent": {"count": 450, "percent": 10.0},
    "70_to_80_percent": {"count": 1350, "percent": 30.0},
    "80_to_90_percent": {"count": 1800, "percent": 40.0},
    "above_90_percent": {"count": 900, "percent": 20.0}
  },
  "farms_reporting": 156,
  "days_analyzed": 30
}
```

### Key Efficiency Metrics

| Metric | Industry Standard | Description |
|--------|-------------------|-------------|
| `eggs_per_layer_per_day` | 0.70 - 0.85 | Higher = better laying performance |
| `feed_per_dozen_eggs_kg` | 1.5 - 2.0 | Lower = better feed efficiency |
| `feed_cost_per_egg_ghs` | Varies | Lower = better cost efficiency |

---

## 6. Egg Defect Analysis

**Endpoint:** `GET /api/admin/analytics/eggs/defects/`

Detailed defect analysis with trends and actionable recommendations.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Period for analysis |

### Response

```json
{
  "period_days": 30,
  "summary": {
    "total_eggs": 8500000,
    "good_eggs": 8075000,
    "total_defective": 425000,
    "defect_rate": 5.0,
    "quality_rate": 95.0
  },
  "defects": {
    "broken": {
      "count": 85000,
      "rate": 1.0,
      "previous_rate": 1.2,
      "trend": -0.2,
      "improving": true
    },
    "dirty": {
      "count": 170000,
      "rate": 2.0,
      "previous_rate": 1.8,
      "trend": 0.2,
      "improving": false
    },
    "small": {
      "count": 127500,
      "rate": 1.5,
      "previous_rate": 1.5,
      "trend": 0.0,
      "improving": false
    },
    "soft_shell": {
      "count": 42500,
      "rate": 0.5,
      "previous_rate": 0.6,
      "trend": -0.1,
      "improving": true
    }
  },
  "primary_issue": "dirty",
  "recommendations": [
    {
      "issue": "High dirty egg rate",
      "possible_causes": [
        "Infrequent collection",
        "Dirty nesting boxes",
        "Overcrowding"
      ],
      "actions": [
        "Increase collection frequency",
        "Clean nesting boxes regularly",
        "Check stocking density"
      ]
    }
  ],
  "daily_trend": [
    {
      "date": "2025-12-05",
      "total_defects": 14500,
      "defect_rate": 5.1
    }
  ]
}
```

### Defect Types and Causes

| Defect Type | Common Causes | Recommended Actions |
|-------------|---------------|---------------------|
| **Broken** | Rough handling, weak shells, poor collection | Review collection procedures, check calcium |
| **Dirty** | Infrequent collection, dirty nests, overcrowding | Clean nests, increase collection frequency |
| **Small** | Young pullets, nutritional deficiency, stress | Review feed, reduce stressors |
| **Soft Shell** | Calcium deficiency, heat stress, disease, old hens | Supplement calcium, improve ventilation |

---

## 7. Period Comparison

**Endpoint:** `GET /api/admin/analytics/eggs/comparison/`

Compare current period with previous period.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Current period days |
| `compare_days` | integer | 30 | Previous period days |

### Response

```json
{
  "current_period": {
    "start_date": "2025-12-05",
    "end_date": "2026-01-04",
    "days": 30,
    "total_eggs": 8500000,
    "good_eggs": 8075000,
    "quality_percent": 95.0,
    "defective_eggs": 425000,
    "avg_production_rate": 82.3,
    "feed_consumed_kg": 1310417,
    "feed_cost_ghs": 1020000,
    "farms_reporting": 156
  },
  "previous_period": {
    "start_date": "2025-11-05",
    "end_date": "2025-12-04",
    "days": 30,
    "total_eggs": 8100000,
    "good_eggs": 7695000,
    "quality_percent": 95.0,
    "avg_production_rate": 80.5,
    "feed_consumed_kg": 1280000,
    "feed_cost_ghs": 980000
  },
  "changes": {
    "eggs_change": 400000,
    "eggs_change_percent": 4.9,
    "quality_change_percent": 0.0,
    "production_rate_change": 1.8,
    "feed_efficiency_improving": false
  },
  "trends": {
    "production": "up",
    "quality": "stable"
  }
}
```

---

## Frontend Integration Guide

### Dashboard Cards Example

```javascript
// Fetch overview for dashboard cards
const overview = await fetch('/api/admin/analytics/eggs/overview/?days=30');

// Display cards
<DashboardCard 
  title="Total Eggs" 
  value={overview.production.total_eggs.toLocaleString()}
  trend={overview.trends.production_trend}
  change={`${overview.trends.production_change_percent}%`}
/>

<DashboardCard 
  title="Quality Rate" 
  value={`${overview.quality.good_eggs_percent}%`}
  trend={overview.trends.quality_trend}
/>

<DashboardCard 
  title="Daily Average" 
  value={overview.production.daily_average.toLocaleString()}
/>
```

### Quality Breakdown Chart

```javascript
// Pie chart data for egg quality
const qualityData = [
  { name: 'Good Eggs', value: overview.quality.good_eggs, color: '#22c55e' },
  { name: 'Broken', value: overview.quality.broken_eggs, color: '#ef4444' },
  { name: 'Dirty', value: overview.quality.dirty_eggs, color: '#f97316' },
  { name: 'Small', value: overview.quality.small_eggs, color: '#eab308' },
  { name: 'Soft Shell', value: overview.quality.soft_shell_eggs, color: '#a855f7' }
];
```

### Production Rate Distribution

```javascript
// Bar chart for production rate distribution
const efficiency = await fetch('/api/admin/analytics/eggs/efficiency/?days=30');

const rateData = [
  { label: '<70%', value: efficiency.rate_distribution.below_70_percent.percent, color: '#ef4444' },
  { label: '70-80%', value: efficiency.rate_distribution['70_to_80_percent'].percent, color: '#f97316' },
  { label: '80-90%', value: efficiency.rate_distribution['80_to_90_percent'].percent, color: '#22c55e' },
  { label: '>90%', value: efficiency.rate_distribution.above_90_percent.percent, color: '#3b82f6' }
];
```

### Defect Recommendations Display

```javascript
// Display recommendations
const defects = await fetch('/api/admin/analytics/eggs/defects/?days=30');

{defects.recommendations.map(rec => (
  <Alert type="warning" title={rec.issue}>
    <p><strong>Possible Causes:</strong> {rec.possible_causes.join(', ')}</p>
    <p><strong>Actions:</strong></p>
    <ul>
      {rec.actions.map(action => <li>{action}</li>)}
    </ul>
  </Alert>
))}
```

---

## Error Responses

### Invalid Granularity
```json
{
  "error": "Invalid granularity. Use daily, weekly, or monthly"
}
```

### Invalid Level
```json
{
  "error": "Invalid level. Use region, district, or constituency"
}
```

### Invalid Metric
```json
{
  "error": "Invalid metric. Use one of: total_eggs, production_rate, quality, efficiency, daily_average"
}
```

---

## Quick Reference

| Use Case | Endpoint | Key Parameters |
|----------|----------|----------------|
| Dashboard overview | `/eggs/overview/` | `days` |
| Production chart | `/eggs/trend/` | `days`, `granularity` |
| Quality by region | `/eggs/quality/?level=region` | `days`, `level`, `parent` |
| Top farms | `/eggs/farms/?limit=10` | `metric`, `region`, `limit` |
| Feed efficiency | `/eggs/efficiency/` | `days` |
| Problem diagnosis | `/eggs/defects/` | `days` |
| Month comparison | `/eggs/comparison/` | `days`, `compare_days` |

---

## Changelog

### v1.0 (January 4, 2026)
- ✅ Initial implementation of 7 egg production endpoints
- ✅ Quality breakdown with 5 categories
- ✅ Geographic drill-down support
- ✅ Efficiency metrics with feed conversion
- ✅ Automated defect recommendations
- ✅ Period-over-period comparison
- ✅ Production rate distribution analysis
