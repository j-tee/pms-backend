"""
Dashboard-specific permissions for role-based access control.
"""

from rest_framework import permissions


class IsExecutive(permissions.BasePermission):
    """
    Permission for executive/national admin dashboard access.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'NATIONAL_ADMIN'
        )


class IsProcurementOfficer(permissions.BasePermission):
    """
    Permission for procurement officer dashboard access.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['PROCUREMENT_OFFICER', 'NATIONAL_ADMIN']
        )


class IsFarmer(permissions.BasePermission):
    """
    Permission for farmer dashboard access.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'FARMER'
        )


class IsConstituencyOfficial(permissions.BasePermission):
    """
    Permission for constituency official dashboard access.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'CONSTITUENCY_OFFICIAL'
        )


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission for Super Admin access (highest privilege level).
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'SUPER_ADMIN'
        )


class IsYEAAdmin(permissions.BasePermission):
    """
    Permission for any YEA admin role (Super Admin or National Admin).
    Used for analytics and institutional subscription management.
    """
    def has_permission(self, request, view):
        admin_roles = ['SUPER_ADMIN', 'NATIONAL_ADMIN']
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in admin_roles
        )
