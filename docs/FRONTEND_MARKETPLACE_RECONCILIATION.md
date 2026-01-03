# Frontend Marketplace Reconciliation Guide

**Date:** January 3, 2026  
**Version:** 2.1  
**Status:** Production Ready  
**Base URL:** `https://pms.alphalogictech.com`

---

## 📋 Summary of Backend Changes

This document outlines all marketplace-related backend changes that require frontend reconciliation.

### Key Changes Overview

| Area | Change | Impact |
|------|--------|--------|
| **Terminology** | "Subscription" → "Marketplace Activation" | UI text, variable names |
| **Farm Model** | New `subscription_type` values | Farmer dashboard, status displays |
| **Platform Settings** | New public endpoint for pricing | Pricing displays, signup flows |
| **Partner Offers** | New advertising system | Farmer dashboard, partner offers section |
| **Advertise With Us** | Lead capture for advertisers | New public page |
| **Celery/Redis** | Background task processing | No frontend changes needed |
| **Scaling** | Production-ready architecture | No frontend changes needed |

---

## 🚨 CRITICAL: Terminology Changes

### DO NOT use these terms in UI:
- ❌ "Subscription" (implies recurring obligation)
- ❌ "Subscription Plan"
- ❌ "Subscribe"

### USE these terms instead:
- ✅ "Marketplace Activation"
- ✅ "Marketplace Access"
- ✅ "Seller Access"
- ✅ "Activate Marketplace"

**Rationale:** Per YEA monetization strategy, "subscription" terminology deters farmers. Use "activation" to frame as a one-time enablement.

---

## 🆕 New API Endpoints

### 1. Public Platform Settings (No Auth Required)

```http
GET /api/public/platform-settings/
```

**Purpose:** Get public-facing platform pricing and feature settings for signup pages, pricing displays, etc.

**Response:**
```json
{
    "marketplace_activation_fee": "50.00",
    "marketplace_trial_days": 14,
    "marketplace_grace_period_days": 5,
    "enable_government_subsidy": true,
    "government_subsidy_percentage": "100.00",
    "enable_verified_seller_tier": false,
    "verified_seller_fee": "50.00",
    "enable_transaction_commission": false,
    "enable_ads": true,
    "free_tier_can_view_marketplace": true,
    "free_tier_can_view_prices": true,
    "free_tier_can_access_education": true
}
```

**Frontend Usage:**
- Display pricing on signup/activation pages
- Show trial period length
- Conditionally display government subsidy info
- Hide verified seller tier if disabled

---

### 2. Admin Platform Settings (Super Admin Only)

```http
GET /api/admin/platform-settings/
PUT /api/admin/platform-settings/
PATCH /api/admin/platform-settings/
```

**Required Role:** `SUPER_ADMIN` or `YEA_OFFICIAL`

**Response:** Full platform settings including commission rates, Paystack config, etc.

---

### 3. Monetization Quick Settings (Super Admin Only)

```http
GET /api/admin/platform-settings/monetization/
PATCH /api/admin/platform-settings/monetization/
```

**Purpose:** Quick access to marketplace monetization settings only.

---

### 4. Reset Platform Settings (Super Admin Only)

```http
POST /api/admin/platform-settings/reset/
```

**Purpose:** Reset all platform settings to defaults.

---

## 📦 Farm Model Changes

### New/Updated Fields on Farm Object

When fetching farm data via `/api/farms/my-farm/` or similar:

```json
{
    "id": "farm-uuid",
    "farm_name": "Alpha Farms",
    
    // MARKETPLACE ACCESS FIELDS (updated)
    "subscription_type": "government_subsidized",  // See values below
    "marketplace_enabled": true,
    "product_images_count": 5,
    
    // GOVERNMENT SUBSIDY TRACKING (new)
    "government_subsidy_active": true,
    "government_subsidy_start_date": "2026-01-01",
    "government_subsidy_end_date": "2026-12-31",
    
    // COMPUTED PROPERTIES (read-only)
    "has_marketplace_access": true,
    "core_platform_accessible": true,
    "eligible_for_government_procurement": true
}
```

### `subscription_type` Values

| Value | Display Text | Description |
|-------|-------------|-------------|
| `none` | No Marketplace Access | Cannot sell on marketplace |
| `government_subsidized` | Government-Subsidized Access | YEA program beneficiaries - free access |
| `standard` | Standard Marketplace Access | Self-paid GHS 50/month |
| `verified` | Verified Seller | Premium tier with priority features |

