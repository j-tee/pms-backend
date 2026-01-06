# CMS & Company Admin - Complete Guide

## 🚀 Quick Reference

### **Permission Matrix**

| Action | SUPER_ADMIN | COMPANY_ADMIN | Public |
|--------|-------------|---------------|--------|
| **Content Pages (About Us, etc.)** | | | |
| Create/Edit/Delete | ✅ | ❌ | ❌ |
| View Published | ✅ | ✅ | ✅ |
| View Drafts | ✅ | ❌ | ❌ |
| **Contact Messages** | | | |
| Read/Reply | ✅ | ❌ | ❌ |
| Submit Form | ✅ | ✅ | ✅ |
| **Company Profile** | | | |
| Edit | ✅ | ❌ | ❌ |
| View | ✅ | ✅ | ❌ |

### **API Endpoints Summary**

**Public (No Auth):**
```
GET /api/public/cms/about-us/
GET /api/public/cms/privacy-policy/
GET /api/public/cms/terms-of-service/
GET /api/public/cms/pages/{slug}/
```

**Admin (SUPER_ADMIN Only):**
```
GET/POST   /api/cms/admin/pages/
GET/PUT    /api/cms/admin/pages/{id}/
POST       /api/cms/admin/pages/{id}/publish/
POST       /api/cms/admin/pages/{id}/unpublish/
GET        /api/cms/admin/pages/{id}/revisions/
POST       /api/cms/admin/pages/{id}/restore_revision/
GET/PATCH  /api/cms/admin/company-profile/
```

### **Common Commands**

