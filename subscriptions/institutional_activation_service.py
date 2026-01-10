"""
Institutional Subscriber Account Activation Service

Handles the workflow of converting an inquiry into an active subscriber
with user account creation, email notifications, and activation tokens.
"""

import secrets
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

from .institutional_models import (
    InstitutionalInquiry,
    InstitutionalSubscriber,
    InstitutionalAPIKey
)

User = get_user_model()


class InstitutionalActivationService:
    """
    Service for activating institutional subscribers and creating user accounts.
    
    Flow:
    1. Admin reviews inquiry and clicks "Activate Subscriber"
    2. System creates InstitutionalSubscriber record
    3. System creates User account with INSTITUTIONAL_SUBSCRIBER role
    4. System sends activation email with temporary password
    5. Subscriber logs in, changes password on first login
    6. Subscriber accesses dashboard and manages API keys
    """
    
    @staticmethod
    def generate_temporary_password():
        """Generate a secure temporary password"""
        return secrets.token_urlsafe(16)
    
    @staticmethod
    def generate_activation_token():
        """Generate activation token for email verification"""
        return secrets.token_urlsafe(32)
    
    @classmethod
    @transaction.atomic
    def activate_inquiry(cls, inquiry_id, activated_by, plan, billing_cycle='monthly', 
                        send_email=True, create_api_key=True):
        """
        Convert an inquiry into an active subscriber with user account.
        
        Args:
            inquiry_id: UUID of the InstitutionalInquiry
            activated_by: User object (admin activating)
            plan: InstitutionalPlan object
            billing_cycle: 'monthly' or 'annually'
            send_email: Whether to send activation email
            create_api_key: Whether to generate initial API key
            
        Returns:
            dict with:
                - subscriber: InstitutionalSubscriber object
                - user: User object
                - temporary_password: String (only if created)
                - api_key: String (only if created)
                
        Raises:
            ValueError: If inquiry already converted or invalid
        """
        try:
            inquiry = InstitutionalInquiry.objects.select_for_update().get(id=inquiry_id)
        except InstitutionalInquiry.DoesNotExist:
            raise ValueError(f"Inquiry {inquiry_id} not found")
        
        if inquiry.status == 'converted':
            raise ValueError("Inquiry already converted to subscriber")
        
        # Step 1: Create InstitutionalSubscriber
        subscriber = InstitutionalSubscriber.objects.create(
            organization_name=inquiry.organization_name,
            organization_category=inquiry.organization_category,
            website=inquiry.website,
            contact_name=inquiry.contact_name,
            contact_email=inquiry.contact_email,
            contact_phone=inquiry.contact_phone,
            contact_position=inquiry.contact_position,
            plan=plan,
            status='pending',  # Will be 'trial' or 'active' after payment
            billing_cycle=billing_cycle,
            data_use_purpose=inquiry.data_use_purpose,
            is_verified=True,
            verified_by=activated_by,
            verified_at=timezone.now(),
            trial_days=plan.trial_days if hasattr(plan, 'trial_days') else 14,
        )
        
        # Step 2: Create User Account
        # Username: lowercase organization name with timestamp to ensure uniqueness
        base_username = inquiry.organization_name.lower()[:20].replace(' ', '_')
        # Remove special characters
        base_username = ''.join(c for c in base_username if c.isalnum() or c == '_')
        username = f"{base_username}_{timezone.now().strftime('%Y%m%d')}"
        
        # Ensure username is unique
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1
        
        # Generate temporary password
        temporary_password = cls.generate_temporary_password()
        
        # Create user - use contact_phone from inquiry
        user = User.objects.create_user(
            username=username,
            email=inquiry.contact_email,
            password=temporary_password,
            first_name=inquiry.contact_name.split()[0] if inquiry.contact_name else '',
            last_name=' '.join(inquiry.contact_name.split()[1:]) if len(inquiry.contact_name.split()) > 1 else '',
            phone=inquiry.contact_phone,  # Use phone from inquiry
            role=User.UserRole.INSTITUTIONAL_SUBSCRIBER,
            institutional_subscriber=subscriber,
            is_verified=True,
            email_verified=False,  # Must verify email via activation link
        )
        
        # Step 3: Update inquiry status
        inquiry.status = 'converted'
        inquiry.converted_subscriber = subscriber
        inquiry.converted_at = timezone.now()
        inquiry.save(update_fields=['status', 'converted_subscriber', 'converted_at'])
        
        # Step 4: Generate initial API key (optional)
        api_key_value = None
        if create_api_key:
            api_key, api_key_value = InstitutionalAPIKey.generate_key(
                subscriber=subscriber,
                name='Primary API Key',
                created_by=activated_by
            )
        
        # Step 5: Send activation email
        if send_email:
            cls.send_activation_email(
                user=user,
                subscriber=subscriber,
                temporary_password=temporary_password,
                api_key=api_key_value
            )
        
        return {
            'subscriber': subscriber,
            'user': user,
            'temporary_password': temporary_password,
            'api_key': api_key_value,
            'activation_sent': send_email
        }
    
    @classmethod
    def send_activation_email(cls, user, subscriber, temporary_password, api_key=None):
        """
        Send activation email to newly created institutional subscriber.
        
        Email contains:
        - Welcome message
        - Login credentials (username + temporary password)
        - Dashboard URL
        - API key (if generated)
        - Next steps
        """
        subject = f"Welcome to YEA PMS Institutional Data Access - {subscriber.organization_name}"
        
        context = {
            'organization_name': subscriber.organization_name,
            'contact_name': subscriber.contact_name,
            'username': user.username,
            'temporary_password': temporary_password,
            'dashboard_url': f"{settings.FRONTEND_URL}/institutional/dashboard",
            'login_url': f"{settings.FRONTEND_URL}/login",
            'plan_name': subscriber.plan.name,
            'billing_cycle': subscriber.billing_cycle,
            'api_key': api_key,
            'support_email': settings.DEFAULT_FROM_EMAIL,
        }
        
        # HTML email
        html_message = render_to_string(
            'emails/institutional_activation.html',
            context
        )
        
        # Plain text fallback
        text_message = f"""
Welcome to YEA PMS Institutional Data Access

Dear {subscriber.contact_name},

Your institutional data subscription account has been activated for {subscriber.organization_name}.

Login Credentials:
-------------------
Username: {user.username}
Temporary Password: {temporary_password}
Dashboard: {context['dashboard_url']}

IMPORTANT: Please log in and change your password immediately.

Your Subscription:
-------------------
Plan: {subscriber.plan.name}
Billing: {subscriber.billing_cycle.title()}

{"API Key: " + api_key if api_key else "You can generate API keys from your dashboard."}

Next Steps:
-------------------
1. Log in at {context['login_url']}
2. Change your temporary password
3. Explore your dashboard
4. Generate additional API keys if needed
5. Start integrating our API into your systems

Need Help?
-------------------
Contact us at {settings.DEFAULT_FROM_EMAIL}
API Documentation: {settings.FRONTEND_URL}/docs/api

Thank you for choosing YEA PMS!

Best regards,
YEA Poultry Management System Team
        """.strip()
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
    
    @classmethod
    @transaction.atomic
    def add_team_member(cls, subscriber, email, name, phone=None, role='member', invited_by=None):
        """
        Add additional team member to institutional subscriber account.
        Supports one-to-many relationship (multiple users per organization).
        
        Args:
            subscriber: InstitutionalSubscriber object
            email: Email address of new team member
            name: Full name
            phone: Phone number (optional, will use subscriber phone if not provided)
            role: 'admin' or 'member' (for future permissions)
            invited_by: User who sent the invitation
            
        Returns:
            dict with:
                - user: User object
                - temporary_password: String
        """
        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            raise ValueError(f"User with email {email} already exists")
        
        # Check subscriber is active
        if not subscriber.is_active:
            raise ValueError("Cannot add team members to inactive subscription")
        
        # Use provided phone or generate unique one based on subscriber's phone
        if not phone:
            # Generate unique phone from subscriber phone
            base_phone = subscriber.contact_phone
            phone = base_phone
            counter = 1
            while User.objects.filter(phone=phone).exists():
                # Append suffix to phone number
                phone = f"{base_phone[:-len(str(counter))]}{counter}"
                counter += 1
        
        # Generate username from email
        base_username = email.split('@')[0].lower()[:20]
        username = base_username
        
        # Ensure unique username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        
        # Generate temporary password
        temporary_password = cls.generate_temporary_password()
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            phone=phone,
            password=temporary_password,
            first_name=name.split()[0] if name else '',
            last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
            role=User.UserRole.INSTITUTIONAL_SUBSCRIBER,
            institutional_subscriber=subscriber,
            is_verified=True,
            email_verified=False,
        )
        
        # Send invitation email
        cls.send_team_member_invitation(
            user=user,
            subscriber=subscriber,
            temporary_password=temporary_password,
            invited_by=invited_by
        )
        
        return {
            'user': user,
            'temporary_password': temporary_password
        }
    
    @classmethod
    def send_team_member_invitation(cls, user, subscriber, temporary_password, invited_by=None):
        """Send invitation email to new team member"""
        inviter_name = invited_by.get_full_name() if invited_by else "Your organization"
        
        subject = f"Invitation to {subscriber.organization_name} - YEA PMS Data Access"
        
        message = f"""
You've been invited to join {subscriber.organization_name}'s institutional data access account.

Invited by: {inviter_name}

Login Credentials:
-------------------
Username: {user.username}
Temporary Password: {temporary_password}
Dashboard: {settings.FRONTEND_URL}/institutional/dashboard

Please log in and change your password immediately.

Best regards,
YEA Poultry Management System Team
        """.strip()
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    
    @classmethod
    def deactivate_subscriber(cls, subscriber_id, deactivated_by, reason=''):
        """
        Deactivate institutional subscriber and all associated users.
        
        - Sets subscriber status to 'suspended'
        - Deactivates all API keys
        - Suspends all user accounts
        """
        try:
            subscriber = InstitutionalSubscriber.objects.get(id=subscriber_id)
        except InstitutionalSubscriber.DoesNotExist:
            raise ValueError(f"Subscriber {subscriber_id} not found")
        
        with transaction.atomic():
            # Update subscriber status
            subscriber.status = 'suspended'
            subscriber.save(update_fields=['status'])
            
            # Deactivate all API keys
            subscriber.api_keys.update(is_active=False)
            
            # Suspend all user accounts
            for user in subscriber.users.all():
                user.is_suspended = True
                user.suspended_at = timezone.now()
                user.suspended_by = deactivated_by
                user.suspension_reason = reason or 'Institutional subscription deactivated'
                user.save(update_fields=[
                    'is_suspended', 'suspended_at', 'suspended_by', 'suspension_reason'
                ])
        
        return subscriber
    
    @classmethod
    def reactivate_subscriber(cls, subscriber_id):
        """
        Reactivate institutional subscriber and all associated users.
        """
        try:
            subscriber = InstitutionalSubscriber.objects.get(id=subscriber_id)
        except InstitutionalSubscriber.DoesNotExist:
            raise ValueError(f"Subscriber {subscriber_id} not found")
        
        with transaction.atomic():
            # Update subscriber status
            subscriber.status = 'active'
            subscriber.save(update_fields=['status'])
            
            # Reactivate API keys
            subscriber.api_keys.update(is_active=True)
            
            # Unsuspend all user accounts
            subscriber.users.update(
                is_suspended=False,
                suspended_at=None,
                suspended_by=None,
                suspension_reason=''
            )
        
        return subscriber
