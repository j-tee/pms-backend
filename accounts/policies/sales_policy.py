"""
Sales & Revenue Authorization Policy

Defines access control rules for sales, payments, and payout models.
"""

from .base_policy import BasePolicy


class SalesPolicy(BasePolicy):
    """Authorization policy for sales and payment models."""
    
    @classmethod
    def can_view_sale(cls, user, sale):
        """
        Check if user can view sale record.
        
        Access Rules:
        - Farmer: Own sales only
        - Auditor: If investigating farm
        - Finance Officer: All sales
        - Admins: All sales
        """
        # Get farm from sale
        farm = sale.farm
        
        # Admins can view all
        if cls.has_admin_access(user):
            return True
        
        # Finance officer can view all
        if cls.is_finance_officer(user):
            return True
        
        # Auditor can view if investigating
        if cls.is_auditor(user):
            return cls.is_active_investigation(user, farm)
        
        # Farmer can view own sales
        if cls.is_farmer(user):
            return farm.owner == user
        
        return False
    
    @classmethod
    def can_create_sale(cls, user, farm):
        """
        Check if user can create sale for farm.
        
        Access Rules:
        - Must be farm owner
        - Must have marketplace enabled
        - Subscription must be active
        """
        # Must be farmer
        if not cls.is_farmer(user):
            return False
        
        # Must own the farm
        if farm.owner != user:
            return False
        
        # Must have marketplace enabled
        if not farm.marketplace_enabled:
            return False
        
        # Check subscription status
        if farm.subscription_type == 'none':
            return False
        
        # If has subscription object, check status
        if hasattr(farm, 'subscription'):
            subscription = farm.subscription
            if subscription.status not in ['trial', 'active']:
                return False
        
        return True
    
    @classmethod
    def can_edit_sale(cls, user, sale):
        """
        Check if user can edit sale.
        
        Access Rules:
        - Farm owner can edit pending sales only
        - Admins can edit any sale
        """
        if cls.is_super_admin(user):
            return True
        
        # Farmer can edit own pending sales
        if cls.is_farmer(user) and sale.farm.owner == user:
            return sale.status == 'pending'
        
        return False
    
    @classmethod
    def can_delete_sale(cls, user, sale):
        """
        Check if user can delete sale.
        
        Access Rules:
        - Only super admin
        - Soft delete with audit trail
        """
        return cls.is_super_admin(user)
    
    @classmethod
    def can_refund_sale(cls, user, sale):
        """
        Check if user can issue refund for sale.
        
        Access Rules:
        - Finance officer can refund
        - Super admin can refund
        """
        return cls.is_super_admin(user) or cls.is_finance_officer(user)
    
    @classmethod
    def can_view_payment(cls, user, payment):
        """Check if user can view payment details."""
        return cls.can_view_sale(user, payment.egg_sale or payment.bird_sale)
    
    @classmethod
    def can_view_payout(cls, user, payout):
        """
        Check if user can view payout details.
        
        Access Rules:
        - Farm owner: Own payouts
        - Finance officer: All payouts
        - Auditor: If investigating
        """
        farm = payout.farm
        
        # Finance officer can view all
        if cls.is_finance_officer(user):
            return True
        
        # Auditor can view if investigating
        if cls.is_auditor(user):
            return cls.is_active_investigation(user, farm)
        
        # Farm owner can view own payouts
        if cls.is_farmer(user):
            return farm.owner == user
        
        # Admins can view all
        if cls.has_admin_access(user):
            return True
        
        return False
    
    @classmethod
    def can_process_payout(cls, user, payout):
        """
        Check if user can process payout.
        
        Access Rules:
        - Finance officer only
        """
        return cls.is_finance_officer(user)
    
    @classmethod
    def can_retry_payout(cls, user, payout):
        """Check if user can retry failed payout."""
        return cls.is_finance_officer(user)
    
    @classmethod
    def can_view_fraud_alert(cls, user, alert):
        """
        Check if user can view fraud alert.
        
        Access Rules:
        - National admin: All alerts
        - Auditor: Assigned alerts
        - Finance officer: All alerts
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_finance_officer(user):
            return True
        
        if cls.is_auditor(user):
            # Can view if assigned to them
            return alert.reviewed_by == user
        
        return False
    
    @classmethod
    def can_investigate_fraud(cls, user, alert):
        """
        Check if user can investigate fraud alert.
        
        Access Rules:
        - Auditor: Assigned or unassigned alerts
        - National admin: Can assign auditors
        """
        if cls.is_national_admin(user):
            return True
        
        if cls.is_auditor(user):
            # Can investigate if unassigned or assigned to them
            return alert.reviewed_by is None or alert.reviewed_by == user
        
        return False
    
    @classmethod
    def can_view_platform_revenue(cls, user):
        """
        Check if user can view platform revenue analytics.
        
        Access Rules:
        - Super admin
        - National admin
        - Finance officer
        """
        return (
            cls.is_super_admin(user) or
            cls.is_national_admin(user) or
            cls.is_finance_officer(user)
        )
    
    @classmethod
    def can_adjust_commission_rate(cls, user):
        """
        Check if user can adjust commission rates.
        
        Access Rules:
        - Super admin only
        """
        return cls.is_super_admin(user)
    
    @classmethod
    def scope_sales(cls, user, queryset=None):
        """Filter sales based on user's access."""
        if queryset is None:
            from sales_revenue.models import EggSale, BirdSale
            # This would need to be called with specific model
            raise ValueError("Must provide queryset")
        
        # Finance officer and admins see all
        if (cls.is_super_admin(user) or cls.is_national_admin(user) or
            cls.is_finance_officer(user)):
            return queryset
        
        # Auditor sees sales from farms under investigation
        if cls.is_auditor(user):
            from sales_revenue.models import FraudAlert
            farm_ids = FraudAlert.objects.filter(
                reviewed_by=user,
                status='under_review'
            ).values_list('farm_id', flat=True)
            return queryset.filter(farm_id__in=farm_ids)
        
        # Farmer sees own sales
        if cls.is_farmer(user):
            return queryset.filter(farm__owner=user)
        
        return queryset.none()
    
    @classmethod
    def scope_payouts(cls, user, queryset=None):
        """Filter payouts based on user's access."""
        if queryset is None:
            from sales_revenue.models import FarmerPayout
            queryset = FarmerPayout.objects.all()
        
        # Finance officer and admins see all
        if (cls.is_super_admin(user) or cls.is_national_admin(user) or
            cls.is_finance_officer(user)):
            return queryset
        
        # Auditor sees payouts from farms under investigation
        if cls.is_auditor(user):
            from sales_revenue.models import FraudAlert
            farm_ids = FraudAlert.objects.filter(
                reviewed_by=user,
                status='under_review'
            ).values_list('farm_id', flat=True)
            return queryset.filter(farm_id__in=farm_ids)
        
        # Farmer sees own payouts
        if cls.is_farmer(user):
            return queryset.filter(farm__owner=user)
        
        return queryset.none()
