# Paystack Subaccount Creation Guide

## Overview

Paystack subaccounts enable **direct settlement** of sales revenue to farmers' mobile money or bank accounts **without the platform holding the money**. This ensures:

✅ Platform **cannot access** farmer's money  
✅ Automatic daily settlements to farmer's account  
✅ Full transparency and audit trail  
✅ No manual transfer process needed  

---

## How Subaccounts Work

### Traditional Payment Flow (NOT USED):
```
Customer pays → Platform receives money → Platform manually transfers to farmer
Problem: Platform holds money, risk of insider fraud
```

### Paystack Subaccount Flow (OUR APPROACH):
```
Customer pays → Paystack splits payment:
  ├─ Commission → Platform account
  └─ Farmer payout → Farmer's subaccount → Farmer's mobile money/bank (automatic)

Benefit: Money goes DIRECTLY to farmer, platform never holds it
```

---

## When Is Subaccount Created?

A Paystack subaccount is created for each farmer when:

1. **On Farm Approval** (Recommended):
   - When farm application status changes to "Approved"
   - Ensures farmer can receive payments immediately upon activation

2. **On First Sale** (Alternative):
   - When farmer makes their first egg or bird sale
   - Just-in-time creation

3. **Manual Creation** (Admin):
   - Admin can manually create subaccount from Django admin
   - Useful for troubleshooting or pre-setup

---

## Prerequisites

### For Mobile Money (Preferred in Ghana):

Farmer must provide:
- ✅ Mobile money number (e.g., 0244123456)
- ✅ Mobile money provider (MTN, Vodafone, AirtelTigo, Telecel)
- ✅ Account holder name

Stored in `Farm` model:
```python
farm.mobile_money_number = "+233244123456"
farm.mobile_money_provider = "MTN Mobile Money"
farm.account_name = "Kwame Mensah"
```

### For Bank Account (Alternative):

Farmer must provide:
- ✅ Bank name (e.g., "GCB Bank", "Ecobank Ghana")
- ✅ Account number
- ✅ Account holder name

Stored in `Farm` model:
```python
farm.bank_name = "GCB Bank"
farm.account_number = "1234567890"
farm.account_name = "Kwame Mensah"
```

---

## Step-by-Step Creation Process

### 1. Import Service
```python
from sales_revenue.services import SubaccountManager

subaccount_manager = SubaccountManager()
```

### 2. Get Farm Instance
```python
from farms.models import Farm

farm = Farm.objects.get(id=farm_id)
```

### 3. Create Subaccount
```python
try:
    subaccount_data = subaccount_manager.create_subaccount(farm)
    print(f"✅ Subaccount created: {subaccount_data['subaccount_code']}")
    print(f"   Settlement account: {subaccount_data['settlement_bank']}")
    print(f"   Account number: {subaccount_data['account_number']}")
    
except ValueError as e:
    print(f"❌ Missing payment details: {e}")
    # Prompt farmer to provide mobile money or bank details
    
except PaystackAPIError as e:
    print(f"❌ Paystack error: {e.message}")
    # Log error and retry later
```

### 4. What Happens Internally

The `create_subaccount()` method:

1. **Validates** farm has payment details (mobile money or bank)
2. **Maps** provider to Paystack bank code:
   ```python
   MTN Mobile Money → 'mtn-gh'
   Vodafone Cash   → 'vod-gh'
   GCB Bank        → 'gcb-gh'
   ```
3. **Calls** Paystack API:
   ```http
   POST https://api.paystack.co/subaccount
   Authorization: Bearer sk_test_xxxxx
   
   {
     "business_name": "Kwame's Poultry Farm",
     "settlement_bank": "mtn-gh",
     "account_number": "0244123456",
     "percentage_charge": 0,
     "description": "Subaccount for Kwame's Poultry Farm (Farm ID: YEA-REG-001)",
     "primary_contact_name": "Kwame Mensah",
     "primary_contact_phone": "+233244123456"
   }
   ```
4. **Stores** subaccount details in Farm model:
   ```python
   farm.paystack_subaccount_code = "ACCT_abc123xyz"
   farm.paystack_subaccount_id = "123456"
   farm.paystack_settlement_account = "0244123456"
   farm.subaccount_created_at = "2025-10-26 14:30:00"
   farm.subaccount_active = True
   farm.save()
   ```

---

## Using Subaccount in Sales

When customer purchases eggs/birds:

