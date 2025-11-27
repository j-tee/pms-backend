# Frontend Development Guide - Expression of Interest (Farm Application)

## Overview

This guide covers the **Expression of Interest (EOI)** workflow where prospective farmers can apply to start a farm without creating an account first. This is the **primary entry point** for new farmers.

**Flow:** Application → Screening → Approval → Invitation → Account Creation → Farm Active

## Priority: Start Here 🎯

The EOI/Farm Application workflow should be the **first feature** frontend developers implement because:

1. **Public-facing**: No authentication required to start
2. **User acquisition**: Primary way to onboard new farmers
3. **Self-contained**: Complete workflow from application to approval
4. **Business critical**: Core to YEA program and platform growth

## User Journey

```
┌─────────────────────────┐
│ 1. Prospective Farmer   │
│    Visits Platform      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 2. Fills Application    │
│    Form (No Login)      │
│    - Personal Info      │
│    - Farm Plans         │
│    - Ghana Card         │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 3. Submit Application   │
│    - Spam Check         │
│    - Rate Limiting      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 4. Track Status         │
│    (via Ghana Card)     │
│    - Submitted          │
│    - Under Review       │
│    - Approved/Rejected  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 5. Receive Invitation   │
│    (Email/SMS)          │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 6. Create Account       │
│    using Invitation     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 7. Farm Active!         │
│    Start Managing       │
└─────────────────────────┘
```

## API Endpoints

### Base URL
```
Development: http://localhost:8000/api
Production: https://api.pms.gov.gh/api
```

### Authentication
Most EOI endpoints are **public** (no authentication required). Only status tracking requires authentication.

---

## 1. Submit Farm Application

**Public endpoint** - No authentication required

### Endpoint
```
POST /api/applications/submit/
```

### Request Headers
```http
Content-Type: application/json
```

### Request Body

```json
{
  "application_type": "government_program",
  
  "personal_information": {
    "first_name": "Kwame",
    "middle_name": "Mensah",
    "last_name": "Asante",
    "date_of_birth": "1995-03-15",
    "gender": "Male",
    "ghana_card_number": "GHA-123456789-0",
    "primary_phone": "+233244567890",
    "alternate_phone": "+233201234567",
    "email": "kwame.asante@example.com",
    "residential_address": "House No. 45, Community 8, Tema"
  },
  
  "location": {
    "primary_constituency": "Tema East",
    "region": "Greater Accra",
    "district": "Tema Metropolitan"
  },
  
  "farm_information": {
    "proposed_farm_name": "Asante Poultry Farm",
    "farm_location_description": "Located near Afienya junction, off Tema-Akosombo road. Close to Afienya Market.",
    "land_size_acres": "2.5",
    "primary_production_type": "Both",
    "planned_bird_capacity": 500,
    "years_in_poultry": "1.5",
    "has_existing_farm": false
  },
  
  "government_program": {
    "yea_program_batch": "YEA-2025-Q1",
    "referral_source": "Social media advertisement"
  }
}
```

### Field Descriptions

#### application_type (required)
- **Type:** String
- **Options:** `"government_program"` or `"independent"`
- **Description:** Whether applying for government program or as independent farmer

#### personal_information (required)

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| first_name | string | Yes | Max 100 chars | First name |
| middle_name | string | No | Max 100 chars | Middle name |
| last_name | string | Yes | Max 100 chars | Last name |
| date_of_birth | date | Yes | Format: YYYY-MM-DD | Birth date (age 18-65) |
| gender | string | Yes | Male/Female/Other | Gender |
| ghana_card_number | string | Yes | Format: GHA-XXXXXXXXX-X | Ghana Card number |
| primary_phone | string | Yes | Format: +233XXXXXXXXX | Primary phone (Ghana) |
| alternate_phone | string | No | Format: +233XXXXXXXXX | Alternate phone |
| email | string | No | Valid email | Email for notifications |
| residential_address | text | Yes | - | Full residential address |

#### location (required)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| primary_constituency | string | Yes | Constituency where farm will be located |
| region | string | No | Region (auto-filled from constituency) |
| district | string | No | District (auto-filled from constituency) |

