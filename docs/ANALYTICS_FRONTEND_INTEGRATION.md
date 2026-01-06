# Analytics Dashboard - Frontend Integration Guide

## Quick Start

### Base Configuration

```typescript
// api/config.ts
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const analyticsApi = {
  baseUrl: `${API_BASE_URL}/api/admin/analytics`,
  
  // Helper to add auth header
  getHeaders: (token: string) => ({
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  }),
};
```

---

## TypeScript Interfaces

### Core Types

```typescript
// types/analytics.ts

// ============================================================================
// EXECUTIVE OVERVIEW
// ============================================================================

interface FarmerStats {
  total: number;
  active: number;
  new_this_month: number;
}

interface FarmStats {
  total: number;
  approved: number;
  operational: number;
  pending_setup: number;
}

interface BirdStats {
  total: number;
  capacity: number;
  utilization_percent: number;
}

interface ProductionStats {
  eggs_this_month: number;
  good_eggs_this_month: number;
  mortality_this_month: number;
}

interface ApplicationStats {
  pending: number;
  submitted: number;
  constituency_review: number;
  regional_review: number;
  national_review: number;
}

interface MarketplaceOverviewStats {
  orders_this_month: number;
  transaction_volume_ghs: number;
}

interface ExecutiveOverview {
  farmers: FarmerStats;
  farms: FarmStats;
  birds: BirdStats;
  production: ProductionStats;
  applications: ApplicationStats;
  marketplace: MarketplaceOverviewStats;
  as_of: string; // ISO datetime
}

// ============================================================================
// PROGRAM METRICS
// ============================================================================

interface ApplicationPipeline {
  pipeline: Record<string, number>;
  summary: {
    total: number;
    pending: number;
    approved: number;
    rejected: number;
    approval_rate: number;
  };
}

interface RegistrationTrendItem {
  month: string; // "2025-08"
  registrations: number;
}

interface RegionFarmCount {
  region: string;
  farm_count: number;
}

interface BatchEnrollmentItem {
  id: string;
  name: string;
  target_capacity: number;
  approved: number;
  pending: number;
  fill_rate: number;
}

interface BatchEnrollmentStats {
  active_batches: number;
  batches: BatchEnrollmentItem[];
}

interface ProgramMetrics {
  application_pipeline: ApplicationPipeline;
  registration_trend: RegistrationTrendItem[];
  farms_by_region: RegionFarmCount[];
  batch_enrollment: BatchEnrollmentStats;
}

// ============================================================================
// PRODUCTION MONITORING
// ============================================================================

interface WeeklyProduction {
  eggs_collected: number;
  good_eggs: number;
  mortality: number;
  avg_production_rate: number;
}

interface MonthlyProduction {
  eggs_collected: number;
  good_eggs: number;
  mortality: number;
}

interface PopulationStats {
  total_birds: number;
  mortality_rate_weekly: number;
}

interface ProductionOverview {
  weekly: WeeklyProduction;
  monthly: MonthlyProduction;
  population: PopulationStats;
}

interface ProductionTrendItem {
  date: string; // "2025-12-05"
  eggs: number;
  good_eggs: number;
  mortality: number;
}

interface RegionProduction {
  region: string;
  eggs_this_month: number;
}

interface TopFarm {
  farm_id: string;
  farm_name: string;
  constituency: string;
  eggs_this_month: number;
  avg_production_rate: number;
}

interface UnderperformingFarm {
  farm_id: string;
  farm_name: string;
  issue: string;
  mortality_count: number;
  mortality_rate: number;
  eggs_produced: number;
}

interface ProductionMetrics {
  overview: ProductionOverview;
  trend: ProductionTrendItem[];
  by_region: RegionProduction[];
  top_farms: TopFarm[];
  underperforming: UnderperformingFarm[];
}

// ============================================================================
// MARKETPLACE ACTIVITY
// ============================================================================

interface MonthlyMarketplaceActivity {
  marketplace_orders: number;
  marketplace_volume_ghs: number;
  guest_orders: number;
  guest_volume_ghs: number;
  total_orders: number;
  total_volume_ghs: number;
  avg_order_value_ghs: number;
}

interface SellerStats {
  active_this_month: number;
  total_with_products: number;
}

interface ProductStats {
  active_listings: number;
}

interface MarketplaceActivity {
  this_month: MonthlyMarketplaceActivity;
  sellers: SellerStats;
  products: ProductStats;
}

interface RegionSales {
  region: string;
  volume_ghs: number;
  order_count: number;
}

interface TopSeller {
  farm_id: string;
  farm_name: string;
  farmer_name: string;
  sales_volume_ghs: number;
  order_count: number;
}

interface MarketplaceMetrics {
  activity: MarketplaceActivity;
  sales_by_region: RegionSales[];
  top_sellers: TopSeller[];
}

// ============================================================================
// ALERTS & WATCHLIST
// ============================================================================

interface Alert {
  type: string;
  message: string;
  farm_id?: string;
  count?: number;
}

interface Alerts {
  critical: Alert[];
  warning: Alert[];
  info: Alert[];
}

interface WatchlistItem {
  farm_id: string;
  farm_name: string;
  reason: string;
  details: string;
  severity: 'high' | 'medium' | 'low';
}

interface AlertsAndWatchlist {
  alerts: Alerts;
  watchlist: WatchlistItem[];
}

// ============================================================================
// FULL DASHBOARD
// ============================================================================

interface FullDashboard {
  overview: ExecutiveOverview;
  application_pipeline: ApplicationPipeline;
  production: ProductionOverview;
  marketplace: MarketplaceActivity;
  alerts: Alerts;
}

// ============================================================================
// PLATFORM REVENUE (SUPER_ADMIN ONLY)
// ============================================================================

interface AdvertisingRevenue {
  adsense_this_month: number;
  partner_conversions: number;
  partner_conversion_value: number;
  platform_commission: number;
  partner_payments_paid: number;
  partner_payments_pending: number;
}

interface MarketplaceActivationRevenue {
  paid_farms: number;
  subsidized_farms: number;
  subscription_revenue: number;
}

interface RevenueTotals {
  ad_revenue_this_month: number;
  platform_fees_this_month: number;
  net_revenue_estimate: number;
}

interface PlatformRevenueOverview {
  advertising: AdvertisingRevenue;
  marketplace_activation: MarketplaceActivationRevenue;
  totals: RevenueTotals;
  as_of: string;
}

interface RevenueTrendItem {
  month: string;
  adsense_revenue: number;
  conversion_revenue: number;
  conversion_count: number;
  total: number;
}

interface TopOffer {
  offer_id: string;
  title: string;
  partner: string;
  conversions: number;
  revenue: number;
}

interface AdvertisingPerformance {
  summary: {
    active_offers: number;
    clicks_this_month: number;
    conversions_this_month: number;
    conversion_rate: number;
    conversion_value: number;
  };
  top_offers: TopOffer[];
}

interface PartnerPayment {
  id: string;
  partner: string;
  amount: number;
  status: 'pending' | 'paid' | 'cancelled';
  payment_date: string | null;
  created_at: string;
}

interface ActivationBreakdown {
  none: number;
  government_subsidized: number;
  standard: number;
  verified: number;
}

interface ActivationStats {
  breakdown: ActivationBreakdown;
  pricing: { activation_fee_ghs: number };
  revenue: {
    paying_farms: number;
    potential_monthly_ghs: number;
  };
}
```

