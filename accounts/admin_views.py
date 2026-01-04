"""
Admin Dashboard API Views for Privileged Office Staff

Provides comprehensive administrative endpoints for:
- User management
- Application screening
- Analytics and reporting
- Program administration
- System configuration
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta

from .models import User
from .serializers import UserSerializer, UserDetailSerializer
from .policies.user_policy import UserPolicy
from farms.models import Farm
from farms.application_models import FarmApplication
from farms.batch_enrollment_models import Batch, BatchEnrollmentApplication


class AdminDashboardOverviewView(APIView):
    """
    GET /api/admin/dashboard/overview/
    
    Returns high-level metrics for admin dashboard home page.
    
    Access:
    - SUPER_ADMIN: All metrics
    - NATIONAL_ADMIN: All metrics
    - REGIONAL_COORDINATOR: Regional metrics
    - CONSTITUENCY_OFFICIAL: Constituency metrics
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check admin access - use role field directly
        admin_roles = ['SUPER_ADMIN', 'YEA_OFFICIAL', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL']
        if user.role not in admin_roles:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Base querysets
        farms_qs = Farm.objects.all()
        applications_qs = FarmApplication.objects.all()
        users_qs = User.objects.all()
        
        # Scope by jurisdiction
        if UserPolicy.is_constituency_official(user):
            farms_qs = farms_qs.filter(primary_constituency=user.constituency)
            applications_qs = applications_qs.filter(primary_constituency=user.constituency)
            users_qs = users_qs.filter(constituency=user.constituency)
        elif UserPolicy.is_regional_coordinator(user):
            farms_qs = farms_qs.filter(region=user.region)
            applications_qs = applications_qs.filter(region=user.region)
            users_qs = users_qs.filter(region=user.region)
        
        # Farm metrics
        total_farms = farms_qs.count()
        active_farms = farms_qs.filter(farm_status='Active').count()
        approved_farms = farms_qs.filter(
            application_status='Approved'
        ).count()
        
        # Application metrics
        total_applications = applications_qs.count()
        pending_statuses = ['constituency_review', 'regional_review', 'national_review']
        pending_applications = applications_qs.filter(
            status__in=pending_statuses
        ).count()
        approved_applications = applications_qs.filter(
            status='approved'
        ).count()
        rejected_applications = applications_qs.filter(
            status='rejected'
        ).count()
        
        # User metrics
        total_users = users_qs.count()
        active_users = users_qs.filter(is_active=True).count()
        verified_users = users_qs.filter(is_verified=True).count()
        
        # Recent applications (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_applications = applications_qs.filter(
            submitted_at__gte=week_ago
        ).count()
        
        # Pending actions based on user role
        pending_screening = 0
        pending_regional = 0
        pending_national = 0

        if UserPolicy.is_constituency_official(user):
            pending_screening = applications_qs.filter(
                status__in=pending_statuses,
                current_review_level='constituency'
            ).count()
        
        if UserPolicy.is_regional_coordinator(user):
            pending_regional = applications_qs.filter(
                status='regional_review',
                current_review_level='regional'
            ).count()
        
        if UserPolicy.is_national_admin(user) or UserPolicy.is_super_admin(user):
            pending_national = applications_qs.filter(
                status='national_review',
                current_review_level='national'
            ).count()
        
        # Pending applications list (for dashboard table)
        pending_list = list(
            applications_qs.filter(status__in=pending_statuses)
            .order_by('submitted_at')[:20]
            .values(
                'id',
                'application_number',
                'first_name',
                'middle_name',
                'last_name',
                'status',
                'submitted_at',
                'primary_constituency',
                'region',
                'primary_production_type',
                'planned_bird_capacity',
            )
        )

        approved_list = list(
            applications_qs.filter(status='approved')
            .order_by('-final_approved_at', '-submitted_at')[:20]
            .values(
                'id',
                'application_number',
                'first_name',
                'middle_name',
                'last_name',
                'status',
                'submitted_at',
                'final_approved_at',
                'primary_constituency',
                'region',
                'primary_production_type',
                'planned_bird_capacity',
            )
        )

        return Response({
            'farms': {
                'total': total_farms,
                'active': active_farms,
                'approved': approved_farms,
                'approval_rate': round((approved_farms / total_farms * 100) if total_farms > 0 else 0, 1)
            },
            'applications': {
                'total': total_applications,
                'pending': pending_applications,
                'approved': approved_applications,
                'rejected': rejected_applications,
                'recent_7_days': recent_applications
            },
            'users': {
                'total': total_users,
                'active': active_users,
                'verified': verified_users,
                'verification_rate': round((verified_users / total_users * 100) if total_users > 0 else 0, 1)
            },
            'pending_actions': {
                'constituency_screening': pending_screening,
                'regional_approval': pending_regional,
                'national_approval': pending_national,
                'total': pending_screening + pending_regional + pending_national
            },
            'pending_applications': pending_list,
            'approved_applications': approved_list,
            'jurisdiction': {
                'level': user.role,
                'region': user.region if user.region else 'All Regions',
                'constituency': user.constituency if user.constituency else 'All Constituencies'
            }
        })


