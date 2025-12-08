# Dashboard Routing Strategy Analysis

## Current Problem

The current implementation routes ALL non-farmer users to `/admin/dashboard`, treating them as admins. This is incorrect because:

1. **Not all officials are admins** - Some are operational staff with limited permissions
2. **Different roles need different dashboards** - A procurement officer's needs differ from a national admin's
3. **Security concern** - Calling all officials "admin" could create confusion about access levels

## User Role Analysis

### Group 1: Farmers
- **Role**: `FARMER`
- **Type**: End users
- **Dashboard**: Farmer Dashboard
- **Permissions**: Manage own farm only

### Group 2: Administrative Roles (True Admins)
These roles have system-wide administrative powers:
- **NATIONAL_ADMIN** - National-level decision making, policy configuration
- **SUPER_ADMIN** (if exists) - Full system access

### Group 3: Regional/Local Officials
These roles have geographic-scoped responsibilities:
- **CONSTITUENCY_OFFICIAL** - Local government officer, constituency-scoped
- **REGIONAL_COORDINATOR** (if exists) - Regional oversight

### Group 4: Specialized Officers
These roles have specific functional responsibilities:
- **PROCUREMENT_OFFICER** - Supply chain management
- **VETERINARY_OFFICER** - Animal health specialist
- **EXTENSION_OFFICER** (if exists) - Field officer, farmer support
- **AUDITOR** - Compliance and fraud investigation
- **FINANCE_OFFICER** (if exists) - Payment processing

## Proposed Solutions

### Option 1: Two-Dashboard Approach (Recommended)
**Dashboards:**
1. **Farmer Dashboard** (`/farmer/dashboard`) - For farmers only
2. **Staff Dashboard** (`/staff/dashboard`) - For ALL YEA officials/staff

**Advantages:**
- Clear separation: Farmers vs. Staff
- Single staff dashboard with role-based feature visibility
- Simpler routing logic
- Easier to maintain

**Implementation:**
- Staff dashboard shows different sections based on role
- Use role-based permissions to show/hide features
- Navigation menu adapts to user's role

### Option 2: Three-Dashboard Approach
**Dashboards:**
1. **Farmer Dashboard** (`/farmer/dashboard`) - For farmers
2. **Admin Dashboard** (`/admin/dashboard`) - For NATIONAL_ADMIN, SUPER_ADMIN only
3. **Staff Dashboard** (`/staff/dashboard`) - For all other officials

**Advantages:**
- Clear distinction between admin and operational staff
- Admins get specialized high-level dashboard
- Staff get operational dashboard

**Disadvantages:**
- More complexity
- Need to maintain three separate dashboards
- Potential code duplication

### Option 3: Role-Specific Dashboards
**Dashboards:**
1. **Farmer Dashboard** (`/farmer/dashboard`)
2. **Admin Dashboard** (`/admin/dashboard`) - NATIONAL_ADMIN, SUPER_ADMIN
3. **Constituency Dashboard** (`/constituency/dashboard`) - CONSTITUENCY_OFFICIAL
4. **Procurement Dashboard** (`/procurement/dashboard`) - PROCUREMENT_OFFICER
5. **Veterinary Dashboard** (`/veterinary/dashboard`) - VETERINARY_OFFICER
6. **Auditor Dashboard** (`/auditor/dashboard`) - AUDITOR

**Advantages:**
- Highly specialized dashboards for each role
- Each dashboard optimized for specific workflows

**Disadvantages:**
- Too many dashboards to maintain
- Code duplication
- Overly complex
- Harder to add new roles

## Recommendation: Option 1 (Two-Dashboard with Role-Based Features)

### Routing Logic

```javascript
if (user.role === 'FARMER') {
  redirect_to = '/farmer/dashboard'
  dashboard_type = 'farmer'
} else {
  redirect_to = '/staff/dashboard'
  dashboard_type = 'staff'
}
```

### Staff Dashboard Sections (Role-Based Visibility)

| Section | Visible To |
|---------|-----------|
| Applications | CONSTITUENCY_OFFICIAL, NATIONAL_ADMIN |
| Farms | All staff |
| Procurement | PROCUREMENT_OFFICER, NATIONAL_ADMIN |
| Health Monitoring | VETERINARY_OFFICER, NATIONAL_ADMIN |
| Audits | AUDITOR, NATIONAL_ADMIN |
| Reports | All staff (content varies by role) |
| User Management | NATIONAL_ADMIN only |
| System Settings | NATIONAL_ADMIN only |

### Benefits
1. **Clear terminology** - "Staff" instead of "Admin" for all officials
2. **Single source of truth** - One dashboard for all staff
3. **Role-based features** - Show/hide based on permissions
4. **Scalable** - Easy to add new roles
5. **Maintainable** - Less code duplication

## Implementation Plan

1. Update `CustomTokenObtainPairSerializer` to use "staff" instead of "admin"
2. Update routing logic to distinguish only Farmer vs. Staff
3. Create comprehensive staff dashboard with role-based sections
4. Update frontend documentation
5. Add role-based navigation menu
