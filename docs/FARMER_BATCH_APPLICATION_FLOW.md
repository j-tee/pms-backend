# 🚜 Farmer Application Flow: Batch Selection Process

**Date:** November 27, 2025  
**Audience:** Frontend Team, Product Managers  
**Status:** ✅ **FINAL SPECIFICATION**

---

## 📋 Executive Summary

This document clarifies the **farmer enrollment journey** in the YEA Poultry Program, specifically addressing **when and how farmers select program batches**.

### Key Decision:
✅ **Farmers select a specific batch DURING the application process**  
❌ **NOT** assigned to a batch after approval

---

## 🎯 Core Concept

### What This Means:
When a farmer applies to the YEA Poultry Program, they must:
1. Browse available **active batches**
2. Choose a **specific batch** to apply to
3. Submit their application **linked to that batch**
4. Get screened/approved **for that specific batch**
5. If approved, they are enrolled **in that same batch**

### Why This Design?
Each batch has specific characteristics:
- **Regional focus**: Some batches target specific regions/constituencies
- **Timeline**: Different start dates, training schedules, distribution dates
- **Capacity**: Limited slots per batch (e.g., 100 farmers per batch)
- **Support package**: Each batch may have different support details
- **Requirements**: Some batches may have specific eligibility criteria

**Result**: Farmers need to choose the batch that fits their location, timing, and needs.

---

## 🔄 Complete Farmer Journey

### Step 1: Browse Available Batches
**Frontend Page**: Public Batches Listing

**Farmer sees:**
```
Available Program Batches
────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────┐
│ 2025 Q2 Batch - Greater Accra                               │
│ Applications: Open until May 31, 2025                       │
│ Start Date: June 1, 2025                                    │
│ Target Region: Greater Accra                                │
│ Available Slots: 45 out of 100                              │
│ [View Details] [Apply Now]                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 2025 Q3 Batch - Ashanti Region                              │
│ Applications: Open until August 31, 2025                    │
│ Start Date: September 1, 2025                               │
│ Target Region: Ashanti                                      │
│ Available Slots: 80 out of 150                              │
│ [View Details] [Apply Now]                                  │
└─────────────────────────────────────────────────────────────┘
```

**API Endpoint:**
```http
GET /api/public/programs/
```

**Query Filters:**
- `is_active=true` - Only show active batches
- `is_published=true` - Only show published batches
- `accepting_applications=true` - Only show batches accepting applications
- `target_region=Greater Accra` - Filter by farmer's region (optional)

**Response Example:**
```json
{
  "count": 2,
  "results": [
    {
      "id": "uuid-1",
      "batch_name": "2025 Q2 Batch - Greater Accra",
      "batch_code": "YEA-2025-Q2-ACCRA",
      "description": "Second quarter recruitment for Greater Accra...",
      "target_region": "Greater Accra",
      "target_constituencies": ["Tema East", "Tema West"],
      "start_date": "2025-06-01",
      "application_deadline": "2025-05-31",
      "total_slots": 100,
      "approved_applications_count": 55,
      "available_slots": 45,
      "support_package_details": {
        "day_old_chicks": 1000,
        "starter_feed_bags": 3,
        "training_hours": 40
      },
      "is_active": true,
      "is_published": true,
      "accepts_applications": true
    }
  ]
}
```

### Step 2: View Batch Details
**Frontend Page**: Batch Detail Page

**Farmer can see:**
- Full batch description
- Eligibility requirements
- Support package breakdown
- Timeline (application deadline, start date, end date)
- Training schedule
- Distribution dates for chicks/feed
- Regional focus
- Available slots

**CTA Button**: "Apply to This Batch"

### Step 3: Start Application
**Frontend Page**: Application Form

**Key Field:**
```typescript
interface ApplicationFormData {
  // Farmer selects from dropdown or it's pre-selected from previous page
  program_batch_id: string;  // REQUIRED - The batch UUID
  
  // Farm information
  farm_id: string;  // If farmer already has registered farm
  // OR new farm details if registering for first time
  
  // Supporting documents
  documents: File[];
  
  // Additional info...
}
```

**UI Example:**
```
Apply to YEA Poultry Program
────────────────────────────────────────────────────

Selected Batch: 2025 Q2 Batch - Greater Accra ✓
[Change Batch]

Farm Details:
[Farm Name Field]
[Location Fields]
...

Supporting Documents:
[Upload Area]

[Submit Application]
```

**Important**: 
- Batch is selected BEFORE filling out the rest of the form
- Farmer can change their batch selection before submitting
- Once submitted, the application is linked to that specific batch

### Step 4: Submit Application
**API Endpoint:**
```http
POST /api/farmer/applications/
```

