# Partner Advertising System - API Documentation

**Date:** January 4, 2026  
**Version:** 1.0  
**Status:** Production Ready  
**Base URL:** `https://pms.alphalogictech.com`

---

## 📋 Overview

The Partner Advertising System is a **curated advertising platform** for businesses to reach verified poultry farmers. Unlike AdSense (external ads), this system manages:

- **Direct partnerships** with agricultural businesses
- **Targeted offers** based on farmer profiles
- **Lead capture** from "Advertise With Us" page
- **Analytics** on impressions, clicks, and conversions

---

## 🎯 Partner Categories

| Value | Display Label | Examples |
|-------|---------------|----------|
| `feed_supplier` | Feed & Nutrition Supplier | Olam, Agricare |
| `equipment` | Equipment & Infrastructure | Incubators, cages, drinkers |
| `veterinary` | Veterinary Services | Vet clinics, vaccines |
| `chicks_supplier` | Day-Old Chicks Supplier | Hatcheries |
| `financial` | Banks & Financial Services | Ecobank, GCB, MFIs |
| `insurance` | Insurance Provider | GLICO, SIC |
| `aggregator` | Aggregator / Offtaker | Bulk buyers, processors |
| `training` | Training & Education | Agricultural training |
| `logistics` | Logistics & Delivery | Transport services |
| `other` | Other Agricultural Service | - |

---

## 🔐 Authentication Requirements

| Endpoint Group | Auth Required | Roles Allowed |
|----------------|---------------|---------------|
| `/api/public/advertise/` | ❌ No | Anyone |
| `/api/advertising/` | ✅ Yes | Farmers (with farm) |
| `/api/admin/advertising/` | ✅ Yes | SUPER_ADMIN, YEA_OFFICIAL |

---

# 📱 PUBLIC ENDPOINTS

## Get Advertising Info

### `GET /api/public/advertise/`

Returns information about advertising on the platform, useful for the "Advertise With Us" landing page.

**Response:**
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
        {"value": "chicks_supplier", "label": "Day-Old Chicks Supplier"},
        {"value": "financial", "label": "Banks & Financial Services"},
        {"value": "insurance", "label": "Insurance Provider"},
        {"value": "aggregator", "label": "Aggregator / Offtaker"},
        {"value": "training", "label": "Training & Education"},
        {"value": "logistics", "label": "Logistics & Delivery"},
        {"value": "other", "label": "Other Agricultural Service"}
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
        "regions_covered": 16
    }
}
```

**Frontend Usage:**
```tsx
function AdvertiseWithUsPage() {
    const [info, setInfo] = useState(null);
    
    useEffect(() => {
        fetch('/api/public/advertise/')
            .then(res => res.json())
            .then(setInfo);
    }, []);
    
    if (!info) return <Loading />;
    
    return (
        <div className="advertise-page">
            <Hero 
                title={info.title}
                description={info.description}
            />
            
            <BenefitsSection benefits={info.benefits} />
            
            <StatsSection stats={info.platform_stats} />
            
            <LeadCaptureForm 
                categories={info.categories}
                budgetRanges={info.budget_ranges}
            />
        </div>
    );
}
```

---

## Submit Advertiser Lead

### `POST /api/public/advertise/`

Submit a lead from a business interested in advertising.

**Request Body:**
```json
{
    "company_name": "Ecobank Ghana",
    "category": "financial",
    "website": "https://ecobank.com/gh",
    "contact_name": "Kwame Mensah",
    "contact_email": "k.mensah@ecobank.com",
    "contact_phone": "+233244123456",
    "job_title": "Agricultural Banking Manager",
    "advertising_interest": "We want to promote our agricultural loan products to poultry farmers. Loans up to GHS 100,000 for farm expansion.",
    "target_audience": "Established farmers with 500+ birds looking to expand",
    "budget_range": "2000_5000"
}
```

**Required Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `company_name` | string | Company name |
| `contact_name` | string | Contact person name |
| `contact_email` | string | Email address |
| `contact_phone` | string | Phone number |
| `advertising_interest` | string | What they want to advertise |

**Optional Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Partner category (see list above) |
| `website` | string | Company website URL |
| `job_title` | string | Contact person's title |
| `target_audience` | string | Who they want to reach |
| `budget_range` | string | Monthly budget range |

**Success Response (201):**
```json
{
    "success": true,
    "message": "Thank you for your interest! Our team will contact you within 2 business days.",
    "lead_id": "uuid-here"
}
```

**Error Response (400):**
```json
{
    "contact_email": ["Enter a valid email address."],
    "contact_name": ["This field is required."]
}
```

**Frontend Usage:**
```tsx
interface LeadFormData {
    company_name: string;
    category: string;
    website?: string;
    contact_name: string;
    contact_email: string;
    contact_phone: string;
    job_title?: string;
    advertising_interest: string;
    target_audience?: string;
    budget_range: string;
}

