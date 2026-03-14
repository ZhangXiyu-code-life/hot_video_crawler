"""
飞瓜数据 HTTP Client。
封装鉴权、限速、超时重试，对 adapter 层透明。

TODO: 拿到 API 文档后填入真实的：
  - BASE_URL
  - 鉴权方式（Header / 签名 / OAuth）
  - 各接口路径
"""
import httpx

from app.config import get_settings
from app.utils.logging import get_logger
from app.utils.rate_limiter import RateLimiter

logger = get_logger(__name__)
settings = get_settings()


class FeiguaClient:
    def __init__(self, redis_client) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.feigua_base_url,
            headers={
                "Authorization": f"Bearer {settings.feigua_api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        # 飞瓜 API 限速：根据实际套餐调整 rate
        self._limiter = RateLimiter(redis_client, key="feigua", rate=2.0)

    async def get(self, path: str, params: dict | None = None) -> dict:
        await self._limiter.acquire()
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("feigua_api_error", status=e.response.status_code, path=path)
            raise
        except httpx.RequestError as e:
            logger.error("feigua_request_error", error=str(e), path=path)
            raise

    async def aclose(self) -> None:
        await self._client.aclose()