### Frontend Display Logic

```javascript
// Example: Display marketplace access status
function getMarketplaceStatusBadge(farm) {
    switch (farm.subscription_type) {
        case 'none':
            return { text: 'Activate Marketplace', color: 'gray', action: 'activate' };
        case 'government_subsidized':
            return { text: 'Government Sponsored', color: 'green', icon: 'shield' };
        case 'standard':
            return { text: 'Marketplace Active', color: 'blue', icon: 'check' };
        case 'verified':
            return { text: 'Verified Seller', color: 'gold', icon: 'star' };
    }
}

// Check if farmer can access marketplace features
function canAccessMarketplace(farm) {
    return farm.has_marketplace_access === true;
}

// Check if farmer has core platform access (always true for approved)
function canAccessCorePlatform(farm) {
    return farm.core_platform_accessible === true;
}
```

---

## 🎨 UI Components to Update

### 1. Farmer Dashboard

**Location:** Farmer home/dashboard page

**Changes Required:**
- Add marketplace access status badge
- Show "Activate Marketplace" CTA if `subscription_type === 'none'`
- Show government subsidy expiry warning if approaching `government_subsidy_end_date`

**Example:**
```jsx
{farm.subscription_type === 'none' ? (
    <ActivateMarketplaceBanner 
        fee={platformSettings.marketplace_activation_fee}
        trialDays={platformSettings.marketplace_trial_days}
    />
) : (
    <MarketplaceStatusBadge type={farm.subscription_type} />
)}
```

---

### 2. Marketplace Activation Flow

**New Page/Modal Required**

**When to show:** When farmer clicks "Activate Marketplace" or tries to access marketplace features without activation.

**Flow:**
1. Fetch `/api/public/platform-settings/` for pricing
2. Display activation fee and trial period
3. If government subsidy available, show that option
4. Process payment (Paystack integration)
5. On success, refresh farm data

**Wireframe:**
```
┌────────────────────────────────────────────┐
│     ACTIVATE YOUR MARKETPLACE ACCESS       │
├────────────────────────────────────────────┤
│                                            │
│  Start selling your products directly to   │
│  customers across Ghana!                   │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │  Standard Access                     │  │
│  │  GHS 50.00/month                     │  │
│  │  • List unlimited products           │  │
│  │  • Up to 20 product images          │  │
│  │  • Customer messaging               │  │
│  │  • Order management                 │  │
│  │                                      │  │
│  │  [14-day free trial included]       │  │
│  │                                      │  │
│  │  [ACTIVATE NOW]                     │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  Already in YEA program?                   │
│  Your access may be government-sponsored.  │
│  Contact your extension officer.           │
│                                            │
└────────────────────────────────────────────┘
```

---

### 3. Navigation Updates

**Marketplace menu items should:**
- Be visible to all authenticated farmers
- Show lock icon if `subscription_type === 'none'`
- On click, redirect to activation flow if no access

```jsx
<NavItem
    to="/marketplace"
    disabled={!farm.has_marketplace_access}
    badge={!farm.has_marketplace_access ? <LockIcon /> : null}
    onClick={() => {
        if (!farm.has_marketplace_access) {
            showActivationModal();
        }
    }}
>
    Marketplace
</NavItem>
```

---

### 4. Admin Platform Settings Page

**Required Role:** Super Admin or YEA Official

**New Admin Page:** `/admin/platform-settings`

**Sections:**
1. **Commission Settings** - Tier percentages and thresholds
2. **Marketplace Monetization** - Activation fee, trial days, subsidy settings
3. **Payment Configuration** - Paystack settings
4. **Feature Flags** - Enable/disable features

**Fetch:** `GET /api/admin/platform-settings/`  
**Update:** `PATCH /api/admin/platform-settings/`

---

## 🔐 Authorization Flow Changes

### Marketplace Access Check Decorator

Backend now enforces marketplace access on relevant endpoints. Frontend should pre-check to provide better UX:

```javascript
// API helper
async function checkMarketplaceAccess() {
    const farm = await getFarmData();
    return farm.has_marketplace_access;
}

// Before calling marketplace endpoints
if (!await checkMarketplaceAccess()) {
    showActivationModal();
    return;
}
// Proceed with API call
```

### Endpoints Requiring Marketplace Access

