"""
Procurement Officer Dashboard Service

Provides officer-specific metrics and workflow management:
- My assigned orders
- Pending approvals
- SLA tracking
- Delivery monitoring
"""

from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from procurement.models import ProcurementOrder, OrderAssignment, DeliveryConfirmation, ProcurementInvoice


class OfficerDashboardService:
    """Service for procurement officer dashboard data"""
    
    def __init__(self, user):
        self.user = user
    
    def get_overview_stats(self):
        """
        Get officer-specific overview statistics.
        
        Returns:
            dict: Overview metrics for the officer
        """
        now = timezone.now()
        
        # My orders
        my_orders = ProcurementOrder.objects.filter(
            Q(created_by=self.user) | Q(assigned_procurement_officer=self.user)
        )
        
        total_orders = my_orders.count()
        active_orders = my_orders.filter(
            status__in=['published', 'assigning', 'assigned', 'in_progress']
        ).count()
        draft_orders = my_orders.filter(status='draft').count()
        completed_orders = my_orders.filter(status='completed').count()
        
        # Pending actions
        pending_deliveries = OrderAssignment.objects.filter(
            order__in=my_orders,
            status='ready'
        ).count()
        
        pending_verifications = DeliveryConfirmation.objects.filter(
            assignment__order__in=my_orders,
            verified_at__isnull=True
        ).count()
        
        # Budget tracking
        total_budget = my_orders.aggregate(
            total=Sum('total_budget')
        )['total'] or Decimal('0.00')
        
        spent = ProcurementInvoice.objects.filter(
            order__in=my_orders,
            payment_status='paid'
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        # Overdue items
        overdue_orders = my_orders.filter(
            delivery_deadline__lt=now.date(),
            status__in=['published', 'assigned', 'in_progress']
        ).count()
        
        # SLA compliance
        total_assignments = OrderAssignment.objects.filter(order__in=my_orders).count()
        accepted_assignments = OrderAssignment.objects.filter(
            order__in=my_orders,
            status__in=['accepted', 'preparing', 'ready', 'delivered', 'verified', 'paid']
        ).count()
        
        return {
            'orders': {
                'total': total_orders,
                'active': active_orders,
                'draft': draft_orders,
                'completed': completed_orders,
                'overdue': overdue_orders,
            },
            'pending_actions': {
                'deliveries': pending_deliveries,
                'verifications': pending_verifications,
                'total': pending_deliveries + pending_verifications,
            },
            'budget': {
                'allocated': float(total_budget),
                'spent': float(spent),
                'remaining': float(total_budget - spent),
                'utilization': round((spent / total_budget * 100), 2) if total_budget > 0 else 0,
            },
            'performance': {
                'total_assignments': total_assignments,
                'accepted_rate': round((accepted_assignments / total_assignments * 100), 2) 
                                if total_assignments > 0 else 0,
            }
        }
    
    def get_my_orders(self, status=None, limit=50):
        """
        Get orders assigned to this officer.
        
        Args:
            status: Filter by status (optional)
            limit: Maximum number of orders to return
            
        Returns:
            list: Order details
        """
        orders = ProcurementOrder.objects.filter(
            Q(created_by=self.user) | Q(assigned_procurement_officer=self.user)
        )
        
        if status:
            orders = orders.filter(status=status)
        
        orders = orders.select_related(
            'created_by', 'assigned_procurement_officer'
        ).prefetch_related(
            'assignments'
        ).order_by('-created_at')[:limit]
        
        return [
            {
                'order_number': order.order_number,
                'title': order.title,
                'status': order.get_status_display(),
                'status_code': order.status,
                'production_type': order.production_type,
                'quantity_needed': order.quantity_needed,
                'quantity_assigned': order.quantity_assigned,
                'quantity_delivered': order.quantity_delivered,
                'fulfillment_percentage': order.fulfillment_percentage,
                'total_budget': float(order.total_budget),
                'delivery_deadline': order.delivery_deadline.isoformat(),
                'days_until_deadline': order.days_until_deadline,
                'is_overdue': order.is_overdue,
                'priority': order.get_priority_display(),
                'created_at': order.created_at.isoformat(),
                'farms_assigned': order.assignments.count(),
            }
            for order in orders
        ]
    
    def get_pending_approvals(self):
        """
        Get deliveries and invoices pending approval.
        
        Returns:
            dict: Pending items grouped by type
        """
        my_orders = ProcurementOrder.objects.filter(
            Q(created_by=self.user) | Q(assigned_procurement_officer=self.user)
        )
        
        # Pending delivery verifications
        pending_deliveries = DeliveryConfirmation.objects.filter(
            assignment__order__in=my_orders,
            verified_at__isnull=True
        ).select_related(
            'assignment__farm', 'assignment__order'
        ).order_by('-delivery_date')[:20]
        
        deliveries = [
            {
                'delivery_number': delivery.delivery_number,
                'order_number': delivery.assignment.order.order_number,
                'farm_name': delivery.assignment.farm.farm_name,
                'quantity': delivery.quantity_delivered,
                'delivery_date': delivery.delivery_date.isoformat(),
                'quality_passed': delivery.quality_passed,
                'requires_attention': not delivery.quality_passed or delivery.mortality_count > 0,
            }
            for delivery in pending_deliveries
        ]
        
        # Ready for delivery
        ready_assignments = OrderAssignment.objects.filter(
            order__in=my_orders,
            status='ready'
        ).select_related('farm', 'order').order_by('-actual_ready_date')[:20]
        
        ready = [
            {
                'assignment_number': assignment.assignment_number,
                'order_number': assignment.order.order_number,
                'farm_name': assignment.farm.farm_name,
                'quantity': assignment.quantity_assigned,
                'ready_date': assignment.actual_ready_date.isoformat() if assignment.actual_ready_date else None,
            }
            for assignment in ready_assignments
        ]
        
        return {
            'pending_verifications': deliveries,
            'ready_for_delivery': ready,
        }
    
    def get_overdue_items(self):
        """
        Get overdue orders and deliveries.
        
        Returns:
            dict: Overdue items
        """
        now = timezone.now()
        
        my_orders = ProcurementOrder.objects.filter(
            Q(created_by=self.user) | Q(assigned_procurement_officer=self.user)
        )
        
        # Overdue orders
        overdue_orders = my_orders.filter(
            delivery_deadline__lt=now.date(),
            status__in=['published', 'assigned', 'in_progress']
        ).order_by('delivery_deadline')
        
        orders = [
            {
                'order_number': order.order_number,
                'title': order.title,
                'deadline': order.delivery_deadline.isoformat(),
                'days_overdue': abs(order.days_until_deadline),
                'fulfillment_percentage': order.fulfillment_percentage,
            }
            for order in overdue_orders
        ]
        
        # Overdue invoices
        overdue_invoices = ProcurementInvoice.objects.filter(
            order__in=my_orders,
            due_date__lt=now.date(),
            payment_status__in=['pending', 'approved']
        ).select_related('farm', 'order').order_by('due_date')
        
        invoices = [
            {
                'invoice_number': invoice.invoice_number,
                'order_number': invoice.order.order_number,
                'farm_name': invoice.farm.farm_name,
                'amount': float(invoice.total_amount),
                'due_date': invoice.due_date.isoformat(),
                'days_overdue': (now.date() - invoice.due_date).days,
            }
            for invoice in overdue_invoices
        ]
        
        return {
            'orders': orders,
            'invoices': invoices,
        }
    
    def get_order_timeline(self, order_id):
        """
        Get detailed timeline for a specific order.
        
        Args:
            order_id: Order UUID or order_number
            
        Returns:
            dict: Order timeline with all events
        """
        try:
            if len(str(order_id)) > 20:  # UUID
                order = ProcurementOrder.objects.get(id=order_id)
            else:
                order = ProcurementOrder.objects.get(order_number=order_id)
        except ProcurementOrder.DoesNotExist:
            return None
        
        timeline = []
        
        # Order created
        timeline.append({
            'event': 'Order Created',
            'timestamp': order.created_at.isoformat(),
            'user': order.created_by.get_full_name(),
            'icon': 'add_circle',
            'color': 'primary',
        })
        
        # Order published
        if order.published_at:
            timeline.append({
                'event': 'Order Published',
                'timestamp': order.published_at.isoformat(),
                'icon': 'publish',
                'color': 'info',
            })
        
        # Assignments
        if order.assigned_at:
            timeline.append({
                'event': f'Assigned to {order.assignments.count()} Farms',
                'timestamp': order.assigned_at.isoformat(),
                'icon': 'assignment_ind',
                'color': 'success',
            })
        
        # Deliveries
        deliveries = DeliveryConfirmation.objects.filter(
            assignment__order=order
        ).order_by('delivery_date')
        
        for delivery in deliveries:
            timeline.append({
                'event': f'Delivery from {delivery.assignment.farm.farm_name}',
                'timestamp': delivery.delivery_date.isoformat(),
                'details': f'{delivery.quantity_delivered} units delivered',
                'icon': 'local_shipping',
                'color': 'success' if delivery.quality_passed else 'warning',
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        
        return {
            'order': {
                'order_number': order.order_number,
                'title': order.title,
                'status': order.get_status_display(),
            },
            'timeline': timeline
        }
    
    def get_performance_metrics(self, days=30):
        """
        Get officer performance metrics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            dict: Performance metrics
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        my_orders = ProcurementOrder.objects.filter(
            Q(created_by=self.user) | Q(assigned_procurement_officer=self.user),
            created_at__gte=cutoff_date
        )
        
        total_orders = my_orders.count()
        completed_orders = my_orders.filter(status='completed').count()
        
        # Average fulfillment time
        completed = my_orders.filter(
            status='completed',
            completed_at__isnull=False
        )
        
        avg_fulfillment_days = 0
        if completed.exists():
            total_days = sum([
                (order.completed_at.date() - order.created_at.date()).days
                for order in completed
            ])
            avg_fulfillment_days = total_days / completed.count()
        
        # On-time delivery rate
        on_time_orders = my_orders.filter(
            completed_at__isnull=False,
            completed_at__date__lte=F('delivery_deadline')
        ).count()
        
        on_time_rate = round((on_time_orders / completed_orders * 100), 2) if completed_orders > 0 else 0
        
        return {
            'period_days': days,
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'completion_rate': round((completed_orders / total_orders * 100), 2) if total_orders > 0 else 0,
            'avg_fulfillment_days': round(avg_fulfillment_days, 1),
            'on_time_delivery_rate': on_time_rate,
        }
