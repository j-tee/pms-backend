"""
Invitation Service

Handles creation and management of farm invitations.
"""

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from farms.invitation_models import FarmInvitation
from core.sms_service import send_sms


class InvitationService:
    """
    Service for managing farm invitations.
    """
    
    @staticmethod
    def create_invitation(
        officer,
        constituency,
        invitation_type='general',
        recipient_email=None,
        recipient_phone=None,
        recipient_name=None,
        is_single_use=True,
        max_uses=1,
        expires_in_days=30,
        notes=""
    ):
        """
        Create a new farm invitation.
        
        Args:
            officer: User object (issuing officer)
            constituency: str (constituency name)
            invitation_type: str ('government_farmer', 'independent_farmer', 'general')
            recipient_email: str (optional - pre-assign to specific email)
            recipient_phone: PhoneNumber (optional - pre-assign to specific phone)
            recipient_name: str (optional - pre-assign to specific farmer)
            is_single_use: bool (True = one-time use, False = reusable)
            max_uses: int (maximum number of uses for reusable codes)
            expires_in_days: int (expiration period in days)
            notes: str (officer notes)
        
        Returns:
            FarmInvitation object
        """
        invitation = FarmInvitation.objects.create(
            issued_by=officer,
            constituency=constituency,
            invitation_type=invitation_type,
            recipient_email=recipient_email or "",
            recipient_phone=recipient_phone or "",
            recipient_name=recipient_name or "",
            is_single_use=is_single_use,
            max_uses=max_uses,
            expires_at=timezone.now() + timedelta(days=expires_in_days),
            notes=notes
        )
        
        return invitation
    
    @staticmethod
    def send_invitation_email(invitation, custom_message=None):
        """
        Send invitation via email.
        
        Args:
            invitation: FarmInvitation object
            custom_message: str (optional custom message)
        
        Returns:
            (success: bool, message: str)
        """
        if not invitation.recipient_email:
            return False, "No recipient email provided"
        
        try:
            # Build invitation URL
            registration_url = f"{settings.FRONTEND_URL}/register?invitation={invitation.invitation_code}"
            
            # Email subject
            subject = "Invitation to Join Poultry Management System"
            
            # Email message
            farmer_type = invitation.get_invitation_type_display()
            officer_name = invitation.issued_by.get_full_name()
            
            message = custom_message or f"""
Dear {invitation.recipient_name or 'Farmer'},

You have been invited to join the Poultry Management System by {officer_name} 
from {invitation.constituency} Constituency.

Invitation Type: {farmer_type}

To complete your registration, please click the link below:
{registration_url}

Your invitation code: {invitation.invitation_code}

This invitation will expire on {invitation.expires_at.strftime('%B %d, %Y')}.

If you have any questions, please contact your constituency office.

Best regards,
Poultry Management System Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [invitation.recipient_email],
                fail_silently=False,
            )
            
            # Update invitation status
            invitation.sent_via_email = True
            invitation.email_sent_at = timezone.now()
            invitation.status = 'sent'
            invitation.save()
            
            return True, "Invitation sent successfully via email"
        
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    @staticmethod
    def send_invitation_sms(invitation, custom_message=None):
        """
        Send invitation via SMS.
        
        Args:
            invitation: FarmInvitation object
            custom_message: str (optional custom message)
        
        Returns:
            (success: bool, message: str)
        """
        if not invitation.recipient_phone:
            return False, "No recipient phone number provided"
        
        try:
            # Build short URL (you'd need a URL shortener service)
            registration_url = f"{settings.FRONTEND_URL}/register?invitation={invitation.invitation_code}"
            
            # SMS message (160 chars limit)
            message = custom_message or f"You're invited to join PMS! Code: {invitation.invitation_code}. Register at: {registration_url}"
            
            # Send SMS
            success, result = send_sms(
                phone_number=str(invitation.recipient_phone),
                message=message
            )
            
            if success:
                # Update invitation status
                invitation.sent_via_sms = True
                invitation.sms_sent_at = timezone.now()
                invitation.status = 'sent'
                invitation.save()
                
                return True, "Invitation sent successfully via SMS"
            else:
                return False, f"Failed to send SMS: {result}"
        
        except Exception as e:
            return False, f"Failed to send SMS: {str(e)}"
    
    @staticmethod
    def validate_invitation(invitation_code):
        """
        Validate an invitation code.
        
        Args:
            invitation_code: str
        
        Returns:
            (valid: bool, invitation: FarmInvitation or None, message: str)
        """
        try:
            invitation = FarmInvitation.objects.get(invitation_code=invitation_code)
            
            if invitation.is_valid:
                return True, invitation, "Invitation is valid"
            else:
                if invitation.status == 'expired':
                    return False, None, "This invitation has expired"
                elif invitation.status == 'revoked':
                    return False, None, "This invitation has been revoked"
                elif invitation.status == 'accepted' and invitation.is_single_use:
                    return False, None, "This invitation has already been used"
                elif not invitation.is_single_use and invitation.current_uses >= invitation.max_uses:
                    return False, None, "This invitation has reached its maximum number of uses"
                else:
                    return False, None, "This invitation is no longer valid"
        
        except FarmInvitation.DoesNotExist:
            return False, None, "Invalid invitation code"
    
    @staticmethod
    def use_invitation(invitation, user):
        """
        Mark invitation as used by a user.
        
        Args:
            invitation: FarmInvitation object
            user: User object
        
        Returns:
            (success: bool, message: str)
        """
        if not invitation.is_valid:
            return False, "Invitation is no longer valid"
        
        invitation.use(user)
        return True, "Invitation accepted successfully"
    
    @staticmethod
    def revoke_invitation(invitation, reason=""):
        """
        Revoke an invitation.
        
        Args:
            invitation: FarmInvitation object
            reason: str (reason for revocation)
        
        Returns:
            (success: bool, message: str)
        """
        if invitation.status == 'accepted':
            return False, "Cannot revoke an invitation that has already been accepted"
        
        invitation.revoke(reason)
        return True, "Invitation revoked successfully"
    
    @staticmethod
    def bulk_create_invitations(
        officer,
        constituency,
        count=10,
        invitation_type='general',
        is_single_use=False,
        max_uses=10,
        expires_in_days=90
    ):
        """
        Create multiple invitations for workshops, training sessions, etc.
        
        Args:
            officer: User object
            constituency: str
            count: int (number of invitations to create)
            invitation_type: str
            is_single_use: bool
            max_uses: int
            expires_in_days: int
        
        Returns:
            list of FarmInvitation objects
        """
        invitations = []
        
        for i in range(count):
            invitation = InvitationService.create_invitation(
                officer=officer,
                constituency=constituency,
                invitation_type=invitation_type,
                is_single_use=is_single_use,
                max_uses=max_uses,
                expires_in_days=expires_in_days,
                notes=f"Bulk invitation {i+1}/{count}"
            )
            invitations.append(invitation)
        
        return invitations
    
    @staticmethod
    def get_officer_invitations(officer, status=None):
        """
        Get all invitations issued by an officer.
        
        Args:
            officer: User object
            status: str (optional filter by status)
        
        Returns:
            QuerySet of FarmInvitation objects
        """
        queryset = FarmInvitation.objects.filter(issued_by=officer)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_constituency_invitations(constituency, status=None):
        """
        Get all invitations for a constituency.
        
        Args:
            constituency: str
            status: str (optional filter by status)
        
        Returns:
            QuerySet of FarmInvitation objects
        """
        queryset = FarmInvitation.objects.filter(constituency=constituency)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
