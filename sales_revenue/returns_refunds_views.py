"""
API views for Returns and Refunds functionality.
Provides endpoints for customers to request returns and for staff to process them.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .returns_refunds_models import ReturnRequest, ReturnItem, RefundTransaction
from .returns_refunds_serializers import (
    ReturnRequestListSerializer, ReturnRequestDetailSerializer,
    ReturnRequestCreateSerializer, ReturnApprovalSerializer,
    ItemsReceivedSerializer, IssueRefundSerializer,
    ReturnItemSerializer, RefundTransactionSerializer
)
from .marketplace_models import MarketplaceOrder
from accounts.policies import UserPolicy


class ReturnRequestListCreateView(generics.ListCreateAPIView):
    """
    List return requests or create a new return request.
    
    Customers see only their own return requests.
    Staff can see all return requests for their farm/jurisdiction.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ReturnRequestCreateSerializer
        return ReturnRequestListSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Customers see only their own returns
        if hasattr(user, 'customer_profile'):
            return ReturnRequest.objects.filter(
                customer=user.customer_profile
            ).order_by('-requested_at')
        
        # Staff see returns based on their permissions
        queryset = ReturnRequest.objects.all()
        
        # Filter by farm if user has a farm (farmers acting as sellers)
        if hasattr(user, 'farm'):
            queryset = queryset.filter(order__farm=user.farm)
        
        # Regional/constituency filtering
        if UserPolicy.is_regional_level(user):
            queryset = queryset.filter(order__farm__region=user.region)
        elif UserPolicy.is_constituency_level(user):
            queryset = queryset.filter(order__farm__constituency=user.constituency)
        
        # Apply filters from query params
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(requested_at__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(requested_at__lte=date_to)
        
        return queryset.select_related('order', 'customer', 'customer__user').order_by('-requested_at')
    
    def perform_create(self, serializer):
        """Create return request and notify seller."""
        return_request = serializer.save()
        
        # TODO: Send notification to seller about new return request
        # from core.tasks import send_return_request_notification
        # send_return_request_notification.delay(return_request.id)


class ReturnRequestDetailView(generics.RetrieveAPIView):
    """
    Retrieve detailed information about a specific return request.
    
    Customers can view their own returns.
    Sellers can view returns for their products.
    Staff can view based on permissions.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReturnRequestDetailSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        user = self.request.user
        
        queryset = ReturnRequest.objects.select_related(
            'order', 'customer', 'customer__user', 'approved_by', 'rejected_by'
        ).prefetch_related(
            'items__product', 'items__order_item', 'refund_transactions'
        )
        
        # Customers see only their own returns
        if hasattr(user, 'customer_profile'):
            return queryset.filter(customer=user.customer_profile)
        
        # Sellers see returns for their farm's products
        if hasattr(user, 'farm'):
            return queryset.filter(order__farm=user.farm)
        
        # Staff see based on jurisdiction
        if UserPolicy.is_regional_level(user):
            return queryset.filter(order__farm__region=user.region)
        elif UserPolicy.is_constituency_level(user):
            return queryset.filter(order__farm__constituency=user.constituency)
        
        # Super admin sees all
        if UserPolicy.is_platform_staff(user):
            return queryset
        
        return queryset.none()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_return_request(request, return_id):
    """
    Approve or reject a return request.
    
    Only the seller (farm owner) or staff can approve/reject returns.
    """
    return_request = get_object_or_404(
        ReturnRequest.objects.select_related('order', 'order__farm'),
        id=return_id
    )
    
    # Check permissions - only seller or authorized staff can approve
    user = request.user
    is_seller = hasattr(user, 'farm') and return_request.order.farm == user.farm
    is_authorized_staff = (
        UserPolicy.is_platform_staff(user) or
        (UserPolicy.is_regional_level(user) and return_request.order.farm.region == user.region) or
        (UserPolicy.is_constituency_level(user) and return_request.order.farm.constituency == user.constituency)
    )
    
    if not (is_seller or is_authorized_staff):
        raise PermissionDenied("You do not have permission to process this return request.")
    
    # Validate request data
    serializer = ReturnApprovalSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    approved = serializer.validated_data['approved']
    
    if approved:
        return_request.approve_return(
            approved_by=user,
            admin_notes=serializer.validated_data.get('admin_notes', '')
        )
        message = "Return request approved successfully."
    else:
        return_request.reject_return(
            rejected_by=user,
            reason=serializer.validated_data['rejection_reason'],
            admin_notes=serializer.validated_data.get('admin_notes', '')
        )
        message = "Return request rejected."
    
    # Return updated return request
    response_serializer = ReturnRequestDetailSerializer(return_request)
    return Response({
        'message': message,
        'return_request': response_serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_items_received(request, return_id):
    """
    Mark return items as received and assess their condition.
    
    Only seller or authorized staff can mark items as received.
    """
    return_request = get_object_or_404(
        ReturnRequest.objects.select_related('order', 'order__farm'),
        id=return_id
    )
    
    # Check permissions
    user = request.user
    is_seller = hasattr(user, 'farm') and return_request.order.farm == user.farm
    is_authorized_staff = (
        UserPolicy.is_platform_staff(user) or
        (UserPolicy.is_regional_level(user) and return_request.order.farm.region == user.region) or
        (UserPolicy.is_constituency_level(user) and return_request.order.farm.constituency == user.constituency)
    )
    
    if not (is_seller or is_authorized_staff):
        raise PermissionDenied("You do not have permission to process this return request.")
    
    # Validate request data
    serializer = ItemsReceivedSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    items_data = serializer.validated_data['items']
    admin_notes = serializer.validated_data.get('admin_notes', '')
    
    # Process items and mark as received
    return_request.mark_items_received(
        items_conditions=items_data,
        admin_notes=admin_notes
    )
    
    # Return updated return request
    response_serializer = ReturnRequestDetailSerializer(return_request)
    return Response({
        'message': 'Items marked as received and quality assessed.',
        'return_request': response_serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def issue_refund(request, return_id):
    """
    Issue refund to customer for approved return.
    
    Only seller or authorized staff can issue refunds.
    """
    return_request = get_object_or_404(
        ReturnRequest.objects.select_related('order', 'order__farm'),
        id=return_id
    )
    
    # Check permissions
    user = request.user
    is_seller = hasattr(user, 'farm') and return_request.order.farm == user.farm
    is_authorized_staff = (
        UserPolicy.is_platform_staff(user) or
        (UserPolicy.is_regional_level(user) and return_request.order.farm.region == user.region) or
        (UserPolicy.is_constituency_level(user) and return_request.order.farm.constituency == user.constituency)
    )
    
    if not (is_seller or is_authorized_staff):
        raise PermissionDenied("You do not have permission to process this return request.")
    
    # Validate request data
    serializer = IssueRefundSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Issue refund
    refund_transaction = return_request.issue_refund(
        initiated_by=user,
        payment_method=serializer.validated_data['payment_method'],
        payment_provider=serializer.validated_data.get('payment_provider', ''),
        transaction_id=serializer.validated_data.get('transaction_id', ''),
        notes=serializer.validated_data.get('notes', '')
    )
    
    # Return updated return request and refund transaction
    return_serializer = ReturnRequestDetailSerializer(return_request)
    refund_serializer = RefundTransactionSerializer(refund_transaction)
    
    return Response({
        'message': 'Refund issued successfully.',
        'return_request': return_serializer.data,
        'refund_transaction': refund_serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def complete_return(request, return_id):
    """
    Mark return as completed after refund has been issued.
    
    Only seller or authorized staff can complete returns.
    """
    return_request = get_object_or_404(
        ReturnRequest.objects.select_related('order', 'order__farm'),
        id=return_id
    )
    
    # Check permissions
    user = request.user
    is_seller = hasattr(user, 'farm') and return_request.order.farm == user.farm
    is_authorized_staff = (
        UserPolicy.is_platform_staff(user) or
        (UserPolicy.is_regional_level(user) and return_request.order.farm.region == user.region) or
        (UserPolicy.is_constituency_level(user) and return_request.order.farm.constituency == user.constituency)
    )
    
    if not (is_seller or is_authorized_staff):
        raise PermissionDenied("You do not have permission to process this return request.")
    
    # Complete the return
    return_request.complete_return()
    
    # Return updated return request
    response_serializer = ReturnRequestDetailSerializer(return_request)
    return Response({
        'message': 'Return completed successfully.',
        'return_request': response_serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def return_statistics(request):
    """
    Get statistics about returns for the current user's context.
    
    Returns counts by status, total refund amounts, etc.
    """
    user = request.user
    
    # Base queryset based on user role
    queryset = ReturnRequest.objects.all()
    
    if hasattr(user, 'customer_profile'):
        queryset = queryset.filter(customer=user.customer_profile)
    elif hasattr(user, 'farm'):
        queryset = queryset.filter(order__farm=user.farm)
    elif UserPolicy.is_regional_level(user):
        queryset = queryset.filter(order__farm__region=user.region)
    elif UserPolicy.is_constituency_level(user):
        queryset = queryset.filter(order__farm__constituency=user.constituency)
    elif not UserPolicy.is_platform_staff(user):
        queryset = queryset.none()
    
    # Calculate statistics
    stats = {
        'total_returns': queryset.count(),
        'by_status': {},
        'total_refund_amount': queryset.filter(
            status__in=['refund_issued', 'completed']
        ).aggregate(total=Sum('total_refund_amount'))['total'] or 0,
        'pending_count': queryset.filter(status='pending').count(),
        'approved_count': queryset.filter(status='approved').count(),
        'completed_count': queryset.filter(status='completed').count(),
        'rejected_count': queryset.filter(status='rejected').count(),
    }
    
    # Count by status
    status_counts = queryset.values('status').annotate(count=Count('id'))
    for item in status_counts:
        stats['by_status'][item['status']] = item['count']
    
    return Response(stats, status=status.HTTP_200_OK)
