"""
National Admin / Agriculture Minister Analytics Service

Comprehensive analytics for National Administrators and the Agriculture Minister.
Provides program-wide insights with drill-down capabilities from:
  National → Regional → Constituency → Farm

Access Control:
- SUPER_ADMIN: Full access + Platform Revenue
- YEA_OFFICIAL: Full access + Platform Revenue  
- NATIONAL_ADMIN: Full access (no platform revenue)
- REGIONAL_COORDINATOR: Region-filtered access
- CONSTITUENCY_OFFICIAL: Constituency-filtered access

Performance Optimization:
- Redis caching with configurable TTL
- Pre-aggregated metrics via Celery tasks
- Query optimization with select_related/prefetch_related
"""

from django.db.models import (
    Sum, Count, Avg, Q, F, Case, When, Value, 
    DecimalField, IntegerField, FloatField
)
from django.db.models.functions import (
    TruncMonth, TruncWeek, TruncDate, Coalesce, 
    ExtractYear, ExtractMonth
)
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta, date
from decimal import Decimal
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Cache TTL settings (seconds)
CACHE_TTL = {
    'short': 300,        # 5 minutes - for frequently changing data
    'medium': 1800,      # 30 minutes - for moderately dynamic data
    'long': 3600,        # 1 hour - for stable aggregate data
    'daily': 86400,      # 24 hours - for historical/computed data
}


