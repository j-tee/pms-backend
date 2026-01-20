"""
Views for Expense Tracking.

All views are farm-scoped to ensure data isolation between farms.
Farmers can only view and manage their own expense data.

API Endpoints:
- /api/expenses/ - List/create expenses
- /api/expenses/{id}/ - Retrieve/update/delete expense
- /api/expenses/dashboard/ - Expense dashboard overview
- /api/expenses/labor/ - Labor record management
- /api/expenses/utilities/ - Utility record management
- /api/expenses/mortality-losses/ - Mortality loss records
- /api/expenses/recurring/ - Recurring expense templates
- /api/expenses/categories/ - Expense categories (constants)
- /api/expenses/sub-categories/ - Custom sub-categories
- /api/expenses/summary/ - Expense summaries
- /api/expenses/flock/{flock_id}/costs/ - Flock cost breakdown
"""

from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Sum, Count, Q, F, Avg
from django.db.models.functions import Coalesce, TruncMonth, TruncWeek
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import timedelta
from decimal import Decimal
import logging

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
from .serializers import (
    ExpenseSubCategorySerializer,
    ExpenseSubCategoryCreateSerializer,
    ExpenseListSerializer,
    ExpenseDetailSerializer,
    ExpenseCreateSerializer,
    LaborRecordListSerializer,
    LaborRecordDetailSerializer,
    LaborRecordCreateSerializer,
    UtilityRecordListSerializer,
    UtilityRecordDetailSerializer,
    UtilityRecordCreateSerializer,
    MortalityLossRecordListSerializer,
    MortalityLossRecordDetailSerializer,
    MortalityLossRecordCreateSerializer,
    RecurringExpenseTemplateListSerializer,
    RecurringExpenseTemplateDetailSerializer,
    RecurringExpenseTemplateCreateSerializer,
    ExpenseSummarySerializer,
    ExpenseDashboardSerializer,
    FlockCostBreakdownSerializer,
    BulkExpenseCreateSerializer,
    BulkLaborRecordCreateSerializer,
)
from flock_management.models import Flock

logger = logging.getLogger(__name__)


# =============================================================================
# PERMISSION CLASSES
# =============================================================================

class IsFarmer(permissions.BasePermission):
    """
    Permission check for farmer access.
    Ensures the user has a farm associated with their account.
    """
    message = "You must have a registered farm to access expense tracking."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            hasattr(request.user, 'farm') and
            request.user.farm is not None
        )


class FarmScopedMixin:
    """
    Mixin that filters querysets to only include data belonging to the farmer's farm.
    
    SECURITY: This is the core security mechanism that prevents data breaches.
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def get_farm(self):
        """Get the authenticated farmer's farm."""
        return self.request.user.farm
    
    def get_queryset(self):
        """Filter queryset to only include records from the farmer's farm."""
        queryset = super().get_queryset()
        return queryset.filter(farm=self.get_farm())


# =============================================================================
# EXPENSE CATEGORY VIEWS (Constants)
# =============================================================================

class ExpenseCategoryListView(APIView):
    """
    GET /api/expenses/categories/
    
    List all expense categories (system constants).
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def get(self, request):
        categories = [
            {
                'value': choice[0],
                'label': choice[1],
                'description': self._get_category_description(choice[0])
            }
            for choice in ExpenseCategory.choices
        ]
        return Response(categories)
    
    def _get_category_description(self, category):
        descriptions = {
            'LABOR': 'Staff wages, worker payments, casual labor',
            'UTILITIES': 'Electricity, water, gas, internet',
            'BEDDING': 'Litter, sawdust, wood shavings',
            'TRANSPORT': 'Vehicle fuel, delivery costs, bird transport',
            'MAINTENANCE': 'Equipment repairs, building maintenance',
            'OVERHEAD': 'Administrative costs, insurance, licenses',
            'MORTALITY_LOSS': 'Economic loss from bird deaths',
            'MISCELLANEOUS': 'Other operational expenses',
        }
        return descriptions.get(category, '')


class ExpenseFrequencyListView(APIView):
    """
    GET /api/expenses/frequencies/
    
    List all expense frequencies (for recurring expenses).
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def get(self, request):
        frequencies = [
            {'value': choice[0], 'label': choice[1]}
            for choice in ExpenseFrequency.choices
        ]
        return Response(frequencies)


