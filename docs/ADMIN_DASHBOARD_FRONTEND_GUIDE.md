# Frontend Implementation Guide: Admin Dashboard
## YEA Poultry Management System - Privileged Office Staff

**Last Updated:** November 27, 2025  
**Version:** 1.0  
**Purpose:** Complete implementation reference for admin dashboard for office staff with various permission levels

---

## Table of Contents

1. [Overview](#overview)
2. [Permission Levels & Access Control](#permission-levels--access-control)
3. [API Endpoints](#api-endpoints)
4. [Dashboard Layouts by Role](#dashboard-layouts-by-role)
5. [TypeScript Types](#typescript-types)
6. [Authentication & Authorization](#authentication--authorization)
7. [UI Components](#ui-components)
8. [State Management](#state-management)
9. [Error Handling](#error-handling)
10. [Accessibility](#accessibility)
11. [Example Implementation](#example-implementation)
12. [Testing Checklist](#testing-checklist)

---

## Overview

### Purpose

The Admin Dashboard provides **privileged office staff** with comprehensive tools to:
- Manage user accounts and permissions
- Screen and approve farm applications
- Monitor system metrics and analytics
- Administer government programs
- Configure system settings
- Generate reports

### Permission Architecture

The system implements **Role-Based Access Control (RBAC)** with **5 primary admin roles**:

1. **SUPER_ADMIN** - Full system access
2. **NATIONAL_ADMIN** - National-level oversight and approvals
3. **REGIONAL_COORDINATOR** - Regional management (16 regions)
4. **CONSTITUENCY_OFFICIAL** - Local constituency management (275+ constituencies)
5. **EXTENSION_OFFICER** - Field officer supporting 10-20 farmers

### Key Features

- **Jurisdiction-Based Data Scoping** - Automatically filter data by region/constituency
- **Permission Checks** - Frontend validates actions before API calls
- **Activity Tracking** - Audit logs for all admin actions
- **Responsive Design** - Works on desktop tablets (mobile optional for field officers)
- **Real-Time Updates** - WebSocket notifications for urgent actions

---

## Permission Levels & Access Control

### Role Hierarchy & Capabilities

#### 1. SUPER_ADMIN

**Access Level:** Full Platform  
**Count:** 2-3 users  
**Color Badge:** 🔴 Red

| Capability | Details |
|------------|---------|
| **User Management** | Create, edit, delete all users; assign any role; impersonate users |
| **Application Screening** | View all applications nationwide; override any decision |
| **Program Management** | Create/edit/delete government programs; configure eligibility |
| **System Config** | Modify system settings; access logs; export database |
| **Analytics** | Access all reports and analytics nationwide |
| **Special Powers** | Emergency overrides; audit log access; bulk operations |

**Restrictions:** None

---

#### 2. NATIONAL_ADMIN

**Access Level:** All Regions & Constituencies  
**Count:** 5-10 users  
**Color Badge:** 🟠 Orange

| Capability | Details |
|------------|---------|
| **User Management** | Create regional coordinators, constituency officials, extension officers; cannot create super admins |
| **Application Screening** | Final tier approval (national level); view all applications |
| **Program Management** | Create/edit programs; view enrollments; manage slots |
| **System Config** | View settings (read-only); request changes from super admin |
| **Analytics** | National-level reports; regional comparisons; trend analysis |

**Restrictions:**
- Cannot delete users
- Cannot modify audit logs
- Cannot impersonate users
- Cannot override super admin decisions

---

#### 3. REGIONAL_COORDINATOR

**Access Level:** Assigned Region Only (e.g., Greater Accra Region)  
**Count:** 16 users (one per region)  
**Color Badge:** 🟡 Yellow

| Capability | Details |
|------------|---------|
| **User Management** | Create constituency officials and extension officers in region; view regional users |
| **Application Screening** | Tier 2 approval (regional level); view applications in region |
| **Program Management** | View programs; recommend adjustments; assign officers |
| **Analytics** | Regional reports; constituency comparisons |

**Restrictions:**
- Cannot access other regions' data
- Cannot approve final tier (requires national admin)
- Cannot modify national policies
- Cannot delete any records

---

#### 4. CONSTITUENCY_OFFICIAL

**Access Level:** Assigned Constituency Only (e.g., Tema East)  
**Count:** 275+ users (one per constituency)  
**Color Badge:** 🟢 Green

| Capability | Details |
|------------|---------|
| **User Management** | View users in constituency; request extension officer assignments |
| **Application Screening** | Tier 1 review (constituency level); verify GPS locations; validate documents |
| **Program Management** | View programs; recommend farmers for enrollment |
| **Analytics** | Constituency reports; farmer lists |

**Restrictions:**
- Cannot access other constituencies
- Cannot approve beyond constituency tier
- Cannot modify approved applications
- Cannot create users (request from regional coordinator)

---

#### 5. EXTENSION_OFFICER

**Access Level:** Assigned Farmers Only (10-20 farms)  
**Count:** 500+ users  
**Color Badge:** 🔵 Blue

| Capability | Details |
|------------|---------|
| **User Management** | View assigned farmers' profiles only |
| **Application Screening** | No approval powers; can flag issues for constituency review |
| **Farm Monitoring** | Record site visits; update inspection notes; submit training records |
| **Analytics** | View assigned farmers' performance; training completion |

**Restrictions:**
- Cannot approve applications
- Cannot access unassigned farms
- Cannot modify financial data
- Read-only access to production records

---

## API Endpoints

### Base URL
```
https://api.example.com/api/admin/
```

### Authentication
All endpoints require JWT Bearer token:
```http
Authorization: Bearer <access_token>
```

---

### 1. Dashboard Overview

#### Get Admin Dashboard Overview
```http
GET /api/admin/dashboard/overview/
```

**Access:** All admin roles  
**Scope:** Automatically filtered by jurisdiction

**Response:**
```json
{
  "farms": {
    "total": 1245,
    "active": 980,
    "approved": 850,
    "approval_rate": 68.3
  },
  "applications": {
    "total": 1520,
    "pending": 215,
    "approved": 1100,
    "rejected": 205,
    "recent_7_days": 42
  },
  "users": {
    "total": 1876,
    "active": 1654,
    "verified": 1589,
    "verification_rate": 84.7
  },
  "pending_actions": {
    "constituency_screening": 18,
    "regional_approval": 5,
    "national_approval": 2,
    "total": 25
  },
  "jurisdiction": {
    "level": "REGIONAL_COORDINATOR",
    "region": "Greater Accra Region",
    "constituency": "All Constituencies"
  }
}
```

---

### 2. User Management

#### List Users
```http
GET /api/admin/users/?role=&region=&constituency=&is_active=&search=&page=1&page_size=20
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `role` | string | Filter by role (FARMER, NATIONAL_ADMIN, etc.) |
| `region` | string | Filter by region |
| `constituency` | string | Filter by constituency |
| `is_active` | boolean | Filter by active status |
| `search` | string | Search by name, email, phone |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Results per page (default: 20) |

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "username": "john.doe",
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "FARMER",
      "phone": "+233241234567",
      "region": "Greater Accra",
      "constituency": "Tema East",
      "is_active": true,
      "is_verified": true,
      "created_at": "2025-01-15T10:30:00Z",
      "last_login_at": "2025-11-25T14:20:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 156,
    "pages": 8
  }
}
```

---

#### Get User Detail
```http
GET /api/admin/users/{user_id}/
```

**Response:**
```json
{
  "id": "uuid",
  "username": "john.doe",
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "FARMER",
  "phone": "+233241234567",
  "phone_verified": true,
  "email_verified": true,
  "region": "Greater Accra",
  "constituency": "Tema East",
  "is_active": true,
  "is_verified": true,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-11-25T14:20:00Z",
  "last_login_at": "2025-11-25T14:20:00Z",
  "failed_login_attempts": 0,
  "account_locked_until": null
}
```

---

#### Update User
```http
PUT /api/admin/users/{user_id}/
Content-Type: application/json
```

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "new.email@example.com",
  "phone": "+233241234567",
  "role": "FARMER",
  "region": "Greater Accra",
  "constituency": "Tema East",
  "is_active": true
}
```

**Note:** Only editable fields for the user's role will be applied. See `editable_fields` in UserPolicy.

**Response:** Updated user object (same as GET detail)

---

#### Create User
```http
POST /api/admin/users/create/
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "new.user",
  "email": "new.user@example.com",
  "password": "SecurePassword123!",
  "first_name": "New",
  "last_name": "User",
  "role": "EXTENSION_OFFICER",
  "phone": "+233241234567",
  "region": "Greater Accra",
  "constituency": "Tema East"
}
```

**Response (201):** Created user object

---

#### Delete User
```http
DELETE /api/admin/users/{user_id}/
```

**Access:** SUPER_ADMIN only

**Response (204):** No content

---

### 3. Application Management

#### List Applications
```http
GET /api/admin/applications/?status=&application_type=&region=&constituency=&screening_stage=&search=&page=1&page_size=20
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | draft, submitted, under_review, approved, rejected |
| `application_type` | string | government_program, independent |
| `region` | string | Filter by region |
| `constituency` | string | Filter by constituency |
| `screening_stage` | string | constituency, regional, national |
| `search` | string | Search by application_id, name, phone |
| `page` | integer | Page number |
| `page_size` | integer | Results per page |

**Response:**
```json
{
  "results": [
    {
      "application_id": "APP-2025-00123",
      "applicant_name": "Jane Smith",
      "farm_name": "Smith Poultry Farm",
      "phone": "+233241234567",
      "application_type": "government_program",
      "status": "submitted",
      "screening_stage": "constituency",
      "region": "Greater Accra",
      "constituency": "Tema East",
      "created_at": "2025-11-20T09:15:00Z",
      "yea_program_batch": "YEA-2025-Q1"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 215,
    "pages": 11
  }
}
```

---

### 4. Program Management

#### List Programs
```http
GET /api/admin/programs/
```

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "program_code": "YEA-2025-Q1",
      "program_name": "YEA Poultry Support Program 2025",
      "program_type": "comprehensive",
      "is_active": true,
      "total_slots": 1000,
      "slots_filled": 588,
      "slots_available": 412,
      "application_deadline": "2025-03-31",
      "start_date": "2025-04-01",
      "end_date": "2026-03-31",
      "created_at": "2025-01-10T00:00:00Z"
    }
  ]
}
```

---

### 5. Analytics

#### Get Analytics Data
```http
GET /api/admin/analytics/?metric=applications_trend&period=30d
```

**Query Parameters:**
| Parameter | Type | Options |
|-----------|------|---------|
| `metric` | string | applications_trend, user_growth, regional_distribution |
| `period` | string | 7d, 30d, 90d, 1y |

**Response (applications_trend):**
```json
{
  "metric": "applications_trend",
  "period": "30d",
  "data": [
    {"date": "2025-11-01", "count": 15},
    {"date": "2025-11-02", "count": 22},
    {"date": "2025-11-03", "count": 18}
  ]
}
```

**Response (regional_distribution):**
```json
{
  "metric": "regional_distribution",
  "data": [
    {
      "region": "Greater Accra",
      "total": 450,
      "pending": 85,
      "approved": 320
    },
    {
      "region": "Ashanti",
      "total": 380,
      "pending": 62,
      "approved": 290
    }
  ]
}
```

---

### 6. System Configuration

#### Get System Config
```http
GET /api/admin/config/
```

**Access:** SUPER_ADMIN only

**Response:**
```json
{
  "sms_enabled": true,
  "debug_mode": false,
  "allowed_hosts": ["api.example.com"],
  "cors_origins": ["https://admin.example.com"],
  "media_url": "/media/",
  "static_url": "/static/"
}
```

---

## Dashboard Layouts by Role

### SUPER_ADMIN / NATIONAL_ADMIN Dashboard

**Layout:** Full-width with 4-column grid

**Sections:**
1. **Overview Cards** (4 cards)
   - Total Farms | Active Users | Pending Applications | System Health

2. **Quick Actions Bar**
   - Create User | Create Program | View Reports | System Settings

3. **Applications Trend Chart** (Line chart, 30 days)

4. **Regional Distribution Map** (Interactive Ghana map with region stats)

5. **Recent Activity Feed** (20 items, real-time updates)

6. **Pending Actions Table**
   - National approvals needed
   - Flagged applications
   - User requests

---

### REGIONAL_COORDINATOR Dashboard

**Layout:** 3-column grid with regional focus

**Sections:**
1. **Regional Overview Cards** (3 cards)
   - Farms in Region | Pending Regional Approvals | Active Officers

2. **Constituency Breakdown Table**
   - List all constituencies in region with metrics

3. **Applications Awaiting Regional Approval**
   - Filterable table with action buttons

4. **Regional Analytics Chart**
   - Constituency comparison (bar chart)

5. **Extension Officer Performance**
   - Table showing officers with visit counts, training completion

---

### CONSTITUENCY_OFFICIAL Dashboard

**Layout:** 2-column layout with local focus

**Sections:**
1. **Constituency Overview Cards** (3 cards)
   - Farms in Constituency | Pending Reviews | Active Farmers

2. **Applications for Constituency Review**
   - Table with review/approve/reject actions

3. **GPS Verification Queue**
   - Applications needing location verification

4. **Extension Officers in Constituency**
   - List with assignment stats

5. **Local Activity Feed**

---

### EXTENSION_OFFICER Dashboard

**Layout:** Mobile-friendly single column

**Sections:**
1. **My Assignments** (10-20 cards)
   - Farmer cards with visit status

2. **Upcoming Site Visits** (Calendar widget)

3. **Training Schedule**

4. **Issues to Report** (Form)

---

## TypeScript Types

```typescript
export type UserRole =
  | 'SUPER_ADMIN'
  | 'NATIONAL_ADMIN'
  | 'REGIONAL_COORDINATOR'
  | 'CONSTITUENCY_OFFICIAL'
  | 'EXTENSION_OFFICER'
  | 'VETERINARY_OFFICER'
  | 'PROCUREMENT_OFFICER'
  | 'AUDITOR'
  | 'FARMER';

export type ApplicationStatus =
  | 'draft'
  | 'submitted'
  | 'under_review'
  | 'approved'
  | 'rejected';

export type ScreeningStage =
  | 'constituency'
  | 'regional'
  | 'national';

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  phone: string;
  region: string | null;
  constituency: string | null;
  is_active: boolean;
  is_verified: boolean;
  phone_verified: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface DashboardOverview {
  farms: {
    total: number;
    active: number;
    approved: number;
    approval_rate: number;
  };
  applications: {
    total: number;
    pending: number;
    approved: number;
    rejected: number;
    recent_7_days: number;
  };
  users: {
    total: number;
    active: number;
    verified: number;
    verification_rate: number;
  };
  pending_actions: {
    constituency_screening: number;
    regional_approval: number;
    national_approval: number;
    total: number;
  };
  jurisdiction: {
    level: UserRole;
    region: string;
    constituency: string;
  };
}

export interface FarmApplication {
  application_id: string;
  applicant_name: string;
  farm_name: string;
  phone: string;
  application_type: 'government_program' | 'independent';
  status: ApplicationStatus;
  screening_stage: ScreeningStage | null;
  region: string;
  constituency: string;
  created_at: string;
  yea_program_batch: string | null;
}

export interface GovernmentProgram {
  id: string;
  program_code: string;
  program_name: string;
  program_type: string;
  is_active: boolean;
  total_slots: number;
  slots_filled: number;
  slots_available: number;
  application_deadline: string | null;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  results: T[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
}

export interface PermissionCheck {
  canView: boolean;
  canEdit: boolean;
  canDelete: boolean;
  canCreate: boolean;
  editableFields?: string[] | '__all__';
}
```

---

## Authentication & Authorization

### Login Flow

```typescript
// 1. Login
const response = await fetch('/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});

const { access, refresh, user } = await response.json();

// Store tokens
localStorage.setItem('access_token', access);
localStorage.setItem('refresh_token', refresh);
localStorage.setItem('user', JSON.stringify(user));

// 2. Check if user has admin role
const ADMIN_ROLES: UserRole[] = [
  'SUPER_ADMIN',
  'NATIONAL_ADMIN',
  'REGIONAL_COORDINATOR',
  'CONSTITUENCY_OFFICIAL',
  'EXTENSION_OFFICER'
];

if (!ADMIN_ROLES.includes(user.role)) {
  // Redirect to farmer dashboard
  router.push('/farmer/dashboard');
} else {
  // Redirect to admin dashboard
  router.push('/admin/dashboard');
}
```

### API Client with Auth

```typescript
class AdminAPIClient {
  private baseURL = '/api/admin/';
  
  private async getHeaders(): Promise<HeadersInit> {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }
  
  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      headers: await this.getHeaders()
    });
    
    if (response.status === 401) {
      // Token expired, try refresh
      await this.refreshToken();
      return this.get(endpoint); // Retry
    }
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async post<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Request failed');
    }
    
    return response.json();
  }
  
  async put<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error('Update failed');
    }
    
    return response.json();
  }
  
  async delete(endpoint: string): Promise<void> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    
    if (!response.ok) {
      throw new Error('Delete failed');
    }
  }
  
  private async refreshToken(): Promise<void> {
    const refresh = localStorage.getItem('refresh_token');
    const response = await fetch('/api/auth/token/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh })
    });
    
    if (!response.ok) {
      // Refresh failed, logout
      localStorage.clear();
      window.location.href = '/login';
      throw new Error('Session expired');
    }
    
    const { access } = await response.json();
    localStorage.setItem('access_token', access);
  }
}

export const adminAPI = new AdminAPIClient();
```

### Permission Checking

```typescript
// Frontend permission helper
export class PermissionChecker {
  constructor(private user: AdminUser) {}
  
  canManageUsers(): boolean {
    return ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR'].includes(this.user.role);
  }
  
  canCreateUsers(): boolean {
    return ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR'].includes(this.user.role);
  }
  
  canDeleteUsers(): boolean {
    return this.user.role === 'SUPER_ADMIN';
  }
  
  canApproveApplications(stage: ScreeningStage): boolean {
    if (stage === 'constituency') {
      return ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL'].includes(this.user.role);
    }
    if (stage === 'regional') {
      return ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR'].includes(this.user.role);
    }
    if (stage === 'national') {
      return ['SUPER_ADMIN', 'NATIONAL_ADMIN'].includes(this.user.role);
    }
    return false;
  }
  
  canAccessSystemConfig(): boolean {
    return this.user.role === 'SUPER_ADMIN';
  }
  
  canViewAllRegions(): boolean {
    return ['SUPER_ADMIN', 'NATIONAL_ADMIN'].includes(this.user.role);
  }
  
  getAccessibleRegions(): string[] {
    if (this.canViewAllRegions()) {
      return ['All Regions'];
    }
    if (this.user.role === 'REGIONAL_COORDINATOR' && this.user.region) {
      return [this.user.region];
    }
    return [];
  }
}
```

---

## UI Components

### 1. Dashboard Overview Cards

```tsx
interface OverviewCardProps {
  title: string;
  value: number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'orange' | 'red';
}

export const OverviewCard: React.FC<OverviewCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  icon,
  color
}) => {
  return (
    <div className={`card card-${color} p-6 rounded-lg shadow`}>
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <h2 className="text-3xl font-bold mt-2">{value.toLocaleString()}</h2>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        <div className="text-4xl">{icon}</div>
      </div>
      {trend && trendValue && (
        <div className={`mt-4 flex items-center text-sm ${
          trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600'
        }`}>
          <span>{trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}</span>
          <span className="ml-1">{trendValue}</span>
        </div>
      )}
    </div>
  );
};
```

### 2. User Management Table

```tsx
interface UserTableProps {
  users: AdminUser[];
  onEdit: (userId: string) => void;
  onDelete: (userId: string) => void;
  permissions: PermissionChecker;
}

