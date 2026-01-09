# Frontend Fee Removal Guide

> **CRITICAL UPDATE: Transaction Fees / Platform Fees Have Been REMOVED**
> 
> The only fee for farmers is the **GHS 50/month Marketplace Activation Fee**.
> Transaction commissions (2%, 3%, 5%) are **NOT applied** - farmers keep 100% of sales.

---

## Summary of Changes

### What Was Removed

| Fee Type | Old Value | Current Value | Status |
|----------|-----------|---------------|--------|
| Platform Commission (Tier 1) | 5% on sales < GHS 100 | **0%** | ❌ REMOVED |
| Platform Commission (Tier 2) | 3% on sales GHS 100-500 | **0%** | ❌ REMOVED |
| Platform Commission (Tier 3) | 2% on sales > GHS 500 | **0%** | ❌ REMOVED |
| Paystack Processing Fee | 1.5% + GHS 0.10 | **0%** | ❌ REMOVED |
| Verified Seller Tier Fee | GHS 100-200/month | **N/A** | ❌ REMOVED |

### What Remains

| Fee Type | Amount | Description | Status |
|----------|--------|-------------|--------|
| Marketplace Activation Fee | **GHS 50/month** | Monthly access to marketplace features | ✅ ACTIVE |

---

## Why Fees Were Removed

1. **Payments happen OFF-PLATFORM**: Farmers receive payments directly (cash, MoMo, bank transfer)
2. **Platform is for RECORD-KEEPING only**: Farmers use the marketplace to find buyers and record sales
3. **Ghanaian farmers are fee-sensitive**: Additional percentage fees would discourage platform adoption
4. **Trust building phase**: During initial rollout, keeping fees minimal increases adoption

---

## Backend API Changes

### Public Platform Settings Endpoint

**Endpoint:** `GET /api/public/platform-settings/`

**Current Response:**
```json
{
  "marketplace_activation_fee": "50.00",
  "marketplace_trial_days": 14,
  "free_tier_can_view_marketplace": true,
  "free_tier_can_view_prices": true,
  "free_tier_can_access_education": true
}
```

**Note:** This endpoint does NOT return any commission/fee percentage fields. If your frontend needs fee information, the only fee is `marketplace_activation_fee`.

### Admin Platform Settings (For Admin Dashboard)

**Endpoint:** `GET /api/admin/platform-settings/`

This returns all settings including the suspended commission fields. Key field:

```json
{
  "enable_transaction_commission": false,
  ...
}
```

When `enable_transaction_commission` is `false`:
- All commission calculations return `0`
- `platform_commission` field on sales = `0`
- `paystack_fee` field on sales = `0`
- `farmer_payout` = `subtotal` (100% to farmer)

---

## Frontend Components to Update

Based on the screenshot showing "Platform Fees (2%)" with "-GHS 1409.60", you need to remove this from:

### 1. Sales Analytics Page (`/marketplace/analytics`)

**REMOVE:**
```tsx
// ❌ REMOVE THIS SECTION
<div className="platform-fees">
  <span>Platform Fees (2%)</span>
  <span className="amount">-GHS {platformFees.toFixed(2)}</span>
</div>
```

**The fee calculation should be:**
```tsx
// ✅ CORRECT - No platform fees
const platformFees = 0; // Always zero - fees are suspended
const farmerReceives = totalSales; // Farmer keeps 100%
```

### 2. Sales Summary / Revenue Cards

**REMOVE any hardcoded fee calculations:**
```tsx
// ❌ WRONG - Hardcoded 2% fee
const platformFee = totalRevenue * 0.02;
const netRevenue = totalRevenue - platformFee;

// ✅ CORRECT - No fees
const platformFee = 0;
const netRevenue = totalRevenue; // Full amount
```

### 3. Sale Record Forms / Receipts

**If showing "Platform Fee" or "Commission" on receipts, remove them:**
```tsx
// ❌ REMOVE from sale details/receipts
<LineItem label="Platform Commission" value={`-GHS ${commission}`} />
<LineItem label="You Receive" value={`GHS ${netAmount}`} />

// ✅ CORRECT - Just show total
<LineItem label="Sale Total" value={`GHS ${totalAmount}`} />
// Optional: Add note that payment is received directly
<Note>Payment received directly from buyer (cash/MoMo)</Note>
```

### 4. POS / Walk-in Sales

