"""
Custom admin dashboard view with real-time statistics.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from farms.models import Farm
from procurement.models import (
    ProcurementOrder,
    OrderAssignment,
    DeliveryConfirmation,
    ProcurementInvoice
)
from django.conf import settings


@staff_member_required
def admin_dashboard(request):
    """
    Custom admin dashboard with comprehensive statistics.
    """
    
    # Farm Statistics
    total_farms = Farm.objects.count()
    approved_farms = Farm.objects.filter(
        application_status='Approved - Farm ID Assigned'
    ).count()
    pending_farms = Farm.objects.filter(
        application_status__in=['Under Review', 'Pending National Approval']
    ).count()
    
    approval_rate = 0
    if total_farms > 0:
        approval_rate = round((approved_farms / total_farms) * 100, 1)
    
    # Order Statistics
    total_orders = ProcurementOrder.objects.count()
    active_orders = ProcurementOrder.objects.filter(
        status__in=['published', 'assigned', 'in_progress', 'assigning']
    ).count()
    completed_orders = ProcurementOrder.objects.filter(
        status='completed'
    ).count()
    
    completion_rate = 0
    if total_orders > 0:
        completion_rate = round((completed_orders / total_orders) * 100, 1)
    
    # Delivery Statistics
    total_deliveries = DeliveryConfirmation.objects.count()
    pending_deliveries = DeliveryConfirmation.objects.filter(
        verified_at__isnull=True
    ).count()
    
    # Budget Statistics
    budget_data = ProcurementOrder.objects.aggregate(
        total_budget=Sum('total_budget'),
        total_spent=Sum('total_spent')
    )
    
    total_budget = budget_data['total_budget'] or Decimal('0.00')
    total_spent = budget_data['total_spent'] or Decimal('0.00')
    
    budget_utilization = 0
    if total_budget > 0:
        budget_utilization = round((total_spent / total_budget) * 100, 1)
    
    # Birds Statistics
    birds_data = ProcurementOrder.objects.aggregate(
        total_birds=Sum('quantity_needed'),
        birds_delivered=Sum('quantity_delivered')
    )
    
    total_birds = birds_data['total_birds'] or 0
    birds_delivered = birds_data['birds_delivered'] or 0
    
    # Payment Statistics
    invoice_data = ProcurementInvoice.objects.aggregate(
        paid_invoices=Count('id', filter=Q(payment_status='paid')),
        total_paid=Sum('total_amount', filter=Q(payment_status='paid'))
    )
    
    paid_invoices = invoice_data['paid_invoices'] or 0
    total_paid = invoice_data['total_paid'] or Decimal('0.00')
    
    # Alerts & Warnings
    now = timezone.now()
    overdue_orders = ProcurementOrder.objects.filter(
        delivery_deadline__lt=now.date(),
        status__in=['published', 'assigned', 'in_progress']
    ).count()
    
    pending_approvals = Farm.objects.filter(
        application_status__in=['Under Review', 'Pending National Approval']
    ).count()
    
    # Performance Metrics
    completed_assignments = OrderAssignment.objects.filter(
        status='paid',
        assigned_at__isnull=False,
        payment_processed_at__isnull=False
    )
    
    avg_fulfillment_days = 0
    if completed_assignments.exists():
        total_days = 0
        count = 0
        for assignment in completed_assignments:
            if assignment.assigned_at and assignment.payment_processed_at:
                delta = assignment.payment_processed_at - assignment.assigned_at
                total_days += delta.days
                count += 1
        if count > 0:
            avg_fulfillment_days = round(total_days / count, 1)
    
    # Quality Pass Rate
    deliveries_with_quality = DeliveryConfirmation.objects.filter(
        quality_passed__isnull=False
    )
    quality_passed_count = deliveries_with_quality.filter(quality_passed=True).count()
    total_quality_checks = deliveries_with_quality.count()
    
    quality_pass_rate = 0
    if total_quality_checks > 0:
        quality_pass_rate = round((quality_passed_count / total_quality_checks) * 100, 1)
    
    # Recent Activities
    recent_activities = []
    
    # Recent farms (last 5)
    recent_farms = Farm.objects.order_by('-created_at')[:5]
    for farm in recent_farms:
        recent_activities.append({
            'type': 'farm',
            'icon': '🏠',
            'title': f'New farm application: {farm.farm_name}',
            'time': farm.created_at
        })
    
    # Recent orders (last 5)
    recent_orders = ProcurementOrder.objects.order_by('-created_at')[:5]
    for order in recent_orders:
        recent_activities.append({
            'type': 'order',
            'icon': '📦',
            'title': f'Order created: {order.order_number} - {order.title}',
            'time': order.created_at
        })
    
    # Recent deliveries (last 5)
    recent_deliveries = DeliveryConfirmation.objects.order_by('-created_at')[:5]
    for delivery in recent_deliveries:
        recent_activities.append({
            'type': 'delivery',
            'icon': '🚚',
            'title': f'Delivery: {delivery.delivery_number}',
            'time': delivery.created_at
        })
    
    # Recent payments (last 5)
    recent_payments = ProcurementInvoice.objects.filter(
        payment_status='paid'
    ).order_by('-payment_date')[:5]
    for payment in recent_payments:
        recent_activities.append({
            'type': 'payment',
            'icon': '💰',
            'title': f'Payment processed: {payment.invoice_number} - GHS {payment.total_amount:,.2f}',
            'time': payment.payment_date
        })
    
    # Sort by time and limit to 10 most recent
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:10]
    
    # SMS Status
    sms_enabled = getattr(settings, 'SMS_ENABLED', False)
    
    context = {
        # Farm stats
        'total_farms': total_farms,
        'approved_farms': approved_farms,
        'pending_farms': pending_farms,
        'approval_rate': approval_rate,
        
        # Order stats
        'total_orders': total_orders,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'completion_rate': completion_rate,
        
        # Delivery stats
        'total_deliveries': total_deliveries,
        'pending_deliveries': pending_deliveries,
        
        # Budget stats
        'total_budget': total_budget,
        'total_spent': total_spent,
        'budget_utilization': budget_utilization,
        
        # Birds stats
        'total_birds': total_birds,
        'birds_delivered': birds_delivered,
        
        # Payment stats
        'paid_invoices': paid_invoices,
        'total_paid': total_paid,
        
        # Alerts
        'overdue_orders': overdue_orders,
        'pending_approvals': pending_approvals,
        
        # Performance
        'avg_fulfillment_days': avg_fulfillment_days,
        'quality_pass_rate': quality_pass_rate,
        
        # System
        'sms_enabled': sms_enabled,
        
        # Activity
        'recent_activities': recent_activities,
    }
    
    return render(request, 'admin/index.html', context)
