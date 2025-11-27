# Frontend Implementation Guide: Step 5 - Experience
## Farm Application Form

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Step:** 5 of 7  
**Purpose:** Implementation blueprint for the Experience step in the apply-first workflow

---

## Table of Contents

1. [Overview](#overview)
2. [Experience Data Model](#experience-data-model)
3. [API Contract](#api-contract)
4. [Form Sections & Fields](#form-sections--fields)
5. [Validation Rules](#validation-rules)
6. [UI/UX Requirements](#uiux-requirements)
7. [TypeScript Types](#typescript-types)
8. [State Management & Auto-Save](#state-management--auto-save)
9. [Derived Metrics & Helpers](#derived-metrics--helpers)
10. [Error Handling](#error-handling)
11. [Accessibility & Mobile](#accessibility--mobile)
12. [Example Implementation](#example-implementation)
13. [Testing Checklist](#testing-checklist)

---

## Overview

### Role of Step 5

The Experience step captures the applicant’s poultry background. These responses power:

- **Priority scoring** – `FarmApplication.calculate_priority_score()` boosts experienced and existing-farm applicants.
- **Review triage** – Officers can skim experience caps before calling applicants.
- **Future onboarding** – Values hydrate the `Farm` model’s education/experience fields after approval so the farmer record is complete from day one.

### Workflow Context

```
Step 1: Introduction ✓
Step 2: Personal Information ✓
Step 3: Location Details ✓
Step 4: Farm Plans ✓
Step 5: Experience ← CURRENT STEP
Step 6: Program Details (government only)
Step 7: Review & Submit
```

### Persistence Rules

- Drafts continue through `POST /api/applications/draft/save/` with `step: 5`.
- `years_in_poultry` (Decimal) and `has_existing_farm` (Boolean) are stored directly on `FarmApplication`.
- Education/literacy answers are staged for the downstream `Farm` profile. Capture them client-side and include them in the payload; backend serializers accept them as part of the experience step snapshot for future migrations.
- Auto-save cadence remains 30 seconds.

---

## Experience Data Model

| Segment | Fields | Notes |
|---------|--------|-------|
| **Education & Literacy** | `education_level`, `literacy_level` | Maps to `farms.Farm` education section; helps tailor future training content |
| **Hands-on Experience** | `has_farming_experience`, `years_in_poultry` | Years stored as decimal with one decimal place (e.g., `"2.5"`) |
| **Current Operations** | `has_existing_farm`, `farming_full_time`, `other_occupation` | Indicates if applicant already runs a farm and whether poultry is their primary work |
| **Training History** | `previous_training`, `other_farming_activities` | Optional text areas for officer context |

> Even though only `years_in_poultry` and `has_existing_farm` exist as physical columns today, the serializer keeps the remaining answers so they can hydrate the `Farm` record after approval.

---

## API Contract

### Save Draft (Step 5)

```
POST /api/applications/draft/save/
```

**Headers**

```http
Content-Type: application/json
X-Application-ID: APP-2025-00123
```

**Request Body**

```json
{
  "step": 5,
  "application_type": "government_program",
  "data": {
    "education_level": "SHS/Technical",
    "literacy_level": "Can Read & Write",
    "has_farming_experience": true,
    "years_in_poultry": "3.5",
    "has_existing_farm": true,
    "farming_full_time": false,
    "other_occupation": "Senior high school teacher",
    "previous_training": "Completed YEA broiler bootcamp in 2023 and attended GIZ biosecurity workshop.",
    "other_farming_activities": "Maize (2 acres) and catfish (small ponds)."
  }
}
```

**Successful Response (200)**

```json
{
  "success": true,
  "application_id": "APP-2025-00123",
  "step_completed": 5,
  "next_step": 6,
  "auto_saved": true,
  "last_saved_at": "2025-11-26T18:05:14Z",
  "validation_errors": {}
}
```

**Validation Errors (400)**

```json
{
  "success": false,
  "validation_errors": {
    "years_in_poultry": [
      "Enter a value between 0 and 50 years"
    ],
    "education_level": [
      "Select one of the allowed education levels"
    ]
  }
}
```

---

## Form Sections & Fields

### Section A: Education Snapshot

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `education_level` | Select | ✓ | Options mirror `farms.Farm.education_level` choices |
| `literacy_level` | Segmented control | ✓ | `Cannot Read/Write`, `Can Read Only`, `Can Read & Write` |

**UX Notes**
- Provide helper text linking literacy to training support (“We adapt materials based on your answer”).

### Section B: Poultry Experience

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `has_farming_experience` | Boolean toggle | ✓ | default `true` |
| `years_in_poultry` | Slider + numeric input | ✓ | 0–50 years, step 0.1 |

**Behavior**
- Disable `years_in_poultry` when `has_farming_experience=false`; auto-set to `"0"` but keep slider accessible once toggled back.
- Display derived experience level badge (Beginner/Intermediate/Expert) near slider.

### Section C: Current Operation

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `has_existing_farm` | Boolean cards | ✓ | “Yes, currently operating” / “No, starting new farm” |
| `farming_full_time` | Boolean toggle | ✓ | Visible only when `has_existing_farm=true` |
| `other_occupation` | Text input | Optional | Summary of day job if not full-time |

### Section D: Training & Other Activities

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `previous_training` | Textarea | Optional | Encourage bullet style (“Course – Year”) |
| `other_farming_activities` | Textarea | Optional | e.g., crops, livestock combos |

### Section E: Review Banner

- Display pill summarizing `experience_level`, `years_in_poultry`, `has_existing_farm`.
- Show messaging that experienced applicants move faster but new entrants are welcome (avoid discouraging novices).

---

## Validation Rules

### Frontend

1. **Education Level** – Must match enumerated options; default to placeholder (“Select education level”).
2. **Literacy Level** – Required radio group; enforce focus/ARIA states.
3. **Years in Poultry** – Accept numeric input between 0 and 50 with one decimal. If slider increments 0.1, format value to `number.toFixed(1)` before storing.
4. **Existing Farm Toggle** – Must be `true` or `false`; disallow `null` when advancing.
5. **Other Occupation** – Required only when `farming_full_time=false`. Limit to 120 characters.
6. **Training & Activities** – Optional but trimmed to 1,000 characters to keep review screens readable.

### Backend

- Validates decimal bounds (0 ≤ years ≤ 50) via `MinValueValidator/MaxValueValidator`.
- Casts `has_existing_farm` to boolean and uses it in queue scoring.
- Stores additional answers in the step payload for future migration to `farms.Farm`.

---

## UI/UX Requirements

1. **Stepper Continuity** – Progress indicator shows 5/7 with supportive copy “Almost there!”.
2. **Guided Copy** – Inline info card explaining why experience questions are asked (training personalization + queue priority).
3. **Live Badge** – Experience level badge updates instantly as slider moves (colors: Grey=Beginner, Blue=Intermediate, Gold=Expert).
4. **Unsaved Changes Chip** – Display whenever values diverge from last auto-save.
5. **Side-by-Side Layout** – On desktop, show slider + derived badge left, contextual copy right.
6. **Navigation Buttons** – `← Previous` goes to Step 4, `Next →` disabled until all required fields valid.
7. **Autosave Banner** – Reuse existing component; show spinner + timestamp.

---

## TypeScript Types

```typescript
export type EducationLevel =
  | 'No Formal Education'
  | 'Primary'
  | 'JHS'
  | 'SHS/Technical'
  | 'Tertiary'
  | 'Postgraduate';

export type LiteracyLevel =
  | 'Cannot Read/Write'
  | 'Can Read Only'
  | 'Can Read & Write';

export interface ExperienceInput {
  education_level: EducationLevel | '';
  literacy_level: LiteracyLevel | '';
  has_farming_experience: boolean | null;
  years_in_poultry: string; // decimal string to preserve 1dp precision
  has_existing_farm: boolean | null;
  farming_full_time: boolean | null;
  other_occupation?: string;
  previous_training?: string;
  other_farming_activities?: string;
}
```

---

## State Management & Auto-Save

- Store values under `form.experience` in the global form context.
- Local UI state (e.g., slider preview) should always sync back to canonical `experience` data to keep auto-save consistent.
- Auto-save hook mirrors prior steps:

```typescript
useAutoSave({
  interval: 30000,
  data: experience,
  enabled:
    Boolean(experience.education_level && experience.literacy_level) &&
    experience.has_existing_farm !== null &&
    experience.has_farming_experience !== null,
  onSave: async (payload) => saveDraft({ step: 5, data: payload })
});
```

- Pause auto-save when required fields invalid to avoid repetitive 400s; show inline tip instead.

---

## Derived Metrics & Helpers

```typescript
export type ExperienceLevel = 'Beginner' | 'Intermediate' | 'Expert';

export function deriveExperienceLevel(yearsValue: string): ExperienceLevel {
  const years = parseFloat(yearsValue || '0');
  if (years <= 1) return 'Beginner';
  if (years <= 5) return 'Intermediate';
  return 'Expert';
}
```

- Keep logic aligned with `farms.Farm.save()` which categorizes experience in the same way.
- Use derived level for:
  - Priority hints (“Intermediates usually complete onboarding in 2 weeks”).
  - Review summary chips in Step 7.

---

## Error Handling

1. **Inline Errors** – Display below each control; for sliders, show helper text under numeric input.
2. **Form Banner** – If backend returns spam-related flags (e.g., inconsistent answers), show dismissible alert linking to support.
3. **Auto-save Failures** – Provide toast with retry CTA and keep unsaved chip visible.
4. **Navigation Guard** – Warn when navigating away with unsaved edits.

---

## Accessibility & Mobile

- Radios and toggle buttons must be keyboard operable with visible focus state.
- Slider should expose `aria-valuemin`, `aria-valuemax`, and `aria-valuenow`; provide numeric input fallback for screen readers.
- Word counters for textareas announced via `aria-live="polite"` when nearing limits.
- On mobile, collapse optional fields behind an accordion labelled “Additional details (optional)” to reduce scroll fatigue.

---

## Example Implementation

```tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAutoSave } from '@/hooks/useAutoSave';
import type { ExperienceInput } from '@/types/application';
import { deriveExperienceLevel } from '@/utils/experience';

const DEFAULT_EXPERIENCE: ExperienceInput = {
  education_level: '',
  literacy_level: '',
  has_farming_experience: null,
  years_in_poultry: '0.0',
  has_existing_farm: null,
  farming_full_time: null,
  other_occupation: '',
  previous_training: '',
  other_farming_activities: ''
};

export default function ExperienceStep() {
  const router = useRouter();
  const [experience, setExperience] = useState(loadExperienceDraft() ?? DEFAULT_EXPERIENCE);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [isSaving, setIsSaving] = useState(false);

  const experienceLevel = deriveExperienceLevel(experience.years_in_poultry);

  useAutoSave({
    interval: 30000,
    data: experience,
    enabled: canAutosave(experience),
    onSave: async (data) => {
      setIsSaving(true);
      try {
        const response = await saveDraft({ step: 5, data });
        setErrors(response.validation_errors || {});
        persistExperienceDraft(data);
      } finally {
        setIsSaving(false);
      }
    }
  });

  const handleNext = async () => {
    const response = await saveDraft({ step: 5, data: experience, complete_step: true });
    if (response.success) {
      persistExperienceDraft(experience);
      router.push('/apply/step-6');
    } else {
      setErrors(response.validation_errors || {});
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <StepHeader step={5} title="Experience" description="Tell us about your poultry background." />

      <AutoSaveBanner isSaving={isSaving} lastSavedKey="step5_last_saved" />

      <EducationCard
        value={experience}
        errors={errors}
        onChange={(partial) => setExperience((prev) => ({ ...prev, ...partial }))}
      />

      <ExperienceCard
        value={experience}
        level={experienceLevel}
        errors={errors}
        onChange={(partial) => setExperience((prev) => ({ ...prev, ...partial }))}
      />

      <CurrentOperationCard
        value={experience}
        errors={errors}
        onChange={(partial) => setExperience((prev) => ({ ...prev, ...partial }))}
      />

      <TrainingCard
        value={experience}
        errors={errors}
        onChange={(partial) => setExperience((prev) => ({ ...prev, ...partial }))}
      />

      <div className="flex justify-between border-t pt-6">
        <Button variant="outline" onClick={() => router.push('/apply/step-4')}>
          ← Previous
        </Button>
        <Button onClick={handleNext} disabled={!isFormValid(experience)}>
          Next →
        </Button>
      </div>
    </div>
  );
}
```

Helper utilities (`loadExperienceDraft`, `persistExperienceDraft`, `canAutosave`, `isFormValid`, `saveDraft`) should live beside other step hooks for reuse/testing.

---

## Testing Checklist

### Functional

- [ ] Education and literacy selects enforce required validation and show helper text.
- [ ] Slider/input keeps `years_in_poultry` within 0–50 and formats to one decimal.
- [ ] Experience level badge updates instantly when value changes.
- [ ] Existing farm toggle cascades visibility of full-time and occupation fields.
- [ ] Optional textareas trim whitespace and enforce 1,000-character limit.
- [ ] Auto-save triggers only when form valid and shows timestamp.
- [ ] Navigating back/forward preserves data via draft persistence.

### Accessibility & Mobile

- [ ] Slider provides numeric fallback for screen readers.
- [ ] Toggle buttons reachable via keyboard/tab order.
- [ ] Sticky navigation buttons remain visible on mobile.

### Performance

- [ ] Autosave debounce prevents overlapping requests when quickly adjusting slider.
- [ ] Derived badge calculation memoized or lightweight (no unnecessary renders).

---

**Next Step:** After Step 5, route the applicant to [Step 6 – Program Details] when `application_type=government_program`, otherwise skip directly to Step 7 for review and submission.
