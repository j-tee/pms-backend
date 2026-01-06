"""
Contact Management Permissions

Role-based permissions for contact message management.
"""
from rest_framework import permissions


class IsAdminOrStaff(permissions.BasePermission):
    """
    Permission for admin/staff users to access contact messages.
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and is admin/staff."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [
                'SUPER_ADMIN', 'NATIONAL_ADMIN', 'YEA_OFFICIAL',
                'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL'
            ]
        )


class CanManageContactMessages(permissions.BasePermission):
    """
    Permission to manage (assign, update, reply) contact messages.
    """
    
    def has_permission(self, request, view):
        """Check if user can manage contact messages."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [
                'SUPER_ADMIN', 'NATIONAL_ADMIN', 'YEA_OFFICIAL'
            ]
        )
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions."""
        # Super admin and national admin can manage all
        if request.user.role in ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'YEA_OFFICIAL']:
            return True
        
        # Regional coordinators can only manage assigned messages
        if request.user.role == 'REGIONAL_COORDINATOR':
            return obj.assigned_to == request.user
        
        return False


class CanReplyToMessages(permissions.BasePermission):
    """
    Permission to reply to contact messages.
    """
    
    def has_permission(self, request, view):
        """Check if user can reply to messages."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [
                'SUPER_ADMIN', 'NATIONAL_ADMIN', 'YEA_OFFICIAL',
                'REGIONAL_COORDINATOR'
            ]
        )
    
    def has_object_permission(self, request, view, obj):
        """Check if user can reply to this specific message."""
        # Super admin and national admin can reply to all
        if request.user.role in ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'YEA_OFFICIAL']:
            return True
        
        # Staff can only reply to assigned messages
        return obj.assigned_to == request.user
