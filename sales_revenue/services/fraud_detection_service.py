"""
Fraud Detection Service

Detects potential off-platform sales by analyzing:
- Production vs sales discrepancies
- Mortality patterns
- Inventory anomalies
- Customer behavior changes
- Historical trends
"""

from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Avg, Q, F, Count
from django.core.cache import cache
import logging

from flock_management.models import DailyProduction, Flock
from sales_revenue.models import EggSale, BirdSale, FraudAlert
from farms.models import Farm


logger = logging.getLogger(__name__)


class FraudDetectionService:
    """
    Analyzes farm data to detect potential off-platform sales.
    
    Red flags:
    1. Production > Sales (eggs disappearing)
    2. Abnormal mortality rates
    3. Sudden drop in on-platform sales
    4. Inconsistent reporting patterns
    5. Large inventory but no sales
    """
    
    def __init__(self, farm):
        self.farm = farm
        self.alerts = []
        self.risk_score = 0
    
    def run_full_analysis(self, days=30, save=True):
        """
        Run complete fraud detection analysis.
        
        Args:
            days: Number of days to analyze (default 30)
            save: Whether to save FraudAlert to database (default True)
            
        Returns:
            FraudAlert object if risk score > 10, None otherwise
        """
        logger.info(f"Running fraud analysis for farm: {self.farm.farm_name}")
        
        # Run all detection checks
        self._check_production_sales_mismatch(days)
        self._check_mortality_anomalies(days)
        self._check_sudden_sales_drop(days)
        self._check_inventory_hoarding(days)
        self._check_customer_complaints(days)
        self._check_reporting_gaps(days)
        self._check_price_manipulation(days)
        
        # Calculate final risk score
        risk_level = self._calculate_risk_level()
        
        # Only create alert if risk score > 10 (LOW or higher)
        if self.risk_score < 10:
            logger.info(f"Farm {self.farm.farm_name} is CLEAN (score: {self.risk_score})")
            return None
        
        # Create FraudAlert
        alert = FraudAlert(
            farm=self.farm,
            risk_score=self.risk_score,
            risk_level=risk_level,
            alerts=self.alerts,
            analysis_period_days=days,
            status='new',
        )
        
        if save:
            alert.save()
            logger.warning(
                f"Fraud alert created for farm {self.farm.farm_name}: "
                f"{risk_level} risk (score: {self.risk_score})"
            )
        
        # Cache result for 24 hours
        cache_key = f'fraud_analysis_{self.farm.id}'
        cache.set(cache_key, {
            'farm': self.farm.farm_name,
            'risk_score': self.risk_score,
            'risk_level': risk_level,
            'alerts': self.alerts,
            'analysis_period_days': days,
            'analyzed_at': timezone.now().isoformat()
        }, 86400)
        
        return alert
    
    def _check_production_sales_mismatch(self, days):
        """
        Check if production significantly exceeds sales.
        
        Red flag: Eggs produced but not sold on platform
        """
        cutoff_date = timezone.now().date() - timedelta(days=days)
        
        # Get total egg production
        total_production = DailyProduction.objects.filter(
            flock__farm=self.farm,
            production_date__gte=cutoff_date
        ).aggregate(
            total_eggs=Sum('eggs_collected')
        )['total_eggs'] or 0
        
        # Get total egg sales (convert to pieces if needed)
        egg_sales = EggSale.objects.filter(
            farm=self.farm,
            sale_date__gte=cutoff_date,
            status__in=['paid', 'completed']
        ).aggregate(
            total_crates=Sum('quantity', filter=Q(unit='crate')),
            total_pieces=Sum('quantity', filter=Q(unit='piece'))
        )
        
        total_sold_crates = egg_sales['total_crates'] or 0
        total_sold_pieces = egg_sales['total_pieces'] or 0
        total_sold = (total_sold_crates * 30) + total_sold_pieces
        
        # Calculate discrepancy
        if total_production > 0:
            discrepancy = total_production - total_sold
            discrepancy_percentage = (discrepancy / total_production) * 100
            
            # Allow for 10% loss (breakage, consumption, etc.)
            expected_loss_rate = 10
            
            if discrepancy_percentage > expected_loss_rate + 15:  # 25% total threshold
                self.risk_score += 30
                self.alerts.append({
                    'type': 'PRODUCTION_SALES_MISMATCH',
                    'severity': 'HIGH',
                    'message': f'{discrepancy_percentage:.1f}% of eggs produced not sold on platform',
                    'details': {
                        'produced': int(total_production),
                        'sold': int(total_sold),
                        'missing': int(discrepancy),
                        'expected_loss': f'{expected_loss_rate}%',
                        'actual_loss': f'{discrepancy_percentage:.1f}%'
                    }
                })
            elif discrepancy_percentage > expected_loss_rate + 5:  # 15% total threshold
                self.risk_score += 15
                self.alerts.append({
                    'type': 'PRODUCTION_SALES_MISMATCH',
                    'severity': 'MEDIUM',
                    'message': f'{discrepancy_percentage:.1f}% discrepancy between production and sales',
                    'details': {
                        'produced': int(total_production),
                        'sold': int(total_sold),
                        'missing': int(discrepancy)
                    }
                })
    
    def _check_mortality_anomalies(self, days):
        """
        Check for suspiciously high mortality rates.
        
        Red flag: Reporting birds as dead to hide off-platform sales
        """
        cutoff_date = timezone.now().date() - timedelta(days=days)
        
        # Get mortality data
        mortality_data = DailyProduction.objects.filter(
            flock__farm=self.farm,
            production_date__gte=cutoff_date
        ).aggregate(
            total_mortality=Sum('birds_died'),
            avg_mortality=Avg('birds_died'),
            days_reported=Count('id')
        )
        
        total_mortality = mortality_data['total_mortality'] or 0
        avg_daily_mortality = mortality_data['avg_mortality'] or 0
        
        # Get current flock size
        current_birds = Flock.objects.filter(
            farm=self.farm,
            status='active'
        ).aggregate(total=Sum('current_count'))['total'] or 1
        
        # Calculate mortality rate
        mortality_rate = (total_mortality / (current_birds * days)) * 100
        
        # Industry standard: 0.5-1% per month (0.016-0.033% per day)
        # Suspicious: >3% per month (>0.1% per day)
        
        if mortality_rate > 0.1:  # >0.1% daily
            self.risk_score += 25
            self.alerts.append({
                'type': 'ABNORMAL_MORTALITY',
                'severity': 'HIGH',
                'message': f'Mortality rate {mortality_rate:.3f}% per day (industry avg: 0.033%)',
                'details': {
                    'total_deaths': int(total_mortality),
                    'avg_daily_deaths': round(avg_daily_mortality, 2),
                    'mortality_rate_daily': f'{mortality_rate:.3f}%',
                    'suspicion': 'Birds may be sold off-platform and reported as dead'
                }
            })
        elif mortality_rate > 0.05:  # >0.05% daily
            self.risk_score += 10
            self.alerts.append({
                'type': 'ELEVATED_MORTALITY',
                'severity': 'MEDIUM',
                'message': f'Mortality rate slightly elevated at {mortality_rate:.3f}% per day',
                'details': {
                    'total_deaths': int(total_mortality),
                    'industry_avg': '0.033% per day'
                }
            })
    
    def _check_sudden_sales_drop(self, days):
        """
        Check for sudden drops in on-platform sales.
        
        Red flag: Farmer switches to off-platform sales
        """
        # Compare recent sales to historical average
        cutoff_date = timezone.now().date() - timedelta(days=days)
        historical_cutoff = cutoff_date - timedelta(days=days)  # Previous period
        
        # Recent sales
        recent_sales = EggSale.objects.filter(
            farm=self.farm,
            sale_date__gte=cutoff_date,
            status__in=['paid', 'completed']
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        # Historical sales (previous period)
        historical_sales = EggSale.objects.filter(
            farm=self.farm,
            sale_date__gte=historical_cutoff,
            sale_date__lt=cutoff_date,
            status__in=['paid', 'completed']
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        recent_total = recent_sales['total'] or 0
        historical_total = historical_sales['total'] or 0
        
        if historical_total > 0:
            drop_percentage = ((historical_total - recent_total) / historical_total) * 100
            
            # Check if production is still normal
            recent_production = DailyProduction.objects.filter(
                flock__farm=self.farm,
                production_date__gte=cutoff_date
            ).aggregate(total=Sum('eggs_collected'))['total'] or 0
            
            historical_production = DailyProduction.objects.filter(
                flock__farm=self.farm,
                production_date__gte=historical_cutoff,
                production_date__lt=cutoff_date
            ).aggregate(total=Sum('eggs_collected'))['total'] or 0
            
            # If sales dropped but production stable = red flag
            if drop_percentage > 30 and recent_production >= historical_production * 0.9:
                self.risk_score += 35
                self.alerts.append({
                    'type': 'SUDDEN_SALES_DROP',
                    'severity': 'HIGH',
                    'message': f'Sales dropped {drop_percentage:.1f}% while production remained stable',
                    'details': {
                        'recent_sales': float(recent_total),
                        'historical_sales': float(historical_total),
                        'drop_percentage': f'{drop_percentage:.1f}%',
                        'production_stable': True,
                        'suspicion': 'May have switched to off-platform customers'
                    }
                })
    
    def _check_inventory_hoarding(self, days):
        """
        Check for large inventory with no corresponding sales.
        
        Red flag: Farmer stockpiling for off-platform bulk sale
        """
        # This would integrate with inventory management if implemented
        # For now, check production accumulation
        
        cutoff_date = timezone.now().date() - timedelta(days=7)  # Last week
        
        recent_production = DailyProduction.objects.filter(
            flock__farm=self.farm,
            production_date__gte=cutoff_date
        ).aggregate(total=Sum('eggs_collected'))['total'] or 0
        
        recent_sales = EggSale.objects.filter(
            farm=self.farm,
            sale_date__gte=cutoff_date,
            status__in=['paid', 'completed']
        ).aggregate(
            total_crates=Sum('quantity', filter=Q(unit='crate')),
            total_pieces=Sum('quantity', filter=Q(unit='piece'))
        )
        
        total_sold = ((recent_sales['total_crates'] or 0) * 30) + (recent_sales['total_pieces'] or 0)
        
        if recent_production > 0:
            unsold_percentage = ((recent_production - total_sold) / recent_production) * 100
            
            # Allow for fresh egg shelf life (7 days max)
            if unsold_percentage > 70:  # >70% unsold
                self.risk_score += 20
                self.alerts.append({
                    'type': 'INVENTORY_HOARDING',
                    'severity': 'MEDIUM',
                    'message': f'{unsold_percentage:.1f}% of last week\'s production unsold',
                    'details': {
                        'produced_last_week': int(recent_production),
                        'sold_last_week': int(total_sold),
                        'unsold': int(recent_production - total_sold),
                        'suspicion': 'May be stockpiling for off-platform bulk sale'
                    }
                })
    
    def _check_customer_complaints(self, days):
        """
        Check for customers complaining about availability.
        
        Red flag: Farmer tells platform customers "out of stock" but has eggs
        """
        # This would integrate with customer feedback system
        # Placeholder for now
        pass
    
    def _check_reporting_gaps(self, days):
        """
        Check for gaps in daily production reporting.
        
        Red flag: Farmer skips reporting on days with off-platform sales
        """
        cutoff_date = timezone.now().date() - timedelta(days=days)
        
        # Get reporting days
        reporting_days = DailyProduction.objects.filter(
            flock__farm=self.farm,
            production_date__gte=cutoff_date
        ).values_list('production_date', flat=True).distinct()
        
        expected_days = days
        actual_days = len(reporting_days)
        gap_percentage = ((expected_days - actual_days) / expected_days) * 100
        
        if gap_percentage > 20:  # Missing >20% of days
            self.risk_score += 15
            self.alerts.append({
                'type': 'REPORTING_GAPS',
                'severity': 'MEDIUM',
                'message': f'{gap_percentage:.1f}% of days not reported in last {days} days',
                'details': {
                    'expected_days': expected_days,
                    'reported_days': actual_days,
                    'missing_days': expected_days - actual_days,
                    'suspicion': 'May be hiding production on off-platform sale days'
                }
            })
    
    def _check_price_manipulation(self, days):
        """
        Check if farmer is consistently pricing above market to discourage platform sales.
        
        Red flag: Farmer overprices on platform to push customers off-platform
        """
        cutoff_date = timezone.now().date() - timedelta(days=days)
        
        # Get farmer's average price
        farmer_avg_price = EggSale.objects.filter(
            farm=self.farm,
            sale_date__gte=cutoff_date
        ).aggregate(avg_price=Avg('price_per_unit'))['avg_price']
        
        # Get market average price (all farms)
        market_avg_price = EggSale.objects.filter(
            sale_date__gte=cutoff_date,
            unit='crate'
        ).aggregate(avg_price=Avg('price_per_unit'))['avg_price']
        
        if farmer_avg_price and market_avg_price:
            price_difference = ((farmer_avg_price - market_avg_price) / market_avg_price) * 100
            
            if price_difference > 15:  # >15% above market
                self.risk_score += 10
                self.alerts.append({
                    'type': 'PRICE_MANIPULATION',
                    'severity': 'LOW',
                    'message': f'Pricing {price_difference:.1f}% above market average',
                    'details': {
                        'farmer_price': float(farmer_avg_price),
                        'market_price': float(market_avg_price),
                        'difference': f'+{price_difference:.1f}%',
                        'suspicion': 'May be discouraging platform sales with high prices'
                    }
                })
    
    def _calculate_risk_level(self):
        """Calculate risk level based on score"""
        if self.risk_score >= 60:
            return 'CRITICAL'
        elif self.risk_score >= 40:
            return 'HIGH'
        elif self.risk_score >= 20:
            return 'MEDIUM'
        elif self.risk_score >= 10:
            return 'LOW'
        else:
            return 'CLEAN'


class FraudPreventionService:
    """
    Proactive measures to prevent off-platform sales.
    """
    
    @staticmethod
    def get_prevention_strategies():
        """
        Return list of prevention strategies to implement.
        """
        return {
            'automated_monitoring': {
                'description': 'Daily automated fraud detection',
                'implementation': 'Celery task runs nightly analysis on all farms',
                'alerts': 'Email/SMS to admin when risk score > 40'
            },
            'random_audits': {
                'description': 'Random farm visits to verify inventory',
                'implementation': 'Extension officers verify stock matches records',
                'frequency': 'Monthly for high-risk farms, quarterly for others'
            },
            'customer_verification': {
                'description': 'Verify platform customers received their orders',
                'implementation': 'SMS survey after each sale',
                'metric': 'Track delivery confirmation rate'
            },
            'blockchain_tracking': {
                'description': 'Immutable production records',
                'implementation': 'Hash chain like FarmerPayout model',
                'benefit': 'Cannot retroactively alter production data'
            },
            'incentive_alignment': {
                'description': 'Make platform more attractive than off-platform',
                'strategies': [
                    'Lower commission for high-volume farmers',
                    'Instant settlements for loyal farmers',
                    'Guaranteed payment (vs cash risk)',
                    'Marketing support (platform promotes farm)',
                    'Quality certification (platform badge)',
                    'Input financing (only for platform-compliant farmers)'
                ]
            },
            'penalty_structure': {
                'description': 'Consequences for off-platform sales',
                'penalties': [
                    'Suspension from platform (1st offense: warning)',
                    'Loss of input financing eligibility',
                    'No extension officer support',
                    'Removal of quality certifications',
                    'Blacklist from government programs'
                ]
            },
            'transparency_tools': {
                'description': 'Make fraud detection visible to farmers',
                'features': [
                    'Show farmer their own risk score',
                    'Dashboard showing production vs sales ratio',
                    'Alerts when metrics look suspicious',
                    'Educational content on platform benefits'
                ]
            },
            'competitor_intelligence': {
                'description': 'Monitor if farmers listing same eggs elsewhere',
                'implementation': 'Scrape other platforms/marketplaces',
                'action': 'Alert if farm name appears on competitor site'
            }
        }
