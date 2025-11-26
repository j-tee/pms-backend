# Platform Settings Management Guide

## Overview

Platform administrators can dynamically configure commission rates, payment settings, and refund policies **without changing code or redeploying** the application.

All settings are managed through the **Django Admin** interface under **Sales Revenue > Platform Settings**.

---

## Quick Start

### 1. Initialize Settings (First Time Only)

After deploying the application, run:

```bash
python manage.py init_platform_settings
```

This creates default settings:
- Commission: 5% / 3% / 2% (tiered)
- Minimum commission: GHS 2.00
- Platform pays all Paystack fees
- 24-hour settlements
- 48-hour refund window

### 2. Access Admin Interface

1. Go to: `http://your-domain.com/admin/`
2. Log in with superuser credentials
3. Navigate to: **Sales Revenue > Platform Settings**
4. Click on the settings record to edit

---

## Settings Categories

### 1. Commission Structure

Control how much the platform charges per transaction.

#### Commission Tiers

**Tier 1:** For small sales
- **Percentage:** Default 5.0%
- **Threshold:** Sales below GHS 100
- **Example:** GHS 50 sale = GHS 2.50 commission

**Tier 2:** For medium sales
- **Percentage:** Default 3.0%
- **Threshold:** Sales GHS 100-500
- **Example:** GHS 200 sale = GHS 6.00 commission

**Tier 3:** For large sales
- **Percentage:** Default 2.0%
- **Threshold:** Sales above GHS 500
- **Example:** GHS 1000 sale = GHS 20.00 commission

**Minimum Commission:**
- Ensures platform covers costs on very small sales
- Default: GHS 2.00
- Applied to ALL sales (overrides percentage if higher)

#### How to Adjust Commission

**To Increase Commission (e.g., platform needs more revenue):**
```
Tier 1: 5% → 7%
Tier 2: 3% → 5%
Tier 3: 2% → 3%
```

**To Decrease Commission (e.g., attract more farmers):**
```
Tier 1: 5% → 4%
Tier 2: 3% → 2.5%
Tier 3: 2% → 1.5%
```

**Important:** Changes apply to **new sales only**. Existing sales keep their original commission.

---

### 2. Paystack Configuration

Control payment processing behavior.

#### Fee Bearer

**Who pays Paystack transaction fees (1.5% + GHS 0.10)?**

- **Platform Pays Fees** (Recommended)
  - Setting: `account`
  - Farmers receive exact displayed amount
  - Platform absorbs Paystack costs
  - Builds farmer trust

- **Farmer Pays Fees** (Not Recommended)
  - Setting: `subaccount`
  - Farmer receives less than displayed
  - Can cause confusion and distrust

**Example:**
```
Sale: GHS 120
Commission: GHS 3.60 (3%)
Paystack fee: GHS 1.90

Platform pays fees:
  • Farmer receives: GHS 116.40
  • Platform profit: GHS 3.60 - GHS 1.90 = GHS 1.70

Farmer pays fees:
  • Farmer receives: GHS 114.50 (GHS 116.40 - GHS 1.90)
  • Platform profit: GHS 3.60
  • ⚠️ Farmer unhappy (expected GHS 116.40)
```

#### Settlement Schedule

**How quickly do farmers receive money?**

- **Auto (24 hours)** (Recommended)
  - Default and free
  - Settlements happen daily at 9 AM
  - No extra fees

- **Instant (2 minutes)**
  - Enable with `enable_instant_settlements` flag
  - Costs extra GHS 10 per settlement
  - Use for urgent farmer needs only

---

### 3. Payment Retry Settings

Control automatic retry behavior for failed payments.

#### Max Retry Attempts
- Default: **3 attempts**
- Range: 1-10
- How many times system retries before giving up

#### Retry Delay
- Default: **300 seconds** (5 minutes)
- Range: 60-3600 seconds (1-60 minutes)
- Time between retry attempts

**Example Flow:**
```
Payment fails at 2:00 PM
  ↓
Retry 1 at 2:05 PM (5 min delay)
  ↓
Retry 2 at 2:10 PM (5 min delay)
  ↓
Retry 3 at 2:15 PM (5 min delay)
  ↓
All retries failed → Auto-refund after 72 hours
```

