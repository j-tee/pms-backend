"""
Authenticated Farm Management Views

Provides endpoints for farmers to manage their farm profiles:
- View and update farm profile
- Manage locations (GPS)
- Manage infrastructure (poultry houses)
- Manage equipment
- Upload documents
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Farm, FarmLocation, PoultryHouse, FarmDocument


class FarmProfileView(APIView):
    """
    GET /api/farms/profile/
    PUT /api/farms/profile/
    
    View or update the authenticated farmer's farm profile.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get farmer's farm profile"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Serialize farm data
        data = {
            'id': str(farm.id),
            'farm_name': farm.farm_name,
            'farm_id': farm.farm_id,
            'primary_production_type': farm.primary_production_type,
            'total_bird_capacity': farm.total_bird_capacity,
            'current_bird_count': farm.current_bird_count,
            'farm_status': farm.farm_status,
            'application_status': farm.application_status,
            'primary_constituency': farm.primary_constituency,
            # Contact
            'primary_phone': str(farm.primary_phone),
            'alternate_phone': str(farm.alternate_phone) if farm.alternate_phone else '',
            'email': farm.email,
            'residential_address': farm.residential_address,
            # Business
            'ownership_type': farm.ownership_type,
            'tin': farm.tin,
            'business_registration_number': farm.business_registration_number,
            # Infrastructure
            'number_of_poultry_houses': farm.number_of_poultry_houses,
            'housing_type': farm.housing_type,
            'total_infrastructure_value_ghs': float(farm.total_infrastructure_value_ghs),
            # Production
            'layer_breed': farm.layer_breed,
            'broiler_breed': farm.broiler_breed,
            'planned_production_start_date': farm.planned_production_start_date.isoformat(),
            # Financial
            'initial_investment_amount': float(farm.initial_investment_amount),
            'funding_source': farm.funding_source,
            'monthly_operating_budget': float(farm.monthly_operating_budget),
            'expected_monthly_revenue': float(farm.expected_monthly_revenue),
            # Personal
            'first_name': farm.first_name,
            'last_name': farm.last_name,
            'middle_name': farm.middle_name,
            'years_in_poultry': float(farm.years_in_poultry),
            'education_level': farm.education_level,
            'literacy_level': farm.literacy_level,
            'farming_full_time': farm.farming_full_time,
        }
        
        return Response(data)
    
    def put(self, request):
        """Update farm profile"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update allowed fields
        updatable_fields = [
            'alternate_phone', 'email', 'residential_address',
            'business_registration_number', 'layer_breed', 'broiler_breed',
            'bank_name', 'account_number', 'account_name',
            'mobile_money_provider', 'mobile_money_number',
            'monthly_operating_budget', 'expected_monthly_revenue',
        ]
        
        for field in updatable_fields:
            if field in request.data:
                setattr(farm, field, request.data[field])
        
        farm.save()
        
        return Response({'success': True, 'message': 'Farm profile updated successfully'})


class FarmLocationsView(APIView):
    """
    GET /api/farms/locations/
    POST /api/farms/locations/
    
    View or add farm locations.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all farm locations"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        locations = FarmLocation.objects.filter(farm=farm)
        data = [{
            'id': str(loc.id),
            'gps_address_string': loc.gps_address_string,
            'latitude': float(loc.latitude),
            'longitude': float(loc.longitude),
            'region': loc.region,
            'district': loc.district,
            'constituency': loc.constituency,
            'community': loc.community,
            'land_size_acres': float(loc.land_size_acres),
            'land_ownership_status': loc.land_ownership_status,
            'is_primary_location': loc.is_primary_location,
            'road_accessibility': loc.road_accessibility,
            'nearest_landmark': loc.nearest_landmark,
        } for loc in locations]
        
        return Response(data)
    
    def post(self, request):
        """Add new farm location using Ghana Post GPS address"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        gps_address = request.data.get('gps_address_string')
        if not gps_address:
            return Response(
                {'error': 'Ghana Post GPS address is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse Ghana Post GPS to get coordinates
        # Format: AK-0123-4567 or similar
        # In production, you would call Ghana Post GPS API to get exact coordinates
        # For now, we'll use a simple placeholder
        from django.contrib.gis.geos import Point
        
        # Placeholder coordinates (center of Ghana)
        # TODO: Integrate with Ghana Post GPS API to get actual coordinates
        lat = 7.9465  # Default latitude
        lon = -1.0232  # Default longitude
        
        location = FarmLocation.objects.create(
            farm=farm,
            gps_address_string=gps_address,
            location=Point(lon, lat),
            region=request.data.get('region', ''),
            district=request.data.get('district', ''),
            constituency=request.data.get('constituency', ''),
            community=request.data.get('community', ''),
            land_size_acres=request.data.get('land_size_acres', 0),
            land_ownership_status=request.data.get('land_ownership_status', 'Owned'),
            road_accessibility=request.data.get('road_accessibility', 'All Year'),
            nearest_landmark=request.data.get('nearest_landmark', ''),
        )
        
        return Response({
            'success': True,
            'message': 'Location added successfully',
            'location_id': str(location.id)
        }, status=status.HTTP_201_CREATED)


class FarmInfrastructureView(APIView):
    """
    GET /api/farms/infrastructure/
    POST /api/farms/infrastructure/
    
    View or add poultry houses.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all poultry houses"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        houses = PoultryHouse.objects.filter(farm=farm)
        data = [{
            'id': str(house.id),
            'house_number': house.house_number,
            'house_type': house.house_type,
            'house_capacity': house.house_capacity,
            'current_occupancy': house.current_occupancy,
            'length_meters': float(house.length_meters),
            'width_meters': float(house.width_meters),
            'height_meters': float(house.height_meters) if house.height_meters else None,
        } for house in houses]
        
        return Response(data)
    
    def post(self, request):
        """Add new poultry house"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        house = PoultryHouse.objects.create(
            farm=farm,
            house_number=request.data.get('house_number'),
            house_type=request.data.get('house_type'),
            house_capacity=request.data.get('house_capacity'),
            current_occupancy=request.data.get('current_occupancy', 0),
            length_meters=request.data.get('length_meters'),
            width_meters=request.data.get('width_meters'),
            height_meters=request.data.get('height_meters'),
        )
        
        return Response({
            'success': True,
            'message': 'Poultry house added successfully',
            'house_id': str(house.id)
        }, status=status.HTTP_201_CREATED)


class FarmEquipmentView(APIView):
    """
    GET /api/farms/equipment/
    
    View farm equipment (to be implemented with proper model).
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get farm equipment"""
        # Placeholder - equipment model needs to be implemented
        return Response([])


class FarmDocumentsView(APIView):
    """
    GET /api/farms/documents/
    POST /api/farms/documents/
    
    View or upload farm documents.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all farm documents"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        documents = FarmDocument.objects.filter(farm=farm)
        data = [{
            'id': str(doc.id),
            'document_type': doc.document_type,
            'document_name': doc.document_name,
            'file_path': doc.file_path,
            'uploaded_at': doc.uploaded_at.isoformat(),
            'status': doc.status,
        } for doc in documents]
        
        return Response(data)
    
    def post(self, request):
        """Upload new document"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Handle file upload
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document = FarmDocument.objects.create(
            farm=farm,
            document_type=request.data.get('document_type'),
            document_name=request.data.get('document_name', file.name),
            file_path=file,  # Django will handle file storage
            status='pending_verification',
        )
        
        return Response({
            'success': True,
            'message': 'Document uploaded successfully',
            'document_id': str(document.id)
        }, status=status.HTTP_201_CREATED)
