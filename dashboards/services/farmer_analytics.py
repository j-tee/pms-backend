"""
Farmer Analytics Service

Comprehensive analytics for individual farmers covering:
1. Production Analytics - Eggs, trends, forecasts
2. Flock Health & Mortality - Death rates, survival, alerts
3. Financial Analytics - Revenue, expenses, profit margins
4. Feed Efficiency - FCR, cost per egg, consumption patterns
5. Marketplace Performance - Orders, customers, conversion
6. Inventory Status - Stock levels, movements, value
7. Comparative Benchmarks - vs history, vs regional average
"""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List
from collections import defaultdict

from django.db.models import (
    Sum, Count, Avg, F, Q, Min, Max, Case, When, Value,
    DecimalField, IntegerField, FloatField
)
from django.db.models.functions import (
    TruncDate, TruncWeek, TruncMonth, Coalesce, ExtractWeekDay
)
from django.utils import timezone

from farms.models import Farm
from flock_management.models import Flock, DailyProduction
from feed_inventory.models import FeedPurchase, FeedInventory, FeedConsumption
from sales_revenue.models import EggSale, BirdSale
from sales_revenue.marketplace_models import MarketplaceOrder, OrderItem, Product
from sales_revenue.inventory_models import FarmInventory, StockMovement
from procurement.models import ProcurementInvoice

logger = logging.getLogger(__name__)


