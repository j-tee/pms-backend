# Frontend Implementation Guide: Step 6 - Program Details
## Farm Application Form

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Step:** 6 of 7  
**Purpose:** Implementation reference for the Program Details stage of the apply-first workflow

---

## Table of Contents

1. [Overview](#overview)
2. [Program Data Model](#program-data-model)
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

Step 6 collects **government program metadata and mandatory supporting documents** for applicants whose `application_type === 'government_program'`. It ensures:

- A program cohort (batch) is selected so reviewers know which slot to allocate.
- Referral insights are recorded for outreach analytics.
- A minimum document package (ID + farm photos) is available before screening (referenced earlier by Step 3 via `ownership_document_url`).
- Applicants explicitly acknowledge program terms (auto-consent + eligibility summary).

Independent applicants skip this step and continue directly to Step 7.

### Workflow Context

```
Step 1: Introduction ✓
Step 2: Personal Information ✓
Step 3: Location Details ✓
Step 4: Farm Plans ✓
Step 5: Experience ✓
Step 6: Program Details ← GOVERNMENT APPLICANTS ONLY
Step 7: Review & Submit
```

### Persistence Rules

- Draft payload still posts to `POST /api/applications/draft/save/` with `step: 6`. Only `yea_program_batch` and `referral_source` live in the `FarmApplication` row today. All document metadata is stored via the document upload APIs and linked to the application ID.
- Skip logic: if `application_type !== 'government_program'`, mark `program_details_completed=true` client-side and navigate to Step 7 without calling the Step 6 save endpoint.
- Auto-save continues every 30 seconds but should only fire after a program batch has been selected and required documents meet minimum counts.

---

## Program Data Model

| Segment | Fields | Notes |
|---------|--------|-------|
| **Program Selection** | `yea_program_batch`, `program_snapshot` (name, support package, slots) | `yea_program_batch` maps to `FarmApplication.yea_program_batch`; `program_snapshot` is cached on the client for review screens |
| **Referral Insights** | `referral_source`, `referral_other_text` | Stored as free text today, but frontend enforces enumerated options for clean analytics |
| **Document Inventory** | `documents[]` of `{id, document_type, url}` | Backed by `FarmDocument` when the application is eventually approved; Step 6 uploads are stored against the application ID and re-linked later |
| **Compliance** | `accepted_program_terms`, `consent_timestamp` | Consent stored only in draft payload for now; reviewers see the timestamp in screening dashboard |

> Minimum document set: Ghana Card photo, Passport photo, **three** farm photos (Exterior, Interior, Layout). Optional uploads add credibility (land deeds, lease, additional infrastructure shots).

---

## API Contract

### 1. Fetch Active Programs

```
GET /api/public/programs/?status=active&fields=program_name,program_code,program_type,description,support_package_details,total_slots,slots_available,application_deadline
```

**Sample Response**

```json
[
  {
    "program_code": "YEA-2025-Q1",
    "program_name": "YEA Poultry Support Program 2025",
    "program_type": "comprehensive",
    "description": "Full support package including chicks, feed, training, and officer supervision.",
    "support_package_details": {
      "day_old_chicks": 500,
      "feed_bags_per_cycle": 100,
      "training_sessions": 12,
      "extension_visits_per_month": 2,
      "marketplace_subsidy_months": 12
    },
    "total_slots": 1000,
    "slots_available": 412,
    "application_deadline": "2025-03-31"
  }
]
```

### 2. Save Draft (Step 6)

```
POST /api/applications/draft/save/
```

**Request Body**

```json
{
  "step": 6,
  "application_type": "government_program",
  "data": {
    "yea_program_batch": "YEA-2025-Q1",
    "referral_source": "radio",
    "referral_other_text": null,
    "accepted_program_terms": true,
    "consent_timestamp": "2025-11-26T19:05:00Z"
  }
}
```

**Successful Response (200)**

```json
{
  "success": true,
  "application_id": "APP-2025-00123",
  "step_completed": 6,
  "next_step": 7,
  "auto_saved": true,
  "validation_errors": {}
}
```

### 3. Upload Document

```
POST /api/applications/documents/upload/
```

**Headers**

```http
Content-Type: multipart/form-data
X-Application-ID: APP-2025-00123
```

**Form Data**

| Key | Value |
|-----|-------|
| `document_type` | `Ghana Card` |
| `file` | (binary up to 5 MB; jpg/png/pdf) |

**Response**

```json
{
  "id": "doc_34d5f0fe",
  "document_type": "Ghana Card",
  "file_name": "ghana-card.jpg",
  "mime_type": "image/jpeg",
  "file_size": 402311,
  "url": "https://cdn.example.com/applications/APP-2025-00123/ghana-card.jpg",
  "uploaded_at": "2025-11-26T19:02:10Z"
}
```

### 4. Delete Document

```
DELETE /api/applications/documents/{document_id}/
```

Returns `204 No Content` on success. Use to replace outdated uploads.

---

## Form Sections & Fields

### Section A: Program Selector

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `yea_program_batch` | Searchable card list | ✓ | Cards show program name, summary, slots, and deadline. Selecting a card persists the `program_code`. |
| `program_snapshot` | Read-only summary | Auto | Store `program_name`, type, support highlights, and slot count for Step 7 review. |

**Behavior**
- Disable selection when `slots_available === 0` or deadline passed; show “Program full/closed” ribbon.
- Provide inline badge if user’s constituency not in the program’s eligible list once backend exposes it (future enhancement).

### Section B: Referral Insight

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `referral_source` | Segmented select | ✓ | Options: `extension_officer`, `radio`, `tv`, `social_media`, `search_engine`, `farmer_referral`, `community_event`, `advertisement`, `other`. |
| `referral_other_text` | Text input | Conditional | Required only when source is `other`; limit 120 chars. |

### Section C: Document Checklist

| Document Type | Required | Notes |
|---------------|----------|-------|
| Ghana Card Photo | ✓ | Clear photo of front of card. |
| Passport Photo | ✓ | Neutral background, max 2 MB recommended. |
| Farm Photo - Exterior | ✓ | Primary poultry house exterior. |
| Farm Photo - Interior | ✓ | Show equipment/housing layout. |
| Farm Photo - Layout | ✓ | Wide shot of entire farm. |
| Optional Extras | – | Feeding system, storage, lease agreements, business registration, etc. |

**Uploader UX**
- Drag & drop zone with file previews, progress bars, and document-type selector.
- Each tile surfaces verification status once backend reviews the doc (read-only flag `is_verified`).
- Provide quick links so Step 3 can reference an uploaded lease document by copying the URL (used for `ownership_document_url`).

### Section D: Terms & Consent

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `accepted_program_terms` | Checkbox | ✓ | Label should cite key bullet points (3-tier review, availability of officers, support obligations). |
| `consent_timestamp` | Auto hidden | ✓ | Set to `new Date().toISOString()` when the checkbox toggles to true and include in draft payload. |

### Section E: Program Health Banner

- Display countdown to application deadline and slot availability indicator (green ≥50%, amber 10–49%, red <10 or zero).
- Show top three support items (e.g., chicks, feed, training) pulled from `support_package_details`.

---

## Validation Rules

### Frontend

1. **Conditional Step** – Guard route so non-government applicants bypass Step 6 entirely.
2. **Program Selection** – `yea_program_batch` required; disable Next when not selected.
3. **Referral Source** – Must be one of the predefined options; show inline field for “Other”.
4. **Documents** – Enforce minimum uploads before enabling Next: `Ghana Card`, `Passport Photo`, and **at least three** distinct farm photos (Exterior, Interior, Layout). Validate file type (jpg/png/pdf) and size (<5 MB) before calling upload API.
5. **Consent** – `accepted_program_terms` must be true; re-prompt if unchecked before navigation.
6. **Upload Duplication** – Prevent multiple files with the same `document_type` unless explicitly allowed (e.g., multiple optional farm photos). Offer replace button rather than add duplicates for required docs.

### Backend

- Reject draft save when `yea_program_batch` missing for government applications (model validation already enforces this once data hits `FarmApplication`).
- Upload endpoint validates MIME type & size (mirrors `FarmDocument.clean`).
- If program closes between fetch and submission, backend returns `409 Program full` or `410 Deadline passed`; handle gracefully (see error handling section).

---

## UI/UX Requirements

1. **Progress Indicator** – Show 6/7 with supportive copy “Confirm your program slot”.
2. **Program Cards** – Include badges for `program_type` (Training, Subsidy, Comprehensive) and state (Open, Filling Fast, Full). Use skeleton loaders while fetching programs.
3. **Support Package Drawer** – Clicking “View package” reveals detailed JSON (converted to list) to set expectations about chicks, feed, and training commitments.
4. **Document Matrix** – Required rows pinned to top with check icons when uploaded; optional rows collapsible.
5. **Upload Feedback** – Display progress bar and success tick per file; show EXIF GPS match info once available.
6. **Auto-Save Banner** – Same component as prior steps; includes warning when auto-save disabled due to missing documents.
7. **Navigation Buttons** – `← Previous` returns to Step 5, `Next →` disabled until all required fields + docs + consent satisfied.

---

## TypeScript Types

```typescript
export type ReferralSource =
  | 'extension_officer'
  | 'radio'
  | 'tv'
  | 'social_media'
  | 'search_engine'
  | 'farmer_referral'
  | 'community_event'
  | 'advertisement'
  | 'other';

export type DocumentType =
  | 'Ghana Card'
  | 'Passport Photo'
  | 'Farm Photo - Exterior'
  | 'Farm Photo - Interior'
  | 'Farm Photo - Layout'
  | 'Farm Photo - Feeding'
  | 'Farm Photo - Water'
  | 'Farm Photo - Equipment'
  | 'Farm Photo - Storage'
  | 'Farm Photo - Biosecurity'
  | 'Title Deed'
  | 'Lease Agreement'
  | 'Chief Letter'
  | 'Survey Plan'
  | 'Business Registration'
  | 'Production Records'
  | 'Tax Clearance'
  | 'Other';

export interface ProgramSummary {
  program_code: string;
  program_name: string;
  program_type: string;
  description: string;
  support_package_details: Record<string, number | string>;
  total_slots: number;
  slots_available: number;
  application_deadline?: string;
}

export interface ProgramDetailsInput {
  yea_program_batch: string;
  program_snapshot: ProgramSummary | null;
  referral_source: ReferralSource | '';
  referral_other_text?: string;
  accepted_program_terms: boolean;
  consent_timestamp?: string;
}

export interface UploadedDocument {
  id: string;
  document_type: DocumentType;
  file_name: string;
  mime_type: string;
  file_size: number;
  url: string;
  uploaded_at: string;
  is_verified?: boolean;
}

export interface ProgramStepState extends ProgramDetailsInput {
  documents: UploadedDocument[];
}
```

---

## State Management & Auto-Save

- Store program data under `form.programDetails`. Uploaded documents can live in a shared `documents` slice so other steps (Step 3 land docs) can reference URLs without re-fetching.
- Auto-save trigger:

```typescript
useAutoSave({
  interval: 30000,
  data: programDetails,
  enabled:
    programDetails.yea_program_batch.length > 0 &&
    programDetails.accepted_program_terms &&
    hasRequiredDocs(documents),
  onSave: async (payload) => {
    await saveDraft({ step: 6, data: payload });
  }
});
```

- `hasRequiredDocs` should verify mandatory document types exist and are fully uploaded (no in-flight uploads).
- Pause auto-save while uploads are running to avoid wasted network calls; re-enable once queue empty.

---

## Derived Metrics & Helpers

```typescript
export type ProgramHealth = {
  slotStatus: 'healthy' | 'limited' | 'full';
  deadlineStatus: 'open' | 'closing-soon' | 'closed';
  deadlineLabel: string;
};

export function getProgramHealth(summary: ProgramSummary): ProgramHealth {
  const availability = summary.total_slots > 0
    ? (summary.slots_available / summary.total_slots) * 100
    : 0;

  let slotStatus: ProgramHealth['slotStatus'] = 'healthy';
  if (summary.slots_available === 0) slotStatus = 'full';
  else if (availability < 10) slotStatus = 'limited';

  let deadlineStatus: ProgramHealth['deadlineStatus'] = 'open';
  let deadlineLabel = 'No deadline';
  if (summary.application_deadline) {
    const daysLeft = Math.ceil(
      (new Date(summary.application_deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );
    if (daysLeft <= 0) {
      deadlineStatus = 'closed';
      deadlineLabel = 'Applications closed';
    } else if (daysLeft <= 7) {
      deadlineStatus = 'closing-soon';
      deadlineLabel = `${daysLeft} day(s) left`;
    } else {
      deadlineLabel = `${daysLeft} days left`;
    }
  }

  return { slotStatus, deadlineStatus, deadlineLabel };
}
```

- Use `ProgramHealth` to color the banner and CTA state (e.g., show warning if `slotStatus === 'full'`).
- Cache selected `ProgramSummary` in local storage so Step 7 can render details even if the list endpoint fails later.

---

## Error Handling

1. **Program Full/Closed** – If save response includes `{'code': 'program_full'}`, show modal instructing user to pick a different batch; automatically refresh the program list.
2. **Upload Failures** – Surface inline error with retry button; failed uploads should not count toward required document tally.
3. **Network Timeouts** – Provide fallback skeleton for program list with “Retry” CTA; keep previously selected program in memory.
4. **Permission Errors** – If upload endpoint returns 401/403, send user back to Step 1 to restart (token likely expired) and display support contact.
5. **Document Deletion Guard** – Prevent deleting required document without immediate replacement; ask for confirmation to avoid falling below minimum checks.

---

## Accessibility & Mobile

- Program cards rendered as radio buttons with `role="radiogroup"`; ensure keyboard navigation (arrow keys) cycles cards.
- File uploader must expose hidden `<input type="file">` with descriptive labels (e.g., `aria-label="Upload Ghana Card"`).
- Progress indicators announced via `aria-live="polite"` when uploads complete or fail.
- On mobile, collapse optional document categories and keep upload CTA sticky near bottom for thumb reach.

---

## Example Implementation

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAutoSave } from '@/hooks/useAutoSave';
import type { ProgramSummary, ProgramStepState, UploadedDocument } from '@/types/application';
import { getProgramHealth } from '@/utils/programs';

const DEFAULT_STATE: ProgramStepState = {
  yea_program_batch: '',
  program_snapshot: null,
  referral_source: '',
  referral_other_text: '',
  accepted_program_terms: false,
  consent_timestamp: undefined,
  documents: []
};

export default function ProgramDetailsStep() {
  const router = useRouter();
  const [state, setState] = useState<ProgramStepState>(loadProgramDraft() ?? DEFAULT_STATE);
  const [programs, setPrograms] = useState<ProgramSummary[]>([]);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingPrograms, setIsLoadingPrograms] = useState(true);

  useEffect(() => {
    if (!isGovernmentApplication()) {
      router.replace('/apply/step-7');
      return;
    }
    fetchPrograms();
  }, []);

  const fetchPrograms = async () => {
    setIsLoadingPrograms(true);
    try {
      const response = await fetch('/api/public/programs/?status=active');
      const data: ProgramSummary[] = await response.json();
      setPrograms(data);
    } finally {
      setIsLoadingPrograms(false);
    }
  };

  useAutoSave({
    interval: 30000,
    data: state,
    enabled: Boolean(state.yea_program_batch && state.accepted_program_terms && hasRequiredDocs(state.documents)),
    onSave: async (payload) => {
      setIsSaving(true);
      try {
        const response = await saveDraft({ step: 6, data: payload });
        setErrors(response.validation_errors || {});
        persistProgramDraft(payload);
      } finally {
        setIsSaving(false);
      }
    }
  });

  const handleProgramSelect = (summary: ProgramSummary) => {
    const health = getProgramHealth(summary);
    if (health.slotStatus === 'full' || health.deadlineStatus === 'closed') return;
    setState((prev) => ({
      ...prev,
      yea_program_batch: summary.program_code,
      program_snapshot: summary
    }));
  };

  const handleUploadComplete = (doc: UploadedDocument) => {
    setState((prev) => ({
      ...prev,
      documents: upsertDocument(prev.documents, doc)
    }));
  };

  const handleNext = async () => {
    const response = await saveDraft({ step: 6, data: state, complete_step: true });
    if (response.success) {
      persistProgramDraft(state);
      router.push('/apply/step-7');
    } else {
      setErrors(response.validation_errors || {});
      if (response.code === 'program_full') {
        fetchPrograms();
      }
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <StepHeader step={6} title="Program Details" description="Select your YEA batch and upload mandatory documents." />
      <AutoSaveBanner isSaving={isSaving} lastSavedKey="step6_last_saved" />

      <ProgramCardGrid
        loading={isLoadingPrograms}
        programs={programs}
        selectedCode={state.yea_program_batch}
        onSelect={handleProgramSelect}
        error={errors.yea_program_batch?.[0]}
      />

      <ReferralSection
        value={state}
        errors={errors}
        onChange={(partial) => setState((prev) => ({ ...prev, ...partial }))}
      />

      <DocumentChecklist
        documents={state.documents}
        onUploadComplete={handleUploadComplete}
        onDelete={(docId) => removeDocument(docId)}
        error={errors.documents?.[0]}
      />

      <ConsentCard
        accepted={state.accepted_program_terms}
        onToggle={(value) =>
          setState((prev) => ({
            ...prev,
            accepted_program_terms: value,
            consent_timestamp: value ? new Date().toISOString() : undefined
          }))
        }
        error={errors.accepted_program_terms?.[0]}
      />

      <div className="flex justify-between border-t pt-6">
        <Button variant="outline" onClick={() => router.push('/apply/step-5')}>
          ← Previous
        </Button>
        <Button onClick={handleNext} disabled={!canProceed(state)}>
          Next →
        </Button>
      </div>
    </div>
  );
}
```

Helper utilities (`hasRequiredDocs`, `upsertDocument`, `removeDocument`, `saveDraft`, `isGovernmentApplication`, `persistProgramDraft`, `loadProgramDraft`) should live alongside other step helpers for shared testing.

---

## Testing Checklist

### Functional

- [ ] Non-government applications skip Step 6 and load Step 7 without regression.
- [ ] Program cards fetch, render skeletons, and disable selection for closed/full programs.
- [ ] Selecting a program stores `program_snapshot` and persists through refresh via cached draft.
- [ ] Referral source control enforces required/optional fields correctly.
- [ ] Required document uploads enforce file type/size and show progress; deleting a required doc blocks navigation until replaced.
- [ ] Auto-save only fires when program + documents + consent satisfied and displays timestamp.
- [ ] Form prevents navigation when consent unchecked or documents missing.

### Error & Edge Cases

- [ ] Backend `program_full` response surfaces inline warning and forces user to re-select.
- [ ] Upload failure (500) shows retry button without counting toward requirement.
- [ ] Offline mode: Document list and selected program remain visible with offline indicator until connectivity restored.

### Accessibility & Mobile

- [ ] Program card radios operable via keyboard; selected card clearly indicated.
- [ ] File uploader accessible to screen readers (label + description).
- [ ] Mobile layout keeps navigation buttons sticky and collapses optional doc rows for shorter scroll.

---

**Next Step:** Upon successful completion of Step 6, route applicants to [Step 7 – Review & Submit]. Provide a summary card referencing the selected program and a table of uploaded documents for final confirmation.
