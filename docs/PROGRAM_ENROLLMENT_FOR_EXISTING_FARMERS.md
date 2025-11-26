# Government Program Enrollment for Existing Farmers

## Overview

This document explains how **EXISTING farmers** (already registered on the platform) can apply to join government support programs like YEA.

This is **different** from the new farmer onboarding process:
- **New Farmers**: Use `FarmApplication` → screening → invitation → create account
- **Existing Farmers**: Use `ProgramEnrollmentApplication` → screening → farm status updated to government-sponsored

## Scenarios Covered

### Scenario 1: Independent Farmer Wants to Join YEA
```
Status: Independent farmer, already using platform for farm management
Goal: Join YEA program to access support package and extension services
Process: Submit program enrollment application → screening → approval → farm converted to government-sponsored
```

### Scenario 2: Private Farmer Wants Government Subsidies
```
Status: Self-registered farmer, paying for marketplace
Goal: Access government subsidies for marketplace subscription
Process: Submit program enrollment application → screening → approval → marketplace subsidy activated
```

### Scenario 3: Government Farmer Wants Additional Programs
```
Status: Already in one government program
Goal: Join additional support program (e.g., infrastructure development)
Process: Submit program enrollment application → screening → approval → additional support added
```

## Database Models

### 1. GovernmentProgram

Master list of available government support programs.

**Key Fields:**
- `program_name`: E.g., "YEA Poultry Support Program 2025"
- `program_code`: E.g., "YEA-2025-Q1"
- `program_type`: training_support, input_subsidy, financial_grant, infrastructure, comprehensive
- `implementing_agency`: E.g., "Youth Employment Agency"
- `start_date` / `end_date`: Program duration
- `application_deadline`: Last date to accept applications

**Eligibility Criteria:**
- `min_farm_age_months`: Minimum months farm must be operational (0 for new farms welcome)
- `max_farm_age_years`: Maximum farm age (e.g., only for farms < 2 years)
- `min_bird_capacity` / `max_bird_capacity`: Capacity requirements
- `eligible_farmer_age_min` / `eligible_farmer_age_max`: Age range (default 18-65)
- `eligible_constituencies`: List of eligible constituencies (empty = all)
- `requires_extension_officer`: Whether extension officer assignment is required

**Support Package:**
```json
{
    "day_old_chicks": 500,
    "feed_bags_per_cycle": 100,
    "training_sessions": 12,
    "extension_visits_per_month": 2,
    "monetary_grant": 5000.00,
    "infrastructure_support": "Cage construction",
    "marketplace_subsidy_months": 12
}
```

**Capacity Management:**
- `total_slots`: Total number of farmers program can support
- `slots_filled`: Current enrollment count
- `slots_available`: Auto-calculated (total - filled)
- `status`: active, full, inactive

**Example Programs:**

#### YEA Comprehensive Support Program
```python
{
    'program_name': 'YEA Poultry Support Program 2025',
    'program_code': 'YEA-2025-Q1',
    'program_type': 'comprehensive',
    'implementing_agency': 'Youth Employment Agency',
    'start_date': '2025-01-01',
    'end_date': '2025-12-31',
    'application_deadline': '2025-03-31',
    
    # Eligibility
    'min_farm_age_months': 0,  # Welcome new farms
    'max_farm_age_years': None,  # No upper limit
    'min_bird_capacity': 100,
    'max_bird_capacity': None,
    'eligible_farmer_age_min': 18,
    'eligible_farmer_age_max': 45,
    'eligible_constituencies': [],  # All constituencies
    'requires_extension_officer': True,
    
    # Support package
    'support_package_details': {
        'day_old_chicks': 500,
        'feed_bags_per_cycle': 100,
        'training_sessions': 12,
        'extension_visits_per_month': 2,
        'marketplace_subsidy_months': 12
    },
    
    # Capacity
    'total_slots': 1000,
    'status': 'active'
}
```

