# Government Farmer Screening Process

## Overview

Government-sponsored farmers (YEA program participants) go through a **3-tier approval workflow** before gaining full platform access and receiving their Farm ID.

## Screening Workflow

### Three Review Levels

1. **Constituency Level** → Extension Officer/Constituency Coordinator
2. **Regional Level** → Regional Coordinator/Regional Admin  
3. **National Level** → National Administrator

Each level must **approve** the application before it advances to the next level.

---

## Step-by-Step Process

### 1. **Registration & Submission**

**How it starts:**
- Extension officer receives invitation to onboard government farmer
- Officer creates invitation → sends to farmer via email/SMS
- Farmer clicks link → completes registration form
- Farm profile created with `registration_source='government_initiative'`

**Automatic actions:**
```python
# When farm is submitted for screening
GovernmentScreeningService.submit_for_screening(farm)
```

**What happens:**
- Farm status: `'Submitted'`
- Current review level: `'constituency'`
- Queue entry created at constituency level
- Extension officer auto-assigned (from farm.extension_officer)
- SLA deadline set (7 days for constituency review)
- Notifications sent to officer and farmer

---

### 2. **Constituency Level Review** (7-day SLA)

**Reviewer:** Extension Officer or Constituency Coordinator

**Actions available:**
- ✅ **Approve** → Advances to Regional Level
- ❌ **Reject** → Application rejected with reason
- 📝 **Request Changes** → Farmer must update application

**Approval process:**
```python
GovernmentScreeningService.approve_at_level(
    farm=farm,
    reviewer=extension_officer,
    review_level='constituency',
    notes="Verified farm location, infrastructure looks good"
)
```

**What happens on approval:**
- Farm status: `'Regional Review'`
- Current review level: `'regional'`
- Queue entry created at regional level
- Regional coordinator auto-assigned
- SLA deadline: 5 days
- Farmer notified: "Approved at constituency level, forwarded to regional"

**What happens on rejection:**
- Farm status: `'Rejected'`
- Rejection reason stored
- Farmer notified with reason
- Process ends

**What happens on request changes:**
- Farm status: `'Changes Requested'`
- Farmer has 14 days to update
- Farmer notified with specific changes needed
- Application remains at constituency level until updated

---

### 3. **Regional Level Review** (5-day SLA)

**Reviewer:** Regional Coordinator or Regional Admin

**Same actions as constituency level:**
- ✅ Approve → Advances to National Level
- ❌ Reject → Application rejected
- 📝 Request Changes → Farmer updates

**Approval process:**
```python
GovernmentScreeningService.approve_at_level(
    farm=farm,
    reviewer=regional_coordinator,
    review_level='regional',
    notes="Regional requirements met"
)
```

**What happens on approval:**
- Farm status: `'National Review'`
- Current review level: `'national'`
- Queue entry created at national level
- National admin auto-assigned
- SLA deadline: 3 days
- Farmer notified: "Approved at regional level, forwarded to national"

---

### 4. **National Level Review** (3-day SLA)

**Reviewer:** National Administrator or System Admin

**Final review before activation:**
- ✅ Approve → **FARM ACTIVATED** 🎉
- ❌ Reject → Application rejected
- 📝 Request Changes → Farmer updates

**Final approval process:**
```python
GovernmentScreeningService.approve_at_level(
    farm=farm,
    reviewer=national_admin,
    review_level='national',
    notes="Final approval granted"
)
```

**What happens on FINAL approval:**
- Farm status: `'Approved'`
- Farm status field: `'Active'`
- **Farm ID generated**: `YEA-REG-CONST-0001`
- Approval timestamp recorded
- Current review level: `None` (completed)
- Farmer gains **full platform access**
- Farmer notified: "Congratulations! Farm approved. Farm ID: YEA-REG-CONST-0001"

---

## Queue Management

### Officers can view their queue:

```python
# Get my assigned applications
queue = GovernmentScreeningService.get_review_queue(
    review_level='constituency',
    officer=extension_officer,
    status='pending'
)
```

### Officers can claim applications:

```python
# Claim an application for review
GovernmentScreeningService.claim_for_review(
    queue_item=queue_item,
    officer=extension_officer
)
```

**Queue statuses:**
- `'pending'` - Waiting to be claimed
- `'claimed'` - Officer claimed it
- `'in_progress'` - Under active review
- `'completed'` - Review finished

---

## Priority Scoring

Applications are ordered by priority score (higher = reviewed first):

**Priority factors:**
- YEA program farmer: **+50 points**
- Complete documentation (5+ docs): **+30 points**
- Has TIN: **+10 points**
- Has business registration: **+10 points**