# =============================================================================
# EXPENSE SUB-CATEGORY VIEWS
# =============================================================================

class ExpenseSubCategoryListCreateView(FarmScopedMixin, generics.ListCreateAPIView):
    """
    GET /api/expenses/sub-categories/
    POST /api/expenses/sub-categories/
    
    List and create custom expense sub-categories.
    """
    queryset = ExpenseSubCategory.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ExpenseSubCategoryCreateSerializer
        return ExpenseSubCategorySerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter active only by default
        is_active = self.request.query_params.get('is_active', 'true')
        if is_active.lower() == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('category', 'name')
    
    def perform_create(self, serializer):
        serializer.save(farm=self.get_farm())


class ExpenseSubCategoryDetailView(FarmScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/expenses/sub-categories/{id}/
    
    Manage individual sub-categories.
    """
    queryset = ExpenseSubCategory.objects.all()
    serializer_class = ExpenseSubCategorySerializer


# =============================================================================
# EXPENSE VIEWS
# =============================================================================

class ExpenseListCreateView(FarmScopedMixin, generics.ListCreateAPIView):
    """
    GET /api/expenses/
    POST /api/expenses/
    
    List farmer's expenses or create a new expense.
    """
    queryset = Expense.objects.all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ExpenseCreateSerializer
        return ExpenseListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by flock
        flock_id = self.request.query_params.get('flock')
        if flock_id:
            queryset = queryset.filter(flock_id=flock_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(expense_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(expense_date__lte=end_date)
        
        # Filter by recurring status
        is_recurring = self.request.query_params.get('is_recurring')
        if is_recurring is not None:
            queryset = queryset.filter(is_recurring=is_recurring.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(payee_name__icontains=search) |
                Q(receipt_number__icontains=search)
            )
        
        # Sorting
        sort_by = self.request.query_params.get('sort_by', '-expense_date')
        valid_sorts = [
            'expense_date', '-expense_date',
            'total_amount', '-total_amount',
            'category', '-category',
            'created_at', '-created_at'
        ]
        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by)
        
        return queryset.select_related('flock', 'subcategory')
    
    def perform_create(self, serializer):
        serializer.save(
            farm=self.get_farm(),
            created_by=self.request.user
        )
    
    def create(self, request, *args, **kwargs):
        """Override to return detail serializer after creation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return detailed response with calculated fields
        detail_serializer = ExpenseDetailSerializer(serializer.instance)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class ExpenseDetailView(FarmScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/expenses/{id}/
    
    Manage individual expense records.
    """
    queryset = Expense.objects.all()
    serializer_class = ExpenseDetailSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class BulkExpenseCreateView(FarmScopedMixin, APIView):
    """
    POST /api/expenses/bulk/
    
    Create multiple expenses at once.
    """
    
    def post(self, request):
        serializer = BulkExpenseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        farm = self.get_farm()
        created = []
        errors = []
        
        for i, expense_data in enumerate(serializer.validated_data['expenses']):
            try:
                expense = Expense.objects.create(
                    farm=farm,
                    created_by=request.user,
                    **expense_data
                )
                created.append(ExpenseListSerializer(expense).data)
            except Exception as e:
                errors.append({'index': i, 'error': str(e)})
        
        return Response({
            'created': len(created),
            'errors': len(errors),
            'expenses': created,
            'error_details': errors
        }, status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST)


# =============================================================================
# LABOR RECORD VIEWS
# =============================================================================

class LaborRecordListCreateView(FarmScopedMixin, generics.ListCreateAPIView):
    """
    GET /api/expenses/labor/
    POST /api/expenses/labor/
    
    Manage labor/wage records.
    """
    queryset = LaborRecord.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LaborRecordCreateSerializer
        return LaborRecordListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by flock
        flock_id = self.request.query_params.get('flock')
        if flock_id:
            queryset = queryset.filter(flock_id=flock_id)
        
        # Filter by worker type
        worker_type = self.request.query_params.get('worker_type')
        if worker_type:
            queryset = queryset.filter(worker_type=worker_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(work_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(work_date__lte=end_date)
        
        return queryset.select_related('flock', 'expense').order_by('-work_date')
    
    def perform_create(self, serializer):
        serializer.save(
            farm=self.get_farm(),
            created_by=self.request.user
        )


class LaborRecordDetailView(FarmScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/expenses/labor/{id}/
    """
    queryset = LaborRecord.objects.all()
    serializer_class = LaborRecordDetailSerializer


class LaborRecordPayView(FarmScopedMixin, APIView):
    """
    POST /api/expenses/labor/{id}/pay/
    
    Mark a labor record as paid and optionally create expense entry.
    """
    
    def post(self, request, pk):
        try:
            record = LaborRecord.objects.get(pk=pk, farm=self.get_farm())
        except LaborRecord.DoesNotExist:
            return Response(
                {'error': 'Labor record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check payment status via the associated expense
        if record.expense and record.expense.payment_status == 'paid':
            return Response(
                {'error': 'Labor record is already marked as paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_date = request.data.get('payment_date', timezone.now().date())
        
        # Mark the associated expense as paid
        if record.expense:
            record.expense.payment_status = 'paid'
            record.expense.save(update_fields=['payment_status'])
        
        return Response({
            'success': True,
            'message': 'Labor record marked as paid',
            'record_id': str(record.id)
        })


class BulkLaborRecordCreateView(FarmScopedMixin, APIView):
    """
    POST /api/expenses/labor/bulk/
    
    Create multiple labor records at once (useful for weekly payroll).
    """
    
    def post(self, request):
        serializer = BulkLaborRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        farm = self.get_farm()
        created = []
        errors = []
        
        for i, record_data in enumerate(serializer.validated_data['records']):
            try:
                record = LaborRecord.objects.create(
                    farm=farm,
                    created_by=request.user,
                    **record_data
                )
                created.append(LaborRecordListSerializer(record).data)
            except Exception as e:
                errors.append({'index': i, 'error': str(e)})
        
        return Response({
            'created': len(created),
            'errors': len(errors),
            'records': created,
            'error_details': errors
        }, status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST)


# =============================================================================
# UTILITY RECORD VIEWS
# =============================================================================

class UtilityRecordListCreateView(FarmScopedMixin, generics.ListCreateAPIView):
    """
    GET /api/expenses/utilities/
    POST /api/expenses/utilities/
    
    Manage utility (electricity, water, etc.) records.
    """
    queryset = UtilityRecord.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UtilityRecordCreateSerializer
        return UtilityRecordListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by utility type
        utility_type = self.request.query_params.get('utility_type')
        if utility_type:
            queryset = queryset.filter(utility_type=utility_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(billing_period_start__gte=start_date)
        if end_date:
            queryset = queryset.filter(billing_period_end__lte=end_date)
        
        return queryset.select_related('expense').order_by('-billing_period_start')
    
    def perform_create(self, serializer):
        serializer.save(
            farm=self.get_farm(),
            created_by=self.request.user
        )


class UtilityRecordDetailView(FarmScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/expenses/utilities/{id}/
    """
    queryset = UtilityRecord.objects.all()
    serializer_class = UtilityRecordDetailSerializer


class UtilityRecordPayView(FarmScopedMixin, APIView):
    """
    POST /api/expenses/utilities/{id}/pay/
    
    Mark a utility record as paid and optionally create expense entry.
    """
    
    def post(self, request, pk):
        try:
            record = UtilityRecord.objects.get(pk=pk, farm=self.get_farm())
        except UtilityRecord.DoesNotExist:
            return Response(
                {'error': 'Utility record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check payment status via the associated expense
        if record.expense and record.expense.payment_status == 'paid':
            return Response(
                {'error': 'Utility record is already marked as paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_date = request.data.get('payment_date', timezone.now().date())
        
        # Mark the associated expense as paid
        if record.expense:
            record.expense.payment_status = 'paid'
            record.expense.save(update_fields=['payment_status'])
        
        return Response({
            'success': True,
            'message': 'Utility record marked as paid',
            'record_id': str(record.id)
        })


# =============================================================================
# MORTALITY LOSS RECORD VIEWS
# =============================================================================

class MortalityLossRecordListCreateView(FarmScopedMixin, generics.ListCreateAPIView):
    """
    GET /api/expenses/mortality-losses/
    POST /api/expenses/mortality-losses/
    
    Manage mortality loss (economic impact) records.
    """
    queryset = MortalityLossRecord.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MortalityLossRecordCreateSerializer
        return MortalityLossRecordListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by flock
        flock_id = self.request.query_params.get('flock')
        if flock_id:
            queryset = queryset.filter(flock_id=flock_id)
        
        # Filter by cause
        cause = self.request.query_params.get('cause')
        if cause:
            queryset = queryset.filter(cause_of_death=cause)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(mortality_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(mortality_date__lte=end_date)
        
        return queryset.select_related('flock', 'expense').order_by('-mortality_date')
    
    def perform_create(self, serializer):
        # Check if auto_calculate is requested
        auto_calculate = self.request.data.get('auto_calculate', False)
        serializer.save(
            farm=self.get_farm(),
            created_by=self.request.user,
            auto_calculate=auto_calculate
        )


class MortalityLossRecordDetailView(FarmScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/expenses/mortality-losses/{id}/
    """
    queryset = MortalityLossRecord.objects.all()
    serializer_class = MortalityLossRecordDetailSerializer


class MortalityLossPreviewView(FarmScopedMixin, APIView):
    """
    POST /api/expenses/mortality-loss/preview/
    
    Preview mortality loss calculation BEFORE creating a record.
    Uses the BirdInvestmentCalculator to show farmers what feed and
    medication costs have been invested in birds before recording the loss.
    
    This endpoint is for the frontend to show:
    1. Auto-calculated feed cost invested (from actual FeedConsumption data)
    2. Auto-calculated medication/vaccination cost invested
    3. Total economic loss breakdown
    
    Request body:
    {
        "flock_id": "uuid",
        "mortality_date": "2026-01-19",
        "birds_lost": 12,
        "acquisition_cost_per_bird": "5.00",  // Optional - defaults to flock's purchase price
        "potential_revenue_per_bird": "25.00"  // Optional - for broilers/spent layers
    }
    
    Response includes:
    - feed_cost_invested: Calculated feed cost for dead birds
    - other_costs_invested: Medication + vaccination costs
    - total_loss_value: Total economic loss
    - breakdown: Detailed per-bird costs and data sources
    """
    
    def post(self, request):
        from .services import BirdInvestmentCalculator
        from flock_management.models import Flock
        from datetime import datetime
        
        farm = self.get_farm()
        
        # Validate required fields
        flock_id = request.data.get('flock_id')
        mortality_date_str = request.data.get('mortality_date')
        birds_lost = request.data.get('birds_lost')
        
        if not all([flock_id, mortality_date_str, birds_lost]):
            return Response(
                {'error': 'Missing required fields: flock_id, mortality_date, birds_lost'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate flock belongs to farm
        try:
            flock = Flock.objects.get(id=flock_id, farm=farm)
        except Flock.DoesNotExist:
            return Response(
                {'error': 'Flock not found or does not belong to your farm'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Parse date
        try:
            if isinstance(mortality_date_str, str):
                mortality_date = datetime.strptime(mortality_date_str, '%Y-%m-%d').date()
            else:
                mortality_date = mortality_date_str
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse birds_lost
        try:
            birds_lost = int(birds_lost)
            if birds_lost < 1:
                raise ValueError("Must be positive")
        except (ValueError, TypeError):
            return Response(
                {'error': 'birds_lost must be a positive integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate bird count
        if birds_lost > flock.current_count:
            return Response(
                {'error': f'Cannot record loss of {birds_lost} birds. Flock only has {flock.current_count} birds.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse optional fields
        acquisition_cost = request.data.get('acquisition_cost_per_bird')
        if acquisition_cost:
            try:
                acquisition_cost = Decimal(str(acquisition_cost))
            except:
                acquisition_cost = None
        
        potential_revenue = request.data.get('potential_revenue_per_bird')
        if potential_revenue:
            try:
                potential_revenue = Decimal(str(potential_revenue))
            except:
                potential_revenue = None
        
        # Calculate using the service
        try:
            calculator = BirdInvestmentCalculator(flock)
            loss_data = calculator.calculate_mortality_loss(
                mortality_date=mortality_date,
                birds_lost=birds_lost,
                acquisition_cost_per_bird=acquisition_cost,
                potential_revenue_per_bird=potential_revenue
            )
            
            return Response({
                'success': True,
                'flock': {
                    'id': str(flock.id),
                    'flock_number': flock.flock_number,
                    'breed': flock.breed,
                    'current_count': flock.current_count,
                    'arrival_date': flock.arrival_date.isoformat(),
                    'purchase_price_per_bird': str(flock.purchase_price_per_bird),
                },
                'mortality_details': {
                    'mortality_date': mortality_date.isoformat(),
                    'birds_lost': birds_lost,
                    'age_at_death_weeks': str(loss_data['age_at_death_weeks']),
                },
                'calculated_costs': {
                    'acquisition_cost_per_bird': str(loss_data['acquisition_cost_per_bird']),
                    'feed_cost_invested': str(loss_data['feed_cost_invested']),
                    'other_costs_invested': str(loss_data['other_costs_invested']),
                    'potential_revenue_lost': str(loss_data['potential_revenue_lost']),
                    'total_loss_value': str(loss_data['total_loss_value']),
                    'additional_investment_value': str(loss_data['additional_investment_value']),
                },
                'breakdown': {
                    'acquisition_loss': str(loss_data['breakdown']['acquisition_loss']),
                    'feed_cost_per_bird': str(loss_data['breakdown']['feed_cost_per_bird']),
                    'medication_cost_per_bird': str(loss_data['breakdown']['medication_cost_per_bird']),
                    'vaccination_cost_per_bird': str(loss_data['breakdown']['vaccination_cost_per_bird']),
                    'average_bird_count_in_period': loss_data['breakdown']['average_bird_count_in_period'],
                    'days_investment_period': loss_data['breakdown']['days_investment_period'],
                },
                'data_sources': loss_data['data_sources'],
                'message': (
                    'These values are auto-calculated from your tracked data. '
                    'You can use these values when creating the mortality loss record, '
                    'or override them with manual values if needed.'
                ),
            })
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(f"Error calculating mortality loss: {e}")
            return Response(
                {'error': f'Calculation error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FlockInvestmentSummaryView(FarmScopedMixin, APIView):
    """
    GET /api/expenses/flock/{flock_id}/investment/
    
    Get a complete investment summary for a flock - how much has been
    invested in feed, medication, and vaccination.
    
    Useful for farmers to understand the total value of their flock
    and for accurate decision-making about culling, selling, etc.
    """
    
    def get(self, request, flock_id):
        from .services import get_flock_investment_summary
        from flock_management.models import Flock
        
        farm = self.get_farm()
        
        try:
            flock = Flock.objects.get(id=flock_id, farm=farm)
        except Flock.DoesNotExist:
            return Response(
                {'error': 'Flock not found or does not belong to your farm'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Parse optional date
        as_of_date = request.query_params.get('as_of_date')
        if as_of_date:
            from datetime import datetime
            try:
                as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            summary = get_flock_investment_summary(flock, as_of_date)
            return Response(summary)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(f"Error calculating flock investment: {e}")
            return Response(
                {'error': f'Calculation error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# RECURRING EXPENSE TEMPLATE VIEWS
# =============================================================================

class RecurringExpenseTemplateListCreateView(FarmScopedMixin, generics.ListCreateAPIView):
    """
    GET /api/expenses/recurring/
    POST /api/expenses/recurring/
    
    Manage recurring expense templates.
    """
    queryset = RecurringExpenseTemplate.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RecurringExpenseTemplateCreateSerializer
        return RecurringExpenseTemplateListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by frequency
        frequency = self.request.query_params.get('frequency')
        if frequency:
            queryset = queryset.filter(frequency=frequency)
        
        return queryset.select_related('flock').order_by('-is_active', 'name')
    
    def perform_create(self, serializer):
        serializer.save(farm=self.get_farm())


class RecurringExpenseTemplateDetailView(FarmScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/expenses/recurring/{id}/
    """
    queryset = RecurringExpenseTemplate.objects.all()
    serializer_class = RecurringExpenseTemplateDetailSerializer


class GenerateRecurringExpenseView(FarmScopedMixin, APIView):
    """
    POST /api/expenses/recurring/{id}/generate/
    
    Manually generate expense from a recurring template.
    """
    
    def post(self, request, pk):
        try:
            template = RecurringExpenseTemplate.objects.get(pk=pk, farm=self.get_farm())
        except RecurringExpenseTemplate.DoesNotExist:
            return Response(
                {'error': 'Template not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        expense_date = request.data.get('expense_date', timezone.now().date())
        
        # Create expense from template
        expense = Expense.objects.create(
            farm=template.farm,
            flock=template.flock,
            expense_date=expense_date,
            category=template.category,
            description=f"{template.name} - {expense_date}",
            amount=template.amount,
            vendor=template.vendor,
            is_recurring=True,
            recurrence_template=template,
            created_by=request.user
        )
        
        # Update template
        template.last_generated = timezone.now()
        template.total_generated = (template.total_generated or 0) + 1
        template.calculate_next_date()
        template.save()
        
        return Response({
            'success': True,
            'expense': ExpenseDetailSerializer(expense).data
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# EXPENSE SUMMARY VIEWS
# =============================================================================

class ExpenseSummaryListView(FarmScopedMixin, generics.ListAPIView):
    """
    GET /api/expenses/summary/
    
    Get expense summaries.
    """
    queryset = ExpenseSummary.objects.all()
    serializer_class = ExpenseSummarySerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by period type
        period_type = self.request.query_params.get('period_type')
        if period_type:
            queryset = queryset.filter(period_type=period_type)
        
        # Filter by flock
        flock_id = self.request.query_params.get('flock')
        if flock_id:
            queryset = queryset.filter(flock_id=flock_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(summary_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(summary_date__lte=end_date)
        
        return queryset.order_by('-summary_date')


# =============================================================================
# DASHBOARD & ANALYTICS VIEWS
# =============================================================================

class ExpenseDashboardView(FarmScopedMixin, APIView):
    """
    GET /api/expenses/dashboard/
    
    Get expense dashboard overview.
    """
    
    def get(self, request):
        farm = self.get_farm()
        today = timezone.now().date()
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_end = month_start - timedelta(days=1)
        
        # Base queryset
        expenses = Expense.objects.filter(farm=farm)
        
        # Total expenses
        total_expenses = expenses.aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0'))
        )['total']
        
        # This month's expenses
        this_month = expenses.filter(
            expense_date__gte=month_start,
            expense_date__lte=today
        ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
        
        # Last month's expenses
        last_month = expenses.filter(
            expense_date__gte=last_month_start,
            expense_date__lte=last_month_end
        ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
        
        # Month over month change
        if last_month > 0:
            mom_change = ((this_month - last_month) / last_month) * 100
        else:
            mom_change = Decimal('100') if this_month > 0 else Decimal('0')
        
        # Breakdown by category
        breakdown = expenses.values('category').annotate(
            amount=Coalesce(Sum('total_amount'), Decimal('0')),
            count=Count('id')
        ).order_by('-amount')
        
        breakdown_data = []
        for item in breakdown:
            category_total = item['amount']
            percentage = (category_total / total_expenses * 100) if total_expenses > 0 else Decimal('0')
            breakdown_data.append({
                'category': item['category'],
                'category_display': dict(ExpenseCategory.choices).get(item['category'], item['category']),
                'amount': category_total,
                'percentage': percentage,
                'count': item['count']
            })
        
        # Top category
        top_category = breakdown_data[0] if breakdown_data else None
        
        # Pending payments (labor and utilities with unpaid status)
        # Note: Payment tracking is handled via the Expense model's payment_status field
        pending_labor = Expense.objects.filter(
            farm=farm, 
            category=ExpenseCategory.LABOR,
            payment_status='unpaid'
        ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
        
        pending_utilities = Expense.objects.filter(
            farm=farm,
            category=ExpenseCategory.UTILITIES,
            payment_status='unpaid'
        ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
        
        # Recurring expenses
        recurring_templates = RecurringExpenseTemplate.objects.filter(
            farm=farm, is_active=True
        )
        recurring_count = recurring_templates.count()
        
        # Estimate monthly recurring total
        monthly_recurring = Decimal('0')
        for template in recurring_templates:
            if template.frequency == 'DAILY':
                monthly_recurring += template.unit_cost * 30
            elif template.frequency == 'WEEKLY':
                monthly_recurring += template.unit_cost * 4
            elif template.frequency == 'BIWEEKLY':
                monthly_recurring += template.unit_cost * 2
            elif template.frequency == 'MONTHLY':
                monthly_recurring += template.unit_cost
            elif template.frequency == 'QUARTERLY':
                monthly_recurring += template.unit_cost / 3
            elif template.frequency == 'YEARLY':
                monthly_recurring += template.unit_cost / 12
        
        return Response({
            'total_expenses': total_expenses,
            'expenses_this_month': this_month,
            'expenses_last_month': last_month,
            'month_over_month_change': round(mom_change, 2),
            'top_category': top_category['category_display'] if top_category else None,
            'top_category_amount': top_category['amount'] if top_category else Decimal('0'),
            'breakdown': breakdown_data,
            'pending_labor_payments': pending_labor,
            'pending_utility_payments': pending_utilities,
            'recurring_count': recurring_count,
            'recurring_monthly_total': monthly_recurring,
        })


class ExpenseAnalyticsView(FarmScopedMixin, APIView):
    """
    GET /api/expenses/analytics/
    
    Get expense analytics for charts and reports.
    """
    
    def get(self, request):
        farm = self.get_farm()
        period = request.query_params.get('period', 'MONTH')
        
        # Determine date range
        today = timezone.now().date()
        if period == 'WEEK':
            start_date = today - timedelta(days=7)
        elif period == 'MONTH':
            start_date = today - timedelta(days=30)
        elif period == 'QUARTER':
            start_date = today - timedelta(days=90)
        elif period == 'YEAR':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)
        
        expenses = Expense.objects.filter(
            farm=farm,
            expense_date__gte=start_date
        )
        
        # Summary stats
        total = expenses.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
        count = expenses.count()
        avg = expenses.aggregate(avg=Coalesce(Avg('total_amount'), Decimal('0')))['avg']
        
        # By category
        by_category = expenses.values('category').annotate(
            amount=Coalesce(Sum('total_amount'), Decimal('0')),
            count=Count('id')
        ).order_by('-amount')
        
        # Daily trend
        daily_trend = expenses.annotate(
            date=F('expense_date')
        ).values('date').annotate(
            amount=Coalesce(Sum('total_amount'), Decimal('0')),
            count=Count('id')
        ).order_by('date')
        
        # Monthly trend (for longer periods)
        monthly_trend = expenses.annotate(
            month=TruncMonth('expense_date')
        ).values('month').annotate(
            amount=Coalesce(Sum('total_amount'), Decimal('0')),
            count=Count('id')
        ).order_by('month')
        
        # Top payees
        top_payees = expenses.exclude(
            payee_name__isnull=True
        ).exclude(
            payee_name=''
        ).values('payee_name').annotate(
            amount=Coalesce(Sum('total_amount'), Decimal('0')),
            count=Count('id')
        ).order_by('-amount')[:10]
        
        return Response({
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': today.isoformat(),
            'summary': {
                'total': total,
                'count': count,
                'average': avg,
            },
            'by_category': [
                {
                    'category': item['category'],
                    'category_display': dict(ExpenseCategory.choices).get(item['category'], item['category']),
                    'amount': item['amount'],
                    'count': item['count'],
                    'percentage': (item['amount'] / total * 100) if total > 0 else 0
                }
                for item in by_category
            ],
            'daily_trend': [
                {
                    'date': item['date'].isoformat(),
                    'amount': item['amount'],
                    'count': item['count']
                }
                for item in daily_trend
            ],
            'monthly_trend': [
                {
                    'month': item['month'].isoformat(),
                    'amount': item['amount'],
                    'count': item['count']
                }
                for item in monthly_trend
            ],
            'top_payees': [
                {
                    'payee_name': item['payee_name'],
                    'amount': item['amount'],
                    'count': item['count']
                }
                for item in top_payees
            ]
        })


class FlockCostBreakdownView(FarmScopedMixin, APIView):
    """
    GET /api/expenses/flock/{flock_id}/costs/
    
    Get complete cost breakdown for a specific flock.
    """
    
    def get(self, request, flock_id):
        try:
            flock = Flock.objects.get(pk=flock_id, farm=self.get_farm())
        except Flock.DoesNotExist:
            return Response(
                {'error': 'Flock not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the cost breakdown from the flock
        cost_breakdown = flock.get_cost_breakdown()
        
        # Calculate per-bird and per-day costs
        current_count = flock.current_count or 1
        days_active = (timezone.now().date() - flock.arrival_date).days if flock.arrival_date else 1
        days_active = max(days_active, 1)
        
        total_investment = cost_breakdown['total_investment']
        cost_per_bird = total_investment / Decimal(str(current_count))
        cost_per_bird_per_day = total_investment / Decimal(str(current_count * days_active))
        
        return Response({
            'flock_id': str(flock.id),
            'flock_number': flock.flock_number,
            'flock_type': flock.flock_type,
            
            'acquisition_cost': flock.total_acquisition_cost,
            'feed_cost': flock.total_feed_cost,
            'medication_cost': flock.total_medication_cost,
            'vaccination_cost': flock.total_vaccination_cost,
            'labor_cost': flock.total_labor_cost,
            'utilities_cost': flock.total_utilities_cost,
            'bedding_cost': flock.total_bedding_cost,
            'transport_cost': flock.total_transport_cost,
            'maintenance_cost': flock.total_maintenance_cost,
            'overhead_cost': flock.total_overhead_cost,
            'miscellaneous_cost': flock.total_miscellaneous_cost,
            'mortality_loss': flock.total_mortality_loss_value,
            
            'total_operational_cost': cost_breakdown['total_operational'],
            'total_investment': total_investment,
            
            'cost_per_bird': cost_per_bird,
            'cost_per_bird_per_day': cost_per_bird_per_day,
            
            'breakdown': cost_breakdown['breakdown'],
            
            # Additional context
            'current_bird_count': flock.current_count,
            'initial_bird_count': flock.initial_count,
            'days_active': days_active,
            'arrival_date': flock.arrival_date.isoformat() if flock.arrival_date else None,
        })
