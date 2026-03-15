"""
NotificationDispatcher：Observer 模式广播器。
新增通知渠道只需注册到此，无需修改任何业务代码。
"""
from app.notification.base import NotificationChannel, RankingResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


class NotificationDispatcher:

    def __init__(self) -> None:
        self._channels: list[NotificationChannel] = []

    def register(self, channel: NotificationChannel) -> None:
        self._channels.append(channel)
        logger.info("notification_channel_registered", channel=channel.name)

    async def dispatch(self, result: RankingResult) -> None:
        """广播榜单到所有已注册渠道，单个渠道失败不影响其他渠道。"""
        if not self._channels:
            logger.warning("no_notification_channels_registered")
            return

        for channel in self._channels:
            try:
                success = await channel.send(result)
                if not success:
                    logger.warning("channel_send_failed", channel=channel.name)
            except Exception as e:
                logger.error("channel_dispatch_error", channel=channel.name, error=str(e))


def build_dispatcher() -> NotificationDispatcher:
    """构建默认 dispatcher，注册邮件渠道。"""
    from app.notification.email import EmailChannel

    dispatcher = NotificationDispatcher()
    dispatcher.register(EmailChannel())
    return dispatcher
