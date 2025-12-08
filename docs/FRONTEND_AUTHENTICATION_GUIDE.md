# Frontend Integration Guide: Authentication & Routing
## YEA Poultry Management System

**Last Updated:** December 4, 2025  
**Purpose:** Guide frontend developers on implementing authentication, user role handling, and dashboard routing

---

## Table of Contents

1. [Overview](#overview)
2. [User Types & Roles](#user-types--roles)
3. [Login API Response](#login-api-response)
4. [Routing Logic](#routing-logic)
5. [Permission System](#permission-system)
6. [Implementation Examples](#implementation-examples)
7. [Dashboard Types](#dashboard-types)

---

## Overview

The YEA PMS backend provides comprehensive user information and routing guidance in the login response. The frontend should use this information to:

1. **Route users** to the appropriate dashboard after login
2. **Display role-specific UI** components
3. **Control feature access** based on permissions
4. **Show/hide menu items** based on user role

---

## User Types & Roles

### Primary Classification

Users are divided into **two main categories**:

1. **Farmers** - End users who manage their farms
2. **YEA Staff** - Government officials and administrators

### User Roles

| Role | Type | Dashboard | Description |
|------|------|-----------|-------------|
| `FARMER` | Farmer | Farmer Dashboard | Farm owners managing their operations |
| `CONSTITUENCY_OFFICIAL` | Staff | Staff Dashboard | Local government officers |
| `NATIONAL_ADMIN` | Staff | Staff Dashboard | National-level administrators |
| `PROCUREMENT_OFFICER` | Staff | Staff Dashboard | Supply chain managers |
| `VETERINARY_OFFICER` | Staff | Staff Dashboard | Animal health specialists |
| `AUDITOR` | Staff | Staff Dashboard | Compliance and fraud investigators |

> **Note:** All YEA officials and government staff use the **Staff Dashboard**. The dashboard shows different features based on the user's specific role and permissions.

---

## Login API Response

### Endpoint

```
POST /api/auth/login/
```

### Request

```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

### Response Structure

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_farmer",
    "email": "john@example.com",
    "phone": "+233244123456",
    "first_name": "John",
    "last_name": "Doe",
    "role": "FARMER",
    "role_display": "Farmer",
    "full_name": "John Doe",
    "region": "Greater Accra",
    "constituency": "Tema East",
    "is_verified": true,
    "is_active": true
  },
  "routing": {
    "dashboard_type": "farmer",
    "redirect_to": "/farmer/dashboard",
    "is_staff": false,
    "is_farmer": true
  }
}
```

### Response Fields Explained

#### `user` Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique user identifier |
| `username` | string | Username for login |
| `email` | string | User's email address |
| `phone` | string | Phone number in international format |
| `first_name` | string | User's first name |
| `last_name` | string | User's last name |
| `role` | string | User's role code (see roles table above) |
| `role_display` | string | Human-readable role name |
| `full_name` | string | Full name (first + last) |
| `region` | string | Assigned region (for staff) or farm location (for farmers) |
| `constituency` | string | Assigned constituency (for staff) or farm location (for farmers) |
| `is_verified` | boolean | Whether account is fully verified |
| `is_active` | boolean | Whether account is active |

#### `routing` Object

| Field | Type | Description |
|-------|------|-------------|
| `dashboard_type` | string | Either `"farmer"` or `"staff"` |
| `redirect_to` | string | Recommended redirect path after login |
| `is_staff` | boolean | `true` if user is YEA staff, `false` if farmer |
| `is_farmer` | boolean | `true` if user is a farmer, `false` if staff |

---

## Routing Logic

### After Successful Login

```javascript
// Example: React/TypeScript
const handleLoginSuccess = (response) => {
  // Store tokens
  localStorage.setItem('access_token', response.access);
  localStorage.setItem('refresh_token', response.refresh);
  
  // Store user info
  localStorage.setItem('user', JSON.stringify(response.user));
  
  // Route based on backend recommendation
  const { redirect_to, dashboard_type, is_admin } = response.routing;
  
  // Use the backend-provided redirect path
  navigate(redirect_to);
  
  // Alternative: Route based on dashboard type
  if (dashboard_type === 'farmer') {
    navigate('/farmer/dashboard');
  } else if (dashboard_type === 'staff') {
    navigate('/staff/dashboard');
  }
};
```

### Recommended Routes

| User Type | Route | Description |
|-----------|-------|-------------|
| Farmers | `/farmer/dashboard` | Farmer dashboard with farm management tools |
| All Staff | `/staff/dashboard` | Staff dashboard with role-specific features |

> **Note:** All YEA staff (regardless of specific role) use the same staff dashboard route (`/staff/dashboard`). The dashboard shows/hides features based on the user's specific role and permissions. See [STAFF_DASHBOARD_FEATURES.md](./STAFF_DASHBOARD_FEATURES.md) for the complete feature visibility matrix.

---

## Permission System

### Role-Based Feature Access

Different roles have different permissions. The frontend should control feature visibility based on the user's role.

#### Farmer Permissions

Farmers can:
- ✅ View and manage their own farm
- ✅ Record daily production
- ✅ Manage flocks
- ✅ Track inventory (feed, medication)
- ✅ Manage customers and sales
- ✅ View their own financial data
- ❌ Cannot view other farms
- ❌ Cannot access admin features

#### Constituency Official Permissions

Constituency Officials can:
- ✅ Review and approve applications (constituency tier)
- ✅ View farms in their assigned constituency
- ✅ Assign extension officers
- ✅ Generate constituency reports
- ❌ Cannot access other constituencies
- ❌ Cannot approve beyond constituency tier

#### National Admin Permissions

National Admins can:
- ✅ Approve/reject applications (final tier)
- ✅ View all farms nationwide
- ✅ Generate national reports
- ✅ Manage programs
- ✅ Configure platform settings
- ❌ Cannot delete system data
- ❌ Cannot modify audit logs

#### Procurement Officer Permissions

Procurement Officers can:
- ✅ Create purchase orders
- ✅ Manage supplier database
- ✅ Allocate supplies to farms
- ✅ Track distribution
- ❌ Cannot approve farmer applications
- ❌ Cannot access farmer sales data

#### Veterinary Officer Permissions

Veterinary Officers can:
- ✅ View all farms in jurisdiction (for disease tracking)
- ✅ Inspect mortality records
- ✅ Verify compensation claims
- ✅ Prescribe treatments
- ❌ Cannot approve applications
- ❌ Cannot modify production data

#### Auditor Permissions

Auditors can:
- ✅ View all data (read-only)
- ✅ Access fraud alerts
- ✅ Review payout histories
- ✅ Generate audit reports
- ❌ Cannot modify any records
- ❌ Cannot approve applications

### Checking Permissions in Frontend

```javascript
// Example: Feature visibility based on role
const canApproveApplications = (user) => {
  const approverRoles = [
    'CONSTITUENCY_OFFICIAL',
    'NATIONAL_ADMIN'
  ];
  return approverRoles.includes(user.role);
};

const canManageProcurement = (user) => {
  return user.role === 'PROCUREMENT_OFFICER';
};

const canViewAllFarms = (user) => {
  const adminRoles = [
    'NATIONAL_ADMIN',
    'AUDITOR',
    'VETERINARY_OFFICER'
  ];
  return adminRoles.includes(user.role);
};

// Usage in component
{canApproveApplications(user) && (
  <Button onClick={handleApprove}>Approve Application</Button>
)}
```

---

## Implementation Examples

### 1. Protected Route Component

```typescript
// ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredDashboardType?: 'farmer' | 'admin';
  requiredRoles?: string[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredDashboardType,
  requiredRoles
}) => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const token = localStorage.getItem('access_token');
  
  // Not authenticated
  if (!token || !user.id) {
    return <Navigate to="/login" replace />;
  }
  
  // Check dashboard type
  if (requiredDashboardType) {
    const userDashboardType = user.role === 'FARMER' ? 'farmer' : 'staff';
    if (userDashboardType !== requiredDashboardType) {
      return <Navigate to="/" replace />;
    }
  }
  
  // Check specific roles
  if (requiredRoles && !requiredRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  
  return <>{children}</>;
};

// Usage
<Route
  path="/farmer/dashboard"
  element={
    <ProtectedRoute requiredDashboardType="farmer">
      <FarmerDashboard />
    </ProtectedRoute>
  }
/>

<Route
  path="/staff/dashboard"
  element={
    <ProtectedRoute requiredDashboardType="staff">
      <StaffDashboard />
    </ProtectedRoute>
  }
/>
```

### 2. Role-Based Menu

```typescript
// Navigation.tsx
const Navigation: React.FC = () => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  
  const farmerMenuItems = [
    { label: 'Dashboard', path: '/farmer/dashboard' },
    { label: 'My Farm', path: '/farmer/farm' },
    { label: 'Production', path: '/farmer/production' },
    { label: 'Sales', path: '/farmer/sales' },
    { label: 'Inventory', path: '/farmer/inventory' },
  ];
  
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

> **See [STAFF_DASHBOARD_FEATURES.md](./STAFF_DASHBOARD_FEATURES.md) for complete feature visibility matrix**
  
  const menuItems = user.role === 'FARMER' ? farmerMenuItems : adminMenuItems;
  
  return (
    <nav>
      {menuItems
        .filter(item => !item.roles || item.roles.includes(user.role))
        .map(item => (
          <Link key={item.path} to={item.path}>
            {item.label}
          </Link>
        ))
      }
    </nav>
  );
};
```

### 3. Login Handler

```typescript
// useAuth.ts
import { useNavigate } from 'react-router-dom';

export const useAuth = () => {
  const navigate = useNavigate();
  
  const login = async (username: string, password: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      if (!response.ok) {
        throw new Error('Login failed');
      }
      
      const data = await response.json();
      
      // Store authentication data
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      localStorage.setItem('user', JSON.stringify(data.user));
      
      // Route based on backend recommendation
      navigate(data.routing.redirect_to);
      
      return data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };
  
  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    navigate('/login');
  };
  
  return { login, logout };
};
```

---

## Dashboard Types

### Farmer Dashboard

**Route:** `/farmer/dashboard`

**Features:**
- Farm overview and statistics
- Production tracking
- Flock management
- Sales and revenue
- Inventory management
- Customer management
- Marketplace (if subscribed)

### Staff Dashboard

**Route:** `/staff/dashboard`

**Features (role-dependent):**
- Application management (for NATIONAL_ADMIN, CONSTITUENCY_OFFICIAL)
- Farm monitoring (all staff, filtered by role)
- Reporting and analytics (all staff, reports vary by role)
- User management (NATIONAL_ADMIN only)
- Procurement (for PROCUREMENT_OFFICER, NATIONAL_ADMIN)
- Health monitoring (for VETERINARY_OFFICER, NATIONAL_ADMIN)
- Audit tools (for AUDITOR, NATIONAL_ADMIN)
- System settings (NATIONAL_ADMIN only)

**Note:** The staff dashboard dynamically shows/hides sections based on the user's specific role. See [STAFF_DASHBOARD_FEATURES.md](./STAFF_DASHBOARD_FEATURES.md) for detailed feature visibility.

---

## Best Practices

### 1. Always Use Backend Routing Information

```javascript
// ✅ Good: Use backend-provided redirect
navigate(response.routing.redirect_to);

// ❌ Bad: Hardcode routing logic in frontend
if (user.role === 'FARMER') {
  navigate('/farmer/dashboard');
} else {
  navigate('/staff/dashboard');
}
```

### 2. Store User Data Securely

```javascript
// Store user data in localStorage for persistence
localStorage.setItem('user', JSON.stringify(response.user));

// Or use a state management solution (Redux, Zustand, etc.)
setUser(response.user);
```

### 3. Handle Token Refresh

```javascript
// Implement token refresh logic
const refreshToken = async () => {
  const refresh = localStorage.getItem('refresh_token');
  const response = await fetch('/api/auth/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh })
  });
  const data = await response.json();
  localStorage.setItem('access_token', data.access);
};
```

### 4. Redirect Unauthenticated Users

```javascript
// In your router or protected route component
if (!isAuthenticated) {
  return <Navigate to="/login" />;
}
```

### 5. Show Role-Specific UI

```javascript
// Conditionally render based on role
{user.role === 'NATIONAL_ADMIN' && (
  <AdminControls />
)}

{user.role === 'FARMER' && (
  <FarmerControls />
)}
```

---

## Common Issues & Solutions

### Issue: User redirected to landing page after login

**Cause:** Frontend not using the `routing.redirect_to` value from login response

**Solution:**
```javascript
// Use the backend-provided redirect path
const { redirect_to } = response.routing;
navigate(redirect_to);
```

### Issue: Admin users seeing farmer dashboard

**Cause:** Routing logic not checking `routing.is_staff` flag

**Solution:**
```javascript
// Check the is_staff flag
if (response.routing.is_staff) {
  navigate('/staff/dashboard');
} else {
  navigate('/farmer/dashboard');
}

// Or simply use the redirect_to value
navigate(response.routing.redirect_to);
```

### Issue: Features visible to wrong user types

**Cause:** Not checking user role before showing UI elements

**Solution:**
```javascript
// Check role before rendering
const canAccessFeature = (user, requiredRoles) => {
  return requiredRoles.includes(user.role);
};

{canAccessFeature(user, ['NATIONAL_ADMIN', 'PROCUREMENT_OFFICER']) && (
  <ProcurementSection />
)}
```

---

## Summary

1. **Use the `routing` object** from the login response to determine where to redirect users
2. **Check `user.role`** to show/hide features and menu items
3. **Implement protected routes** to prevent unauthorized access
4. **Store user data** for persistence across page refreshes
5. **Handle token refresh** to maintain authentication
6. **Follow the backend's routing recommendations** for consistency

For detailed permission information, see [RBAC_AUTHORIZATION_GUIDE.md](./RBAC_AUTHORIZATION_GUIDE.md).
