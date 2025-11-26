# Production Tracking System - User Guide

## Overview
The production tracking system manages daily farm operations for the YEA Poultry Management System. It tracks bird batches (flocks), daily production records, and detailed mortality incidents for disease surveillance and compensation claims.

## Core Components

### 1. **Flock Model** - Bird Batch Management
Represents a cohort of birds managed together (not tracked individually).

#### Key Features:
- **Identification**: Unique flock number, type (Layers/Broilers/Breeders), breed
- **Acquisition**: Source (YEA Program/Purchased), arrival date, initial count
- **Financial Tracking**: Purchase price, total costs (feed, medication, vaccination)
- **Status Tracking**: Current count, mortality rate, survival rate
- **Production Metrics**: Total eggs produced, feed conversion ratio
- **Auto-Calculations**: Mortality rate, average daily mortality, production efficiency

#### Flock Types:
- **Layers**: Egg production birds (18-80 weeks lifecycle)
- **Broilers**: Meat production (6-8 weeks lifecycle)
- **Breeders**: Hatching eggs production
- **Pullets**: Young layers (0-18 weeks)
- **Mixed**: Multi-purpose birds

#### Example Use Case:
```
Flock: FLOCK-2025-001
Type: Layers
Breed: Isa Brown
Source: YEA Program
Arrival: 2025-01-01
Initial Count: 1,000 birds (8 weeks old)
Current Count: 950 birds
Mortality Rate: 5.0%
Production Start: 2025-03-15 (at 18 weeks)
```

#### Auto-Calculated Metrics:
- **Current Age**: Automatically calculated from arrival date + age at arrival
- **Mortality Rate**: (Total deaths / Initial count) × 100
- **Average Daily Mortality**: Total deaths / Days since arrival
- **Survival Rate**: (Current count / Initial count) × 100
- **Average Eggs Per Bird**: Total eggs / Initial count
- **Feed Conversion Ratio**: Feed consumed (kg) / Production (kg)

---

### 2. **DailyProduction Model** - Daily Operations Record
Captures daily farm data for monitoring and government reporting.

#### Key Features:

##### **Egg Production (Layers)**
- Total eggs collected
- Quality breakdown: Good, Broken, Dirty, Small, Soft-shell
- Production rate % (eggs per bird ratio)

##### **Mortality Tracking**
- Number of birds died
- Mortality reason (Disease/Predator/Heat Stress/etc.)
- Detailed notes for investigation

##### **Feed Consumption**
- Amount consumed (kg)
- Feed type (Starter/Grower/Layer Mash/etc.)
- Daily feed cost

##### **Health Observations**
- General health status (Excellent → Critical)
- Unusual behavior notes
- Disease symptoms flagging
- Vaccination/medication records

##### **Birds Sold**
- Number sold
- Revenue generated

#### Automatic Updates:
When a daily production record is saved:
1. **Flock current count** decreases by (birds died + birds sold)
2. **Total eggs produced** increases
3. **Total feed consumed** accumulates
4. **Feed/medication costs** accumulate
5. **Production rate** is calculated

#### Validation Rules:
- ✅ Egg breakdown must equal total eggs collected
- ✅ Birds died cannot exceed current flock count
- ✅ Production date cannot be in the future
- ✅ Production date cannot be before flock arrival
- ✅ One record per flock per day (unique constraint)

#### Example Daily Record:
```
Date: 2025-01-15
Flock: FLOCK-2025-001
Eggs Collected: 820 eggs
  - Good: 800
  - Broken: 10
  - Dirty: 5
  - Small: 5
Production Rate: 86.3% (820 eggs / 950 birds)
Birds Died: 2
Mortality Reason: Heat Stress
Feed Consumed: 120 kg (Layer Mash)
General Health: Good
```

---

### 3. **MortalityRecord Model** - Disease Surveillance & Claims
Detailed investigation of mortality incidents for government monitoring and compensation.

#### Key Features:

##### **Incident Details**
- Date discovered
- Number of birds affected
- Link to daily production record

##### **Cause Analysis**
- Probable cause (Viral/Bacterial/Parasitic/Predator/etc.)
- Specific disease suspected (Newcastle, Fowl Pox, etc.)
- Symptoms observed (JSON array for multi-select)
- Detailed symptom description

##### **Veterinary Investigation**
- Inspection required flag (auto-set for 10+ deaths or disease)
- Vet inspector assignment
- Inspection date
- Veterinary diagnosis
- Lab test results