| Endpoint | Requires Activation |
|----------|---------------------|
| `GET /api/marketplace/products/` | ✅ Yes |
| `POST /api/marketplace/products/` | ✅ Yes |
| `GET /api/marketplace/orders/` | ✅ Yes |
| `GET /api/marketplace/customers/` | ✅ Yes |
| `GET /api/marketplace/` (dashboard) | ✅ Yes |
| `GET /api/farms/my-farm/` | ❌ No (core platform) |
| `GET /api/flocks/` | ❌ No (core platform) |
| `GET /api/public/marketplace/products/` | ❌ No (public) |

---

## 📊 Dashboard Updates

### Farmer Dashboard

Add these new data points:

```javascript
// Fetch platform settings for display
const platformSettings = await fetch('/api/public/platform-settings/').then(r => r.json());

// Display items
const dashboardData = {
    // Existing...
    
    // New marketplace activation info
    marketplaceStatus: farm.subscription_type,
    isMarketplaceActive: farm.has_marketplace_access,
    isGovernmentSubsidized: farm.government_subsidy_active,
    subsidyExpiresOn: farm.government_subsidy_end_date,
    
    // For non-activated farmers
    activationFee: platformSettings.marketplace_activation_fee,
    trialDays: platformSettings.marketplace_trial_days,
};
```

### Admin/YEA Dashboard

Add monetization analytics:

```javascript
// New stats to display
const monetizationStats = {
    activeFarmers: farms.filter(f => f.has_marketplace_access).length,
    governmentSubsidizedFarmers: farms.filter(f => f.government_subsidy_active).length,
    standardFarmers: farms.filter(f => f.subscription_type === 'standard').length,
    pendingActivations: farms.filter(f => f.subscription_type === 'none').length,
};
```

---

## 🔄 API Response Changes

### Farm Serializer Updates

The farm serializer now includes these fields in responses:

```diff
{
    "id": "...",
    "farm_name": "...",
    
+   "subscription_type": "government_subsidized",
+   "marketplace_enabled": true,
+   "product_images_count": 5,
+   "government_subsidy_active": true,
+   "government_subsidy_start_date": "2026-01-01",
+   "government_subsidy_end_date": "2026-12-31",
+   "has_marketplace_access": true,
+   "core_platform_accessible": true,
    
    // ... other fields
}
```

### Error Responses for Marketplace Access

When calling marketplace endpoints without activation:

```json
{
    "error": "Marketplace activation required to access this feature",
    "code": "MARKETPLACE_ACCESS_REQUIRED",
    "detail": "Activate your marketplace access to start selling products",
    "activation_url": "/marketplace/activate"
}
```

**Frontend handling:**
```javascript
if (response.code === 'MARKETPLACE_ACCESS_REQUIRED') {
    showActivationModal();
}
```

---

## ✅ Frontend Checklist

### Immediate (Required for Launch)

- [ ] Update all "Subscription" text to "Marketplace Activation"
- [ ] Add marketplace status badge to farmer dashboard
- [ ] Create marketplace activation modal/page
- [ ] Fetch and display `/api/public/platform-settings/` pricing
- [ ] Handle `MARKETPLACE_ACCESS_REQUIRED` errors
- [ ] Update navigation with lock icons for inactive farmers
- [ ] Show government subsidy expiry warnings

### Admin Panel

- [ ] Create Platform Settings admin page
- [ ] Add monetization analytics to admin dashboard
- [ ] Display farmer marketplace activation status in lists

### Nice to Have

- [ ] Activation success animation
- [ ] Email/SMS notification preferences for activation
- [ ] Government subsidy application flow (if applicable)

---

## 📝 Environment Variables

No new frontend environment variables required. All pricing and settings are fetched from the API.

---

## 🧪 Testing Scenarios

### Test Case 1: New Farmer Without Activation
1. Login as new farmer
2. Verify "Activate Marketplace" CTA is visible
3. Click marketplace nav → Should show activation modal
4. Verify pricing matches `/api/public/platform-settings/`

### Test Case 2: Government-Subsidized Farmer
1. Login as YEA program farmer
2. Verify "Government Sponsored" badge
3. Marketplace should be accessible
4. No payment prompts should appear

### Test Case 3: Standard Activated Farmer
1. Login as self-paid farmer
2. Verify "Marketplace Active" badge
3. Full marketplace access

### Test Case 4: Admin Platform Settings
1. Login as Super Admin
2. Navigate to Platform Settings
3. Modify activation fee
4. Verify change reflected in public endpoint
5. Verify farmer signup shows new price