export const UserTable: React.FC<UserTableProps> = ({
  users,
  onEdit,
  onDelete,
  permissions
}) => {
  return (
    <table className="w-full table-auto">
      <thead className="bg-gray-100">
        <tr>
          <th className="px-4 py-2 text-left">Name</th>
          <th className="px-4 py-2 text-left">Email</th>
          <th className="px-4 py-2 text-left">Role</th>
          <th className="px-4 py-2 text-left">Region</th>
          <th className="px-4 py-2 text-left">Status</th>
          <th className="px-4 py-2 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        {users.map((user) => (
          <tr key={user.id} className="border-b hover:bg-gray-50">
            <td className="px-4 py-3">
              {user.first_name} {user.last_name}
            </td>
            <td className="px-4 py-3">{user.email}</td>
            <td className="px-4 py-3">
              <span className={`badge badge-${getRoleBadgeColor(user.role)}`}>
                {user.role}
              </span>
            </td>
            <td className="px-4 py-3">{user.region || '-'}</td>
            <td className="px-4 py-3">
              <span className={`badge ${user.is_active ? 'badge-success' : 'badge-gray'}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </span>
            </td>
            <td className="px-4 py-3 text-right">
              <button
                onClick={() => onEdit(user.id)}
                className="btn btn-sm btn-primary mr-2"
              >
                Edit
              </button>
              {permissions.canDeleteUsers() && (
                <button
                  onClick={() => onDelete(user.id)}
                  className="btn btn-sm btn-danger"
                >
                  Delete
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

function getRoleBadgeColor(role: UserRole): string {
  const colors: Record<UserRole, string> = {
    SUPER_ADMIN: 'red',
    NATIONAL_ADMIN: 'orange',
    REGIONAL_COORDINATOR: 'yellow',
    CONSTITUENCY_OFFICIAL: 'green',
    EXTENSION_OFFICER: 'blue',
    VETERINARY_OFFICER: 'purple',
    PROCUREMENT_OFFICER: 'indigo',
    AUDITOR: 'pink',
    FARMER: 'gray'
  };
  return colors[role] || 'gray';
}
```

### 3. Application Screening Card

```tsx
interface ApplicationCardProps {
  application: FarmApplication;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onViewDetails: (id: string) => void;
  canApprove: boolean;
}

export const ApplicationCard: React.FC<ApplicationCardProps> = ({
  application,
  onApprove,
  onReject,
  onViewDetails,
  canApprove
}) => {
  return (
    <div className="card p-4 border rounded-lg">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-bold text-lg">{application.farm_name}</h3>
          <p className="text-sm text-gray-600">{application.applicant_name}</p>
        </div>
        <span className={`badge badge-${getStatusColor(application.status)}`}>
          {application.status}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
        <div>
          <span className="text-gray-500">ID:</span>
          <span className="ml-2">{application.application_id}</span>
        </div>
        <div>
          <span className="text-gray-500">Type:</span>
          <span className="ml-2">{application.application_type}</span>
        </div>
        <div>
          <span className="text-gray-500">Region:</span>
          <span className="ml-2">{application.region}</span>
        </div>
        <div>
          <span className="text-gray-500">Stage:</span>
          <span className="ml-2">{application.screening_stage || '-'}</span>
        </div>
      </div>
      
      <div className="flex gap-2">
        <button
          onClick={() => onViewDetails(application.application_id)}
          className="btn btn-sm btn-outline flex-1"
        >
          View Details
        </button>
        {canApprove && application.status === 'submitted' && (
          <>
            <button
              onClick={() => onApprove(application.application_id)}
              className="btn btn-sm btn-success"
            >
              Approve
            </button>
            <button
              onClick={() => onReject(application.application_id)}
              className="btn btn-sm btn-danger"
            >
              Reject
            </button>
          </>
        )}
      </div>
    </div>
  );
};

function getStatusColor(status: ApplicationStatus): string {
  const colors: Record<ApplicationStatus, string> = {
    draft: 'gray',
    submitted: 'blue',
    under_review: 'yellow',
    approved: 'green',
    rejected: 'red'
  };
  return colors[status];
}
```

---

## State Management

### Zustand Store Example

```typescript
import create from 'zustand';
import { adminAPI } from './api-client';

interface AdminStore {
  user: AdminUser | null;
  permissions: PermissionChecker | null;
  overview: DashboardOverview | null;
  users: AdminUser[];
  applications: FarmApplication[];
  loading: boolean;
  error: string | null;
  
  // Actions
  setUser: (user: AdminUser) => void;
  fetchOverview: () => Promise<void>;
  fetchUsers: (filters?: Record<string, string>) => Promise<void>;
  fetchApplications: (filters?: Record<string, string>) => Promise<void>;
  updateUser: (userId: string, data: Partial<AdminUser>) => Promise<void>;
  deleteUser: (userId: string) => Promise<void>;
}

export const useAdminStore = create<AdminStore>((set, get) => ({
  user: null,
  permissions: null,
  overview: null,
  users: [],
  applications: [],
  loading: false,
  error: null,
  
  setUser: (user) => {
    set({
      user,
      permissions: new PermissionChecker(user)
    });
  },
  
  fetchOverview: async () => {
    set({ loading: true, error: null });
    try {
      const overview = await adminAPI.get<DashboardOverview>('dashboard/overview/');
      set({ overview, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
  
  fetchUsers: async (filters = {}) => {
    set({ loading: true, error: null });
    try {
      const queryString = new URLSearchParams(filters).toString();
      const response = await adminAPI.get<PaginatedResponse<AdminUser>>(
        `users/?${queryString}`
      );
      set({ users: response.results, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
  
  fetchApplications: async (filters = {}) => {
    set({ loading: true, error: null });
    try {
      const queryString = new URLSearchParams(filters).toString();
      const response = await adminAPI.get<PaginatedResponse<FarmApplication>>(
        `applications/?${queryString}`
      );
      set({ applications: response.results, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
  
  updateUser: async (userId, data) => {
    set({ loading: true, error: null });
    try {
      await adminAPI.put(`users/${userId}/`, data);
      await get().fetchUsers();
      set({ loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },
  
  deleteUser: async (userId) => {
    set({ loading: true, error: null });
    try {
      await adminAPI.delete(`users/${userId}/`);
      await get().fetchUsers();
      set({ loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  }
}));
```

---

## Error Handling

### Error Types

```typescript
export class AdminAPIError extends Error {
  constructor(
    public statusCode: number,
    public message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'AdminAPIError';
  }
}

export function handleAPIError(error: any): string {
  if (error instanceof AdminAPIError) {
    switch (error.statusCode) {
      case 401:
        return 'Session expired. Please log in again.';
      case 403:
        return 'You do not have permission to perform this action.';
      case 404:
        return 'The requested resource was not found.';
      case 409:
        return 'This action conflicts with existing data.';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return error.message || 'An unexpected error occurred.';
    }
  }
  return 'Network error. Please check your connection.';
}
```

### Toast Notifications

```typescript
import { toast } from 'react-toastify';

export const showSuccess = (message: string) => {
  toast.success(message, {
    position: 'top-right',
    autoClose: 3000
  });
};

export const showError = (error: any) => {
  const message = handleAPIError(error);
  toast.error(message, {
    position: 'top-right',
    autoClose: 5000
  });
};

export const showWarning = (message: string) => {
  toast.warning(message, {
    position: 'top-right',
    autoClose: 4000
  });
};
```

---

## Accessibility

### ARIA Labels

```tsx
// Navigation
<nav aria-label="Admin dashboard navigation">
  <ul role="menubar">
    <li role="menuitem">
      <a href="/admin/dashboard" aria-current="page">Dashboard</a>
    </li>
  </ul>
</nav>

// Tables
<table aria-label="User management table">
  <thead>
    <tr>
      <th scope="col">Name</th>
      <th scope="col">Role</th>
    </tr>
  </thead>
</table>

// Buttons
<button aria-label="Edit user profile">
  <EditIcon />
</button>

// Status indicators
<span role="status" aria-live="polite">
  {loading ? 'Loading...' : 'Data loaded'}
</span>
```

### Keyboard Navigation

```typescript
// Table row keyboard navigation
const handleKeyDown = (e: React.KeyboardEvent, userId: string) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    onViewDetails(userId);
  }
};

<tr
  tabIndex={0}
  onKeyDown={(e) => handleKeyDown(e, user.id)}
  className="cursor-pointer"
>
  ...
</tr>
```

---

## Example Implementation

### Complete Admin Dashboard Page

```tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAdminStore } from '@/store/admin-store';
import { OverviewCard } from '@/components/admin/OverviewCard';
import { UserTable } from '@/components/admin/UserTable';
import { ApplicationCard } from '@/components/admin/ApplicationCard';

export default function AdminDashboard() {
  const router = useRouter();
  const {
    user,
    permissions,
    overview,
    users,
    applications,
    loading,
    error,
    fetchOverview,
    fetchUsers,
    fetchApplications
  } = useAdminStore();
  
  useEffect(() => {
    // Check auth
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
      return;
    }
    
    const parsedUser = JSON.parse(storedUser);
    useAdminStore.getState().setUser(parsedUser);
    
    // Fetch data
    fetchOverview();
    fetchUsers({ page: '1', page_size: '20' });
    fetchApplications({ status: 'submitted', page: '1' });
  }, []);
  
  if (!user || !permissions) {
    return <div>Loading...</div>;
  }
  
  return (
    <div className="admin-dashboard p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <p className="text-gray-600">
          Welcome, {user.first_name} {user.last_name} ({user.role})
        </p>
        <p className="text-sm text-gray-500">
          {overview?.jurisdiction.region} · {overview?.jurisdiction.constituency}
        </p>
      </div>
      
      {/* Overview Cards */}
      {overview && (
        <div className="grid grid-cols-4 gap-6 mb-8">
          <OverviewCard
            title="Total Farms"
            value={overview.farms.total}
            subtitle={`${overview.farms.approved} approved`}
            trend="up"
            trendValue={`${overview.farms.approval_rate}% approval rate`}
            icon="🏠"
            color="blue"
          />
          <OverviewCard
            title="Active Users"
            value={overview.users.active}
            subtitle={`${overview.users.total} total`}
            trend="neutral"
            trendValue={`${overview.users.verification_rate}% verified`}
            icon="👥"
            color="green"
          />
          <OverviewCard
            title="Pending Actions"
            value={overview.pending_actions.total}
            subtitle="Require your attention"
            trend="down"
            trendValue="5 less than yesterday"
            icon="⏳"
            color="orange"
          />
          <OverviewCard
            title="Recent Applications"
            value={overview.applications.recent_7_days}
            subtitle="Last 7 days"
            trend="up"
            trendValue="+12% from last week"
            icon="📝"
            color="red"
          />
        </div>
      )}
      
      {/* Quick Actions */}
      {permissions.canCreateUsers() && (
        <div className="mb-8 flex gap-4">
          <button
            onClick={() => router.push('/admin/users/create')}
            className="btn btn-primary"
          >
            + Create User
          </button>
          <button
            onClick={() => router.push('/admin/programs/create')}
            className="btn btn-secondary"
          >
            + Create Program
          </button>
          <button
            onClick={() => router.push('/admin/reports')}
            className="btn btn-outline"
          >
            📊 View Reports
          </button>
        </div>
      )}
      
      {/* Pending Applications */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Pending Applications</h2>
        {loading ? (
          <div>Loading applications...</div>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {applications.slice(0, 6).map((app) => (
              <ApplicationCard
                key={app.application_id}
                application={app}
                onApprove={(id) => console.log('Approve', id)}
                onReject={(id) => console.log('Reject', id)}
                onViewDetails={(id) => router.push(`/admin/applications/${id}`)}
                canApprove={permissions.canApproveApplications(app.screening_stage || 'constituency')}
              />
            ))}
          </div>
        )}
      </section>
      
      {/* User Management */}
      {permissions.canManageUsers() && (
        <section>
          <h2 className="text-2xl font-bold mb-4">User Management</h2>
          <UserTable
            users={users}
            onEdit={(id) => router.push(`/admin/users/${id}/edit`)}
            onDelete={(id) => console.log('Delete', id)}
            permissions={permissions}
          />
        </section>
      )}
      
      {/* Error Display */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}
    </div>
  );
}
```

---

## Testing Checklist

### Functional Tests

- [ ] Login with each role type redirects to correct dashboard
- [ ] Overview cards display correct metrics scoped by jurisdiction
- [ ] User list filters by role, region, constituency
- [ ] User creation validates required fields and role permissions
- [ ] User edit only allows editing permitted fields
- [ ] User delete only accessible to SUPER_ADMIN
- [ ] Applications list filters by status and screening stage
- [ ] Application approval only available when user has permission for that stage
- [ ] Analytics charts load correct data for selected period
- [ ] System config only accessible to SUPER_ADMIN

### Permission Tests

- [ ] REGIONAL_COORDINATOR cannot access other regions' data
- [ ] CONSTITUENCY_OFFICIAL cannot approve beyond constituency tier
- [ ] EXTENSION_OFFICER sees only assigned farmers
- [ ] Non-admin roles redirect to farmer dashboard
- [ ] Token refresh works when access token expires
- [ ] 403 errors display appropriate "Permission denied" message

### UI/UX Tests

- [ ] Dashboard responsive on tablet and desktop
- [ ] Tables paginate correctly
- [ ] Search/filter updates results immediately
- [ ] Loading states display during API calls
- [ ] Error messages clear and actionable
- [ ] Success toasts confirm actions
- [ ] Keyboard navigation works in tables
- [ ] Screen readers announce status changes

---

## Next Steps

1. **Implement Application Screening Workflow** - Build detailed application review UI with document preview, GPS map, and approval/rejection forms
2. **Add Real-Time Notifications** - Integrate WebSocket for live updates when applications need attention
3. **Create Reporting Module** - Build export functionality for CSV/PDF reports
4. **Audit Log Viewer** - Display user action history for SUPER_ADMIN
5. **Mobile App for Extension Officers** - Build React Native app for field data collection

---

**Questions? Contact the development team or refer to the RBAC Authorization Guide for detailed permission rules.**
