# Farmer Dashboard Overview API

This guide shows how the frontend should consume the farmer dashboard overview endpoint.

## Endpoint
- `GET /api/dashboards/farmer/overview/`
- Auth required. Allowed role: `FARMER` (farmers only).
- **No user ID required in URL** - the backend automatically uses the authenticated user from the session/token.

## Response Shape
```json
{
  "farm": {
    "farm_name": "Tetteh Poultry Farms",
    "farm_id": "YEA-GAR-ODO-0001",
    "primary_production_type": "Both",
    "total_bird_capacity": 5000,
    "current_bird_count": 3200,
    "capacity_utilization": 64.0,
    "active_flocks": 3
  },
  "production": {
    "total_eggs_last_30_days": 45000,
    "avg_daily_eggs": 1500.0,
    "total_mortality_last_30_days": 25,
    "mortality_rate_percent": 0.78,
    "total_feed_consumed_kg": 9600.0,
    "avg_daily_feed_kg": 320.0
  },
  "assignments": {
    "total": 12,
    "pending": 2,
    "accepted": 3,
    "completed": 7,
    "acceptance_rate": 83.33
  },
  "earnings": {
    "total": 125000.00,
    "pending": 15000.00,
    "last_payment_amount": 25000.00,
    "last_payment_date": "2025-11-28"
  },
  "deliveries": {
    "total": 8,
    "pending": 1
  },
  "performance": {
    "avg_quality": 2.85,
    "quality_pass_rate": 87.5
  }
}
```

## Fields for Dashboard Cards

### Farm Overview Card
- **Farm Name**: `farm.farm_name`
- **Farm ID**: `farm.farm_id`
- **Production Type**: `farm.primary_production_type` (Layers/Broilers/Both)
- **Current Birds**: `farm.current_bird_count`
- **Capacity**: `farm.total_bird_capacity`
- **Utilization**: `farm.capacity_utilization`% (visual progress bar)
- **Active Flocks**: `farm.active_flocks`

### Production Statistics Card (Last 30 Days)
- **Total Eggs**: `production.total_eggs_last_30_days`
- **Avg Daily Eggs**: `production.avg_daily_eggs`
- **Total Mortality**: `production.total_mortality_last_30_days` birds
- **Mortality Rate**: `production.mortality_rate_percent`%
- **Feed Consumed**: `production.total_feed_consumed_kg` kg
- **Avg Daily Feed**: `production.avg_daily_feed_kg` kg

### Procurement & Earnings Card
- **Total Assignments**: `assignments.total` - Total government procurement orders assigned to this farm
- **Pending Responses**: `assignments.pending` - Orders awaiting farmer's accept/reject response
- **Accepted**: `assignments.accepted` - Orders accepted and in preparation/delivery stages
- **Completed**: `assignments.completed` - Orders delivered, verified, or paid
- **Acceptance Rate**: `assignments.acceptance_rate`% - Percentage of accepted vs total assignments
- **Total Earnings**: GHS `earnings.total` - Total payments received from completed orders
- **Pending Payments**: GHS `earnings.pending` - Invoices awaiting payment approval/processing
- **Last Payment**: GHS `earnings.last_payment_amount` on `earnings.last_payment_date`

### Performance Card
- **Quality Score**: `performance.avg_quality` / 5.0
- **Quality Pass Rate**: `performance.quality_pass_rate`%
- **Total Deliveries**: `deliveries.total`
- **Pending Deliveries**: `deliveries.pending`

## Sample Request (frontend service)
```ts
async function getFarmerDashboardOverview() {
  const res = await httpClient.get('/dashboards/farmer/overview/');
  console.log('Farmer dashboard response:', res.data); // Debug: log the response
  return res.data;
}

// Usage with error handling
async function loadFarmerDashboard() {
  try {
    const data = await getFarmerDashboardOverview();
    
    if (data.error) {
      // No farm profile yet
      showNoFarmMessage(data.error);
      return null;
    }
    
    // Display dashboard with farm data
    return data;
  } catch (error) {
    console.error('Failed to load farmer dashboard:', error);
    if (error.response?.status === 403) {
      // Not a farmer
      showPermissionDenied();
    } else if (error.response?.status === 401) {
      // Not authenticated
      redirectToLogin();
    }
    throw error;
  }
}
```

## Error Handling

