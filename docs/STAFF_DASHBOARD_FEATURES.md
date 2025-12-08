# Staff Dashboard Feature Matrix
## YEA Poultry Management System

**Last Updated:** December 4, 2025  
**Purpose:** Define which features are visible to each staff role in the unified staff dashboard

---

## Overview

The staff dashboard (`/staff/dashboard`) is used by ALL YEA officials and staff members. Features are shown/hidden based on the user's role and permissions.

---

## Feature Visibility Matrix

| Feature/Section | NATIONAL_ADMIN | CONSTITUENCY_OFFICIAL | PROCUREMENT_OFFICER | VETERINARY_OFFICER | AUDITOR |
|----------------|----------------|----------------------|--------------------|--------------------|---------|
| **Dashboard Overview** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Application Management** |
| View Applications | ✅ All | ✅ Constituency | ❌ | ❌ | ✅ Read-only |
| Approve Applications | ✅ Final tier | ✅ Constituency tier | ❌ | ❌ | ❌ |
| Reject Applications | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Farm Management** |
| View Farms | ✅ All | ✅ Constituency | ✅ All (for health) | ✅ All (for health) | ✅ All (read-only) |
| Edit Farm Status | ✅ | ✅ Limited | ❌ | ❌ | ❌ |
| Assign Extension Officers | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Procurement** |
| View Purchase Orders | ✅ | ❌ | ✅ | ❌ | ✅ Read-only |
| Create Purchase Orders | ✅ | ❌ | ✅ | ❌ | ❌ |
| Manage Suppliers | ✅ | ❌ | ✅ | ❌ | ❌ |
| Distribute Supplies | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Health & Veterinary** |
| View Health Records | ✅ | ✅ Limited | ❌ | ✅ | ✅ Read-only |
| Investigate Mortality | ✅ | ❌ | ❌ | ✅ | ✅ Read-only |
| Verify Compensation Claims | ✅ | ❌ | ❌ | ✅ | ❌ |
| Prescribe Treatments | ❌ | ❌ | ❌ | ✅ | ❌ |
| Impose Quarantine | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Audit & Compliance** |
| View Audit Logs | ✅ | ❌ | ❌ | ❌ | ✅ |
| Initiate Audits | ✅ | ❌ | ❌ | ❌ | ✅ |
| View Fraud Alerts | ✅ | ❌ | ❌ | ❌ | ✅ |
| Investigate Fraud | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Financial** |
| View Platform Revenue | ✅ | ❌ | ❌ | ❌ | ✅ Read-only |
| View Payout History | ✅ | ❌ | ❌ | ❌ | ✅ Read-only |
| Process Payouts | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Reports & Analytics** |
| National Reports | ✅ | ❌ | ❌ | ❌ | ✅ |
| Regional Reports | ✅ | ❌ | ❌ | ❌ | ✅ |
| Constituency Reports | ✅ | ✅ Own only | ❌ | ❌ | ✅ |
| Procurement Reports | ✅ | ❌ | ✅ | ❌ | ✅ |
| Health Reports | ✅ | ❌ | ❌ | ✅ | ✅ |
| **User Management** |
| View Users | ✅ | ✅ Limited | ❌ | ❌ | ✅ Read-only |
| Create Users | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign Roles | ✅ | ❌ | ❌ | ❌ | ❌ |
| Suspend Users | ✅ | ❌ | ❌ | ❌ | ❌ |
| **System Settings** |
| View Settings | ✅ | ❌ | ❌ | ❌ | ❌ |
| Edit Settings | ✅ | ❌ | ❌ | ❌ | ❌ |
| Manage Programs | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## Dashboard Sections

### 1. Overview/Home
**Visible to:** All staff  
**Content varies by role:**
- **NATIONAL_ADMIN**: National statistics, pending approvals, system alerts
- **CONSTITUENCY_OFFICIAL**: Constituency statistics, pending applications, local alerts
- **PROCUREMENT_OFFICER**: Inventory levels, pending orders, distribution schedule
- **VETERINARY_OFFICER**: Disease alerts, mortality trends, vaccination schedule
- **AUDITOR**: Fraud alerts, audit cases, compliance issues

