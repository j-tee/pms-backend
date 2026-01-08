"""
Institutional Data API Views.

These endpoints provide aggregated/anonymized poultry sector data
for institutional subscribers (banks, insurers, agribusinesses).

All data is:
- Aggregated at regional/constituency level (no individual farmer data unless Enterprise tier)
- Anonymized (no PII, farm names replaced with IDs for Enterprise tier)
- Rate-limited based on subscription plan
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Avg, Count, F, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .institutional_auth import (
    InstitutionalAPIKeyAuthentication,
    IsInstitutionalSubscriber,
    HasDataAccess,
    InstitutionalRateLimiter,
)


class InstitutionalBaseView(APIView):
    """
    Base view for institutional data endpoints.
    Handles authentication, rate limiting, and common patterns.
    """
    authentication_classes = [InstitutionalAPIKeyAuthentication]
    permission_classes = [IsInstitutionalSubscriber, HasDataAccess]
    required_access = None  # Override in subclass
    
    def initial(self, request, *args, **kwargs):
        """Check rate limit before processing request"""
        super().initial(request, *args, **kwargs)
        
        subscriber = getattr(request, 'institutional_subscriber', None)
        api_key = getattr(request, 'institutional_api_key', None)
        
        if subscriber and api_key:
            InstitutionalRateLimiter.check_rate_limit(subscriber, api_key)
    
    def get_date_range(self, request, default_days=30, max_days=365):
        """Parse date range from query parameters"""
        days = min(int(request.query_params.get('days', default_days)), max_days)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Allow custom date range
        if 'start_date' in request.query_params:
            try:
                start_date = timezone.datetime.strptime(
                    request.query_params['start_date'], '%Y-%m-%d'
                ).date()
            except ValueError:
                pass
        
        if 'end_date' in request.query_params:
            try:
                end_date = timezone.datetime.strptime(
                    request.query_params['end_date'], '%Y-%m-%d'
                ).date()
            except ValueError:
                pass
        
        return start_date, end_date
    
    def filter_by_subscriber_regions(self, queryset, subscriber, region_field='region'):
        """Filter data to subscriber's preferred regions if specified"""
        if subscriber.preferred_regions:
            return queryset.filter(**{f'{region_field}__in': subscriber.preferred_regions})
        return queryset


class ProductionOverviewView(InstitutionalBaseView):
    """
    GET /api/institutional/production/overview/
    
    National/regional production overview with key metrics.
    Available to all plans.
    """
    required_access = 'access_regional_aggregates'
    
    def get(self, request):
        from flock_management.models import DailyEggProduction, Flock
        from farms.models import Farm
        
        subscriber = request.institutional_subscriber
        start_date, end_date = self.get_date_range(request)
        
        # Get farms queryset (filter by subscriber regions if specified)
        farms = Farm.objects.filter(status='operational')
        if subscriber.preferred_regions:
            farms = farms.filter(region__in=subscriber.preferred_regions)
        farm_ids = farms.values_list('id', flat=True)
        
        # Production data
        production = DailyEggProduction.objects.filter(
            flock__farm_id__in=farm_ids,
            collection_date__gte=start_date,
            collection_date__lte=end_date
        )
        
        production_stats = production.aggregate(
            total_eggs=Sum('total_eggs_collected'),
            good_eggs=Sum('good_eggs'),
            average_production=Avg('total_eggs_collected'),
        )
        
        # Flock data
        flock_stats = Flock.objects.filter(
            farm_id__in=farm_ids,
            status='active'
        ).aggregate(
            total_flocks=Count('id'),
            total_birds=Sum('current_bird_count'),
            average_flock_size=Avg('current_bird_count'),
        )
        
        # Regional breakdown
        regional_breakdown = farms.values('region').annotate(
            farm_count=Count('id'),
        ).order_by('-farm_count')
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'production': {
                'total_eggs': production_stats['total_eggs'] or 0,
                'good_eggs': production_stats['good_eggs'] or 0,
                'average_daily': round(production_stats['average_production'] or 0, 0),
                'good_egg_rate': round(
                    (production_stats['good_eggs'] or 0) / 
                    max(production_stats['total_eggs'] or 1, 1) * 100, 1
                ),
            },
            'flocks': {
                'total_active_flocks': flock_stats['total_flocks'] or 0,
                'total_birds': flock_stats['total_birds'] or 0,
                'average_flock_size': round(flock_stats['average_flock_size'] or 0, 0),
            },
            'farms': {
                'total_operational': farms.count(),
                'by_region': list(regional_breakdown),
            },
            'data_freshness': timezone.now().isoformat(),
        })


