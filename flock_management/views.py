"""
Flock Management API Views

Provides CRUD operations for flock/batch management.
"""

import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from datetime import datetime
from decimal import Decimal

from farms.models import Farm, PoultryHouse
from .models import DailyProduction, Flock, MortalityRecord, HealthRecord


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for flock management views."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response_data(self, data):
        """Return pagination metadata along with results."""
        return {
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        }


class FlockView(APIView):
    """
    GET /api/flocks/
    POST /api/flocks/
    GET /api/flocks/{id}/
    PUT /api/flocks/{id}/
    DELETE /api/flocks/{id}/
    
    Manage bird flocks/batches.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request, flock_id=None, active_only=False):
        """Get all flocks or specific flock by ID"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get single flock
        if flock_id:
            try:
                flock = Flock.objects.get(id=flock_id, farm=farm)
                data = self._serialize_flock(flock)
                return Response(data)
            except Flock.DoesNotExist:
                return Response(
                    {'error': 'Flock not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # List all flocks with optional filtering
        flocks = Flock.objects.filter(farm=farm)
        
        # Filter for active flocks only if requested
        if active_only:
            flocks = flocks.filter(status='Active')
        
        # Apply filters
        flock_type = request.query_params.get('type')
        if flock_type:
            flocks = flocks.filter(flock_type=flock_type)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            flocks = flocks.filter(status=status_filter)
        
        housed_in = request.query_params.get('housed_in')
        if housed_in:
            flocks = flocks.filter(housed_in_id=housed_in)
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(flocks, request)
        
        if page is not None:
            data = [self._serialize_flock(flock) for flock in page]
            return Response(paginator.get_paginated_response_data(data))
        
        # Fallback for non-paginated
        data = [self._serialize_flock(flock) for flock in flocks]
        return Response({'results': data, 'count': len(data)})
    
    def post(self, request):
        """Create new flock"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Support both frontend naming (batch_*) and backend naming (flock_*)
        flock_number = request.data.get('flock_number') or request.data.get('batch_number')
        flock_type = request.data.get('flock_type') or request.data.get('bird_type')
        breed = request.data.get('breed')
        arrival_date = request.data.get('arrival_date') or request.data.get('placement_date')
        initial_count = request.data.get('initial_count') or request.data.get('initial_quantity')
        
        # Validate required fields
        missing_fields = []
        if not flock_number:
            missing_fields.append('flock_number/batch_number')
        if not flock_type:
            missing_fields.append('flock_type/bird_type')
        if not breed:
            missing_fields.append('breed')
        if not arrival_date:
            missing_fields.append('arrival_date/placement_date')
        if not initial_count:
            missing_fields.append('initial_count/initial_quantity')
            
        if missing_fields:
            return Response(
                {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for duplicate flock_number
        if Flock.objects.filter(farm=farm, flock_number=flock_number).exists():
            return Response(
                {'error': 'A flock with this number already exists for your farm'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse dates (support both naming conventions)
        arrival_date_parsed = self._parse_date(arrival_date)
        if not arrival_date_parsed:
            return Response(
                {'error': 'Invalid arrival_date/placement_date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        production_start_date = None
        prod_start = request.data.get('production_start_date')
        if prod_start:
            production_start_date = self._parse_date(prod_start)
        
        expected_production_end_date = None
        expected_end = request.data.get('expected_production_end_date') or request.data.get('expected_end_date')
        if expected_end:
            expected_production_end_date = self._parse_date(expected_end)
        
        # Get poultry house if provided (support both field names)
        housed_in = None
        house_id = request.data.get('housed_in_id') or request.data.get('poultry_house_id')
        if house_id:
            try:
                housed_in = PoultryHouse.objects.get(id=house_id, farm=farm)
            except PoultryHouse.DoesNotExist:
                return Response(
                    {'error': 'Poultry house not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Create flock
        flock = Flock.objects.create(
            farm=farm,
            flock_number=flock_number,
            flock_type=flock_type,
            breed=breed,
            source=request.data.get('source', 'YEA Program'),
            supplier_name=request.data.get('supplier_name', ''),
            arrival_date=arrival_date_parsed,
            initial_count=int(initial_count),
            current_count=int(request.data.get('current_count', initial_count)),
            age_at_arrival_weeks=Decimal(str(request.data.get('age_at_arrival_weeks', 0))),
            purchase_price_per_bird=Decimal(str(request.data.get('purchase_price_per_bird', 0))),
            status=request.data.get('status', 'Active'),
            production_start_date=production_start_date,
            expected_production_end_date=expected_production_end_date,
            is_currently_producing=request.data.get('is_currently_producing', False),
            housed_in=housed_in,
            notes=request.data.get('notes', '')
        )
        
        return Response({
            'success': True,
            'message': 'Flock created successfully',
            'flock_id': str(flock.id)
        }, status=status.HTTP_201_CREATED)
    
    def put(self, request, flock_id):
        """Update existing flock (supports partial updates)"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get flock and verify ownership
        try:
            flock = Flock.objects.get(id=flock_id, farm=farm)
        except Flock.DoesNotExist:
            return Response(
                {'error': 'Flock not found or you do not have permission to update it'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update fields if provided
        if 'flock_number' in request.data:
            # Check for duplicate if changing flock_number
            if request.data['flock_number'] != flock.flock_number:
                if Flock.objects.filter(farm=farm, flock_number=request.data['flock_number']).exists():
                    return Response(
                        {'error': 'A flock with this number already exists'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            flock.flock_number = request.data['flock_number']
        
        if 'flock_type' in request.data:
            flock.flock_type = request.data['flock_type']
        if 'breed' in request.data:
            flock.breed = request.data['breed']
        if 'source' in request.data:
            flock.source = request.data['source']
        if 'supplier_name' in request.data:
            flock.supplier_name = request.data['supplier_name']
        if 'current_count' in request.data:
            flock.current_count = int(request.data['current_count'])
        if 'age_at_arrival_weeks' in request.data:
            flock.age_at_arrival_weeks = Decimal(str(request.data['age_at_arrival_weeks']))
        if 'purchase_price_per_bird' in request.data:
            flock.purchase_price_per_bird = Decimal(str(request.data['purchase_price_per_bird']))
        if 'status' in request.data:
            flock.status = request.data['status']
        if 'is_currently_producing' in request.data:
            flock.is_currently_producing = request.data['is_currently_producing']
        if 'notes' in request.data:
            flock.notes = request.data['notes']
        
        # Handle date fields
        if 'arrival_date' in request.data:
            arrival_date = self._parse_date(request.data['arrival_date'])
            if arrival_date:
                flock.arrival_date = arrival_date
        
        if 'production_start_date' in request.data:
            date_str = request.data['production_start_date']
            if date_str:
                flock.production_start_date = self._parse_date(date_str)
            else:
                flock.production_start_date = None
        
        if 'expected_production_end_date' in request.data:
            date_str = request.data['expected_production_end_date']
            if date_str:
                flock.expected_production_end_date = self._parse_date(date_str)
            else:
                flock.expected_production_end_date = None
        
        # Handle housed_in
        if 'housed_in_id' in request.data:
            if request.data['housed_in_id']:
                try:
                    housed_in = PoultryHouse.objects.get(id=request.data['housed_in_id'], farm=farm)
                    flock.housed_in = housed_in
                except PoultryHouse.DoesNotExist:
                    return Response(
                        {'error': 'Poultry house not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                flock.housed_in = None
        
        flock.save()
        
        return Response({
            'success': True,
            'message': 'Flock updated successfully'
        })
    
    def delete(self, request, flock_id):
        """Delete flock"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get flock and verify ownership
        try:
            flock = Flock.objects.get(id=flock_id, farm=farm)
        except Flock.DoesNotExist:
            return Response(
                {'error': 'Flock not found or you do not have permission to delete it'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        flock_number = flock.flock_number
        flock.delete()
        
        return Response({
            'success': True,
            'message': f'Flock "{flock_number}" deleted successfully'
        })
    
    def _serialize_flock(self, flock):
        """Serialize flock object to dict"""
        return {
            'id': str(flock.id),
            'flock_number': flock.flock_number,
            'flock_type': flock.flock_type,
            'breed': flock.breed,
            'source': flock.source,
            'supplier_name': flock.supplier_name,
            'arrival_date': flock.arrival_date.isoformat(),
            'initial_count': flock.initial_count,
            'current_count': flock.current_count,
            'age_at_arrival_weeks': float(flock.age_at_arrival_weeks),
            'purchase_price_per_bird': float(flock.purchase_price_per_bird),
            'total_acquisition_cost': float(flock.total_acquisition_cost),
            'status': flock.status,
            'production_start_date': flock.production_start_date.isoformat() if flock.production_start_date else None,
            'expected_production_end_date': flock.expected_production_end_date.isoformat() if flock.expected_production_end_date else None,
            'is_currently_producing': flock.is_currently_producing,
            'housed_in': {
                'id': str(flock.housed_in.id),
                'house_name': flock.housed_in.infrastructure_name,
                'capacity': flock.housed_in.bird_capacity
            } if flock.housed_in else None,
            'total_feed_cost': float(flock.total_feed_cost),
            'total_medication_cost': float(flock.total_medication_cost),
            'total_vaccination_cost': float(flock.total_vaccination_cost),
            'total_mortality': flock.total_mortality,
            'mortality_rate_percent': float(flock.mortality_rate_percent),
            'average_daily_mortality': float(flock.average_daily_mortality),
            'total_eggs_produced': flock.total_eggs_produced,
            'average_eggs_per_bird': float(flock.average_eggs_per_bird),
            'total_feed_consumed_kg': float(flock.total_feed_consumed_kg),
            'feed_conversion_ratio': float(flock.feed_conversion_ratio),
            'notes': flock.notes,
            'created_at': flock.created_at.isoformat(),
            'updated_at': flock.updated_at.isoformat()
        }
    
    def _parse_date(self, date_str):
        """Parse date string to date object"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        except (ValueError, AttributeError):
            return None


class FlockStatisticsView(APIView):
    """
    GET /api/flocks/statistics/
    
    Get aggregated statistics about flocks.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get flock statistics"""
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'No farm found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from django.db.models import Count, Sum, Avg
        
        flocks = Flock.objects.filter(farm=farm)
        
        # Overall statistics
        total_flocks = flocks.count()
        total_birds = flocks.aggregate(Sum('current_count'))['current_count__sum'] or 0
        active_flocks = flocks.filter(status='Active').count()
        
        # By type
        by_type = {}
        type_counts = flocks.values('flock_type').annotate(count=Count('id'), birds=Sum('current_count'))
        for item in type_counts:
            by_type[item['flock_type']] = {
                'flocks': item['count'],
                'birds': item['birds'] or 0
            }
        
        # By status
        by_status = {}
        status_counts = flocks.values('status').annotate(count=Count('id'), birds=Sum('current_count'))
        for item in status_counts:
            by_status[item['status']] = {
                'flocks': item['count'],
                'birds': item['birds'] or 0
            }
        
        # Performance metrics
        avg_mortality_rate = flocks.aggregate(Avg('mortality_rate_percent'))['mortality_rate_percent__avg'] or 0
        total_eggs = flocks.aggregate(Sum('total_eggs_produced'))['total_eggs_produced__sum'] or 0
        
        # Production status
        producing_flocks = flocks.filter(is_currently_producing=True).count()
        
        return Response({
            'total_flocks': total_flocks,
            'total_birds': total_birds,
            'active_flocks': active_flocks,
            'producing_flocks': producing_flocks,
            'by_type': by_type,
            'by_status': by_status,
            'performance': {
                'avg_mortality_rate_percent': round(float(avg_mortality_rate), 2),
                'total_eggs_produced': total_eggs
            }
        })


class DailyProductionView(APIView):
    """
    POST /api/flocks/production/

    Create daily production records for a flock. The endpoint accepts both the
    backend field names and the simpler frontend payload used by the modal
    (e.g. `record_date`, `mortality_count`, `feed_consumed_kg`).
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def _serialize_record(self, rec):
        """Serialize a DailyProduction record."""
        return {
            'id': str(rec.id),
            'flock_id': str(rec.flock_id),
            'flock_number': rec.flock.flock_number if rec.flock else None,
            'production_date': rec.production_date.isoformat() if rec.production_date else None,
            'eggs_collected': rec.eggs_collected,
            'birds_died': rec.birds_died,
            'feed_consumed_kg': float(rec.feed_consumed_kg) if rec.feed_consumed_kg else 0,
            'water_consumed_liters': float(rec.water_consumed_liters) if hasattr(rec, 'water_consumed_liters') and rec.water_consumed_liters else None,
            'feed_cost_today': float(rec.feed_cost_today) if rec.feed_cost_today else 0,
            'production_rate_percent': float(rec.production_rate_percent) if rec.production_rate_percent else 0,
            'notes': rec.unusual_behavior,
            'general_health': rec.general_health,
            'recorded_at': rec.recorded_at.isoformat() if rec.recorded_at else None,
        }

    def get(self, request):
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        flock_id = request.query_params.get('flock_id') or request.query_params.get('flock')
        qs = DailyProduction.objects.filter(farm=farm).select_related('flock').order_by('-production_date')
        if flock_id:
            qs = qs.filter(flock_id=flock_id)

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            data = [self._serialize_record(rec) for rec in page]
            return Response(paginator.get_paginated_response_data(data))

        # Fallback for non-paginated (shouldn't happen)
        data = [self._serialize_record(rec) for rec in qs]
        return Response({'results': data, 'count': len(data)})

    def post(self, request):
        try:
            farm = Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        flock_id = request.data.get('flock_id') or request.data.get('flock')
        if not flock_id:
            return Response({'error': 'flock_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        flock = get_object_or_404(Flock, id=flock_id, farm=farm)

        production_date = (
            request.data.get('production_date')
            or request.data.get('record_date')
            or request.data.get('date')
        )
        production_date = self._parse_date(production_date)
        if not production_date:
            return Response({'error': 'production_date/record_date is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        eggs_collected = self._to_int(request.data.get('eggs_collected'))
        feed_consumed_kg = self._to_decimal(request.data.get('feed_consumed_kg'))
        feed_cost_today = self._to_decimal(request.data.get('feed_cost_today'))
        birds_died = self._to_int(request.data.get('birds_died') or request.data.get('mortality_count'))

        # Ensure egg breakdown matches total to satisfy model validation
        egg_breakdown = {
            'good_eggs': eggs_collected,
            'broken_eggs': 0,
            'dirty_eggs': 0,
            'small_eggs': 0,
            'soft_shell_eggs': 0,
        }

        with transaction.atomic():
            daily_prod = DailyProduction(
                farm=farm,
                flock=flock,
                production_date=production_date,
                eggs_collected=eggs_collected,
                birds_died=birds_died,
                feed_consumed_kg=feed_consumed_kg,
                feed_cost_today=feed_cost_today,
                general_health=request.data.get('general_health', 'Good'),
                unusual_behavior=request.data.get('notes', ''),
                signs_of_disease=self._to_bool(request.data.get('signs_of_disease', False)),
                disease_symptoms=request.data.get('disease_symptoms', ''),
                vaccination_given=self._to_bool(request.data.get('vaccination_given', False)),
                vaccination_type=request.data.get('vaccination_type', ''),
                medication_given=self._to_bool(request.data.get('medication_given', False)),
                medication_type=request.data.get('medication_type', ''),
                medication_cost_today=self._to_decimal(request.data.get('medication_cost_today')),
                birds_sold=self._to_int(request.data.get('birds_sold')),
                birds_sold_revenue=self._to_decimal(request.data.get('birds_sold_revenue')),
                mortality_reason=request.data.get('mortality_reason', ''),
                mortality_notes=request.data.get('mortality_notes', ''),
                recorded_by=request.user,
                **egg_breakdown,
            )

            try:
                daily_prod.full_clean()
                daily_prod.save()
            except IntegrityError:
                return Response(
                    {'error': 'A production record for this flock and date already exists'},
                    status=status.HTTP_409_CONFLICT
                )
            except Exception as exc:  # Catch validation errors and surface message
                from django.core.exceptions import ValidationError

                if isinstance(exc, ValidationError):
                    return Response({'errors': exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
                raise

        return Response(
            {
                'success': True,
                'message': 'Production record saved',
                'record_id': str(daily_prod.id),
            },
            status=status.HTTP_201_CREATED,
        )

    def _parse_date(self, date_str):
        if not date_str:
            return None
        # Accept ISO (YYYY-MM-DD) and common UI formats with slashes
        candidates = [
            str(date_str).replace('Z', '+00:00'),
        ]
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except Exception:
                continue
        try:
            return datetime.fromisoformat(candidates[0]).date()
        except Exception:
            return None

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() in {'true', '1', 'yes', 'y', 'on'}
        return bool(value)

    def _to_int(self, value, default=0):
        try:
            if value in (None, ''):
                return int(default)
            return int(value)
        except Exception:
            return int(default)

    def _to_decimal(self, value, default=0):
        try:
            if value in (None, ''):
                return Decimal(default)
            return Decimal(str(value))
        except Exception:
            return Decimal(default)


class MortalityBaseView(APIView):
    """Shared helpers for mortality endpoints."""

    permission_classes = [IsAuthenticated]

    def _get_farm(self, request):
        try:
            return Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return None

    def _parse_date(self, date_str):
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00')).date()
        except (ValueError, TypeError, AttributeError):
            return None

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() in {'true', '1', 'yes', 'y', 'on'}
        return bool(value)

    def _to_int(self, value, default=0):
        try:
            if value in (None, ''):
                return int(default)
            return int(value)
        except Exception:
            return int(default)

    def _to_decimal(self, value, default=0):
        try:
            if value in (None, ''):
                return Decimal(default)
            return Decimal(str(value))
        except Exception:
            return Decimal(default)

    def _parse_symptoms(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [item.strip() for item in value.split(',') if item.strip()]
        return []

    def _serialize_record(self, record):
        return {
            'id': str(record.id),
            'farm_id': str(record.farm_id),
            'flock_id': str(record.flock_id),
            'flock_number': record.flock.flock_number,
            'daily_production_id': str(record.daily_production_id) if record.daily_production_id else None,
            'date_discovered': record.date_discovered.isoformat(),
            'number_of_birds': record.number_of_birds,
            'probable_cause': record.probable_cause,
            'disease_suspected': record.disease_suspected,
            'symptoms_observed': record.symptoms_observed,
            'symptoms_description': record.symptoms_description,
            'vet_inspection_required': record.vet_inspection_required,
            'vet_inspection_requested_date': record.vet_inspection_requested_date.isoformat() if record.vet_inspection_requested_date else None,
            'vet_inspected': record.vet_inspected,
            'vet_inspection_date': record.vet_inspection_date.isoformat() if record.vet_inspection_date else None,
            'vet_diagnosis': record.vet_diagnosis,
            'lab_test_conducted': record.lab_test_conducted,
            'lab_test_results': record.lab_test_results,
            'disposal_method': record.disposal_method,
            'disposal_location': record.disposal_location,
            'disposal_date': record.disposal_date.isoformat() if record.disposal_date else None,
            'estimated_value_per_bird': float(record.estimated_value_per_bird),
            'total_estimated_loss': float(record.total_estimated_loss),
            'compensation_claimed': record.compensation_claimed,
            'compensation_amount': float(record.compensation_amount),
            'compensation_status': record.compensation_status,
            'notes': record.notes,
            'reported_by': record.reported_by.email if record.reported_by else None,
            'created_at': record.created_at.isoformat(),
            'updated_at': record.updated_at.isoformat(),
        }


class MortalityRecordView(MortalityBaseView):
    """
    GET /api/mortality/
    POST /api/mortality/

    List or create mortality records scoped to the farmer's farm.
    """
    pagination_class = StandardResultsSetPagination

    def get(self, request, pending_only=False):
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        queryset = (
            MortalityRecord.objects
            .filter(farm=farm)
            .select_related('flock', 'daily_production', 'reported_by')
            .order_by('-date_discovered')
        )

        flock_id = request.query_params.get('flock_id') or request.query_params.get('flock')
        if flock_id:
            queryset = queryset.filter(flock_id=flock_id)

        probable_cause = request.query_params.get('probable_cause')
        if probable_cause:
            queryset = queryset.filter(probable_cause=probable_cause)

        compensation_status = request.query_params.get('compensation_status')
        if compensation_status:
            queryset = queryset.filter(compensation_status=compensation_status)

        start_date = self._parse_date(request.query_params.get('start_date'))
        end_date = self._parse_date(request.query_params.get('end_date'))
        if start_date:
            queryset = queryset.filter(date_discovered__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_discovered__lte=end_date)

        if pending_only:
            queryset = queryset.filter(vet_inspection_required=True, vet_inspected=False)

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            records = [self._serialize_record(rec) for rec in page]
            return Response(paginator.get_paginated_response_data(records))

        # Fallback for non-paginated
        records = [self._serialize_record(rec) for rec in queryset]
        return Response({'results': records, 'count': len(records)})

    def post(self, request):
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        flock_id = request.data.get('flock_id') or request.data.get('flock')
        if not flock_id:
            return Response({'error': 'flock_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        flock = get_object_or_404(Flock, id=flock_id, farm=farm)

        daily_production = None
        dp_id = request.data.get('daily_production_id') or request.data.get('daily_production')
        if dp_id:
            daily_production = get_object_or_404(DailyProduction, id=dp_id, farm=farm)

        date_discovered = self._parse_date(
            request.data.get('date_discovered')
            or request.data.get('record_date')
            or request.data.get('incident_date')
        )
        if not date_discovered:
            return Response(
                {'error': 'date_discovered/record_date is required (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        number_of_birds = self._to_int(
            request.data.get('number_of_birds')
            or request.data.get('mortality_count')
            or request.data.get('bird_count')
        )
        if number_of_birds <= 0:
            return Response({'error': 'number_of_birds must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        compensation_claimed = self._to_bool(request.data.get('compensation_claimed', False))
        compensation_status = request.data.get('compensation_status')
        if not compensation_status:
            compensation_status = 'Pending' if compensation_claimed else 'Not Claimed'

        # Map frontend aliases
        probable_cause = (
            request.data.get('probable_cause')
            or request.data.get('cause')
            or 'Unknown'
        )
        # Map simple "Disease" to the allowed choice bucket
        if probable_cause == 'Disease':
            probable_cause = 'Disease - Viral'

        symptoms_observed = request.data.get('symptoms_observed')
        if symptoms_observed is None:
            symptoms_observed = request.data.get('symptoms')
        if symptoms_observed in (None, '', []):
            symptoms_observed = []
        vet_inspection_required = self._to_bool(
            request.data.get('vet_inspection_required', request.data.get('vet_consulted', False))
        )
        notes = request.data.get('notes', '')
        if not notes and request.data.get('action_taken'):
            notes = f"Action taken: {request.data.get('action_taken')}"

        record = MortalityRecord(
            farm=farm,
            flock=flock,
            daily_production=daily_production,
            date_discovered=date_discovered,
            number_of_birds=number_of_birds,
            probable_cause=probable_cause,
            disease_suspected=request.data.get('disease_suspected', ''),
            symptoms_observed=self._parse_symptoms(symptoms_observed),
            symptoms_description=request.data.get('symptoms_description', ''),
            vet_inspection_required=vet_inspection_required,
            vet_inspection_requested_date=self._parse_date(request.data.get('vet_inspection_requested_date')),
            vet_inspected=self._to_bool(request.data.get('vet_inspected', False)),
            vet_inspection_date=self._parse_date(request.data.get('vet_inspection_date')),
            vet_diagnosis=request.data.get('vet_diagnosis', ''),
            lab_test_conducted=self._to_bool(request.data.get('lab_test_conducted', False)),
            lab_test_results=request.data.get('lab_test_results', ''),
            disposal_method=request.data.get('disposal_method', ''),
            disposal_location=request.data.get('disposal_location', ''),
            disposal_date=self._parse_date(request.data.get('disposal_date')),
            estimated_value_per_bird=self._to_decimal(request.data.get('estimated_value_per_bird')), 
            compensation_claimed=compensation_claimed,
            compensation_amount=self._to_decimal(request.data.get('compensation_amount')), 
            compensation_status=compensation_status,
            notes=notes,
            reported_by=request.user,
        )

        adjust_current_count = self._to_bool(request.data.get('adjust_current_count', False))

        try:
            with transaction.atomic():
                record.full_clean()
                record.save()

                if adjust_current_count:
                    new_count = record.flock.current_count - record.number_of_birds
                    if new_count < 0:
                        raise ValueError('Mortality count exceeds flock current count')
                    record.flock.current_count = new_count
                    record.flock.save()
        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                return Response({'errors': exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'success': True,
                'message': 'Mortality record saved',
                'record': self._serialize_record(record),
            },
            status=status.HTTP_201_CREATED,
        )


class HealthRecordView(MortalityBaseView):
    """
    POST /api/flocks/health/
    GET  /api/flocks/health/

    Capture vaccinations/medications/health check records for a flock.
    """
    pagination_class = StandardResultsSetPagination

    def _serialize_health_record(self, rec):
        return {
            'id': str(rec.id),
            'flock_id': str(rec.flock_id),
            'flock_number': rec.flock.flock_number,
            'record_date': rec.record_date.isoformat(),
            'record_type': rec.record_type,
            'disease': rec.disease,
            'diagnosis': rec.diagnosis,
            'symptoms': rec.symptoms,
            'treatment_name': rec.treatment_name,
            'treatment_method': rec.treatment_method,
            'dosage': rec.dosage,
            'administering_person': rec.administering_person,
            'vet_name': rec.vet_name,
            'vet_license': rec.vet_license,
            'birds_affected': rec.birds_affected,
            'cost_ghs': float(rec.cost_ghs),
            'outcome': rec.outcome,
            'follow_up_date': rec.follow_up_date.isoformat() if rec.follow_up_date else None,
            'notes': rec.notes,
            'created_at': rec.created_at.isoformat(),
        }

    def get(self, request):
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        qs = (
            HealthRecord.objects
            .filter(farm=farm)
            .select_related('flock')
            .order_by('-record_date')
        )

        flock_id = request.query_params.get('flock_id') or request.query_params.get('flock')
        if flock_id:
            qs = qs.filter(flock_id=flock_id)

        record_type = request.query_params.get('record_type')
        if record_type:
            qs = qs.filter(record_type=record_type)

        start_date = self._parse_date(request.query_params.get('start_date'))
        end_date = self._parse_date(request.query_params.get('end_date'))
        if start_date:
            qs = qs.filter(record_date__gte=start_date)
        if end_date:
            qs = qs.filter(record_date__lte=end_date)

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            data = [self._serialize_health_record(rec) for rec in page]
            return Response(paginator.get_paginated_response_data(data))

        # Fallback for non-paginated
        data = [self._serialize_health_record(rec) for rec in qs]
        return Response({'results': data, 'count': len(data)})

    def post(self, request):
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        flock_id = request.data.get('flock_id') or request.data.get('flock')
        if not flock_id:
            return Response({'error': 'flock_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        flock = get_object_or_404(Flock, id=flock_id, farm=farm)

        record_date = self._parse_date(
            request.data.get('record_date')
            or request.data.get('date')
        )
        if not record_date:
            return Response({'error': 'record_date/date is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data

        record = HealthRecord(
            farm=farm,
            flock=flock,
            record_date=record_date,
            record_type=payload.get('record_type', 'Health Check'),
            disease=payload.get('disease', ''),
            diagnosis=payload.get('diagnosis', ''),
            symptoms=payload.get('symptoms', ''),
            treatment_name=payload.get('treatment_name') or payload.get('treatment', ''),
            treatment_method=payload.get('treatment_method', ''),
            dosage=payload.get('dosage', ''),
            administering_person=payload.get('administering_person', ''),
            vet_name=payload.get('vet_name', ''),
            vet_license=payload.get('vet_license', ''),
            birds_affected=self._to_int(payload.get('birds_affected'), 0),
            cost_ghs=self._to_decimal(payload.get('cost_ghs'), 0),
            outcome=payload.get('outcome', ''),
            follow_up_date=self._parse_date(payload.get('follow_up_date')),
            notes=payload.get('notes', ''),
        )

        try:
            record.full_clean()
            record.save()
        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                return Response({'errors': exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'success': True,
                'message': 'Health record saved',
                'record_id': str(record.id),
            },
            status=status.HTTP_201_CREATED,
        )


class MortalityRecordDetailView(MortalityBaseView):
    """
    GET /api/mortality/{id}/
    PUT /api/mortality/{id}/

    Retrieve or update a specific mortality record.
    """

    def get(self, request, record_id):
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        record = get_object_or_404(
            MortalityRecord.objects.select_related('flock', 'daily_production', 'reported_by'),
            id=record_id,
            farm=farm,
        )
        return Response(self._serialize_record(record))

    def put(self, request, record_id):
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        record = get_object_or_404(
            MortalityRecord.objects.select_related('flock', 'daily_production', 'reported_by'),
            id=record_id,
            farm=farm,
        )

        old_number = record.number_of_birds
        new_number = self._to_int(request.data.get('number_of_birds'), default=old_number)

        field_updates = {
            'probable_cause': request.data.get('probable_cause'),
            'disease_suspected': request.data.get('disease_suspected'),
            'symptoms_description': request.data.get('symptoms_description'),
            'vet_diagnosis': request.data.get('vet_diagnosis'),
            'lab_test_results': request.data.get('lab_test_results'),
            'disposal_method': request.data.get('disposal_method'),
            'disposal_location': request.data.get('disposal_location'),
            'notes': request.data.get('notes'),
        }

        for field, value in field_updates.items():
            if value is not None:
                setattr(record, field, value)

        date_fields = {
            'date_discovered': request.data.get('date_discovered'),
            'vet_inspection_requested_date': request.data.get('vet_inspection_requested_date'),
            'vet_inspection_date': request.data.get('vet_inspection_date'),
            'disposal_date': request.data.get('disposal_date'),
        }

        for field, raw in date_fields.items():
            if raw is not None:
                parsed = self._parse_date(raw)
                setattr(record, field, parsed)

        record.symptoms_observed = self._parse_symptoms(
            request.data.get('symptoms_observed', record.symptoms_observed)
        )

        if 'lab_test_conducted' in request.data:
            record.lab_test_conducted = self._to_bool(request.data.get('lab_test_conducted'))

        if 'vet_inspection_required' in request.data:
            record.vet_inspection_required = self._to_bool(request.data.get('vet_inspection_required'))

        if 'vet_inspected' in request.data:
            record.vet_inspected = self._to_bool(request.data.get('vet_inspected'))

        if 'compensation_claimed' in request.data:
            record.compensation_claimed = self._to_bool(request.data.get('compensation_claimed'))

        if 'compensation_status' in request.data:
            record.compensation_status = request.data.get('compensation_status') or record.compensation_status

        if 'compensation_amount' in request.data:
            record.compensation_amount = self._to_decimal(request.data.get('compensation_amount'), record.compensation_amount)

        if 'estimated_value_per_bird' in request.data:
            record.estimated_value_per_bird = self._to_decimal(
                request.data.get('estimated_value_per_bird'), record.estimated_value_per_bird
            )

        record.number_of_birds = new_number

        adjust_current_count = self._to_bool(request.data.get('adjust_current_count', False))
        delta = new_number - old_number

        try:
            with transaction.atomic():
                if adjust_current_count and delta != 0:
                    prospective = record.flock.current_count - delta
                    if prospective < 0:
                        raise ValueError('Mortality count exceeds flock current count')
                    record.flock.current_count = prospective

                record.full_clean()
                record.save()

                if adjust_current_count and delta != 0:
                    record.flock.save()
        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                return Response({'errors': exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self._serialize_record(record))
