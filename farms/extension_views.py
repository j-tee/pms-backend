"""
Extension Officer / Field Officer Views

"Extension Officer" and "Field Officer" are synonymous terms in this system.
All three roles below have field officer access:
- EXTENSION_OFFICER (primary field officer role)
- VETERINARY_OFFICER (field officer with animal health focus)
- CONSTITUENCY_OFFICIAL (senior field officer with assignment privileges)

PRIMARY RESPONSIBILITY:
Field officers ensure farmers are feeding the system with accurate data.
They verify farmer-entered data and assist with data input when necessary.

Core Functions:
1. DATA VERIFICATION - Review and verify farmer-entered production data
2. DATA ASSISTANCE - Help farmers enter data when they need support
3. FARMER REGISTRATION - Register farmers on behalf (field registration)
4. FARM UPDATES - Update farm information after field visits
5. QUALITY TRACKING - Monitor data quality and flag issues

EXTENSION/VET ADDITIONAL DUTIES:
Extension officers and veterinary officers have additional responsibilities:
- Technical advice and recommendations
- Health monitoring and interventions
- Training and capacity building
- Issue escalation to regional/national level
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import logging
import uuid

from farms.models import Farm, FarmLocation, Infrastructure, FarmDocument
from farms.application_models import FarmApplication
from accounts.models import User

logger = logging.getLogger(__name__)
User = get_user_model()


class IsFieldOfficer:
    """
    Permission check for field officers (Extension Officers, Vet Officers, Constituency Officials).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in [
            'EXTENSION_OFFICER',
            'VETERINARY_OFFICER', 
            'CONSTITUENCY_OFFICIAL'
        ]


class FieldOfficerDashboardView(APIView):
    """
    GET /api/extension/dashboard/
    
    Dashboard overview for field officers.
    Shows farms, pending tasks, recent activities.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get farms in jurisdiction
        farms = self._get_jurisdiction_farms(user)
        
        # Calculate stats
        total_farms = farms.count()
        active_farms = farms.filter(farm_status='Active').count()
        pending_approval = farms.filter(application_status='Pending').count()
        
        # Recent registrations (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_registrations = farms.filter(created_at__gte=thirty_days_ago).count()
        
        # Farms needing attention (no recent updates)
        ninety_days_ago = timezone.now() - timedelta(days=90)
        farms_needing_update = farms.filter(updated_at__lt=ninety_days_ago).count()
        
        # Get recent extension visits if model exists
        recent_visits = []
        try:
            from .extension_models import ExtensionVisit
            visits = ExtensionVisit.objects.filter(
                officer=user
            ).order_by('-visit_date')[:5]
            recent_visits = [{
                'id': str(v.id),
                'farm_name': v.farm.farm_name,
                'visit_date': v.visit_date.isoformat(),
                'purpose': v.purpose,
            } for v in visits]
        except ImportError:
            pass
        
        return Response({
            'summary': {
                'total_farms': total_farms,
                'active_farms': active_farms,
                'pending_approval': pending_approval,
                'recent_registrations': recent_registrations,
                'farms_needing_update': farms_needing_update,
            },
            'recent_visits': recent_visits,
            'officer': {
                'name': user.get_full_name() or user.username,
                'role': user.get_role_display(),
                'constituency': getattr(user, 'constituency', None),
                'region': getattr(user, 'region', None),
            }
        })
    
    def _get_jurisdiction_farms(self, user):
        """Get farms based on user's role and jurisdiction"""
        if user.role == 'CONSTITUENCY_OFFICIAL':
            return Farm.objects.filter(primary_constituency=user.constituency)
        elif user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
            return Farm.objects.filter(
                Q(extension_officer=user) | 
                Q(assigned_extension_officer=user) |
                Q(primary_constituency=user.constituency)
            )
        return Farm.objects.none()


