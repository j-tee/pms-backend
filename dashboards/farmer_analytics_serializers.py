"""
Farmer Analytics Serializers

Serializers for farmer analytics API responses.
"""

from rest_framework import serializers
from decimal import Decimal


class FarmSummarySerializer(serializers.Serializer):
    """Basic farm information"""
    farm_id = serializers.UUIDField()
    farm_name = serializers.CharField()
    farm_number = serializers.CharField(allow_null=True)
    constituency = serializers.CharField(allow_null=True)
    primary_production_type = serializers.CharField()
    total_bird_capacity = serializers.IntegerField()
    current_bird_count = serializers.IntegerField()
    capacity_utilization = serializers.FloatField()
    active_flocks = serializers.IntegerField()
    marketplace_enabled = serializers.BooleanField()
    subscription_type = serializers.CharField()


# =============================================================================
# PRODUCTION ANALYTICS
# =============================================================================

class QualityBreakdownSerializer(serializers.Serializer):
    """Egg quality breakdown"""
    good = serializers.IntegerField()
    broken = serializers.IntegerField()
    dirty = serializers.IntegerField()
    small = serializers.IntegerField()
    soft_shell = serializers.IntegerField()
    good_percentage = serializers.FloatField()


class ProductionSummarySerializer(serializers.Serializer):
    """Production summary stats"""
    total_eggs = serializers.IntegerField()
    avg_daily_production = serializers.FloatField()
    production_rate_percent = serializers.FloatField()
    total_laying_birds = serializers.IntegerField()
    eggs_per_bird = serializers.FloatField()


class ProductionForecastSerializer(serializers.Serializer):
    """Production forecast"""
    next_7_days = serializers.IntegerField()
    next_30_days = serializers.IntegerField()


class CratesEquivalentSerializer(serializers.Serializer):
    """Eggs in crates"""
    total = serializers.FloatField()
    sellable = serializers.FloatField()


class DailyProductionTrendSerializer(serializers.Serializer):
    """Daily production trend item"""
    production_date = serializers.DateField()
    eggs = serializers.IntegerField()
    good = serializers.IntegerField()
    broken = serializers.IntegerField()


class WeeklyProductionTrendSerializer(serializers.Serializer):
    """Weekly production trend item"""
    week = serializers.DateField()
    eggs = serializers.IntegerField()
    avg_daily = serializers.FloatField()


class BestProductionDaySerializer(serializers.Serializer):
    """Best production day"""
    day = serializers.CharField()
    avg_eggs = serializers.FloatField()


class ProductionAnalyticsSerializer(serializers.Serializer):
    """Complete production analytics"""
    summary = ProductionSummarySerializer()
    quality = QualityBreakdownSerializer()
    daily_trend = DailyProductionTrendSerializer(many=True)
    weekly_trend = WeeklyProductionTrendSerializer(many=True)
    best_production_days = BestProductionDaySerializer(many=True)
    forecast = ProductionForecastSerializer()
    crates_equivalent = CratesEquivalentSerializer()


# =============================================================================
# FLOCK HEALTH ANALYTICS
# =============================================================================

class MortalitySummarySerializer(serializers.Serializer):
    """Mortality summary"""
    current_bird_count = serializers.IntegerField()
    initial_bird_count = serializers.IntegerField()
    total_mortality = serializers.IntegerField()
    period_deaths = serializers.IntegerField()
    mortality_rate_period = serializers.FloatField()
    survival_rate = serializers.FloatField()
    avg_daily_mortality = serializers.FloatField()


class MortalityCausesSerializer(serializers.Serializer):
    """Deaths by cause"""
    disease = serializers.IntegerField()
    predator = serializers.IntegerField()
    cannibalism = serializers.IntegerField()
    heat_stress = serializers.IntegerField()
    suffocation = serializers.IntegerField()
    culled = serializers.IntegerField()
    old_age = serializers.IntegerField()
    unknown = serializers.IntegerField()


class FlockDetailSerializer(serializers.Serializer):
    """Individual flock details"""
    flock_id = serializers.UUIDField()
    flock_number = serializers.CharField()
    flock_type = serializers.CharField()
    breed = serializers.CharField()
    current_count = serializers.IntegerField()
    initial_count = serializers.IntegerField()
    mortality_count = serializers.IntegerField()
    mortality_rate = serializers.FloatField()
    survival_rate = serializers.FloatField()
    age_weeks = serializers.FloatField(allow_null=True)
    housed_in = serializers.CharField(allow_null=True)


