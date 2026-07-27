"""
Retry handler with exponential backoff.

Provides retry decorators for functions.
"""
import random
import time
from functools import wraps
from typing import Callable, Type, Tuple, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from core.logger import logger


def retry_with_backoff(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for retrying function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff_factor),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logger.level("INFO").name),
        )
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        return wrapper
    return decorator


def exponential_backoff_sleep(
    attempt: int,
    backoff_factor: float = 1.0,
) -> float:
    """
    Calculate sleep time with exponential backoff + jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        backoff_factor: Backoff multiplier
        
    Returns:
        Sleep time in seconds
    """
    sleep_time = backoff_factor * (2 ** attempt)
    jitter = random.uniform(0, 0.1 * sleep_time)
    return sleep_time + jitter


def rate_limit_wait(delay_min: float = 0.5, delay_max: float = 2.0) -> None:
    """
    Sleep with random delay to implement rate limiting.
    
    Args:
        delay_min: Minimum delay in seconds
        delay_max: Maximum delay in seconds
    """
    delay = random.uniform(delay_min, delay_max)
    time.sleep(delay)
