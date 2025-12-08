# Farm Profile Auto-Creation on Final Approval

## Overview
When an application reaches final approval (national-level approval), the system now automatically creates the farm profile. This eliminates the data integrity issue where approved applications had user accounts but no farm records.

## What Changed

### 1. Admin Approval Workflow (`accounts/admin_views.py`)
Added automatic farm profile creation when application is approved at national level:

```python
def _create_farm_profile(application):
    """Create farm profile from approved application"""
    # Creates Farm record with all required fields populated from application
    # Links farm to application
    # Sets farm_status = 'Pending Setup' until farmer completes profile
```

**When**: Called automatically in `AdminApplicationApproveView` when status changes from `national_review` → `approved`

**Response includes**:
```json
{
  "success": true,
  "application_number": "APP-2025-00007",
  "new_status": "approved",
  "next_level": "final",
  "farm_created": true,
  "message": "Application approved and farm profile created"
}
```

### 2. Backfill Command (`farms/management/commands/backfill_farm_profiles.py`)
Created management command to fix existing data:

```bash
# Dry run to see what would be created
python manage.py backfill_farm_profiles --dry-run

# Create missing farm profiles
python manage.py backfill_farm_profiles

# Backfill specific application
python manage.py backfill_farm_profiles --application-id <uuid>
```

**What it does**:
- Finds approved applications with user accounts but no farm profiles
- Creates farm records with all required fields
- Links farm to application
- Safe to run multiple times (skips existing farms)

## Farm Profile Creation Details

### Data Mapping (Application → Farm)
| Application Field | Farm Field | Notes |
|-------------------|------------|-------|
| first_name, middle_name, last_name | Same | Direct copy |
| date_of_birth | Same | With age validation (18-65) |
| gender | Same | Male/Female/Other |
| ghana_card_number | Same | GHA-XXXXXXXXX-X format |
| primary_phone, alternate_phone | Same | Ghana phone numbers |
| email | Same | Optional |
| residential_address | Same | Text field |
| primary_constituency | Same | Required for all farmers |
| proposed_farm_name | farm_name | Unique farm name |
| primary_production_type | Same | Layers/Broilers/Both |
| planned_bird_capacity | total_bird_capacity | Integer |
| years_in_poultry | Same | Decimal (0-50) |
| application_type | registration_source | government_initiative or self_registered |
| yea_program_batch | Same | YEA batch number |

### Default Values for Required Fields
Since applications don't collect all farm registration details, we use sensible defaults:

| Field | Default | Reason |
|-------|---------|--------|
| `marital_status` | Single | Can be updated later |
| `number_of_dependents` | 0 | Can be updated later |
| `nok_full_name` | "To be provided" | Required, farmer must update |
| `nok_relationship` | "To be provided" | Required, farmer must update |
| `nok_phone` | farmer's phone | Temporary, farmer must update |
| `education_level` | JHS | Common level, can update |
| `literacy_level` | Can Read & Write | Assumption for applicants |
| `farming_full_time` | true | Assumption for program farmers |
| `ownership_type` | Sole Proprietorship | Most common |
| `tin` | Generated from UUID | Temporary, farmer must get real TIN |
| `number_of_poultry_houses` | 1 | Minimum, can update |
| `housing_type` | Deep Litter | Most common |
| `total_infrastructure_value_ghs` | 0 | To be assessed |
| `planned_production_start_date` | Today | Can be updated |
| `initial_investment_amount` | 0 | To be assessed |
| `funding_source` | ["YEA Program"] | For government program |
| `monthly_operating_budget` | 0 | To be assessed |
| `expected_monthly_revenue` | 0 | To be assessed |
| `has_outstanding_debt` | false | Default assumption |
| `farm_status` | "Pending Setup" | Until farmer completes profile |

## Data Model Explanation

### Why Two Tables?

**FarmApplication**:
- Pre-approval application form
- Submitted before farmer has account
- Contains proposed/planned information
- Used by admin for screening and approval
- Less comprehensive (only essential fields)

**Farm**:
- Operational farm profile
- Created after approval
- Contains comprehensive operational details
- Required for daily operations (production tracking, procurement, etc.)
- Links to user account for authentication

### Workflow
```
1. Prospective farmer submits FarmApplication (no account yet)
   ↓
2. Admin reviews at constituency → regional → national levels
   ↓
3. National admin approves → FarmApplication status = 'approved'
   ↓
4. System automatically creates:
   - Farm record (from application data + defaults)
   - Links Farm ↔ FarmApplication
   ↓
5. Admin sends invitation email/SMS
   ↓
6. Farmer accepts invitation → User account created (if not exists)
   ↓
7. Farmer logs in → sees dashboard with farm data
   ↓
8. Farmer completes missing details (TIN, Next of Kin, financials, etc.)
   ↓
9. Farm status changes: 'Pending Setup' → 'Active'
```

## Benefits

### Before This Change
❌ Manual farm creation required  
❌ Data integrity issues (user without farm)  
❌ Farmers couldn't log in to see dashboard  
❌ Extra admin work to create farms  

### After This Change
✅ Automatic farm creation on approval  
✅ Data integrity guaranteed  
✅ Farmers see dashboard immediately after login  
✅ Reduced admin workload  
✅ Clear workflow: approve → farm created → invitation sent  

## Testing

### Test Scenario 1: New Application Approval
```bash
# 1. Create and approve application through all levels
POST /api/admin/applications/<id>/approve/  # Constituency
POST /api/admin/applications/<id>/approve/  # Regional
POST /api/admin/applications/<id>/approve/  # National (creates farm)

# 2. Verify farm created
GET /api/dashboards/farmer/overview/  # As farmer
# Should show farm details, not "No farm found"
```

### Test Scenario 2: Backfill Existing Data
```bash
# 1. Find approved applications without farms
python manage.py shell -c "
from farms.application_models import FarmApplication
apps = FarmApplication.objects.filter(
    status='approved',
    user_account__isnull=False,
    farm_profile__isnull=True
)
print(f'Found {apps.count()} applications needing backfill')
"

# 2. Run backfill
python manage.py backfill_farm_profiles

# 3. Verify all have farms now
# Re-run query from step 1, should show 0
```

## Future Improvements

1. **Progressive Profile Completion**:
   - Track which fields have default values
   - Show "Complete Your Profile" banner in farmer dashboard
   - Guide farmers through updating required fields (TIN, Next of Kin, financials)

2. **Farm Status Automation**:
   - Auto-change status from "Pending Setup" → "Active" when all required fields updated
   - Send notification when profile is complete

3. **Admin Dashboard Enhancement**:
   - Show which farms have incomplete profiles
   - Send reminders to farmers to complete profiles

4. **TIN Integration**:
   - API integration with Ghana Revenue Authority (GRA) to validate real TINs
   - Replace temporary TINs with validated ones

## Related Files
- `accounts/admin_views.py` - Approval workflow with farm creation
- `farms/management/commands/backfill_farm_profiles.py` - Data backfill command
- `dashboards/services/farmer.py` - Farmer dashboard (requires farm)
- `FARMER_DASHBOARD_API.md` - Frontend integration guide