def _can_user_approve(user, application):
    if UserPolicy.is_super_admin(user) or UserPolicy.is_national_admin(user):
        return True
    if application.status == 'regional_review' and UserPolicy.is_regional_coordinator(user):
        return application.region == user.region
    if application.status == 'constituency_review' and UserPolicy.is_constituency_official(user):
        return application.primary_constituency == user.constituency
    return False


def _create_farm_profile(application):
    """
    Create farm profile from approved application.
    Also creates a primary FarmLocation based on application data.
    Returns True if created successfully, False otherwise.
    """
    from datetime import date
    from django.contrib.gis.geos import Point
    from farms.models import FarmLocation
    from farms.services.gps_service import GhanaPostGPSService
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Skip if farm already exists
    if hasattr(application, 'farm_profile') and application.farm_profile:
        return False
    
    # Skip if user account not created yet
    if not application.user_account:
        return False
    
    try:
        farm = Farm.objects.create(
            user=application.user_account,
            # Section 1: Personal Identity
            first_name=application.first_name,
            middle_name=application.middle_name or '',
            last_name=application.last_name,
            date_of_birth=application.date_of_birth,
            gender=application.gender,
            ghana_card_number=application.ghana_card_number,
            marital_status='Single',
            number_of_dependents=0,
            # Section 1.2: Contact
            primary_phone=application.primary_phone,
            alternate_phone=application.alternate_phone or '',
            email=application.email,
            preferred_contact_method='Phone Call',
            residential_address=application.residential_address or '',
            primary_constituency=application.primary_constituency,
            # Section 1.3: Next of Kin (required)
            nok_full_name='To be provided',
            nok_relationship='To be provided',
            nok_phone=application.primary_phone,
            # Section 1.4: Education & Experience
            education_level='JHS',
            literacy_level='Can Read & Write',
            years_in_poultry=application.years_in_poultry or 0,
            farming_full_time=True,
            # Section 2: Business Information
            farm_name=application.proposed_farm_name,
            ownership_type='Sole Proprietorship',
            tin=f'{application.id.int % 10000000000:010d}',  # 10 digit numeric TIN from UUID
            # Section 4: Infrastructure
            number_of_poultry_houses=1,
            total_bird_capacity=application.planned_bird_capacity,
            current_bird_count=0,
            housing_type='Deep Litter',
            total_infrastructure_value_ghs=0,
            # Section 5: Production Planning
            primary_production_type=application.primary_production_type,
            planned_production_start_date=date.today(),
            # Section 7: Financial Information (required)
            initial_investment_amount=0,
            funding_source=['YEA Program'],
            monthly_operating_budget=0,
            expected_monthly_revenue=0,
            has_outstanding_debt=False,
            # Section 9: Application Workflow
            application_status='Approved',
            farm_status='Pending Setup',
            approval_date=application.final_approved_at,
            approved_by=application.final_approved_by,
            activation_date=timezone.now(),
            registration_source='government_initiative' if application.application_type == 'government_program' else 'self_registered',
            yea_program_batch=application.yea_program_batch or '',
            referral_source=application.referral_source or 'Direct Application',
        )
        
        # Create primary farm location from application data
        try:
            # Get application data
            gps_address = getattr(application, 'farm_gps_address', '').strip()
            location_description = getattr(application, 'farm_location_description', 'Primary farm location')
            land_size = getattr(application, 'land_size_acres', 0)
            
            # Try to decode GPS address if provided in application
            if gps_address and gps_address != 'PENDING-GPS-UPDATE':
                try:
                    location_data = GhanaPostGPSService.get_coordinates(gps_address)
                    lat = location_data['latitude']
                    lon = location_data['longitude']
                    logger.info(f"Used GPS address from application: {gps_address}")
                except Exception as e:
                    logger.warning(f"Could not decode GPS from application: {e}. Using region center.")
                    # Fallback to region center based on application data
                    region_code = application.region[:2].upper() if application.region else 'GA'
                    lat, lon = GhanaPostGPSService._get_region_center(region_code)
                    gps_address = 'PENDING-GPS-UPDATE'
            else:
                # No GPS address in application, use region center
                region_code = application.region[:2].upper() if application.region else 'GA'
                lat, lon = GhanaPostGPSService._get_region_center(region_code)
                gps_address = 'PENDING-GPS-UPDATE'
                logger.info(f"No GPS in application. Using {application.region} center coordinates.")
            
            FarmLocation.objects.create(
                farm=farm,
                gps_address_string=gps_address,
                location=Point(lon, lat),
                region=application.region or 'Greater Accra',
                district=application.district or '',
                constituency=application.primary_constituency,
                community='',  # To be updated by farmer
                land_size_acres=land_size,
                land_ownership_status='Owned',
                is_primary_location=True,
                road_accessibility='All Year',
                nearest_landmark=location_description[:200] if location_description else '',
            )
            logger.info(f"Primary location created for {farm.farm_name}")
        except Exception as loc_error:
            # Don't fail farm creation if location creation fails
            logger.error(f"Warning: Could not create primary location: {loc_error}")
        
        # Link farm to application
        application.farm_profile = farm
        application.farm_created_at = timezone.now()
        application.save()
        
        return True
    except Exception as e:
        # Log error but don't fail the approval
        print(f"Error creating farm profile: {e}")
        return False


