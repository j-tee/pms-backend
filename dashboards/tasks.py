"""
Dashboard Celery tasks for YEA Poultry Management System.

Background tasks for analytics aggregation and report generation.
These tasks cache expensive queries to improve dashboard performance.
"""
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def aggregate_daily_metrics():
    """
    Aggregate daily dashboard metrics and cache them.
    
    Scheduled via Celery Beat to run at 1 AM daily.
    This pre-computes expensive queries for fast dashboard loading.
    """
    from dashboards.services import YEAAnalyticsService
    
    logger.info("Starting daily metrics aggregation...")
    
    try:
        service = YEAAnalyticsService()
        
        # Cache executive overview (most requested)
        overview = service.get_executive_overview()
        cache.set('dashboard:executive_overview', overview, timeout=86400)  # 24 hours
        
        # Cache application pipeline
        pipeline = service.get_application_pipeline()
        cache.set('dashboard:application_pipeline', pipeline, timeout=86400)
        
        # Cache production overview
        production = service.get_production_overview()
        cache.set('dashboard:production_overview', production, timeout=86400)
        
        # Cache production trend (last 30 days)
        trend = service.get_production_trend(days=30)
        cache.set('dashboard:production_trend_30d', trend, timeout=86400)
        
        # Cache marketplace activity
        marketplace = service.get_marketplace_activity()
        cache.set('dashboard:marketplace_activity', marketplace, timeout=86400)
        
        # Cache alerts
        alerts = service.get_alerts()
        cache.set('dashboard:alerts', alerts, timeout=3600)  # 1 hour - alerts need fresher data
        
        logger.info("Daily metrics aggregation completed successfully")
        return {
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'cached_keys': [
                'dashboard:executive_overview',
                'dashboard:application_pipeline', 
                'dashboard:production_overview',
                'dashboard:production_trend_30d',
                'dashboard:marketplace_activity',
                'dashboard:alerts'
            ]
        }
    except Exception as exc:
        logger.error(f"Daily metrics aggregation failed: {exc}")
        return {'status': 'error', 'error': str(exc)}


@shared_task
def aggregate_regional_metrics():
    """
    Aggregate metrics per region for regional dashboards.
    
    Can be called manually or scheduled as needed.
    """
    from dashboards.services import YEAAnalyticsService
    from accounts.models import User
    
    logger.info("Starting regional metrics aggregation...")
    
    try:
        # Get unique regions from regional coordinators
        regions = User.objects.filter(
            role='REGIONAL_COORDINATOR'
        ).values_list('region', flat=True).distinct()
        
        for region in regions:
            if region:
                service = YEAAnalyticsService(region=region)
                overview = service.get_executive_overview()
                cache.set(f'dashboard:region:{region}:overview', overview, timeout=86400)
        
        logger.info(f"Regional metrics aggregation completed for {len(regions)} regions")
        return {'status': 'success', 'regions_processed': len(list(regions))}
    except Exception as exc:
        logger.error(f"Regional metrics aggregation failed: {exc}")
        return {'status': 'error', 'error': str(exc)}


