# Apply-First Registration Workflow

## Overview

Prospective farmers can now **apply online WITHOUT creating an account**. Applications go through screening, and upon approval, farmers receive invitations to create accounts.

## Key Benefits

✅ **Lower barrier to entry** - No account required to apply  
✅ **Better spam prevention** - Applications screened before account creation  
✅ **Farmer-friendly** - Apply anytime from anywhere  
✅ **Officer control** - Officers still review and approve  
✅ **Quality assurance** - 3-tier review ensures legitimacy  

---

## Complete Application Flow

### **Step 1: Public Application Form**

**Who:** Prospective farmer (no account needed)  
**Where:** Public website application page

**Information Required:**
- Personal details (name, DOB, Ghana Card, phone, email)
- Location (constituency, region, district)
- Proposed farm name and location description
- Production plans (layers/broilers, capacity)
- Experience (years in poultry, existing farm?)
- YEA batch (if government program)

**What Happens:**
```python
# Frontend submits application
ApplicationScreeningService.submit_application(
    application_data={
        'application_type': 'government_program',  # or 'independent'
        'first_name': 'Kwame',
        'last_name': 'Mensah',
        'ghana_card_number': 'GHA-123456789-1',
        'primary_phone': '+233244123456',
        'email': 'kwame@example.com',
        'primary_constituency': 'Ayawaso Central',
        'proposed_farm_name': 'Mensah Poultry Farm',
        'primary_production_type': 'Both',
        'planned_bird_capacity': 500,
        'years_in_poultry': 2,
        # ... more fields
    },
    ip_address='192.168.1.1'
)
```

**Backend Actions:**
1. **Rate limit check** - Max 3 applications per IP per day
2. **Spam detection** - Automated scoring (0-100)
3. **Application created** - Assigned unique application number
4. **Priority calculated** - Based on verification, experience, program type
5. **Screening started** - Enters constituency review queue
6. **Auto-assignment** - Assigned to extension officer
7. **Email sent** - "Application received" confirmation

---

### **Step 2: Constituency Review** (7-day SLA)

**Who:** Extension Officer or Constituency Coordinator

**Officer Dashboard Shows:**
- All pending applications in their constituency
- Sorted by priority (government program, verified, experience)
- Application details with spam score
- Documents (if any uploaded)

**Actions Available:**

#### ✅ **Approve**
```python
ApplicationScreeningService.approve_at_level(
    application=application,
    reviewer=extension_officer,
    review_level='constituency',
    notes="Verified location, contacted applicant"
)
```
- Application advances to **Regional Review**
- Regional coordinator notified
- Applicant notified: "Your application has been approved at constituency level"

#### ❌ **Reject**
```python
ApplicationScreeningService.reject_at_level(
    application=application,
    reviewer=extension_officer,
    review_level='constituency',
    reason="Location not suitable for poultry farming"
)
```
- Application marked as **Rejected**
- Applicant notified with reason
- Process ends

#### 📝 **Request Changes**
```python
ApplicationScreeningService.request_changes(
    application=application,
    reviewer=extension_officer,
    review_level='constituency',
    requested_changes="Please provide: 1) Proof of land ownership 2) Valid phone number",
    deadline_days=14
)
```
- Application status: **Changes Requested**
- Applicant has 14 days to update
- Remains at constituency level until updated

---

### **Step 3: Regional Review** (5-day SLA)

**Who:** Regional Coordinator or Regional Admin

**Same process as constituency:**
- Approve → Advances to **National Review**
- Reject → Application rejected
- Request Changes → Applicant updates

---

### **Step 4: National Review** (3-day SLA)

**Who:** National Administrator or System Admin

**Final review before approval:**

#### ✅ **Final Approval**
```python
ApplicationScreeningService.approve_at_level(
    application=application,
    reviewer=national_admin,
    review_level='national',
    notes="Final approval granted"
)
```

**What Happens:**
1. **Invitation created** - Unique invitation code generated
2. **Invitation sent** - Via email AND SMS
3. **Application status** - Changed to **Approved**
4. **30-day validity** - Invitation expires in 30 days

**Email Sent to Applicant:**
```
Subject: Congratulations! Your Farm Application is Approved

Dear Kwame Mensah,

Congratulations! Your farm application (APP-2025-00123) has been approved!

You can now create your account and complete your farm registration.

Your invitation code: AbCdEfGh123456XyZ

Register at: https://pms.example.com/register?invitation=AbCdEfGh123456XyZ

This invitation is valid for 30 days.

Best regards,
Poultry Management System Team
```

**SMS Sent:**
```
Congratulations! Your farm application is approved. 
Code: AbCdEfGh123456XyZ. Valid 30 days.
```

---

### **Step 5: Account Creation**

**Who:** Approved applicant

**Process:**
1. Applicant receives invitation email/SMS
2. Clicks registration link
3. System validates invitation code
4. Applicant creates password
5. Account created automatically

**Backend:**
```python
ApplicationScreeningService.create_account_from_application(
    application=application,
    invitation_code='AbCdEfGh123456XyZ',
    password='secure_password_123'
)
```

**What Gets Created:**

#### **User Account:**
- Email/phone from application
- Password set by applicant
- Role: FARMER
- Linked to application

#### **Farm Profile:**
- All data copied from application
- Registration source: 'government_initiative' or 'self_registered'
- Status: 'Approved' and 'Active'
- **Farm ID generated**: `YEA-REG-AYAW-0001`
- Extension officer assigned (if government program)
- Approval dates preserved

