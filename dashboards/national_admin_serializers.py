"""
National Admin Analytics Serializers

Serializers for National Admin / Agriculture Minister reporting endpoints.
"""

from rest_framework import serializers


# =============================================================================
# DRILL-DOWN SUPPORT
# =============================================================================

class DrillDownOptionsSerializer(serializers.Serializer):
    """Options for geographic drill-down navigation."""
    current_scope = serializers.CharField(read_only=True)
    region = serializers.CharField(read_only=True, allow_null=True)
    regions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
        required=False
    )
    constituencies = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
        required=False
    )


class DrillDownSerializer(serializers.Serializer):
    """Nested drill-down info in responses."""
    current_level = serializers.CharField(read_only=True)
    region = serializers.CharField(read_only=True, allow_null=True)
    constituency = serializers.CharField(read_only=True, allow_null=True)
    available_regions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
        allow_null=True
    )
    available_constituencies = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
        allow_null=True
    )


# =============================================================================
# PROGRAM PERFORMANCE
# =============================================================================

class ProgramPerformanceSummarySerializer(serializers.Serializer):
    total_farms = serializers.IntegerField()
    operational_farms = serializers.IntegerField()
    government_supported = serializers.IntegerField()
    independent = serializers.IntegerField()
    new_this_month = serializers.IntegerField()
    growth_rate_percent = serializers.FloatField()


class EnrollmentSummarySerializer(serializers.Serializer):
    active_batches = serializers.IntegerField()
    total_batch_enrollments = serializers.IntegerField()


class RetentionSummarySerializer(serializers.Serializer):
    mature_farms_count = serializers.IntegerField()
    still_operational = serializers.IntegerField()
    retention_rate_percent = serializers.FloatField()


class CoverageSummarySerializer(serializers.Serializer):
    total_regions = serializers.IntegerField()
    regions_list = serializers.ListField(child=serializers.CharField())


class ProgramPerformanceSerializer(serializers.Serializer):
    summary = ProgramPerformanceSummarySerializer()
    enrollment = EnrollmentSummarySerializer()
    retention = RetentionSummarySerializer()
    coverage = CoverageSummarySerializer()
    drill_down = DrillDownSerializer()
    as_of = serializers.DateTimeField()


class EnrollmentTrendItemSerializer(serializers.Serializer):
    month = serializers.CharField()
    total = serializers.IntegerField()
    government = serializers.IntegerField()
    independent = serializers.IntegerField()


class EnrollmentTrendSerializer(serializers.Serializer):
    period_months = serializers.IntegerField()
    trend = EnrollmentTrendItemSerializer(many=True)
    as_of = serializers.DateTimeField()


# =============================================================================
# PRODUCTION
# =============================================================================

class ProductionStatsSerializer(serializers.Serializer):
    total_eggs = serializers.IntegerField()
    good_eggs = serializers.IntegerField()
    small_eggs = serializers.IntegerField()
    soft_shell_eggs = serializers.IntegerField()
    egg_quality_rate_percent = serializers.FloatField()
    avg_eggs_per_farm = serializers.IntegerField()


class BirdStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    capacity = serializers.IntegerField()
    utilization_percent = serializers.FloatField()
    active_flocks = serializers.IntegerField()


class MortalitySummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    rate_percent = serializers.FloatField()


class FeedSummarySerializer(serializers.Serializer):
    total_consumed_kg = serializers.FloatField()


class DailyTrendItemSerializer(serializers.Serializer):
    date = serializers.CharField()
    eggs = serializers.IntegerField()
    mortality = serializers.IntegerField()


class ProductionOverviewSerializer(serializers.Serializer):
    period_days = serializers.IntegerField()
    production = ProductionStatsSerializer()
    birds = BirdStatsSerializer()
    mortality = MortalitySummarySerializer()
    feed = FeedSummarySerializer()
    daily_trend = DailyTrendItemSerializer(many=True)
    as_of = serializers.DateTimeField()


class RegionalProductionItemSerializer(serializers.Serializer):
    region = serializers.CharField()
    farms = serializers.IntegerField()
    birds = serializers.IntegerField()
    eggs_30d = serializers.IntegerField()
    mortality_30d = serializers.IntegerField()
    avg_eggs_per_farm = serializers.IntegerField()


