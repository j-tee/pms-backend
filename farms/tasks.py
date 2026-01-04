"""
Farms Celery tasks for YEA Poultry Management System.

Background tasks for farm management, batch enrollment,
and farmer notification.
"""
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_enrollment_reminders():
    """
    Send reminders for open batch enrollments.
    
    Scheduled via Celery Beat to run weekdays at 9 AM.
    Notifies farmers about:
    - Open batches they haven't applied to
    - Pending application status updates
    """
    from farms.batch_enrollment_models import Batch, BatchEnrollmentApplication
    from farms.models import Farm
    
    logger.info("Sending batch enrollment reminders...")
    
    today = timezone.now().date()
    reminders_sent = 0
    
    # Find active, published batches with open enrollment
    active_batches = Batch.objects.filter(
        is_active=True,
        is_published=True,
        enrollment_end_date__gte=today
    )
    
    for batch in active_batches:
        days_until_close = (batch.enrollment_end_date - today).days
        
        # Send reminders at 7 days, 3 days, and 1 day before closing
        if days_until_close in [7, 3, 1]:
            # Find eligible farmers who haven't applied
            already_applied = BatchEnrollmentApplication.objects.filter(
                batch=batch
            ).values_list('farm_id', flat=True)
            
            eligible_farms = Farm.objects.filter(
                application_status='Approved',
                farm_status='Active'
            ).exclude(
                id__in=already_applied
            ).select_related('owner')[:100]  # Limit to 100 per run
            
            for farm in eligible_farms:
                if farm.owner and farm.owner.phone_number:
                    from core.tasks import send_sms_async
                    send_sms_async.delay(
                        str(farm.owner.phone_number),
                        f"YEA Poultry: {batch.name} enrollment closes in {days_until_close} day(s)! "
                        f"Apply now to join this batch. Visit your dashboard."
                    )
                    reminders_sent += 1
    
    logger.info(f"Sent {reminders_sent} enrollment reminders")
    return {'reminders_sent': reminders_sent}


@shared_task
def notify_application_status_change(application_id: str, new_status: str, message: str = None):
    """
    Notify farmer of application status change.
    
    Called when admin updates application status.
    
    Usage:
        from farms.tasks import notify_application_status_change
        notify_application_status_change.delay(
            str(application.id),
            'Approved',
            'Congratulations! Your application has been approved.'
        )
    """
    from farms.application_models import FarmApplication
    
    logger.info(f"Notifying application {application_id} of status: {new_status}")
    
    try:
        application = FarmApplication.objects.get(pk=application_id)
        
        default_messages = {
            'Approved': f"Congratulations! Your YEA Poultry farm application has been approved. "
                       f"Welcome to the program!",
            'Rejected': f"Your YEA Poultry farm application was not approved at this time. "
                       f"Please contact your extension officer for details.",
            'Under Review': f"Your YEA Poultry farm application is now under review. "
                           f"We will notify you of the outcome.",
            'Pending': f"Your YEA Poultry application has been received and is pending review."
        }
        
        sms_message = message or default_messages.get(new_status, f"Application status: {new_status}")
        
        if application.phone_number:
            from core.tasks import send_sms_async
            send_sms_async.delay(str(application.phone_number), sms_message)
            logger.info(f"Status notification sent for application {application_id}")
            return {'status': 'sent', 'application_id': application_id}
        else:
            logger.warning(f"No phone number for application {application_id}")
            return {'status': 'no_phone', 'application_id': application_id}
    except FarmApplication.DoesNotExist:
        logger.error(f"Application not found: {application_id}")
        return {'status': 'error', 'error': 'Application not found'}