### 2. Applications
**Visible to:** NATIONAL_ADMIN, CONSTITUENCY_OFFICIAL, AUDITOR (read-only)  
**Features:**
- Application queue
- Review and approve/reject
- Application history
- Status tracking

### 3. Farms
**Visible to:** All staff (content filtered by role)  
**Features:**
- Farm directory
- Farm details
- Production data (if permitted)
- Health records (if permitted)

### 4. Procurement
**Visible to:** PROCUREMENT_OFFICER, NATIONAL_ADMIN, AUDITOR (read-only)  
**Features:**
- Purchase orders
- Supplier management
- Inventory tracking
- Distribution management

### 5. Health & Veterinary
**Visible to:** VETERINARY_OFFICER, NATIONAL_ADMIN, AUDITOR (read-only)  
**Features:**
- Disease monitoring
- Mortality investigations
- Vaccination tracking
- Compensation claims

### 6. Audit & Compliance
**Visible to:** AUDITOR, NATIONAL_ADMIN  
**Features:**
- Audit logs
- Fraud detection
- Compliance reports
- Investigation tools

### 7. Reports
**Visible to:** All staff (reports vary by role)  
**Features:**
- Dashboard-specific reports
- Export functionality
- Scheduled reports

### 8. User Management
**Visible to:** NATIONAL_ADMIN, CONSTITUENCY_OFFICIAL (limited)  
**Features:**
- User directory
- Role assignment
- Account management

### 9. Settings
**Visible to:** NATIONAL_ADMIN only  
**Features:**
- System configuration
- Program management
- Notification settings

---

## Navigation Menu Structure

### For NATIONAL_ADMIN
```
- Dashboard
- Applications
- Farms
- Procurement
- Health & Veterinary
- Audit & Compliance
- Reports
- User Management
- Settings
```

### For CONSTITUENCY_OFFICIAL
```
- Dashboard
- Applications
- Farms
- Reports
```

### For PROCUREMENT_OFFICER
```
- Dashboard
- Farms (limited)
- Procurement
- Reports
```

### For VETERINARY_OFFICER
```
- Dashboard
- Farms (health view)
- Health & Veterinary
- Reports
```

### For AUDITOR
```
- Dashboard
- Farms (read-only)
- Audit & Compliance
- Reports
```

---

## Implementation Guidelines

### 1. Role-Based Rendering

```typescript
// Example: Show section based on role
const canViewProcurement = (role: string) => {
  return ['NATIONAL_ADMIN', 'PROCUREMENT_OFFICER', 'AUDITOR'].includes(role);
};

{canViewProcurement(user.role) && (
  <ProcurementSection />
)}
```

### 2. Feature-Level Permissions

```typescript
// Example: Check specific permission
const canCreatePurchaseOrder = (role: string) => {
  return ['NATIONAL_ADMIN', 'PROCUREMENT_OFFICER'].includes(role);
};

{canCreatePurchaseOrder(user.role) && (
  <Button onClick={handleCreate}>Create Purchase Order</Button>
)}
```

### 3. Data Filtering

```typescript
// Example: Filter data based on role
const getVisibleFarms = (farms: Farm[], user: User) => {
  if (user.role === 'NATIONAL_ADMIN') {
    return farms; // All farms
  } else if (user.role === 'CONSTITUENCY_OFFICIAL') {
    return farms.filter(f => f.constituency === user.constituency);
  } else if (user.role === 'VETERINARY_OFFICER') {
    return farms; // All farms for health monitoring
  }
  return [];
};
```

---

## Summary

The unified staff dashboard provides:
1. **Single entry point** for all YEA staff
2. **Role-based feature visibility** to show relevant tools
3. **Clear permissions** to prevent unauthorized actions
4. **Scalable architecture** for adding new roles
5. **Consistent UX** across all staff types
