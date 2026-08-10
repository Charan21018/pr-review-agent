from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import asyncio

# Simple retry decorator for async functions
def retry_async(attempts: int = 3, wait_seconds: int = 2, exceptions: tuple = (Exception,)):
    """Return a tenacity retry decorator configured for async functions.
    Usage:
        @retry_async(attempts=5, wait_seconds=1)
        async def my_func(...):
            ...
    """
    return retry(
        reraise=True,
        stop=stop_after_attempt(attempts),
        wait=wait_fixed(wait_seconds),
        retry=retry_if_exception_type(exceptions),
    )

# Convenience wrapper to apply to coroutine functions
def async_retry(*, attempts: int = 3, wait_seconds: int = 2, exceptions: tuple = (Exception,)):
    def decorator(func):
        return retry_async(attempts, wait_seconds, exceptions)(func)
    return decorator

# Example usage (commented out for production):
# @async_retry(attempts=4, wait_seconds=1)
# async def fragile_io():
#     ...