class FarmerAnalyticsService:
    """
    Comprehensive analytics service for individual farmers.
    
    Usage:
        from dashboards.services.farmer_analytics import FarmerAnalyticsService
        
        service = FarmerAnalyticsService(user)
        
        # Get full analytics dashboard
        analytics = service.get_full_analytics()
        
        # Get specific analytics
        production = service.get_production_analytics(days=30)
        financials = service.get_financial_analytics(days=90)
    """
    
    def __init__(self, user):
        self.user = user
        self.farm = None
        self._load_farm()
    
    def _load_farm(self):
        """Load farm for the user"""
        try:
            self.farm = Farm.objects.get(user=self.user)
        except Farm.DoesNotExist:
            self.farm = None
    
    def _get_date_range(self, days: int) -> tuple:
        """Get start and end dates for the period"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date
    
    # =========================================================================
    # FULL DASHBOARD
    # =========================================================================
    
    def get_full_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get complete analytics dashboard for a farmer.
        
        Args:
            days: Number of days for trend data (default 30)
            
        Returns:
            Complete analytics data covering all categories
        """
        if not self.farm:
            return {
                'error': 'No farm found for this user',
                'code': 'NO_FARM'
            }
        
        return {
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'farm': self._get_farm_summary(),
            'production': self.get_production_analytics(days),
            'flock_health': self.get_flock_health_analytics(days),
            'financial': self.get_financial_analytics(days),
            'feed': self.get_feed_analytics(days),
            'marketplace': self.get_marketplace_analytics(days),
            'inventory': self.get_inventory_analytics(),
            'benchmarks': self.get_benchmark_analytics(days),
        }
    
    def _get_farm_summary(self) -> Dict[str, Any]:
        """Get basic farm information"""
        if not self.farm:
            return {}
        
        active_flocks = Flock.objects.filter(farm=self.farm, status='Active')
        
        total_birds = active_flocks.aggregate(
            total=Coalesce(Sum('current_count'), 0)
        )['total']
        
        return {
            'farm_id': str(self.farm.id),
            'farm_name': self.farm.farm_name,
            'farm_number': self.farm.farm_id,
            'constituency': self.farm.primary_constituency or None,
            'primary_production_type': self.farm.primary_production_type,
            'total_bird_capacity': self.farm.total_bird_capacity,
            'current_bird_count': total_birds,
            'capacity_utilization': round(
                (total_birds / self.farm.total_bird_capacity * 100), 1
            ) if self.farm.total_bird_capacity > 0 else 0,
            'active_flocks': active_flocks.count(),
            'marketplace_enabled': self.farm.marketplace_enabled,
            'subscription_type': self.farm.subscription_type,
        }
    
    # =========================================================================
    # 1. PRODUCTION ANALYTICS
    # =========================================================================
    
    def get_production_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get egg production analytics with trends.
        
        Includes:
        - Total eggs collected
        - Production rate (eggs per bird)
        - Daily/weekly trends
        - Quality breakdown (good vs broken/dirty)
        - Peak production days
        """
        if not self.farm:
            return {}
        
        start_date, end_date = self._get_date_range(days)
        
        # Get production records for period
        productions = DailyProduction.objects.filter(
            farm=self.farm,
            production_date__gte=start_date,
            production_date__lte=end_date
        )
        
        # Aggregate totals
        totals = productions.aggregate(
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
            good_eggs=Coalesce(Sum('good_eggs'), 0),
            broken_eggs=Coalesce(Sum('broken_eggs'), 0),
            dirty_eggs=Coalesce(Sum('dirty_eggs'), 0),
            small_eggs=Coalesce(Sum('small_eggs'), 0),
            soft_shell_eggs=Coalesce(Sum('soft_shell_eggs'), 0),
        )
        
        total_eggs = totals['total_eggs']
        good_eggs = totals['good_eggs']
        
        # Get current laying birds count (active layer flocks)
        laying_flocks = Flock.objects.filter(
            farm=self.farm,
            status='Active',
            flock_type__in=['Layers', 'Breeders'],
            is_currently_producing=True
        )
        total_laying_birds = laying_flocks.aggregate(
            total=Coalesce(Sum('current_count'), 0)
        )['total']
        
        # Calculate production rate
        production_rate = 0
        if total_laying_birds > 0 and days > 0:
            eggs_per_bird_per_day = total_eggs / (total_laying_birds * days)
            production_rate = round(eggs_per_bird_per_day * 100, 1)  # As percentage
        
        # Daily trend data
        daily_trend = list(productions.values('production_date').annotate(
            eggs=Sum('eggs_collected'),
            good=Sum('good_eggs'),
            broken=Sum('broken_eggs'),
        ).order_by('production_date'))
        
        # Weekly aggregation
        weekly_trend = list(productions.annotate(
            week=TruncWeek('production_date')
        ).values('week').annotate(
            eggs=Sum('eggs_collected'),
            avg_daily=Avg('eggs_collected'),
        ).order_by('week'))
        
        # Best production days (day of week analysis)
        by_weekday = productions.annotate(
            weekday=ExtractWeekDay('production_date')
        ).values('weekday').annotate(
            avg_eggs=Avg('eggs_collected')
        ).order_by('-avg_eggs')
        
        weekday_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        best_days = [
            {
                'day': weekday_names[item['weekday'] - 1],
                'avg_eggs': round(item['avg_eggs'], 1)
            }
            for item in by_weekday[:3]
        ]
        
        # Quality breakdown
        quality_breakdown = {
            'good': good_eggs,
            'broken': totals['broken_eggs'],
            'dirty': totals['dirty_eggs'],
            'small': totals['small_eggs'],
            'soft_shell': totals['soft_shell_eggs'],
            'good_percentage': round(
                (good_eggs / total_eggs * 100), 1
            ) if total_eggs > 0 else 0,
        }
        
        # Calculate averages
        avg_daily = round(total_eggs / days, 1) if days > 0 else 0
        
        # Production forecast (simple linear projection)
        forecast_next_week = round(avg_daily * 7, 0)
        forecast_next_month = round(avg_daily * 30, 0)
        
        return {
            'summary': {
                'total_eggs': total_eggs,
                'avg_daily_production': avg_daily,
                'production_rate_percent': production_rate,
                'total_laying_birds': total_laying_birds,
                'eggs_per_bird': round(
                    total_eggs / total_laying_birds, 2
                ) if total_laying_birds > 0 else 0,
            },
            'quality': quality_breakdown,
            'daily_trend': daily_trend,
            'weekly_trend': weekly_trend,
            'best_production_days': best_days,
            'forecast': {
                'next_7_days': forecast_next_week,
                'next_30_days': forecast_next_month,
            },
            'crates_equivalent': {
                'total': round(total_eggs / 30, 1),
                'sellable': round(good_eggs / 30, 1),
            }
        }
    
    # =========================================================================
    # 2. FLOCK HEALTH & MORTALITY
    # =========================================================================
    
    def get_flock_health_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get flock health and mortality analytics.
        
        Includes:
        - Mortality rates
        - Deaths by cause
        - Survival rates
        - Health alerts
        """
        if not self.farm:
            return {}
        
        start_date, end_date = self._get_date_range(days)
        
        # Get all active flocks
        flocks = Flock.objects.filter(farm=self.farm, status='Active')
        
        flock_summary = flocks.aggregate(
            total_birds=Coalesce(Sum('current_count'), 0),
            initial_birds=Coalesce(Sum('initial_count'), 0),
            total_mortality=Coalesce(Sum('total_mortality'), 0),
        )
        
        # Get mortality from daily productions
        productions = DailyProduction.objects.filter(
            farm=self.farm,
            production_date__gte=start_date,
            production_date__lte=end_date
        )
        
        # Use conditional aggregation to count deaths by reason
        mortality_totals = productions.aggregate(
            total_deaths=Coalesce(Sum('birds_died'), 0),
            disease_deaths=Coalesce(Sum(
                Case(When(mortality_reason='Disease', then='birds_died'), default=0, output_field=IntegerField())
            ), 0),
            predator_deaths=Coalesce(Sum(
                Case(When(mortality_reason='Predator', then='birds_died'), default=0, output_field=IntegerField())
            ), 0),
            cannibalism_deaths=Coalesce(Sum(
                Case(When(mortality_reason='Cannibalism', then='birds_died'), default=0, output_field=IntegerField())
            ), 0),
            heat_stress_deaths=Coalesce(Sum(
                Case(When(mortality_reason='Heat Stress', then='birds_died'), default=0, output_field=IntegerField())
            ), 0),
            suffocation_deaths=Coalesce(Sum(
                Case(When(mortality_reason='Suffocation', then='birds_died'), default=0, output_field=IntegerField())
            ), 0),
            culled_deaths=Coalesce(Sum(
                Case(When(mortality_reason='Culled', then='birds_died'), default=0, output_field=IntegerField())
            ), 0),
            old_age_deaths=Coalesce(Sum(
                Case(When(mortality_reason='Old Age', then='birds_died'), default=0, output_field=IntegerField())
            ), 0),
            unknown_deaths=Coalesce(Sum(
                Case(When(Q(mortality_reason='Unknown') | Q(mortality_reason=''), then='birds_died'), default=0, output_field=IntegerField())
            ), 0),
        )
        
        total_deaths = mortality_totals['total_deaths']
        current_birds = flock_summary['total_birds']
        initial_birds = flock_summary['initial_birds']
        
        # Mortality rate for period
        mortality_rate_period = 0
        if current_birds + total_deaths > 0:
            mortality_rate_period = round(
                (total_deaths / (current_birds + total_deaths) * 100), 2
            )
        
        # Overall survival rate
        survival_rate = 0
        if initial_birds > 0:
            survival_rate = round((current_birds / initial_birds * 100), 1)
        
        # Mortality by cause breakdown
        causes_breakdown = {
            'disease': mortality_totals['disease_deaths'],
            'predator': mortality_totals['predator_deaths'],
            'cannibalism': mortality_totals['cannibalism_deaths'],
            'heat_stress': mortality_totals['heat_stress_deaths'],
            'suffocation': mortality_totals['suffocation_deaths'],
            'culled': mortality_totals['culled_deaths'],
            'old_age': mortality_totals['old_age_deaths'],
            'unknown': mortality_totals['unknown_deaths'],
        }
        
        # Daily mortality trend
        daily_mortality = list(productions.filter(
            birds_died__gt=0
        ).values('production_date').annotate(
            deaths=Sum('birds_died')
        ).order_by('production_date'))
        
        # Flock-level details
        flock_details = []
        for flock in flocks.select_related('housed_in'):
            flock_mortality_rate = 0
            if flock.initial_count > 0:
                flock_mortality_rate = round(
                    (flock.total_mortality / flock.initial_count * 100), 2
                )
            
            flock_details.append({
                'flock_id': str(flock.id),
                'flock_number': flock.flock_number,
                'flock_type': flock.flock_type,
                'breed': flock.breed,
                'current_count': flock.current_count,
                'initial_count': flock.initial_count,
                'mortality_count': flock.total_mortality,
                'mortality_rate': flock_mortality_rate,
                'survival_rate': round(flock.survival_rate_percent, 1),
                'age_weeks': float(flock.current_age_weeks) if flock.current_age_weeks else None,
                'housed_in': flock.house_name,
            })
        
        # Health alerts
        alerts = []
        avg_daily_mortality = total_deaths / days if days > 0 else 0
        
        # Check for mortality spikes (> 2x average)
        high_mortality_days = productions.filter(
            birds_died__gt=avg_daily_mortality * 2
        ).count()
        
        if high_mortality_days > 0:
            alerts.append({
                'type': 'mortality_spike',
                'severity': 'warning',
                'message': f'{high_mortality_days} days with above-average mortality in period',
            })
        
        # Check for high overall mortality rate
        if mortality_rate_period > 5:
            alerts.append({
                'type': 'high_mortality',
                'severity': 'critical' if mortality_rate_period > 10 else 'warning',
                'message': f'Mortality rate of {mortality_rate_period}% exceeds healthy threshold',
            })
        
        return {
            'summary': {
                'current_bird_count': current_birds,
                'initial_bird_count': initial_birds,
                'total_mortality': flock_summary['total_mortality'],
                'period_deaths': total_deaths,
                'mortality_rate_period': mortality_rate_period,
                'survival_rate': survival_rate,
                'avg_daily_mortality': round(avg_daily_mortality, 2),
            },
            'causes_breakdown': causes_breakdown,
            'daily_trend': daily_mortality,
            'flocks': flock_details,
            'alerts': alerts,
        }
    
    # =========================================================================
    # 3. FINANCIAL ANALYTICS
    # =========================================================================
    
    def get_financial_analytics(self, days: int = 90) -> Dict[str, Any]:
        """
        Get financial analytics including revenue, expenses, and profit.
        
        Includes:
        - Revenue from eggs, birds, marketplace
        - Expenses (feed, medication)
        - Profit margins
        - Revenue trends
        """
        if not self.farm:
            return {}
        
        start_date, end_date = self._get_date_range(days)
        
        # === REVENUE ===
        
        # Egg sales revenue
        egg_sales = EggSale.objects.filter(
            farm=self.farm,
            status='completed',
            sale_date__gte=start_date,
            sale_date__lte=end_date
        )
        
        egg_revenue = egg_sales.aggregate(
            total=Coalesce(Sum('subtotal'), Decimal('0')),
            count=Count('id'),
            commissions=Coalesce(Sum('platform_commission'), Decimal('0')),
            net=Coalesce(Sum('farmer_payout'), Decimal('0')),
        )
        
        # Bird sales revenue
        bird_sales = BirdSale.objects.filter(
            farm=self.farm,
            status='completed',
            sale_date__gte=start_date,
            sale_date__lte=end_date
        )
        
        bird_revenue = bird_sales.aggregate(
            total=Coalesce(Sum('subtotal'), Decimal('0')),
            count=Count('id'),
            birds_sold=Coalesce(Sum('quantity'), 0),
            net=Coalesce(Sum('farmer_payout'), Decimal('0')),
        )
        
        # Marketplace orders revenue
        marketplace_orders = MarketplaceOrder.objects.filter(
            farm=self.farm,
            status='completed',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        marketplace_revenue = marketplace_orders.aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0')),
            count=Count('id'),
        )
        
        # Government procurement revenue
        procurement_invoices = ProcurementInvoice.objects.filter(
            farm=self.farm,
            payment_status='paid',
            payment_date__gte=start_date,
            payment_date__lte=end_date
        )
        
        procurement_revenue = procurement_invoices.aggregate(
            gross=Coalesce(Sum('gross_amount'), Decimal('0')),
            net=Coalesce(Sum('total_amount'), Decimal('0')),
            deductions=Coalesce(
                Sum('quality_deduction') + Sum('mortality_deduction') + Sum('other_deductions'),
                Decimal('0')
            ),
            count=Count('id'),
        )
        
        total_revenue = (
            egg_revenue['total'] + 
            bird_revenue['total'] + 
            marketplace_revenue['total'] +
            procurement_revenue['net']
        )
        
        # === EXPENSES ===
        
        # Feed costs (from purchases)
        feed_purchases = FeedPurchase.objects.filter(
            farm=self.farm,
            purchase_date__gte=start_date,
            purchase_date__lte=end_date
        )
        
        feed_cost = feed_purchases.aggregate(
            total=Coalesce(Sum('total_cost'), Decimal('0'))
        )['total']
        
        # Flock-accumulated costs
        flocks = Flock.objects.filter(farm=self.farm, status='Active')
        flock_costs = flocks.aggregate(
            medication=Coalesce(Sum('total_medication_cost'), Decimal('0')),
            vaccination=Coalesce(Sum('total_vaccination_cost'), Decimal('0')),
        )
        
        total_expenses = feed_cost + flock_costs['medication'] + flock_costs['vaccination']
        
        # === PROFIT ===
        gross_profit = total_revenue - total_expenses
        profit_margin = 0
        if total_revenue > 0:
            profit_margin = round((float(gross_profit) / float(total_revenue) * 100), 1)
        
        # === TRENDS ===
        
        # Revenue by month
        monthly_revenue = []
        
        # Egg sales by month
        egg_monthly = egg_sales.annotate(
            month=TruncMonth('sale_date')
        ).values('month').annotate(
            amount=Sum('subtotal')
        ).order_by('month')
        
        monthly_data = defaultdict(lambda: {'eggs': 0, 'birds': 0, 'marketplace': 0, 'procurement': 0})
        for item in egg_monthly:
            if item['month']:
                key = item['month'].strftime('%Y-%m')
                monthly_data[key]['eggs'] = float(item['amount'] or 0)
        
        bird_monthly = bird_sales.annotate(
            month=TruncMonth('sale_date')
        ).values('month').annotate(
            amount=Sum('subtotal')
        ).order_by('month')
        
        for item in bird_monthly:
            if item['month']:
                key = item['month'].strftime('%Y-%m')
                monthly_data[key]['birds'] = float(item['amount'] or 0)
        
        marketplace_monthly = marketplace_orders.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            amount=Sum('total_amount')
        ).order_by('month')
        
        for item in marketplace_monthly:
            if item['month']:
                key = item['month'].strftime('%Y-%m')
                monthly_data[key]['marketplace'] = float(item['amount'] or 0)
        
        # Procurement revenue by month
        procurement_monthly = procurement_invoices.annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            amount=Sum('total_amount')
        ).order_by('month')
        
        for item in procurement_monthly:
            if item['month']:
                key = item['month'].strftime('%Y-%m')
                monthly_data[key]['procurement'] = float(item['amount'] or 0)
        
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            monthly_revenue.append({
                'month': month_key,
                'eggs': data['eggs'],
                'birds': data['birds'],
                'marketplace': data['marketplace'],
                'procurement': data.get('procurement', 0),
                'total': data['eggs'] + data['birds'] + data['marketplace'] + data.get('procurement', 0),
            })
        
        return {
            'summary': {
                'total_revenue': float(total_revenue),
                'total_expenses': float(total_expenses),
                'gross_profit': float(gross_profit),
                'profit_margin_percent': profit_margin,
            },
            'revenue_breakdown': {
                'eggs': {
                    'gross': float(egg_revenue['total']),
                    'net': float(egg_revenue['net']),
                    'commissions': float(egg_revenue['commissions']),
                    'transactions': egg_revenue['count'],
                },
                'birds': {
                    'gross': float(bird_revenue['total']),
                    'net': float(bird_revenue['net']),
                    'birds_sold': bird_revenue['birds_sold'],
                    'transactions': bird_revenue['count'],
                },
                'marketplace': {
                    'gross': float(marketplace_revenue['total']),
                    'orders': marketplace_revenue['count'],
                },
                'government_procurement': {
                    'gross': float(procurement_revenue['gross']),
                    'net': float(procurement_revenue['net']),
                    'deductions': float(procurement_revenue['deductions']),
                    'orders': procurement_revenue['count'],
                },
            },
            'expenses_breakdown': {
                'feed': float(feed_cost),
                'medication': float(flock_costs['medication']),
                'vaccination': float(flock_costs['vaccination']),
            },
            'monthly_trend': monthly_revenue,
            'metrics': {
                'avg_daily_revenue': round(float(total_revenue) / days, 2) if days > 0 else 0,
                'revenue_per_bird': round(
                    float(total_revenue) / self._get_farm_summary().get('current_bird_count', 1), 2
                ) if self._get_farm_summary().get('current_bird_count', 0) > 0 else 0,
            },
        }
    
    # =========================================================================
    # 4. FEED ANALYTICS
    # =========================================================================
    
    def get_feed_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get feed consumption and efficiency analytics.
        
        Includes:
        - Feed consumption trends
        - Feed conversion ratio (FCR)
        - Cost per egg/bird
        - Stock levels
        """
        if not self.farm:
            return {}
        
        start_date, end_date = self._get_date_range(days)
        
        # Daily feed consumption from production records
        productions = DailyProduction.objects.filter(
            farm=self.farm,
            production_date__gte=start_date,
            production_date__lte=end_date
        )
        
        feed_totals = productions.aggregate(
            total_kg=Coalesce(Sum('feed_consumed_kg'), Decimal('0')),
            total_cost=Coalesce(Sum('feed_cost_today'), Decimal('0')),
            total_eggs=Coalesce(Sum('eggs_collected'), 0),
        )
        
        total_feed_kg = feed_totals['total_kg']
        total_eggs = feed_totals['total_eggs']
        
        # Current bird count
        farm_summary = self._get_farm_summary()
        bird_count = farm_summary.get('current_bird_count', 0)
        
        # Feed conversion ratio (kg feed per dozen eggs for layers)
        fcr = 0
        if total_eggs > 0:
            dozen_eggs = total_eggs / 12
            fcr = round(float(total_feed_kg) / dozen_eggs, 3) if dozen_eggs > 0 else 0
        
        # Feed cost per egg
        cost_per_egg = 0
        if total_eggs > 0:
            cost_per_egg = round(float(feed_totals['total_cost']) / total_eggs, 4)
        
        # Feed per bird per day
        feed_per_bird_day = 0
        if bird_count > 0 and days > 0:
            feed_per_bird_day = round(float(total_feed_kg * 1000) / (bird_count * days), 1)  # grams
        
        # Daily consumption trend
        daily_consumption = list(productions.filter(
            feed_consumed_kg__gt=0
        ).values('production_date').annotate(
            kg=Sum('feed_consumed_kg'),
            cost=Sum('feed_cost_today'),
        ).order_by('production_date'))
        
        # Current feed inventory
        try:
            feed_inventory = FeedInventory.objects.filter(
                farm=self.farm
            ).aggregate(
                total_kg=Coalesce(Sum('current_stock_kg'), Decimal('0')),
                total_value=Coalesce(Sum(F('current_stock_kg') * F('unit_price')), Decimal('0')),
            )
        except Exception:
            feed_inventory = {'total_kg': Decimal('0'), 'total_value': Decimal('0')}
        
        # Days of feed remaining (based on average consumption)
        avg_daily_consumption = float(total_feed_kg) / days if days > 0 else 0
        days_remaining = 0
        if avg_daily_consumption > 0:
            days_remaining = round(float(feed_inventory['total_kg']) / avg_daily_consumption, 1)
        
        # Feed type breakdown from purchases
        feed_purchases = FeedPurchase.objects.filter(
            farm=self.farm,
            purchase_date__gte=start_date,
            purchase_date__lte=end_date
        ).select_related('feed_type')
        
        by_feed_type = list(feed_purchases.values(
            'feed_type__name', 'feed_type__category'
        ).annotate(
            quantity_kg=Sum('quantity_kg'),
            total_cost=Sum('total_cost'),
        ).order_by('-quantity_kg'))
        
        return {
            'summary': {
                'total_feed_consumed_kg': float(total_feed_kg),
                'total_feed_cost': float(feed_totals['total_cost']),
                'avg_daily_consumption_kg': round(avg_daily_consumption, 2),
                'feed_per_bird_grams': feed_per_bird_day,
            },
            'efficiency': {
                'fcr_kg_per_dozen_eggs': fcr,
                'cost_per_egg': cost_per_egg,
                'cost_per_crate': round(cost_per_egg * 30, 2),
            },
            'inventory': {
                'current_stock_kg': float(feed_inventory['total_kg']),
                'stock_value': float(feed_inventory['total_value']),
                'days_remaining': days_remaining,
                'reorder_alert': days_remaining < 7,
            },
            'daily_trend': daily_consumption,
            'by_feed_type': by_feed_type,
        }
    
    # =========================================================================
    # 5. MARKETPLACE PERFORMANCE
    # =========================================================================
    
    def get_marketplace_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get marketplace performance analytics.
        
        Includes:
        - Order counts and values
        - Customer metrics
        - Product performance
        - Conversion rates
        """
        if not self.farm:
            return {}
        
        if not self.farm.marketplace_enabled:
            return {
                'enabled': False,
                'message': 'Marketplace not activated. Activate to view analytics.',
            }
        
        start_date, end_date = self._get_date_range(days)
        
        # Orders
        orders = MarketplaceOrder.objects.filter(
            farm=self.farm,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        order_stats = orders.aggregate(
            total_orders=Count('id'),
            completed_orders=Count('id', filter=Q(status='completed')),
            cancelled_orders=Count('id', filter=Q(status='cancelled')),
            pending_orders=Count('id', filter=Q(status__in=['pending', 'confirmed', 'processing'])),
            total_revenue=Coalesce(
                Sum('total_amount', filter=Q(status='completed')),
                Decimal('0')
            ),
        )
        
        # Average order value
        avg_order_value = 0
        if order_stats['completed_orders'] > 0:
            avg_order_value = round(
                float(order_stats['total_revenue']) / order_stats['completed_orders'], 2
            )
        
        # Unique customers
        unique_customers = orders.filter(
            status='completed'
        ).values('customer').distinct().count()
        
        # Repeat customers (customers with > 1 order)
        repeat_customers = orders.filter(
            status='completed'
        ).values('customer').annotate(
            order_count=Count('id')
        ).filter(order_count__gt=1).count()
        
        # Products performance
        products = Product.objects.filter(farm=self.farm, status='active')
        
        product_stats = []
        for product in products[:10]:  # Top 10
            product_orders = OrderItem.objects.filter(
                product=product,
                order__status='completed',
                order__created_at__date__gte=start_date,
            )
            
            stats = product_orders.aggregate(
                quantity_sold=Coalesce(Sum('quantity'), Decimal('0'), output_field=DecimalField()),
                revenue=Coalesce(Sum('line_total'), Decimal('0'), output_field=DecimalField()),
                orders=Count('id'),
            )
            
            if stats['orders'] > 0:
                product_stats.append({
                    'product_id': str(product.id),
                    'name': product.name,
                    'category': product.category.name if product.category else None,
                    'quantity_sold': float(stats['quantity_sold']),
                    'revenue': float(stats['revenue']),
                    'orders': stats['orders'],
                })
        
        # Sort by revenue
        product_stats.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Orders by status
        by_status = list(orders.values('status').annotate(
            count=Count('id'),
            value=Sum('total_amount'),
        ))
        
        # Daily orders trend
        daily_orders = list(orders.filter(
            status='completed'
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            orders=Count('id'),
            revenue=Sum('total_amount'),
        ).order_by('date'))
        
        return {
            'enabled': True,
            'summary': {
                'total_orders': order_stats['total_orders'],
                'completed_orders': order_stats['completed_orders'],
                'cancelled_orders': order_stats['cancelled_orders'],
                'pending_orders': order_stats['pending_orders'],
                'total_revenue': float(order_stats['total_revenue']),
                'avg_order_value': avg_order_value,
                'completion_rate': round(
                    (order_stats['completed_orders'] / order_stats['total_orders'] * 100), 1
                ) if order_stats['total_orders'] > 0 else 0,
            },
            'customers': {
                'unique_customers': unique_customers,
                'repeat_customers': repeat_customers,
                'repeat_rate': round(
                    (repeat_customers / unique_customers * 100), 1
                ) if unique_customers > 0 else 0,
            },
            'products': {
                'active_listings': products.count(),
                'top_sellers': product_stats[:5],
            },
            'by_status': by_status,
            'daily_trend': daily_orders,
        }
    
    # =========================================================================
    # 6. INVENTORY ANALYTICS
    # =========================================================================
    
    def get_inventory_analytics(self) -> Dict[str, Any]:
        """
        Get current inventory status.
        
        Includes:
        - Stock levels by category
        - Stock value
        - Movement summary
        - Alerts (low stock, aging)
        """
        if not self.farm:
            return {}
        
        # Get all inventory items
        inventory_items = FarmInventory.objects.filter(
            farm=self.farm,
            is_active=True
        )
        
        items_data = []
        total_value = Decimal('0')
        low_stock_items = []
        
        for item in inventory_items:
            item_value = item.quantity_available * item.unit_cost
            total_value += item_value
            
            item_data = {
                'id': str(item.id),
                'category': item.category,
                'product_name': item.product_name,
                'quantity': float(item.quantity_available),
                'unit': item.unit,
                'unit_cost': float(item.unit_cost),
                'total_value': float(item_value),
                'is_low_stock': item.is_low_stock,
                'oldest_stock_date': item.oldest_stock_date.isoformat() if item.oldest_stock_date else None,
            }
            items_data.append(item_data)
            
            if item.is_low_stock:
                low_stock_items.append({
                    'name': item.product_name,
                    'quantity': float(item.quantity_available),
                    'threshold': float(item.low_stock_threshold),
                })
        
        # Category summary
        by_category = inventory_items.values('category').annotate(
            items=Count('id'),
            total_quantity=Sum('quantity_available'),
            total_value=Sum(F('quantity_available') * F('unit_cost')),
        )
        
        category_summary = {
            item['category']: {
                'items': item['items'],
                'quantity': float(item['total_quantity'] or 0),
                'value': float(item['total_value'] or 0),
            }
            for item in by_category
        }
        
        # Recent stock movements (last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        
        try:
            movements = StockMovement.objects.filter(
                inventory__farm=self.farm,
                movement_date__gte=thirty_days_ago
            )
            
            movement_summary = movements.values('movement_type').annotate(
                count=Count('id'),
                quantity=Sum('quantity'),
            )
        except Exception:
            movement_summary = []
        
        return {
            'summary': {
                'total_items': inventory_items.count(),
                'total_value': float(total_value),
                'low_stock_count': len(low_stock_items),
            },
            'by_category': category_summary,
            'items': items_data,
            'low_stock_alerts': low_stock_items,
            'recent_movements': list(movement_summary),
        }
    
    # =========================================================================
    # 7. BENCHMARK ANALYTICS
    # =========================================================================
    
    def get_benchmark_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comparative benchmarks.
        
        Includes:
        - Performance vs last period
        - Performance vs regional average
        """
        if not self.farm:
            return {}
        
        start_date, end_date = self._get_date_range(days)
        prev_start = start_date - timedelta(days=days)
        prev_end = start_date - timedelta(days=1)
        
        # Current period production
        current_production = DailyProduction.objects.filter(
            farm=self.farm,
            production_date__gte=start_date,
            production_date__lte=end_date
        ).aggregate(
            eggs=Coalesce(Sum('eggs_collected'), 0),
            mortality=Coalesce(Sum('birds_died'), 0),
            feed_kg=Coalesce(Sum('feed_consumed_kg'), Decimal('0')),
        )
        
        # Previous period production
        previous_production = DailyProduction.objects.filter(
            farm=self.farm,
            production_date__gte=prev_start,
            production_date__lte=prev_end
        ).aggregate(
            eggs=Coalesce(Sum('eggs_collected'), 0),
            mortality=Coalesce(Sum('birds_died'), 0),
            feed_kg=Coalesce(Sum('feed_consumed_kg'), Decimal('0')),
        )
        
        # Calculate changes
        def calc_change(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)
        
        vs_previous = {
            'eggs_change_percent': calc_change(
                current_production['eggs'],
                previous_production['eggs']
            ),
            'mortality_change_percent': calc_change(
                current_production['mortality'],
                previous_production['mortality']
            ),
            'feed_change_percent': calc_change(
                float(current_production['feed_kg']),
                float(previous_production['feed_kg'])
            ),
        }
        
        # Regional comparison (if constituency data available)
        regional_comparison = None
        if self.farm.primary_constituency:
            # Get averages for farms in same constituency
            regional_farms = Farm.objects.filter(
                primary_constituency=self.farm.primary_constituency,
                application_status='Approved'
            ).exclude(id=self.farm.id)
            
            regional_production = DailyProduction.objects.filter(
                farm__in=regional_farms,
                production_date__gte=start_date,
                production_date__lte=end_date
            )
            
            regional_avg = regional_production.aggregate(
                avg_eggs_per_farm=Avg('eggs_collected'),
                avg_mortality_per_farm=Avg('birds_died'),
            )
            
            farm_avg_eggs = current_production['eggs'] / days if days > 0 else 0
            
            if regional_avg['avg_eggs_per_farm']:
                regional_comparison = {
                    'regional_avg_daily_eggs': round(regional_avg['avg_eggs_per_farm'], 1),
                    'your_avg_daily_eggs': round(farm_avg_eggs, 1),
                    'vs_regional_percent': calc_change(
                        farm_avg_eggs,
                        regional_avg['avg_eggs_per_farm']
                    ),
                    'farms_in_region': regional_farms.count(),
                }
        
        return {
            'vs_previous_period': vs_previous,
            'current_period': {
                'total_eggs': current_production['eggs'],
                'total_mortality': current_production['mortality'],
                'total_feed_kg': float(current_production['feed_kg']),
            },
            'previous_period': {
                'total_eggs': previous_production['eggs'],
                'total_mortality': previous_production['mortality'],
                'total_feed_kg': float(previous_production['feed_kg']),
            },
            'regional_comparison': regional_comparison,
        }