#### Small Farm Infrastructure Program
```python
{
    'program_name': 'Small Farm Infrastructure Development 2025',
    'program_code': 'INFRA-2025',
    'program_type': 'infrastructure',
    'implementing_agency': 'Ministry of Food and Agriculture',
    
    # Target small, established farms
    'min_farm_age_months': 12,  # Must be operational for 1 year
    'max_farm_age_years': 5,  # Only farms < 5 years old
    'min_bird_capacity': 50,
    'max_bird_capacity': 500,  # Small-scale only
    
    'support_package_details': {
        'infrastructure_support': 'Cage construction',
        'monetary_grant': 10000.00,
        'training_sessions': 6
    },
    
    'total_slots': 200,
    'status': 'active'
}
```

### 2. ProgramEnrollmentApplication

Application from existing farmer to join a government program.

**Key Fields:**
- `application_number`: Format: PROG-YYYY-XXXXX
- `farm`: FK to existing Farm
- `program`: FK to GovernmentProgram
- `applicant`: FK to User (farm owner)

**Application Content:**
- `motivation`: Why farmer wants to join
- `current_challenges`: Challenges farmer faces
- `expected_benefits`: How program will help

**Current Farm Status (Snapshot):**
- `current_bird_count`: Current birds on farm
- `current_production_type`: Layers/Broilers/Both
- `monthly_revenue`: Average monthly revenue
- `years_operational`: Years farm has been operational

**Supporting Documents:**
- `farm_photos`: URLs to uploaded photos
- `business_documents`: Business registration, permits, etc.

**Eligibility Assessment (Auto-calculated):**
- `eligibility_score`: 0-100 score
- `eligibility_flags`: Issues found
- `meets_eligibility`: Boolean (pass threshold = 50)

**Screening Workflow:**
- `status`: draft, submitted, constituency_review, regional_review, national_review, approved, enrolled, rejected
- `current_review_level`: eligibility, constituency, regional, national

**Approval Timeline:**
- `submitted_at`
- `constituency_reviewed_at`
- `regional_reviewed_at`
- `national_reviewed_at`
- `final_decision_at`

**Enrollment (After Approval):**
- `enrollment_completed`: Boolean
- `enrolled_at`: Timestamp
- `assigned_extension_officer`: FK to User
- `support_package_allocated`: Actual support received

**Priority Scoring:**
- Time waiting (older = higher priority)
- Farm size (smaller = higher priority)
- Revenue (lower = higher priority)
- Program deadline approaching
- Score 0-100

**Constraints:**
- Unique together: (farm, program) - One application per farm per program

### 3. ProgramEnrollmentReview

Audit trail for all review actions.

**Actions Tracked:**
- `submitted`: Application submitted
- `eligibility_passed` / `eligibility_failed`: Automated check
- `assigned`: Assigned to reviewer
- `claimed`: Reviewer claimed application
- `approved`: Approved at level
- `rejected`: Rejected
- `changes_requested`: Changes needed
- `withdrawn`: Farmer withdrew
- `enrolled`: Enrollment completed

**Fields:**
- `application`: FK to ProgramEnrollmentApplication
- `reviewer`: FK to User (null for automated)
- `review_level`: eligibility, constituency, regional, national
- `action`: See choices above
- `notes`: Review notes
- `timestamp`: When action occurred

### 4. ProgramEnrollmentQueue

Queue management for screening.

**Fields:**
- `application`: FK to ProgramEnrollmentApplication
- `review_level`: eligibility, constituency, regional, national
- `status`: pending, assigned, in_review, completed
- `assigned_to`: FK to User (reviewer)
- `assigned_at`: When assigned
- `priority`: Priority score (higher = more urgent)
- `sla_deadline`: When review should be completed
- `completed_at`: When completed

**SLA (Service Level Agreement):**
- Eligibility: 1 day (automated)
- Constituency: 7 days
- Regional: 5 days
- National: 3 days

**Constraints:**
- Unique together: (application, review_level)

## Application Workflow

### Step 1: Farmer Submits Application

**Requirements:**
- Must have existing Farm account
- Program must be accepting applications (status='active')
- Farm not already enrolled in this program
- Farm not already in a similar program (optional check)

