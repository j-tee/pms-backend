"""
Procurement Workflow Service

Manages government bulk orders:
- Farm recommendation algorithm
- Auto-assignment to farms
- Inventory reservation
- Delivery tracking
- Payment processing

ATOMICITY & IDEMPOTENCY:
- All mutating operations use @transaction.atomic
- Critical operations use select_for_update() to prevent race conditions
- Idempotency keys prevent duplicate operations on retry
- State machine validation ensures valid status transitions
- Audit logging provides full traceability
"""

from django.db import transaction, DatabaseError, OperationalError
from django.utils import timezone
from django.db.models import Q, Sum, F, Case, When, Value, IntegerField
from datetime import timedelta
from decimal import Decimal
import logging

from procurement.models import (
    ProcurementOrder, OrderAssignment, DeliveryConfirmation, ProcurementInvoice,
    IdempotencyKey, ProcurementAuditLog
)
from farms.models import Farm
from procurement.services.notification_service import get_notification_service
from procurement.services.idempotency import (
    idempotent_operation,
    validate_status_transition,
    StatusTransitionError,
    ORDER_STATUS_TRANSITIONS,
    ASSIGNMENT_STATUS_TRANSITIONS,
    INVOICE_STATUS_TRANSITIONS,
    DistributedLock,
    retry_on_failure,
    RetryableError,
)

logger = logging.getLogger(__name__)
notification_service = get_notification_service()


