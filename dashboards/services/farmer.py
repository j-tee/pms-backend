"""
Farmer Dashboard Service

Provides farmer-specific metrics and workflow management:
- My assignments
- Earnings and payments
- Upcoming deliveries
- Performance metrics
"""

from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from farms.models import Farm
from procurement.models import OrderAssignment, DeliveryConfirmation, ProcurementInvoice


class FarmerDashboardService:
    """Service for farmer dashboard data"""
    
    def __init__(self, user):
        self.user = user
        try:
            self.farm = Farm.objects.get(user=user)
        except Farm.DoesNotExist:
            self.farm = None
    
    def get_overview_stats(self):
        """
        Get farmer-specific overview statistics.
        
        Returns:
            dict: Overview metrics for the farmer
        """
        if not self.farm:
            return {
                'error': 'No farm found for this user',
                'assignments': {},
                'earnings': {},
                'deliveries': {},
                'performance': {},
            }
        
        now = timezone.now()
        
        # Assignment statistics
        all_assignments = OrderAssignment.objects.filter(farm=self.farm)
        total_assignments = all_assignments.count()
        pending_assignments = all_assignments.filter(status='pending').count()
        accepted_assignments = all_assignments.filter(
            status__in=['accepted', 'preparing', 'ready']
        ).count()
        completed_assignments = all_assignments.filter(
            status__in=['delivered', 'verified', 'paid']
        ).count()
        
        # Earnings statistics
        total_earnings = ProcurementInvoice.objects.filter(
            farm=self.farm,
            payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        pending_payments = ProcurementInvoice.objects.filter(
            farm=self.farm,
            payment_status__in=['pending', 'approved']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        last_payment = ProcurementInvoice.objects.filter(
            farm=self.farm,
            payment_status='paid',
            payment_date__isnull=False
        ).order_by('-payment_date').first()
        
        # Delivery statistics
        total_deliveries = DeliveryConfirmation.objects.filter(
            assignment__farm=self.farm
        ).count()
        
        pending_deliveries = all_assignments.filter(status='ready').count()
        
        # Quality performance
        avg_quality = DeliveryConfirmation.objects.filter(
            assignment__farm=self.farm,
            quality_passed=True
        ).aggregate(avg=Avg('average_weight_per_bird'))['avg'] or Decimal('0.00')
        
        quality_pass_rate = 0
        if total_deliveries > 0:
            passed = DeliveryConfirmation.objects.filter(
                assignment__farm=self.farm,
                quality_passed=True
            ).count()
            quality_pass_rate = round((passed / total_deliveries * 100), 2)
        
        return {
            'assignments': {
                'total': total_assignments,
                'pending': pending_assignments,
                'accepted': accepted_assignments,
                'completed': completed_assignments,
                'acceptance_rate': round((accepted_assignments / total_assignments * 100), 2) 
                                  if total_assignments > 0 else 0,
            },
            'earnings': {
                'total': float(total_earnings),
                'pending': float(pending_payments),
                'last_payment_amount': float(last_payment.total_amount) if last_payment else 0,
                'last_payment_date': last_payment.payment_date.isoformat() if last_payment and last_payment.payment_date else None,
            },
            'deliveries': {
                'total': total_deliveries,
                'pending': pending_deliveries,
            },
            'performance': {
                'avg_quality': float(avg_quality),
                'quality_pass_rate': quality_pass_rate,
            }
        }
    
    def get_my_assignments(self, status=None, limit=50):
        """
        Get assignments for this farm.
        
        Args:
            status: Filter by status (optional)
            limit: Maximum number of assignments to return
            
        Returns:
            list: Assignment details
        """
        if not self.farm:
            return []
        
        assignments = OrderAssignment.objects.filter(farm=self.farm)
        
        if status:
            assignments = assignments.filter(status=status)
        
        assignments = assignments.select_related(
            'order'
        ).prefetch_related(
            'deliveries'
        ).order_by('-assigned_at')[:limit]
        
        return [
            {
                'assignment_number': assignment.assignment_number,
                'order_number': assignment.order.order_number,
                'order_title': assignment.order.title,
                'status': assignment.get_status_display(),
                'status_code': assignment.status,
                'quantity_assigned': assignment.quantity_assigned,
                'quantity_delivered': assignment.quantity_delivered,
                'fulfillment_percentage': assignment.fulfillment_percentage,
                'price_per_unit': float(assignment.price_per_unit),
                'total_value': float(assignment.total_value),
                'assigned_at': assignment.assigned_at.isoformat(),
                'expected_ready_date': assignment.expected_ready_date.isoformat() if assignment.expected_ready_date else None,
                'actual_ready_date': assignment.actual_ready_date.isoformat() if assignment.actual_ready_date else None,
                'delivery_deadline': assignment.order.delivery_deadline.isoformat(),
                'requires_action': assignment.status == 'pending',
            }
            for assignment in assignments
        ]
    
    def get_pending_actions(self):
        """
        Get assignments requiring farmer action.
        
        Returns:
            dict: Pending items grouped by action type
        """
        if not self.farm:
            return {
                'pending_responses': [],
                'preparing_orders': [],
                'ready_for_delivery': [],
            }
        
        # Pending responses (need to accept/reject)
        pending = OrderAssignment.objects.filter(
            farm=self.farm,
            status='pending'
        ).select_related('order').order_by('assigned_at')
        
        pending_responses = [
            {
                'assignment_number': assignment.assignment_number,
                'order_number': assignment.order.order_number,
                'order_title': assignment.order.title,
                'quantity': assignment.quantity_assigned,
                'value': float(assignment.total_value),
                'delivery_deadline': assignment.order.delivery_deadline.isoformat(),
                'days_until_deadline': assignment.order.days_until_deadline,
            }
            for assignment in pending
        ]
        
        # Preparing orders
        preparing = OrderAssignment.objects.filter(
            farm=self.farm,
            status__in=['accepted', 'preparing']
        ).select_related('order').order_by('expected_ready_date')
        
        preparing_orders = [
            {
                'assignment_number': assignment.assignment_number,
                'order_number': assignment.order.order_number,
                'quantity': assignment.quantity_assigned,
                'expected_ready_date': assignment.expected_ready_date.isoformat() if assignment.expected_ready_date else None,
                'delivery_deadline': assignment.order.delivery_deadline.isoformat(),
            }
            for assignment in preparing
        ]
        
        # Ready for delivery
        ready = OrderAssignment.objects.filter(
            farm=self.farm,
            status='ready'
        ).select_related('order').order_by('-actual_ready_date')
        
        ready_for_delivery = [
            {
                'assignment_number': assignment.assignment_number,
                'order_number': assignment.order.order_number,
                'quantity': assignment.quantity_assigned,
                'ready_since': assignment.actual_ready_date.isoformat() if assignment.actual_ready_date else None,
            }
            for assignment in ready
        ]
        
        return {
            'pending_responses': pending_responses,
            'preparing_orders': preparing_orders,
            'ready_for_delivery': ready_for_delivery,
        }
    
    def get_earnings_breakdown(self):
        """
        Get detailed earnings breakdown.
        
        Returns:
            dict: Earnings by status and time period
        """
        if not self.farm:
            return {}
        
        invoices = ProcurementInvoice.objects.filter(farm=self.farm)
        
        # By status
        paid = invoices.filter(payment_status='paid').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        approved = invoices.filter(payment_status='approved').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        pending = invoices.filter(payment_status='pending').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        # Deductions
        total_deductions = invoices.filter(payment_status='paid').aggregate(
            quality=Sum('quality_deduction'),
            mortality=Sum('mortality_deduction'),
            other=Sum('other_deductions')
        )
        
        quality_deductions = total_deductions['quality'] or Decimal('0.00')
        mortality_deductions = total_deductions['mortality'] or Decimal('0.00')
        other_deductions = total_deductions['other'] or Decimal('0.00')
        
        # Monthly trend (last 6 months)
        from django.db.models.functions import TruncMonth
        
        six_months_ago = timezone.now() - timedelta(days=180)
        
        monthly_earnings = invoices.filter(
            payment_status='paid',
            payment_date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('month')
        
        monthly_data = [
            {
                'month': item['month'].strftime('%b %Y'),
                'earnings': float(item['total']),
                'orders': item['count']
            }
            for item in monthly_earnings
        ]
        
        return {
            'by_status': {
                'paid': float(paid),
                'approved': float(approved),
                'pending': float(pending),
            },
            'deductions': {
                'quality': float(quality_deductions),
                'mortality': float(mortality_deductions),
                'other': float(other_deductions),
                'total': float(quality_deductions + mortality_deductions + other_deductions),
            },
            'monthly_trend': monthly_data,
        }
    
    def get_delivery_history(self, limit=20):
        """
        Get delivery history for this farm.
        
        Args:
            limit: Maximum number of deliveries to return
            
        Returns:
            list: Delivery details
        """
        if not self.farm:
            return []
        
        deliveries = DeliveryConfirmation.objects.filter(
            assignment__farm=self.farm
        ).select_related(
            'assignment__order', 'received_by'
        ).order_by('-delivery_date')[:limit]
        
        return [
            {
                'delivery_number': delivery.delivery_number,
                'order_number': delivery.assignment.order.order_number,
                'quantity': delivery.quantity_delivered,
                'delivery_date': delivery.delivery_date.isoformat(),
                'quality_passed': delivery.quality_passed,
                'average_weight': float(delivery.average_weight_per_bird) if delivery.average_weight_per_bird else None,
                'mortality_count': delivery.mortality_count,
                'verified': delivery.verified_at is not None,
                'verified_at': delivery.verified_at.isoformat() if delivery.verified_at else None,
                'received_by': delivery.received_by.get_full_name() if delivery.received_by else None,
            }
            for delivery in deliveries
        ]
    
    def get_performance_summary(self):
        """
        Get overall performance summary.
        
        Returns:
            dict: Performance metrics
        """
        if not self.farm:
            return {}
        
        assignments = OrderAssignment.objects.filter(farm=self.farm)
        total = assignments.count()
        
        if total == 0:
            return {
                'total_assignments': 0,
                'completion_rate': 0,
                'on_time_rate': 0,
                'rejection_rate': 0,
                'avg_quality_score': 0,
            }
        
        # Completion rate
        completed = assignments.filter(status='paid').count()
        completion_rate = round((completed / total * 100), 2)
        
        # Rejection rate
        rejected = assignments.filter(status='rejected').count()
        rejection_rate = round((rejected / total * 100), 2)
        
        # On-time delivery rate
        on_time = assignments.filter(
            status__in=['delivered', 'verified', 'paid'],
            delivery_date__lte=F('order__delivery_deadline')
        ).count()
        
        on_time_rate = round((on_time / completed * 100), 2) if completed > 0 else 0
        
        # Average quality score
        avg_quality = DeliveryConfirmation.objects.filter(
            assignment__farm=self.farm
        ).aggregate(avg=Avg('average_weight_per_bird'))['avg'] or Decimal('0.00')
        
        return {
            'total_assignments': total,
            'completion_rate': completion_rate,
            'on_time_rate': on_time_rate,
            'rejection_rate': rejection_rate,
            'avg_quality_score': float(avg_quality),
        }