**Data Required:**
```python
application_data = {
    'motivation': 'Text explaining why',
    'current_challenges': 'List of challenges',
    'expected_benefits': 'How program helps',
    'current_bird_count': 300,
    'current_production_type': 'Layers',
    'monthly_revenue': 5000.00,
    'years_operational': 2.5,
    'farm_photos': ['url1', 'url2'],
    'business_documents': ['url1']
}

# Submit
from farms.services.program_enrollment_service import ProgramEnrollmentService

application = ProgramEnrollmentService.submit_application(
    farm=farm,
    program=program,
    application_data=application_data,
    applicant=request.user
)
```

### Step 2: Automated Eligibility Check

System automatically checks:

1. **Farmer Age**
   - Must be within program age range (default 18-65)
   - Deduct 30 points if outside range

2. **Farm Operational Duration**
   - Check if farm operational long enough (min_farm_age_months)
   - Check if farm not too old (max_farm_age_years)
   - Deduct 25 points if fails

3. **Bird Capacity**
   - Check if meets min_bird_capacity
   - Check if under max_bird_capacity
   - Deduct 20 points if fails

4. **Constituency**
   - Check if farm constituency in eligible list
   - Deduct 40 points if not eligible

5. **Application Deadline**
   - Check if before deadline
   - Deduct 50 points if past deadline

6. **Program Capacity**
   - Check if slots available
   - Deduct 50 points if full

7. **Documentation**
   - Check if farm photos uploaded (10 points)
   - Check if business documents uploaded (10 points)

8. **Bonus Points**
   - Already government farmer +10 (easier transition)

**Pass Threshold:** 50 points or higher

**Result:**
- **Pass**: Application enters screening workflow (constituency_review)
- **Fail**: Application auto-rejected with reasons

### Step 3: Three-Tier Screening

Same process as new farmer screening, but for program enrollment.

#### Level 1: Constituency Review (7 days SLA)

**Constituency Officer Reviews:**
- Farm authenticity
- Local reputation
- Community standing
- Documentation validity
- Officer may visit farm

**Actions:**
- **Approve**: Move to regional review
- **Reject**: Application rejected
- **Request Changes**: Paused for farmer updates

#### Level 2: Regional Review (5 days SLA)

**Regional Officer Reviews:**
- Cross-constituency validation
- Program fit assessment
- Resource allocation planning
- Extension officer assignment planning

**Actions:**
- **Approve**: Move to national review
- **Reject**: Application rejected
- **Request Changes**: Paused for updates

#### Level 3: National Review (3 days SLA)

**National Officer Reviews:**
- Final program enrollment decision
- Budget availability
- Support package allocation
- Strategic alignment

**Actions:**
- **Approve**: Enrollment completed
- **Reject**: Application rejected

### Step 4: Enrollment Completion

Upon final approval, system automatically:

1. **Updates Farm Model:**
   ```python
   farm.registration_source = 'government_initiative'
   farm.yea_program_batch = program.program_code
   farm.yea_program_start_date = today
   farm.yea_program_end_date = today + program_duration
   farm.extension_officer = assigned_officer
   farm.government_support_package = support_package
   farm.save()
   ```

2. **Decrements Program Slots:**
   ```python
   program.slots_filled += 1
   program.save()  # Auto-updates slots_available
   ```

3. **Sends Notifications:**
   - Email/SMS to farmer: "Congratulations! Enrolled in [program]"
   - Notification to extension officer: "New farmer assigned"
   - Notification to constituency officer: "Enrollment completed"

### Step 5: Post-Enrollment

**Farmer Gains Access To:**
- Extension officer support
- Training sessions
- Input subsidies (chicks, feed)
- Marketplace subsidies (if included in package)
- Infrastructure support (if applicable)
- Financial grants (if applicable)

**Extension Officer Responsibilities:**
- Schedule initial farm visit
- Create training schedule
- Coordinate support package delivery
- Monitor farm progress
- Submit regular reports

## Service Methods

### ProgramEnrollmentService

Located: `farms/services/program_enrollment_service.py`

#### submit_application()
```python
ProgramEnrollmentService.submit_application(
    farm=farm_instance,
    program=program_instance,
    application_data=dict,
    applicant=user_instance
)
```
Submits new program enrollment application, runs eligibility check, starts screening.

