"""
Sales & Revenue Celery tasks for YEA Poultry Management System.

Background tasks for marketplace subscription/activation management,
payment processing, and revenue calculations.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_expired_activations():
    """
    Check for expired marketplace activations and update farm status.
    
    Scheduled via Celery Beat to run every 6 hours.
    
    NOTE: Government subsidy logic has been REMOVED (Jan 2025).
    All farmers must pay the standard GHS 50/month marketplace fee.
    Government subsidies are for birds/equipment/feed, NOT marketplace fees.
    
    This task now only handles subscription-based expirations via the
    Subscription model's status field.
    """
    from subscriptions.models import Subscription
    
    logger.info("Starting marketplace subscription expiration check...")
    
    today = timezone.now().date()
    expired_count = 0
    past_due_count = 0
    
    # Check for subscriptions that need status updates
    # The Subscription model handles its own expiration logic
    # This task triggers a sweep to catch any missed expirations
    
    # Find active subscriptions past their billing date
    overdue_subscriptions = Subscription.objects.filter(
        status='active',
        next_billing_date__lt=today
    ).select_related('farm')
    
    for subscription in overdue_subscriptions:
        with transaction.atomic():
            subscription.status = 'past_due'
            subscription.save(update_fields=['status', 'updated_at'])
            past_due_count += 1
            logger.info(f"Subscription {subscription.id} marked as past_due")
    
    # Find past_due subscriptions past grace period (7 days default)
    grace_days = 7
    grace_cutoff = today - timedelta(days=grace_days)
    
    expired_subscriptions = Subscription.objects.filter(
        status='past_due',
        next_billing_date__lt=grace_cutoff
    ).select_related('farm', 'farm__user')
    
    for subscription in expired_subscriptions:
        with transaction.atomic():
            # Suspend the subscription
            subscription.status = 'suspended'
            subscription.save(update_fields=['status', 'updated_at'])
            
            # Update farm
            if subscription.farm:
                subscription.farm.marketplace_enabled = False
                subscription.farm.subscription_type = 'none'
                subscription.farm.save(update_fields=[
                    'marketplace_enabled',
                    'subscription_type',
                    'updated_at'
                ])
            
            expired_count += 1
            logger.info(f"Subscription {subscription.id} suspended (past grace period)")
            
            # Send notification to farmer
            farm = subscription.farm
            if farm and farm.user and hasattr(farm.user, 'phone'):
                from core.tasks import send_sms_async
                send_sms_async.delay(
                    str(farm.user.phone),
                    f"Your YEA marketplace subscription has been suspended. "
                    f"Visit your dashboard to reactivate. Contact support for assistance."
                )
    
    logger.info(
        f"Subscription check complete. Past due: {past_due_count}, Suspended: {expired_count}"
    )
    return {
        'status': 'success',
        'past_due': past_due_count,
        'suspended': expired_count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task
def send_expiration_warnings():
    """
    Send warnings to farmers whose marketplace subscriptions are expiring soon.
    
    Sends notifications at:
    - 7 days before expiration
    - 3 days before expiration
    - 1 day before expiration
    
    NOTE: Government subsidy logic has been REMOVED (Jan 2025).
    This task now checks Subscription.next_billing_date instead.
    """
    from subscriptions.models import Subscription
    
    logger.info("Sending marketplace subscription expiration warnings...")
    
    today = timezone.now().date()
    warning_days = [7, 3, 1]
    warnings_sent = {d: 0 for d in warning_days}
    
    for days in warning_days:
        expiry_date = today + timedelta(days=days)
        
        # Find subscriptions expiring on this date
        expiring_subscriptions = Subscription.objects.filter(
            status='active',
            next_billing_date=expiry_date
        ).select_related('farm', 'farm__user')
        
        for subscription in expiring_subscriptions:
            farm = subscription.farm
            if farm and farm.user and hasattr(farm.user, 'phone'):
                from core.tasks import send_sms_async
                send_sms_async.delay(
                    str(farm.user.phone),
                    f"YEA Poultry: Your marketplace subscription expires in {days} day(s). "
                    f"Visit your dashboard to renew and maintain visibility in buyer searches."
                )
                warnings_sent[days] += 1
    
    logger.info(f"Expiration warnings sent: {warnings_sent}")
    return {'warnings_sent': warnings_sent}


@shared_task
def calculate_daily_platform_revenue():
    """
    Calculate and cache daily platform revenue metrics.
    
    Runs daily to aggregate revenue from:
    - Marketplace commissions
    - Activation fees
    - Advertising revenue
    """
    from sales_revenue.models import Order, PlatformSettings
    from advertising.models import PartnerPayment
    from subscriptions.models import Subscription
    from django.db.models import Sum
    from django.core.cache import cache
    
    logger.info("Calculating daily platform revenue...")
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)
    
    try:
        # Marketplace commissions (completed orders)
        daily_commissions = Order.objects.filter(
            status='completed',
            created_at__date=yesterday
        ).aggregate(
            total_commission=Sum('platform_commission')
        )['total_commission'] or 0
        
        monthly_commissions = Order.objects.filter(
            status='completed',
            created_at__date__gte=month_start
        ).aggregate(
            total_commission=Sum('platform_commission')
        )['total_commission'] or 0
        
        # Activation fee revenue (subscriptions)
        daily_activations = Subscription.objects.filter(
            payment_status='paid',
            created_at__date=yesterday
        ).aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        monthly_activations = Subscription.objects.filter(
            payment_status='paid',
            created_at__date__gte=month_start
        ).aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        # Advertising revenue
        daily_ads = PartnerPayment.objects.filter(
            status='paid',
            paid_date=yesterday
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        monthly_ads = PartnerPayment.objects.filter(
            status='paid',
            paid_date__gte=month_start
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        revenue_data = {
            'date': yesterday.isoformat(),
            'daily': {
                'commissions': float(daily_commissions),
                'activations': float(daily_activations),
                'advertising': float(daily_ads),
                'total': float(daily_commissions + daily_activations + daily_ads)
            },
            'monthly': {
                'commissions': float(monthly_commissions),
                'activations': float(monthly_activations),
                'advertising': float(monthly_ads),
                'total': float(monthly_commissions + monthly_activations + monthly_ads)
            },
            'calculated_at': timezone.now().isoformat()
        }
        
        # Cache for dashboards
        cache.set('platform:daily_revenue', revenue_data, timeout=86400)
        
        logger.info(f"Daily revenue calculated: {revenue_data['daily']['total']} GHS")
        return revenue_data
    except Exception as exc:
        logger.error(f"Revenue calculation failed: {exc}")
        return {'status': 'error', 'error': str(exc)}


@shared_task
def process_partner_payments():
    """
    Process pending partner payments for advertising.
    
    This is a placeholder for payment gateway integration.
    Would connect to actual payment processor in production.
    """
    from advertising.models import PartnerPayment
    
    logger.info("Processing partner payments...")
    
    pending_payments = PartnerPayment.objects.filter(
        status='pending'
    ).select_related('partner')
    
    processed = 0
    for payment in pending_payments:
        # In production, this would:
        # 1. Connect to payment gateway
        # 2. Initiate transfer
        # 3. Update payment status
        # 4. Notify partner
        
        logger.info(f"Would process payment {payment.id} for partner {payment.partner.id}")
        processed += 1
    
    return {'pending_count': pending_payments.count(), 'processed': processed}


@shared_task
def sync_order_commissions():
    """
    Ensure all completed orders have platform commission calculated.
    
    Catches any orders that might have missed commission calculation.
    """
    from sales_revenue.models import Order, PlatformSettings
    
    logger.info("Syncing order commissions...")
    
    settings = PlatformSettings.get_settings()
    
    # Find completed orders with null commission
    orders_to_update = Order.objects.filter(
        status='completed',
        platform_commission__isnull=True
    )
    
    updated_count = 0
    for order in orders_to_update:
        try:
            # Calculate commission based on order total
            total = float(order.total_amount)
            if total < float(settings.commission_tier_1_threshold):
                rate = float(settings.commission_tier_1_percentage) / 100
            elif total < float(settings.commission_tier_2_threshold):
                rate = float(settings.commission_tier_2_percentage) / 100
            else:
                rate = float(settings.commission_tier_3_percentage) / 100
            
            commission = max(
                total * rate,
                float(settings.minimum_commission_amount)
            )
            
            order.platform_commission = commission
            order.save(update_fields=['platform_commission'])
            updated_count += 1
        except Exception as exc:
            logger.error(f"Failed to calculate commission for order {order.id}: {exc}")
    
    logger.info(f"Commission sync complete. Updated: {updated_count} orders")
    return {'updated': updated_count}


@shared_task
def generate_seller_payout_report(period: str = 'weekly'):
    """
    Generate payout report for sellers.
    
    Aggregates sales per seller for the given period.
    
    Args:
        period: 'daily', 'weekly', or 'monthly'
    """
    from sales_revenue.models import Order
    from farms.models import Farm
    from django.db.models import Sum, Count
    from django.core.cache import cache
    
    logger.info(f"Generating {period} seller payout report...")
    
    today = timezone.now().date()
    
    if period == 'daily':
        start_date = today - timedelta(days=1)
    elif period == 'weekly':
        start_date = today - timedelta(days=7)
    else:  # monthly
        start_date = today - timedelta(days=30)
    
    # Aggregate sales per farm
    farm_sales = Order.objects.filter(
        status='completed',
        created_at__date__gte=start_date,
        created_at__date__lt=today
    ).values(
        'farm_id',
        'farm__farm_name',
        'farm__owner__phone_number',
        'farm__owner__email'
    ).annotate(
        total_sales=Sum('total_amount'),
        total_commission=Sum('platform_commission'),
        order_count=Count('id')
    ).order_by('-total_sales')
    
    report = {
        'period': period,
        'start_date': start_date.isoformat(),
        'end_date': today.isoformat(),
        'sellers': list(farm_sales),
        'generated_at': timezone.now().isoformat()
    }
    
    # Cache the report
    cache.set(f'report:seller_payout:{period}', report, timeout=86400)
    
    logger.info(f"Seller payout report generated: {len(report['sellers'])} sellers")
    return {'sellers_count': len(report['sellers']), 'period': period}
