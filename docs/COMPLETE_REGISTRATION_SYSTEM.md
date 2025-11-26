# Complete Farmer Registration & Enrollment System

## Overview

The PMS platform now supports **THREE distinct pathways** for farmers to join and access government programs:

1. **New Farmers Starting Fresh** → `FarmApplication` workflow
2. **Independent Farmers Joining YEA** → `ProgramEnrollmentApplication` workflow  
3. **Officer-Initiated Invitations** → `FarmInvitation` workflow

## The Three Pathways

### Pathway 1: New Farmer (Apply-First Workflow)

**Use Case:** Prospective farmer with no account wants to start a farm through YEA or independently.

**Process:**
```
Application → Screening → Approval → Invitation → Account Creation → Farm Active
```

**Key Points:**
- No account required to apply
- Applicant provides personal info (Ghana Card, DOB, phone, email)
- Proposes farm name and production plans
- Goes through 3-tier screening (constituency → regional → national)
- Upon approval, invitation sent via email/SMS
- Farmer creates account using invitation link
- Farm profile automatically created

**Models Used:**
- `FarmApplication`: Anonymous application
- `ApplicationQueue`: Queue management
- `ApplicationReviewAction`: Audit trail
- `FarmInvitation`: Invitation sent after approval
- `Farm`: Created from approved application

**Service:**
- `ApplicationScreeningService`

**Documentation:**
- `docs/APPLY_FIRST_WORKFLOW.md`

---

### Pathway 2: Existing Farmer (Program Enrollment)

**Use Case:** Farmer already has account and farm, wants to join government program (YEA).

**Process:**
```
Enrollment Application → Eligibility Check → Screening → Approval → Farm Status Updated
```

**Key Points:**
- Farmer already has User account + Farm
- Applies to specific government program (e.g., YEA-2025-Q1)
- Automated eligibility check (age, capacity, location, documentation)
- Goes through 3-tier screening if eligible
- Upon approval, farm converted to government-sponsored
- Extension officer assigned
- Support package allocated
- No invitation needed (already has account)

**Models Used:**
- `GovernmentProgram`: Available programs
- `ProgramEnrollmentApplication`: Application to join program
- `ProgramEnrollmentQueue`: Queue management
- `ProgramEnrollmentReview`: Audit trail
- `Farm`: Updated to government-sponsored status

**Service:**
- `ProgramEnrollmentService`

**Documentation:**
- `docs/PROGRAM_ENROLLMENT_FOR_EXISTING_FARMERS.md`

---

### Pathway 3: Officer Invitation

**Use Case:** Extension/constituency officer directly invites farmer to join platform.

**Process:**
```
Officer Creates Invitation → Email/SMS Sent → Farmer Registers → Farm Created
```

**Key Points:**
- Officer-initiated (trusted source)
- Can be single-use or multi-use invitation
- Includes invitation code
- Expires after set period
- Farmer registers using invitation link
- Government farmers go through screening
- Independent farmers get instant access

**Models Used:**
- `FarmInvitation`: Invitation issued by officer
- `Farm`: Created after registration

**Service:**
- `InvitationService`

**Documentation:**
- Covered in `docs/APPLY_FIRST_WORKFLOW.md` (hybrid section)

---

## Comparison Matrix

| Aspect | New Farmer | Existing Farmer | Officer Invitation |
|--------|-----------|----------------|-------------------|
| **Starting Point** | No account | Has account + farm | No account |
| **Initiated By** | Prospective farmer | Existing farmer | Officer |
| **Authentication** | Not required initially | Required | Not required initially |
| **Main Model** | FarmApplication | ProgramEnrollmentApplication | FarmInvitation |
| **Screening** | 3-tier (const→reg→nat) | 3-tier (const→reg→nat) | Optional (govt only) |
| **Eligibility Check** | Manual (during screening) | Automated + manual | Trusted (officer vouches) |
| **Outcome** | New account + farm | Farm status updated | New account + farm |
| **Invitation** | Yes (after approval) | No (already has account) | Yes (invitation IS the entry) |
| **Extension Officer** | Assigned during screening | Assigned during enrollment | Specified in invitation |
| **Priority** | Medium | Based on need | High (trusted source) |
| **Spam Risk** | Medium (public form) | Low (verified farmer) | Very Low (officer-vetted) |

