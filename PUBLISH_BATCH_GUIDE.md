# Quick Guide: Publishing Batches in Production

**Date:** December 16, 2025  
**Issue:** Public batch API returning 0 records despite batch existing in database  
**Root Cause:** Batch has `is_published=false`, causing it to be filtered out

---

## Understanding the Status Fields

### **`is_active`** - Operational Status
- Controls whether batch is operationally active or paused
- Used for temporary pauses (maintenance, review, etc.)

### **`is_published`** - Public Visibility
- Controls whether batch is visible to farmers/public
- Used for draft management and launch control

### **Both Fields Required for Public Visibility**
For a batch to appear in public API (`/api/public/batches/`), **both** must be `true`:
- `is_active=true` ✅
- `is_published=true` ✅

---

## Immediate Fix: Publish YEA-0001 Batch

Run this on the production server:

```bash
cd /var/www/YEA/PMS/pms-backend
source venv/bin/activate

# Publish the batch
python manage.py shell -c "
from farms.batch_enrollment_models import Batch
batch = Batch.objects.get(batch_code='YEA-0001')
print(f'Before: is_active={batch.is_active}, is_published={batch.is_published}')
batch.is_published = True
batch.is_active = True  # Ensure both are true
batch.save()
print(f'After: is_active={batch.is_active}, is_published={batch.is_published}')
print('✅ Batch YEA-0001 is now published and active!')
"
```

---

## Verify the Fix

Test the public API:

```bash
# From production server
curl -s "http://localhost:8000/api/public/batches/?is_active=true&is_published=true" | python -m json.tool

# From your machine (replace with actual domain)
curl -s "https://pms.alphalogictech.com/api/public/batches/?is_active=true&is_published=true" | jq .
```

**Expected Result:**
```json
{
  "count": 1,
  "results": [
    {
      "id": "...",
      "batch_name": "YEA Poultry Program 2025 - Cohort 1",
      "batch_code": "YEA-0001",
      "is_active": true,
      "is_published": true,
      ...
    }
  ]
}
```

---

## New Feature: Toggle Publish Endpoint

After deploying the latest code, admins can use the new endpoint:

```bash
# Publish a batch
curl -X POST "https://pms.alphalogictech.com/api/admin/batches/{batch_id}/toggle-publish/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_published": true,
    "reason": "Launching batch to public"
  }'

# Unpublish a batch
curl -X POST "https://pms.alphalogictech.com/api/admin/batches/{batch_id}/toggle-publish/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_published": false,
    "reason": "Temporarily unpublishing for edits"
  }'
```

---

## Workflow Examples

### **1. Creating a New Batch (Draft)**
```json
POST /api/admin/batches/
{
  "batch_name": "New Cohort 2026",
  "is_active": false,
  "is_published": false,
  ...
}
```
→ Result: Draft batch, not visible to public

### **2. Ready to Launch**
```json
PATCH /api/admin/batches/{batch_id}/
{
  "is_active": true,
  "is_published": true
}
```
→ Result: Batch visible and accepting applications

### **3. Temporary Pause (Still Visible)**
```json
POST /api/admin/batches/{batch_id}/toggle-active/
{
  "is_active": false,
  "reason": "Pausing for review"
}
```
→ Result: Batch visible but not accepting applications (`is_published` still true)

### **4. Hide from Public**
```json
POST /api/admin/batches/{batch_id}/toggle-publish/
{
  "is_published": false,
  "reason": "Making major edits"
}
```
→ Result: Batch hidden from public immediately

### **5. Permanently Close**
```json
PATCH /api/admin/batches/{batch_id}/
{
  "is_active": false,
  "is_published": false
}
```
→ Result: Batch completely hidden and inactive

---

## Troubleshooting

### Batch Not Appearing in Public API

**Check status:**
```bash
python manage.py shell -c "
from farms.batch_enrollment_models import Batch
batch = Batch.objects.get(batch_code='YOUR-BATCH-CODE')
print(f'active: {batch.is_active}')
print(f'published: {batch.is_published}')
print(f'archived: {batch.archived}')
"
```

**Common issues:**
- ❌ `is_published=false` → Batch filtered out (most common)
- ❌ `is_active=false` → Batch filtered out
- ❌ `archived=true` → Batch soft-deleted
- ❌ Query uses wrong filters → Check query parameters

**Fix:**
```bash
python manage.py shell -c "
from farms.batch_enrollment_models import Batch
batch = Batch.objects.get(batch_code='YOUR-BATCH-CODE')
batch.is_published = True
batch.is_active = True
batch.save()
"
```

---

## Deployment Steps

1. **Deploy latest code** (contains new toggle-publish endpoint):
   ```bash
   cd /var/www/YEA/PMS/pms-backend
   git pull origin main
   source venv/bin/activate
   python manage.py migrate  # If needed
   sudo systemctl restart pms-backend
   ```

2. **Publish YEA-0001 batch** (run the shell command above)

3. **Verify API** returns data

4. **Test new endpoint** with frontend team

---

## Key Takeaways

✅ **Both fields serve different purposes** - don't eliminate either one  
✅ **Public visibility requires BOTH** `is_active=true` AND `is_published=true`  
✅ **Draft workflow enabled** by `is_published` field  
✅ **Temporary pauses possible** by toggling `is_active` while keeping `is_published=true`  
✅ **New toggle-publish endpoint** provides better admin control  

---

**Updated:** December 16, 2025  
**Version:** 1.1  
**See:** `docs/BATCH_API_DOCUMENTATION.md` for complete API reference