class ProcurementWorkflowService:
    """Service for managing procurement workflow with atomicity and idempotency guarantees."""
    
    @transaction.atomic
    def create_order(self, created_by, selected_farm_ids=None, **order_data):
        """
        Create a new procurement order with optional pre-selected farms.
        
        Atomicity: Wrapped in transaction.atomic
        Idempotency: Order number generation is sequential and unique
        
        Args:
            created_by: User creating the order
            selected_farm_ids: Optional list of farm IDs to auto-assign when published
                              These are farms selected from the distress recommendations.
            **order_data: Order fields
        
        Returns:
            dict with order instance and selected_farms info
        """
        # Store selected farms to assign after publishing
        pre_selected_farms = None
        if selected_farm_ids:
            # Validate that all farm IDs exist and are eligible
            pre_selected_farms = Farm.objects.filter(
                id__in=selected_farm_ids,
                farm_status='Active',
                application_status='Approved - Farm ID Assigned'
            )
            invalid_ids = set(str(id) for id in selected_farm_ids) - set(str(f.id) for f in pre_selected_farms)
            if invalid_ids:
                raise ValueError(f"Invalid or ineligible farm IDs: {invalid_ids}")
        
        order = ProcurementOrder.objects.create(
            created_by=created_by,
            status='draft',
            **order_data
        )
        
        # Audit log
        ProcurementAuditLog.log(
            operation='create_order',
            resource_type='ProcurementOrder',
            resource_id=order.id,
            user=created_by,
            new_state={
                'status': 'draft', 
                'order_number': order.order_number,
                'selected_farm_ids': selected_farm_ids if selected_farm_ids else []
            },
        )
        
        logger.info(f"Procurement order created: {order.order_number}")
        
        return {
            'order': order,
            'selected_farms': list(pre_selected_farms) if pre_selected_farms else [],
            'selected_farm_count': pre_selected_farms.count() if pre_selected_farms else 0,
        }
    
    @transaction.atomic
    def create_and_assign_order(self, created_by, selected_farm_ids, farm_quantities=None, idempotency_key=None, **order_data):
        """
        Create an order and immediately assign to selected farms.
        
        This is the full workflow when officer selects farms from distress recommendations:
        1. Create order
        2. Publish order
        3. Assign to selected farms (auto-distribute quantities if not specified)
        
        ATOMICITY: Entire operation is wrapped in transaction.atomic.
                  If any assignment fails, ALL changes are rolled back.
        
        IDEMPOTENCY: If idempotency_key provided, returns cached result on retry.
                    Otherwise generates key from order params + farm IDs.
        
        Args:
            created_by: User creating the order
            selected_farm_ids: List of farm IDs from distress recommendations
            farm_quantities: Optional dict {farm_id: quantity} for custom distribution.
                            If None, quantity is distributed proportionally.
            idempotency_key: Optional key for retry protection
            **order_data: Order fields
        
        Returns:
            dict with order and assignments info
        """
        # Generate idempotency key if not provided
        if idempotency_key is None:
            key_data = {
                'user_id': str(created_by.id) if created_by else 'anonymous',
                'operation': 'create_and_assign_order',
                'farm_ids': ','.join(sorted(str(fid) for fid in selected_farm_ids)),
                'product_type': order_data.get('product_type', ''),
                'quantity_needed': str(order_data.get('quantity_needed', 0)),
            }
            idempotency_key = IdempotencyKey.generate_key(**key_data)
        
        # Check for existing completed operation (idempotency)
        try:
            existing = IdempotencyKey.objects.get(
                key=idempotency_key,
                operation='create_and_assign_order',
                status='completed',
                expires_at__gt=timezone.now()
            )
            if existing.response_data:
                logger.info(f"Idempotent return for create_and_assign_order: {idempotency_key[:16]}...")
                # Return cached result - need to fetch actual objects
                cached = existing.response_data
                order = ProcurementOrder.objects.get(id=cached.get('order_id'))
                assignments = list(OrderAssignment.objects.filter(order=order))
                return {
                    'order': order,
                    'assignments': assignments,
                    'assignment_count': len(assignments),
                    'total_assigned': order.quantity_assigned,
                    'remaining': order.quantity_needed - order.quantity_assigned,
                    'idempotent': True,
                }
        except IdempotencyKey.DoesNotExist:
            pass
        
        # Create idempotency record to mark operation as in-progress
        idem_record = IdempotencyKey.objects.create(
            key=idempotency_key,
            user_id=created_by.id if created_by else None,
            operation='create_and_assign_order',
            resource_type='ProcurementOrder',
            status='processing',
            expires_at=timezone.now() + timedelta(hours=24),
        )
        
        # Collect assignments for deferred notifications
        pending_notifications = []
        
        try:
            # Create the order
            result = self.create_order(created_by, selected_farm_ids=selected_farm_ids, **order_data)
            order = result['order']
            selected_farms = result['selected_farms']
            
            if not selected_farms:
                raise ValueError("At least one valid farm must be selected")
            
            # Publish the order
            order = self.publish_order(order, user=created_by)
            
            # Calculate quantities for each farm
            total_needed = order.quantity_needed
            assignments = []
            
            if farm_quantities:
                # Use specified quantities
                for farm in selected_farms:
                    qty = farm_quantities.get(str(farm.id), 0)
                    if qty > 0:
                        assignment = self._assign_to_farm_no_notify(
                            order, farm, qty,
                            user=created_by
                        )
                        assignments.append(assignment)
                        pending_notifications.append(assignment)
            else:
                # SOCIAL WELFARE DISTRIBUTION:
                # Prioritize farms by distress score (highest distress = most urgent need for sales)
                # Distribute order quantities starting from most distressed farms
                from procurement.services.farmer_distress_v2 import get_distress_service
                service = get_distress_service()
                
                # Get distress scores and available stock for each farm
                farm_assessments = []
                for farm in selected_farms:
                    assessment = service.calculate_distress_score(farm, include_full_details=False)
                    inventory = assessment.get('inventory', {})
                    capacity = assessment.get('capacity', {})
                    
                    # Get available quantity based on order type (eggs vs birds)
                    if order.unit in ['crates', 'eggs', 'trays']:
                        available = inventory.get('total_eggs_available', 0) or 0
                    else:
                        available = inventory.get('total_birds_available', 0) or capacity.get('available_for_sale', 0) or farm.current_bird_count or 0
                    
                    farm_assessments.append({
                        'farm': farm,
                        'distress_score': assessment['distress_score'],
                        'distress_level': assessment['distress_level'],
                        'available': available,
                        'days_without_sales': assessment.get('days_without_sales'),
                    })
                
                # Sort by distress score (highest first) - most distressed farmers get priority
                farm_assessments.sort(key=lambda x: x['distress_score'], reverse=True)
                
                # Distribute to farms starting from most distressed
                # Each farm gets assigned what they can supply, until order is filled
                remaining = total_needed
                total_available = sum(fa['available'] for fa in farm_assessments)
                
                # Check if total supply meets demand
                if total_available < total_needed:
                    logger.warning(
                        f"Selected farms can only supply {total_available} of {total_needed} needed. "
                        f"Order will be partially assigned."
                    )
                
                for fa in farm_assessments:
                    if remaining <= 0:
                        break
                    
                    # Assign what this farm can supply, up to what's still needed
                    qty = min(fa['available'], remaining)
                    
                    if qty > 0:
                        assignment = self._assign_to_farm_no_notify(
                            order, fa['farm'], qty,
                            user=created_by
                        )
                        assignments.append(assignment)
                        pending_notifications.append(assignment)
                        remaining -= qty
                        
                        logger.info(
                            f"Assigned {qty} to {fa['farm'].farm_name} "
                            f"(distress: {fa['distress_level']}, score: {fa['distress_score']})"
                        )
            
            # Refresh order to get updated quantities
            order.refresh_from_db()
            
            # Mark idempotency record as completed
            idem_record.status = 'completed'
            idem_record.resource_id = str(order.id)
            idem_record.response_data = {
                'order_id': str(order.id),
                'assignment_count': len(assignments),
                'total_assigned': order.quantity_assigned,
            }
            idem_record.completed_at = timezone.now()
            idem_record.save()
            
            result = {
                'order': order,
                'assignments': assignments,
                'assignment_count': len(assignments),
                'total_assigned': order.quantity_assigned,
                'remaining': order.quantity_needed - order.quantity_assigned,
            }
            
            # Register post-commit callback for notifications
            # This ensures SMS is only sent AFTER the transaction commits successfully
            from django.db import connection
            connection.on_commit(lambda: self._send_deferred_notifications(pending_notifications))
            
            return result
            
        except Exception as e:
            # Mark idempotency record as failed
            idem_record.status = 'failed'
            idem_record.response_data = {'error': str(e)}
            idem_record.completed_at = timezone.now()
            idem_record.save()
            raise
    
    def _assign_to_farm_no_notify(self, order, farm, quantity, price_per_unit=None, user=None):
        """
        Internal assignment method that skips SMS notification.
        Used by batch operations that send notifications after commit.
        
        This is a lighter version of assign_to_farm() for use within
        already-locked transactions.
        """
        if price_per_unit is None:
            price_per_unit = order.price_per_unit
        
        # IDEMPOTENCY: Check if already assigned to this farm
        existing = OrderAssignment.objects.filter(order=order, farm=farm).first()
        if existing:
            if existing.quantity_assigned == quantity:
                logger.info(f"Idempotent: Farm {farm.farm_name} already assigned to order")
                return existing
            raise ValueError(f"Farm {farm.farm_name} is already assigned to this order with different quantity")
        
        # Check quantity doesn't exceed remaining need
        remaining = order.quantity_needed - order.quantity_assigned
        if quantity > remaining:
            raise ValueError(
                f"Cannot assign {quantity} units. Only {remaining} units remaining."
            )
        
        # Create assignment
        assignment = OrderAssignment.objects.create(
            order=order,
            farm=farm,
            quantity_assigned=quantity,
            price_per_unit=price_per_unit,
            status='pending'
        )
        
        # Update order quantities atomically
        order.quantity_assigned = F('quantity_assigned') + quantity
        if order.status == 'published':
            order.status = 'assigning'
        order.save(update_fields=['quantity_assigned', 'status', 'updated_at'])
        
        # Refresh to get updated value
        order.refresh_from_db()
        
        # Audit log
        ProcurementAuditLog.log(
            operation='assign_to_farm',
            resource_type='OrderAssignment',
            resource_id=assignment.id,
            user=user,
            new_state={
                'order': str(order.id),
                'farm': str(farm.id),
                'quantity': quantity,
                'status': 'pending'
            },
        )
        
        logger.info(f"Assigned {quantity} units to {farm.farm_name} for order {order.order_number}")
        return assignment
    
    def _send_deferred_notifications(self, assignments):
        """Send SMS notifications for completed assignments."""
        for assignment in assignments:
            try:
                notification_service.notify_farm_assignment(assignment)
            except Exception as e:
                logger.warning(f"Failed to send assignment notification: {str(e)}")
    
    @transaction.atomic
    def publish_order(self, order, user=None):
        """
        Publish order - make it visible for farm assignments.
        
        Atomicity: Uses select_for_update to lock the order row
        State Validation: Validates draft -> published transition
        """
        # Lock the order row to prevent concurrent modifications
        order = ProcurementOrder.objects.select_for_update().get(pk=order.pk)
        
        # Validate state transition
        validate_status_transition(
            order.status, 'published', 
            ORDER_STATUS_TRANSITIONS, 'order'
        )
        
        previous_status = order.status
        order.status = 'published'
        order.published_at = timezone.now()
        order.save()
        
        # Audit log
        ProcurementAuditLog.log(
            operation='publish_order',
            resource_type='ProcurementOrder',
            resource_id=order.id,
            user=user,
            previous_state={'status': previous_status},
            new_state={'status': 'published'},
            changes={'status': {'from': previous_status, 'to': 'published'}},
        )
        
        logger.info(f"Order published: {order.order_number}")
        return order
    
    def recommend_farms(self, order, limit=None, prioritize_distress=True):
        """
        Recommend farms for an order based on:
        
        PRIMARY (Social Welfare - prioritize_distress=True):
        1. Farmer distress score (struggling farmers first)
        2. Current inventory/capacity
        3. Production type match
        
        SECONDARY:
        4. Distance from delivery location (if GPS available)
        5. Farm approval status
        6. Past performance (quality, on-time delivery)
        7. Business registration
        
        The primary goal is to help struggling farmers by purchasing 
        from them first, before moving to less distressed farmers.
        
        Args:
            order: ProcurementOrder instance
            limit: Maximum number of farms to return
            prioritize_distress: If True, sort by distress score (default)
        
        Returns:
            List of dicts with farm, recommended_quantity, distress info
        """
        if limit is None:
            limit = order.max_farms
        
        # Use distress-based prioritization if enabled
        if prioritize_distress:
            from procurement.services.farmer_distress import get_distress_service
            service = get_distress_service(days_lookback=30)
            return service.get_farms_for_procurement_priority(order, limit=limit)
        
        # Legacy recommendation logic (fallback)
        return self._legacy_recommend_farms(order, limit)
    
    def _legacy_recommend_farms(self, order, limit):
        """
        Legacy farm recommendation based on business metrics.
        Used when prioritize_distress=False.
        """
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
            
            recommended_farms.append({
                'farm': farm,
                'recommended_quantity': recommended_qty,
                'priority_score': farm.priority_score if hasattr(farm, 'priority_score') else 0,
                'distress_score': None,  # Not calculated in legacy mode
                'distress_level': 'unknown',
            })
            remaining_needed -= recommended_qty
        
        logger.info(f"Recommended {len(recommended_farms)} farms for order {order.order_number}")
        return recommended_farms
    
    @transaction.atomic
    def assign_to_farm(self, order, farm, quantity, price_per_unit=None, user=None, idempotency_key=None):
        """
        Assign part of an order to a specific farm.
        
        Atomicity: Uses select_for_update on both order and farm
        Idempotency: Checks for existing assignment before creating
        Concurrency: Uses distributed lock for the order
        
        Args:
            order: ProcurementOrder instance
            farm: Farm instance
            quantity: Quantity to assign
            price_per_unit: Optional custom price (defaults to order price)
            user: User performing the assignment
            idempotency_key: Optional key for idempotent retries
        
        Returns:
            OrderAssignment instance
        """
        # Use distributed lock to prevent race conditions across multiple requests
        with DistributedLock(f"order:{order.id}:assign", ttl_seconds=30):
            # Lock and refresh the order
            order = ProcurementOrder.objects.select_for_update().get(pk=order.pk)
            
            # Validate order status
            if order.status not in ['published', 'assigning', 'assigned']:
                raise StatusTransitionError(
                    f"Cannot assign farms to order with status: {order.status}"
                )
            
            if price_per_unit is None:
                price_per_unit = order.price_per_unit
            
            # IDEMPOTENCY: Check if already assigned to this farm
            existing = OrderAssignment.objects.filter(order=order, farm=farm).first()
            if existing:
                # If idempotency_key matches or same quantity, return existing
                if existing.quantity_assigned == quantity:
                    logger.info(f"Idempotent: Farm {farm.farm_name} already assigned to order")
                    return existing
                raise ValueError(f"Farm {farm.farm_name} is already assigned to this order with different quantity")
            
            # Check quantity doesn't exceed remaining need
            remaining = order.quantity_needed - order.quantity_assigned
            if quantity > remaining:
                raise ValueError(
                    f"Cannot assign {quantity} units. Only {remaining} units remaining."
                )
            
            # Create assignment
            assignment = OrderAssignment.objects.create(
                order=order,
                farm=farm,
                quantity_assigned=quantity,
                price_per_unit=price_per_unit,
                status='pending'
            )
            
            # Update order quantities atomically
            previous_status = order.status
            order.quantity_assigned = F('quantity_assigned') + quantity
            if order.status == 'published':
                order.status = 'assigning'
            order.save(update_fields=['quantity_assigned', 'status', 'updated_at'])
            
            # Refresh to get updated value
            order.refresh_from_db()
        
        # Audit log (outside the lock)
        ProcurementAuditLog.log(
            operation='assign_to_farm',
            resource_type='OrderAssignment',
            resource_id=assignment.id,
            user=user,
            new_state={
                'order': str(order.id),
                'farm': str(farm.id),
                'quantity': quantity,
                'status': 'pending'
            },
            idempotency_key=idempotency_key,
        )
        
        # Send SMS notification AFTER transaction commits successfully
        # This prevents sending notifications for rolled-back assignments
        from django.db import connection
        assignment_for_notification = assignment  # Capture reference
        connection.on_commit(
            lambda: self._notify_single_assignment(assignment_for_notification)
        )
        
        logger.info(f"Assigned {quantity} units to {farm.farm_name} for order {order.order_number}")
        return assignment
    
    def _notify_single_assignment(self, assignment):
        """Send SMS notification for a single assignment."""
        try:
            notification_service.notify_farm_assignment(assignment)
        except Exception as e:
            logger.warning(f"Failed to send assignment notification: {str(e)}")
    
    @transaction.atomic
    def auto_assign_order(self, order, user=None):
        """
        Automatically assign order to recommended farms.
        
        Atomicity: Uses distributed lock to prevent concurrent auto-assignments
        
        Returns:
            List of OrderAssignment instances
        """
        # Use distributed lock to prevent concurrent auto-assignments
        with DistributedLock(f"order:{order.id}:auto_assign", ttl_seconds=120):
            # Refresh and lock order
            order = ProcurementOrder.objects.select_for_update().get(pk=order.pk)
            
            if not order.auto_assign:
                raise ValueError("Auto-assign is disabled for this order")
            
            if order.status not in ['published', 'assigning']:
                raise ValueError(f"Cannot auto-assign order with status: {order.status}")
            
            # Mark as assigning to prevent duplicate runs
            if order.status == 'published':
                order.status = 'assigning'
                order.save(update_fields=['status', 'updated_at'])
            
            recommended_farms = self.recommend_farms(order)
            assignments = []
            failed_assignments = []
            
            for rec in recommended_farms:
                farm = rec['farm']
                recommended_qty = rec['recommended_quantity']
                if recommended_qty > 0:
                    try:
                        assignment = self.assign_to_farm(
                            order,
                            farm,
                            recommended_qty,
                            user=user
                        )
                        assignments.append(assignment)
                    except Exception as e:
                        logger.error(f"Failed to assign to {farm.farm_name}: {str(e)}")
                        failed_assignments.append({
                            'farm': farm.farm_name,
                            'error': str(e)
                        })
                        continue
            
            # Update order status
            order.refresh_from_db()
            if assignments and order.quantity_assigned >= order.quantity_needed:
                order.status = 'assigned'
                order.assigned_at = timezone.now()
                order.save(update_fields=['status', 'assigned_at', 'updated_at'])
            elif assignments:
                # Partially assigned, keep status as 'assigning' for manual completion
                pass
            
            # Audit log
            ProcurementAuditLog.log(
                operation='auto_assign_order',
                resource_type='ProcurementOrder',
                resource_id=order.id,
                user=user,
                previous_state={'status': 'published'},
                new_state={
                    'status': order.status,
                    'assignments_created': len(assignments),
                    'failed_assignments': failed_assignments,
                },
            )
        
        logger.info(f"Auto-assigned order {order.order_number} to {len(assignments)} farms")
        return assignments
    
    @transaction.atomic
    def farm_accept_assignment(self, assignment, expected_ready_date=None, user=None):
        """
        Farm accepts an assignment.
        
        Atomicity: Uses select_for_update on assignment
        State Validation: Validates pending -> accepted transition
        """
        # Lock the assignment
        assignment = OrderAssignment.objects.select_for_update().get(pk=assignment.pk)
        
        # Validate state transition
        validate_status_transition(
            assignment.status, 'accepted',
            ASSIGNMENT_STATUS_TRANSITIONS, 'assignment'
        )
        
        previous_status = assignment.status
        assignment.status = 'accepted'
        assignment.accepted_at = timezone.now()
        if expected_ready_date:
            assignment.expected_ready_date = expected_ready_date
        assignment.save()
        
        # Update order status if all assignments accepted
        order = ProcurementOrder.objects.select_for_update().get(pk=assignment.order_id)
        all_accepted = not order.assignments.filter(status='pending').exists()
        if all_accepted and order.status == 'assigned':
            validate_status_transition(order.status, 'in_progress', ORDER_STATUS_TRANSITIONS, 'order')
            order.status = 'in_progress'
            order.save()
        
        # Audit log
        ProcurementAuditLog.log(
            operation='accept_assignment',
            resource_type='OrderAssignment',
            resource_id=assignment.id,
            user=user,
            previous_state={'status': previous_status},
            new_state={'status': 'accepted'},
        )
        
        # Send SMS notification to procurement officer
        try:
            notification_service.notify_assignment_accepted(assignment)
        except Exception as e:
            logger.warning(f"Failed to send acceptance notification: {str(e)}")
        
        logger.info(f"Farm {assignment.farm.farm_name} accepted assignment {assignment.assignment_number}")
        return assignment
    
    @transaction.atomic
    def farm_reject_assignment(self, assignment, reason, user=None):
        """
        Farm rejects an assignment.
        
        Atomicity: Uses select_for_update on both assignment and order
        State Validation: Validates pending -> rejected transition
        """
        # Lock the assignment
        assignment = OrderAssignment.objects.select_for_update().get(pk=assignment.pk)
        
        # Validate state transition
        validate_status_transition(
            assignment.status, 'rejected',
            ASSIGNMENT_STATUS_TRANSITIONS, 'assignment'
        )
        
        previous_status = assignment.status
        quantity = assignment.quantity_assigned
        
        assignment.status = 'rejected'
        assignment.rejected_at = timezone.now()
        assignment.rejection_reason = reason
        assignment.save()
        
        # Update order quantities atomically
        order = ProcurementOrder.objects.select_for_update().get(pk=assignment.order_id)
        order.quantity_assigned = F('quantity_assigned') - quantity
        order.save(update_fields=['quantity_assigned', 'updated_at'])
        order.refresh_from_db()
        
        # Audit log
        ProcurementAuditLog.log(
            operation='reject_assignment',
            resource_type='OrderAssignment',
            resource_id=assignment.id,
            user=user,
            previous_state={'status': previous_status},
            new_state={'status': 'rejected', 'reason': reason},
        )
        
        # Send SMS notification to procurement officer
        try:
            notification_service.notify_assignment_rejected(assignment, reason)
        except Exception as e:
            logger.warning(f"Failed to send rejection notification: {str(e)}")
        
        logger.info(f"Farm {assignment.farm.farm_name} rejected assignment {assignment.assignment_number}")
        return assignment
    
    @transaction.atomic
    def mark_ready_for_delivery(self, assignment, actual_ready_date=None, user=None):
        """
        Farm marks order as ready for delivery.
        
        Atomicity: Uses select_for_update on assignment
        State Validation: Validates transition to ready status
        """
        # Lock the assignment
        assignment = OrderAssignment.objects.select_for_update().get(pk=assignment.pk)
        
        previous_status = assignment.status
        
        # Allow transition from accepted/preparing to ready
        if assignment.status not in ['accepted', 'preparing', 'ready']:
            raise ValueError(f"Cannot mark ready from status: {assignment.status}")
        
        assignment.status = 'ready'
        assignment.actual_ready_date = actual_ready_date or timezone.now().date()
        assignment.save()
        
        # Audit log
        ProcurementAuditLog.log(
            operation='mark_ready',
            resource_type='OrderAssignment',
            resource_id=assignment.id,
            user=user,
            previous_state={'status': previous_status},
            new_state={'status': 'ready'},
        )
        
        # Send SMS notification to procurement officer
        try:
            notification_service.notify_ready_for_delivery(assignment)
        except Exception as e:
            logger.warning(f"Failed to send ready notification: {str(e)}")
        
        logger.info(f"Assignment {assignment.assignment_number} marked as ready")
        return assignment
    
    @transaction.atomic
    def create_delivery(self, assignment, quantity_delivered, delivery_date, 
                       delivery_time, received_by, idempotency_key=None, **delivery_data):
        """
        Create a delivery confirmation record.
        
        Atomicity: Uses select_for_update on assignment and order
        Idempotency: Uses idempotency_key to prevent duplicate deliveries
        
        Args:
            assignment: OrderAssignment instance
            quantity_delivered: Quantity in this delivery
            delivery_date: Date of delivery
            delivery_time: Time of delivery
            received_by: User who received delivery
            idempotency_key: Optional key for idempotent operation
            **delivery_data: Additional delivery fields (quality inspection, etc.)
        
        Returns:
            DeliveryConfirmation instance
        """
        # Use distributed lock for delivery creation
        with DistributedLock(f"assignment:{assignment.id}:delivery", ttl_seconds=30):
            # Check idempotency
            if idempotency_key:
                existing = IdempotencyKey.get_if_exists(idempotency_key)
                if existing:
                    logger.info(f"Duplicate delivery request (idempotency_key={idempotency_key})")
                    return DeliveryConfirmation.objects.get(pk=existing.get('delivery_id'))
            
            # Lock the assignment
            assignment = OrderAssignment.objects.select_for_update().get(pk=assignment.pk)
            
            # Validate status
            if assignment.status not in ['accepted', 'preparing', 'ready', 'in_transit', 'delivered']:
                raise ValueError(f"Cannot create delivery for assignment with status: {assignment.status}")
            
            previous_status = assignment.status
            if assignment.status in ['accepted', 'preparing', 'ready']:
                assignment.status = 'in_transit'
            
            # Create delivery record
            delivery = DeliveryConfirmation.objects.create(
                assignment=assignment,
                quantity_delivered=quantity_delivered,
                delivery_date=delivery_date,
                delivery_time=delivery_time,
                received_by=received_by,
                **delivery_data
            )
            
            # Update assignment quantities atomically
            assignment.quantity_delivered = F('quantity_delivered') + quantity_delivered
            assignment.save(update_fields=['quantity_delivered', 'status', 'updated_at'])
            assignment.refresh_from_db()
            
            if assignment.quantity_delivered >= assignment.quantity_assigned:
                assignment.status = 'delivered'
                assignment.delivery_date = delivery_date
                assignment.save(update_fields=['status', 'delivery_date', 'updated_at'])
            
            # Update order quantities atomically
            order = ProcurementOrder.objects.select_for_update().get(pk=assignment.order_id)
            order.quantity_delivered = F('quantity_delivered') + quantity_delivered
            order.save(update_fields=['quantity_delivered', 'updated_at'])
            order.refresh_from_db()
            
            # Update order status based on delivery progress
            if order.quantity_delivered >= order.quantity_needed:
                validate_status_transition(order.status, 'fully_delivered', ORDER_STATUS_TRANSITIONS, 'order')
                order.status = 'fully_delivered'
            elif order.quantity_delivered > 0 and order.status not in ['partially_delivered', 'fully_delivered']:
                order.status = 'partially_delivered'
            order.save(update_fields=['status', 'updated_at'])
            
            # Store idempotency key
            if idempotency_key:
                IdempotencyKey.store(
                    idempotency_key, 
                    {'delivery_id': str(delivery.id)}, 
                    ttl_hours=24
                )
            
            # Audit log
            ProcurementAuditLog.log(
                operation='create_delivery',
                resource_type='DeliveryConfirmation',
                resource_id=delivery.id,
                user=received_by,
                previous_state={'assignment_status': previous_status},
                new_state={
                    'delivery_id': str(delivery.id),
                    'quantity': quantity_delivered,
                    'assignment_status': assignment.status
                },
                idempotency_key=idempotency_key,
            )
        
        logger.info(f"Delivery created: {delivery.delivery_number} - {quantity_delivered} units")
        return delivery
    
    @transaction.atomic
    def verify_delivery(self, delivery, verified_by, quality_passed=True, 
                       average_weight=None, mortality_count=0, quality_issues=''):
        """
        Verify and quality-check a delivery.
        
        Atomicity: Uses select_for_update on delivery and assignment
        """
        # Lock the delivery
        delivery = DeliveryConfirmation.objects.select_for_update().get(pk=delivery.pk)
        
        # Prevent duplicate verification
        if delivery.verified_at is not None:
            logger.warning(f"Delivery {delivery.delivery_number} already verified")
            return delivery
        
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
        
        # Lock and update assignment quality tracking
        assignment = OrderAssignment.objects.select_for_update().get(pk=delivery.assignment_id)
        previous_status = assignment.status
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
            validate_status_transition(assignment.status, 'verified', ASSIGNMENT_STATUS_TRANSITIONS, 'assignment')
            assignment.status = 'verified'
            assignment.save()
            
            # Create invoice
            self.generate_invoice(assignment, user=verified_by)
        
        # Audit log
        ProcurementAuditLog.log(
            operation='verify_delivery',
            resource_type='DeliveryConfirmation',
            resource_id=delivery.id,
            user=verified_by,
            previous_state={'assignment_status': previous_status, 'verified': False},
            new_state={'quality_passed': quality_passed, 'verified': True},
        )
        
        logger.info(f"Delivery verified: {delivery.delivery_number} - Quality: {quality_passed}")
        return delivery
    
    @transaction.atomic
    def generate_invoice(self, assignment, user=None):
        """
        Generate invoice for a verified assignment.
        
        Atomicity: Uses select_for_update on assignment
        Idempotency: Checks for existing invoice before creating
        
        Returns:
            ProcurementInvoice instance
        """
        # Lock the assignment
        assignment = OrderAssignment.objects.select_for_update().get(pk=assignment.pk)
        
        # Validate state
        if assignment.status != 'verified':
            raise ValueError(f"Cannot generate invoice for assignment with status: {assignment.status}")
        
        # Check if invoice already exists (idempotent)
        if hasattr(assignment, 'invoice') and assignment.invoice:
            logger.info(f"Invoice already exists for assignment {assignment.assignment_number}")
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
        
        # Audit log
        ProcurementAuditLog.log(
            operation='generate_invoice',
            resource_type='ProcurementInvoice',
            resource_id=invoice.id,
            user=user,
            previous_state={},
            new_state={
                'invoice_number': invoice.invoice_number,
                'subtotal': str(invoice.subtotal),
                'total_amount': str(invoice.total_amount),
                'payment_status': 'pending'
            },
        )
        
        logger.info(f"Invoice generated: {invoice.invoice_number} - GHS {invoice.total_amount}")
        return invoice
    
    @transaction.atomic
    def approve_invoice(self, invoice, approved_by):
        """
        Approve invoice for payment.
        
        Atomicity: Uses select_for_update on invoice
        State Validation: Validates pending -> approved transition
        Separation of Duties: Enforced via ProcurementPolicy
        """
        # Lock the invoice
        invoice = ProcurementInvoice.objects.select_for_update().get(pk=invoice.pk)
        
        # Validate state transition
        validate_status_transition(
            invoice.payment_status, 'approved',
            INVOICE_STATUS_TRANSITIONS, 'invoice'
        )
        
        previous_status = invoice.payment_status
        invoice.payment_status = 'approved'
        invoice.approved_by = approved_by
        invoice.approved_at = timezone.now()
        invoice.save()
        
        # Audit log - critical for financial accountability
        ProcurementAuditLog.log(
            operation='approve_invoice',
            resource_type='ProcurementInvoice',
            resource_id=invoice.id,
            user=approved_by,
            previous_state={'payment_status': previous_status},
            new_state={'payment_status': 'approved'},
        )
        
        # Send SMS notification to farmer about invoice
        try:
            notification_service.notify_invoice_generated(invoice)
        except Exception as e:
            logger.warning(f"Failed to send invoice notification: {str(e)}")
        
        logger.info(f"Invoice approved: {invoice.invoice_number} by {approved_by.get_full_name()}")
        return invoice
    
    @transaction.atomic
    def process_payment(self, invoice, payment_method, payment_reference, 
                       payment_date=None, paid_to_account='', processed_by=None):
        """
        Record payment for an invoice.
        
        Atomicity: Uses select_for_update on invoice, assignment, and order
        State Validation: Validates approved -> paid transition
        Separation of Duties: Enforced via ProcurementPolicy
        Idempotency: Payment reference serves as natural idempotency key
        """
        # Use distributed lock for payment processing
        with DistributedLock(f"invoice:{invoice.id}:payment", ttl_seconds=60):
            # Lock the invoice
            invoice = ProcurementInvoice.objects.select_for_update().get(pk=invoice.pk)
            
            # Check for duplicate payment (idempotent)
            if invoice.payment_status == 'paid':
                if invoice.payment_reference == payment_reference:
                    logger.info(f"Duplicate payment request for {invoice.invoice_number}")
                    return invoice
                raise ValueError("Invoice already paid with different reference")
            
            # Validate state transition
            validate_status_transition(
                invoice.payment_status, 'paid',
                INVOICE_STATUS_TRANSITIONS, 'invoice'
            )
            
            previous_status = invoice.payment_status
            invoice.payment_status = 'paid'
            invoice.payment_method = payment_method
            invoice.payment_reference = payment_reference
            invoice.payment_date = payment_date or timezone.now().date()
            invoice.paid_to_account = paid_to_account
            invoice.save()
            
            # Lock and update assignment status
            assignment = OrderAssignment.objects.select_for_update().get(pk=invoice.assignment_id)
            validate_status_transition(assignment.status, 'paid', ASSIGNMENT_STATUS_TRANSITIONS, 'assignment')
            assignment.status = 'paid'
            assignment.payment_processed_at = timezone.now()
            assignment.save()
            
            # Lock and check if all assignments are paid
            order = ProcurementOrder.objects.select_for_update().get(pk=invoice.order_id)
            all_paid = not order.assignments.exclude(status='paid').exclude(status='cancelled').exists()
            if all_paid:
                validate_status_transition(order.status, 'completed', ORDER_STATUS_TRANSITIONS, 'order')
                order.status = 'completed'
                order.completed_at = timezone.now()
                order.save()
            
            # Audit log - critical for financial accountability
            ProcurementAuditLog.log(
                operation='process_payment',
                resource_type='ProcurementInvoice',
                resource_id=invoice.id,
                user=processed_by,
                previous_state={'payment_status': previous_status},
                new_state={
                    'payment_status': 'paid',
                    'payment_method': payment_method,
                    'payment_reference': payment_reference,
                    'total_amount': str(invoice.total_amount),
                },
            )
        
        # Send SMS payment confirmation to farmer (outside transaction)
        try:
            notification_service.notify_payment_processed(invoice)
        except Exception as e:
            logger.warning(f"Failed to send payment notification: {str(e)}")
        
        logger.info(f"Payment processed: {invoice.invoice_number} - {payment_method} - {payment_reference}")
        return invoice
    
    @transaction.atomic
    def cancel_order(self, order, reason, cancelled_by=None):
        """
        Cancel a procurement order.
        
        Atomicity: Uses select_for_update on order and all assignments
        State Validation: Validates transition to cancelled status
        """
        # Lock the order
        order = ProcurementOrder.objects.select_for_update().get(pk=order.pk)
        
        # Validate state
        if order.status in ['completed', 'cancelled']:
            raise ValueError(f"Cannot cancel order with status: {order.status}")
        
        previous_status = order.status
        cancelled_assignments = []
        
        # Lock and cancel all pending/accepted assignments
        for assignment in order.assignments.select_for_update().filter(
            status__in=['pending', 'accepted', 'preparing']
        ):
            prev_assignment_status = assignment.status
            assignment.status = 'cancelled'
            assignment.save()
            cancelled_assignments.append({
                'assignment_number': assignment.assignment_number,
                'farm': assignment.farm.farm_name,
                'previous_status': prev_assignment_status
            })
        
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.cancellation_reason = reason
        order.save()
        
        # Audit log
        ProcurementAuditLog.log(
            operation='cancel_order',
            resource_type='ProcurementOrder',
            resource_id=order.id,
            user=cancelled_by,
            previous_state={'status': previous_status},
            new_state={
                'status': 'cancelled',
                'reason': reason,
                'cancelled_assignments': cancelled_assignments
            },
        )
        
        # TODO: Send notifications to assigned farms
        # TODO: Release reserved inventory
        
        logger.info(f"Order cancelled: {order.order_number} - {len(cancelled_assignments)} assignments cancelled")
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