function LeadCaptureForm({ categories, budgetRanges }) {
    const [formData, setFormData] = useState<LeadFormData>({
        company_name: '',
        category: 'other',
        contact_name: '',
        contact_email: '',
        contact_phone: '',
        advertising_interest: '',
        budget_range: 'not_sure',
    });
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);
    
    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        
        const res = await fetch('/api/public/advertise/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData),
        });
        
        if (res.ok) {
            setSuccess(true);
        } else {
            const errors = await res.json();
            // Handle validation errors
        }
        
        setSubmitting(false);
    };
    
    if (success) {
        return (
            <SuccessMessage>
                Thank you! Our team will contact you within 2 business days.
            </SuccessMessage>
        );
    }
    
    return (
        <form onSubmit={handleSubmit}>
            <Input 
                label="Company Name" 
                value={formData.company_name}
                onChange={(v) => setFormData(f => ({ ...f, company_name: v }))}
                required
            />
            
            <Select 
                label="Business Category"
                options={categories}
                value={formData.category}
                onChange={(v) => setFormData(f => ({ ...f, category: v }))}
            />
            
            <Input label="Your Name" value={formData.contact_name} required />
            <Input label="Email" type="email" value={formData.contact_email} required />
            <Input label="Phone" type="tel" value={formData.contact_phone} required />
            
            <Textarea 
                label="What would you like to advertise?"
                value={formData.advertising_interest}
                required
            />
            
            <Select 
                label="Monthly Budget"
                options={budgetRanges}
                value={formData.budget_range}
            />
            
            <Button type="submit" loading={submitting}>
                Submit Inquiry
            </Button>
        </form>
    );
}
```

---

# 🌾 FARMER ENDPOINTS

## Get Relevant Offers

### `GET /api/advertising/offers/`

Get partner offers targeted to the authenticated farmer. Returns offers based on:
- Farmer's region
- Farm flock size
- Marketplace activation status
- Government program participation

**Headers:**
```http
Authorization: Bearer {jwt_token}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `source` | string | Page where offers are displayed (default: "dashboard") |

**Response:**
```json
{
    "offers": [
        {
            "id": "uuid",
            "partner_name": "Ecobank Ghana",
            "partner_logo": "/media/partners/logos/ecobank.png",
            "partner_category": "Banks & Financial Services",
            "partner_verified": true,
            "title": "Agricultural Loan - Up to GHS 100,000",
            "description": "Expand your poultry farm with our flexible agricultural loans. Competitive rates starting at 15% APR. Quick approval within 7 days.",
            "offer_type": "loan",
            "offer_type_display": "Loan / Financing",
            "image": "/media/partners/offers/ecobank-agri-loan.jpg",
            "cta_text": "Apply Now",
            "cta_url": "https://ecobank.com/gh/agri-loan?ref=yeapms",
            "promo_code": "",
            "is_featured": true
        },
        {
            "id": "uuid",
            "partner_name": "Agricare Feeds",
            "partner_logo": "/media/partners/logos/agricare.png",
            "partner_category": "Feed & Nutrition Supplier",
            "partner_verified": true,
            "title": "10% Off Starter & Grower Feed",
            "description": "Use code YEAPOULTRY for 10% off your first order of starter or grower feed. Free delivery on orders over GHS 500.",
            "offer_type": "discount",
            "offer_type_display": "Discount / Promo Code",
            "image": "/media/partners/offers/agricare-discount.jpg",
            "cta_text": "Shop Now",
            "cta_url": "https://agricare.com.gh/shop",
            "promo_code": "YEAPOULTRY",
            "is_featured": false
        }
    ],
    "count": 2
}
```

**Offer Types:**
| Value | Display | Description |
|-------|---------|-------------|
| `discount` | Discount / Promo Code | Percentage or fixed discount |
| `loan` | Loan / Financing | Financial products |
| `insurance` | Insurance Product | Livestock/farm insurance |
| `service` | Service Offering | Professional services |
| `product` | Product Promotion | Physical products |
| `event` | Event / Training | Workshops, seminars |
| `bulk_purchase` | Bulk Purchase Deal | Volume discounts |

