"""
Retry utilities for handling transient Bedrock errors.
"""
import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Optional, Tuple, Type

logger = logging.getLogger(__name__)


# Transient errors that should be retried
TRANSIENT_ERRORS = [
    "modelStreamErrorException",
    "ThrottlingException",
    "ProvisionedThroughputExceededException",
    "RequestLimitExceeded",
    "ServiceUnavailable",
    "InternalFailure",
]


def is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and should be retried."""
    error_str = str(error)
    return any(transient in error_str for transient in TRANSIENT_ERRORS)


async def retry_with_exponential_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delay
        retryable_exceptions: Tuple of exception types to retry. 
                              If None, uses is_transient_error() check.
    
    Returns:
        Result of the function call
    
    Raises:
        The last exception if all retries fail
    """
    import random
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            # Check if we should retry
            should_retry = False
            if retryable_exceptions:
                should_retry = isinstance(e, retryable_exceptions)
            else:
                should_retry = is_transient_error(e)
            
            # Don't retry if we've exhausted attempts or error is not transient
            if attempt == max_retries or not should_retry:
                logger.error(
                    "Retry exhausted or non-transient error after %d attempts: %s",
                    attempt + 1,
                    e
                )
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random())  # Add jitter: [0.5*delay, 1.5*delay]
            
            logger.warning(
                "Transient error (attempt %d/%d), retrying in %.2f seconds: %s",
                attempt + 1,
                max_retries + 1,
                delay,
                e
            )
            
            await asyncio.sleep(delay)
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


def retry_decorator(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    jitter: bool = True,
):
    """
    Decorator for retry with exponential backoff.
    
    Usage:
        @retry_decorator(max_retries=3)
        async def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_exponential_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter
            )
        return wrapper
    return decorator
