"""
Procurement Authorization Policy

Defines access control rules for government procurement operations.

Role Access Matrix:
    SUPER_ADMIN - Full access to all procurement operations
    NATIONAL_ADMIN - Full access to all procurement operations
    NATIONAL_STAFF - Access based on granted permissions
    PROCUREMENT_OFFICER - Create, manage orders, assign farms, receive deliveries (no payment approval)
    FINANCE_OFFICER - View orders, approve and process payments
    AUDITOR - Read-only access to all procurement data
    REGIONAL_ADMIN/STAFF - View orders in their region
    VETERINARY_OFFICER - Quality verification access
    FARMER - View and respond to their own farm's assignments only

Key Principle: Separation of Duties
    - Procurement Officers handle operational aspects (orders, assignments, deliveries)
    - Finance Officers handle financial aspects (invoice approval, payment processing)
    - This prevents fraud and ensures accountability
"""

from .base_policy import BasePolicy


class ProcurementPolicy(BasePolicy):
    """Authorization policy for Procurement models."""
    
    # ========================================
    # PROCUREMENT ORDER POLICIES
    # ========================================
    
    @classmethod
    def can_view_order(cls, user, order=None):
        """
        Check if user can view a procurement order.
        
        Access Rules:
        - Super Admin / National Admin: All orders
        - Procurement Officer: All orders
        - Finance Officer: All orders (for payment tracking)
        - Auditor: All orders (read-only oversight)
        - National Staff: With view_procurement_orders permission
        - Regional Admin/Staff: Orders with their region as preferred
        - Farmer: Only assignments for their farm
        """
        # Platform and national admins
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        # Specialized roles with full view access
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_finance_officer(user):
            return True
        
        if cls.is_auditor(user):
            return True
        
        # National staff with permission
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'view_procurement_orders')
        
        # Regional level - can view orders with their region
        if cls.is_regional_admin(user) or cls.is_regional_staff(user):
            if order is None:
                # General view access - will be filtered by region in queryset
                return True
            # Specific order - check if region matches
            return order.preferred_region == user.region if user.region else False
        
        # Farmers can only see their assignments (handled in can_view_assignment)
        if cls.is_farmer(user):
            return False  # Use can_view_assignment instead
        
        return False
    
    @classmethod
    def can_create_order(cls, user):
        """
        Check if user can create procurement orders.
        
        Access Rules:
        - Super Admin / National Admin: Yes
        - Procurement Officer: Yes
        - National Staff: With create_procurement_orders permission
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'create_procurement_orders')
        
        return False
    
    @classmethod
    def can_edit_order(cls, user, order):
        """
        Check if user can edit a procurement order.
        
        Access Rules:
        - Super Admin / National Admin: Always
        - Procurement Officer: Draft, published, and assigning orders only
        - National Staff: With edit_procurement_orders permission (draft/published only)
        
        Note: Cannot edit completed or cancelled orders (except Super Admin)
        """
        if cls.is_super_admin(user):
            return True
        
        # No editing completed/cancelled orders (except super admin)
        if order.status in ['completed', 'cancelled']:
            return False
        
        if cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            # Can edit if they're the assigned officer or creator
            return order.assigned_procurement_officer == user or order.created_by == user
        
        if cls.is_national_staff(user):
            if order.status not in ['draft', 'published']:
                return False
            return cls.has_permission(user, 'edit_procurement_orders')
        
        return False
    
    @classmethod
    def can_publish_order(cls, user, order):
        """
        Check if user can publish a procurement order.
        
        Access Rules:
        - Super Admin / National Admin: Yes
        - Procurement Officer: Yes (draft orders only)
        - National Staff: With publish_procurement_orders permission
        """
        # Can only publish draft orders
        if order.status != 'draft':
            return False
        
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'publish_procurement_orders')
        
        return False
    
    @classmethod
    def can_assign_farms(cls, user, order):
        """
        Check if user can assign farms to a procurement order.
        
        Access Rules:
        - Super Admin / National Admin: Yes
        - Procurement Officer: Published orders they manage
        - National Staff: With assign_procurement_farms permission
        """
        # Can only assign to published or assigning orders
        if order.status not in ['published', 'assigning', 'assigned']:
            return False
        
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'assign_procurement_farms')
        
        return False
    
    @classmethod
    def can_cancel_order(cls, user, order):
        """
        Check if user can cancel a procurement order.
        
        Access Rules:
        - Super Admin: Always (override)
        - National Admin: Non-completed orders
        - Procurement Officer: Draft and published orders only
        - National Staff: With cancel_procurement_orders permission (draft only)
        """
        if cls.is_super_admin(user):
            return True
        
        # Cannot cancel already completed/cancelled orders
        if order.status in ['completed', 'cancelled']:
            return False
        
        if cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            # Procurement officer can cancel before assignments start
            return order.status in ['draft', 'published']
        
        if cls.is_national_staff(user):
            if order.status != 'draft':
                return False
            return cls.has_permission(user, 'cancel_procurement_orders')
        
        return False
    
    # ========================================
    # ORDER ASSIGNMENT POLICIES
    # ========================================
    
    @classmethod
    def can_view_assignment(cls, user, assignment=None):
        """
        Check if user can view an order assignment.
        
        Access Rules:
        - Super Admin / National Admin: All assignments
        - Procurement Officer: All assignments
        - Finance Officer: All assignments
        - Auditor: All assignments
        - National Staff: With view_procurement_orders permission
        - Regional Admin/Staff: Assignments for farms in their region
        - Farmer: Their own farm's assignments only
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_finance_officer(user):
            return True
        
        if cls.is_auditor(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'view_procurement_orders')
        
        # Regional level - check farm's region
        if cls.is_regional_admin(user) or cls.is_regional_staff(user):
            if assignment is None:
                return True  # Will be filtered by region in queryset
            return assignment.farm.region == user.region if user.region else False
        
        # Farmer can view their own farm's assignments
        if cls.is_farmer(user) and assignment is not None:
            return cls._is_farm_owner(user, assignment.farm)
        
        return False
    
    @classmethod
    def can_respond_to_assignment(cls, user, assignment):
        """
        Check if user (farmer) can accept or reject an assignment.
        
        Access Rules:
        - Farmer: Their own farm's pending assignments only
        """
        # Only pending assignments can be responded to
        if assignment.status != 'pending':
            return False
        
        if cls.is_farmer(user):
            return cls._is_farm_owner(user, assignment.farm)
        
        # Super admin and national admin can respond on behalf
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        return False
    
    @classmethod
    def can_update_assignment_status(cls, user, assignment):
        """
        Check if user can update assignment status (preparing, ready, etc.)
        
        Access Rules:
        - Farmer: Their own farm's accepted assignments
        - Procurement Officer: Any assignment
        - Super Admin / National Admin: Any assignment
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        # Farmer can update their own accepted assignments
        if cls.is_farmer(user):
            if assignment.status not in ['accepted', 'preparing', 'ready']:
                return False
            return cls._is_farm_owner(user, assignment.farm)
        
        return False
    
    # ========================================
    # DELIVERY POLICIES
    # ========================================
    
    @classmethod
    def can_receive_delivery(cls, user, assignment=None):
        """
        Check if user can confirm receipt of a delivery.
        
        Access Rules:
        - Super Admin / National Admin: Yes
        - Procurement Officer: Yes
        - National Staff: With receive_procurement_deliveries permission
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'receive_procurement_deliveries')
        
        return False
    
    @classmethod
    def can_verify_quality(cls, user, delivery=None):
        """
        Check if user can verify quality of a delivery.
        
        Access Rules:
        - Super Admin / National Admin: Yes
        - Procurement Officer: Yes
        - Veterinary Officer: Yes (animal health expertise)
        - National Staff: With verify_procurement_quality permission
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        # Veterinary officers can verify quality (animal health expertise)
        if cls.is_veterinary_officer(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'verify_procurement_quality')
        
        return False
    
    # ========================================
    # INVOICE & PAYMENT POLICIES
    # ========================================
    
    @classmethod
    def can_view_invoice(cls, user, invoice=None):
        """
        Check if user can view a procurement invoice.
        
        Access Rules:
        - Super Admin / National Admin: All invoices
        - Procurement Officer: All invoices
        - Finance Officer: All invoices
        - Auditor: All invoices
        - Farmer: Their own farm's invoices only
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_finance_officer(user):
            return True
        
        if cls.is_auditor(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'view_procurement_orders')
        
        # Farmer can view their own invoices
        if cls.is_farmer(user) and invoice is not None:
            return cls._is_farm_owner(user, invoice.farm)
        
        return False
    
    @classmethod
    def can_create_invoice(cls, user, assignment=None):
        """
        Check if user can create an invoice for a delivered assignment.
        
        Access Rules:
        - Super Admin / National Admin: Yes
        - Procurement Officer: Yes
        - Finance Officer: Yes
        - National Staff: With manage_procurement_invoices permission
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_finance_officer(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'manage_procurement_invoices')
        
        return False
    
    @classmethod
    def can_approve_invoice(cls, user, invoice):
        """
        Check if user can approve an invoice for payment.
        
        Access Rules (Separation of Duties):
        - Super Admin / National Admin: Yes
        - Finance Officer: Yes (primary responsibility)
        - National Staff: With approve_procurement_invoices permission
        
        Note: Procurement Officers cannot approve invoices (separation of duties)
        """
        # Can only approve pending invoices
        if invoice.payment_status != 'pending':
            return False
        
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        # Finance Officer - primary invoice approval role
        if cls.is_finance_officer(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'approve_procurement_invoices')
        
        # Procurement Officer CANNOT approve (separation of duties)
        return False
    
    @classmethod
    def can_process_payment(cls, user, invoice):
        """
        Check if user can process payment for an approved invoice.
        
        Access Rules (Separation of Duties):
        - Super Admin / National Admin: Yes
        - Finance Officer: Yes (primary responsibility)
        - National Staff: With process_procurement_payments permission
        
        Note: Procurement Officers cannot process payments (separation of duties)
        """
        # Can only process approved invoices
        if invoice.payment_status != 'approved':
            return False
        
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        # Finance Officer - primary payment processing role
        if cls.is_finance_officer(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'process_procurement_payments')
        
        # Procurement Officer CANNOT process payments (separation of duties)
        return False
    
    # ========================================
    # REPORT & ANALYTICS POLICIES
    # ========================================
    
    @classmethod
    def can_view_procurement_reports(cls, user):
        """
        Check if user can view procurement reports and analytics.
        
        Access Rules:
        - Super Admin / National Admin: Yes
        - Procurement Officer: Yes
        - Finance Officer: Yes
        - Auditor: Yes
        - National Staff: With view_procurement_reports permission
        - Regional Admin/Staff: Regional reports only
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_finance_officer(user):
            return True
        
        if cls.is_auditor(user):
            return True
        
        if cls.is_national_staff(user):
            return cls.has_permission(user, 'view_procurement_reports')
        
        if cls.is_regional_admin(user) or cls.is_regional_staff(user):
            return True  # Will be scoped to their region
        
        return False
    
    # ========================================
    # QUERYSET FILTERS
    # ========================================
    
    @classmethod
    def filter_orders_queryset(cls, user, queryset):
        """
        Filter procurement orders queryset based on user's access level.
        
        Returns:
            Filtered queryset appropriate for user's role
        """
        from django.db.models import Q
        
        # Full access roles
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return queryset
        
        if cls.is_procurement_officer(user):
            return queryset
        
        if cls.is_finance_officer(user):
            return queryset
        
        if cls.is_auditor(user):
            return queryset
        
        if cls.is_national_staff(user) and cls.has_permission(user, 'view_procurement_orders'):
            return queryset
        
        # Regional level - filter by preferred region
        if cls.is_regional_admin(user) or cls.is_regional_staff(user):
            if user.region:
                return queryset.filter(preferred_region=user.region)
            return queryset.none()
        
        # No access for other roles
        return queryset.none()
    
    @classmethod
    def filter_assignments_queryset(cls, user, queryset):
        """
        Filter order assignments queryset based on user's access level.
        
        Returns:
            Filtered queryset appropriate for user's role
        """
        # Full access roles
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return queryset
        
        if cls.is_procurement_officer(user):
            return queryset
        
        if cls.is_finance_officer(user):
            return queryset
        
        if cls.is_auditor(user):
            return queryset
        
        if cls.is_national_staff(user) and cls.has_permission(user, 'view_procurement_orders'):
            return queryset
        
        # Regional level - filter by farm's region
        if cls.is_regional_admin(user) or cls.is_regional_staff(user):
            if user.region:
                return queryset.filter(farm__region=user.region)
            return queryset.none()
        
        # Farmer - only their farm's assignments
        if cls.is_farmer(user):
            if hasattr(user, 'farm') and user.farm:
                return queryset.filter(farm=user.farm)
            return queryset.none()
        
        return queryset.none()
    
    @classmethod
    def filter_invoices_queryset(cls, user, queryset):
        """
        Filter procurement invoices queryset based on user's access level.
        
        Returns:
            Filtered queryset appropriate for user's role
        """
        # Full access roles
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return queryset
        
        if cls.is_procurement_officer(user):
            return queryset
        
        if cls.is_finance_officer(user):
            return queryset
        
        if cls.is_auditor(user):
            return queryset
        
        if cls.is_national_staff(user) and cls.has_permission(user, 'view_procurement_orders'):
            return queryset
        
        # Farmer - only their farm's invoices
        if cls.is_farmer(user):
            if hasattr(user, 'farm') and user.farm:
                return queryset.filter(farm=user.farm)
            return queryset.none()
        
        return queryset.none()
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    @staticmethod
    def _is_farm_owner(user, farm):
        """Check if user owns the given farm."""
        if hasattr(user, 'farm') and user.farm:
            return user.farm.id == farm.id
        # Also check via farm's user field
        return farm.user_id == user.id if farm.user_id else False