@shared_task
def generate_weekly_report():
    """
    Generate weekly summary report for YEA administrators.
    
    Scheduled via Celery Beat to run Monday at 6 AM.
    """
    from dashboards.services import YEAAnalyticsService
    from django.core.mail import send_mail
    from django.conf import settings
    from accounts.models import User
    
    logger.info("Starting weekly report generation...")
    
    try:
        service = YEAAnalyticsService()
        
        # Gather weekly data
        overview = service.get_executive_overview()
        pipeline = service.get_application_pipeline()
        production = service.get_production_overview()
        marketplace = service.get_marketplace_activity()
        
        # Calculate week-over-week changes
        week_start = timezone.now() - timedelta(days=7)
        week_end = timezone.now()
        
        report_data = {
            'period': {
                'start': week_start.isoformat(),
                'end': week_end.isoformat(),
            },
            'executive_overview': overview,
            'application_pipeline': pipeline,
            'production_overview': production,
            'marketplace_activity': marketplace,
            'generated_at': timezone.now().isoformat(),
        }
        
        # Cache the report
        cache.set('dashboard:weekly_report:latest', report_data, timeout=604800)  # 7 days
        
        # Get YEA admin emails for notification
        yea_admin_emails = list(User.objects.filter(
            role__in=['SUPER_ADMIN', 'YEA_OFFICIAL', 'NATIONAL_ADMIN'],
            is_active=True,
            email__isnull=False
        ).exclude(email='').values_list('email', flat=True))
        
        if yea_admin_emails and hasattr(settings, 'DEFAULT_FROM_EMAIL'):
            # Send notification email (actual email template would be HTML)
            try:
                send_mail(
                    subject=f"YEA PMS Weekly Report - {week_end.strftime('%B %d, %Y')}",
                    message=f"""
Weekly Summary Report
=====================

Total Farmers: {overview.get('total_farmers', 0)}
Active Farms: {overview.get('active_farms', 0)}
Total Birds: {overview.get('total_birds', 0)}
Total Eggs This Week: {production.get('total_eggs_today', 0)}

New Applications: {pipeline.get('pending_applications', 0)}
Marketplace Orders: {marketplace.get('orders_this_month', 0)}

View the full report in the admin dashboard.
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=yea_admin_emails[:5],  # Limit to first 5 admins
                    fail_silently=True,
                )
                logger.info(f"Weekly report email sent to {len(yea_admin_emails[:5])} admins")
            except Exception as mail_exc:
                logger.warning(f"Failed to send weekly report email: {mail_exc}")
        
        logger.info("Weekly report generation completed")
        return {'status': 'success', 'report_cached': True}
    except Exception as exc:
        logger.error(f"Weekly report generation failed: {exc}")
        return {'status': 'error', 'error': str(exc)}


@shared_task
def refresh_dashboard_cache(cache_keys: list = None):
    """
    Manually refresh specific dashboard cache keys.
    
    Usage:
        from dashboards.tasks import refresh_dashboard_cache
        refresh_dashboard_cache.delay(['executive_overview', 'alerts'])
    """
    from dashboards.services import YEAAnalyticsService
    
    service = YEAAnalyticsService()
    
    all_keys = {
        'executive_overview': lambda: service.get_executive_overview(),
        'application_pipeline': lambda: service.get_application_pipeline(),
        'production_overview': lambda: service.get_production_overview(),
        'production_trend': lambda: service.get_production_trend(days=30),
        'marketplace_activity': lambda: service.get_marketplace_activity(),
        'alerts': lambda: service.get_alerts(),
        'watchlist': lambda: service.get_watchlist(),
    }
    
    keys_to_refresh = cache_keys or list(all_keys.keys())
    refreshed = []
    
    for key in keys_to_refresh:
        if key in all_keys:
            try:
                data = all_keys[key]()
                timeout = 3600 if key == 'alerts' else 86400
                cache.set(f'dashboard:{key}', data, timeout=timeout)
                refreshed.append(key)
            except Exception as exc:
                logger.error(f"Failed to refresh {key}: {exc}")
    
    return {'refreshed': refreshed, 'requested': keys_to_refresh}


@shared_task
def generate_production_report(farm_id: str, date_from: str, date_to: str, email: str = None):
    """
    Generate a production report for a specific farm.
    
    Can be requested by farmers or admins.
    
    Usage:
        from dashboards.tasks import generate_production_report
        generate_production_report.delay(
            'farm-uuid',
            '2024-01-01',
            '2024-01-31',
            'farmer@example.com'
        )
    """
    from farms.models import Farm
    from flock_management.models import FlockBatch, DailyFlockRecord
    from django.db.models import Sum
    
    logger.info(f"Generating production report for farm {farm_id}")
    
    try:
        farm = Farm.objects.get(pk=farm_id)
        
        records = DailyFlockRecord.objects.filter(
            flock_batch__farm=farm,
            date__gte=date_from,
            date__lte=date_to
        ).aggregate(
            total_eggs=Sum('eggs_collected'),
            total_mortality=Sum('mortality_count'),
        )
        
        report = {
            'farm_id': str(farm.id),
            'farm_name': farm.farm_name,
            'period': {'from': date_from, 'to': date_to},
            'production': records,
            'generated_at': timezone.now().isoformat(),
        }
        
        # Cache the report for retrieval
        cache_key = f'report:production:{farm_id}:{date_from}:{date_to}'
        cache.set(cache_key, report, timeout=86400)
        
        # Send email if requested
        if email:
            from core.tasks import send_email_async
            send_email_async.delay(
                subject=f"Production Report - {farm.farm_name}",
                message=f"""
Production Report for {farm.farm_name}
Period: {date_from} to {date_to}

Total Eggs: {records.get('total_eggs') or 0}
Total Mortality: {records.get('total_mortality') or 0}

Report generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}
                """,
                recipient_list=[email]
            )
        
        logger.info(f"Production report generated for farm {farm_id}")
        return {'status': 'success', 'cache_key': cache_key}
    except Farm.DoesNotExist:
        logger.error(f"Farm not found: {farm_id}")
        return {'status': 'error', 'error': 'Farm not found'}
    except Exception as exc:
        logger.error(f"Failed to generate production report: {exc}")
        return {'status': 'error', 'error': str(exc)}


# =============================================================================
# NATIONAL ADMIN / MINISTER REPORT TASKS
# =============================================================================

@shared_task
def precompute_national_admin_reports():
    """
    Pre-compute all National Admin reports for fast access.
    
    Scheduled via Celery Beat to run at 2 AM daily.
    This ensures the Minister/National Admin dashboard loads instantly.
    """
    from dashboards.services.national_admin_analytics import NationalAdminAnalyticsService
    from farms.models import FarmLocation
    
    logger.info("Starting National Admin reports pre-computation...")
    
    try:
        service = NationalAdminAnalyticsService(use_cache=False)
        
        # Pre-compute national-level reports
        reports = {
            'executive_dashboard': service.get_executive_dashboard(),
            'program_performance': service.get_program_performance_overview(),
            'production_overview': service.get_production_overview(days=30),
            'regional_comparison': service.get_regional_production_comparison(),
            'financial_overview': service.get_financial_overview(days=30),
            'flock_health': service.get_flock_health_overview(days=30),
            'food_security': service.get_food_security_metrics(),
            'farmer_welfare': service.get_farmer_welfare_metrics(),
            'operational': service.get_operational_metrics(),
            'enrollment_trend': service.get_enrollment_trend(months=12),
        }
        
        # Cache each report with appropriate TTL
        for key, data in reports.items():
            cache.set(f'national_admin:{key}', data, timeout=86400)
        
        logger.info("National-level reports pre-computed successfully")
        
        # Pre-compute regional reports for each region
        regions = list(
            FarmLocation.objects.filter(is_primary_location=True)
            .values_list('region', flat=True)
            .distinct()
        )
        
        for region in regions:
            if not region:
                continue
            try:
                regional_service = NationalAdminAnalyticsService(use_cache=False)
                regional_data = {
                    'executive_dashboard': regional_service.get_executive_dashboard(region=region),
                    'production_overview': regional_service.get_production_overview(region=region, days=30),
                    'financial_overview': regional_service.get_financial_overview(region=region, days=30),
                }
                for key, data in regional_data.items():
                    cache.set(f'national_admin:{key}:{region}', data, timeout=86400)
            except Exception as region_exc:
                logger.warning(f"Failed to pre-compute for region {region}: {region_exc}")
        
        logger.info(f"Regional reports pre-computed for {len(regions)} regions")
        
        return {
            'status': 'success',
            'national_reports': list(reports.keys()),
            'regions_processed': len([r for r in regions if r]),
            'timestamp': timezone.now().isoformat(),
        }
        
    except Exception as exc:
        logger.error(f"National Admin reports pre-computation failed: {exc}")
        return {'status': 'error', 'error': str(exc)}


@shared_task
def generate_minister_report(
    report_type: str,
    region: str = None,
    constituency: str = None,
    format: str = 'json'
) -> dict:
    """
    Generate on-demand report for Minister/National Admin.
    
    Args:
        report_type: Type of report to generate
        region: Optional region filter
        constituency: Optional constituency filter
        format: Output format (json, for caching)
    
    Returns:
        dict: Report data or cache key
    """
    from dashboards.services.national_admin_analytics import NationalAdminAnalyticsService
    
    logger.info(f"Generating {report_type} report (region={region}, constituency={constituency})")
    
    try:
        service = NationalAdminAnalyticsService(use_cache=False)
        
        report_methods = {
            'executive_dashboard': lambda: service.get_executive_dashboard(region, constituency),
            'program_performance': lambda: service.get_program_performance_overview(region, constituency),
            'production': lambda: service.get_production_overview(region, constituency),
            'financial': lambda: service.get_financial_overview(region, constituency),
            'flock_health': lambda: service.get_flock_health_overview(region, constituency),
            'food_security': lambda: service.get_food_security_metrics(region, constituency),
            'procurement': lambda: service.get_procurement_overview(region, constituency),
            'farmer_welfare': lambda: service.get_farmer_welfare_metrics(region, constituency),
            'operational': lambda: service.get_operational_metrics(region, constituency),
            'regional_comparison': lambda: service.get_regional_production_comparison(),
            'enrollment_trend': lambda: service.get_enrollment_trend(12, region, constituency),
        }
        
        if report_type not in report_methods:
            return {'status': 'error', 'error': f'Unknown report type: {report_type}'}
        
        data = report_methods[report_type]()
        
        # Cache the result
        cache_key = f"national_admin:ondemand:{report_type}:{region or 'national'}:{constituency or 'all'}"
        cache.set(cache_key, data, timeout=1800)  # 30 minutes
        
        logger.info(f"Report {report_type} generated and cached")
        return {
            'status': 'success',
            'cache_key': cache_key,
            'data': data,
        }
        
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        return {'status': 'error', 'error': str(exc)}


@shared_task
def refresh_national_admin_cache(report_types: list = None, region: str = None):
    """
    Manually refresh specific National Admin cache entries.
    
    Usage:
        from dashboards.tasks import refresh_national_admin_cache
        refresh_national_admin_cache.delay(['executive_dashboard', 'production'])
        refresh_national_admin_cache.delay(region='Greater Accra')
    """
    from dashboards.services.national_admin_analytics import NationalAdminAnalyticsService
    
    service = NationalAdminAnalyticsService(use_cache=False)
    
    all_reports = {
        'executive_dashboard': lambda: service.get_executive_dashboard(region),
        'program_performance': lambda: service.get_program_performance_overview(region),
        'production_overview': lambda: service.get_production_overview(region=region),
        'financial_overview': lambda: service.get_financial_overview(region=region),
        'flock_health': lambda: service.get_flock_health_overview(region=region),
        'food_security': lambda: service.get_food_security_metrics(region),
        'farmer_welfare': lambda: service.get_farmer_welfare_metrics(region),
        'operational': lambda: service.get_operational_metrics(region),
    }
    
    types_to_refresh = report_types or list(all_reports.keys())
    refreshed = []
    
    for report_type in types_to_refresh:
        if report_type in all_reports:
            try:
                data = all_reports[report_type]()
                cache_key = f'national_admin:{report_type}'
                if region:
                    cache_key += f':{region}'
                cache.set(cache_key, data, timeout=86400)
                refreshed.append(report_type)
            except Exception as exc:
                logger.error(f"Failed to refresh {report_type}: {exc}")
    
    return {'refreshed': refreshed, 'requested': types_to_refresh}
