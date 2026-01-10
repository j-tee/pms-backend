"""
Permission Management API Views

Provides endpoints for admins to view and manage user permissions.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import User
from .policies import UserPolicy
from .services.permission_management_service import PermissionManagementService, PermissionManagementError
from .permissions_config import SYSTEM_PERMISSIONS


class PermissionListView(APIView):
    """
    List all available permissions.
    
    GET /api/admin/permissions/
    
    Returns list of all system permissions grouped by category.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Only admins can view permissions
        if not UserPolicy.has_admin_access(request.user):
            return Response(
                {'error': 'Admin access required', 'code': 'ADMIN_REQUIRED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Format permissions by category
        from accounts.permissions_config import get_permissions_as_dict
        all_permissions = get_permissions_as_dict()
        
        permissions_by_category = {}
        for codename, details in all_permissions.items():
            category = details['category']
            if category not in permissions_by_category:
                permissions_by_category[category] = []
            
            permissions_by_category[category].append({
                'codename': codename,
                'name': details['name'],
                'description': details['description'],
            })
        
        return Response({
            'permissions': permissions_by_category,
            'total_count': len(SYSTEM_PERMISSIONS)
        })


class UserPermissionsView(APIView):
    """
    View and manage a user's permissions.
    
    GET /api/admin/users/<user_id>/permissions/
    - View user's effective permissions
    
    POST /api/admin/users/<user_id>/permissions/
    - Bulk update permissions (grant/revoke multiple)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """Get user's permissions with details."""
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found', 'code': 'USER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requester can view this user
        if not UserPolicy.can_view(request.user, target_user):
            return Response(
                {'error': 'Access denied', 'code': 'ACCESS_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        service = PermissionManagementService(request.user)
        permissions = service.get_user_permissions(target_user)
        
        return Response({
            'user_id': str(target_user.id),
            'user_name': target_user.get_full_name() or target_user.email,
            'user_role': target_user.role,
            'permissions': permissions,
            'can_manage': UserPolicy.can_manage_permissions(request.user, target_user)
        })
    
    def post(self, request, user_id):
        """Bulk update user permissions."""
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found', 'code': 'USER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requester can manage this user's permissions
        if not UserPolicy.can_manage_permissions(request.user, target_user):
            return Response(
                {'error': 'Cannot manage this user\'s permissions', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Expected payload: {"permissions": {"view_all_farms": true, "create_batch": false, ...}}
        permission_updates = request.data.get('permissions', {})
        
        if not isinstance(permission_updates, dict):
            return Response(
                {'error': 'Invalid permissions format. Expected object with permission codenames as keys.',
                 'code': 'INVALID_FORMAT'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Transform dict format to lists for service
        grants = [codename for codename, should_grant in permission_updates.items() if should_grant]
        revokes = [codename for codename, should_grant in permission_updates.items() if not should_grant]
        
        service = PermissionManagementService(request.user)
        result = service.bulk_update_permissions(
            target_user, 
            grants=grants, 
            revokes=revokes,
            reason=request.data.get('reason', '')
        )
        
        # Return the lists of updated permissions
        return Response({
            'message': 'Permissions updated successfully',
            'updated': result['granted'] + result['revoked'],  # Combined list
            'granted': result['granted'],
            'revoked': result['revoked'],
            'errors': result['errors']
        })


class GrantPermissionView(APIView):
    """
    Grant a specific permission to a user.
    
    POST /api/admin/users/<user_id>/permissions/grant/
    
    Payload: {"permission": "permission_codename"}
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found', 'code': 'USER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        permission_codename = request.data.get('permission')
        if not permission_codename:
            return Response(
                {'error': 'Permission codename required', 'code': 'MISSING_PERMISSION'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = PermissionManagementService(request.user)
        
        try:
            result = service.grant_permission(target_user, permission_codename)
            
            return Response({
                'message': f'Permission "{permission_codename}" granted successfully',
                'permission': permission_codename,
                'user_id': str(target_user.id)
            })
        except PermissionManagementError as e:
            return Response({
                'error': str(e),
                'code': 'PERMISSION_MANAGEMENT_ERROR'
            }, status=status.HTTP_403_FORBIDDEN)


class RevokePermissionView(APIView):
    """
    Revoke a specific permission from a user.
    
    POST /api/admin/users/<user_id>/permissions/revoke/
    
    Payload: {"permission": "permission_codename"}
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found', 'code': 'USER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        permission_codename = request.data.get('permission')
        if not permission_codename:
            return Response(
                {'error': 'Permission codename required', 'code': 'MISSING_PERMISSION'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = PermissionManagementService(request.user)
        
        try:
            result = service.revoke_permission(target_user, permission_codename)
            
            return Response({
                'message': f'Permission "{permission_codename}" revoked successfully',
                'permission': permission_codename,
                'user_id': str(target_user.id)
            })
        except PermissionManagementError as e:
            return Response({
                'error': str(e),
                'code': 'REVOKE_FAILED'
            }, status=status.HTTP_400_BAD_REQUEST)


class ResetPermissionView(APIView):
    """
    Reset a user's permission to default (remove explicit grant/revoke).
    
    POST /api/admin/users/<user_id>/permissions/reset/
    
    Payload: {"permission": "permission_codename"} or {"all": true}
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found', 'code': 'USER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if requester can manage this user's permissions
        if not UserPolicy.can_manage_permissions(request.user, target_user):
            return Response(
                {'error': 'Cannot manage this user\'s permissions', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reset_all = request.data.get('all', False)
        permission_codename = request.data.get('permission')
        
        if not reset_all and not permission_codename:
            return Response(
                {'error': 'Provide "permission" codename or set "all" to true', 'code': 'MISSING_PARAMETER'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = PermissionManagementService(request.user)
        
        if reset_all:
            # Reset all explicit permissions
            from .roles import UserPermission
            deleted_count = UserPermission.objects.filter(user=target_user).count()
            UserPermission.objects.filter(user=target_user).delete()
            
            return Response({
                'message': f'All explicit permissions reset to default',
                'permissions_cleared': deleted_count,
                'user_id': str(target_user.id)
            })
        else:
            try:
                result = service.reset_permission(target_user, permission_codename)
                
                return Response({
                    'message': f'Permission "{permission_codename}" reset to default',
                    'permission': permission_codename,
                    'user_id': str(target_user.id)
                })
            except PermissionManagementError as e:
                return Response({
                    'error': str(e),
                    'code': 'RESET_FAILED'
                }, status=status.HTTP_400_BAD_REQUEST)


class ManageableUsersView(APIView):
    """
    List users whose permissions the current admin can manage.
    
    GET /api/admin/permissions/manageable-users/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not UserPolicy.has_admin_access(request.user):
            return Response(
                {'error': 'Admin access required', 'code': 'ADMIN_REQUIRED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        service = PermissionManagementService(request.user)
        users = service.get_manageable_users()
        
        # Serialize users
        user_data = []
        for user in users:
            user_data.append({
                'id': str(user.id),
                'email': user.email,
                'name': user.get_full_name() or user.email,
                'role': user.role,
                'region': user.region,
                'constituency': user.constituency,
                'is_active': user.is_active,
            })
        
        return Response({
            'users': user_data,
            'count': len(user_data)
        })
