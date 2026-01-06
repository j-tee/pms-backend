"""
YEA Admin Analytics Service

Comprehensive analytics for YEA Administrators (NATIONAL_ADMIN and above).
Provides program-level insights for monitoring the poultry development program.

Access Control:
- SUPER_ADMIN: Full access + Platform Revenue
- YEA_OFFICIAL: Full access + Platform Revenue  
- NATIONAL_ADMIN: Full access (no platform revenue)
- REGIONAL_COORDINATOR: Region-filtered access
- CONSTITUENCY_OFFICIAL: Constituency-filtered access
"""

from django.db.models import Sum, Count, Avg, Q, F, Case, When, Value, DecimalField
from django.db.models.functions import TruncMonth, TruncWeek, TruncDate, Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class YEAAnalyticsService:
    """
    Analytics service for YEA administrators.
    Provides program metrics, production data, and marketplace activity.
    """
    
    def __init__(self, user=None):
        """
        Initialize with optional user for geographic scoping.
        
        Args:
            user: The requesting user (for role-based filtering)
        """
        self.user = user
        self.now = timezone.now()
        self.today = self.now.date()
    
    def _get_farm_queryset(self):
        """Get farm queryset with geographic filtering based on user role."""
        from farms.models import Farm
        
        qs = Farm.objects.all()
        
        if not self.user:
            return qs
        
        # Apply geographic filtering based on role
        if self.user.role == 'REGIONAL_COORDINATOR' and self.user.region:
            # Filter by region through FarmLocation
            qs = qs.filter(
                Q(locations__region__icontains=self.user.region) |
                Q(primary_constituency__region__name__icontains=self.user.region)
            ).distinct()
        elif self.user.role == 'CONSTITUENCY_OFFICIAL' and self.user.constituency:
            qs = qs.filter(primary_constituency=self.user.constituency)
        
        return qs
    
    def _get_application_queryset(self):
        """Get application queryset with geographic filtering."""
        from farms.application_models import FarmApplication
        
        qs = FarmApplication.objects.all()
        
        if not self.user:
            return qs
        
        if self.user.role == 'REGIONAL_COORDINATOR' and self.user.region:
            qs = qs.filter(region__icontains=self.user.region)
        elif self.user.role == 'CONSTITUENCY_OFFICIAL' and self.user.constituency:
            qs = qs.filter(primary_constituency=self.user.constituency)
        
        return qs
    
    # =========================================================================
    # EXECUTIVE OVERVIEW
    # =========================================================================
    
    def get_executive_overview(self):
        """
        Get high-level executive metrics for dashboard cards.
        
        Returns:
            dict: Key metrics for executive overview
        """
        farms = self._get_farm_queryset()
        applications = self._get_application_queryset()
        
        from flock_management.models import DailyProduction, Flock
        from sales_revenue.marketplace_models import MarketplaceOrder
        from accounts.models import User
        
        # Date ranges
        last_30_days = self.now - timedelta(days=30)
        last_7_days = self.now - timedelta(days=7)
        this_month_start = self.today.replace(day=1)
        
        # Farm metrics
        total_farmers = User.objects.filter(role='FARMER').count()
        total_farms = farms.count()
        approved_farms = farms.filter(application_status='Approved').count()
        operational_farms = farms.filter(farm_status='Operational').count()
        
        # Bird metrics
        total_birds = farms.aggregate(
            total=Coalesce(Sum('current_bird_count'), 0)
        )['total']
        
        # Get flocks for capacity
        farm_ids = farms.values_list('id', flat=True)
        active_flocks = Flock.objects.filter(
            farm_id__in=farm_ids,
            status='active'
        )
        total_capacity = farms.aggregate(
            total=Coalesce(Sum('total_bird_capacity'), 0)
        )['total']
        
        # Production metrics (this month)
        monthly_production = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=this_month_start
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            total_good_eggs=Coalesce(Sum('good_eggs'), 0),
            total_mortality=Coalesce(Sum('birds_died'), 0)
        )
        
        # Application metrics
        pending_applications = applications.filter(
            status__in=['submitted', 'constituency_review', 'regional_review', 'national_review']
        ).count()
        
        # Marketplace metrics (this month) - farmer transaction volume, NOT platform revenue
        marketplace_orders = MarketplaceOrder.objects.filter(
            farm_id__in=farm_ids,
            created_at__gte=this_month_start,
            status__in=['confirmed', 'processing', 'ready', 'shipped', 'delivered', 'completed']
        )
        
        marketplace_stats = marketplace_orders.aggregate(
            order_count=Count('id'),
            total_volume=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )
        
        return {
            'farmers': {
                'total': total_farmers,
                'active': operational_farms,
                'new_this_month': farms.filter(created_at__gte=this_month_start).count()
            },
            'farms': {
                'total': total_farms,
                'approved': approved_farms,
                'operational': operational_farms,
                'pending_setup': farms.filter(farm_status='Pending Setup').count()
            },
            'birds': {
                'total': total_birds,
                'capacity': total_capacity,
                'utilization_percent': round((total_birds / total_capacity * 100), 1) if total_capacity > 0 else 0
            },
            'production': {
                'eggs_this_month': monthly_production['total_eggs'],
                'good_eggs_this_month': monthly_production['total_good_eggs'],
                'mortality_this_month': monthly_production['total_mortality']
            },
            'applications': {
                'pending': pending_applications,
                'submitted': applications.filter(status='submitted').count(),
                'constituency_review': applications.filter(status='constituency_review').count(),
                'regional_review': applications.filter(status='regional_review').count(),
                'national_review': applications.filter(status='national_review').count()
            },
            'marketplace': {
                'orders_this_month': marketplace_stats['order_count'],
                'transaction_volume_ghs': float(marketplace_stats['total_volume'])
            },
            'as_of': self.now.isoformat()
        }
    
    # =========================================================================
    # PROGRAM METRICS
    # =========================================================================
    
    def get_application_pipeline(self):
        """
        Get application pipeline breakdown.
        
        Returns:
            dict: Application counts by status
        """
        applications = self._get_application_queryset()
        
        pipeline = applications.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Convert to dict with display names
        status_map = {
            'submitted': 'Submitted',
            'constituency_review': 'Constituency Review',
            'regional_review': 'Regional Review',
            'national_review': 'National Review',
            'changes_requested': 'Changes Requested',
            'approved': 'Approved',
            'rejected': 'Rejected',
            'account_created': 'Account Created'
        }
        
        result = {status_map.get(item['status'], item['status']): item['count'] 
                  for item in pipeline}
        
        # Calculate totals
        total = sum(result.values())
        pending = sum(result.get(s, 0) for s in ['Submitted', 'Constituency Review', 'Regional Review', 'National Review'])
        approved = result.get('Approved', 0) + result.get('Account Created', 0)
        rejected = result.get('Rejected', 0)
        
        return {
            'pipeline': result,
            'summary': {
                'total': total,
                'pending': pending,
                'approved': approved,
                'rejected': rejected,
                'approval_rate': round((approved / (approved + rejected) * 100), 1) if (approved + rejected) > 0 else 0
            }
        }
    
    def get_registration_trend(self, months=6):
        """
        Get farmer registration trend over time.
        
        Args:
            months: Number of months to include
            
        Returns:
            list: Monthly registration data
        """
        from accounts.models import User
        
        start_date = self.now - timedelta(days=months * 30)
        
        # Get farmer registrations by month
        registrations = User.objects.filter(
            role='FARMER',
            date_joined__gte=start_date
        ).annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        return [
            {
                'month': item['month'].strftime('%Y-%m') if item['month'] else None,
                'registrations': item['count']
            }
            for item in registrations
        ]
    
    def get_farms_by_region(self):
        """
        Get farm distribution by region.
        
        Returns:
            list: Farm counts by region
        """
        farms = self._get_farm_queryset()
        
        # Get region from FarmLocation
        from farms.models import FarmLocation
        
        distribution = FarmLocation.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            is_primary_location=True
        ).values('region').annotate(
            count=Count('farm_id', distinct=True)
        ).order_by('-count')
        
        return [
            {
                'region': item['region'] or 'Unknown',
                'farm_count': item['count']
            }
            for item in distribution
        ]
    
    def get_batch_enrollment_stats(self):
        """
        Get batch/program enrollment statistics.
        
        Returns:
            dict: Batch enrollment metrics
        """
        from farms.batch_enrollment_models import Batch, BatchEnrollmentApplication
        
        active_batches = Batch.objects.filter(is_active=True, is_published=True)
        
        batch_stats = []
        for batch in active_batches[:10]:  # Limit to 10 most recent
            enrollments = BatchEnrollmentApplication.objects.filter(batch=batch)
            approved = enrollments.filter(status='approved').count()
            pending = enrollments.filter(status__in=['submitted', 'under_review']).count()
            
            batch_stats.append({
                'id': str(batch.id),
                'name': batch.batch_name,
                'target_capacity': batch.total_slots or 0,
                'approved': approved,
                'pending': pending,
                'fill_rate': round((approved / batch.total_slots * 100), 1) if batch.total_slots else 0
            })
        
        return {
            'active_batches': active_batches.count(),
            'batches': batch_stats
        }
    
    # =========================================================================
    # PRODUCTION MONITORING
    # =========================================================================
    
    def get_production_overview(self):
        """
        Get production overview metrics.
        
        Returns:
            dict: Production metrics
        """
        from flock_management.models import DailyProduction, Flock
        
        farms = self._get_farm_queryset()
        farm_ids = farms.values_list('id', flat=True)
        
        # Date ranges
        last_7_days = self.today - timedelta(days=7)
        last_30_days = self.today - timedelta(days=30)
        this_month_start = self.today.replace(day=1)
        
        # Weekly production
        weekly_production = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=last_7_days
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            total_mortality=Coalesce(Sum('birds_died'), 0),
            avg_production_rate=Coalesce(Avg('production_rate_percent'), Decimal('0'))
        )
        
        # Monthly production
        monthly_production = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=this_month_start
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            total_mortality=Coalesce(Sum('birds_died'), 0)
        )
        
        # Bird population
        total_birds = farms.aggregate(total=Coalesce(Sum('current_bird_count'), 0))['total']
        
        # Calculate mortality rate
        mortality_rate = 0
        if total_birds > 0 and weekly_production['total_mortality']:
            mortality_rate = round((weekly_production['total_mortality'] / total_birds * 100), 2)
        
        return {
            'weekly': {
                'eggs_collected': weekly_production['total_eggs'],
                'good_eggs': weekly_production['good_eggs'],
                'mortality': weekly_production['total_mortality'],
                'avg_production_rate': float(weekly_production['avg_production_rate'])
            },
            'monthly': {
                'eggs_collected': monthly_production['total_eggs'],
                'good_eggs': monthly_production['good_eggs'],
                'mortality': monthly_production['total_mortality']
            },
            'population': {
                'total_birds': total_birds,
                'mortality_rate_weekly': mortality_rate
            }
        }
    
    def get_production_trend(self, days=30):
        """
        Get daily production trend.
        
        Args:
            days: Number of days to include
            
        Returns:
            list: Daily production data
        """
        from flock_management.models import DailyProduction
        
        farms = self._get_farm_queryset()
        farm_ids = farms.values_list('id', flat=True)
        
        start_date = self.today - timedelta(days=days)
        
        trend = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=start_date
        ).values('production_date').annotate(
            total_eggs=Sum('eggs_collected'),
            good_eggs=Sum('good_eggs'),
            mortality=Sum('birds_died')
        ).order_by('production_date')
        
        return [
            {
                'date': item['production_date'].isoformat(),
                'eggs': item['total_eggs'] or 0,
                'good_eggs': item['good_eggs'] or 0,
                'mortality': item['mortality'] or 0
            }
            for item in trend
        ]
    
    def get_production_by_region(self):
        """
        Get production aggregated by region.
        
        Returns:
            list: Production by region
        """
        from flock_management.models import DailyProduction
        from farms.models import FarmLocation
        
        farms = self._get_farm_queryset()
        this_month_start = self.today.replace(day=1)
        
        # Get farm-to-region mapping
        farm_regions = dict(
            FarmLocation.objects.filter(
                farm_id__in=farms.values_list('id', flat=True),
                is_primary_location=True
            ).values_list('farm_id', 'region')
        )
        
        # Get production by farm
        production = DailyProduction.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            production_date__gte=this_month_start
        ).values('farm_id').annotate(
            total_eggs=Sum('eggs_collected')
        )
        
        # Aggregate by region
        region_data = {}
        for item in production:
            region = farm_regions.get(item['farm_id'], 'Unknown')
            if region not in region_data:
                region_data[region] = 0
            region_data[region] += item['total_eggs'] or 0
        
        return [
            {'region': region, 'eggs_this_month': eggs}
            for region, eggs in sorted(region_data.items(), key=lambda x: -x[1])
        ]
    
    def get_top_performing_farms(self, limit=10):
        """
        Get top performing farms by egg production.
        
        Args:
            limit: Number of farms to return
            
        Returns:
            list: Top farms with production data
        """
        from flock_management.models import DailyProduction
        
        farms = self._get_farm_queryset()
        this_month_start = self.today.replace(day=1)
        
        # Get top farms by this month's production
        top_farms = DailyProduction.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            production_date__gte=this_month_start
        ).values('farm_id', 'farm__farm_name', 'farm__primary_constituency').annotate(
            total_eggs=Sum('eggs_collected'),
            avg_rate=Avg('production_rate_percent')
        ).order_by('-total_eggs')[:limit]
        
        return [
            {
                'farm_id': str(item['farm_id']),
                'farm_name': item['farm__farm_name'],
                'constituency': item['farm__primary_constituency'] or 'N/A',
                'eggs_this_month': item['total_eggs'] or 0,
                'avg_production_rate': float(item['avg_rate'] or 0)
            }
            for item in top_farms
        ]
    
    def get_underperforming_farms(self, limit=10):
        """
        Get farms needing attention (low production or high mortality).
        
        Args:
            limit: Number of farms to return
            
        Returns:
            list: Underperforming farms
        """
        from flock_management.models import DailyProduction
        
        farms = self._get_farm_queryset().filter(farm_status='Operational')
        last_7_days = self.today - timedelta(days=7)
        
        # Farms with high mortality rate
        high_mortality = DailyProduction.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            production_date__gte=last_7_days,
            birds_died__gt=0
        ).values('farm_id', 'farm__farm_name', 'farm__current_bird_count').annotate(
            total_mortality=Sum('birds_died'),
            total_eggs=Sum('eggs_collected')
        ).order_by('-total_mortality')[:limit]
        
        result = []
        for item in high_mortality:
            bird_count = item['farm__current_bird_count'] or 1
            mortality_rate = round((item['total_mortality'] / bird_count * 100), 2)
            
            if mortality_rate > 2:  # Flag if > 2% weekly mortality
                result.append({
                    'farm_id': str(item['farm_id']),
                    'farm_name': item['farm__farm_name'],
                    'issue': 'High Mortality',
                    'mortality_count': item['total_mortality'],
                    'mortality_rate': mortality_rate,
                    'eggs_produced': item['total_eggs'] or 0
                })
        
        return result[:limit]
    
    # =========================================================================
    # MARKETPLACE ACTIVITY (NOT Platform Revenue)
    # =========================================================================
    
    def get_marketplace_activity(self):
        """
        Get marketplace transaction activity (farmer sales, not platform revenue).
        
        Returns:
            dict: Marketplace activity metrics
        """
        from sales_revenue.marketplace_models import MarketplaceOrder, Product
        from sales_revenue.guest_order_models import GuestOrder
        
        farms = self._get_farm_queryset()
        farm_ids = farms.values_list('id', flat=True)
        
        # Date ranges
        this_month_start = self.today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        # Marketplace orders (registered users)
        marketplace_orders = MarketplaceOrder.objects.filter(farm_id__in=farm_ids)
        
        this_month_orders = marketplace_orders.filter(
            created_at__gte=this_month_start,
            status__in=['confirmed', 'processing', 'ready', 'shipped', 'delivered', 'completed']
        )
        
        this_month_stats = this_month_orders.aggregate(
            order_count=Count('id'),
            total_volume=Coalesce(Sum('total_amount'), Decimal('0.00')),
            avg_order_value=Coalesce(Avg('total_amount'), Decimal('0.00'))
        )
        
        # Guest orders
        guest_orders = GuestOrder.objects.filter(farm_id__in=farm_ids)
        
        guest_this_month = guest_orders.filter(
            created_at__gte=this_month_start,
            status__in=['confirmed', 'processing', 'ready', 'shipped', 'delivered', 'completed']
        ).aggregate(
            order_count=Count('id'),
            total_volume=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )
        
        # Active sellers
        active_sellers = farms.filter(
            Q(marketplace_orders__created_at__gte=this_month_start) |
            Q(guest_orders__created_at__gte=this_month_start)
        ).distinct().count()
        
        # Active products
        active_products = Product.objects.filter(
            farm_id__in=farm_ids,
            status='active'
        ).count()
        
        return {
            'this_month': {
                'marketplace_orders': this_month_stats['order_count'],
                'marketplace_volume_ghs': float(this_month_stats['total_volume']),
                'guest_orders': guest_this_month['order_count'],
                'guest_volume_ghs': float(guest_this_month['total_volume']),
                'total_orders': this_month_stats['order_count'] + guest_this_month['order_count'],
                'total_volume_ghs': float(this_month_stats['total_volume'] + guest_this_month['total_volume']),
                'avg_order_value_ghs': float(this_month_stats['avg_order_value'])
            },
            'sellers': {
                'active_this_month': active_sellers,
                'total_with_products': farms.filter(marketplace_products__status='active').distinct().count()
            },
            'products': {
                'active_listings': active_products
            }
        }
    
    def get_sales_by_region(self):
        """
        Get marketplace sales volume by region.
        
        Returns:
            list: Sales by region
        """
        from sales_revenue.marketplace_models import MarketplaceOrder
        from farms.models import FarmLocation
        
        farms = self._get_farm_queryset()
        this_month_start = self.today.replace(day=1)
        
        # Get farm-to-region mapping
        farm_regions = dict(
            FarmLocation.objects.filter(
                farm_id__in=farms.values_list('id', flat=True),
                is_primary_location=True
            ).values_list('farm_id', 'region')
        )
        
        # Get sales by farm
        sales = MarketplaceOrder.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            created_at__gte=this_month_start,
            status__in=['confirmed', 'processing', 'ready', 'shipped', 'delivered', 'completed']
        ).values('farm_id').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        # Aggregate by region
        region_data = {}
        for item in sales:
            region = farm_regions.get(item['farm_id'], 'Unknown')
            if region not in region_data:
                region_data[region] = {'volume': Decimal('0'), 'orders': 0}
            region_data[region]['volume'] += item['total'] or Decimal('0')
            region_data[region]['orders'] += item['count']
        
        return [
            {
                'region': region,
                'volume_ghs': float(data['volume']),
                'order_count': data['orders']
            }
            for region, data in sorted(region_data.items(), key=lambda x: -float(x[1]['volume']))
        ]
    
    def get_top_selling_farmers(self, limit=10):
        """
        Get farmers with highest sales volume.
        
        Args:
            limit: Number of farmers to return
            
        Returns:
            list: Top selling farmers
        """
        from sales_revenue.marketplace_models import MarketplaceOrder
        
        farms = self._get_farm_queryset()
        this_month_start = self.today.replace(day=1)
        
        top_sellers = MarketplaceOrder.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            created_at__gte=this_month_start,
            status__in=['confirmed', 'processing', 'ready', 'shipped', 'delivered', 'completed']
        ).values(
            'farm_id', 'farm__farm_name', 'farm__user__first_name', 'farm__user__last_name'
        ).annotate(
            total_sales=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('-total_sales')[:limit]
        
        return [
            {
                'farm_id': str(item['farm_id']),
                'farm_name': item['farm__farm_name'],
                'farmer_name': f"{item['farm__user__first_name']} {item['farm__user__last_name']}".strip(),
                'sales_volume_ghs': float(item['total_sales'] or 0),
                'order_count': item['order_count']
            }
            for item in top_sellers
        ]
    
    # =========================================================================
    # ALERTS & WATCHLIST
    # =========================================================================
    
    def get_alerts(self):
        """
        Get system alerts for admin attention.
        
        Returns:
            dict: Categorized alerts
        """
        from flock_management.models import DailyProduction
        from farms.application_models import FarmApplication
        
        farms = self._get_farm_queryset()
        applications = self._get_application_queryset()
        
        last_7_days = self.today - timedelta(days=7)
        last_30_days = self.today - timedelta(days=30)
        
        alerts = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        # High mortality alerts (> 5% weekly)
        high_mortality_farms = self.get_underperforming_farms(limit=20)
        for farm in high_mortality_farms:
            if farm['mortality_rate'] > 5:
                alerts['critical'].append({
                    'type': 'high_mortality',
                    'message': f"{farm['farm_name']} has {farm['mortality_rate']}% mortality rate",
                    'farm_id': farm['farm_id']
                })
            elif farm['mortality_rate'] > 2:
                alerts['warning'].append({
                    'type': 'elevated_mortality',
                    'message': f"{farm['farm_name']} has {farm['mortality_rate']}% mortality rate",
                    'farm_id': farm['farm_id']
                })
        
        # Aging applications (> 14 days in review)
        old_date = self.now - timedelta(days=14)
        aging_apps = applications.filter(
            status__in=['constituency_review', 'regional_review', 'national_review'],
            updated_at__lt=old_date
        ).count()
        
        if aging_apps > 0:
            alerts['warning'].append({
                'type': 'aging_applications',
                'message': f"{aging_apps} applications pending review for over 14 days",
                'count': aging_apps
            })
        
        # Inactive farms (no production in 30 days)
        active_farm_ids = DailyProduction.objects.filter(
            production_date__gte=last_30_days
        ).values_list('farm_id', flat=True).distinct()
        
        operational_farms = farms.filter(farm_status='Operational')
        inactive_farms = operational_farms.exclude(id__in=active_farm_ids).count()
        
        if inactive_farms > 0:
            alerts['warning'].append({
                'type': 'inactive_farms',
                'message': f"{inactive_farms} operational farms with no production logged in 30 days",
                'count': inactive_farms
            })
        
        # Pending applications summary
        pending = applications.filter(status='submitted').count()
        if pending > 10:
            alerts['info'].append({
                'type': 'pending_assignment',
                'message': f"{pending} applications awaiting review assignment",
                'count': pending
            })
        
        return alerts
    
    def get_watchlist(self, limit=20):
        """
        Get farms on watchlist (needing attention).
        
        Returns:
            list: Farms requiring attention
        """
        watchlist = []
        
        # Add underperforming farms
        underperforming = self.get_underperforming_farms(limit=limit)
        for farm in underperforming:
            watchlist.append({
                'farm_id': farm['farm_id'],
                'farm_name': farm['farm_name'],
                'reason': farm['issue'],
                'details': f"Mortality: {farm['mortality_rate']}%",
                'severity': 'high' if farm['mortality_rate'] > 5 else 'medium'
            })
        
        return watchlist[:limit]

    # =========================================================================
    # GEOGRAPHIC BREAKDOWN ANALYTICS
    # =========================================================================
    
    def get_geographic_breakdown(self, level='region', parent_filter=None, period_days=30):
        """
        Get comprehensive geographic breakdown of all key metrics.
        
        Args:
            level: 'region', 'district', or 'constituency'
            parent_filter: For drill-down (e.g., region name when level='district')
            period_days: Number of days for production data
            
        Returns:
            dict: Geographic breakdown with farms, production, mortality, etc.
        """
        from farms.models import Farm, FarmLocation
        from flock_management.models import DailyProduction
        from accounts.models import User
        
        farms = self._get_farm_queryset()
        start_date = self.today - timedelta(days=period_days)
        
        # Build farm-location mapping
        location_qs = FarmLocation.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            is_primary_location=True
        )
        
        # Apply parent filter for drill-down
        if parent_filter:
            if level == 'district':
                location_qs = location_qs.filter(region__iexact=parent_filter)
            elif level == 'constituency':
                location_qs = location_qs.filter(district__iexact=parent_filter)
        
        # Group by geographic level
        group_field = level  # 'region', 'district', or 'constituency'
        
        # Get farm counts per geographic unit
        farm_locations = location_qs.values(group_field).annotate(
            farm_count=Count('farm_id', distinct=True)
        )
        
        # Create mapping of farm_id to geographic location
        farm_geo_map = dict(
            location_qs.values_list('farm_id', group_field)
        )
        
        # Get farm IDs in this filtered set
        filtered_farm_ids = list(farm_geo_map.keys())
        
        # Get production data by farm
        production_by_farm = DailyProduction.objects.filter(
            farm_id__in=filtered_farm_ids,
            production_date__gte=start_date
        ).values('farm_id').annotate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            total_mortality=Coalesce(Sum('birds_died'), 0),
            avg_production_rate=Coalesce(Avg('production_rate_percent'), Decimal('0'))
        )
        
        # Aggregate production by geographic level
        geo_production = {}
        for item in production_by_farm:
            geo_unit = farm_geo_map.get(item['farm_id'], 'Unknown')
            if geo_unit not in geo_production:
                geo_production[geo_unit] = {
                    'eggs': 0,
                    'good_eggs': 0,
                    'mortality': 0,
                    'production_rates': []
                }
            geo_production[geo_unit]['eggs'] += item['total_eggs'] or 0
            geo_production[geo_unit]['good_eggs'] += item['good_eggs'] or 0
            geo_production[geo_unit]['mortality'] += item['total_mortality'] or 0
            if item['avg_production_rate']:
                geo_production[geo_unit]['production_rates'].append(float(item['avg_production_rate']))
        
        # Get bird counts by geographic level
        farms_with_birds = farms.filter(id__in=filtered_farm_ids).values('id', 'current_bird_count')
        geo_birds = {}
        for farm in farms_with_birds:
            geo_unit = farm_geo_map.get(farm['id'], 'Unknown')
            if geo_unit not in geo_birds:
                geo_birds[geo_unit] = 0
            geo_birds[geo_unit] += farm['current_bird_count'] or 0
        
        # Get farmer counts by geographic level
        geo_farmers = {}
        for loc in location_qs.select_related('farm__user'):
            geo_unit = getattr(loc, group_field)
            if geo_unit not in geo_farmers:
                geo_farmers[geo_unit] = set()
            if loc.farm.user_id:
                geo_farmers[geo_unit].add(loc.farm.user_id)
        
        # Build result
        result = []
        for loc in farm_locations:
            geo_unit = loc[group_field]
            if not geo_unit:
                continue
            
            prod = geo_production.get(geo_unit, {})
            birds = geo_birds.get(geo_unit, 0)
            farmers = len(geo_farmers.get(geo_unit, set()))
            
            # Calculate mortality rate
            mortality = prod.get('mortality', 0)
            mortality_rate = round((mortality / birds * 100), 2) if birds > 0 else 0
            
            # Calculate average production rate
            rates = prod.get('production_rates', [])
            avg_rate = round(sum(rates) / len(rates), 1) if rates else 0
            
            result.append({
                'name': geo_unit,
                'level': level,
                'farms': loc['farm_count'],
                'farmers': farmers,
                'total_birds': birds,
                'eggs_produced': prod.get('eggs', 0),
                'good_eggs': prod.get('good_eggs', 0),
                'mortality_count': mortality,
                'mortality_rate': mortality_rate,
                'avg_production_rate': avg_rate,
                'period_days': period_days
            })
        
        # Sort by eggs produced descending
        result.sort(key=lambda x: -x['eggs_produced'])
        
        return {
            'level': level,
            'parent_filter': parent_filter,
            'period_days': period_days,
            'data': result,
            'summary': {
                'total_locations': len(result),
                'total_farms': sum(r['farms'] for r in result),
                'total_birds': sum(r['total_birds'] for r in result),
                'total_eggs': sum(r['eggs_produced'] for r in result),
                'total_mortality': sum(r['mortality_count'] for r in result)
            }
        }
    
    def get_mortality_breakdown(self, level='region', parent_filter=None, period_days=30, comparison_period_days=30):
        """
        Get detailed mortality breakdown by geographic level with trends.
        
        Args:
            level: 'region', 'district', or 'constituency'
            parent_filter: For drill-down filtering
            period_days: Current period
            comparison_period_days: Previous period for trend comparison
            
        Returns:
            dict: Mortality breakdown with trends
        """
        from farms.models import Farm, FarmLocation
        from flock_management.models import DailyProduction
        
        farms = self._get_farm_queryset()
        
        current_start = self.today - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=comparison_period_days)
        previous_end = current_start - timedelta(days=1)
        
        # Build location filter
        location_qs = FarmLocation.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            is_primary_location=True
        )
        
        if parent_filter:
            if level == 'district':
                location_qs = location_qs.filter(region__iexact=parent_filter)
            elif level == 'constituency':
                location_qs = location_qs.filter(district__iexact=parent_filter)
        
        group_field = level
        
        # Farm to geo mapping
        farm_geo_map = dict(location_qs.values_list('farm_id', group_field))
        filtered_farm_ids = list(farm_geo_map.keys())
        
        # Get bird counts
        farms_with_birds = farms.filter(id__in=filtered_farm_ids).values('id', 'current_bird_count')
        geo_birds = {}
        for farm in farms_with_birds:
            geo_unit = farm_geo_map.get(farm['id'], 'Unknown')
            if geo_unit not in geo_birds:
                geo_birds[geo_unit] = 0
            geo_birds[geo_unit] += farm['current_bird_count'] or 0
        
        # Current period mortality
        current_mortality = DailyProduction.objects.filter(
            farm_id__in=filtered_farm_ids,
            production_date__gte=current_start
        ).values('farm_id').annotate(
            mortality=Coalesce(Sum('birds_died'), 0)
        )
        
        geo_current = {}
        for item in current_mortality:
            geo_unit = farm_geo_map.get(item['farm_id'], 'Unknown')
            if geo_unit not in geo_current:
                geo_current[geo_unit] = 0
            geo_current[geo_unit] += item['mortality'] or 0
        
        # Previous period mortality
        previous_mortality = DailyProduction.objects.filter(
            farm_id__in=filtered_farm_ids,
            production_date__gte=previous_start,
            production_date__lte=previous_end
        ).values('farm_id').annotate(
            mortality=Coalesce(Sum('birds_died'), 0)
        )
        
        geo_previous = {}
        for item in previous_mortality:
            geo_unit = farm_geo_map.get(item['farm_id'], 'Unknown')
            if geo_unit not in geo_previous:
                geo_previous[geo_unit] = 0
            geo_previous[geo_unit] += item['mortality'] or 0
        
        # Build result with trends
        result = []
        all_units = set(geo_current.keys()) | set(geo_previous.keys()) | set(geo_birds.keys())
        
        for geo_unit in all_units:
            if not geo_unit or geo_unit == 'Unknown':
                continue
            
            current = geo_current.get(geo_unit, 0)
            previous = geo_previous.get(geo_unit, 0)
            birds = geo_birds.get(geo_unit, 0)
            
            current_rate = round((current / birds * 100), 2) if birds > 0 else 0
            previous_rate = round((previous / birds * 100), 2) if birds > 0 else 0
            
            # Trend calculation
            if previous > 0:
                trend_pct = round(((current - previous) / previous * 100), 1)
            else:
                trend_pct = 100 if current > 0 else 0
            
            trend_direction = 'up' if current > previous else ('down' if current < previous else 'stable')
            
            # Risk level
            if current_rate >= 5:
                risk_level = 'critical'
            elif current_rate >= 3:
                risk_level = 'high'
            elif current_rate >= 1:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            result.append({
                'name': geo_unit,
                'level': level,
                'total_birds': birds,
                'current_period': {
                    'mortality_count': current,
                    'mortality_rate': current_rate,
                    'days': period_days
                },
                'previous_period': {
                    'mortality_count': previous,
                    'mortality_rate': previous_rate,
                    'days': comparison_period_days
                },
                'trend': {
                    'direction': trend_direction,
                    'change_percent': trend_pct,
                    'is_improving': trend_direction == 'down'
                },
                'risk_level': risk_level
            })
        
        # Sort by current mortality rate descending (worst first)
        result.sort(key=lambda x: -x['current_period']['mortality_rate'])
        
        # Summary statistics
        total_current = sum(r['current_period']['mortality_count'] for r in result)
        total_previous = sum(r['previous_period']['mortality_count'] for r in result)
        critical_count = sum(1 for r in result if r['risk_level'] == 'critical')
        high_count = sum(1 for r in result if r['risk_level'] == 'high')
        
        return {
            'level': level,
            'parent_filter': parent_filter,
            'data': result,
            'summary': {
                'total_locations': len(result),
                'current_total_mortality': total_current,
                'previous_total_mortality': total_previous,
                'overall_trend': 'improving' if total_current < total_previous else 'worsening',
                'critical_areas': critical_count,
                'high_risk_areas': high_count
            }
        }
    
    def get_production_comparison(self, level='region', parent_filter=None, period_days=30, metric='eggs'):
        """
        Get production comparison across geographic units.
        
        Args:
            level: 'region', 'district', or 'constituency'
            parent_filter: For drill-down
            period_days: Period for comparison
            metric: 'eggs', 'mortality', 'production_rate', 'birds'
            
        Returns:
            dict: Production comparison with rankings
        """
        breakdown = self.get_geographic_breakdown(level, parent_filter, period_days)
        data = breakdown['data']
        
        # Sort by requested metric
        metric_map = {
            'eggs': 'eggs_produced',
            'mortality': 'mortality_rate',
            'production_rate': 'avg_production_rate',
            'birds': 'total_birds',
            'farms': 'farms'
        }
        
        sort_field = metric_map.get(metric, 'eggs_produced')
        reverse = metric != 'mortality'  # Lower mortality is better
        
        data.sort(key=lambda x: x.get(sort_field, 0), reverse=reverse)
        
        # Add rankings
        for i, item in enumerate(data, 1):
            item['rank'] = i
        
        # Calculate statistics
        if data:
            values = [d.get(sort_field, 0) for d in data]
            avg = sum(values) / len(values)
            top_value = max(values)
            bottom_value = min(values)
            
            stats = {
                'average': round(avg, 2),
                'highest': top_value,
                'lowest': bottom_value,
                'top_performer': data[0]['name'] if data else None,
                'bottom_performer': data[-1]['name'] if data else None
            }
        else:
            stats = {}
        
        return {
            'level': level,
            'parent_filter': parent_filter,
            'metric': metric,
            'period_days': period_days,
            'data': data,
            'statistics': stats
        }
    
    def get_farm_performance_ranking(self, region=None, district=None, constituency=None, 
                                     metric='eggs', period_days=30, limit=50):
        """
        Get individual farm performance rankings with geographic filtering.
        
        Args:
            region: Filter by region
            district: Filter by district
            constituency: Filter by constituency
            metric: Ranking metric
            period_days: Period for data
            limit: Max farms to return
            
        Returns:
            dict: Farm rankings
        """
        from farms.models import Farm, FarmLocation
        from flock_management.models import DailyProduction
        
        farms = self._get_farm_queryset()
        start_date = self.today - timedelta(days=period_days)
        
        # Build location filter
        location_qs = FarmLocation.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            is_primary_location=True
        )
        
        if region:
            location_qs = location_qs.filter(region__iexact=region)
        if district:
            location_qs = location_qs.filter(district__iexact=district)
        if constituency:
            location_qs = location_qs.filter(constituency__iexact=constituency)
        
        filtered_farm_ids = location_qs.values_list('farm_id', flat=True)
        
        # Get production data with farm details
        production = DailyProduction.objects.filter(
            farm_id__in=filtered_farm_ids,
            production_date__gte=start_date
        ).values(
            'farm_id',
            'farm__farm_name',
            'farm__primary_constituency',
            'farm__current_bird_count'
        ).annotate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            total_mortality=Coalesce(Sum('birds_died'), 0),
            avg_production_rate=Coalesce(Avg('production_rate_percent'), Decimal('0')),
            days_recorded=Count('id')
        )
        
        result = []
        for item in production:
            farm_id = item['farm_id']
            birds = item['farm__current_bird_count'] or 0
            mortality = item['total_mortality'] or 0
            
            mortality_rate = round((mortality / birds * 100), 2) if birds > 0 else 0
            
            # Get location from separate query
            loc_info = location_qs.filter(farm_id=farm_id).values(
                'region', 'district', 'constituency'
            ).first() or {}
            
            result.append({
                'farm_id': str(farm_id),
                'farm_name': item['farm__farm_name'],
                'region': loc_info.get('region', 'Unknown'),
                'district': loc_info.get('district', 'Unknown'),
                'constituency': loc_info.get('constituency', item['farm__primary_constituency'] or 'Unknown'),
                'total_birds': birds,
                'eggs_produced': item['total_eggs'],
                'good_eggs': item['good_eggs'],
                'mortality_count': mortality,
                'mortality_rate': mortality_rate,
                'avg_production_rate': float(item['avg_production_rate']),
                'days_recorded': item['days_recorded']
            })
        
        # Sort by metric
        metric_map = {
            'eggs': ('eggs_produced', True),
            'production_rate': ('avg_production_rate', True),
            'mortality': ('mortality_rate', False),  # Lower is better
            'birds': ('total_birds', True)
        }
        
        sort_field, reverse = metric_map.get(metric, ('eggs_produced', True))
        result.sort(key=lambda x: x.get(sort_field, 0), reverse=reverse)
        
        # Add rankings
        for i, item in enumerate(result[:limit], 1):
            item['rank'] = i
        
        return {
            'filters': {
                'region': region,
                'district': district,
                'constituency': constituency
            },
            'metric': metric,
            'period_days': period_days,
            'total_farms': len(result),
            'data': result[:limit]
        }
    
    def get_geographic_hierarchy(self):
        """
        Get available geographic hierarchy for drill-down navigation.
        
        Returns:
            dict: Hierarchy of regions -> districts -> constituencies
        """
        from farms.models import FarmLocation
        
        farms = self._get_farm_queryset()
        
        locations = FarmLocation.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            is_primary_location=True
        ).values('region', 'district', 'constituency').distinct()
        
        # Build hierarchy
        hierarchy = {}
        for loc in locations:
            region = loc['region'] or 'Unknown'
            district = loc['district'] or 'Unknown'
            constituency = loc['constituency'] or 'Unknown'
            
            if region not in hierarchy:
                hierarchy[region] = {'districts': {}, 'farm_count': 0}
            
            if district not in hierarchy[region]['districts']:
                hierarchy[region]['districts'][district] = {'constituencies': [], 'farm_count': 0}
            
            if constituency not in hierarchy[region]['districts'][district]['constituencies']:
                hierarchy[region]['districts'][district]['constituencies'].append(constituency)
        
        # Add farm counts
        farm_counts = FarmLocation.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            is_primary_location=True
        ).values('region', 'district').annotate(
            count=Count('farm_id', distinct=True)
        )
        
        for fc in farm_counts:
            region = fc['region'] or 'Unknown'
            district = fc['district'] or 'Unknown'
            if region in hierarchy and district in hierarchy[region]['districts']:
                hierarchy[region]['districts'][district]['farm_count'] = fc['count']
                hierarchy[region]['farm_count'] += fc['count']
        
        # Convert to list format
        result = []
        for region, data in sorted(hierarchy.items()):
            districts = []
            for district, d_data in sorted(data['districts'].items()):
                districts.append({
                    'name': district,
                    'constituencies': sorted(d_data['constituencies']),
                    'farm_count': d_data['farm_count']
                })
            
            result.append({
                'name': region,
                'districts': districts,
                'farm_count': data['farm_count']
            })
        
        return {
            'regions': result,
            'total_regions': len(result),
            'total_districts': sum(len(r['districts']) for r in result),
            'total_constituencies': sum(
                len(d['constituencies']) for r in result for d in r['districts']
            )
        }

    # =========================================================================
    # EGG PRODUCTION ANALYTICS
    # =========================================================================
    
    def get_egg_production_overview(self, period_days=30):
        """
        Get comprehensive egg production overview with quality breakdown.
        
        Args:
            period_days: Period for analysis
            
        Returns:
            dict: Complete egg production metrics
        """
        from flock_management.models import DailyProduction
        from farms.models import Farm
        
        farms = self._get_farm_queryset()
        farm_ids = farms.values_list('id', flat=True)
        
        start_date = self.today - timedelta(days=period_days)
        previous_start = start_date - timedelta(days=period_days)
        previous_end = start_date - timedelta(days=1)
        
        # Current period production
        current_production = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=start_date
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            broken_eggs=Coalesce(Sum('broken_eggs'), 0),
            dirty_eggs=Coalesce(Sum('dirty_eggs'), 0),
            small_eggs=Coalesce(Sum('small_eggs'), 0),
            soft_shell_eggs=Coalesce(Sum('soft_shell_eggs'), 0),
            avg_production_rate=Coalesce(Avg('production_rate_percent'), Decimal('0')),
            days_recorded=Count('production_date', distinct=True),
            farms_reporting=Count('farm_id', distinct=True)
        )
        
        # Previous period for comparison
        previous_production = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=previous_start,
            production_date__lte=previous_end
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0)
        )
        
        # Bird population
        total_birds = farms.aggregate(total=Coalesce(Sum('current_bird_count'), 0))['total']
        
        # Calculate quality percentages
        total = current_production['total_eggs'] or 1  # Avoid division by zero
        good_pct = round((current_production['good_eggs'] / total * 100), 1)
        broken_pct = round((current_production['broken_eggs'] / total * 100), 1)
        dirty_pct = round((current_production['dirty_eggs'] / total * 100), 1)
        small_pct = round((current_production['small_eggs'] / total * 100), 1)
        soft_shell_pct = round((current_production['soft_shell_eggs'] / total * 100), 1)
        
        # Calculate trends
        prev_total = previous_production['total_eggs'] or 1
        production_change = round(((current_production['total_eggs'] - previous_production['total_eggs']) / prev_total * 100), 1)
        quality_change = 0
        if previous_production['good_eggs'] > 0:
            prev_quality_rate = previous_production['good_eggs'] / prev_total * 100
            curr_quality_rate = current_production['good_eggs'] / total * 100
            quality_change = round(curr_quality_rate - prev_quality_rate, 1)
        
        # Calculate eggs per bird per day
        days = current_production['days_recorded'] or 1
        eggs_per_bird_per_day = round((current_production['total_eggs'] / (total_birds * days)), 3) if total_birds > 0 else 0
        
        return {
            'period_days': period_days,
            'production': {
                'total_eggs': current_production['total_eggs'],
                'daily_average': round(current_production['total_eggs'] / days, 0),
                'eggs_per_bird_per_day': eggs_per_bird_per_day,
                'avg_production_rate': float(current_production['avg_production_rate']),
                'farms_reporting': current_production['farms_reporting'],
                'days_recorded': current_production['days_recorded']
            },
            'quality': {
                'good_eggs': current_production['good_eggs'],
                'good_eggs_percent': good_pct,
                'broken_eggs': current_production['broken_eggs'],
                'broken_eggs_percent': broken_pct,
                'dirty_eggs': current_production['dirty_eggs'],
                'dirty_eggs_percent': dirty_pct,
                'small_eggs': current_production['small_eggs'],
                'small_eggs_percent': small_pct,
                'soft_shell_eggs': current_production['soft_shell_eggs'],
                'soft_shell_eggs_percent': soft_shell_pct
            },
            'trends': {
                'production_change_percent': production_change,
                'production_trend': 'up' if production_change > 0 else ('down' if production_change < 0 else 'stable'),
                'quality_change_percent': quality_change,
                'quality_trend': 'improving' if quality_change > 0 else ('declining' if quality_change < 0 else 'stable'),
                'previous_period_eggs': previous_production['total_eggs']
            },
            'population': {
                'total_birds': total_birds,
                'laying_efficiency': float(current_production['avg_production_rate'])
            }
        }
    
    def get_egg_production_trend(self, period_days=30, granularity='daily'):
        """
        Get egg production trend over time with quality breakdown.
        
        Args:
            period_days: Number of days to include
            granularity: 'daily', 'weekly', or 'monthly'
            
        Returns:
            dict: Time-series production data
        """
        from flock_management.models import DailyProduction
        
        farms = self._get_farm_queryset()
        farm_ids = farms.values_list('id', flat=True)
        
        start_date = self.today - timedelta(days=period_days)
        
        # Choose truncation function
        if granularity == 'weekly':
            trunc_fn = TruncWeek('production_date')
            date_format = '%Y-W%W'
        elif granularity == 'monthly':
            trunc_fn = TruncMonth('production_date')
            date_format = '%Y-%m'
        else:
            trunc_fn = TruncDate('production_date')
            date_format = '%Y-%m-%d'
        
        trend = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=start_date
        ).annotate(
            period=trunc_fn
        ).values('period').annotate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            broken_eggs=Coalesce(Sum('broken_eggs'), 0),
            dirty_eggs=Coalesce(Sum('dirty_eggs'), 0),
            small_eggs=Coalesce(Sum('small_eggs'), 0),
            soft_shell_eggs=Coalesce(Sum('soft_shell_eggs'), 0),
            avg_production_rate=Coalesce(Avg('production_rate_percent'), Decimal('0')),
            farms_count=Count('farm_id', distinct=True)
        ).order_by('period')
        
        data = []
        for item in trend:
            total = item['total_eggs'] or 1
            data.append({
                'period': item['period'].strftime(date_format) if item['period'] else None,
                'date': item['period'].isoformat() if item['period'] else None,
                'total_eggs': item['total_eggs'],
                'good_eggs': item['good_eggs'],
                'good_eggs_percent': round((item['good_eggs'] / total * 100), 1),
                'defective_eggs': item['broken_eggs'] + item['dirty_eggs'] + item['small_eggs'] + item['soft_shell_eggs'],
                'breakdown': {
                    'broken': item['broken_eggs'],
                    'dirty': item['dirty_eggs'],
                    'small': item['small_eggs'],
                    'soft_shell': item['soft_shell_eggs']
                },
                'avg_production_rate': float(item['avg_production_rate']),
                'farms_reporting': item['farms_count']
            })
        
        # Calculate moving average (7-day for daily, 4-week for weekly)
        if len(data) >= 3:
            window = 7 if granularity == 'daily' else (4 if granularity == 'weekly' else 3)
            for i in range(len(data)):
                start_idx = max(0, i - window + 1)
                window_data = data[start_idx:i + 1]
                data[i]['moving_avg'] = round(sum(d['total_eggs'] for d in window_data) / len(window_data), 0)
        
        return {
            'period_days': period_days,
            'granularity': granularity,
            'data_points': len(data),
            'data': data
        }
    
    def get_egg_quality_analysis(self, period_days=30, level='region', parent_filter=None):
        """
        Get egg quality breakdown by geographic level.
        
        Args:
            period_days: Period for analysis
            level: 'region', 'district', or 'constituency'
            parent_filter: Parent filter for drill-down
            
        Returns:
            dict: Quality metrics by geographic area
        """
        from flock_management.models import DailyProduction
        from farms.models import Farm, FarmLocation
        
        farms = self._get_farm_queryset()
        farm_ids = farms.values_list('id', flat=True)
        start_date = self.today - timedelta(days=period_days)
        
        # Build location filter
        location_qs = FarmLocation.objects.filter(
            farm_id__in=farm_ids,
            is_primary_location=True
        )
        
        if parent_filter:
            if level == 'district':
                location_qs = location_qs.filter(region__iexact=parent_filter)
            elif level == 'constituency':
                location_qs = location_qs.filter(district__iexact=parent_filter)
        
        group_field = level
        farm_geo_map = dict(location_qs.values_list('farm_id', group_field))
        filtered_farm_ids = list(farm_geo_map.keys())
        
        # Get production by farm
        production = DailyProduction.objects.filter(
            farm_id__in=filtered_farm_ids,
            production_date__gte=start_date
        ).values('farm_id').annotate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            broken_eggs=Coalesce(Sum('broken_eggs'), 0),
            dirty_eggs=Coalesce(Sum('dirty_eggs'), 0),
            small_eggs=Coalesce(Sum('small_eggs'), 0),
            soft_shell_eggs=Coalesce(Sum('soft_shell_eggs'), 0)
        )
        
        # Aggregate by geographic level
        geo_data = {}
        for item in production:
            geo_unit = farm_geo_map.get(item['farm_id'], 'Unknown')
            if geo_unit not in geo_data:
                geo_data[geo_unit] = {
                    'total': 0, 'good': 0, 'broken': 0, 
                    'dirty': 0, 'small': 0, 'soft_shell': 0
                }
            geo_data[geo_unit]['total'] += item['total_eggs']
            geo_data[geo_unit]['good'] += item['good_eggs']
            geo_data[geo_unit]['broken'] += item['broken_eggs']
            geo_data[geo_unit]['dirty'] += item['dirty_eggs']
            geo_data[geo_unit]['small'] += item['small_eggs']
            geo_data[geo_unit]['soft_shell'] += item['soft_shell_eggs']
        
        result = []
        for geo_unit, data in geo_data.items():
            if not geo_unit or geo_unit == 'Unknown':
                continue
            
            total = data['total'] or 1
            defective = data['broken'] + data['dirty'] + data['small'] + data['soft_shell']
            quality_score = round((data['good'] / total * 100), 1)
            
            # Quality rating
            if quality_score >= 95:
                quality_rating = 'excellent'
            elif quality_score >= 90:
                quality_rating = 'good'
            elif quality_score >= 80:
                quality_rating = 'fair'
            else:
                quality_rating = 'poor'
            
            result.append({
                'name': geo_unit,
                'level': level,
                'total_eggs': data['total'],
                'good_eggs': data['good'],
                'good_eggs_percent': quality_score,
                'defective_eggs': defective,
                'defective_percent': round((defective / total * 100), 1),
                'breakdown': {
                    'broken': {'count': data['broken'], 'percent': round((data['broken'] / total * 100), 2)},
                    'dirty': {'count': data['dirty'], 'percent': round((data['dirty'] / total * 100), 2)},
                    'small': {'count': data['small'], 'percent': round((data['small'] / total * 100), 2)},
                    'soft_shell': {'count': data['soft_shell'], 'percent': round((data['soft_shell'] / total * 100), 2)}
                },
                'quality_rating': quality_rating
            })
        
        # Sort by quality score descending
        result.sort(key=lambda x: -x['good_eggs_percent'])
        
        # Add rankings
        for i, item in enumerate(result, 1):
            item['rank'] = i
        
        # Overall statistics
        total_all = sum(r['total_eggs'] for r in result)
        good_all = sum(r['good_eggs'] for r in result)
        
        return {
            'level': level,
            'parent_filter': parent_filter,
            'period_days': period_days,
            'data': result,
            'summary': {
                'total_locations': len(result),
                'total_eggs': total_all,
                'good_eggs': good_all,
                'overall_quality_percent': round((good_all / total_all * 100), 1) if total_all > 0 else 0,
                'best_performer': result[0]['name'] if result else None,
                'worst_performer': result[-1]['name'] if result else None
            }
        }
    
    def get_egg_production_by_farm(self, region=None, district=None, constituency=None,
                                    metric='total_eggs', period_days=30, limit=50):
        """
        Get individual farm egg production rankings.
        
        Args:
            region, district, constituency: Geographic filters
            metric: 'total_eggs', 'production_rate', 'quality', 'efficiency'
            period_days: Period for data
            limit: Max farms to return
            
        Returns:
            dict: Farm egg production rankings
        """
        from flock_management.models import DailyProduction
        from farms.models import Farm, FarmLocation
        
        farms = self._get_farm_queryset()
        start_date = self.today - timedelta(days=period_days)
        
        # Build location filter
        location_qs = FarmLocation.objects.filter(
            farm_id__in=farms.values_list('id', flat=True),
            is_primary_location=True
        )
        
        if region:
            location_qs = location_qs.filter(region__iexact=region)
        if district:
            location_qs = location_qs.filter(district__iexact=district)
        if constituency:
            location_qs = location_qs.filter(constituency__iexact=constituency)
        
        filtered_farm_ids = location_qs.values_list('farm_id', flat=True)
        
        # Get production with farm details
        production = DailyProduction.objects.filter(
            farm_id__in=filtered_farm_ids,
            production_date__gte=start_date
        ).values(
            'farm_id',
            'farm__farm_name',
            'farm__current_bird_count'
        ).annotate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            broken_eggs=Coalesce(Sum('broken_eggs'), 0),
            dirty_eggs=Coalesce(Sum('dirty_eggs'), 0),
            small_eggs=Coalesce(Sum('small_eggs'), 0),
            soft_shell_eggs=Coalesce(Sum('soft_shell_eggs'), 0),
            avg_production_rate=Coalesce(Avg('production_rate_percent'), Decimal('0')),
            days_recorded=Count('production_date', distinct=True)
        )
        
        result = []
        for item in production:
            farm_id = item['farm_id']
            total = item['total_eggs'] or 1
            birds = item['farm__current_bird_count'] or 1
            days = item['days_recorded'] or 1
            defective = item['broken_eggs'] + item['dirty_eggs'] + item['small_eggs'] + item['soft_shell_eggs']
            
            quality_percent = round((item['good_eggs'] / total * 100), 1)
            eggs_per_bird = round((item['total_eggs'] / birds), 2)
            daily_average = round((item['total_eggs'] / days), 0)
            
            # Get location
            loc_info = location_qs.filter(farm_id=farm_id).values(
                'region', 'district', 'constituency'
            ).first() or {}
            
            result.append({
                'farm_id': str(farm_id),
                'farm_name': item['farm__farm_name'],
                'region': loc_info.get('region', 'Unknown'),
                'district': loc_info.get('district', 'Unknown'),
                'constituency': loc_info.get('constituency', 'Unknown'),
                'bird_count': item['farm__current_bird_count'] or 0,
                'production': {
                    'total_eggs': item['total_eggs'],
                    'daily_average': daily_average,
                    'eggs_per_bird': eggs_per_bird,
                    'production_rate': float(item['avg_production_rate'])
                },
                'quality': {
                    'good_eggs': item['good_eggs'],
                    'good_percent': quality_percent,
                    'defective_eggs': defective,
                    'defective_percent': round((defective / total * 100), 1)
                },
                'breakdown': {
                    'broken': item['broken_eggs'],
                    'dirty': item['dirty_eggs'],
                    'small': item['small_eggs'],
                    'soft_shell': item['soft_shell_eggs']
                },
                'days_recorded': item['days_recorded']
            })
        
        # Sort by metric
        metric_map = {
            'total_eggs': ('production', 'total_eggs'),
            'production_rate': ('production', 'production_rate'),
            'quality': ('quality', 'good_percent'),
            'efficiency': ('production', 'eggs_per_bird'),
            'daily_average': ('production', 'daily_average')
        }
        
        sort_keys = metric_map.get(metric, ('production', 'total_eggs'))
        result.sort(key=lambda x: -x[sort_keys[0]][sort_keys[1]])
        
        # Add rankings
        for i, item in enumerate(result[:limit], 1):
            item['rank'] = i
        
        return {
            'filters': {
                'region': region,
                'district': district,
                'constituency': constituency
            },
            'metric': metric,
            'period_days': period_days,
            'total_farms': len(result),
            'data': result[:limit]
        }
    
    def get_egg_production_efficiency(self, period_days=30):
        """
        Get egg production efficiency metrics.
        
        Args:
            period_days: Period for analysis
            
        Returns:
            dict: Efficiency metrics
        """
        from flock_management.models import DailyProduction, Flock
        from farms.models import Farm
        
        farms = self._get_farm_queryset()
        farm_ids = farms.values_list('id', flat=True)
        start_date = self.today - timedelta(days=period_days)
        
        # Get production and feed data
        production = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=start_date
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            total_feed_kg=Coalesce(Sum('feed_consumed_kg'), Decimal('0')),
            total_feed_cost=Coalesce(Sum('feed_cost_today'), Decimal('0')),
            avg_production_rate=Coalesce(Avg('production_rate_percent'), Decimal('0')),
            days=Count('production_date', distinct=True),
            farms_count=Count('farm_id', distinct=True)
        )
        
        # Bird population
        total_birds = farms.aggregate(total=Coalesce(Sum('current_bird_count'), 0))['total']
        
        # Layer flocks
        layer_flocks = Flock.objects.filter(
            farm_id__in=farm_ids,
            flock_type='Layers',
            status='active'
        ).aggregate(
            count=Count('id'),
            total_birds=Coalesce(Sum('current_count'), 0)
        )
        
        # Calculate efficiency metrics
        total_eggs = production['total_eggs'] or 1
        total_feed = float(production['total_feed_kg']) or 1
        days = production['days'] or 1
        
        # Feed conversion (kg feed per dozen eggs)
        eggs_in_dozens = total_eggs / 12
        feed_per_dozen = round((total_feed / eggs_in_dozens), 3) if eggs_in_dozens > 0 else 0
        
        # Cost per egg
        total_feed_cost = float(production['total_feed_cost'])
        cost_per_egg = round((total_feed_cost / total_eggs), 4) if total_eggs > 0 else 0
        cost_per_dozen = round(cost_per_egg * 12, 2)
        
        # Eggs per bird metrics
        eggs_per_bird_total = round((total_eggs / total_birds), 2) if total_birds > 0 else 0
        eggs_per_bird_per_day = round((total_eggs / (total_birds * days)), 3) if (total_birds * days) > 0 else 0
        
        # Production rate distribution
        rate_distribution = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=start_date
        ).aggregate(
            below_70=Count('id', filter=Q(production_rate_percent__lt=70)),
            rate_70_80=Count('id', filter=Q(production_rate_percent__gte=70, production_rate_percent__lt=80)),
            rate_80_90=Count('id', filter=Q(production_rate_percent__gte=80, production_rate_percent__lt=90)),
            above_90=Count('id', filter=Q(production_rate_percent__gte=90))
        )
        
        total_records = sum(rate_distribution.values())
        
        return {
            'period_days': period_days,
            'birds': {
                'total': total_birds,
                'layer_flocks': layer_flocks['count'],
                'layers': layer_flocks['total_birds']
            },
            'production': {
                'total_eggs': production['total_eggs'],
                'good_eggs': production['good_eggs'],
                'quality_percent': round((production['good_eggs'] / total_eggs * 100), 1),
                'daily_average': round(production['total_eggs'] / days, 0),
                'avg_production_rate': float(production['avg_production_rate'])
            },
            'efficiency': {
                'eggs_per_bird_total': eggs_per_bird_total,
                'eggs_per_bird_per_day': eggs_per_bird_per_day,
                'eggs_per_layer_per_day': round((total_eggs / (layer_flocks['total_birds'] * days)), 3) if layer_flocks['total_birds'] > 0 else 0,
                'feed_per_dozen_eggs_kg': feed_per_dozen,
                'feed_cost_per_egg_ghs': cost_per_egg,
                'feed_cost_per_dozen_ghs': cost_per_dozen
            },
            'feed': {
                'total_consumed_kg': float(production['total_feed_kg']),
                'total_cost_ghs': float(production['total_feed_cost']),
                'daily_average_kg': round(float(production['total_feed_kg']) / days, 2)
            },
            'rate_distribution': {
                'below_70_percent': {
                    'count': rate_distribution['below_70'],
                    'percent': round((rate_distribution['below_70'] / total_records * 100), 1) if total_records > 0 else 0
                },
                '70_to_80_percent': {
                    'count': rate_distribution['rate_70_80'],
                    'percent': round((rate_distribution['rate_70_80'] / total_records * 100), 1) if total_records > 0 else 0
                },
                '80_to_90_percent': {
                    'count': rate_distribution['rate_80_90'],
                    'percent': round((rate_distribution['rate_80_90'] / total_records * 100), 1) if total_records > 0 else 0
                },
                'above_90_percent': {
                    'count': rate_distribution['above_90'],
                    'percent': round((rate_distribution['above_90'] / total_records * 100), 1) if total_records > 0 else 0
                }
            },
            'farms_reporting': production['farms_count'],
            'days_analyzed': production['days']
        }
    
    def get_egg_defect_analysis(self, period_days=30):
        """
        Get detailed egg defect analysis with trends.
        
        Args:
            period_days: Period for analysis
            
        Returns:
            dict: Defect analysis
        """
        from flock_management.models import DailyProduction
        
        farms = self._get_farm_queryset()
        farm_ids = farms.values_list('id', flat=True)
        
        start_date = self.today - timedelta(days=period_days)
        previous_start = start_date - timedelta(days=period_days)
        previous_end = start_date - timedelta(days=1)
        
        # Current period
        current = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=start_date
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            broken_eggs=Coalesce(Sum('broken_eggs'), 0),
            dirty_eggs=Coalesce(Sum('dirty_eggs'), 0),
            small_eggs=Coalesce(Sum('small_eggs'), 0),
            soft_shell_eggs=Coalesce(Sum('soft_shell_eggs'), 0)
        )
        
        # Previous period
        previous = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=previous_start,
            production_date__lte=previous_end
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            broken_eggs=Coalesce(Sum('broken_eggs'), 0),
            dirty_eggs=Coalesce(Sum('dirty_eggs'), 0),
            small_eggs=Coalesce(Sum('small_eggs'), 0),
            soft_shell_eggs=Coalesce(Sum('soft_shell_eggs'), 0)
        )
        
        # Daily breakdown for trend visualization
        daily_defects = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=start_date
        ).values('production_date').annotate(
            total=Sum('eggs_collected'),
            broken=Sum('broken_eggs'),
            dirty=Sum('dirty_eggs'),
            small=Sum('small_eggs'),
            soft_shell=Sum('soft_shell_eggs')
        ).order_by('production_date')
        
        current_total = current['total_eggs'] or 1
        previous_total = previous['total_eggs'] or 1
        
        def calc_rate_and_trend(current_val, prev_val, curr_total, prev_total):
            curr_rate = round((current_val / curr_total * 100), 2)
            prev_rate = round((prev_val / prev_total * 100), 2)
            trend = round(curr_rate - prev_rate, 2)
            return {
                'count': current_val,
                'rate': curr_rate,
                'previous_rate': prev_rate,
                'trend': trend,
                'improving': trend < 0  # Lower defect rate is better
            }
        
        defects = {
            'broken': calc_rate_and_trend(
                current['broken_eggs'], previous['broken_eggs'], 
                current_total, previous_total
            ),
            'dirty': calc_rate_and_trend(
                current['dirty_eggs'], previous['dirty_eggs'],
                current_total, previous_total
            ),
            'small': calc_rate_and_trend(
                current['small_eggs'], previous['small_eggs'],
                current_total, previous_total
            ),
            'soft_shell': calc_rate_and_trend(
                current['soft_shell_eggs'], previous['soft_shell_eggs'],
                current_total, previous_total
            )
        }
        
        total_defects = (current['broken_eggs'] + current['dirty_eggs'] + 
                        current['small_eggs'] + current['soft_shell_eggs'])
        
        # Identify primary issues
        issues = sorted(defects.items(), key=lambda x: -x[1]['rate'])
        primary_issue = issues[0][0] if issues else None
        
        return {
            'period_days': period_days,
            'summary': {
                'total_eggs': current['total_eggs'],
                'good_eggs': current['good_eggs'],
                'total_defective': total_defects,
                'defect_rate': round((total_defects / current_total * 100), 2),
                'quality_rate': round((current['good_eggs'] / current_total * 100), 2)
            },
            'defects': defects,
            'primary_issue': primary_issue,
            'recommendations': self._get_defect_recommendations(defects),
            'daily_trend': [
                {
                    'date': item['production_date'].isoformat(),
                    'total_defects': (item['broken'] or 0) + (item['dirty'] or 0) + 
                                    (item['small'] or 0) + (item['soft_shell'] or 0),
                    'defect_rate': round(
                        ((item['broken'] or 0) + (item['dirty'] or 0) + 
                         (item['small'] or 0) + (item['soft_shell'] or 0)) / 
                        (item['total'] or 1) * 100, 2
                    )
                }
                for item in daily_defects
            ]
        }
    
    def _get_defect_recommendations(self, defects):
        """Generate recommendations based on defect analysis."""
        recommendations = []
        
        if defects['broken']['rate'] > 2:
            recommendations.append({
                'issue': 'High breakage rate',
                'possible_causes': ['Rough handling', 'Weak shells (calcium deficiency)', 'Poor collection practices'],
                'actions': ['Review collection procedures', 'Check calcium in feed', 'Inspect egg collection equipment']
            })
        
        if defects['dirty']['rate'] > 5:
            recommendations.append({
                'issue': 'High dirty egg rate',
                'possible_causes': ['Infrequent collection', 'Dirty nesting boxes', 'Overcrowding'],
                'actions': ['Increase collection frequency', 'Clean nesting boxes regularly', 'Check stocking density']
            })
        
        if defects['soft_shell']['rate'] > 1:
            recommendations.append({
                'issue': 'Soft shell eggs',
                'possible_causes': ['Calcium deficiency', 'Heat stress', 'Disease', 'Old laying hens'],
                'actions': ['Supplement calcium', 'Improve ventilation', 'Check bird health', 'Review flock age']
            })
        
        if defects['small']['rate'] > 3:
            recommendations.append({
                'issue': 'High rate of small eggs',
                'possible_causes': ['Young pullets', 'Nutritional deficiency', 'Stress'],
                'actions': ['Review feed formulation', 'Reduce stressors', 'Allow pullets to mature']
            })
        
        return recommendations
    
    def get_egg_production_comparison(self, period_days=30, compare_period_days=30):
        """
        Compare current period with previous period.
        
        Args:
            period_days: Current period
            compare_period_days: Previous period for comparison
            
        Returns:
            dict: Period comparison
        """
        from flock_management.models import DailyProduction
        
        farms = self._get_farm_queryset()
        farm_ids = farms.values_list('id', flat=True)
        
        current_start = self.today - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=compare_period_days)
        previous_end = current_start - timedelta(days=1)
        
        # Current period
        current = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=current_start
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            broken_eggs=Coalesce(Sum('broken_eggs'), 0),
            dirty_eggs=Coalesce(Sum('dirty_eggs'), 0),
            small_eggs=Coalesce(Sum('small_eggs'), 0),
            soft_shell_eggs=Coalesce(Sum('soft_shell_eggs'), 0),
            avg_production_rate=Coalesce(Avg('production_rate_percent'), Decimal('0')),
            total_feed_kg=Coalesce(Sum('feed_consumed_kg'), Decimal('0')),
            total_feed_cost=Coalesce(Sum('feed_cost_today'), Decimal('0')),
            farms_count=Count('farm_id', distinct=True)
        )
        
        # Previous period
        previous = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=previous_start,
            production_date__lte=previous_end
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            avg_production_rate=Coalesce(Avg('production_rate_percent'), Decimal('0')),
            total_feed_kg=Coalesce(Sum('feed_consumed_kg'), Decimal('0')),
            total_feed_cost=Coalesce(Sum('feed_cost_today'), Decimal('0'))
        )
        
        def calc_change(current_val, previous_val):
            if previous_val == 0:
                return 100 if current_val > 0 else 0
            return round(((current_val - previous_val) / previous_val * 100), 1)
        
        current_total = current['total_eggs'] or 1
        previous_total = previous['total_eggs'] or 1
        current_defects = (current['broken_eggs'] + current['dirty_eggs'] + 
                          current['small_eggs'] + current['soft_shell_eggs'])
        
        return {
            'current_period': {
                'start_date': current_start.isoformat(),
                'end_date': self.today.isoformat(),
                'days': period_days,
                'total_eggs': current['total_eggs'],
                'good_eggs': current['good_eggs'],
                'quality_percent': round((current['good_eggs'] / current_total * 100), 1),
                'defective_eggs': current_defects,
                'avg_production_rate': float(current['avg_production_rate']),
                'feed_consumed_kg': float(current['total_feed_kg']),
                'feed_cost_ghs': float(current['total_feed_cost']),
                'farms_reporting': current['farms_count']
            },
            'previous_period': {
                'start_date': previous_start.isoformat(),
                'end_date': previous_end.isoformat(),
                'days': compare_period_days,
                'total_eggs': previous['total_eggs'],
                'good_eggs': previous['good_eggs'],
                'quality_percent': round((previous['good_eggs'] / previous_total * 100), 1),
                'avg_production_rate': float(previous['avg_production_rate']),
                'feed_consumed_kg': float(previous['total_feed_kg']),
                'feed_cost_ghs': float(previous['total_feed_cost'])
            },
            'changes': {
                'eggs_change': current['total_eggs'] - previous['total_eggs'],
                'eggs_change_percent': calc_change(current['total_eggs'], previous['total_eggs']),
                'quality_change_percent': round(
                    (current['good_eggs'] / current_total * 100) - 
                    (previous['good_eggs'] / previous_total * 100), 1
                ),
                'production_rate_change': round(
                    float(current['avg_production_rate']) - float(previous['avg_production_rate']), 1
                ),
                'feed_efficiency_improving': (
                    float(current['total_feed_kg']) / current_total < 
                    float(previous['total_feed_kg']) / previous_total
                ) if previous_total > 0 else False
            },
            'trends': {
                'production': 'up' if current['total_eggs'] > previous['total_eggs'] else 
                             ('down' if current['total_eggs'] < previous['total_eggs'] else 'stable'),
                'quality': 'improving' if (current['good_eggs'] / current_total) > (previous['good_eggs'] / previous_total) else 'declining'
            }
        }
