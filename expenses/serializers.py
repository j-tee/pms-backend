"""
Serializers for Expense Tracking models.

Provides serialization for all expense-related data including:
- General expenses (all categories)
- Labor records (wages, workers)
- Utility records (electricity, water)
- Mortality loss records (economic loss from bird deaths)
- Recurring expense templates
- Expense summaries
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

from .models import (
    ExpenseCategory,
    ExpenseFrequency,
    ExpenseSubCategory,
    Expense,
    LaborRecord,
    UtilityRecord,
    MortalityLossRecord,
    RecurringExpenseTemplate,
    ExpenseSummary,
)
from farms.models import Farm
from flock_management.models import Flock


# =============================================================================
# EXPENSE SUB-CATEGORY SERIALIZERS
# =============================================================================

class ExpenseSubCategorySerializer(serializers.ModelSerializer):
    """Serializer for custom expense sub-categories"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = ExpenseSubCategory
        fields = [
            'id', 'farm', 'name', 'category', 'category_display',
            'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExpenseSubCategoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating sub-categories (farm auto-populated)"""
    
    class Meta:
        model = ExpenseSubCategory
        fields = ['name', 'category', 'description', 'is_active']


# =============================================================================
# EXPENSE SERIALIZERS
# =============================================================================

class ExpenseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for expense lists"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    flock_number = serializers.CharField(source='flock.flock_number', read_only=True, allow_null=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'expense_date', 'category', 'category_display',
            'subcategory', 'subcategory_name', 'description', 'total_amount',
            'flock', 'flock_number', 'payee_name', 'is_recurring', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ExpenseDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for expense viewing/editing"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    flock_number = serializers.CharField(source='flock.flock_number', read_only=True, allow_null=True)
    flock_type = serializers.CharField(source='flock.flock_type', read_only=True, allow_null=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'farm', 'flock', 'flock_number', 'flock_type',
            'expense_date', 'category', 'category_display',
            'subcategory', 'subcategory_name', 'description',
            'quantity', 'unit', 'unit_cost', 'total_amount',
            'frequency', 'frequency_display', 'is_recurring',
            'payment_status', 'payment_status_display', 'payment_method',
            'receipt_number', 'payee_name', 'payee_contact', 'notes',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'farm', 'total_amount', 'created_by', 'created_at', 'updated_at']


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating expenses (farm auto-populated)"""
    
    class Meta:
        model = Expense
        fields = [
            'flock', 'expense_date', 'category', 'subcategory',
            'description', 'quantity', 'unit', 'unit_cost',
            'frequency', 'is_recurring', 'payment_status', 'payment_method',
            'receipt_number', 'payee_name', 'payee_contact', 'notes'
        ]
    
    def validate_flock(self, value):
        """Ensure flock belongs to the same farm"""
        if value:
            request = self.context.get('request')
            if request and hasattr(request.user, 'farm'):
                if value.farm != request.user.farm:
                    raise serializers.ValidationError(
                        "Flock does not belong to your farm"
                    )
        return value


# =============================================================================
# LABOR RECORD SERIALIZERS
# =============================================================================

class LaborRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for labor records list"""
    worker_type_display = serializers.CharField(source='get_worker_type_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    flock_number = serializers.CharField(source='flock.flock_number', read_only=True, allow_null=True)
    
    class Meta:
        model = LaborRecord
        fields = [
            'id', 'work_date', 'worker_name', 'worker_type', 'worker_type_display',
            'task_type', 'task_type_display', 'hours_worked', 'total_pay',
            'flock', 'flock_number', 'created_at'
        ]
        read_only_fields = ['id', 'total_pay', 'created_at']


class LaborRecordDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for labor records"""
    worker_type_display = serializers.CharField(source='get_worker_type_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    flock_number = serializers.CharField(source='flock.flock_number', read_only=True, allow_null=True)
    
    class Meta:
        model = LaborRecord
        fields = [
            'id', 'expense', 'farm', 'flock', 'flock_number',
            'worker_name', 'worker_type', 'worker_type_display',
            'worker_contact', 'work_date', 'task_type', 'task_type_display',
            'hours_worked', 'hourly_rate', 'base_pay',
            'overtime_hours', 'overtime_rate', 'overtime_pay', 'total_pay',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'farm', 'base_pay', 'overtime_pay', 'total_pay', 'created_at', 'updated_at']


class LaborRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating labor records"""
    
    class Meta:
        model = LaborRecord
        fields = [
            'expense', 'flock', 'worker_name', 'worker_type', 'worker_contact',
            'work_date', 'task_type', 'hours_worked', 'hourly_rate',
            'overtime_hours', 'overtime_rate', 'notes'
        ]


# =============================================================================
# UTILITY RECORD SERIALIZERS
# =============================================================================

class UtilityRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for utility records list"""
    utility_type_display = serializers.CharField(source='get_utility_type_display', read_only=True)
    billing_period = serializers.SerializerMethodField()
    
    class Meta:
        model = UtilityRecord
        fields = [
            'id', 'billing_period_start', 'billing_period_end', 'billing_period',
            'utility_type', 'utility_type_display', 'units_consumed',
            'unit_of_measure', 'provider', 'created_at'
        ]
        read_only_fields = ['id', 'units_consumed', 'created_at']
    
    def get_billing_period(self, obj):
        if obj.billing_period_start and obj.billing_period_end:
            return f"{obj.billing_period_start} to {obj.billing_period_end}"
        return None


class UtilityRecordDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for utility records"""
    utility_type_display = serializers.CharField(source='get_utility_type_display', read_only=True)
    
    class Meta:
        model = UtilityRecord
        fields = [
            'id', 'expense', 'farm',
            'utility_type', 'utility_type_display',
            'billing_period_start', 'billing_period_end',
            'previous_reading', 'current_reading', 'units_consumed',
            'unit_of_measure', 'rate_per_unit',
            'provider', 'account_number',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'farm', 'units_consumed', 'created_at', 'updated_at']


class UtilityRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating utility records"""
    
    class Meta:
        model = UtilityRecord
        fields = [
            'expense', 'utility_type',
            'billing_period_start', 'billing_period_end',
            'previous_reading', 'current_reading',
            'unit_of_measure', 'rate_per_unit',
            'provider', 'account_number', 'notes'
        ]
    
    def validate(self, attrs):
        """Validate billing period"""
        start = attrs.get('billing_period_start')
        end = attrs.get('billing_period_end')
        if start and end and end < start:
            raise serializers.ValidationError({
                'billing_period_end': 'End date must be after start date'
            })
        return attrs


# =============================================================================
# MORTALITY LOSS RECORD SERIALIZERS
# =============================================================================

class MortalityLossRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for mortality loss records"""
    flock_number = serializers.CharField(source='flock.flock_number', read_only=True, allow_null=True)
    
    class Meta:
        model = MortalityLossRecord
        fields = [
            'id', 'mortality_date', 'flock', 'flock_number',
            'birds_lost', 'total_loss_value', 'additional_investment_value',
            'cause_of_death', 'created_at'
        ]
        read_only_fields = ['id', 'total_loss_value', 'additional_investment_value', 'created_at']


class MortalityLossRecordDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for mortality loss records"""
    flock_number = serializers.CharField(source='flock.flock_number', read_only=True, allow_null=True)
    
    class Meta:
        model = MortalityLossRecord
        fields = [
            'id', 'expense', 'farm', 'flock', 'flock_number', 'mortality_record',
            'mortality_date', 'birds_lost', 'cause_of_death', 'age_at_death_weeks',
            'acquisition_cost_per_bird', 'feed_cost_invested',
            'other_costs_invested', 'potential_revenue_lost',
            'total_loss_value', 'additional_investment_value',
            'costs_auto_calculated', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'farm', 'total_loss_value', 'additional_investment_value', 'created_at', 'updated_at']


class MortalityLossRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating mortality loss records"""
    
    class Meta:
        model = MortalityLossRecord
        fields = [
            'id', 'expense', 'flock', 'mortality_record', 'mortality_date', 'birds_lost',
            'cause_of_death', 'age_at_death_weeks',
            'acquisition_cost_per_bird', 'feed_cost_invested',
            'other_costs_invested', 'potential_revenue_lost',
            'total_loss_value', 'additional_investment_value',
            'costs_auto_calculated', 'notes'
        ]
        read_only_fields = ['id', 'total_loss_value', 'additional_investment_value', 'costs_auto_calculated']
    
    def create(self, validated_data):
        """
        Create MortalityLossRecord, handling auto_calculate kwarg.
        
        The auto_calculate flag is passed via serializer.save() from the view
        but it's not a model field - it's passed to model.save() as a kwarg.
        """
        # Pop non-model fields that are passed via save()
        auto_calculate = validated_data.pop('auto_calculate', False)
        # created_by is not a field on MortalityLossRecord - it's tracked on the parent Expense
        validated_data.pop('created_by', None)
        
        # Create the instance
        instance = MortalityLossRecord(**validated_data)
        # Save with auto_calculate flag
        instance.save(auto_calculate=auto_calculate)
        
        return instance


# =============================================================================
# RECURRING EXPENSE TEMPLATE SERIALIZERS
# =============================================================================

class RecurringExpenseTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for recurring expense templates"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    flock_number = serializers.CharField(source='flock.flock_number', read_only=True, allow_null=True)
    
    class Meta:
        model = RecurringExpenseTemplate
        fields = [
            'id', 'name', 'category', 'category_display',
            'estimated_amount', 'frequency', 'frequency_display',
            'flock', 'flock_number', 'is_active',
            'next_due_date', 'last_generated_date', 'created_at'
        ]
        read_only_fields = ['id', 'estimated_amount', 'last_generated_date', 'created_at']


class RecurringExpenseTemplateDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for recurring expense templates"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    flock_number = serializers.CharField(source='flock.flock_number', read_only=True, allow_null=True)
    
    class Meta:
        model = RecurringExpenseTemplate
        fields = [
            'id', 'farm', 'flock', 'flock_number',
            'name', 'category', 'category_display', 'subcategory', 'description',
            'quantity', 'unit', 'unit_cost', 'estimated_amount',
            'payee_name', 'payee_contact', 'frequency', 'frequency_display',
            'start_date', 'end_date', 'next_due_date',
            'is_active', 'last_generated_date', 'notes',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'farm', 'estimated_amount', 'last_generated_date', 'created_by', 'created_at', 'updated_at']


class RecurringExpenseTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating recurring expense templates"""
    
    class Meta:
        model = RecurringExpenseTemplate
        fields = [
            'flock', 'name', 'category', 'subcategory', 'description',
            'quantity', 'unit', 'unit_cost',
            'payee_name', 'payee_contact', 'frequency',
            'start_date', 'end_date', 'is_active', 'notes'
        ]


# =============================================================================
# EXPENSE SUMMARY SERIALIZERS
# =============================================================================

class ExpenseSummarySerializer(serializers.ModelSerializer):
    """Serializer for expense summaries"""
    period_type_display = serializers.CharField(source='get_period_type_display', read_only=True)
    flock_number = serializers.CharField(source='flock.flock_number', read_only=True, allow_null=True)
    
    class Meta:
        model = ExpenseSummary
        fields = [
            'id', 'farm', 'flock', 'flock_number',
            'period_type', 'period_type_display',
            'period_start', 'period_end',
            'labor_total', 'utilities_total', 'bedding_total',
            'transport_total', 'maintenance_total', 'overhead_total',
            'mortality_loss_total', 'miscellaneous_total',
            'grand_total', 'expense_count', 'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']


class ExpenseSummaryBreakdownSerializer(serializers.Serializer):
    """Serializer for expense breakdown response"""
    category = serializers.CharField()
    category_display = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    count = serializers.IntegerField()


class ExpenseDashboardSerializer(serializers.Serializer):
    """Serializer for expense dashboard data"""
    total_expenses = serializers.DecimalField(max_digits=14, decimal_places=2)
    expenses_this_month = serializers.DecimalField(max_digits=14, decimal_places=2)
    expenses_last_month = serializers.DecimalField(max_digits=14, decimal_places=2)
    month_over_month_change = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    top_category = serializers.CharField()
    top_category_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    
    breakdown = ExpenseSummaryBreakdownSerializer(many=True)
    
    pending_labor_payments = serializers.DecimalField(max_digits=14, decimal_places=2)
    pending_utility_payments = serializers.DecimalField(max_digits=14, decimal_places=2)
    
    recurring_count = serializers.IntegerField()
    recurring_monthly_total = serializers.DecimalField(max_digits=14, decimal_places=2)


# =============================================================================
# BULK OPERATIONS SERIALIZERS
# =============================================================================

class BulkExpenseCreateSerializer(serializers.Serializer):
    """Serializer for bulk expense creation"""
    expenses = ExpenseCreateSerializer(many=True)
    
    def validate_expenses(self, value):
        if len(value) > 100:
            raise serializers.ValidationError(
                "Maximum 100 expenses can be created at once"
            )
        return value


class BulkLaborRecordCreateSerializer(serializers.Serializer):
    """Serializer for bulk labor record creation"""
    records = LaborRecordCreateSerializer(many=True)
    
    def validate_records(self, value):
        if len(value) > 50:
            raise serializers.ValidationError(
                "Maximum 50 labor records can be created at once"
            )
        return value


# =============================================================================
# FLOCK COST ANALYSIS SERIALIZERS
# =============================================================================

class FlockCostBreakdownSerializer(serializers.Serializer):
    """Serializer for flock cost breakdown response"""
    flock_id = serializers.UUIDField()
    flock_number = serializers.CharField()
    flock_type = serializers.CharField()
    
    acquisition_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    feed_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    medication_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    vaccination_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    labor_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    utilities_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    bedding_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    transport_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    maintenance_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    overhead_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    miscellaneous_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    mortality_loss = serializers.DecimalField(max_digits=14, decimal_places=2)
    
    total_operational_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_investment = serializers.DecimalField(max_digits=14, decimal_places=2)
    
    cost_per_bird = serializers.DecimalField(max_digits=10, decimal_places=2)
    cost_per_bird_per_day = serializers.DecimalField(max_digits=10, decimal_places=4)