```python
from sales_revenue.models import EggSale, Payment
from sales_revenue.services import PaymentService

# Create sale
sale = EggSale.objects.create(
    farm=farm,
    customer=customer,
    quantity=10,
    unit='crate',
    price_per_unit=12.00,
    # Amounts calculated automatically
)

# Initialize payment with subaccount
payment_service = PaymentService()
payment = payment_service.initialize_payment(
    amount=sale.total_amount,  # GHS 120.00
    email=customer.email,
    subaccount=farm.paystack_subaccount_code,  # ⭐ Key!
    transaction_charge=sale.platform_commission,  # GHS 3.60 (3%)
    bearer='account'  # ⭐ Platform pays Paystack fees
)

# Payment split happens automatically:
# - Customer pays: GHS 120.00
# - Platform gets: GHS 3.60 (commission) - GHS 1.90 (Paystack fee) = GHS 1.70
# - Farmer gets: GHS 116.40 (directly to mobile money within 24 hours)
```

---

## Settlement Timeline

| Schedule Type | Settlement Time | Extra Fee | Use Case |
|---------------|-----------------|-----------|----------|
| **Auto** (Default) | 24 hours | None | Standard sales |
| **Instant** | 2 minutes | GHS 10 | Urgent farmer needs |

Configure in `.env`:
```bash
PAYSTACK_SETTLEMENT_SCHEDULE=auto  # or 'instant'
```

---

## Farmer Experience

### What Farmer Sees:

1. **Sale Made** (10 crates @ GHS 12):
   - Customer pays GHS 120 via mobile money/card
   - Farmer receives SMS: "Payment of GHS 120 received for 10 crates"

2. **Settlement** (Next day, 9 AM):
   - Farmer receives mobile money notification:
     ```
     You have received GHS 116.40 from Paystack
     Reference: SALE_20251026_001
     New balance: GHS 456.40
     ```

3. **Platform Dashboard**:
   - Shows: "Payout: GHS 116.40 (Completed)"
   - Shows: "Platform fee: GHS 3.60"
   - Shows: "Settlement date: Oct 26, 2025"

### What Farmer DOESN'T Need:

❌ Paystack account  
❌ App installation  
❌ Dashboard login  
❌ Manual withdrawal  
❌ Technical knowledge  

**Just mobile money number = automatic payments!**

---

## Subaccount Management

### Check If Subaccount Exists
```python
if farm.paystack_subaccount_code:
    print(f"Subaccount: {farm.paystack_subaccount_code}")
else:
    print("No subaccount - create one before first sale")
```

### Ensure Subaccount Exists (Auto-create)
```python
subaccount_code = subaccount_manager.ensure_subaccount_exists(farm)
# Returns existing code OR creates new subaccount if missing
```

### Update Subaccount (e.g., farmer changes mobile money number)
```python
subaccount_manager.update_subaccount(
    farm,
    account_number="0201234567",  # New mobile money number
    settlement_bank="vod-gh"      # New provider (Vodafone)
)
```

### Deactivate Subaccount (e.g., farm suspended)
```python
subaccount_manager.deactivate_subaccount(farm)
# farm.subaccount_active = False
# No new payments will settle until reactivated
```

### Reactivate Subaccount
```python
subaccount_manager.reactivate_subaccount(farm)
# farm.subaccount_active = True
```

---

## Error Handling

### Common Errors & Solutions

#### 1. Missing Payment Details
```python
ValueError: Farm has no valid payment method. Please provide either mobile money details or bank account details.
```
**Solution:** Prompt farmer to add mobile money or bank details in profile.

#### 2. Invalid Mobile Money Number
```python
PaystackAPIError: Invalid account number for mobile money
```
**Solution:** Validate phone number format (0XXXXXXXXX, not +233).

#### 3. Unknown Bank
```python
ValueError: Unknown bank: ABC Bank. Supported banks: GCB Bank, Ecobank Ghana...
```
**Solution:** Add bank code mapping in `_get_bank_code()` method.

#### 4. Duplicate Subaccount
```python
PaystackAPIError: Subaccount already exists for this account
```
**Solution:** Fetch existing subaccount instead of creating new one.

---

## Testing

### Sandbox Mode (Development)

Use Paystack test keys in `.env.development`:
```bash
PAYSTACK_SECRET_KEY=sk_test_your_test_key_here
PAYSTACK_PUBLIC_KEY=pk_test_your_test_key_here
```

Test mobile money numbers (Paystack sandbox):
```python
# These numbers work in test mode
"0244123456"  # MTN test number
"0501234567"  # Vodafone test number
```

### Production Mode

Use live keys in `.env.production`:
```bash
PAYSTACK_SECRET_KEY=sk_live_your_live_key_here
PAYSTACK_PUBLIC_KEY=pk_live_your_live_key_here
```