POS sales should NOT show any platform fees. The `POSSaleSerializer` returns:
- `subtotal`
- `discount_amount`
- `total_amount`
- `amount_received`

No commission or fee fields are included.

---

## API Response Fields to Check

### EggSale / BirdSale Models

These models have `platform_commission`, `paystack_fee`, and `farmer_payout` fields, but:

```python
# Backend always returns 0 for commission when disabled
if not settings.enable_transaction_commission:
    self.platform_commission = Decimal('0.00')
    self.paystack_fee = Decimal('0.00')
    self.farmer_payout = self.subtotal  # 100% to farmer
```

**If your frontend reads these fields from API responses, they will be 0. But you should still remove any UI that displays "Platform Fee" sections.**

### Farmer Analytics API

**Endpoint:** `GET /api/dashboards/farmer/sales-revenue/`

Response includes:
```json
{
  "revenue_breakdown": {
    "eggs": {
      "gross": 70480.00,
      "net": 70480.00,       // Same as gross (no commission)
      "commissions": 0.00,   // Always 0
      "transactions": 234
    }
  }
}
```

The `commissions` field is returned but will always be `0`. You can:
1. Ignore this field in your UI
2. Or conditionally hide "Commissions" section when value is 0

---

## Recommended Frontend Changes

### 1. Remove Hardcoded Fee Percentages

Search your codebase for:
```
grep -r "0.02\|2%\|0.03\|3%\|0.05\|5%\|platform.*fee\|commission" src/
```

Remove any:
- `const FEE_PERCENTAGE = 0.02`
- `const PLATFORM_FEE_RATE = 2`
- `sale.total * 0.02`

### 2. Update TypeScript Interfaces

If you have fee-related types, update them:

```typescript
// ❌ OLD
interface SaleAnalytics {
  grossRevenue: number;
  platformFees: number;
  netRevenue: number;
}

// ✅ NEW - Simpler
interface SaleAnalytics {
  totalRevenue: number;
  // No fees - farmer keeps 100%
}
```

### 3. Update Revenue Display Components

```tsx
// ❌ OLD - With fee breakdown
<RevenueCard>
  <Line label="Gross Sales" value={gross} />
  <Line label="Platform Fees (2%)" value={-fees} negative />
  <Line label="Net Revenue" value={net} highlight />
</RevenueCard>

// ✅ NEW - Simple total
<RevenueCard>
  <Line label="Total Sales" value={total} highlight />
  <Note>You receive 100% of all sales</Note>
</RevenueCard>
```

### 4. Update Sales Analytics Charts

If you have charts showing fee trends, remove them or repurpose:

```tsx
// ❌ REMOVE
<PieChart 
  data={[
    { name: 'Your Earnings', value: netRevenue },
    { name: 'Platform Fees', value: platformFees }
  ]} 
/>

// ✅ KEEP SIMPLE
<BarChart 
  data={salesByPeriod}
  label="Total Sales Revenue"
/>
```

---

## API Endpoints Reference

### Endpoints That Return Sales Data

| Endpoint | Contains Fee Fields? | Action |
|----------|---------------------|--------|
| `GET /api/dashboards/farmer/sales-revenue/` | Yes (always 0) | Ignore `commissions` field |
| `GET /api/dashboards/farmer/summary/` | No | No changes needed |
| `GET /api/marketplace/orders/` | No fees | No changes needed |
| `GET /api/pos/sales/` | No fees | No changes needed |

### Platform Settings

| Endpoint | Purpose |
|----------|---------|
| `GET /api/public/platform-settings/` | Get marketplace fee (GHS 50) |
| `GET /api/subscriptions/marketplace-access/` | Check farmer's subscription status |

---

## Testing Checklist

After making changes, verify:

- [ ] Sales Analytics page shows NO "Platform Fees" section
- [ ] Revenue totals match gross sales (no deductions)
- [ ] Sale receipts/details don't show commission
- [ ] POS sales show full amount received
- [ ] No hardcoded 2%/3%/5% calculations remain
- [ ] Marketplace activation fee (GHS 50) still displays correctly on subscription pages

---

## Contact

If you have questions about these changes:
- Backend API: Check the `sales_revenue/models.py` `calculate_amounts()` method
- Platform Settings: Check `sales_revenue/platform_settings_views.py`

---

*Document Created: January 9, 2026*
*Backend Commit: eafc101 (development branch)*