---

## API Service Layer

```typescript
// services/analyticsService.ts
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class AnalyticsService {
  private getAuthHeader() {
    const token = localStorage.getItem('accessToken');
    return { Authorization: `Bearer ${token}` };
  }

  // ========================================================================
  // YEA ADMIN ENDPOINTS
  // ========================================================================

  /**
   * Get full dashboard data in one call
   * Use for initial load
   */
  async getFullDashboard(): Promise<FullDashboard> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/`,
      { headers: this.getAuthHeader() }
    );
    return response.data;
  }

  /**
   * Get executive overview cards only
   * Use for quick refresh
   */
  async getOverview(): Promise<ExecutiveOverview> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/overview/`,
      { headers: this.getAuthHeader() }
    );
    return response.data;
  }

  /**
   * Get program metrics (applications, enrollments, registrations)
   */
  async getProgramMetrics(months: number = 6): Promise<ProgramMetrics> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/program/`,
      { 
        headers: this.getAuthHeader(),
        params: { months }
      }
    );
    return response.data;
  }

  /**
   * Get production monitoring data
   */
  async getProductionMetrics(days: number = 30, limit: number = 10): Promise<ProductionMetrics> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/production/`,
      { 
        headers: this.getAuthHeader(),
        params: { days, limit }
      }
    );
    return response.data;
  }

  /**
   * Get marketplace activity (transaction volume, NOT platform revenue)
   */
  async getMarketplaceMetrics(limit: number = 10): Promise<MarketplaceMetrics> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/marketplace/`,
      { 
        headers: this.getAuthHeader(),
        params: { limit }
      }
    );
    return response.data;
  }

  /**
   * Get alerts and watchlist
   */
  async getAlerts(limit: number = 20): Promise<AlertsAndWatchlist> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/alerts/`,
      { 
        headers: this.getAuthHeader(),
        params: { limit }
      }
    );
    return response.data;
  }

  // ========================================================================
  // PLATFORM REVENUE ENDPOINTS (SUPER_ADMIN ONLY)
  // ========================================================================

  /**
   * Get platform revenue overview
   * Only accessible to SUPER_ADMIN and YEA_OFFICIAL
   */
  async getPlatformRevenue(): Promise<PlatformRevenueOverview> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/platform-revenue/`,
      { headers: this.getAuthHeader() }
    );
    return response.data;
  }

  /**
   * Get revenue trend over months
   */
  async getRevenueTrend(months: number = 6): Promise<RevenueTrendItem[]> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/platform-revenue/trend/`,
      { 
        headers: this.getAuthHeader(),
        params: { months }
      }
    );
    return response.data;
  }

  /**
   * Get advertising performance
   */
  async getAdvertisingPerformance(): Promise<AdvertisingPerformance> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/platform-revenue/advertising/`,
      { headers: this.getAuthHeader() }
    );
    return response.data;
  }

  /**
   * Get partner payments
   */
  async getPartnerPayments(status?: 'pending' | 'paid' | 'cancelled'): Promise<PartnerPayment[]> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/platform-revenue/partner-payments/`,
      { 
        headers: this.getAuthHeader(),
        params: status ? { status } : {}
      }
    );
    return response.data;
  }

  /**
   * Get marketplace activation statistics
   */
  async getActivationStats(): Promise<ActivationStats> {
    const response = await axios.get(
      `${API_URL}/api/admin/analytics/platform-revenue/activation/`,
      { headers: this.getAuthHeader() }
    );
    return response.data;
  }
}

export const analyticsService = new AnalyticsService();
```

