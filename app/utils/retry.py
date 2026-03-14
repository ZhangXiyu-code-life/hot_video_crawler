import functools
from typing import Callable, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.utils.logging import get_logger

logger = get_logger(__name__)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """指数退避重试装饰器，适用于外部 API 调用。"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _retry = retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
                retry=retry_if_exception_type(exceptions),
                reraise=True,
            )
            return await _retry(func)(*args, **kwargs)
        return wrapper
    return decorator