---

## � Partner Offers / Advertising System

### Overview

The platform now includes a **Partner Offers** system for displaying targeted promotions from agricultural partners (feed suppliers, banks, insurance, etc.) on farmer dashboards.

**Key Concept:** This replaces generic Google AdSense on authenticated pages with curated, high-value offers relevant to farmers.

### New Endpoints

#### 1. Get Partner Offers for Farmer Dashboard

```http
GET /api/advertising/offers/
Authorization: Bearer {token}
```

**Query Parameters:**
- `source` (optional): Page source for analytics (e.g., `dashboard`, `marketplace`)

**Response:**
```json
{
    "offers": [
        {
            "id": "offer-uuid",
            "partner_name": "Olam Ghana",
            "partner_logo": "https://pms.alphalogictech.com/media/partners/logos/olam.png",
            "partner_category": "Feed & Nutrition Supplier",
            "partner_verified": true,
            "title": "10% Off Starter Feed - New Year Special",
            "description": "Get premium starter feed for your day-old chicks at 10% off. Use code YEAPOULTRY at checkout.",
            "offer_type": "discount",
            "offer_type_display": "Discount / Promo Code",
            "image": "https://pms.alphalogictech.com/media/partners/offers/starter-feed.jpg",
            "cta_text": "Shop Now",
            "cta_url": "https://olamghana.com/poultry-feed?promo=YEAPOULTRY",
            "promo_code": "YEAPOULTRY",
            "is_featured": true
        },
        {
            "id": "offer-uuid-2",
            "partner_name": "Ecobank Ghana",
            "partner_logo": "...",
            "partner_category": "Banks & Financial Services",
            "partner_verified": true,
            "title": "Agricultural Loan - Up to GHS 50,000",
            "description": "Expand your poultry operation with our low-interest agricultural loans. Pre-qualify in 5 minutes.",
            "offer_type": "loan",
            "offer_type_display": "Loan / Financing",
            "image": "...",
            "cta_text": "Check Eligibility",
            "cta_url": "https://ecobank.com/agri-loan",
            "promo_code": "",
            "is_featured": false
        }
    ],
    "count": 2
}
```

---

#### 2. Record Offer Click

Call this when a farmer clicks on an offer:

```http
POST /api/advertising/offers/click/
Authorization: Bearer {token}
Content-Type: application/json

{
    "offer_id": "offer-uuid",
    "source_page": "dashboard"
}
```

**Response:**
```json
{
    "success": true,
    "redirect_url": "https://olamghana.com/poultry-feed?promo=YEAPOULTRY"
}
```

---

#### 3. Dismiss Offer

Call this when a farmer dismisses/closes an offer:

```http
POST /api/advertising/offers/{offer_id}/dismiss/
Authorization: Bearer {token}
```

---

### Frontend Implementation

#### Partner Offers Component for Farmer Dashboard

```jsx
function PartnerOffers() {
    const [offers, setOffers] = useState([]);
    
    useEffect(() => {
        fetch('/api/advertising/offers/?source=dashboard', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(data => setOffers(data.offers));
    }, []);
    
    const handleOfferClick = async (offer) => {
        // Record click for analytics
        await fetch('/api/advertising/offers/click/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                offer_id: offer.id,
                source_page: 'dashboard'
            })
        });
        
        // Open offer URL
        window.open(offer.cta_url, '_blank');
    };
    
    return (
        <div className="partner-offers">
            <h3>Special Offers for Farmers</h3>
            {offers.map(offer => (
                <OfferCard 
                    key={offer.id}
                    offer={offer}
                    onClick={() => handleOfferClick(offer)}
                    onDismiss={() => dismissOffer(offer.id)}
                />
            ))}
        </div>
    );
}
```

---

## 📝 Advertise With Us Page

### Public Endpoint (No Auth)

```http
GET /api/public/advertise/
```

Returns advertising info and form options:

```json
{
    "title": "Advertise on YEA Poultry Platform",
    "description": "Reach thousands of verified poultry farmers across Ghana",
    "benefits": [
        "Direct access to verified, active poultry farmers",
        "Target by region, flock size, or production volume",
        "Farmers with transaction history and production data",
        "Premium placement on farmer dashboards",
        "Detailed analytics and reporting"
    ],
    "categories": [
        {"value": "feed_supplier", "label": "Feed & Nutrition Supplier"},
        {"value": "equipment", "label": "Equipment & Infrastructure"},
        {"value": "veterinary", "label": "Veterinary Services"},
        {"value": "financial", "label": "Banks & Financial Services"},
        {"value": "insurance", "label": "Insurance Provider"},
        ...
    ],
    "budget_ranges": [
        {"value": "under_500", "label": "Under GHS 500/month"},
        {"value": "500_2000", "label": "GHS 500 - 2,000/month"},
        {"value": "2000_5000", "label": "GHS 2,000 - 5,000/month"},
        {"value": "over_5000", "label": "Over GHS 5,000/month"},
        {"value": "not_sure", "label": "Not Sure Yet"}
    ],
    "platform_stats": {
        "total_farmers": 1250,
        "active_farmers": 890,
        "regions_covered": 10
    }
}
```

### Submit Advertiser Lead

```http
POST /api/public/advertise/
Content-Type: application/json

{
    "company_name": "Agri Feeds Ltd",
    "category": "feed_supplier",
    "website": "https://agrifeeds.gh",
    "contact_name": "John Mensah",
    "contact_email": "john@agrifeeds.gh",
    "contact_phone": "+233244123456",
    "job_title": "Marketing Manager",
    "advertising_interest": "We want to promote our new layer feed to farmers in Greater Accra and Ashanti regions.",
    "target_audience": "Farmers with 500+ birds, layer operations",
    "budget_range": "2000_5000"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Thank you for your interest! Our team will contact you within 2 business days.",
    "lead_id": "lead-uuid"
}
```

### Frontend Page Wireframe

```
┌────────────────────────────────────────────────────────────┐
│            ADVERTISE ON YEA POULTRY PLATFORM               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Reach thousands of verified poultry farmers across Ghana  │
│                                                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │  1,250  │  │   890   │  │   10    │                     │
│  │ Farmers │  │ Active  │  │ Regions │                     │
│  └─────────┘  └─────────┘  └─────────┘                     │
│                                                            │
│  ✓ Direct access to verified farmers                       │
│  ✓ Target by region, flock size, production                │
│  ✓ Premium placement on dashboards                         │
│  ✓ Detailed analytics and reporting                        │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                    GET STARTED                             │
│                                                            │
│  Company Name: [_______________________]                   │
│  Category:     [Feed Supplier       ▼]                     │
│  Website:      [_______________________]                   │
│                                                            │
│  Contact Name: [_______________________]                   │
│  Email:        [_______________________]                   │
│  Phone:        [_______________________]                   │
│                                                            │
│  What would you like to advertise?                         │
│  [                                    ]                    │
│  [                                    ]                    │
│                                                            │
│  Monthly Budget: [GHS 2,000-5,000    ▼]                    │
│                                                            │
│              [SUBMIT INQUIRY]                              │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Admin Advertising Management

### Endpoints for Super Admin / YEA Official

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/advertising/partners/` | GET, POST | List/create partners |
| `/api/admin/advertising/partners/{id}/` | GET, PUT, DELETE | Partner details |
| `/api/admin/advertising/offers/` | GET, POST | List/create offers |
| `/api/admin/advertising/offers/{id}/` | GET, PUT, DELETE | Offer details |
| `/api/admin/advertising/leads/` | GET | List advertiser leads |
| `/api/admin/advertising/leads/{id}/` | GET, PUT | Lead details/update status |
| `/api/admin/advertising/analytics/` | GET | Advertising analytics |

### Analytics Response

```json
{
    "partners": {
        "total": 5,
        "verified": 3
    },
    "offers": {
        "active": 8,
        "total_impressions": 15420,
        "total_clicks": 342
    },
    "leads": {
        "new": 3,
        "total": 12,
        "converted": 5,
        "conversion_rate": "41.7%"
    },
    "top_offers": [
        {
            "id": "...",
            "title": "10% Off Starter Feed",
            "partner_name": "Olam Ghana",
            "impressions": 5230,
            "clicks": 156,
            "click_through_rate": "2.98"
        }
    ]
}
```

---

## �📞 Support

For questions about these changes:
- Backend issues: Check API error responses
- Integration help: Refer to [MARKETPLACE_API_DOCUMENTATION.md](./MARKETPLACE_API_DOCUMENTATION.md)
- Guest checkout: See [GUEST_CHECKOUT_POS_GUIDE.md](./GUEST_CHECKOUT_POS_GUIDE.md)