---

## React Hooks

```typescript
// hooks/useAnalytics.ts
import { useState, useEffect, useCallback } from 'react';
import { analyticsService } from '../services/analyticsService';

// Hook for overview data with auto-refresh
export function useOverview(refreshInterval = 300000) { // 5 minutes
  const [data, setData] = useState<ExecutiveOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const result = await analyticsService.getOverview();
      setData(result);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load overview');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchData, refreshInterval]);

  return { data, loading, error, refetch: fetchData };
}

// Hook for production data
export function useProductionMetrics(days = 30, limit = 10) {
  const [data, setData] = useState<ProductionMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const result = await analyticsService.getProductionMetrics(days, limit);
      setData(result);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load production data');
    } finally {
      setLoading(false);
    }
  }, [days, limit]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// Hook for alerts with frequent refresh
export function useAlerts(refreshInterval = 120000) { // 2 minutes
  const [data, setData] = useState<AlertsAndWatchlist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasNewAlerts, setHasNewAlerts] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const result = await analyticsService.getAlerts();
      
      // Check for new critical alerts
      if (data && result.alerts.critical.length > data.alerts.critical.length) {
        setHasNewAlerts(true);
      }
      
      setData(result);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
  }, [data]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]); // Note: don't include fetchData to avoid infinite loop

  const clearNewAlerts = () => setHasNewAlerts(false);

  return { data, loading, error, refetch: fetchData, hasNewAlerts, clearNewAlerts };
}

// Hook for platform revenue (SUPER_ADMIN only)
export function usePlatformRevenue() {
  const [data, setData] = useState<PlatformRevenueOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const result = await analyticsService.getPlatformRevenue();
      setData(result);
      setError(null);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('Access denied. Platform revenue is only visible to Super Admins.');
      } else {
        setError(err.response?.data?.detail || 'Failed to load revenue data');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}
```

---

## React Components

### Overview Cards

