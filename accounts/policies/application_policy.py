"""
Application Authorization Policy

Defines access control rules for FarmApplication and ApplicationQueue models.
"""

from .base_policy import BasePolicy


class ApplicationPolicy(BasePolicy):
    """Authorization policy for FarmApplication model."""
    
    @classmethod
    def can_view(cls, user, application):
        """
        Check if user can view application.
        
        Access Rules:
        - Super Admin: All applications
        - National Admin: All applications
        - Regional Coordinator: Applications in their region
        - Constituency Official: Applications in their constituency
        - Applicant: Own application only (if they have account)
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_regional_coordinator(user):
            return cls.is_in_user_jurisdiction(user, application.primary_constituency)
        
        if cls.is_constituency_official(user):
            return application.primary_constituency == user.constituency
        
        # Check if user is the applicant (after account creation)
        if hasattr(application, 'user_account') and application.user_account == user:
            return True
        
        return False
    
    @classmethod
    def can_create(cls, user, resource_class):
        """
        Check if user can create application.
        
        Access Rules:
        - Anonymous users can submit applications (public endpoint)
        - Admins can create applications on behalf of applicants
        """
        # Public can create (handled separately in public API)
        return True
    
    @classmethod
    def can_edit(cls, user, application):
        """
        Check if user can edit application.
        
        Access Rules:
        - Only before submission or when changes requested
        - Admins can edit at any stage
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        # Applicant can edit only if status allows
        if hasattr(application, 'user_account') and application.user_account == user:
            return application.status in ['draft', 'changes_requested']
        
        return False
    
    @classmethod
    def can_delete(cls, user, application):
        """
        Check if user can delete application.
        
        Access Rules:
        - Only super admin can delete
        - Soft delete with audit trail
        """
        return cls.is_super_admin(user)
    
    @classmethod
    def can_claim(cls, user, application):
        """
        Check if user can claim application from queue.
        
        Access Rules:
        - Must match current review level
        - Must be in correct jurisdiction
        - Cannot be already claimed
        """
        # Check if already claimed
        from farms.models import ApplicationQueue
        if ApplicationQueue.objects.filter(
            application=application,
            status__in=['claimed', 'in_progress']
        ).exists():
            return False
        
        # Check if user role matches review level
        current_level = application.current_review_level
        
        if current_level == 'constituency':
            if not cls.is_constituency_official(user):
                return False
            return application.primary_constituency == user.constituency
        
        elif current_level == 'regional':
            if not cls.is_regional_coordinator(user):
                return False
            return cls.is_in_user_jurisdiction(user, application.primary_constituency)
        
        elif current_level == 'national':
            return cls.is_national_admin(user)
        
        return False
    
    @classmethod
    def can_approve(cls, user, application):
        """
        Check if user can approve application at current stage.
        
        Access Rules:
        - Constituency Official: Can approve at constituency tier
        - Regional Coordinator: Can approve at regional tier
        - National Admin: Can approve at national tier
        - Must match jurisdiction
        """
        current_level = application.current_review_level
        
        if current_level == 'constituency':
            if not cls.is_constituency_official(user):
                return False
            return application.primary_constituency == user.constituency
        
        elif current_level == 'regional':
            if not cls.is_regional_coordinator(user):
                return False
            return cls.is_in_user_jurisdiction(user, application.primary_constituency)
        
        elif current_level == 'national':
            return cls.is_national_admin(user)
        
        return False
    
    @classmethod
    def can_reject(cls, user, application):
        """
        Check if user can reject application.
        
        Access Rules:
        - Same as can_approve
        - Any tier can reject
        """
        return cls.can_approve(user, application)
    
    @classmethod
    def can_request_changes(cls, user, application):
        """
        Check if user can request changes to application.
        
        Access Rules:
        - Any reviewer at current tier can request changes
        """
        return cls.can_approve(user, application)
    
    @classmethod
    def can_escalate(cls, user, application):
        """
        Check if user can escalate application to next tier.
        
        Access Rules:
        - Constituency can escalate to regional
        - Regional can escalate to national
        """
        current_level = application.current_review_level
        
        if current_level == 'constituency':
            return cls.is_constituency_official(user) and \
                   application.primary_constituency == user.constituency
        
        elif current_level == 'regional':
            return cls.is_regional_coordinator(user) and \
                   cls.is_in_user_jurisdiction(user, application.primary_constituency)
        
        return False
    
    @classmethod
    def can_set_priority(cls, user, application):
        """Check if user can set application priority."""
        # Admins and officials at current tier can set priority
        return cls.can_approve(user, application)
    
    @classmethod
    def scope(cls, user, queryset=None):
        """
        Filter applications based on user's access level.
        
        Returns:
            Filtered queryset
        """
        if queryset is None:
            from farms.models import FarmApplication
            queryset = FarmApplication.objects.all()
        
        # Super admin and national admin see all
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return queryset
        
        # Regional coordinator sees applications in their region
        if cls.is_regional_coordinator(user):
            constituencies = cls.get_user_constituencies(user)
            return queryset.filter(primary_constituency__in=constituencies)
        
        # Constituency official sees applications in their constituency
        if cls.is_constituency_official(user):
            return queryset.filter(primary_constituency=user.constituency)
        
        # Farmer sees own application only
        if cls.is_farmer(user):
            return queryset.filter(user_account=user)
        
        return queryset.none()
    
    @classmethod
    def queue_scope(cls, user):
        """
        Get applications in user's review queue.
        
        Returns:
            Queryset of applications pending user's review
        """
        from farms.models import FarmApplication
        
        base_queryset = FarmApplication.objects.filter(
            status__in=['submitted', 'constituency_review', 'regional_review', 'national_review']
        )
        
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            # National admins see applications at national tier
            return base_queryset.filter(current_review_level='national')
        
        if cls.is_regional_coordinator(user):
            # Regional coordinators see applications at regional tier in their region
            constituencies = cls.get_user_constituencies(user)
            return base_queryset.filter(
                current_review_level='regional',
                primary_constituency__in=constituencies
            )
        
        if cls.is_constituency_official(user):
            # Constituency officials see applications at constituency tier
            return base_queryset.filter(
                current_review_level='constituency',
                primary_constituency=user.constituency
            )
        
        return base_queryset.none()