**Real mobile money numbers and actual settlements!**

---

## Security Considerations

### ✅ What Platform CAN Do:
- View subaccount details
- See settlement history
- Deactivate/reactivate subaccount
- Calculate commissions

### ❌ What Platform CANNOT Do:
- Withdraw money from farmer's subaccount
- Change settlement destination without farmer's approval
- Access farmer's mobile money balance
- Block settlements (beyond deactivation)

### 🔐 Additional Security:
- All API calls logged with timestamps
- Farm model updates tracked (created_at, updated_at)
- Subaccount code stored securely (indexed for fast lookup)
- Settlement account encrypted in database (future enhancement)

---

## Database Schema

### Farm Model Fields

```python
# Paystack Subaccount Fields
paystack_subaccount_code = CharField(max_length=100, unique=True)
paystack_subaccount_id = CharField(max_length=100)
paystack_settlement_account = CharField(max_length=50)
subaccount_created_at = DateTimeField(null=True)
subaccount_active = BooleanField(default=False)

# Payment Method Fields (one required)
mobile_money_number = PhoneNumberField(region='GH', blank=True)
mobile_money_provider = CharField(max_length=50, blank=True)
bank_name = CharField(max_length=100, blank=True)
account_number = CharField(max_length=50, blank=True)
account_name = CharField(max_length=200, blank=True)
```

---

## API Endpoints (Future)

```python
# Create subaccount
POST /api/farms/{farm_id}/subaccount/create/

# Check subaccount status
GET /api/farms/{farm_id}/subaccount/

# Update settlement details
PUT /api/farms/{farm_id}/subaccount/update/

# Settlement history
GET /api/farms/{farm_id}/settlements/
```

---

## Recommended Implementation Flow

### For New Farms (Farm Registration):

```python
# In farm approval workflow
def approve_farm(farm_id):
    farm = Farm.objects.get(id=farm_id)
    
    # 1. Approve farm
    farm.application_status = 'Approved'
    farm.farm_status = 'Active'
    farm.approval_date = timezone.now()
    farm.save()
    
    # 2. Create Paystack subaccount
    try:
        subaccount_manager = SubaccountManager()
        subaccount_manager.create_subaccount(farm)
        
        # 3. Send SMS to farmer
        send_sms(
            farm.primary_phone,
            f"Congratulations! Your farm {farm.farm_name} has been approved. "
            f"You can now start selling and will receive payments directly to "
            f"your mobile money {farm.mobile_money_number}."
        )
    except Exception as e:
        logger.error(f"Failed to create subaccount: {e}")
        # Farm still approved, create subaccount later
```

### For Existing Farms (Migration):

```python
# Management command: python manage.py create_subaccounts
from django.core.management.base import BaseCommand
from farms.models import Farm
from sales_revenue.services import SubaccountManager

class Command(BaseCommand):
    def handle(self, *args, **options):
        subaccount_manager = SubaccountManager()
        
        # Get approved farms without subaccounts
        farms = Farm.objects.filter(
            farm_status='Active',
            paystack_subaccount_code__isnull=True
        )
        
        for farm in farms:
            try:
                subaccount_manager.create_subaccount(farm)
                self.stdout.write(f"✅ Created subaccount for {farm.farm_name}")
            except Exception as e:
                self.stdout.write(f"❌ Failed for {farm.farm_name}: {e}")
```

---

## Monitoring & Logging

All subaccount operations are logged:

```python
# logs/sales_revenue.log

[2025-10-26 14:30:15] INFO: Creating Paystack subaccount for farm: Kwame's Poultry Farm
[2025-10-26 14:30:16] INFO: Paystack API POST /subaccount
[2025-10-26 14:30:17] INFO: Paystack API success: Subaccount created
[2025-10-26 14:30:17] INFO: Subaccount created successfully: ACCT_abc123xyz
```

Monitor in Django admin:
- `Farms` → Filter by `subaccount_active=True`
- View subaccount details in farm detail page
- Check `subaccount_created_at` timestamp

---

## Summary

**Paystack subaccounts enable:**
- ✅ Direct farmer settlements (platform never holds money)
- ✅ Automatic daily payouts to mobile money
- ✅ Zero complexity for farmers (just SMS notifications)
- ✅ Full audit trail and transparency
- ✅ Platform pays ALL Paystack fees (bearer='account')
- ✅ Tiered commission structure (2-5%)

**When created:**
- On farm approval (recommended)
- OR on first sale (just-in-time)

**Farmer needs:**
- Mobile money number + provider
- OR bank account + bank name
- Nothing else!