---

## Complete Database Schema

### Registration & Invitations
```
FarmInvitation
├── invitation_code (unique)
├── issued_by (officer FK)
├── constituency
├── recipient (email/phone/name)
├── is_single_use
├── expires_at
└── status

RegistrationApproval
├── user (OneToOne)
├── spam_score
├── email_verified
├── phone_verified
├── status
└── assigned_to (officer FK)

VerificationToken
├── user (FK)
├── token_type (email/phone)
├── code (6 digits)
├── expires_at
└── verify() method

RegistrationRateLimit
├── ip_address
├── attempts_count
├── window_start
└── blocked_until
```

### New Farmer Applications
```
FarmApplication
├── application_number
├── application_type (government/independent)
├── personal_info (name, DOB, ghana_card, phone, email)
├── primary_constituency
├── proposed_farm_name
├── production_plans
├── status (submitted → screening → approved)
├── current_review_level
├── spam_score / spam_flags
├── invitation (FK) - sent after approval
├── user_account (FK) - created post-approval
└── farm_profile (FK) - created from application

ApplicationQueue
├── application (FK)
├── review_level
├── status
├── assigned_to (officer FK)
├── priority
└── sla_deadline

ApplicationReviewAction
├── application (FK)
├── reviewer (FK)
├── review_level
├── action
├── notes
└── timestamp
```

### Program Enrollment (Existing Farmers)
```
GovernmentProgram
├── program_name
├── program_code
├── program_type
├── implementing_agency
├── start_date / end_date
├── application_deadline
├── eligibility_criteria (age, capacity, location)
├── support_package_details (JSON)
├── total_slots / slots_filled / slots_available
└── status (active/full/inactive)

ProgramEnrollmentApplication
├── application_number
├── farm (FK) - existing farm
├── program (FK)
├── applicant (FK) - farm owner
├── motivation / current_challenges / expected_benefits
├── current_farm_status (birds, revenue, years_operational)
├── farm_photos / business_documents
├── eligibility_score / eligibility_flags / meets_eligibility
├── status (submitted → screening → enrolled)
├── current_review_level
├── priority_score
├── assigned_extension_officer (FK)
└── support_package_allocated (JSON)

ProgramEnrollmentQueue
├── application (FK)
├── review_level
├── status
├── assigned_to (officer FK)
├── priority
└── sla_deadline

ProgramEnrollmentReview
├── application (FK)
├── reviewer (FK)
├── review_level
├── action
├── notes
└── timestamp
```

### Farm Model (Central)
```
Farm
├── farmer (FK to User)
├── farm_id (YEA-REG-CONST-0001)
├── farm_name
├── primary_constituency (UNIVERSAL requirement)
├── registration_source (government_initiative / self_registered)
├── yea_program_batch (e.g., 'YEA-2025-Q1')
├── yea_program_start_date / yea_program_end_date
├── extension_officer (FK to User) - required govt, optional independent
├── government_support_package (JSON)
└── approval_workflow (government_screening / auto_approve)
```

---

## Workflow Logic Summary

### New Farmer Journey

```
┌─────────────────────┐
│ Farmer visits site  │
│ (no account)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Fill FarmApplication│
│ - Personal details  │
│ - Farm plans        │
│ - Ghana Card        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Spam Detection      │
│ - Rate limiting     │
│ - Spam scoring      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3-Tier Screening    │
│ Constituency → 7d   │
│ Regional → 5d       │
│ National → 3d       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Approval            │
│ - Generate Farm ID  │
│ - Send Invitation   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Farmer Clicks Link  │
│ - Create account    │
│ - Farm profile      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Farm Active!        │
└─────────────────────┘
```

