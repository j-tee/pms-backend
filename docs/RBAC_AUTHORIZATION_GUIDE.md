# Role-Based Access Control & Authorization Guide
## YEA Poultry Management System

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Purpose:** Comprehensive guide to roles, permissions, and authorization policies

---

## Table of Contents

1. [Overview](#overview)
2. [Role Hierarchy](#role-hierarchy)
3. [Permission System](#permission-system)
4. [Authorization Policies](#authorization-policies)
5. [Implementation Guide](#implementation-guide)
6. [Permission Matrix](#permission-matrix)
7. [Resource-Level Permissions](#resource-level-permissions)
8. [API Examples](#api-examples)

---

## Overview

### RBAC Architecture

The system implements a **fine-grained Role-Based Access Control (RBAC)** system inspired by CanCanCan, featuring:

- **10 Primary Roles** with hierarchical inheritance
- **100+ Granular Permissions** across 12 categories
- **Resource-level authorization** (object-specific permissions)
- **Conditional permissions** based on context
- **Permission inheritance** through role hierarchy
- **Temporal roles** with expiration support

### Core Concepts

```
User → UserRole → Role → RolePermission → Permission
             ↓
         Resource (Optional: Farm, Application, etc.)
```

**Key Features:**
- Users can have **multiple roles** simultaneously
- Roles can be **global** or **resource-scoped**
- Permissions can have **conditions** (ownership, status, location)
- Support for **temporary role assignments** with expiration

---

## Role Hierarchy

### 1. Primary Roles

#### **SUPER_ADMIN**
**Level:** System Administrator  
**Scope:** Entire platform  
**Count:** 2-3 users

**Responsibilities:**
- Full system access
- User management (create/delete/modify all users)
- System configuration
- Role and permission management
- Audit log access
- Emergency overrides

**Special Powers:**
- Can impersonate any user
- Can override any permission check
- Can access all data without restrictions
- Can delete records (with audit trail)

---

#### **NATIONAL_ADMIN** (Executive Dashboard)
**Level:** National Leadership  
**Scope:** All regions and constituencies  
**Count:** 5-10 users

**Responsibilities:**
- National-level application approvals
- Policy configuration
- System-wide reporting and analytics
- Program management
- Budget oversight
- Performance monitoring

**Permissions:**
- Approve/reject applications (final tier)
- Create government programs
- View all farms nationwide
- Generate national reports
- Configure platform settings
- Manage regional/constituency officers
- Override lower-tier decisions

**Restrictions:**
- Cannot delete system data
- Cannot modify audit logs
- Cannot access farmer financial details (unless investigating fraud)

---

#### **REGIONAL_COORDINATOR**
**Level:** Regional Management  
**Scope:** Specific region (e.g., Greater Accra Region)  
**Count:** 16 users (one per region)

**Responsibilities:**
- Regional application approvals (tier 2)
- Oversee constituency officials
- Regional reporting and analytics
- Resource allocation coordination
- Training coordination
- Quality assurance

**Permissions:**
- Approve/reject applications (regional tier)
- View all farms in assigned region
- Generate regional reports
- Manage constituency officials in region
- Schedule regional programs
- Escalate issues to national level

**Restrictions:**
- Cannot access other regions' data
- Cannot approve final tier (national approval required)
- Cannot modify national policies

---

#### **CONSTITUENCY_OFFICIAL**
**Level:** Local Government Officer  
**Scope:** Specific constituency (e.g., Tema East)  
**Count:** 275+ users (one per constituency)

**Responsibilities:**
- First-tier application review
- Local farm monitoring
- Extension officer supervision
- Community engagement
- Local reporting

**Permissions:**
- Review and approve applications (constituency tier)
- View farms in assigned constituency
- Assign extension officers
- Generate constituency reports
- Schedule local site visits
- Verify GPS locations
- Validate applicant information

**Restrictions:**
- Cannot approve beyond constituency tier
- Cannot access other constituencies' data
- Cannot modify approved applications
- Cannot delete records

---

#### **EXTENSION_OFFICER**
**Level:** Field Officer  
**Scope:** Assigned farmers (10-20 farms)  
**Count:** 500+ users

**Responsibilities:**
- Direct farmer support
- Site visits and inspections
- Training delivery
- Data collection and verification
- Issue reporting
- Best practices guidance

**Permissions:**
- View assigned farmers' profiles
- Record site visit notes
- Update farm inspection records
- Submit training completion reports
- Flag issues for constituency review
- Submit supply distribution records
- Comment on farmer performance

**Restrictions:**
- Cannot approve applications
- Cannot access unassigned farms
- Cannot modify farm financial data
- Cannot approve program enrollments
- Read-only access to production data

---

#### **VETERINARY_OFFICER**
**Level:** Animal Health Specialist  
**Scope:** Regional or constituency-based  
**Count:** 100+ users

**Responsibilities:**
- Disease investigation and diagnosis
- Mortality record verification
- Vaccination program oversight
- Health advisory services
- Quarantine enforcement
- Compensation claim verification

**Permissions:**
- View all farms in jurisdiction (for disease tracking)
- Inspect mortality records
- Verify compensation claims
- Prescribe treatments
- Order quarantine measures
- Generate health reports
- Access vaccination records
- Submit lab test results

**Restrictions:**
- Cannot approve applications
- Cannot modify production data
- Cannot access financial transactions
- Cannot approve compensation payments

---

#### **PROCUREMENT_OFFICER**
**Level:** Supply Chain Manager  
**Scope:** National or regional  
**Count:** 20-30 users

**Responsibilities:**
- Feed and medication procurement
- Supplier management
- Day-old chick sourcing
- Distribution logistics
- Inventory management
- Quality control

**Permissions:**
- Create purchase orders
- Manage supplier database
- Allocate supplies to farms
- Track distribution
- Generate procurement reports
- Verify delivery confirmations
- Manage inventory levels

**Restrictions:**
- Cannot approve farmer applications
- Cannot access farmer sales data
- Cannot modify farm production records
- Cannot access farmer payouts

---

#### **AUDITOR**
**Level:** Compliance & Fraud Investigation  
**Scope:** System-wide (investigation-triggered)  
**Count:** 5-10 users

**Responsibilities:**
- Fraud investigation
- Financial audits
- Data integrity verification
- Compliance monitoring
- Investigation reports
- Policy violation enforcement

**Permissions:**
- View all data (read-only, case-specific)
- Access fraud alerts
- Review payout histories
- Compare production vs. sales
- Generate audit reports
- Request document uploads
- Flag suspicious activities
- Recommend sanctions

**Restrictions:**
- Cannot modify any records
- Cannot approve applications
- Cannot process payments
- Cannot delete data
- Access requires case assignment

---

#### **FINANCE_OFFICER**
**Level:** Payment & Settlement Manager  
**Scope:** National  
**Count:** 10-15 users

**Responsibilities:**
- Review payout requests
- Settlement processing
- Subscription payment tracking
- Refund processing
- Financial reporting
- Commission reconciliation

**Permissions:**
- View farmer payout requests
- Process settlements
- Verify payment details
- Generate financial reports
- Handle refund requests
- Manage subscription billing
- Reconcile platform commissions
- Access Paystack dashboard

**Restrictions:**
- Cannot modify production data
- Cannot approve applications
- Cannot access farmer production details
- Cannot override commission rates without approval

---

#### **FARMER**
**Level:** System End User  
**Scope:** Own farm only  
**Count:** Unlimited

**Responsibilities:**
- Farm operations management
- Daily production recording
- Inventory tracking
- Sales management
- Customer relationships
- Marketplace participation (if subscribed)

**Permissions:**
- View own farm profile
- Record daily production
- Manage flocks
- Track feed inventory
- Record medications
- Manage customers
- Create sales (if marketplace enabled)
- View own financial data
- Update farm profile (limited fields)
- Upload product images (if subscribed)

**Restrictions:**
- Cannot view other farms' data
- Cannot modify application status
- Cannot access officer dashboards
- Cannot delete historical records
- Cannot modify commission rates
- Marketplace features require subscription

---

### 2. Specialized Sub-Roles

#### **MARKETPLACE_SUBSCRIBER**
**Type:** Feature flag  
**Duration:** Monthly subscription  
**Applied to:** Farmers with active subscription

**Additional Permissions:**
- Create product listings
- Manage public farm profile
- Upload up to 20 product images
- Access marketplace analytics
- Receive customer inquiries
- Process online orders

---

#### **GOVERNMENT_BENEFICIARY**
**Type:** Program participant  
**Duration:** Program duration  
**Applied to:** Government program farmers

**Additional Permissions:**
- Access government-subsidized marketplace (if program includes)
- View extension officer assignments
- Access training materials
- View supply distribution schedule
- Submit progress reports

---

#### **PROGRAM_COORDINATOR**
**Type:** Temporary role  
**Duration:** Per program  
**Applied to:** Officers managing specific programs

**Additional Permissions:**
- Manage specific program enrollments
- Track program participant progress
- Distribute program benefits
- Generate program-specific reports
- Evaluate program outcomes

---

## Permission System

### Permission Categories

#### 1. **Application Management** (20 permissions)

```python
PERM_VIEW_APPLICATION = "view_application"
PERM_VIEW_ALL_APPLICATIONS = "view_all_applications"
PERM_VIEW_CONSTITUENCY_APPLICATIONS = "view_constituency_applications"
PERM_VIEW_REGIONAL_APPLICATIONS = "view_regional_applications"

PERM_REVIEW_APPLICATION = "review_application"
PERM_APPROVE_APPLICATION_CONSTITUENCY = "approve_application_constituency"
PERM_APPROVE_APPLICATION_REGIONAL = "approve_application_regional"
PERM_APPROVE_APPLICATION_NATIONAL = "approve_application_national"

PERM_REJECT_APPLICATION = "reject_application"
PERM_REQUEST_CHANGES = "request_application_changes"
PERM_REASSIGN_APPLICATION = "reassign_application"

PERM_CLAIM_APPLICATION = "claim_application_from_queue"
PERM_PRIORITIZE_APPLICATION = "set_application_priority"
PERM_ESCALATE_APPLICATION = "escalate_application"

PERM_VERIFY_GHANA_CARD = "verify_ghana_card"
PERM_VERIFY_GPS_LOCATION = "verify_gps_location"
PERM_VERIFY_TIN = "verify_tin"

PERM_CREATE_FARM_FROM_APPLICATION = "create_farm_from_application"
PERM_SEND_APPLICATION_INVITATION = "send_farm_invitation"
PERM_CANCEL_APPLICATION = "cancel_application"
```

---

#### 2. **Farm Management** (25 permissions)

```python
# View permissions
PERM_VIEW_OWN_FARM = "view_own_farm"
PERM_VIEW_ANY_FARM = "view_any_farm"
PERM_VIEW_CONSTITUENCY_FARMS = "view_constituency_farms"
PERM_VIEW_REGIONAL_FARMS = "view_regional_farms"
PERM_VIEW_ASSIGNED_FARMS = "view_assigned_farms"

# Edit permissions
PERM_EDIT_OWN_FARM_PROFILE = "edit_own_farm_profile"
PERM_EDIT_FARM_STATUS = "edit_farm_status"
PERM_SUSPEND_FARM = "suspend_farm"
PERM_ACTIVATE_FARM = "activate_farm"
PERM_DELETE_FARM = "delete_farm"

# Farm operations
PERM_ASSIGN_EXTENSION_OFFICER = "assign_extension_officer"
PERM_REMOVE_EXTENSION_OFFICER = "remove_extension_officer"
PERM_UPDATE_FARM_LOCATION = "update_farm_location"
PERM_VERIFY_FARM_INFRASTRUCTURE = "verify_farm_infrastructure"

# Farm monitoring
PERM_VIEW_FARM_ANALYTICS = "view_farm_analytics"
PERM_VIEW_FARM_AUDIT_LOG = "view_farm_audit_log"
PERM_GENERATE_FARM_REPORT = "generate_farm_report"

# Farm financial
PERM_VIEW_FARM_FINANCIAL_DATA = "view_farm_financial_data"
PERM_VIEW_FARM_DEBT_INFO = "view_farm_debt_info"
PERM_VIEW_FARM_INVESTMENT = "view_farm_investment"

# Marketplace
PERM_ENABLE_MARKETPLACE = "enable_farm_marketplace"
PERM_DISABLE_MARKETPLACE = "disable_farm_marketplace"
PERM_VIEW_MARKETPLACE_ANALYTICS = "view_marketplace_analytics"
PERM_MANAGE_PRODUCT_LISTINGS = "manage_product_listings"
PERM_UPLOAD_PRODUCT_IMAGES = "upload_product_images"
```

---

#### 3. **Production Management** (18 permissions)

```python
# Flock management
PERM_CREATE_FLOCK = "create_flock"
PERM_VIEW_OWN_FLOCKS = "view_own_flocks"
PERM_VIEW_ANY_FLOCK = "view_any_flock"
PERM_EDIT_FLOCK = "edit_flock"
PERM_DELETE_FLOCK = "delete_flock"
PERM_TRANSFER_FLOCK = "transfer_flock"

# Daily production
PERM_RECORD_DAILY_PRODUCTION = "record_daily_production"
PERM_VIEW_DAILY_PRODUCTION = "view_daily_production"
PERM_EDIT_DAILY_PRODUCTION = "edit_daily_production"
PERM_DELETE_DAILY_PRODUCTION = "delete_daily_production"

# Production analytics
PERM_VIEW_PRODUCTION_TRENDS = "view_production_trends"
PERM_GENERATE_PRODUCTION_REPORT = "generate_production_report"
PERM_COMPARE_PRODUCTION_BENCHMARKS = "compare_production_benchmarks"

# Mortality
PERM_RECORD_MORTALITY = "record_mortality"
PERM_VIEW_MORTALITY_RECORDS = "view_mortality_records"
PERM_INVESTIGATE_MORTALITY = "investigate_mortality"
PERM_VERIFY_MORTALITY_CLAIM = "verify_mortality_claim"
PERM_APPROVE_COMPENSATION = "approve_mortality_compensation"
```

---

#### 4. **Sales & Revenue** (22 permissions)

```python
# Customer management
PERM_CREATE_CUSTOMER = "create_customer"
PERM_VIEW_OWN_CUSTOMERS = "view_own_customers"
PERM_EDIT_CUSTOMER = "edit_customer"
PERM_DELETE_CUSTOMER = "delete_customer"

# Sales recording
PERM_CREATE_EGG_SALE = "create_egg_sale"
PERM_CREATE_BIRD_SALE = "create_bird_sale"
PERM_VIEW_OWN_SALES = "view_own_sales"
PERM_VIEW_ANY_SALES = "view_any_sales"
PERM_EDIT_SALE = "edit_sale"
PERM_DELETE_SALE = "delete_sale"
PERM_REFUND_SALE = "refund_sale"

# Payment processing
PERM_INITIATE_PAYMENT = "initiate_payment"
PERM_VERIFY_PAYMENT = "verify_payment"
PERM_PROCESS_PAYOUT = "process_farmer_payout"
PERM_VIEW_PAYOUT_HISTORY = "view_payout_history"
PERM_RETRY_FAILED_PAYOUT = "retry_failed_payout"

# Financial oversight
PERM_VIEW_PLATFORM_REVENUE = "view_platform_revenue"
PERM_VIEW_COMMISSION_REPORT = "view_commission_report"
PERM_ADJUST_COMMISSION_RATE = "adjust_commission_rate"

# Fraud detection
PERM_VIEW_FRAUD_ALERTS = "view_fraud_alerts"
PERM_INVESTIGATE_FRAUD = "investigate_fraud"
PERM_MARK_FRAUD_RESOLVED = "mark_fraud_resolved"
```

---

#### 5. **Inventory Management** (15 permissions)

```python
# Feed inventory
PERM_VIEW_OWN_FEED_INVENTORY = "view_own_feed_inventory"
PERM_VIEW_ANY_FEED_INVENTORY = "view_any_feed_inventory"
PERM_RECORD_FEED_PURCHASE = "record_feed_purchase"
PERM_RECORD_FEED_CONSUMPTION = "record_feed_consumption"
PERM_UPDATE_FEED_INVENTORY = "update_feed_inventory"

# Medication inventory
PERM_VIEW_OWN_MEDICATION_INVENTORY = "view_own_medication_inventory"
PERM_RECORD_MEDICATION_PURCHASE = "record_medication_purchase"
PERM_RECORD_MEDICATION_USE = "record_medication_use"
PERM_UPDATE_MEDICATION_INVENTORY = "update_medication_inventory"

# Procurement
PERM_CREATE_PURCHASE_ORDER = "create_purchase_order"
PERM_APPROVE_PURCHASE_ORDER = "approve_purchase_order"
PERM_RECEIVE_SUPPLIES = "receive_supplies"
PERM_DISTRIBUTE_SUPPLIES = "distribute_supplies"

# Inventory oversight
PERM_VIEW_LOW_STOCK_ALERTS = "view_low_stock_alerts"
PERM_GENERATE_INVENTORY_REPORT = "generate_inventory_report"
```

---

#### 6. **Health & Medication** (16 permissions)

```python
# Health monitoring
PERM_RECORD_HEALTH_OBSERVATION = "record_health_observation"
PERM_VIEW_HEALTH_RECORDS = "view_health_records"
PERM_FLAG_DISEASE_OUTBREAK = "flag_disease_outbreak"

# Vaccination
PERM_CREATE_VACCINATION_SCHEDULE = "create_vaccination_schedule"
PERM_RECORD_VACCINATION = "record_vaccination"
PERM_VIEW_VACCINATION_RECORDS = "view_vaccination_records"
PERM_VERIFY_VACCINATION = "verify_vaccination"

# Medication
PERM_PRESCRIBE_MEDICATION = "prescribe_medication"
PERM_RECORD_MEDICATION_ADMINISTRATION = "record_medication"
PERM_VIEW_MEDICATION_RECORDS = "view_medication_records"

# Veterinary services
PERM_SCHEDULE_VET_VISIT = "schedule_vet_visit"
PERM_RECORD_VET_VISIT = "record_vet_visit"
PERM_REQUEST_LAB_TEST = "request_lab_test"
PERM_SUBMIT_LAB_RESULTS = "submit_lab_results"

# Quarantine
PERM_IMPOSE_QUARANTINE = "impose_quarantine"
PERM_LIFT_QUARANTINE = "lift_quarantine"
```

---

#### 7. **Program Management** (14 permissions)

```python
# Program administration
PERM_CREATE_GOVERNMENT_PROGRAM = "create_government_program"
PERM_EDIT_GOVERNMENT_PROGRAM = "edit_government_program"
PERM_ACTIVATE_PROGRAM = "activate_program"
PERM_DEACTIVATE_PROGRAM = "deactivate_program"
PERM_VIEW_ALL_PROGRAMS = "view_all_programs"

# Enrollment
PERM_APPLY_TO_PROGRAM = "apply_to_program"
PERM_VIEW_PROGRAM_APPLICATIONS = "view_program_applications"
PERM_REVIEW_PROGRAM_APPLICATION = "review_program_application"
PERM_APPROVE_PROGRAM_ENROLLMENT = "approve_program_enrollment"
PERM_REJECT_PROGRAM_APPLICATION = "reject_program_application"

# Program monitoring
PERM_VIEW_PROGRAM_PARTICIPANTS = "view_program_participants"
PERM_TRACK_PROGRAM_BENEFITS = "track_program_benefits"
PERM_GENERATE_PROGRAM_REPORT = "generate_program_report"
PERM_EVALUATE_PROGRAM_OUTCOMES = "evaluate_program_outcomes"
```

---

#### 8. **Subscription Management** (12 permissions)

```python
# Subscription actions
PERM_SUBSCRIBE_TO_MARKETPLACE = "subscribe_to_marketplace"
PERM_CANCEL_SUBSCRIPTION = "cancel_subscription"
PERM_VIEW_OWN_SUBSCRIPTION = "view_own_subscription"
PERM_VIEW_ANY_SUBSCRIPTION = "view_any_subscription"

# Subscription admin
PERM_CREATE_SUBSCRIPTION_PLAN = "create_subscription_plan"
PERM_EDIT_SUBSCRIPTION_PLAN = "edit_subscription_plan"
PERM_SUSPEND_SUBSCRIPTION = "suspend_subscription"
PERM_RESUME_SUBSCRIPTION = "resume_subscription"

# Billing
PERM_VIEW_SUBSCRIPTION_INVOICES = "view_subscription_invoices"
PERM_PROCESS_SUBSCRIPTION_PAYMENT = "process_subscription_payment"
PERM_ISSUE_SUBSCRIPTION_REFUND = "issue_subscription_refund"
PERM_EXTEND_TRIAL_PERIOD = "extend_trial_period"
```

---

#### 9. **User Management** (18 permissions)

```python
# User administration
PERM_CREATE_USER = "create_user"
PERM_VIEW_USER = "view_user"
PERM_EDIT_USER = "edit_user"
PERM_DELETE_USER = "delete_user"
PERM_SUSPEND_USER = "suspend_user"
PERM_ACTIVATE_USER = "activate_user"

# Role management
PERM_ASSIGN_ROLE = "assign_role"
PERM_REMOVE_ROLE = "remove_role"
PERM_VIEW_USER_ROLES = "view_user_roles"

# Account security
PERM_RESET_USER_PASSWORD = "reset_user_password"
PERM_UNLOCK_USER_ACCOUNT = "unlock_user_account"
PERM_REQUIRE_PASSWORD_CHANGE = "require_password_change"
PERM_VIEW_LOGIN_HISTORY = "view_login_history"

# Advanced
PERM_IMPERSONATE_USER = "impersonate_user"
PERM_VIEW_USER_PERMISSIONS = "view_user_permissions"
PERM_GRANT_PERMISSION = "grant_permission"
PERM_REVOKE_PERMISSION = "revoke_permission"
PERM_MANAGE_MFA_SETTINGS = "manage_mfa_settings"
```

---

#### 10. **Reporting & Analytics** (16 permissions)

```python
# Dashboard access
PERM_VIEW_EXECUTIVE_DASHBOARD = "view_executive_dashboard"
PERM_VIEW_PROCUREMENT_DASHBOARD = "view_procurement_dashboard"
PERM_VIEW_CONSTITUENCY_DASHBOARD = "view_constituency_dashboard"
PERM_VIEW_EXTENSION_OFFICER_DASHBOARD = "view_extension_officer_dashboard"

# Report generation
PERM_GENERATE_NATIONAL_REPORT = "generate_national_report"
PERM_GENERATE_REGIONAL_REPORT = "generate_regional_report"
PERM_GENERATE_CONSTITUENCY_REPORT = "generate_constituency_report"
PERM_GENERATE_FARM_PERFORMANCE_REPORT = "generate_farm_performance_report"

# Analytics
PERM_VIEW_PLATFORM_STATISTICS = "view_platform_statistics"
PERM_VIEW_FINANCIAL_ANALYTICS = "view_financial_analytics"
PERM_VIEW_PRODUCTION_ANALYTICS = "view_production_analytics"
PERM_EXPORT_DATA = "export_data"

# Custom reports
PERM_CREATE_CUSTOM_REPORT = "create_custom_report"
PERM_SCHEDULE_REPORT = "schedule_report"
PERM_SHARE_REPORT = "share_report"
PERM_DOWNLOAD_REPORT = "download_report"
```

---

#### 11. **System Configuration** (10 permissions)

```python
PERM_VIEW_SYSTEM_SETTINGS = "view_system_settings"
PERM_EDIT_SYSTEM_SETTINGS = "edit_system_settings"
PERM_MANAGE_CONSTITUENCIES = "manage_constituencies"
PERM_MANAGE_REGIONS = "manage_regions"
PERM_CONFIGURE_NOTIFICATIONS = "configure_notifications"
PERM_MANAGE_EMAIL_TEMPLATES = "manage_email_templates"
PERM_MANAGE_SMS_TEMPLATES = "manage_sms_templates"
PERM_CONFIGURE_COMMISSION_RATES = "configure_commission_rates"
PERM_MANAGE_FEED_TYPES = "manage_feed_types"
PERM_MANAGE_MEDICATION_TYPES = "manage_medication_types"
```

---

#### 12. **Audit & Compliance** (8 permissions)

```python
PERM_VIEW_AUDIT_LOG = "view_audit_log"
PERM_VIEW_SYSTEM_LOG = "view_system_log"
PERM_EXPORT_AUDIT_LOG = "export_audit_log"
PERM_INITIATE_AUDIT = "initiate_audit"
PERM_COMPLETE_AUDIT = "complete_audit"
PERM_VIEW_COMPLIANCE_REPORTS = "view_compliance_reports"
PERM_FLAG_POLICY_VIOLATION = "flag_policy_violation"
PERM_RESOLVE_VIOLATION = "resolve_policy_violation"
```

---

## Authorization Policies

### Policy Definition Structure

```python
class Policy:
    """
    Defines authorization rules similar to CanCanCan abilities.
    """
    
    def can(self, user, action, resource):
        """
        Check if user can perform action on resource.
        
        Args:
            user: User instance
            action: Permission codename (e.g., 'edit_farm')
            resource: Resource instance or class
        
        Returns:
            Boolean indicating if action is allowed
        """
        pass
    
    def scope(self, user, resource_class):
        """
        Return QuerySet of resources user can access.
        
        Args:
            user: User instance
            resource_class: Model class
        
        Returns:
            Filtered QuerySet
        """
        pass
```

### Example Policy Implementations

#### Farm Access Policy

```python
from django.db.models import Q

class FarmPolicy:
    """Authorization policy for Farm model."""
    
    @staticmethod
    def can_view(user, farm):
        """Check if user can view specific farm."""
        
        # Super admin: can view all
        if user.has_role('SUPER_ADMIN'):
            return True
        
        # National admin: can view all
        if user.has_role('NATIONAL_ADMIN'):
            return True
        
        # Auditor: can view if assigned to investigation
        if user.has_role('AUDITOR'):
            return farm.fraud_alerts.filter(
                reviewed_by=user,
                status='under_review'
            ).exists()
        
        # Regional coordinator: can view farms in region
        if user.has_role('REGIONAL_COORDINATOR'):
            return farm.primary_constituency in user.get_managed_constituencies()
        
        # Constituency official: can view farms in constituency
        if user.has_role('CONSTITUENCY_OFFICIAL'):
            return farm.primary_constituency == user.constituency
        
        # Extension officer: can view assigned farms only
        if user.has_role('EXTENSION_OFFICER'):
            return farm.extension_officer == user or farm.assigned_extension_officer == user
        
        # Veterinary officer: can view farms in jurisdiction
        if user.has_role('VETERINARY_OFFICER'):
            return farm.primary_constituency in user.get_jurisdiction_constituencies()
        
        # Farmer: can view own farm only
        if user.has_role('FARMER'):
            return farm.owner == user
        
        return False
    
    @staticmethod
    def can_edit(user, farm):
        """Check if user can edit specific farm."""
        
        # Super admin: can edit all
        if user.has_role('SUPER_ADMIN'):
            return True
        
        # National admin: can edit specific fields
        if user.has_role('NATIONAL_ADMIN'):
            return True
        
        # Farmer: can edit own farm (limited fields)
        if user.has_role('FARMER') and farm.owner == user:
            return True
        
        return False
    
    @staticmethod
    def editable_fields(user, farm):
        """Return list of fields user can edit."""
        
        if user.has_role('SUPER_ADMIN') or user.has_role('NATIONAL_ADMIN'):
            return '__all__'  # All fields
        
        if user.has_role('FARMER') and farm.owner == user:
            # Farmers can only edit specific fields
            return [
                'farm_name',
                'alternate_phone',
                'email',
                'preferred_contact_method',
                'current_bird_count',
                'monthly_operating_budget',
                'expected_monthly_revenue'
            ]
        
        return []  # No editable fields
    
    @staticmethod
    def scope(user):
        """Return QuerySet of farms user can access."""
        from farms.models import Farm
        
        if user.has_role('SUPER_ADMIN') or user.has_role('NATIONAL_ADMIN'):
            return Farm.objects.all()
        
        if user.has_role('REGIONAL_COORDINATOR'):
            constituencies = user.get_managed_constituencies()
            return Farm.objects.filter(primary_constituency__in=constituencies)
        
        if user.has_role('CONSTITUENCY_OFFICIAL'):
            return Farm.objects.filter(primary_constituency=user.constituency)
        
        if user.has_role('EXTENSION_OFFICER'):
            return Farm.objects.filter(
                Q(extension_officer=user) | Q(assigned_extension_officer=user)
            )
        
        if user.has_role('FARMER'):
            return Farm.objects.filter(owner=user)
        
        return Farm.objects.none()
```

---

#### Application Review Policy

```python
class ApplicationPolicy:
    """Authorization policy for FarmApplication model."""
    
    @staticmethod
    def can_approve(user, application):
        """Check if user can approve application at current stage."""
        
        # Must match review level with user role
        if application.current_review_level == 'constituency':
            if not user.has_role('CONSTITUENCY_OFFICIAL'):
                return False
            # Must be in same constituency
            return application.primary_constituency == user.constituency
        
        elif application.current_review_level == 'regional':
            if not user.has_role('REGIONAL_COORDINATOR'):
                return False
            # Must manage the region containing the constituency
            return application.primary_constituency in user.get_managed_constituencies()
        
        elif application.current_review_level == 'national':
            return user.has_role('NATIONAL_ADMIN')
        
        return False
    
    @staticmethod
    def can_claim(user, application):
        """Check if user can claim application from queue."""
        
        # Check if already claimed
        if application.queue_entries.filter(status__in=['claimed', 'in_progress']).exists():
            return False
        
        # Check user role matches review level
        return ApplicationPolicy.can_approve(user, application)
```

---

#### Sales & Payment Policy

```python
class SalesPolicy:
    """Authorization policy for sales and payments."""
    
    @staticmethod
    def can_create_sale(user, farm):
        """Check if user can create sale for farm."""
        
        # Must be farm owner
        if farm.owner != user:
            return False
        
        # Must have marketplace enabled
        if not farm.marketplace_enabled:
            return False
        
        # Check subscription status
        if farm.subscription_type == 'none':
            return False
        
        # Check if subscription is active (not past_due or suspended)
        if hasattr(farm, 'subscription'):
            if farm.subscription.status not in ['trial', 'active']:
                return False
        
        return True
    
    @staticmethod
    def can_view_payout(user, payout):
        """Check if user can view payout details."""
        
        # Farm owner can view own payouts
        if payout.farm.owner == user:
            return True
        
        # Finance officers can view all payouts
        if user.has_role('FINANCE_OFFICER'):
            return True
        
        # Auditors can view if investigating
        if user.has_role('AUDITOR'):
            return payout.farm.fraud_alerts.filter(
                reviewed_by=user,
                status='under_review'
            ).exists()
        
        return False
```

---

## Permission Matrix

### Complete Role-Permission Mapping

| Permission Category | SUPER_ADMIN | NATIONAL_ADMIN | REGIONAL_COORD | CONSTITUENCY_OFF | EXTENSION_OFF | VET_OFF | PROCUREMENT_OFF | AUDITOR | FINANCE_OFF | FARMER |
|---------------------|-------------|----------------|----------------|------------------|---------------|---------|-----------------|---------|-------------|--------|
| **Application Management** |
| View all applications | ✓ | ✓ | Regional | Constituency | ✗ | ✗ | ✗ | Case-based | ✗ | Own only |
| Approve (Tier 1) | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Approve (Tier 2) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Approve (Tier 3) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Farm Management** |
| View any farm | ✓ | ✓ | Regional | Constituency | Assigned | Jurisdiction | ✗ | Case-based | ✗ | Own only |
| Edit farm profile | ✓ | ✓ | Limited | Limited | ✗ | ✗ | ✗ | ✗ | ✗ | Limited |
| Suspend farm | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Assign extension officer | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Production** |
| Record production | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| View production | ✓ | ✓ | Regional | Constituency | Assigned | Assigned | ✗ | Case-based | ✗ | Own only |
| Edit production | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | Limited |
| **Sales & Revenue** |
| Create sale | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ (if subscribed) |
| View any sales | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | Case-based | ✓ | Own only |
| Process payout | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| View fraud alerts | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ |
| **Inventory** |
| Record purchase | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ |
| Distribute supplies | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| View inventory | ✓ | ✓ | Regional | Constituency | Assigned | ✗ | ✓ | Case-based | ✗ | Own only |
| **Health & Medication** |
| Prescribe medication | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Impose quarantine | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Verify mortality | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Approve compensation | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| **Programs** |
| Create program | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Apply to program | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Approve enrollment | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **User Management** |
| Create user | ✓ | ✓ | Limited | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Assign role | ✓ | ✓ | Limited | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Suspend user | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Impersonate | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Reporting** |
| National reports | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Regional reports | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Constituency reports | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Export data | ✓ | ✓ | Regional | Constituency | ✗ | ✗ | ✓ | ✓ | ✓ | Own only |
| **System Config** |
| Edit system settings | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Manage constituencies | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Configure commission | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Audit** |
| View audit log | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Initiate audit | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |

**Legend:**
- ✓ = Full permission
- ✗ = No permission
- Limited = Restricted subset
- Regional = Within assigned region
- Constituency = Within assigned constituency
- Assigned = Only assigned resources
- Case-based = Only when assigned to specific case/investigation
- Own only = Only user's own resources

---

## Implementation Guide

### 1. Backend Setup (Django)

#### Install the authorization system

```bash
# Already implemented in accounts/roles.py
# Run migrations
python manage.py makemigrations
python manage.py migrate
```

#### Create permissions seeder

```python
# accounts/management/commands/seed_permissions.py
from django.core.management.base import BaseCommand
from accounts.roles import Permission

class Command(BaseCommand):
    help = 'Seed permissions into the database'
    
    def handle(self, *args, **kwargs):
        permissions = [
            # Application Management
            ('view_application', 'View Application', 'application_management'),
            ('approve_application_constituency', 'Approve Application (Tier 1)', 'application_management'),
            # ... add all 194 permissions
        ]
        
        for codename, name, category in permissions:
            Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': name,
                    'category': category,
                    'is_system_permission': True
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Permissions seeded successfully'))
```

---

### 2. Create Authorization Decorator

```python
# accounts/decorators.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status

def authorize(permission_codename, resource_getter=None):
    """
    Decorator to check permissions before executing view.
    
    Usage:
        @authorize('edit_farm', resource_getter=lambda request, pk: Farm.objects.get(pk=pk))
        def update_farm(request, pk):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get resource if getter provided
            resource = None
            if resource_getter:
                try:
                    resource = resource_getter(request, *args, **kwargs)
                except Exception as e:
                    return Response(
                        {'error': 'Resource not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Check permission
            if not user.has_permission(permission_codename):
                return Response(
                    {'error': 'You do not have permission to perform this action'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Additional resource-level check using policies
            if resource:
                policy_class = get_policy_for_resource(resource)
                if policy_class:
                    action = permission_codename.split('_', 1)[0]  # 'edit' from 'edit_farm'
                    if not policy_class.can(user, action, resource):
                        return Response(
                            {'error': 'You do not have permission to access this resource'},
                            status=status.HTTP_403_FORBIDDEN
                        )
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator
```

---

### 3. Policy Classes

```python
# accounts/policies/__init__.py
from .farm_policy import FarmPolicy
from .application_policy import ApplicationPolicy
from .sales_policy import SalesPolicy

POLICY_REGISTRY = {
    'Farm': FarmPolicy,
    'FarmApplication': ApplicationPolicy,
    'EggSale': SalesPolicy,
    'BirdSale': SalesPolicy,
}

def get_policy_for_resource(resource):
    """Get policy class for resource."""
    resource_type = resource.__class__.__name__
    return POLICY_REGISTRY.get(resource_type)
```

---

### 4. API View Examples

```python
# farms/views.py
from rest_framework.decorators import api_view
from accounts.decorators import authorize
from farms.models import Farm

@api_view(['GET'])
@authorize('view_farm', resource_getter=lambda request, pk: Farm.objects.get(pk=pk))
def get_farm(request, pk):
    """Get farm details."""
    farm = Farm.objects.get(pk=pk)
    serializer = FarmSerializer(farm)
    return Response(serializer.data)

@api_view(['PUT'])
@authorize('edit_farm', resource_getter=lambda request, pk: Farm.objects.get(pk=pk))
def update_farm(request, pk):
    """Update farm details."""
    farm = Farm.objects.get(pk=pk)
    
    # Get editable fields based on user role
    from accounts.policies import FarmPolicy
    editable_fields = FarmPolicy.editable_fields(request.user, farm)
    
    if editable_fields != '__all__':
        # Filter data to only include editable fields
        data = {k: v for k, v in request.data.items() if k in editable_fields}
    else:
        data = request.data
    
    serializer = FarmSerializer(farm, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

---

### 5. Scoped Queries

```python
# farms/views.py
from accounts.policies import FarmPolicy

@api_view(['GET'])
def list_farms(request):
    """List all farms user has access to."""
    # Get scoped queryset based on user's permissions
    farms = FarmPolicy.scope(request.user)
    
    # Apply additional filters
    if 'status' in request.query_params:
        farms = farms.filter(farm_status=request.query_params['status'])
    
    serializer = FarmSerializer(farms, many=True)
    return Response(serializer.data)
```

---

### 6. Frontend Integration

#### Check permissions in React/TypeScript

```typescript
// hooks/usePermission.ts
import { useAuth } from './useAuth';

export const usePermission = () => {
  const { user } = useAuth();
  
  const can = (permission: string, resource?: any): boolean => {
    // Check if user has permission
    if (!user || !user.permissions) return false;
    return user.permissions.includes(permission);
  };
  
  const canAny = (permissions: string[]): boolean => {
    return permissions.some(perm => can(perm));
  };
  
  const canAll = (permissions: string[]): boolean => {
    return permissions.every(perm => can(perm));
  };
  
  return { can, canAny, canAll };
};

// Usage in component
const FarmEditButton = ({ farm }) => {
  const { can } = usePermission();
  
  if (!can('edit_farm', farm)) {
    return null; // Don't show button
  }
  
  return <button onClick={handleEdit}>Edit Farm</button>;
};
```

---

## API Examples

### 1. Assign Role to User

```http
POST /api/users/{user_id}/roles/
Authorization: Bearer {token}

{
  "role_name": "EXTENSION_OFFICER",
  "resource_type": "farm",  // Optional: for resource-scoped role
  "resource_id": "farm-uuid",
  "expires_at": "2026-12-31T23:59:59Z"  // Optional: for temporary role
}
```

**Response:**
```json
{
  "success": true,
  "user_role": {
    "id": "user-role-uuid",
    "user": "user-uuid",
    "role": {
      "name": "EXTENSION_OFFICER",
      "resource": {
        "type": "farm",
        "id": "farm-uuid",
        "name": "Asante Poultry Farm"
      }
    },
    "assigned_by": "admin-user-uuid",
    "assigned_at": "2025-11-26T10:00:00Z",
    "expires_at": "2026-12-31T23:59:59Z"
  }
}
```

---

### 2. Check User Permissions

```http
GET /api/users/me/permissions/
Authorization: Bearer {token}
```

**Response:**
```json
{
  "roles": [
    {
      "name": "EXTENSION_OFFICER",
      "is_global": true,
      "assigned_at": "2025-01-15T10:00:00Z"
    }
  ],
  "permissions": [
    "view_assigned_farms",
    "record_site_visit",
    "submit_training_report",
    "view_health_records",
    "flag_issues"
  ],
  "resource_permissions": {
    "farm-uuid-1": ["view", "comment"],
    "farm-uuid-2": ["view", "comment"]
  }
}
```

---

### 3. Check Specific Permission

```http
POST /api/auth/can/
Authorization: Bearer {token}

{
  "permission": "edit_farm",
  "resource_type": "farm",
  "resource_id": "farm-uuid"
}
```

**Response:**
```json
{
  "allowed": true,
  "reason": "User is farm owner",
  "editable_fields": [
    "farm_name",
    "alternate_phone",
    "email",
    "current_bird_count"
  ]
}
```

---

**End of RBAC Authorization Guide**

This comprehensive authorization system provides:
- ✓ 10 primary roles with clear responsibilities
- ✓ 194 granular permissions across 12 categories
- ✓ Resource-level authorization (object-specific)
- ✓ Conditional permissions based on context
- ✓ Policy classes for complex authorization logic
- ✓ Complete API integration examples
- ✓ Frontend permission checking patterns

**Next Steps:**
1. Implement policy classes for each model
2. Create permission seeder script
3. Add authorization decorators to all API endpoints
4. Build role management UI for admins
5. Create permission testing suite