**Frontend Usage:**
```tsx
interface PartnerOffer {
    id: string;
    partner_name: string;
    partner_logo: string | null;
    partner_category: string;
    partner_verified: boolean;
    title: string;
    description: string;
    offer_type: string;
    offer_type_display: string;
    image: string | null;
    cta_text: string;
    cta_url: string;
    promo_code: string;
    is_featured: boolean;
}

function DashboardOffers() {
    const [offers, setOffers] = useState<PartnerOffer[]>([]);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        fetch('/api/advertising/offers/?source=dashboard', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(data => setOffers(data.offers))
        .finally(() => setLoading(false));
    }, []);
    
    if (loading) return <OffersSkeleton />;
    if (offers.length === 0) return null; // Hide section if no offers
    
    return (
        <section className="partner-offers">
            <h3>Special Offers for You</h3>
            
            <div className="offers-carousel">
                {offers.map(offer => (
                    <OfferCard 
                        key={offer.id} 
                        offer={offer}
                        onDismiss={() => handleDismiss(offer.id)}
                    />
                ))}
            </div>
        </section>
    );
}

function OfferCard({ offer, onDismiss }: { offer: PartnerOffer; onDismiss: () => void }) {
    const handleClick = async () => {
        // Record click before redirecting
        await fetch('/api/advertising/offers/click/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                offer_id: offer.id,
                source_page: 'dashboard',
            }),
        });
        
        // Redirect to offer URL
        window.open(offer.cta_url, '_blank');
    };
    
    return (
        <div className={`offer-card ${offer.is_featured ? 'featured' : ''}`}>
            {offer.is_featured && <span className="featured-badge">Featured</span>}
            
            <button className="dismiss-btn" onClick={onDismiss}>×</button>
            
            {offer.image && (
                <img src={offer.image} alt={offer.title} className="offer-image" />
            )}
            
            <div className="offer-content">
                <div className="partner-info">
                    {offer.partner_logo && (
                        <img src={offer.partner_logo} alt="" className="partner-logo" />
                    )}
                    <span className="partner-name">
                        {offer.partner_name}
                        {offer.partner_verified && <VerifiedBadge />}
                    </span>
                </div>
                
                <h4>{offer.title}</h4>
                <p>{offer.description}</p>
                
                {offer.promo_code && (
                    <div className="promo-code">
                        Code: <code>{offer.promo_code}</code>
                        <CopyButton text={offer.promo_code} />
                    </div>
                )}
                
                <Button onClick={handleClick}>
                    {offer.cta_text}
                </Button>
            </div>
        </div>
    );
}
```

---

## Record Offer Click

### `POST /api/advertising/offers/click/`

Record when a farmer clicks on an offer. Call this **before** redirecting to the offer URL.

**Request Body:**
```json
{
    "offer_id": "uuid-of-offer",
    "source_page": "dashboard"
}
```

**Response:**
```json
{
    "success": true,
    "redirect_url": "https://ecobank.com/gh/agri-loan?ref=yeapms"
}
```

**Error Response (404):**
```json
{
    "error": "Offer not found",
    "code": "OFFER_NOT_FOUND"
}
```

---

## Dismiss Offer

### `POST /api/advertising/offers/{offer_id}/dismiss/`

Record when a farmer dismisses an offer. Can be used to avoid showing it again.

**Request Body (optional):**
```json
{
    "source_page": "dashboard"
}
```

**Response:**
```json
{
    "success": true
}
```

---

# 🔧 ADMIN ENDPOINTS

All admin endpoints require authentication with `SUPER_ADMIN` or `YEA_OFFICIAL` role.

## Partners Management

### List Partners

#### `GET /api/admin/advertising/partners/`

**Response:**
```json
[
    {
        "id": "uuid",
        "company_name": "Ecobank Ghana",
        "category": "financial",
        "category_display": "Banks & Financial Services",
        "logo": "/media/partners/logos/ecobank.png",
        "website": "https://ecobank.com/gh",
        "description": "Leading pan-African bank with agricultural financing solutions",
        "contact_name": "Kwame Mensah",
        "contact_email": "k.mensah@ecobank.com",
        "contact_phone": "+233244123456",
        "is_verified": true,
        "is_active": true,
        "has_active_contract": true,
        "contract_start_date": "2025-01-01",
        "contract_end_date": "2025-12-31",
        "monthly_fee": "2000.00",
        "active_offers_count": 3,
        "created_at": "2025-01-01T10:00:00Z",
        "updated_at": "2025-06-15T14:30:00Z"
    }
]
```

### Create Partner

#### `POST /api/admin/advertising/partners/`