class FieldOfficerFarmListView(APIView):
    """
    GET /api/extension/farms/
    
    List farms in the field officer's jurisdiction.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        farms = self._get_jurisdiction_farms(user)
        
        # Apply filters
        farm_status = request.query_params.get('status')
        if farm_status:
            farms = farms.filter(farm_status=farm_status)
        
        application_status = request.query_params.get('application_status')
        if application_status:
            farms = farms.filter(application_status=application_status)
        
        search = request.query_params.get('search')
        if search:
            farms = farms.filter(
                Q(farm_name__icontains=search) |
                Q(farm_id__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(primary_phone__icontains=search)
            )
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = farms.count()
        farms = farms.order_by('-created_at')[start:end]
        
        farm_list = [{
            'id': str(f.id),
            'farm_id': f.farm_id,
            'farm_name': f.farm_name,
            'farmer_name': f.user.get_full_name() if f.user else 'N/A',
            'farmer_phone': str(f.primary_phone),
            'constituency': f.primary_constituency,
            'district': f.district,
            'farm_status': f.farm_status,
            'application_status': f.application_status,
            'production_type': f.primary_production_type,
            'bird_capacity': f.total_bird_capacity,
            'current_birds': f.current_bird_count,
            'has_extension_officer': f.extension_officer is not None,
            'created_at': f.created_at.isoformat(),
            'last_updated': f.updated_at.isoformat(),
        } for f in farms]
        
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'results': farm_list,
        })
    
    def _get_jurisdiction_farms(self, user):
        """Get farms based on user's role and jurisdiction"""
        if user.role == 'CONSTITUENCY_OFFICIAL':
            return Farm.objects.filter(primary_constituency=user.constituency)
        elif user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
            return Farm.objects.filter(
                Q(extension_officer=user) | 
                Q(assigned_extension_officer=user) |
                Q(primary_constituency=user.constituency)
            )
        return Farm.objects.none()


