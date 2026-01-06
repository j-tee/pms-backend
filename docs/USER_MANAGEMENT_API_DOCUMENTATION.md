# User Management API Documentation

**Version:** 1.0  
**Last Updated:** January 4, 2026  
**Backend Version:** Django 5.2 / DRF 3.x  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Role Hierarchy](#2-role-hierarchy)
3. [Authentication](#3-authentication)
4. [User CRUD Endpoints](#4-user-crud-endpoints)
5. [User Action Endpoints](#5-user-action-endpoints)
6. [Staff Invitation Endpoints](#6-staff-invitation-endpoints)
7. [Permission Matrix](#7-permission-matrix)
8. [TypeScript Interfaces](#8-typescript-interfaces)
9. [Error Handling](#9-error-handling)
10. [Frontend Implementation Guide](#10-frontend-implementation-guide)

---

## 1. Overview

The User Management API provides comprehensive user administration capabilities for the YEA Poultry Management System. All endpoints are under `/api/admin/` and require JWT authentication.

### Base URL
```
Production: https://api.yeapms.gov.gh/api/admin/
Development: http://localhost:8000/api/admin/
```

### Key Features
- ✅ Role-based access control
- ✅ SUPER_ADMIN account protection
- ✅ User suspension/unsuspension
- ✅ Account locking/unlocking
- ✅ Force logout capability
- ✅ Admin-initiated password reset
- ✅ 2FA management
- ✅ Login attempt tracking

---

## 2. Role Hierarchy

Roles are ordered from highest to lowest privilege:

```
┌─────────────────────────────────────────────────────────────────┐
│  SUPER_ADMIN        ← Protected account (cannot be modified)    │
│       ↓                                                          │
│  YEA_OFFICIAL       ← Elevated administrator                    │
│       ↓                                                          │
│  NATIONAL_ADMIN     ← National scope                            │
│       ↓                                                          │
│  REGIONAL_COORDINATOR ← Regional scope                          │
│       ↓                                                          │
│  CONSTITUENCY_OFFICIAL ← Constituency scope                     │
│       ↓                                                          │
│  EXTENSION_OFFICER   ← Field officer                            │
│  VETERINARY_OFFICER  ← Field officer (animal health)            │
│  PROCUREMENT_OFFICER ← Specialized                              │
│  FINANCE_OFFICER     ← Specialized                              │
│  AUDITOR             ← Read-only audit access                   │
│       ↓                                                          │
│  FARMER              ← End user                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Role Constants
```typescript
export const USER_ROLES = {
  SUPER_ADMIN: 'SUPER_ADMIN',
  YEA_OFFICIAL: 'YEA_OFFICIAL',
  NATIONAL_ADMIN: 'NATIONAL_ADMIN',
  REGIONAL_COORDINATOR: 'REGIONAL_COORDINATOR',
  CONSTITUENCY_OFFICIAL: 'CONSTITUENCY_OFFICIAL',
  EXTENSION_OFFICER: 'EXTENSION_OFFICER',
  VETERINARY_OFFICER: 'VETERINARY_OFFICER',
  PROCUREMENT_OFFICER: 'PROCUREMENT_OFFICER',
  FINANCE_OFFICER: 'FINANCE_OFFICER',
  AUDITOR: 'AUDITOR',
  FARMER: 'FARMER',
} as const;
```

---

## 3. Authentication

All admin endpoints require JWT Bearer token authentication.

### Headers
```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Token Versioning (Force Logout)

The backend uses `token_version` to invalidate tokens. When a user is force-logged out:
1. Their `token_version` is incremented
2. All existing tokens become invalid
3. User must re-authenticate

**Frontend Handling:**
```typescript
// Check if token is invalidated (401 response)
if (response.status === 401 && response.data?.code === 'TOKEN_INVALID') {
  // Clear local tokens and redirect to login
  authService.logout();
  router.push('/login?reason=session_expired');
}
```

---

## 4. User CRUD Endpoints

### 4.1 List Users

```http
GET /api/admin/users/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20, max: 100) |
| `role` | string | Filter by role |
| `region` | string | Filter by region |
| `constituency` | string | Filter by constituency |
| `is_active` | boolean | Filter by active status |
| `is_suspended` | boolean | Filter by suspension status |
| `search` | string | Search name, email, phone |

**Response:**
```json
{
  "count": 150,
  "next": "/api/admin/users/?page=2",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "john.doe",
      "email": "john@example.com",
      "phone": "+233241234567",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "role": "REGIONAL_COORDINATOR",
      "role_display": "Regional Coordinator",
      "region": "Greater Accra",
      "constituency": null,
      "is_active": true,
      "is_verified": true,
      "is_suspended": false,
      "date_joined": "2025-06-01T00:00:00Z",
      "last_login_at": "2026-01-04T10:00:00Z"
    }
  ]
}
```

### 4.2 Get User Details

```http
GET /api/admin/users/{user_id}/
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john.doe",
  "email": "john@example.com",
  "phone": "+233241234567",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "role": "REGIONAL_COORDINATOR",
  "role_display": "Regional Coordinator",
  "preferred_contact_method": "EMAIL",
  "region": "Greater Accra",
  "constituency": null,
  "is_verified": true,
  "is_active": true,
  "phone_verified": true,
  "email_verified": true,
  "is_staff": true,
  "date_joined": "2025-06-01T00:00:00Z",
  "last_login_at": "2026-01-04T10:00:00Z",
  "created_at": "2025-06-01T00:00:00Z",
  "updated_at": "2026-01-04T12:00:00Z",
  "failed_login_attempts": 0,
  "account_locked_until": null,
  "is_suspended": false,
  "suspended_at": null,
  "suspended_until": null,
  "suspended_by": null,
  "suspended_by_name": null,
  "suspension_reason": "",
  "token_version": 0,
  "last_failed_login_at": null
}
```

### 4.3 Create User (Staff Invitation)

```http
POST /api/admin/users/create/
```

**Request Body:**
```json
{
  "email": "staff@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "CONSTITUENCY_OFFICIAL",
  "phone": "+233241234567",
  "region": "Greater Accra",
  "constituency": "Tema East"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "username": "jane.smith",
  "email": "staff@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "CONSTITUENCY_OFFICIAL",
  "is_active": false,
  "invitation_sent": true,
  "expires_at": "2026-01-11T00:00:00Z",
  "message": "Staff invitation sent successfully"
}
```

**Notes:**
- User is created in inactive state
- Invitation email is sent automatically
- User activates account by accepting invitation

### 4.4 Update User

```http
PUT /api/admin/users/{user_id}/
PATCH /api/admin/users/{user_id}/
```

**Request Body (partial update supported):**
```json
{
  "first_name": "Jane",
  "last_name": "Smith-Johnson",
  "region": "Ashanti",
  "is_active": true
}
```

**Protected Fields (read-only via this endpoint):**
- `is_suspended`, `suspended_at`, `suspended_until`, `suspension_reason`
- `token_version`, `last_failed_login_at`
- `date_joined`, `created_at`, `last_login_at`

**SUPER_ADMIN Protection:**
- SUPER_ADMIN accounts can ONLY be edited by themselves
- Other admins receive 403 Forbidden

### 4.5 Delete User

```http
DELETE /api/admin/users/{user_id}/
```

**Response (204 No Content)**

**Restrictions:**
- Only SUPER_ADMIN can delete users
- SUPER_ADMIN accounts CANNOT be deleted (returns 403)

---

## 5. User Action Endpoints

### 5.1 Suspend User

```http
POST /api/admin/users/{user_id}/suspend/
```

**Request Body:**
```json
{
  "reason": "Violation of terms of service",
  "duration_days": 30
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | Yes | Reason for suspension |
| `duration_days` | int | No | Days to suspend (null = indefinite) |

**Response:**
```json
{
  "message": "User suspended successfully.",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "suspended_until": "2026-02-04T00:00:00Z",
  "is_indefinite": false
}
```

**Permissions:**
- SUPER_ADMIN: Can suspend all (except SUPER_ADMIN)
- YEA_OFFICIAL: Can suspend lower roles (except YEA_OFFICIAL)
- NATIONAL_ADMIN: Can suspend lower roles (except YEA_OFFICIAL)

### 5.2 Unsuspend User

```http
POST /api/admin/users/{user_id}/unsuspend/
```

**Request Body:**
```json
{
  "reason": "Suspension review completed"
}
```

**Response:**
```json
{
  "message": "User unsuspended successfully.",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 5.3 Get Suspension Status

```http
GET /api/admin/users/{user_id}/suspension-status/
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john@example.com",
  "is_suspended": true,
  "suspended_at": "2026-01-04T10:00:00Z",
  "suspended_until": "2026-02-04T10:00:00Z",
  "suspended_by": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Admin Name",
    "email": "admin@example.com"
  },
  "suspension_reason": "Policy violation",
  "is_indefinite": false,
  "days_remaining": 30
}
```

### 5.4 Unlock Account

```http
POST /api/admin/users/{user_id}/unlock/
```

**Request Body:**
```json
{
  "reason": "User verified via phone"
}
```

**Response:**
```json
{
  "message": "Account unlocked successfully.",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "failed_login_attempts": 0
}
```

**Permissions:**
- SUPER_ADMIN and YEA_OFFICIAL only

**Note:** Accounts auto-lock after 5 failed login attempts (15-minute lockout)

### 5.5 Force Logout

```http
POST /api/admin/users/{user_id}/force-logout/
```

**Request Body:**
```json
{
  "reason": "Security concern - possible account compromise"
}
```

**Response:**
```json
{
  "message": "User logged out from all sessions.",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "sessions_terminated": 3,
  "token_version": 2
}
```

**Permissions:**
- SUPER_ADMIN only
- Cannot force logout other SUPER_ADMINs

### 5.6 Admin-Initiated Password Reset

```http
POST /api/admin/users/{user_id}/reset-password/
```

**Request Body:**
```json
{
  "notify_user": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `notify_user` | boolean | true | Send reset email to user |

**Response (notify_user=true):**
```json
{
  "message": "Password reset email sent successfully.",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "reset_link_sent": true
}
```

**Response (notify_user=false):**
```json
{
  "message": "Password reset token generated.",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "reset_link_sent": false,
  "token": "abc123...",
  "expires_at": "2026-01-05T00:00:00Z"
}
```

**Permissions:**
- SUPER_ADMIN: All users (except other SUPER_ADMINs)
- YEA_OFFICIAL: Lower roles only

### 5.7 Reset 2FA

```http
POST /api/admin/users/{user_id}/reset-2fa/
```

**Request Body:**
```json
{
  "reason": "User lost phone with authenticator app",
  "require_setup_on_next_login": true
}
```

**Response:**
```json
{
  "message": "2FA has been reset for user.",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "mfa_disabled": true,
  "require_setup_on_next_login": true
}
```

**Permissions:**
- SUPER_ADMIN only
- Cannot reset 2FA for SUPER_ADMIN accounts

### 5.8 Get Login Attempts

```http
GET /api/admin/users/{user_id}/login-attempts/
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john@example.com",
  "failed_attempts": 3,
  "locked": false,
  "locked_until": null,
  "last_failed_login_at": "2026-01-04T10:00:00Z",
  "last_successful_login_at": "2026-01-03T08:00:00Z",
  "is_suspended": false,
  "suspended_until": null
}
```

### 5.9 Get Login History

```http
GET /api/admin/users/{user_id}/login-history/
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john@example.com",
  "last_login": "2026-01-04T10:00:00Z",
  "date_joined": "2025-06-01T00:00:00Z",
  "account_created": "2025-06-01T00:00:00Z",
  "is_active": true,
  "is_suspended": false,
  "login_count": null,
  "recent_logins": [],
  "_note": "Detailed login history requires LoginHistory model implementation"
}
```

---

## 6. Staff Invitation Endpoints

### 6.1 Resend Invitation

```http
POST /api/admin/staff/{user_id}/resend-invitation/
```

**Response:**
```json
{
  "message": "Invitation resent successfully",
  "expires_at": "2026-01-11T00:00:00Z"
}
```

### 6.2 Cancel Invitation

```http
DELETE /api/admin/staff/{user_id}/cancel-invitation/
```

**Response (204 No Content)**

---

## 7. Permission Matrix

### User Actions

| Action | SUPER_ADMIN | YEA_OFFICIAL | NATIONAL_ADMIN | REGIONAL_COORD | Others |
|--------|:-----------:|:------------:|:--------------:|:--------------:|:------:|
| View all users | ✅ | ✅ | ✅ | Region only | Limited |
| Create users | ✅ All roles | Most roles | Most roles | Limited roles | ❌ |
| Edit SUPER_ADMIN | Self only | ❌ | ❌ | ❌ | ❌ |
| Edit YEA_OFFICIAL | ✅ | Self only | ❌ | ❌ | ❌ |
| Edit other users | ✅ | ✅ | ✅ | Region only | ❌ |
| Delete users | ✅ (not SUPER) | ❌ | ❌ | ❌ | ❌ |
| Suspend users | ✅ (not SUPER) | ✅ lower roles | ✅ lower roles | ❌ | ❌ |
| Unlock accounts | ✅ | ✅ | ❌ | ❌ | ❌ |
| Force logout | ✅ (not other SUPER) | ❌ | ❌ | ❌ | ❌ |
| Reset password | ✅ | ✅ lower roles | ❌ | ❌ | ❌ |
| Reset 2FA | ✅ (not SUPER) | ❌ | ❌ | ❌ | ❌ |

### SUPER_ADMIN Protection Rules

1. ❌ Cannot be edited by other users (403 Forbidden)
2. ❌ Cannot be deleted by anyone (403 Forbidden)
3. ❌ Cannot be suspended (403 Forbidden)
4. ❌ Cannot have 2FA reset by others (403 Forbidden)
5. ❌ Cannot be force-logged-out by other SUPER_ADMINs (403 Forbidden)
6. ✅ Can only self-edit their own profile
7. ✅ Can self-service password reset

---

## 8. TypeScript Interfaces

```typescript
// User Types
export interface AdminUser {
  id: string;
  username: string;
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: UserRole;
  role_display: string;
  preferred_contact_method: 'EMAIL' | 'PHONE' | 'SMS' | 'WHATSAPP';
  region: string | null;
  constituency: string | null;
  is_verified: boolean;
  is_active: boolean;
  phone_verified: boolean;
  email_verified: boolean;
  is_staff: boolean;
  date_joined: string;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
  
  // Security fields
  failed_login_attempts: number;
  account_locked_until: string | null;
  last_failed_login_at: string | null;
  
  // Suspension fields
  is_suspended: boolean;
  suspended_at: string | null;
  suspended_until: string | null;
  suspended_by: string | null;
  suspended_by_name: string | null;
  suspension_reason: string;
  
  token_version: number;
}

export type UserRole = 
  | 'SUPER_ADMIN'
  | 'YEA_OFFICIAL'
  | 'NATIONAL_ADMIN'
  | 'REGIONAL_COORDINATOR'
  | 'CONSTITUENCY_OFFICIAL'
  | 'EXTENSION_OFFICER'
  | 'VETERINARY_OFFICER'
  | 'PROCUREMENT_OFFICER'
  | 'FINANCE_OFFICER'
  | 'AUDITOR'
  | 'FARMER';

// Request Types
export interface SuspendUserRequest {
  reason: string;
  duration_days?: number | null;
}

export interface UnsuspendUserRequest {
  reason?: string;
}

export interface ResetPasswordRequest {
  notify_user?: boolean;
}

export interface ForceLogoutRequest {
  reason: string;
}

export interface Reset2FARequest {
  reason: string;
  require_setup_on_next_login?: boolean;
}

export interface UnlockAccountRequest {
  reason?: string;
}

// Response Types
export interface SuspendUserResponse {
  message: string;
  user_id: string;
  suspended_until: string | null;
  is_indefinite: boolean;
}

export interface LoginAttemptsResponse {
  user_id: string;
  email: string;
  failed_attempts: number;
  locked: boolean;
  locked_until: string | null;
  last_failed_login_at: string | null;
  last_successful_login_at: string | null;
  is_suspended: boolean;
  suspended_until: string | null;
}

export interface SuspensionStatusResponse {
  user_id: string;
  email: string;
  is_suspended: boolean;
  suspended_at: string | null;
  suspended_until: string | null;
  suspended_by: {
    id: string;
    name: string;
    email: string;
  } | null;
  suspension_reason: string;
  is_indefinite: boolean;
  days_remaining: number | null;
}

// Paginated Response
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
```

---

## 9. Error Handling

### Standard Error Response Format

```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE"
}
```

### Common Error Codes

| Status | Code | Description |
|--------|------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request data |
| 401 | `TOKEN_INVALID` | Token expired or invalidated |
| 403 | `PERMISSION_DENIED` | User lacks permission |
| 403 | `SUPER_ADMIN_PROTECTED` | Cannot modify SUPER_ADMIN |
| 404 | `USER_NOT_FOUND` | User does not exist |
| 409 | `ALREADY_SUSPENDED` | User already suspended |
| 409 | `NOT_SUSPENDED` | User not currently suspended |
| 409 | `NOT_LOCKED` | Account not locked |

### Frontend Error Handling Example

```typescript
import { AxiosError } from 'axios';

interface ApiError {
  error: string;
  code?: string;
  detail?: string;
}

export function handleApiError(error: AxiosError<ApiError>): string {
  if (!error.response) {
    return 'Network error. Please check your connection.';
  }
  
  const { status, data } = error.response;
  
  switch (status) {
    case 403:
      if (data.error?.includes('SUPER_ADMIN')) {
        return 'This action cannot be performed on SUPER_ADMIN accounts.';
      }
      return data.error || 'You do not have permission to perform this action.';
    
    case 404:
      return 'User not found.';
    
    case 409:
      return data.error || 'Operation cannot be completed due to current state.';
    
    default:
      return data.error || 'An unexpected error occurred.';
  }
}
```

---

## 10. Frontend Implementation Guide

### 10.1 Permission Checker Utility

```typescript
// src/utils/permissions.ts

export class PermissionChecker {
  private user: AdminUser;
  
  constructor(user: AdminUser) {
    this.user = user;
  }
  
  private getRoleLevel(role: UserRole): number {
    const levels: Record<UserRole, number> = {
      'SUPER_ADMIN': 100,
      'YEA_OFFICIAL': 90,
      'NATIONAL_ADMIN': 80,
      'REGIONAL_COORDINATOR': 70,
      'CONSTITUENCY_OFFICIAL': 60,
      'EXTENSION_OFFICER': 50,
      'VETERINARY_OFFICER': 50,
      'PROCUREMENT_OFFICER': 40,
      'FINANCE_OFFICER': 40,
      'AUDITOR': 30,
      'FARMER': 10,
    };
    return levels[role] || 0;
  }
  
  canViewUser(targetUser: AdminUser): boolean {
    // Admins can view based on geographic scope
    if (['SUPER_ADMIN', 'YEA_OFFICIAL', 'NATIONAL_ADMIN'].includes(this.user.role)) {
      return true;
    }
    
    if (this.user.role === 'REGIONAL_COORDINATOR') {
      return targetUser.region === this.user.region;
    }
    
    if (this.user.role === 'CONSTITUENCY_OFFICIAL') {
      return targetUser.constituency === this.user.constituency;
    }
    
    return this.user.id === targetUser.id;
  }
  
  canEditUser(targetUser: AdminUser): boolean {
    // SUPER_ADMIN can only be self-edited
    if (targetUser.role === 'SUPER_ADMIN') {
      return this.user.id === targetUser.id;
    }
    
    // Can always edit self
    if (this.user.id === targetUser.id) {
      return true;
    }
    
    // Check role hierarchy
    return this.getRoleLevel(this.user.role) > this.getRoleLevel(targetUser.role);
  }
  
  canDeleteUser(targetUser: AdminUser): boolean {
    // Only SUPER_ADMIN can delete
    if (this.user.role !== 'SUPER_ADMIN') return false;
    
    // Cannot delete SUPER_ADMIN accounts
    if (targetUser.role === 'SUPER_ADMIN') return false;
    
    return true;
  }
  
  canSuspendUser(targetUser: AdminUser): boolean {
    // SUPER_ADMIN cannot be suspended
    if (targetUser.role === 'SUPER_ADMIN') return false;
    
    // Only certain roles can suspend
    if (!['SUPER_ADMIN', 'YEA_OFFICIAL', 'NATIONAL_ADMIN'].includes(this.user.role)) {
      return false;
    }
    
    // Cannot suspend equal or higher roles
    return this.getRoleLevel(this.user.role) > this.getRoleLevel(targetUser.role);
  }
  
  canUnlockUser(targetUser: AdminUser): boolean {
    return ['SUPER_ADMIN', 'YEA_OFFICIAL'].includes(this.user.role);
  }
  
  canForceLogout(targetUser: AdminUser): boolean {
    if (this.user.role !== 'SUPER_ADMIN') return false;
    
    // Cannot force logout other SUPER_ADMINs
    if (targetUser.role === 'SUPER_ADMIN' && this.user.id !== targetUser.id) {
      return false;
    }
    
    return true;
  }
  
  canResetPassword(targetUser: AdminUser): boolean {
    // SUPER_ADMIN passwords - self only
    if (targetUser.role === 'SUPER_ADMIN') {
      return this.user.id === targetUser.id;
    }
    
    return ['SUPER_ADMIN', 'YEA_OFFICIAL'].includes(this.user.role);
  }
  
  canReset2FA(targetUser: AdminUser): boolean {
    if (this.user.role !== 'SUPER_ADMIN') return false;
    
    // Cannot reset 2FA for SUPER_ADMIN accounts
    if (targetUser.role === 'SUPER_ADMIN') return false;
    
    return true;
  }
}
```

### 10.2 API Service

```typescript
// src/services/userManagementService.ts

import axios from './axiosInstance';
import type {
  AdminUser,
  SuspendUserRequest,
  SuspendUserResponse,
  LoginAttemptsResponse,
  SuspensionStatusResponse,
  PaginatedResponse,
} from '@/types/user';

const BASE_URL = '/api/admin/users';

export const userManagementService = {
  // CRUD
  async listUsers(params?: Record<string, any>): Promise<PaginatedResponse<AdminUser>> {
    const response = await axios.get(BASE_URL, { params });
    return response.data;
  },
  
  async getUser(userId: string): Promise<AdminUser> {
    const response = await axios.get(`${BASE_URL}/${userId}/`);
    return response.data;
  },
  
  async updateUser(userId: string, data: Partial<AdminUser>): Promise<AdminUser> {
    const response = await axios.patch(`${BASE_URL}/${userId}/`, data);
    return response.data;
  },
  
  async deleteUser(userId: string): Promise<void> {
    await axios.delete(`${BASE_URL}/${userId}/`);
  },
  
  // Suspension
  async suspendUser(userId: string, data: SuspendUserRequest): Promise<SuspendUserResponse> {
    const response = await axios.post(`${BASE_URL}/${userId}/suspend/`, data);
    return response.data;
  },
  
  async unsuspendUser(userId: string, reason?: string): Promise<{ message: string }> {
    const response = await axios.post(`${BASE_URL}/${userId}/unsuspend/`, { reason });
    return response.data;
  },
  
  async getSuspensionStatus(userId: string): Promise<SuspensionStatusResponse> {
    const response = await axios.get(`${BASE_URL}/${userId}/suspension-status/`);
    return response.data;
  },
  
  // Security Actions
  async unlockAccount(userId: string, reason?: string): Promise<{ message: string }> {
    const response = await axios.post(`${BASE_URL}/${userId}/unlock/`, { reason });
    return response.data;
  },
  
  async forceLogout(userId: string, reason: string): Promise<{ message: string; sessions_terminated: number }> {
    const response = await axios.post(`${BASE_URL}/${userId}/force-logout/`, { reason });
    return response.data;
  },
  
  async resetPassword(userId: string, notifyUser = true): Promise<{ message: string; reset_link_sent: boolean }> {
    const response = await axios.post(`${BASE_URL}/${userId}/reset-password/`, { notify_user: notifyUser });
    return response.data;
  },
  
  async reset2FA(userId: string, reason: string, requireSetup = true): Promise<{ message: string }> {
    const response = await axios.post(`${BASE_URL}/${userId}/reset-2fa/`, {
      reason,
      require_setup_on_next_login: requireSetup,
    });
    return response.data;
  },
  
  // Login Info
  async getLoginAttempts(userId: string): Promise<LoginAttemptsResponse> {
    const response = await axios.get(`${BASE_URL}/${userId}/login-attempts/`);
    return response.data;
  },
  
  async getLoginHistory(userId: string): Promise<any> {
    const response = await axios.get(`${BASE_URL}/${userId}/login-history/`);
    return response.data;
  },
};
```

### 10.3 UI Component Example

```tsx
// src/components/admin/UserActionsMenu.tsx

import React from 'react';
import { Menu, MenuItem, IconButton } from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import { AdminUser } from '@/types/user';
import { PermissionChecker } from '@/utils/permissions';
import { useAuth } from '@/hooks/useAuth';

interface UserActionsMenuProps {
  user: AdminUser;
  onSuspend: () => void;
  onUnsuspend: () => void;
  onUnlock: () => void;
  onForceLogout: () => void;
  onResetPassword: () => void;
  onReset2FA: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export const UserActionsMenu: React.FC<UserActionsMenuProps> = ({
  user,
  onSuspend,
  onUnsuspend,
  onUnlock,
  onForceLogout,
  onResetPassword,
  onReset2FA,
  onEdit,
  onDelete,
}) => {
  const { currentUser } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  
  const permissions = new PermissionChecker(currentUser);
  
  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };
  
  const handleClose = () => {
    setAnchorEl(null);
  };
  
  return (
    <>
      <IconButton onClick={handleClick}>
        <MoreVertIcon />
      </IconButton>
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleClose}>
        {permissions.canEditUser(user) && (
          <MenuItem onClick={() => { handleClose(); onEdit(); }}>
            Edit User
          </MenuItem>
        )}
        
        {permissions.canSuspendUser(user) && !user.is_suspended && (
          <MenuItem onClick={() => { handleClose(); onSuspend(); }}>
            Suspend User
          </MenuItem>
        )}
        
        {permissions.canSuspendUser(user) && user.is_suspended && (
          <MenuItem onClick={() => { handleClose(); onUnsuspend(); }}>
            Unsuspend User
          </MenuItem>
        )}
        
        {permissions.canUnlockUser(user) && user.account_locked_until && (
          <MenuItem onClick={() => { handleClose(); onUnlock(); }}>
            Unlock Account
          </MenuItem>
        )}
        
        {permissions.canForceLogout(user) && (
          <MenuItem onClick={() => { handleClose(); onForceLogout(); }}>
            Force Logout
          </MenuItem>
        )}
        
        {permissions.canResetPassword(user) && (
          <MenuItem onClick={() => { handleClose(); onResetPassword(); }}>
            Reset Password
          </MenuItem>
        )}
        
        {permissions.canReset2FA(user) && (
          <MenuItem onClick={() => { handleClose(); onReset2FA(); }}>
            Reset 2FA
          </MenuItem>
        )}
        
        {permissions.canDeleteUser(user) && (
          <MenuItem onClick={() => { handleClose(); onDelete(); }} sx={{ color: 'error.main' }}>
            Delete User
          </MenuItem>
        )}
      </Menu>
    </>
  );
};
```

---

## Appendix: URL Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users/` | List users (paginated) |
| POST | `/api/admin/users/create/` | Create user (send invitation) |
| GET | `/api/admin/users/{id}/` | Get user details |
| PUT/PATCH | `/api/admin/users/{id}/` | Update user |
| DELETE | `/api/admin/users/{id}/` | Delete user |
| POST | `/api/admin/users/{id}/suspend/` | Suspend user |
| POST | `/api/admin/users/{id}/unsuspend/` | Unsuspend user |
| GET | `/api/admin/users/{id}/suspension-status/` | Get suspension details |
| POST | `/api/admin/users/{id}/unlock/` | Unlock locked account |
| POST | `/api/admin/users/{id}/force-logout/` | Force logout all sessions |
| POST | `/api/admin/users/{id}/reset-password/` | Admin-initiated password reset |
| POST | `/api/admin/users/{id}/reset-2fa/` | Reset user's 2FA |
| GET | `/api/admin/users/{id}/login-attempts/` | Get login attempt info |
| GET | `/api/admin/users/{id}/login-history/` | Get login history |
| POST | `/api/admin/staff/{id}/resend-invitation/` | Resend invitation |
| DELETE | `/api/admin/staff/{id}/cancel-invitation/` | Cancel invitation |

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-04 | 1.0 | Initial release with all user management endpoints |

---

**Questions?** Contact the backend team or open an issue in the repository.
