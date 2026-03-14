"""
Redis 令牌桶限速器。
用于控制对第三方 API 的请求频率，避免触发平台限流。
"""
import asyncio
import time

import redis.asyncio as aioredis


class RateLimiter:
    def __init__(
        self,
        redis_client: aioredis.Redis,
        key: str,
        rate: float,          # 每秒允许的请求数
        burst: int = 1,       # 突发容量
    ) -> None:
        self._redis = redis_client
        self._key = f"rate_limit:{key}"
        self._rate = rate
        self._burst = burst
        self._interval = 1.0 / rate  # 每个令牌的生成间隔（秒）

    async def acquire(self) -> None:
        """阻塞直到获取到令牌。"""
        while True:
            allowed = await self._try_acquire()
            if allowed:
                return
            await asyncio.sleep(self._interval)

    async def _try_acquire(self) -> bool:
        now = time.time()
        pipe = self._redis.pipeline()
        pipe.get(self._key)
        results = await pipe.execute()
        last_time = float(results[0]) if results[0] else 0.0

        elapsed = now - last_time
        if elapsed >= self._interval:
            await self._redis.set(self._key, now, ex=60)
            return True
        return False
