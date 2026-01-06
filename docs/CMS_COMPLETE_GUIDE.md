# Content Management System (CMS) - Complete Guide

## Overview

Complete content management system for platform pages (About Us, Privacy Policy, Terms of Service, etc.) with role-based access control.

### **Key Requirements Met**

✅ **ONLY SUPER_ADMIN** can create, edit, update, or delete content pages (About Us, etc.)  
✅ **Public** can view published content pages  
✅ **Contact messages ONLY SUPER_ADMIN** can read and manage  
✅ **COMPANY_ADMIN role** added for Alphalogique Technologies staff with limited permissions  

---

## Role Hierarchy & Permissions

### **New Role: COMPANY_ADMIN**

Added for **Alphalogique Technologies** (platform owner company) staff.

```python
class UserRole(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN'          # Full system access
    COMPANY_ADMIN = 'COMPANY_ADMIN'      # Platform owner staff (NEW!)
    YEA_OFFICIAL = 'YEA_OFFICIAL'        # YEA officials
    NATIONAL_ADMIN = 'NATIONAL_ADMIN'    # National administrators
    # ... other roles
```

### **Permission Matrix**

| Feature | SUPER_ADMIN | COMPANY_ADMIN | Public |
|---------|-------------|---------------|--------|
| **About Us Page** |
| Create/Edit/Delete | ✅ | ❌ | ❌ |
| View Published | ✅ | ✅ | ✅ |
| View Drafts | ✅ | ❌ | ❌ |
| **Contact Messages** |
| Read/Manage | ✅ | ❌ | ❌ |
| Submit | ✅ | ✅ | ✅ |
| **Company Profile** |
| Edit | ✅ | ❌ | ❌ |
| View | ✅ | ✅ | ❌ |

---

## Database Models

### 1. ContentPage

Stores platform content pages (About Us, Privacy Policy, etc.).

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
- `created_by` (ForeignKey) - User who created
- `updated_by` (ForeignKey) - Last user who updated
- `is_deleted` (BooleanField) - Soft delete flag

**Indexes:**
- `(status, published_at)` - For filtering published pages
- `(page_type, status)` - For page type queries

**Unique Constraints:**
- `page_type` - Only one page per type
- `slug` - Unique URL slugs

### 2. ContentPageRevision

Version history for content pages.

**Fields:**
- `id` (UUID) - Primary key
- `page` (ForeignKey) - Related ContentPage
- `version` (IntegerField) - Version number
- `title`, `content`, `excerpt` - Snapshot of page content
- `changed_by` (ForeignKey) - User who made changes
- `change_summary` (TextField) - Description of changes
- `created_at` (DateTimeField) - Revision timestamp

**Unique Constraint:**
- `(page, version)` - One revision per version per page

### 3. CompanyProfile

Company information for Alphalogique Technologies.

**Fields:**
- `company_name`, `tagline`, `description`
- `email`, `phone`, `website`
- `address_line1`, `address_line2`, `city`, `region`, `country`, `postal_code`
- `facebook_url`, `twitter_url`, `linkedin_url`, `instagram_url`
- `logo_url`
- `updated_by` (ForeignKey)

**Singleton Pattern:** Only one company profile allowed.

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
  "content": "Full page content here...",
  "excerpt": "Short summary...",
  "meta_description": "Learn about our platform...",
  "published_at": "2026-01-01T00:00:00Z"
}
```

#### Get Privacy Policy
```http
GET /api/public/cms/privacy-policy/
```

#### Get Terms of Service
```http
GET /api/public/cms/terms-of-service/
```

#### Get Any Page by Slug
```http
GET /api/public/cms/pages/{slug}/
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
    "created_by": {
      "id": "uuid",
      "email": "admin@example.com",
      "full_name": "Admin User"
    },
    "updated_by": {
      "id": "uuid",
      "email": "admin@example.com",
      "full_name": "Admin User"
    },
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-06T10:00:00Z"
  }
]
```

#### Get Content Page Details
```http
GET /api/cms/admin/pages/{id}/
Authorization: Bearer {token}
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
  "content": "# About Us\n\nWelcome to the YEA Poultry Management System...",
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
Content-Type: application/json