@shared_task
def notify_batch_enrollment_status(enrollment_id: str, new_status: str, message: str = None):
    """
    Notify farmer of batch enrollment status change.
    
    Usage:
        from farms.tasks import notify_batch_enrollment_status
        notify_batch_enrollment_status.delay(str(enrollment.id), 'approved')
    """
    from farms.batch_enrollment_models import BatchEnrollmentApplication
    
    logger.info(f"Notifying enrollment {enrollment_id} of status: {new_status}")
    
    try:
        enrollment = BatchEnrollmentApplication.objects.select_related(
            'farm__owner', 'batch'
        ).get(pk=enrollment_id)
        
        farmer_phone = enrollment.farm.owner.phone_number if enrollment.farm.owner else None
        batch_name = enrollment.batch.name if enrollment.batch else "the program"
        
        default_messages = {
            'approved': f"Your enrollment in {batch_name} has been approved! "
                       f"Check your dashboard for next steps.",
            'rejected': f"Your enrollment application for {batch_name} was not approved. "
                       f"Contact your extension officer for details.",
            'pending': f"Your enrollment for {batch_name} is being reviewed.",
            'waitlisted': f"You've been waitlisted for {batch_name}. "
                         f"We'll notify you if a spot opens up."
        }
        
        sms_message = message or default_messages.get(new_status.lower(), f"Enrollment status: {new_status}")
        
        if farmer_phone:
            from core.tasks import send_sms_async
            send_sms_async.delay(str(farmer_phone), sms_message)
            logger.info(f"Enrollment notification sent for {enrollment_id}")
            return {'status': 'sent', 'enrollment_id': enrollment_id}
        else:
            logger.warning(f"No phone number for enrollment {enrollment_id}")
            return {'status': 'no_phone', 'enrollment_id': enrollment_id}
    except BatchEnrollmentApplication.DoesNotExist:
        logger.error(f"Enrollment not found: {enrollment_id}")
        return {'status': 'error', 'error': 'Enrollment not found'}


@shared_task
def check_pending_applications():
    """
    Check for applications that have been pending too long.
    
    Sends alerts to admins about stale applications.
    """
    from farms.application_models import FarmApplication
    
    logger.info("Checking for stale pending applications...")
    
    cutoff_date = timezone.now() - timedelta(days=7)  # Pending > 7 days
    
    stale_applications = FarmApplication.objects.filter(
        application_status='Pending',
        created_at__lt=cutoff_date
    )
    
    count = stale_applications.count()
    
    if count > 0:
        logger.warning(f"Found {count} stale pending applications (>7 days)")
        
        # Could send admin notification here
        # For now, just return the count
    
    return {
        'stale_applications': count,
        'cutoff_days': 7,
        'checked_at': timezone.now().isoformat()
    }


@shared_task
def sync_farmer_locations():
    """
    Sync farmer location data from farms to user profiles.
    
    Ensures User model has accurate location data for filtering.
    Can be run periodically to catch any missed updates.
    """
    from farms.models import Farm, FarmLocation
    from accounts.models import User
    
    logger.info("Syncing farmer locations...")
    
    synced = 0
    farmers = User.objects.filter(
        Q(region__isnull=True) | Q(region=''),
        role='FARMER',
        is_active=True
    ).prefetch_related('farms')
    
    for farmer in farmers:
        farm = farmer.farms.first()
        if farm:
            location = getattr(farm, 'location', None)
            
            updated = False
            if location:
                if location.region and not farmer.region:
                    farmer.region = location.region
                    updated = True
                if location.district and not farmer.district:
                    farmer.district = location.district
                    updated = True
                if location.constituency and not farmer.constituency:
                    farmer.constituency = location.constituency
                    updated = True
            else:
                # Fall back to farm-level location
                if farm.region and not farmer.region:
                    farmer.region = farm.region
                    updated = True
                if farm.district and not farmer.district:
                    farmer.district = farm.district
                    updated = True
            
            if updated:
                farmer.save(update_fields=['region', 'district', 'constituency'])
                synced += 1
    
    logger.info(f"Synced locations for {synced} farmers")
    return {'synced': synced}


