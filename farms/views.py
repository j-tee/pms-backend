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
from django.db.models import Q
from datetime import datetime
import logging
import os

from .models import Farm, FarmLocation, Infrastructure, FarmDocument, FarmEquipment

logger = logging.getLogger(__name__)


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
        """
        Add new farm location using Ghana Post GPS address.
        
        Farmers only need to provide their Ghana Post GPS address (e.g., GA-184-2278).
        The system automatically extracts latitude/longitude from the GPS address
        using the ghanapostgps library (no API required).
        """
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        gps_address = request.data.get('gps_address_string', '').strip().upper()
        if not gps_address:
            return Response(
                {'error': 'Ghana Post GPS address is required (e.g., GA-184-2278)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Decode GPS address to coordinates using ghanapostgps library
        # This works offline, no API needed
        from django.contrib.gis.geos import Point
        from farms.services.gps_service import GhanaPostGPSService
        
        try:
            # Decode GPS address locally
            location_data = GhanaPostGPSService.get_coordinates(gps_address)
            lat = location_data['latitude']
            lon = location_data['longitude']
            
            # Auto-populate region from GPS address if not provided
            region = request.data.get('region') or location_data.get('region', '')
            
        except ValueError as e:
            # Invalid GPS address format or decoding error
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Unexpected error - use fallback coordinates and log
            logger.error(f"GPS decoding failed for {gps_address}: {e}")
            lat, lon = GhanaPostGPSService.get_fallback_coordinates()
            region = request.data.get('region', '')
        
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


class UnifiedInfrastructureView(APIView):
    """
    Unified Infrastructure Management (Housing + Support Systems)
    
    Poultry houses use infrastructure_type='Accommodation' with housing_system field.
    Frontend filters by checking if infrastructure_type === 'Accommodation'.
    
    GET /api/farms/infrastructure/ - List all infrastructure
    GET /api/farms/infrastructure/<id>/ - Get specific infrastructure
    POST /api/farms/infrastructure/ - Create new infrastructure
    PUT /api/farms/infrastructure/<id>/ - Update infrastructure
    DELETE /api/farms/infrastructure/<id>/ - Delete infrastructure
    """
    permission_classes = [IsAuthenticated]
    
    def _serialize_infrastructure(self, infra):
        """Serialize infrastructure to unified format"""
        data = {
            'id': str(infra.id),
            'infrastructure_type': infra.infrastructure_type,
            'infrastructure_name': infra.infrastructure_name,
            'description': infra.description,
            'status': infra.status,
            'condition': infra.condition,
            'created_at': infra.created_at.isoformat(),
            'updated_at': infra.updated_at.isoformat(),
        }
        
        # Add housing-specific fields if type is Accommodation
        if infra.is_accommodation:
            data.update({
                'bird_capacity': infra.bird_capacity,
                'housing_system': infra.housing_system,
                'current_occupancy': infra.current_occupancy,
                'length_meters': float(infra.length_meters) if infra.length_meters else None,
                'width_meters': float(infra.width_meters) if infra.width_meters else None,
                'height_meters': float(infra.height_meters) if infra.height_meters else None,
            })
        else:
            # Add support system fields
            data.update({
                'bird_capacity': infra.bird_capacity,
                'capacity': infra.capacity,
                'supplier': infra.supplier,
                'installation_date': infra.installation_date.isoformat() if infra.installation_date else None,
                'warranty_expiry': infra.warranty_expiry.isoformat() if infra.warranty_expiry else None,
            })
        
        # Common fields for all types
        data.update({
            'condition_notes': infra.condition_notes,
            'maintenance_frequency': infra.maintenance_frequency,
            'last_maintenance_date': infra.last_maintenance_date.isoformat() if infra.last_maintenance_date else None,
            'next_maintenance_due': infra.next_maintenance_due.isoformat() if infra.next_maintenance_due else None,
            'notes': infra.notes,
        })
        
        return data
    
    def get(self, request, infrastructure_id=None):
        """Get all infrastructure or specific item by ID"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if infrastructure_id:
            # Get specific infrastructure item
            try:
                infra = Infrastructure.objects.get(id=infrastructure_id, farm=farm)
                return Response({
                    'message': 'Infrastructure retrieved successfully',
                    'infrastructure': self._serialize_infrastructure(infra)
                })
            except Infrastructure.DoesNotExist:
                return Response(
                    {'error': 'Infrastructure not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # List all infrastructure (housing + support systems)
            infrastructures = Infrastructure.objects.filter(farm=farm)
            houses_data = [self._serialize_infrastructure(infra) for infra in infrastructures]
            
            return Response({
                'message': 'Infrastructure retrieved successfully',
                'houses': houses_data,
                'total_houses': infrastructures.count()
            })
    
    def post(self, request):
        """Create new infrastructure (housing or support system)"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Required fields
        infrastructure_type = request.data.get('infrastructure_type')
        infrastructure_name = request.data.get('infrastructure_name')
        
        if not infrastructure_type:
            return Response({'error': 'infrastructure_type is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not infrastructure_name:
            return Response({'error': 'infrastructure_name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create infrastructure
        infra_data = {
            'farm': farm,
            'infrastructure_type': infrastructure_type,
            'infrastructure_name': infrastructure_name,
            'description': request.data.get('description', ''),
            'status': request.data.get('status', 'Operational'),
            'condition': request.data.get('condition', 'Good'),
        }
        
        # Add housing fields if type is Accommodation
        if infrastructure_type == 'Accommodation':
            infra_data.update({
                'bird_capacity': request.data.get('bird_capacity'),
                'housing_system': request.data.get('housing_system'),
                'current_occupancy': request.data.get('current_occupancy', 0),
                'length_meters': request.data.get('length_meters'),
                'width_meters': request.data.get('width_meters'),
                'height_meters': request.data.get('height_meters'),
            })
            
            # Validate bird_capacity is required for Accommodation
            if not infra_data.get('bird_capacity'):
                return Response(
                    {'error': 'bird_capacity is required for Accommodation'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Add support system fields
            from datetime import datetime
            
            # Parse dates if provided
            installation_date = request.data.get('installation_date')
            if installation_date:
                installation_date = datetime.fromisoformat(installation_date.replace('Z', '+00:00')).date()
            
            warranty_expiry = request.data.get('warranty_expiry')
            if warranty_expiry:
                warranty_expiry = datetime.fromisoformat(warranty_expiry.replace('Z', '+00:00')).date()
            
            last_maintenance_date = request.data.get('last_maintenance_date')
            if last_maintenance_date:
                last_maintenance_date = datetime.fromisoformat(last_maintenance_date.replace('Z', '+00:00')).date()
            
            next_maintenance_due = request.data.get('next_maintenance_due')
            if next_maintenance_due:
                next_maintenance_due = datetime.fromisoformat(next_maintenance_due.replace('Z', '+00:00')).date()
            
            infra_data.update({
                'bird_capacity': request.data.get('bird_capacity'),
                'capacity': request.data.get('capacity', ''),
                'supplier': request.data.get('supplier', ''),
                'installation_date': installation_date,
                'warranty_expiry': warranty_expiry,
                'condition_notes': request.data.get('condition_notes', ''),
                'maintenance_frequency': request.data.get('maintenance_frequency', 'As Needed'),
                'last_maintenance_date': last_maintenance_date,
                'next_maintenance_due': next_maintenance_due,
                'notes': request.data.get('notes', ''),
            })
        
        infrastructure = Infrastructure.objects.create(**infra_data)
        
        return Response({
            'success': True,
            'message': f'{"Accommodation" if infrastructure.is_accommodation else "Infrastructure"} created successfully',
            'house_id': str(infrastructure.id),
            'infrastructure': self._serialize_infrastructure(infrastructure)
        }, status=status.HTTP_201_CREATED)
    
    def put(self, request, infrastructure_id):
        """Update existing infrastructure"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            infra = Infrastructure.objects.get(id=infrastructure_id, farm=farm)
        except Infrastructure.DoesNotExist:
            return Response(
                {'error': 'Infrastructure not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update basic fields
        if 'infrastructure_type' in request.data:
            infra.infrastructure_type = request.data['infrastructure_type']
        if 'infrastructure_name' in request.data:
            infra.infrastructure_name = request.data['infrastructure_name']
        if 'description' in request.data:
            infra.description = request.data['description']
        if 'status' in request.data:
            infra.status = request.data['status']
        if 'condition' in request.data:
            infra.condition = request.data['condition']
        
        # Update type-specific fields
        if infra.is_accommodation:
            housing_fields = [
                'bird_capacity', 'housing_system', 'current_occupancy', 'length_meters', 
                'width_meters', 'height_meters'
            ]
            for field in housing_fields:
                if field in request.data:
                    setattr(infra, field, request.data[field])
        else:
            # Update support system fields
            from datetime import datetime
            
            if 'installation_date' in request.data and request.data['installation_date']:
                infra.installation_date = datetime.fromisoformat(request.data['installation_date'].replace('Z', '+00:00')).date()
            if 'warranty_expiry' in request.data and request.data['warranty_expiry']:
                infra.warranty_expiry = datetime.fromisoformat(request.data['warranty_expiry'].replace('Z', '+00:00')).date()
            if 'last_maintenance_date' in request.data and request.data['last_maintenance_date']:
                infra.last_maintenance_date = datetime.fromisoformat(request.data['last_maintenance_date'].replace('Z', '+00:00')).date()
            if 'next_maintenance_due' in request.data and request.data['next_maintenance_due']:
                infra.next_maintenance_due = datetime.fromisoformat(request.data['next_maintenance_due'].replace('Z', '+00:00')).date()
            
            system_fields = [
                'bird_capacity', 'capacity', 'supplier', 'condition_notes', 
                'maintenance_frequency', 'notes'
            ]
            for field in system_fields:
                if field in request.data:
                    setattr(infra, field, request.data[field])
        
        infra.save()
        
        return Response({
            'message': 'Infrastructure updated successfully',
            'infrastructure': self._serialize_infrastructure(infra)
        })
    
    def delete(self, request, infrastructure_id):
        """Delete infrastructure (with active flock check for housing)"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            infra = Infrastructure.objects.get(id=infrastructure_id, farm=farm)
        except Infrastructure.DoesNotExist:
            return Response(
                {'error': 'Infrastructure not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # If accommodation, check for active flocks
        if infra.is_accommodation:
            from flock_management.models import Flock
            active_flocks = Flock.objects.filter(
                housed_in=infra,
                is_active=True
            ).count()
            
            if active_flocks > 0:
                return Response(
                    {'error': f'Cannot delete housing. It has {active_flocks} active flock(s). Please deactivate or move the flocks first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        item_name = infra.infrastructure_name
        infra.delete()
        
        return Response({
            'message': f'Infrastructure "{item_name}" deleted successfully'
        })




class FarmEquipmentView(APIView):
    """
    GET /api/farms/equipment/
    POST /api/farms/equipment/
    PUT /api/farms/equipment/<id>/
    DELETE /api/farms/equipment/<id>/
    
    Manage farm equipment (movable, operational items like feeders, drinkers, etc.)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, equipment_id=None):
        """
        Get farm equipment
        - GET /api/farms/equipment/ - List all equipment
        - GET /api/farms/equipment/<id>/ - Get specific equipment
        
        Query parameters:
        - type: Filter by equipment type
        - status: Filter by status
        - location: Filter by location
        """
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if equipment_id:
            # Get specific equipment item
            equipment = get_object_or_404(FarmEquipment, id=equipment_id, farm=farm)
            data = self._serialize_equipment(equipment)
            return Response(data)
        
        # Get all equipment for the farm
        equipment_list = FarmEquipment.objects.filter(farm=farm)
        
        # Apply filters
        equipment_type = request.query_params.get('type')
        equipment_status = request.query_params.get('status')
        location = request.query_params.get('location')
        
        if equipment_type:
            equipment_list = equipment_list.filter(equipment_type=equipment_type)
        if equipment_status:
            equipment_list = equipment_list.filter(status=equipment_status)
        if location:
            equipment_list = equipment_list.filter(location__icontains=location)
        
        data = [self._serialize_equipment(eq) for eq in equipment_list]
        return Response(data)
    
    def post(self, request):
        """Create new equipment"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate required fields
        equipment_name = request.data.get('equipment_name')
        equipment_type = request.data.get('equipment_type')
        
        if not equipment_name:
            return Response(
                {'error': 'Equipment name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not equipment_type:
            return Response(
                {'error': 'Equipment type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate equipment type
        valid_types = [choice[0] for choice in FarmEquipment.EQUIPMENT_TYPES]
        if equipment_type not in valid_types:
            return Response(
                {'error': f'Invalid equipment type. Allowed types: {", ".join(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate quantity
        quantity = request.data.get('quantity', 1)
        try:
            quantity = int(quantity)
            if quantity < 1:
                return Response(
                    {'error': 'Quantity must be at least 1'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid quantity value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate status
        equipment_status = request.data.get('status', 'Available')
        valid_statuses = [choice[0] for choice in FarmEquipment.STATUS_CHOICES]
        if equipment_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Allowed values: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate condition
        condition = request.data.get('condition', 'Good')
        valid_conditions = [choice[0] for choice in FarmEquipment.CONDITION_CHOICES]
        if condition not in valid_conditions:
            return Response(
                {'error': f'Invalid condition. Allowed values: {", ".join(valid_conditions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse dates
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f'Invalid date format: {date_str}. Expected YYYY-MM-DD')
        
        try:
            purchase_date = parse_date(request.data.get('purchase_date'))
            last_maintenance_date = parse_date(request.data.get('last_maintenance_date'))
            next_maintenance_due = parse_date(request.data.get('next_maintenance_due'))
            warranty_expiry = parse_date(request.data.get('warranty_expiry'))
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create equipment
        equipment = FarmEquipment.objects.create(
            farm=farm,
            created_by=request.user,
            equipment_name=equipment_name,
            equipment_type=equipment_type,
            brand=request.data.get('brand', ''),
            model=request.data.get('model', ''),
            serial_number=request.data.get('serial_number', ''),
            quantity=quantity,
            status=equipment_status,
            condition=condition,
            location=request.data.get('location', ''),
            supplier=request.data.get('supplier', ''),
            purchase_date=purchase_date,
            purchase_price_ghs=request.data.get('purchase_price_ghs'),
            current_value_ghs=request.data.get('current_value_ghs'),
            last_maintenance_date=last_maintenance_date,
            next_maintenance_due=next_maintenance_due,
            warranty_expiry=warranty_expiry,
            notes=request.data.get('notes', '')
        )
        
        return Response(
            {
                'success': True,
                'message': 'Equipment added successfully',
                'equipment_id': str(equipment.id)
            },
            status=status.HTTP_201_CREATED
        )
    
    def put(self, request, equipment_id):
        """Update equipment"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            equipment = FarmEquipment.objects.get(id=equipment_id, farm=farm)
        except FarmEquipment.DoesNotExist:
            return Response(
                {'error': 'Equipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update fields (partial update supported)
        if 'equipment_name' in request.data:
            equipment.equipment_name = request.data['equipment_name']
        
        if 'equipment_type' in request.data:
            equipment_type = request.data['equipment_type']
            valid_types = [choice[0] for choice in FarmEquipment.EQUIPMENT_TYPES]
            if equipment_type not in valid_types:
                return Response(
                    {'error': f'Invalid equipment type. Allowed types: {", ".join(valid_types)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            equipment.equipment_type = equipment_type
        
        if 'brand' in request.data:
            equipment.brand = request.data['brand']
        if 'model' in request.data:
            equipment.model = request.data['model']
        if 'serial_number' in request.data:
            equipment.serial_number = request.data['serial_number']
        
        if 'quantity' in request.data:
            try:
                quantity = int(request.data['quantity'])
                if quantity < 1:
                    return Response(
                        {'error': 'Quantity must be at least 1'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                equipment.quantity = quantity
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid quantity value'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if 'status' in request.data:
            equipment_status = request.data['status']
            valid_statuses = [choice[0] for choice in FarmEquipment.STATUS_CHOICES]
            if equipment_status not in valid_statuses:
                return Response(
                    {'error': f'Invalid status. Allowed values: {", ".join(valid_statuses)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            equipment.status = equipment_status
        
        if 'condition' in request.data:
            condition = request.data['condition']
            valid_conditions = [choice[0] for choice in FarmEquipment.CONDITION_CHOICES]
            if condition not in valid_conditions:
                return Response(
                    {'error': f'Invalid condition. Allowed values: {", ".join(valid_conditions)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            equipment.condition = condition
        
        if 'location' in request.data:
            equipment.location = request.data['location']
        if 'supplier' in request.data:
            equipment.supplier = request.data['supplier']
        if 'notes' in request.data:
            equipment.notes = request.data['notes']
        
        # Parse and update dates
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f'Invalid date format: {date_str}. Expected YYYY-MM-DD')
        
        try:
            if 'purchase_date' in request.data:
                equipment.purchase_date = parse_date(request.data['purchase_date'])
            if 'last_maintenance_date' in request.data:
                equipment.last_maintenance_date = parse_date(request.data['last_maintenance_date'])
            if 'next_maintenance_due' in request.data:
                equipment.next_maintenance_due = parse_date(request.data['next_maintenance_due'])
            if 'warranty_expiry' in request.data:
                equipment.warranty_expiry = parse_date(request.data['warranty_expiry'])
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update prices
        if 'purchase_price_ghs' in request.data:
            equipment.purchase_price_ghs = request.data['purchase_price_ghs']
        if 'current_value_ghs' in request.data:
            equipment.current_value_ghs = request.data['current_value_ghs']
        
        equipment.save()
        
        return Response(
            {
                'success': True,
                'message': 'Equipment updated successfully'
            }
        )
    
    def delete(self, request, equipment_id):
        """Delete equipment"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            equipment = FarmEquipment.objects.get(id=equipment_id, farm=farm)
        except FarmEquipment.DoesNotExist:
            return Response(
                {'error': 'Equipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        equipment.delete()
        
        return Response(
            {
                'success': True,
                'message': 'Equipment deleted successfully'
            }
        )
    
    def _serialize_equipment(self, equipment):
        """Serialize equipment object to dict"""
        return {
            'id': str(equipment.id),
            'farm_id': str(equipment.farm.id),
            'equipment_name': equipment.equipment_name,
            'equipment_type': equipment.equipment_type,
            'brand': equipment.brand,
            'model': equipment.model,
            'serial_number': equipment.serial_number,
            'quantity': equipment.quantity,
            'status': equipment.status,
            'condition': equipment.condition,
            'location': equipment.location,
            'supplier': equipment.supplier,
            'purchase_date': equipment.purchase_date.isoformat() if equipment.purchase_date else None,
            'purchase_price_ghs': float(equipment.purchase_price_ghs) if equipment.purchase_price_ghs else None,
            'current_value_ghs': float(equipment.current_value_ghs) if equipment.current_value_ghs else None,
            'last_maintenance_date': equipment.last_maintenance_date.isoformat() if equipment.last_maintenance_date else None,
            'next_maintenance_due': equipment.next_maintenance_due.isoformat() if equipment.next_maintenance_due else None,
            'is_maintenance_overdue': equipment.is_maintenance_overdue,
            'days_until_maintenance': equipment.days_until_maintenance,
            'warranty_expiry': equipment.warranty_expiry.isoformat() if equipment.warranty_expiry else None,
            'is_under_warranty': equipment.is_under_warranty,
            'notes': equipment.notes,
            'created_at': equipment.created_at.isoformat(),
            'updated_at': equipment.updated_at.isoformat(),
        }


class FarmDocumentsView(APIView):
    """
    GET /api/farms/documents/
    POST /api/farms/documents/
    DELETE /api/farms/documents/{document_id}/
    
    Simple document management aligned with EOI application structure.
    Only accepts: file + document_type
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, document_id=None):
        """Get all farm documents or download specific document"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Download specific document
        if document_id:
            try:
                document = FarmDocument.objects.get(id=document_id, farm=farm)
                
                # Return file for download
                from django.http import FileResponse
                import os
                
                file_path = document.file.path
                if os.path.exists(file_path):
                    response = FileResponse(
                        open(file_path, 'rb'),
                        content_type=document.mime_type
                    )
                    response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
                    return response
                else:
                    return Response(
                        {'error': 'File not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            except FarmDocument.DoesNotExist:
                return Response(
                    {'error': 'Document not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # List all documents
        documents = FarmDocument.objects.filter(farm=farm)
        data = [{
            'id': str(doc.id),
            'document_type': doc.document_type,
            'file_name': doc.file_name,
            'mime_type': doc.mime_type,
            'file_size': doc.file_size,
            'url': request.build_absolute_uri(doc.file.url) if doc.file else None,
            'uploaded_at': doc.uploaded_at.isoformat(),
            'is_verified': doc.is_verified,
        } for doc in documents]
        
        return Response(data)
    
    def post(self, request):
        """Upload new document (only file + document_type required)"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate required fields
        file = request.FILES.get('file')
        document_type = request.data.get('document_type')
        
        if not file:
            return Response(
                {'error': 'File is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not document_type:
            return Response(
                {'error': 'Document type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate document type
        valid_types = [choice[0] for choice in FarmDocument._meta.get_field('document_type').choices]
        if document_type not in valid_types:
            return Response(
                {'error': f'Invalid document type. Must be one of: {", ".join(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check limit for farm product photos (max 20)
        if document_type == 'Farm Photo - Products':
            existing_count = FarmDocument.objects.filter(
                farm=farm,
                document_type='Farm Photo - Products'
            ).count()
            
            if existing_count >= 20:
                return Response(
                    {'error': 'Maximum of 20 product photos allowed. Please delete some existing photos before uploading new ones.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate file size (10MB max)
        max_size = 10 * 1024 * 1024  # 10MB
        if file.size > max_size:
            return Response(
                {'error': f'File size exceeds maximum allowed size of 10MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
        file_ext = os.path.splitext(file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return Response(
                {'error': f'File type not allowed. Allowed: {", ".join(allowed_extensions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine MIME type
        mime_mapping = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
        }
        mime_type = mime_mapping.get(file_ext, 'application/octet-stream')
        
        # Create document
        try:
            document = FarmDocument.objects.create(
                farm=farm,
                document_type=document_type,
                file=file,
                file_name=file.name,
                file_size=file.size,
                mime_type=mime_type,
                is_verified=False,
            )
            
            return Response({
                'success': True,
                'message': 'Document uploaded successfully',
                'document_id': str(document.id)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to upload document: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, document_id):
        """Delete a document"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            document = FarmDocument.objects.get(id=document_id, farm=farm)
            
            # Delete the file from storage
            if document.file:
                document.file.delete()
            
            # Delete the database record
            document.delete()
            
            return Response({
                'success': True,
                'message': 'Document deleted successfully'
            })
            
        except FarmDocument.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