**Request Payload:**
```json
{
  "program_batch": "uuid-of-selected-batch",  // ✅ REQUIRED
  "farm": "uuid-of-farm",
  "farmer_name": "John Doe",
  "farmer_phone": "+233241234567",
  "farmer_email": "john@example.com",
  "farm_location": "Tema, Greater Accra",
  "experience_years": 2,
  "poultry_housing_type": "open_sided",
  "has_water_source": true,
  "supporting_documents": [
    {
      "document_type": "id_card",
      "file_url": "https://..."
    }
  ]
}
```

**Backend Validation:**
```python
# In ProgramEnrollmentApplication model
program_batch = models.ForeignKey(
    ProgramBatch,
    on_delete=models.CASCADE,
    related_name='applications',
    help_text="YEA Poultry Program batch/cohort farmer is applying to"
)

# Unique constraint ensures one application per farm per batch
class Meta:
    unique_together = [['farm', 'program']]
```

**What Happens:**
1. ✅ Application record created with `program_batch` foreign key
2. ✅ Application linked to specific batch permanently
3. ✅ Farmer receives confirmation with batch details
4. ✅ Admin can see application in that batch's application list

### Step 5: Application Review
**Admin Dashboard**: Applications List (Filtered by Batch)

**Admin sees:**
```
2025 Q2 Batch - Greater Accra
Applications Management
────────────────────────────────────────────────────────

Total Applications: 175
Pending Review: 45
Approved: 55
Rejected: 75

[Filter by Status] [Export List]

Farmer Name | Phone | Location | Status | Screening | Actions
─────────────────────────────────────────────────────────────
John Doe    | +233... | Tema | Pending | Not Started | [Review]
Jane Smith  | +233... | Accra | Under Review | In Progress | [View]
...
```

**Key Point**: Each batch has its own application pool.

### Step 6: Screening Process
**Workflow:**
1. Document verification
2. Farm site visit (if required)
3. Eligibility check
4. Capacity assessment
5. Final approval/rejection

**Status Updates:**
```python
APPLICATION_STATUS_CHOICES = [
    ('pending', 'Pending Review'),
    ('under_review', 'Under Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('withdrawn', 'Withdrawn'),
]
```

### Step 7: Approval & Enrollment
**If Approved:**

**API automatically updates:**
```python
# Application approved
application.status = 'approved'
application.approved_at = timezone.now()
application.approved_by = admin_user
application.save()

# Farmer is now enrolled in THAT batch
# No additional batch assignment needed
# The program_batch foreign key handles everything
```

**Farmer Notification:**
```
Congratulations! 🎉

Your application to the YEA Poultry Program has been APPROVED.

Batch Details:
• Batch Name: 2025 Q2 Batch - Greater Accra
• Start Date: June 1, 2025
• Training Date: June 5-7, 2025
• Chick Distribution: June 15, 2025
• Location: Tema Community Center

Next Steps:
1. Attend mandatory orientation on June 5, 2025
2. Prepare your poultry housing
3. Arrange transportation for chick collection

[View Full Details] [Download Schedule]
```

**Frontend Dashboard:**
```
My Program Enrollment
────────────────────────────────────────────────────────

Status: ✅ APPROVED

Enrolled Batch: 2025 Q2 Batch - Greater Accra
Program Timeline:
• Training: June 5-7, 2025
• Chick Distribution: June 15, 2025 (1000 chicks)
• Feed Collection: June 15, 2025 (3 bags starter feed)
• Expected Harvest: September 2025

[View Training Materials] [Contact Support]
```

---

## 🎯 Key Data Model Relationships

### Database Structure
```python
# The critical relationship
class ProgramEnrollmentApplication(models.Model):
    # Farmer selects this during application
    program_batch = models.ForeignKey(
        ProgramBatch,
        on_delete=models.CASCADE,
        related_name='applications'  # batch.applications.all()
    )
    
    farm = models.ForeignKey(
        'farms.Farm',
        on_delete=models.CASCADE,
        related_name='program_applications'  # farm.program_applications.all()
    )
    
    # One application per farm per batch
    class Meta:
        unique_together = [['farm', 'program']]
```

### Query Examples

**Get all applications for a specific batch:**
```python
batch = ProgramBatch.objects.get(batch_code="YEA-2025-Q2-ACCRA")
applications = batch.applications.all()
approved_farmers = batch.applications.filter(status='approved')
```

**Get farmer's application history:**
```python
farm = Farm.objects.get(id=farm_id)
applications = farm.program_applications.all()
current_batch = farm.program_applications.filter(
    status='approved'
).first().program_batch
```

---

## 🚫 What Farmers CANNOT Do

### ❌ Apply Without Selecting a Batch
```
Error: You must select a program batch to apply to.
```

### ❌ Apply to Multiple Batches Simultaneously
```
Error: You already have a pending application for the 2025 Q2 Batch.
You can only have one active application at a time.
```

