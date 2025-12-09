"""
Staff User Invitation Service

Handles creation and management of office staff accounts through
secure email invitation system.
"""

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from accounts.models import User
import secrets
from datetime import timedelta


class StaffInvitationService:
    """
    Service for inviting office staff members to create their accounts.
    
    Flow:
    1. Admin creates user account with basic info (no password)
    2. System generates secure invitation token
    3. Invitation email sent with account setup link
    4. Staff member clicks link, sets password, completes profile
    5. Account activated
    """
    
    @staticmethod
    def create_staff_invitation(
        admin_user,
        email,
        first_name,
        last_name,
        role,
        phone=None,
        region=None,
        constituency=None
    ):
        """
        Create a new staff user account and send invitation email.
        
        Args:
            admin_user: User creating the invitation (must have permission)
            email: Staff member's email
            first_name: First name
            last_name: Last name
            role: User role (REGIONAL_COORDINATOR, CONSTITUENCY_OFFICIAL, etc.)
            phone: Optional phone number
            region: Required for REGIONAL_COORDINATOR and below
            constituency: Required for CONSTITUENCY_OFFICIAL
            
        Returns:
            dict with user and invitation_url
        """
        
        # Validate admin permission
        if admin_user.role not in ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR']:
            raise PermissionError("Only admins can create staff invitations")
        
        # Validate role hierarchy
        if admin_user.role == 'REGIONAL_COORDINATOR':
            if role not in ['CONSTITUENCY_OFFICIAL', 'EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
                raise PermissionError(f"Regional coordinators cannot create {role} users")
        
        if admin_user.role == 'NATIONAL_ADMIN':
            if role == 'SUPER_ADMIN':
                raise PermissionError("National admins cannot create SUPER_ADMIN users")
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise ValueError(f"User with email {email} already exists")
        
        # Generate username from email
        username = email.split('@')[0]
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}{counter}"
            counter += 1
        
        # Create user account (inactive until password set)
        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            phone=phone or '',
            region=region,
            constituency=constituency,
            is_active=False,  # Inactive until invitation accepted
            is_verified=False,
            email_verified=False
        )
        
        # Generate invitation token (valid for 7 days)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build invitation URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        invitation_url = f"{frontend_url}/staff/accept-invitation/{uid}/{token}/"
        
        # Store invitation expiry
        user.password_reset_token = token
        user.password_reset_token_expires = timezone.now() + timedelta(days=7)
        user.save()
        
        # Send invitation email
        try:
            StaffInvitationService._send_invitation_email(
                user=user,
                invitation_url=invitation_url,
                admin_name=f"{admin_user.first_name} {admin_user.last_name}",
                expires_days=7
            )
        except Exception as e:
            # If email fails, delete the user to maintain consistency
            user.delete()
            raise Exception(f"Failed to send invitation email: {str(e)}")
        
        return {
            'user': user,
            'invitation_url': invitation_url,
            'expires_at': user.password_reset_token_expires,
            'message': f'Invitation sent to {email}'
        }
    
    @staticmethod
    def _send_invitation_email(user, invitation_url, admin_name, expires_days):
        """Send invitation email to staff member."""
        
        subject = 'YEA Poultry Management System - Staff Account Invitation'
        
        message = f"""
Dear {user.first_name} {user.last_name},

You have been invited to join the YEA Poultry Management System as {user.get_role_display()}.

This invitation was sent by {admin_name}.

To activate your account and set your password, please click the link below:

{invitation_url}

This invitation link will expire in {expires_days} days.

Your Account Details:
- Username: {user.username}
- Email: {user.email}
- Role: {user.get_role_display()}
- Region: {user.region or 'N/A'}
- Constituency: {user.constituency or 'N/A'}

After setting up your account, you will be able to:
- Access the admin dashboard
- Review and approve applications (based on your role)
- Manage farmers and programs in your jurisdiction

If you did not expect this invitation, please contact your administrator.

Best regards,
YEA Poultry Management System
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    
    @staticmethod
    def accept_invitation(uid, token, password, confirm_password):
        """
        Accept staff invitation and activate account.
        
        Args:
            uid: User ID (base64 encoded)
            token: Invitation token
            password: New password
            confirm_password: Password confirmation
            
        Returns:
            dict with user and success message
        """
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        
        # Validate passwords match
        if password != confirm_password:
            raise ValueError("Passwords do not match")
        
        # Decode user ID
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise ValueError("Invalid invitation link")
        
        # Check if invitation expired
        if user.password_reset_token_expires and user.password_reset_token_expires < timezone.now():
            raise ValueError("This invitation has expired")
        
        # Validate token
        if not default_token_generator.check_token(user, token):
            raise ValueError("Invalid or expired invitation token")
        
        # Validate password strength
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Set password and activate account
        user.set_password(password)
        user.is_active = True
        user.email_verified = True  # Email verified through invitation
        user.is_verified = True
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.save()
        
        # Send welcome email
        StaffInvitationService._send_welcome_email(user)
        
        return {
            'user': user,
            'message': 'Account activated successfully. You can now log in.'
        }
    
    @staticmethod
    def _send_welcome_email(user):
        """Send welcome email after account activation."""
        
        subject = 'Welcome to YEA Poultry Management System'
        
        message = f"""
Dear {user.first_name} {user.last_name},

Welcome to the YEA Poultry Management System!

Your account has been successfully activated. You can now log in using:

Username: {user.username}
Email: {user.email}

Login at: {getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')}/login

Your role: {user.get_role_display()}
Jurisdiction: {user.region or 'National'} - {user.constituency or 'All Constituencies'}

Need help? Contact your administrator or refer to the system documentation.

Best regards,
YEA Poultry Management System
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,  # Don't fail if welcome email doesn't send
        )
    
    @staticmethod
    def resend_invitation(user_id, admin_user):
        """
        Resend invitation email to a user who hasn't activated yet.
        
        Args:
            user_id: UUID of the user
            admin_user: Admin requesting resend
            
        Returns:
            dict with new invitation_url
        """
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found")
        
        # Check if user already activated
        if user.is_active:
            raise ValueError("User account is already active")
        
        # Check admin permission
        if admin_user.role not in ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR']:
            raise PermissionError("Permission denied")
        
        # Generate new token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build new invitation URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        invitation_url = f"{frontend_url}/staff/accept-invitation/{uid}/{token}/"
        
        # Update expiry
        user.password_reset_token = token
        user.password_reset_token_expires = timezone.now() + timedelta(days=7)
        user.save()
        
        # Resend email
        StaffInvitationService._send_invitation_email(
            user=user,
            invitation_url=invitation_url,
            admin_name=f"{admin_user.first_name} {admin_user.last_name}",
            expires_days=7
        )
        
        return {
            'invitation_url': invitation_url,
            'expires_at': user.password_reset_token_expires,
            'message': f'Invitation resent to {user.email}'
        }
    
    @staticmethod
    def cancel_invitation(user_id, admin_user):
        """
        Cancel a pending staff invitation (deletes inactive user).
        
        Args:
            user_id: UUID of the user
            admin_user: Admin requesting cancellation
        """
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found")
        
        # Can only cancel inactive users
        if user.is_active:
            raise ValueError("Cannot cancel invitation for active user. Use deactivate instead.")
        
        # Check admin permission
        if admin_user.role not in ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR']:
            raise PermissionError("Permission denied")
        
        # Delete the user
        email = user.email
        user.delete()
        
        return {
            'message': f'Invitation for {email} has been cancelled'
        }
