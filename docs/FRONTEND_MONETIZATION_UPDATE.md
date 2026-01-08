# 🚨 Frontend Update Required: Monetization Changes

**Date:** January 8, 2026  
**Priority:** HIGH  
**Backend Commits:** `9671931`, `c6dbd07`

---

## Summary

The monetization model has been simplified. **Farmers now pay ONLY ONE fee:**

| Fee | Amount | Status |
|-----|--------|--------|
| **Marketplace Activation Fee** | GHS 50/month | ✅ ACTIVE |
| Transaction Commission | 2-5% | ❌ REMOVED |
| Verified Seller Tier | GHS 50/month | ❌ REMOVED |

**Reason:** Ghanaian farmers are very sensitive to platform fees. Payments happen OFF-PLATFORM (cash, MoMo, bank transfer direct to farmer). Farmers only use the platform to record sales.

---

## 🔴 Required Frontend Changes

### 1. Remove Verified Seller Tier UI

**Remove all references to:**
- "Verified Seller" tier/badge
- "Premium Seller" options
- Any upgrade to verified tier buttons/modals
- Verified seller pricing (GHS 50/month extra)

**Affected areas:**
- Subscription/pricing pages
- Farm profile settings
- Marketplace seller badges
- Any "upgrade" CTAs

### 2. Remove Transaction Commission Display

**Remove:**
- Commission percentage displays (2-5%)
- "Platform fee" or "Commission" line items in sale summaries
- Commission breakdowns in analytics

**Update sale recording UI:**
```
BEFORE:
  Sale Amount: GHS 300
  Platform Commission (3%): -GHS 9
  Farmer Receives: GHS 291

AFTER:
  Sale Amount: GHS 300
  Farmer Receives: GHS 300 (100%)
```

### 3. Update Subscription Type Options

**Old options (REMOVE `verified`):**
```typescript
type SubscriptionType = 'none' | 'government_subsidized' | 'standard' | 'verified';
```

**New options:**
```typescript
type SubscriptionType = 'none' | 'government_subsidized' | 'standard';
```

### 4. Update Pricing Page

Show only ONE fee:

```
┌─────────────────────────────────────────────┐
│  Marketplace Activation Fee                │
│  GHS 50/month                              │
│                                            │
│  ✓ List products on public marketplace    │
│  ✓ Contact info visible to buyers         │
│  ✓ Sales tracking & analytics             │
│  ✓ 14-day free trial                      │
│                                            │
│  [Activate Marketplace]                    │
└─────────────────────────────────────────────┘
```

**DO NOT show:**
- Multiple pricing tiers
- Premium/Verified options
- Commission percentages

### 5. Update API Response Handling

**Public Platform Settings API** (`GET /api/public/platform-settings/`)

**Old response:**
```json
{
  "marketplace_activation_fee": "50.00",
  "marketplace_trial_days": 14,
  "enable_verified_seller_tier": false,
  "verified_seller_fee": "50.00",
  "free_tier_can_view_marketplace": true,
  "free_tier_can_view_prices": true,
  "free_tier_can_access_education": true
}
```

**New response (fields removed):**
```json
{
  "marketplace_activation_fee": "50.00",
  "marketplace_trial_days": 14,
  "free_tier_can_view_marketplace": true,
  "free_tier_can_view_prices": true,
  "free_tier_can_access_education": true
}
```

### 6. Update Sale Recording Flow

When farmers record a sale:

```
┌─────────────────────────────────────────────┐
│  Record Sale                                │
│                                            │
│  Product: Eggs (Crate)                     │
│  Quantity: 10                              │
│  Price per crate: GHS 30                   │
│  ─────────────────────────────             │
│  Total: GHS 300                            │
│                                            │
│  Payment received: [Cash ▼]                │
│                                            │
│  ℹ️ Payment was received directly.         │
│     Recording for tracking purposes only.  │
│                                            │
│  [Record Sale]                             │
└─────────────────────────────────────────────┘
```

**Key messaging:**
- "Payment received directly" (not through platform)
- "Recording for tracking purposes"
- No commission deducted

---

## 🟡 Optional Cleanup

### Remove from TypeScript interfaces:

```typescript
// REMOVE these fields from PlatformSettings interface
interface PlatformSettings {
  // ...
  // enable_verified_seller_tier: boolean;  // REMOVE
  // verified_seller_fee: string;            // REMOVE
  // ...
}
```

### Remove from constants:

```typescript
// REMOVE
const SUBSCRIPTION_TYPES = {
  NONE: 'none',
  GOVERNMENT: 'government_subsidized',
  STANDARD: 'standard',
  // VERIFIED: 'verified',  // REMOVE THIS
};
```

---

## 🟢 What Stays the Same

| Feature | Status |
|---------|--------|
| Marketplace Activation Fee (GHS 50/month) | ✅ No change |
| 14-day free trial | ✅ No change |
| Government subsidized access | ✅ No change |
| Free core platform (farm management) | ✅ No change |
| Sale recording functionality | ✅ Works, just no commission |

---

## API Endpoints Affected

| Endpoint | Change |
|----------|--------|
| `GET /api/public/platform-settings/` | Removed `enable_verified_seller_tier`, `verified_seller_fee` |
| `GET /api/admin/platform-settings/` | Removed verified seller fields |
| `PATCH /api/admin/platform-settings/` | No longer accepts verified seller fields |
| `POST /api/admin/platform-settings/reset/` | No longer resets verified seller fields |
| `GET /api/admin/revenue/summary/` | Removed `verified_seller_fees` from type breakdown |
| `GET /api/admin/payments/` | Removed `verified_seller` payment type |

---

## Testing Checklist

- [ ] Pricing page shows only GHS 50/month
- [ ] No "Verified Seller" option anywhere
- [ ] Sale recording shows 100% to farmer
- [ ] No commission displayed anywhere
- [ ] Subscription type dropdown has only 3 options
- [ ] API calls handle missing `verified_seller` fields gracefully

---

## Questions?

Contact backend team if you have questions about these changes.

**Commits to reference:**
- `9671931` - Suspend transaction commission
- `c6dbd07` - Remove Verified Seller Tier completely