### Existing Farmer Joining YEA

```
┌─────────────────────┐
│ Farmer logs in      │
│ (has account+farm)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Browse Programs     │
│ - YEA-2025-Q1       │
│ - Infrastructure    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Submit Enrollment   │
│ Application         │
│ - Motivation        │
│ - Current status    │
│ - Documents         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Eligibility Check   │
│ (Automated)         │
│ - Age ✓             │
│ - Capacity ✓        │
│ - Location ✓        │
│ - Docs ✓            │
└──────────┬──────────┘
           │
           ├─[FAIL]──► Rejected
           │
           ▼[PASS]
┌─────────────────────┐
│ 3-Tier Screening    │
│ Constituency → 7d   │
│ Regional → 5d       │
│ National → 3d       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Enrollment Complete │
│ Farm updated:       │
│ - Source=govt       │
│ - Extension officer │
│ - Support package   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Access YEA Benefits │
│ - Training          │
│ - Subsidies         │
│ - Extension support │
└─────────────────────┘
```

### Officer Invitation

```
┌─────────────────────┐
│ Officer dashboard   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Create Invitation   │
│ - Email/phone       │
│ - Constituency      │
│ - Farmer type       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Email/SMS Sent      │
│ with link + code    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Farmer Registers    │
│ - Uses invitation   │
│ - Validates code    │
└──────────┬──────────┘
           │
           ├─[Govt]──► Screening
           │
           ▼[Independent]
┌─────────────────────┐
│ Auto-Approved!      │
└─────────────────────┘
```

---

## Integration Points

### 1. Dashboard Views

**Farmer Dashboard:**
- If `registration_source == 'self_registered'`:
  - Show "Join Government Program" button
  - List available programs
  - Show "Apply Now" for eligible programs

- If `registration_source == 'government_initiative'`:
  - Show program details (batch, start date, end date)
  - Show extension officer contact
  - Show support package details
  - Track support package delivery

**Officer Dashboard:**
- **Constituency Officer:**
  - Review new farmer applications (FarmApplication)
  - Review program enrollment applications (ProgramEnrollmentApplication)
  - Create invitations (FarmInvitation)
  - Manage verification tokens

- **Extension Officer:**
  - View assigned farmers
  - Schedule farm visits
  - Log support package distribution
  - Submit progress reports

### 2. Notification System

**Events to Notify:**

For New Farmer Applications:
- Application received
- Constituency approved
- Regional approved
- Final approval (with invitation link)
- Changes requested
- Rejected

For Program Enrollment:
- Application received
- Eligibility check passed/failed
- Constituency approved
- Regional approved
- Enrollment completed (with program details)
- Changes requested
- Rejected

For Invitations:
- Invitation sent
- Invitation used
- Invitation expired

### 3. Admin Interface

**Program Management:**
- CRUD operations for GovernmentProgram
- Set eligibility criteria
- Manage capacity (slots)
- View statistics (applications, enrollment, acceptance rate)
- Close/open applications

**Queue Monitoring:**
- View pending applications by level
- Track SLA compliance
- Identify overdue reviews
- Reassign applications

**Reporting:**
- Enrollment trends
- Acceptance rates by constituency
- Processing times by level
- Support package allocation

---

## Key Business Rules

### For New Farmers

1. **Universal Constituency Requirement**
   - ALL farmers must register with constituency
   - Government and independent farmers

2. **Extension Officer Assignment**
   - Government farmers: REQUIRED
   - Independent farmers: OPTIONAL (but recommended)

3. **Approval Workflow**
   - Government farmers: 3-tier screening
   - Independent farmers: AUTO-APPROVE (instant access)

4. **Support Package**
   - Government farmers: Allocated during enrollment
   - Independent farmers: None (pay for marketplace if desired)