**Request Body:**
```json
{
    "company_name": "GLICO Insurance",
    "category": "insurance",
    "website": "https://glico.com.gh",
    "description": "Leading insurance provider with livestock coverage",
    "contact_name": "Ama Owusu",
    "contact_email": "a.owusu@glico.com.gh",
    "contact_phone": "+233244567890",
    "is_verified": true,
    "is_active": true,
    "contract_start_date": "2026-01-01",
    "contract_end_date": "2026-12-31",
    "monthly_fee": "1500.00"
}
```

### Update Partner

#### `PUT /api/admin/advertising/partners/{id}/`

Same body as create.

### Delete Partner

#### `DELETE /api/admin/advertising/partners/{id}/`

**Response:** 204 No Content

---

## Offers Management

### List Offers

#### `GET /api/admin/advertising/offers/`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `partner` | uuid | Filter by partner ID |
| `active` | boolean | Filter active offers only (`true`) |

**Response:**
```json
[
    {
        "id": "uuid",
        "partner": "partner-uuid",
        "partner_name": "Ecobank Ghana",
        "partner_logo": "/media/partners/logos/ecobank.png",
        "partner_category": "Banks & Financial Services",
        "title": "Agricultural Loan - Up to GHS 100,000",
        "description": "Expand your poultry farm with our flexible agricultural loans.",
        "offer_type": "loan",
        "offer_type_display": "Loan / Financing",
        "image": "/media/partners/offers/ecobank-loan.jpg",
        "cta_text": "Apply Now",
        "cta_url": "https://ecobank.com/gh/agri-loan",
        "promo_code": "",
        "targeting": "all",
        "targeting_display": "All Farmers",
        "target_regions": [],
        "min_flock_size": null,
        "max_flock_size": null,
        "start_date": "2025-01-01T00:00:00Z",
        "end_date": "2025-12-31T23:59:59Z",
        "is_active": true,
        "is_featured": true,
        "priority": 90,
        "is_currently_active": true,
        "impressions": 5420,
        "clicks": 342,
        "click_through_rate": "6.31",
        "created_at": "2025-01-01T10:00:00Z",
        "updated_at": "2025-06-15T14:30:00Z"
    }
]
```

### Create Offer

#### `POST /api/admin/advertising/offers/`

**Request Body:**
```json
{
    "partner": "partner-uuid",
    "title": "Free Vaccination Campaign",
    "description": "Register for free Newcastle Disease vaccination for your flock. Limited to first 100 farmers in Greater Accra region.",
    "offer_type": "event",
    "cta_text": "Register Now",
    "cta_url": "https://vetclinic.com/register",
    "targeting": "region",
    "target_regions": ["Greater Accra"],
    "start_date": "2026-02-01T00:00:00Z",
    "end_date": "2026-02-28T23:59:59Z",
    "is_active": true,
    "is_featured": false,
    "priority": 50
}
```

**Targeting Options:**
| Value | Description | Additional Fields |
|-------|-------------|-------------------|
| `all` | All farmers | None |
| `region` | By region | `target_regions: ["Greater Accra", "Ashanti"]` |
| `flock_size` | By flock size | `min_flock_size`, `max_flock_size` |
| `marketplace` | Marketplace active farmers | None |
| `government` | Government program farmers | None |

### Update/Delete Offer

#### `PUT /api/admin/advertising/offers/{id}/`
#### `DELETE /api/admin/advertising/offers/{id}/`

---

## Leads Management

### List Leads

#### `GET /api/admin/advertising/leads/`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by lead status |

**Lead Status Values:**
| Value | Display | Description |
|-------|---------|-------------|
| `new` | New Lead | Just submitted |
| `contacted` | Contacted | Initial contact made |
| `meeting_scheduled` | Meeting Scheduled | Meeting arranged |
| `proposal_sent` | Proposal Sent | Proposal delivered |
| `negotiating` | Negotiating | In negotiation |
| `converted` | Converted to Partner | Deal closed |
| `declined` | Declined | Lead declined |
| `lost` | Lost | Lost opportunity |

**Response:**
```json
[
    {
        "id": "uuid",
        "company_name": "AgriFinance Ltd",
        "category": "financial",
        "category_display": "Banks & Financial Services",
        "website": "https://agrifinance.com.gh",
        "contact_name": "Kofi Asante",
        "contact_email": "kofi@agrifinance.com.gh",
        "contact_phone": "+233244789012",
        "job_title": "Marketing Manager",
        "advertising_interest": "We provide microloans to smallholder farmers and want to reach poultry farmers.",
        "target_audience": "Small to medium scale farmers with 100-1000 birds",
        "budget_range": "500_2000",
        "budget_display": "GHS 500 - 2,000/month",
        "status": "new",
        "status_display": "New Lead",
        "admin_notes": "",
        "assigned_to": null,
        "assigned_to_name": null,
        "follow_up_date": null,
        "converted_partner": null,
        "created_at": "2026-01-04T10:30:00Z",
        "updated_at": "2026-01-04T10:30:00Z"
    }
]
```