#### approve_at_level()
```python
ProgramEnrollmentService.approve_at_level(
    application=application,
    reviewer=user_instance,
    notes='Approval notes'
)
```
Approves at current level, advances to next level or completes enrollment.

#### reject_at_level()
```python
ProgramEnrollmentService.reject_at_level(
    application=application,
    reviewer=user_instance,
    rejection_reason='ineligible_capacity',
    rejection_notes='Explanation'
)
```
Rejects application with reason.

#### request_changes()
```python
ProgramEnrollmentService.request_changes(
    application=application,
    reviewer=user_instance,
    requested_changes='Please upload farm photos'
)
```
Requests changes before approval.

#### resubmit_application()
```python
ProgramEnrollmentService.resubmit_application(
    application=application,
    updated_data={'farm_photos': ['new_urls']}
)
```
Farmer resubmits after making requested changes.

#### get_review_queue()
```python
queue = ProgramEnrollmentService.get_review_queue(
    review_level='constituency',
    constituency='Tema East',  # Optional
    assigned_to=officer  # Optional
)
```
Gets pending applications for review.

#### claim_for_review()
```python
ProgramEnrollmentService.claim_for_review(
    application=application,
    officer=user_instance
)
```
Officer claims application for review.

#### get_farmer_applications()
```python
applications = ProgramEnrollmentService.get_farmer_applications(
    farmer=user_instance
)
```
Gets all program applications for a farmer.

#### get_program_statistics()
```python
stats = ProgramEnrollmentService.get_program_statistics(
    program=program_instance
)

# Returns:
{
    'total_applications': 150,
    'pending': 45,
    'approved': 80,
    'enrolled': 75,
    'rejected': 25,
    'slots_total': 1000,
    'slots_filled': 75,
    'slots_available': 925,
    'acceptance_rate': 53.3
}
```

## Example Usage

### Example 1: Farmer Applies to YEA Program

```python
from farms.models import Farm, GovernmentProgram
from farms.services.program_enrollment_service import ProgramEnrollmentService

# Get farmer's farm
farm = Farm.objects.get(farmer=request.user)

# Get YEA program
program = GovernmentProgram.objects.get(program_code='YEA-2025-Q1')

# Check if program accepting applications
if not program.is_accepting_applications:
    return Response({'error': 'Program not accepting applications'}, status=400)

# Prepare application data
application_data = {
    'motivation': 'I want to expand my farm and need training on modern techniques',
    'current_challenges': 'Limited access to quality feed, need better marketing channels',
    'expected_benefits': 'Extension officer guidance, feed subsidies, marketplace access',
    'current_bird_count': 200,
    'current_production_type': 'Layers',
    'monthly_revenue': 3000.00,
    'years_operational': 1.5,
    'farm_photos': ['https://example.com/photo1.jpg'],
    'business_documents': ['https://example.com/tin_cert.pdf']
}

# Submit application
try:
    application = ProgramEnrollmentService.submit_application(
        farm=farm,
        program=program,
        application_data=application_data,
        applicant=request.user
    )
    
    if application.status == 'rejected':
        # Failed eligibility check
        return Response({
            'status': 'rejected',
            'reasons': application.eligibility_flags,
            'score': application.eligibility_score
        }, status=400)
    
    # Success - entered screening
    return Response({
        'application_number': application.application_number,
        'status': application.status,
        'eligibility_score': application.eligibility_score,
        'message': 'Application submitted successfully'
    }, status=201)
    
except ValidationError as e:
    return Response({'error': str(e)}, status=400)
```

### Example 2: Constituency Officer Reviews Application

```python
from farms.program_enrollment_models import ProgramEnrollmentApplication
from farms.services.program_enrollment_service import ProgramEnrollmentService

# Officer claims application
application = ProgramEnrollmentApplication.objects.get(application_number='PROG-2025-00001')

ProgramEnrollmentService.claim_for_review(
    application=application,
    officer=request.user
)

# After review, approve or reject
if decision == 'approve':
    ProgramEnrollmentService.approve_at_level(
        application=application,
        reviewer=request.user,
        notes='Farm verified. Good standing in community.'
    )
elif decision == 'reject':
    ProgramEnrollmentService.reject_at_level(
        application=application,
        reviewer=request.user,
        rejection_reason='failed_verification',
        rejection_notes='Farm location could not be verified'
    )
elif decision == 'changes_needed':
    ProgramEnrollmentService.request_changes(
        application=application,
        reviewer=request.user,
        requested_changes='Please provide clearer farm photos and business registration document'
    )
```