### For Existing Farmers Joining Programs

1. **Eligibility Enforcement**
   - Automated checks before screening
   - Must score ≥50 to proceed
   - Failed eligibility = auto-reject

2. **One Application Per Program**
   - Unique constraint: (farm, program)
   - Cannot apply to same program twice
   - Can apply to different programs

3. **Program Capacity**
   - Programs have slot limits
   - Auto-close when full
   - Priority queue for fairness

4. **Farm Status Update**
   - Upon enrollment, farm becomes government-sponsored
   - `registration_source` changed to 'government_initiative'
   - Extension officer assigned if not already assigned

### For All Pathways

1. **Spam Prevention**
   - Rate limiting: 3 applications per IP per day
   - Spam detection scoring
   - Email/phone verification
   - Officer approval for self-registrations

2. **SLA Tracking**
   - Constituency: 7 days
   - Regional: 5 days
   - National: 3 days
   - Escalation for overdue reviews

3. **Audit Trail**
   - Every action logged with reviewer + timestamp
   - Complete review history
   - Notes for transparency

4. **Priority Scoring**
   - Older applications = higher priority
   - Urgent cases (deadline approaching) = higher priority
   - Smaller farms = higher priority (for support programs)

---

## What's Next?

### Immediate Priorities

1. **API Endpoints** - Build REST APIs for all three workflows
2. **Notification System** - Email/SMS at each stage
3. **Officer Dashboards** - Review queues, claim system, approve/reject
4. **Farmer UI** - Application forms, status tracking, program browsing

### Future Enhancements

1. **Document Upload** - S3/cloud storage integration for photos and documents
2. **Payment Integration** - For marketplace subscriptions (Paystack/Flutterwave)
3. **Extension Officer Tools** - Farm visit scheduling, training tracking, reporting
4. **Analytics Dashboard** - Program performance, enrollment trends, farmer progress
5. **Mobile App** - Native iOS/Android for farmers and officers

---

## Files Created

### Models
- `farms/invitation_models.py` - FarmInvitation, RegistrationApproval, VerificationToken, RegistrationRateLimit
- `farms/application_models.py` - FarmApplication, ApplicationQueue, ApplicationReviewAction
- `farms/program_enrollment_models.py` - GovernmentProgram, ProgramEnrollmentApplication, ProgramEnrollmentQueue, ProgramEnrollmentReview

### Services
- `farms/services/spam_detection.py` - SpamDetectionService, RateLimitService, VerificationService
- `farms/services/invitation_service.py` - InvitationService
- `farms/services/registration_approval.py` - RegistrationApprovalService
- `farms/services/government_screening.py` - GovernmentScreeningService
- `farms/services/application_screening.py` - ApplicationScreeningService
- `farms/services/program_enrollment_service.py` - ProgramEnrollmentService

### Documentation
- `docs/GOVERNMENT_SCREENING_PROCESS.md` - Government farmer screening workflow
- `docs/APPLY_FIRST_WORKFLOW.md` - Anonymous application workflow
- `docs/PROGRAM_ENROLLMENT_FOR_EXISTING_FARMERS.md` - Existing farmer program enrollment

### Migrations
- `0005` - Universal constituency, extension officer updates
- `0006` - Invitation and spam prevention models
- `0007` - FarmApplication models
- `0008` - Program enrollment models

---

## Summary

The system now provides **complete flexibility** for farmers to join the platform and access government programs:

- **New farmers** can apply online without accounts
- **Existing farmers** can join government programs anytime
- **Officers** can directly invite trusted farmers
- **All pathways** include spam prevention and quality control
- **Government programs** have automated eligibility checks
- **Capacity management** prevents program overload
- **Audit trails** ensure transparency
- **Priority queues** ensure fairness

This creates a **user-friendly, secure, and scalable** farmer onboarding and program enrollment system.
