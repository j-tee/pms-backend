# Financial Dashboard & AdSense API Documentation

**Date:** January 4, 2026  
**Version:** 1.0  
**Status:** Production Ready  
**Base URL:** `https://pms.alphalogictech.com`

---

## 🔒 Access Control

**IMPORTANT:** All financial endpoints are restricted to **SUPER_ADMIN only**.

| Role | Access |
|------|--------|
| SUPER_ADMIN | ✅ Full access |
| YEA_OFFICIAL | ❌ 403 Forbidden |
| NATIONAL_ADMIN | ❌ 403 Forbidden |
| All other roles | ❌ 403 Forbidden |

The frontend should **hide** all financial menu items and routes for non-SUPER_ADMIN users.

---

## 🔐 Authentication

All endpoints require JWT authentication:

```http
Authorization: Bearer {jwt_token}
```

---

## 📊 Endpoints Overview

### Financial Reporting

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/finance/dashboard/` | GET | Quick overview dashboard |
| `/api/admin/payments/` | GET | Payment history |
| `/api/admin/revenue/summary/` | GET | Revenue breakdown |
| `/api/admin/subscribers/` | GET | Marketplace subscribers |

### AdSense Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/adsense/status/` | GET | Check connection status |
| `/api/admin/adsense/connect/` | GET | Get OAuth URL |
| `/api/admin/adsense/callback/` | GET | OAuth callback (automatic) |
| `/api/admin/adsense/disconnect/` | POST | Disconnect account |
| `/api/admin/adsense/earnings/` | GET | Earnings summary |
| `/api/admin/adsense/reports/` | GET | Detailed reports |
| `/api/admin/adsense/payments/` | GET | Payment history |

---

## 1. Finance Dashboard

### GET `/api/admin/finance/dashboard/`

Quick overview of platform financial metrics.

**Response:**
```json
{
    "today": {
        "revenue": "500.00",
        "transactions": 25,
        "new_subscribers": 5
    },
    "this_week": {
        "revenue": "2500.00",
        "transactions": 125,
        "new_subscribers": 30
    },
    "this_month": {
        "revenue": "8000.00",
        "transactions": 400,
        "new_subscribers": 100
    },
    "pending_payments": {
        "count": 15,
        "amount": "300.00"
    },
    "expiring_soon": {
        "count": 45,
        "in_7_days": 20,
        "in_30_days": 45
    },
    "recent_payments": [
        {
            "id": "uuid",
            "farm_name": "Kwame's Poultry",
            "amount": "50.00",
            "payment_method": "mobile_money",
            "paid_at": "2026-01-04T10:30:00Z"
        }
    ],
    "adsense": {
        "connected": true,
        "today": "45.32",
        "this_week": "320.50",
        "this_month": "1200.00",
        "currency": "USD"
    }
}
```

**AdSense Object (when not connected):**
```json
{
    "adsense": {
        "connected": false,
        "message": "AdSense not connected"
    }
}
```

**Frontend Usage:**
```tsx
interface FinanceDashboardData {
    today: PeriodStats;
    this_week: PeriodStats;
    this_month: PeriodStats;
    pending_payments: { count: number; amount: string };
    expiring_soon: { count: number; in_7_days: number; in_30_days: number };
    recent_payments: RecentPayment[];
    adsense: AdSenseData | { connected: false; message: string };
}

interface PeriodStats {
    revenue: string;
    transactions: number;
    new_subscribers: number;
}

interface AdSenseData {
    connected: true;
    today: string;
    this_week: string;
    this_month: string;
    currency: string;
}

function FinanceDashboard() {
    const [data, setData] = useState<FinanceDashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        fetch('/api/admin/finance/dashboard/', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => {
            if (res.status === 403) {
                // User doesn't have access - redirect
                navigate('/admin/dashboard');
                return null;
            }
            return res.json();
        })
        .then(setData)
        .finally(() => setLoading(false));
    }, []);
    
    if (!data) return <AccessDenied />;
    
    return (
        <div className="finance-dashboard">
            {/* Revenue Cards */}
            <div className="stats-grid">
                <StatCard 
                    title="Today's Revenue" 
                    value={`GHS ${data.today.revenue}`}
                    subtitle={`${data.today.transactions} transactions`}
                />
                <StatCard 
                    title="This Week" 
                    value={`GHS ${data.this_week.revenue}`}
                    subtitle={`${data.this_week.new_subscribers} new subscribers`}
                />
                <StatCard 
                    title="This Month" 
                    value={`GHS ${data.this_month.revenue}`}
                    trend="+15%"
                />
            </div>
            
            {/* AdSense Card */}
            {data.adsense.connected ? (
                <AdSenseCard data={data.adsense} />
            ) : (
                <AdSenseConnectPrompt />
            )}
            
            {/* Alerts */}
            <AlertsSection 
                pending={data.pending_payments}
                expiring={data.expiring_soon}
            />
            
            {/* Recent Payments */}
            <RecentPaymentsTable payments={data.recent_payments} />
        </div>
    );
}
```

