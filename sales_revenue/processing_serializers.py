"""
Serializers for Processing Batch and Output models.

WEIGHT-BASED TRACKING:
- Processed products are tracked in KILOGRAMS (kg), not pieces
- Flow: 100 birds → processing → 400 kg products
- Sales: Sold 200 kg → 200 kg remaining

Handles:
- Creating processing batches with flock deduction
- Adding outputs (in kg) to batches
- Completing batches with inventory updates (in kg)
- Analytics and reporting
"""

from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .processing_models import (
    ProcessingBatch, 
    ProcessingOutput, 
    ProcessingBatchStatus,
    ProcessingType,
    ProductCategory,
    ProductGrade
)


class ProcessingOutputSerializer(serializers.ModelSerializer):
    """
    Serializer for processing outputs (products).
    
    PRIMARY UNIT: weight_kg (kilograms)
    - Processed products are measured in kg
    - quantity (pieces) is optional for reference
    """
    
    product_category_display = serializers.CharField(
        source='get_product_category_display', 
        read_only=True
    )
    grade_display = serializers.CharField(
        source='get_grade_display', 
        read_only=True
    )
    # Primary field: weight_kg (now writable)
    weight_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Total weight in kilograms (PRIMARY UNIT for processed products)'
    )
    total_weight_kg = serializers.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        read_only=True
    )
    cost_per_kg = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    cost_per_unit = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    age_days = serializers.IntegerField(read_only=True)
    
    # Marketplace product info
    marketplace_product_name = serializers.CharField(
        source='marketplace_product.name', 
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = ProcessingOutput
        fields = [
            'id',
            'processing_batch',
            'product_category',
            'product_category_display',
            'weight_kg',  # PRIMARY: Total weight in kg
            'quantity',   # OPTIONAL: Piece count for reference
            'unit',
            'unit_weight_kg',  # Optional: Weight per piece
            'total_weight_kg',
            'grade',
            'grade_display',
            'production_date',
            'expiry_date',
            'shelf_life_days',
            'marketplace_product',
            'marketplace_product_name',
            'allocated_cost',
            'cost_per_kg',    # Cost per kilogram
            'cost_per_unit',  # Cost per piece (if tracking pieces)
            'cost_allocation_method',
            'inventory_updated',
            'inventory_updated_at',
            'days_until_expiry',
            'is_expired',
            'age_days',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 
            'inventory_updated', 
            'inventory_updated_at',
            'created_at', 
            'updated_at'
        ]


class ProcessingOutputCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating processing outputs.
    
    PRIMARY UNIT: weight_kg (kilograms)
    - weight_kg is REQUIRED
    - quantity (pieces) is OPTIONAL for reference
    """
    
    weight_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        help_text='Total weight in kilograms (REQUIRED - primary unit for processed products)'
    )
    quantity = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='Optional: Number of pieces for reference (not used for inventory tracking)'
    )
    
    class Meta:
        model = ProcessingOutput
        fields = [
            'product_category',
            'weight_kg',      # PRIMARY: Total weight in kg (REQUIRED)
            'quantity',       # OPTIONAL: Piece count
            'unit',           # Default: 'kg'
            'unit_weight_kg', # OPTIONAL: Weight per piece
            'grade',
            'production_date',
            'expiry_date',
            'shelf_life_days',
            'marketplace_product',
            'allocated_cost',
            'cost_allocation_method',
        ]


class ProcessingBatchSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for processing batches.
    
    WEIGHT-BASED TRACKING:
    - average_bird_weight_kg: Average weight per bird (e.g., 4.0 kg)
    - expected_yield_weight_kg: birds_processed × average_bird_weight_kg
    - actual_yield_weight_kg: Sum of all output weights
    - yield_efficiency_percent: actual / expected × 100
    """
    
    # Read-only computed fields
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    processing_type_display = serializers.CharField(
        source='get_processing_type_display', 
        read_only=True
    )
    total_cost = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    birds_successfully_processed = serializers.IntegerField(read_only=True)
    loss_rate_percent = serializers.FloatField(read_only=True)
    total_output_quantity = serializers.IntegerField(read_only=True)
    total_output_weight_kg = serializers.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        read_only=True
    )
    yield_per_bird_kg = serializers.DecimalField(
        max_digits=8, 
        decimal_places=3, 
        read_only=True,
        help_text='Actual weight yield per bird (kg)'
    )
    yield_efficiency_percent = serializers.FloatField(
        read_only=True,
        help_text='Actual yield vs expected yield (%)'
    )
    weight_per_bird_actual = serializers.FloatField(
        read_only=True,
        help_text='Actual average weight per bird processed (kg)'
    )
    
    # Related objects
    outputs = ProcessingOutputSerializer(many=True, read_only=True)
    
    # Source info
    farm_name = serializers.CharField(
        source='farm.farm_name', 
        read_only=True
    )
    flock_name = serializers.CharField(
        source='source_flock.flock_number', 
        read_only=True,
        allow_null=True
    )
    flock_breed = serializers.CharField(
        source='source_flock.breed', 
        read_only=True,
        allow_null=True
    )
    flock_current_count = serializers.IntegerField(
        source='source_flock.current_count', 
        read_only=True
    )
    processed_by_name = serializers.CharField(
        source='processed_by.full_name', 
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = ProcessingBatch
        fields = [
            'id',
            'farm',
            'farm_name',
            'source_flock',
            'flock_name',
            'flock_breed',
            'flock_current_count',
            'source_birds_ready',
            'batch_number',
            'birds_processed',
            'processing_date',
            'processing_type',
            'processing_type_display',
            # Weight-based tracking
            'average_bird_weight_kg',
            'expected_yield_weight_kg',
            'actual_yield_weight_kg',
            'yield_efficiency_percent',
            'weight_per_bird_actual',
            # Costs
            'bird_cost_per_unit',
            'labor_cost',
            'processing_cost',
            'packaging_cost',
            'total_cost',
            'birds_lost_in_processing',
            'loss_reason',
            'birds_successfully_processed',
            'loss_rate_percent',
            'status',
            'status_display',
            'completed_at',
            'inventory_updated',
            'notes',
            'outputs',
            'total_output_quantity',
            'total_output_weight_kg',
            'yield_per_bird_kg',
            'processed_by',
            'processed_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'batch_number',
            'completed_at',
            'inventory_updated',
            'expected_yield_weight_kg',  # Auto-calculated
            'actual_yield_weight_kg',    # Auto-calculated from outputs
            'created_at',
            'updated_at',
        ]


class ProcessingBatchCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating processing batches.
    
    WEIGHT-BASED TRACKING:
    - average_bird_weight_kg: Estimated weight per bird (e.g., 4.0 kg)
    - Expected yield = birds_processed × average_bird_weight_kg
    
    On creation:
    1. Validates birds are available in source flock
    2. Deducts birds from flock
    3. Creates the batch with weight estimates
    """
    
    outputs = ProcessingOutputCreateSerializer(many=True, required=False)
    deduct_from_flock = serializers.BooleanField(
        default=True, 
        write_only=True,
        help_text='If true, automatically deduct birds from source flock on creation'
    )
    average_bird_weight_kg = serializers.DecimalField(
        max_digits=6,
        decimal_places=3,
        required=False,
        allow_null=True,
        help_text='Estimated average weight per bird in kg (e.g., 4.0). Used to calculate expected yield.'
    )
    
    class Meta:
        model = ProcessingBatch
        fields = [
            'farm',
            'source_flock',
            'source_birds_ready',
            'birds_processed',
            'average_bird_weight_kg',  # Weight-based: Expected yield = birds × avg_weight
            'processing_date',
            'processing_type',
            'bird_cost_per_unit',
            'labor_cost',
            'processing_cost',
            'packaging_cost',
            'birds_lost_in_processing',
            'loss_reason',
            'notes',
            'outputs',
            'deduct_from_flock',
        ]
    
    def validate(self, attrs):
        """Validate processing batch data."""
        source_flock = attrs.get('source_flock')
        birds_processed = attrs.get('birds_processed', 0)
        deduct_from_flock = attrs.pop('deduct_from_flock', True)
        
        # Store for use in create
        self.context['deduct_from_flock'] = deduct_from_flock
        
        # Validate source flock has enough birds
        if source_flock and hasattr(source_flock, 'current_count'):
            if birds_processed > source_flock.current_count:
                raise serializers.ValidationError({
                    'birds_processed': f'Cannot process {birds_processed} birds. '
                                      f'Flock only has {source_flock.current_count} birds available.'
                })
        
        # Validate losses don't exceed processed
        birds_lost = attrs.get('birds_lost_in_processing', 0)
        if birds_lost > birds_processed:
            raise serializers.ValidationError({
                'birds_lost_in_processing': 'Birds lost cannot exceed birds processed.'
            })
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """Create processing batch with optional flock deduction."""
        outputs_data = validated_data.pop('outputs', [])
        deduct_from_flock = self.context.get('deduct_from_flock', True)
        
        # Set the user who is processing
        if 'request' in self.context:
            validated_data['processed_by'] = self.context['request'].user
        
        # Create batch
        batch = ProcessingBatch.objects.create(**validated_data)
        
        # Deduct from flock if requested
        if deduct_from_flock:
            batch.deduct_from_flock()
            batch.status = ProcessingBatchStatus.IN_PROGRESS
            batch.save(update_fields=['status'])
        
        # Create outputs if provided
        for output_data in outputs_data:
            ProcessingOutput.objects.create(
                processing_batch=batch,
                **output_data
            )
        
        return batch


class ProcessingBatchUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating processing batches."""
    
    class Meta:
        model = ProcessingBatch
        fields = [
            'birds_lost_in_processing',
            'loss_reason',
            'labor_cost',
            'processing_cost',
            'packaging_cost',
            'notes',
        ]
    
    def validate(self, attrs):
        """Prevent updates to completed batches."""
        if self.instance and self.instance.status == ProcessingBatchStatus.COMPLETED:
            raise serializers.ValidationError(
                'Cannot update a completed processing batch.'
            )
        return attrs


class ProcessingBatchCompleteSerializer(serializers.Serializer):
    """Serializer for completing a processing batch."""
    
    force_complete = serializers.BooleanField(
        default=False,
        help_text='Force completion even if no outputs are defined'
    )
    
    def validate(self, attrs):
        batch = self.context.get('batch')
        force = attrs.get('force_complete', False)
        
        if not batch:
            raise serializers.ValidationError('No batch provided')
        
        if batch.status == ProcessingBatchStatus.COMPLETED:
            raise serializers.ValidationError('Batch is already completed')
        
        if batch.status == ProcessingBatchStatus.CANCELLED:
            raise serializers.ValidationError('Cannot complete a cancelled batch')
        
        if not force and not batch.outputs.exists():
            raise serializers.ValidationError(
                'Cannot complete batch without any outputs. '
                'Add outputs first or set force_complete=true.'
            )
        
        return attrs


class ProcessingBatchCancelSerializer(serializers.Serializer):
    """Serializer for cancelling a processing batch."""
    
    reason = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text='Reason for cancellation'
    )
    restore_flock = serializers.BooleanField(
        default=True,
        help_text='Restore birds back to source flock'
    )


