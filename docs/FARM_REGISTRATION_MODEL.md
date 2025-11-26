# Farm Registration Model Specification

## Document Information
- **Version**: 1.0
- **Date**: October 26, 2025
- **Project**: YEA Poultry Management System
- **Purpose**: Define complete data structure for farm registration

---

## 1. FARM OWNER/OPERATOR INFORMATION

### 1.1 Personal Identity
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `first_name` | String(100) | Yes | Alpha characters, spaces allowed | Legal first name |
| `middle_name` | String(100) | No | Alpha characters, spaces allowed | |
| `last_name` | String(100) | Yes | Alpha characters, spaces allowed | Legal surname |
| `date_of_birth` | Date | Yes | Must be 18-65 years old | For age verification |
| `gender` | Choice | Yes | Male, Female, Other | Demographics tracking |
| `ghana_card_number` | String(20) | Yes | Format: GHA-XXXXXXXXX-X | National ID |
| `profile_photo` | ImageField | No | Max 2MB, JPG/PNG | Optional profile picture |

### 1.2 Contact Information
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `primary_phone` | String(15) | Yes | Ghana phone format (10 digits) | Main contact number |
| `secondary_phone` | String(15) | No | Ghana phone format | Alternative contact |
| `email` | Email | No | Valid email format | Many farmers may not have |
| `residential_address` | Text | Yes | Min 10 characters | Current home address |
| `preferred_contact_method` | Choice | Yes | Phone Call, SMS, WhatsApp, Email | Communication preference |

### 1.3 Next of Kin (Emergency Contact)
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `kin_full_name` | String(200) | Yes | Alpha characters | Emergency contact person |
| `kin_relationship` | Choice | Yes | Spouse, Parent, Sibling, Child, Other | Relationship to farmer |
| `kin_phone` | String(15) | Yes | Ghana phone format | Emergency contact number |
| `kin_address` | Text | No | | Where kin can be reached |

### 1.4 Education & Experience
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `education_level` | Choice | Yes | None, Primary, JHS, SHS, Tertiary, Vocational | For training customization |
| `can_read_write` | Boolean | Yes | True/False | Literacy assessment |
| `has_farming_experience` | Boolean | Yes | True/False | Any prior farming |
| `years_in_poultry` | Integer | No | 0-50 years | Poultry farming experience |
| `previous_training` | Text | No | | List any agricultural training received |
| `other_farming_activities` | Text | No | | E.g., crops, livestock, fish farming |

**Why Education & Experience?**
- **Education Level**: Tailor training materials (video vs. text, simple vs. technical language)
- **Literacy**: Determine if farmer needs extra support with reporting
- **Experience**: Experienced farmers may need less hand-holding, can mentor others
- **Previous Training**: Avoid redundant training, build on existing knowledge

---

## 2. FARM BUSINESS INFORMATION

### 2.1 Business Identity
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `farm_name` | String(200) | Yes | Unique within constituency | Business/trading name |
| `farm_establishment_date` | Date | No | Not in future | When farm started operations |
| `ownership_type` | Choice | Yes | Individual, Cooperative, Partnership, Company | Legal structure |
| `business_registration_number` | String(50) | No | | **Strongly encouraged - eligible for incentives** |
| `is_business_registered` | Boolean | Yes | True/False | Track registration status |
| `tax_identification_number` | String(20) | **Yes** | Ghana TIN format | **Required for govt procurement compliance** |

**Business Registration Incentives**:
- Priority consideration for government procurement orders
- Access to bulk purchase discounts on supplies
- Eligibility for business development grants
- Featured listing in public marketplace
- Training on business formalization benefits

**Note**: System flags unregistered businesses and sends periodic reminders about registration benefits

### 2.2 Employment
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `number_of_employees` | Integer | Yes | 0-100 | Full-time workers |
| `number_of_part_time_workers` | Integer | No | 0-50 | Casual/seasonal workers |
| `family_members_involved` | Integer | No | 0-20 | Unpaid family labor |

**Why?**
- Track **youth employment impact** (program goal)
- Assess **farm management capacity**
- Identify **potential for job creation**