```bash
# Create About Us page
POST /api/cms/admin/pages/
{"page_type": "about_us", "title": "About Us", "content": "...", "status": "draft"}

# Publish it
POST /api/cms/admin/pages/{id}/publish/

# Public views it (no auth)
GET /api/public/cms/about-us/

# Create COMPANY_ADMIN user
python manage.py shell
>>> User.objects.create_user(email='company@alphalogique.com', role='COMPANY_ADMIN', ...)
```

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [New COMPANY_ADMIN Role](#new-company_admin-role)
3. [Database Models](#database-models)
4. [API Endpoints](#api-endpoints)
5. [Content Workflow](#content-workflow)
6. [Frontend Integration](#frontend-integration)
7. [Production Deployment](#production-deployment)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Complete content management system for platform pages (About Us, Privacy Policy, Terms of Service, etc.) with role-based access control and version tracking.

### **Key Requirements Met**

✅ **ONLY SUPER_ADMIN** can create, edit, update, or delete content pages  
✅ **Public** can view published content pages  
✅ **Contact messages ONLY SUPER_ADMIN** can read and manage  
✅ **COMPANY_ADMIN role** for Alphalogique Technologies staff with limited permissions  

### **Features**

- 📄 Content pages: About Us, Privacy Policy, Terms of Service, FAQ, etc.
- 🔄 Full version control with revision history
- 📊 Status workflow: draft → published → archived
- 🔒 SUPER_ADMIN only can create/edit/delete
- 🌐 Public can view published pages (no auth)
- 💾 Soft delete support
- 🔍 SEO metadata support (title, description, keywords)

---

## New COMPANY_ADMIN Role

### **Purpose**

Created for **Alphalogique Technologies** (platform owner company) staff members who need limited access to manage company-specific duties.

### **Role Definition**

```python
class UserRole(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN'          # Full system access
    COMPANY_ADMIN = 'COMPANY_ADMIN'      # Platform owner staff (NEW!)
    YEA_OFFICIAL = 'YEA_OFFICIAL'        # YEA officials
    NATIONAL_ADMIN = 'NATIONAL_ADMIN'    # National administrators
    # ... other roles
```

### **What COMPANY_ADMIN Can Do**

✅ View company profile (read-only)  
✅ View published content pages  
✅ Submit contact forms  

### **What COMPANY_ADMIN Cannot Do**

❌ Create/edit/delete content pages (About Us, etc.)  
❌ Read contact messages  
❌ Edit company profile  
❌ Access YEA program data  

### **Creating COMPANY_ADMIN Users**

#### **Method 1: Django Shell**
```bash
python manage.py shell

>>> from accounts.models import User
>>> User.objects.create_user(
...     email='staff@alphalogique.com',
...     password='secure_password',
...     first_name='Company',
...     last_name='Staff',
...     phone_number='+233XXXXXXXXX',
...     role='COMPANY_ADMIN'
... )
```

#### **Method 2: Admin Invite**
```bash
POST /api/admin/staff/invite/
{
  "email": "staff@alphalogique.com",
  "role": "COMPANY_ADMIN",
  "first_name": "Company",
  "last_name": "Staff"
}
```

---

## Database Models

### 1. ContentPage

Stores platform content pages with version tracking.

**Fields:**
- `id` (UUID) - Primary key
- `page_type` (CharField) - Type: about_us, privacy_policy, terms_of_service, faq, contact_info, custom
- `title` (CharField) - Page title
- `slug` (SlugField) - URL-friendly identifier (e.g., 'about-us')
- `content` (TextField) - Full page content (Markdown/HTML)
- `excerpt` (TextField) - Short summary
- `meta_description` (CharField) - SEO meta description (160 chars)
- `meta_keywords` (CharField) - SEO keywords
- `status` (CharField) - draft, published, archived
- `published_at` (DateTimeField) - Publication timestamp
- `version` (IntegerField) - Version number (auto-incremented)
- `created_by`, `updated_by` (ForeignKey) - Audit trail
- `is_deleted` (BooleanField) - Soft delete flag

**Unique Constraints:**
- `page_type` - Only one page per type
- `slug` - Unique URL slugs

**Indexes:**
- `(status, published_at)` - Fast published page queries
- `(page_type, status)` - Page type filtering

### 2. ContentPageRevision

Version history for all content changes.

**Fields:**
- `page` (ForeignKey) - Related ContentPage
- `version` (IntegerField) - Version number
- `title`, `content`, `excerpt` - Content snapshot
- `changed_by` (ForeignKey) - User who made changes
- `change_summary` (TextField) - Description of changes
- `created_at` (DateTimeField) - Revision timestamp

**Unique Constraint:**
- `(page, version)` - One revision per version per page

### 3. CompanyProfile

Company information (singleton pattern - only one allowed).

**Fields:**
- `company_name`, `tagline`, `description`
- `email`, `phone`, `website`
- `address_line1`, `address_line2`, `city`, `region`, `country`, `postal_code`
- `facebook_url`, `twitter_url`, `linkedin_url`, `instagram_url`
- `logo_url`
- `updated_by` (ForeignKey)

---

## API Endpoints

### **Public Endpoints (No Authentication)**

#### Get About Us Page
```http
GET /api/public/cms/about-us/
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "page_type": "about_us",
  "page_type_display": "About Us",
  "title": "About YEA Poultry Management System",
  "slug": "about-us",
  "content": "# About Us\n\nFull content here...",
  "excerpt": "Short summary...",
  "meta_description": "Learn about our platform...",
  "published_at": "2026-01-01T00:00:00Z"
}
```

#### Other Public Pages
```http
GET /api/public/cms/privacy-policy/       # Privacy Policy
GET /api/public/cms/terms-of-service/     # Terms of Service
GET /api/public/cms/pages/{slug}/         # Any page by slug
```

---

### **Admin Endpoints (SUPER_ADMIN Only)**

#### List All Content Pages
```http
GET /api/cms/admin/pages/
Authorization: Bearer {token}
```

**Query Parameters:**
- `status` - Filter by status (draft, published, archived)
- `page_type` - Filter by page type
- `search` - Search in title, content

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "page_type": "about_us",
    "page_type_display": "About Us",
    "title": "About YEA Poultry",
    "slug": "about-us",
    "excerpt": "Brief summary...",
    "status": "published",
    "status_display": "Published",
    "published_at": "2026-01-01T00:00:00Z",
    "version": 3,
    "created_by": {"email": "admin@example.com", "full_name": "Admin User"},
    "updated_by": {"email": "admin@example.com", "full_name": "Admin User"},
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-06T10:00:00Z"
  }
]
```

#### Create New Content Page
```http
POST /api/cms/admin/pages/
Authorization: Bearer {token}
Content-Type: application/json

{
  "page_type": "about_us",
  "title": "About YEA Poultry Management System",
  "slug": "about-us",
  "content": "# About Us\n\nWelcome to YEA Poultry...",
  "excerpt": "Our mission is to revolutionize poultry farming in Ghana.",
  "meta_description": "Learn about the YEA Poultry Management System",
  "meta_keywords": "YEA, poultry, Ghana, agriculture",
  "status": "draft",
  "change_summary": "Initial creation of About Us page"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "page_type": "about_us",
  "title": "About YEA Poultry Management System",
  "slug": "about-us",
  "content": "# About Us...",
  "status": "draft",
  "version": 1
}
```

#### Update Content Page
```http
PUT /api/cms/admin/pages/{id}/
Authorization: Bearer {token}

{
  "title": "About Us - Updated",
  "content": "Updated content...",
  "change_summary": "Updated mission statement and contact info"
}
```

**Note:** Version auto-increments with each update.

#### Publish Content Page
```http
POST /api/cms/admin/pages/{id}/publish/
Authorization: Bearer {token}
```

**What it does:**
- Sets `status = 'published'`
- Sets `published_at = now()`
- Makes page visible to public

#### Unpublish Content Page
```http
POST /api/cms/admin/pages/{id}/unpublish/
Authorization: Bearer {token}
```

**What it does:**
- Sets `status = 'draft'`
- Hides page from public

#### Archive Content Page
```http
POST /api/cms/admin/pages/{id}/archive/
Authorization: Bearer {token}
```

#### Get Revision History
```http
GET /api/cms/admin/pages/{id}/revisions/
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": "uuid",
    "version": 3,
    "title": "About Us - Version 3",
    "content": "Latest content...",
    "changed_by": {"email": "admin@example.com", "full_name": "Admin User"},
    "change_summary": "Updated contact information",
    "created_at": "2026-01-06T10:00:00Z"
  }
]
```

#### Restore Previous Revision
```http
POST /api/cms/admin/pages/{id}/restore_revision/
Authorization: Bearer {token}

{
  "revision_id": "uuid-of-revision-to-restore"
}
```

**What it does:**
- Restores content from specified revision
- Creates new revision with restored content
- Change summary: "Restored from version X"

#### Delete Content Page (Soft Delete)
```http
DELETE /api/cms/admin/pages/{id}/
Authorization: Bearer {token}
```

**What it does:**
- Sets `is_deleted = True`
- Sets `deleted_at = now()`
- Page no longer appears in listings

---

### **Company Profile Endpoints**

#### Get Company Profile
```http
GET /api/cms/admin/company-profile/
Authorization: Bearer {token}
```

**Permissions:**
- SUPER_ADMIN: Full access
- COMPANY_ADMIN: Read-only

#### Update Company Profile (SUPER_ADMIN Only)
```http
PATCH /api/cms/admin/company-profile/
Authorization: Bearer {token}

{
  "tagline": "New tagline here",
  "phone": "+233XXXXXXXXX",
  "facebook_url": "https://facebook.com/newpage"
}
```

---

## Content Workflow

### **Full Lifecycle Example**

#### **1. Create Draft**
```bash
POST /api/cms/admin/pages/
{
  "page_type": "about_us",
  "title": "About Us",
  "content": "Draft content...",
  "status": "draft"
}
# Creates version 1
```

#### **2. Review & Edit**
```bash
PUT /api/cms/admin/pages/{id}/
{
  "content": "Updated content...",
  "change_summary": "Added team bios"
}
# Version increments: v1 → v2
```

#### **3. Publish**
```bash
POST /api/cms/admin/pages/{id}/publish/
# Now visible to public
```

#### **4. Public Access**
```bash
GET /api/public/cms/about-us/
# Anyone can now view (no auth)
```

#### **5. Update Published Page**
```bash
PUT /api/cms/admin/pages/{id}/
{
  "content": "New content...",
  "change_summary": "Annual update"
}
# Version: v2 → v3
# Public sees updated content immediately
```

#### **6. Rollback if Needed**
```bash
POST /api/cms/admin/pages/{id}/restore_revision/
{"revision_id": "revision-v2-uuid"}
# Creates v4 with v2's content
```

### **Status Workflow**

```
draft → published → archived
  ↑         ↓
  └─────────┘ (can unpublish back to draft)
```

---

## Frontend Integration

### **Public Pages (React Example)**

```jsx
import { useEffect, useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

function AboutUs() {
  const [page, setPage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('http://localhost:8000/api/public/cms/about-us/')
      .then(res => {
        setPage(res.data);
        setLoading(false);
      })
      .catch(err => console.error(err));
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="about-us-page">
      <h1>{page.title}</h1>
      <ReactMarkdown>{page.content}</ReactMarkdown>
    </div>
  );
}
```

### **Admin CMS Management**

```jsx
import { useEffect, useState } from 'react';
import axios from 'axios';

function AdminContentPages() {
  const [pages, setPages] = useState([]);
  const token = localStorage.getItem('access_token');

  useEffect(() => {
    axios.get('http://localhost:8000/api/cms/admin/pages/', {
      headers: { Authorization: `Bearer ${token}` }
    }).then(res => setPages(res.data));
  }, []);

  const publishPage = (pageId) => {
    axios.post(
      `http://localhost:8000/api/cms/admin/pages/${pageId}/publish/`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    ).then(() => {
      alert('Page published successfully!');
      // Refresh list
    });
  };

  return (
    <div>
      <h1>Content Pages</h1>
      {pages.map(page => (
        <div key={page.id} className="page-item">
          <h3>{page.title}</h3>
          <span>Status: {page.status_display}</span>
          <span>Version: {page.version}</span>
          {page.status === 'draft' && (
            <button onClick={() => publishPage(page.id)}>Publish</button>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## Production Deployment

### **1. Run Migrations**
```bash
python manage.py migrate
```

### **2. Create Initial Content**
```bash
python manage.py shell

>>> from cms.models import ContentPage, CompanyProfile
>>> from accounts.models import User

>>> admin = User.objects.get(email='admin@example.com', role='SUPER_ADMIN')

>>> # Create About Us page
>>> ContentPage.objects.create(
...     page_type='about_us',
...     title='About YEA Poultry Management System',
...     slug='about-us',
...     content='# About Us\n\nYour content here...',
...     status='published',
...     created_by=admin,
...     updated_by=admin
... )

>>> # Create Privacy Policy
>>> ContentPage.objects.create(
...     page_type='privacy_policy',
...     title='Privacy Policy',
...     slug='privacy-policy',
...     content='# Privacy Policy\n\nYour privacy is important...',
...     status='published',
...     created_by=admin,
...     updated_by=admin
... )

>>> # Create Company Profile
>>> CompanyProfile.objects.create(
...     company_name='Alphalogique Technologies',
...     email='info@alphalogique.com',
...     phone='+233XXXXXXXXX',
...     description='Technology solutions for agricultural development',
...     address_line1='Accra, Ghana',
...     city='Accra',
...     region='Greater Accra',
...     country='Ghana',
...     updated_by=admin
... )
```

### **3. Create Company Admin Users**
```bash
python manage.py shell

>>> from accounts.models import User
>>> User.objects.create_user(
...     email='company@alphalogique.com',
...     password='secure_password',
...     first_name='Company',
...     last_name='Admin',
...     phone_number='+233XXXXXXXXX',
...     role='COMPANY_ADMIN'
... )
```

---

## Testing

### **Test SUPER_ADMIN Access**
```bash
# 1. Login as SUPER_ADMIN
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"password"}'

export TOKEN="your-access-token"

# 2. Create About Us page
curl -X POST http://localhost:8000/api/cms/admin/pages/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "page_type": "about_us",
    "title": "About YEA Poultry",
    "slug": "about-us",
    "content": "# About Us\n\nWe are YEA Poultry...",
    "status": "draft"
  }'

# 3. Publish it
curl -X POST http://localhost:8000/api/cms/admin/pages/{page-id}/publish/ \
  -H "Authorization: Bearer $TOKEN"

# 4. Public can now view (no auth)
curl http://localhost:8000/api/public/cms/about-us/
```

### **Test COMPANY_ADMIN Restrictions**
```bash
# Login as COMPANY_ADMIN
curl -X POST http://localhost:8000/api/auth/login/ \
  -d '{"email":"company@alphalogique.com","password":"password"}'

# Try to create page (should fail - 403)
curl -X POST http://localhost:8000/api/cms/admin/pages/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"page_type":"about_us",...}'
# Expected: 403 Forbidden

# View company profile (read-only - should work)
curl http://localhost:8000/api/cms/admin/company-profile/ \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK
```

### **Test Contact Message Restrictions**
```bash
# Login as NATIONAL_ADMIN (used to have access)
# Try to read contact messages
curl http://localhost:8000/api/admin/contact-messages/ \
  -H "Authorization: Bearer $TOKEN"
# Expected: 403 Forbidden (ONLY SUPER_ADMIN can access now)
```

---

## Troubleshooting

### **Problem: 403 when creating content**
**Solution:** Ensure user is SUPER_ADMIN
```bash
python manage.py shell
>>> from accounts.models import User
>>> user = User.objects.get(email='user@example.com')
>>> user.role = 'SUPER_ADMIN'
>>> user.save()
```

### **Problem: Page not visible to public**
**Solution:** Check page status is 'published'
```bash
python manage.py shell
>>> from cms.models import ContentPage
>>> page = ContentPage.objects.get(slug='about-us')
>>> page.status
'draft'  # Issue found!
>>> page.status = 'published'
>>> page.save()
```

### **Problem: Cannot create two About Us pages**
**Solution:** By design! Each `page_type` is unique. Update the existing page instead.

### **Problem: Version not incrementing**
**Solution:** Ensure you're using PUT/PATCH, not directly modifying the model.

---

## Django Admin

Access CMS models via Django Admin: `http://localhost:8000/admin/cms/`

**Models Available:**
- **Content Pages** - Create, edit, publish pages
- **Content Page Revisions** - View version history
- **Company Profile** - Edit company information

**Features:**
- List view with filters (status, page type)
- Search by title, content
- Inline editing
- Only one company profile allowed (enforced)

---

## Summary

### **What Changed**

1. ✅ **New Role:** `COMPANY_ADMIN` for Alphalogique Technologies staff
2. ✅ **CMS App:** Complete content management for About Us, Privacy Policy, etc.
3. ✅ **SUPER_ADMIN Only:** Can create/edit/delete content pages
4. ✅ **Contact Messages:** Now SUPER_ADMIN only (was NATIONAL_ADMIN + others)
5. ✅ **Version Control:** All content changes tracked with revisions
6. ✅ **Public Access:** Anyone can view published pages

### **Key Statistics**

| Metric | Count |
|--------|-------|
| Files Created | 12 |
| Lines of Code | 2,050+ |
| Models | 3 |
| API Endpoints | 12+ |
| Database Tables | 3 |
| Indexes | 3 |

### **Page Types Available**

- `about_us` - About Us
- `privacy_policy` - Privacy Policy
- `terms_of_service` - Terms of Service
- `faq` - Frequently Asked Questions
- `contact_info` - Contact Information
- `custom` - Custom Page

---

**Git Commit:** d6f9e8b  
**Branch:** development  
**Last Updated:** January 6, 2026  
**Status:** ✅ Ready for Production