##### **Disposal Tracking**
- Disposal method (Burial/Incineration/Composting)
- Disposal location (GPS coordinates)
- Disposal date

##### **Financial Impact**
- Estimated value per bird
- Total estimated loss (auto-calculated)

##### **Compensation Claims**
- Claim status (Not Claimed → Pending → Approved/Rejected → Paid)
- Compensation amount
- Photo evidence (3 photos supported)

#### Auto-Features:
- **Auto-flag for vet inspection** if:
  - 10+ birds died in incident
  - Probable cause is disease
- **Auto-calculate total loss**: birds × value per bird

#### Example Mortality Record:
```
Date: 2025-01-20
Flock: FLOCK-2025-001
Number of Birds: 15
Probable Cause: Disease - Viral
Disease Suspected: Newcastle Disease
Symptoms: Respiratory distress, nervous signs, drop in egg production
Vet Inspection: Required (auto-flagged)
Estimated Value: GHS 35 per bird
Total Loss: GHS 525
Compensation Status: Pending
```

---

## Database Schema

### Table: `flocks`
**38 columns total** including:
- `id` (UUID, Primary Key)
- `farm_id` (FK to farms)
- `flock_number` (varchar 50, indexed)
- `flock_type` (varchar 20, choices, indexed)
- `breed` (varchar 100)
- `arrival_date` (date, indexed)
- `initial_count` (integer)
- `current_count` (integer)
- `mortality_rate_percent` (decimal, auto-calculated)
- `total_eggs_produced` (integer, auto-calculated)
- `feed_conversion_ratio` (decimal, auto-calculated)

**Unique Constraint**: (farm, flock_number)

**Indexes**:
- (farm_id, status)
- (flock_type, status)
- (arrival_date)

---

### Table: `daily_production`
**32 columns total** including:
- `id` (UUID, Primary Key)
- `farm_id` (FK to farms)
- `flock_id` (FK to flocks)
- `production_date` (date, indexed)
- `eggs_collected` (integer)
- `good_eggs` (integer)
- `broken_eggs` (integer)
- `birds_died` (integer)
- `feed_consumed_kg` (decimal)
- `production_rate_percent` (decimal, auto-calculated)
- `general_health` (varchar 20, choices)

**Unique Constraint**: (flock, production_date)

**Indexes**:
- (farm_id, production_date)
- (flock_id, production_date)
- (-production_date) [descending for recent records]

---

### Table: `mortality_records`
**33 columns total** including:
- `id` (UUID, Primary Key)
- `farm_id` (FK to farms)
- `flock_id` (FK to flocks)
- `daily_production_id` (FK, nullable)
- `date_discovered` (date, indexed)
- `number_of_birds` (integer)
- `probable_cause` (varchar 50, choices, indexed)
- `vet_inspection_required` (boolean, indexed)
- `vet_inspected` (boolean, indexed)
- `compensation_status` (varchar 20, choices, indexed)
- `total_estimated_loss` (decimal, auto-calculated)

**Indexes**:
- (farm_id, date_discovered)
- (flock_id, date_discovered)
- (probable_cause)
- (vet_inspection_required, vet_inspected)
- (compensation_claimed, compensation_status)

---

## Admin Interface Features

### Flock Admin
**List View**:
- Color-coded mortality rate badges (Green <5%, Orange 5-10%, Red >10%)
- Current age in weeks (auto-calculated)
- Production status
- Quick filters by status, type, source

**Bulk Actions**:
- Mark as Sold
- Mark as Active
- Recalculate Metrics

**Detail View**:
- Collapsible sections for organization
- Read-only auto-calculated fields
- Production phase tracking for layers

---

### Daily Production Admin
**List View**:
- Color-coded production rate (Green ≥80%, Orange 60-80%, Red <60%)
- Health status badges (color-coded)
- Clickable flock links
- Date hierarchy for easy navigation

**Bulk Actions**:
- Flag for disease inspection

**Validation**:
- Egg breakdown validation
- Prevents future dates
- Enforces one record per day per flock

---

### Mortality Record Admin
**List View**:
- Vet inspection status badges (Green=Inspected, Orange=Pending)
- Compensation status badges (color-coded)
- Total estimated loss displayed
- Quick filters by cause, vet status, compensation

