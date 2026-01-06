"""
Subscription Celery Tasks

Background tasks for:
- Payment verification polling
- Subscription renewal reminders
- Subscription suspension
- Payment status checks
"""

import logging
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def verify_pending_payment(self, payment_id: str):
    """
    Verify a pending payment with Paystack
    
    Called after initiating a payment to check status.
    Retries up to 3 times with 60 second delays.
    """
    from .models import SubscriptionPayment
    from core.paystack_service import PaystackService, PaystackError
    
    try:
        payment = SubscriptionPayment.objects.select_related(
            'subscription__farm'
        ).get(id=payment_id)
    except SubscriptionPayment.DoesNotExist:
        logger.warning(f"Payment not found for verification: {payment_id}")
        return {'status': 'error', 'message': 'Payment not found'}
    
    # Skip if already processed
    if payment.status in ['completed', 'failed']:
        return {'status': payment.status, 'reference': payment.payment_reference}
    
    try:
        result = PaystackService.verify_transaction(payment.payment_reference)
        
        if result['status'] == 'success':
            payment.mark_as_completed(gateway_response=result)
            logger.info(f"Payment verified (task): {payment.payment_reference}")
            
            # Send confirmation SMS
            send_payment_confirmation_sms.delay(str(payment.id))
            
            return {'status': 'success', 'reference': payment.payment_reference}
        
        elif result['status'] == 'failed':
            payment.mark_as_failed(
                reason=result.get('gateway_response', 'Payment failed'),
                gateway_response=result
            )
            return {'status': 'failed', 'reference': payment.payment_reference}
        
        else:
            # Still pending, retry
            if self.request.retries < self.max_retries:
                raise self.retry(countdown=120)  # Retry in 2 minutes
            else:
                # Mark as abandoned after max retries
                payment.status = 'abandoned'
                payment.save()
                return {'status': 'abandoned', 'reference': payment.payment_reference}
                
    except PaystackError as e:
        logger.error(f"Payment verification error: {e.message}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {'status': 'error', 'message': str(e.message)}


@shared_task
def send_payment_confirmation_sms(payment_id: str):
    """
    Send SMS confirmation after successful payment
    """
    from .models import SubscriptionPayment
    from core.sms_service import SMSService
    
    try:
        payment = SubscriptionPayment.objects.select_related(
            'subscription__farm'
        ).get(id=payment_id)
    except SubscriptionPayment.DoesNotExist:
        return {'status': 'error', 'message': 'Payment not found'}
    
    if payment.status != 'completed':
        return {'status': 'skipped', 'message': 'Payment not completed'}
    
    farm = payment.subscription.farm
    phone = payment.momo_phone or str(farm.primary_phone)
    
    message = (
        f"YEA Marketplace: Your subscription payment of GHS {payment.amount} was successful. "
        f"Marketplace access active until {payment.period_end.strftime('%d %b %Y')}. "
        f"Ref: {payment.payment_reference}"
    )
    
    try:
        SMSService.send_sms(phone=phone, message=message)
        logger.info(f"Payment confirmation SMS sent to {phone}")
        return {'status': 'sent', 'phone': phone}
    except Exception as e:
        logger.error(f"Failed to send payment confirmation SMS: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def check_expiring_subscriptions():
    """
    Check for subscriptions expiring in the next 7 days and send reminders
    
    Should run daily via Celery Beat
    """
    from .models import Subscription
    
    today = timezone.now().date()
    reminder_date = today + timedelta(days=7)
    
    # Find subscriptions expiring in 7 days
    expiring_subscriptions = Subscription.objects.filter(
        status='active',
        next_billing_date=reminder_date,
        auto_renew=True
    ).select_related('farm')
    
    count = 0
    for subscription in expiring_subscriptions:
        send_renewal_reminder.delay(str(subscription.id), days_until=7)
        count += 1
    
    # Also check 3-day reminders
    reminder_date_3 = today + timedelta(days=3)
    expiring_3_days = Subscription.objects.filter(
        status='active',
        next_billing_date=reminder_date_3,
        auto_renew=True
    ).select_related('farm')
    
    for subscription in expiring_3_days:
        send_renewal_reminder.delay(str(subscription.id), days_until=3)
        count += 1
    
    logger.info(f"Queued {count} subscription renewal reminders")
    return {'reminders_queued': count}


@shared_task
def send_renewal_reminder(subscription_id: str, days_until: int = 7):
    """
    Send renewal reminder SMS to farmer
    """
    from .models import Subscription
    from core.sms_service import SMSService
    
    try:
        subscription = Subscription.objects.select_related('farm').get(id=subscription_id)
    except Subscription.DoesNotExist:
        return {'status': 'error', 'message': 'Subscription not found'}
    
    farm = subscription.farm
    phone = str(farm.primary_phone)
    
    message = (
        f"YEA Marketplace: Your subscription expires in {days_until} days on "
        f"{subscription.next_billing_date.strftime('%d %b %Y')}. "
        f"Amount due: GHS {subscription.plan.price_monthly}. "
        f"Renew now to keep selling on the marketplace."
    )
    
    try:
        SMSService.send_sms(phone=phone, message=message)
        
        # Update reminder tracking
        subscription.reminder_sent_at = timezone.now()
        subscription.reminder_count += 1
        subscription.save(update_fields=['reminder_sent_at', 'reminder_count'])
        
        logger.info(f"Renewal reminder sent to {phone} for {farm.farm_name}")
        return {'status': 'sent', 'phone': phone}
    except Exception as e:
        logger.error(f"Failed to send renewal reminder: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def process_subscription_expirations():
    """
    Process expired subscriptions and move to past_due status
    
    Should run daily via Celery Beat
    """
    from .models import Subscription
    from sales_revenue.models import PlatformSettings
    
    today = timezone.now().date()
    settings = PlatformSettings.get_settings()
    grace_days = settings.marketplace_grace_period_days
    
    # Move expired active subscriptions to past_due
    expired_active = Subscription.objects.filter(
        status='active',
        next_billing_date__lt=today
    )
    
    past_due_count = expired_active.update(status='past_due')
    
    logger.info(f"Moved {past_due_count} subscriptions to past_due status")
    
    # Suspend subscriptions past grace period
    grace_cutoff = today - timedelta(days=grace_days)
    
    past_grace = Subscription.objects.filter(
        status='past_due',
        next_billing_date__lte=grace_cutoff
    ).select_related('farm')
    
    suspended_count = 0
    for subscription in past_grace:
        subscription.suspend(reason="Payment overdue - grace period expired")
        
        # Disable marketplace on farm
        farm = subscription.farm
        farm.marketplace_enabled = False
        farm.save(update_fields=['marketplace_enabled', 'updated_at'])
        
        # Send suspension notification
        send_suspension_notification.delay(str(subscription.id))
        
        suspended_count += 1
    
    logger.info(f"Suspended {suspended_count} subscriptions for non-payment")
    
    return {
        'past_due': past_due_count,
        'suspended': suspended_count
    }


@shared_task
def send_suspension_notification(subscription_id: str):
    """
    Send notification when subscription is suspended
    """
    from .models import Subscription
    from core.sms_service import SMSService
    
    try:
        subscription = Subscription.objects.select_related('farm').get(id=subscription_id)
    except Subscription.DoesNotExist:
        return {'status': 'error', 'message': 'Subscription not found'}
    
    farm = subscription.farm
    phone = str(farm.primary_phone)
    
    message = (
        f"YEA Marketplace: Your marketplace access has been suspended due to non-payment. "
        f"Pay GHS {subscription.plan.price_monthly} to reactivate and continue selling. "
        f"Your listings are currently hidden from buyers."
    )
    
    try:
        SMSService.send_sms(phone=phone, message=message)
        logger.info(f"Suspension notification sent to {phone}")
        return {'status': 'sent', 'phone': phone}
    except Exception as e:
        logger.error(f"Failed to send suspension notification: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def send_overdue_payment_reminders():
    """
    Send reminders to farmers with overdue payments
    
    Should run daily via Celery Beat
    """
    from .models import Subscription
    from core.sms_service import SMSService
    
    # Get past_due subscriptions that haven't been reminded in 2 days
    two_days_ago = timezone.now() - timedelta(days=2)
    
    overdue_subscriptions = Subscription.objects.filter(
        status='past_due',
        reminder_count__lt=3  # Max 3 overdue reminders
    ).filter(
        models.Q(reminder_sent_at__isnull=True) |
        models.Q(reminder_sent_at__lt=two_days_ago)
    ).select_related('farm')
    
    count = 0
    for subscription in overdue_subscriptions:
        farm = subscription.farm
        phone = str(farm.primary_phone)
        days_overdue = (timezone.now().date() - subscription.next_billing_date).days
        
        message = (
            f"YEA Marketplace: Your payment of GHS {subscription.plan.price_monthly} "
            f"is {days_overdue} days overdue. Pay now to avoid suspension. "
            f"Visit the app to renew your marketplace access."
        )
        
        try:
            SMSService.send_sms(phone=phone, message=message)
            subscription.reminder_sent_at = timezone.now()
            subscription.reminder_count += 1
            subscription.save(update_fields=['reminder_sent_at', 'reminder_count'])
            count += 1
        except Exception as e:
            logger.error(f"Failed to send overdue reminder to {phone}: {e}")
    
    logger.info(f"Sent {count} overdue payment reminders")
    return {'reminders_sent': count}


@shared_task
def generate_monthly_invoices():
    """
    Generate invoices for upcoming subscription renewals
    
    Should run on the 1st of each month
    """
    from .models import Subscription, SubscriptionInvoice
    from dateutil.relativedelta import relativedelta
    
    today = timezone.now().date()
    next_month = today + relativedelta(months=1)
    
    # Find active subscriptions with billing due this month
    subscriptions = Subscription.objects.filter(
        status='active',
        next_billing_date__year=today.year,
        next_billing_date__month=today.month
    ).select_related('farm', 'plan')
    
    invoice_count = 0
    for subscription in subscriptions:
        # Check if invoice already exists
        existing = SubscriptionInvoice.objects.filter(
            subscription=subscription,
            billing_period_start=subscription.current_period_end,
            billing_period_end=subscription.current_period_end + relativedelta(months=1)
        ).exists()
        
        if existing:
            continue
        
        # Generate invoice number
        import secrets
        invoice_number = f"SUB-INV-{today.strftime('%Y-%m')}-{secrets.token_hex(3).upper()}"
        
        period_start = subscription.current_period_end
        period_end = period_start + relativedelta(months=1)
        
        SubscriptionInvoice.objects.create(
            invoice_number=invoice_number,
            subscription=subscription,
            amount=subscription.plan.price_monthly,
            description=f"Marketplace Access - {period_start.strftime('%B %Y')}",
            billing_period_start=period_start,
            billing_period_end=period_end,
            due_date=subscription.next_billing_date,
            status='issued'
        )
        
        invoice_count += 1
    
    logger.info(f"Generated {invoice_count} subscription invoices")
    return {'invoices_generated': invoice_count}


# Import models at module level for the overdue query
from django.db import models