**Constraint Enforcement:**
```python
# Database constraint
unique_together = [['farm', 'program']]

# This prevents:
# 1. Multiple applications to same batch from same farm
# 2. Application without batch selection (foreign key is required)
```

### ❌ Change Batch After Application Submission
Once submitted, the application is permanently linked to that batch.

**If farmer wants to join a different batch:**
1. Withdraw current application
2. Submit new application to different batch

### ❌ Get Auto-Assigned to a Batch
Admin cannot move approved farmers between batches. The batch selection is permanent from application time.

---

## 🎨 Frontend Implementation Guide

### 1. Public Batches Listing Component

**Component**: `<PublicBatchesList />`

```typescript
interface PublicBatch {
  id: string;
  batch_name: string;
  batch_code: string;
  description: string;
  target_region: string;
  target_constituencies: string[];
  application_deadline: string;
  start_date: string;
  available_slots: number;
  total_slots: number;
  support_package_details: {
    day_old_chicks: number;
    starter_feed_bags: number;
    training_hours: number;
  };
  accepts_applications: boolean;
}

// Usage
function PublicBatchesList() {
  const [batches, setBatches] = useState<PublicBatch[]>([]);
  
  useEffect(() => {
    fetchActiveBatches();
  }, []);
  
  async function fetchActiveBatches() {
    const response = await api.get('/api/public/programs/', {
      params: {
        is_active: true,
        is_published: true,
        accepts_applications: true
      }
    });
    setBatches(response.data.results);
  }
  
  return (
    <div>
      <h1>Available Program Batches</h1>
      {batches.map(batch => (
        <BatchCard 
          key={batch.id} 
          batch={batch}
          onApply={() => navigateToApplication(batch.id)}
        />
      ))}
    </div>
  );
}
```

### 2. Application Form Component

**Component**: `<ApplicationForm />`

```typescript
interface ApplicationFormData {
  program_batch_id: string;  // ✅ CRITICAL FIELD
  farm_id?: string;
  farmer_name: string;
  // ... other fields
}

function ApplicationForm({ preSelectedBatchId }: { preSelectedBatchId?: string }) {
  const [formData, setFormData] = useState<ApplicationFormData>({
    program_batch_id: preSelectedBatchId || '',
    // ...
  });
  
  const [selectedBatch, setSelectedBatch] = useState<PublicBatch | null>(null);
  
  useEffect(() => {
    if (formData.program_batch_id) {
      fetchBatchDetails(formData.program_batch_id);
    }
  }, [formData.program_batch_id]);
  
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    
    // Validate batch selection
    if (!formData.program_batch_id) {
      alert('Please select a program batch');
      return;
    }
    
    try {
      await api.post('/api/farmer/applications/', {
        program_batch: formData.program_batch_id,
        // ... other fields
      });
      
      alert('Application submitted successfully!');
      navigate('/application-success');
    } catch (error) {
      // Handle errors
    }
  }
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Batch Selection */}
      <div className="batch-selection">
        <label>Selected Batch *</label>
        {selectedBatch ? (
          <div className="selected-batch-card">
            <h3>{selectedBatch.batch_name}</h3>
            <p>Application Deadline: {selectedBatch.application_deadline}</p>
            <button type="button" onClick={() => setShowBatchSelector(true)}>
              Change Batch
            </button>
          </div>
        ) : (
          <button type="button" onClick={() => setShowBatchSelector(true)}>
            Select Batch
          </button>
        )}
      </div>
      
      {/* Rest of form */}
      <input name="farmer_name" {...} />
      {/* ... */}
      
      <button type="submit" disabled={!formData.program_batch_id}>
        Submit Application
      </button>
    </form>
  );
}
```

### 3. Admin Applications List (Filtered by Batch)

**Component**: `<BatchApplicationsList />`