class RegionalProductionComparisonSerializer(serializers.Serializer):
    regions = RegionalProductionItemSerializer(many=True)
    total_regions = serializers.IntegerField()
    top_producer = serializers.CharField(allow_null=True)
    as_of = serializers.DateTimeField()


# =============================================================================
# FINANCIAL
# =============================================================================

class MarketplaceStatsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    transaction_volume_ghs = serializers.FloatField()
    avg_order_value_ghs = serializers.FloatField()
    active_sellers = serializers.IntegerField()
    marketplace_enabled_farms = serializers.IntegerField()


class PlatformRevenueSerializer(serializers.Serializer):
    commission_collected_ghs = serializers.FloatField()
    commission_rate_percent = serializers.FloatField()
    activation_fee_ghs = serializers.FloatField()


class FarmerIncomeSerializer(serializers.Serializer):
    gross_earnings_ghs = serializers.FloatField()
    net_earnings_ghs = serializers.FloatField()


class EconomicImpactSerializer(serializers.Serializer):
    estimated_multiplier = serializers.FloatField()
    total_impact_ghs = serializers.FloatField()


class FinancialOverviewSerializer(serializers.Serializer):
    period_days = serializers.IntegerField()
    marketplace = MarketplaceStatsSerializer()
    platform_revenue = PlatformRevenueSerializer()
    farmer_income = FarmerIncomeSerializer()
    economic_impact = EconomicImpactSerializer()
    as_of = serializers.DateTimeField()


# =============================================================================
# FLOCK HEALTH
# =============================================================================

class MortalityByReasonSerializer(serializers.Serializer):
    reason = serializers.CharField()
    count = serializers.IntegerField()


class MortalityDetailSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    rate_percent = serializers.FloatField()
    by_reason = MortalityByReasonSerializer(many=True)


class HighMortalityAlertSerializer(serializers.Serializer):
    farm_name = serializers.CharField()
    mortality = serializers.IntegerField()
    rate_percent = serializers.FloatField()


class FlockAgeDistributionSerializer(serializers.Serializer):
    pullets_0_18_weeks = serializers.IntegerField()
    young_layers_18_40_weeks = serializers.IntegerField()
    peak_layers_40_72_weeks = serializers.IntegerField()
    mature_layers_72_plus = serializers.IntegerField()


class FlockHealthOverviewSerializer(serializers.Serializer):
    period_days = serializers.IntegerField()
    mortality = MortalityDetailSerializer()
    high_mortality_alerts = HighMortalityAlertSerializer(many=True)
    flock_age_distribution = FlockAgeDistributionSerializer()
    total_birds = serializers.IntegerField()
    active_flocks = serializers.IntegerField()
    as_of = serializers.DateTimeField()


# =============================================================================
# FOOD SECURITY
# =============================================================================

class FoodSecurityProductionSerializer(serializers.Serializer):
    eggs_30d = serializers.IntegerField()
    good_eggs_30d = serializers.IntegerField()
    daily_average = serializers.IntegerField()


class StockLevelsSerializer(serializers.Serializer):
    total_items_listed = serializers.IntegerField()
    egg_stock_crates = serializers.IntegerField()


class MarketActivitySerializer(serializers.Serializer):
    orders_completed_30d = serializers.IntegerField()


class SupplyEstimateSerializer(serializers.Serializer):
    weekly_capacity = serializers.IntegerField()
    monthly_capacity = serializers.IntegerField()


class FoodSecurityMetricsSerializer(serializers.Serializer):
    production = FoodSecurityProductionSerializer()
    stock_levels = StockLevelsSerializer()
    market_activity = MarketActivitySerializer()
    supply_estimate = SupplyEstimateSerializer()
    as_of = serializers.DateTimeField()


# =============================================================================
# PROCUREMENT
# =============================================================================

class ProcurementOrdersSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    quantity_ordered = serializers.IntegerField()
    quantity_fulfilled = serializers.IntegerField()
    fulfillment_rate_percent = serializers.FloatField()


class OrderStatusBreakdownSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class TopOrderSerializer(serializers.Serializer):
    title = serializers.CharField()
    status = serializers.CharField()
    quantity = serializers.IntegerField()


class ProcurementOverviewSerializer(serializers.Serializer):
    period_days = serializers.IntegerField()
    orders = ProcurementOrdersSerializer()
    status_breakdown = OrderStatusBreakdownSerializer(many=True)
    top_orders = TopOrderSerializer(many=True)
    as_of = serializers.DateTimeField()


# =============================================================================
# FARMER WELFARE
# =============================================================================

class DemographicsSerializer(serializers.Serializer):
    total_farmers = serializers.IntegerField()
    gender = serializers.DictField(child=serializers.IntegerField())
    age_distribution = serializers.DictField(child=serializers.IntegerField())


class SupportMetricsSerializer(serializers.Serializer):
    with_extension_officer = serializers.IntegerField()
    without_extension_officer = serializers.IntegerField()


class EmploymentImpactSerializer(serializers.Serializer):
    direct_farmers = serializers.IntegerField()
    estimated_workers = serializers.IntegerField()
    total_estimated_jobs = serializers.IntegerField()


class FarmerWelfareMetricsSerializer(serializers.Serializer):
    demographics = DemographicsSerializer()
    education = serializers.DictField(child=serializers.IntegerField())
    experience = serializers.DictField(child=serializers.IntegerField())
    support = SupportMetricsSerializer()
    employment_impact = EmploymentImpactSerializer()
    as_of = serializers.DateTimeField()


# =============================================================================
# OPERATIONAL
# =============================================================================

class ExtensionOfficerMetricsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    farms_covered = serializers.IntegerField()
    farms_uncovered = serializers.IntegerField()
    avg_farms_per_officer = serializers.FloatField()


class ApplicationMetricsSerializer(serializers.Serializer):
    total_90d = serializers.IntegerField()
    pending = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    approval_rate_percent = serializers.FloatField()
    avg_processing_days = serializers.IntegerField(allow_null=True)


class OperationalMetricsSerializer(serializers.Serializer):
    extension_officers = ExtensionOfficerMetricsSerializer()
    applications = ApplicationMetricsSerializer()
    as_of = serializers.DateTimeField()


# =============================================================================
# EXECUTIVE DASHBOARD (COMBINED)
# =============================================================================

class ExecutiveDashboardSerializer(serializers.Serializer):
    """Combined executive dashboard for Minister/National Admin."""
    program_performance = ProgramPerformanceSerializer()
    production = ProductionOverviewSerializer()
    financial = FinancialOverviewSerializer()
    flock_health = FlockHealthOverviewSerializer()
    food_security = FoodSecurityMetricsSerializer()
    farmer_welfare = FarmerWelfareMetricsSerializer()
    operational = OperationalMetricsSerializer()
    drill_down = DrillDownSerializer()
    as_of = serializers.DateTimeField()


# =============================================================================
# FARMS LIST (DRILL-DOWN)
# =============================================================================

class FarmListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    farm_name = serializers.CharField()
    farmer_name = serializers.CharField()
    constituency = serializers.CharField()
    status = serializers.CharField()
    bird_count = serializers.IntegerField()
    registration_source = serializers.CharField()
    created_at = serializers.DateTimeField()


class PaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class FarmListResponseSerializer(serializers.Serializer):
    farms = FarmListItemSerializer(many=True)
    pagination = PaginationSerializer()


# =============================================================================
# REQUEST SERIALIZERS
# =============================================================================

class ReportRequestSerializer(serializers.Serializer):
    """Base request serializer for report endpoints."""
    region = serializers.CharField(required=False, allow_null=True)
    constituency = serializers.CharField(required=False, allow_null=True)
    days = serializers.IntegerField(required=False, default=30, min_value=1, max_value=365)


class FarmListRequestSerializer(serializers.Serializer):
    """Request serializer for farm list drill-down."""
    region = serializers.CharField(required=False, allow_null=True)
    constituency = serializers.CharField(required=False, allow_null=True)
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)