**Bulk Actions**:
- Request vet inspection
- Mark as inspected
- Approve/reject compensation

**Photo Evidence**:
- 3 photo upload fields
- Stored in `/media/mortality_evidence/YYYY/MM/`

---

## Workflow Examples

### Scenario 1: New Flock Arrival
1. **Farm registers in system** → `farms` app
2. **Create Flock record**:
   ```
   Flock Number: FLOCK-2025-001
   Type: Layers
   Breed: Isa Brown
   Source: YEA Program
   Arrival Date: 2025-01-01
   Initial Count: 1000 birds
   Age at Arrival: 8 weeks
   Purchase Price: GHS 25/bird
   ```
3. **System auto-calculates**:
   - Total acquisition cost: GHS 25,000
   - Current count: 1000 (same as initial)
   - Mortality rate: 0%

---

### Scenario 2: Daily Production Entry
1. **Farmer enters daily data**:
   ```
   Date: 2025-03-20
   Flock: FLOCK-2025-001
   Eggs: 850 (820 good, 20 broken, 5 dirty, 5 small)
   Birds Died: 3 (Heat Stress)
   Feed: 125 kg Layer Mash (GHS 120)
   Health: Good
   ```
2. **System auto-updates Flock**:
   - Current count: 1000 → 997
   - Total eggs: 0 → 850
   - Total feed consumed: 0 → 125 kg
   - Total feed cost: 0 → GHS 120
   - Mortality rate: 0.3%
   - Production rate: 85.3%

---

### Scenario 3: Disease Outbreak
1. **Farmer discovers 20 dead birds**
2. **Create Mortality Record**:
   ```
   Date: 2025-03-25
   Birds: 20
   Cause: Disease - Viral
   Disease Suspected: Newcastle Disease
   Symptoms: Respiratory distress, twisted necks
   ```
3. **System auto-flags**:
   - Vet inspection required: ✓ (20 birds > 10 threshold)
   - Inspection requested date: 2025-03-25
4. **Veterinary Officer** assigned:
   - Inspects farm
   - Enters diagnosis
   - Orders lab tests
5. **Compensation Process**:
   - Farmer claims: GHS 700 (20 birds × GHS 35)
   - Status: Pending → Approved → Paid

---

## Government Reporting Use Cases

### 1. **Monthly Production Report**
Query all `DailyProduction` records for a region:
```sql
SELECT 
    f.district,
    COUNT(DISTINCT dp.flock_id) as active_flocks,
    SUM(dp.eggs_collected) as total_eggs,
    SUM(dp.birds_died) as total_mortality,
    AVG(dp.production_rate_percent) as avg_production_rate
FROM daily_production dp
JOIN farms f ON dp.farm_id = f.id
WHERE dp.production_date BETWEEN '2025-03-01' AND '2025-03-31'
GROUP BY f.district
```

### 2. **Disease Surveillance Dashboard**
Query mortality records for disease hotspots:
```sql
SELECT 
    f.district,
    mr.disease_suspected,
    COUNT(*) as incidents,
    SUM(mr.number_of_birds) as total_deaths
FROM mortality_records mr
JOIN farms f ON mr.farm_id = f.id
WHERE mr.probable_cause LIKE 'Disease%'
    AND mr.date_discovered >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY f.district, mr.disease_suspected
ORDER BY total_deaths DESC
```

### 3. **ROI Calculation**
Calculate return on investment per flock:
```sql
SELECT 
    flock_number,
    total_acquisition_cost + total_feed_cost + total_medication_cost as total_investment,
    total_eggs_produced * 0.50 as egg_revenue, -- GHS 0.50 per egg
    (total_eggs_produced * 0.50) - (total_acquisition_cost + total_feed_cost) as profit
FROM flocks
WHERE status = 'Active'
ORDER BY profit DESC
```

---

## Performance Metrics Tracked

### Flock-Level Metrics:
1. **Mortality Rate** = (Total deaths / Initial count) × 100
2. **Survival Rate** = (Current count / Initial count) × 100
3. **Average Daily Mortality** = Total deaths / Days since arrival
4. **Average Eggs Per Bird** = Total eggs / Initial count
5. **Feed Conversion Ratio** = Feed consumed (kg) / Production (kg)

### Daily Production Metrics:
1. **Production Rate** = (Eggs collected / Current count) × 100
2. **Egg Quality Rate** = (Good eggs / Total eggs) × 100
3. **Feed Efficiency** = Eggs collected / Feed consumed (kg)

