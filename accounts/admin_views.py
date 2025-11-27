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
        admin_roles = ['SUPER_ADMIN', 'NATIONAL_ADMIN', 'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL']
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
        pending_applications = applications_qs.filter(
            status__in=['submitted', 'constituency_review', 'regional_review', 'national_review']
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
                status__in=['submitted', 'constituency_review'],
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
            'jurisdiction': {
                'level': user.role,
                'region': user.region if user.region else 'All Regions',
                'constituency': user.constituency if user.constituency else 'All Constituencies'
            }
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
        
        # Check edit permission
        user = request.user
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
        
        if not all([uidb64, token, password]):
            return Response(
                {'error': 'uidb64, token, and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = StaffInvitationService.accept_invitation(uidb64, token, password)
            
            return Response({
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_active': user.is_active,
                'message': 'Invitation accepted successfully. You can now log in with your credentials.'
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
                admin_user=request.user,
                user_id=user_id
            )
            
            return Response({
                'id': str(result['user'].id),
                'username': result['user'].username,
                'email': result['user'].email,
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
            StaffInvitationService.cancel_invitation(
                admin_user=request.user,
                user_id=user_id
            )
            
            return Response({
                'message': 'Invitation cancelled successfully'
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
