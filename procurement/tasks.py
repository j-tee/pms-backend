"""
Procurement Celery Tasks

Background tasks for:
- Daily distress score calculation
- Distress alerts and notifications
- Procurement analytics aggregation
"""

from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def calculate_all_farm_distress_scores(self):
    """
    Daily task to recalculate distress scores for all active farms.
    
    Runs at midnight to update the cached distress scores on Farm model
    and record history in FarmDistressHistory.
    
    Schedule in celery beat:
        'calculate-distress-scores': {
            'task': 'procurement.tasks.calculate_all_farm_distress_scores',
            'schedule': crontab(hour=0, minute=0),  # Midnight daily
        }
    """
    from farms.models import Farm
    from procurement.models import FarmDistressHistory
    from procurement.services.farmer_distress_v2 import FarmerDistressService
    
    logger.info("Starting daily distress score calculation...")
    
    service = FarmerDistressService(days_lookback=30)
    
    # Get all active, approved farms
    farms = Farm.objects.filter(
        farm_status='Active',
        application_status='Approved - Farm ID Assigned'
    ).select_related('user')
    
    total_farms = farms.count()
    processed = 0
    errors = 0
    
    critical_farms = []
    high_distress_farms = []
    
    for farm in farms.iterator(chunk_size=100):
        try:
            with transaction.atomic():
                # Calculate distress score
                assessment = service.calculate_distress_score(farm)
                
                # Update cached fields on Farm model
                farm.distress_score = int(assessment['distress_score'])
                farm.distress_level = assessment['distress_level']
                farm.distress_last_calculated = timezone.now()
                
                # Update quick-access metrics
                if assessment['sales_history']:
                    farm.days_since_last_sale = assessment['sales_history'].get('days_since_sale') or 0
                
                if assessment['capacity']:
                    farm.unsold_inventory_count = assessment['capacity'].get('available_for_sale', 0)
                
                # Get inventory stagnation from factors
                for factor in assessment.get('distress_factors', []):
                    if factor['factor'] == 'INVENTORY_STAGNATION':
                        # Extract days from detail if available
                        detail = factor.get('detail', '')
                        if 'days' in detail:
                            try:
                                import re
                                days_match = re.search(r'(\d+)\s*days', detail)
                                if days_match:
                                    farm.inventory_stagnation_days = int(days_match.group(1))
                            except:
                                pass
                
                farm.save(update_fields=[
                    'distress_score',
                    'distress_level',
                    'distress_last_calculated',
                    'days_since_last_sale',
                    'unsold_inventory_count',
                    'inventory_stagnation_days',
                ])
                
                # Record history
                FarmDistressHistory.record(
                    farm=farm,
                    assessment=assessment,
                    calculated_by='system_daily'
                )
                
                # Track critical/high distress for alerts
                if assessment['distress_level'] == 'CRITICAL':
                    critical_farms.append({
                        'farm_id': str(farm.id),
                        'farm_name': farm.farm_name,
                        'score': assessment['distress_score'],
                        'region': farm.region,
                    })
                elif assessment['distress_level'] == 'HIGH':
                    high_distress_farms.append({
                        'farm_id': str(farm.id),
                        'farm_name': farm.farm_name,
                        'score': assessment['distress_score'],
                    })
                
                processed += 1
                
        except Exception as e:
            logger.error(f"Error calculating distress for farm {farm.id}: {e}")
            errors += 1
    
    # Log summary
    logger.info(
        f"Distress calculation complete. "
        f"Processed: {processed}/{total_farms}, "
        f"Errors: {errors}, "
        f"Critical: {len(critical_farms)}, "
        f"High: {len(high_distress_farms)}"
    )
    
    # Trigger alerts if there are critical farms
    if critical_farms:
        send_distress_alerts.delay(critical_farms)
    
    return {
        'total_farms': total_farms,
        'processed': processed,
        'errors': errors,
        'critical_count': len(critical_farms),
        'high_count': len(high_distress_farms),
    }


@shared_task(bind=True)
def calculate_single_farm_distress(self, farm_id: str, calculated_by: str = 'api'):
    """
    Calculate distress score for a single farm.
    
    Called on-demand when procurement officer views a farm or
    when farm data is updated.
    
    Args:
        farm_id: UUID of the farm
        calculated_by: Who triggered ('api', 'officer', 'webhook')
    """
    from farms.models import Farm
    from procurement.models import FarmDistressHistory
    from procurement.services.farmer_distress_v2 import FarmerDistressService
    
    try:
        farm = Farm.objects.get(id=farm_id)
    except Farm.DoesNotExist:
        logger.warning(f"Farm {farm_id} not found for distress calculation")
        return {'success': False, 'error': f'Farm {farm_id} not found'}
    
    service = FarmerDistressService(days_lookback=30)
    
    with transaction.atomic():
        assessment = service.calculate_distress_score(farm)
        
        # Update cached fields
        farm.distress_score = int(assessment['distress_score'])
        farm.distress_level = assessment['distress_level']
        farm.distress_last_calculated = timezone.now()
        
        if assessment['sales_history']:
            farm.days_since_last_sale = assessment['sales_history'].get('days_since_sale') or 0
        
        if assessment['capacity']:
            farm.unsold_inventory_count = assessment['capacity'].get('available_for_sale', 0)
        
        farm.save(update_fields=[
            'distress_score',
            'distress_level',
            'distress_last_calculated',
            'days_since_last_sale',
            'unsold_inventory_count',
        ])
        
        # Record history
        FarmDistressHistory.record(
            farm=farm,
            assessment=assessment,
            calculated_by=calculated_by
        )
    
    return assessment


