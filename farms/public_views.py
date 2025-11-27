"""
Public Farm Application Views

Handles public-facing farm application submission (no authentication required).
Prospective farmers can apply without creating an account first.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone

from farms.services.application_screening import ApplicationScreeningService
from farms.application_models import FarmApplication
from farms.batch_enrollment_models import Batch


class SubmitFarmApplicationView(APIView):
    """
    Submit farm application (public - no authentication required)
    
    POST /api/applications/submit/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Submit a new farm application"""
        # Get client IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Extract application data
        application_data = {
            'application_type': request.data.get('application_type', 'government_program'),
            'first_name': request.data.get('first_name'),
            'middle_name': request.data.get('middle_name', ''),
            'last_name': request.data.get('last_name'),
            'date_of_birth': request.data.get('date_of_birth'),
            'gender': request.data.get('gender'),
            'ghana_card_number': request.data.get('ghana_card_number'),
            'primary_phone': request.data.get('primary_phone'),
            'alternate_phone': request.data.get('alternate_phone', ''),
            'email': request.data.get('email', ''),
            'residential_address': request.data.get('residential_address'),
            'primary_constituency': request.data.get('primary_constituency'),
            'region': request.data.get('region'),
            'district': request.data.get('district'),
            'proposed_farm_name': request.data.get('proposed_farm_name'),
            'farm_location_description': request.data.get('farm_location_description'),
            'land_size_acres': request.data.get('land_size_acres'),
            'primary_production_type': request.data.get('primary_production_type'),
            'planned_bird_capacity': request.data.get('planned_bird_capacity'),
            'years_in_poultry': request.data.get('years_in_poultry', 0),
            'has_existing_farm': request.data.get('has_existing_farm', False),
            'yea_program_batch': request.data.get('yea_program_batch', ''),
            'referral_source': request.data.get('referral_source', ''),
        }
        
        # Validate required fields
        required_fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 
            'ghana_card_number', 'primary_phone', 'residential_address',
            'primary_constituency', 'region', 'district',
            'proposed_farm_name', 'farm_location_description',
            'primary_production_type', 'planned_bird_capacity'
        ]
        
        missing_fields = [field for field in required_fields if not application_data.get(field)]
        if missing_fields:
            return Response({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Submit application
        try:
            success, message, application = ApplicationScreeningService.submit_application(
                application_data=application_data,
                ip_address=ip_address
            )
            
            if not success:
                return Response({
                    'error': message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Return submitted application data for review page
            return Response({
                'success': True,
                'message': message,
                'application': {
                    'application_number': application.application_number,
                    'application_type': application.application_type,
                    'full_name': application.full_name,
                    'first_name': application.first_name,
                    'middle_name': application.middle_name,
                    'last_name': application.last_name,
                    'date_of_birth': str(application.date_of_birth) if application.date_of_birth else None,
                    'gender': application.gender,
                    'ghana_card_number': application.ghana_card_number,
                    'primary_phone': str(application.primary_phone) if application.primary_phone else None,
                    'alternate_phone': str(application.alternate_phone) if application.alternate_phone else None,
                    'email': application.email,
                    'residential_address': application.residential_address,
                    'primary_constituency': application.primary_constituency,
                    'region': application.region,
                    'district': application.district,
                    'proposed_farm_name': application.proposed_farm_name,
                    'farm_location_description': application.farm_location_description,
                    'land_size_acres': str(application.land_size_acres) if application.land_size_acres else None,
                    'primary_production_type': application.primary_production_type,
                    'planned_bird_capacity': application.planned_bird_capacity,
                    'years_in_poultry': str(application.years_in_poultry),
                    'has_existing_farm': application.has_existing_farm,
                    'yea_program_batch': application.yea_program_batch,
                    'referral_source': application.referral_source,
                    'status': application.status,
                    'submitted_at': application.submitted_at.isoformat() if application.submitted_at else None,
                },
                'track_url': f'/api/applications/track/{application.ghana_card_number}/',
                'next_steps': {
                    'constituency_review': '7 days',
                    'regional_review': '5 days',
                    'national_review': '3 days'
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': 'An error occurred while processing your application',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrackApplicationView(APIView):
    """
    Track application status by Ghana Card number
    
    GET /api/applications/track/{ghana_card_number}/
    """
    permission_classes = [AllowAny]
    
    def get(self, request, ghana_card_number):
        """Get application status"""
        try:
            application = FarmApplication.objects.filter(
                ghana_card_number=ghana_card_number
            ).order_by('-submitted_at').first()
            
            if not application:
                return Response({
                    'error': 'No application found for this Ghana Card number'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'application_number': application.application_number,
                'full_name': application.full_name,
                'proposed_farm_name': application.proposed_farm_name,
                'status': application.status,
                'current_review_level': application.current_review_level,
                'submitted_at': application.submitted_at.isoformat() if application.submitted_at else None,
                'constituency_approved_at': application.constituency_approved_at.isoformat() if application.constituency_approved_at else None,
                'regional_approved_at': application.regional_approved_at.isoformat() if application.regional_approved_at else None,
                'final_approved_at': application.final_approved_at.isoformat() if application.final_approved_at else None,
                'rejection_reason': application.rejection_reason if application.status == 'rejected' else None,
                'changes_requested': application.changes_requested if application.status == 'changes_requested' else None,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'An error occurred while fetching application status',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ApplicationStatisticsView(APIView):
    """
    Public statistics about farm applications
    
    GET /api/applications/statistics/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get application statistics"""
        try:
            total_applications = FarmApplication.objects.count()
            approved_applications = FarmApplication.objects.filter(status='approved').count()
            pending_applications = FarmApplication.objects.filter(
                status__in=['constituency_review', 'regional_review', 'national_review']
            ).count()
            
            return Response({
                'total_applications': total_applications,
                'approved_applications': approved_applications,
                'pending_applications': pending_applications,
                'success_rate': f"{(approved_applications / total_applications * 100):.1f}%" if total_applications > 0 else "0%"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'An error occurred while fetching statistics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicBatchListView(APIView):
    """
    List public batches for application selection
    
    GET /api/public/batches/?is_active=true&is_published=true
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get list of active, published batches"""
        try:
            # Get query parameters
            is_active = request.query_params.get('is_active', '').lower() == 'true'
            is_published = request.query_params.get('is_published', '').lower() == 'true'
            accepts_applications = request.query_params.get('accepts_applications', '').lower() == 'true'
            
            # Build query
            queryset = Batch.objects.all()
            
            if is_active:
                queryset = queryset.filter(is_active=True)
            
            if is_published:
                queryset = queryset.filter(is_published=True)
            
            if accepts_applications:
                queryset = queryset.filter(accepts_applications=True)
            
            # Order by most recent
            queryset = queryset.order_by('-created_at')
            
            # Serialize batches
            batches = []
            for batch in queryset:
                # Check if batch accepts applications
                accepts_apps = batch.status == 'open' and batch.is_active and batch.slots_available > 0
                
                batches.append({
                    'id': str(batch.id),
                    'batch_name': batch.batch_name,
                    'batch_code': batch.batch_code,
                    'description': batch.description,
                    'long_description': batch.long_description,
                    'target_region': batch.target_region,
                    'implementing_agency': batch.implementing_agency,
                    'total_slots': batch.total_slots,
                    'slots_filled': batch.slots_filled,
                    'slots_available': batch.slots_available,
                    'start_date': batch.start_date.isoformat() if batch.start_date else None,
                    'end_date': batch.end_date.isoformat() if batch.end_date else None,
                    'application_deadline': batch.application_deadline.isoformat() if batch.application_deadline else None,
                    'early_application_deadline': batch.early_application_deadline.isoformat() if batch.early_application_deadline else None,
                    'is_active': batch.is_active,
                    'is_published': batch.is_published,
                    'accepts_applications': accepts_apps,
                    'status': batch.status,
                    'support_package_details': batch.support_package_details,
                    'support_package_value_ghs': str(batch.support_package_value_ghs) if batch.support_package_value_ghs else None,
                    'beneficiary_contribution_ghs': str(batch.beneficiary_contribution_ghs) if batch.beneficiary_contribution_ghs else None,
                    'min_bird_capacity': batch.min_bird_capacity,
                    'max_bird_capacity': batch.max_bird_capacity,
                    'eligible_farmer_age_min': batch.eligible_farmer_age_min,
                    'eligible_farmer_age_max': batch.eligible_farmer_age_max,
                })
            
            return Response({
                'count': len(batches),
                'results': batches
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'An error occurred while fetching batches',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
