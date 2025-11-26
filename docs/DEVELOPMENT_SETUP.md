# Development Setup Guide - YEA Poultry Management System

## Current Status: Setting Up Authentication & Authorization

**Date**: October 26, 2025  
**Phase**: User Authentication (US-1.1, US-1.2, US-1.3)  
**Next**: Farm Registration (after authentication is complete)

---

## ✅ Completed Steps

### 1. Environment Configuration
- ✅ Created `.env.development` with PostgreSQL credentials
- ✅ Created `.env.production` template
- ✅ Created `.gitignore` to protect sensitive data
- ✅ Updated `settings.py` to use environment variables

### 2. Database Setup
**PostgreSQL Configuration**:
```
DB_NAME: poultry_db
DB_USER: teejay
DB_PASSWORD: &&Roju11TET
DB_HOST: localhost
DB_PORT: 5432
```

### 3. Django Configuration
- ✅ Configured Django REST Framework
- ✅ Configured JWT Authentication (SimpleJWT)
- ✅ Added CORS headers for frontend integration
- ✅ Set timezone to `Africa/Accra` (Ghana)
- ✅ Configured media and static file handling

### 4. Dependencies Installed
```
Django 5.2.7
djangorestframework 3.14.0
djangorestframework-simplejwt 5.3.0
django-cors-headers 4.3.1
django-filter 23.5
psycopg2-binary 2.9.9
python-dotenv 1.0.0
Pillow 10.4.0
celery 5.3.4
redis 5.0.1
+ testing & code quality tools
```

---

## 📋 Next Steps

### Step 1: Create PostgreSQL Database
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database
CREATE DATABASE poultry_db;

# Grant privileges to user teejay
GRANT ALL PRIVILEGES ON DATABASE poultry_db TO teejay;

# Enable PostGIS extension (for GPS/geospatial data)
\c poultry_db
CREATE EXTENSION postgis;

# Exit
\q
```

### Step 2: Create Accounts App (Authentication)
```bash
python manage.py startapp accounts
```

**Accounts app will handle**:
- User registration (farmers, officials, procurement officers)
- User authentication (login, logout, token refresh)
- Role-based access control (permissions)
- Password reset functionality
- User profile management

### Step 3: Create Custom User Model
**Why custom user?**
- Add role field (Farmer, Constituency Official, National Admin, etc.)
- Add constituency/region assignment for officials
- Add profile fields (phone, preferred contact method)
- Flexible for future requirements

**User Roles**:
1. Farmer
2. Constituency Official
3. National Administrator
4. Procurement Officer
5. Veterinary Officer
6. Auditor

### Step 4: Implement Authentication Endpoints
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - Login (get JWT tokens)
- `POST /api/auth/logout/` - Logout (blacklist token)
- `POST /api/auth/refresh/` - Refresh access token
- `POST /api/auth/password-reset/` - Request password reset
- `POST /api/auth/password-reset-confirm/` - Confirm password reset
- `GET /api/auth/me/` - Get current user profile
- `PUT /api/auth/me/` - Update current user profile

### Step 5: Database Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Create Superuser
```bash
python manage.py createsuperuser
```

### Step 7: Test Authentication
- Test user registration
- Test login (get tokens)
- Test protected endpoints with token
- Test token refresh
- Test password reset flow

---

## 🏗️ Architecture Decisions

### Why Start with Authentication?
1. **Foundation**: Every other feature requires authenticated users
2. **Security**: Establish secure patterns from the beginning
3. **Role-Based Access**: Farm registration needs role verification
4. **User Context**: All operations are tied to specific users

### Why JWT over Session Auth?
1. **Stateless**: Better for REST APIs
2. **Scalability**: No server-side session storage needed
3. **Mobile-Friendly**: Works well with PWA/mobile apps
4. **Cross-Domain**: Easier for separate frontend/backend

### Why PostgreSQL over SQLite?
1. **Production-Ready**: SQLite not suitable for production
2. **PostGIS**: Need geospatial capabilities for GPS data
3. **Concurrency**: Better handling of multiple users
4. **Data Integrity**: Better constraints and transactions

---

## 📁 Current Project Structure

```
pms-backend/
├── .env.development          # ✅ Development environment vars
├── .env.production           # ✅ Production environment template
├── .gitignore                # ✅ Protect sensitive files
├── requirements.txt          # ✅ Python dependencies
├── README.md                 # ✅ Project overview
├── manage.py                 # Django management
├── db.sqlite3                # Old SQLite (will remove after PostgreSQL)
├── core/                     # Django project settings
│   ├── __init__.py
│   ├── settings.py           # ✅ Updated with env vars & PostgreSQL
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── docs/                     # ✅ All documentation
│   ├── REQUIREMENTS_DISCUSSION.md
│   ├── USER_STORIES.md
│   ├── FARM_REGISTRATION_MODEL.md
│   └── ALIGNMENT_CHECK.md
└── venv/                     # Virtual environment
```

**After authentication setup**:
```
pms-backend/
├── accounts/                 # ⏭️ Authentication app (next)
│   ├── models.py            # Custom User model with roles
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # API endpoints
│   ├── permissions.py       # Custom permissions
│   ├── urls.py              # URL routing
│   └── tests/               # Unit tests
└── farms/                    # ⏭️ Farm management app (after auth)
    ├── models.py            # Farm, Location, Infrastructure models
    ├── serializers.py
    ├── views.py
    └── tests/
