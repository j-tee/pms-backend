# Frontend Implementation Guide: Step 2 - Personal Information
## Farm Application Form

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Step:** 2 of 7  
**Purpose:** Complete guide for implementing the Personal Information step

---

## Table of Contents

1. [Overview](#overview)
2. [API Endpoint](#api-endpoint)
3. [Form Fields Reference](#form-fields-reference)
4. [Validation Rules](#validation-rules)
5. [UI/UX Requirements](#uiux-requirements)
6. [TypeScript Interfaces](#typescript-interfaces)
7. [Form State Management](#form-state-management)
8. [Auto-Save Implementation](#auto-save-implementation)
9. [Error Handling](#error-handling)
10. [Accessibility](#accessibility)
11. [Mobile Optimization](#mobile-optimization)
12. [Example Implementation](#example-implementation)

---

## Overview

### Step Context

**Step 2** collects personal information about the applicant. This is a critical step as it:
- Verifies applicant identity via Ghana Card
- Captures demographic information for government records
- Establishes primary contact details
- Determines constituency for application routing

### Step Position in Workflow

```
Step 1: Introduction ✓
Step 2: Personal Information ← YOU ARE HERE
Step 3: Location Details
Step 4: Farm Plans
Step 5: Experience
Step 6: Program Details (if government)
Step 7: Review & Submit
```

### Data Storage

- All data saved to `FarmApplication` model
- Auto-saved every 30 seconds (as shown in screenshot)
- No user account required at this stage (anonymous application)
- Application ID: `APP-YYYY-XXXXX` format

---

## API Endpoint

### Base Endpoint

```
POST /api/applications/draft/save/
```

### Request Headers

```http
Content-Type: application/json
X-Application-ID: APP-2025-00123  (if continuing existing application)
```

### Request Body (Step 2 Fields)

```json
{
  "step": 2,
  "application_type": "government_program",
  "data": {
    "first_name": "Kwame",
    "middle_name": "Mensah",
    "last_name": "Asante",
    "date_of_birth": "1995-05-15",
    "gender": "Male",
    "ghana_card_number": "GHA-123456789-0",
    "primary_phone": "+233244567890",
    "alternate_phone": "+233209876543",
    "email": "kwame@example.com",
    "residential_address": "House No. 45, Community 8, Tema",
    "primary_constituency": "Tema East"
  }
}
```

### Response

**Success (200 OK)**
```json
{
  "success": true,
  "application_id": "APP-2025-00123",
  "step_completed": 2,
  "next_step": 3,
  "auto_saved": true,
  "last_saved_at": "2025-11-26T15:45:30Z",
  "validation_errors": [],
  "message": "Personal information saved successfully"
}
```

**Validation Errors (400 Bad Request)**
```json
{
  "success": false,
  "validation_errors": {
    "ghana_card_number": [
      "This Ghana Card number is already registered",
      "Format must be GHA-XXXXXXXXX-X"
    ],
    "date_of_birth": [
      "Applicant must be between 18 and 65 years old"
    ],
    "primary_phone": [
      "This phone number is already in use"
    ]
  },
  "message": "Please correct the errors and try again"
}
```

---

## Form Fields Reference

### 1. First Name

| Property | Value |
|----------|-------|
| **Field Name** | `first_name` |
| **Type** | Text input |
| **Required** | Yes ✓ |
| **Max Length** | 100 characters |
| **Validation** | Letters only, minimum 2 characters |
| **Database Field** | `FarmApplication.first_name` |

**Validation Rules:**
```typescript
{
  required: "First name is required",
  minLength: {
    value: 2,
    message: "First name must be at least 2 characters"
  },
  maxLength: {
    value: 100,
    message: "First name cannot exceed 100 characters"
  },
  pattern: {
    value: /^[A-Za-z\s\-']+$/,
    message: "First name can only contain letters, spaces, hyphens, and apostrophes"
  }
}
```

**UI Component:**
```tsx
<FormField
  label="First Name"
  required
  error={errors.first_name?.message}
>
  <Input
    name="first_name"
    placeholder="Enter your first name"
    maxLength={100}
    autoComplete="given-name"
  />
</FormField>
```

---

### 2. Middle Name

| Property | Value |
|----------|-------|
| **Field Name** | `middle_name` |
| **Type** | Text input |
| **Required** | No |
| **Max Length** | 100 characters |
| **Validation** | Letters only (if provided) |
| **Database Field** | `FarmApplication.middle_name` |

**Validation Rules:**
```typescript
{
  maxLength: {
    value: 100,
    message: "Middle name cannot exceed 100 characters"
  },
  pattern: {
    value: /^[A-Za-z\s\-']*$/,
    message: "Middle name can only contain letters"
  }
}
```

---

### 3. Last Name

| Property | Value |
|----------|-------|
| **Field Name** | `last_name` |
| **Type** | Text input |
| **Required** | Yes ✓ |
| **Max Length** | 100 characters |
| **Validation** | Letters only, minimum 2 characters |
| **Database Field** | `FarmApplication.last_name` |

**Validation Rules:** Same as First Name

---

### 4. Date of Birth

| Property | Value |
|----------|-------|
| **Field Name** | `date_of_birth` |
| **Type** | Date picker |
| **Required** | Yes ✓ |
| **Age Range** | 18-65 years |
| **Format** | YYYY-MM-DD (ISO 8601) |
| **Database Field** | `FarmApplication.date_of_birth` |

**Validation Rules:**
```typescript
{
  required: "Date of birth is required",
  validate: {
    minimumAge: (value) => {
      const age = calculateAge(value);
      return age >= 18 || "You must be at least 18 years old";
    },
    maximumAge: (value) => {
      const age = calculateAge(value);
      return age <= 65 || "You must be under 65 years old";
    },
    validDate: (value) => {
      return isValidDate(value) || "Please enter a valid date";
    }
  }
}
```

**Age Calculator Helper:**
```typescript
function calculateAge(dateOfBirth: string): number {
  const today = new Date();
  const birthDate = new Date(dateOfBirth);
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();
  
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }
  
  return age;
}
```

**UI Component:**
```tsx
<FormField
  label="Date of Birth"
  required
  error={errors.date_of_birth?.message}
  hint="You must be between 18 and 65 years old"
>
  <DatePicker
    name="date_of_birth"
    maxDate={new Date()} // Cannot select future dates
    yearRange={[1960, 2007]} // 18 to 65 years old
    format="dd/MM/yyyy"
  />
</FormField>
```

---

### 5. Gender

| Property | Value |
|----------|-------|
| **Field Name** | `gender` |
| **Type** | Radio buttons / Select |
| **Required** | Yes ✓ |
| **Options** | Male, Female, Other |
| **Database Field** | `FarmApplication.gender` |

**Options:**
```typescript
const GENDER_OPTIONS = [
  { value: 'Male', label: 'Male' },
  { value: 'Female', label: 'Female' },
  { value: 'Other', label: 'Other' }
];
```

**Validation Rules:**
```typescript
{
  required: "Please select your gender"
}
```

**UI Component:**
```tsx
<FormField
  label="Gender"
  required
  error={errors.gender?.message}
>
  <RadioGroup name="gender" options={GENDER_OPTIONS} />
</FormField>
```

---

### 6. Ghana Card Number

| Property | Value |
|----------|-------|
| **Field Name** | `ghana_card_number` |
| **Type** | Text input (formatted) |
| **Required** | Yes ✓ |
| **Format** | GHA-XXXXXXXXX-X |
| **Pattern** | `^GHA-\d{9}-\d$` |
| **Uniqueness** | Must be unique across all applications |
| **Database Field** | `FarmApplication.ghana_card_number` |

**Validation Rules:**
```typescript
{
  required: "Ghana Card number is required",
  pattern: {
    value: /^GHA-\d{9}-\d$/,
    message: "Ghana Card format must be GHA-XXXXXXXXX-X"
  },
  validate: {
    unique: async (value) => {
      const response = await checkGhanaCardAvailability(value);
      return response.available || "This Ghana Card number is already registered";
    }
  }
}
```

**Format Helper:**
```typescript
function formatGhanaCard(value: string): string {
  // Remove all non-digits
  const digits = value.replace(/\D/g, '');
  
  // Format as GHA-XXXXXXXXX-X
  if (digits.length <= 9) {
    return `GHA-${digits}`;
  } else if (digits.length === 10) {
    return `GHA-${digits.slice(0, 9)}-${digits.slice(9)}`;
  } else {
    return `GHA-${digits.slice(0, 9)}-${digits.slice(9, 10)}`;
  }
}
```

**Uniqueness Check API:**
```typescript
// Debounced check (every 500ms after typing stops)
async function checkGhanaCardAvailability(ghanaCard: string): Promise<{available: boolean}> {
  const response = await fetch('/api/applications/check-ghana-card/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ghana_card_number: ghanaCard })
  });
  return response.json();
}
```

**UI Component:**
```tsx
<FormField
  label="Ghana Card Number"
  required
  error={errors.ghana_card_number?.message}
  hint="Format: GHA-123456789-0"
>
  <Input
    name="ghana_card_number"
    placeholder="GHA-123456789-0"
    maxLength={17}
    onChange={(e) => {
      const formatted = formatGhanaCard(e.target.value);
      setValue('ghana_card_number', formatted);
    }}
  />
  {isCheckingGhanaCard && <Spinner size="sm" />}
</FormField>
```

---

### 7. Primary Phone

| Property | Value |
|----------|-------|
| **Field Name** | `primary_phone` |
| **Type** | Phone input |
| **Required** | Yes ✓ |
| **Format** | +233XXXXXXXXX (Ghana format) |
| **Uniqueness** | Must be unique |
| **Verification** | Will be verified via SMS in later step |
| **Database Field** | `FarmApplication.primary_phone` |

**Validation Rules:**
```typescript
{
  required: "Primary phone number is required",
  pattern: {
    value: /^\+233\d{9}$/,
    message: "Phone number must be in format +233XXXXXXXXX"
  },
  validate: {
    unique: async (value) => {
      const response = await checkPhoneAvailability(value);
      return response.available || "This phone number is already registered";
    },
    validGhanaNetwork: (value) => {
      const prefix = value.slice(4, 6); // Get first 2 digits after +233
      const validPrefixes = ['20', '23', '24', '25', '26', '27', '28', '50', '54', '55', '56', '57', '59'];
      return validPrefixes.includes(prefix) || "Invalid Ghana phone number";
    }
  }
}
```

**Format Helper:**
```typescript
function formatGhanaPhone(value: string): string {
  // Remove all non-digits
  let digits = value.replace(/\D/g, '');
  
  // Handle leading 0
  if (digits.startsWith('0')) {
    digits = digits.slice(1);
  }
  
  // Add Ghana country code
  if (!digits.startsWith('233')) {
    digits = '233' + digits;
  }
  
  // Limit to correct length (233 + 9 digits)
  digits = digits.slice(0, 12);
  
  return '+' + digits;
}
```

**UI Component:**
```tsx
<FormField
  label="Primary Phone Number"
  required
  error={errors.primary_phone?.message}
  hint="This number will be used for SMS notifications"
>
  <PhoneInput
    name="primary_phone"
    country="GH"
    placeholder="0244 567 890"
    format="+233 ## ### ####"
    mask="_"
  />
  {isCheckingPhone && <Spinner size="sm" />}
</FormField>
```

---

### 8. Alternate Phone

| Property | Value |
|----------|-------|
| **Field Name** | `alternate_phone` |
| **Type** | Phone input |
| **Required** | No |
| **Format** | +233XXXXXXXXX (Ghana format) |
| **Database Field** | `FarmApplication.alternate_phone` |

**Validation Rules:**
```typescript
{
  pattern: {
    value: /^\+233\d{9}$/,
    message: "Phone number must be in format +233XXXXXXXXX"
  },
  validate: {
    different: (value, formValues) => {
      if (!value) return true; // Optional field
      return value !== formValues.primary_phone || 
        "Alternate phone must be different from primary phone";
    }
  }
}
```

---

### 9. Email Address

| Property | Value |
|----------|-------|
| **Field Name** | `email` |
| **Type** | Email input |
| **Required** | No (Optional) |
| **Format** | Standard email format |
| **Verification** | Will be verified via email if provided |
| **Database Field** | `FarmApplication.email` |

**Validation Rules:**
```typescript
{
  pattern: {
    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
    message: "Please enter a valid email address"
  },
  validate: {
    unique: async (value) => {
      if (!value) return true; // Optional field
      const response = await checkEmailAvailability(value);
      return response.available || "This email is already registered";
    }
  }
}
```

**UI Component:**
```tsx
<FormField
  label="Email Address"
  optional
  error={errors.email?.message}
  hint="Optional - for email notifications"
>
  <Input
    type="email"
    name="email"
    placeholder="kwame@example.com"
    autoComplete="email"
  />
</FormField>
```

---

### 10. Residential Address

| Property | Value |
|----------|-------|
| **Field Name** | `residential_address` |
| **Type** | Textarea |
| **Required** | Yes ✓ |
| **Min Length** | 10 characters |
| **Max Length** | 500 characters |
| **Database Field** | `FarmApplication.residential_address` |

**Validation Rules:**
```typescript
{
  required: "Residential address is required",
  minLength: {
    value: 10,
    message: "Please provide a detailed address (at least 10 characters)"
  },
  maxLength: {
    value: 500,
    message: "Address cannot exceed 500 characters"
  }
}
```

**UI Component:**
```tsx
<FormField
  label="Residential Address"
  required
  error={errors.residential_address?.message}
  hint="Your current place of residence"
>
  <Textarea
    name="residential_address"
    placeholder="House No., Street, Community/Town, City"
    rows={3}
    maxLength={500}
  />
  <CharacterCount current={watchAddress?.length || 0} max={500} />
</FormField>
```

---

### 11. Primary Constituency

| Property | Value |
|----------|-------|
| **Field Name** | `primary_constituency` |
| **Type** | Searchable select / Autocomplete |
| **Required** | Yes ✓ |
| **Options** | 275 constituencies in Ghana |
| **Database Field** | `FarmApplication.primary_constituency` |

**Validation Rules:**
```typescript
{
  required: "Please select your constituency",
  validate: {
    validConstituency: (value) => {
      return GHANA_CONSTITUENCIES.includes(value) || 
        "Please select a valid constituency";
    }
  }
}
```

**Data Source:**
```typescript
// Fetch constituencies from API or use static list
const GHANA_CONSTITUENCIES = [
  { value: "Tema East", label: "Tema East", region: "Greater Accra" },
  { value: "Tema West", label: "Tema West", region: "Greater Accra" },
  { value: "Tema Central", label: "Tema Central", region: "Greater Accra" },
  // ... 272 more constituencies
];
```

**API Endpoint for Constituencies:**
```
GET /api/constituencies/
```

**Response:**
```json
{
  "constituencies": [
    {
      "name": "Tema East",
      "region": "Greater Accra",
      "district": "Tema Metropolitan"
    },
    // ... more
  ]
}
```

**UI Component:**
```tsx
<FormField
  label="Primary Constituency"
  required
  error={errors.primary_constituency?.message}
  hint="Select the constituency where your farm will be located"
>
  <Select
    name="primary_constituency"
    options={GHANA_CONSTITUENCIES}
    searchable
    placeholder="Search for your constituency..."
    groupBy="region"
  />
</FormField>
```

---

## Validation Rules

### Client-Side Validation

All validation should happen in real-time as users type or change fields. Use debouncing for async validations (uniqueness checks).

### Server-Side Validation

Backend will perform comprehensive validation including:
1. Format validation
2. Uniqueness checks (Ghana Card, Phone, Email)
3. Age range validation
4. Cross-field validation

### Validation Timing

```typescript
// Real-time validation (on blur or on change)
const form = useForm({
  mode: 'onBlur', // Validate on field blur
  reValidateMode: 'onChange', // Re-validate on every change after first validation
});

// Async validation (debounced)
const debouncedValidation = useMemo(
  () => debounce(async (value: string) => {
    // Perform async validation
  }, 500),
  []
);
```

---

## UI/UX Requirements

### Visual Design

1. **Field Layout**
   - Two-column layout on desktop (>=768px)
   - Single column on mobile (<768px)
   - Logical grouping of related fields

2. **Required Field Indicator**
   ```tsx
   <label>
     First Name <span className="text-red-500">*</span>
   </label>
   ```

3. **Validation Feedback**
   - ✓ Green checkmark for valid fields
   - ✗ Red error message for invalid fields
   - Loading spinner for async validations

4. **Progress Indicator**
   ```
   Step 2 of 7
   [=====>         ] 28% Complete
   ```

### Field Grouping

**Group 1: Basic Information**
- First Name, Middle Name, Last Name
- Date of Birth, Gender

**Group 2: Identity Verification**
- Ghana Card Number

**Group 3: Contact Information**
- Primary Phone, Alternate Phone
- Email Address

**Group 4: Location**
- Residential Address
- Primary Constituency

### Auto-Save Indicator

```tsx
<div className="flex items-center gap-2 text-sm text-gray-600">
  <SaveIcon className="w-4 h-4" />
  <span>Your progress is automatically saved every 30 seconds</span>
  {isSaving && <Spinner size="sm" />}
  {lastSaved && <span className="text-green-600">Last saved: {formatRelativeTime(lastSaved)}</span>}
</div>
```

---

## TypeScript Interfaces

### Form Data Interface

```typescript
interface PersonalInformationForm {
  first_name: string;
  middle_name?: string;
  last_name: string;
  date_of_birth: string; // ISO 8601 date string
  gender: 'Male' | 'Female' | 'Other';
  ghana_card_number: string; // Format: GHA-XXXXXXXXX-X
  primary_phone: string; // Format: +233XXXXXXXXX
  alternate_phone?: string; // Format: +233XXXXXXXXX
  email?: string;
  residential_address: string;
  primary_constituency: string;
}
```

### Application State Interface

```typescript
interface ApplicationState {
  application_id: string | null;
  application_type: 'government_program' | 'independent';
  current_step: number;
  completed_steps: number[];
  form_data: {
    step1?: IntroductionForm;
    step2?: PersonalInformationForm;
    step3?: LocationDetailsForm;
    step4?: FarmPlansForm;
    step5?: ExperienceForm;
    step6?: ProgramDetailsForm;
    step7?: ReviewForm;
  };
  last_saved_at: string | null;
  is_saving: boolean;
  validation_errors: Record<string, string[]>;
}
```

### API Response Interfaces

```typescript
interface SaveDraftResponse {
  success: boolean;
  application_id: string;
  step_completed: number;
  next_step: number;
  auto_saved: boolean;
  last_saved_at: string;
  validation_errors: Record<string, string[]>;
  message: string;
}

interface ValidationError {
  field: string;
  errors: string[];
}

interface UniqueCheckResponse {
  available: boolean;
  message?: string;
}
```

### Constituency Interface

```typescript
interface Constituency {
  name: string;
  region: string;
  district: string;
  code?: string;
}

interface ConstituencyOption {
  value: string;
  label: string;
  region: string;
}
```

---

## Form State Management

### Using React Hook Form

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

// Zod schema for validation
const personalInfoSchema = z.object({
  first_name: z.string()
    .min(2, 'First name must be at least 2 characters')
    .max(100, 'First name cannot exceed 100 characters')
    .regex(/^[A-Za-z\s\-']+$/, 'First name can only contain letters'),
  
  middle_name: z.string()
    .max(100, 'Middle name cannot exceed 100 characters')
    .regex(/^[A-Za-z\s\-']*$/, 'Middle name can only contain letters')
    .optional(),
  
  last_name: z.string()
    .min(2, 'Last name must be at least 2 characters')
    .max(100, 'Last name cannot exceed 100 characters')
    .regex(/^[A-Za-z\s\-']+$/, 'Last name can only contain letters'),
  
  date_of_birth: z.string()
    .refine((date) => {
      const age = calculateAge(date);
      return age >= 18 && age <= 65;
    }, 'You must be between 18 and 65 years old'),
  
  gender: z.enum(['Male', 'Female', 'Other']),
  
  ghana_card_number: z.string()
    .regex(/^GHA-\d{9}-\d$/, 'Ghana Card format must be GHA-XXXXXXXXX-X'),
  
  primary_phone: z.string()
    .regex(/^\+233\d{9}$/, 'Phone number must be in format +233XXXXXXXXX'),
  
  alternate_phone: z.string()
    .regex(/^\+233\d{9}$/, 'Phone number must be in format +233XXXXXXXXX')
    .optional(),
  
  email: z.string()
    .email('Please enter a valid email address')
    .optional(),
  
  residential_address: z.string()
    .min(10, 'Please provide a detailed address')
    .max(500, 'Address cannot exceed 500 characters'),
  
  primary_constituency: z.string()
    .min(1, 'Please select your constituency'),
});

type PersonalInfoFormData = z.infer<typeof personalInfoSchema>;

// Component
function PersonalInformationStep() {
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    setValue,
    trigger,
  } = useForm<PersonalInfoFormData>({
    resolver: zodResolver(personalInfoSchema),
    mode: 'onBlur',
    defaultValues: loadSavedData(), // Load from localStorage or API
  });

  // Watch for changes to trigger auto-save
  const formValues = watch();

  // Auto-save logic
  useEffect(() => {
    const timer = setTimeout(() => {
      autoSave(formValues);
    }, 30000); // 30 seconds

    return () => clearTimeout(timer);
  }, [formValues]);

  const onSubmit = async (data: PersonalInfoFormData) => {
    // Save and proceed to next step
    await saveAndContinue(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* Form fields */}
    </form>
  );
}
```

---

## Auto-Save Implementation

### Auto-Save Hook

```typescript
import { useEffect, useRef } from 'react';

interface AutoSaveOptions {
  interval: number; // milliseconds
  onSave: (data: any) => Promise<void>;
  data: any;
  enabled: boolean;
}

function useAutoSave({ interval, onSave, data, enabled }: AutoSaveOptions) {
  const savedDataRef = useRef<string>('');
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!enabled) return;

    // Clear existing timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Set new timer
    timerRef.current = setTimeout(() => {
      const currentData = JSON.stringify(data);
      
      // Only save if data has changed
      if (currentData !== savedDataRef.current) {
        savedDataRef.current = currentData;
        onSave(data).catch(console.error);
      }
    }, interval);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [data, interval, onSave, enabled]);
}

// Usage
function PersonalInformationStep() {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  
  const formValues = watch();

  useAutoSave({
    interval: 30000, // 30 seconds
    data: formValues,
    enabled: true,
    onSave: async (data) => {
      setIsSaving(true);
      try {
        await saveDraft(data);
        setLastSaved(new Date());
      } finally {
        setIsSaving(false);
      }
    },
  });
}
```

### Save Draft Function

```typescript
async function saveDraft(data: PersonalInfoFormData): Promise<SaveDraftResponse> {
  const applicationId = localStorage.getItem('application_id');
  
  const response = await fetch('/api/applications/draft/save/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(applicationId && { 'X-Application-ID': applicationId }),
    },
    body: JSON.stringify({
      step: 2,
      application_type: getApplicationType(), // From step 1
      data,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to save draft');
  }

  const result = await response.json();
  
  // Store application ID for future requests
  if (result.application_id) {
    localStorage.setItem('application_id', result.application_id);
  }

  return result;
}
```

---

## Error Handling

### Field-Level Errors

```tsx
<FormField
  label="Ghana Card Number"
  required
  error={errors.ghana_card_number?.message}
>
  <Input
    name="ghana_card_number"
    className={errors.ghana_card_number ? 'border-red-500' : ''}
  />
  {errors.ghana_card_number && (
    <ErrorMessage>{errors.ghana_card_number.message}</ErrorMessage>
  )}
</FormField>
```

### Form-Level Errors

```tsx
{serverErrors && (
  <Alert variant="error" className="mb-4">
    <AlertTitle>Please correct the following errors:</AlertTitle>
    <ul className="list-disc list-inside">
      {Object.entries(serverErrors).map(([field, errors]) => (
        <li key={field}>
          <strong>{formatFieldName(field)}:</strong> {errors.join(', ')}
        </li>
      ))}
    </ul>
  </Alert>
)}
```

### Network Errors

```tsx
{networkError && (
  <Alert variant="warning">
    <AlertTitle>Connection Issue</AlertTitle>
    <p>We couldn't save your progress. Please check your internet connection.</p>
    <Button onClick={retrySave} variant="outline" size="sm">
      Retry
    </Button>
  </Alert>
)}
```

---

## Accessibility

### ARIA Labels

```tsx
<Input
  name="first_name"
  aria-label="First name"
  aria-required="true"
  aria-invalid={!!errors.first_name}
  aria-describedby={errors.first_name ? 'first-name-error' : undefined}
/>
{errors.first_name && (
  <span id="first-name-error" role="alert" className="text-red-500">
    {errors.first_name.message}
  </span>
)}
```

### Keyboard Navigation

- All form fields must be accessible via Tab key
- Submit button should be reachable and activatable via Enter key
- Error messages should receive focus when displayed

### Screen Reader Support

```tsx
<div role="status" aria-live="polite" aria-atomic="true">
  {isSaving ? 'Saving your progress...' : lastSaved ? `Last saved at ${formatTime(lastSaved)}` : ''}
</div>
```

---

## Mobile Optimization

### Responsive Layout

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  {/* First Name */}
  <FormField label="First Name" required>
    <Input name="first_name" />
  </FormField>
  
  {/* Last Name */}
  <FormField label="Last Name" required>
    <Input name="last_name" />
  </FormField>
</div>
```

### Mobile Input Types

```tsx
{/* Optimized for mobile keyboards */}
<Input type="tel" name="primary_phone" inputMode="tel" />
<Input type="email" name="email" inputMode="email" />
<Input type="date" name="date_of_birth" />
```

### Touch-Friendly

- Minimum tap target size: 44x44 pixels
- Adequate spacing between form fields
- Large, easy-to-tap buttons

---

## Example Implementation

### Complete Component

```typescript
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// Validation schema
const personalInfoSchema = z.object({
  first_name: z.string().min(2).max(100).regex(/^[A-Za-z\s\-']+$/),
  middle_name: z.string().max(100).regex(/^[A-Za-z\s\-']*$/).optional(),
  last_name: z.string().min(2).max(100).regex(/^[A-Za-z\s\-']+$/),
  date_of_birth: z.string().refine((date) => {
    const age = calculateAge(date);
    return age >= 18 && age <= 65;
  }),
  gender: z.enum(['Male', 'Female', 'Other']),
  ghana_card_number: z.string().regex(/^GHA-\d{9}-\d$/),
  primary_phone: z.string().regex(/^\+233\d{9}$/),
  alternate_phone: z.string().regex(/^\+233\d{9}$/).optional(),
  email: z.string().email().optional(),
  residential_address: z.string().min(10).max(500),
  primary_constituency: z.string().min(1),
});

type PersonalInfoFormData = z.infer<typeof personalInfoSchema>;

export default function PersonalInformationStep() {
  const router = useRouter();
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [serverErrors, setServerErrors] = useState<Record<string, string[]> | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    setValue,
  } = useForm<PersonalInfoFormData>({
    resolver: zodResolver(personalInfoSchema),
    mode: 'onBlur',
    defaultValues: loadFromLocalStorage(),
  });

  const formValues = watch();

  // Auto-save every 30 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      autoSaveDraft(formValues);
    }, 30000);

    return () => clearTimeout(timer);
  }, [formValues]);

  const autoSaveDraft = async (data: PersonalInfoFormData) => {
    setIsSaving(true);
    try {
      const response = await fetch('/api/applications/draft/save/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Application-ID': localStorage.getItem('application_id') || '',
        },
        body: JSON.stringify({
          step: 2,
          application_type: localStorage.getItem('application_type'),
          data,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        localStorage.setItem('application_id', result.application_id);
        setLastSaved(new Date());
      }
    } catch (error) {
      console.error('Auto-save failed:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const onSubmit = async (data: PersonalInfoFormData) => {
    try {
      setServerErrors(null);
      
      const response = await fetch('/api/applications/draft/save/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Application-ID': localStorage.getItem('application_id') || '',
        },
        body: JSON.stringify({
          step: 2,
          application_type: localStorage.getItem('application_type'),
          data,
          complete_step: true, // Mark step as complete
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        setServerErrors(error.validation_errors);
        return;
      }

      const result = await response.json();
      localStorage.setItem('application_id', result.application_id);
      
      // Save to local storage
      saveToLocalStorage(data);
      
      // Navigate to next step
      router.push('/apply/step-3');
    } catch (error) {
      console.error('Submission failed:', error);
      alert('An error occurred. Please try again.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Progress Header */}
      <div className="mb-8">
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-2xl font-bold">Personal Information</h2>
          <span className="text-sm text-gray-600">2 / 7</span>
        </div>
        <p className="text-gray-600 mb-4">Tell us about yourself</p>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div className="bg-green-600 h-2 rounded-full" style={{ width: '28%' }} />
        </div>
      </div>

      {/* Auto-save Indicator */}
      <div className="mb-4 flex items-center gap-2 text-sm text-gray-600">
        <SaveIcon className="w-4 h-4" />
        <span>Your progress is automatically saved every 30 seconds</span>
        {isSaving && <Spinner size="sm" />}
        {lastSaved && (
          <span className="text-green-600">
            Last saved: {formatRelativeTime(lastSaved)}
          </span>
        )}
      </div>

      {/* Server Errors */}
      {serverErrors && (
        <Alert variant="error" className="mb-6">
          <AlertTitle>Please correct the following errors:</AlertTitle>
          <ul className="list-disc list-inside">
            {Object.entries(serverErrors).map(([field, errors]) => (
              <li key={field}>
                <strong>{formatFieldName(field)}:</strong> {errors.join(', ')}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Information */}
        <fieldset className="border border-gray-300 rounded-lg p-4">
          <legend className="text-lg font-semibold px-2">Basic Information</legend>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {/* First Name */}
            <FormField label="First Name" required error={errors.first_name?.message}>
              <Input {...register('first_name')} placeholder="Enter your first name" />
            </FormField>

            {/* Middle Name */}
            <FormField label="Middle Name" error={errors.middle_name?.message}>
              <Input {...register('middle_name')} placeholder="Enter your middle name (optional)" />
            </FormField>

            {/* Last Name */}
            <FormField label="Last Name" required error={errors.last_name?.message}>
              <Input {...register('last_name')} placeholder="Enter your last name" />
            </FormField>

            {/* Date of Birth */}
            <FormField 
              label="Date of Birth" 
              required 
              error={errors.date_of_birth?.message}
              hint="You must be between 18 and 65 years old"
            >
              <Input type="date" {...register('date_of_birth')} />
            </FormField>

            {/* Gender */}
            <FormField label="Gender" required error={errors.gender?.message}>
              <RadioGroup 
                {...register('gender')}
                options={[
                  { value: 'Male', label: 'Male' },
                  { value: 'Female', label: 'Female' },
                  { value: 'Other', label: 'Other' },
                ]}
              />
            </FormField>
          </div>
        </fieldset>

        {/* Identity Verification */}
        <fieldset className="border border-gray-300 rounded-lg p-4">
          <legend className="text-lg font-semibold px-2">Identity Verification</legend>
          
          <div className="mt-4">
            <FormField 
              label="Ghana Card Number" 
              required 
              error={errors.ghana_card_number?.message}
              hint="Format: GHA-123456789-0"
            >
              <Input 
                {...register('ghana_card_number')} 
                placeholder="GHA-123456789-0"
                maxLength={17}
              />
            </FormField>
          </div>
        </fieldset>

        {/* Contact Information */}
        <fieldset className="border border-gray-300 rounded-lg p-4">
          <legend className="text-lg font-semibold px-2">Contact Information</legend>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <FormField 
              label="Primary Phone Number" 
              required 
              error={errors.primary_phone?.message}
              hint="This number will be used for SMS notifications"
            >
              <PhoneInput {...register('primary_phone')} country="GH" />
            </FormField>

            <FormField label="Alternate Phone Number" error={errors.alternate_phone?.message}>
              <PhoneInput {...register('alternate_phone')} country="GH" />
            </FormField>

            <FormField 
              label="Email Address" 
              error={errors.email?.message}
              hint="Optional - for email notifications"
            >
              <Input type="email" {...register('email')} placeholder="kwame@example.com" />
            </FormField>
          </div>
        </fieldset>

        {/* Location */}
        <fieldset className="border border-gray-300 rounded-lg p-4">
          <legend className="text-lg font-semibold px-2">Location</legend>
          
          <div className="space-y-4 mt-4">
            <FormField 
              label="Residential Address" 
              required 
              error={errors.residential_address?.message}
              hint="Your current place of residence"
            >
              <Textarea 
                {...register('residential_address')} 
                placeholder="House No., Street, Community/Town, City"
                rows={3}
              />
            </FormField>

            <FormField 
              label="Primary Constituency" 
              required 
              error={errors.primary_constituency?.message}
              hint="Select the constituency where your farm will be located"
            >
              <ConstituencySelect {...register('primary_constituency')} />
            </FormField>
          </div>
        </fieldset>

        {/* Navigation Buttons */}
        <div className="flex justify-between pt-6">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.push('/apply/step-1')}
          >
            ← Previous
          </Button>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Next →'}
          </Button>
        </div>
      </form>
    </div>
  );
}

// Helper functions
function calculateAge(dateOfBirth: string): number {
  const today = new Date();
  const birthDate = new Date(dateOfBirth);
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }
  return age;
}

function loadFromLocalStorage(): Partial<PersonalInfoFormData> {
  const saved = localStorage.getItem('application_step2');
  return saved ? JSON.parse(saved) : {};
}

function saveToLocalStorage(data: PersonalInfoFormData) {
  localStorage.setItem('application_step2', JSON.stringify(data));
}

function formatRelativeTime(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
  return `${Math.floor(seconds / 3600)} hours ago`;
}

function formatFieldName(field: string): string {
  return field
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
```

---

## Testing Checklist

### Functional Testing

- [ ] All required fields show validation errors when empty
- [ ] Ghana Card format validation works correctly
- [ ] Phone number format validation works correctly
- [ ] Email validation works correctly (when provided)
- [ ] Age validation (18-65 years) works correctly
- [ ] Constituency dropdown loads all 275 constituencies
- [ ] Auto-save triggers every 30 seconds
- [ ] Manual save on "Next" button works
- [ ] Previous button navigates to Step 1
- [ ] Form data persists after navigation
- [ ] Uniqueness checks work for Ghana Card, Phone, Email
- [ ] Server validation errors display correctly

### Browser Testing

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

### Accessibility Testing

- [ ] All form fields have proper labels
- [ ] Error messages are announced to screen readers
- [ ] Keyboard navigation works correctly
- [ ] ARIA attributes are properly set
- [ ] Color contrast meets WCAG AA standards

### Performance Testing

- [ ] Page loads in under 2 seconds
- [ ] Form is responsive on all device sizes
- [ ] No unnecessary re-renders
- [ ] Debounced async validations don't block UI

---

## Summary

This guide provides everything needed to implement Step 2 (Personal Information) of the Farm Application Form:

✓ **11 form fields** with detailed specifications  
✓ **Comprehensive validation** (client-side and server-side)  
✓ **Auto-save functionality** (every 30 seconds)  
✓ **TypeScript interfaces** for type safety  
✓ **Complete example** implementation  
✓ **Accessibility** considerations  
✓ **Mobile optimization** guidelines  
✓ **Testing checklist** for QA  

**Next Steps:**
1. Review the API endpoints with backend team
2. Implement the form using provided code examples
3. Test all validation rules
4. Ensure auto-save works correctly
5. Conduct accessibility testing
6. Proceed to Step 3: Location Details

**Questions or Issues:**
Contact the backend team for any API-related questions or clarifications.

---

**End of Guide**
