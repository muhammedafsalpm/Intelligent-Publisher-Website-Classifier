import asyncio
from typing import Callable, Any, Tuple, Type
import logging

logger = logging.getLogger(__name__)

async def retry_async(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1,
    exponential: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Any:
    """Retry async function with exponential backoff"""
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt == max_retries - 1:
                break
            
            delay = base_delay * (2 ** attempt) if exponential else base_delay
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
            await asyncio.sleep(delay)
    
    raise last_exception
