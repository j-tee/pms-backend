"""
Role-based Access Control System (Rolify equivalent for Django)

This module provides a comprehensive role management system similar to Ruby's Rolify gem.
It includes:
- Dynamic role assignment
- Resource-level roles (roles scoped to specific objects)
- Role checking and permissions
- Role hierarchy support
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings
import uuid


class Role(models.Model):
    """
    Represents a role in the system.
    Roles can be global or scoped to specific resources (objects).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Role name (e.g., 'admin', 'moderator', 'farm_owner')"
    )
    
    # Resource-specific role (optional)
    resource_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Content type of the resource this role is scoped to"
    )
    resource_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="ID of the specific resource this role is scoped to"
    )
    resource = GenericForeignKey('resource_type', 'resource_id')
    
    # Role metadata
    description = models.TextField(
        blank=True,
        help_text="Description of what this role can do"
    )
    
    is_system_role = models.BooleanField(
        default=False,
        help_text="System roles cannot be deleted"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'roles'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
        unique_together = [['name', 'resource_type', 'resource_id']]
    
    def __str__(self):
        if self.resource:
            return f"{self.name} on {self.resource}"
        return self.name
    
    @classmethod
    def create_system_role(cls, name, description=''):
        """Create a system-wide role that cannot be deleted."""
        role, created = cls.objects.get_or_create(
            name=name,
            resource_type=None,
            resource_id=None,
            defaults={
                'description': description,
                'is_system_role': True
            }
        )
        return role
    
    @classmethod
    def create_resource_role(cls, name, resource, description=''):
        """Create a role scoped to a specific resource."""
        content_type = ContentType.objects.get_for_model(resource)
        role, created = cls.objects.get_or_create(
            name=name,
            resource_type=content_type,
            resource_id=resource.pk,
            defaults={'description': description}
        )
        return role


class UserRole(models.Model):
    """
    Assigns roles to users.
    Supports both global and resource-scoped role assignments.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_assignments'
    )
    
    # Assignment metadata
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments_made',
        help_text="User who assigned this role"
    )
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date for temporary roles"
    )
    
    class Meta:
        db_table = 'user_roles'
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'
        unique_together = [['user', 'role']]
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
    def is_expired(self):
        """Check if this role assignment has expired."""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False


class Permission(models.Model):
    """
    Defines specific permissions that can be granted to roles.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Permission name (e.g., 'can_approve_farms', 'can_edit_reports')"
    )
    
    codename = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique code for this permission"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of what this permission allows"
    )
    
    # Categorization
    category = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Category (e.g., 'farm_management', 'procurement', 'reporting')"
    )
    
    is_system_permission = models.BooleanField(
        default=False,
        help_text="System permissions cannot be deleted"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """
    Assigns permissions to roles.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='roles'
    )
    
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'role_permissions'
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'
        unique_together = [['role', 'permission']]
    
    def __str__(self):
        return f"{self.role} - {self.permission}"


class UserPermission(models.Model):
    """
    Direct permission assignment to users.
    
    This allows admins to grant specific permissions to staff users
    without having to create custom roles. Permissions can be granted
    or revoked by the user's managing admin.
    
    The user's effective permissions are:
    1. Implicit permissions from their role (admin roles)
    2. Default permissions for their role (staff roles)
    3. Explicitly granted permissions (this model)
    4. Minus any explicitly revoked permissions
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_permissions_granted'
    )
    
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='user_assignments'
    )
    
    # Whether this is a grant or revocation
    is_granted = models.BooleanField(
        default=True,
        help_text="True = permission granted, False = permission revoked"
    )
    
    # Who granted/revoked this permission
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='permissions_granted_to_others',
        help_text="Admin who granted/revoked this permission"
    )
    
    granted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Optional note explaining why permission was granted/revoked
    reason = models.TextField(
        blank=True,
        help_text="Reason for granting/revoking this permission"
    )
    
    class Meta:
        db_table = 'user_permissions'
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
        unique_together = [['user', 'permission']]
        indexes = [
            models.Index(fields=['user', 'is_granted']),
        ]
    
    def __str__(self):
        action = "granted" if self.is_granted else "revoked"
        return f"{self.permission.codename} {action} for {self.user.username}"


