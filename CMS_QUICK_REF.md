# CMS & Company Admin - Quick Reference

## 🎯 What Was Implemented

### **3 Major Changes**

1. ✅ **COMPANY_ADMIN Role** - For Alphalogique Technologies staff
2. ✅ **Content Management System** - About Us, Privacy Policy, etc.
3. ✅ **Contact Permissions** - Now SUPER_ADMIN only

---

## 👥 New Role: COMPANY_ADMIN

**Purpose:** Platform owner company (Alphalogique Technologies) staff

### **What COMPANY_ADMIN Can Do:**
- ✅ View company profile (read-only)
- ✅ Submit contact forms
- ✅ View published content pages

### **What COMPANY_ADMIN Cannot Do:**
- ❌ Create/edit/delete content pages (About Us, etc.)
- ❌ Read contact messages
- ❌ Edit company profile
- ❌ Access YEA program data

### **Create COMPANY_ADMIN User:**
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

---

## 📄 Content Management System (CMS)

### **Quick Start**

#### **1. Create About Us Page (SUPER_ADMIN)**
```bash
POST /api/cms/admin/pages/
Authorization: Bearer {SUPER_ADMIN_token}

{
  "page_type": "about_us",
  "title": "About YEA Poultry",
  "slug": "about-us",
  "content": "# About Us\n\nYour content here...",
  "status": "draft"
}
```

#### **2. Publish It**
```bash
POST /api/cms/admin/pages/{page-id}/publish/
Authorization: Bearer {SUPER_ADMIN_token}
```

#### **3. Public Can View**
```bash
GET /api/public/cms/about-us/
# No authentication required!
```

---

## 🔑 Permission Matrix

| Action | SUPER_ADMIN | COMPANY_ADMIN | Public |
|--------|-------------|---------------|--------|
| **Content Pages (About Us, etc.)** |
| Create/Edit/Delete | ✅ | ❌ | ❌ |
| View Published | ✅ | ✅ | ✅ |
| View Drafts | ✅ | ❌ | ❌ |
| **Contact Messages** |
| Read/Reply | ✅ | ❌ | ❌ |
| Submit Form | ✅ | ✅ | ✅ |
| **Company Profile** |
| Edit | ✅ | ❌ | ❌ |
| View | ✅ | ✅ | ❌ |

---

## 🚀 Common Tasks

### **Create About Us Page**
```bash
curl -X POST http://localhost:8000/api/cms/admin/pages/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "page_type": "about_us",
    "title": "About Us",
    "slug": "about-us",
    "content": "# About YEA Poultry\n\nOur mission...",
    "status": "draft",
    "change_summary": "Initial creation"
  }'
```

### **Update Content**
```bash
curl -X PUT http://localhost:8000/api/cms/admin/pages/{id}/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "content": "Updated content...",
    "change_summary": "Updated mission statement"
  }'
# Version auto-increments
```

### **Publish to Public**
```bash
curl -X POST http://localhost:8000/api/cms/admin/pages/{id}/publish/ \
  -H "Authorization: Bearer $TOKEN"
```

### **View Published (Public)**
```bash
curl http://localhost:8000/api/public/cms/about-us/
# No token needed!
```

### **Get Revision History**
```bash
curl http://localhost:8000/api/cms/admin/pages/{id}/revisions/ \
  -H "Authorization: Bearer $TOKEN"
```

### **Restore Previous Version**
```bash
curl -X POST http://localhost:8000/api/cms/admin/pages/{id}/restore_revision/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"revision_id": "uuid-of-revision"}'
```

---

## 📡 API Endpoints Summary

### **Public (No Auth)**
```
GET /api/public/cms/about-us/
GET /api/public/cms/privacy-policy/
GET /api/public/cms/terms-of-service/
GET /api/public/cms/pages/{slug}/
```

### **Admin (SUPER_ADMIN Only)**
```
GET    /api/cms/admin/pages/
POST   /api/cms/admin/pages/
GET    /api/cms/admin/pages/{id}/
PUT    /api/cms/admin/pages/{id}/
PATCH  /api/cms/admin/pages/{id}/
DELETE /api/cms/admin/pages/{id}/

POST   /api/cms/admin/pages/{id}/publish/
POST   /api/cms/admin/pages/{id}/unpublish/
POST   /api/cms/admin/pages/{id}/archive/
GET    /api/cms/admin/pages/{id}/revisions/
POST   /api/cms/admin/pages/{id}/restore_revision/

GET    /api/cms/admin/company-profile/
PATCH  /api/cms/admin/company-profile/
```

---

## 🗂️ Page Types Available

| Value | Display |
|-------|---------|
| `about_us` | About Us |
| `privacy_policy` | Privacy Policy |
| `terms_of_service` | Terms of Service |
| `faq` | Frequently Asked Questions |
| `contact_info` | Contact Information |
| `custom` | Custom Page |

**Note:** Each page type can only exist once (unique constraint)

---

## 📊 Content Status Workflow

```
draft → published → archived
  ↑         ↓
  └─────────┘ (can unpublish back to draft)
```

**Status Values:**
- `draft` - Work in progress, not public
- `published` - Live and visible to public
- `archived` - No longer active, not visible

---

## 🔄 Version Control

Every update creates a new version:

```bash
# v1: Initial creation
POST /api/cms/admin/pages/

# v2: Update content
PUT /api/cms/admin/pages/{id}/

# v3: Another update
PUT /api/cms/admin/pages/{id}/

# Rollback to v2
POST /api/cms/admin/pages/{id}/restore_revision/
{"revision_id": "v2-uuid"}
# Creates v4 with v2's content
```

