# Sales & Revenue Module (Phase 5)

## Overview
The Sales & Revenue module manages egg and bird sales, customer tracking, payment processing via Paystack, and farmer payouts with mobile money integration for Ghana.

## Models Created

### 1. Customer
Tracks buyers of eggs and birds with mobile money payment support.

**Key Features:**
- Customer types: Individual, Business, Retailer, Wholesaler
- Mobile money integration (MTN, Vodafone, AirtelTigo)
- Purchase history tracking
- Delivery address management

**Fields:**
- Basic: first_name, last_name, business_name, customer_type
- Contact: phone_number, email, location, delivery_address
- Payment: mobile_money_number, mobile_money_provider, mobile_money_account_name
- Stats: total_purchases, total_orders, is_active

### 2. EggSale
Tracks egg sales with automatic commission calculation.

**Key Features:**
- Units: Crates (30 eggs) or Individual pieces
- Automatic amount calculations
- Tiered commission structure (3-5%)
- Links to DailyProduction records
- Payment tracking via Paystack

**Calculated Fields:**
- `subtotal` = quantity × price_per_unit
- `platform_commission` = Tiered percentage (5% <GHS100, 3% GHS100-500, 2% >GHS500)
- `paystack_fee` = 1.5% + GHS 0.10 (paid by platform)
- `farmer_payout` = subtotal - commission
- `total_amount` = subtotal (what customer pays)

**Statuses:**
- pending → paid → processing → completed
- cancelled, refunded

### 3. BirdSale
Tracks bird sales (layers, broilers, cockerels, spent hens).

**Key Features:**
- Bird types: Layer, Broiler, Cockerel, Spent Hen
- Same commission structure as egg sales
- Links to Flock records
- Automatic inventory reduction (future feature)

**Calculated Fields:**
- Same calculation logic as EggSale
- Tiered commission based on total sale amount

### 4. Payment
Paystack payment tracking with retry and refund mechanisms.

**Key Features:**
- Payment methods: Mobile Money, Bank Transfer, Card
- Retry mechanism (max 3 attempts, 5-minute delays)
- Refund eligibility (48 hours from payment)
- Auto-refund (72 hours if payout fails)
- Full Paystack API response storage

**Statuses:**
- pending → processing → success
- failed, refunded, partial_refund

**Refund Logic:**
- Customers can request refund within 48 hours
- System auto-refunds after 72 hours if farmer payout fails
- Full audit trail via payment_response JSONField

### 5. FarmerPayout
Tracks farmer settlements via Paystack subaccounts to mobile money.

**Key Features:**
- Direct mobile money transfer to farmers
- Cryptographic audit trail (blockchain-like hashing)
- Retry mechanism for failed transfers
- Links to either EggSale or BirdSale
- Settlement tracking

**Audit Trail:**
- Each payout contains hash of previous payout (chain)
- Prevents tampering with payout history
- Cryptographic verification via SHA-256

**Statuses:**
- pending → processing → success
- failed, cancelled

## Payment Architecture

### Paystack Configuration
```python
# Platform pays ALL Paystack fees (not farmers)
PAYSTACK_FEE_BEARER = 'account'

# Settlement schedule (24-hour auto or instant)
PAYSTACK_SETTLEMENT_SCHEDULE = 'auto'

# Currency
PAYSTACK_CURRENCY = 'GHS'
```

### Commission Structure (SUSPENDED)

> ⚠️ **IMPORTANT**: Transaction commissions are currently **SUSPENDED**.
> 
> **Reason**: In Ghana's local context, farmers are sensitive to platform fees. 
> Payments happen **OFF-PLATFORM** (cash, mobile money direct transfer, etc.).
> Farmers use the platform only to **record sales** for tracking purposes.
> 
> **Current fee**: Only the GHS 50/month Marketplace Activation Fee applies.
> 
> Commission can be enabled in the future via `PlatformSettings.enable_transaction_commission`
> if farmers request on-platform payment processing.

```python
# SUSPENDED - These rates are NOT currently applied
# Tier 1: Sales < GHS 100
COMMISSION_TIER_1_PERCENTAGE = 5.0  # 5%

# Tier 2: Sales GHS 100-500
COMMISSION_TIER_2_PERCENTAGE = 3.0  # 3%

# Tier 3: Sales > GHS 500
COMMISSION_TIER_3_PERCENTAGE = 2.0  # 2%

# Minimum commission per transaction
COMMISSION_MINIMUM_AMOUNT = 2.00  # GHS 2.00

# To enable commission (FUTURE USE ONLY):
# PlatformSettings.enable_transaction_commission = True
```

### Current Payment Flow (Off-Platform)
1. **Customer contacts farmer** via marketplace listing
2. **Payment happens OFF-PLATFORM** (cash, MoMo, bank transfer)
3. **Farmer records sale** on the platform for tracking
4. **No commission taken** - farmer keeps 100%

### Future Payment Flow (If Commission Enabled)
1. **Customer Purchase:**
   - Customer pays via mobile money/card
   - Payment creates Payment record with Paystack reference
   - Status: pending → processing