---

## 2. Payment History

### GET `/api/admin/payments/`

List all marketplace activation payments with filtering.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `completed`, `pending`, `failed`, `refunded` |
| `payment_method` | string | `momo`, `bank`, `card`, `cash` |
| `date_from` | string | Start date (YYYY-MM-DD) |
| `date_to` | string | End date (YYYY-MM-DD) |
| `search` | string | Search farm name, farmer name, reference |
| `page` | number | Page number (default: 1) |
| `page_size` | number | Items per page (default: 20) |

**Example Request:**
```http
GET /api/admin/payments/?status=completed&date_from=2025-01-01&date_to=2025-12-31&page=1
Authorization: Bearer {token}
```

**Response:**
```json
{
    "results": [
        {
            "id": "uuid",
            "farm_id": "uuid",
            "farm_name": "Kwame's Poultry",
            "farmer_name": "Kwame Asante",
            "farmer_phone": "+233244123456",
            "amount": "50.00",
            "payment_type": "marketplace_activation",
            "payment_method": "momo",
            "transaction_reference": "TXN123456",
            "status": "completed",
            "paid_at": "2026-01-04T10:30:00Z",
            "period_start": "2026-01-04",
            "period_end": "2026-02-04",
            "verified_by": "Admin User",
            "notes": ""
        }
    ],
    "count": 150,
    "total_amount": "7500.00",
    "page": 1,
    "page_size": 20,
    "total_pages": 8
}
```

**Payment Types:**
| Value | Description |
|-------|-------------|
| `marketplace_activation` | Initial marketplace access payment |
| `subscription_renewal` | Monthly renewal |
| `verified_seller` | Verified seller tier upgrade |

**Payment Methods (Display Mapping):**
| API Value | Display Text |
|-----------|-------------|
| `momo` | Mobile Money |
| `bank` | Bank Transfer |
| `card` | Card Payment |
| `cash` | Cash |

**Frontend Usage:**
```tsx
interface PaymentFilters {
    status?: string;
    payment_method?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
}

function PaymentsList() {
    const [payments, setPayments] = useState([]);
    const [filters, setFilters] = useState<PaymentFilters>({});
    const [pagination, setPagination] = useState({ page: 1, total: 0 });
    
    const fetchPayments = async () => {
        const params = new URLSearchParams({
            page: String(pagination.page),
            ...Object.fromEntries(
                Object.entries(filters).filter(([_, v]) => v)
            )
        });
        
        const res = await fetch(`/api/admin/payments/?${params}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        setPayments(data.results);
        setPagination(prev => ({ ...prev, total: data.count }));
    };
    
    return (
        <div>
            <PaymentFiltersBar 
                filters={filters} 
                onChange={setFilters}
            />
            
            <Table
                columns={[
                    { key: 'farm_name', label: 'Farm' },
                    { key: 'farmer_name', label: 'Farmer' },
                    { key: 'amount', label: 'Amount', render: (v) => `GHS ${v}` },
                    { key: 'payment_method', label: 'Method', render: formatPaymentMethod },
                    { key: 'status', label: 'Status', render: (v) => <StatusBadge status={v} /> },
                    { key: 'paid_at', label: 'Date', render: formatDate },
                ]}
                data={payments}
            />
            
            <Pagination 
                current={pagination.page}
                total={pagination.total}
                pageSize={20}
                onChange={(p) => setPagination(prev => ({ ...prev, page: p }))}
            />
        </div>
    );
}

