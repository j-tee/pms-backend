"""
Batch Management Additional Views

Program action endpoints, participants management, and statistics.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta, datetime

from farms.batch_enrollment_models import (
    Batch,
    BatchEnrollmentApplication,
    BatchEnrollmentReview
)
from farms.application_models import FarmApplication
from accounts.policies.batch_policy import BatchPolicy


class AdminBatchToggleActiveView(APIView):
    """
    POST /api/admin/programs/{batch_id}/toggle-active/
    
    Activate or deactivate a program.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, batch_id):
        try:
            program = Batch.objects.get(id=batch_id, archived=False)
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not BatchPolicy.can_edit_batch(request.user, program):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        is_active = request.data.get('is_active', not program.is_active)
        reason = request.data.get('reason', '')
        
        program.is_active = is_active
        program.status = 'active' if is_active else 'inactive'
        program.last_modified_by = request.user
        program.save()
        
        # TODO: Send notifications to relevant users if needed
        
        return Response({
            'id': str(program.id),
            'batch_code': program.batch_code,
            'is_active': program.is_active,
            'status': program.status,
            'reason': reason,
            'message': f'Program {"activated" if is_active else "deactivated"} successfully',
            'updated_at': program.updated_at.isoformat()
        })


class AdminBatchCloseApplicationsView(APIView):
    """
    POST /api/admin/programs/{batch_id}/close-applications/
    
    Close applications early for a program.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, batch_id):
        try:
            program = Batch.objects.get(id=batch_id, archived=False)
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not BatchPolicy.can_edit_batch(request.user, program):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', 'Applications closed by admin')
        send_notification = request.data.get('send_notification', True)
        
        program.is_accepting_applications_override = False
        program.application_deadline = timezone.now().date()
        program.last_modified_by = request.user
        program.save()
        
        # TODO: Send notifications if send_notification=True
        
        return Response({
            'id': str(program.id),
            'batch_code': program.batch_code,
            'is_accepting_applications': False,
            'closed_at': timezone.now().isoformat(),
            'reason': reason,
            'message': 'Applications closed successfully'
        })


class AdminBatchExtendDeadlineView(APIView):
    """
    POST /api/admin/programs/{batch_id}/extend-deadline/
    
    Extend application deadline for a program.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, batch_id):
        try:
            program = Batch.objects.get(id=batch_id, archived=False)
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not BatchPolicy.can_edit_batch(request.user, program):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_deadline = request.data.get('new_deadline')
        if not new_deadline:
            return Response(
                {'error': 'new_deadline is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse deadline
        try:
            if isinstance(new_deadline, str):
                new_deadline_date = datetime.fromisoformat(new_deadline.replace('Z', '+00:00')).date()
            else:
                new_deadline_date = new_deadline
        except Exception as e:
            return Response(
                {'error': f'Invalid date format: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate: new deadline must be in future
        if new_deadline_date <= timezone.now().date():
            return Response(
                {'error': 'New deadline must be in the future'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate: new deadline should be before end_date
        if new_deadline_date > program.end_date:
            return Response(
                {'error': 'New deadline cannot be after program end date'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'Deadline extended by admin')
        notify_applicants = request.data.get('notify_applicants', True)
        
        old_deadline = program.application_deadline
        program.application_deadline = new_deadline_date
        program.last_modified_by = request.user
        program.save()
        
        # TODO: Send notifications if notify_applicants=True
        
        return Response({
            'id': str(program.id),
            'batch_code': program.batch_code,
            'old_deadline': old_deadline.isoformat() if old_deadline else None,
            'new_deadline': new_deadline_date.isoformat(),
            'days_added': (new_deadline_date - old_deadline).days if old_deadline else None,
            'reason': reason,
            'message': 'Deadline extended successfully',
            'updated_at': program.updated_at.isoformat()
        })


class AdminBatchParticipantsView(APIView):
    """
    GET /api/admin/programs/{batch_id}/participants/
    
    List all participants (applicants) for a program.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, batch_id):
        try:
            program = Batch.objects.get(id=batch_id, archived=False)
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not BatchPolicy.can_view_batch_participants(request.user, program):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all applications for this program
        applications = BatchEnrollmentApplication.objects.filter(batch=program)
        
        # Apply filters
        app_status = request.query_params.get('status')
        if app_status:
            applications = applications.filter(status=app_status)
        
        region = request.query_params.get('region')
        if region:
            applications = applications.filter(farm__primary_region=region)
        
        constituency = request.query_params.get('constituency')
        if constituency:
            applications = applications.filter(farm__primary_constituency=constituency)
        
        # Order by
        applications = applications.order_by('-submitted_at')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        
        paginator = Paginator(applications, page_size)
        page_obj = paginator.get_page(page)
        
        # Build response
        participants = []
        for app in page_obj.object_list:
            participants.append({
                'application_id': str(app.id),
                'application_number': app.application_number,
                'applicant_name': app.applicant.get_full_name() if app.applicant else 'N/A',
                'phone': app.applicant.phone if app.applicant else 'N/A',
                'email': app.applicant.email if app.applicant else 'N/A',
                'region': app.farm.primary_region if app.farm else 'N/A',
                'constituency': app.farm.primary_constituency if app.farm else 'N/A',
                'farm_name': app.farm.farm_name if app.farm else 'N/A',
                'status': app.status,
                'application_date': app.submitted_at.isoformat() if app.submitted_at else None,
                'approved_date': app.final_decision_at.isoformat() if app.final_decision_at and app.status == 'approved' else None,
                'beneficiary_status': 'active' if app.enrollment_completed else 'pending'
            })
        
        return Response({
            'program': {
                'id': str(program.id),
                'batch_code': program.batch_code,
                'batch_name': program.batch_name
            },
            'participants': participants,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': paginator.count,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })


class AdminBatchStatisticsView(APIView):
    """
    GET /api/admin/programs/{batch_id}/statistics/
    
    Get detailed statistics for a program.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, batch_id):
        try:
            program = Batch.objects.get(id=batch_id, archived=False)
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not BatchPolicy.has_admin_access(request.user):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get query parameters
        period = request.query_params.get('period', 'all_time')
        breakdown_by = request.query_params.get('breakdown_by', 'region')
        
        # Calculate date range
        end_date = timezone.now()
        if period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        else:  # all_time
            start_date = program.created_at
        
        # Get applications within period
        applications = BatchEnrollmentApplication.objects.filter(
            batch=program,
            created_at__gte=start_date
        )
        
        # Overview statistics
        total_applications = applications.count()
        approved = applications.filter(status='approved').count()
        rejected = applications.filter(status='rejected').count()
        pending = applications.filter(
            status__in=['submitted', 'eligibility_check', 'constituency_review',
                       'regional_review', 'national_review']
        ).count()
        
        approval_rate = 0
        if total_applications > 0:
            approval_rate = round((approved / total_applications) * 100, 1)
        
        # Average review time
        avg_review_days = 0
        completed = applications.filter(
            final_decision_at__isnull=False,
            submitted_at__isnull=False
        )
        if completed.exists():
            review_times = []
            for app in completed:
                delta = app.final_decision_at - app.submitted_at
                review_times.append(delta.days)
            if review_times:
                avg_review_days = round(sum(review_times) / len(review_times))
        
        # Budget utilization
        budget_utilized = approved * float(program.support_package_value_ghs)
        
        # Applications over time (by month)
        apps_over_time = []
        if period != 'all_time':
            # Group by month
            from django.db.models.functions import TruncMonth
            monthly_data = applications.annotate(
                month=TruncMonth('submitted_at')
            ).values('month').annotate(
                total=Count('id'),
                approved_count=Count('id', filter=Q(status='approved')),
                rejected_count=Count('id', filter=Q(status='rejected')),
                pending_count=Count('id', filter=Q(status__in=[
                    'submitted', 'eligibility_check', 'constituency_review',
                    'regional_review', 'national_review'
                ]))
            ).order_by('month')
            
            for data in monthly_data:
                if data['month']:
                    apps_over_time.append({
                        'month': data['month'].strftime('%Y-%m'),
                        'applications': data['total'],
                        'approved': data['approved_count'],
                        'rejected': data['rejected_count'],
                        'pending': data['pending_count']
                    })
        
        # Regional breakdown
        regional_breakdown = []
        if breakdown_by == 'region':
            regions = applications.values('farm__primary_region').annotate(
                total=Count('id'),
                approved_count=Count('id', filter=Q(status='approved')),
                approval_rate_calc=Count('id', filter=Q(status='approved')) * 100.0 / Count('id')
            ).order_by('-total')
            
            for region_data in regions:
                region = region_data['farm__primary_region'] or 'Unknown'
                
                # Get allocated slots for this region
                allocated_slots = 0
                if program.regional_allocation:
                    for r in program.regional_allocation:
                        if r.get('region') == region:
                            allocated_slots = r.get('allocated_slots', 0)
                            break
                
                regional_breakdown.append({
                    'region': region,
                    'applications': region_data['total'],
                    'approved': region_data['approved_count'],
                    'approval_rate': round(region_data['approval_rate_calc'], 1) if region_data['total'] > 0 else 0,
                    'slots_allocated': allocated_slots,
                    'slots_filled': region_data['approved_count']
                })
        
        # Beneficiary progress
        enrolled = applications.filter(enrollment_completed=True).count()
        active_beneficiaries = enrolled  # Would need more tracking
        
        # Distribution metrics (would need more data tracking)
        distribution_metrics = {
            'chicks_distributed': 0,  # Would calculate from support_package
            'feed_bags_distributed': 0,
            'trainings_conducted': 0,
            'farm_visits_completed': 0,
            'veterinary_interventions': 0
        }
        
        return Response({
            'batch_id': str(program.id),
            'batch_name': program.batch_name,
            'period': period,
            'overview': {
                'total_applications': total_applications,
                'approved': approved,
                'rejected': rejected,
                'pending': pending,
                'approval_rate': approval_rate,
                'average_review_days': avg_review_days,
                'total_budget_utilized': budget_utilized
            },
            'applications_over_time': apps_over_time,
            'regional_breakdown': regional_breakdown,
            'beneficiary_progress': {
                'total_beneficiaries': approved,
                'active': active_beneficiaries,
                'completed': 0,  # Would need tracking
                'dropouts': 0,  # Would need tracking
                'dropout_rate': 0,
                'average_completion_time_months': 0  # Would need tracking
            },
            'distribution_metrics': distribution_metrics
        })


class AdminBatchDuplicateView(APIView):
    """
    POST /api/admin/programs/{batch_id}/duplicate/
    
    Duplicate a program as a template for a new program.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, batch_id):
        try:
            source_program = Batch.objects.get(id=batch_id)
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Source program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not BatchPolicy.can_create_batch(request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get new program details
        new_code = request.data.get('new_program_code')
        new_name = request.data.get('new_program_name')
        
        if not new_code or not new_name:
            return Response(
                {'error': 'new_program_code and new_program_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check uniqueness
        if Batch.objects.filter(batch_code=new_code).exists():
            return Response(
                {'error': f'Batch code {new_code} already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Copy settings
        copy_settings = request.data.get('copy_settings', {})
        adjustments = request.data.get('adjustments', {})
        
        # Create new program
        new_program = Batch.objects.create(
            batch_code=new_code,
            batch_name=new_name,
            description=source_program.description if copy_settings.get('copy_eligibility', True) else '',
            long_description=source_program.long_description,
            implementing_agency=source_program.implementing_agency,
            start_date=adjustments.get('batch_info', {}).get('start_date', source_program.start_date),
            end_date=adjustments.get('batch_info', {}).get('end_date', source_program.end_date),
            application_deadline=source_program.application_deadline,
            eligible_farmer_age_min=source_program.eligible_farmer_age_min,
            eligible_farmer_age_max=source_program.eligible_farmer_age_max,
            eligibility_criteria=source_program.eligibility_criteria if copy_settings.get('copy_eligibility', True) else {},
            support_package_details=source_program.support_package_details if copy_settings.get('copy_support_package', True) else {},
            support_package_value_ghs=source_program.support_package_value_ghs,
            beneficiary_contribution_ghs=source_program.beneficiary_contribution_ghs,
            document_requirements=source_program.document_requirements if copy_settings.get('copy_document_requirements', True) else [],
            batch_info=adjustments.get('batch_info', source_program.batch_info),
            total_slots=adjustments.get('slot_allocation', {}).get('total_slots', source_program.total_slots),
            allow_overbooking=source_program.allow_overbooking,
            overbooking_percentage=source_program.overbooking_percentage,
            regional_allocation=source_program.regional_allocation if copy_settings.get('copy_regional_allocation', True) else [],
            requires_constituency_approval=source_program.requires_constituency_approval if copy_settings.get('copy_approval_workflow', True) else True,
            requires_regional_approval=source_program.requires_regional_approval if copy_settings.get('copy_approval_workflow', True) else True,
            requires_national_approval=source_program.requires_national_approval if copy_settings.get('copy_approval_workflow', True) else True,
            approval_sla_days=source_program.approval_sla_days,
            funding_source=source_program.funding_source,
            budget_code=adjustments.get('funding', {}).get('budget_code', source_program.budget_code),
            total_budget_ghs=source_program.total_budget_ghs,
            is_active=False,  # New programs start inactive
            is_accepting_applications_override=False,
            is_published=False,
            status='inactive',
            created_by=request.user
        )
        
        return Response({
            'id': str(new_program.id),
            'batch_code': new_program.batch_code,
            'batch_name': new_program.batch_name,
            'message': 'Program duplicated successfully',
            'source_batch_id': str(source_program.id),
            'created_at': new_program.created_at.isoformat()
        }, status=status.HTTP_201_CREATED)
