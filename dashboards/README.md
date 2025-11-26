# Dashboard API Documentation

## Overview
The Dashboard API provides role-based endpoints that return JSON data for frontend dashboards. Each user role (Executive, Officer, Farmer) has dedicated endpoints with permission-based access control.

## Testing
Run comprehensive dashboard tests:
```bash
python manage.py test_dashboard_apis
```

## API Endpoints

### Executive Dashboard (National Admin Only)

**Base URL:** `/api/dashboards/executive/`

#### 1. Full Dashboard
```http
GET /api/dashboards/executive/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "overview": {
    "farms": {...},
    "procurement": {...},
    "financials": {...},
    "approvals": {...}
  },
  "revenue_trend": [...],
  "orders_by_status": [...],
  "top_farms": [...],
  "sla_compliance": {...},
  "farm_distribution": [...],
  "production_types": [...],
  "recent_activities": [...]
}
```

#### 2. Overview Stats Only
```http
GET /api/dashboards/executive/overview/
```

#### 3. Chart Data
```http
GET /api/dashboards/executive/charts/?months=6
```

---

### Officer Dashboard (Procurement Officers)

**Base URL:** `/api/dashboards/officer/`

#### 1. Full Dashboard
```http
GET /api/dashboards/officer/
```

**Response:**
```json
{
  "overview": {
    "orders": {...},
    "pending_actions": {...},
    "budget": {...}
  },
  "my_orders": [...],
  "pending_approvals": {...},
  "overdue_items": {...},
  "performance": {...}
}
```

#### 2. Overview Stats Only
```http
GET /api/dashboards/officer/overview/
```

#### 3. My Orders
```http
GET /api/dashboards/officer/orders/?status=active&limit=50
```

**Query Parameters:**
- `status` (optional): Filter by order status
- `limit` (optional): Max results (default: 50)

#### 4. Order Timeline
```http
GET /api/dashboards/officer/orders/{order_id}/timeline/
```

---

### Farmer Dashboard (Farmers Only)

**Base URL:** `/api/dashboards/farmer/`

#### 1. Full Dashboard
```http
GET /api/dashboards/farmer/
```

**Response:**
```json
{
  "overview": {
    "assignments": {...},
    "earnings": {...},
    "deliveries": {...},
    "performance": {...}
  },
  "assignments": [...],
  "pending_actions": {...},
  "earnings": {...},
  "delivery_history": [...],
  "performance": {...}
}
```

#### 2. Overview Stats Only
```http
GET /api/dashboards/farmer/overview/
```

#### 3. My Assignments
```http
GET /api/dashboards/farmer/assignments/?status=pending&limit=50
```

**Query Parameters:**
- `status` (optional): Filter by assignment status
- `limit` (optional): Max results (default: 50)

#### 4. Earnings Breakdown
```http
GET /api/dashboards/farmer/earnings/
```

**Response:**
```json
{
  "by_status": {
    "paid": 185000.00,
    "approved": 25000.00,
    "pending": 15000.00
  },
  "deductions": {
    "quality": 5000.00,
    "mortality": 2000.00,
    "other": 500.00,
    "total": 7500.00
  },
  "monthly_trend": [...]
}
```

#### 5. Pending Actions
```http
GET /api/dashboards/farmer/pending-actions/
```

**Response:**
```json
{
  "pending_responses": [...],
  "preparing_orders": [...],
  "ready_for_delivery": [...]
}
```

---

## Permissions

### IsExecutive
- Allowed roles: `national_admin`
- Access: Full system-wide metrics

### IsProcurementOfficer
- Allowed roles: `procurement_officer`, `national_admin`
- Access: Officer-specific workflow data

### IsFarmer
- Allowed roles: `farmer`
- Access: Farm-specific data only

### IsConstituencyOfficial
- Allowed roles: `constituency_official`
- Access: Regional oversight data

---

## Service Layer Architecture

Each dashboard role has a dedicated service class:

### `ExecutiveDashboardService`
- `get_overview_stats()` - Farm/procurement/financial overview
- `get_revenue_trend(months=6)` - Monthly revenue chart
- `get_orders_by_status()` - Order status distribution
- `get_top_performing_farms(limit=10)` - Top farms by revenue
- `get_approval_sla_compliance()` - SLA metrics
- `get_farm_distribution_by_region()` - Regional breakdown
- `get_production_type_distribution()` - Production types
- `get_recent_activities(limit=20)` - Activity feed

