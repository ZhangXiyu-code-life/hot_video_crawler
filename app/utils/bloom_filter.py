"""
Redis-backed 布隆过滤器，用于视频发现去重。
避免同一视频被重复入库。
"""
import hashlib

import redis.asyncio as aioredis


class BloomFilter:
    def __init__(
        self,
        redis_client: aioredis.Redis,
        key: str = "bloom:video_ids",
        capacity: int = 1_000_000,
        error_rate: float = 0.01,
    ) -> None:
        self._redis = redis_client
        self._key = key
        # 根据容量和误判率计算 bit 数组大小和哈希函数数量
        self._size = self._optimal_size(capacity, error_rate)
        self._hash_count = self._optimal_hash_count(self._size, capacity)

    async def is_seen(self, video_id: str) -> bool:
        positions = self._positions(video_id)
        pipe = self._redis.pipeline()
        for pos in positions:
            pipe.getbit(self._key, pos)
        results = await pipe.execute()
        return all(results)

    async def mark_seen(self, video_id: str) -> None:
        positions = self._positions(video_id)
        pipe = self._redis.pipeline()
        for pos in positions:
            pipe.setbit(self._key, pos, 1)
        await pipe.execute()

    async def is_new(self, video_id: str) -> bool:
        """如果是新视频则标记并返回 True；已存在返回 False。"""
        if await self.is_seen(video_id):
            return False
        await self.mark_seen(video_id)
        return True

    def _positions(self, value: str) -> list[int]:
        positions = []
        for i in range(self._hash_count):
            digest = hashlib.md5(f"{i}:{value}".encode()).hexdigest()
            pos = int(digest, 16) % self._size
            positions.append(pos)
        return positions

    @staticmethod
    def _optimal_size(capacity: int, error_rate: float) -> int:
        import math
        return int(-capacity * math.log(error_rate) / (math.log(2) ** 2))

    @staticmethod
    def _optimal_hash_count(size: int, capacity: int) -> int:
        import math
        return max(1, int(size / capacity * math.log(2)))