class ProductionTrendsView(InstitutionalBaseView):
    """
    GET /api/institutional/production/trends/
    
    Historical production trends by day/week/month.
    """
    required_access = 'access_production_trends'
    
    def get(self, request):
        from flock_management.models import DailyEggProduction
        from farms.models import Farm
        
        subscriber = request.institutional_subscriber
        start_date, end_date = self.get_date_range(request, default_days=90, max_days=365)
        granularity = request.query_params.get('granularity', 'week')  # day, week, month
        
        # Get farms
        farms = Farm.objects.filter(status='operational')
        if subscriber.preferred_regions:
            farms = farms.filter(region__in=subscriber.preferred_regions)
        farm_ids = farms.values_list('id', flat=True)
        
        # Get production data
        production = DailyEggProduction.objects.filter(
            flock__farm_id__in=farm_ids,
            collection_date__gte=start_date,
            collection_date__lte=end_date
        )
        
        # Aggregate by granularity
        if granularity == 'day':
            trunc_func = TruncDate('collection_date')
        elif granularity == 'month':
            trunc_func = TruncMonth('collection_date')
        else:
            trunc_func = TruncWeek('collection_date')
        
        trends = production.annotate(
            period=trunc_func
        ).values('period').annotate(
            total_eggs=Sum('total_eggs_collected'),
            good_eggs=Sum('good_eggs'),
            farms_reporting=Count('flock__farm_id', distinct=True),
        ).order_by('period')
        
        # Calculate rates
        trend_data = []
        for item in trends:
            trend_data.append({
                'period': item['period'].isoformat() if item['period'] else None,
                'total_eggs': item['total_eggs'] or 0,
                'good_eggs': item['good_eggs'] or 0,
                'good_egg_rate': round(
                    (item['good_eggs'] or 0) / max(item['total_eggs'] or 1, 1) * 100, 1
                ),
                'farms_reporting': item['farms_reporting'],
            })
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'granularity': granularity,
            },
            'trends': trend_data,
        })


class RegionalBreakdownView(InstitutionalBaseView):
    """
    GET /api/institutional/production/regions/
    
    Production breakdown by region.
    """
    required_access = 'access_regional_aggregates'
    
    def get(self, request):
        from flock_management.models import DailyEggProduction, Flock
        from farms.models import Farm
        
        subscriber = request.institutional_subscriber
        start_date, end_date = self.get_date_range(request)
        
        # Get farms
        farms = Farm.objects.filter(status='operational')
        if subscriber.preferred_regions:
            farms = farms.filter(region__in=subscriber.preferred_regions)
        
        # Regional stats
        regional_data = []
        for region in farms.values_list('region', flat=True).distinct():
            region_farms = farms.filter(region=region)
            farm_ids = region_farms.values_list('id', flat=True)
            
            production = DailyEggProduction.objects.filter(
                flock__farm_id__in=farm_ids,
                collection_date__gte=start_date,
                collection_date__lte=end_date
            ).aggregate(
                total_eggs=Sum('total_eggs_collected'),
                good_eggs=Sum('good_eggs'),
            )
            
            flock_stats = Flock.objects.filter(
                farm_id__in=farm_ids,
                status='active'
            ).aggregate(
                total_birds=Sum('current_bird_count'),
                total_flocks=Count('id'),
            )
            
            regional_data.append({
                'region': region,
                'farms': region_farms.count(),
                'active_flocks': flock_stats['total_flocks'] or 0,
                'total_birds': flock_stats['total_birds'] or 0,
                'total_eggs': production['total_eggs'] or 0,
                'good_eggs': production['good_eggs'] or 0,
            })
        
        # Sort by production
        regional_data.sort(key=lambda x: x['total_eggs'], reverse=True)
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'regions': regional_data,
        })


