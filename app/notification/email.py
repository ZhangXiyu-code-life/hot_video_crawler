"""
Outlook 邮件通知渠道（SMTP/STARTTLS）。
"""
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings
from app.notification.base import NotificationChannel, RankingResult
from app.notification.formatters import format_email_body, format_email_subject
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmailChannel(NotificationChannel):

    @property
    def name(self) -> str:
        return "email"

    async def send(self, result: RankingResult) -> bool:
        if not all([
            settings.email_smtp_host,
            settings.email_smtp_user,
            settings.email_smtp_password,
            settings.email_to,
        ]):
            logger.warning("email_not_configured")
            return False

        subject = format_email_subject(result)
        body = format_email_body(result)

        try:
            # smtplib 是同步的，放到线程池避免阻塞事件循环
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_sync, subject, body
            )
            logger.info("email_sent", period=result.period_type, track=result.track)
            return True
        except Exception as e:
            logger.error("email_send_error", error=str(e))
            return False

    def _send_sync(self, subject: str, body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_smtp_user
        msg["To"] = settings.email_to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.email_smtp_user, settings.email_smtp_password)
            server.sendmail(settings.email_smtp_user, settings.email_to, msg.as_string())