### 2.3 Financial Information
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `bank_name` | String(100) | Yes | | For payments |
| `account_number` | String(20) | Yes | Numeric | Government procurement payments |
| `account_name` | String(200) | Yes | | Must match farmer name |
| `bank_branch` | String(100) | No | | |
| `mobile_money_number` | String(15) | No | Ghana phone format | Alternative payment method |
| `mobile_money_network` | Choice | No | MTN, Vodafone, AirtelTigo | |

---

## 3. FARM LOCATION(S)

**Structure**: One farm can have multiple locations (e.g., separate sites for layers and broilers)

### 3.1 Location Model (Can have multiple per farm)
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `location_name` | String(100) | Yes | E.g., "Main Site", "Layer House" | Location identifier |
| `gps_address_string` | String(50) | Yes | Ghana GPS app format | From GPS app |
| `latitude` | Decimal | Auto | -90 to 90 | Extracted from GPS string |
| `longitude` | Decimal | Auto | -180 to 180 | Extracted from GPS string |
| `region` | Choice | Yes | 16 Ghana regions | Auto-filled from GPS |
| `district` | String(100) | Yes | | Auto-filled from GPS |
| `constituency` | Choice | Yes | Ghana constituencies | For jurisdiction |
| `nearest_landmark` | String(200) | No | | E.g., "Near Amakom Roundabout" |
| `descriptive_address` | Text | No | | Traditional address |
| `land_ownership_status` | Choice | Yes | Owned, Leased, Family Land, Govt Allocated | Land tenure |
| `land_size_acres` | Decimal | Yes | 0.1-1000 | Farm land area |
| `accessible_by_vehicle` | Boolean | Yes | True/False | For logistics planning |
| `distance_to_nearest_town_km` | Decimal | No | 0-500 | Market access |
| `is_primary_location` | Boolean | Yes | True/False | Main farm site flag |

**Why Multiple Locations?**
- Farmers may have **separate sites** for different production types
- **Biosecurity**: Separate broilers from layers
- **Land availability**: Expand to new locations over time

---

## 4. FARM INFRASTRUCTURE & CAPACITY

### 4.1 Overall Farm Infrastructure
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `number_of_poultry_houses` | Integer | Yes | 1-50 | Total structures |
| `total_bird_capacity` | Integer | Yes | 100-100,000 | Maximum birds farm can hold |
| `current_bird_count` | Integer | Yes | 0 to total_capacity | Birds at registration |
| `primary_housing_type` | Choice | Yes | See options below | Dominant housing system |
| `total_infrastructure_value_ghs` | Decimal | Yes | 0-10,000,000 | **Total estimated value for investment analysis** |

**Housing Type Options**:
- Deep Litter System
- Battery Cage
- Free Range
- Semi-Intensive
- Intensive (Closed House)
- Open-Sided House

**Note**: Infrastructure details are **assessment criteria**, not mandatory requirements for approval. Used for:
- Farm readiness scoring
- Appropriate support package design
- Investment tracking and ROI analysis
- Infrastructure development monitoring over time

### 4.2 Individual Poultry House Details
**Structure**: Multiple houses per farm

| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `house_name` | String(50) | Yes | E.g., "House A", "Layer House 1" | Identifier |
| `house_type` | Choice | Yes | Same as primary_housing_type | Housing system |
| `bird_capacity` | Integer | Yes | 50-10,000 | Max birds per house |
| `current_occupancy` | Integer | Yes | 0 to capacity | Current birds in house |
| `length_meters` | Decimal | No | | House dimensions |
| `width_meters` | Decimal | No | | House dimensions |
| `year_built` | Integer | No | 1950-2025 | Construction year |
| `last_renovated` | Date | No | | Last upgrade |
| `house_condition` | Choice | No | Excellent, Good, Fair, Poor | Current state |
| `estimated_house_value_ghs` | Decimal | No | 0-1,000,000 | **House construction/renovation value** |