@shared_task
def calculate_farm_scores():
    """
    Calculate and update farm readiness and biosecurity scores.
    
    Runs periodically to keep scores current.
    """
    from farms.models import Farm, FarmInfrastructure
    
    logger.info("Calculating farm scores...")
    
    updated = 0
    farms = Farm.objects.filter(
        application_status='Approved'
    ).select_related('infrastructure')
    
    for farm in farms:
        try:
            # Calculate biosecurity score
            infrastructure = getattr(farm, 'infrastructure', None)
            if infrastructure:
                total_measures = 0
                active_measures = 0
                
                biosecurity_fields = [
                    'footbath_at_entry',
                    'proper_ventilation',
                    'perimeter_fence',
                ]
                
                for field in biosecurity_fields:
                    if hasattr(infrastructure, field):
                        total_measures += 1
                        if getattr(infrastructure, field, False):
                            active_measures += 1
                
                if total_measures > 0:
                    farm.biosecurity_score = (active_measures / total_measures) * 100
            
            # Calculate readiness score (simplified)
            readiness_factors = [
                farm.application_status == 'Approved',
                farm.farm_status == 'Active',
                bool(farm.bird_capacity and farm.bird_capacity > 0),
                hasattr(farm, 'infrastructure'),
            ]
            
            farm.farm_readiness_score = (sum(readiness_factors) / len(readiness_factors)) * 100
            farm.save(update_fields=['biosecurity_score', 'farm_readiness_score'])
            updated += 1
        except Exception as exc:
            logger.error(f"Failed to calculate scores for farm {farm.id}: {exc}")
    
    logger.info(f"Updated scores for {updated} farms")
    return {'updated': updated}


@shared_task
def generate_farm_activity_report(farm_id: str, days: int = 30, email: str = None):
    """
    Generate an activity report for a specific farm.
    
    Includes production data, orders, and events.
    """
    from farms.models import Farm
    from flock_management.models import DailyFlockRecord
    from sales_revenue.models import Order
    from django.db.models import Sum, Count
    from django.core.cache import cache
    
    logger.info(f"Generating activity report for farm {farm_id}")
    
    try:
        farm = Farm.objects.get(pk=farm_id)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Production data
        production = DailyFlockRecord.objects.filter(
            flock_batch__farm=farm,
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(
            total_eggs=Sum('eggs_collected'),
            total_mortality=Sum('mortality_count'),
            record_count=Count('id')
        )
        
        # Order data
        orders = Order.objects.filter(
            farm=farm,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('total_amount'),
            completed_orders=Count('id', filter=Q(status='completed'))
        )
        
        report = {
            'farm_id': str(farm.id),
            'farm_name': farm.farm_name,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'production': {
                'total_eggs': production['total_eggs'] or 0,
                'total_mortality': production['total_mortality'] or 0,
                'records_logged': production['record_count'] or 0,
            },
            'sales': {
                'total_orders': orders['total_orders'] or 0,
                'completed_orders': orders['completed_orders'] or 0,
                'total_revenue': float(orders['total_revenue'] or 0),
            },
            'generated_at': timezone.now().isoformat()
        }
        
        # Cache the report
        cache_key = f'report:farm_activity:{farm_id}:{days}'
        cache.set(cache_key, report, timeout=86400)
        
        # Send email if requested
        if email:
            from core.tasks import send_email_async
            send_email_async.delay(
                subject=f"Farm Activity Report - {farm.farm_name}",
                message=f"""
Farm Activity Report for {farm.farm_name}
Period: {start_date} to {end_date}

Production:
- Total Eggs: {report['production']['total_eggs']}
- Total Mortality: {report['production']['total_mortality']}
- Days Logged: {report['production']['records_logged']}

Sales:
- Total Orders: {report['sales']['total_orders']}
- Completed: {report['sales']['completed_orders']}
- Revenue: GHS {report['sales']['total_revenue']:.2f}

Report generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}
                """,
                recipient_list=[email]
            )
        
        logger.info(f"Activity report generated for farm {farm_id}")
        return {'status': 'success', 'cache_key': cache_key}
    except Farm.DoesNotExist:
        logger.error(f"Farm not found: {farm_id}")
        return {'status': 'error', 'error': 'Farm not found'}
    except Exception as exc:
        logger.error(f"Failed to generate activity report: {exc}")
        return {'status': 'error', 'error': str(exc)}