class AdminApplicationApproveView(APIView):
    """
    POST /api/admin/applications/<uuid>/approve/
    Advances application to next review level or final approval.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        try:
            application = FarmApplication.objects.get(id=application_id)
        except FarmApplication.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        if not _can_user_approve(request.user, application):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        next_level = None

        if application.status == 'constituency_review':
            application.status = 'regional_review'
            application.constituency_approved_at = now
            application.constituency_approved_by = request.user
            application.current_review_level = 'regional'
            next_level = 'regional'
        elif application.status == 'regional_review':
            application.status = 'national_review'
            application.regional_approved_at = now
            application.regional_approved_by = request.user
            application.current_review_level = 'national'
            next_level = 'national'
        elif application.status == 'national_review':
            application.status = 'approved'
            application.final_approved_at = now
            application.final_approved_by = request.user
            application.current_review_level = None
            next_level = 'final'
            
            # Create farm profile immediately upon final approval
            farm_created = _create_farm_profile(application)
        else:
            return Response({'error': f'Cannot approve application in status {application.status}'}, status=status.HTTP_400_BAD_REQUEST)

        comments = request.data.get('comments')
        if comments:
            application.approval_comments = comments

        application.save()

        response_data = {
            'success': True,
            'application_number': application.application_number,
            'new_status': application.status,
            'next_level': next_level,
        }
        
        if next_level == 'final' and farm_created:
            response_data['farm_created'] = True
            response_data['message'] = 'Application approved and farm profile created'

        return Response(response_data)


class AdminApplicationRejectView(APIView):
    """
    POST /api/admin/applications/<uuid>/reject/
    Rejects application with a reason.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        try:
            application = FarmApplication.objects.get(id=application_id)
        except FarmApplication.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        if not _can_user_approve(request.user, application):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get('reason')
        if not reason:
            return Response({'error': 'Rejection reason is required'}, status=status.HTTP_400_BAD_REQUEST)

        application.status = 'rejected'
        application.rejected_at = timezone.now()
        application.rejected_by = request.user
        application.rejection_reason = reason
        application.rejection_details = request.data.get('details', '')
        application.current_review_level = None
        application.save()

        return Response({
            'success': True,
            'application_number': application.application_number,
            'new_status': 'rejected'
        })