### Farm-Level Aggregations:
1. **Total Egg Production** (all flocks)
2. **Overall Mortality Rate**
3. **Revenue vs Investment**
4. **Disease Incident Frequency**

---

## API Endpoints (Future Implementation)

### Flock Management:
- `GET /api/flocks/` - List all flocks
- `POST /api/flocks/` - Create new flock
- `GET /api/flocks/{id}/` - Flock details
- `PUT /api/flocks/{id}/` - Update flock
- `GET /api/flocks/{id}/metrics/` - Performance metrics

### Daily Production:
- `GET /api/production/` - List daily records
- `POST /api/production/` - Submit daily record
- `GET /api/production/{id}/` - Record details
- `GET /api/production/bulk/` - Bulk import historical data

### Mortality Records:
- `GET /api/mortality/` - List mortality incidents
- `POST /api/mortality/` - Report mortality
- `PUT /api/mortality/{id}/` - Update investigation
- `GET /api/mortality/pending-inspection/` - Vet queue

---

## Best Practices

### For Farmers:
1. **Enter daily production records every day** (even if no eggs/deaths)
2. **Be accurate with egg counts** - breakdown must match total
3. **Report all mortality immediately** - critical for disease control
4. **Take photos of unusual deaths** - supports compensation claims
5. **Record all feed deliveries** - helps calculate true costs

### For Veterinary Officers:
1. **Inspect flagged mortality within 48 hours**
2. **Document findings thoroughly** - diagnosis impacts compensation
3. **Recommend lab tests for unknown diseases**
4. **Update disposal methods** - environmental compliance

### For Government Administrators:
1. **Monitor production rates weekly** - identify struggling farms
2. **Track disease patterns regionally** - early outbreak detection
3. **Review compensation claims promptly** - maintain farmer trust
4. **Generate monthly reports** - measure program success

---

## Technical Notes

### UUID Primary Keys:
All models use UUID (128-bit unique identifiers) instead of integer IDs:
- **Non-sequential**: Prevents data leakage about farm count
- **Globally unique**: Supports distributed data collection
- **Secure**: Cannot guess valid IDs
- **Scalable**: Handles nationwide deployment

### Data Validation:
- **Model-level validation** in `clean()` methods
- **Database constraints** (unique, foreign keys)
- **Admin-level validation** before save
- **API-level validation** (future DRF serializers)

### Auto-Calculations:
Triggered on model `save()`:
- Flock metrics recalculated when DailyProduction saved
- Mortality rates updated when bird count changes
- Total costs accumulated from daily records

### Audit Trail:
- `created_at`, `updated_at` timestamps on all models
- `recorded_by`, `reported_by` user references
- `vet_inspector` assignment tracking

---

## Database Statistics (Current)

```
Total Tables: 38
Production Tables: 3
  - flocks
  - daily_production
  - mortality_records

Total Fields: 98
  - Flock: 33 fields
  - DailyProduction: 32 fields
  - MortalityRecord: 33 fields

Primary Keys: UUID (all models)
Foreign Keys: 7
Unique Constraints: 2
Indexes: 15
```

---

## Next Steps (Future Development)

1. **Feed Inventory Module**:
   - Track feed purchases
   - Monitor stock levels
   - Alert low inventory
   - Calculate feed costs per bag

2. **Medication & Vaccination Module**:
   - Vaccination schedules
   - Medication tracking
   - Treatment history
   - Vet prescription management

3. **Sales & Revenue Module**:
   - Egg sales tracking
   - Bird sales (culled layers, broilers)
   - Customer management
   - Invoice generation

4. **Analytics Dashboard**:
   - Real-time production charts
   - Regional performance maps
   - Disease outbreak alerts
   - ROI calculators

5. **Mobile App Integration**:
   - Farmer-facing daily entry app
   - Photo upload for mortality
   - Push notifications for alerts
   - Offline data collection

---

## Support & Documentation

- **Django Admin**: http://localhost:8000/admin/flock_management/
- **Models**: `/flock_management/models.py`
- **Admin Config**: `/flock_management/admin.py`
- **Migrations**: `/flock_management/migrations/`

For technical support, contact the YEA PMS development team.

---

**Last Updated**: January 2025  
**Version**: 1.0  
**Status**: Production Ready ✅