class ConstituencyBreakdownView(InstitutionalBaseView):
    """
    GET /api/institutional/production/constituencies/
    
    Production breakdown by constituency (Professional+ plans).
    """
    required_access = 'access_constituency_data'
    
    def get(self, request):
        from flock_management.models import DailyEggProduction, Flock
        from farms.models import Farm
        
        subscriber = request.institutional_subscriber
        start_date, end_date = self.get_date_range(request)
        region = request.query_params.get('region', None)
        
        # Get farms
        farms = Farm.objects.filter(status='operational')
        if subscriber.preferred_regions:
            farms = farms.filter(region__in=subscriber.preferred_regions)
        if region:
            farms = farms.filter(region=region)
        
        # Constituency stats
        constituency_data = []
        for item in farms.values('region', 'constituency').distinct():
            const_farms = farms.filter(
                region=item['region'],
                constituency=item['constituency']
            )
            farm_ids = const_farms.values_list('id', flat=True)
            
            production = DailyEggProduction.objects.filter(
                flock__farm_id__in=farm_ids,
                collection_date__gte=start_date,
                collection_date__lte=end_date
            ).aggregate(
                total_eggs=Sum('total_eggs_collected'),
            )
            
            flock_stats = Flock.objects.filter(
                farm_id__in=farm_ids,
                status='active'
            ).aggregate(
                total_birds=Sum('current_bird_count'),
            )
            
            constituency_data.append({
                'region': item['region'],
                'constituency': item['constituency'],
                'farms': const_farms.count(),
                'total_birds': flock_stats['total_birds'] or 0,
                'total_eggs': production['total_eggs'] or 0,
            })
        
        # Sort by production
        constituency_data.sort(key=lambda x: x['total_eggs'], reverse=True)
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'filter': {'region': region},
            'constituencies': constituency_data,
        })


class MarketPricesView(InstitutionalBaseView):
    """
    GET /api/institutional/market/prices/
    
    Average market prices by region.
    """
    required_access = 'access_market_prices'
    
    def get(self, request):
        from sales_revenue.models import EggSale, BirdSale
        from farms.models import Farm
        
        subscriber = request.institutional_subscriber
        start_date, end_date = self.get_date_range(request)
        
        # Get farms
        farms = Farm.objects.filter(status='operational')
        if subscriber.preferred_regions:
            farms = farms.filter(region__in=subscriber.preferred_regions)
        farm_ids = farms.values_list('id', flat=True)
        
        # Egg prices by region
        egg_prices = EggSale.objects.filter(
            farm_id__in=farm_ids,
            sale_date__gte=start_date,
            sale_date__lte=end_date,
            status='completed'
        ).values('farm__region').annotate(
            avg_price_per_crate=Avg('price_per_crate'),
            total_crates=Sum('quantity_crates'),
            total_value=Sum('gross_amount'),
            transactions=Count('id'),
        ).order_by('farm__region')
        
        # Bird prices by type
        bird_prices = BirdSale.objects.filter(
            farm_id__in=farm_ids,
            sale_date__gte=start_date,
            sale_date__lte=end_date,
            status='completed'
        ).values('bird_type').annotate(
            avg_price_per_bird=Avg('unit_price'),
            total_birds=Sum('quantity'),
            total_value=Sum('gross_amount'),
            transactions=Count('id'),
        ).order_by('bird_type')
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'egg_prices': [
                {
                    'region': item['farm__region'],
                    'avg_price_per_crate': float(item['avg_price_per_crate'] or 0),
                    'total_crates_sold': item['total_crates'] or 0,
                    'total_value': float(item['total_value'] or 0),
                    'transactions': item['transactions'],
                }
                for item in egg_prices
            ],
            'bird_prices': [
                {
                    'bird_type': item['bird_type'],
                    'avg_price_per_bird': float(item['avg_price_per_bird'] or 0),
                    'total_birds_sold': item['total_birds'] or 0,
                    'total_value': float(item['total_value'] or 0),
                    'transactions': item['transactions'],
                }
                for item in bird_prices
            ],
        })