### Update Lead

#### `PUT /api/admin/advertising/leads/{id}/`

**Request Body:**
```json
{
    "status": "contacted",
    "admin_notes": "Called on Jan 4. Very interested. Scheduled demo for Jan 8.",
    "assigned_to": "admin-user-uuid",
    "follow_up_date": "2026-01-08"
}
```

### Convert Lead to Partner

When a lead is converted, update the lead status and create a Partner:

```tsx
async function convertLeadToPartner(leadId: string, lead: Lead) {
    // 1. Create the partner
    const partnerRes = await fetch('/api/admin/advertising/partners/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            company_name: lead.company_name,
            category: lead.category,
            website: lead.website,
            contact_name: lead.contact_name,
            contact_email: lead.contact_email,
            contact_phone: lead.contact_phone,
            is_active: true,
            contract_start_date: new Date().toISOString().split('T')[0],
        }),
    });
    const partner = await partnerRes.json();
    
    // 2. Update lead status
    await fetch(`/api/admin/advertising/leads/${leadId}/`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            status: 'converted',
            converted_partner: partner.id,
        }),
    });
    
    return partner;
}
```

---

## Analytics

### Get Advertising Analytics

#### `GET /api/admin/advertising/analytics/`

**Response:**
```json
{
    "partners": {
        "total": 12,
        "verified": 10
    },
    "offers": {
        "active": 25,
        "total_impressions": 45280,
        "total_clicks": 2845
    },
    "leads": {
        "new": 5,
        "total": 45,
        "converted": 12,
        "conversion_rate": "26.7%"
    },
    "top_offers": [
        {
            "id": "uuid",
            "title": "Agricultural Loan - Up to GHS 100,000",
            "partner_name": "Ecobank Ghana",
            "impressions": 5420,
            "clicks": 342,
            "click_through_rate": "6.31",
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-12-31T23:59:59Z",
            "is_active": true
        }
    ]
}
```

**Frontend Usage:**
```tsx
function AdvertisingDashboard() {
    const [analytics, setAnalytics] = useState(null);
    
    useEffect(() => {
        fetch('/api/admin/advertising/analytics/', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(setAnalytics);
    }, []);
    
    return (
        <div className="advertising-dashboard">
            <h2>Advertising Overview</h2>
            
            <div className="stats-grid">
                <StatCard 
                    title="Active Partners" 
                    value={analytics?.partners.total}
                    subtitle={`${analytics?.partners.verified} verified`}
                />
                <StatCard 
                    title="Active Offers" 
                    value={analytics?.offers.active}
                />
                <StatCard 
                    title="Total Impressions" 
                    value={formatNumber(analytics?.offers.total_impressions)}
                />
                <StatCard 
                    title="Total Clicks" 
                    value={formatNumber(analytics?.offers.total_clicks)}
                    subtitle={`${(analytics?.offers.total_clicks / analytics?.offers.total_impressions * 100).toFixed(1)}% CTR`}
                />
            </div>
            
            <div className="leads-section">
                <h3>Lead Pipeline</h3>
                <LeadFunnel 
                    new={analytics?.leads.new}
                    total={analytics?.leads.total}
                    converted={analytics?.leads.converted}
                />
            </div>
            
            <div className="top-offers">
                <h3>Top Performing Offers</h3>
                <TopOffersTable offers={analytics?.top_offers || []} />
            </div>
        </div>
    );
}
```

---

## 🎨 UI Component Recommendations

### Offer Card Styles

```css
.offer-card {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
}

.offer-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.offer-card.featured {
    border: 2px solid #4CAF50;
}

.featured-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    background: #4CAF50;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
}

.promo-code code {
    background: #f5f5f5;
    padding: 4px 8px;
    border-radius: 4px;
    font-family: monospace;
    font-weight: 600;
}
```

### Category Icons

```tsx
const categoryIcons: Record<string, ReactNode> = {
    feed_supplier: <WheatIcon />,
    equipment: <SettingsIcon />,
    veterinary: <MedicalIcon />,
    chicks_supplier: <ChickIcon />,
    financial: <BankIcon />,
    insurance: <ShieldIcon />,
    aggregator: <TruckIcon />,
    training: <GraduationIcon />,
    logistics: <DeliveryIcon />,
    other: <BuildingIcon />,
};
```