{
  "title": "About Us - Updated",
  "content": "Updated content...",
  "change_summary": "Updated mission statement and contact info"
}
```

**Response (200 OK):** Updated page with `version` incremented

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
    "changed_by": {
      "email": "admin@example.com",
      "full_name": "Admin User"
    },
    "change_summary": "Updated contact information",
    "created_at": "2026-01-06T10:00:00Z"
  },
  {
    "id": "uuid",
    "version": 2,
    "title": "About Us - Version 2",
    "content": "Previous content...",
    "changed_by": {
      "email": "admin@example.com",
      "full_name": "Admin User"
    },
    "change_summary": "Fixed typos",
    "created_at": "2026-01-02T15:30:00Z"
  }
]
```

#### Restore Previous Revision
```http
POST /api/cms/admin/pages/{id}/restore_revision/
Authorization: Bearer {token}
Content-Type: application/json

{
  "revision_id": "uuid-of-revision-to-restore"
}
```

**What it does:**
- Restores content from specified revision
- Creates new revision (e.g., v4) with restored content
- Change summary: "Restored from version X"

#### Delete Content Page (Soft Delete)
```http
DELETE /api/cms/admin/pages/{id}/
Authorization: Bearer {token}
```

**What it does:**
- Sets `is_deleted = True`
- Sets `deleted_at = now()`
- Sets `deleted_by = current_user`
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

**Response (200 OK):**
```json
{
  "id": "uuid",
  "company_name": "Alphalogique Technologies",
  "tagline": "Innovating Agriculture Through Technology",
  "description": "We build technology solutions...",
  "email": "info@alphalogique.com",
  "phone": "+233XXXXXXXXX",
  "website": "https://alphalogique.com",
  "address_line1": "123 Tech Street",
  "city": "Accra",
  "region": "Greater Accra",
  "country": "Ghana",
  "facebook_url": "https://facebook.com/alphalogique",
  "linkedin_url": "https://linkedin.com/company/alphalogique",
  "logo_url": "https://cdn.example.com/logo.png",
  "updated_by": {
    "email": "admin@example.com",
    "full_name": "Admin User"
  },
  "updated_at": "2026-01-06T10:00:00Z"
}
```

#### Update Company Profile (SUPER_ADMIN Only)
```http
PATCH /api/cms/admin/company-profile/
Authorization: Bearer {token}
Content-Type: application/json

{
  "tagline": "New tagline here",
  "phone": "+233XXXXXXXXX",
  "facebook_url": "https://facebook.com/newpage"
}
```

---

## Contact Message Permissions (Updated)

### **SUPER_ADMIN Only Access**

Contact message management is now **SUPER_ADMIN only**:

```http
GET /api/admin/contact-messages/
Authorization: Bearer {SUPER_ADMIN_token}
```

**Other roles (NATIONAL_ADMIN, REGIONAL_COORDINATOR, etc.):** ❌ **403 Forbidden**

---

## Content Workflow

### 1. **Create Draft**
```bash
# SUPER_ADMIN creates About Us page
POST /api/cms/admin/pages/
{
  "page_type": "about_us",
  "title": "About Us",
  "content": "...",
  "status": "draft"
}
```

### 2. **Review & Edit**
```bash
# SUPER_ADMIN reviews and updates
PUT /api/cms/admin/pages/{id}/
{
  "content": "Updated content...",
  "change_summary": "Added team bios"
}
# Version increments: v1 → v2
```

### 3. **Publish**
```bash
# Make live to public
POST /api/cms/admin/pages/{id}/publish/
```

### 4. **Public Access**
```bash
# Anyone can now view
GET /api/public/cms/about-us/
# No authentication required
```

### 5. **Update Published Page**
```bash
# SUPER_ADMIN updates live page
PUT /api/cms/admin/pages/{id}/
{
  "content": "New content...",
  "change_summary": "Annual update"
}
# Version increments: v2 → v3
# Public sees updated content immediately
```

### 6. **Rollback if Needed**
```bash
# Restore previous version
POST /api/cms/admin/pages/{id}/restore_revision/
{
  "revision_id": "revision-v2-uuid"
}
# Creates v4 with v2's content
```

---

## Frontend Integration

### **Public Pages (No Auth Required)**

```jsx
// AboutUs.jsx
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

export default AboutUs;
```

### **Admin CMS Management**

```jsx
// AdminContentPages.jsx
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

## Creating Company Admin Users

### **Method 1: Django Shell**
```bash
python manage.py shell

