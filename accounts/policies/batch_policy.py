"""
Batch/Program Authorization Policy

Defines access control rules for YEA Poultry Program batch models.
Note: Function names use 'batch' for backward compatibility, but internally manage batches.
"""

from .base_policy import BasePolicy


class BatchPolicy(BasePolicy):
    """Authorization policy for YEA Poultry Program batch models."""
    
    @classmethod
    def can_view_batch(cls, user, batch):
        """
        Check if user can view batch details.
        
        Access Rules:
        - Public batches: Anyone can view
        - Active batches: All users can view
        - Admins: Can view all batches
        """
        # Admins can view all
        if cls.has_admin_access(user):
            return True
        
        # Active programs are visible to all authenticated users
        if batch.status == 'active':
            return True
        
        return False
    
    @classmethod
    def can_create_batch(cls, user):
        """
        Check if user can create batch.
        
        Access Rules:
        - Super Admin
        - National Admin
        """
        return cls.is_super_admin(user) or cls.is_national_admin(user)
    
    @classmethod
    def can_edit_batch(cls, user, batch):
        """
        Check if user can edit batch.
        
        Access Rules:
        - Super Admin: All batches
        - National Admin: All batches
        """
        return cls.is_super_admin(user) or cls.is_national_admin(user)
    
    @classmethod
    def can_delete_batch(cls, user, batch):
        """Only super admin can delete batches."""
        return cls.is_super_admin(user)
    
    @classmethod
    def can_apply_to_batch(cls, user, batch):
        """
        Check if user can apply to batch.
        
        Access Rules:
        - Must be farmer
        - Must meet eligibility criteria
        - Batch must be active
        """
        if not cls.is_farmer(user):
            return False
        
        if batch.status != 'active':
            return False
        
        # Check if slots available
        if batch.slots_available <= 0:
            return False
        
        # Additional eligibility checks would go here
        # (farm age, capacity, constituency, batch target region, etc.)
        
        return True
    
    @classmethod
    def can_view_batch_applications(cls, user, batch):
        """
        Check if user can view applications to batch.
        
        Access Rules:
        - Admins: All applications
        - Officials: Applications in jurisdiction
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        # Regional/constituency officials can view if batch includes their area
        if cls.is_regional_coordinator(user) or cls.is_constituency_official(user):
            # Would need to check if batch targets their area
            return True
        
        return False
    
    @classmethod
    def can_approve_enrollment(cls, user, enrollment_application):
        """
        Check if user can approve batch enrollment.
        
        Access Rules:
        - Similar to farm application approval
        - Tier-based approval
        """
        current_level = enrollment_application.current_review_level
        
        if current_level == 'constituency':
            if not cls.is_constituency_official(user):
                return False
            return enrollment_application.farm.primary_constituency == user.constituency
        
        elif current_level == 'regional':
            if not cls.is_regional_coordinator(user):
                return False
            return cls.is_in_user_jurisdiction(user, enrollment_application.farm.primary_constituency)
        
        elif current_level == 'national':
            return cls.is_national_admin(user)
        
        return False
    
    @classmethod
    def can_view_batch_participants(cls, user, batch):
        """
        Check if user can view batch participants.
        
        Access Rules:
        - Admins: All participants
        - Officials: Participants in jurisdiction
        """
        if cls.has_admin_access(user):
            return True
        
        # Procurement officer can view (for distribution)
        if cls.is_procurement_officer(user):
            return True
        
        return False
    
    @classmethod
    def scope_batches(cls, user, queryset=None):
        """Filter batches based on user's access."""
        if queryset is None:
            from farms.models import Batch
            queryset = Batch.objects.all()
        
        # Admins see all
        if cls.has_admin_access(user):
            return queryset
        
        # Others see active batches only
        return queryset.filter(status='active')
    
    @classmethod
    def scope_enrollments(cls, user, queryset=None):
        """Filter batch enrollments based on user's access."""
        if queryset is None:
            from farms.models import BatchEnrollmentApplication
            queryset = BatchEnrollmentApplication.objects.all()
        
        # Admins see all
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return queryset
        
        # Regional coordinator sees enrollments in region
        if cls.is_regional_coordinator(user):
            constituencies = cls.get_user_constituencies(user)
            return queryset.filter(farm__primary_constituency__in=constituencies)
        
        # Constituency official sees enrollments in constituency
        if cls.is_constituency_official(user):
            return queryset.filter(farm__primary_constituency=user.constituency)
        
        # Farmer sees own enrollments
        if cls.is_farmer(user):
            return queryset.filter(farm__owner=user)
        
        return queryset.none()
