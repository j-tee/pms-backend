"""
Views for Processing Batch operations.

Handles:
- CRUD for processing batches and outputs
- Batch completion with inventory updates
- Analytics and reporting for government visibility
- Stale stock detection
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Count, Sum, Avg, F, Q
from django.utils import timezone
from datetime import timedelta

from farms.models import Farm
from .processing_models import (
    ProcessingBatch,
    ProcessingOutput,
    ProcessingBatchStatus,
    ProcessingType,
    ProductCategory,
    ProcessingOutputAnalytics
)
from .processing_serializers import (
    ProcessingBatchSerializer,
    ProcessingBatchCreateSerializer,
    ProcessingBatchUpdateSerializer,
    ProcessingBatchListSerializer,
    ProcessingBatchCompleteSerializer,
    ProcessingBatchCancelSerializer,
    ProcessingOutputSerializer,
    ProcessingOutputCreateSerializer,
    BulkOutputCreateSerializer,
    StaleStockReportSerializer,
    ProcessingAnalyticsSerializer
)


class IsFarmOwnerOrAdmin(permissions.BasePermission):
    """Permission check for farm owner or admin access."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admins can access all
        if request.user.is_staff or request.user.role in ['super_admin', 'national_admin']:
            return True
        
        # Farm owner can access their own batches
        # Farm model uses 'user' field (OneToOneField) for ownership
        if hasattr(obj, 'farm'):
            return obj.farm.user == request.user
        
        # For outputs, check via batch
        if hasattr(obj, 'processing_batch'):
            farm = obj.processing_batch.farm
            return farm.user == request.user
        
        return False


class ProcessingBatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing processing batches.
    
    Endpoints:
    - GET /api/processing/batches/ - List batches
    - POST /api/processing/batches/ - Create batch (deducts from flock)
    - GET /api/processing/batches/{id}/ - Get batch detail
    - PATCH /api/processing/batches/{id}/ - Update batch
    - DELETE /api/processing/batches/{id}/ - Delete batch (restores flock if not completed)
    - POST /api/processing/batches/{id}/complete/ - Complete batch and update inventory
    - POST /api/processing/batches/{id}/cancel/ - Cancel batch and restore flock
    - GET /api/processing/batches/{id}/outputs/ - List batch outputs
    - POST /api/processing/batches/{id}/add-outputs/ - Add outputs to batch
    """
    
    permission_classes = [IsFarmOwnerOrAdmin]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Get processing batches for user's farms or all for admins."""
        user = self.request.user
        
        queryset = ProcessingBatch.objects.select_related(
            'farm', 'source_flock', 'processed_by'
        ).prefetch_related('outputs').annotate(
            output_count=Count('outputs')
        )
        
        # Filter by farm ownership for non-admins
        # Farm model uses 'user' field (OneToOneField) for ownership
        if not user.is_staff and user.role not in ['super_admin', 'national_admin', 'regional_admin']:
            queryset = queryset.filter(farm__user=user)
        
        # Admin regional filtering
        if user.role == 'regional_admin' and hasattr(user, 'region'):
            queryset = queryset.filter(farm__primary_region=user.region)
        
        # Apply query filters
        farm_id = self.request.query_params.get('farm')
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        
        flock_id = self.request.query_params.get('flock')
        if flock_id:
            queryset = queryset.filter(source_flock_id=flock_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        processing_type = self.request.query_params.get('processing_type')
        if processing_type:
            queryset = queryset.filter(processing_type=processing_type)
        
        # Date filters
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(processing_date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(processing_date__lte=date_to)
        
        return queryset.order_by('-processing_date', '-created_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ProcessingBatchCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProcessingBatchUpdateSerializer
        elif self.action == 'list':
            return ProcessingBatchListSerializer
        return ProcessingBatchSerializer
    
    def perform_destroy(self, instance):
        """Delete batch, restoring flock if not completed."""
        if instance.status == ProcessingBatchStatus.COMPLETED:
            # Can't delete completed batches (would mess up inventory)
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                'Cannot delete a completed processing batch. '
                'Inventory has already been updated.'
            )
        
        # Restore birds to flock if not cancelled
        if instance.status != ProcessingBatchStatus.CANCELLED:
            instance.cancel(reason='Batch deleted', restore_flock=True)
        
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def complete(self, request, id=None):
        """
        Complete the processing batch and add outputs to inventory.
        
        This is the critical endpoint that:
        1. Validates outputs are defined
        2. Creates inventory entries for each output
        3. Links outputs to marketplace products
        4. Marks batch as completed
        """
        batch = self.get_object()
        
        serializer = ProcessingBatchCompleteSerializer(
            data=request.data,
            context={'batch': batch, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            batch.complete_and_update_inventory(user=request.user)
            
            return Response({
                'message': 'Processing batch completed successfully',
                'batch_id': str(batch.id),
                'batch_number': batch.batch_number,
                'outputs_added': batch.outputs.count(),
                'total_quantity': batch.total_output_quantity,
                'inventory_updated': True,
                'completed_at': batch.completed_at.isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to complete batch',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, id=None):
        """
        Cancel the processing batch.
        
        Options:
        - restore_flock: If true, birds are added back to source flock
        - reason: Cancellation reason for audit trail
        """
        batch = self.get_object()
        
        serializer = ProcessingBatchCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            batch.cancel(
                reason=serializer.validated_data.get('reason', ''),
                restore_flock=serializer.validated_data.get('restore_flock', True)
            )
            
            return Response({
                'message': 'Processing batch cancelled',
                'batch_id': str(batch.id),
                'batch_number': batch.batch_number,
                'flock_restored': serializer.validated_data.get('restore_flock', True),
                'birds_restored': batch.birds_processed if serializer.validated_data.get('restore_flock', True) else 0
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to cancel batch',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def outputs(self, request, id=None):
        """Get all outputs for this batch."""
        batch = self.get_object()
        outputs = batch.outputs.all()
        serializer = ProcessingOutputSerializer(outputs, many=True)
        
        return Response({
            'batch_id': str(batch.id),
            'batch_number': batch.batch_number,
            'count': outputs.count(),
            'outputs': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='add-outputs')
    def add_outputs(self, request, id=None):
        """
        Add outputs to this batch.
        
        Accepts either:
        - Single output: {product_category, quantity, ...}
        - Multiple outputs: {outputs: [{...}, {...}]}
        """
        batch = self.get_object()
        
        if batch.status == ProcessingBatchStatus.COMPLETED:
            return Response({
                'error': 'Cannot add outputs to a completed batch'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if it's bulk or single
        if 'outputs' in request.data:
            serializer = BulkOutputCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            outputs_created = []
            for output_data in serializer.validated_data['outputs']:
                output = ProcessingOutput.objects.create(
                    processing_batch=batch,
                    **output_data
                )
                outputs_created.append(output)
            
            # Auto-allocate costs if requested
            if serializer.validated_data.get('auto_allocate_costs', True):
                method = serializer.validated_data.get('allocation_method', 'quantity')
                for output in outputs_created:
                    if method == 'weight':
                        output.allocate_cost_by_weight()
                    else:
                        output.allocate_cost_by_quantity()
            
            return Response({
                'message': f'Added {len(outputs_created)} outputs to batch',
                'batch_id': str(batch.id),
                'outputs': ProcessingOutputSerializer(outputs_created, many=True).data
            }, status=status.HTTP_201_CREATED)
        else:
            # Single output
            serializer = ProcessingOutputCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            output = ProcessingOutput.objects.create(
                processing_batch=batch,
                **serializer.validated_data
            )
            
            return Response({
                'message': 'Output added to batch',
                'batch_id': str(batch.id),
                'output': ProcessingOutputSerializer(output).data
            }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """
        Get processing analytics summary.
        
        Query params:
        - farm: Filter by farm ID
        - date_from, date_to: Date range
        """
        queryset = self.get_queryset()
        
        # Aggregate statistics
        stats = queryset.aggregate(
            total_batches=Count('id'),
            completed_batches=Count('id', filter=Q(status=ProcessingBatchStatus.COMPLETED)),
            pending_batches=Count('id', filter=Q(status__in=[
                ProcessingBatchStatus.PENDING, 
                ProcessingBatchStatus.IN_PROGRESS
            ])),
            total_birds_processed=Sum('birds_processed'),
            total_birds_lost=Sum('birds_lost_in_processing'),
            total_processing_cost=Sum(
                F('processing_cost') + F('labor_cost') + F('packaging_cost')
            ),
        )
        
        # Calculate outputs
        total_outputs = ProcessingOutput.objects.filter(
            processing_batch__in=queryset
        ).aggregate(
            total_count=Count('id'),
            total_quantity=Sum('quantity')
        )
        
        # Stale stock count (older than 7 days)
        stale_threshold = timezone.now().date() - timedelta(days=7)
        stale_count = ProcessingOutput.objects.filter(
            processing_batch__in=queryset,
            inventory_updated=True,
            production_date__lte=stale_threshold
        ).count()
        
        # Expiring soon (within 3 days)
        expiry_window = timezone.now().date() + timedelta(days=3)
        expiring_count = ProcessingOutput.objects.filter(
            processing_batch__in=queryset,
            inventory_updated=True,
            expiry_date__lte=expiry_window,
            expiry_date__gte=timezone.now().date()
        ).count()
        
        # By processing type breakdown
        by_type = list(queryset.values('processing_type').annotate(
            count=Count('id'),
            birds_processed=Sum('birds_processed')
        ).order_by('-count'))
        
        avg_loss_rate = 0
        if stats['total_birds_processed'] and stats['total_birds_processed'] > 0:
            avg_loss_rate = (
                (stats['total_birds_lost'] or 0) / stats['total_birds_processed']
            ) * 100
        
        return Response({
            'total_batches': stats['total_batches'] or 0,
            'completed_batches': stats['completed_batches'] or 0,
            'pending_batches': stats['pending_batches'] or 0,
            'total_birds_processed': stats['total_birds_processed'] or 0,
            'total_birds_lost': stats['total_birds_lost'] or 0,
            'average_loss_rate_percent': round(avg_loss_rate, 2),
            'total_outputs_produced': total_outputs['total_quantity'] or 0,
            'total_processing_cost': stats['total_processing_cost'] or 0,
            'stale_stock_count': stale_count,
            'expiring_soon_count': expiring_count,
            'by_processing_type': by_type
        })


class ProcessingOutputViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual processing outputs.
    
    Most output operations should go through the batch's add_outputs endpoint,
    but this provides direct access for updates and deletes.
    """
    
    permission_classes = [IsFarmOwnerOrAdmin]
    serializer_class = ProcessingOutputSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        """Get outputs filtered by user's access."""
        user = self.request.user
        
        queryset = ProcessingOutput.objects.select_related(
            'processing_batch__farm',
            'marketplace_product'
        )
        
        # Filter by farm ownership for non-admins
        # Farm model uses 'user' field (OneToOneField) for ownership
        if not user.is_staff and user.role not in ['super_admin', 'national_admin']:
            queryset = queryset.filter(processing_batch__farm__user=user)
        
        # Query param filters
        batch_id = self.request.query_params.get('batch')
        batch_id_alt = self.request.query_params.get('batch_id')
        batch_number = self.request.query_params.get('batch_number')
        if batch_id or batch_id_alt:
            queryset = queryset.filter(processing_batch_id=batch_id or batch_id_alt)
        if batch_number:
            queryset = queryset.filter(processing_batch__batch_number=batch_number)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(product_category=category)
        
        expiring = self.request.query_params.get('expiring')
        if expiring == 'true':
            expiry_window = timezone.now().date() + timedelta(days=3)
            queryset = queryset.filter(
                expiry_date__lte=expiry_window,
                expiry_date__gte=timezone.now().date()
            )
        
        expired = self.request.query_params.get('expired')
        if expired == 'true':
            queryset = queryset.filter(
                expiry_date__lt=timezone.now().date()
            )
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action in ['create']:
            return ProcessingOutputCreateSerializer
        return ProcessingOutputSerializer
    
    @action(detail=True, methods=['post'], url_path='allocate-cost')
    def allocate_cost(self, request, id=None):
        """Allocate batch cost to this output."""
        output = self.get_object()
        
        method = request.data.get('method', 'quantity')
        
        if method == 'weight':
            output.allocate_cost_by_weight()
        else:
            output.allocate_cost_by_quantity()
        
        return Response({
            'message': f'Cost allocated by {method}',
            'output': ProcessingOutputSerializer(output).data
        })


class StaleStockReportView(APIView):
    """
    API endpoint for stale stock reporting.
    
    Used by:
    - Government admins: See all farms with old/stale processed stock
    - Farmers: See their own farm's stale stock
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get stale stock report.
        
        Query params:
        - days_threshold: Days since production to consider stale (default: 7)
        - include_expired: Include already expired items (default: true)
        - region: Filter by region (admin only)
        - constituency: Filter by constituency (admin only)
        """
        days_threshold = int(request.query_params.get('days_threshold', 7))
        include_expired = request.query_params.get('include_expired', 'true').lower() == 'true'
        threshold_date = timezone.now().date() - timedelta(days=days_threshold)
        
        # Check if user is admin or farmer (using uppercase role values)
        from accounts.models import User
        is_admin = request.user.role in [
            User.UserRole.SUPER_ADMIN,
            User.UserRole.NATIONAL_ADMIN,
            User.UserRole.REGIONAL_COORDINATOR,
            User.UserRole.CONSTITUENCY_OFFICIAL,
            User.UserRole.YEA_OFFICIAL,
        ]
        is_farmer = request.user.role == User.UserRole.FARMER
        
        # Base query
        stale_outputs = ProcessingOutput.objects.filter(
            inventory_updated=True,
            production_date__lte=threshold_date,
            processing_batch__status=ProcessingBatchStatus.COMPLETED
        ).select_related(
            'processing_batch__farm',
            'processing_batch__source_flock'
        )
        
        # Filter by expiry if requested
        if not include_expired:
            stale_outputs = stale_outputs.filter(
                expiry_date__gte=timezone.now().date()
            )
        
        if is_farmer:
            # Farmers only see their own farm's stale stock
            try:
                farm = Farm.objects.get(user=request.user)
                stale_outputs = stale_outputs.filter(processing_batch__farm=farm)
            except Farm.DoesNotExist:
                return Response({
                    'error': 'No farm found for this user',
                    'code': 'NO_FARM'
                }, status=status.HTTP_400_BAD_REQUEST)
        elif is_admin:
            # Regional filtering for regional coordinators
            if request.user.role == User.UserRole.REGIONAL_COORDINATOR and hasattr(request.user, 'region'):
                stale_outputs = stale_outputs.filter(
                    processing_batch__farm__primary_region=request.user.region
                )
            
            # Query param region filter
            region = request.query_params.get('region')
            if region:
                stale_outputs = stale_outputs.filter(
                    processing_batch__farm__primary_region=region
                )
            
            constituency = request.query_params.get('constituency')
            if constituency:
                stale_outputs = stale_outputs.filter(
                    processing_batch__farm__primary_constituency=constituency
                )
        else:
            # Other roles don't have access
            return Response({
                'error': 'Access denied. Only farmers and admins can view stale stock reports.',
                'code': 'ACCESS_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Build report
        report_data = []
        for output in stale_outputs:
            report_data.append({
                'output_id': str(output.id),
                'product_category': output.product_category,
                'product_category_display': output.get_product_category_display(),
                'quantity': output.quantity,
                'production_date': output.production_date,
                'expiry_date': output.expiry_date,
                'age_days': output.age_days,
                'days_until_expiry': output.days_until_expiry,
                'is_expired': output.is_expired,
                'farm_id': str(output.processing_batch.farm.id),
                'farm_name': output.processing_batch.farm.farm_name,
                'farm_region': output.processing_batch.farm.primary_region,
                'farm_constituency': output.processing_batch.farm.primary_constituency,
                'batch_number': output.processing_batch.batch_number,
                'processing_date': output.processing_batch.processing_date,
            })
        
        # Summary by region
        regional_summary = {}
        for item in report_data:
            region = item['farm_region']
            if region not in regional_summary:
                regional_summary[region] = {
                    'region': region,
                    'farms_affected': set(),
                    'total_stale_outputs': 0,
                    'total_quantity': 0,
                    'expired_count': 0
                }
            regional_summary[region]['farms_affected'].add(item['farm_id'])
            regional_summary[region]['total_stale_outputs'] += 1
            regional_summary[region]['total_quantity'] += item['quantity']
            if item['is_expired']:
                regional_summary[region]['expired_count'] += 1
        
        # Convert sets to counts
        for region, data in regional_summary.items():
            data['farms_affected'] = len(data['farms_affected'])
        
        return Response({
            'report_date': timezone.now().isoformat(),
            'days_threshold': days_threshold,
            'total_stale_outputs': len(report_data),
            'total_farms_affected': len(set(item['farm_id'] for item in report_data)),
            'regional_summary': list(regional_summary.values()),
            'stale_stock': report_data
        })


class FlockProcessingHistoryView(APIView):
    """
    Get processing history for a specific flock.
    
    Shows the complete lifecycle:
    - Initial count
    - Birds sold live
    - Birds processed
    - Current count remaining
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, flock_id):
        """Get processing history for a flock."""
        from flock_management.models import Flock
        from .models import BirdSale
        
        try:
            flock = Flock.objects.get(id=flock_id)
        except Flock.DoesNotExist:
            return Response({
                'error': 'Flock not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check access
        # Farm model uses 'user' field (OneToOneField) for ownership
        if not request.user.is_staff:
            if flock.farm.user != request.user:
                return Response({
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Get processing batches
        processing_batches = ProcessingBatch.objects.filter(
            source_flock=flock
        ).order_by('-processing_date')
        
        total_processed = processing_batches.aggregate(
            total=Sum('birds_processed')
        )['total'] or 0
        
        # Get live bird sales (approximate - from BirdsReadyForMarket or BirdSale)
        total_sold_live = 0
        try:
            from .inventory_models import BirdsReadyForMarket
            sold_live = BirdsReadyForMarket.objects.filter(
                flock=flock
            ).aggregate(total=Sum('quantity'))['total'] or 0
            total_sold_live = sold_live
        except:
            pass
        
        return Response({
            'flock_id': str(flock.id),
            'flock_name': getattr(flock, 'name', str(flock)),
            'flock_type': flock.flock_type,
            'breed': flock.breed,
            'initial_count': flock.initial_count,
            'current_count': flock.current_count,
            'total_processed': total_processed,
            'total_sold_live': total_sold_live,
            'total_mortality': flock.total_mortality,
            'unaccounted': flock.initial_count - flock.current_count - total_processed - total_sold_live - flock.total_mortality,
            'processing_batches': ProcessingBatchListSerializer(processing_batches, many=True).data,
            'pathways_summary': {
                'live_sales': {
                    'count': total_sold_live,
                    'percentage': round((total_sold_live / flock.initial_count) * 100, 1) if flock.initial_count > 0 else 0
                },
                'processed': {
                    'count': total_processed,
                    'percentage': round((total_processed / flock.initial_count) * 100, 1) if flock.initial_count > 0 else 0
                },
                'mortality': {
                    'count': flock.total_mortality,
                    'percentage': round((flock.total_mortality / flock.initial_count) * 100, 1) if flock.initial_count > 0 else 0
                },
                'remaining': {
                    'count': flock.current_count,
                    'percentage': round((flock.current_count / flock.initial_count) * 100, 1) if flock.initial_count > 0 else 0
                }
            }
        })