@shared_task(bind=True)
def send_distress_alerts(self, critical_farms: list):
    """
    Send alerts about critically distressed farms to procurement officers.
    
    This could send:
    - Email to national procurement officers
    - SMS to regional officers
    - In-app notifications
    """
    from accounts.models import User
    
    if not critical_farms:
        return
    
    logger.info(f"Sending distress alerts for {len(critical_farms)} critical farms")
    
    # Get procurement officers
    officers = User.objects.filter(
        role__in=['PROCUREMENT_OFFICER', 'NATIONAL_ADMIN'],
        is_active=True
    )
    
    # For now, just log - actual notification implementation depends on
    # the notification system in place
    for officer in officers:
        logger.info(
            f"Would notify {officer.get_full_name()} about {len(critical_farms)} "
            f"critically distressed farms"
        )
    
    # TODO: Integrate with actual notification system
    # from core.notifications import send_notification
    # send_notification(
    #     users=officers,
    #     title="Critical Farmer Distress Alert",
    #     message=f"{len(critical_farms)} farmers need urgent procurement support",
    #     notification_type="distress_alert",
    #     data={'farms': critical_farms}
    # )
    
    return {'officers_notified': officers.count(), 'farms': len(critical_farms)}


@shared_task(bind=True)
def record_intervention_impact(self, farm_id: str, intervention_type: str,
                                 intervention_value: float = None,
                                 intervention_reference: str = None):
    """
    Record distress score after an intervention to measure impact.
    
    Called after:
    - Procurement assignment is made
    - Training/extension visit completed
    - Support package distributed
    
    Args:
        farm_id: UUID of the farm
        intervention_type: Type of intervention (PROCUREMENT, LOAN, TRAINING, etc.)
        intervention_value: Monetary value of intervention
        intervention_reference: Reference ID (order number, etc.)
    """
    from farms.models import Farm
    from procurement.models import FarmDistressHistory
    from procurement.services.farmer_distress_v2 import FarmerDistressService
    from decimal import Decimal
    
    try:
        farm = Farm.objects.get(id=farm_id)
    except Farm.DoesNotExist:
        logger.warning(f"Farm {farm_id} not found for intervention recording")
        return None
    
    service = FarmerDistressService(days_lookback=30)
    assessment = service.calculate_distress_score(farm)
    
    # Record with intervention info
    record = FarmDistressHistory.record(
        farm=farm,
        assessment=assessment,
        intervention_type=intervention_type,
        intervention_value=Decimal(str(intervention_value)) if intervention_value else None,
        intervention_reference=intervention_reference,
        calculated_by='intervention_tracker'
    )
    
    logger.info(
        f"Recorded intervention impact for farm {farm.farm_name}: "
        f"{intervention_type} - Score: {assessment['distress_score']}"
    )
    
    return {
        'farm_id': str(farm.id),
        'distress_score': assessment['distress_score'],
        'intervention_type': intervention_type,
        'record_id': str(record.id),
    }


@shared_task(bind=True)
def generate_distress_analytics(self, period_days: int = 30):
    """
    Generate aggregate distress analytics for reporting.
    
    Creates summary statistics for procurement dashboard.
    """
    from farms.models import Farm
    from procurement.models import FarmDistressHistory, OrderAssignment
    from django.db.models import Count, Avg, Sum
    from django.db.models.functions import TruncDate
    
    cutoff = timezone.now() - timezone.timedelta(days=period_days)
    
    # Current state from Farm model
    farms = Farm.objects.filter(
        farm_status='Active',
        application_status='Approved - Farm ID Assigned'
    )
    
    current_stats = farms.aggregate(
        total_farms=Count('id'),
        avg_distress=Avg('distress_score'),
        critical_count=Count('id', filter=Q(distress_level='CRITICAL')),
        high_count=Count('id', filter=Q(distress_level='HIGH')),
        moderate_count=Count('id', filter=Q(distress_level='MODERATE')),
    )
    
    # Interventions in period
    from django.db.models import Q
    
    interventions = OrderAssignment.objects.filter(
        assigned_at__gte=cutoff,
        status__in=['accepted', 'verified', 'paid', 'completed']
    ).aggregate(
        total_assignments=Count('id'),
        unique_farms=Count('farm', distinct=True),
        total_value=Sum('total_value'),
        distressed_farms=Count('id', filter=Q(farmer_distress_level__in=['CRITICAL', 'HIGH'])),
    )
    
    # Score trends from history
    history_trend = FarmDistressHistory.objects.filter(
        recorded_at__gte=cutoff,
        calculated_by='system_daily'
    ).annotate(
        date=TruncDate('recorded_at')
    ).values('date').annotate(
        avg_score=Avg('distress_score'),
        farm_count=Count('farm', distinct=True),
    ).order_by('date')
    
    return {
        'period_days': period_days,
        'current_state': current_stats,
        'interventions': interventions,
        'trend': list(history_trend),
        'generated_at': timezone.now().isoformat(),
    }
