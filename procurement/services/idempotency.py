"""
Idempotency and Transaction Safety for Procurement Operations

This module provides utilities for:
1. State machine validation for status transitions
2. Idempotent operation decorators
3. Retry logic with exponential backoff
4. Distributed locking via cache
5. Row-level locking helpers

Key Principles:
- Every mutating operation should be idempotent (safe to retry)
- Use database locks to prevent race conditions
- Validate state transitions to ensure data consistency
- Log all operations for audit trail

Models (IdempotencyKey, ProcurementAuditLog) are defined in procurement/models.py
"""

from django.core.cache import cache
from django.utils import timezone
from functools import wraps
import uuid
import logging
import time
from typing import Callable, Any, Dict, List

logger = logging.getLogger(__name__)


# ==============================================================================
# STATE MACHINE FOR STATUS TRANSITIONS
# ==============================================================================

class StatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""
    pass


# Valid status transitions for ProcurementOrder
ORDER_STATUS_TRANSITIONS = {
    'draft': ['published', 'cancelled'],
    'published': ['assigning', 'assigned', 'cancelled'],
    'assigning': ['assigned', 'cancelled'],
    'assigned': ['in_progress', 'partially_delivered', 'cancelled'],
    'in_progress': ['partially_delivered', 'fully_delivered', 'cancelled'],
    'partially_delivered': ['fully_delivered', 'cancelled'],
    'fully_delivered': ['completed'],
    'completed': [],  # Terminal state
    'cancelled': [],  # Terminal state
}

# Valid status transitions for OrderAssignment
ASSIGNMENT_STATUS_TRANSITIONS = {
    'pending': ['accepted', 'rejected', 'cancelled'],
    'accepted': ['preparing', 'ready', 'cancelled'],  # Can skip preparing
    'rejected': [],  # Terminal state
    'preparing': ['ready', 'cancelled'],
    'ready': ['in_transit', 'delivered', 'cancelled'],
    'in_transit': ['delivered', 'cancelled'],
    'delivered': ['verified', 'cancelled'],
    'verified': ['paid'],
    'paid': [],  # Terminal state
    'cancelled': [],  # Terminal state
}

# Valid status transitions for ProcurementInvoice
INVOICE_STATUS_TRANSITIONS = {
    'pending': ['approved', 'disputed'],
    'approved': ['processing', 'paid', 'disputed'],  # Can go directly to paid
    'processing': ['paid', 'failed'],
    'paid': [],  # Terminal state
    'failed': ['processing', 'disputed'],  # Can retry
    'disputed': ['pending', 'approved'],  # Can resolve dispute
}


def validate_status_transition(current_status: str, new_status: str, 
                               transitions: Dict[str, List[str]], 
                               resource_type: str = 'resource') -> bool:
    """
    Validate that a status transition is allowed.
    
    Args:
        current_status: Current status of the resource
        new_status: Proposed new status
        transitions: Dict mapping status to list of valid next statuses
        resource_type: Name of resource for error messages
    
    Returns:
        True if transition is valid
    
    Raises:
        StatusTransitionError if transition is invalid
    """
    if current_status == new_status:
        return True  # No change is always valid
    
    valid_transitions = transitions.get(current_status, [])
    
    if new_status not in valid_transitions:
        raise StatusTransitionError(
            f"Invalid {resource_type} status transition: {current_status} -> {new_status}. "
            f"Valid transitions: {valid_transitions}"
        )
    
    return True


# ==============================================================================
# RETRY WITH EXPONENTIAL BACKOFF
# ==============================================================================

class RetryableError(Exception):
    """Exception that indicates an operation can be safely retried."""
    pass