---

## SLA (Service Level Agreement) Tracking

Each level has a deadline:
- **Constituency:** 7 days
- **Regional:** 5 days  
- **National:** 3 days

**Total time:** Up to 15 days from submission to final approval

**Overdue applications:**
```python
# Get applications past deadline
overdue = GovernmentScreeningService.get_overdue_reviews(
    review_level='constituency'
)
```

Overdue applications are flagged with `is_overdue=True` for manager visibility.

---

## Audit Trail

Every action is recorded in `FarmReviewAction`:

- Who reviewed
- What action (approved/rejected/request_changes)
- When it happened
- Notes/comments
- Requested changes (if any)

**Complete audit trail:**
```python
# Get all review actions for a farm
actions = farm.review_actions.all().order_by('created_at')

for action in actions:
    print(f"{action.created_at}: {action.reviewer.name} {action.action} at {action.review_level}")
```

---

## Notifications

Farmers receive notifications at each stage:

| Event | Channel | Message |
|-------|---------|---------|
| Submitted | In-app | "Application submitted for constituency review" |
| Approved (Constituency) | In-app | "Approved at constituency, forwarded to regional" |
| Approved (Regional) | In-app | "Approved at regional, forwarded to national" |
| **Final Approval** | In-app + SMS + Email | "Congratulations! Farm ID: XXX" |
| Changes Requested | In-app + Email | "Additional information required..." |
| Rejected | In-app + Email | "Application rejected. Reason: ..." |

Officers also receive notifications:
- New application assigned
- Application forwarded to their level
- SLA deadline approaching

---

## Farm ID Generation

Upon final approval, a unique Farm ID is generated:

**Format:** `YEA-REG-{CONSTITUENCY}-{NUMBER}`

**Example:** `YEA-REG-AYAW-0001`

- `YEA` - Youth Employment Agency
- `REG` - Registered
- `AYAW` - Constituency abbreviation (Ayawaso Central → AYAW)
- `0001` - Sequential number within constituency

---

## Role Permissions

| Review Level | Allowed Roles |
|-------------|---------------|
| Constituency | Extension Officer, Constituency Coordinator |
| Regional | Regional Coordinator, Regional Admin |
| National | National Admin, System Admin |

**Permission validation:**
```python
# Validates reviewer has appropriate role
_validate_reviewer_role(user, review_level)
```

---

## Auto-Assignment

Applications are automatically assigned to officers:

1. **Constituency level:** Assigned to extension officer linked to farm
2. **Regional level:** Load-balanced to regional coordinator with fewest assignments
3. **National level:** Load-balanced to national admin with fewest assignments

**Manual reassignment also supported.**

---

## Example: Complete Screening Flow

```python
# 1. Officer submits farm for screening
success, message, queue = GovernmentScreeningService.submit_for_screening(farm)
# Farm status: 'Submitted', Level: 'constituency'

# 2. Extension officer approves
success, msg, next_level = GovernmentScreeningService.approve_at_level(
    farm, extension_officer, 'constituency', "Looks good"
)
# Farm status: 'Regional Review', Level: 'regional'

# 3. Regional coordinator approves
success, msg, next_level = GovernmentScreeningService.approve_at_level(
    farm, regional_coordinator, 'regional', "Approved"
)
# Farm status: 'National Review', Level: 'national'

# 4. National admin gives final approval
success, msg, next_level = GovernmentScreeningService.approve_at_level(
    farm, national_admin, 'national', "Final approval"
)
# Farm status: 'Approved', Farm ID: 'YEA-REG-AYAW-0001', Active!
```

---

## Database Tables Involved

1. **farms** - Main farm record with status fields
2. **farm_approval_queue** - Queue entries at each level
3. **farm_review_actions** - Audit trail of all actions
4. **farm_notifications** - Notifications sent to users

---

## Benefits of 3-Tier System

✅ **Quality Control** - Multiple checkpoints ensure only legitimate farms approved  
✅ **Regional Oversight** - Regional coordinators validate constituency decisions  
✅ **National Standards** - Final review ensures consistency across all regions  
✅ **Audit Trail** - Complete record of who approved what and when  
✅ **Accountability** - Each level responsible for their review  
✅ **Fraud Prevention** - Harder to approve fraudulent applications  

---

## Independent Farmers: No Screening

**Important:** Independent (self-registered) farmers **skip this entire process**.

They get:
- Automatic approval (no 3-tier review)
- Instant platform access
- Different Farm ID format

Only government-sponsored farmers go through screening.