### 4.3 Equipment Inventory
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `feeders_count` | Integer | Yes | 0-1000 | Number of feeding troughs |
| `feeders_type` | Choice | No | Manual, Automatic, Hanging, Trough | |
| `feeders_value_ghs` | Decimal | No | 0-100,000 | **Investment in feeders** |
| `drinkers_count` | Integer | Yes | 0-1000 | Water dispensers |
| `drinkers_type` | Choice | No | Manual, Nipple, Bell, Automatic | |
| `drinkers_value_ghs` | Decimal | No | 0-100,000 | **Investment in drinkers** |
| `has_incubators` | Boolean | Yes | True/False | For hatching |
| `incubator_capacity` | Integer | No | 0-10,000 | Egg capacity if yes |
| `incubator_value_ghs` | Decimal | No | 0-500,000 | **Incubator investment** |
| `has_backup_generator` | Boolean | Yes | True/False | Power backup |
| `generator_capacity_kva` | Decimal | No | | If yes |
| `generator_value_ghs` | Decimal | No | 0-100,000 | **Generator investment** |
| `has_weighing_scale` | Boolean | Yes | True/False | For weight monitoring |
| `weighing_scale_value_ghs` | Decimal | No | 0-10,000 | **Scale investment** |
| `storage_capacity_tonnes` | Decimal | No | 0-100 | Feed storage |
| `storage_facility_value_ghs` | Decimal | No | 0-200,000 | **Storage infrastructure value** |
| `other_equipment_description` | Text | No | Max 500 chars | Additional equipment |
| `other_equipment_value_ghs` | Decimal | No | 0-500,000 | **Other equipment value** |

**Total Equipment Value** = Sum of all equipment values (auto-calculated)

### 4.4 Utilities & Services
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `water_source` | Choice | Yes | Borehole, Pipe-borne, Well, River, Tanker | Primary water |
| `water_source_reliability` | Choice | Yes | Very Reliable, Reliable, Unreliable | Consistency |
| `power_source` | Choice | Yes | National Grid, Generator, Solar, None | Electricity |
| `power_availability` | Choice | Yes | 24/7, Intermittent, Rare, None | Reliability |
| `internet_available` | Boolean | Yes | True/False | For digital reporting |
| `internet_type` | Choice | No | Mobile Data, Broadband, None | If available |
| `mobile_network_coverage` | Choice | Yes | Excellent, Good, Fair, Poor, None | SMS/calls |

**Why Utilities?**
- **Water**: Critical for production, affects support planning
- **Power**: Determines if automated systems viable
- **Internet**: Affects digital reporting capability
- **Mobile**: For SMS notifications and communication

### 4.5 Biosecurity Measures
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `has_perimeter_fence` | Boolean | Yes | True/False | Security & biosecurity |
| `fence_condition` | Choice | No | Good, Fair, Poor | If yes |
| `has_footbath` | Boolean | Yes | True/False | Disease prevention |
| `has_changing_room` | Boolean | No | True/False | Visitor biosecurity |
| `has_quarantine_area` | Boolean | No | True/False | Sick bird isolation |
| `rodent_control_system` | Boolean | Yes | True/False | Pest management |
| `has_bird_netting` | Boolean | No | True/False | Wild bird prevention |
| `waste_disposal_method` | Choice | Yes | Pit, Compost, Biogas, Sold, Burning, Other | Manure management |

**Biosecurity Risk Score**: System calculates based on measures (0-100%)

---

## 5. PRODUCTION INFORMATION

### 5.1 Production Type & Focus
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `primary_production_type` | Choice | Yes | Layers, Broilers, Both, Parent Stock | Main focus |
| `layer_breed` | Choice | No | Isa Brown, Lohmann, Black, Other | If layers |
| `broiler_breed` | Choice | No | Cobb, Ross, Arbor Acres, Other | If broilers |
| `production_system` | Choice | Yes | Intensive, Semi-Intensive, Free Range | Management system |

### 5.2 Production Planning
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `planned_annual_egg_production` | Integer | No | 0-10,000,000 | For layers |
| `planned_annual_bird_sales` | Integer | No | 0-100,000 | For broilers |
| `production_cycles_per_year` | Integer | Yes | 1-6 | Batching frequency |
| `planned_production_start_date` | Date | **Yes** | Future or current date | **Next/first production cycle start** |
| `planned_monthly_egg_production` | Integer | **Conditional** | 0-1,000,000 | **Required if primary_production_type = Layers** |
| `planned_monthly_bird_sales` | Integer | **Conditional** | 0-10,000 | **Required if primary_production_type = Broilers** |
| `target_eggs_per_bird_per_month` | Integer | No | 0-30 | Expected productivity |
| `target_bird_weight_kg` | Decimal | No | 0-5 | Target market weight for broilers |