function formatPaymentMethod(method: string): string {
    const map: Record<string, string> = {
        'momo': 'Mobile Money',
        'bank': 'Bank Transfer',
        'card': 'Card',
        'cash': 'Cash',
    };
    return map[method] || method;
}
```

---

## 3. Revenue Summary

### GET `/api/admin/revenue/summary/`

Get revenue breakdown with trend analysis.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | `daily`, `weekly`, `monthly`, `yearly` (default: monthly) |
| `year` | number | Year to filter (default: current year) |
| `month` | number | Month filter (for daily period) |

**Example Request:**
```http
GET /api/admin/revenue/summary/?period=monthly&year=2025
Authorization: Bearer {token}
```

**Response:**
```json
{
    "total_revenue": "15000.00",
    "period": "monthly",
    "year": 2025,
    "breakdown": [
        { "month": "2025-01", "amount": "2500.00", "transaction_count": 125 },
        { "month": "2025-02", "amount": "3200.00", "transaction_count": 160 },
        { "month": "2025-03", "amount": "2800.00", "transaction_count": 140 }
    ],
    "by_type": {
        "marketplace_activation": "12000.00",
        "verified_seller_fees": "2000.00",
        "transaction_commission": "1000.00"
    },
    "comparison": {
        "previous_period": "12000.00",
        "current_period": "15000.00",
        "growth_percentage": "25.00"
    }
}
```

**Frontend Usage (Chart):**
```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function RevenueChart() {
    const [data, setData] = useState(null);
    const [period, setPeriod] = useState('monthly');
    const [year, setYear] = useState(new Date().getFullYear());
    
    useEffect(() => {
        fetch(`/api/admin/revenue/summary/?period=${period}&year=${year}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(setData);
    }, [period, year]);
    
    if (!data) return <Loading />;
    
    const chartData = data.breakdown.map(item => ({
        name: item.month || item.date,
        revenue: parseFloat(item.amount),
        transactions: item.transaction_count,
    }));
    
    return (
        <div>
            <div className="filters">
                <Select value={period} onChange={setPeriod}>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="yearly">Yearly</option>
                </Select>
                <YearPicker value={year} onChange={setYear} />
            </div>
            
            <div className="summary-cards">
                <Card title="Total Revenue" value={`GHS ${data.total_revenue}`} />
                <Card 
                    title="Growth" 
                    value={`${data.comparison.growth_percentage}%`}
                    trend={parseFloat(data.comparison.growth_percentage) > 0 ? 'up' : 'down'}
                />
            </div>
            
            <ResponsiveContainer width="100%" height={400}>
                <LineChart data={chartData}>
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="revenue" stroke="#8884d8" />
                </LineChart>
            </ResponsiveContainer>
            
            {/* Revenue by Type Pie Chart */}
            <RevenueByTypePie data={data.by_type} />
        </div>
    );
}
```

---

## 4. Subscribers Management

### GET `/api/admin/subscribers/`

List marketplace subscribers with status and tier information.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `active`, `trial`, `grace_period`, `expired` |
| `tier` | string | `standard`, `verified`, `government_subsidized` |
| `search` | string | Search farm name, farmer name |
| `page` | number | Page number (default: 1) |
| `page_size` | number | Items per page (default: 20) |

**Response:**
```json
{
    "results": [
        {
            "farm_id": "uuid",
            "farm_name": "Kwame's Poultry",
            "farmer_name": "Kwame Asante",
            "tier": "standard",
            "subscription_status": "active",
            "started_at": "2025-01-04",
            "expires_at": "2026-02-04",
            "days_remaining": 28,
            "total_paid": "600.00",
            "last_payment_date": "2026-01-04"
        }
    ],
    "count": 450,
    "page": 1,
    "page_size": 20,
    "total_pages": 23,
    "summary": {
        "total_active": 450,
        "total_trial": 50,
        "total_grace_period": 20,
        "total_expired": 100,
        "by_tier": {
            "standard": 400,
            "verified": 50,
            "government_subsidized": 120
        }
    }
}
```

**Subscription Status Values:**
| Status | Description | UI Color |
|--------|-------------|----------|
| `active` | Active paid subscriber | 🟢 Green |
| `trial` | In trial period | 🔵 Blue |
| `grace_period` | Payment overdue, in grace period | 🟡 Yellow |
| `expired` | Subscription expired | 🔴 Red |

**Tier Values:**
| Tier | Description |
|------|-------------|
| `standard` | Standard marketplace access (GHS 50/month) |
| `verified` | Verified seller tier (premium) |
| `government_subsidized` | Government-funded access |

**Frontend Usage:**
```tsx
function SubscribersList() {
    const [data, setData] = useState(null);
    const [filters, setFilters] = useState({ status: '', tier: '' });
    
    useEffect(() => {
        const params = new URLSearchParams(
            Object.entries(filters).filter(([_, v]) => v)
        );
        
        fetch(`/api/admin/subscribers/?${params}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(setData);
    }, [filters]);
    
    return (
        <div>
            {/* Summary Cards */}
            <div className="summary-grid">
                <StatCard title="Active" value={data?.summary.total_active} color="green" />
                <StatCard title="Trial" value={data?.summary.total_trial} color="blue" />
                <StatCard title="Grace Period" value={data?.summary.total_grace_period} color="yellow" />
                <StatCard title="Expired" value={data?.summary.total_expired} color="red" />
            </div>
            
            {/* Tier Breakdown */}
            <TierBreakdownChart data={data?.summary.by_tier} />
            
            {/* Filters */}
            <div className="filters">
                <Select 
                    value={filters.status} 
                    onChange={(e) => setFilters(f => ({ ...f, status: e.target.value }))}
                >
                    <option value="">All Statuses</option>
                    <option value="active">Active</option>
                    <option value="trial">Trial</option>
                    <option value="grace_period">Grace Period</option>
                    <option value="expired">Expired</option>
                </Select>
                
                <Select 
                    value={filters.tier}
                    onChange={(e) => setFilters(f => ({ ...f, tier: e.target.value }))}
                >
                    <option value="">All Tiers</option>
                    <option value="standard">Standard</option>
                    <option value="verified">Verified</option>
                    <option value="government_subsidized">Government Subsidized</option>
                </Select>
            </div>
            
            {/* Subscribers Table */}
            <Table
                columns={[
                    { key: 'farm_name', label: 'Farm' },
                    { key: 'farmer_name', label: 'Farmer' },
                    { key: 'tier', label: 'Tier', render: formatTier },
                    { key: 'subscription_status', label: 'Status', render: StatusBadge },
                    { key: 'days_remaining', label: 'Days Left', render: DaysRemaining },
                    { key: 'total_paid', label: 'Total Paid', render: (v) => `GHS ${v}` },
                ]}
                data={data?.results || []}
            />
        </div>
    );
}

function DaysRemaining({ value }: { value: number | null }) {
    if (value === null) return <span>-</span>;
    if (value <= 7) return <span className="text-red-500">{value} days</span>;
    if (value <= 14) return <span className="text-yellow-500">{value} days</span>;
    return <span className="text-green-500">{value} days</span>;
}
```

---

## 5. AdSense Integration

### Check Connection Status

#### GET `/api/admin/adsense/status/`

**Response (Not Connected):**
```json
{
    "configured": true,
    "connected": false,
    "account_info": null
}
```

**Response (Connected):**
```json
{
    "configured": true,
    "connected": true,
    "account_info": {
        "account_id": "pub-1234567890123456",
        "display_name": "YEA PMS",
        "timezone": "Africa/Accra",
        "state": "READY"
    }
}
```

**Response (Not Configured):**
```json
{
    "configured": false,
    "connected": false,
    "account_info": null
}
```

---

### Connect AdSense

#### GET `/api/admin/adsense/connect/`

Get the OAuth authorization URL to connect AdSense.

**Response:**
```json
{
    "authorization_url": "https://accounts.google.com/o/oauth2/auth?client_id=...",
    "message": "Redirect user to this URL to authorize AdSense access",
    "instructions": [
        "1. Open the authorization URL in a browser",
        "2. Sign in with your Google account that has AdSense",
        "3. Grant access to the application",
        "4. You will be redirected back with an authorization code"
    ]
}
```

**Frontend Flow:**
```tsx
function AdSenseConnectButton() {
    const [loading, setLoading] = useState(false);
    
    const handleConnect = async () => {
        setLoading(true);
        
        const res = await fetch('/api/admin/adsense/connect/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        if (data.authorization_url) {
            // Open OAuth popup or redirect
            window.location.href = data.authorization_url;
        }
        
        setLoading(false);
    };
    
    return (
        <Button onClick={handleConnect} loading={loading}>
            Connect Google AdSense
        </Button>
    );
}
```

---

### Disconnect AdSense

#### POST `/api/admin/adsense/disconnect/`

**Response:**
```json
{
    "success": true,
    "message": "AdSense disconnected successfully",
    "connected": false
}
```

---

### Get Earnings Summary

#### GET `/api/admin/adsense/earnings/`

**Response:**
```json
{
    "connected": true,
    "earnings": {
        "today": "45.32",
        "yesterday": "52.10",
        "this_week": "320.50",
        "this_month": "1200.00",
        "last_month": "980.00",
        "currency": "USD",
        "last_updated": "2026-01-04T10:30:00Z"
    },
    "top_pages": [
        {
            "page": "/marketplace",
            "earnings": "450.00",
            "page_views": 12500,
            "impressions": 25000,
            "clicks": 350
        },
        {
            "page": "/farms",
            "earnings": "320.00",
            "page_views": 8500,
            "impressions": 17000,
            "clicks": 210
        }
    ]
}
```

**Frontend Usage:**
```tsx
function AdSenseWidget() {
    const [data, setData] = useState(null);
    
    useEffect(() => {
        fetch('/api/admin/adsense/earnings/', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(setData);
    }, []);
    
    if (!data?.connected) {
        return <AdSenseConnectPrompt />;
    }
    
    return (
        <div className="adsense-widget">
            <h3>AdSense Revenue (USD)</h3>
            
            <div className="earnings-grid">
                <EarningsCard label="Today" value={data.earnings.today} />
                <EarningsCard label="This Week" value={data.earnings.this_week} />
                <EarningsCard label="This Month" value={data.earnings.this_month} />
            </div>
            
            <h4>Top Performing Pages</h4>
            <TopPagesTable pages={data.top_pages} />
        </div>
    );
}
```

---

### Get Detailed Reports

#### GET `/api/admin/adsense/reports/`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | string | Start date (YYYY-MM-DD) |
| `end_date` | string | End date (YYYY-MM-DD) |
| `dimension` | string | `DATE`, `MONTH`, `AD_UNIT_NAME`, `COUNTRY_NAME`, `PLATFORM_TYPE_NAME` |

**Example Request:**
```http
GET /api/admin/adsense/reports/?start_date=2025-12-01&end_date=2025-12-31&dimension=DATE
Authorization: Bearer {token}
```

**Response:**
```json
{
    "connected": true,
    "start_date": "2025-12-01",
    "end_date": "2025-12-31",
    "dimension": "DATE",
    "report": {
        "rows": [
            {
                "date": "2025-12-01",
                "estimated_earnings": "45.32",
                "impressions": 12500,
                "clicks": 350,
                "page_views": 8500,
                "ad_requests_ctr": "2.8"
            }
        ],
        "totals": {
            "estimated_earnings": "1400.00",
            "impressions": 387500,
            "clicks": 10850,
            "page_views": 263500
        },
        "row_count": 31
    }
}
```

---

### Get AdSense Payment History

#### GET `/api/admin/adsense/payments/`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | number | Maximum payments to return (default: 12) |

**Response:**
```json
{
    "connected": true,
    "payments": [
        {
            "date": "2025-12-21",
            "amount": "1250.00",
            "name": "accounts/pub-xxx/payments/2025-12"
        },
        {
            "date": "2025-11-21",
            "amount": "980.00",
            "name": "accounts/pub-xxx/payments/2025-11"
        }
    ],
    "count": 12
}
```

---

## 🎨 UI Components Reference

### Recommended Page Structure

```
/admin/finance/
├── /dashboard          → FinanceDashboardView
├── /payments           → PaymentHistoryView
├── /revenue            → RevenueSummaryView
├── /subscribers        → SubscribersListView
└── /adsense
    ├── /settings       → AdSense connection management
    └── /reports        → Detailed AdSense reports
```

### Access Check Component

```tsx
// components/FinanceGuard.tsx
import { useAuth } from '@/hooks/useAuth';
import { Navigate } from 'react-router-dom';

export function FinanceGuard({ children }: { children: React.ReactNode }) {
    const { user } = useAuth();
    
    // Only SUPER_ADMIN can access finance pages
    if (user?.role !== 'SUPER_ADMIN') {
        return <Navigate to="/admin/dashboard" replace />;
    }
    
    return <>{children}</>;
}

// Usage in routes
<Route 
    path="/admin/finance/*" 
    element={
        <FinanceGuard>
            <FinanceRoutes />
        </FinanceGuard>
    } 
/>
```

### Navigation Visibility

```tsx
// components/AdminSidebar.tsx
function AdminSidebar() {
    const { user } = useAuth();
    const isSuperAdmin = user?.role === 'SUPER_ADMIN';
    
    return (
        <nav>
            {/* Always visible */}
            <NavItem to="/admin/dashboard" icon={<DashboardIcon />}>Dashboard</NavItem>
            <NavItem to="/admin/users" icon={<UsersIcon />}>Users</NavItem>
            <NavItem to="/admin/farms" icon={<FarmIcon />}>Farms</NavItem>
            
            {/* Only for SUPER_ADMIN */}
            {isSuperAdmin && (
                <>
                    <NavDivider label="Platform Finance" />
                    <NavItem to="/admin/finance/dashboard" icon={<ChartIcon />}>
                        Finance Dashboard
                    </NavItem>
                    <NavItem to="/admin/finance/payments" icon={<PaymentIcon />}>
                        Payments
                    </NavItem>
                    <NavItem to="/admin/finance/revenue" icon={<RevenueIcon />}>
                        Revenue
                    </NavItem>
                    <NavItem to="/admin/finance/subscribers" icon={<SubscribersIcon />}>
                        Subscribers
                    </NavItem>
                    <NavItem to="/admin/finance/adsense" icon={<GoogleIcon />}>
                        AdSense
                    </NavItem>
                </>
            )}
        </nav>
    );
}
```

---

## 🔄 Error Handling

### 403 Forbidden Response

When a non-SUPER_ADMIN tries to access financial endpoints:

```json
{
    "detail": "You do not have permission to perform this action."
}
```

**Frontend Handling:**
```tsx
async function fetchFinanceData(endpoint: string) {
    const res = await fetch(endpoint, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (res.status === 403) {
        // Redirect to main dashboard
        toast.error('Access denied. Finance data is restricted.');
        navigate('/admin/dashboard');
        return null;
    }
    
    if (!res.ok) {
        throw new Error('Failed to fetch data');
    }
    
    return res.json();
}
```

---

## 📱 Responsive Considerations

- Finance dashboard should work on tablet (admin use case)
- Mobile view may be simplified to key metrics only
- Charts should be responsive with proper touch interactions
- Tables should scroll horizontally on smaller screens

---

## 🔐 Security Notes

1. **Never expose** financial endpoints to non-SUPER_ADMIN users
2. **Cache tokens** securely - AdSense OAuth tokens are stored server-side
3. **Audit logging** - Consider logging all financial data access
4. **HTTPS only** - All financial API calls must be over HTTPS
5. **Rate limiting** - AdSense API has quotas; frontend should handle gracefully

---

## 📊 Export Features (Future)

Consider adding export functionality:
- CSV export for payments list
- PDF export for revenue reports
- Excel export for subscriber data

These would be additional endpoints:
- `GET /api/admin/payments/export/?format=csv`
- `GET /api/admin/revenue/export/?format=pdf`
