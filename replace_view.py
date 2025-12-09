# Replace UnifiedInfrastructureView with simpler version

new_view = '''class UnifiedInfrastructureView(APIView):
    """
    Unified Infrastructure Management (Housing + Support Systems)
    
    Housing types include 'Housing' suffix (e.g., 'Deep Litter Housing').
    Frontend filters by checking if infrastructure_type.includes('Housing').
    
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
        
        # Add housing-specific fields if type contains 'Housing'
        if infra.is_housing():
            data.update({
                'bird_capacity': infra.bird_capacity,
                'current_occupancy': infra.current_occupancy,
                'length_meters': float(infra.length_meters) if infra.length_meters else None,
                'width_meters': float(infra.width_meters) if infra.width_meters else None,
                'height_meters': float(infra.height_meters) if infra.height_meters else None,
                'construction_material': infra.construction_material,
                'roofing_material': infra.roofing_material,
                'flooring_type': infra.flooring_type,
                'year_built': infra.year_built,
                'ventilation_system': infra.ventilation_system,
                'number_of_fans': infra.number_of_fans,
            })
        else:
            # Add support system fields
            data.update({
                'capacity': infra.capacity,
                'specifications': infra.specifications,
                'supplier': infra.supplier,
                'supplier_contact': infra.supplier_contact,
                'installation_date': infra.installation_date.isoformat() if infra.installation_date else None,
                'installation_cost_ghs': float(infra.installation_cost_ghs) if infra.installation_cost_ghs else None,
                'installer_company': infra.installer_company,
                'warranty_expiry': infra.warranty_expiry.isoformat() if infra.warranty_expiry else None,
                'warranty_terms': infra.warranty_terms,
                'is_under_warranty': infra.is_under_warranty,
                'condition_notes': infra.condition_notes,
                'maintenance_frequency': infra.maintenance_frequency,
                'last_maintenance_date': infra.last_maintenance_date.isoformat() if infra.last_maintenance_date else None,
                'next_maintenance_due': infra.next_maintenance_due.isoformat() if infra.next_maintenance_due else None,
                'is_maintenance_overdue': infra.is_maintenance_overdue,
                'days_until_maintenance': infra.days_until_maintenance,
                'maintenance_provider': infra.maintenance_provider,
                'maintenance_cost_ghs': float(infra.maintenance_cost_ghs) if infra.maintenance_cost_ghs else None,
                'notes': infra.notes,
                'photos': infra.photos,
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
        
        # Add housing fields if type contains 'Housing'
        if 'Housing' in infrastructure_type:
            infra_data.update({
                'bird_capacity': request.data.get('bird_capacity', 0),
                'current_occupancy': request.data.get('current_occupancy', 0),
                'length_meters': request.data.get('length_meters'),
                'width_meters': request.data.get('width_meters'),
                'height_meters': request.data.get('height_meters'),
                'construction_material': request.data.get('construction_material', ''),
                'roofing_material': request.data.get('roofing_material', ''),
                'flooring_type': request.data.get('flooring_type', ''),
                'year_built': request.data.get('year_built'),
                'ventilation_system': request.data.get('ventilation_system', ''),
                'number_of_fans': request.data.get('number_of_fans', 0),
            })
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
                'capacity': request.data.get('capacity', ''),
                'supplier': request.data.get('supplier', ''),
                'supplier_contact': request.data.get('supplier_contact', ''),
                'installation_date': installation_date,
                'installation_cost_ghs': request.data.get('installation_cost_ghs'),
                'installer_company': request.data.get('installer_company', ''),
                'warranty_expiry': warranty_expiry,
                'warranty_terms': request.data.get('warranty_terms', ''),
                'condition_notes': request.data.get('condition_notes', ''),
                'maintenance_frequency': request.data.get('maintenance_frequency', 'As Needed'),
                'last_maintenance_date': last_maintenance_date,
                'next_maintenance_due': next_maintenance_due,
                'maintenance_provider': request.data.get('maintenance_provider', ''),
                'maintenance_cost_ghs': request.data.get('maintenance_cost_ghs'),
                'notes': request.data.get('notes', ''),
                'created_by': request.user
            })
        
        infrastructure = Infrastructure.objects.create(**infra_data)
        
        return Response({
            'success': True,
            'message': f'{"Housing" if infrastructure.is_housing() else "Infrastructure"} created successfully',
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
        if infra.is_housing():
            housing_fields = [
                'bird_capacity', 'current_occupancy', 'length_meters', 'width_meters',
                'height_meters', 'construction_material', 'roofing_material', 'flooring_type',
                'year_built', 'ventilation_system', 'number_of_fans'
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
                'capacity', 'supplier', 'supplier_contact', 'installation_cost_ghs',
                'installer_company', 'warranty_terms', 'condition_notes', 'maintenance_frequency',
                'maintenance_provider', 'maintenance_cost_ghs', 'notes'
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
        
        # If housing, check for active flocks
        if infra.is_housing():
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


'''

# Read current file
with open('farms/views.py', 'r') as f:
    content = f.read()

# Find the start and end of UnifiedInfrastructureView
start_marker = 'class UnifiedInfrastructureView(APIView):'
end_marker = '\n\nclass FarmEquipmentView(APIView):'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    # Replace the view
    new_content = content[:start_idx] + new_view + content[end_idx:]
    
    with open('farms/views.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully replaced UnifiedInfrastructureView")
else:
    print("❌ Could not find view boundaries")