**Why Monthly Targets?**
- More granular procurement planning
- Early identification of underperformance
- Quarterly performance reviews
- Better inventory forecasting

**Validation Rules**:
- If `primary_production_type` = "Layers" → `planned_monthly_egg_production` is **required**
- If `primary_production_type` = "Broilers" → `planned_monthly_bird_sales` is **required**
- If `primary_production_type` = "Both" → **both** monthly targets are **required**

### 5.3 Market Focus
**Multi-select**: Farmer can target multiple markets

| Market Channel | Priority |
|---------------|----------|
| Government Procurement | High/Medium/Low |
| Public Market/Individual Buyers | High/Medium/Low |
| Hotels & Restaurants | High/Medium/Low |
| Retail Shops | High/Medium/Low |
| Schools & Institutions | High/Medium/Low |
| Export | High/Medium/Low |

**Why?**
- Match farmers to **appropriate procurement opportunities**
- Identify **niche markets** (hotels prefer certain sizes)
- **Market linkage** support

---

## 6. SUPPORT NEEDS ASSESSMENT

### 6.1 Support Required from YEA
**Multi-select checkboxes**:

| Support Type | Selected | Priority |
|-------------|----------|----------|
| Day-old Chicks | ☐ | High/Medium/Low |
| Feed | ☐ | High/Medium/Low |
| Medication & Vaccines | ☐ | High/Medium/Low |
| Equipment | ☐ | High/Medium/Low |
| Technical Training | ☐ | High/Medium/Low |
| Veterinary Services | ☐ | High/Medium/Low |
| Market Linkage | ☐ | High/Medium/Low |
| Financial Management Training | ☐ | High/Medium/Low |
| Record Keeping Tools | ☐ | High/Medium/Low |

**Assessment Update Schedule**:
- **Initial**: At registration
- **Quarterly**: Every 3 months during first year
- **Bi-annually**: After first year
- **Ad-hoc**: Farmer can request reassessment anytime

**System tracks**:
- Support needs changes over time
- Support provided vs. requested
- Effectiveness of interventions
- Emerging common needs across farms

### 6.2 Current Challenges
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `major_challenges` | Text | No | Max 1000 chars | Open-ended challenges |
| `specific_equipment_needs` | Text | No | Max 500 chars | What equipment lacking |

### 6.3 Training Interests
**Multi-select**:
- ☐ Disease Management & Prevention
- ☐ Feed Formulation & Nutrition
- ☐ Record Keeping & Data Management
- ☐ Biosecurity Best Practices
- ☐ Marketing & Sales
- ☐ Financial Management
- ☐ Breeding & Hatchery Management
- ☐ Processing & Value Addition

**Why Training Needs?**
- **Customize training programs** based on demand
- **Identify knowledge gaps** across farmer base
- **Plan extension officer activities**

---

## 7. FINANCIAL INFORMATION (**Mandatory Section**)

### 7.1 Investment & Funding
| Field | Type | Required | Validation | Notes |
|-------|------|----------|------------|-------|
| `initial_investment_amount` | Decimal | **Yes** | 0-10,000,000 GHS | **Farmer's capital invested** |
| `funding_source` | Multi-select | **Yes** | Personal Savings, Family, Loan, Grant, Other | **How farm was funded** |
| `monthly_operating_budget` | Decimal | **Yes** | 0-1,000,000 GHS | **Estimated monthly expenses** |
| `expected_monthly_revenue` | Decimal | **Yes** | 0-1,000,000 GHS | **Revenue projection** |
| `has_outstanding_debt` | Boolean | **Yes** | True/False | **Current loans/debts** |
| `debt_amount` | Decimal | Conditional | 0-10,000,000 GHS | **Required if has_outstanding_debt = True** |
| `debt_purpose` | Text | No | Max 200 chars | What loan was for |
| `monthly_debt_payment` | Decimal | No | 0-100,000 GHS | Monthly repayment amount |