# Mixin to add role methods to User model
class RoleMixin:
    """
    Mixin to add Rolify-style methods to the User model.
    Add this to your custom User model.
    """
    
    def add_role(self, role_name, resource=None, assigned_by=None):
        """
        Add a role to the user.
        
        Args:
            role_name: Name of the role to add
            resource: Optional resource object to scope the role to
            assigned_by: User who is assigning this role
        
        Returns:
            UserRole instance
        """
        if resource:
            role = Role.create_resource_role(role_name, resource)
        else:
            role = Role.create_system_role(role_name)
        
        user_role, created = UserRole.objects.get_or_create(
            user=self,
            role=role,
            defaults={'assigned_by': assigned_by}
        )
        return user_role
    
    def remove_role(self, role_name, resource=None):
        """
        Remove a role from the user.
        
        Args:
            role_name: Name of the role to remove
            resource: Optional resource object if role is scoped
        
        Returns:
            Boolean indicating if role was removed
        """
        if resource:
            content_type = ContentType.objects.get_for_model(resource)
            role = Role.objects.filter(
                name=role_name,
                resource_type=content_type,
                resource_id=resource.pk
            ).first()
        else:
            role = Role.objects.filter(
                name=role_name,
                resource_type=None,
                resource_id=None
            ).first()
        
        if role:
            deleted_count, _ = UserRole.objects.filter(user=self, role=role).delete()
            return deleted_count > 0
        return False
    
    def has_role(self, role_name, resource=None):
        """
        Check if user has a specific role.
        
        Args:
            role_name: Name of the role to check
            resource: Optional resource object if role is scoped
        
        Returns:
            Boolean indicating if user has the role
        """
        from django.utils import timezone
        
        query = {
            'user': self,
            'role__name': role_name
        }
        
        if resource:
            content_type = ContentType.objects.get_for_model(resource)
            query['role__resource_type'] = content_type
            query['role__resource_id'] = resource.pk
        else:
            query['role__resource_type__isnull'] = True
            query['role__resource_id__isnull'] = True
        
        user_role = UserRole.objects.filter(**query).first()
        
        if user_role:
            # Check if role has expired
            if user_role.is_expired():
                user_role.delete()
                return False
            return True
        return False
    
    def has_any_role(self, *role_names, resource=None):
        """
        Check if user has any of the specified roles.
        
        Args:
            role_names: Variable number of role names to check
            resource: Optional resource object if roles are scoped
        
        Returns:
            Boolean indicating if user has any of the roles
        """
        return any(self.has_role(role_name, resource) for role_name in role_names)
    
    def has_all_roles(self, *role_names, resource=None):
        """
        Check if user has all of the specified roles.
        
        Args:
            role_names: Variable number of role names to check
            resource: Optional resource object if roles are scoped
        
        Returns:
            Boolean indicating if user has all of the roles
        """
        return all(self.has_role(role_name, resource) for role_name in role_names)
    
    def get_roles(self, resource=None):
        """
        Get all roles for the user.
        
        Args:
            resource: Optional resource object to filter scoped roles
        
        Returns:
            QuerySet of Role objects
        """
        from django.utils import timezone
        
        query = {'user': self}
        
        if resource:
            content_type = ContentType.objects.get_for_model(resource)
            query['role__resource_type'] = content_type
            query['role__resource_id'] = resource.pk
        
        # Exclude expired roles
        user_roles = UserRole.objects.filter(**query).exclude(
            expires_at__lt=timezone.now()
        )
        
        return Role.objects.filter(user_assignments__in=user_roles)
    
    def has_permission(self, permission_codename):
        """
        Check if user has a specific permission.
        
        Permission sources (in order of precedence):
        1. Explicitly revoked permissions (UserPermission with is_granted=False)
        2. Implicit permissions from admin role (from permissions_config)
        3. Explicitly granted permissions (UserPermission with is_granted=True)
        4. Default permissions for staff role (from permissions_config)
        5. Role-based permissions (through RolePermission)
        
        Args:
            permission_codename: Codename of the permission to check
        
        Returns:
            Boolean indicating if user has the permission
        """
        from django.utils import timezone
        from accounts.permissions_config import (
            get_implicit_permissions, 
            get_default_permissions
        )
        
        # 1. Check for explicit revocation
        if UserPermission.objects.filter(
            user=self,
            permission__codename=permission_codename,
            is_granted=False
        ).exists():
            return False
        
        # 2. Check implicit permissions for admin roles
        implicit = get_implicit_permissions(self.role)
        if implicit and (implicit == '__all__' or permission_codename in implicit):
            return True
        
        # 3. Check explicitly granted permissions
        if UserPermission.objects.filter(
            user=self,
            permission__codename=permission_codename,
            is_granted=True
        ).exists():
            return True
        
        # 4. Check default permissions for staff roles
        defaults = get_default_permissions(self.role)
        if permission_codename in defaults:
            return True
        
        # 5. Check role-based permissions (through Role model)
        active_user_roles = UserRole.objects.filter(user=self).exclude(
            expires_at__lt=timezone.now()
        )
        
        return RolePermission.objects.filter(
            role__user_assignments__in=active_user_roles,
            permission__codename=permission_codename
        ).exists()
    
    def get_effective_permissions(self):
        """
        Get all effective permissions for the user.
        
        Returns a dict with:
        - codenames: Set of permission codenames
        - details: List of dicts with permission info and source
        """
        from accounts.permissions_config import (
            get_implicit_permissions,
            get_default_permissions,
            get_all_permission_codenames,
            SYSTEM_PERMISSIONS
        )
        
        permissions = {}
        
        # 1. Start with implicit permissions from role
        implicit = get_implicit_permissions(self.role)
        if implicit:
            for codename in (get_all_permission_codenames() if implicit == '__all__' else implicit):
                permissions[codename] = {'source': 'role_implicit', 'granted': True}
        
        # 2. Add default permissions for staff roles
        defaults = get_default_permissions(self.role)
        for codename in defaults:
            if codename not in permissions:
                permissions[codename] = {'source': 'role_default', 'granted': True}
        
        # 3. Add explicitly granted permissions
        granted = UserPermission.objects.filter(
            user=self, is_granted=True
        ).select_related('permission')
        for up in granted:
            permissions[up.permission.codename] = {
                'source': 'explicit_grant',
                'granted': True,
                'granted_by': str(up.granted_by_id) if up.granted_by_id else None,
                'granted_at': up.granted_at.isoformat() if up.granted_at else None,
            }
        
        # 4. Remove explicitly revoked permissions
        revoked = UserPermission.objects.filter(
            user=self, is_granted=False
        ).select_related('permission')
        for up in revoked:
            if up.permission.codename in permissions:
                permissions[up.permission.codename] = {
                    'source': 'explicit_revoke',
                    'granted': False,
                    'revoked_by': str(up.granted_by_id) if up.granted_by_id else None,
                }
        
        # Build result
        active_codenames = {k for k, v in permissions.items() if v.get('granted', False)}
        
        return {
            'codenames': active_codenames,
            'details': permissions,
        }
    
    def grant_permission(self, permission_codename, granted_by=None, reason=''):
        """
        Grant a specific permission to this user.
        
        Args:
            permission_codename: Codename of the permission to grant
            granted_by: User granting the permission
            reason: Optional reason for granting
            
        Returns:
            UserPermission instance
        """
        permission = Permission.objects.filter(codename=permission_codename).first()
        if not permission:
            raise ValueError(f"Permission '{permission_codename}' does not exist")
        
        up, created = UserPermission.objects.update_or_create(
            user=self,
            permission=permission,
            defaults={
                'is_granted': True,
                'granted_by': granted_by,
                'reason': reason,
            }
        )
        return up
    
    def revoke_permission(self, permission_codename, revoked_by=None, reason=''):
        """
        Revoke a specific permission from this user.
        
        Args:
            permission_codename: Codename of the permission to revoke
            revoked_by: User revoking the permission
            reason: Optional reason for revoking
            
        Returns:
            UserPermission instance
        """
        permission = Permission.objects.filter(codename=permission_codename).first()
        if not permission:
            raise ValueError(f"Permission '{permission_codename}' does not exist")
        
        up, created = UserPermission.objects.update_or_create(
            user=self,
            permission=permission,
            defaults={
                'is_granted': False,
                'granted_by': revoked_by,
                'reason': reason,
            }
        )
        return up
    
    def clear_permission_override(self, permission_codename):
        """
        Remove any explicit grant/revoke for a permission.
        This resets the permission to its default state for the user's role.
        
        Args:
            permission_codename: Codename of the permission
            
        Returns:
            Boolean indicating if an override was cleared
        """
        deleted, _ = UserPermission.objects.filter(
            user=self,
            permission__codename=permission_codename
        ).delete()
        return deleted > 0

    def get_permissions(self):
        """
        Get all permissions for the user through their roles.
        
        Returns:
            QuerySet of Permission objects
        """
        from django.utils import timezone
        
        active_user_roles = UserRole.objects.filter(user=self).exclude(
            expires_at__lt=timezone.now()
        )
        
        return Permission.objects.filter(
            roles__role__user_assignments__in=active_user_roles
        ).distinct()
