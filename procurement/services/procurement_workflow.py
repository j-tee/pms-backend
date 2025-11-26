"""
Procurement Workflow Service

Manages government bulk orders:
- Farm recommendation algorithm
- Auto-assignment to farms
- Inventory reservation
- Delivery tracking
- Payment processing
"""

from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum, F, Case, When, Value, IntegerField
from datetime import timedelta
from decimal import Decimal
import logging

from procurement.models import (
    ProcurementOrder, OrderAssignment, DeliveryConfirmation, ProcurementInvoice
)
from farms.models import Farm
from procurement.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)
notification_service = get_notification_service()


class ProcurementWorkflowService:
    """Service for managing procurement workflow"""
    
    @transaction.atomic
    def create_order(self, created_by, **order_data):
        """
        Create a new procurement order.
        
        Args:
            created_by: User creating the order
            **order_data: Order fields
        
        Returns:
            ProcurementOrder instance
        """
        order = ProcurementOrder.objects.create(
            created_by=created_by,
            status='draft',
            **order_data
        )
        
        logger.info(f"Procurement order created: {order.order_number}")
        return order
    
    @transaction.atomic
    def publish_order(self, order):
        """
        Publish order - make it visible for farm assignments.
        """
        if order.status != 'draft':
            raise ValueError(f"Cannot publish order with status: {order.status}")
        
        order.status = 'published'
        order.published_at = timezone.now()
        order.save()
        
        logger.info(f"Order published: {order.order_number}")
        return order
    
    def recommend_farms(self, order, limit=None):
        """
        Recommend farms for an order based on:
        1. Production type match
        2. Current inventory/capacity
        3. Distance from delivery location (if GPS available)
        4. Farm approval status
        5. Past performance (quality, on-time delivery)
        6. Business registration (priority)
        
        Returns:
            QuerySet of Farm objects with recommended_quantity annotation
        """
        if limit is None:
            limit = order.max_farms
        
        # Base filter: Active approved farms with matching production type
        base_filter = Q(
            farm_status='Active',
            application_status='Approved - Farm ID Assigned'
        )
        
        # Production type matching
        if order.production_type == 'Broilers':
            base_filter &= Q(primary_production_type__in=['Broilers', 'Both'])
        elif order.production_type == 'Layers':
            base_filter &= Q(primary_production_type__in=['Layers', 'Both'])
        
        # Preferred region filter
        if order.preferred_region:
            # Priority to preferred region, but don't exclude others
            pass  # Handle with Case/When in ordering
        
        farms = Farm.objects.filter(base_filter).select_related('user')
        
        # Annotate priority score
        farms = farms.annotate(
            # Priority score (higher is better)
            priority_score=Case(
                # Business registered = +100 points
                When(business_registration_number__isnull=False, then=Value(100)),
                default=Value(0),
                output_field=IntegerField()
            ) + Case(
                # Paystack subaccount = +50 points (easier payment)
                When(subaccount_active=True, then=Value(50)),
                default=Value(0),
                output_field=IntegerField()
            )
            # TODO: Add distance calculation when GPS fields are populated
            # TODO: Add quality score from past deliveries
            # TODO: Add on-time delivery percentage
        )
        
        # Filter farms with available inventory (using current_bird_count)
        farms = farms.filter(current_bird_count__gt=0)
        
        # Order by priority score, then inventory (using current_bird_count)
        farms = farms.order_by('-priority_score', '-current_bird_count')
        
        # Limit results
        farms = farms[:limit]
        
        # Calculate recommended quantity per farm
        total_available = sum(f.current_bird_count or 0 for f in farms)
        remaining_needed = order.quantity_needed - order.quantity_assigned
        
        recommended_farms = []
        for farm in farms:
            if remaining_needed <= 0:
                break
            
            # Recommend quantity: proportional to farm's inventory, but not more than needed
            farm_capacity = farm.current_bird_count or 0
            if total_available > 0:
                proportion = farm_capacity / total_available
                recommended_qty = min(
                    int(remaining_needed * proportion),
                    farm_capacity,
                    remaining_needed
                )
            else:
                recommended_qty = 0
            
            farm.recommended_quantity = recommended_qty
            recommended_farms.append({
                'farm': farm,
                'recommended_quantity': recommended_qty,
                'priority_score': farm.priority_score if hasattr(farm, 'priority_score') else 0
            })
            remaining_needed -= recommended_qty
        
        logger.info(f"Recommended {len(recommended_farms)} farms for order {order.order_number}")
        return recommended_farms
    
    @transaction.atomic
    def assign_to_farm(self, order, farm, quantity, price_per_unit=None):
        """
        Assign part of an order to a specific farm.
        
        Args:
            order: ProcurementOrder instance
            farm: Farm instance
            quantity: Quantity to assign
            price_per_unit: Optional custom price (defaults to order price)
        
        Returns:
            OrderAssignment instance
        """
        if order.status not in ['published', 'assigning', 'assigned']:
            raise ValueError(f"Cannot assign farms to order with status: {order.status}")
        
        if price_per_unit is None:
            price_per_unit = order.price_per_unit
        
        # Check if already assigned to this farm
        existing = OrderAssignment.objects.filter(order=order, farm=farm).first()
        if existing:
            raise ValueError(f"Farm {farm.farm_name} is already assigned to this order")
        
        # Create assignment
        assignment = OrderAssignment.objects.create(
            order=order,
            farm=farm,
            quantity_assigned=quantity,
            price_per_unit=price_per_unit,
            status='pending'
        )
        
        # Update order quantities
        order.quantity_assigned = (order.quantity_assigned or 0) + quantity
        if order.status == 'published':
            order.status = 'assigning'
        order.save()
        
        # Send SMS notification to farm about new assignment
        try:
            notification_service.notify_farm_assignment(assignment)
        except Exception as e:
            logger.warning(f"Failed to send assignment notification: {str(e)}")
        
        logger.info(f"Assigned {quantity} units to {farm.farm_name} for order {order.order_number}")
        return assignment
    
    @transaction.atomic
    def auto_assign_order(self, order):
        """
        Automatically assign order to recommended farms.
        
        Returns:
            List of OrderAssignment instances
        """
        if not order.auto_assign:
            raise ValueError("Auto-assign is disabled for this order")
        
        if order.status not in ['published', 'assigning']:
            raise ValueError(f"Cannot auto-assign order with status: {order.status}")
        
        recommended_farms = self.recommend_farms(order)
        assignments = []
        
        for rec in recommended_farms:
            farm = rec['farm']
            recommended_qty = rec['recommended_quantity']
            if recommended_qty > 0:
                try:
                    assignment = self.assign_to_farm(
                        order,
                        farm,
                        recommended_qty
                    )
                    assignments.append(assignment)
                except Exception as e:
                    logger.error(f"Failed to assign to {farm.farm_name}: {str(e)}")
                    continue
        
        # Update order status
        if assignments:
            order.status = 'assigned'
            order.assigned_at = timezone.now()
            order.save()
        
        logger.info(f"Auto-assigned order {order.order_number} to {len(assignments)} farms")
        return assignments
    
    @transaction.atomic
    def farm_accept_assignment(self, assignment, expected_ready_date=None):
        """
        Farm accepts an assignment.
        """
        if assignment.status != 'pending':
            raise ValueError(f"Cannot accept assignment with status: {assignment.status}")
        
        assignment.status = 'accepted'
        assignment.accepted_at = timezone.now()
        if expected_ready_date:
            assignment.expected_ready_date = expected_ready_date
        assignment.save()
        
        # Update order status if all assignments accepted
        order = assignment.order
        all_accepted = not order.assignments.filter(status='pending').exists()
        if all_accepted and order.status == 'assigned':
            order.status = 'in_progress'
            order.save()
        
        # Send SMS notification to procurement officer
        try:
            notification_service.notify_assignment_accepted(assignment)
        except Exception as e:
            logger.warning(f"Failed to send acceptance notification: {str(e)}")
        
        logger.info(f"Farm {assignment.farm.farm_name} accepted assignment {assignment.assignment_number}")
        return assignment
    
    @transaction.atomic
    def farm_reject_assignment(self, assignment, reason):
        """
        Farm rejects an assignment.
        """
        if assignment.status != 'pending':
            raise ValueError(f"Cannot reject assignment with status: {assignment.status}")
        
        assignment.status = 'rejected'
        assignment.rejected_at = timezone.now()
        assignment.rejection_reason = reason
        assignment.save()
        
        # Update order quantities
        order = assignment.order
        order.quantity_assigned -= assignment.quantity_assigned
        order.save()
        
        # Send SMS notification to procurement officer
        try:
            notification_service.notify_assignment_rejected(assignment, reason)
        except Exception as e:
            logger.warning(f"Failed to send rejection notification: {str(e)}")
        
        logger.info(f"Farm {assignment.farm.farm_name} rejected assignment {assignment.assignment_number}")
        return assignment
    
    @transaction.atomic
    def mark_ready_for_delivery(self, assignment, actual_ready_date=None):
        """
        Farm marks order as ready for delivery.
        """
        if assignment.status != 'preparing':
            assignment.status = 'preparing'
        
        assignment.status = 'ready'
        assignment.actual_ready_date = actual_ready_date or timezone.now().date()
        assignment.save()
        
        # Send SMS notification to procurement officer
        try:
            notification_service.notify_ready_for_delivery(assignment)
        except Exception as e:
            logger.warning(f"Failed to send ready notification: {str(e)}")
        
        logger.info(f"Assignment {assignment.assignment_number} marked as ready")
        return assignment
    
    @transaction.atomic
    def create_delivery(self, assignment, quantity_delivered, delivery_date, 
                       delivery_time, received_by, **delivery_data):
        """
        Create a delivery confirmation record.
        
        Args:
            assignment: OrderAssignment instance
            quantity_delivered: Quantity in this delivery
            delivery_date: Date of delivery
            delivery_time: Time of delivery
            received_by: User who received delivery
            **delivery_data: Additional delivery fields (quality inspection, etc.)
        
        Returns:
            DeliveryConfirmation instance
        """
        if assignment.status not in ['ready', 'in_transit', 'delivered']:
            assignment.status = 'in_transit'
            assignment.save()
        
        # Create delivery record
        delivery = DeliveryConfirmation.objects.create(
            assignment=assignment,
            quantity_delivered=quantity_delivered,
            delivery_date=delivery_date,
            delivery_time=delivery_time,
            received_by=received_by,
            **delivery_data
        )
        
        # Update assignment quantities
        assignment.quantity_delivered += quantity_delivered
        if assignment.quantity_delivered >= assignment.quantity_assigned:
            assignment.status = 'delivered'
            assignment.delivery_date = delivery_date
        assignment.save()
        
        # Update order quantities
        order = assignment.order
        order.quantity_delivered += quantity_delivered
        if order.quantity_delivered >= order.quantity_needed:
            order.status = 'fully_delivered'
        elif order.quantity_delivered > 0:
            order.status = 'partially_delivered'
        order.save()
        
        logger.info(f"Delivery created: {delivery.delivery_number} - {quantity_delivered} units")
        return delivery
    
    @transaction.atomic
    def verify_delivery(self, delivery, verified_by, quality_passed=True, 
                       average_weight=None, mortality_count=0, quality_issues=''):
        """
        Verify and quality-check a delivery.
        """
        delivery.verified_by = verified_by
        delivery.verified_at = timezone.now()
        delivery.quality_passed = quality_passed
        
        if average_weight:
            delivery.average_weight_per_bird = average_weight
        if mortality_count:
            delivery.mortality_count = mortality_count
        if quality_issues:
            delivery.quality_issues = quality_issues
        
        delivery.delivery_confirmed = True
        delivery.save()
        
        # Update assignment quality tracking
        assignment = delivery.assignment
        assignment.quality_passed = quality_passed
        
        # Calculate average weight across all deliveries
        all_deliveries = assignment.deliveries.filter(verified_at__isnull=False)
        if all_deliveries.exists():
            avg_weights = [d.average_weight_per_bird for d in all_deliveries 
                          if d.average_weight_per_bird]
            if avg_weights:
                assignment.average_weight_per_bird = sum(avg_weights) / len(avg_weights)
        
        assignment.verified_at = timezone.now()
        assignment.save()
        
        # Auto-generate invoice if fully delivered and verified
        if assignment.is_fully_delivered and assignment.status == 'delivered':
            assignment.status = 'verified'
            assignment.save()
            
            # Create invoice
            self.generate_invoice(assignment)
        
        logger.info(f"Delivery verified: {delivery.delivery_number} - Quality: {quality_passed}")
        return delivery
    
    @transaction.atomic
    def generate_invoice(self, assignment):
        """
        Generate invoice for a verified assignment.
        
        Returns:
            ProcurementInvoice instance
        """
        if assignment.status != 'verified':
            raise ValueError(f"Cannot generate invoice for assignment with status: {assignment.status}")
        
        # Check if invoice already exists
        if hasattr(assignment, 'invoice'):
            return assignment.invoice
        
        # Calculate deductions
        quality_deduction = Decimal('0.00')
        mortality_deduction = Decimal('0.00')
        
        # Quality deduction (if quality failed)
        if not assignment.quality_passed:
            # Example: 10% deduction for quality issues
            quality_deduction = assignment.total_value * Decimal('0.10')
        
        # Mortality deduction
        total_mortality = sum(
            d.mortality_count for d in assignment.deliveries.all()
        )
        if total_mortality > 0:
            mortality_deduction = Decimal(str(total_mortality)) * assignment.price_per_unit
        
        # Create invoice
        invoice = ProcurementInvoice.objects.create(
            assignment=assignment,
            farm=assignment.farm,
            order=assignment.order,
            quantity_invoiced=assignment.quantity_delivered,
            unit_price=assignment.price_per_unit,
            subtotal=assignment.total_value,
            quality_deduction=quality_deduction,
            mortality_deduction=mortality_deduction,
            other_deductions=Decimal('0.00'),
            due_date=timezone.now().date() + timedelta(days=30)  # 30 days payment term
        )
        
        logger.info(f"Invoice generated: {invoice.invoice_number} - GHS {invoice.total_amount}")
        return invoice
    
    @transaction.atomic
    def approve_invoice(self, invoice, approved_by):
        """
        Approve invoice for payment.
        """
        if invoice.payment_status != 'pending':
            raise ValueError(f"Cannot approve invoice with status: {invoice.payment_status}")
        
        invoice.payment_status = 'approved'
        invoice.approved_by = approved_by
        invoice.approved_at = timezone.now()
        invoice.save()
        
        # Send SMS notification to farmer about invoice
        try:
            notification_service.notify_invoice_generated(invoice)
        except Exception as e:
            logger.warning(f"Failed to send invoice notification: {str(e)}")
        
        logger.info(f"Invoice approved: {invoice.invoice_number}")
        return invoice
    
    @transaction.atomic
    def process_payment(self, invoice, payment_method, payment_reference, 
                       payment_date=None, paid_to_account=''):
        """
        Record payment for an invoice.
        """
        if invoice.payment_status not in ['approved', 'processing']:
            raise ValueError(f"Cannot process payment for invoice with status: {invoice.payment_status}")
        
        invoice.payment_status = 'paid'
        invoice.payment_method = payment_method
        invoice.payment_reference = payment_reference
        invoice.payment_date = payment_date or timezone.now().date()
        invoice.paid_to_account = paid_to_account
        invoice.save()
        
        # Update assignment status
        assignment = invoice.assignment
        assignment.status = 'paid'
        assignment.payment_processed_at = timezone.now()
        assignment.save()
        
        # Check if all assignments are paid
        order = invoice.order
        all_paid = not order.assignments.exclude(status='paid').exists()
        if all_paid:
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()
        
        # Send SMS payment confirmation to farmer
        try:
            notification_service.notify_payment_processed(invoice)
        except Exception as e:
            logger.warning(f"Failed to send payment notification: {str(e)}")
        
        logger.info(f"Payment processed: {invoice.invoice_number} - {payment_method}")
        return invoice
    
    @transaction.atomic
    def cancel_order(self, order, reason):
        """
        Cancel a procurement order.
        """
        if order.status in ['completed', 'cancelled']:
            raise ValueError(f"Cannot cancel order with status: {order.status}")
        
        # Cancel all pending assignments
        for assignment in order.assignments.filter(status__in=['pending', 'accepted']):
            assignment.status = 'cancelled'
            assignment.save()
        
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.cancellation_reason = reason
        order.save()
        
        # TODO: Send notifications to assigned farms
        # TODO: Release reserved inventory
        
        logger.info(f"Order cancelled: {order.order_number}")
        return order
    
    def get_order_summary(self, order):
        """
        Get comprehensive summary of order status.
        
        Returns:
            Dictionary with order statistics
        """
        assignments = order.assignments.all()
        
        return {
            'order_number': order.order_number,
            'status': order.status,
            'quantity_needed': order.quantity_needed,
            'quantity_assigned': order.quantity_assigned,
            'quantity_delivered': order.quantity_delivered,
            'fulfillment_percentage': order.fulfillment_percentage,
            'assignment_percentage': order.assignment_percentage,
            'days_until_deadline': order.days_until_deadline,
            'is_overdue': order.is_overdue,
            'total_farms_assigned': assignments.count(),
            'farms_accepted': assignments.filter(status='accepted').count(),
            'farms_preparing': assignments.filter(status='preparing').count(),
            'farms_delivered': assignments.filter(status='delivered').count(),
            'farms_paid': assignments.filter(status='paid').count(),
            'total_budget': order.total_budget,
            'total_cost_actual': order.total_cost_actual,
        }