class MortalityDataView(InstitutionalBaseView):
    """
    GET /api/institutional/health/mortality/
    
    Mortality rates by region (Professional+ plans).
    Useful for insurance risk assessment.
    """
    required_access = 'access_mortality_data'
    
    def get(self, request):
        from flock_management.models import MortalityRecord, Flock
        from farms.models import Farm
        
        subscriber = request.institutional_subscriber
        start_date, end_date = self.get_date_range(request)
        
        # Get farms
        farms = Farm.objects.filter(status='operational')
        if subscriber.preferred_regions:
            farms = farms.filter(region__in=subscriber.preferred_regions)
        farm_ids = farms.values_list('id', flat=True)
        
        # Regional mortality
        regional_mortality = []
        for region in farms.values_list('region', flat=True).distinct():
            region_farm_ids = farms.filter(region=region).values_list('id', flat=True)
            
            mortality = MortalityRecord.objects.filter(
                flock__farm_id__in=region_farm_ids,
                date__gte=start_date,
                date__lte=end_date
            ).aggregate(
                total_deaths=Sum('quantity'),
            )
            
            # Current flock sizes
            flock_stats = Flock.objects.filter(
                farm_id__in=region_farm_ids,
                status='active'
            ).aggregate(
                total_birds=Sum('current_bird_count'),
                initial_birds=Sum('initial_bird_count'),
            )
            
            initial_birds = flock_stats['initial_birds'] or 1
            total_deaths = mortality['total_deaths'] or 0
            
            regional_mortality.append({
                'region': region,
                'total_birds': flock_stats['total_birds'] or 0,
                'total_deaths': total_deaths,
                'mortality_rate': round(total_deaths / max(initial_birds, 1) * 100, 2),
            })
        
        # Causes breakdown (anonymized)
        causes = MortalityRecord.objects.filter(
            flock__farm_id__in=farm_ids,
            date__gte=start_date,
            date__lte=end_date
        ).values('cause').annotate(
            count=Sum('quantity')
        ).order_by('-count')
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'by_region': regional_mortality,
            'by_cause': [
                {'cause': item['cause'] or 'Unknown', 'count': item['count']}
                for item in causes
            ],
        })


class SupplyForecastView(InstitutionalBaseView):
    """
    GET /api/institutional/supply/forecast/
    
    Supply forecasting based on current flock data (Enterprise plans).
    """
    required_access = 'access_supply_forecasts'
    
    def get(self, request):
        from flock_management.models import Flock, DailyEggProduction
        from farms.models import Farm
        from django.db.models import Avg
        
        subscriber = request.institutional_subscriber
        forecast_weeks = min(int(request.query_params.get('weeks', 4)), 12)
        
        # Get farms
        farms = Farm.objects.filter(status='operational')
        if subscriber.preferred_regions:
            farms = farms.filter(region__in=subscriber.preferred_regions)
        farm_ids = farms.values_list('id', flat=True)
        
        # Current capacity
        active_flocks = Flock.objects.filter(
            farm_id__in=farm_ids,
            status='active'
        )
        
        flock_stats = active_flocks.aggregate(
            total_birds=Sum('current_bird_count'),
            total_flocks=Count('id'),
        )
        
        # Historical production rate (last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_production = DailyEggProduction.objects.filter(
            flock__farm_id__in=farm_ids,
            collection_date__gte=thirty_days_ago
        ).aggregate(
            avg_daily_eggs=Avg('total_eggs_collected'),
            avg_production_rate=Avg(
                F('total_eggs_collected') * 100.0 / F('flock__current_bird_count')
            ),
        )
        
        # Calculate forecasts
        avg_daily = recent_production['avg_daily_eggs'] or 0
        total_birds = flock_stats['total_birds'] or 0
        
        # Simple linear forecast
        forecasts = []
        for week in range(1, forecast_weeks + 1):
            # Assume stable production
            forecasts.append({
                'week': week,
                'start_date': (timezone.now().date() + timedelta(weeks=week-1)).isoformat(),
                'end_date': (timezone.now().date() + timedelta(weeks=week) - timedelta(days=1)).isoformat(),
                'projected_eggs': round(avg_daily * 7),
                'projected_birds': total_birds,  # Simplified, no mortality modeling
                'confidence': 'medium' if week <= 2 else 'low',
            })
        
        return Response({
            'current_capacity': {
                'total_birds': total_birds,
                'active_flocks': flock_stats['total_flocks'] or 0,
                'avg_daily_production': round(avg_daily),
                'production_rate': round(recent_production['avg_production_rate'] or 0, 1),
            },
            'forecast': forecasts,
            'methodology': 'Linear extrapolation from 30-day historical average',
            'disclaimer': 'Forecasts are estimates based on historical data and may not account for market conditions, disease outbreaks, or other factors.',
        })