def retry_on_failure(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    retryable_exceptions: tuple = (RetryableError,),
):
    """
    Decorator to retry an operation with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        retryable_exceptions: Tuple of exceptions that trigger retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                            f"after {delay:.2f}s: {str(e)}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All retries failed for {func.__name__}: {str(e)}")
                        raise
            
            raise last_exception
        
        return wrapper
    return decorator


# ==============================================================================
# LOCKING UTILITIES
# ==============================================================================

def with_row_lock(model_class, pk, nowait: bool = False):
    """
    Context manager to acquire a row-level lock.
    
    Usage:
        with with_row_lock(ProcurementOrder, order_id) as order:
            order.status = 'published'
            order.save()
    
    Args:
        model_class: Django model class
        pk: Primary key of the record
        nowait: If True, raise error instead of waiting for lock
    """
    class RowLockContext:
        def __init__(self, model_class, pk, nowait):
            self.model_class = model_class
            self.pk = pk
            self.nowait = nowait
            self.instance = None
        
        def __enter__(self):
            queryset = self.model_class.objects.filter(pk=self.pk)
            if self.nowait:
                queryset = queryset.select_for_update(nowait=True)
            else:
                queryset = queryset.select_for_update()
            
            self.instance = queryset.first()
            if not self.instance:
                raise self.model_class.DoesNotExist(
                    f"{self.model_class.__name__} with pk={self.pk} does not exist"
                )
            return self.instance
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            return False  # Don't suppress exceptions
    
    return RowLockContext(model_class, pk, nowait)


def acquire_distributed_lock(lock_name: str, ttl_seconds: int = 30) -> bool:
    """
    Acquire a distributed lock using cache.
    
    Args:
        lock_name: Unique name for the lock
        ttl_seconds: Lock timeout
    
    Returns:
        True if lock acquired, False otherwise
    """
    lock_key = f"lock:{lock_name}"
    lock_value = str(uuid.uuid4())
    
    # Use cache.add() which is atomic
    acquired = cache.add(lock_key, lock_value, ttl_seconds)
    
    if acquired:
        logger.debug(f"Acquired lock: {lock_name}")
    else:
        logger.debug(f"Failed to acquire lock: {lock_name}")
    
    return acquired


def release_distributed_lock(lock_name: str) -> bool:
    """
    Release a distributed lock.
    
    Args:
        lock_name: Unique name for the lock
    
    Returns:
        True if released, False if not held
    """
    lock_key = f"lock:{lock_name}"
    result = cache.delete(lock_key)
    
    if result:
        logger.debug(f"Released lock: {lock_name}")
    
    return result


class DistributedLock:
    """
    Context manager for distributed locks.
    
    Usage:
        with DistributedLock(f"order:{order_id}:assign"):
            # Only one process can execute this at a time
            assign_to_farm(order, farm, quantity)
    """
    
    def __init__(self, lock_name: str, ttl_seconds: int = 30, 
                 wait: bool = True, max_wait: float = 10.0):
        self.lock_name = lock_name
        self.ttl_seconds = ttl_seconds
        self.wait = wait
        self.max_wait = max_wait
        self.acquired = False
    
    def __enter__(self):
        start_time = time.time()
        
        while True:
            self.acquired = acquire_distributed_lock(self.lock_name, self.ttl_seconds)
            
            if self.acquired:
                return self
            
            if not self.wait:
                raise Exception(f"Could not acquire lock: {self.lock_name}")
            
            elapsed = time.time() - start_time
            if elapsed > self.max_wait:
                raise Exception(
                    f"Timeout waiting for lock: {self.lock_name} after {elapsed:.2f}s"
                )
            
            time.sleep(0.1)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            release_distributed_lock(self.lock_name)
        return False


# ==============================================================================
# IDEMPOTENT OPERATION DECORATOR
# ==============================================================================

def idempotent_operation(
    operation_name: str,
    resource_type: str,
    get_resource_id: Callable = None,
    ttl_seconds: int = 86400,  # 24 hours default
    use_cache: bool = True,
):
    """
    Decorator to make an operation idempotent.
    
    Usage:
        @idempotent_operation('assign_farm', 'OrderAssignment', 
                              get_resource_id=lambda args, kwargs: kwargs.get('order').id)
        def assign_to_farm(self, order, farm, quantity, idempotency_key=None):
            ...
    
    Args:
        operation_name: Name of the operation for logging
        resource_type: Type of resource being modified
        get_resource_id: Callable to extract resource ID from args/kwargs
        ttl_seconds: How long to cache the idempotency key
        use_cache: Whether to use cache for fast lookups
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Import here to avoid circular imports
            from procurement.models import IdempotencyKey, ProcurementAuditLog
            
            # Extract idempotency key from kwargs
            idempotency_key = kwargs.pop('idempotency_key', None)
            user = kwargs.get('user') or (args[1] if len(args) > 1 else None)
            
            # If no idempotency key provided, generate one
            if idempotency_key is None:
                # Generate based on operation parameters
                key_params = {
                    'operation': operation_name,
                    'resource_type': resource_type,
                }
                if get_resource_id:
                    try:
                        key_params['resource_id'] = str(get_resource_id(args, kwargs))
                    except:
                        pass
                
                # Add relevant kwargs to key
                for k, v in kwargs.items():
                    if k not in ['user', 'request']:
                        try:
                            if hasattr(v, 'id'):
                                key_params[k] = str(v.id)
                            else:
                                key_params[k] = str(v)
                        except:
                            pass
                
                user_id = str(user.id) if user and hasattr(user, 'id') else 'anonymous'
                idempotency_key = IdempotencyKey.generate_key(user_id, operation_name, **key_params)
            
            # Check cache first (faster)
            cache_key = f"idem:{idempotency_key}"
            if use_cache:
                cached = cache.get(cache_key)
                if cached:
                    logger.info(f"Idempotent cache hit for {operation_name}: {idempotency_key[:16]}...")
                    return cached
            
            # Check database
            try:
                existing = IdempotencyKey.objects.get(
                    key=idempotency_key,
                    expires_at__gt=timezone.now()
                )
                
                if existing.status == 'completed':
                    logger.info(f"Idempotent DB hit for {operation_name}: {idempotency_key[:16]}...")
                    return existing.response_data
                elif existing.status == 'processing':
                    # Another request is processing - wait briefly and check again
                    time.sleep(0.5)
                    existing.refresh_from_db()
                    if existing.status == 'completed':
                        return existing.response_data
                    raise Exception(f"Operation {operation_name} is already in progress")
            except IdempotencyKey.DoesNotExist:
                pass
            
            # Create idempotency record
            from datetime import timedelta
            expires_at = timezone.now() + timedelta(seconds=ttl_seconds)
            idem_record = IdempotencyKey.objects.create(
                key=idempotency_key,
                user_id=user.id if user and hasattr(user, 'id') else None,
                operation=operation_name,
                resource_type=resource_type,
                resource_id=str(get_resource_id(args, kwargs)) if get_resource_id else None,
                status='processing',
                expires_at=expires_at,
            )
            
            start_time = time.time()
            try:
                # Execute the operation
                result = func(*args, **kwargs)
                
                # Mark as completed
                duration_ms = int((time.time() - start_time) * 1000)
                idem_record.status = 'completed'
                idem_record.completed_at = timezone.now()
                idem_record.response_data = _serialize_result(result)
                idem_record.save()
                
                # Cache the result
                if use_cache:
                    cache.set(cache_key, idem_record.response_data, ttl_seconds)
                
                return result
                
            except Exception as e:
                # Mark as failed
                idem_record.status = 'failed'
                idem_record.completed_at = timezone.now()
                idem_record.response_data = {'error': str(e)}
                idem_record.save()
                
                raise
        
        return wrapper
    return decorator


def _serialize_result(result) -> Any:
    """Serialize a result for storage."""
    if result is None:
        return None
    if isinstance(result, (str, int, float, bool, list, dict)):
        return result
    if hasattr(result, 'id'):
        return {'id': str(result.id), 'type': result.__class__.__name__}
    return str(result)