### No Farm Profile
If the authenticated farmer does not have a farm profile yet (e.g., application still pending):
```json
{
  "error": "No farm found for this user",
  "farm": {},
  "production": {},
  "assignments": {},
  "earnings": {},
  "deliveries": {},
  "performance": {}
}
```
**Frontend should**: Display a message like "Your farm profile is being set up. Please wait for approval." and hide the dashboard cards.

### Permission Denied (Non-Farmer)
If user is not a farmer (returns `403 Forbidden`):
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### Authentication Required
If no valid token (returns `401 Unauthorized`):
```json
{
  "detail": "Authentication credentials were not provided."
}
```

## Understanding Procurement Assignments

### What are Procurement Assignments?
Procurement assignments are **government bulk orders** distributed to approved farms in the YEA program. When the government needs poultry products (broilers for meat or eggs from layers), procurement officers create orders that are assigned to multiple farms based on capacity and availability.

**Key Points:**
- 📦 **One government order** → **Multiple farm assignments** (distributed based on capacity)
- 💰 **Guaranteed pricing** agreed upfront (e.g., GHS 20 per bird)
- ⏱️ **Time-bound deliveries** with specific deadlines
- ✅ **Quality inspection** before payment approval
- 📊 **Performance tracking** affects future assignment opportunities

### Assignment Workflow
```
1. Government creates ProcurementOrder
   └─> Example: Need 10,000 broilers by Dec 31, Budget: GHS 200,000
   
2. System assigns portions to multiple farms (OrderAssignment)
   ├─> Farm A: 3,000 birds @ GHS 20/bird = GHS 60,000
   ├─> Farm B: 2,500 birds @ GHS 20/bird = GHS 50,000
   ├─> Farm C: 2,000 birds @ GHS 20/bird = GHS 40,000
   ├─> Farm D: 1,500 birds @ GHS 20/bird = GHS 30,000
   └─> Farm E: 1,000 birds @ GHS 20/bird = GHS 20,000
   
3. Farmers receive assignment notification
   └─> Status: "pending" - awaiting farmer response
   
4. Farmer accepts or rejects assignment
   ├─> Accept → status: "accepted" → farmer prepares order
   └─> Reject → status: "rejected" → system reassigns to another farm
   
5. Farmer prepares order
   └─> Status: "preparing" → "ready" → "in_transit"
   
6. Farmer delivers to specified location
   └─> Status: "delivered" - delivery confirmation created
   
7. Quality inspection and verification
   ├─> Weight check, mortality assessment, quality grading
   └─> Status: "verified" - delivery accepted
   
8. Invoice generated and payment processed
   └─> Status: "paid" - farmer receives payment
```

### Assignment Statuses Explained

| Status | Meaning | Farmer Action |
|--------|---------|---------------|
| **pending** | Awaiting your response | Accept or reject the assignment |
| **accepted** | You accepted the order | Prepare the order for delivery |
| **rejected** | You rejected the order | No further action |
| **preparing** | You're preparing the order | Continue raising/preparing birds |
| **ready** | Order is ready for pickup/delivery | Coordinate delivery |
| **in_transit** | Order is being delivered | Complete delivery |
| **delivered** | Order delivered | Wait for verification |
| **verified** | Delivery verified by officer | Wait for invoice/payment |
| **paid** | Payment processed | Order complete |
| **cancelled** | Order was cancelled | No further action |

### Assignment Metrics in Dashboard

- **Total Assignments** = All orders ever assigned to your farm (lifetime count)
- **Pending** = Orders awaiting your accept/reject response (requires immediate attention)
- **Accepted** = Orders you've accepted and are currently preparing/delivering
- **Completed** = Orders that have been delivered, verified, or paid
- **Acceptance Rate** = (Accepted orders ÷ Total assignments) × 100
  - High rate (>80%) = Good track record, more future assignments
  - Low rate (<50%) = May reduce future assignment priority

### Why This Matters for Farmers

✅ **Guaranteed Market**: Government procurement provides stable demand  
✅ **Fair Pricing**: Price per unit agreed upfront (e.g., GHS 20/bird)  
✅ **Reliable Payments**: Payments processed through formal invoicing system  
✅ **Performance Tracking**: Quality and acceptance rate affect future opportunities  
✅ **Capacity Planning**: Helps you know when to increase/decrease production

### Common Scenarios