2. **Payment Success:**
   - Paystack webhook confirms payment
   - Payment status → success
   - EggSale/BirdSale status → paid

3. **Farmer Payout:**
   - FarmerPayout record created
   - Money sent to farmer's mobile money via Paystack subaccount
   - Settlement within 24 hours (or instant with fee)
   - SMS notification to farmer

4. **Failure Handling:**
   - Payment retry (3 attempts, 5-minute delays)
   - If still failing after 72 hours → auto-refund to customer
   - Customer can request refund within 48 hours

### Mobile Money Integration
Supported providers in Ghana:
- **MTN Mobile Money** (most common)
- **Vodafone Cash**
- **AirtelTigo Money**

Farmers receive:
- Direct transfer to their mobile money account
- SMS notification with amount and transaction ID
- No app or dashboard needed

## Configuration (.env.development)

```bash
# Paystack API Keys
PAYSTACK_SECRET_KEY=sk_test_your_secret_key_here
PAYSTACK_PUBLIC_KEY=pk_test_your_public_key_here
PAYSTACK_WEBHOOK_SECRET=your_webhook_secret_here

# Payment Settings
PAYSTACK_FEE_BEARER=account  # Platform pays fees
PAYMENT_RETRY_MAX_ATTEMPTS=3
PAYMENT_RETRY_DELAY_SECONDS=300  # 5 minutes
PAYMENT_AUTO_REFUND_HOURS=72
REFUND_ELIGIBILITY_HOURS=48

# Commission Structure
COMMISSION_TIER_1_PERCENTAGE=5.0
COMMISSION_TIER_2_PERCENTAGE=3.0
COMMISSION_TIER_3_PERCENTAGE=2.0
COMMISSION_MINIMUM_AMOUNT=2.00
```

## Database Migrations

```bash
# Create migrations
python manage.py makemigrations sales_revenue

# Apply migrations
python manage.py migrate sales_revenue
```

## Admin Interface

All models registered in Django admin with:
- List views with filtering and search
- Readonly calculated fields
- Date hierarchies
- Collapsible fieldsets
- Custom display methods

## Example Sale Calculation

### Example 1: Egg Sale (10 crates @ GHS 12/crate)
```python
quantity = 10
price_per_unit = 12.00
subtotal = 10 × 12 = GHS 120.00

# Commission (Tier 2: 3% for GHS 100-500)
platform_commission = 120 × 0.03 = GHS 3.60

# Paystack fee (platform pays this)
paystack_fee = (120 × 0.015) + 0.10 = GHS 1.90

# Farmer receives
farmer_payout = 120 - 3.60 = GHS 116.40

# Customer pays
total_amount = GHS 120.00
```

**Platform profit:** GHS 3.60 (commission) - GHS 1.90 (Paystack fee) = **GHS 1.70**

### Example 2: Bird Sale (50 birds @ GHS 25/bird)
```python
quantity = 50
price_per_bird = 25.00
subtotal = 50 × 25 = GHS 1,250.00

# Commission (Tier 3: 2% for >GHS 500)
platform_commission = 1,250 × 0.02 = GHS 25.00

# Paystack fee
paystack_fee = (1,250 × 0.015) + 0.10 = GHS 18.85

# Farmer receives
farmer_payout = 1,250 - 25 = GHS 1,225.00

# Customer pays
total_amount = GHS 1,250.00
```

**Platform profit:** GHS 25.00 - GHS 18.85 = **GHS 6.15**

## Security Features

1. **Cryptographic Audit Trail:**
   - Each payout hashed with SHA-256
   - Chain of hashes prevents tampering
   - Full transaction history immutable

2. **Multi-Layer Safety Net:**
   - Automatic retry (3 attempts)
   - Manual intervention window
   - Auto-refund after 72 hours
   - Customer refund requests within 48 hours

3. **Paystack Subaccounts:**
   - Platform cannot access farmer's money
   - Direct settlement to farmer's account
   - No manual transfers needed

4. **Fee Transparency:**
   - Platform bears ALL Paystack fees
   - Farmers see exact amounts they receive
   - No surprise deductions

## Next Steps

1. **Create Paystack Service Layer:**
   - PaystackService for API calls
   - SubaccountManager for farmer accounts
   - RefundService for refund handling
   - PayoutService with retry logic

2. **Create Celery Tasks:**
   - Async payment processing
   - Scheduled payout retries
   - Auto-refund checks
   - Daily reconciliation

3. **Create API Endpoints:**
   - Customer CRUD
   - Create egg/bird sales
   - Payment status checking
   - Refund requests

4. **Testing:**
   - Unit tests for commission calculations
   - Integration tests with Paystack sandbox
   - Refund flow testing
   - Payout retry testing

## Notes

- All monetary amounts use DecimalField for precision
- UUID primary keys for security
- Comprehensive indexing for performance
- JSONField for storing raw API responses
- Ghana phone number validation (+233)
- Mobile money provider choices hardcoded for Ghana market