All revisions stored in `ContentPageRevision` model with:
- Version number
- Full content snapshot
- Who changed it
- When changed
- Change summary

---

## 🧪 Testing Checklist

### **1. SUPER_ADMIN Access**
```bash
# Should work
curl -X POST http://localhost:8000/api/cms/admin/pages/ \
  -H "Authorization: Bearer $SUPER_ADMIN_TOKEN" \
  -d '{"page_type":"about_us",...}'
# Expected: 201 Created
```

### **2. COMPANY_ADMIN Restrictions**
```bash
# Should fail - cannot create content
curl -X POST http://localhost:8000/api/cms/admin/pages/ \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN" \
  -d '{"page_type":"about_us",...}'
# Expected: 403 Forbidden

# Should work - can view company profile
curl http://localhost:8000/api/cms/admin/company-profile/ \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN"
# Expected: 200 OK
```

### **3. Contact Message Restrictions**
```bash
# NATIONAL_ADMIN can no longer access
curl http://localhost:8000/api/admin/contact-messages/ \
  -H "Authorization: Bearer $NATIONAL_ADMIN_TOKEN"
# Expected: 403 Forbidden

# Only SUPER_ADMIN can access
curl http://localhost:8000/api/admin/contact-messages/ \
  -H "Authorization: Bearer $SUPER_ADMIN_TOKEN"
# Expected: 200 OK
```

### **4. Public Access**
```bash
# Anyone can view published pages
curl http://localhost:8000/api/public/cms/about-us/
# Expected: 200 OK (no token needed)

# Draft pages not visible
curl http://localhost:8000/api/public/cms/draft-page/
# Expected: 404 Not Found
```

---

## 🏭 Production Setup

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

>>> # About Us page
>>> ContentPage.objects.create(
...     page_type='about_us',
...     title='About YEA Poultry Management System',
...     slug='about-us',
...     content='# About Us\n\nContent here...',
...     status='published',
...     created_by=admin,
...     updated_by=admin
... )

>>> # Privacy Policy
>>> ContentPage.objects.create(
...     page_type='privacy_policy',
...     title='Privacy Policy',
...     slug='privacy-policy',
...     content='# Privacy Policy\n\nYour privacy...',
...     status='published',
...     created_by=admin,
...     updated_by=admin
... )

>>> # Company Profile
>>> CompanyProfile.objects.create(
...     company_name='Alphalogique Technologies',
...     email='info@alphalogique.com',
...     phone='+233XXXXXXXXX',
...     description='Technology solutions for agriculture',
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

## 📚 Frontend Integration Examples

### **Display About Us (React)**
```jsx
import { useEffect, useState } from 'react';
import axios from 'axios';

function AboutUsPage() {
  const [page, setPage] = useState(null);

  useEffect(() => {
    axios.get('http://localhost:8000/api/public/cms/about-us/')
      .then(res => setPage(res.data));
  }, []);

  if (!page) return <div>Loading...</div>;

  return (
    <div>
      <h1>{page.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: page.content }} />
    </div>
  );
}
```

### **Admin Content Editor**
```jsx
function AdminCMSEditor() {
  const [content, setContent] = useState('');
  const token = localStorage.getItem('access_token');

  const saveContent = () => {
    axios.put(
      'http://localhost:8000/api/cms/admin/pages/{id}/',
      {
        content: content,
        change_summary: 'Updated via admin editor'
      },
      { headers: { Authorization: `Bearer ${token}` } }
    ).then(() => alert('Saved!'));
  };

  return (
    <div>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
      />
      <button onClick={saveContent}>Save</button>
    </div>
  );
}
```

---

## ❓ Troubleshooting

### **Problem:** 403 when creating content
**Solution:** Ensure user is SUPER_ADMIN
```bash
python manage.py shell
>>> from accounts.models import User
>>> user = User.objects.get(email='user@example.com')
>>> user.role = 'SUPER_ADMIN'
>>> user.save()
```

### **Problem:** Page not visible to public
**Solution:** Check page status is 'published'
```bash
python manage.py shell
>>> from cms.models import ContentPage
>>> page = ContentPage.objects.get(slug='about-us')
>>> page.status = 'published'
>>> page.save()
```

### **Problem:** Cannot create two About Us pages
**Solution:** By design! Each page_type is unique. Update existing page instead.

---

## 📝 Database Tables

**Created:**
- `cms_content_page` - Content pages
- `cms_content_page_revision` - Version history
- `cms_company_profile` - Company info

**Indexes:**
- `(status, published_at)` - Fast published page queries
- `(page_type, status)` - Page type filtering
- `(page, version)` - Revision lookups

---

## 🎯 Key Takeaways

1. ✅ **ONLY SUPER_ADMIN** can edit About Us and other content
2. ✅ **Contact messages** now SUPER_ADMIN only
3. ✅ **COMPANY_ADMIN** role for Alphalogique staff (limited permissions)
4. ✅ **Public access** to published content (no auth required)
5. ✅ **Version control** tracks all changes with rollback capability
6. ✅ **Django admin** available at `/admin/cms/`

---

**Git Commit:** d6f9e8b  
**Branch:** development  
**Documentation:** docs/CMS_COMPLETE_GUIDE.md  
**Last Updated:** January 6, 2026  

🚀 **Ready for Production!**