```tsx
// components/analytics/OverviewCards.tsx
import React from 'react';
import { useOverview } from '../../hooks/useAnalytics';
import { Card, CardContent, Typography, Grid, Skeleton, Chip } from '@mui/material';
import { 
  People, Agriculture, Egg, ShoppingCart, 
  Assignment, TrendingUp 
} from '@mui/icons-material';

interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: React.ReactNode;
  color?: string;
  trend?: number;
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, value, subtitle, icon, color = '#1976d2', trend 
}) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Grid container spacing={2} alignItems="center">
        <Grid item>
          <div style={{ 
            backgroundColor: `${color}20`, 
            borderRadius: 8, 
            padding: 12,
            color 
          }}>
            {icon}
          </div>
        </Grid>
        <Grid item xs>
          <Typography variant="body2" color="textSecondary">
            {title}
          </Typography>
          <Typography variant="h4" fontWeight="bold">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="textSecondary">
              {subtitle}
            </Typography>
          )}
        </Grid>
        {trend !== undefined && (
          <Grid item>
            <Chip 
              size="small"
              label={`${trend > 0 ? '+' : ''}${trend}%`}
              color={trend >= 0 ? 'success' : 'error'}
              icon={<TrendingUp />}
            />
          </Grid>
        )}
      </Grid>
    </CardContent>
  </Card>
);

export const OverviewCards: React.FC = () => {
  const { data, loading, error } = useOverview();

  if (loading) {
    return (
      <Grid container spacing={3}>
        {[...Array(6)].map((_, i) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={i}>
            <Skeleton variant="rectangular" height={120} />
          </Grid>
        ))}
      </Grid>
    );
  }

  if (error || !data) {
    return <Typography color="error">{error || 'Failed to load data'}</Typography>;
  }

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} sm={6} md={4} lg={2}>
        <StatCard
          title="Total Farmers"
          value={data.farmers.total}
          subtitle={`${data.farmers.new_this_month} new this month`}
          icon={<People />}
          color="#4caf50"
        />
      </Grid>
      
      <Grid item xs={12} sm={6} md={4} lg={2}>
        <StatCard
          title="Active Farms"
          value={data.farms.operational}
          subtitle={`${data.farms.pending_setup} pending setup`}
          icon={<Agriculture />}
          color="#2196f3"
        />
      </Grid>
      
      <Grid item xs={12} sm={6} md={4} lg={2}>
        <StatCard
          title="Total Birds"
          value={data.birds.total}
          subtitle={`${data.birds.utilization_percent}% capacity`}
          icon={<Egg />}
          color="#ff9800"
        />
      </Grid>
      
      <Grid item xs={12} sm={6} md={4} lg={2}>
        <StatCard
          title="Eggs This Month"
          value={data.production.eggs_this_month}
          icon={<Egg />}
          color="#9c27b0"
        />
      </Grid>
      
      <Grid item xs={12} sm={6} md={4} lg={2}>
        <StatCard
          title="Pending Applications"
          value={data.applications.pending}
          icon={<Assignment />}
          color="#f44336"
        />
      </Grid>
      
      <Grid item xs={12} sm={6} md={4} lg={2}>
        <StatCard
          title="Marketplace Volume"
          value={`GHS ${data.marketplace.transaction_volume_ghs.toLocaleString()}`}
          subtitle={`${data.marketplace.orders_this_month} orders`}
          icon={<ShoppingCart />}
          color="#00bcd4"
        />
      </Grid>
    </Grid>
  );
};
```

### Application Pipeline Chart

```tsx
// components/analytics/ApplicationPipeline.tsx
import React from 'react';
import { Card, CardContent, CardHeader, Box } from '@mui/material';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell 
} from 'recharts';

interface ApplicationPipelineProps {
  data: ApplicationPipeline;
}

const COLORS = {
  'Submitted': '#90caf9',
  'Constituency Review': '#64b5f6',
  'Regional Review': '#42a5f5',
  'National Review': '#2196f3',
  'Approved': '#4caf50',
  'Account Created': '#81c784',
  'Rejected': '#f44336',
  'Changes Requested': '#ff9800',
};

export const ApplicationPipelineChart: React.FC<ApplicationPipelineProps> = ({ data }) => {
  const chartData = Object.entries(data.pipeline).map(([name, value]) => ({
    name,
    value,
    color: COLORS[name as keyof typeof COLORS] || '#9e9e9e',
  }));

  return (
    <Card>
      <CardHeader 
        title="Application Pipeline"
        subheader={`${data.summary.approval_rate}% approval rate`}
      />
      <CardContent>
        <Box sx={{ width: '100%', height: 300 }}>
          <ResponsiveContainer>
            <BarChart data={chartData} layout="vertical">
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={150} />
              <Tooltip />
              <Bar dataKey="value">
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};
```

