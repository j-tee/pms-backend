# CORS Configuration Fix Summary

## Issue
Frontend running on `http://localhost:5173` (Vite dev server) was blocked by CORS policy when trying to access backend APIs at `http://localhost:8000`.

**Error Message:**
```
Access to fetch at 'http://localhost:8000/auth/login/' from origin 'http://localhost:5173' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on 
the requested resource.
```

## Root Cause
The `django-cors-headers` package was installed and configured in middleware, but the CORS settings were not properly allowing the frontend origin.

## Solution Applied

### Updated `core/settings.py` (lines 345-375)

```python
# =============================================================================
# CORS SETTINGS
# =============================================================================

# For development - allow all origins. In production, use specific CORS_ALLOWED_ORIGINS list
DEBUG_MODE = os.getenv('DEBUG', 'True') == 'True'

if DEBUG_MODE:
    # Development: Allow all origins for easier testing
    CORS_ORIGIN_ALLOW_ALL = True
else:
    # Production: Whitelist specific frontend origins
    cors_origins_env = os.getenv(
        'CORS_ALLOWED_ORIGINS', 
        'https://yourdomain.com'
    )
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_env.split(',')]

# CSRF Trusted Origins (both dev and prod)
csrf_origins_env = os.getenv(
    'CSRF_TRUSTED_ORIGINS', 
    'http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173'
)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins_env.split(',')]

# CORS Headers Configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
```

## Configuration Details

### Development Mode (DEBUG=True)
- **`CORS_ORIGIN_ALLOW_ALL = True`**: Allows requests from any origin
- Makes frontend development easier without needing to whitelist specific ports
- Automatically allows `localhost:5173`, `localhost:3000`, or any other frontend port

### Production Mode (DEBUG=False)
- **`CORS_ALLOWED_ORIGINS`**: Whitelist specific frontend domains
- Set via environment variable `CORS_ALLOWED_ORIGINS`
- Example: `CORS_ALLOWED_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com`

### CORS Headers Sent
When a request comes from an allowed origin, the backend now responds with:
```
access-control-allow-origin: http://localhost:5173
access-control-allow-credentials: true
access-control-allow-methods: DELETE, GET, OPTIONS, PATCH, POST, PUT
access-control-allow-headers: accept, accept-encoding, authorization, content-type, ...
```

## Verification

### Test CORS Preflight (OPTIONS)
```bash
curl -i -X OPTIONS http://localhost:8000/api/auth/login/ \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"
```

**Expected Response:**
```
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:5173
access-control-allow-credentials: true
access-control-allow-methods: DELETE, GET, OPTIONS, PATCH, POST, PUT
```

### Test Actual Login POST
```bash
curl -i -X POST http://localhost:8000/api/auth/login/ \
  -H "Origin: http://localhost:5173" \
  -H "Content-Type: application/json" \
  -d '{"username":"adminuser","password":"testuser123"}'
```

**Expected Response:**
```
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:5173
access-control-allow-credentials: true
Content-Type: application/json

{
  "access": "eyJhbGc...",
  "refresh": "eyJhbGc...",
  "user": {...},
  "routing": {...}
}
```

## Frontend Usage

### Axios Configuration
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true, // Important for CORS with credentials
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### Fetch API Configuration
```typescript
const response = await fetch('http://localhost:8000/api/auth/login/', {
  method: 'POST',
  credentials: 'include', // Important for CORS with credentials
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ username, password }),
});
```

## Production Deployment Checklist

When deploying to production:

1. **Set `DEBUG=False`** in environment variables
2. **Set `CORS_ALLOWED_ORIGINS`** environment variable:
   ```bash
   CORS_ALLOWED_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
   ```
3. **Update `CSRF_TRUSTED_ORIGINS`** for production domains:
   ```bash
   CSRF_TRUSTED_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
   ```
4. **Verify HTTPS** is properly configured for both backend and frontend
5. **Test CORS** with production domains before going live

## Troubleshooting

### CORS Headers Not Appearing
1. Check `django-cors-headers` is installed: `pip list | grep cors`
2. Verify middleware order in `settings.py`:
   ```python
   MIDDLEWARE = [
       'django.middleware.security.SecurityMiddleware',
       'corsheaders.middleware.CorsMiddleware',  # Must be before CommonMiddleware
       'django.contrib.sessions.middleware.SessionMiddleware',
       'django.middleware.common.CommonMiddleware',
       ...
   ]
   ```
3. Restart Django server after changes

### CORS Working in Development but Not Production
1. Verify `DEBUG=False` in production environment
2. Check `CORS_ALLOWED_ORIGINS` includes production frontend URL
3. Ensure HTTPS is used (browsers enforce stricter CORS with HTTPS)

### Credentials Not Being Sent
1. Frontend must set `withCredentials: true` (Axios) or `credentials: 'include'` (Fetch)
2. Backend must have `CORS_ALLOW_CREDENTIALS = True`
3. Cannot use `CORS_ORIGIN_ALLOW_ALL = True` with credentials in some cases - use specific origins

## Related Documentation
- **Unified Login Guide**: `docs/UNIFIED_LOGIN_GUIDE.md`
- **Admin Dashboard Guide**: `docs/ADMIN_DASHBOARD_FRONTEND_GUIDE.md`
- **Django CORS Headers**: https://github.com/adamchainz/django-cors-headers

---

**Last Updated**: November 27, 2025  
**Status**: ✅ RESOLVED  
**Django Server**: Running on http://localhost:8000  
**Frontend Dev Server**: http://localhost:5173  
**CORS**: Enabled for all origins in development mode