class AdminUserListView(APIView):
    """
    GET /api/admin/users/
    
    List users with filtering, search, and pagination.
    
    Query Params:
    - role: Filter by role
    - region: Filter by region
    - constituency: Filter by constituency
    - is_active: Filter by active status
    - search: Search by name, email, phone
    - page: Page number (default: 1)
    - page_size: Results per page (default: 20)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check if user has admin access
        admin_roles = ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL', 'EXTENSION_OFFICER']
        if user.role not in admin_roles:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get base queryset
        queryset = User.objects.all()
        
        # Scope by jurisdiction
        if user.role == 'CONSTITUENCY_OFFICIAL':
            queryset = queryset.filter(constituency=user.constituency)
        elif user.role == 'REGIONAL_COORDINATOR':
            queryset = queryset.filter(region=user.region)
        # SUPER_ADMIN and NATIONAL_ADMIN see all users
        
        # Apply filters
        role = request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        region = request.query_params.get('region')
        if region:
            queryset = queryset.filter(region=region)
        
        constituency = request.query_params.get('constituency')
        if constituency:
            queryset = queryset.filter(constituency=constituency)
        
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(username__icontains=search)
            )
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        pages = (total + page_size - 1) // page_size
        users = queryset.order_by('-created_at')[start:end]
        
        serializer = UserSerializer(users, many=True)
        
        return Response({
            'results': serializer.data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'pages': pages,
                'has_next': page < pages,
                'has_previous': page > 1
            }
        })


class AdminUserDetailView(APIView):
    """
    GET /api/admin/users/{user_id}/
    PUT /api/admin/users/{user_id}/
    DELETE /api/admin/users/{user_id}/
    
    SECURITY: SUPER_ADMIN accounts are protected and cannot be modified or deleted
    by any other user. Only the SUPER_ADMIN can update their own account.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check view permission (simplified)
        user = request.user
        if user.role not in ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL']:
            if user.id != target_user.id:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = UserDetailSerializer(target_user)
        return Response(serializer.data)
    
    def put(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user = request.user
        
        # SECURITY: Protect SUPER_ADMIN accounts from being modified by others
        if target_user.role == 'SUPER_ADMIN' and user.id != target_user.id:
            return Response(
                {'error': 'SUPER_ADMIN accounts cannot be modified by other users. Only the account owner can update their own profile.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check edit permission for non-SUPER_ADMIN targets
        if user.role not in ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR']:
            if user.id != target_user.id:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        data = request.data
        
        serializer = UserDetailSerializer(target_user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, user_id):
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # SECURITY: SUPER_ADMIN accounts cannot be deleted by anyone
        if target_user.role == 'SUPER_ADMIN':
            return Response(
                {'error': 'SUPER_ADMIN accounts cannot be deleted. This is a protected account type.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only SUPER_ADMIN can delete users
        if request.user.role != 'SUPER_ADMIN':
            return Response(
                {'error': 'Permission denied. Only SUPER_ADMIN can delete users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        target_user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserCreateView(APIView):
    """
    POST /api/admin/users/create/
    
    Create new staff user account and send invitation email.
    
    Request Body:
    {
        "email": "staff@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "CONSTITUENCY_OFFICIAL",
        "phone": "+233241234567",  // Optional
        "region": "Greater Accra",  // Required for regional roles
        "constituency": "Tema East"  // Required for constituency roles
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from accounts.services.staff_invitation_service import StaffInvitationService
        
        # Extract required fields
        email = request.data.get('email')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        role = request.data.get('role')
        
        # Validate required fields
        if not all([email, first_name, last_name, role]):
            return Response(
                {'error': 'email, first_name, last_name, and role are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create staff invitation
            result = StaffInvitationService.create_staff_invitation(
                admin_user=request.user,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                phone=request.data.get('phone'),
                region=request.data.get('region'),
                constituency=request.data.get('constituency')
            )
            
            return Response({
                'id': str(result['user'].id),
                'username': result['user'].username,
                'email': result['user'].email,
                'first_name': result['user'].first_name,
                'last_name': result['user'].last_name,
                'role': result['user'].role,
                'is_active': result['user'].is_active,
                'invitation_sent': True,
                'expires_at': result['expires_at'].isoformat(),
                'message': result['message']
            }, status=status.HTTP_201_CREATED)
            
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to create invitation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminApplicationListView(APIView):
    """
    GET /api/admin/applications/
    
    List farm applications with filtering and search.
    
    Query Params:
    - status: Filter by status
    - application_type: government_program or independent
    - region: Filter by region
    - constituency: Filter by constituency
    - screening_stage: constituency, regional, national
    - search: Search by name, phone, application_id
    - page, page_size: Pagination
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check admin access
        admin_roles = ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL']
        if user.role not in admin_roles:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Base queryset
        queryset = FarmApplication.objects.all()
        
        # Scope by jurisdiction
        if user.role == 'CONSTITUENCY_OFFICIAL':
            queryset = queryset.filter(primary_constituency=user.constituency)
        elif user.role == 'REGIONAL_COORDINATOR':
            queryset = queryset.filter(region=user.region)
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        app_type = request.query_params.get('application_type')
        if app_type:
            queryset = queryset.filter(application_type=app_type)
        
        region = request.query_params.get('region')
        if region:
            queryset = queryset.filter(region=region)
        
        constituency = request.query_params.get('constituency')
        if constituency:
            queryset = queryset.filter(primary_constituency=constituency)
        
        screening_stage = request.query_params.get('screening_stage')
        if screening_stage:
            queryset = queryset.filter(screening_stage=screening_stage)
        
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(application_id__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(primary_phone__icontains=search)
            )
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        pages = (total + page_size - 1) // page_size
        applications = queryset.order_by('-submitted_at')[start:end]
        
        # Serialize (basic fields for list view)
        data = []
        for app in applications:
            data.append({
                'id': str(app.id),
                'application_number': app.application_number,
                'applicant_name': f"{app.first_name} {app.last_name}",
                'farm_name': app.proposed_farm_name,
                'phone': str(app.primary_phone),
                'email': app.email,
                'application_type': app.application_type,
                'status': app.status,
                'current_review_level': app.current_review_level,
                'region': app.region,
                'constituency': app.primary_constituency,
                'submitted_at': app.submitted_at.isoformat() if app.submitted_at else None,
                'yea_program_batch': app.yea_program_batch
            })
        
        return Response({
            'results': data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'pages': pages,
                'has_next': page < pages,
                'has_previous': page > 1
            }
        })


class AdminBatchListView(APIView):
    """
    GET /api/admin/programs/
    
    List batchs with statistics.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not UserPolicy.has_admin_access(request.user):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        programs = Batch.objects.all().order_by('-created_at')
        
        data = []
        for program in programs:
            data.append({
                'id': program.id,
                'batch_code': program.batch_code,
                'batch_name': program.batch_name,
                'is_active': program.is_active,
                'total_slots': program.total_slots,
                'slots_filled': program.slots_filled,
                'slots_available': program.slots_available,
                'application_deadline': program.application_deadline,
                'start_date': program.start_date,
                'end_date': program.end_date,
                'created_at': program.created_at
            })
        
        return Response({'results': data})


class AdminAnalyticsView(APIView):
    """
    GET /api/admin/analytics/
    
    Returns analytics data for charts and reports.
    
    Query Params:
    - metric: applications_trend, user_growth, regional_distribution
    - period: 7d, 30d, 90d, 1y
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        admin_roles = ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL']
        if request.user.role not in admin_roles:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        metric = request.query_params.get('metric', 'applications_trend')
        period = request.query_params.get('period', '30d')
        
        # Calculate date range
        days_map = {'7d': 7, '30d': 30, '90d': 90, '1y': 365}
        days = days_map.get(period, 30)
        start_date = timezone.now() - timedelta(days=days)
        
        if metric == 'applications_trend':
            # Applications over time
            applications = FarmApplication.objects.filter(
                submitted_at__gte=start_date
            ).extra({'date': 'date(submitted_at)'}).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            return Response({
                'metric': 'applications_trend',
                'period': period,
                'data': list(applications)
            })
        
        elif metric == 'regional_distribution':
            # Applications by region
            regional_data = FarmApplication.objects.values('region').annotate(
                total=Count('id'),
                pending=Count('id', filter=Q(status='submitted')),
                approved=Count('id', filter=Q(status='approved'))
            ).order_by('-total')
            
            return Response({
                'metric': 'regional_distribution',
                'data': list(regional_data)
            })
        
        elif metric == 'user_growth':
            # User registrations over time
            users = User.objects.filter(
                created_at__gte=start_date
            ).extra({'date': 'date(created_at)'}).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            return Response({
                'metric': 'user_growth',
                'period': period,
                'data': list(users)
            })
        
        return Response({'error': 'Invalid metric'}, status=status.HTTP_400_BAD_REQUEST)


class AdminStaffInvitationAcceptView(APIView):
    """
    POST /api/staff/accept-invitation/
    
    Accept staff invitation and set password (PUBLIC endpoint).
    
    Request Body:
    {
        "uidb64": "encoded_user_id",
        "token": "invitation_token",
        "password": "secure_password"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from accounts.services.staff_invitation_service import StaffInvitationService
        
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')
        
        if not all([uidb64, token, password]):
            return Response(
                {'error': 'uidb64, token, and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use password for both if confirm_password not provided (backward compatibility)
        if not confirm_password:
            confirm_password = password
        
        try:
            result = StaffInvitationService.accept_invitation(uidb64, token, password, confirm_password)
            user = result['user']
            
            return Response({
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_active': user.is_active,
                'message': result['message']
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to accept invitation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminStaffInvitationResendView(APIView):
    """
    POST /api/admin/staff/{user_id}/resend-invitation/
    
    Resend invitation email to inactive staff member.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        from accounts.services.staff_invitation_service import StaffInvitationService
        
        try:
            result = StaffInvitationService.resend_invitation(
                user_id=user_id,
                admin_user=request.user
            )
            
            return Response({
                'invitation_sent': True,
                'expires_at': result['expires_at'].isoformat(),
                'message': result['message']
            }, status=status.HTTP_200_OK)
            
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to resend invitation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminStaffInvitationCancelView(APIView):
    """
    DELETE /api/admin/staff/{user_id}/cancel-invitation/
    
    Cancel pending staff invitation (deletes inactive user).
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, user_id):
        from accounts.services.staff_invitation_service import StaffInvitationService
        
        try:
            result = StaffInvitationService.cancel_invitation(
                user_id=user_id,
                admin_user=request.user
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to cancel invitation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminSystemConfigView(APIView):
    """
    GET /api/admin/config/
    PUT /api/admin/config/
    
    System configuration settings (Super Admin only).
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 'SUPER_ADMIN':
            return Response(
                {'error': 'Super Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from django.conf import settings
        
        config = {
            'sms_enabled': getattr(settings, 'SMS_ENABLED', False),
            'debug_mode': settings.DEBUG,
            'allowed_hosts': settings.ALLOWED_HOSTS,
            'cors_origins': getattr(settings, 'CORS_ALLOWED_ORIGINS', []),
            'media_url': settings.MEDIA_URL,
            'static_url': settings.STATIC_URL
        }
        
        return Response(config)