**Why Financial Data is Mandatory:**
- **Program Sustainability**: Assess if farmers can maintain operations beyond initial support
- **ROI Tracking**: Calculate government investment return over time
- **Risk Assessment**: Identify farmers at financial risk early
- **Impact Measurement**: Track wealth creation and poverty reduction
- **Support Targeting**: Prioritize financially vulnerable but viable farms
- **Budget Planning**: Aggregate data for national program budgeting
- **Success Stories**: Document transformation from investment to profitability

**Financial Health Score**: System calculates based on:
- Revenue vs. Expenses ratio
- Debt-to-Asset ratio
- Expected profitability timeline
- Cash flow sustainability

**Privacy Protection**:
- Financial data encrypted at rest
- Access restricted to national officials and auditors
- Not displayed in public marketplace
- Aggregated only for program-level reports

---

## 8. APPLICATION DOCUMENTS

### 8.1 Required Documents
| Document | Type | Required | Max Size | Notes |
|----------|------|----------|----------|-------|
| `ghana_card_photo` | Image/PDF | Yes | 2MB | National ID |
| `passport_photo` | Image | No | 2MB | For profile |

### 8.2 Farm Photos (**Mandatory - Minimum 3 Required**)
| Photo Type | Required | Max Size | Notes |
|-----------|----------|----------|-------|
| Poultry House - Exterior | **Yes** | 5MB | **Mandatory - At least 1 house** |
| Poultry House - Interior | **Yes** | 5MB | **Mandatory - Show housing system** |
| Overall Farm Layout | **Yes** | 5MB | **Mandatory - Bird's eye view if possible** |
| Feeding System | Recommended | 5MB | Feeders/drinkers |
| Water System | Recommended | 5MB | Water source |
| Equipment | Recommended | 5MB | Any significant equipment |
| Storage Facilities | Recommended | 5MB | Feed storage |
| Biosecurity Measures | Recommended | 5MB | Fencing, footbaths, etc. |

**Photo Requirements**:
- **Minimum 3 farm photos MANDATORY** for application approval
- Must include at least 1 exterior and 1 interior poultry house shot
- Photos must be clear and show infrastructure details
- EXIF GPS data checked to verify location match (if available)
- Recent photos (within last 30 days recommended)

**Why Photos are Mandatory:**
- Visual verification without site visit (saves time and cost)
- Fraud prevention (ensure farm exists)
- Infrastructure assessment accuracy
- Benchmark for monitoring improvements over time
- Documentation for approval justification
- Training material (showcase good practices)

### 8.3 Land Documentation (**Recommended but Not Required**)
| Document | Required | Format | Notes |
|----------|----------|--------|-------|
| Title Deed | **Recommended** | PDF/Image | **Strongly encouraged if land is owned** |
| Lease Agreement | **Recommended** | PDF | **Strongly encouraged if leased** |
| Letter from Chief/Family Head | **Recommended** | PDF/Image | **If family land - helps prevent disputes** |
| Survey Plan | **Recommended** | PDF/Image | **Land demarcation - encouraged** |

**Why Land Documentation is Recommended:**
- **Tenure Security**: Reduces risk of land disputes
- **Long-term Planning**: Confidence for infrastructure investment
- **Loan Eligibility**: Banks require land documentation
- **Dispute Prevention**: Clear ownership prevents future conflicts
- **Program Protection**: YEA investment protected

**System Action**:
- Flags farms without land documentation
- Periodic reminders to upload (every 6 months)
- Priority support for farms with secure tenure
- Legal assistance program for documentation (future)

### 8.4 Business Documents (If Applicable)
| Document | Required | Format | Notes |
|----------|----------|--------|-------|
| Business Registration Certificate | No | PDF/Image | If registered |
| Previous Production Records | No | PDF/Excel | Historical data |
| Tax Clearance | No | PDF | For procurement |

---

## 9. APPLICATION METADATA & WORKFLOW

