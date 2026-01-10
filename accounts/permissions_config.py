"""
Permissions Configuration

Defines all system permissions organized by category.
These permissions provide fine-grained access control within each role level.

Usage:
    - Admins at each level can grant/revoke permissions to staff at their level
    - NATIONAL_ADMIN manages NATIONAL_STAFF permissions
    - REGIONAL_ADMIN manages REGIONAL_STAFF permissions
    - CONSTITUENCY_ADMIN manages CONSTITUENCY_STAFF and field officer permissions
"""

# Permission Categories
PERMISSION_CATEGORIES = {
    'user_management': 'User Management',
    'farm_management': 'Farm Management',
    'batch_management': 'Batch/Program Management',
    'application_review': 'Application Review',
    'analytics': 'Analytics & Reporting',
    'financial': 'Financial Management',
    'marketplace': 'Marketplace Management',
    'content': 'Content Management',
    'system': 'System Administration',
}

# All system permissions
# Format: (codename, name, description, category, applicable_roles)
SYSTEM_PERMISSIONS = [
    # ========================================
    # USER MANAGEMENT
    # ========================================
    (
        'view_users',
        'View Users',
        'Can view user list and profiles within jurisdiction',
        'user_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'create_users',
        'Create Users',
        'Can create new user accounts within jurisdiction',
        'user_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    (
        'edit_users',
        'Edit Users',
        'Can edit user profiles within jurisdiction',
        'user_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'suspend_users',
        'Suspend Users',
        'Can suspend user accounts within jurisdiction',
        'user_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    (
        'manage_staff_invitations',
        'Manage Staff Invitations',
        'Can send and manage staff invitations',
        'user_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    
    # ========================================
    # FARM MANAGEMENT
    # ========================================
    (
        'view_farms',
        'View Farms',
        'Can view farm details within jurisdiction',
        'farm_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'edit_farms',
        'Edit Farms',
        'Can edit farm information within jurisdiction',
        'farm_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'verify_farms',
        'Verify Farms',
        'Can verify farm registration details',
        'farm_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'assign_extension_officers',
        'Assign Extension Officers',
        'Can assign extension officers to farms',
        'farm_management',
        ['REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    
    # ========================================
    # BATCH/PROGRAM MANAGEMENT
    # ========================================
    (
        'view_batches',
        'View Batches',
        'Can view batch/program details',
        'batch_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'create_batches',
        'Create Batches',
        'Can create new batches/programs',
        'batch_management',
        ['NATIONAL_STAFF']
    ),
    (
        'edit_batches',
        'Edit Batches',
        'Can edit batch/program details',
        'batch_management',
        ['NATIONAL_STAFF']
    ),
    (
        'publish_batches',
        'Publish Batches',
        'Can publish batches to make them visible to farmers',
        'batch_management',
        ['NATIONAL_STAFF']
    ),
    (
        'manage_batch_enrollment',
        'Manage Batch Enrollment',
        'Can manage farmer enrollment in batches',
        'batch_management',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    
    # ========================================
    # APPLICATION REVIEW
    # ========================================
    (
        'view_applications',
        'View Applications',
        'Can view farm and enrollment applications',
        'application_review',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'review_applications',
        'Review Applications',
        'Can review and add notes to applications',
        'application_review',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'approve_applications',
        'Approve Applications',
        'Can approve farm and enrollment applications',
        'application_review',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    (
        'reject_applications',
        'Reject Applications',
        'Can reject farm and enrollment applications',
        'application_review',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    
    # ========================================
    # ANALYTICS & REPORTING
    # ========================================
    (
        'view_basic_analytics',
        'View Basic Analytics',
        'Can view basic dashboard statistics',
        'analytics',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'view_detailed_analytics',
        'View Detailed Analytics',
        'Can view detailed analytics and trends',
        'analytics',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    (
        'view_national_analytics',
        'View National Analytics',
        'Can view nation-wide analytics (not scoped to region)',
        'analytics',
        ['NATIONAL_STAFF']
    ),
    (
        'export_reports',
        'Export Reports',
        'Can export data reports to CSV/Excel',
        'analytics',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    (
        'view_audit_logs',
        'View Audit Logs',
        'Can view system audit logs',
        'analytics',
        ['NATIONAL_STAFF']
    ),
    
    # ========================================
    # FINANCIAL MANAGEMENT
    # ========================================
    (
        'view_financial_data',
        'View Financial Data',
        'Can view financial reports and transaction data',
        'financial',
        ['NATIONAL_STAFF']
    ),
    (
        'manage_subscriptions',
        'Manage Subscriptions',
        'Can manage marketplace subscriptions',
        'financial',
        ['NATIONAL_STAFF']
    ),
    (
        'view_payment_records',
        'View Payment Records',
        'Can view payment and subscription records',
        'financial',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    
    # ========================================
    # MARKETPLACE MANAGEMENT
    # ========================================
    (
        'view_marketplace_listings',
        'View Marketplace Listings',
        'Can view all marketplace listings',
        'marketplace',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    ),
    (
        'moderate_listings',
        'Moderate Listings',
        'Can moderate (approve/reject) marketplace listings',
        'marketplace',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    (
        'manage_marketplace_settings',
        'Manage Marketplace Settings',
        'Can manage marketplace configuration',
        'marketplace',
        ['NATIONAL_STAFF']
    ),
    
    # ========================================
    # CONTENT MANAGEMENT
    # ========================================
    (
        'manage_cms_content',
        'Manage CMS Content',
        'Can create and edit CMS pages and content',
        'content',
        ['NATIONAL_STAFF']
    ),
    (
        'manage_contact_messages',
        'Manage Contact Messages',
        'Can view and respond to contact form messages',
        'content',
        ['NATIONAL_STAFF', 'REGIONAL_STAFF']
    ),
    
    # ========================================
    # SYSTEM ADMINISTRATION
    # ========================================
    (
        'view_system_health',
        'View System Health',
        'Can view system health and status',
        'system',
        ['NATIONAL_STAFF']
    ),
    (
        'manage_cache',
        'Manage Cache',
        'Can refresh system caches',
        'system',
        ['NATIONAL_STAFF']
    ),
]

# Permissions that are automatically granted to admin roles (cannot be revoked)
ADMIN_IMPLICIT_PERMISSIONS = {
    'SUPER_ADMIN': '__all__',  # All permissions
    'NATIONAL_ADMIN': [
        'view_users', 'create_users', 'edit_users', 'suspend_users', 'manage_staff_invitations',
        'view_farms', 'edit_farms', 'verify_farms',
        'view_batches', 'create_batches', 'edit_batches', 'publish_batches', 'manage_batch_enrollment',
        'view_applications', 'review_applications', 'approve_applications', 'reject_applications',
        'view_basic_analytics', 'view_detailed_analytics', 'view_national_analytics', 'export_reports', 'view_audit_logs',
        'view_financial_data', 'manage_subscriptions', 'view_payment_records',
        'view_marketplace_listings', 'moderate_listings', 'manage_marketplace_settings',
        'manage_cms_content', 'manage_contact_messages',
        'view_system_health', 'manage_cache',
    ],
    'REGIONAL_ADMIN': [
        'view_users', 'create_users', 'edit_users', 'suspend_users', 'manage_staff_invitations',
        'view_farms', 'edit_farms', 'verify_farms', 'assign_extension_officers',
        'view_batches', 'manage_batch_enrollment',
        'view_applications', 'review_applications', 'approve_applications', 'reject_applications',
        'view_basic_analytics', 'view_detailed_analytics', 'export_reports',
        'view_payment_records',
        'view_marketplace_listings', 'moderate_listings',
        'manage_contact_messages',
    ],
    'CONSTITUENCY_ADMIN': [
        'view_users', 'edit_users',
        'view_farms', 'edit_farms', 'verify_farms', 'assign_extension_officers',
        'view_batches',
        'view_applications', 'review_applications',
        'view_basic_analytics',
        'view_marketplace_listings',
    ],
}

# Default permissions for staff roles (can be modified by their admin)
DEFAULT_STAFF_PERMISSIONS = {
    'NATIONAL_STAFF': [
        'view_users', 'view_farms', 'view_batches', 'view_applications',
        'view_basic_analytics', 'view_marketplace_listings',
    ],
    'REGIONAL_STAFF': [
        'view_users', 'view_farms', 'view_batches', 'view_applications',
        'view_basic_analytics', 'view_marketplace_listings',
    ],
    'CONSTITUENCY_STAFF': [
        'view_farms', 'view_applications', 'view_basic_analytics',
    ],
}

# Which admin can manage which staff roles
PERMISSION_MANAGEMENT_HIERARCHY = {
    'SUPER_ADMIN': ['NATIONAL_ADMIN', 'NATIONAL_STAFF', 'REGIONAL_ADMIN', 'REGIONAL_STAFF', 
                    'CONSTITUENCY_ADMIN', 'CONSTITUENCY_STAFF', 'EXTENSION_OFFICER', 
                    'VETERINARY_OFFICER', 'YEA_OFFICIAL'],
    'NATIONAL_ADMIN': ['NATIONAL_STAFF', 'REGIONAL_ADMIN', 'REGIONAL_STAFF', 'REGIONAL_COORDINATOR'],  # Added legacy alias
    'REGIONAL_ADMIN': ['REGIONAL_STAFF', 'CONSTITUENCY_ADMIN', 'CONSTITUENCY_STAFF'],
    'REGIONAL_COORDINATOR': ['REGIONAL_STAFF', 'CONSTITUENCY_ADMIN', 'CONSTITUENCY_STAFF'],  # Legacy alias for REGIONAL_ADMIN
    'CONSTITUENCY_ADMIN': ['CONSTITUENCY_STAFF', 'EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL'],
    'CONSTITUENCY_OFFICIAL': ['CONSTITUENCY_STAFF', 'EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL'],  # Legacy alias for CONSTITUENCY_ADMIN
}

# Permissions that each admin level can grant to their staff
GRANTABLE_PERMISSIONS = {
    'NATIONAL_ADMIN': [
        # Can grant any permission to NATIONAL_STAFF
        'view_users', 'create_users', 'edit_users', 'suspend_users', 'manage_staff_invitations',
        'view_farms', 'edit_farms', 'verify_farms',
        'view_batches', 'create_batches', 'edit_batches', 'publish_batches', 'manage_batch_enrollment',
        'view_applications', 'review_applications', 'approve_applications', 'reject_applications',
        'view_basic_analytics', 'view_detailed_analytics', 'view_national_analytics', 'export_reports',
        'view_financial_data', 'view_payment_records',
        'view_marketplace_listings', 'moderate_listings',
        'manage_cms_content', 'manage_contact_messages',
    ],
    'REGIONAL_ADMIN': [
        'view_users', 'create_users', 'edit_users',
        'view_farms', 'edit_farms', 'verify_farms', 'assign_extension_officers',
        'view_batches', 'manage_batch_enrollment',
        'view_applications', 'review_applications', 'approve_applications', 'reject_applications',
        'view_basic_analytics', 'view_detailed_analytics', 'export_reports',
    ],
    'REGIONAL_COORDINATOR': [  # Legacy alias - same as REGIONAL_ADMIN
        'view_users', 'create_users', 'edit_users',
        'view_farms', 'edit_farms', 'verify_farms', 'assign_extension_officers',
        'view_batches', 'manage_batch_enrollment',
        'view_applications', 'review_applications', 'approve_applications', 'reject_applications',
        'view_basic_analytics', 'view_detailed_analytics', 'export_reports',
        'view_marketplace_listings', 'moderate_listings',
    ],
    'CONSTITUENCY_ADMIN': [
        'view_users', 'view_farms', 'edit_farms', 'verify_farms', 'assign_extension_officers',
        'view_batches', 'view_applications', 'review_applications',
        'view_basic_analytics', 'view_marketplace_listings',
    ],
    'CONSTITUENCY_OFFICIAL': [  # Legacy alias - same as CONSTITUENCY_ADMIN
        'view_users', 'view_farms', 'edit_farms', 'verify_farms', 'assign_extension_officers',
        'view_batches', 'view_applications', 'review_applications',
        'view_basic_analytics', 'view_marketplace_listings',
    ],
}


def get_permission_by_codename(codename):
    """Get permission definition by codename."""
    for perm in SYSTEM_PERMISSIONS:
        if perm[0] == codename:
            return {
                'codename': perm[0],
                'name': perm[1],
                'description': perm[2],
                'category': perm[3],
                'applicable_roles': perm[4],
            }
    return None


def get_permissions_by_category(category):
    """Get all permissions in a category."""
    return [
        {
            'codename': perm[0],
            'name': perm[1],
            'description': perm[2],
            'applicable_roles': perm[4],
        }
        for perm in SYSTEM_PERMISSIONS
        if perm[3] == category
    ]


def get_all_permission_codenames():
    """Get list of all permission codenames."""
    return [perm[0] for perm in SYSTEM_PERMISSIONS]


def can_admin_manage_role(admin_role, target_role):
    """Check if admin role can manage permissions for target role."""
    manageable = PERMISSION_MANAGEMENT_HIERARCHY.get(admin_role, [])
    return target_role in manageable


def can_admin_grant_permission(admin_role, permission_codename):
    """Check if admin role can grant a specific permission."""
    if admin_role == 'SUPER_ADMIN':
        return True
    grantable = GRANTABLE_PERMISSIONS.get(admin_role, [])
    return permission_codename in grantable


def get_implicit_permissions(role):
    """Get permissions implicitly granted to a role (admin roles)."""
    implicit = ADMIN_IMPLICIT_PERMISSIONS.get(role)
    if implicit == '__all__':
        return get_all_permission_codenames()
    return implicit or []


def get_default_permissions(role):
    """Get default permissions for a staff role."""
    return DEFAULT_STAFF_PERMISSIONS.get(role, [])


def get_permissions_as_dict():
    """
    Convert SYSTEM_PERMISSIONS list to dict format.
    
    Returns:
        dict: {codename: {name, description, category, applicable_roles}}
    """
    return {
        perm[0]: {
            'name': perm[1],
            'description': perm[2],
            'category': perm[3],
            'applicable_roles': perm[4] if len(perm) > 4 else []
        }
        for perm in SYSTEM_PERMISSIONS
    }
