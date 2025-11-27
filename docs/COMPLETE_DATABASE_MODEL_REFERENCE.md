# Complete Database Model Reference
## YEA Poultry Management System

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Purpose:** Comprehensive reference for frontend developers to understand data structures

---

## Table of Contents

1. [Overview](#overview)
2. [Model Categories](#model-categories)
3. [Core Models](#core-models)
4. [Application & Onboarding Models](#application--onboarding-models)
5. [Production & Operations Models](#production--operations-models)
6. [Sales & Revenue Models](#sales--revenue-models)
7. [Inventory Models](#inventory-models)
8. [Health & Medication Models](#health--medication-models)
9. [Subscription & Payment Models](#subscription--payment-models)
10. [Security & Authentication Models](#security--authentication-models)
11. [Model Relationships](#model-relationships)
12. [Common Field Types](#common-field-types)

---

## Overview

### Database Statistics

- **Total Models:** 50+
- **Main Apps:** 11
- **Primary Relationships:** Farm-centric (most models link to Farm)
- **Access Patterns:** Role-based access control

### Database Engine
- **Production:** PostgreSQL 14+
- **Extensions:** PostGIS (for GPS coordinates)
- **Features:** JSON fields, Array fields, Full-text search

---

## Model Categories

### By Functionality

```
1. ACCOUNTS & ACCESS (6 models)
   └─ User management, roles, permissions, MFA

2. FARM REGISTRATION (12 models)
   └─ Farm profiles, locations, infrastructure

3. APPLICATIONS (8 models)
   └─ New farmer applications, program enrollment

4. PRODUCTION (5 models)
   └─ Flocks, daily production, mortality

5. INVENTORY (5 models)
   └─ Feed and medication inventory

6. SALES & MARKETPLACE (8 models)
   └─ Products, orders, payments, customers

7. SUBSCRIPTIONS (4 models)
   └─ Marketplace subscription management

8. HEALTH & MEDICATION (7 models)
   └─ Vaccinations, treatments, vet visits

9. NOTIFICATIONS (3 models)
   └─ Email, SMS, in-app notifications

10. AUDIT & SECURITY (4 models)
    └─ Logs, fraud detection, MFA
```

---

## Core Models

### 1. **User** (`accounts.User`)

**Purpose:** Central authentication and user management  
**Extends:** Django AbstractUser + RoleMixin

#### Fields

| Field | Type | Description | UI Display |
|-------|------|-------------|------------|
| `id` | UUID | Primary key | Hidden |
| `username` | string(150) | Unique username | Input field |
| `email` | string(254) | Email address | Input (verified) |
| `first_name` | string(150) | First name | Text input |
| `last_name` | string(150) | Last name | Text input |
| `phone` | PhoneNumber | Ghana format (+233) | Phone input |
| `phone_verified` | boolean | Phone verification status | Badge/Icon |
| `email_verified` | boolean | Email verification status | Badge/Icon |
| `role` | choice | FARMER/OFFICER/ADMIN | Role badge |
| `region` | string(100) | Assigned region (officers) | Dropdown |
| `constituency` | string(100) | Assigned constituency | Dropdown |
| `is_verified` | boolean | Account verified | Status badge |
| `is_active` | boolean | Account active | Toggle |
| `failed_login_attempts` | integer | Failed login count | Alert badge |
| `account_locked_until` | datetime | Lock expiry time | Countdown |
| `created_at` | datetime | Registration date | Date display |
| `last_login_at` | datetime | Last login time | Relative time |

#### Example JSON Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "kwame_farmer",
  "email": "kwame@example.com",
  "first_name": "Kwame",
  "last_name": "Asante",
  "phone": "+233244567890",
  "phone_verified": true,
  "email_verified": true,
  "role": "FARMER",
  "region": "Greater Accra",
  "constituency": "Tema East",
  "is_verified": true,
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z",
  "last_login_at": "2025-11-26T08:15:00Z"
}
```

#### UI Components Needed
- User profile form
- Role badge component
- Verification status indicators
- Phone/email verification modals

---

### 2. **Farm** (`farms.Farm`)

**Purpose:** Main farm registration and profile  
**Relationship:** OneToOne with User

#### Key Field Groups

**A. Identity & Status**
```
application_id: "APP-2025-00123" (unique)
farm_id: "YEA-REG-TE-0045" (assigned on approval)
farm_name: "Asante Poultry Farm"
application_status: "Approved" | "Submitted" | "Review" | etc.
farm_status: "Active" | "Inactive" | "Suspended"
```

**B. Personal Information**
```
first_name, middle_name, last_name
date_of_birth (18-65 years)
gender: "Male" | "Female" | "Other"
ghana_card_number: "GHA-XXXXXXXXX-X" (unique, validated)
marital_status
number_of_dependents
```

**C. Contact & Location**
```
primary_phone: "+233XXXXXXXXX" (Ghana format)
alternate_phone: "+233XXXXXXXXX"
email (optional)
preferred_contact_method: "Phone Call" | "SMS" | "WhatsApp" | "Email"
residential_address (text)
primary_constituency (REQUIRED for ALL farmers)
```

**D. Business Information**
```
ownership_type: "Sole Proprietorship" | "Partnership" | etc.
tin: Tax ID (MANDATORY, unique)
business_registration_number (encouraged)
bank_name, account_number, account_name
mobile_money_provider, mobile_money_number
```

**E. Production Information**
```
number_of_poultry_houses: integer >= 1
total_bird_capacity: integer >= 1
current_bird_count: integer
housing_type: "Deep Litter" | "Battery Cage" | etc.
primary_production_type: "Layers" | "Broilers" | "Both"
```

**F. Financial Tracking**
```
initial_investment_amount: decimal
monthly_operating_budget: decimal
expected_monthly_revenue: decimal
has_outstanding_debt: boolean
debt_amount, debt_purpose, monthly_debt_payment
```

**G. Farmer Type (IMPORTANT for UI)**
```
registration_source:
  - "government_initiative" (YEA farmer)
  - "self_registered" (Independent farmer)
  - "migrated"

approval_workflow:
  - "full_government" (3-tier review)
  - "auto_approve" (instant access)
  - "simplified"

subscription_type:
  - "none" (FREE core platform)
  - "government_subsidized" (Govt farmers with marketplace)
  - "standard" (GHS 100/month marketplace)
```

**H. Marketplace Subscription**
```
marketplace_enabled: boolean
subscription_type: choice
government_subsidy_active: boolean
government_subsidy_start_date, government_subsidy_end_date
product_images_count: integer (max 20 with subscription)
```

**I. Extension Officer Support**
```
extension_officer: FK to User (REQUIRED for govt farmers)
assigned_extension_officer: FK to User
```

#### Example JSON Response
```json
{
  "id": "farm-uuid",
  "application_id": "APP-2025-00123",
  "farm_id": "YEA-REG-TE-0045",
  "farm_name": "Asante Poultry Farm",
  "application_status": "Approved",
  "farm_status": "Active",
  
  "owner": {
    "name": "Kwame Mensah Asante",
    "phone": "+233244567890",
    "email": "kwame@example.com"
  },
  
  "location": {
    "constituency": "Tema East",
    "region": "Greater Accra",
    "district": "Tema Metropolitan"
  },
  
  "production": {
    "bird_capacity": 500,
    "current_count": 480,
    "production_type": "Layers",
    "housing_type": "Battery Cage"
  },
  
  "farmer_type": {
    "registration_source": "government_initiative",
    "is_government_farmer": true,
    "extension_officer": {
      "id": "officer-uuid",
      "name": "Dr. Adjei",
      "phone": "+233209876543"
    }
  },
  
  "marketplace": {
    "enabled": true,
    "subscription_type": "government_subsidized",
    "subsidy_active": true,
    "subsidy_expires": "2026-12-31"
  },
  
  "created_at": "2025-01-20T14:30:00Z"
}
```

#### UI Components Needed
- Farm profile display card
- Status badge component
- Farmer type indicator
- Subscription status widget
- Location map display
- Production capacity meters
- Financial health dashboard

---

### 3. **FarmLocation** (`farms.FarmLocation`)

**Purpose:** GPS coordinates and location details  
**Relationship:** Many locations per farm

#### Fields
```
farm: FK
gps_address_string: "AK-0123-4567" (Ghana GPS)
location: PointField (PostGIS)
latitude, longitude: decimal (auto-extracted)
region, district, constituency, community
land_size_acres: decimal
land_ownership_status: "Owned" | "Leased" | etc.
is_primary_location: boolean
gps_verified, constituency_match_verified: boolean
```

#### Example JSON
```json
{
  "id": "location-uuid",
  "gps_address": "AK-0123-4567",
  "coordinates": {
    "latitude": 5.6108,
    "longitude": -0.0993
  },
  "constituency": "Tema East",
  "community": "Community 8",
  "land_size_acres": "2.5",
  "ownership": "Leased",
  "is_primary": true,
  "verified": true
}
```

#### UI Components
- Map display (Google Maps / Mapbox)
- GPS coordinate input
- Location verification badge
- Land ownership indicator

---

## Application & Onboarding Models

### 4. **FarmApplication** (`farms.FarmApplication`)

**Purpose:** Anonymous applications (apply-first workflow)  
**Relationship:** Creates Farm after approval

#### Key Fields
```
application_number: "APP-2025-00123" (unique)
application_type: "government_program" | "independent"
status: "submitted" | "constituency_review" | "approved" | etc.
current_review_level: "constituency" | "regional" | "national"

# Applicant info (NO account yet)
first_name, last_name, date_of_birth, ghana_card_number
primary_phone, email
primary_constituency

# Farm plans
proposed_farm_name
farm_location_description
land_size_acres
primary_production_type
planned_bird_capacity
years_in_poultry
has_existing_farm

# Government program (if applicable)
yea_program_batch
referral_source

# Approval tracking
constituency_approved_at, constituency_approved_by
regional_approved_at, regional_approved_by
final_approved_at, final_approved_by

# Post-approval
invitation: OneToOne to FarmInvitation
user_account: OneToOne to User (created after approval)
farm_profile: OneToOne to Farm

# Spam prevention
spam_score: 0-100
spam_flags: array
priority_score: integer (queue priority)
```

#### Application Status Flow
```
submitted → constituency_review → regional_review → 
national_review → approved → account_created
```

#### Example JSON
```json
{
  "application_number": "APP-2025-00123",
  "application_type": "government_program",
  "status": "constituency_review",
  "current_review_level": "constituency",
  
  "applicant": {
    "name": "Kwame Mensah Asante",
    "ghana_card": "GHA-123456789-0",
    "phone": "+233244567890",
    "email": "kwame@example.com"
  },
  
  "farm_plans": {
    "name": "Asante Poultry Farm",
    "constituency": "Tema East",
    "production_type": "Layers",
    "planned_capacity": 500,
    "experience_years": "1.5"
  },
  
  "progress": {
    "percentage": 25,
    "current_stage": "Constituency Review",
    "days_since_submission": 6,
    "sla_deadline": "2025-11-27"
  },
  
  "submitted_at": "2025-11-20T10:30:00Z"
}
```

#### UI Components
- Multi-step application form (7 steps)
- Status tracker component
- Progress bar
- Timeline visualization
- Application summary card

---

### 5. **ApplicationQueue** (`farms.ApplicationQueue`)

**Purpose:** Queue management for officers  
**Relationship:** Links Application to Officer

#### Fields
```
application: FK
review_level: "constituency" | "regional" | "national"
status: "pending" | "claimed" | "in_progress" | "completed"
assigned_to: FK to User (officer)
priority: integer (higher = more urgent)
sla_due_date: datetime
is_overdue: boolean
entered_queue_at, claimed_at, completed_at
```

#### Example JSON
```json
{
  "id": "queue-uuid",
  "application": {
    "number": "APP-2025-00123",
    "farmer_name": "Kwame Asante",
    "constituency": "Tema East"
  },
  "review_level": "constituency",
  "status": "claimed",
  "assigned_to": {
    "id": "officer-uuid",
    "name": "Officer Adjei"
  },
  "priority": 65,
  "sla_due_date": "2025-11-27T10:30:00Z",
  "is_overdue": false,
  "days_in_queue": 6
}
```

#### UI Components
- Officer queue dashboard
- Claim button
- Priority sorting
- SLA countdown
- Overdue alerts

---

### 6. **GovernmentProgram** (`farms.GovernmentProgram`)

**Purpose:** Master list of government support programs  
**Used for:** Program enrollment by existing farmers

#### Fields
```
program_name: "YEA Poultry Support Program 2025"
program_code: "YEA-2025-Q1" (unique)
program_type: "training_support" | "input_subsidy" | etc.
description: text
start_date, end_date, application_deadline

# Eligibility criteria
min_farm_age_months, max_farm_age_years
min_bird_capacity, max_bird_capacity
eligible_farmer_age_min, eligible_farmer_age_max
eligible_constituencies: array
requires_extension_officer: boolean

# Capacity
total_slots, slots_filled, slots_available
status: "active" | "full" | "inactive"

# Support package
support_package_details: JSON
{
  "day_old_chicks": 500,
  "feed_bags_per_cycle": 100,
  "training_sessions": 12,
  "monetary_grant": 5000.00,
  "marketplace_subsidy_months": 12
}
```

#### Example JSON
```json
{
  "id": "program-uuid",
  "program_name": "YEA Poultry Support Program 2025",
  "program_code": "YEA-2025-Q1",
  "status": "active",
  "application_deadline": "2025-12-31",
  
  "eligibility": {
    "min_capacity": 100,
    "max_capacity": 1000,
    "age_range": "18-65",
    "constituencies": ["Tema East", "Tema West"]
  },
  
  "capacity": {
    "total_slots": 500,
    "filled": 345,
    "available": 155
  },
  
  "support_package": {
    "chicks": 500,
    "feed_bags": 100,
    "training_sessions": 12,
    "grant": 5000.00
  },
  
  "is_accepting_applications": true,
  "days_until_deadline": 35
}
```

#### UI Components
- Program card display
- Eligibility checker
- Capacity indicator
- Application button
- Support package breakdown

---

## Production & Operations Models

### 7. **Flock** (`flock_management.Flock`)

**Purpose:** Track bird batches/cohorts  
**Relationship:** Multiple flocks per farm

#### Fields
```
farm: FK
flock_number: "FLOCK-2025-001" (unique per farm)
flock_type: "Layers" | "Broilers" | "Breeders" | etc.
breed: "Isa Brown" | "Cobb 500" | etc.

# Acquisition
source: "YEA Program" | "Purchased" | etc.
arrival_date: date
initial_count: integer >= 1
age_at_arrival_weeks: decimal
purchase_price_per_bird: decimal

# Current status
current_count: integer
status: "Active" | "Sold" | "Culled" | "Depleted"
housed_in: FK to PoultryHouse

# Production tracking
production_start_date: date (for layers)
expected_production_end_date: date
is_currently_producing: boolean

# Accumulated metrics
total_feed_cost, total_medication_cost: decimal
total_mortality: integer
mortality_rate_percent: decimal
total_eggs_produced: integer (for layers)
feed_conversion_ratio: decimal
```

#### Calculated Properties
```python
current_age_weeks: auto-calculated from arrival_date
survival_rate_percent: (current_count / initial_count) × 100
capacity_utilization: if housed, occupancy percentage
```

#### Example JSON
```json
{
  "id": "flock-uuid",
  "flock_number": "LAYER-2025-001",
  "flock_type": "Layers",
  "breed": "Isa Brown",
  
  "acquisition": {
    "source": "YEA Program",
    "arrival_date": "2025-01-15",
    "initial_count": 500,
    "age_at_arrival_weeks": 18,
    "cost_per_bird": 15.00
  },
  
  "current_status": {
    "count": 480,
    "status": "Active",
    "age_weeks": 42.5,
    "housed_in": "House A"
  },
  
  "production": {
    "start_date": "2025-01-29",
    "is_producing": true,
    "days_in_production": 302,
    "total_eggs": 120450
  },
  
  "performance": {
    "mortality_rate": 4.0,
    "survival_rate": 96.0,
    "avg_eggs_per_bird": 240.9,
    "feed_conversion": 2.1
  },
  
  "costs": {
    "feed": 18500.00,
    "medication": 2400.00,
    "total_investment": 28400.00
  }
}
```

#### UI Components
- Flock card display
- Age calculator widget
- Performance metrics dashboard
- Mortality tracker
- Production graph (eggs over time)

---

### 8. **DailyProduction** (`flock_management.DailyProduction`)

**Purpose:** Daily production records  
**Relationship:** Many records per flock (one per day)

#### Fields
```
farm, flock: FK
production_date: date (unique per flock)

# Egg production (layers)
eggs_collected: integer
good_eggs, broken_eggs, dirty_eggs, small_eggs, soft_shell_eggs
production_rate_percent: auto-calculated

# Mortality
birds_died: integer
mortality_reason: "Disease" | "Predator" | etc.
mortality_notes: text

# Feed
feed_consumed_kg: decimal
feed_type: FK to FeedType
feed_cost_today: decimal

# Birds sold
birds_sold: integer
birds_sold_revenue: decimal

# Health observations
general_health: "Excellent" | "Good" | "Fair" | "Poor"
unusual_behavior: text
signs_of_disease: boolean
disease_symptoms: text

# Medication/vaccination
vaccination_given, medication_given: boolean
vaccination_type, medication_type: string
medication_cost_today: decimal

# Audit
recorded_by: FK to User
recorded_at, updated_at: datetime
```

#### Example JSON
```json
{
  "id": "production-uuid",
  "flock": "LAYER-2025-001",
  "production_date": "2025-11-26",
  
  "eggs": {
    "total_collected": 450,
    "good": 440,
    "broken": 5,
    "dirty": 3,
    "small": 2,
    "production_rate": 93.75
  },
  
  "mortality": {
    "count": 2,
    "reason": "Disease",
    "notes": "Suspected Newcastle disease"
  },
  
  "feed": {
    "consumed_kg": 25.5,
    "type": "Layer Mash 16%",
    "cost": 85.00
  },
  
  "health": {
    "general": "Good",
    "disease_signs": true,
    "symptoms": "Respiratory distress in 2 birds"
  },
  
  "recorded_by": "Kwame Asante",
  "recorded_at": "2025-11-26T18:30:00Z"
}
```

#### UI Components
- Daily entry form (mobile-optimized)
- Egg counter with breakdown
- Mortality recorder
- Feed consumption tracker
- Health assessment checklist
- Quick entry widgets

---

### 9. **MortalityRecord** (`flock_management.MortalityRecord`)

**Purpose:** Detailed death investigation & compensation  
**Relationship:** Links to DailyProduction

#### Fields
```
farm, flock, daily_production: FK
date_discovered: date
number_of_birds: integer

# Cause analysis
probable_cause: "Disease - Viral" | "Predator" | etc.
disease_suspected: "Newcastle Disease" | etc.
symptoms_observed: JSON array
symptoms_description: text

# Veterinary investigation
vet_inspection_required, vet_inspected: boolean
vet_inspection_date: date
vet_inspector: FK to User (vet officer)
vet_diagnosis, lab_test_results: text

# Disposal
disposal_method: "Burial" | "Incineration" | etc.
disposal_location, disposal_date

# Financial impact
estimated_value_per_bird: decimal
total_estimated_loss: decimal (auto-calculated)

# Compensation claim
compensation_claimed: boolean
compensation_amount: decimal
compensation_status: "Not Claimed" | "Pending" | "Paid"

# Evidence
photo_1, photo_2, photo_3: file upload
```

#### Example JSON
```json
{
  "id": "mortality-uuid",
  "flock": "LAYER-2025-001",
  "date_discovered": "2025-11-26",
  "number_of_birds": 10,
  
  "cause": {
    "probable": "Disease - Viral",
    "suspected_disease": "Newcastle Disease",
    "symptoms": [
      "Respiratory distress",
      "Greenish diarrhea",
      "Twisted neck"
    ]
  },
  
  "vet_investigation": {
    "required": true,
    "inspected": true,
    "inspector": "Dr. Adjei",
    "diagnosis": "Confirmed Newcastle Disease",
    "lab_results": "Virus isolated and confirmed"
  },
  
  "financial": {
    "value_per_bird": 45.00,
    "total_loss": 450.00
  },
  
  "compensation": {
    "claimed": true,
    "amount": 450.00,
    "status": "Pending"
  },
  
  "photos": [
    "/media/mortality/photo1.jpg",
    "/media/mortality/photo2.jpg"
  ]
}
```

#### UI Components
- Mortality form with photo upload
- Symptom checklist
- Vet inspection request button
- Compensation claim form
- Evidence gallery

---

## Sales & Revenue Models

### 10. **Customer** (`sales_revenue.Customer`)

**Purpose:** Buyer information for farmers  
**Relationship:** Multiple customers per farm

#### Fields
```
farm: FK
customer_type: "individual" | "business" | "retailer" | "wholesaler"
first_name, last_name, business_name
phone_number: Ghana format
email: optional

# Payment (Mobile Money)
mobile_money_number: Ghana format
mobile_money_provider: "MTN" | "Vodafone" | "AirtelTigo"
mobile_money_account_name

# Location & delivery
location, delivery_address: text

# Metrics (auto-calculated)
total_purchases: decimal
total_orders: integer
is_active: boolean
notes: text
```

#### Example JSON
```json
{
  "id": "customer-uuid",
  "customer_type": "retailer",
  "name": "Akosua Traders",
  "contact": {
    "phone": "+233244111222",
    "email": "akosua@example.com"
  },
  "mobile_money": {
    "number": "+233244111222",
    "provider": "MTN",
    "account_name": "Akosua Mensah"
  },
  "location": "Tema Market",
  "metrics": {
    "total_purchases": 12450.00,
    "total_orders": 24,
    "average_order": 518.75
  },
  "is_active": true
}
```

#### UI Components
- Customer directory
- Customer profile card
- Add customer form
- Purchase history
- Communication buttons (Call, Message)

---

### 11. **EggSale** (`sales_revenue.EggSale`)

**Purpose:** Egg sales with payment tracking  
**Relationship:** Links Farm, Customer, DailyProduction

#### Fields
```
farm, customer, daily_production: FK
sale_date: date
quantity: decimal
unit: "crate" | "piece"
price_per_unit: decimal

# Auto-calculated amounts
subtotal: quantity × price_per_unit
platform_commission: based on PlatformSettings
paystack_fee: 1.5% + GHS 0.10
farmer_payout: subtotal - commission
total_amount: same as subtotal (customer pays)

# Status & payment
status: "pending" | "paid" | "completed" | "refunded"
payment: OneToOne to Payment model

notes: text
```

#### Example JSON
```json
{
  "id": "sale-uuid",
  "sale_date": "2025-11-26",
  "customer": {
    "name": "Akosua Traders",
    "phone": "+233244111222"
  },
  
  "items": {
    "product": "Layer Eggs (Brown)",
    "quantity": 10,
    "unit": "crate",
    "price_per_unit": 25.00
  },
  
  "amounts": {
    "subtotal": 250.00,
    "commission": 5.00,
    "paystack_fee": 3.85,
    "farmer_receives": 245.00,
    "customer_pays": 250.00
  },
  
  "status": "paid",
  "payment": {
    "reference": "PAY-2025-12345",
    "method": "mobile_money",
    "status": "success"
  }
}
```

#### UI Components
- Sale entry form
- Product selection
- Price calculator
- Commission breakdown display
- Payment status badge
- Receipt generator

---

### 12. **BirdSale** (`sales_revenue.BirdSale`)

**Purpose:** Live bird sales  
**Similar to EggSale but for birds**

#### Fields
```
farm, customer, flock: FK
sale_date: date
bird_type: "layer" | "broiler" | "cockerel" | "spent_hen"
quantity: integer
price_per_bird: decimal

# Auto-calculated amounts (same as EggSale)
subtotal, platform_commission, paystack_fee
farmer_payout, total_amount

status: "pending" | "paid" | "completed"
payment: OneToOne to Payment
```

---

### 13. **Payment** (`sales_revenue.Payment`)

**Purpose:** Payment processing with Paystack  
**Relationship:** OneToOne with EggSale or BirdSale

#### Fields
```
farm, customer: FK
amount: decimal
payment_method: "mobile_money" | "bank_transfer" | "card"
status: "pending" | "success" | "failed" | "refunded"

# Paystack integration
paystack_reference: unique string
paystack_access_code, paystack_transaction_id
payment_response: JSON (raw Paystack data)

# Retry mechanism
retry_count: integer
last_retry_at, next_retry_at: datetime

# Refund
refund_requested, refund_requested_at
refund_reason, refunded_amount, refunded_at
```

#### Example JSON
```json
{
  "id": "payment-uuid",
  "reference": "PAY-2025-12345",
  "amount": 250.00,
  "method": "mobile_money",
  "status": "success",
  
  "paystack": {
    "transaction_id": "1234567890",
    "reference": "PAY-2025-12345",
    "authorization_code": "AUTH_xyz123"
  },
  
  "customer": {
    "name": "Akosua Traders",
    "phone": "+233244111222"
  },
  
  "created_at": "2025-11-26T10:30:00Z",
  "paid_at": "2025-11-26T10:32:00Z"
}
```

---

### 14. **FarmerPayout** (`sales_revenue.FarmerPayout`)

**Purpose:** Track money sent to farmer  
**Relationship:** Links to EggSale or BirdSale

#### Fields
```
farm: FK
egg_sale, bird_sale: FK (one of these)
amount: decimal
status: "pending" | "processing" | "success" | "failed"

# Paystack transfer
paystack_transfer_code, paystack_transfer_id
settlement_date: datetime

# Mobile money recipient
recipient_mobile_number
recipient_name
mobile_money_provider

# Audit trail (blockchain-like)
previous_hash, current_hash: SHA256 hashes

# Metadata
payout_response: JSON
retry_count: integer
```

#### Example JSON
```json
{
  "id": "payout-uuid",
  "amount": 245.00,
  "status": "success",
  
  "recipient": {
    "name": "Kwame Asante",
    "mobile_number": "+233244567890",
    "provider": "MTN"
  },
  
  "transfer": {
    "code": "TRF_xyz789",
    "settled_at": "2025-11-26T10:35:00Z"
  },
  
  "audit": {
    "current_hash": "abc123...",
    "previous_hash": "def456..."
  }
}
```

---

### 15. **FraudAlert** (`sales_revenue.FraudAlert`)

**Purpose:** Off-platform sales detection  
**Relationship:** Per farm analysis

#### Fields
```
farm: FK
risk_score: 0-100
risk_level: "CLEAN" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

# Alert details
alerts: JSON array of specific issues
analysis_period_days: 30

# Review
status: "new" | "under_review" | "false_positive" | "confirmed"
reviewed_by: FK to User
reviewed_at, review_notes

# Actions
action_taken: text
audit_scheduled, audit_date
```

#### Example JSON
```json
{
  "id": "alert-uuid",
  "farm": "Asante Poultry Farm",
  "risk_score": 75,
  "risk_level": "HIGH",
  
  "alerts": [
    {
      "severity": "HIGH",
      "code": "production_sales_mismatch",
      "message": "Eggs produced: 13,500 but only 3,200 sold on platform (76% off-platform)"
    },
    {
      "severity": "MEDIUM",
      "code": "sudden_production_drop",
      "message": "Production dropped 40% without explanation"
    }
  ],
  
  "status": "under_review",
  "reviewed_by": "Admin Officer",
  "detected_at": "2025-11-26T12:00:00Z"
}
```

---

## Inventory Models

### 16. **FeedType** (`feed_inventory.FeedType`)

**Purpose:** Master feed catalog  
**Used by:** All farmers

#### Fields
```
name: "Layer Mash 16%" (unique)
category: "STARTER" | "GROWER" | "LAYER" | etc.
form: "MASH" | "PELLET" | "CRUMBLE"
manufacturer: "Agricare" | etc.

# Nutritional info
protein_content: decimal (%)
energy_content: decimal (kcal/kg)
calcium_content, phosphorus_content: decimal (%)

# Usage
recommended_age_weeks_min, recommended_age_weeks_max
daily_consumption_per_bird_grams
standard_price_per_kg: decimal (reference)

is_active: boolean
```

#### Example JSON
```json
{
  "id": "feed-uuid",
  "name": "Layer Mash 16%",
  "category": "LAYER",
  "form": "MASH",
  "manufacturer": "Agricare",
  
  "nutrition": {
    "protein": 16.0,
    "energy": 2750,
    "calcium": 3.5,
    "phosphorus": 0.45
  },
  
  "usage": {
    "age_range": "19-80 weeks",
    "daily_per_bird": 120
  },
  
  "price": 3.50
}
```

---

### 17. **FeedInventory** (`feed_inventory.FeedInventory`)

**Purpose:** Current stock per farm per feed type  
**Relationship:** Unique per (farm, feed_type)

#### Fields
```
farm, feed_type: FK
current_stock_kg: decimal
min_stock_level, max_stock_level: decimal

# Value tracking
average_cost_per_kg: weighted average
total_value: stock × cost

# Alerts
low_stock_alert: auto-set when < min_stock_level

# Tracking
last_purchase_date, last_consumption_date
storage_location: text
```

#### Example JSON
```json
{
  "id": "inventory-uuid",
  "feed_type": "Layer Mash 16%",
  "current_stock": 350.0,
  "min_stock": 100.0,
  "max_stock": 1000.0,
  
  "value": {
    "avg_cost_per_kg": 3.50,
    "total_value": 1225.00
  },
  
  "alerts": {
    "low_stock": false
  },
  
  "last_purchase": "2025-11-20",
  "last_consumption": "2025-11-26"
}
```

---

## Subscription & Payment Models

### 18. **SubscriptionPlan** (`subscriptions.SubscriptionPlan`)

**Purpose:** Marketplace subscription tiers  
**Current:** Single plan - GHS 100/month

#### Fields
```
name: "Standard Marketplace"
description: text
price_monthly: 100.00

# Features
max_product_images: 20
max_image_size_mb: 5
marketplace_listing: true
sales_tracking: true
analytics_dashboard: true

# Trial
trial_period_days: 14

is_active: boolean
```

---

### 19. **Subscription** (`subscriptions.Subscription`)

**Purpose:** Farmer's marketplace subscription  
**Relationship:** OneToOne with Farm

#### Fields
```
farm, plan: FK
status: "trial" | "active" | "past_due" | "suspended" | "cancelled"

# Billing cycle
start_date, current_period_start, current_period_end
next_billing_date

# Trial
trial_start, trial_end

# Payment
last_payment_date, last_payment_amount

# Grace period
grace_period_days: 5 (default)
suspension_date

# Cancellation
cancelled_at, cancellation_reason, cancelled_by

# Reminders
reminder_sent_at, reminder_count

auto_renew: boolean
```

#### Example JSON
```json
{
  "id": "subscription-uuid",
  "farm": "Asante Poultry Farm",
  "plan": "Standard Marketplace",
  "status": "active",
  
  "billing": {
    "current_period": "2025-11-01 to 2025-11-30",
    "next_billing_date": "2025-12-01",
    "price": 100.00
  },
  
  "trial": {
    "active": false,
    "ended": "2025-10-15"
  },
  
  "last_payment": {
    "date": "2025-11-01",
    "amount": 100.00
  },
  
  "auto_renew": true
}
```

---

## Security & Authentication Models

### 20. **MFAMethod** (`accounts.MFAMethod`)

**Purpose:** Multi-factor authentication  
**Types:** TOTP, SMS, Email

#### Fields
```
user: FK
method_type: "totp" | "sms" | "email"
is_primary, is_enabled: boolean

# TOTP specific
totp_secret: base32 encoded

# SMS/Email specific
phone_number, email_address

# Verification
is_verified, verified_at
last_used_at, use_count
```

---

## Model Relationships

### Entity Relationship Overview

```
User (1) ─────────── (1) Farm
  │                       │
  │                       ├── (M) FarmLocation
  │                       ├── (M) Flock
  │                       │     └── (M) DailyProduction
  │                       ├── (M) Customer
  │                       ├── (M) EggSale
  │                       ├── (M) BirdSale
  │                       ├── (1) Subscription
  │                       └── (M) FeedInventory
  │
  └── (M) MFAMethod

FarmApplication (1) ───→ (1) Farm (after approval)
GovernmentProgram (1) ─→ (M) ProgramEnrollmentApplication
```

---

## Common Field Types

### Standard Types Used Across Models

```python
# IDs
id: UUID (primary key for all models)

# Text
CharField(max_length=N): Short text
TextField(): Long text
EmailField(): Email with validation
URLField(): URL with validation

# Numbers
IntegerField(): Whole numbers
PositiveIntegerField(): >= 0
DecimalField(max_digits=M, decimal_places=N): Money, percentages
FloatField(): Rarely used (prefer Decimal)

# Dates & Times
DateField(): YYYY-MM-DD
DateTimeField(): ISO 8601 timestamp
TimeField(): HH:MM:SS

# Booleans
BooleanField(): true/false

# Choices
CharField with choices: Dropdown/select

# Relations
ForeignKey: Many-to-One
OneToOneField: One-to-One
ManyToManyField: Many-to-Many

# Files
FileField(): File upload
ImageField(): Image upload (extends FileField)

# JSON & Arrays (PostgreSQL)
JSONField(): JSON data
ArrayField(): Array of items

# GIS (PostGIS)
PointField(): GPS coordinates
```

---

## Data Format Examples

### Date/Time Formats

```json
{
  "date": "2025-11-26",
  "datetime": "2025-11-26T10:30:00Z",
  "datetime_with_tz": "2025-11-26T10:30:00+00:00"
}
```

### Money Formats

```json
{
  "amount": "1234.50",
  "currency": "GHS"
}
```

### Phone Numbers

```json
{
  "phone": "+233244567890",
  "display": "0244 567 890"
}
```

### Ghana Card Format

```
Pattern: GHA-XXXXXXXXX-X
Example: GHA-123456789-0
Validation: /^GHA-\d{9}-\d$/
```

---

**End of Database Reference**

**For More Details:**
- Model Source Code: `/path/to/models.py` files
- API Documentation: `http://localhost:8000/api/docs/`
- Backend Team: backend@pms.gov.gh