### 9.1 Application Tracking
| Field | Type | Auto-Generated | Notes |
|-------|------|----------------|-------|
| `application_id` | String | Yes | Format: APP-YYYY-XXXXX |
| `application_date` | DateTime | Yes | Submission timestamp |
| `application_status` | Choice | No | See workflow below |
| `assigned_constituency` | FK | Auto | From GPS location |
| `assigned_extension_officer` | FK | No | Manual assignment |
| `assigned_reviewer` | FK | No | Official reviewing |

**Application Status Workflow**:
```
Submitted → Under Review → More Info Needed → Approved → Active
                         ↓
                      Rejected
```

### 9.2 Review Information
| Field | Type | Notes |
|-------|------|-------|
| `review_comments` | Text | Official's assessment |
| `site_visit_required` | Boolean | Flag for physical inspection |
| `site_visit_date` | Date | If scheduled |
| `site_visit_notes` | Text | Findings from visit |
| `rejection_reason` | Text | If rejected |
| `more_info_requested` | Text | What additional info needed |

### 9.3 Approval & Activation
| Field | Type | Notes |
|-------|------|-------|
| `approval_date` | DateTime | When approved |
| `approved_by` | FK | Official who approved |
| `benefit_package_assigned` | JSON | Details below |
| `farm_id` | String | Format: YEA-REG-CONST-XXXX |
| `farm_status` | Choice | Active, Inactive, Suspended |
| `activation_date` | DateTime | When farm became active |

### 9.4 Benefit Package Structure (JSON)
```json
{
  "initial_flock_size": 500,
  "chick_type": "Isa Brown Layers",
  "feed_allocation_kg": 2000,
  "feed_type": ["Starter", "Grower", "Layer"],
  "medication_package": "Standard Vaccination Protocol",
  "equipment_support": ["50 Feeders", "50 Drinkers"],
  "total_package_value_ghs": 15000,
  "delivery_schedule": "2025-11-15"
}
```

---

## 10. CALCULATED FIELDS & METRICS

**System Auto-Calculates**:

| Metric | Formula | Purpose |
|--------|---------|---------|
| `farm_readiness_score` | Based on infrastructure checklist | Qualification assessment |
| `biosecurity_score` | Count of biosecurity measures / total × 100 | Risk rating |
| `capacity_utilization` | (current_birds / total_capacity) × 100 | Expansion potential |
| `experience_level` | Categorize: Beginner (0-1yr), Intermediate (2-5yr), Expert (5+yr) | Support targeting |
| `support_priority_score` | Based on needs, readiness, location | Resource allocation |

---

## 11. DATA VALIDATION RULES

### Required Field Combinations:
- If `primary_production_type` = "Layers" → `layer_breed` required
- If `primary_production_type` = "Broilers" → `broiler_breed` required
- If `has_outstanding_debt` = True → `debt_amount` required
- If `land_ownership_status` = "Leased" → Lease document recommended

### Business Logic:
- `current_bird_count` ≤ `total_bird_capacity`
- Sum of `house_capacity` across all houses = `total_bird_capacity`
- `date_of_birth` must make farmer 18-65 years old
- `ghana_card_number` must be unique in system
- `primary_phone` must be unique (one phone per farmer)
- At least **3 farm photos** must be uploaded
- At least **1 location** must be registered per farm

### Geographic Validation:
- GPS coordinates must be **within Ghana boundaries**
- `constituency` must match GPS location (auto-verified)
- If GPS and stated constituency mismatch → flag for review

---

## 12. PRIVACY & DATA PROTECTION

### Sensitive Data (Restricted Access):
- Ghana Card Number (encrypted)
- Bank Account Details (encrypted)
- Phone Numbers (masked for non-authorized users)
- Financial Information (admin only)
- Next of Kin details (admin + farmer only)

### Public Data (Marketplace):
- Farm Name
- General Location (District, not exact GPS)
- Production Type
- Available Products
- Contact preference (not actual number, use contact form)

---

## SUMMARY: TOTAL FIELDS COUNT

