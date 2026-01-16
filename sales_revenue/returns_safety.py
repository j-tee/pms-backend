"""
Returns/Refunds Safety Utilities

Provides atomicity and idempotency mechanisms for returns and refunds:
1. State machine validation for status transitions
2. Distributed locking for concurrent protection
3. Audit logging for compliance

These utilities mirror the procurement safety mechanisms but are specific
to the returns/refunds workflow.
"""

from django.core.cache import cache
from django.utils import timezone
from functools import wraps
import uuid
import logging
import time
from typing import Callable, Dict, List

logger = logging.getLogger(__name__)


# ==============================================================================
# STATE MACHINE FOR STATUS TRANSITIONS
# ==============================================================================

class ReturnStatusTransitionError(Exception):
    """Raised when an invalid return status transition is attempted."""
    pass


# Valid status transitions for ReturnRequest
RETURN_STATUS_TRANSITIONS = {
    'pending': ['approved', 'rejected', 'cancelled'],
    'approved': ['items_received', 'cancelled'],
    'rejected': [],  # Terminal state
    'items_received': ['refund_issued', 'cancelled'],
    'refund_issued': ['completed'],
    'completed': [],  # Terminal state
    'cancelled': [],  # Terminal state
}

# Valid status transitions for RefundTransaction
REFUND_STATUS_TRANSITIONS = {
    'pending': ['processing', 'completed', 'cancelled'],
    'processing': ['completed', 'failed'],
    'completed': [],  # Terminal state
    'failed': ['processing', 'pending'],  # Can retry
    'cancelled': [],  # Terminal state
}


def validate_return_status_transition(current_status: str, new_status: str, 
                                      resource_type: str = 'return') -> bool:
    """
    Validate that a return status transition is allowed.
    
    Args:
        current_status: Current status of the return
        new_status: Proposed new status
        resource_type: 'return' or 'refund' for error messages
    
    Returns:
        True if transition is valid
    
    Raises:
        ReturnStatusTransitionError if transition is invalid
    """
    if current_status == new_status:
        return True  # No change is always valid
    
    if resource_type == 'refund':
        transitions = REFUND_STATUS_TRANSITIONS
    else:
        transitions = RETURN_STATUS_TRANSITIONS
    
    valid_transitions = transitions.get(current_status, [])
    
    if new_status not in valid_transitions:
        raise ReturnStatusTransitionError(
            f"Invalid {resource_type} status transition: {current_status} -> {new_status}. "
            f"Valid transitions from '{current_status}': {valid_transitions}"
        )
    
    return True


def validate_refund_status_transition(current_status: str, new_status: str) -> bool:
    """
    Validate that a refund transaction status transition is allowed.
    
    Convenience wrapper around validate_return_status_transition for refunds.
    """
    return validate_return_status_transition(
        current_status, new_status, resource_type='refund'
    )


# ==============================================================================
# DISTRIBUTED LOCKING
# ==============================================================================

def acquire_return_lock(lock_name: str, ttl_seconds: int = 30) -> bool:
    """Acquire a distributed lock for return operations."""
    lock_key = f"return_lock:{lock_name}"
    lock_value = str(uuid.uuid4())
    acquired = cache.add(lock_key, lock_value, ttl_seconds)
    if acquired:
        logger.debug(f"Acquired return lock: {lock_name}")
    return acquired


def release_return_lock(lock_name: str) -> bool:
    """Release a distributed lock."""
    lock_key = f"return_lock:{lock_name}"
    result = cache.delete(lock_key)
    if result:
        logger.debug(f"Released return lock: {lock_name}")
    return result


class ReturnLock:
    """
    Context manager for distributed locks on return operations.
    
    Usage:
        with ReturnLock(f"return:{return_id}:refund"):
            # Only one process can issue refund at a time
            issue_refund(return_request)
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
            self.acquired = acquire_return_lock(self.lock_name, self.ttl_seconds)
            
            if self.acquired:
                return self
            
            if not self.wait:
                raise Exception(f"Could not acquire return lock: {self.lock_name}")
            
            elapsed = time.time() - start_time
            if elapsed > self.max_wait:
                raise Exception(
                    f"Timeout waiting for return lock: {self.lock_name} after {elapsed:.2f}s"
                )
            
            time.sleep(0.1)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            release_return_lock(self.lock_name)
        return False


# ==============================================================================
# IDEMPOTENCY HELPERS
# ==============================================================================

def check_refund_idempotency(return_request_id: str) -> dict:
    """
    Check if a refund has already been issued for this return request.
    
    Returns:
        Dict with existing refund info if found, None otherwise
    """
    cache_key = f"refund_issued:{return_request_id}"
    return cache.get(cache_key)


def mark_refund_issued(return_request_id: str, refund_transaction_id: str, amount: str):
    """
    Mark that a refund has been issued (for idempotency).
    """
    cache_key = f"refund_issued:{return_request_id}"
    cache.set(cache_key, {
        'refund_transaction_id': refund_transaction_id,
        'amount': amount,
        'issued_at': timezone.now().isoformat()
    }, timeout=86400 * 7)  # 7 days TTL


def check_stock_restoration_idempotency(return_item_id: str) -> bool:
    """
    Check if stock has already been restored for this return item.
    Uses cache for fast check in addition to database field.
    """
    cache_key = f"stock_restored:{return_item_id}"
    return cache.get(cache_key) is not None


def mark_stock_restored(return_item_id: str):
    """Mark that stock has been restored for this return item."""
    cache_key = f"stock_restored:{return_item_id}"
    cache.set(cache_key, True, timeout=86400 * 7)  # 7 days TTL