>>> from accounts.models import User
>>> company_admin = User.objects.create_user(
...     email='staff@alphalogique.com',
...     password='secure_password',
...     first_name='Company',
...     last_name='Staff',
...     phone_number='+233XXXXXXXXX',
...     role='COMPANY_ADMIN'
... )
>>> company_admin.save()
```

### **Method 2: Admin Invite**

SUPER_ADMIN can invite company staff via `/api/admin/staff/invite/`:

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

## Testing

### **Test SUPER_ADMIN Access**
```bash
# Login as SUPER_ADMIN
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"password"}'

# Use returned token
export TOKEN="your-access-token"

# Create About Us page
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

# Publish it
curl -X POST http://localhost:8000/api/cms/admin/pages/{page-id}/publish/ \
  -H "Authorization: Bearer $TOKEN"

# Public can now view (no auth)
curl http://localhost:8000/api/public/cms/about-us/
```

### **Test COMPANY_ADMIN Access**
```bash
# Login as COMPANY_ADMIN
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
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
curl -X POST http://localhost:8000/api/auth/login/ \
  -d '{"email":"national@test.com","password":"password"}'

# Try to read contact messages
curl http://localhost:8000/api/admin/contact-messages/ \
  -H "Authorization: Bearer $TOKEN"
# Expected: 403 Forbidden (ONLY SUPER_ADMIN can access)
```

---

## Django Admin

Access CMS models via Django Admin:

**URL:** `http://localhost:8000/admin/cms/`

**Models:**
- **Content Pages** - Create, edit, publish pages
- **Content Page Revisions** - View version history
- **Company Profile** - Edit company information

**Features:**
- List view with filters (status, page type)
- Search by title, content
- Inline editing
- Only one company profile allowed

---

## Production Deployment

### 1. **Environment Variables**
```bash
# No additional env vars needed
# Uses existing Django/PostgreSQL setup
```

### 2. **Run Migrations**
```bash
python manage.py migrate
```

### 3. **Create Initial Content**
```bash
python manage.py shell

>>> from cms.models import ContentPage, CompanyProfile
>>> from accounts.models import User

>>> admin = User.objects.get(role='SUPER_ADMIN')

>>> # Create About Us page
>>> about_us = ContentPage.objects.create(
...     page_type='about_us',
...     title='About YEA Poultry Management System',
...     slug='about-us',
...     content='# About Us\n\nContent here...',
...     status='published',
...     created_by=admin,
...     updated_by=admin
... )

>>> # Create company profile
>>> company = CompanyProfile.objects.create(
...     company_name='Alphalogique Technologies',
...     email='info@alphalogique.com',
...     phone='+233XXXXXXXXX',
...     description='Technology solutions for agriculture',
...     address_line1='Accra, Ghana',
...     city='Accra',
...     region='Greater Accra',
...     country='Ghana'
... )
```

### 4. **Create Company Admin Users**
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

## Summary

### **What Changed**

1. ✅ **New Role:** `COMPANY_ADMIN` for Alphalogique Technologies staff
2. ✅ **CMS App:** Complete content management for About Us, Privacy Policy, etc.
3. ✅ **SUPER_ADMIN Only:** Can create/edit/delete content pages
4. ✅ **Contact Messages:** Now SUPER_ADMIN only (was NATIONAL_ADMIN + others)
5. ✅ **Version Control:** All content changes tracked with revisions
6. ✅ **Public Access:** Anyone can view published pages

### **API Endpoints Summary**

**Public:**
- `GET /api/public/cms/about-us/`
- `GET /api/public/cms/privacy-policy/`
- `GET /api/public/cms/terms-of-service/`
- `GET /api/public/cms/pages/{slug}/`

**Admin (SUPER_ADMIN Only):**
- `GET/POST /api/cms/admin/pages/`
- `GET/PUT/PATCH/DELETE /api/cms/admin/pages/{id}/`
- `POST /api/cms/admin/pages/{id}/publish/`
- `POST /api/cms/admin/pages/{id}/unpublish/`
- `GET /api/cms/admin/pages/{id}/revisions/`
- `POST /api/cms/admin/pages/{id}/restore_revision/`
- `GET/PATCH /api/cms/admin/company-profile/`

---

**Last Updated:** January 6, 2026  
**Version:** 1.0.0  
**Status:** Ready for Production ✅