| Section | Required Fields | Optional Fields | Total |
|---------|----------------|-----------------|-------|
| Personal Identity | 6 | 3 | 9 |
| Contact Info | 3 | 2 | 5 |
| Next of Kin | 3 | 1 | 4 |
| Education & Experience | 3 | 3 | 6 |
| Business Info | 6 (**TIN required**) | 1 | 7 |
| Employment | 1 | 2 | 3 |
| **Financial Info** | **6 (Mandatory)** | **2** | **8** |
| Location (per site) | 9 | 4 | 13 |
| Infrastructure | 5 | 0 | 5 |
| Poultry Houses | 5/house | 5/house | 10/house |
| Equipment | 5 | 12 | 17 |
| Utilities | 5 | 1 | 6 |
| Biosecurity | 5 | 4 | 9 |
| Production | 5 (**incl. start date & monthly targets**) | 5 | 10 |
| Support Needs | 0 (**Updated periodically**) | 11 | 11 |
| **Documents** | **5 (ID + 3 photos + TIN)** | **8** | **13** |

**Estimated Completion Time**: 35-50 minutes for comprehensive registration

---

## KEY POLICY DECISIONS SUMMARY

### ✅ **MANDATORY REQUIREMENTS**

1. **Tax Identification Number (TIN)** - Required for government procurement compliance
2. **Financial Information** - All financial fields mandatory for:
   - Program sustainability assessment
   - ROI tracking
   - Risk assessment
   - Impact measurement
3. **Farm Photos** - Minimum 3 photos mandatory:
   - 1 exterior poultry house
   - 1 interior poultry house
   - 1 overall farm layout
4. **Production Start Date** - Required for cycle planning
5. **Monthly Production Targets** - Required for procurement forecasting

### ⚠️ **STRONGLY ENCOURAGED (With Incentives)**

1. **Business Registration** - Not required but incentivized:
   - Priority for government procurement
   - Bulk purchase discounts
   - Business development grants eligibility
   - Featured marketplace listing
   - Formalization support and training

### 📋 **RECOMMENDED (Not Required)**

1. **Land Documentation** - Encouraged if available:
   - Tenure security
   - Dispute prevention
   - Loan eligibility
   - Long-term planning confidence
   - System sends periodic reminders

### 📊 **ASSESSMENT CRITERIA (Not Requirements)**

1. **Infrastructure Details** - Used for scoring, not blocking approval:
   - Farm readiness score
   - Support package customization
   - Investment value tracking
   - Development monitoring

### 🔄 **PERIODIC UPDATES**

1. **Support Needs Assessment** - Updated:
   - Quarterly (first year)
   - Bi-annually (after first year)
   - Ad-hoc (farmer request)

---

## INVESTMENT TRACKING SYSTEM

**Total Farm Investment Value** = Auto-calculated from:
- Total Infrastructure Value
- All Poultry Houses Value
- All Equipment Values (feeders, drinkers, incubators, generator, storage, etc.)
- Initial Capital Investment

**Used for**:
- ROI calculation per farm
- Program-wide investment analysis
- Growth tracking over time
- Success metrics
- Loan eligibility assessment

**Formula**:
```
Total Investment = 
  total_infrastructure_value_ghs + 
  Σ(estimated_house_value_ghs) + 
  Σ(all_equipment_values) + 
  initial_investment_amount
```

---

## BUSINESS REGISTRATION INCENTIVE FRAMEWORK

### **Registered Business Benefits**:
| Benefit | Impact |
|---------|--------|
| Priority Procurement | 20% higher chance of government orders |
| Bulk Discounts | 10-15% discount on supplies |
| Grant Eligibility | Access to ₵50,000-₵200,000 grants |
| Featured Listing | Top placement in public marketplace |
| Business Training | Free formalization workshops |
| Credit Access | Pre-qualified for partner bank loans |

### **System Actions for Unregistered Farms**:
- Dashboard banner: "Register your business to unlock benefits"
- Quarterly email/SMS reminders
- Success stories from registered farmers
- Free webinars on registration process
- Partnership with Registrar General's Dept for fast-track registration

**Conversion Goal**: 80% of farms registered within 2 years

---

## NEXT STEPS

1. ✅ Review this model specification
2. ⏭️ Design **database schema** (Django models)
3. ⏭️ Create **registration form UI** (multi-step wizard)
4. ⏭️ Define **approval criteria & scoring system**
5. ⏭️ Build **benefit package templates**

**Ready to proceed with database schema design?**
