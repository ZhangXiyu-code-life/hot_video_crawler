"""
飞书 Webhook Bot 通知渠道。
"""
import httpx

from app.config import get_settings
from app.notification.base import NotificationChannel, RankingResult
from app.notification.formatters import format_feishu_card
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class FeishuChannel(NotificationChannel):

    @property
    def name(self) -> str:
        return "feishu"

    async def send(self, result: RankingResult) -> bool:
        if not settings.feishu_webhook_url:
            logger.warning("feishu_webhook_not_configured")
            return False

        payload = format_feishu_card(result)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(settings.feishu_webhook_url, json=payload)
                response.raise_for_status()
                resp_json = response.json()
                # 飞书 API 返回 {"code": 0} 表示成功
                if resp_json.get("code") != 0:
                    logger.error("feishu_send_failed", resp=resp_json)
                    return False
            logger.info("feishu_sent", period=result.period_type, track=result.track)
            return True
        except Exception as e:
            logger.error("feishu_send_error", error=str(e))
            return False