---

## 🔒 Access Control Summary

| Feature | FARMER | YEA_OFFICIAL | SUPER_ADMIN |
|---------|--------|--------------|-------------|
| View offers | ✅ | ❌ | ❌ |
| Click offers | ✅ | ❌ | ❌ |
| Dismiss offers | ✅ | ❌ | ❌ |
| Manage partners | ❌ | ✅ | ✅ |
| Manage offers | ❌ | ✅ | ✅ |
| View leads | ❌ | ✅ | ✅ |
| Update leads | ❌ | ✅ | ✅ |
| View analytics | ❌ | ✅ | ✅ |
| A/B Testing | ❌ | ✅ | ✅ |
| Manage conversions | ❌ | ✅ | ✅ |
| **View ad revenue** | ❌ | ❌ | ✅ |
| **Manage ad payments** | ❌ | ❌ | ✅ |

---

## 📱 Mobile Considerations

- Offer cards should be full-width on mobile
- Carousel navigation with swipe gestures
- Tap-to-copy for promo codes
- Large touch targets for CTA buttons
- Consider bottom sheet for offer details on mobile

---

# 🧪 A/B TESTING

## Overview

A/B testing allows you to test different versions of an offer to optimize performance.

### Create Variant

#### `POST /api/admin/advertising/offers/{offer_id}/variants/`

**Request Body:**
```json
{
    "name": "Green CTA",
    "title": "Save GHS 50 on Your First Order",
    "description": "",
    "cta_text": "Claim Discount",
    "traffic_percentage": 50,
    "is_active": true
}
```

### Get A/B Test Results

#### `GET /api/admin/advertising/offers/{offer_id}/ab-results/`

**Response:**
```json
{
    "offer_id": "uuid",
    "offer_title": "10% Off Starter Feed",
    "is_ab_test_active": true,
    "variants": [
        {
            "id": "variant-uuid-1",
            "name": "Control",
            "traffic_percentage": 50,
            "impressions": 5000,
            "clicks": 250,
            "conversions": 25,
            "ctr": "5.00%",
            "cvr": "10.00%",
            "is_winner": false
        },
        {
            "id": "variant-uuid-2",
            "name": "Green CTA",
            "traffic_percentage": 50,
            "impressions": 5000,
            "clicks": 350,
            "conversions": 42,
            "ctr": "7.00%",
            "cvr": "12.00%",
            "is_winner": true
        }
    ],
    "base_offer": {
        "id": "base",
        "name": "Original (No Variant)",
        "impressions": 10000,
        "clicks": 600,
        "ctr": "6.00%"
    },
    "recommendations": {
        "best_ctr_variant": "variant-uuid-2",
        "best_cvr_variant": "variant-uuid-2",
        "statistical_significance": "Sufficient data for analysis"
    }
}
```

---

# 📊 CONVERSION TRACKING

## Overview

Track when farmers complete actions after clicking offers:
- Sign ups with partners
- Purchases using promo codes
- Loan applications
- Event registrations

### List Conversions

#### `GET /api/admin/advertising/conversions/`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `offer` | uuid | Filter by offer |
| `partner` | uuid | Filter by partner |
| `verified` | boolean | Filter by verification status |

**Response:**
```json
[
    {
        "id": "uuid",
        "offer": "offer-uuid",
        "offer_title": "Agricultural Loan",
        "partner_name": "Ecobank Ghana",
        "variant": null,
        "variant_name": null,
        "farm": "farm-uuid",
        "farm_name": "Kwame's Poultry",
        "conversion_type": "application",
        "conversion_type_display": "Application Submitted",
        "conversion_value": "5000.00",
        "promo_code_used": "YEAFARM2025",
        "external_reference": "ECO-APP-12345",
        "source": "webhook",
        "source_display": "Partner Webhook",
        "is_verified": true,
        "verified_by": "admin-uuid",
        "verified_at": "2026-01-04T12:00:00Z",
        "created_at": "2026-01-04T10:30:00Z"
    }
]
```

### Manual Conversion Entry

#### `POST /api/admin/advertising/conversions/`

**Request Body:**
```json
{
    "offer": "offer-uuid",
    "farm_id": "farm-uuid",
    "conversion_type": "purchase",
    "conversion_value": "250.00",
    "promo_code_used": "YEAPOULTRY",
    "notes": "Verified via partner email"
}
```

### Verify Conversion