**Best Practices:**
- **High traffic periods:** Increase delay to 10 minutes
- **Critical sales:** Increase attempts to 5
- **Network issues common:** Increase both

---

### 4. Refund Configuration

Control customer refund policies.

#### Refund Eligibility Window
- Default: **48 hours**
- Range: 1-168 hours (1 hour to 1 week)
- How long customers can request refunds

#### Auto-Refund Timeout
- Default: **72 hours**
- Range: 24-336 hours (1 day to 2 weeks)
- When system auto-refunds failed payments

#### Enable Refunds
- Default: **Enabled**
- Turn off to block all refund requests
- Use during policy changes or investigations

#### Enable Auto-Refunds
- Default: **Enabled**
- Automatically refund stuck payments
- Disable for manual review process

**Refund Scenarios:**

**Scenario 1: Customer wants refund within 48 hours**
```
✅ Refund eligible
→ Admin reviews and approves
→ Money returned to customer
```

**Scenario 2: Customer wants refund after 48 hours**
```
❌ Not eligible (window closed)
→ Customer must contact support
→ Admin can manually refund if justified
```

**Scenario 3: Payment fails, payout pending for 72+ hours**
```
✅ Auto-refund triggered
→ Money automatically returned
→ Customer and farmer notified
→ No manual intervention needed
```

---

### 5. Feature Flags

Enable or disable platform features.

#### Enable Instant Settlements
- Default: **Disabled**
- Allows farmers to request instant payouts (2 min)
- Costs GHS 10 extra per settlement
- Enable only if farmers frequently need urgent cash

#### Enable Refunds
- Default: **Enabled**
- Master switch for refund system
- Disable to temporarily block refunds

#### Enable Auto-Refunds
- Default: **Enabled**
- Automatic refunds for failed payments
- Disable to require manual review

---

## Common Admin Tasks

### Task 1: Increase Commission (Platform Needs More Revenue)

**Situation:** Paystack fees eating into profits

**Solution:**
1. Go to Django Admin > Platform Settings
2. Update commission tiers:
   ```
   Tier 1: 5% → 6%
   Tier 2: 3% → 4%
   Tier 3: 2% → 2.5%
   Minimum: GHS 2.00 → GHS 2.50
   ```
3. Add note: "Commission increased to cover rising payment processing costs"
4. Click **Save**

**Result:** New sales use new rates immediately

---

### Task 2: Decrease Commission (Attract New Farmers)

**Situation:** Marketing campaign to onboard 100 new farmers

**Solution:**
1. Reduce commission temporarily:
   ```
   Tier 1: 5% → 3%
   Tier 2: 3% → 2%
   Tier 3: 2% → 1.5%
   ```
2. Add note: "Promotional rates for Q1 2026 campaign"
3. Save settings

**After Campaign:**
1. Restore original rates
2. Update note with end date

---

### Task 3: Extend Refund Window (Customer Complaints)

**Situation:** Many farmers complaining 48 hours is too short

**Solution:**
1. Increase refund window:
   ```
   Refund eligibility: 48 hours → 72 hours
   ```
2. Add note: "Extended to 72 hours based on farmer feedback"
3. Save

---

### Task 4: Disable Refunds Temporarily (System Maintenance)

**Situation:** Migrating payment processor, need to freeze refunds

**Solution:**
1. Disable refunds:
   ```
   Enable refunds: ✅ → ❌
   Enable auto-refunds: ✅ → ❌
   ```
2. Add note: "Refunds disabled during payment system migration (Jan 15-17, 2026)"
3. Save

**After Maintenance:**
1. Re-enable both flags
2. Update note with completion date

---

### Task 5: Make Platform Pay Fees (Build Trust)

**Situation:** Farmers confused about deductions

**Solution:**
1. Change fee bearer:
   ```
   Paystack fee bearer: Subaccount → Account (Platform Pays Fees)
   ```
2. Adjust commission to compensate:
   ```
   Tier 2: 3% → 3.5% (to cover the GHS 1.90 Paystack fee)
   ```
3. Add note: "Platform now absorbs all Paystack fees for farmer transparency"
4. Save

---

## Impact Calculator

Use this calculator to understand commission changes:

### Current Settings (Default)
| Sale Amount | Tier | Commission Rate | Commission | Paystack Fee | Farmer Gets | Platform Profit |
|-------------|------|-----------------|------------|--------------|-------------|-----------------|
| GHS 50      | 1    | 5%              | GHS 2.50   | GHS 0.85     | GHS 47.50   | GHS 1.65        |
| GHS 100     | 2    | 3%              | GHS 3.00   | GHS 1.60     | GHS 97.00   | GHS 1.40        |
| GHS 200     | 2    | 3%              | GHS 6.00   | GHS 3.10     | GHS 194.00  | GHS 2.90        |
| GHS 500     | 3    | 2%              | GHS 10.00  | GHS 7.60     | GHS 490.00  | GHS 2.40        |
| GHS 1000    | 3    | 2%              | GHS 20.00  | GHS 15.10    | GHS 980.00  | GHS 4.90        |

### After Increasing Tier 2 to 4%
| Sale Amount | Tier | Commission Rate | Commission | Paystack Fee | Farmer Gets | Platform Profit |
|-------------|------|-----------------|------------|--------------|-------------|-----------------|
| GHS 200     | 2    | 4%              | GHS 8.00   | GHS 3.10     | GHS 192.00  | **GHS 4.90** ⬆️ |

**Farmer impact:** -GHS 2.00 per GHS 200 sale  
**Platform benefit:** +GHS 2.00 per sale

---

## Security & Best Practices

### ✅ DO:
- **Track changes:** Always add notes when modifying settings
- **Test first:** Use sandbox/test environment before production
- **Communicate:** Notify farmers before commission changes
- **Monitor impact:** Review sales reports after changes
- **Document reasoning:** Include business justification in notes

### ❌ DON'T:
- **Frequent changes:** Avoid changing rates more than quarterly
- **Extreme values:** Commission > 10% will drive farmers away
- **No communication:** Surprise changes damage trust
- **Delete settings:** Can't delete (singleton model prevents this)
- **Forget Paystack fees:** Always factor in 1.5% + GHS 0.10 cost

---

## Monitoring Changes

### View Change History

Settings track:
- **Last modified by:** Which admin made the change
- **Updated at:** Timestamp of last change
- **Notes:** Admin's explanation

### Audit Trail

All settings changes are logged in Django admin history:
1. Go to Platform Settings
2. Click "History" button (top-right)
3. See all changes with timestamps and users

---

## Troubleshooting

### Problem: Commission seems incorrect on new sales

**Check:**
1. Clear Django cache: `python manage.py shell` → `from django.core.cache import cache` → `cache.clear()`
2. Verify sale was created AFTER settings change
3. Check sale's `calculate_amounts()` method was called

### Problem: Changes not taking effect

**Solution:**
1. Restart application servers
2. Clear cache (settings cached for 1 hour)
3. Check singleton model (only 1 settings record should exist)

### Problem: Can't create new settings

**Reason:** Singleton pattern allows only ONE settings record

**Solution:** Edit existing settings instead of creating new

### Problem: Want to restore defaults

**Solution:**
1. Delete existing settings (Django admin)
2. Run: `python manage.py init_platform_settings`
3. Default values restored

---

## API Access (Future)

Settings will be accessible via API:

```http
GET /api/platform-settings/
```

Response:
```json
{
  "commission_tier_1_percentage": 5.0,
  "commission_tier_1_threshold": 100.0,
  "commission_tier_2_percentage": 3.0,
  "commission_tier_2_threshold": 500.0,
  "commission_tier_3_percentage": 2.0,
  "commission_minimum_amount": 2.0,
  "paystack_fee_bearer": "account",
  "refund_eligibility_hours": 48,
  "enable_refunds": true
}
```

---

## Summary

**Platform Settings provide:**
- ✅ Dynamic commission rate control
- ✅ Flexible payment configuration
- ✅ Customizable refund policies
- ✅ Feature flags for controlled rollouts
- ✅ Cached for performance (1-hour cache)
- ✅ Audit trail and change tracking
- ✅ No code changes or deployment needed

**Admin Access:**
Django Admin → Sales Revenue → Platform Settings

**Management Command:**
`python manage.py init_platform_settings`

**Always remember:** Changes affect NEW sales only. Existing sales retain original commission rates.
