# Frontend Implementation Guide: Step 4 - Farm Plans
## Farm Application Form

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Step:** 4 of 7  
**Purpose:** Blueprint for building the Farm Plans step of the apply-first workflow

---

## Table of Contents

1. [Overview](#overview)
2. [Farm Plan Data Model](#farm-plan-data-model)
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

### Step Role

The Farm Plans step validates that the applicant has a coherent production strategy before reviewers invest time in the application. Data captured here feeds directly into:

- `FarmApplication` Section 2 (farm information & production plans)
- Spam detection heuristics (quality of farm name, land vs capacity ratios)
- Screening dashboards where officers compare planned capacity against local benchmarks

### Workflow Context

```
Step 1: Introduction ✓
Step 2: Personal Information ✓
Step 3: Location Details ✓
Step 4: Farm Plans ← CURRENT STEP
Step 5: Experience
Step 6: Program Details (government only)
Step 7: Review & Submit
```

### Persistence Rules

- Drafts continue to save through `POST /api/applications/draft/save/` with `step: 4`.
- Data maps one-to-one to `FarmApplication` fields: `proposed_farm_name`, `farm_location_description`, `land_size_acres`, `primary_production_type`, `planned_bird_capacity`.
- Auto-save interval remains 30 seconds. Unsaved edits should be clearly indicated to prevent accidental navigation.

---

## Farm Plan Data Model

| Segment | Fields | Notes |
|---------|--------|-------|
| **Identity & Branding** | `proposed_farm_name` | Stored exactly as entered; must be unique system-wide after approval |
| **Narrative Location** | `farm_location_description` | Free text describing landmarks, access, crop rotation intentions |
| **Land & Scale** | `land_size_acres` | Decimal (max 8 digits, 2 decimals). Represents total land committed to poultry |
| **Production Focus** | `primary_production_type` | Enum: `Layers`, `Broilers`, `Both` |
| **Capacity Planning** | `planned_bird_capacity` | Positive integer; number of birds planned per production cycle |

> Downstream services derive additional KPIs (land utilization, officer workload) from these fields, so accuracy is critical.

---

## API Contract

### Save Draft (Step 4)

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
  "step": 4,
  "application_type": "government_program",
  "data": {
    "proposed_farm_name": "Fountain Ridge Poultry",
    "farm_location_description": "Along the main road behind Fountain School, 2km from Community 8 market.",
    "land_size_acres": "2.50",
    "primary_production_type": "Layers",
    "planned_bird_capacity": 1500
  }
}
```

**Successful Response (200)**

```json
{
  "success": true,
  "application_id": "APP-2025-00123",
  "step_completed": 4,
  "next_step": 5,
  "auto_saved": true,
  "last_saved_at": "2025-11-26T17:42:10Z",
  "validation_errors": {}
}
```

**Validation Errors (400)**

```json
{
  "success": false,
  "validation_errors": {
    "proposed_farm_name": [
      "Farm name must be at least 5 characters",
      "Farm name contains disallowed pattern"
    ],
    "land_size_acres": [
      "Enter a value greater than 0"
    ],
    "planned_bird_capacity": [
      "Planned capacity must be at least 1"
    ]
  }
}
```

### Supporting Services

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/applications/farm-name/preview/` *(planned)* | POST | Returns slug + warnings from spam detector (front-end can fall back to inline heuristics if endpoint not yet available) |
| `/api/catalog/production-types/` *(static fallback)* | GET | Optional metadata for radio options (Layers, Broilers, Both) |
| `/api/analytics/capacity-benchmarks/?constituency=TEMA-EAST` *(read-only)* | GET | Provides median land size and bird capacity for contextual hints |

> If supporting endpoints are unavailable, use cached metadata from bootstrap JSON and rely on backend validation for spam detection.

---

## Form Sections & Fields

### Section A: Farm Identity

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `proposed_farm_name` | Text input | ✓ | 5–200 chars; auto-capitalize first letter of each word; show live slug preview |

**Guidance**
- Highlight best practices surfaced by `spam_detection`: avoid repetitive characters (e.g., "AAAA Farm"), keep vowels, do not copy applicant name verbatim.
- Show contextual chip if the name matches personal full name to warn users.

### Section B: Site Narrative

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `farm_location_description` | Textarea (multi-line) | ✓ | 50–600 characters recommended; include landmarks, road type, utilities |

**UX Notes**
- Provide template prompts ("Example: Located 2km north of ...")
- Word counter encourages detailed yet concise descriptions.

### Section C: Land & Scale

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `land_size_acres` | Decimal input | ✓ | > 0, max 8 digits, 2 decimals; format hint `e.g., 2.50` |

**Behavior**
- Accept numbers or decimals; convert to string w/ two decimals before submission to preserve precision.
- Display derived `birds_per_acre = planned_bird_capacity / land_size_acres` once both fields populated.

### Section D: Production Focus

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `primary_production_type` | Radio segment | ✓ | Options: `Layers`, `Broilers`, `Both` with short description per option |

**Conditional UI**
- If `Layers` or `Both`, show helper text "Expect egg production measurement in Step 5".
- If `Broilers` or `Both`, mention expected sales cadence.

### Section E: Capacity Planning

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `planned_bird_capacity` | Integer input | ✓ | ≥ 1; max 100,000 to prevent accidental zeros |

**UX Notes**
- Provide quick buttons (+100, +500) for incremental adjustments.
- Show "Projected birds per acre" indicator using derived metric.

### Section F: Review Summary

- Summary card surfaces name, land, production type, capacity.
- Include warning badges if derived density below 200 birds/acre (low utilization) or above 800 birds/acre (possible overstatement). Thresholds configurable.

---

## Validation Rules

### Frontend

1. **Farm Name** – 5–200 chars, allow letters, digits, spaces, `-` and `'`. Reject strings with >4 repeating characters or lacking vowels (mirrors spam detector hints).
2. **Description** – Minimum 50 characters to ensure meaningful detail; maximum 800 to keep review screens readable.
3. **Land Size** – Accept decimals only; enforce 2 decimal places client-side to match DB precision. Prevent zero or negative values.
4. **Production Type** – Must be one of the enumerated options; default to `Layers` but require explicit confirmation (no implicit selection).
5. **Planned Capacity** – Integer ≥1. If value exceeds 25,000 prompt user to confirm due to infrastructure implications.
6. **Density Check** – When both land and capacity present, compute `birds_per_acre`. If <100 or >2,000 show inline advisory but allow submission (final check occurs server-side).

### Backend

- Enforces same constraints plus uniqueness/spam heuristics (`FarmNameSpamDetector`).
- Normalizes whitespace and rejects duplicates found in pending applications.
- Logs suspicious payloads for officer follow-up (no extra work for frontend besides surfacing warnings returned in `validation_errors`).

---

## UI/UX Requirements

1. **Stepper Continuity** – Maintain progress indicator (4/7). Display copy reminding users they are halfway done.
2. **Guided Copy** – Provide side panel with tips: recommended stocking density, financing reminders, etc.
3. **Comparative Benchmarks** – If benchmark endpoint available, show "Typical farms in Tema East run 1,200 birds on 2 acres".
4. **Auto-Save Banner** – Same component as Steps 2 & 3. Show timestamp + spinner during network calls.
5. **Draft Chips** – When edits diverge from last save, place "Unsaved changes" chip near section header.
6. **Navigation** – `← Previous` goes back to Step 3; `Next →` disabled until all required fields valid.
7. **Mobile Layout** – Stack cards vertically; keep summary card sticky at bottom for quick review.

---

## TypeScript Types

```typescript
export type ProductionType = 'Layers' | 'Broilers' | 'Both';

export interface FarmPlanInput {
  proposed_farm_name: string;
  farm_location_description: string;
  land_size_acres: string; // keep as string for decimal precision
  primary_production_type: ProductionType;
  planned_bird_capacity: number | '';
}

export interface FarmPlanStepPayload extends FarmPlanInput {}
```

Derived helper type:

```typescript
export interface FarmPlanDerivedMetrics {
  birds_per_acre: number | null;
  density_flag: 'low' | 'ok' | 'high' | null;
}
```

---

## State Management & Auto-Save

- Reuse global form store (e.g., Zustand or React Context). Keep farm plan data under `form.farmPlan`.
- Local state holds transient UI bits (density flag, warnings). Only canonical values go into `saveDraft` payload.
- Auto-save hook
  ```typescript
  useAutoSave({
    interval: 30000,
    data: farmPlan,
    enabled: Boolean(farmPlan.proposed_farm_name),
    onSave: async (data) => {
      await saveDraft({ step: 4, data });
    }
  });
  ```
- Disable auto-save if form invalid to avoid repeated 400s; instead show banner instructing user to fix highlighted fields.

---

## Derived Metrics & Helpers

```typescript
export function calculateBirdsPerAcre(plan: FarmPlanInput): FarmPlanDerivedMetrics {
  const acres = Number(plan.land_size_acres);
  if (!acres || acres <= 0 || !plan.planned_bird_capacity) {
    return { birds_per_acre: null, density_flag: null };
  }
  const birdsPerAcre = plan.planned_bird_capacity / acres;
  let flag: FarmPlanDerivedMetrics['density_flag'] = 'ok';
  if (birdsPerAcre < 150) flag = 'low';
  if (birdsPerAcre > 1500) flag = 'high';
  return { birds_per_acre: Math.round(birdsPerAcre), density_flag: flag };
}
```

- Use derived metrics purely for UX hints; do **not** send them to backend.
- Surface warnings inline (e.g., "Density appears low for Layers farms in Tema East").

---

## Error Handling

1. **Inline Field Errors** – tie server messages to fields (use `validation_errors.proposed_farm_name`).
2. **Form-level Alerts** – if backend returns spam flags (e.g., `farm_name_contains_crypto`), show dismissible alert referencing official naming policy.
3. **Auto-save Failures** – show toast + keep retry queue. Provide "Retry now" button.
4. **Navigation Guard** – warn if user attempts to leave with `isDirty=true`.

---

## Accessibility & Mobile

- All inputs labeled and grouped; radios presented as accessible button group with `role="radiogroup"`.
- Word counter for description uses `aria-live="polite"` to announce remaining characters.
- Derived metric chips announced when they change to keep keyboard users informed.
- On mobile, keep Next/Previous buttons sticky for easier navigation.

---

## Example Implementation

```tsx
'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAutoSave } from '@/hooks/useAutoSave';
import type { FarmPlanInput } from '@/types/application';
import { calculateBirdsPerAcre } from '@/utils/farmPlan';

const DEFAULT_PLAN: FarmPlanInput = {
  proposed_farm_name: '',
  farm_location_description: '',
  land_size_acres: '',
  primary_production_type: 'Layers',
  planned_bird_capacity: ''
};

export default function FarmPlansStep() {
  const router = useRouter();
  const [plan, setPlan] = useState<FarmPlanInput>(loadPlanDraft() ?? DEFAULT_PLAN);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [isSaving, setIsSaving] = useState(false);

  const metrics = useMemo(() => calculateBirdsPerAcre(plan), [plan]);

  useAutoSave({
    interval: 30000,
    data: plan,
    enabled: Boolean(plan.proposed_farm_name && plan.land_size_acres && plan.planned_bird_capacity),
    onSave: async (data) => {
      setIsSaving(true);
      try {
        const response = await saveDraft({ step: 4, data });
        setErrors(response.validation_errors || {});
        persistPlanDraft(data);
      } finally {
        setIsSaving(false);
      }
    }
  });

  const handleNext = async () => {
    const response = await saveDraft({ step: 4, data: plan, complete_step: true });
    if (response.success) {
      persistPlanDraft(plan);
      router.push('/apply/step-5');
    } else {
      setErrors(response.validation_errors || {});
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <StepHeader step={4} title="Farm Plans" description="Describe how you intend to run your poultry operation." />

      <AutoSaveBanner isSaving={isSaving} lastSavedKey="step4_last_saved" />

      <FarmNameCard
        value={plan.proposed_farm_name}
        error={errors.proposed_farm_name?.[0]}
        onChange={(value) => setPlan((prev) => ({ ...prev, proposed_farm_name: value }))}
      />

      <DescriptionCard
        value={plan.farm_location_description}
        error={errors.farm_location_description?.[0]}
        onChange={(value) => setPlan((prev) => ({ ...prev, farm_location_description: value }))}
      />

      <LandAndCapacityCard
        plan={plan}
        errors={errors}
        metrics={metrics}
        onChange={(partial) => setPlan((prev) => ({ ...prev, ...partial }))}
      />

      <SummaryCard plan={plan} metrics={metrics} />

      <div className="flex justify-between border-t pt-6">
        <Button variant="outline" onClick={() => router.push('/apply/step-3')}>
          ← Previous
        </Button>
        <Button onClick={handleNext} disabled={!isFormValid(plan)}>
          Next →
        </Button>
      </div>
    </div>
  );
}
```

Helper utilities (`loadPlanDraft`, `persistPlanDraft`, `saveDraft`, `isFormValid`) should live beside other step hooks for reuse/testing.

---

## Testing Checklist

### Functional

- [ ] Farm name validation enforces length + allowed characters.
- [ ] Description enforces minimum characters and shows live counter.
- [ ] Land size accepts two decimal places and rejects zero/negative input.
- [ ] Production type switches radio state and persists selection across reloads.
- [ ] Planned capacity input prevents non-numeric characters and supports arrow increments.
- [ ] Density indicator updates instantly when land or capacity changes.
- [ ] Auto-save triggers only when form valid and shows last saved timestamp.
- [ ] Navigating back/forward preserves entered data.

### Performance

- [ ] Farm name quality hints debounce network call (if endpoint available) to ≥400 ms.
- [ ] Derived metrics calculations memoized to avoid re-renders.

### Accessibility

- [ ] Radios accessible via keyboard; focus ring visible.
- [ ] Word counter announced via ARIA when thresholds crossed.
- [ ] Error summaries include anchor links to affected fields.

### Cross-Browser

- [ ] Chrome / Firefox / Edge / Safari (desktop)
- [ ] Safari iOS / Chrome Android (mobile form layout + sticky CTA)

---

**Next Step:** After Step 4 validation succeeds, route applicants to [Step 5 – Experience] to capture background and skills data.
