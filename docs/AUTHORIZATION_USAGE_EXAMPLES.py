"""
Authorization System Usage Examples

This file demonstrates how to use the authorization system in various scenarios.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from accounts.decorators import (
    authorize,
    require_role,
    require_permission,
    require_verification,
    require_marketplace_subscription,
    AuthorizationContext
)
from accounts.policies import (
    FarmPolicy,
    ApplicationPolicy,
    SalesPolicy,
    ProductionPolicy
)
from farms.models import Farm, FarmApplication
from sales_revenue.models import EggSale, Customer
from flock_management.models import Flock, DailyProduction


# ============================================================================
# EXAMPLE 1: Simple Permission Check
# ============================================================================

@api_view(['GET'])
@require_permission('view_executive_dashboard')
def executive_dashboard(request):
    """
    Executive dashboard - requires specific permission.
    """
    # User has permission, proceed with logic
    statistics = {
        'total_farms': Farm.objects.count(),
        'active_applications': FarmApplication.objects.filter(
            status='submitted'
        ).count(),
        # ... more statistics
    }
    
    return Response(statistics)


# ============================================================================
# EXAMPLE 2: Role-Based Access
# ============================================================================

@api_view(['POST'])
@require_role('NATIONAL_ADMIN', 'SUPER_ADMIN')
def create_government_program(request):
    """
    Create government program - requires admin role.
    """
    from farms.models import GovernmentProgram
    
    # Only admins can reach here
    program = GovernmentProgram.objects.create(
        program_name=request.data.get('program_name'),
        program_code=request.data.get('program_code'),
        # ... other fields
    )
    
    return Response({'id': str(program.id)}, status=status.HTTP_201_CREATED)


# ============================================================================
# EXAMPLE 3: Resource-Level Authorization (Policy-Based)
# ============================================================================

@api_view(['GET'])
@authorize(
    action='view',
    resource_getter=lambda request, pk, **kwargs: Farm.objects.get(pk=pk)
)
def get_farm(request, pk):
    """
    Get farm details - checks if user can view specific farm.
    """
    farm = Farm.objects.get(pk=pk)
    
    # If we reach here, user is authorized to view this farm
    data = {
        'id': str(farm.id),
        'farm_name': farm.farm_name,
        'farm_status': farm.farm_status,
        'owner': {
            'name': f"{farm.owner.first_name} {farm.owner.last_name}",
            'phone': str(farm.owner.phone)
        },
        # ... more fields
    }
    
    return Response(data)


@api_view(['PUT', 'PATCH'])
@authorize(
    action='edit',
    resource_getter=lambda request, pk, **kwargs: Farm.objects.get(pk=pk)
)
def update_farm(request, pk):
    """
    Update farm - checks if user can edit specific farm.
    """
    farm = Farm.objects.get(pk=pk)
    user = request.user
    
    # Get editable fields based on user's role
    editable_fields = FarmPolicy.editable_fields(user, farm)
    
    if editable_fields == '__all__':
        # User can edit all fields (super admin)
        allowed_data = request.data
    else:
        # Filter data to only include editable fields
        allowed_data = {
            key: value for key, value in request.data.items()
            if key in editable_fields
        }
    
    # Update farm
    for field, value in allowed_data.items():
        setattr(farm, field, value)
    
    farm.save()
    
    return Response({'message': 'Farm updated successfully'})


# ============================================================================
# EXAMPLE 4: Scoped Queries (List View)
# ============================================================================

@api_view(['GET'])
def list_farms(request):
    """
    List farms - automatically scoped to user's access level.
    """
    user = request.user
    
    # Get scoped queryset based on user's permissions
    farms = FarmPolicy.scope(user)
    
    # Apply additional filters from query params
    status_filter = request.query_params.get('status')
    if status_filter:
        farms = farms.filter(farm_status=status_filter)
    
    constituency_filter = request.query_params.get('constituency')
    if constituency_filter:
        farms = farms.filter(primary_constituency=constituency_filter)
    
    # Paginate and serialize
    page = request.query_params.get('page', 1)
    page_size = 20
    start = (int(page) - 1) * page_size
    end = start + page_size
    
    farm_list = []
    for farm in farms[start:end]:
        farm_list.append({
            'id': str(farm.id),
            'farm_name': farm.farm_name,
            'farm_status': farm.farm_status,
            'primary_constituency': farm.primary_constituency,
        })
    
    return Response({
        'count': farms.count(),
        'results': farm_list
    })


# ============================================================================
# EXAMPLE 5: Application Review Queue
# ============================================================================

@api_view(['GET'])
@require_role('CONSTITUENCY_OFFICIAL', 'REGIONAL_COORDINATOR', 'NATIONAL_ADMIN')
def get_application_queue(request):
    """
    Get applications in user's review queue.
    """
    user = request.user
    
    # Get applications user can review
    queue_applications = ApplicationPolicy.queue_scope(user)
    
    # Filter by status
    queue_applications = queue_applications.filter(
        status__in=['submitted', 'constituency_review', 'regional_review', 'national_review']
    )
    
    # Order by priority
    queue_applications = queue_applications.order_by('-priority_score', 'submitted_at')
    
    applications = []
    for app in queue_applications[:50]:  # Limit to 50
        applications.append({
            'application_number': app.application_number,
            'applicant_name': f"{app.first_name} {app.last_name}",
            'constituency': app.primary_constituency,
            'current_review_level': app.current_review_level,
            'submitted_at': app.submitted_at,
            'priority_score': app.priority_score,
        })
    
    return Response({
        'count': queue_applications.count(),
        'applications': applications
    })


@api_view(['POST'])
@authorize(
    action='approve',
    resource_getter=lambda request, application_id, **kwargs: 
        FarmApplication.objects.get(application_number=application_id)
)
def approve_application(request, application_id):
    """
    Approve application - checks if user can approve at current tier.
    """
    application = FarmApplication.objects.get(application_number=application_id)
    user = request.user
    
    # Perform approval
    current_level = application.current_review_level
    
    if current_level == 'constituency':
        application.constituency_approved_at = timezone.now()
        application.constituency_approved_by = user
        application.current_review_level = 'regional'
        application.status = 'regional_review'
    
    elif current_level == 'regional':
        application.regional_approved_at = timezone.now()
        application.regional_approved_by = user
        application.current_review_level = 'national'
        application.status = 'national_review'
    
    elif current_level == 'national':
        application.final_approved_at = timezone.now()
        application.final_approved_by = user
        application.status = 'approved'
        # Trigger account creation
        # ...
    
    application.save()
    
    return Response({
        'message': 'Application approved',
        'new_status': application.status
    })


# ============================================================================
# EXAMPLE 6: Marketplace Sales (Requires Subscription)
# ============================================================================

@api_view(['POST'])
@require_verification(check_phone=True)
@require_marketplace_subscription
def create_egg_sale(request):
    """
    Create egg sale - requires marketplace subscription.
    """
    user = request.user
    farm = user.farm
    
    # User has active marketplace subscription if we reach here
    customer_id = request.data.get('customer_id')
    customer = Customer.objects.get(id=customer_id, farm=farm)
    
    sale = EggSale.objects.create(
        farm=farm,
        customer=customer,
        quantity=request.data.get('quantity'),
        unit=request.data.get('unit', 'crate'),
        price_per_unit=request.data.get('price_per_unit'),
        # ... other fields
    )
    
    return Response({
        'id': str(sale.id),
        'message': 'Sale created successfully'
    }, status=status.HTTP_201_CREATED)


# ============================================================================
# EXAMPLE 7: Manual Authorization Check (Context Manager)
# ============================================================================

@api_view(['DELETE'])
def delete_flock(request, flock_id):
    """
    Delete flock - manual authorization check.
    """
    user = request.user
    flock = get_object_or_404(Flock, id=flock_id)
    
    # Manual authorization check
    with AuthorizationContext(user, 'delete', flock) as authorized:
        if not authorized:
            return Response(
                {
                    'error': 'You do not have permission to delete this flock',
                    'code': 'DELETE_NOT_AUTHORIZED'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # User is authorized, proceed with deletion
        flock.delete()
        
        return Response({
            'message': 'Flock deleted successfully'
        })


# ============================================================================
# EXAMPLE 8: Conditional Access (Veterinary Investigation)
# ============================================================================

@api_view(['POST'])
@require_role('VETERINARY_OFFICER')
def investigate_mortality(request, mortality_id):
    """
    Investigate mortality - vet must be in jurisdiction.
    """
    from flock_management.models import MortalityRecord
    
    user = request.user
    mortality = get_object_or_404(MortalityRecord, id=mortality_id)
    
    # Check if vet can investigate (jurisdiction check)
    if not ProductionPolicy.can_investigate_mortality(user, mortality):
        return Response(
            {
                'error': 'This farm is not in your jurisdiction',
                'code': 'JURISDICTION_ERROR'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Update mortality record with vet findings
    mortality.vet_inspected = True
    mortality.vet_inspector = user
    mortality.vet_diagnosis = request.data.get('diagnosis')
    mortality.lab_test_results = request.data.get('lab_results')
    mortality.save()
    
    return Response({
        'message': 'Investigation completed',
        'mortality_id': str(mortality.id)
    })


# ============================================================================
# EXAMPLE 9: Field-Level Authorization
# ============================================================================

@api_view(['GET'])
@authorize(
    action='view',
    resource_getter=lambda request, pk, **kwargs: Farm.objects.get(pk=pk)
)
def get_farm_detailed(request, pk):
    """
    Get farm with conditional field visibility.
    """
    user = request.user
    farm = Farm.objects.get(pk=pk)
    
    # Base data visible to all authorized users
    data = {
        'id': str(farm.id),
        'farm_name': farm.farm_name,
        'farm_status': farm.farm_status,
        'primary_constituency': farm.primary_constituency,
    }
    
    # Financial data only for authorized users
    if FarmPolicy.can_view_financial_data(user, farm):
        data['financial'] = {
            'initial_investment': float(farm.initial_investment_amount),
            'monthly_budget': float(farm.monthly_operating_budget),
            'has_debt': farm.has_outstanding_debt,
            'debt_amount': float(farm.debt_amount) if farm.debt_amount else None,
        }
    
    # Production data
    if FarmPolicy.can_view(user, farm):
        data['production'] = {
            'bird_capacity': farm.total_bird_capacity,
            'current_count': farm.current_bird_count,
            'production_type': farm.primary_production_type,
        }
    
    return Response(data)


# ============================================================================
# EXAMPLE 10: Fraud Investigation (Auditor Access)
# ============================================================================

@api_view(['GET'])
@require_role('AUDITOR')
def get_fraud_investigation_data(request, farm_id):
    """
    Get fraud investigation data - auditor must be assigned to case.
    """
    user = request.user
    farm = get_object_or_404(Farm, id=farm_id)
    
    # Check if auditor has active investigation
    from accounts.policies.base_policy import BasePolicy
    if not BasePolicy.is_active_investigation(user, farm):
        return Response(
            {
                'error': 'No active investigation assigned for this farm',
                'code': 'NO_INVESTIGATION'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Gather comprehensive data for investigation
    from sales_revenue.models import EggSale, BirdSale, FarmerPayout
    from flock_management.models import DailyProduction
    
    # Get all production records
    production_records = DailyProduction.objects.filter(farm=farm)
    total_eggs_produced = sum(p.eggs_collected for p in production_records)
    
    # Get all sales
    egg_sales = EggSale.objects.filter(farm=farm)
    total_eggs_sold = sum(
        s.quantity * 30 if s.unit == 'crate' else s.quantity
        for s in egg_sales
    )
    
    # Calculate discrepancy
    discrepancy_percent = (
        (total_eggs_produced - total_eggs_sold) / total_eggs_produced * 100
        if total_eggs_produced > 0 else 0
    )
    
    data = {
        'farm': {
            'id': str(farm.id),
            'name': farm.farm_name,
            'owner': f"{farm.owner.first_name} {farm.owner.last_name}",
        },
        'production': {
            'total_eggs_produced': total_eggs_produced,
            'production_days': production_records.count(),
        },
        'sales': {
            'total_eggs_sold': total_eggs_sold,
            'total_sales': egg_sales.count(),
        },
        'analysis': {
            'discrepancy_eggs': total_eggs_produced - total_eggs_sold,
            'discrepancy_percent': round(discrepancy_percent, 2),
            'risk_level': 'HIGH' if discrepancy_percent > 50 else 'MEDIUM' if discrepancy_percent > 30 else 'LOW',
        },
        'payouts': list(
            FarmerPayout.objects.filter(farm=farm).values(
                'amount', 'status', 'settlement_date'
            )
        ),
    }
    
    return Response(data)


# ============================================================================
# EXAMPLE 11: Custom Policy Check
# ============================================================================

def can_create_sale_custom_check(user, request, **kwargs):
    """Custom authorization logic."""
    # Must be farmer
    if not user.has_role('FARMER'):
        return False
    
    # Must have farm
    if not hasattr(user, 'farm'):
        return False
    
    farm = user.farm
    
    # Farm must be active
    if farm.farm_status != 'Active':
        return False
    
    # Must have marketplace enabled
    if not farm.marketplace_enabled:
        return False
    
    # Must have active subscription
    if hasattr(farm, 'subscription'):
        if farm.subscription.status not in ['trial', 'active']:
            return False
    
    # Must have verified phone
    if not user.phone_verified:
        return False
    
    return True


@api_view(['POST'])
@authorize(policy_check=can_create_sale_custom_check)
def create_sale_with_custom_check(request):
    """
    Create sale with custom authorization logic.
    """
    # All custom checks passed
    # ... create sale logic
    return Response({'message': 'Sale created'}, status=status.HTTP_201_CREATED)


# ============================================================================
# EXAMPLE 12: ViewSet with Authorization
# ============================================================================

from rest_framework import viewsets
from rest_framework.decorators import action

class FarmViewSet(viewsets.ModelViewSet):
    """
    Farm CRUD with built-in authorization.
    """
    
    def get_queryset(self):
        """Return scoped queryset based on user's access."""
        user = self.request.user
        return FarmPolicy.scope(user)
    
    def retrieve(self, request, pk=None):
        """Get single farm - checks view permission."""
        farm = self.get_object()
        
        # Check if user can view
        if not FarmPolicy.can_view(request.user, farm):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # ... serialize and return
        return Response({'farm_name': farm.farm_name})
    
    def update(self, request, pk=None):
        """Update farm - checks edit permission."""
        farm = self.get_object()
        
        # Check if user can edit
        if not FarmPolicy.can_edit(request.user, farm):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get editable fields
        editable_fields = FarmPolicy.editable_fields(request.user, farm)
        
        # Filter data
        if editable_fields != '__all__':
            data = {k: v for k, v in request.data.items() if k in editable_fields}
        else:
            data = request.data
        
        # Update
        for field, value in data.items():
            setattr(farm, field, value)
        farm.save()
        
        return Response({'message': 'Updated'})
    
    @action(detail=True, methods=['post'])
    def assign_extension_officer(self, request, pk=None):
        """Assign extension officer to farm."""
        farm = self.get_object()
        
        # Check permission
        if not FarmPolicy.can_assign_extension_officer(request.user, farm):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        officer_id = request.data.get('officer_id')
        from accounts.models import User
        officer = User.objects.get(id=officer_id, role='EXTENSION_OFFICER')
        
        farm.assigned_extension_officer = officer
        farm.save()
        
        return Response({'message': 'Officer assigned'})
