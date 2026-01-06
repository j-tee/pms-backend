"""
Accounts Celery tasks for YEA Poultry Management System.

Background tasks for user management, notifications,
authentication events, and security alerts.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_welcome_notification(self, user_id: str, temp_password: str = None):
    """
    Send welcome notification to newly registered user.
    
    Usage:
        from accounts.tasks import send_welcome_notification
        send_welcome_notification.delay(str(user.id), 'temp123')
    """
    from accounts.models import User
    
    logger.info(f"Sending welcome notification to user {user_id}")
    
    try:
        user = User.objects.get(pk=user_id)
        
        if user.phone_number:
            from core.tasks import send_sms_async
            
            if temp_password:
                message = (
                    f"Welcome to YEA Poultry! Your account has been created. "
                    f"Username: {user.username}, Temporary Password: {temp_password}. "
                    f"Please login and change your password."
                )
            else:
                message = (
                    f"Welcome to YEA Poultry! Your account is ready. "
                    f"Login at the portal with your registered email."
                )
            
            send_sms_async.delay(str(user.phone_number), message)
            logger.info(f"Welcome SMS queued for user {user_id}")
        
        if user.email:
            from core.tasks import send_email_async
            
            subject = "Welcome to YEA Poultry Management System"
            if temp_password:
                html_content = f"""
                <h2>Welcome to YEA Poultry!</h2>
                <p>Your account has been created successfully.</p>
                <p><strong>Username:</strong> {user.username}</p>
                <p><strong>Temporary Password:</strong> {temp_password}</p>
                <p>Please login and change your password immediately.</p>
                <p>If you did not request this account, please ignore this email.</p>
                """
            else:
                html_content = """
                <h2>Welcome to YEA Poultry!</h2>
                <p>Your account is now active. You can login at the portal.</p>
                """
            
            send_email_async.delay(
                subject=subject,
                message=f"Welcome to YEA Poultry! Your account is ready.",
                recipient_list=[user.email],
                html_message=html_content
            )
            logger.info(f"Welcome email queued for user {user_id}")
        
        return {'status': 'success', 'user_id': user_id}
    except User.DoesNotExist:
        logger.error(f"User not found: {user_id}")
        return {'status': 'error', 'error': 'User not found'}
    except Exception as exc:
        logger.error(f"Failed to send welcome notification: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def send_password_reset_notification(user_id: str, reset_token: str):
    """
    Send password reset link/token to user.
    
    Usage:
        from accounts.tasks import send_password_reset_notification
        send_password_reset_notification.delay(str(user.id), 'reset-token')
    """
    from accounts.models import User
    from django.conf import settings
    
    logger.info(f"Sending password reset notification to user {user_id}")
    
    try:
        user = User.objects.get(pk=user_id)
        
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://app.yeapoultry.gov.gh')
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        if user.email:
            from core.tasks import send_email_async
            
            send_email_async.delay(
                subject="Password Reset - YEA Poultry",
                message=f"Click here to reset your password: {reset_link}",
                recipient_list=[user.email],
                html_message=f"""
                <h2>Password Reset Request</h2>
                <p>You requested a password reset for your YEA Poultry account.</p>
                <p><a href="{reset_link}">Click here to reset your password</a></p>
                <p>This link expires in 1 hour.</p>
                <p>If you didn't request this, please ignore this email.</p>
                """
            )
            logger.info(f"Password reset email queued for user {user_id}")
        
        if user.phone_number:
            from core.tasks import send_sms_async
            # Send OTP instead of link for SMS
            otp = reset_token[:6].upper()  # First 6 chars as OTP
            send_sms_async.delay(
                str(user.phone_number),
                f"YEA Poultry password reset OTP: {otp}. Valid for 1 hour."
            )
            logger.info(f"Password reset SMS queued for user {user_id}")
        
        return {'status': 'success', 'user_id': user_id}
    except User.DoesNotExist:
        logger.error(f"User not found: {user_id}")
        return {'status': 'error', 'error': 'User not found'}


@shared_task
def send_mfa_alert(user_id: str, action: str, device_info: str = None):
    """
    Send security alert for MFA-related actions.
    
    Actions: 'enabled', 'disabled', 'backup_used', 'reset'
    
    Usage:
        from accounts.tasks import send_mfa_alert
        send_mfa_alert.delay(str(user.id), 'enabled', 'Chrome on Windows')
    """
    from accounts.models import User
    
    logger.info(f"Sending MFA alert to user {user_id}: {action}")
    
    try:
        user = User.objects.get(pk=user_id)
        
        action_messages = {
            'enabled': "Two-factor authentication has been ENABLED on your account.",
            'disabled': "Two-factor authentication has been DISABLED on your account.",
            'backup_used': "A backup code was used to login to your account.",
            'reset': "Two-factor authentication has been RESET on your account by an administrator."
        }
        
        message = action_messages.get(action, f"MFA action: {action}")
        if device_info:
            message += f" Device: {device_info}"
        message += " If this wasn't you, contact support immediately."
        
        if user.email:
            from core.tasks import send_email_async
            send_email_async.delay(
                subject=f"Security Alert - YEA Poultry",
                message=message,
                recipient_list=[user.email],
                html_message=f"""
                <h2>Security Alert</h2>
                <p>{message}</p>
                <p>Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                """
            )
        
        if user.phone_number and action in ['disabled', 'backup_used']:
            # Only SMS for critical security events
            from core.tasks import send_sms_async
            send_sms_async.delay(str(user.phone_number), f"YEA Poultry Security Alert: {message}")
        
        return {'status': 'success', 'action': action}
    except User.DoesNotExist:
        return {'status': 'error', 'error': 'User not found'}


@shared_task
def send_login_alert(user_id: str, ip_address: str, location: str = None, device: str = None):
    """
    Send alert for suspicious login activity.
    
    Called when login is from new device/location.
    """
    from accounts.models import User
    
    logger.info(f"Sending login alert to user {user_id}")
    
    try:
        user = User.objects.get(pk=user_id)
        
        message = f"New login detected on your YEA Poultry account from {ip_address}"
        if location:
            message += f" ({location})"
        if device:
            message += f" using {device}"
        message += ". If this wasn't you, change your password immediately."
        
        if user.email:
            from core.tasks import send_email_async
            send_email_async.delay(
                subject="New Login Alert - YEA Poultry",
                message=message,
                recipient_list=[user.email]
            )
        
        return {'status': 'success', 'user_id': user_id}
    except User.DoesNotExist:
        return {'status': 'error', 'error': 'User not found'}


@shared_task
def cleanup_expired_tokens():
    """
    Clean up expired password reset tokens and invitation tokens.
    
    Runs periodically to maintain database hygiene.
    """
    from accounts.models import StaffInvitation
    
    logger.info("Cleaning up expired tokens...")
    
    now = timezone.now()
    deleted_counts = {}
    
    # Clean expired staff invitations
    expired_invitations = StaffInvitation.objects.filter(
        status='pending',
        expires_at__lt=now
    )
    deleted_counts['staff_invitations'] = expired_invitations.update(status='expired')
    
    logger.info(f"Token cleanup complete: {deleted_counts}")
    return deleted_counts


@shared_task
def notify_role_change(user_id: str, old_role: str, new_role: str, changed_by: str = None):
    """
    Notify user of role change.
    
    Usage:
        from accounts.tasks import notify_role_change
        notify_role_change.delay(str(user.id), 'FARMER', 'EXTENSION_OFFICER')
    """
    from accounts.models import User
    
    logger.info(f"Notifying user {user_id} of role change: {old_role} -> {new_role}")
    
    try:
        user = User.objects.get(pk=user_id)
        
        role_display = {
            'SUPER_ADMIN': 'Super Administrator',
            'YEA_OFFICIAL': 'YEA Official',
            'NATIONAL_ADMIN': 'National Administrator',
            'REGIONAL_COORDINATOR': 'Regional Coordinator',
            'CONSTITUENCY_OFFICIAL': 'Constituency Official',
            'EXTENSION_OFFICER': 'Extension Officer',
            'VETERINARY_OFFICER': 'Veterinary Officer',
            'FARMER': 'Farmer'
        }
        
        new_role_display = role_display.get(new_role, new_role)
        
        message = (
            f"Your YEA Poultry account role has been updated to {new_role_display}. "
            f"Your new permissions are now active."
        )
        
        if user.email:
            from core.tasks import send_email_async
            send_email_async.delay(
                subject="Role Update - YEA Poultry",
                message=message,
                recipient_list=[user.email]
            )
        
        if user.phone_number:
            from core.tasks import send_sms_async
            send_sms_async.delay(str(user.phone_number), message)
        
        return {'status': 'success', 'new_role': new_role}
    except User.DoesNotExist:
        return {'status': 'error', 'error': 'User not found'}


@shared_task
def send_staff_invitation_reminder(invitation_id: str):
    """
    Send reminder for pending staff invitation.
    
    Called 3 days before invitation expires.
    """
    from accounts.models import StaffInvitation
    
    logger.info(f"Sending invitation reminder for {invitation_id}")
    
    try:
        invitation = StaffInvitation.objects.get(pk=invitation_id, status='pending')
        
        days_left = (invitation.expires_at - timezone.now()).days
        
        if days_left > 0:
            from core.tasks import send_email_async
            send_email_async.delay(
                subject="Reminder: YEA Poultry Staff Invitation",
                message=f"You have a pending invitation to join YEA Poultry. "
                       f"Your invitation expires in {days_left} days. "
                       f"Please complete your registration.",
                recipient_list=[invitation.email]
            )
            return {'status': 'sent', 'days_left': days_left}
        else:
            return {'status': 'expired'}
    except StaffInvitation.DoesNotExist:
        return {'status': 'error', 'error': 'Invitation not found'}


@shared_task
def generate_user_activity_report(user_id: str = None, days: int = 30):
    """
    Generate user activity report for admin review.
    
    If user_id is None, generates system-wide activity report.
    """
    from accounts.models import User, LoginHistory
    from django.db.models import Count
    from django.core.cache import cache
    
    logger.info(f"Generating user activity report for {'user ' + user_id if user_id else 'all users'}")
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    if user_id:
        # Single user report
        try:
            user = User.objects.get(pk=user_id)
            logins = LoginHistory.objects.filter(
                user=user,
                timestamp__gte=start_date
            ).order_by('-timestamp')[:50]
            
            report = {
                'user_id': user_id,
                'username': user.username,
                'period_days': days,
                'login_count': logins.count(),
                'recent_logins': [
                    {
                        'timestamp': l.timestamp.isoformat(),
                        'ip': l.ip_address,
                        'success': l.success
                    } for l in logins[:10]
                ]
            }
        except User.DoesNotExist:
            return {'status': 'error', 'error': 'User not found'}
    else:
        # System-wide report
        active_users = User.objects.filter(
            last_login__gte=start_date
        ).count()
        
        new_users = User.objects.filter(
            date_joined__gte=start_date
        ).count()
        
        users_by_role = User.objects.values('role').annotate(
            count=Count('id')
        )
        
        report = {
            'period_days': days,
            'active_users': active_users,
            'new_users': new_users,
            'users_by_role': list(users_by_role),
            'total_users': User.objects.filter(is_active=True).count()
        }
    
    report['generated_at'] = timezone.now().isoformat()
    
    # Cache the report
    cache_key = f'report:user_activity:{user_id or "all"}:{days}'
    cache.set(cache_key, report, timeout=3600)
    
    logger.info(f"User activity report generated: {cache_key}")
    return report


@shared_task
def deactivate_dormant_accounts(days_inactive: int = 365):
    """
    Identify and optionally deactivate dormant accounts.
    
    For now, just reports dormant accounts. Actual deactivation
    would require admin approval.
    """
    from accounts.models import User
    
    logger.info(f"Checking for dormant accounts ({days_inactive}+ days inactive)")
    
    cutoff_date = timezone.now() - timedelta(days=days_inactive)
    
    dormant_users = User.objects.filter(
        is_active=True,
        last_login__lt=cutoff_date
    ).exclude(
        role__in=['SUPER_ADMIN', 'YEA_OFFICIAL', 'NATIONAL_ADMIN']  # Don't flag admin accounts
    )
    
    count = dormant_users.count()
    
    if count > 0:
        logger.warning(f"Found {count} dormant accounts (no login in {days_inactive}+ days)")
        
        # Get sample for review
        sample = dormant_users[:10].values('id', 'username', 'email', 'role', 'last_login')
        
        return {
            'dormant_count': count,
            'sample': list(sample),
            'days_inactive': days_inactive
        }
    
    return {'dormant_count': 0, 'days_inactive': days_inactive}