### Alerts Panel

```tsx
// components/analytics/AlertsPanel.tsx
import React from 'react';
import { 
  Card, CardContent, CardHeader, List, ListItem, 
  ListItemIcon, ListItemText, Chip, Badge, IconButton,
  Collapse, Alert as MuiAlert
} from '@mui/material';
import { 
  Error, Warning, Info, ExpandMore, ExpandLess,
  Visibility
} from '@mui/icons-material';
import { useAlerts } from '../../hooks/useAnalytics';
import { useNavigate } from 'react-router-dom';

const severityConfig = {
  critical: { icon: <Error />, color: 'error' as const, label: 'Critical' },
  warning: { icon: <Warning />, color: 'warning' as const, label: 'Warning' },
  info: { icon: <Info />, color: 'info' as const, label: 'Info' },
};

export const AlertsPanel: React.FC = () => {
  const { data, loading, hasNewAlerts, clearNewAlerts } = useAlerts();
  const [expanded, setExpanded] = React.useState<string[]>(['critical']);
  const navigate = useNavigate();

  if (loading || !data) return null;

  const handleToggle = (severity: string) => {
    setExpanded(prev => 
      prev.includes(severity) 
        ? prev.filter(s => s !== severity)
        : [...prev, severity]
    );
  };

  const handleAlertClick = (alert: Alert) => {
    clearNewAlerts();
    if (alert.farm_id) {
      navigate(`/admin/farms/${alert.farm_id}`);
    }
  };

  const totalAlerts = 
    data.alerts.critical.length + 
    data.alerts.warning.length + 
    data.alerts.info.length;

  return (
    <Card>
      <CardHeader
        title={
          <Badge 
            badgeContent={hasNewAlerts ? 'New' : 0} 
            color="error"
          >
            System Alerts ({totalAlerts})
          </Badge>
        }
      />
      <CardContent>
        {(['critical', 'warning', 'info'] as const).map(severity => {
          const alerts = data.alerts[severity];
          const config = severityConfig[severity];
          
          if (alerts.length === 0) return null;

          return (
            <React.Fragment key={severity}>
              <ListItem 
                button 
                onClick={() => handleToggle(severity)}
                sx={{ bgcolor: 'grey.100', borderRadius: 1, mb: 1 }}
              >
                <ListItemIcon sx={{ color: `${config.color}.main` }}>
                  {config.icon}
                </ListItemIcon>
                <ListItemText 
                  primary={`${config.label} (${alerts.length})`}
                />
                {expanded.includes(severity) ? <ExpandLess /> : <ExpandMore />}
              </ListItem>
              
              <Collapse in={expanded.includes(severity)}>
                <List dense sx={{ pl: 2 }}>
                  {alerts.map((alert, idx) => (
                    <ListItem 
                      key={idx}
                      secondaryAction={
                        alert.farm_id && (
                          <IconButton 
                            edge="end" 
                            size="small"
                            onClick={() => handleAlertClick(alert)}
                          >
                            <Visibility fontSize="small" />
                          </IconButton>
                        )
                      }
                    >
                      <MuiAlert 
                        severity={config.color}
                        sx={{ width: '100%' }}
                      >
                        {alert.message}
                      </MuiAlert>
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            </React.Fragment>
          );
        })}
      </CardContent>
    </Card>
  );
};
```

### Production Trend Chart

```tsx
// components/analytics/ProductionTrendChart.tsx
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, ToggleButtonGroup, ToggleButton } from '@mui/material';
import { 
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  CartesianGrid, Legend 
} from 'recharts';
import { useProductionMetrics } from '../../hooks/useAnalytics';

export const ProductionTrendChart: React.FC = () => {
  const [days, setDays] = useState(30);
  const { data, loading } = useProductionMetrics(days);

  if (loading || !data) return null;

  return (
    <Card>
      <CardHeader 
        title="Production Trend"
        action={
          <ToggleButtonGroup
            value={days}
            exclusive
            onChange={(_, v) => v && setDays(v)}
            size="small"
          >
            <ToggleButton value={7}>7D</ToggleButton>
            <ToggleButton value={30}>30D</ToggleButton>
            <ToggleButton value={90}>90D</ToggleButton>
          </ToggleButtonGroup>
        }
      />
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={data.trend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tickFormatter={(v) => new Date(v).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
            />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip 
              labelFormatter={(v) => new Date(v).toLocaleDateString()}
            />
            <Legend />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="eggs" 
              stroke="#4caf50" 
              name="Eggs Collected"
              dot={false}
            />
            <Line 
              yAxisId="right"
              type="monotone" 
              dataKey="mortality" 
              stroke="#f44336" 
              name="Mortality"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};
```

