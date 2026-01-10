"""
Contact Management Permissions

Role-based permissions for contact message management.
"""
from rest_framework import permissions


class IsAdminOrStaff(permissions.BasePermission):
    """
    Permission for admin/staff users to access contact messages.
    ONLY SUPER_ADMIN can read contact messages.
    """
    
    def has_permission(self, request, view):
        """Check if user is SUPER_ADMIN."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'SUPER_ADMIN'
        )


class CanManageContactMessages(permissions.BasePermission):
    """
    Permission to manage (assign, update, reply) contact messages.
    ONLY SUPER_ADMIN can read and manage contact messages.
    """
    
    def has_permission(self, request, view):
        """Check if user can manage contact messages - SUPER_ADMIN only."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'SUPER_ADMIN'
        )
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions - SUPER_ADMIN only."""
        return request.user.role == 'SUPER_ADMIN'
        
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
                'SUPER_ADMIN', 'NATIONAL_ADMIN',
                'REGIONAL_COORDINATOR'
            ]
        )
    
    def has_object_permission(self, request, view, obj):
        """Check if user can reply to this specific message."""
        # Super admin and national admin can reply to all
        if request.user.role in ['SUPER_ADMIN', 'NATIONAL_ADMIN']:
            return True
        
        # Staff can only reply to assigned messages
        return obj.assigned_to == request.user