#### farm_information (required)

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| proposed_farm_name | string | Yes | Max 200 chars | Proposed farm name |
| farm_location_description | text | Yes | - | Describe farm location with landmarks |
| land_size_acres | decimal | Yes | > 0 | Land size in acres |
| primary_production_type | string | Yes | Layers/Broilers/Both | Production focus |
| planned_bird_capacity | integer | Yes | >= 1 | How many birds planned |
| years_in_poultry | decimal | Yes | 0-50 | Years of experience |
| has_existing_farm | boolean | Yes | true/false | Already have operational farm? |

#### government_program (conditional)
Required only if `application_type === "government_program"`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| yea_program_batch | string | Yes (if govt) | YEA batch/cohort |
| referral_source | string | No | How heard about program |

### Response (Success)

**Status Code:** `201 Created`

```json
{
  "success": true,
  "application_number": "APP-2025-00123",
  "status": "submitted",
  "message": "Application submitted successfully",
  "spam_score": 5,
  "current_review_level": "constituency",
  "tracking": {
    "track_url": "/api/applications/track/GHA-123456789-0/",
    "sms_notification": "Verification code sent to +233244567890"
  },
  "next_steps": [
    "Your application has been submitted and assigned number APP-2025-00123",
    "You will receive SMS/Email updates as your application progresses",
    "Constituency review will be completed within 7 days",
    "Track your application status using your Ghana Card number"
  ],
  "estimated_timeline": {
    "constituency_review": "7 days",
    "regional_review": "5 days",
    "national_review": "3 days",
    "total_estimated_days": "15 days"
  }
}
```

### Response (Validation Error)

**Status Code:** `400 Bad Request`

```json
{
  "success": false,
  "error": "Validation failed",
  "errors": {
    "ghana_card_number": [
      "Ghana Card number already registered. Use APP-2025-00015 to track your application."
    ],
    "date_of_birth": [
      "Farmer must be between 18 and 65 years old. Current age: 17"
    ],
    "primary_phone": [
      "Enter a valid phone number in format +233XXXXXXXXX"
    ]
  }
}
```

### Response (Rate Limited)