### Platform Revenue Tab (SUPER_ADMIN Only)

```tsx
// components/analytics/PlatformRevenueTab.tsx
import React from 'react';
import { 
  Grid, Card, CardContent, CardHeader, Typography, 
  Table, TableBody, TableCell, TableHead, TableRow,
  Chip, Box, Alert
} from '@mui/material';
import { 
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { usePlatformRevenue } from '../../hooks/useAnalytics';
import { analyticsService } from '../../services/analyticsService';

const COLORS = ['#4caf50', '#2196f3', '#ff9800', '#9e9e9e'];

export const PlatformRevenueTab: React.FC = () => {
  const { data, loading, error } = usePlatformRevenue();
  const [trend, setTrend] = React.useState<RevenueTrendItem[]>([]);
  const [activation, setActivation] = React.useState<ActivationStats | null>(null);

  React.useEffect(() => {
    analyticsService.getRevenueTrend(6).then(setTrend).catch(console.error);
    analyticsService.getActivationStats().then(setActivation).catch(console.error);
  }, []);

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (loading || !data) return null;

  const pieData = activation ? [
    { name: 'Standard', value: activation.breakdown.standard },
    { name: 'Verified', value: activation.breakdown.verified },
    { name: 'Subsidized', value: activation.breakdown.government_subsidized },
    { name: 'None', value: activation.breakdown.none },
  ] : [];

  return (
    <Grid container spacing={3}>
      {/* Revenue Overview Cards */}
      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              Net Revenue Estimate
            </Typography>
            <Typography variant="h4" color="primary">
              GHS {data.totals.net_revenue_estimate.toLocaleString()}
            </Typography>
            <Typography variant="caption">This month</Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              Ad Revenue
            </Typography>
            <Typography variant="h4">
              GHS {data.totals.ad_revenue_this_month.toLocaleString()}
            </Typography>
            <Typography variant="caption">
              {data.advertising.partner_conversions} conversions
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              Marketplace Activation
            </Typography>
            <Typography variant="h4">
              GHS {data.totals.platform_fees_this_month.toLocaleString()}
            </Typography>
            <Typography variant="caption">
              {data.marketplace_activation.paid_farms} paying farms
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      {/* Revenue Trend Chart */}
      <Grid item xs={12} md={8}>
        <Card>
          <CardHeader title="Revenue Trend" />
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trend}>
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="adsense_revenue" 
                  stroke="#4caf50" 
                  name="AdSense"
                />
                <Line 
                  type="monotone" 
                  dataKey="conversion_revenue" 
                  stroke="#2196f3" 
                  name="Partner Conversions"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Activation Breakdown Pie */}
      <Grid item xs={12} md={4}>
        <Card>
          <CardHeader title="Farm Activation Breakdown" />
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="value"
                  label
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Partner Payments Table */}
      <Grid item xs={12}>
        <Card>
          <CardHeader title="Partner Payments" />
          <CardContent>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
              Pending: GHS {data.advertising.partner_payments_pending.toLocaleString()} | 
              Paid: GHS {data.advertising.partner_payments_paid.toLocaleString()}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};
```

---

## Main Dashboard Page