#### `POST /api/admin/advertising/conversions/{id}/verify/`

**Response:**
```json
{
    "success": true,
    "message": "Conversion verified successfully"
}
```

---

# 🔗 PARTNER WEBHOOK API

Partners can send conversion data via webhook to automatically track farmer actions.

## Setup

1. Admin creates webhook key for partner via `/api/admin/advertising/webhook-keys/`
2. Partner receives API key
3. Partner sends conversions to webhook endpoint

### Send Conversion (Partner → Platform)

#### `POST /api/advertising/webhook/conversion/`

**Headers:**
```http
X-API-Key: partner-api-key-here
Content-Type: application/json
```

**Request Body:**
```json
{
    "offer_id": "offer-uuid",
    "conversion_type": "purchase",
    "conversion_value": 500.00,
    "promo_code": "YEAPOULTRY",
    "external_reference": "ORD-12345",
    "farmer_phone": "+233244123456"
}
```

**Conversion Types:**
| Type | Description |
|------|-------------|
| `signup` | Partner Sign Up |
| `purchase` | Purchase Made |
| `application` | Application Submitted |
| `registration` | Event Registration |
| `quote_request` | Quote Requested |
| `contact` | Contact Form Submitted |
| `download` | Resource Downloaded |
| `other` | Other Conversion |

**Success Response (201):**
```json
{
    "success": true,
    "conversion_id": "uuid",
    "message": "Conversion recorded successfully"
}
```

### Webhook Key Management

#### List Webhook Keys
`GET /api/admin/advertising/webhook-keys/`

#### Create Webhook Key
`POST /api/admin/advertising/webhook-keys/`

```json
{
    "partner": "partner-uuid",
    "daily_limit": 1000,
    "is_active": true
}
```

#### Regenerate Key
`POST /api/admin/advertising/webhook-keys/{id}/regenerate/`

```json
{
    "success": true,
    "message": "API key regenerated successfully",
    "api_key": "new-api-key-here"
}
```

---

# 💰 PARTNER PAYMENTS (Revenue Tracking)

**Access:** SUPER_ADMIN only

Track advertising revenue from partners - monthly fees, campaign payments, etc.

### List Payments

#### `GET /api/admin/advertising/payments/`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `partner` | uuid | Filter by partner |
| `status` | string | pending, paid, overdue, cancelled, refunded |

**Response:**
```json
[
    {
        "id": "uuid",
        "partner": "partner-uuid",
        "partner_name": "Ecobank Ghana",
        "partner_category": "Banks & Financial Services",
        "amount": "2000.00",
        "currency": "GHS",
        "payment_type": "monthly_fee",
        "payment_type_display": "Monthly Advertising Fee",
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
        "status": "paid",
        "status_display": "Paid",
        "payment_method": "bank_transfer",
        "payment_method_display": "Bank Transfer",
        "transaction_reference": "TXN-123456",
        "invoice_number": "INV-2026-001",
        "invoice_date": "2025-12-25",
        "due_date": "2026-01-05",
        "paid_at": "2026-01-03T10:00:00Z",
        "notes": "",
        "recorded_by": "admin-uuid",
        "recorded_by_name": "Admin User"
    }
]
```

### Create Payment Record

#### `POST /api/admin/advertising/payments/`

**Request Body:**
```json
{
    "partner": "partner-uuid",
    "amount": "1500.00",
    "payment_type": "monthly_fee",
    "period_start": "2026-02-01",
    "period_end": "2026-02-28",
    "status": "pending",
    "payment_method": "bank_transfer",
    "invoice_number": "INV-2026-002",
    "invoice_date": "2026-01-25",
    "due_date": "2026-02-05"
}
```

### Mark Payment as Paid

#### `POST /api/admin/advertising/payments/{id}/mark-paid/`

**Request Body:**
```json
{
    "transaction_reference": "BANK-REF-789"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Payment marked as paid",
    "paid_at": "2026-01-04T12:30:00Z"
}
```

### Advertising Revenue Summary

#### `GET /api/admin/advertising/revenue/`

**Response:**
```json
{
    "total_revenue": "45000.00",
    "this_month": "5000.00",
    "last_month": "4200.00",
    "this_year": "45000.00",
    "growth_percentage": "19.0",
    "pending": {
        "amount": "3500.00",
        "count": 3
    },
    "overdue": {
        "amount": "1000.00",
        "count": 1
    },
    "monthly_breakdown": [
        {"month": "2025-10", "amount": "4000.00", "payments": 4},
        {"month": "2025-11", "amount": "4200.00", "payments": 4},
        {"month": "2025-12", "amount": "5000.00", "payments": 5}
    ],
    "top_partners": [
        {"partner_name": "Ecobank Ghana", "total_revenue": "24000.00", "payments": 12},
        {"partner_name": "Agricare Feeds", "total_revenue": "12000.00", "payments": 12}
    ]
}
```