**Status Code:** `429 Too Many Requests`

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "message": "Maximum 3 applications per IP address per day",
  "retry_after": "23:45:30",
  "retry_after_seconds": 85530
}
```

### Response (High Spam Score)

**Status Code:** `400 Bad Request`

```json
{
  "success": false,
  "error": "Application flagged for review",
  "message": "Your application requires manual verification",
  "spam_score": 85,
  "spam_flags": [
    "Disposable email domain detected",
    "Invalid Ghana Card format",
    "Farm name contains suspicious keywords"
  ],
  "next_steps": [
    "Contact your constituency office for assistance",
    "Phone: +233-XXX-XXXX",
    "Email: tema.east@mofa.gov.gh"
  ]
}
```

---

## 2. Track Application Status

**Public endpoint** - No authentication required

### Endpoint
```
GET /api/applications/track/{ghana_card_number}/
```

### Path Parameters
- `ghana_card_number`: Ghana Card number used in application (URL encoded)

### Example
```
GET /api/applications/track/GHA-123456789-0/
```

### Request Headers
```http
Content-Type: application/json
```

### Response (Success)

**Status Code:** `200 OK`

```json
{
  "success": true,
  "application": {
    "application_number": "APP-2025-00123",
    "application_type": "government_program",
    "status": "constituency_review",
    "current_review_level": "constituency",
    
    "applicant": {
      "name": "Kwame Mensah Asante",
      "phone": "+233244567890",
      "email": "kwame.asante@example.com"
    },
    
    "farm": {
      "proposed_name": "Asante Poultry Farm",
      "constituency": "Tema East",
      "production_type": "Both",
      "planned_capacity": 500
    },
    
    "timeline": {
      "submitted_at": "2025-11-20T10:30:00Z",
      "constituency_reviewed_at": null,
      "regional_reviewed_at": null,
      "national_reviewed_at": null,
      "final_decision_at": null,
      "days_in_review": 6
    },
    
    "progress": {
      "percentage": 25,
      "current_stage": "Constituency Review",
      "completed_stages": ["Submitted", "Eligibility Check"],
      "pending_stages": ["Constituency Review", "Regional Review", "National Review"],
      "sla_deadline": "2025-11-27T10:30:00Z",
      "days_remaining": 1,
      "is_overdue": false
    },
    
    "priority_score": 65,
    "eligibility_score": 95,
    
    "history": [
      {
        "date": "2025-11-20T10:30:00Z",
        "action": "Application Submitted",
        "level": "System",
        "notes": "Application received and entered screening workflow"
      },
      {
        "date": "2025-11-20T10:31:00Z",
        "action": "Eligibility Check Passed",
        "level": "System",
        "notes": "Eligibility score: 95/100. All checks passed."
      },
      {
        "date": "2025-11-20T10:32:00Z",
        "action": "Assigned to Constituency Review",
        "level": "Constituency",
        "notes": "Application queued for constituency officer review"
      }
    ],
    
    "next_steps": [
      "Your application is currently under constituency review",
      "Expected completion: November 27, 2025",
      "You will be notified via SMS/Email when review is complete",
      "Contact your constituency office for urgent matters"
    ]
  }
}
```

### Response (Not Found)

**Status Code:** `404 Not Found`

```json
{
  "success": false,
  "error": "Application not found",
  "message": "No application found for Ghana Card number GHA-123456789-0",
  "help": {
    "check_ghana_card": "Verify you entered the correct Ghana Card number",
    "format": "Format should be GHA-XXXXXXXXX-X",
    "contact": "Contact support if you need assistance"
  }
}
```

---

## 3. Get Available Constituencies

**Public endpoint** - Helper for form dropdowns

### Endpoint
```
GET /api/constituencies/
```

### Query Parameters
- `region` (optional): Filter by region
- `search` (optional): Search constituencies by name

### Example
```
GET /api/constituencies/?region=Greater%20Accra
```

### Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "count": 34,
  "results": [
    {
      "name": "Tema East",
      "region": "Greater Accra",
      "district": "Tema Metropolitan",
      "code": "GAR-TEMA-EAST",
      "contact": {
        "phone": "+233-XXX-XXXX",
        "email": "tema.east@mofa.gov.gh",
        "office_address": "Ministry of Food and Agriculture, Tema"
      }
    },
    {
      "name": "Tema West",
      "region": "Greater Accra",
      "district": "Tema Metropolitan",
      "code": "GAR-TEMA-WEST",
      "contact": {
        "phone": "+233-XXX-XXXX",
        "email": "tema.west@mofa.gov.gh",
        "office_address": "Community 1, Tema"
      }
    }
  ]
}
```

---

## 4. Verify Ghana Card

**Public endpoint** - Validate Ghana Card before submission

### Endpoint
```
POST /api/applications/verify-ghana-card/
```

### Request Body

```json
{
  "ghana_card_number": "GHA-123456789-0"
}
```

### Response (Valid & Available)

**Status Code:** `200 OK`

```json
{
  "success": true,
  "valid": true,
  "available": true,
  "message": "Ghana Card number is valid and available for use"
}
```

### Response (Valid but Already Used)

**Status Code:** `200 OK`

```json
{
  "success": true,
  "valid": true,
  "available": false,
  "message": "Ghana Card number already registered",
  "existing_application": {
    "application_number": "APP-2025-00015",
    "status": "constituency_review",
    "submitted_at": "2025-11-15T08:00:00Z",
    "track_url": "/api/applications/track/GHA-123456789-0/"
  }
}
```

### Response (Invalid Format)

**Status Code:** `400 Bad Request`

```json
{
  "success": false,
  "valid": false,
  "message": "Invalid Ghana Card format",
  "error": "GHA-123456 is not a valid Ghana Card number. Format: GHA-XXXXXXXXX-X"
}
```

---

## 5. Get Application Statistics (Public)

**Public endpoint** - Show platform statistics to build trust

### Endpoint
```
GET /api/applications/statistics/
```

### Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "statistics": {
    "total_applications": 5420,
    "applications_approved": 4103,
    "applications_pending": 982,
    "applications_rejected": 335,
    "approval_rate": 75.7,
    "average_processing_days": 14,
    "farmers_active": 4050,
    
    "by_constituency": {
      "top_5": [
        {"name": "Tema East", "count": 234},
        {"name": "Accra Central", "count": 198},
        {"name": "Kumasi South", "count": 176},
        {"name": "Takoradi", "count": 165},
        {"name": "Tamale Central", "count": 143}
      ]
    },
    
    "by_production_type": {
      "Layers": 2145,
      "Broilers": 1876,
      "Both": 1399
    },
    
    "recent_approvals": 142,
    "last_updated": "2025-11-26T12:00:00Z"
  }
}
```

---

## Status Flow & Values

### Application Status Values

| Status | Description | User Message |
|--------|-------------|--------------|
| `submitted` | Application received | Your application has been submitted successfully |
| `constituency_review` | Under constituency review | Being reviewed by constituency officer |
| `regional_review` | Under regional review | Being reviewed by regional officer |
| `national_review` | Under national review | Being reviewed by national officer |
| `changes_requested` | Changes needed | Officer has requested changes to your application |
| `approved` | Approved, invitation sent | Congratulations! Your application has been approved |
| `rejected` | Application rejected | Unfortunately, your application was not approved |
| `account_created` | Account created | Account successfully created. Welcome aboard! |

### Review Level Values

| Level | SLA (Days) | Role Required |
|-------|-----------|---------------|
| `constituency` | 7 | Constituency Officer |
| `regional` | 5 | Regional Officer |
| `national` | 3 | National Officer |

---

## Frontend Implementation Guide

### 1. Application Form Component

**Recommended Tech Stack:**
- React with TypeScript / Next.js
- Form Library: React Hook Form or Formik
- Validation: Yup or Zod
- HTTP Client: Axios or Fetch API
- State Management: Context API or Zustand

**Form Structure:**

```typescript
interface FarmApplicationForm {
  application_type: 'government_program' | 'independent';
  
  personal_information: {
    first_name: string;
    middle_name?: string;
    last_name: string;
    date_of_birth: string; // YYYY-MM-DD
    gender: 'Male' | 'Female' | 'Other';
    ghana_card_number: string;
    primary_phone: string;
    alternate_phone?: string;
    email?: string;
    residential_address: string;
  };
  
  location: {
    primary_constituency: string;
    region?: string;
    district?: string;
  };
  
  farm_information: {
    proposed_farm_name: string;
    farm_location_description: string;
    land_size_acres: number;
    primary_production_type: 'Layers' | 'Broilers' | 'Both';
    planned_bird_capacity: number;
    years_in_poultry: number;
    has_existing_farm: boolean;
  };
  
  government_program?: {
    yea_program_batch: string;
    referral_source: string;
  };
}
```

**Multi-Step Form Flow:**

```
Step 1: Application Type
  → Government Program or Independent

Step 2: Personal Information
  → Name, DOB, Ghana Card, Phone, Address

Step 3: Location
  → Constituency, Region, District

Step 4: Farm Plans
  → Farm name, Location, Size, Production type

Step 5: Experience
  → Years in poultry, Existing farm

Step 6 (if Government): Program Details
  → YEA batch, Referral source

Step 7: Review & Submit
  → Show summary, Confirm & Submit
```

### 2. Form Validation Rules

```typescript
const validationSchema = {
  ghana_card_number: {
    pattern: /^GHA-\d{9}-\d$/,
    message: 'Invalid format. Use: GHA-XXXXXXXXX-X'
  },
  
  primary_phone: {
    pattern: /^\+233[0-9]{9}$/,
    message: 'Use format: +233XXXXXXXXX'
  },
  
  email: {
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    optional: true
  },
  
  date_of_birth: {
    minAge: 18,
    maxAge: 65,
    message: 'Farmer must be between 18 and 65 years old'
  },
  
  planned_bird_capacity: {
    min: 1,
    message: 'Must plan for at least 1 bird'
  },
  
  land_size_acres: {
    min: 0.01,
    message: 'Land size must be greater than 0'
  }
};
```

### 3. Ghana Card Verification (Real-time)

```typescript
const verifyGhanaCard = async (ghanaCard: string) => {
  try {
    const response = await axios.post('/api/applications/verify-ghana-card/', {
      ghana_card_number: ghanaCard
    });
    
    if (!response.data.available) {
      return {
        error: 'Ghana Card already registered',
        existingApplication: response.data.existing_application
      };
    }
    
    return { valid: true };
  } catch (error) {
    return { error: error.response.data.message };
  }
};