class HealthAlertSerializer(serializers.Serializer):
    """Health alert"""
    type = serializers.CharField()
    severity = serializers.CharField()
    message = serializers.CharField()


class FlockHealthAnalyticsSerializer(serializers.Serializer):
    """Complete flock health analytics"""
    summary = MortalitySummarySerializer()
    causes_breakdown = MortalityCausesSerializer()
    daily_trend = serializers.ListField()
    flocks = FlockDetailSerializer(many=True)
    alerts = HealthAlertSerializer(many=True)


# =============================================================================
# FINANCIAL ANALYTICS
# =============================================================================

class RevenueItemSerializer(serializers.Serializer):
    """Revenue by source"""
    gross = serializers.FloatField()
    net = serializers.FloatField(required=False)
    commissions = serializers.FloatField(required=False)
    deductions = serializers.FloatField(required=False)
    transactions = serializers.IntegerField(required=False)
    birds_sold = serializers.IntegerField(required=False)
    orders = serializers.IntegerField(required=False)


class RevenueBreakdownSerializer(serializers.Serializer):
    """Revenue by category"""
    eggs = RevenueItemSerializer()
    birds = RevenueItemSerializer()
    marketplace = RevenueItemSerializer()
    government_procurement = RevenueItemSerializer()


class ExpensesBreakdownSerializer(serializers.Serializer):
    """Expenses by category"""
    feed = serializers.FloatField()
    medication = serializers.FloatField()
    vaccination = serializers.FloatField()


class FinancialSummarySerializer(serializers.Serializer):
    """Financial summary"""
    total_revenue = serializers.FloatField()
    total_expenses = serializers.FloatField()
    gross_profit = serializers.FloatField()
    profit_margin_percent = serializers.FloatField()


class MonthlyRevenueSerializer(serializers.Serializer):
    """Monthly revenue trend"""
    month = serializers.CharField()
    eggs = serializers.FloatField()
    birds = serializers.FloatField()
    marketplace = serializers.FloatField()
    procurement = serializers.FloatField()
    total = serializers.FloatField()


class FinancialMetricsSerializer(serializers.Serializer):
    """Financial metrics"""
    avg_daily_revenue = serializers.FloatField()
    revenue_per_bird = serializers.FloatField()


class FinancialAnalyticsSerializer(serializers.Serializer):
    """Complete financial analytics"""
    summary = FinancialSummarySerializer()
    revenue_breakdown = RevenueBreakdownSerializer()
    expenses_breakdown = ExpensesBreakdownSerializer()
    monthly_trend = MonthlyRevenueSerializer(many=True)
    metrics = FinancialMetricsSerializer()


# =============================================================================
# FEED ANALYTICS
# =============================================================================

class FeedSummarySerializer(serializers.Serializer):
    """Feed consumption summary"""
    total_feed_consumed_kg = serializers.FloatField()
    total_feed_cost = serializers.FloatField()
    avg_daily_consumption_kg = serializers.FloatField()
    feed_per_bird_grams = serializers.FloatField()


class FeedEfficiencySerializer(serializers.Serializer):
    """Feed efficiency metrics"""
    fcr_kg_per_dozen_eggs = serializers.FloatField()
    cost_per_egg = serializers.FloatField()
    cost_per_crate = serializers.FloatField()


class FeedInventorySerializer(serializers.Serializer):
    """Current feed inventory"""
    current_stock_kg = serializers.FloatField()
    stock_value = serializers.FloatField()
    days_remaining = serializers.FloatField()
    reorder_alert = serializers.BooleanField()


class FeedAnalyticsSerializer(serializers.Serializer):
    """Complete feed analytics"""
    summary = FeedSummarySerializer()
    efficiency = FeedEfficiencySerializer()
    inventory = FeedInventorySerializer()
    daily_trend = serializers.ListField()
    by_feed_type = serializers.ListField()


# =============================================================================
# MARKETPLACE ANALYTICS
# =============================================================================

class MarketplaceSummarySerializer(serializers.Serializer):
    """Marketplace order summary"""
    total_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    avg_order_value = serializers.FloatField()
    completion_rate = serializers.FloatField()


class CustomerMetricsSerializer(serializers.Serializer):
    """Customer metrics"""
    unique_customers = serializers.IntegerField()
    repeat_customers = serializers.IntegerField()
    repeat_rate = serializers.FloatField()