class BulkOutputCreateSerializer(serializers.Serializer):
    """Serializer for bulk-creating outputs for a batch."""
    
    outputs = ProcessingOutputCreateSerializer(many=True)
    auto_allocate_costs = serializers.BooleanField(
        default=True,
        help_text='Automatically allocate batch costs to outputs'
    )
    allocation_method = serializers.ChoiceField(
        choices=[('weight', 'By Weight'), ('quantity', 'By Quantity')],
        default='quantity'
    )


class ProcessingBatchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing processing batches."""
    
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    processing_type_display = serializers.CharField(
        source='get_processing_type_display', 
        read_only=True
    )
    farm_name = serializers.CharField(
        source='farm.farm_name', 
        read_only=True
    )
    flock_name = serializers.CharField(
        source='source_flock.flock_number', 
        read_only=True,
        allow_null=True
    )
    output_count = serializers.IntegerField(read_only=True)
    total_cost = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = ProcessingBatch
        fields = [
            'id',
            'batch_number',
            'farm',
            'farm_name',
            'source_flock',
            'flock_name',
            'birds_processed',
            'birds_lost_in_processing',
            'processing_date',
            'processing_type',
            'processing_type_display',
            'status',
            'status_display',
            'inventory_updated',
            'total_cost',
            'output_count',
            'created_at',
        ]


# Analytics Serializers

class StaleStockReportSerializer(serializers.Serializer):
    """Serializer for stale stock reports."""
    
    output_id = serializers.UUIDField(source='id')
    product_category = serializers.CharField()
    product_category_display = serializers.CharField(
        source='get_product_category_display'
    )
    quantity = serializers.IntegerField()
    production_date = serializers.DateField()
    expiry_date = serializers.DateField(allow_null=True)
    age_days = serializers.IntegerField()
    days_until_expiry = serializers.IntegerField(allow_null=True)
    is_expired = serializers.BooleanField()
    
    # Farm info
    farm_id = serializers.UUIDField(source='processing_batch.farm.id')
    farm_name = serializers.CharField(source='processing_batch.farm.farm_name')
    farm_region = serializers.CharField(source='processing_batch.farm.primary_region')
    
    # Batch info
    batch_number = serializers.CharField(source='processing_batch.batch_number')
    processing_date = serializers.DateField(source='processing_batch.processing_date')


class ProcessingAnalyticsSerializer(serializers.Serializer):
    """Serializer for processing analytics summary."""
    
    total_batches = serializers.IntegerField()
    completed_batches = serializers.IntegerField()
    pending_batches = serializers.IntegerField()
    total_birds_processed = serializers.IntegerField()
    total_birds_lost = serializers.IntegerField()
    average_loss_rate_percent = serializers.FloatField()
    total_outputs_produced = serializers.IntegerField()
    total_processing_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    
    # Stale stock summary
    stale_stock_count = serializers.IntegerField()
    expiring_soon_count = serializers.IntegerField()
    
    # By processing type breakdown
    by_processing_type = serializers.ListField(
        child=serializers.DictField()
    )


class FlockProcessingHistorySerializer(serializers.Serializer):
    """Serializer for flock's processing history."""
    
    flock_id = serializers.UUIDField()
    flock_name = serializers.CharField()
    initial_count = serializers.IntegerField()
    current_count = serializers.IntegerField()
    total_processed = serializers.IntegerField()
    total_sold_live = serializers.IntegerField()
    total_mortality = serializers.IntegerField()
    processing_batches = ProcessingBatchListSerializer(many=True)