class FieldOfficerFarmDetailView(APIView):
    """
    GET /api/extension/farms/{farm_id}/
    PUT /api/extension/farms/{farm_id}/
    
    View or update farm details.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, farm_id):
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        farm = self._get_farm_if_accessible(user, farm_id)
        if not farm:
            return Response(
                {'error': 'Farm not found or access denied', 'code': 'FARM_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Full farm details
        data = {
            'id': str(farm.id),
            'farm_id': farm.farm_id,
            'farm_name': farm.farm_name,
            
            # Farmer info
            'farmer': {
                'id': str(farm.user.id) if farm.user else None,
                'name': farm.user.get_full_name() if farm.user else None,
                'phone': str(farm.primary_phone),
                'email': farm.email,
                'ghana_card': farm.ghana_card_number,
            },
            
            # Location
            'region': farm.region,
            'district': farm.district,
            'constituency': farm.primary_constituency,
            'town': farm.town,
            'residential_address': farm.residential_address,
            
            # Farm details
            'production_type': farm.primary_production_type,
            'housing_type': farm.housing_type,
            'total_bird_capacity': farm.total_bird_capacity,
            'current_bird_count': farm.current_bird_count,
            'number_of_poultry_houses': farm.number_of_poultry_houses,
            
            # Status
            'farm_status': farm.farm_status,
            'application_status': farm.application_status,
            'is_government_farmer': farm.is_government_farmer,
            
            # Financial
            'monthly_operating_budget': str(farm.monthly_operating_budget) if farm.monthly_operating_budget else None,
            'expected_monthly_revenue': str(farm.expected_monthly_revenue) if farm.expected_monthly_revenue else None,
            
            # Scores
            'farm_readiness_score': str(farm.farm_readiness_score) if farm.farm_readiness_score else None,
            'biosecurity_score': str(farm.biosecurity_score) if farm.biosecurity_score else None,
            
            # Assignment
            'extension_officer': {
                'id': str(farm.extension_officer.id),
                'name': farm.extension_officer.get_full_name(),
            } if farm.extension_officer else None,
            
            # Timestamps
            'created_at': farm.created_at.isoformat(),
            'updated_at': farm.updated_at.isoformat(),
        }
        
        return Response(data)
    
    def put(self, request, farm_id):
        """Update farm information"""
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        farm = self._get_farm_if_accessible(user, farm_id)
        if not farm:
            return Response(
                {'error': 'Farm not found or access denied', 'code': 'FARM_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Fields that field officers can update
        allowed_fields = [
            'farm_name',
            'current_bird_count',
            'number_of_poultry_houses',
            'total_bird_capacity',
            'housing_type',
            'primary_production_type',
            'monthly_operating_budget',
            'expected_monthly_revenue',
            'residential_address',
            'town',
            # Scores can be updated by field officers after assessment
            'farm_readiness_score',
            'biosecurity_score',
        ]
        
        # Additional fields for constituency officials
        if user.role == 'CONSTITUENCY_OFFICIAL':
            allowed_fields.extend([
                'farm_status',
                'extension_officer',
                'assigned_extension_officer',
            ])
        
        updated_fields = []
        for field in allowed_fields:
            if field in request.data:
                value = request.data[field]
                
                # Handle foreign key for extension officer
                if field in ['extension_officer', 'assigned_extension_officer'] and value:
                    try:
                        officer = User.objects.get(id=value)
                        if officer.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
                            return Response(
                                {'error': f'Invalid {field}: User is not an extension/vet officer'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        setattr(farm, field, officer)
                    except User.DoesNotExist:
                        return Response(
                            {'error': f'Invalid {field}: User not found'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    setattr(farm, field, value)
                updated_fields.append(field)
        
        if updated_fields:
            farm.save()
            
            # Log the update
            logger.info(f"Farm {farm.farm_id} updated by {user.username}: {updated_fields}")
            
            return Response({
                'success': True,
                'message': 'Farm updated successfully',
                'updated_fields': updated_fields,
            })
        
        return Response(
            {'error': 'No valid fields provided for update'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def _get_farm_if_accessible(self, user, farm_id):
        """Get farm if user has access"""
        try:
            farm = Farm.objects.get(id=farm_id)
            
            if user.role == 'CONSTITUENCY_OFFICIAL':
                if farm.primary_constituency == user.constituency:
                    return farm
            elif user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
                if (farm.extension_officer == user or 
                    farm.assigned_extension_officer == user or
                    farm.primary_constituency == user.constituency):
                    return farm
            
            return None
        except Farm.DoesNotExist:
            return None


class RegisterFarmerView(APIView):
    """
    POST /api/extension/register-farmer/
    
    Register a new farmer on behalf (field registration).
    Creates user account + farm in one step.
    
    This is the primary endpoint for field officers to onboard farmers.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data
        
        # Required fields
        required_fields = [
            'first_name', 'last_name', 'phone', 
            'farm_name', 'primary_constituency', 'district', 'region'
        ]
        
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return Response(
                {'error': f'Missing required fields: {", ".join(missing)}', 'code': 'MISSING_FIELDS'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate phone number
        phone = data['phone']
        if User.objects.filter(phone=phone).exists():
            return Response(
                {'error': 'A user with this phone number already exists', 'code': 'PHONE_EXISTS'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check Ghana Card if provided
        ghana_card = data.get('ghana_card_number')
        if ghana_card and Farm.objects.filter(ghana_card_number=ghana_card).exists():
            return Response(
                {'error': 'A farm with this Ghana Card already exists', 'code': 'GHANA_CARD_EXISTS'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create user account
            farmer_user = User.objects.create_user(
                username=f"farmer_{uuid.uuid4().hex[:8]}",
                phone=phone,
                email=data.get('email', ''),
                first_name=data['first_name'],
                last_name=data['last_name'],
                role='FARMER',
                is_active=True,
            )
            
            # Set password if provided, otherwise generate temporary
            password = data.get('password')
            if password:
                farmer_user.set_password(password)
            else:
                # Generate temporary password from last 4 digits of phone
                temp_password = f"YEA{phone[-4:]}!"
                farmer_user.set_password(temp_password)
            
            farmer_user.save()
            
            # Create farm
            farm = Farm.objects.create(
                user=farmer_user,
                farm_name=data['farm_name'],
                primary_phone=phone,
                alternate_phone=data.get('alternate_phone', ''),
                email=data.get('email', ''),
                ghana_card_number=ghana_card,
                
                # Location
                region=data['region'],
                district=data['district'],
                primary_constituency=data['primary_constituency'],
                town=data.get('town', ''),
                residential_address=data.get('residential_address', ''),
                
                # Farm details
                primary_production_type=data.get('production_type', 'Layers'),
                housing_type=data.get('housing_type', 'Deep Litter'),
                total_bird_capacity=data.get('total_bird_capacity', 0),
                current_bird_count=data.get('current_bird_count', 0),
                number_of_poultry_houses=data.get('number_of_poultry_houses', 1),
                
                # Status
                application_status='Approved',  # Field registered = pre-approved
                farm_status='Active',
                is_government_farmer=data.get('is_government_farmer', True),
                
                # Assign registering officer as extension officer
                extension_officer=user if user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER'] else None,
                assigned_extension_officer=user,
                
                # Financial (optional)
                monthly_operating_budget=data.get('monthly_operating_budget'),
                expected_monthly_revenue=data.get('expected_monthly_revenue'),
            )
            
            # Log registration
            logger.info(f"Farmer {farmer_user.username} registered by {user.username} in {data['primary_constituency']}")
            
            # TODO: Send SMS to farmer with login credentials
            # from core.tasks import send_sms_async
            # send_sms_async.delay(phone, f"Welcome to YEA Poultry! Your account: {farmer_user.username}, Password: {temp_password}")
            
            return Response({
                'success': True,
                'message': 'Farmer registered successfully',
                'farmer': {
                    'id': str(farmer_user.id),
                    'username': farmer_user.username,
                    'name': farmer_user.get_full_name(),
                    'phone': str(phone),
                },
                'farm': {
                    'id': str(farm.id),
                    'farm_id': farm.farm_id,
                    'farm_name': farm.farm_name,
                },
                'temporary_password': temp_password if not password else None,
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error registering farmer: {str(e)}")
            return Response(
                {'error': f'Registration failed: {str(e)}', 'code': 'REGISTRATION_ERROR'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AssignExtensionOfficerView(APIView):
    """
    POST /api/extension/farms/{farm_id}/assign-officer/
    
    Assign or reassign extension officer to a farm.
    Only constituency officials can do this.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, farm_id):
        user = request.user
        
        if user.role != 'CONSTITUENCY_OFFICIAL':
            return Response(
                {'error': 'Only constituency officials can assign extension officers', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            farm = Farm.objects.get(id=farm_id)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'Farm not found', 'code': 'FARM_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify farm is in constituency
        if farm.primary_constituency != user.constituency:
            return Response(
                {'error': 'Farm is not in your constituency', 'code': 'JURISDICTION_ERROR'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        officer_id = request.data.get('officer_id')
        if not officer_id:
            return Response(
                {'error': 'officer_id is required', 'code': 'MISSING_OFFICER_ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            officer = User.objects.get(id=officer_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Officer not found', 'code': 'OFFICER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if officer.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
            return Response(
                {'error': 'User is not an extension or veterinary officer', 'code': 'INVALID_OFFICER'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Assign officer
        farm.extension_officer = officer
        farm.assigned_extension_officer = officer
        farm.save()
        
        logger.info(f"Farm {farm.farm_id} assigned to officer {officer.username} by {user.username}")
        
        return Response({
            'success': True,
            'message': f'Farm assigned to {officer.get_full_name()}',
            'farm_id': str(farm.id),
            'officer': {
                'id': str(officer.id),
                'name': officer.get_full_name(),
                'phone': str(officer.phone),
            }
        })


class ListExtensionOfficersView(APIView):
    """
    GET /api/extension/officers/
    
    List extension/vet officers in the constituency.
    For assignment purposes.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role not in ['CONSTITUENCY_OFFICIAL', 'REGIONAL_COORDINATOR', 'NATIONAL_ADMIN', 'SUPER_ADMIN']:
            return Response(
                {'error': 'Access denied', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        officers = User.objects.filter(
            role__in=['EXTENSION_OFFICER', 'VETERINARY_OFFICER'],
            is_active=True
        )
        
        # Filter by constituency for constituency officials
        if user.role == 'CONSTITUENCY_OFFICIAL' and hasattr(user, 'constituency'):
            officers = officers.filter(constituency=user.constituency)
        elif user.role == 'REGIONAL_COORDINATOR' and hasattr(user, 'region'):
            officers = officers.filter(region=user.region)
        
        officer_list = [{
            'id': str(o.id),
            'name': o.get_full_name(),
            'role': o.role,
            'role_display': o.get_role_display(),
            'phone': str(o.phone),
            'email': o.email,
            'constituency': getattr(o, 'constituency', None),
            'assigned_farms_count': Farm.objects.filter(
                Q(extension_officer=o) | Q(assigned_extension_officer=o)
            ).count(),
        } for o in officers]
        
        return Response({
            'count': len(officer_list),
            'results': officer_list,
        })


class BulkUpdateFarmsView(APIView):
    """
    POST /api/extension/farms/bulk-update/
    
    Update multiple farms at once (e.g., after field visit).
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        updates = request.data.get('updates', [])
        if not updates:
            return Response(
                {'error': 'No updates provided', 'code': 'NO_UPDATES'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        for update in updates:
            farm_id = update.get('farm_id')
            if not farm_id:
                results.append({'farm_id': None, 'success': False, 'error': 'Missing farm_id'})
                continue
            
            try:
                farm = Farm.objects.get(id=farm_id)
                
                # Check access
                if user.role == 'CONSTITUENCY_OFFICIAL':
                    if farm.primary_constituency != user.constituency:
                        results.append({'farm_id': farm_id, 'success': False, 'error': 'Access denied'})
                        continue
                elif user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
                    if not (farm.extension_officer == user or 
                            farm.assigned_extension_officer == user or
                            farm.primary_constituency == user.constituency):
                        results.append({'farm_id': farm_id, 'success': False, 'error': 'Access denied'})
                        continue
                
                # Update allowed fields
                allowed_fields = ['current_bird_count', 'farm_status', 'biosecurity_score', 'farm_readiness_score']
                for field in allowed_fields:
                    if field in update:
                        setattr(farm, field, update[field])
                
                farm.save()
                results.append({'farm_id': farm_id, 'success': True})
                
            except Farm.DoesNotExist:
                results.append({'farm_id': farm_id, 'success': False, 'error': 'Farm not found'})
        
        successful = sum(1 for r in results if r['success'])
        
        return Response({
            'total': len(updates),
            'successful': successful,
            'failed': len(updates) - successful,
            'results': results,
        })


# =============================================================================
# DATA VERIFICATION VIEWS
# Primary responsibility: Ensure farmers input accurate data
# =============================================================================

class FarmDataVerificationView(APIView):
    """
    GET /api/extension/farms/{farm_id}/data-review/
    POST /api/extension/farms/{farm_id}/data-review/
    
    Review and verify farmer-entered data.
    Field officers can view recent entries and mark them as verified or flag issues.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, farm_id):
        """Get recent data entries for verification"""
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        farm = self._get_farm_if_accessible(user, farm_id)
        if not farm:
            return Response(
                {'error': 'Farm not found or access denied', 'code': 'FARM_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get recent production records
        production_data = []
        try:
            from flock_management.models import DailyProduction, Flock
            
            # Get flocks for this farm
            flocks = Flock.objects.filter(farm=farm)
            
            # Get last 30 days of production data
            thirty_days_ago = timezone.now() - timedelta(days=30)
            productions = DailyProduction.objects.filter(
                flock__farm=farm,
                date__gte=thirty_days_ago.date()
            ).order_by('-date')[:30]
            
            production_data = [{
                'id': str(p.id),
                'date': p.date.isoformat(),
                'flock_name': p.flock.name if p.flock else 'Unknown',
                'eggs_collected': p.eggs_collected,
                'mortality_count': p.mortality_count,
                'feed_consumed_kg': str(p.feed_consumed_kg) if p.feed_consumed_kg else None,
                'is_verified': getattr(p, 'is_verified', False),
                'verified_by': p.verified_by.get_full_name() if hasattr(p, 'verified_by') and p.verified_by else None,
                'created_at': p.created_at.isoformat() if hasattr(p, 'created_at') else None,
            } for p in productions]
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Error fetching production data: {e}")
        
        # Get recent mortality records
        mortality_data = []
        try:
            from flock_management.models import MortalityRecord
            
            mortalities = MortalityRecord.objects.filter(
                flock__farm=farm,
                date__gte=thirty_days_ago.date()
            ).order_by('-date')[:20]
            
            mortality_data = [{
                'id': str(m.id),
                'date': m.date.isoformat(),
                'flock_name': m.flock.name if m.flock else 'Unknown',
                'count': m.count,
                'cause': m.cause,
                'is_verified': getattr(m, 'is_verified', False),
            } for m in mortalities]
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Error fetching mortality data: {e}")
        
        # Calculate data quality score
        total_entries = len(production_data) + len(mortality_data)
        verified_entries = sum(1 for p in production_data if p.get('is_verified'))
        verified_entries += sum(1 for m in mortality_data if m.get('is_verified'))
        
        data_quality_score = (verified_entries / total_entries * 100) if total_entries > 0 else 0
        
        # Check for data gaps (missing days)
        data_gaps = self._find_data_gaps(production_data)
        
        return Response({
            'farm': {
                'id': str(farm.id),
                'farm_id': farm.farm_id,
                'farm_name': farm.farm_name,
                'farmer_name': farm.user.get_full_name() if farm.user else 'N/A',
            },
            'data_quality': {
                'score': round(data_quality_score, 1),
                'total_entries': total_entries,
                'verified_entries': verified_entries,
                'pending_verification': total_entries - verified_entries,
                'data_gaps': data_gaps,
            },
            'production_records': production_data,
            'mortality_records': mortality_data,
        })
    
    def post(self, request, farm_id):
        """Verify or flag data entries"""
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        farm = self._get_farm_if_accessible(user, farm_id)
        if not farm:
            return Response(
                {'error': 'Farm not found or access denied', 'code': 'FARM_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        action = request.data.get('action')  # 'verify' or 'flag'
        record_type = request.data.get('record_type')  # 'production' or 'mortality'
        record_ids = request.data.get('record_ids', [])
        notes = request.data.get('notes', '')
        
        if action not in ['verify', 'flag']:
            return Response(
                {'error': 'Invalid action. Use "verify" or "flag"', 'code': 'INVALID_ACTION'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not record_ids:
            return Response(
                {'error': 'No record_ids provided', 'code': 'NO_RECORDS'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process records
        processed = 0
        try:
            if record_type == 'production':
                from flock_management.models import DailyProduction
                for record_id in record_ids:
                    try:
                        record = DailyProduction.objects.get(id=record_id, flock__farm=farm)
                        if action == 'verify':
                            record.is_verified = True
                            record.verified_by = user
                            record.verified_at = timezone.now()
                        else:
                            record.is_flagged = True
                            record.flag_notes = notes
                            record.flagged_by = user
                        record.save()
                        processed += 1
                    except DailyProduction.DoesNotExist:
                        continue
            
            elif record_type == 'mortality':
                from flock_management.models import MortalityRecord
                for record_id in record_ids:
                    try:
                        record = MortalityRecord.objects.get(id=record_id, flock__farm=farm)
                        if action == 'verify':
                            record.is_verified = True
                            record.verified_by = user
                            record.verified_at = timezone.now()
                        else:
                            record.is_flagged = True
                            record.flag_notes = notes
                            record.flagged_by = user
                        record.save()
                        processed += 1
                    except MortalityRecord.DoesNotExist:
                        continue
        except ImportError:
            return Response(
                {'error': 'Flock management module not available', 'code': 'MODULE_NOT_FOUND'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'success': True,
            'action': action,
            'processed': processed,
            'total': len(record_ids),
            'message': f'{processed} records {action}ed successfully',
        })
    
    def _get_farm_if_accessible(self, user, farm_id):
        """Get farm if user has access"""
        try:
            farm = Farm.objects.get(id=farm_id)
            
            if user.role == 'CONSTITUENCY_OFFICIAL':
                if farm.primary_constituency == user.constituency:
                    return farm
            elif user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
                if (farm.extension_officer == user or 
                    farm.assigned_extension_officer == user or
                    farm.primary_constituency == user.constituency):
                    return farm
            
            return None
        except Farm.DoesNotExist:
            return None
    
    def _find_data_gaps(self, production_data):
        """Find missing dates in production data"""
        if not production_data:
            return []
        
        dates = sorted([p['date'] for p in production_data])
        gaps = []
        
        for i in range(len(dates) - 1):
            from datetime import datetime
            current = datetime.fromisoformat(dates[i]).date()
            next_date = datetime.fromisoformat(dates[i + 1]).date()
            diff = (next_date - current).days
            
            if diff > 1:
                gaps.append({
                    'start': dates[i],
                    'end': dates[i + 1],
                    'missing_days': diff - 1,
                })
        
        return gaps


class FarmerDataAssistanceView(APIView):
    """
    POST /api/extension/farms/{farm_id}/assist-entry/
    
    Help farmers enter data when they need assistance.
    Field officer can enter production/mortality data on behalf of farmer.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, farm_id):
        """Enter data on behalf of farmer"""
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        farm = self._get_farm_if_accessible(user, farm_id)
        if not farm:
            return Response(
                {'error': 'Farm not found or access denied', 'code': 'FARM_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        entry_type = request.data.get('entry_type')  # 'production' or 'mortality'
        data = request.data.get('data', {})
        
        if entry_type == 'production':
            return self._enter_production_data(farm, user, data)
        elif entry_type == 'mortality':
            return self._enter_mortality_data(farm, user, data)
        else:
            return Response(
                {'error': 'Invalid entry_type. Use "production" or "mortality"', 'code': 'INVALID_TYPE'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _enter_production_data(self, farm, officer, data):
        """Enter daily production data on behalf of farmer"""
        try:
            from flock_management.models import DailyProduction, Flock
            from datetime import datetime
            
            flock_id = data.get('flock_id')
            date = data.get('date', timezone.now().date().isoformat())
            
            # Get or validate flock
            if flock_id:
                flock = Flock.objects.get(id=flock_id, farm=farm)
            else:
                # Get active flock
                flock = Flock.objects.filter(farm=farm, is_active=True).first()
                if not flock:
                    return Response(
                        {'error': 'No active flock found for this farm', 'code': 'NO_ACTIVE_FLOCK'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Parse date
            if isinstance(date, str):
                date = datetime.fromisoformat(date).date()
            
            # Create production record
            production, created = DailyProduction.objects.update_or_create(
                flock=flock,
                date=date,
                defaults={
                    'eggs_collected': data.get('eggs_collected', 0),
                    'mortality_count': data.get('mortality_count', 0),
                    'feed_consumed_kg': data.get('feed_consumed_kg'),
                    'water_consumed_liters': data.get('water_consumed_liters'),
                    'notes': data.get('notes', ''),
                    # Mark as entered by field officer and auto-verified
                    'entered_by_officer': True,
                    'is_verified': True,
                    'verified_by': officer,
                    'verified_at': timezone.now(),
                }
            )
            
            return Response({
                'success': True,
                'message': 'Production data entered successfully',
                'created': created,
                'record': {
                    'id': str(production.id),
                    'date': date.isoformat(),
                    'flock': flock.name,
                    'eggs_collected': production.eggs_collected,
                },
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        except ImportError:
            return Response(
                {'error': 'Flock management module not available', 'code': 'MODULE_NOT_FOUND'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Flock.DoesNotExist:
            return Response(
                {'error': 'Flock not found', 'code': 'FLOCK_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error entering production data: {e}")
            return Response(
                {'error': f'Failed to enter data: {str(e)}', 'code': 'ENTRY_ERROR'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _enter_mortality_data(self, farm, officer, data):
        """Enter mortality data on behalf of farmer"""
        try:
            from flock_management.models import MortalityRecord, Flock
            from datetime import datetime
            
            flock_id = data.get('flock_id')
            date = data.get('date', timezone.now().date().isoformat())
            count = data.get('count', 0)
            cause = data.get('cause', '')
            
            if not count or count < 1:
                return Response(
                    {'error': 'Mortality count must be at least 1', 'code': 'INVALID_COUNT'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or validate flock
            if flock_id:
                flock = Flock.objects.get(id=flock_id, farm=farm)
            else:
                flock = Flock.objects.filter(farm=farm, is_active=True).first()
                if not flock:
                    return Response(
                        {'error': 'No active flock found for this farm', 'code': 'NO_ACTIVE_FLOCK'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Parse date
            if isinstance(date, str):
                date = datetime.fromisoformat(date).date()
            
            # Create mortality record
            mortality = MortalityRecord.objects.create(
                flock=flock,
                date=date,
                count=count,
                cause=cause,
                notes=data.get('notes', ''),
                # Mark as entered by field officer and auto-verified
                entered_by_officer=True,
                is_verified=True,
                verified_by=officer,
                verified_at=timezone.now(),
            )
            
            return Response({
                'success': True,
                'message': 'Mortality record entered successfully',
                'record': {
                    'id': str(mortality.id),
                    'date': date.isoformat(),
                    'flock': flock.name,
                    'count': count,
                    'cause': cause,
                },
            }, status=status.HTTP_201_CREATED)
            
        except ImportError:
            return Response(
                {'error': 'Flock management module not available', 'code': 'MODULE_NOT_FOUND'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Flock.DoesNotExist:
            return Response(
                {'error': 'Flock not found', 'code': 'FLOCK_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error entering mortality data: {e}")
            return Response(
                {'error': f'Failed to enter data: {str(e)}', 'code': 'ENTRY_ERROR'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_farm_if_accessible(self, user, farm_id):
        """Get farm if user has access"""
        try:
            farm = Farm.objects.get(id=farm_id)
            
            if user.role == 'CONSTITUENCY_OFFICIAL':
                if farm.primary_constituency == user.constituency:
                    return farm
            elif user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
                if (farm.extension_officer == user or 
                    farm.assigned_extension_officer == user or
                    farm.primary_constituency == user.constituency):
                    return farm
            
            return None
        except Farm.DoesNotExist:
            return None


class DataQualityDashboardView(APIView):
    """
    GET /api/extension/data-quality/
    
    Overview of data quality across all farms in jurisdiction.
    Helps field officers identify farms needing data assistance.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role not in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Field officer access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        farms = self._get_jurisdiction_farms(user)
        
        # Analyze data quality for each farm
        farm_quality = []
        thirty_days_ago = timezone.now() - timedelta(days=30)
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        try:
            from flock_management.models import DailyProduction, Flock
            
            for farm in farms[:50]:  # Limit to 50 farms for performance
                # Count recent entries
                recent_entries = DailyProduction.objects.filter(
                    flock__farm=farm,
                    date__gte=thirty_days_ago.date()
                ).count()
                
                # Count very recent entries (last 7 days)
                very_recent = DailyProduction.objects.filter(
                    flock__farm=farm,
                    date__gte=seven_days_ago.date()
                ).count()
                
                # Expected entries (1 per day per active flock)
                active_flocks = Flock.objects.filter(farm=farm, is_active=True).count()
                expected_entries = active_flocks * 30 if active_flocks > 0 else 30
                
                # Data completeness score
                completeness = (recent_entries / expected_entries * 100) if expected_entries > 0 else 0
                
                # Determine status
                if very_recent == 0:
                    status_label = 'no_recent_data'
                elif completeness < 50:
                    status_label = 'needs_attention'
                elif completeness < 80:
                    status_label = 'fair'
                else:
                    status_label = 'good'
                
                farm_quality.append({
                    'farm_id': str(farm.id),
                    'farm_name': farm.farm_name,
                    'farmer_name': farm.user.get_full_name() if farm.user else 'N/A',
                    'farmer_phone': str(farm.primary_phone),
                    'entries_last_30_days': recent_entries,
                    'entries_last_7_days': very_recent,
                    'expected_entries': expected_entries,
                    'completeness_score': round(completeness, 1),
                    'status': status_label,
                    'last_entry': self._get_last_entry_date(farm),
                })
        except ImportError:
            pass
        
        # Sort by completeness (worst first)
        farm_quality.sort(key=lambda x: x['completeness_score'])
        
        # Summary stats
        total_farms = len(farm_quality)
        needs_attention = sum(1 for f in farm_quality if f['status'] in ['no_recent_data', 'needs_attention'])
        good_farms = sum(1 for f in farm_quality if f['status'] == 'good')
        
        return Response({
            'summary': {
                'total_farms_analyzed': total_farms,
                'needs_attention': needs_attention,
                'fair_quality': total_farms - needs_attention - good_farms,
                'good_quality': good_farms,
                'average_completeness': round(
                    sum(f['completeness_score'] for f in farm_quality) / total_farms, 1
                ) if total_farms > 0 else 0,
            },
            'farms': farm_quality,
        })
    
    def _get_jurisdiction_farms(self, user):
        """Get farms based on user's role and jurisdiction"""
        if user.role == 'CONSTITUENCY_OFFICIAL':
            return Farm.objects.filter(
                primary_constituency=user.constituency,
                application_status='Approved'
            )
        elif user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER']:
            return Farm.objects.filter(
                Q(extension_officer=user) | 
                Q(assigned_extension_officer=user) |
                Q(primary_constituency=user.constituency),
                application_status='Approved'
            )
        return Farm.objects.none()
    
    def _get_last_entry_date(self, farm):
        """Get the date of the last production entry"""
        try:
            from flock_management.models import DailyProduction
            last = DailyProduction.objects.filter(flock__farm=farm).order_by('-date').first()
            return last.date.isoformat() if last else None
        except:
            return None