class TopProductSerializer(serializers.Serializer):
    """Top selling product"""
    product_id = serializers.UUIDField()
    name = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    quantity_sold = serializers.FloatField()
    revenue = serializers.FloatField()
    orders = serializers.IntegerField()


class ProductsInfoSerializer(serializers.Serializer):
    """Products information"""
    active_listings = serializers.IntegerField()
    top_sellers = TopProductSerializer(many=True)


class MarketplaceAnalyticsSerializer(serializers.Serializer):
    """Complete marketplace analytics"""
    enabled = serializers.BooleanField()
    message = serializers.CharField(required=False)
    summary = MarketplaceSummarySerializer(required=False)
    customers = CustomerMetricsSerializer(required=False)
    products = ProductsInfoSerializer(required=False)
    by_status = serializers.ListField(required=False)
    daily_trend = serializers.ListField(required=False)


# =============================================================================
# INVENTORY ANALYTICS
# =============================================================================

class InventorySummarySerializer(serializers.Serializer):
    """Inventory summary"""
    total_items = serializers.IntegerField()
    total_value = serializers.FloatField()
    low_stock_count = serializers.IntegerField()


class InventoryItemSerializer(serializers.Serializer):
    """Inventory item"""
    id = serializers.UUIDField()
    category = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.FloatField()
    unit = serializers.CharField()
    unit_cost = serializers.FloatField()
    total_value = serializers.FloatField()
    is_low_stock = serializers.BooleanField()
    oldest_stock_date = serializers.CharField(allow_null=True)


class LowStockAlertSerializer(serializers.Serializer):
    """Low stock alert"""
    name = serializers.CharField()
    quantity = serializers.FloatField()
    threshold = serializers.FloatField()


class InventoryAnalyticsSerializer(serializers.Serializer):
    """Complete inventory analytics"""
    summary = InventorySummarySerializer()
    by_category = serializers.DictField()
    items = InventoryItemSerializer(many=True)
    low_stock_alerts = LowStockAlertSerializer(many=True)
    recent_movements = serializers.ListField()


# =============================================================================
# BENCHMARK ANALYTICS
# =============================================================================

class PeriodComparisonSerializer(serializers.Serializer):
    """Period comparison"""
    eggs_change_percent = serializers.FloatField()
    mortality_change_percent = serializers.FloatField()
    feed_change_percent = serializers.FloatField()


class PeriodStatsSerializer(serializers.Serializer):
    """Period statistics"""
    total_eggs = serializers.IntegerField()
    total_mortality = serializers.IntegerField()
    total_feed_kg = serializers.FloatField()


class RegionalComparisonSerializer(serializers.Serializer):
    """Regional comparison"""
    regional_avg_daily_eggs = serializers.FloatField()
    your_avg_daily_eggs = serializers.FloatField()
    vs_regional_percent = serializers.FloatField()
    farms_in_region = serializers.IntegerField()


class BenchmarkAnalyticsSerializer(serializers.Serializer):
    """Complete benchmark analytics"""
    vs_previous_period = PeriodComparisonSerializer()
    current_period = PeriodStatsSerializer()
    previous_period = PeriodStatsSerializer()
    regional_comparison = RegionalComparisonSerializer(allow_null=True)


# =============================================================================
# FULL ANALYTICS RESPONSE
# =============================================================================

class FarmerAnalyticsSerializer(serializers.Serializer):
    """Complete farmer analytics response"""
    period_days = serializers.IntegerField()
    generated_at = serializers.CharField()
    farm = FarmSummarySerializer()
    production = ProductionAnalyticsSerializer()
    flock_health = FlockHealthAnalyticsSerializer()
    financial = FinancialAnalyticsSerializer()
    feed = FeedAnalyticsSerializer()
    marketplace = MarketplaceAnalyticsSerializer()
    inventory = InventoryAnalyticsSerializer()
    benchmarks = BenchmarkAnalyticsSerializer()


# =============================================================================
# QUERY PARAMETER SERIALIZERS
# =============================================================================

class AnalyticsPeriodSerializer(serializers.Serializer):
    """Query parameters for analytics"""
    days = serializers.IntegerField(
        default=30,
        min_value=1,
        max_value=365,
        help_text="Number of days for analytics period (1-365)"
    )


class DateRangeSerializer(serializers.Serializer):
    """Date range query parameters"""
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    days = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=365,
        help_text="Alternative to start_date/end_date"
    )
    
    def validate(self, data):
        if not data.get('days') and not (data.get('start_date') and data.get('end_date')):
            data['days'] = 30  # Default
        return data