```typescript
function BatchApplicationsList({ batchId }: { batchId: string }) {
  const [applications, setApplications] = useState([]);
  
  useEffect(() => {
    fetchApplicationsForBatch();
  }, [batchId]);
  
  async function fetchApplicationsForBatch() {
    const response = await api.get(`/api/admin/programs/${batchId}/applications/`);
    setApplications(response.data);
  }
  
  return (
    <div>
      <h2>Applications for Batch</h2>
      <table>
        <thead>
          <tr>
            <th>Farmer Name</th>
            <th>Phone</th>
            <th>Location</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {applications.map(app => (
            <tr key={app.id}>
              <td>{app.farmer_name}</td>
              <td>{app.farmer_phone}</td>
              <td>{app.farm_location}</td>
              <td><StatusBadge status={app.status} /></td>
              <td>
                <button onClick={() => reviewApplication(app.id)}>
                  Review
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## ✅ Testing Checklist

### User Flow Testing

**Farmer Journey:**
- [ ] Farmer can browse available batches
- [ ] Farmer can view batch details
- [ ] Farmer can select a batch before applying
- [ ] Farmer can change batch selection before submitting
- [ ] Application form requires batch selection
- [ ] Application submission includes batch_id
- [ ] Farmer cannot submit without selecting batch
- [ ] Farmer receives confirmation with batch details
- [ ] Farmer can view their enrolled batch after approval

**Admin Journey:**
- [ ] Admin can view applications grouped by batch
- [ ] Admin can filter applications by batch
- [ ] Admin can see batch details for each application
- [ ] Admin can approve/reject applications
- [ ] Approved farmers are automatically enrolled in their selected batch
- [ ] Admin can view enrolled farmers per batch
- [ ] Admin can see batch capacity (slots filled/available)

### API Testing

**Batch Listing:**
```bash
# Test public batches endpoint
curl -X GET "http://localhost:8000/api/public/programs/?is_active=true&accepts_applications=true"

# Expected: List of active batches accepting applications
```

**Application Submission:**
```bash
# Test application with batch selection
curl -X POST "http://localhost:8000/api/farmer/applications/" \
  -H "Content-Type: application/json" \
  -d '{
    "program_batch": "batch-uuid",
    "farm": "farm-uuid",
    "farmer_name": "Test Farmer",
    "farmer_phone": "+233241234567"
  }'

# Expected: 201 Created with application details
```

**Duplicate Application Prevention:**
```bash
# Test submitting second application to same batch
curl -X POST "http://localhost:8000/api/farmer/applications/" \
  -H "Content-Type: application/json" \
  -d '{
    "program_batch": "same-batch-uuid",
    "farm": "same-farm-uuid",
    ...
  }'

# Expected: 400 Bad Request - "You already have an application for this batch"
```

### Database Constraint Testing

**Unique Constraint:**
```python
# Test in Django shell
from farms.models import ProgramEnrollmentApplication, ProgramBatch, Farm

batch = ProgramBatch.objects.first()
farm = Farm.objects.first()

# Create first application (should succeed)
app1 = ProgramEnrollmentApplication.objects.create(
    program_batch=batch,
    farm=farm,
    farmer_name="Test",
    status='pending'
)

# Try to create duplicate (should fail)
try:
    app2 = ProgramEnrollmentApplication.objects.create(
        program_batch=batch,
        farm=farm,
        farmer_name="Test",
        status='pending'
    )
except IntegrityError:
    print("✅ Duplicate prevented correctly")
```

---

## 📊 Business Logic Summary

### Batch Capacity Management
```python
# In ProgramBatch model
@property
def available_slots(self):
    """Calculate remaining slots in batch"""
    approved_count = self.applications.filter(status='approved').count()
    return self.total_slots - approved_count

@property
def is_full(self):
    """Check if batch has reached capacity"""
    return self.available_slots <= 0

@property
def accepts_applications(self):
    """Check if batch is accepting new applications"""
    if not self.is_active or not self.is_published:
        return False
    if self.is_full:
        return False
    if timezone.now().date() > self.application_deadline:
        return False
    return True
```

### Application Rules
1. ✅ Farmer must select batch BEFORE applying
2. ✅ One application per farm per batch
3. ✅ Cannot apply to full batches
4. ✅ Cannot apply after deadline
5. ✅ Cannot change batch after submission
6. ✅ Must withdraw to apply to different batch

---

## 🆘 Common Questions

**Q: Can a farmer apply to multiple batches at once?**  
A: No. The `unique_together = [['farm', 'program']]` constraint allows only one application per batch. However, if their application is rejected or withdrawn, they can apply to a different batch.

**Q: Can admin reassign a farmer to a different batch?**  
A: No. The batch is selected by the farmer during application and is permanent. The only way to change batches is for the farmer to withdraw and reapply.

**Q: What if a batch becomes full while a farmer is filling out the application?**  
A: The frontend should check availability before showing the form. The backend will reject the submission if the batch is full.

**Q: Can a farmer see all batches or only those for their region?**  
A: Farmers can see all active batches, but they can filter by region. The `target_region` field helps farmers find relevant batches.

**Q: What happens to applications when a batch is closed/deactivated?**  
A: Existing applications remain in the system. Farmers with approved applications stay enrolled. New applications are prevented.

---

## 📚 Related Documentation

- [Batch Terminology Update](./BATCH_TERMINOLOGY_UPDATE.md) - Backend field name changes
- [Program Enrollment Models](../farms/program_enrollment_models.py) - Source code reference
- [API Documentation](./PROGRAMS_MANAGEMENT_API.md) - Complete API reference

---

**Last Updated**: November 27, 2025  
**Document Version**: 1.0  
**Author**: Backend Team