class NationalAdminAnalyticsService:
    """
    Analytics service for National Administrators and Agriculture Minister.
    
    Provides comprehensive program metrics with geographic drill-down capability.
    All methods support caching and can be pre-computed via Celery tasks.
    """
    
    def __init__(self, user=None, use_cache: bool = True):
        """
        Initialize the service.
        
        Args:
            user: The requesting user (for role-based filtering)
            use_cache: Whether to use cached data when available
        """
        self.user = user
        self.use_cache = use_cache
        self.now = timezone.now()
        self.today = self.now.date()
        
    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate consistent cache key."""
        parts = [prefix] + [str(a) for a in args if a]
        return f"national_admin:{':'.join(parts)}"
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Retrieve data from cache if enabled."""
        if self.use_cache:
            return cache.get(key)
        return None
    
    def _set_cache(self, key: str, data: Any, ttl: int = CACHE_TTL['medium']):
        """Store data in cache."""
        cache.set(key, data, timeout=ttl)
        
    # =========================================================================
    # GEOGRAPHIC SCOPING
    # =========================================================================
    
    def _get_farm_queryset(self, region: str = None, constituency: str = None):
        """
        Get farm queryset with geographic filtering.
        
        Args:
            region: Filter by region name
            constituency: Filter by constituency name
        """
        from farms.models import Farm
        
        qs = Farm.objects.select_related('user').prefetch_related('locations')
        
        # Apply user role-based filtering
        if self.user:
            if self.user.role == 'REGIONAL_COORDINATOR' and self.user.region:
                region = self.user.region
            elif self.user.role == 'CONSTITUENCY_OFFICIAL' and self.user.constituency:
                constituency = self.user.constituency
        
        # Apply geographic filters
        if constituency:
            qs = qs.filter(primary_constituency__iexact=constituency)
        elif region:
            qs = qs.filter(
                Q(locations__region__iexact=region, locations__is_primary_location=True) |
                Q(primary_constituency__icontains=region)
            ).distinct()
            
        return qs
    
    def _get_production_queryset(self, region: str = None, constituency: str = None):
        """Get DailyProduction queryset with geographic filtering."""
        from flock_management.models import DailyProduction
        
        farm_qs = self._get_farm_queryset(region, constituency)
        farm_ids = farm_qs.values_list('id', flat=True)
        
        return DailyProduction.objects.filter(farm_id__in=farm_ids)
    
    def _get_available_regions(self) -> List[str]:
        """Get list of all regions with farms."""
        from farms.models import FarmLocation
        
        cache_key = self._get_cache_key('regions')
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        regions = list(
            FarmLocation.objects.filter(is_primary_location=True)
            .values_list('region', flat=True)
            .distinct()
            .order_by('region')
        )
        
        self._set_cache(cache_key, regions, CACHE_TTL['daily'])
        return regions
    
    def _get_constituencies_in_region(self, region: str) -> List[str]:
        """Get list of constituencies in a region."""
        from farms.models import FarmLocation
        
        cache_key = self._get_cache_key('constituencies', region)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        constituencies = list(
            FarmLocation.objects.filter(
                is_primary_location=True,
                region__iexact=region
            )
            .values_list('constituency', flat=True)
            .distinct()
            .order_by('constituency')
        )
        
        self._set_cache(cache_key, constituencies, CACHE_TTL['daily'])
        return constituencies
    
    # =========================================================================
    # 1. PROGRAM PERFORMANCE REPORTS
    # =========================================================================
    
    def get_program_performance_overview(
        self, 
        region: str = None, 
        constituency: str = None
    ) -> Dict[str, Any]:
        """
        Get program performance metrics.
        
        Includes:
        - Enrollment statistics
        - Program growth metrics
        - Farmer retention rates
        - Geographic coverage
        
        Args:
            region: Optional region filter
            constituency: Optional constituency filter
        """
        cache_key = self._get_cache_key('program_performance', region, constituency)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        from farms.models import Farm
        from farms.batch_enrollment_models import Batch, BatchEnrollmentApplication
        from accounts.models import User
        
        farms = self._get_farm_queryset(region, constituency)
        
        # Date ranges
        this_month_start = self.today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        last_year = self.now - timedelta(days=365)
        
        # Farmer counts
        total_farms = farms.count()
        operational_farms = farms.filter(farm_status='Active').count()
        government_farms = farms.filter(
            registration_source__in=['YEA Program', 'Government Initiative']
        ).count()
        independent_farms = farms.filter(
            registration_source__in=['Self Registration', 'Independent']
        ).count()
        
        # New registrations
        new_this_month = farms.filter(created_at__gte=this_month_start).count()
        new_last_month = farms.filter(
            created_at__gte=last_month_start,
            created_at__lt=this_month_start
        ).count()
        
        # Calculate growth rate
        growth_rate = 0
        if new_last_month > 0:
            growth_rate = round(
                ((new_this_month - new_last_month) / new_last_month) * 100, 1
            )
        
        # Batch enrollment stats
        active_batches = Batch.objects.filter(
            is_active=True, 
            is_published=True
        ).count()
        
        # Count approved or enrolled batch applications
        total_enrollments = BatchEnrollmentApplication.objects.filter(
            status__in=['approved', 'enrolled']
        ).count()
        
        # Retention (farms operational for > 6 months)
        six_months_ago = self.now - timedelta(days=180)
        mature_farms = farms.filter(created_at__lte=six_months_ago)
        still_operational = mature_farms.filter(
            farm_status='Active'
        ).count()
        
        retention_rate = 0
        if mature_farms.count() > 0:
            retention_rate = round(
                (still_operational / mature_farms.count()) * 100, 1
            )
        
        # Geographic coverage
        total_regions = self._get_available_regions()
        regions_with_farms = len([r for r in total_regions if r])
        
        result = {
            'summary': {
                'total_farms': total_farms,
                'operational_farms': operational_farms,
                'government_supported': government_farms,
                'independent': independent_farms,
                'new_this_month': new_this_month,
                'growth_rate_percent': growth_rate,
            },
            'enrollment': {
                'active_batches': active_batches,
                'total_batch_enrollments': total_enrollments,
            },
            'retention': {
                'mature_farms_count': mature_farms.count(),
                'still_operational': still_operational,
                'retention_rate_percent': retention_rate,
            },
            'coverage': {
                'total_regions': regions_with_farms,
                'regions_list': total_regions[:10],  # Top 10
            },
            'drill_down': {
                'available_regions': total_regions if not region else None,
                'available_constituencies': (
                    self._get_constituencies_in_region(region) 
                    if region and not constituency else None
                ),
            },
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['medium'])
        return result
    
    def get_enrollment_trend(
        self, 
        months: int = 12,
        region: str = None,
        constituency: str = None
    ) -> Dict[str, Any]:
        """Get farmer enrollment trend over time."""
        cache_key = self._get_cache_key('enrollment_trend', months, region, constituency)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        farms = self._get_farm_queryset(region, constituency)
        start_date = self.now - timedelta(days=months * 30)
        
        trend = farms.filter(
            created_at__gte=start_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id'),
            government=Count('id', filter=Q(
                registration_source__in=['YEA Program', 'Government Initiative']
            )),
            independent=Count('id', filter=Q(
                registration_source__in=['Self Registration', 'Independent']
            ))
        ).order_by('month')
        
        result = {
            'period_months': months,
            'trend': [
                {
                    'month': item['month'].strftime('%Y-%m') if item['month'] else None,
                    'total': item['count'],
                    'government': item['government'],
                    'independent': item['independent'],
                }
                for item in trend
            ],
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['long'])
        return result
    
    # =========================================================================
    # 2. PRODUCTION REPORTS
    # =========================================================================
    
    def get_production_overview(
        self, 
        region: str = None, 
        constituency: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get national/regional production overview.
        
        Includes:
        - Total egg production
        - Average production per farm
        - Production trends
        - Regional comparison (if national view)
        """
        cache_key = self._get_cache_key('production_overview', region, constituency, days)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        from flock_management.models import DailyProduction, Flock
        
        production = self._get_production_queryset(region, constituency)
        farms = self._get_farm_queryset(region, constituency)
        farm_ids = list(farms.values_list('id', flat=True))
        
        start_date = self.today - timedelta(days=days)
        period_production = production.filter(production_date__gte=start_date)
        
        # Aggregate production stats
        stats = period_production.aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            small_eggs=Coalesce(Sum('small_eggs'), 0),
            soft_shell=Coalesce(Sum('soft_shell_eggs'), 0),
            total_mortality=Coalesce(Sum('birds_died'), 0),
            feed_consumed_kg=Coalesce(Sum('feed_consumed_kg'), Decimal('0')),
        )
        
        # Bird counts
        total_birds = farms.aggregate(
            total=Coalesce(Sum('current_bird_count'), 0)
        )['total']
        
        total_capacity = farms.aggregate(
            total=Coalesce(Sum('total_bird_capacity'), 0)
        )['total']
        
        # Active flocks
        active_flocks = Flock.objects.filter(
            farm_id__in=farm_ids,
            status='active'
        ).count()
        
        # Calculate averages
        operational_farms = farms.filter(farm_status='Active').count()
        avg_eggs_per_farm = 0
        if operational_farms > 0:
            avg_eggs_per_farm = round(stats['total_eggs'] / operational_farms)
        
        # Egg quality rate
        egg_quality_rate = 0
        if stats['total_eggs'] > 0:
            egg_quality_rate = round(
                (stats['good_eggs'] / stats['total_eggs']) * 100, 1
            )
        
        # Mortality rate
        mortality_rate = 0
        if total_birds > 0:
            mortality_rate = round(
                (stats['total_mortality'] / total_birds) * 100, 2
            )
        
        # Daily production trend
        daily_trend = period_production.annotate(
            date=TruncDate('production_date')
        ).values('date').annotate(
            eggs=Coalesce(Sum('eggs_collected'), 0),
            mortality=Coalesce(Sum('birds_died'), 0),
        ).order_by('date')[:30]  # Last 30 days
        
        result = {
            'period_days': days,
            'production': {
                'total_eggs': stats['total_eggs'],
                'good_eggs': stats['good_eggs'],
                'small_eggs': stats['small_eggs'],
                'soft_shell_eggs': stats['soft_shell'],
                'egg_quality_rate_percent': egg_quality_rate,
                'avg_eggs_per_farm': avg_eggs_per_farm,
            },
            'birds': {
                'total': total_birds,
                'capacity': total_capacity,
                'utilization_percent': round(
                    (total_birds / total_capacity * 100), 1
                ) if total_capacity > 0 else 0,
                'active_flocks': active_flocks,
            },
            'mortality': {
                'total': stats['total_mortality'],
                'rate_percent': mortality_rate,
            },
            'feed': {
                'total_consumed_kg': float(stats['feed_consumed_kg']),
            },
            'daily_trend': [
                {
                    'date': item['date'].isoformat() if item['date'] else None,
                    'eggs': item['eggs'],
                    'mortality': item['mortality'],
                }
                for item in daily_trend
            ],
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['medium'])
        return result
    
    def get_regional_production_comparison(self) -> Dict[str, Any]:
        """
        Compare production metrics across all regions.
        National-level view only.
        """
        cache_key = self._get_cache_key('regional_production_comparison')
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        from farms.models import Farm, FarmLocation
        from flock_management.models import DailyProduction
        
        regions = self._get_available_regions()
        last_30_days = self.today - timedelta(days=30)
        
        comparison = []
        for region in regions:
            if not region:
                continue
                
            # Get farms in region
            farm_ids = FarmLocation.objects.filter(
                is_primary_location=True,
                region__iexact=region
            ).values_list('farm_id', flat=True)
            
            # Farm stats
            farms = Farm.objects.filter(id__in=farm_ids)
            farm_count = farms.count()
            total_birds = farms.aggregate(
                total=Coalesce(Sum('current_bird_count'), 0)
            )['total']
            
            # Production stats
            production = DailyProduction.objects.filter(
                farm_id__in=farm_ids,
                production_date__gte=last_30_days
            ).aggregate(
                total_eggs=Coalesce(Sum('eggs_collected'), 0),
                total_mortality=Coalesce(Sum('birds_died'), 0),
            )
            
            comparison.append({
                'region': region,
                'farms': farm_count,
                'birds': total_birds,
                'eggs_30d': production['total_eggs'],
                'mortality_30d': production['total_mortality'],
                'avg_eggs_per_farm': round(
                    production['total_eggs'] / farm_count
                ) if farm_count > 0 else 0,
            })
        
        # Sort by total eggs descending
        comparison.sort(key=lambda x: x['eggs_30d'], reverse=True)
        
        result = {
            'regions': comparison,
            'total_regions': len(comparison),
            'top_producer': comparison[0]['region'] if comparison else None,
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['long'])
        return result
    
    # =========================================================================
    # 3. FINANCIAL & ECONOMIC IMPACT REPORTS
    # =========================================================================
    
    def get_financial_overview(
        self, 
        region: str = None, 
        constituency: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get financial and economic impact metrics.
        
        Includes:
        - Marketplace transaction volume
        - Platform fees collected
        - Estimated farmer income
        - Economic impact estimates
        """
        cache_key = self._get_cache_key('financial_overview', region, constituency, days)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        from sales_revenue.marketplace_models import MarketplaceOrder
        from sales_revenue.models import PlatformSettings
        
        farms = self._get_farm_queryset(region, constituency)
        farm_ids = list(farms.values_list('id', flat=True))
        start_date = self.now - timedelta(days=days)
        
        # Marketplace orders
        orders = MarketplaceOrder.objects.filter(
            farm_id__in=farm_ids,
            created_at__gte=start_date,
            status__in=['confirmed', 'processing', 'ready', 'shipped', 
                       'delivered', 'completed']
        )
        
        order_stats = orders.aggregate(
            count=Count('id'),
            total_volume=Coalesce(Sum('total_amount'), Decimal('0.00')),
        )
        
        # Active sellers
        active_sellers = orders.values('farm_id').distinct().count()
        
        # Average order value
        avg_order_value = Decimal('0.00')
        if order_stats['count'] > 0:
            avg_order_value = order_stats['total_volume'] / order_stats['count']
        
        # Subscription/activation revenue (marketplace fees)
        marketplace_farms = farms.filter(
            marketplace_enabled=True
        ).count()
        
        # Get platform settings for fee rate
        settings = PlatformSettings.get_settings()
        activation_fee = settings.marketplace_activation_fee if settings else Decimal('50.00')
        # Use tier 1 commission as default rate for display
        commission_rate = settings.commission_tier_1_percentage if settings else Decimal('5.00')
        # Ensure commission_rate is Decimal (it may come as float from model default)
        commission_rate = Decimal(str(commission_rate))
        
        # Estimate commission based on average tier rate
        # In production, this should be calculated from actual transaction records
        estimated_commission = order_stats['total_volume'] * (commission_rate / Decimal('100'))
        
        # Estimated farmer earnings (volume - estimated commission)
        farmer_earnings = order_stats['total_volume'] - estimated_commission
        
        # Economic impact multiplier (rough estimate)
        economic_multiplier = Decimal('2.5')  # Each GHS generates 2.5x economic activity
        economic_impact = farmer_earnings * economic_multiplier
        
        result = {
            'period_days': days,
            'marketplace': {
                'total_orders': order_stats['count'],
                'transaction_volume_ghs': float(order_stats['total_volume']),
                'avg_order_value_ghs': float(round(avg_order_value, 2)),
                'active_sellers': active_sellers,
                'marketplace_enabled_farms': marketplace_farms,
            },
            'platform_revenue': {
                'estimated_commission_ghs': float(estimated_commission),
                'commission_rate_percent': float(commission_rate),
                'activation_fee_ghs': float(activation_fee),
            },
            'farmer_income': {
                'gross_earnings_ghs': float(order_stats['total_volume']),
                'net_earnings_ghs': float(farmer_earnings),
            },
            'economic_impact': {
                'estimated_multiplier': float(economic_multiplier),
                'total_impact_ghs': float(economic_impact),
            },
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['medium'])
        return result
    
    # =========================================================================
    # 4. FLOCK HEALTH & BIOSECURITY REPORTS
    # =========================================================================
    
    def get_flock_health_overview(
        self, 
        region: str = None, 
        constituency: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get flock health and biosecurity metrics.
        
        Includes:
        - Mortality statistics
        - Disease incidents
        - Vaccination coverage
        - Health alerts
        """
        cache_key = self._get_cache_key('flock_health', region, constituency, days)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        from flock_management.models import DailyProduction, Flock
        
        production = self._get_production_queryset(region, constituency)
        farms = self._get_farm_queryset(region, constituency)
        farm_ids = list(farms.values_list('id', flat=True))
        start_date = self.today - timedelta(days=days)
        
        period_production = production.filter(production_date__gte=start_date)
        
        # Mortality by reason
        mortality_by_reason = period_production.exclude(
            mortality_reason__isnull=True
        ).exclude(
            mortality_reason=''
        ).values('mortality_reason').annotate(
            count=Sum('birds_died')
        ).order_by('-count')
        
        # Total mortality
        total_mortality = period_production.aggregate(
            total=Coalesce(Sum('birds_died'), 0)
        )['total']
        
        # Total birds for mortality rate
        total_birds = farms.aggregate(
            total=Coalesce(Sum('current_bird_count'), 0)
        )['total']
        
        mortality_rate = 0
        if total_birds > 0:
            mortality_rate = round((total_mortality / total_birds) * 100, 2)
        
        # Farms with high mortality (>5% in period)
        high_mortality_farms = []
        for farm in farms.filter(current_bird_count__gt=0)[:100]:  # Limit for performance
            farm_mortality = period_production.filter(
                farm_id=farm.id
            ).aggregate(
                total=Coalesce(Sum('birds_died'), 0)
            )['total']
            
            if farm.current_bird_count > 0:
                rate = (farm_mortality / farm.current_bird_count) * 100
                if rate > 5:
                    high_mortality_farms.append({
                        'farm_name': farm.farm_name,
                        'mortality': farm_mortality,
                        'rate_percent': round(rate, 1),
                    })
        
        high_mortality_farms.sort(key=lambda x: x['rate_percent'], reverse=True)
        
        # Flock age distribution
        active_flocks = Flock.objects.filter(
            farm_id__in=farm_ids,
            status='active'
        ).select_related('farm')
        
        age_distribution = {
            'pullets_0_18_weeks': 0,
            'young_layers_18_40_weeks': 0,
            'peak_layers_40_72_weeks': 0,
            'mature_layers_72_plus': 0,
        }
        
        for flock in active_flocks:
            age_weeks = (self.today - flock.start_date).days // 7 if flock.start_date else 0
            if age_weeks < 18:
                age_distribution['pullets_0_18_weeks'] += flock.current_count or 0
            elif age_weeks < 40:
                age_distribution['young_layers_18_40_weeks'] += flock.current_count or 0
            elif age_weeks < 72:
                age_distribution['peak_layers_40_72_weeks'] += flock.current_count or 0
            else:
                age_distribution['mature_layers_72_plus'] += flock.current_count or 0
        
        result = {
            'period_days': days,
            'mortality': {
                'total': total_mortality,
                'rate_percent': mortality_rate,
                'by_reason': [
                    {
                        'reason': item['mortality_reason'],
                        'count': item['count'],
                    }
                    for item in mortality_by_reason[:10]
                ],
            },
            'high_mortality_alerts': high_mortality_farms[:10],
            'flock_age_distribution': age_distribution,
            'total_birds': total_birds,
            'active_flocks': active_flocks.count(),
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['medium'])
        return result
    
    # =========================================================================
    # 5. FOOD SECURITY & MARKET REPORTS
    # =========================================================================
    
    def get_food_security_metrics(
        self, 
        region: str = None, 
        constituency: str = None
    ) -> Dict[str, Any]:
        """
        Get food security and market contribution metrics.
        
        Includes:
        - National supply contribution
        - Market pricing data
        - Stock levels
        - Supply forecasts
        """
        cache_key = self._get_cache_key('food_security', region, constituency)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        from sales_revenue.inventory_models import FarmInventory
        from sales_revenue.marketplace_models import MarketplaceOrder
        from flock_management.models import DailyProduction
        
        farms = self._get_farm_queryset(region, constituency)
        farm_ids = list(farms.values_list('id', flat=True))
        
        last_30_days = self.today - timedelta(days=30)
        
        # Production metrics
        production_30d = DailyProduction.objects.filter(
            farm_id__in=farm_ids,
            production_date__gte=last_30_days
        ).aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
        )
        
        # Daily average production
        daily_avg = production_30d['total_eggs'] / 30
        
        # Current inventory/stock
        current_stock = FarmInventory.objects.filter(
            farm_id__in=farm_ids,
            quantity_available__gt=0
        ).aggregate(
            total_items=Count('id'),
            total_quantity=Coalesce(Sum('quantity_available'), Decimal('0')),
        )
        
        # Eggs inventory specifically
        egg_stock = FarmInventory.objects.filter(
            farm_id__in=farm_ids,
            category__iexact='eggs',
            quantity_available__gt=0
        ).aggregate(
            quantity=Coalesce(Sum('quantity_available'), Decimal('0')),
        )
        
        # Average pricing from marketplace - use active items with cost
        pricing = FarmInventory.objects.filter(
            farm_id__in=farm_ids,
            is_active=True,
            unit_cost__gt=0
        ).values('category').annotate(
            avg_price=Avg('unit_cost'),
        ).order_by('category')
        
        # Market activity
        market_orders = MarketplaceOrder.objects.filter(
            farm_id__in=farm_ids,
            created_at__gte=last_30_days,
            status__in=['completed', 'delivered']
        ).count()
        
        result = {
            'production': {
                'eggs_30d': production_30d['total_eggs'],
                'good_eggs_30d': production_30d['good_eggs'],
                'daily_average': round(daily_avg),
            },
            'stock_levels': {
                'total_items_listed': current_stock['total_items'],
                'egg_stock_crates': egg_stock['quantity'],
            },
            'market_activity': {
                'orders_completed_30d': market_orders,
            },
            'supply_estimate': {
                'weekly_capacity': round(daily_avg * 7),
                'monthly_capacity': round(daily_avg * 30),
            },
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['medium'])
        return result
    
    # =========================================================================
    # 6. PROCUREMENT & INSTITUTIONAL SUPPLY REPORTS
    # =========================================================================
    
    def get_procurement_overview(
        self, 
        region: str = None, 
        constituency: str = None,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Get government/institutional procurement metrics.
        
        Includes:
        - Government orders
        - School feeding program supply
        - Institutional buyer data
        """
        cache_key = self._get_cache_key('procurement', region, constituency, days)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        from procurement.models import ProcurementOrder
        
        start_date = self.now - timedelta(days=days)
        
        # Procurement orders
        orders = ProcurementOrder.objects.filter(
            created_at__gte=start_date
        )
        
        if region:
            orders = orders.filter(preferred_region__iexact=region)
        
        order_stats = orders.aggregate(
            total_orders=Count('id'),
            total_quantity=Coalesce(Sum('quantity_needed'), 0),
            fulfilled_quantity=Coalesce(Sum('quantity_delivered'), 0),
        )
        
        # Order by status
        status_breakdown = orders.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Top orders by quantity
        top_orders = orders.values('title', 'status').annotate(
            total_quantity=Sum('quantity_needed'),
        ).order_by('-total_quantity')[:10]
        
        # Fulfillment rate
        fulfillment_rate = 0
        if order_stats['total_quantity'] > 0:
            fulfillment_rate = round(
                (order_stats['fulfilled_quantity'] / order_stats['total_quantity']) * 100, 1
            )
        
        result = {
            'period_days': days,
            'orders': {
                'total': order_stats['total_orders'],
                'quantity_ordered': order_stats['total_quantity'],
                'quantity_fulfilled': order_stats['fulfilled_quantity'],
                'fulfillment_rate_percent': fulfillment_rate,
            },
            'status_breakdown': [
                {
                    'status': item['status'],
                    'count': item['count'],
                }
                for item in status_breakdown
            ],
            'top_orders': [
                {
                    'title': item['title'],
                    'status': item['status'],
                    'quantity': item['total_quantity'],
                }
                for item in top_orders
            ],
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['medium'])
        return result
    
    # =========================================================================
    # 7. FARMER WELFARE & IMPACT REPORTS
    # =========================================================================
    
    def get_farmer_welfare_metrics(
        self, 
        region: str = None, 
        constituency: str = None
    ) -> Dict[str, Any]:
        """
        Get farmer welfare and social impact metrics.
        
        Includes:
        - Employment statistics
        - Demographic breakdown
        - Gender distribution
        - Training/support participation
        """
        cache_key = self._get_cache_key('farmer_welfare', region, constituency)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        from accounts.models import User
        
        farms = self._get_farm_queryset(region, constituency)
        
        # Demographics
        gender_dist = farms.values('gender').annotate(
            count=Count('id')
        ).order_by('gender')
        
        # Age distribution
        from datetime import date
        today = date.today()
        
        age_ranges = {
            '18-25': Q(date_of_birth__lte=today.replace(year=today.year-18)) & 
                    Q(date_of_birth__gt=today.replace(year=today.year-26)),
            '26-35': Q(date_of_birth__lte=today.replace(year=today.year-26)) & 
                    Q(date_of_birth__gt=today.replace(year=today.year-36)),
            '36-45': Q(date_of_birth__lte=today.replace(year=today.year-36)) & 
                    Q(date_of_birth__gt=today.replace(year=today.year-46)),
            '46-55': Q(date_of_birth__lte=today.replace(year=today.year-46)) & 
                    Q(date_of_birth__gt=today.replace(year=today.year-56)),
            '56-65': Q(date_of_birth__lte=today.replace(year=today.year-56)) & 
                    Q(date_of_birth__gt=today.replace(year=today.year-66)),
        }
        
        age_distribution = {}
        for range_name, query in age_ranges.items():
            age_distribution[range_name] = farms.filter(query).count()
        
        # Education levels
        education_dist = farms.values('education_level').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Experience levels
        experience_dist = farms.values('experience_level').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Farmers with extension officer support
        with_extension = farms.filter(
            assigned_extension_officer__isnull=False
        ).count()
        
        # Employment estimate (assuming 1-3 workers per farm)
        total_farms = farms.count()
        estimated_employment = total_farms * 2  # Conservative 2 per farm
        
        result = {
            'demographics': {
                'total_farmers': total_farms,
                'gender': {
                    item['gender']: item['count'] 
                    for item in gender_dist if item['gender']
                },
                'age_distribution': age_distribution,
            },
            'education': {
                item['education_level']: item['count'] 
                for item in education_dist if item['education_level']
            },
            'experience': {
                str(item['experience_level']): item['count'] 
                for item in experience_dist
            },
            'support': {
                'with_extension_officer': with_extension,
                'without_extension_officer': total_farms - with_extension,
            },
            'employment_impact': {
                'direct_farmers': total_farms,
                'estimated_workers': estimated_employment,
                'total_estimated_jobs': total_farms + estimated_employment,
            },
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['long'])
        return result
    
    # =========================================================================
    # 8. OPERATIONAL REPORTS
    # =========================================================================
    
    def get_operational_metrics(
        self, 
        region: str = None, 
        constituency: str = None
    ) -> Dict[str, Any]:
        """
        Get operational efficiency metrics.
        
        Includes:
        - Extension officer coverage
        - Application processing times
        - Support ticket stats
        """
        cache_key = self._get_cache_key('operational', region, constituency)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        from accounts.models import User
        from farms.application_models import FarmApplication
        from farms.batch_enrollment_models import BatchEnrollmentApplication
        
        farms = self._get_farm_queryset(region, constituency)
        
        # Extension officer stats
        extension_officers = User.objects.filter(
            role='EXTENSION_OFFICER',
            is_active=True
        )
        
        if region:
            extension_officers = extension_officers.filter(region__iexact=region)
        if constituency:
            extension_officers = extension_officers.filter(
                constituency__iexact=constituency
            )
        
        eo_count = extension_officers.count()
        farms_with_eo = farms.filter(
            assigned_extension_officer__isnull=False
        ).count()
        
        # Average farms per extension officer
        avg_farms_per_eo = 0
        if eo_count > 0:
            avg_farms_per_eo = round(farms_with_eo / eo_count, 1)
        
        # Application processing stats
        last_90_days = self.now - timedelta(days=90)
        
        applications = FarmApplication.objects.filter(
            submitted_at__gte=last_90_days
        )
        
        if region:
            applications = applications.filter(region__iexact=region)
        if constituency:
            applications = applications.filter(
                primary_constituency__iexact=constituency
            )
        
        app_stats = applications.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(
                status__in=['submitted', 'constituency_review', 
                           'regional_review', 'national_review']
            )),
            approved=Count('id', filter=Q(status='approved')),
            rejected=Count('id', filter=Q(status='rejected')),
        )
        
        # Calculate approval rate
        total_decided = app_stats['approved'] + app_stats['rejected']
        approval_rate = 0
        if total_decided > 0:
            approval_rate = round(
                (app_stats['approved'] / total_decided) * 100, 1
            )
        
        # Average processing time (for approved applications)
        from django.db.models import Avg as DjangoAvg
        from django.db.models import F as DjangoF
        
        avg_processing = applications.filter(
            status='approved',
            final_approved_at__isnull=False
        ).annotate(
            processing_time=DjangoF('final_approved_at') - DjangoF('submitted_at')
        ).aggregate(
            avg=DjangoAvg('processing_time')
        )
        
        avg_processing_days = None
        if avg_processing['avg']:
            avg_processing_days = avg_processing['avg'].days
        
        result = {
            'extension_officers': {
                'total': eo_count,
                'farms_covered': farms_with_eo,
                'farms_uncovered': farms.count() - farms_with_eo,
                'avg_farms_per_officer': avg_farms_per_eo,
            },
            'applications': {
                'total_90d': app_stats['total'],
                'pending': app_stats['pending'],
                'approved': app_stats['approved'],
                'rejected': app_stats['rejected'],
                'approval_rate_percent': approval_rate,
                'avg_processing_days': avg_processing_days,
            },
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['medium'])
        return result
    
    # =========================================================================
    # COMBINED EXECUTIVE DASHBOARD
    # =========================================================================
    
    def get_executive_dashboard(
        self, 
        region: str = None, 
        constituency: str = None
    ) -> Dict[str, Any]:
        """
        Get combined executive dashboard with all key metrics.
        Optimized for the Minister/National Admin landing page.
        """
        cache_key = self._get_cache_key('executive_dashboard', region, constituency)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Gather all summaries in parallel-friendly structure
        result = {
            'program_performance': self.get_program_performance_overview(
                region, constituency
            ),
            'production': self.get_production_overview(region, constituency, days=30),
            'financial': self.get_financial_overview(region, constituency, days=30),
            'flock_health': self.get_flock_health_overview(region, constituency, days=30),
            'food_security': self.get_food_security_metrics(region, constituency),
            'farmer_welfare': self.get_farmer_welfare_metrics(region, constituency),
            'operational': self.get_operational_metrics(region, constituency),
            'drill_down': {
                'current_level': 'constituency' if constituency else (
                    'region' if region else 'national'
                ),
                'region': region,
                'constituency': constituency,
                'available_regions': (
                    self._get_available_regions() if not region else None
                ),
                'available_constituencies': (
                    self._get_constituencies_in_region(region) 
                    if region and not constituency else None
                ),
            },
            'as_of': self.now.isoformat(),
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['short'])
        return result
    
    # =========================================================================
    # DRILL-DOWN HELPERS
    # =========================================================================
    
    def get_drill_down_options(
        self, 
        region: str = None
    ) -> Dict[str, Any]:
        """Get available drill-down options for navigation."""
        cache_key = self._get_cache_key('drill_down_options', region)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        result = {
            'current_scope': 'regional' if region else 'national',
        }
        
        if region:
            # Show constituencies in region
            result['region'] = region
            result['constituencies'] = self._get_constituencies_in_region(region)
        else:
            # Show all regions
            result['regions'] = self._get_available_regions()
        
        self._set_cache(cache_key, result, CACHE_TTL['daily'])
        return result
    
    def get_farms_in_scope(
        self,
        region: str = None,
        constituency: str = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get list of farms for the deepest drill-down level.
        """
        cache_key = self._get_cache_key(
            'farms_list', region, constituency, page, page_size
        )
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        farms = self._get_farm_queryset(region, constituency)
        
        total = farms.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        farm_list = farms.select_related('user').order_by('-created_at')[start:end]
        
        result = {
            'farms': [
                {
                    'id': str(f.id),
                    'farm_name': f.farm_name,
                    'farmer_name': f.user.get_full_name() if f.user else 'Unknown',
                    'constituency': f.primary_constituency,
                    'status': f.farm_status,
                    'bird_count': f.current_bird_count or 0,
                    'registration_source': f.registration_source,
                    'created_at': f.created_at.isoformat(),
                }
                for f in farm_list
            ],
            'count': total,  # For backward compatibility with tests
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': (total + page_size - 1) // page_size,
            },
        }
        
        self._set_cache(cache_key, result, CACHE_TTL['short'])
        return result
