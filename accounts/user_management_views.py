"""
User Management Admin Views

Provides administrative endpoints for:
- User suspension/unsuspension
- Admin-initiated password reset
- Account unlock
- Force logout (session termination)
- Login history and attempts
- 2FA reset
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from .models import User
from .policies.user_policy import UserPolicy


class AdminUserSuspendView(APIView):
    """
    POST /api/admin/users/{user_id}/suspend/
    
    Suspend a user account.
    
    Request Body:
    {
        "reason": "Violation of terms of service",
        "duration_days": 30  // Optional - null for indefinite
    }
    
    Response:
    {
        "message": "User suspended successfully",
        "suspended_until": "2026-02-04T00:00:00Z"  // null if indefinite
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if not UserPolicy.can_suspend(request.user, target_user):
            return Response(
                {'error': 'Permission denied. You cannot suspend this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # SUPER_ADMIN accounts cannot be suspended
        if target_user.role == 'SUPER_ADMIN':
            return Response(
                {'error': 'SUPER_ADMIN accounts cannot be suspended.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Already suspended?
        if target_user.is_suspended:
            return Response(
                {'error': 'User is already suspended.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get suspension parameters
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Suspension reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        duration_days = request.data.get('duration_days')
        if duration_days is not None:
            try:
                duration_days = int(duration_days)
                if duration_days <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return Response(
                    {'error': 'duration_days must be a positive integer.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Perform suspension
        target_user.suspend(
            suspended_by=request.user,
            reason=reason,
            duration_days=duration_days
        )
        
        return Response({
            'message': 'User suspended successfully.',
            'user_id': str(target_user.id),
            'suspended_until': target_user.suspended_until.isoformat() if target_user.suspended_until else None,
            'is_indefinite': target_user.suspended_until is None
        })


class AdminUserUnsuspendView(APIView):
    """
    POST /api/admin/users/{user_id}/unsuspend/
    
    Remove suspension from a user account.
    
    Request Body:
    {
        "reason": "Suspension review completed"  // Optional
    }
    
    Response:
    {
        "message": "User unsuspended successfully"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission (same as suspend)
        if not UserPolicy.can_suspend(request.user, target_user):
            return Response(
                {'error': 'Permission denied. You cannot unsuspend this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Not suspended?
        if not target_user.is_suspended:
            return Response(
                {'error': 'User is not currently suspended.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform unsuspension
        target_user.unsuspend()
        
        return Response({
            'message': 'User unsuspended successfully.',
            'user_id': str(target_user.id)
        })


class AdminUserResetPasswordView(APIView):
    """
    POST /api/admin/users/{user_id}/reset-password/
    
    Trigger a password reset email for a user (admin-initiated).
    
    Request Body:
    {
        "notify_user": true  // Whether to send email notification
    }
    
    Response:
    {
        "message": "Password reset email sent",
        "reset_link_sent": true
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if not UserPolicy.can_reset_password(request.user, target_user):
            return Response(
                {'error': 'Permission denied. You cannot reset this user\'s password.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # SUPER_ADMIN passwords can only be reset by themselves
        if target_user.role == 'SUPER_ADMIN' and request.user.id != target_user.id:
            return Response(
                {'error': 'SUPER_ADMIN passwords can only be reset by the account owner.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notify_user = request.data.get('notify_user', True)
        
        try:
            from .auth_services import PasswordResetService
            
            if notify_user:
                # Send password reset email
                token = PasswordResetService.send_password_reset_email(target_user)
                return Response({
                    'message': 'Password reset email sent successfully.',
                    'user_id': str(target_user.id),
                    'reset_link_sent': True
                })
            else:
                # Generate token without sending email (admin will communicate separately)
                import secrets
                token = secrets.token_urlsafe(32)
                target_user.password_reset_token = token
                target_user.password_reset_token_expires = timezone.now() + timedelta(hours=24)
                target_user.save(update_fields=['password_reset_token', 'password_reset_token_expires'])
                
                return Response({
                    'message': 'Password reset token generated.',
                    'user_id': str(target_user.id),
                    'reset_link_sent': False,
                    'token': token,  # Admin can share this manually
                    'expires_at': target_user.password_reset_token_expires.isoformat()
                })
                
        except Exception as e:
            return Response(
                {'error': f'Failed to initiate password reset: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminUserUnlockView(APIView):
    """
    POST /api/admin/users/{user_id}/unlock/
    
    Unlock a user account that was locked due to failed login attempts.
    
    Request Body:
    {
        "reason": "User verified via phone"  // Optional
    }
    
    Response:
    {
        "message": "Account unlocked successfully"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission - same users who can suspend can unlock
        user = request.user
        if user.role not in ['SUPER_ADMIN', 'NATIONAL_ADMIN']:
            return Response(
                {'error': 'Permission denied. Only SUPER_ADMIN and NATIONAL_ADMIN can unlock accounts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # SUPER_ADMIN accounts - only self or other SUPER_ADMIN
        if target_user.role == 'SUPER_ADMIN' and user.id != target_user.id:
            if user.role != 'SUPER_ADMIN':
                return Response(
                    {'error': 'Only SUPER_ADMIN can unlock another SUPER_ADMIN account.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Check if actually locked
        if not target_user.is_account_locked():
            return Response(
                {'error': 'Account is not currently locked.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Unlock
        target_user.unlock_account()
        
        return Response({
            'message': 'Account unlocked successfully.',
            'user_id': str(target_user.id),
            'failed_login_attempts': target_user.failed_login_attempts
        })


class AdminUserForceLogoutView(APIView):
    """
    POST /api/admin/users/{user_id}/force-logout/
    
    Force logout a user by invalidating all their tokens.
    
    Request Body:
    {
        "reason": "Security concern"
    }
    
    Response:
    {
        "message": "User logged out from all sessions",
        "sessions_terminated": 1
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Only SUPER_ADMIN can force logout
        if request.user.role != 'SUPER_ADMIN':
            return Response(
                {'error': 'Permission denied. Only SUPER_ADMIN can force logout users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cannot force logout other SUPER_ADMINs
        if target_user.role == 'SUPER_ADMIN' and request.user.id != target_user.id:
            return Response(
                {'error': 'Cannot force logout another SUPER_ADMIN.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', '')
        
        # Force logout by incrementing token version
        old_version = target_user.token_version
        target_user.force_logout()
        
        # Also try to blacklist outstanding tokens if using token blacklist
        sessions_terminated = 1  # Minimum - token version increment
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            outstanding_tokens = OutstandingToken.objects.filter(user=target_user)
            for token in outstanding_tokens:
                BlacklistedToken.objects.get_or_create(token=token)
            sessions_terminated = outstanding_tokens.count() or 1
        except ImportError:
            # Token blacklist not installed, rely on token_version
            pass
        except Exception:
            # Blacklist failed, but token_version still works
            pass
        
        return Response({
            'message': 'User logged out from all sessions.',
            'user_id': str(target_user.id),
            'sessions_terminated': sessions_terminated,
            'token_version': target_user.token_version
        })


class AdminUserLoginAttemptsView(APIView):
    """
    GET /api/admin/users/{user_id}/login-attempts/
    
    Get login attempt information for a user.
    
    Response:
    {
        "user_id": "...",
        "failed_attempts": 3,
        "locked": false,
        "locked_until": null,
        "last_failed_login_at": "2026-01-04T10:00:00Z",
        "last_successful_login_at": "2026-01-03T08:00:00Z"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check view permission
        if not UserPolicy.can_view(request.user, target_user):
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # SUPER_ADMIN login attempts - only viewable by SUPER_ADMIN
        if target_user.role == 'SUPER_ADMIN' and request.user.role != 'SUPER_ADMIN':
            return Response(
                {'error': 'Only SUPER_ADMIN can view SUPER_ADMIN login attempts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        is_locked = target_user.is_account_locked()
        
        return Response({
            'user_id': str(target_user.id),
            'email': target_user.email,
            'failed_attempts': target_user.failed_login_attempts,
            'locked': is_locked,
            'locked_until': target_user.account_locked_until.isoformat() if target_user.account_locked_until else None,
            'last_failed_login_at': target_user.last_failed_login_at.isoformat() if target_user.last_failed_login_at else None,
            'last_successful_login_at': target_user.last_login_at.isoformat() if target_user.last_login_at else None,
            'is_suspended': target_user.is_suspended,
            'suspended_until': target_user.suspended_until.isoformat() if target_user.suspended_until else None
        })


class AdminUserLoginHistoryView(APIView):
    """
    GET /api/admin/users/{user_id}/login-history/
    
    Get login history for a user (requires audit logging to be implemented).
    
    Note: This returns basic info from User model. For detailed login history,
    a separate LoginHistory model would need to be created.
    
    Response:
    {
        "user_id": "...",
        "last_login": "2026-01-04T10:00:00Z",
        "account_created": "2025-06-01T00:00:00Z",
        "login_count": null,  // Requires LoginHistory model
        "recent_logins": []   // Requires LoginHistory model
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check view permission
        if not UserPolicy.can_view(request.user, target_user):
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # SUPER_ADMIN login history - only viewable by SUPER_ADMIN
        if target_user.role == 'SUPER_ADMIN' and request.user.role != 'SUPER_ADMIN':
            return Response(
                {'error': 'Only SUPER_ADMIN can view SUPER_ADMIN login history.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response({
            'user_id': str(target_user.id),
            'email': target_user.email,
            'last_login': target_user.last_login_at.isoformat() if target_user.last_login_at else None,
            'date_joined': target_user.date_joined.isoformat() if target_user.date_joined else None,
            'account_created': target_user.created_at.isoformat() if target_user.created_at else None,
            'is_active': target_user.is_active,
            'is_suspended': target_user.is_suspended,
            # Note: Detailed login history requires a LoginHistory model
            'login_count': None,
            'recent_logins': [],
            '_note': 'Detailed login history requires LoginHistory model implementation'
        })


class AdminUserReset2FAView(APIView):
    """
    POST /api/admin/users/{user_id}/reset-2fa/
    
    Reset/disable 2FA for a user who is locked out.
    
    Request Body:
    {
        "reason": "User lost phone",
        "require_setup_on_next_login": true
    }
    
    Response:
    {
        "message": "2FA has been reset for user",
        "mfa_disabled": true
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Only SUPER_ADMIN can reset 2FA
        if request.user.role != 'SUPER_ADMIN':
            return Response(
                {'error': 'Permission denied. Only SUPER_ADMIN can reset 2FA.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cannot reset 2FA for SUPER_ADMIN accounts
        if target_user.role == 'SUPER_ADMIN':
            return Response(
                {'error': 'Cannot reset 2FA for SUPER_ADMIN accounts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Reason is required for 2FA reset.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        require_setup = request.data.get('require_setup_on_next_login', True)
        
        try:
            from .mfa_models import MFAMethod, MFABackupCode, MFASettings
            
            # Disable all MFA methods
            MFAMethod.objects.filter(user=target_user).update(is_enabled=False)
            
            # Delete backup codes
            MFABackupCode.objects.filter(user=target_user).delete()
            
            # Update MFA settings
            mfa_settings, _ = MFASettings.objects.get_or_create(user=target_user)
            mfa_settings.is_enabled = False
            mfa_settings.require_on_next_login = require_setup
            mfa_settings.save()
            
            return Response({
                'message': '2FA has been reset for user.',
                'user_id': str(target_user.id),
                'mfa_disabled': True,
                'require_setup_on_next_login': require_setup
            })
            
        except ImportError:
            return Response(
                {'error': 'MFA models not available.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to reset 2FA: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminUserSuspensionStatusView(APIView):
    """
    GET /api/admin/users/{user_id}/suspension-status/
    
    Get detailed suspension status for a user.
    
    Response:
    {
        "user_id": "...",
        "is_suspended": true,
        "suspended_at": "2026-01-04T10:00:00Z",
        "suspended_until": "2026-02-04T10:00:00Z",
        "suspended_by": { "id": "...", "name": "Admin Name" },
        "suspension_reason": "Policy violation",
        "is_indefinite": false,
        "days_remaining": 30
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check view permission
        if not UserPolicy.can_view(request.user, target_user):
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check for expired suspension
        target_user.check_and_clear_expired_suspension()
        
        days_remaining = None
        if target_user.is_suspended and target_user.suspended_until:
            delta = target_user.suspended_until - timezone.now()
            days_remaining = max(0, delta.days)
        
        suspended_by_info = None
        if target_user.suspended_by:
            suspended_by_info = {
                'id': str(target_user.suspended_by.id),
                'name': target_user.suspended_by.get_full_name(),
                'email': target_user.suspended_by.email
            }
        
        return Response({
            'user_id': str(target_user.id),
            'email': target_user.email,
            'is_suspended': target_user.is_suspended,
            'suspended_at': target_user.suspended_at.isoformat() if target_user.suspended_at else None,
            'suspended_until': target_user.suspended_until.isoformat() if target_user.suspended_until else None,
            'suspended_by': suspended_by_info,
            'suspension_reason': target_user.suspension_reason,
            'is_indefinite': target_user.is_suspended and target_user.suspended_until is None,
            'days_remaining': days_remaining
        })