**Scenario 1: New farmer, no assignments yet**
```json
"assignments": {
  "total": 0,
  "pending": 0,
  "accepted": 0,
  "completed": 0,
  "acceptance_rate": 0
}
```
→ Farm is new or not yet selected for procurement. Focus on building capacity.

**Scenario 2: Active farmer with pending assignments**
```json
"assignments": {
  "total": 5,
  "pending": 2,    ← NEEDS ATTENTION: 2 orders waiting for response
  "accepted": 1,
  "completed": 2,
  "acceptance_rate": 60
}
```
→ Check pending assignments and accept/reject based on your capacity.

**Scenario 3: Established farmer with good track record**
```json
"assignments": {
  "total": 20,
  "pending": 0,
  "accepted": 3,
  "completed": 15,
  "acceptance_rate": 90
}
```
→ High acceptance rate (90%) = reliable farmer, likely to receive more assignments.

## Notes
- **No user ID in URL**: The endpoint automatically uses `request.user` from the authentication token. Do NOT include `/api/dashboards/farmer/overview/{user_id}/` - the correct URL is `/api/dashboards/farmer/overview/`.
- **Production metrics** are calculated from the last 30 days of `DailyProduction` records.
- **Current bird count** is the sum of all active flocks' `current_count`.
- **Capacity utilization** = (current_bird_count / total_capacity) × 100.
- **Mortality rate** = (total_mortality_last_30_days / current_bird_count) × 100.
- **Assignments** are procurement orders assigned to the farmer by government officers.
- **Acceptance Rate** formula: (accepted_assignments / total_assignments) × 100, where accepted includes statuses: accepted, preparing, ready.
- Endpoint is already wired via `dashboards/urls.py` under `api/dashboards/farmer/overview/`.
- **Farm creation**: Farm profiles are automatically created when applications receive final (national-level) approval. See `FARM_PROFILE_AUTO_CREATION.md` for details.

## Frontend Integration Tips

### Display Priority
1. **Alert Badges** (requires immediate attention):
   - `assignments.pending > 0` → Show red badge: "X pending assignments need response"
   - `deliveries.pending > 0` → Show orange badge: "X deliveries ready for dispatch"
   - `production.mortality_rate_percent > 2` → Show warning: "High mortality rate detected"

2. **Action Cards** (clickable for details):
   - Pending Assignments → Link to assignment list with accept/reject buttons
   - Accepted Orders → Link to order preparation/delivery tracking
   - Pending Payments → Link to invoice/payment history

3. **Visual Indicators**:
   - Capacity utilization: Progress bar (green <70%, yellow 70-90%, red >90%)
   - Acceptance rate: Color-coded (green >80%, yellow 60-80%, red <60%)
   - Quality pass rate: Star rating or percentage badge

### Suggested Card Layout
```
┌─────────────────────────────────┬─────────────────────────────────┐
│  Farm Overview                  │  Production (Last 30 Days)      │
│  • Alpha Farms                  │  • 45,000 eggs (1,500/day)      │
│  • 3,200 / 5,000 birds (64%)    │  • 25 deaths (0.78% mortality)  │
│  • 3 active flocks              │  • 9,600 kg feed (320 kg/day)   │
└─────────────────────────────────┴─────────────────────────────────┘

┌─────────────────────────────────┬─────────────────────────────────┐
│  Procurement Assignments        │  Earnings & Payments            │
│  📦 2 pending (needs response!) │  💰 GHS 125,000 earned          │
│  ✓ 3 accepted (in progress)     │  ⏳ GHS 15,000 pending          │
│  ✅ 7 completed (paid)          │  📅 Last: GHS 25,000 on Nov 28  │
│  📊 Acceptance: 83.3%           │                                 │
└─────────────────────────────────┴─────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Performance Metrics                                                │
│  ⭐ Quality: 2.85/5.0  |  ✓ Pass Rate: 87.5%  |  🚚 8 deliveries   │
└─────────────────────────────────────────────────────────────────────┘
```

### Best Practices
- Display farm name and ID prominently at the top
- Use visual indicators (progress bars, gauges) for capacity utilization and mortality rate
- **Highlight pending assignments with badge/notification icon** - this requires immediate farmer action
- Show production trends with sparkline charts for eggs and feed consumption
- Alert farmers when mortality rate exceeds threshold (e.g., > 2%)
- Link to detailed flock management and production tracking pages from the dashboard
- Show acceptance rate with explanation tooltip: "High acceptance rate increases future assignment priority"