// Use with debouncing (500ms)
```

### 4. Application Submission

```typescript
const submitApplication = async (formData: FarmApplicationForm) => {
  try {
    const response = await axios.post('/api/applications/submit/', formData);
    
    // Store application number for tracking
    localStorage.setItem('application_number', response.data.application_number);
    localStorage.setItem('ghana_card', formData.personal_information.ghana_card_number);
    
    return {
      success: true,
      application_number: response.data.application_number,
      tracking_url: response.data.tracking.track_url
    };
  } catch (error) {
    if (error.response.status === 429) {
      // Rate limited
      return {
        error: 'Too many applications',
        retry_after: error.response.data.retry_after
      };
    }
    
    if (error.response.status === 400) {
      // Validation errors
      return {
        error: 'Validation failed',
        errors: error.response.data.errors
      };
    }
    
    throw error;
  }
};
```

### 5. Status Tracking Component

```typescript
const trackApplication = async (ghanaCard: string) => {
  try {
    const response = await axios.get(
      `/api/applications/track/${encodeURIComponent(ghanaCard)}/`
    );
    
    return response.data.application;
  } catch (error) {
    if (error.response.status === 404) {
      return {
        error: 'Application not found',
        message: 'No application found for this Ghana Card number'
      };
    }
    throw error;
  }
};
```

### 6. Progress Indicator

```typescript
interface ApplicationProgress {
  percentage: number;
  current_stage: string;
  completed_stages: string[];
  pending_stages: string[];
}