class FarmPerformanceView(InstitutionalBaseView):
    """
    GET /api/institutional/farms/performance/
    
    Anonymized individual farm performance data (Enterprise only).
    Returns farm IDs, not names for privacy.
    """
    required_access = 'access_individual_farm_data'
    
    def get(self, request):
        from flock_management.models import DailyEggProduction, Flock
        from farms.models import Farm
        
        subscriber = request.institutional_subscriber
        start_date, end_date = self.get_date_range(request)
        limit = min(int(request.query_params.get('limit', 100)), subscriber.plan.max_export_records)
        
        # Get farms
        farms = Farm.objects.filter(status='operational')
        if subscriber.preferred_regions:
            farms = farms.filter(region__in=subscriber.preferred_regions)
        
        # Calculate performance metrics per farm
        farm_performance = []
        for farm in farms[:limit]:
            production = DailyEggProduction.objects.filter(
                flock__farm=farm,
                collection_date__gte=start_date,
                collection_date__lte=end_date
            ).aggregate(
                total_eggs=Sum('total_eggs_collected'),
                avg_daily=Avg('total_eggs_collected'),
            )
            
            flocks = Flock.objects.filter(farm=farm, status='active')
            flock_stats = flocks.aggregate(
                total_birds=Sum('current_bird_count'),
            )
            
            farm_performance.append({
                'farm_id': str(farm.id),  # Anonymized - no name
                'region': farm.region,
                'constituency': farm.constituency,
                'production_type': farm.production_type,
                'total_birds': flock_stats['total_birds'] or 0,
                'total_eggs': production['total_eggs'] or 0,
                'avg_daily_eggs': round(production['avg_daily'] or 0, 0),
            })
        
        # Sort by production
        farm_performance.sort(key=lambda x: x['total_eggs'], reverse=True)
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'farms': farm_performance,
            'total_farms': len(farm_performance),
            'note': 'Farm identifiers are anonymized. Contact support for data matching services.',
        })


class UsageStatusView(InstitutionalBaseView):
    """
    GET /api/institutional/usage/
    
    Get current API usage and quota status.
    Available to all authenticated subscribers.
    """
    required_access = None  # No specific access required
    
    def get(self, request):
        subscriber = request.institutional_subscriber
        usage = InstitutionalRateLimiter.get_usage(subscriber)
        
        return Response({
            'subscriber': {
                'organization': subscriber.organization_name,
                'plan': subscriber.plan.name,
                'status': subscriber.status,
            },
            'quota': {
                'daily': {
                    'used': usage['daily_used'],
                    'limit': usage['daily_limit'],
                    'remaining': usage['daily_remaining'],
                    'percent_used': round(usage['daily_used'] / max(usage['daily_limit'], 1) * 100, 1),
                },
                'monthly': {
                    'used': usage['monthly_used'],
                    'limit': usage['monthly_limit'],
                    'remaining': usage['monthly_remaining'],
                    'percent_used': round(usage['monthly_used'] / max(usage['monthly_limit'], 1) * 100, 1),
                },
            },
            'plan_features': {
                'access_regional_aggregates': subscriber.plan.access_regional_aggregates,
                'access_constituency_data': subscriber.plan.access_constituency_data,
                'access_production_trends': subscriber.plan.access_production_trends,
                'access_market_prices': subscriber.plan.access_market_prices,
                'access_mortality_data': subscriber.plan.access_mortality_data,
                'access_supply_forecasts': subscriber.plan.access_supply_forecasts,
                'access_individual_farm_data': subscriber.plan.access_individual_farm_data,
            },
        })
