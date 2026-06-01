import asyncio
import functools
import logging
from config.config import MAX_RETRIES

logger = logging.getLogger(__name__)

def retry_async(max_retries=MAX_RETRIES, delay=2):
    """
    Decorator for retrying async functions.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    logger.warning(f"Function {func.__name__} failed (attempt {retries}/{max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