const ProgressIndicator = ({ progress }: { progress: ApplicationProgress }) => {
  const stages = [
    'Submitted',
    'Constituency Review',
    'Regional Review',
    'National Review',
    'Approved'
  ];
  
  return (
    <div className="progress-tracker">
      {stages.map((stage, index) => (
        <div 
          key={stage}
          className={`
            stage
            ${progress.completed_stages.includes(stage) ? 'completed' : ''}
            ${progress.current_stage === stage ? 'active' : ''}
          `}
        >
          <div className="stage-icon">
            {progress.completed_stages.includes(stage) ? '✓' : index + 1}
          </div>
          <div className="stage-name">{stage}</div>
        </div>
      ))}
    </div>
  );
};
```

---

## Error Handling

### Common Error Scenarios

1. **Network Error**
```typescript
try {
  await submitApplication(data);
} catch (error) {
  if (!error.response) {
    // Network error
    showError('Connection failed. Please check your internet.');
  }
}
```

2. **Validation Errors**
```typescript
if (error.response.status === 400) {
  const errors = error.response.data.errors;
  // Show field-specific errors
  Object.keys(errors).forEach(field => {
    setFieldError(field, errors[field][0]);
  });
}
```

3. **Rate Limiting**
```typescript
if (error.response.status === 429) {
  const retryAfter = error.response.data.retry_after;
  showError(`Please wait ${retryAfter} before submitting again.`);
}
```

4. **Server Error**
```typescript
if (error.response.status >= 500) {
  showError('Server error. Please try again later.');
  // Log to error tracking (Sentry, etc.)
}
```

---

## UI/UX Best Practices

### 1. Landing Page
- Show statistics (applications processed, success rate)
- Clear call-to-action: "Apply Now" button
- Testimonials from approved farmers
- FAQ section
- Estimated timeline: "Get approved in 15 days"

### 2. Application Form
- Progress indicator showing current step
- Save draft functionality (localStorage)
- Real-time validation feedback
- Ghana Card verification on blur
- Constituency autocomplete with search
- Phone number input with country code (+233)
- Tooltips for complex fields
- Character counters for text fields

### 3. Success Page
- Celebration animation
- Application number prominently displayed
- Print/Download confirmation
- Next steps clearly outlined
- Add to calendar option
- Share buttons (WhatsApp, etc.)

### 4. Tracking Page
- Search by Ghana Card number
- Visual progress tracker
- Timeline view of history
- Estimated completion date
- SLA countdown
- Contact information for constituency
- Print application details

### 5. Mobile Optimization
- Touch-friendly inputs
- Large buttons (min 44px)
- Bottom navigation for multi-step
- Swipe gestures between steps
- Native phone number keyboard
- Camera integration for Ghana Card scan (future)

---

## Testing Checklist

### Functional Tests
- [ ] Submit application with all required fields
- [ ] Submit application with optional fields omitted
- [ ] Verify Ghana Card validation
- [ ] Verify phone number validation
- [ ] Test age validation (17, 18, 65, 66)
- [ ] Test duplicate Ghana Card detection
- [ ] Test rate limiting (3 submissions)
- [ ] Track application by Ghana Card
- [ ] View application not found error
- [ ] Test constituency dropdown
- [ ] Test form draft saving
- [ ] Test form validation errors
- [ ] Test network error handling

### UI Tests
- [ ] All form steps render correctly
- [ ] Progress indicator updates
- [ ] Error messages display inline
- [ ] Success page shows correctly
- [ ] Tracking page displays timeline
- [ ] Mobile responsive design
- [ ] Print-friendly layout
- [ ] Loading states during API calls
- [ ] Disabled states during submission

### Accessibility Tests
- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] Color contrast meets WCAG 2.1 AA
- [ ] Form labels properly associated
- [ ] Error messages announced
- [ ] Focus management in multi-step form

---

## Mock Data for Development

### Sample Valid Request
```json
{
  "application_type": "government_program",
  "personal_information": {
    "first_name": "Kofi",
    "middle_name": "Agyeman",
    "last_name": "Owusu",
    "date_of_birth": "1992-05-20",
    "gender": "Male",
    "ghana_card_number": "GHA-987654321-5",
    "primary_phone": "+233244111222",
    "alternate_phone": "+233202333444",
    "email": "kofi.owusu@gmail.com",
    "residential_address": "Plot 23, Dansoman, Accra"
  },
  "location": {
    "primary_constituency": "Ablekuma South",
    "region": "Greater Accra",
    "district": "Accra Metropolitan"
  },
  "farm_information": {
    "proposed_farm_name": "Owusu Farms Limited",
    "farm_location_description": "Near Dansoman Market, behind Police Station",
    "land_size_acres": "1.5",
    "primary_production_type": "Layers",
    "planned_bird_capacity": 300,
    "years_in_poultry": "2.0",
    "has_existing_farm": true
  },
  "government_program": {
    "yea_program_batch": "YEA-2025-Q1",
    "referral_source": "Radio advertisement"
  }
}
```

### Sample Ghana Card Numbers for Testing
```
Valid & Available: GHA-111111111-1
Valid & Available: GHA-222222222-2
Valid & Available: GHA-333333333-3
Already Used: GHA-123456789-0 (APP-2025-00015)
Invalid Format: GHA-12345 (too short)
Invalid Format: GHA-ABCDEFGHI-1 (letters not allowed)
```

---

## Next Steps After EOI

Once the EOI frontend is complete, next priorities are:

1. **Account Creation from Invitation** (users with approved applications)
2. **Officer Dashboard** (for reviewing applications)
3. **Farmer Dashboard** (after account creation)
4. **MFA Setup** (security enhancement)
5. **Farm Management** (core features)

---

## Support & Resources

### Backend API Documentation
- Full API docs: `http://localhost:8000/api/docs/`
- OpenAPI spec: `http://localhost:8000/api/schema/`

### Reference Documents
- `docs/APPLY_FIRST_WORKFLOW.md` - Complete workflow documentation
- `docs/COMPLETE_REGISTRATION_SYSTEM.md` - System overview
- `docs/SPAM_DETECTION.md` - Spam prevention details

### Contact
- Backend Team: backend@pms.gov.gh
- Technical Questions: Slack #frontend-backend-integration
- Bug Reports: GitHub Issues

---

## Quick Start Checklist

- [ ] Read this documentation thoroughly
- [ ] Set up development environment
- [ ] Install HTTP client (Axios/Fetch)
- [ ] Create application form component
- [ ] Implement multi-step form flow
- [ ] Add form validation
- [ ] Implement Ghana Card verification
- [ ] Create application submission handler
- [ ] Build success/confirmation page
- [ ] Create tracking page component
- [ ] Add error handling
- [ ] Test with mock data
- [ ] Test with backend API
- [ ] Mobile responsive testing
- [ ] Accessibility testing
- [ ] Ready for QA/UAT

---

**Last Updated:** November 26, 2025
**Version:** 1.0
**Status:** Production Ready ✅