```

---

## 🔐 Security Considerations

### Environment Variables
- ✅ Never commit `.env` files to Git
- ✅ Different configs for development and production
- ✅ Strong SECRET_KEY in production
- ✅ Strong database passwords

### Authentication
- ✅ JWT with short-lived access tokens (60 min)
- ✅ Longer-lived refresh tokens (7 days)
- ✅ Token blacklisting on logout
- ✅ Password hashing (Django default: PBKDF2)
- ✅ Rate limiting on login endpoint (future)

### API Security
- ✅ CORS configured for allowed origins only
- ✅ CSRF protection enabled
- ✅ HTTPS enforced in production
- ✅ Secure cookies in production

---

## 📊 Development Workflow

### Current Sprint: Authentication (Week 1)
- [ ] Create PostgreSQL database
- [ ] Create accounts app
- [ ] Implement custom User model with roles
- [ ] Create registration serializer & endpoint
- [ ] Create login endpoint (JWT)
- [ ] Create logout endpoint (blacklist token)
- [ ] Create token refresh endpoint
- [ ] Create password reset flow
- [ ] Create user profile endpoints
- [ ] Write unit tests (80% coverage target)
- [ ] Test manually with Postman/curl

### Next Sprint: Farm Registration (Week 2)
- [ ] Create farms app
- [ ] Implement Farm model (based on FARM_REGISTRATION_MODEL.md)
- [ ] Implement Location model (GPS address string + coordinates)
- [ ] Implement Infrastructure models
- [ ] Create farm registration API endpoints
- [ ] Implement multi-step form support
- [ ] Add photo upload functionality
- [ ] Add GPS address string parser
- [ ] Create farm approval workflow
- [ ] Write unit tests

---

## 🧪 Testing Strategy

### Unit Tests (pytest)
- Model tests (validation, methods)
- Serializer tests (validation, data transformation)
- View tests (endpoint behavior, permissions)
- Permission tests (role-based access)

### API Tests
- Registration flow (success, validation errors)
- Login flow (success, invalid credentials)
- Token refresh (success, expired token)
- Protected endpoints (with/without auth)

### Integration Tests
- Complete user journey (register → login → access resource)
- Role-based access (farmer can't access admin endpoints)

---

## 📝 Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Start with Authentication | Foundation for all other features | Oct 26, 2025 |
| Use PostgreSQL from start | Avoid migration headaches later | Oct 26, 2025 |
| JWT Authentication | Stateless, mobile-friendly | Oct 26, 2025 |
| Environment variables for config | Security best practice | Oct 26, 2025 |
| Custom User model | Flexibility for roles and profiles | Oct 26, 2025 |

---

## 🤝 Development Team Notes

**Before starting farm registration**:
1. Authentication MUST be complete and tested
2. All user roles defined and tested
3. Permission system working correctly
4. Token management tested

**Why this order matters**:
- Farm registration requires authenticated users
- Farm approval requires role-based permissions
- Reports and dashboards require user context
- Procurement requires user authentication

---

**Last Updated**: October 26, 2025  
**Next Review**: After authentication implementation complete