### `OfficerDashboardService`
- `__init__(user)` - Takes authenticated user
- `get_overview_stats()` - Officer metrics
- `get_my_orders(status=None, limit=50)` - Assigned orders
- `get_pending_approvals()` - Items needing approval
- `get_overdue_items()` - Overdue orders/invoices
- `get_order_timeline(order_id)` - Complete order history
- `get_performance_metrics(days=30)` - Officer performance

### `FarmerDashboardService`
- `__init__(user)` - Gets user's farm
- `get_overview_stats()` - Farmer metrics
- `get_my_assignments(status=None, limit=50)` - Farm assignments
- `get_pending_actions()` - Items requiring response
- `get_earnings_breakdown()` - Earnings with deductions
- `get_delivery_history(limit=20)` - Past deliveries
- `get_performance_summary()` - Overall performance

---

## Frontend Integration

### React/Next.js Example

```javascript
// Executive Dashboard
const fetchExecutiveDashboard = async () => {
  const response = await fetch('/api/dashboards/executive/', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  const data = await response.json();
  return data;
};

// Officer Orders with Filter
const fetchOfficerOrders = async (status = 'active') => {
  const response = await fetch(
    `/api/dashboards/officer/orders/?status=${status}&limit=20`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  return await response.json();
};

// Farmer Earnings
const fetchFarmerEarnings = async () => {
  const response = await fetch('/api/dashboards/farmer/earnings/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return await response.json();
};
```

### Chart Integration (Chart.js/Recharts)

```javascript
// Revenue Trend Chart
const data = await fetch('/api/dashboards/executive/charts/?months=12');
const chartData = data.revenue_trend.map(item => ({
  month: item.month,
  revenue: item.revenue,
  orders: item.orders
}));

// Use with Chart.js or Recharts
<LineChart data={chartData}>
  <Line dataKey="revenue" stroke="#8884d8" />
  <Line dataKey="orders" stroke="#82ca9d" />
</LineChart>
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK` - Success
- `401 Unauthorized` - Missing/invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found (e.g., invalid order_id)
- `500 Internal Server Error` - Server error

**Error Response Format:**
```json
{
  "detail": "Error message here"
}
```

---

## Performance Optimization

### Query Optimization
- Uses `select_related()` for foreign keys
- Uses `prefetch_related()` for reverse relations
- Aggregations done at database level
- Limited result sets with configurable limits

### Caching (Optional)
For production, consider caching expensive queries:

```python
from django.core.cache import cache

def get_overview_stats(self):
    cache_key = 'executive_overview_stats'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    data = {
        # ... expensive calculations
    }
    
    cache.set(cache_key, data, 300)  # Cache for 5 minutes
    return data
```

---

## Development

### Running Tests
```bash
# Test all dashboard services
python manage.py test_dashboard_apis

# Django system check
python manage.py check

# Run development server
python manage.py runserver
```

### Adding New Metrics

1. Add method to appropriate service class:
```python
# dashboards/services/executive.py
def get_new_metric(self):
    # Query logic here
    return {...}
```

2. Add endpoint in views:
```python
# dashboards/views.py
class ExecutiveNewMetricView(APIView):
    permission_classes = [IsAuthenticated, IsExecutive]
    
    def get(self, request):
        service = ExecutiveDashboardService()
        data = service.get_new_metric()
        return Response(data)
```

3. Add URL pattern:
```python
# dashboards/urls.py
path('executive/new-metric/', ExecutiveNewMetricView.as_view(), name='executive-new-metric'),
```

---

## Next Steps

1. **Frontend Development**: Build React/Next.js dashboards
2. **Real-time Updates**: Add WebSocket support
3. **Export Features**: PDF/CSV reports
4. **Advanced Analytics**: Predictive models
5. **Mobile App**: React Native dashboards

---

## Support

For issues or questions:
- Check the test command: `python manage.py test_dashboard_apis`
- Review service layer code in `dashboards/services/`
- Check permissions in `dashboards/permissions.py`
