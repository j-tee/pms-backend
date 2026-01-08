"""
Feed Inventory API Views

Provides endpoints for managing feed inventory, purchases, and consumption.
"""

import json
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farms.models import Farm
from flock_management.models import Flock, DailyProduction

from .models import FeedInventory, FeedPurchase, FeedType, FeedConsumption


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for feed inventory views."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response_data(self, data):
        """Return pagination metadata with results."""
        return {
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        }


class FeedPurchaseView(APIView):
    """
    GET  /api/feed/purchases/ - List all feed purchases
    POST /api/feed/purchases/ - Create a new feed purchase record
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def _serialize_purchase(self, purchase):
        """Serialize a single feed purchase record."""
        return {
            'id': str(purchase.id),
            'batch_number': purchase.batch_number,
            'purchase_date': purchase.purchase_date.isoformat(),
            'delivery_date': purchase.delivery_date.isoformat() if purchase.delivery_date else None,
            'supplier': purchase.supplier,
            'supplier_contact': purchase.supplier_contact,
            'feed_type': purchase.feed_type.name,
            'feed_type_id': str(purchase.feed_type_id),
            'brand': purchase.brand,
            'quantity_bags': purchase.quantity_bags,
            'bag_weight_kg': float(purchase.bag_weight_kg),
            'quantity_kg': float(purchase.quantity_kg),
            'stock_balance_kg': float(purchase.stock_balance_kg),
            'unit_cost_ghs': float(purchase.unit_cost_ghs),
            'unit_price': float(purchase.unit_price),
            'total_cost': float(purchase.total_cost),
            'payment_status': purchase.payment_status,
            'payment_method': purchase.payment_method,
            'amount_paid': float(purchase.amount_paid),
            'receipt_number': purchase.receipt_number,
            'invoice_number': purchase.invoice_number,
            'received_by': purchase.received_by,
            'notes': purchase.notes,
            'created_at': purchase.created_at.isoformat(),
            'created_by': purchase.created_by.email if purchase.created_by else None,
        }
    
    def get(self, request):
        """List all feed purchases for the farmer's farm."""
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)
        
        purchases = (
            FeedPurchase.objects.filter(farm=farm)
            .select_related('feed_type', 'created_by')
            .order_by('-purchase_date', '-created_at')
        )
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(purchases, request)
        
        if page is not None:
            data = [self._serialize_purchase(purchase) for purchase in page]
            return Response(paginator.get_paginated_response_data(data))
        
        # Fallback for non-paginated
        data = [self._serialize_purchase(purchase) for purchase in purchases]
        return Response({'results': data, 'count': len(data)})
    
    def post(self, request):
        """Create a feed purchase and update inventory."""
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)
        
        # Extract and validate required fields
        feed_type_name = request.data.get('feed_type')
        if not feed_type_name:
            return Response({'error': 'feed_type is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create feed type
        feed_type, created = FeedType.objects.get_or_create(
            name=feed_type_name,
            defaults={
                'category': 'LAYER',
                'form': 'MASH',
                'protein_content': Decimal('16.0'),
                'is_active': True,
            },
        )
        
        # Extract fields from request
        brand = request.data.get('brand', '')
        supplier = request.data.get('supplier', '')
        supplier_contact = request.data.get('supplier_contact', '')
        quantity_bags = self._to_int(request.data.get('quantity_bags'), 1)
        bag_weight_kg = self._to_decimal(request.data.get('bag_weight_kg'), 50)
        unit_cost_ghs = self._to_decimal(request.data.get('unit_cost_ghs'), 0)
        receipt_number = request.data.get('receipt_number', '')
        purchase_date = self._parse_date(request.data.get('purchase_date'))
        delivery_date = self._parse_date(request.data.get('delivery_date'))
        payment_method = request.data.get('payment_method', '')
        payment_status = request.data.get('payment_status', 'Paid').upper()
        notes = request.data.get('notes', '')
        
        if not purchase_date:
            purchase_date = timezone.now().date()
        
        # Validate payment status
        valid_statuses = ['PENDING', 'PARTIAL', 'PAID', 'OVERDUE']
        if payment_status not in valid_statuses:
            payment_status = 'PAID'
        
        # Create purchase record
        try:
            with transaction.atomic():
                purchase = FeedPurchase(
                    farm=farm,
                    supplier=supplier,
                    supplier_contact=supplier_contact,
                    feed_type=feed_type,
                    brand=brand,
                    purchase_date=purchase_date,
                    delivery_date=delivery_date or purchase_date,
                    receipt_number=receipt_number,
                    quantity_bags=quantity_bags,
                    bag_weight_kg=bag_weight_kg,
                    unit_cost_ghs=unit_cost_ghs,
                    payment_status=payment_status,
                    payment_method=payment_method,
                    received_by=request.user.email,
                    notes=notes,
                    created_by=request.user,
                )
                purchase.full_clean()
                purchase.save()
                
                # After save, purchase object now has calculated quantity_kg and unit_price
                # Update inventory
                inventory, inv_created = FeedInventory.objects.get_or_create(
                    farm=farm,
                    feed_type=feed_type,
                    defaults={
                        'current_stock_kg': Decimal('0.0'),
                        'min_stock_level': Decimal('50.0'),
                        'max_stock_level': Decimal('10000.0'),
                        'average_cost_per_kg': purchase.unit_price,
                    },
                )
                
                # Update inventory with weighted average cost
                old_value = inventory.current_stock_kg * inventory.average_cost_per_kg
                new_value = purchase.quantity_kg * purchase.unit_price
                total_new_stock = inventory.current_stock_kg + purchase.quantity_kg
                
                if total_new_stock > 0:
                    inventory.average_cost_per_kg = (old_value + new_value) / total_new_stock
                
                inventory.current_stock_kg = total_new_stock
                inventory.last_purchase_date = purchase_date
                inventory.save()
        
        except Exception as exc:
            from django.core.exceptions import ValidationError
            
            if isinstance(exc, ValidationError):
                return Response({'errors': exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            {
                'success': True,
                'message': 'Feed purchase created successfully',
                'purchase_id': str(purchase.id),
                'batch_number': purchase.batch_number,
                'stock_balance_kg': float(purchase.stock_balance_kg),
                'inventory_id': str(inventory.id),
            },
            status=status.HTTP_201_CREATED,
        )
    
    def _get_farm(self, request):
        try:
            return Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return None
    
    def _parse_date(self, date_str):
        if not date_str:
            return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except Exception:
                continue
        try:
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00')).date()
        except Exception:
            return None
    
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
                return Decimal(str(default))
            return Decimal(str(value))
        except Exception:
            return Decimal(str(default))


class FeedStockView(APIView):
    """
    POST /api/feed/create/
    GET  /api/feed/stock/

    Add new feed stock (purchase) and list current inventory.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def _serialize_inventory(self, inv):
        """Serialize a single inventory record."""
        return {
            'id': str(inv.id),
            'feed_type': inv.feed_type.name,
            'feed_type_id': str(inv.feed_type_id),
            'current_stock_kg': float(inv.current_stock_kg),
            'min_stock_level': float(inv.min_stock_level),
            'max_stock_level': float(inv.max_stock_level),
            'average_cost_per_kg': float(inv.average_cost_per_kg),
            'total_value': float(inv.total_value),
            'low_stock_alert': inv.low_stock_alert,
            'storage_location': inv.storage_location,
            'last_purchase_date': inv.last_purchase_date.isoformat() if inv.last_purchase_date else None,
            'updated_at': inv.updated_at.isoformat(),
        }

    def get(self, request):
        """List current feed inventory for the farmer's farm."""
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        inventory = (
            FeedInventory.objects.filter(farm=farm)
            .select_related('feed_type')
            .order_by('feed_type__name')
        )

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(inventory, request)
        
        if page is not None:
            data = [self._serialize_inventory(inv) for inv in page]
            return Response(paginator.get_paginated_response_data(data))
        
        # Fallback for non-paginated
        data = [self._serialize_inventory(inv) for inv in inventory]
        return Response({'results': data, 'count': len(data)})

    def post(self, request):
        """Create a feed purchase and update inventory."""
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)

        # Extract and validate payload
        feed_type_name = request.data.get('feed_type')
        if not feed_type_name:
            return Response({'error': 'feed_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create feed type
        feed_type, created = FeedType.objects.get_or_create(
            name=feed_type_name,
            defaults={
                'category': 'LAYER',  # Default category
                'form': 'MASH',
                'protein_content': Decimal('16.0'),
                'is_active': True,
            },
        )

        brand = request.data.get('brand', '')
        supplier_name = request.data.get('supplier', '')
        batch_number = request.data.get('batch_number', '')
        quantity_bags = self._to_int(request.data.get('quantity_bags'), 1)
        bag_weight_kg = self._to_decimal(request.data.get('bag_weight_kg'), 50)
        unit_cost_ghs = self._to_decimal(request.data.get('unit_cost_ghs'), 0)
        storage_location = request.data.get('storage_location', '')
        purchase_date = self._parse_date(request.data.get('purchase_date') or request.data.get('date'))
        expiry_date = self._parse_date(request.data.get('expiry_date'))
        reorder_level = self._to_int(request.data.get('reorder_level'), 43)
        notes = request.data.get('notes', '')

        if not purchase_date:
            purchase_date = timezone.now().date()

        # Calculate total quantity
        total_quantity_kg = Decimal(quantity_bags) * bag_weight_kg

        # Create purchase record
        try:
            with transaction.atomic():
                purchase = FeedPurchase(
                    farm=farm,
                    supplier=supplier_name or '',
                    feed_type=feed_type,
                    brand=brand,
                    purchase_date=purchase_date,
                    delivery_date=purchase_date,
                    invoice_number=batch_number,
                    quantity_bags=quantity_bags,
                    bag_weight_kg=bag_weight_kg,
                    unit_cost_ghs=unit_cost_ghs,
                    payment_status='PAID',
                    amount_paid=total_quantity_kg * unit_cost_ghs / quantity_bags if quantity_bags > 0 else Decimal('0'),
                    received_by=request.user.email,
                    notes=notes,
                    created_by=request.user,
                )
                purchase.full_clean()
                purchase.save()

                # Update or create inventory
                inventory, inv_created = FeedInventory.objects.get_or_create(
                    farm=farm,
                    feed_type=feed_type,
                    defaults={
                        'current_stock_kg': Decimal('0.0'),
                        'min_stock_level': Decimal(str(reorder_level)),
                        'max_stock_level': Decimal('10000.0'),
                        'average_cost_per_kg': unit_cost_ghs,
                        'storage_location': storage_location,
                    },
                )

                # Calculate new weighted average cost
                old_value = inventory.current_stock_kg * inventory.average_cost_per_kg
                new_value = total_quantity_kg * unit_cost_ghs
                total_new_stock = inventory.current_stock_kg + total_quantity_kg

                if total_new_stock > 0:
                    inventory.average_cost_per_kg = (old_value + new_value) / total_new_stock

                inventory.current_stock_kg = total_new_stock
                inventory.last_purchase_date = purchase_date
                if storage_location:
                    inventory.storage_location = storage_location
                inventory.min_stock_level = Decimal(str(reorder_level))
                inventory.save()

        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                return Response({'errors': exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'success': True,
                'message': 'Feed stock added successfully',
                'purchase_id': str(purchase.id),
                'inventory_id': str(inventory.id),
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_farm(self, request):
        try:
            return Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return None

    def _parse_date(self, date_str):
        if not date_str:
            return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except Exception:
                continue
        try:
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00')).date()
        except Exception:
            return None

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
                return Decimal(str(default))
            return Decimal(str(value))
        except Exception:
            return Decimal(str(default))
