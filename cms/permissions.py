"""
CMS Permissions
Role-based permissions for content management.
"""
from rest_framework import permissions


class IsSuperAdminOnly(permissions.BasePermission):
    """
    ONLY SUPER_ADMIN can create, edit, update, or delete content pages.
    This includes About Us, Privacy Policy, Terms of Service, etc.
    """
    
    def has_permission(self, request, view):
        """Check if user is SUPER_ADMIN."""
        # Public can read (GET) published content
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only SUPER_ADMIN can create/update/delete
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'SUPER_ADMIN'
        )
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions."""
        # Public can read published content
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'status'):
                return obj.status == 'published'
            return True
        
        # Only SUPER_ADMIN can edit/delete
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'SUPER_ADMIN'
        )


class CanManageContent(permissions.BasePermission):
    """
    Permission for managing content pages.
    SUPER_ADMIN: Full access (CRUD)
    COMPANY_ADMIN: Can view drafts and make suggestions (future feature)
    Public: Can only view published content
    """
    
    def has_permission(self, request, view):
        """Check permissions based on role."""
        # Public can read
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only SUPER_ADMIN can modify
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'SUPER_ADMIN'
        )
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions."""
        # SUPER_ADMIN has full access
        if request.user and request.user.role == 'SUPER_ADMIN':
            return True
        
        # COMPANY_ADMIN can view all (including drafts) but not modify
        if request.user and request.user.role == 'COMPANY_ADMIN':
            return request.method in permissions.SAFE_METHODS
        
        # Public can only view published content
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'status'):
                return obj.status == 'published'
        
        return False


class CanViewCompanyProfile(permissions.BasePermission):
    """
    Permission for viewing company profile.
    SUPER_ADMIN: Full access (CRUD)
    COMPANY_ADMIN: Read-only access
    Public: No access
    """
    
    def has_permission(self, request, view):
        """Check permissions."""
        # Only authenticated users
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SUPER_ADMIN can do everything
        if request.user.role == 'SUPER_ADMIN':
            return True
        
        # COMPANY_ADMIN can only read
        if request.user.role == 'COMPANY_ADMIN':
            return request.method in permissions.SAFE_METHODS
        
        return False