---

# 📈 FINANCE DASHBOARD INTEGRATION

The finance dashboard now includes advertising revenue:

#### `GET /api/admin/finance/dashboard/`

**Response includes:**
```json
{
    "today": { ... },
    "this_week": { ... },
    "this_month": { ... },
    "pending_payments": { ... },
    "expiring_soon": { ... },
    "recent_payments": [ ... ],
    "adsense": {
        "connected": true,
        "today": "45.32",
        "this_week": "320.50",
        "this_month": "1200.00",
        "currency": "USD"
    },
    "advertising": {
        "this_month": "5000.00",
        "this_year": "45000.00",
        "total": "120000.00",
        "pending_amount": "3500.00",
        "pending_count": 3,
        "active_partners": 12,
        "currency": "GHS"
    }
}
```

**Frontend Integration:**
```tsx
function FinanceDashboard() {
    const { data } = useFinanceDashboard();
    
    return (
        <div className="finance-dashboard">
            {/* Marketplace Revenue */}
            <RevenueSection title="Marketplace Revenue">
                <StatCard title="Today" value={`GHS ${data.today.revenue}`} />
                <StatCard title="This Month" value={`GHS ${data.this_month.revenue}`} />
            </RevenueSection>
            
            {/* AdSense Revenue */}
            {data.adsense.connected && (
                <RevenueSection title="AdSense Revenue">
                    <StatCard title="Today" value={`$${data.adsense.today}`} />
                    <StatCard title="This Month" value={`$${data.adsense.this_month}`} />
                </RevenueSection>
            )}
            
            {/* Partner Advertising Revenue */}
            <RevenueSection title="Partner Advertising">
                <StatCard title="This Month" value={`GHS ${data.advertising.this_month}`} />
                <StatCard title="This Year" value={`GHS ${data.advertising.this_year}`} />
                <StatCard 
                    title="Pending" 
                    value={`GHS ${data.advertising.pending_amount}`}
                    subtitle={`${data.advertising.pending_count} invoices`}
                    alert={data.advertising.pending_count > 0}
                />
                <StatCard 
                    title="Active Partners" 
                    value={data.advertising.active_partners}
                />
            </RevenueSection>
            
            {/* Total Platform Revenue */}
            <TotalRevenueCard 
                marketplace={parseFloat(data.this_month.revenue)}
                adsense={parseFloat(data.adsense.this_month || 0)}
                advertising={parseFloat(data.advertising.this_month)}
            />
        </div>
    );
}
```

---

## 📊 New Endpoints Summary

| Endpoint | Method | Access | Description |
|----------|--------|--------|-------------|
| **A/B Testing** ||||
| `/api/admin/advertising/offers/{id}/variants/` | GET/POST | Admin | List/Create variants |
| `/api/admin/advertising/variants/{id}/` | GET/PUT/DELETE | Admin | Variant detail |
| `/api/admin/advertising/offers/{id}/ab-results/` | GET | Admin | A/B test results |
| **Conversions** ||||
| `/api/admin/advertising/conversions/` | GET/POST | Admin | List/Create conversions |
| `/api/admin/advertising/conversions/{id}/` | GET/PUT | Admin | Conversion detail |
| `/api/admin/advertising/conversions/{id}/verify/` | POST | Admin | Verify conversion |
| `/api/advertising/webhook/conversion/` | POST | API Key | Partner webhook |
| **Webhook Keys** ||||
| `/api/admin/advertising/webhook-keys/` | GET/POST | Admin | List/Create keys |
| `/api/admin/advertising/webhook-keys/{id}/` | GET/PUT/DELETE | Admin | Key detail |
| `/api/admin/advertising/webhook-keys/{id}/regenerate/` | POST | Admin | Regenerate key |
| **Payments (SUPER_ADMIN only)** ||||
| `/api/admin/advertising/payments/` | GET/POST | SUPER_ADMIN | List/Create payments |
| `/api/admin/advertising/payments/{id}/` | GET/PUT/DELETE | SUPER_ADMIN | Payment detail |
| `/api/admin/advertising/payments/{id}/mark-paid/` | POST | SUPER_ADMIN | Mark as paid |
| `/api/admin/advertising/revenue/` | GET | SUPER_ADMIN | Revenue summary |
