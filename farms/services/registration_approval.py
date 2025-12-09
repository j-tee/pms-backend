"""
Registration Approval Service

Handles approval queue for self-registered farmers.
"""

from django.utils import timezone
from farms.invitation_models import RegistrationApproval
from farms.services.spam_detection import SpamDetectionService


class RegistrationApprovalService:
    """
    Service for managing registration approval queue.
    """
    
    @staticmethod
    def create_approval_request(
        user,
        farm_name,
        primary_constituency,
        ghana_card_number,
        phone_number,
        email="",
        first_name="",
        last_name=""
    ):
        """
        Create a registration approval request for self-registered farmer.
        
        Args:
            user: User object
            farm_name: str
            primary_constituency: str
            ghana_card_number: str
            phone_number: PhoneNumber
            email: str
            first_name: str
            last_name: str
        
        Returns:
            RegistrationApproval object
        """
        # Run spam detection
        spam_score, spam_flags = SpamDetectionService.check_registration({
            'farm_name': farm_name,
            'email': email,
            'phone_number': str(phone_number),
            'ghana_card_number': ghana_card_number,
            'first_name': first_name,
            'last_name': last_name,
        })
        
        # Create approval request
        approval = RegistrationApproval.objects.create(
            user=user,
            farm_name=farm_name,
            primary_constituency=primary_constituency,
            ghana_card_number=ghana_card_number,
            phone_number=phone_number,
            email=email,
            spam_score=spam_score,
            spam_flags=spam_flags,
        )
        
        # Calculate priority
        approval.calculate_priority()
        
        return approval
    
    @staticmethod
    def get_approval_queue(constituency=None, status='pending', order_by_priority=True):
        """
        Get approval queue for officers to review.
        
        Args:
            constituency: str (optional filter by constituency)
            status: str (filter by status, default 'pending')
            order_by_priority: bool (order by priority score)
        
        Returns:
            QuerySet of RegistrationApproval objects
        """
        queryset = RegistrationApproval.objects.filter(status=status)
        
        if constituency:
            queryset = queryset.filter(primary_constituency=constituency)
        
        if order_by_priority:
            queryset = queryset.order_by('-priority', 'submitted_at')
        else:
            queryset = queryset.order_by('submitted_at')
        
        return queryset
    
    @staticmethod
    def approve_registration(approval, officer, notes=""):
        """
        Approve a registration.
        
        Args:
            approval: RegistrationApproval object
            officer: User object (reviewing officer)
            notes: str (officer notes)
        
        Returns:
            (success: bool, message: str)
        """
        if approval.status != 'pending':
            return False, f"Cannot approve registration with status '{approval.status}'"
        
        approval.approve(officer, notes)
        
        # TODO: Send notification to farmer
        # TODO: Trigger farm profile creation
        
        return True, "Registration approved successfully"
    
    @staticmethod
    def reject_registration(approval, officer, reason):
        """
        Reject a registration.
        
        Args:
            approval: RegistrationApproval object
            officer: User object (reviewing officer)
            reason: str (rejection reason)
        
        Returns:
            (success: bool, message: str)
        """
        if approval.status != 'pending':
            return False, f"Cannot reject registration with status '{approval.status}'"
        
        if not reason:
            return False, "Rejection reason is required"
        
        approval.reject(officer, reason)
        
        # TODO: Send rejection notification to farmer
        
        return True, "Registration rejected"
    
    @staticmethod
    def flag_as_spam(approval, officer, reason):
        """
        Flag registration as spam.
        
        Args:
            approval: RegistrationApproval object
            officer: User object (reviewing officer)
            reason: str (spam reason)
        
        Returns:
            (success: bool, message: str)
        """
        approval.flag_as_spam(officer, reason)
        
        # TODO: Consider blocking IP address or user email
        
        return True, "Registration flagged as spam"
    
    @staticmethod
    def assign_to_officer(approval, officer):
        """
        Assign a registration to an officer for review.
        
        Args:
            approval: RegistrationApproval object
            officer: User object
        
        Returns:
            (success: bool, message: str)
        """
        if approval.status != 'pending':
            return False, "Can only assign pending registrations"
        
        approval.assigned_to = officer
        approval.save()
        
        return True, f"Registration assigned to {officer.get_full_name()}"
    
    @staticmethod
    def auto_assign_by_constituency(approval):
        """
        Auto-assign registration to an officer based on constituency.
        
        Args:
            approval: RegistrationApproval object
        
        Returns:
            (success: bool, officer: User or None, message: str)
        """
        from accounts.models import User
        from accounts.roles import UserRole
        
        # Find extension officers in this constituency
        officers = User.objects.filter(
            role=UserRole.EXTENSION_OFFICER,
            is_active=True,
            # TODO: Add constituency field to User model for filtering
        )
        
        if not officers.exists():
            return False, None, "No extension officers found for this constituency"
        
        # Simple round-robin: find officer with least assignments
        from django.db.models import Count
        officer = officers.annotate(
            assignment_count=Count('assigned_registrations')
        ).order_by('assignment_count').first()
        
        if officer:
            approval.assigned_to = officer
            approval.save()
            return True, officer, f"Auto-assigned to {officer.get_full_name()}"
        
        return False, None, "Failed to auto-assign"
    
    @staticmethod
    def mark_email_verified(approval):
        """
        Mark email as verified for an approval.
        
        Args:
            approval: RegistrationApproval object
        
        Returns:
            (success: bool, message: str)
        """
        approval.email_verified = True
        approval.email_verified_at = timezone.now()
        approval.save()
        
        # Recalculate priority (verified users get higher priority)
        approval.calculate_priority()
        
        return True, "Email marked as verified"
    
    @staticmethod
    def mark_phone_verified(approval):
        """
        Mark phone as verified for an approval.
        
        Args:
            approval: RegistrationApproval object
        
        Returns:
            (success: bool, message: str)
        """
        approval.phone_verified = True
        approval.phone_verified_at = timezone.now()
        approval.save()
        
        # Recalculate priority (verified users get higher priority)
        approval.calculate_priority()
        
        return True, "Phone marked as verified"
    
    @staticmethod
    def get_officer_queue(officer, status='pending'):
        """
        Get registrations assigned to a specific officer.
        
        Args:
            officer: User object
            status: str (filter by status)
        
        Returns:
            QuerySet of RegistrationApproval objects
        """
        return RegistrationApproval.objects.filter(
            assigned_to=officer,
            status=status
        ).order_by('-priority', 'submitted_at')
    
    @staticmethod
    def get_high_spam_score_registrations(threshold=50, constituency=None):
        """
        Get registrations with high spam scores for review.
        
        Args:
            threshold: int (spam score threshold, 0-100)
            constituency: str (optional filter by constituency)
        
        Returns:
            QuerySet of RegistrationApproval objects
        """
        queryset = RegistrationApproval.objects.filter(
            status='pending',
            spam_score__gte=threshold
        )
        
        if constituency:
            queryset = queryset.filter(primary_constituency=constituency)
        
        return queryset.order_by('-spam_score', 'submitted_at')
