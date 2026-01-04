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
                'name': batch.name,
                'target_capacity': batch.target_enrollment or 0,
                'approved': approved,
                'pending': pending,
                'fill_rate': round((approved / batch.target_enrollment * 100), 1) if batch.target_enrollment else 0
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