```tsx
// pages/admin/AnalyticsDashboard.tsx
import React, { useState } from 'react';
import { 
  Box, Container, Typography, Tabs, Tab, 
  Paper, CircularProgress 
} from '@mui/material';
import { OverviewCards } from '../../components/analytics/OverviewCards';
import { ApplicationPipelineChart } from '../../components/analytics/ApplicationPipeline';
import { ProductionTrendChart } from '../../components/analytics/ProductionTrendChart';
import { AlertsPanel } from '../../components/analytics/AlertsPanel';
import { PlatformRevenueTab } from '../../components/analytics/PlatformRevenueTab';
import { useAuth } from '../../hooks/useAuth';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index} style={{ paddingTop: 24 }}>
    {value === index && children}
  </div>
);

export const AnalyticsDashboard: React.FC = () => {
  const [tab, setTab] = useState(0);
  const { user } = useAuth();
  
  // Check if user can see platform revenue
  const canSeePlatformRevenue = ['SUPER_ADMIN', 'YEA_OFFICIAL'].includes(user?.role || '');

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        <Typography variant="h4" gutterBottom>
          Analytics Dashboard
        </Typography>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          {user?.role === 'REGIONAL_COORDINATOR' && `Showing data for ${user.region}`}
          {user?.role === 'CONSTITUENCY_OFFICIAL' && `Showing data for ${user.constituency}`}
        </Typography>

        {/* Overview Cards - Always visible */}
        <Box sx={{ mb: 4 }}>
          <OverviewCards />
        </Box>

        {/* Tabbed Content */}
        <Paper sx={{ mb: 3 }}>
          <Tabs 
            value={tab} 
            onChange={(_, v) => setTab(v)}
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label="Program" />
            <Tab label="Production" />
            <Tab label="Marketplace" />
            <Tab label="Alerts" />
            {canSeePlatformRevenue && <Tab label="Platform Revenue" />}
          </Tabs>
        </Paper>

        <TabPanel value={tab} index={0}>
          <ApplicationPipelineChart />
          {/* Add more program components */}
        </TabPanel>

        <TabPanel value={tab} index={1}>
          <ProductionTrendChart />
          {/* Add top/underperforming farms tables */}
        </TabPanel>

        <TabPanel value={tab} index={2}>
          {/* Marketplace activity components */}
        </TabPanel>

        <TabPanel value={tab} index={3}>
          <AlertsPanel />
        </TabPanel>

        {canSeePlatformRevenue && (
          <TabPanel value={tab} index={4}>
            <PlatformRevenueTab />
          </TabPanel>
        )}
      </Box>
    </Container>
  );
};
```

---

## Route Configuration

```tsx
// routes/adminRoutes.tsx
import { AnalyticsDashboard } from '../pages/admin/AnalyticsDashboard';

// Add to your admin routes
{
  path: '/admin/analytics',
  element: <AnalyticsDashboard />,
  // Optional: Add role-based guard
  loader: () => {
    const user = getCurrentUser();
    const allowedRoles = [
      'SUPER_ADMIN', 'YEA_OFFICIAL', 'NATIONAL_ADMIN',
      'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL'
    ];
    if (!allowedRoles.includes(user?.role)) {
      throw redirect('/admin/dashboard');
    }
    return null;
  }
}
```

---

## Error Handling

```typescript
// utils/analyticsErrors.ts
export function handleAnalyticsError(error: any): string {
  if (error.response) {
    switch (error.response.status) {
      case 401:
        return 'Your session has expired. Please log in again.';
      case 403:
        return 'You do not have permission to view this data.';
      case 404:
        return 'The requested data was not found.';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return error.response.data?.detail || 'An unexpected error occurred.';
    }
  }
  return 'Network error. Please check your connection.';
}
```

---

## Formatting Utilities

```typescript
// utils/formatters.ts
export const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toLocaleString();
};

export const formatCurrency = (amount: number, currency = 'GHS'): string => {
  return `${currency} ${amount.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

export const formatPercent = (value: number): string => {
  return `${value.toFixed(1)}%`;
};

export const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

export const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};
```

---

## Environment Variables

```env
# .env.development
REACT_APP_API_URL=http://localhost:8000

# .env.production
REACT_APP_API_URL=https://api.yeapms.gov.gh
```

---

## Dependencies

```json
{
  "dependencies": {
    "axios": "^1.6.0",
    "recharts": "^2.10.0",
    "@mui/material": "^5.14.0",
    "@mui/icons-material": "^5.14.0",
    "react-router-dom": "^6.20.0"
  }
}
```

---

## Testing

```typescript
// __tests__/analyticsService.test.ts
import { analyticsService } from '../services/analyticsService';

describe('AnalyticsService', () => {
  beforeEach(() => {
    localStorage.setItem('accessToken', 'test-token');
  });

  it('should fetch overview data', async () => {
    const data = await analyticsService.getOverview();
    expect(data).toHaveProperty('farmers');
    expect(data).toHaveProperty('farms');
    expect(data).toHaveProperty('birds');
  });

  it('should handle 403 for platform revenue when not SUPER_ADMIN', async () => {
    // Mock user as NATIONAL_ADMIN
    await expect(analyticsService.getPlatformRevenue())
      .rejects.toHaveProperty('response.status', 403);
  });
});
```
