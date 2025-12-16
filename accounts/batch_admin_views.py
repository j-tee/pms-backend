"""
Batch Management Admin API Views

Provides comprehensive administrative endpoints for managing batchs,
including CRUD operations, statistics, participants management, and program actions.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta

from farms.batch_enrollment_models import (
    Batch,
    BatchEnrollmentApplication,
    BatchEnrollmentReview
)
from farms.application_models import FarmApplication
from accounts.policies.batch_policy import BatchPolicy
from accounts.models import User


class AdminBatchListView(APIView):
    """
    GET /api/admin/programs/
    
    List all batchs with filtering, search, and pagination.
    
    Query Parameters:
    - page (int): Page number (default: 1)
    - page_size (int): Items per page (default: 20, max: 100)
    - is_active (boolean): Filter by active status
    - search (string): Search by name or code
    - sort_by (string): Sort field (e.g., '-created_at', 'application_deadline')
    - status (string): Filter by status (active, full, inactive)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check permission
        if not BatchPolicy.has_admin_access(request.user):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Start with all programs (including archived for admins)
        queryset = Batch.objects.filter(archived=False)
        
        # Apply filters
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_active=is_active_bool)
        
        batch_status = request.query_params.get('status')
        if batch_status:
            queryset = queryset.filter(status=batch_status)
        
        # Search
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(batch_name__icontains=search) |
                Q(batch_code__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Sorting
        sort_by = request.query_params.get('sort_by', '-created_at')
        allowed_sorts = [
            'created_at', '-created_at',
            'batch_name', '-batch_name',
            'application_deadline', '-application_deadline',
            'start_date', '-start_date',
            'total_slots', '-total_slots'
        ]
        if sort_by in allowed_sorts:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-is_active', '-created_at')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # Build response data with computed statistics
        results = []
        for program in page_obj.object_list:
            # Calculate real-time statistics from applications
            applications = BatchEnrollmentApplication.objects.filter(batch=program)
            total_applications = applications.count()
            approved_applications = applications.filter(status='approved').count()
            rejected_applications = applications.filter(status='rejected').count()
            pending_applications = applications.filter(
                status__in=['submitted', 'eligibility_check', 'constituency_review', 
                           'regional_review', 'national_review']
            ).count()
            
            # Calculate slots from farm applications if this is for new farmers
            farm_apps = FarmApplication.objects.filter(
                yea_program_batch=program.batch_code if hasattr(program, 'batch_code') else None
            )
            farm_apps_approved = farm_apps.filter(status='approved').count()
            
            # Total slots filled (both enrollment and farm applications)
            slots_filled = approved_applications + farm_apps_approved
            slots_available = max(0, program.total_slots - slots_filled)
            
            # Calculate regional allocation with actual fills
            regional_data = []
            if program.regional_allocation:
                for region_info in program.regional_allocation:
                    region = region_info.get('region')
                    allocated = region_info.get('allocated_slots', 0)
                    
                    # Count approved applications in this region
                    region_filled = applications.filter(
                        status='approved',
                        farm__primary_region=region
                    ).count()
                    
                    # Count pending in region
                    region_pending = applications.filter(
                        status__in=['submitted', 'eligibility_check', 'constituency_review',
                                   'regional_review', 'national_review'],
                        farm__primary_region=region
                    ).count()
                    
                    regional_data.append({
                        'region': region,
                        'allocated_slots': allocated,
                        'filled_slots': region_filled,
                        'available_slots': max(0, allocated - region_filled),
                        'pending_slots': region_pending
                    })
            
            # Calculate approval rate
            approval_rate = 0
            if total_applications > 0:
                approval_rate = round((approved_applications / total_applications) * 100, 1)
            
            # Calculate average review time
            avg_review_time = 0
            completed_apps = applications.filter(
                final_decision_at__isnull=False,
                submitted_at__isnull=False
            )
            if completed_apps.exists():
                review_times = []
                for app in completed_apps:
                    delta = app.final_decision_at - app.submitted_at
                    review_times.append(delta.days)
                if review_times:
                    avg_review_time = round(sum(review_times) / len(review_times))
            
            # Days remaining
            days_remaining = program.days_until_deadline
            
            # Application window status
            is_open = program.application_window_is_open and program.is_accepting_applications
            
            results.append({
                'id': str(program.id),
                'batch_code': program.batch_code,
                'batch_name': program.batch_name,
                'description': program.description,
                'eligibility_criteria': program.eligibility_criteria,
                'support_package': program.support_package_details,
                'support_package_value_ghs': float(program.support_package_value_ghs),
                'document_requirements': program.document_requirements,
                'batch_info': program.batch_info,
                'slot_allocation': {
                    'total_slots': program.total_slots,
                    'slots_filled': slots_filled,
                    'slots_available': slots_available,
                    'slots_pending_approval': pending_applications,
                    'slots_reserved': 0
                },
                'application_window': {
                    'opens_at': program.start_date.isoformat() if program.start_date else None,
                    'closes_at': program.application_deadline.isoformat() if program.application_deadline else None,
                    'is_open': is_open,
                    'days_remaining': days_remaining
                },
                'regional_allocation': regional_data,
                'statistics': {
                    'total_applications': total_applications,
                    'approved_applications': approved_applications,
                    'rejected_applications': rejected_applications,
                    'pending_review': pending_applications,
                    'approval_rate': approval_rate,
                    'average_review_time_days': avg_review_time
                },
                'is_active': program.is_active,
                'is_accepting_applications': program.is_accepting_applications,
                'created_at': program.created_at.isoformat(),
                'updated_at': program.updated_at.isoformat(),
                'created_by': {
                    'id': str(program.created_by.id) if program.created_by else None,
                    'username': program.created_by.username if program.created_by else None,
                    'full_name': program.created_by.get_full_name() if program.created_by else None
                } if program.created_by else None
            })
        
        return Response({
            'results': results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': paginator.count,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
    
    def post(self, request):
        """
        POST /api/admin/programs/
        Create a new batch/cohort.
        Accepts both old field names (batch_name, batch_code) and new field names (batch_name, batch_code)
        """
        # Check permission
        if not BatchPolicy.can_create_batch(request.user):
            return Response(
                {'error': 'Permission denied. Only Super Admin and National Admin can create programs.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Support both old and new field names for backward compatibility
        batch_name = request.data.get('batch_name') or request.data.get('batch_name')
        batch_code = request.data.get('batch_code') or request.data.get('batch_code')
        
        # Validate required fields
        required_fields = {
            'batch_name': batch_name,
            'total_slots': request.data.get('total_slots'),
            'start_date': request.data.get('start_date'),
            'end_date': request.data.get('end_date')
        }
        
        for field_name, field_value in required_fields.items():
            if not field_value:
                return Response(
                    {'error': f'Missing required field: {field_name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Auto-generate batch_code if not provided
        if not batch_code:
            year = timezone.now().year
            count = Batch.objects.filter(created_at__year=year).count() + 1
            batch_code = f"YEA-{year}-BATCH-{count:02d}"
        
        # Check uniqueness
        if Batch.objects.filter(batch_code=batch_code).exists():
            return Response(
                {'error': f'Batch code {batch_code} already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if Batch.objects.filter(batch_name=batch_name).exists():
            return Response(
                {'error': f'Batch name already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate and parse dates
        from datetime import datetime
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        # Parse start_date
        if start_date:
            if isinstance(start_date, str):
                # Handle both datetime and date formats
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00').split('T')[0]).date()
            start_date_obj = start_date
        else:
            start_date_obj = None
            
        # Parse end_date
        if end_date:
            if isinstance(end_date, str):
                # Handle both datetime and date formats
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00').split('T')[0]).date()
            end_date_obj = end_date
        else:
            end_date_obj = None
            
        # Validate date logic
        if start_date_obj and end_date_obj:
            if start_date_obj >= end_date_obj:
                return Response(
                    {'error': 'start_date must be before end_date'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate total_slots
        total_slots = int(request.data.get('total_slots', 0))
        if total_slots < 1:
            return Response(
                {'error': 'total_slots must be at least 1'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate regional allocation if provided
        regional_allocation = request.data.get('regional_allocation', [])
        if regional_allocation:
            regional_sum = sum(r.get('allocated_slots', 0) for r in regional_allocation)
            if regional_sum > total_slots:
                return Response(
                    {'error': f'Regional allocation sum ({regional_sum}) exceeds total_slots ({total_slots})'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create batch
        try:
            # Extract application window dates
            app_window = request.data.get('application_window', {})
            application_deadline = app_window.get('closes_at') or request.data.get('application_deadline')
            early_deadline = app_window.get('early_application_deadline')
            
            # Parse application_deadline if provided
            if application_deadline and isinstance(application_deadline, str):
                application_deadline = datetime.fromisoformat(application_deadline.replace('Z', '+00:00').split('T')[0]).date()
                
            # Parse early_deadline if provided
            if early_deadline and isinstance(early_deadline, str):
                early_deadline = datetime.fromisoformat(early_deadline.replace('Z', '+00:00').split('T')[0]).date()
            
            # Extract funding source
            funding = request.data.get('funding_source', {})
            
            # Extract approval workflow
            workflow = request.data.get('approval_workflow', {})
            
            # Extract slot allocation
            slot_alloc = request.data.get('slot_allocation', {})
            
            program = Batch.objects.create(
                batch_code=batch_code,
                batch_name=batch_name,
                target_region=request.data.get('target_region'),
                target_constituencies=request.data.get('target_constituencies', []),
                description=request.data.get('description', ''),
                long_description=request.data.get('long_description', ''),
                implementing_agency=request.data.get('implementing_agency', 'Youth Employment Agency'),
                start_date=start_date_obj,
                end_date=end_date_obj,
                application_deadline=application_deadline,
                early_application_deadline=early_deadline,
                eligibility_criteria=request.data.get('eligibility_criteria', {}),
                support_package_details=request.data.get('support_package', {}),
                support_package_value_ghs=request.data.get('support_package_value_ghs', 0),
                beneficiary_contribution_ghs=request.data.get('beneficiary_contribution_ghs', 0),
                document_requirements=request.data.get('document_requirements', []),
                batch_info=request.data.get('batch_info', {}),
                total_slots=total_slots,
                allow_overbooking=slot_alloc.get('allow_overbooking', False),
                overbooking_percentage=slot_alloc.get('overbooking_percentage', 0),
                regional_allocation=regional_allocation,
                requires_constituency_approval=workflow.get('requires_constituency_approval', True),
                requires_regional_approval=workflow.get('requires_regional_approval', True),
                requires_national_approval=workflow.get('requires_national_approval', True),
                approval_sla_days=workflow.get('approval_sla_days', 30),
                funding_source=funding.get('source', ''),
                budget_code=funding.get('budget_code', ''),
                total_budget_ghs=funding.get('total_budget_ghs', 0),
                is_active=request.data.get('is_active', False),
                is_accepting_applications_override=request.data.get('is_accepting_applications', False),
                is_published=request.data.get('is_published', False),
                status='active' if request.data.get('is_active', False) else 'inactive',
                created_by=request.user
            )
            
            return Response({
                'id': str(program.id),
                'batch_code': program.batch_code,
                'batch_name': program.batch_name,
                'message': 'Batch created successfully',
                'created_at': program.created_at.isoformat()
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create batch: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminBatchDetailUpdateDeleteView(APIView):
    """
    Combined view for batch detail operations
    
    GET /api/admin/batches/{batch_id}/     - Get batch details
    PUT /api/admin/batches/{batch_id}/     - Full update
    PATCH /api/admin/batches/{batch_id}/   - Partial update
    DELETE /api/admin/batches/{batch_id}/  - Archive batch
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, batch_id):
        """Get detailed batch information - delegates to AdminBatchDetailView"""
        view = AdminBatchDetailView()
        view.request = request
        return view.get(request, batch_id)
    
    def put(self, request, batch_id):
        """Full update - delegates to AdminBatchUpdateView"""
        view = AdminBatchUpdateView()
        view.request = request
        return view.put(request, batch_id)
    
    def patch(self, request, batch_id):
        """Partial update - delegates to AdminBatchUpdateView"""
        view = AdminBatchUpdateView()
        view.request = request
        return view.patch(request, batch_id)
    
    def delete(self, request, batch_id):
        """Archive batch - delegates to AdminBatchDeleteView"""
        view = AdminBatchDeleteView()
        view.request = request
        return view.delete(request, batch_id)


class AdminBatchDetailView(APIView):
    """
    GET /api/admin/programs/{batch_id}/
    
    Get detailed information about a specific program including participants and statistics.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, batch_id):
        # Check permission
        if not BatchPolicy.has_admin_access(request.user):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            program = Batch.objects.get(id=batch_id, archived=False)
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate statistics
        applications = BatchEnrollmentApplication.objects.filter(batch=program)
        total_applications = applications.count()
        approved_applications = applications.filter(status='approved').count()
        rejected_applications = applications.filter(status='rejected').count()
        pending_applications = applications.filter(
            status__in=['submitted', 'eligibility_check', 'constituency_review',
                       'regional_review', 'national_review']
        ).count()
        enrolled_count = applications.filter(enrollment_completed=True).count()
        
        # Farm applications (for new farmers)
        farm_apps = FarmApplication.objects.filter(
            yea_program_batch=program.batch_code
        )
        farm_apps_approved = farm_apps.filter(status='approved').count()
        
        # Total slots filled
        slots_filled = approved_applications + farm_apps_approved
        slots_available = max(0, program.total_slots - slots_filled)
        
        # Calculate approval rate
        approval_rate = 0
        if total_applications > 0:
            approval_rate = round((approved_applications / total_applications) * 100, 1)
        
        # Calculate average review time
        avg_review_time = 0
        completed_apps = applications.filter(
            final_decision_at__isnull=False,
            submitted_at__isnull=False
        )
        if completed_apps.exists():
            review_times = []
            for app in completed_apps:
                delta = app.final_decision_at - app.submitted_at
                review_times.append(delta.days)
            if review_times:
                avg_review_time = round(sum(review_times) / len(review_times))
        
        # Regional allocation with real data
        regional_data = []
        if program.regional_allocation:
            for region_info in program.regional_allocation:
                region = region_info.get('region')
                allocated = region_info.get('allocated_slots', 0)
                
                region_filled = applications.filter(
                    status='approved',
                    farm__primary_region=region
                ).count()
                
                region_pending = applications.filter(
                    status__in=['submitted', 'eligibility_check', 'constituency_review',
                               'regional_review', 'national_review'],
                    farm__primary_region=region
                ).count()
                
                regional_data.append({
                    'region': region,
                    'allocated_slots': allocated,
                    'filled_slots': region_filled,
                    'available_slots': max(0, allocated - region_filled),
                    'pending_slots': region_pending
                })
        
        # Get participants (recent approved applications)
        participants = []
        approved_apps = applications.filter(status='approved').order_by('-final_decision_at')[:50]
        for app in approved_apps:
            participants.append({
                'id': str(app.id),
                'applicant_name': app.applicant.get_full_name() if app.applicant else 'N/A',
                'application_number': app.application_number,
                'region': app.farm.primary_region if app.farm else 'N/A',
                'constituency': app.farm.primary_constituency if app.farm else 'N/A',
                'status': app.status,
                'approved_at': app.final_decision_at.isoformat() if app.final_decision_at else None
            })
        
        # Budget utilization
        spent_ghs = slots_filled * float(program.support_package_value_ghs)
        remaining_ghs = float(program.total_budget_ghs) - spent_ghs
        
        # Response data
        data = {
            'id': str(program.id),
            'batch_code': program.batch_code,
            'batch_name': program.batch_name,
            'description': program.description,
            'long_description': program.long_description,
            'eligibility_criteria': {
                'min_age': program.eligible_farmer_age_min,
                'max_age': program.eligible_farmer_age_max,
                'citizenship': program.eligibility_criteria.get('citizenship', 'Ghanaian') if program.eligibility_criteria else 'Ghanaian',
                'restrictions': program.eligibility_criteria.get('restrictions', []) if program.eligibility_criteria else [],
                **(program.eligibility_criteria if program.eligibility_criteria else {})
            },
            'support_package': program.support_package_details,
            'support_package_value_ghs': float(program.support_package_value_ghs),
            'beneficiary_contribution_ghs': float(program.beneficiary_contribution_ghs),
            'document_requirements': program.document_requirements,
            'batch_info': program.batch_info,
            'slot_allocation': {
                'total_slots': program.total_slots,
                'slots_filled': slots_filled,
                'slots_available': slots_available,
                'slots_pending_approval': pending_applications,
                'slots_reserved': 0,
                'allow_overbooking': program.allow_overbooking,
                'overbooking_percentage': float(program.overbooking_percentage)
            },
            'regional_allocation': regional_data,
            'application_window': {
                'opens_at': program.start_date.isoformat() if program.start_date else None,
                'closes_at': program.application_deadline.isoformat() if program.application_deadline else None,
                'early_application_deadline': program.early_application_deadline.isoformat() if program.early_application_deadline else None,
                'is_open': program.application_window_is_open and program.is_accepting_applications,
                'days_remaining': program.days_until_deadline,
                'can_extend': True  # Always allow admins to extend
            },
            'approval_workflow': {
                'requires_constituency_approval': program.requires_constituency_approval,
                'requires_regional_approval': program.requires_regional_approval,
                'requires_national_approval': program.requires_national_approval,
                'auto_approve_if_slots_available': False,
                'approval_sla_days': program.approval_sla_days
            },
            'funding_source': {
                'source': program.funding_source,
                'budget_code': program.budget_code,
                'total_budget_ghs': float(program.total_budget_ghs),
                'spent_ghs': spent_ghs,
                'remaining_ghs': remaining_ghs
            },
            'participants': participants,
            'statistics': {
                'total_applications': total_applications,
                'approved_applications': approved_applications,
                'rejected_applications': rejected_applications,
                'pending_review': pending_applications,
                'approval_rate': approval_rate,
                'average_review_time_days': avg_review_time,
                'completion_rate': 0,  # Would need tracking
                'active_beneficiaries': enrolled_count,
                'graduated_beneficiaries': 0,  # Would need tracking
                'dropout_rate': 0  # Would need tracking
            },
            'is_active': program.is_active,
            'is_accepting_applications': program.is_accepting_applications,
            'is_published': program.is_published,
            'archived': program.archived,
            'created_at': program.created_at.isoformat(),
            'updated_at': program.updated_at.isoformat(),
            'created_by': {
                'id': str(program.created_by.id) if program.created_by else None,
                'username': program.created_by.username if program.created_by else None,
                'full_name': program.created_by.get_full_name() if program.created_by else None
            } if program.created_by else None,
            'last_modified_by': {
                'id': str(program.last_modified_by.id) if program.last_modified_by else None,
                'username': program.last_modified_by.username if program.last_modified_by else None,
                'full_name': program.last_modified_by.get_full_name() if program.last_modified_by else None
            } if program.last_modified_by else None
        }
        
        return Response(data)


class AdminBatchCreateView(APIView):
    """
    POST /api/admin/programs/
    
    Create a new batch.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check permission
        if not BatchPolicy.can_create_batch(request.user):
            return Response(
                {'error': 'Permission denied. Only Super Admin and National Admin can create programs.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate required fields
        required_fields = ['batch_name', 'total_slots', 'start_date', 'end_date']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {'error': f'Missing required field: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Auto-generate batch_code if not provided
        batch_code = request.data.get('batch_code')
        if not batch_code:
            year = timezone.now().year
            count = Batch.objects.filter(created_at__year=year).count() + 1
            batch_code = f"YEA-PROGRAM-{year}-{count:02d}"
        
        # Check uniqueness
        if Batch.objects.filter(batch_code=batch_code).exists():
            return Response(
                {'error': f'Batch code {batch_code} already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if Batch.objects.filter(batch_name=request.data['batch_name']).exists():
            return Response(
                {'error': f'Batch name already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate and parse dates
        from datetime import datetime
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        # Parse start_date
        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00').split('T')[0]).date()
            start_date_obj = start_date
        else:
            start_date_obj = None
            
        # Parse end_date
        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00').split('T')[0]).date()
            end_date_obj = end_date
        else:
            end_date_obj = None
            
        # Validate date logic
        if start_date_obj and end_date_obj:
            if start_date_obj >= end_date_obj:
                return Response(
                    {'error': 'start_date must be before end_date'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate age range if provided
        eligibility = request.data.get('eligibility_criteria', {})
        min_age = eligibility.get('min_age', 18)
        max_age = eligibility.get('max_age', 65)
        if min_age >= max_age:
            return Response(
                {'error': 'min_age must be less than max_age'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate total_slots
        total_slots = int(request.data.get('total_slots', 0))
        if total_slots < 1:
            return Response(
                {'error': 'total_slots must be at least 1'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate regional allocation if provided
        regional_allocation = request.data.get('regional_allocation', [])
        if regional_allocation:
            regional_sum = sum(r.get('allocated_slots', 0) for r in regional_allocation)
            if regional_sum > total_slots:
                return Response(
                    {'error': f'Regional allocation sum ({regional_sum}) exceeds total_slots ({total_slots})'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create program
        try:
            # Extract application window dates
            app_window = request.data.get('application_window', {})
            application_deadline = app_window.get('closes_at') or request.data.get('application_deadline')
            early_deadline = app_window.get('early_application_deadline')
            
            # Parse application_deadline if provided
            if application_deadline and isinstance(application_deadline, str):
                application_deadline = datetime.fromisoformat(application_deadline.replace('Z', '+00:00').split('T')[0]).date()
                
            # Parse early_deadline if provided
            if early_deadline and isinstance(early_deadline, str):
                early_deadline = datetime.fromisoformat(early_deadline.replace('Z', '+00:00').split('T')[0]).date()
            
            # Extract funding source
            funding = request.data.get('funding_source', {})
            
            # Extract approval workflow
            workflow = request.data.get('approval_workflow', {})
            
            # Extract slot allocation
            slot_alloc = request.data.get('slot_allocation', {})
            
            program = Batch.objects.create(
                batch_code=batch_code,
                batch_name=request.data['batch_name'],
                description=request.data.get('description', ''),
                long_description=request.data.get('long_description', ''),
                implementing_agency=request.data.get('implementing_agency', 'Youth Employment Agency'),
                start_date=start_date_obj,
                end_date=end_date_obj,
                application_deadline=application_deadline,
                early_application_deadline=early_deadline,
                eligible_farmer_age_min=min_age,
                eligible_farmer_age_max=max_age,
                eligibility_criteria=request.data.get('eligibility_criteria', {}),
                support_package_details=request.data.get('support_package', {}),
                support_package_value_ghs=request.data.get('support_package_value_ghs', 0),
                beneficiary_contribution_ghs=request.data.get('beneficiary_contribution_ghs', 0),
                document_requirements=request.data.get('document_requirements', []),
                batch_info=request.data.get('batch_info', {}),
                total_slots=total_slots,
                allow_overbooking=slot_alloc.get('allow_overbooking', False),
                overbooking_percentage=slot_alloc.get('overbooking_percentage', 0),
                regional_allocation=regional_allocation,
                requires_constituency_approval=workflow.get('requires_constituency_approval', True),
                requires_regional_approval=workflow.get('requires_regional_approval', True),
                requires_national_approval=workflow.get('requires_national_approval', True),
                approval_sla_days=workflow.get('approval_sla_days', 30),
                funding_source=funding.get('source', ''),
                budget_code=funding.get('budget_code', ''),
                total_budget_ghs=funding.get('total_budget_ghs', 0),
                is_active=request.data.get('is_active', False),
                is_accepting_applications_override=request.data.get('is_accepting_applications', False),
                is_published=request.data.get('is_published', False),
                status='active' if request.data.get('is_active', False) else 'inactive',
                created_by=request.user
            )
            
            return Response({
                'id': str(program.id),
                'batch_code': program.batch_code,
                'batch_name': program.batch_name,
                'message': 'Program created successfully',
                'created_at': program.created_at.isoformat()
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create program: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminBatchUpdateView(APIView):
    """
    PUT /api/admin/programs/{batch_id}/
    PATCH /api/admin/programs/{batch_id}/
    
    Update an existing program.
    """
    permission_classes = [IsAuthenticated]
    
    def put(self, request, batch_id):
        return self._update_program(request, batch_id, partial=False)
    
    def patch(self, request, batch_id):
        return self._update_program(request, batch_id, partial=True)
    
    def _update_program(self, request, batch_id, partial=True):
        # Check permission
        try:
            program = Batch.objects.get(id=batch_id, archived=False)
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not BatchPolicy.can_edit_batch(request.user, program):
            return Response(
                {'error': 'Permission denied. Only Super Admin and National Admin can edit programs.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        updated_fields = []
        
        # Update basic fields
        if 'batch_name' in request.data:
            # Check uniqueness (exclude current program)
            if Batch.objects.filter(
                batch_name=request.data['batch_name']
            ).exclude(id=batch_id).exists():
                return Response(
                    {'error': 'Batch name already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            program.batch_name = request.data['batch_name']
            updated_fields.append('batch_name')
        
        if 'description' in request.data:
            program.description = request.data['description']
            updated_fields.append('description')
        
        if 'long_description' in request.data:
            program.long_description = request.data['long_description']
            updated_fields.append('long_description')
        
        # Update dates (parse datetime strings to dates)
        from datetime import datetime
        if 'start_date' in request.data:
            start_date = request.data['start_date']
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00').split('T')[0]).date()
            program.start_date = start_date
            updated_fields.append('start_date')
        
        if 'end_date' in request.data:
            end_date = request.data['end_date']
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00').split('T')[0]).date()
            program.end_date = end_date
            updated_fields.append('end_date')
        
        # Update application window
        if 'application_window' in request.data:
            app_window = request.data['application_window']
            if 'closes_at' in app_window:
                closes_at = app_window['closes_at']
                if isinstance(closes_at, str):
                    closes_at = datetime.fromisoformat(closes_at.replace('Z', '+00:00').split('T')[0]).date()
                program.application_deadline = closes_at
                updated_fields.append('application_deadline')
            if 'early_application_deadline' in app_window:
                early_deadline = app_window.get('early_application_deadline')
                if early_deadline and isinstance(early_deadline, str):
                    early_deadline = datetime.fromisoformat(early_deadline.replace('Z', '+00:00').split('T')[0]).date()
                program.early_application_deadline = early_deadline
                updated_fields.append('early_application_deadline')
        
        # Update slots (with validation)
        if 'slot_allocation' in request.data or 'total_slots' in request.data:
            slot_data = request.data.get('slot_allocation', {})
            new_total_slots = slot_data.get('total_slots') or request.data.get('total_slots')
            
            if new_total_slots:
                new_total_slots = int(new_total_slots)
                # Validate: can't reduce below filled slots
                if new_total_slots < program.slots_filled:
                    return Response(
                        {'error': f'Cannot reduce total_slots to {new_total_slots}. Already {program.slots_filled} slots filled.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                program.total_slots = new_total_slots
                updated_fields.append('total_slots')
            
            if 'allow_overbooking' in slot_data:
                program.allow_overbooking = slot_data['allow_overbooking']
                updated_fields.append('allow_overbooking')
            
            if 'overbooking_percentage' in slot_data:
                program.overbooking_percentage = slot_data['overbooking_percentage']
                updated_fields.append('overbooking_percentage')
        
        # Update eligibility
        if 'eligibility_criteria' in request.data:
            # Merge with existing data
            program.eligibility_criteria = {
                **program.eligibility_criteria,
                **request.data['eligibility_criteria']
            }
            updated_fields.append('eligibility_criteria')
        
        # Update support package
        if 'support_package' in request.data:
            program.support_package_details = {
                **program.support_package_details,
                **request.data['support_package']
            }
            updated_fields.append('support_package')
        
        if 'support_package_value_ghs' in request.data:
            program.support_package_value_ghs = request.data['support_package_value_ghs']
            updated_fields.append('support_package_value_ghs')
        
        # Update document requirements
        if 'document_requirements' in request.data:
            program.document_requirements = request.data['document_requirements']
            updated_fields.append('document_requirements')
        
        # Update batch info
        if 'batch_info' in request.data:
            program.batch_info = {
                **program.batch_info,
                **request.data['batch_info']
            }
            updated_fields.append('batch_info')
        
        # Update regional allocation
        if 'regional_allocation' in request.data:
            program.regional_allocation = request.data['regional_allocation']
            updated_fields.append('regional_allocation')
        
        # Update approval workflow
        if 'approval_workflow' in request.data:
            workflow = request.data['approval_workflow']
            if 'requires_constituency_approval' in workflow:
                program.requires_constituency_approval = workflow['requires_constituency_approval']
                updated_fields.append('requires_constituency_approval')
            if 'requires_regional_approval' in workflow:
                program.requires_regional_approval = workflow['requires_regional_approval']
                updated_fields.append('requires_regional_approval')
            if 'requires_national_approval' in workflow:
                program.requires_national_approval = workflow['requires_national_approval']
                updated_fields.append('requires_national_approval')
            if 'approval_sla_days' in workflow:
                program.approval_sla_days = workflow['approval_sla_days']
                updated_fields.append('approval_sla_days')
        
        # Update funding
        if 'funding_source' in request.data:
            funding = request.data['funding_source']
            if 'source' in funding:
                program.funding_source = funding['source']
                updated_fields.append('funding_source')
            if 'budget_code' in funding:
                program.budget_code = funding['budget_code']
                updated_fields.append('budget_code')
            if 'total_budget_ghs' in funding:
                program.total_budget_ghs = funding['total_budget_ghs']
                updated_fields.append('total_budget_ghs')
        
        # Update status flags
        if 'is_active' in request.data:
            program.is_active = request.data['is_active']
            if program.is_active:
                program.status = 'active'
            updated_fields.append('is_active')
        
        if 'is_accepting_applications' in request.data:
            program.is_accepting_applications_override = request.data['is_accepting_applications']
            updated_fields.append('is_accepting_applications')
        
        if 'is_published' in request.data:
            program.is_published = request.data['is_published']
            updated_fields.append('is_published')
        
        # Update last_modified_by
        program.last_modified_by = request.user
        
        # Save changes
        program.save()
        
        return Response({
            'id': str(program.id),
            'batch_code': program.batch_code,
            'message': 'Program updated successfully',
            'updated_fields': updated_fields,
            'updated_at': program.updated_at.isoformat()
        })


class AdminBatchDeleteView(APIView):
    """
    DELETE /api/admin/programs/{batch_id}/
    
    Archive (soft delete) a program.
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, batch_id):
        try:
            program = Batch.objects.get(id=batch_id, archived=False)
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not BatchPolicy.can_delete_batch(request.user, program):
            return Response(
                {'error': 'Permission denied. Only Super Admin can delete programs.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if program has approved applications
        approved_count = BatchEnrollmentApplication.objects.filter(
            batch=program,
            status='approved'
        ).count()
        
        if approved_count > 0:
            return Response({
                'error': 'Cannot delete program',
                'reason': f'Program has {approved_count} approved applications',
                'suggestion': 'Set is_active=false to hide program instead',
                'applications_count': approved_count,
                'active_beneficiaries': BatchEnrollmentApplication.objects.filter(
                    batch=program,
                    enrollment_completed=True
                ).count()
            }, status=status.HTTP_409_CONFLICT)
        
        # Check if currently accepting applications
        if program.is_accepting_applications:
            return Response({
                'error': 'Cannot delete program',
                'reason': 'Program is currently accepting applications',
                'suggestion': 'Set is_accepting_applications=false first'
            }, status=status.HTTP_409_CONFLICT)
        
        # Soft delete (archive)
        program.archived = True
        program.is_active = False
        program.last_modified_by = request.user
        program.save()
        
        applications_count = BatchEnrollmentApplication.objects.filter(batch=program).count()
        
        return Response({
            'message': 'Program archived successfully',
            'batch_id': str(program.id),
            'applications_affected': applications_count,
            'archived_at': timezone.now().isoformat()
        })