### Example 3: Check Program Statistics

```python
from farms.models import GovernmentProgram
from farms.services.program_enrollment_service import ProgramEnrollmentService

program = GovernmentProgram.objects.get(program_code='YEA-2025-Q1')

stats = ProgramEnrollmentService.get_program_statistics(program)

print(f"Total Applications: {stats['total_applications']}")
print(f"Pending Review: {stats['pending']}")
print(f"Enrolled: {stats['enrolled']}")
print(f"Slots Available: {stats['slots_available']}/{stats['slots_total']}")
print(f"Acceptance Rate: {stats['acceptance_rate']:.1f}%")

# Check if program should close
if stats['slots_available'] <= 0:
    program.status = 'full'
    program.save()
```

## Key Differences: New Farmer vs Existing Farmer

| Aspect | New Farmer (FarmApplication) | Existing Farmer (ProgramEnrollmentApplication) |
|--------|------------------------------|----------------------------------------------|
| **Purpose** | Create new farm account | Join government program |
| **Starting Point** | No account/farm | Has account + farm |
| **Identity** | Ghana Card, personal info | Farm details, operational history |
| **Screening Focus** | Eligibility to farm | Eligibility for program support |
| **Outcome** | User account + Farm created | Farm status updated to government-sponsored |
| **Invitation** | Yes, sent after approval | No, already has account |
| **Extension Officer** | Assigned during screening | Assigned during enrollment |
| **Support Package** | Part of new farm setup | Added to existing farm |

## Benefits of This System

### For Farmers
1. **Easy Application**: Apply directly from dashboard
2. **Transparent Process**: Track application status at each stage
3. **Automated Eligibility**: Instant feedback on eligibility
4. **Priority Scoring**: Urgent cases reviewed faster
5. **Support Access**: Gain access to extension officers, training, subsidies

### For Government
1. **Capacity Management**: Control program enrollment with slot limits
2. **Eligibility Enforcement**: Automated checks ensure criteria met
3. **Audit Trail**: Complete record of all review decisions
4. **Resource Planning**: Track support package allocation
5. **Performance Metrics**: Statistics on acceptance rates, processing times

### For Officers
1. **Queue Management**: Prioritized review queues
2. **SLA Tracking**: Deadlines for each review level
3. **Role-Based Access**: Officers only see applications for their level
4. **Claim System**: Officers claim applications to avoid duplicates
5. **Document Review**: Access to farm photos, business docs

## API Endpoints (To Be Built)

### Public Endpoints
```
POST /api/program-enrollment/submit/
GET  /api/program-enrollment/my-applications/
GET  /api/program-enrollment/application/{id}/
POST /api/program-enrollment/application/{id}/resubmit/
POST /api/program-enrollment/application/{id}/withdraw/
```

### Officer Endpoints
```
GET  /api/program-enrollment/queue/{level}/
POST /api/program-enrollment/application/{id}/claim/
POST /api/program-enrollment/application/{id}/approve/
POST /api/program-enrollment/application/{id}/reject/
POST /api/program-enrollment/application/{id}/request-changes/
```

### Admin Endpoints
```
GET  /api/programs/
POST /api/programs/
GET  /api/programs/{id}/
PUT  /api/programs/{id}/
GET  /api/programs/{id}/statistics/
GET  /api/programs/{id}/applications/
```

## Next Steps

1. ✅ Create database models
2. ✅ Implement screening service
3. ✅ Apply migrations
4. ✅ Write documentation
5. ⏳ Create API endpoints (serializers, viewsets, URLs)
6. ⏳ Build notification system
7. ⏳ Create officer dashboard views
8. ⏳ Build farmer application form UI
9. ⏳ Implement program management admin interface
10. ⏳ Add comprehensive tests