## Troubleshooting

### "Cannot read properties of undefined (reading 'error')"
This means the response is `undefined`. Check:
1. **Is the API call being made?** Check browser Network tab for the request.
2. **Is the response coming back?** Look for `200 OK` status and response body in Network tab.
3. **Is the axios/httpClient configured correctly?** Verify base URL and response interceptors.
4. **Are you accessing `res.data` correctly?** Some HTTP clients nest the data differently (e.g., `res.data.data`).

**Quick fix**: Add `console.log('Response:', res)` before `return res.data` to see the full response structure.

### Response shows data but frontend says "no data"
If Network tab shows valid JSON but your component says "no data":
1. **Check the data structure**: Response includes `error`, `farm`, `production`, `assignments`, `earnings`, `deliveries`, `performance` keys.
2. **Handle the error case**: If `data.error` exists, the user has no farm profile yet.
3. **Verify async/await**: Make sure you're awaiting the API call before accessing data.
4. **Check state management**: Ensure data is being set in React state correctly.

Example:
```tsx
const [dashboardData, setDashboardData] = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  async function fetchDashboard() {
    try {
      const data = await getFarmerDashboardOverview();
      console.log('Dashboard data received:', data); // Debug log
      
      if (data.error) {
        setError(data.error);
      } else {
        setDashboardData(data);
      }
    } catch (err) {
      console.error('API error:', err);
      setError('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }
  
  fetchDashboard();
}, []);

if (loading) return <LoadingSpinner />;
if (error) return <ErrorMessage message={error} />;
if (!dashboardData?.farm?.farm_id) return <NoFarmMessage />;

return <DashboardView data={dashboardData} />;
```

## Frequently Asked Questions

### Q: What counts as "pending" assignment?
A: Assignments with status = "pending" are orders that have been assigned to your farm but you haven't yet accepted or rejected. These require immediate farmer action.

### Q: How is acceptance rate calculated?
A: `acceptance_rate = (accepted + preparing + ready orders) / total assignments × 100`

Example: If you have 12 total assignments and 10 were accepted (3 currently in progress + 7 completed), your acceptance rate is (10/12) × 100 = 83.33%

### Q: Why is my acceptance rate important?
A: Government procurement officers use acceptance rate to determine farm reliability. Higher rates (>80%) mean you're more likely to:
- Receive priority for future assignments
- Get larger order quantities
- Be contacted first for urgent orders

### Q: What if I have 0 assignments?
A: This is normal for new farms. Assignments are distributed based on:
- Farm capacity and active flocks
- Geographic location (proximity to delivery points)
- Historical performance (quality and acceptance rate)
- Current inventory availability

Focus on building up your flocks and maintaining good production records. As your capacity increases, you'll receive assignments.

### Q: What's the difference between "accepted" and "completed"?
A: 
- **Accepted** = Orders you've agreed to fulfill and are currently working on (statuses: accepted, preparing, ready)
- **Completed** = Orders that have been fully processed (statuses: delivered, verified, paid)

### Q: How do earnings work?
A: 
1. You complete and deliver an assigned order
2. Procurement officer verifies delivery (quality check)
3. System auto-generates invoice based on delivered quantity
4. Officer approves invoice → status becomes "pending payment"
5. Payment is processed → status becomes "paid"
6. Amount appears in "total earnings"

**Total Earnings** = Sum of all paid invoices (money already received)  
**Pending Payments** = Sum of approved invoices awaiting payment processing

### Q: Can I reject an assignment?
A: Yes! When you receive an assignment (status = "pending"), you can:
- **Accept**: If you have capacity and can meet the deadline
- **Reject**: If you don't have enough birds, can't meet quality requirements, or can't deliver by deadline

Note: Frequent rejections will lower your acceptance rate, so only accept orders you can fulfill.

### Q: What happens if my quality doesn't pass inspection?
A: 
- Delivery is marked as `quality_passed: false`
- Deductions may be applied to your invoice (reduced payment)
- Your quality pass rate decreases
- This affects your performance score and future assignment priority

Maintain high quality by:
- Following proper feeding schedules
- Regular health checks and vaccinations
- Proper housing and sanitation
- Timely delivery to maintain freshness