**Applicant notified:**
```
Welcome to the Poultry Management System!

Your account has been created successfully.
Farm ID: YEA-REG-AYAW-0001

You now have full access to:
✓ Farm management tools
✓ Production tracking
✓ Inventory management
✓ Financial records
✓ Extension officer support (government farmers)

Login at: https://pms.example.com/login
```

---

## Two Application Types

### **Government Program (YEA)**
- Goes through full 3-tier review
- Extension officer assigned
- Farm ID format: `YEA-REG-CONST-0001`
- Free marketplace access (government subsidized)
- Extension officer supervision included

### **Independent Farmer**
- Can also use apply-first workflow
- Goes through simplified review (optional)
- Farm ID format: Different (TBD)
- Marketplace access: 14-day trial, then GHS 100/month
- Extension officer optional

---

## Priority Scoring

Applications are reviewed in priority order:

| Factor | Points |
|--------|--------|
| Government program application | +50 |
| Email verified | +25 |
| Phone verified | +25 |
| Low spam score (<20) | +30 |
| Medium spam score (20-50) | +15 |
| 2+ years experience | +10 |
| Existing farm | +10 |
| Days waiting (max 30) | +1 per day |

**Example:**
- Government program: 50
- Email verified: 25
- Phone verified: 25
- Low spam: 30
- Experience: 10
- Waiting 5 days: 5
- **Total: 145 points** → Reviewed first

---

## Spam Prevention

### **Automated Detection:**
- Spam keywords in names/farm names
- Disposable email domains
- Repetitive characters
- Invalid Ghana Card patterns
- Sequential numbers
- Data inconsistencies

### **Manual Review:**
- Officers see spam score (0-100)
- High spam applications flagged
- Officers can reject suspicious applications

### **Rate Limiting:**
- Max 3 applications per IP per day
- Automatic 24-hour block after limit
- Prevents bot attacks

---

## SLA Tracking

| Level | Deadline | Overdue Action |
|-------|----------|----------------|
| Constituency | 7 days | Flagged as overdue |
| Regional | 5 days | Flagged as overdue |
| National | 3 days | Flagged as overdue |

**Total maximum time:** 15 days from submission to approval

Overdue applications:
- Highlighted in officer dashboards
- Managers receive alerts
- Tracked for performance metrics

---

## Queue Management

### **Officers can:**
- View their assigned queue
- Claim applications from pool
- See priority scores
- Filter by status/constituency
- Track SLA deadlines

### **Auto-assignment:**
- Load-balanced to officers with fewest assignments
- Constituency matching for extension officers
- Can be manually reassigned

---

## Audit Trail

Every action recorded:

```python
# Get complete history
actions = application.review_actions.all().order_by('created_at')

for action in actions:
    print(f"{action.created_at}: {action.reviewer.name} {action.action} at {action.review_level}")
```

**Example Output:**
```
2025-11-20 10:30: John Mensah claimed at constituency
2025-11-22 14:45: John Mensah approved at constituency
2025-11-23 09:15: Mary Adjei claimed at regional
2025-11-24 16:20: Mary Adjei approved at regional
2025-11-25 11:00: Peter Asante claimed at national
2025-11-26 13:30: Peter Asante approved at national
```

---

## Database Tables

### **farm_applications**
Main application record with applicant data

### **application_queue**
Queue entries at each review level

### **application_review_actions**
Audit trail of all review actions

---

## API Endpoints (To Be Created)

```
POST   /api/applications/submit/              # Submit new application
GET    /api/applications/{id}/                # Get application details
GET    /api/applications/my-application/      # Check application status (by ghana_card)

# Officer endpoints
GET    /api/applications/queue/               # Get review queue
POST   /api/applications/{id}/claim/          # Claim for review
POST   /api/applications/{id}/approve/        # Approve
POST   /api/applications/{id}/reject/         # Reject
POST   /api/applications/{id}/request-changes/ # Request changes

# Account creation
POST   /api/applications/create-account/      # Create account from invitation
```

---

## Benefits of Apply-First Workflow

### **For Farmers:**
✅ No account required to start
✅ Apply anytime, anywhere
✅ Know application status before investing time
✅ Clear communication throughout process

### **For Officers:**
✅ Review applications before account creation
✅ Better spam/bot prevention
✅ Centralized queue management
✅ Complete audit trail

### **For System:**
✅ Reduces fake accounts
✅ Better data quality
✅ Prevents database pollution
✅ Easier to manage screening workflow

---

## Migration from Old Workflow

**Old:** Officer sends invitation → Farmer registers → Farm created → Screening

**New:** Farmer applies → Screening → Approval → Invitation sent → Account created

**Both workflows supported:**
- Officers can still send direct invitations (existing FarmInvitation model)
- Farmers can submit applications (new FarmApplication model)
- Both lead to same end result: approved farm with account

---

## Next Steps

1. ✅ Models created (FarmApplication, ApplicationQueue, ApplicationReviewAction)
2. ✅ Service implemented (ApplicationScreeningService)
3. ⏳ Create API endpoints for:
   - Public application submission
   - Officer review queue
   - Account creation from invitation
4. ⏳ Create officer dashboard views
5. ⏳ Implement email/SMS notifications
6. ⏳ Create applicant status check page
