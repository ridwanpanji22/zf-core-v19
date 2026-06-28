import httpx
import structlog
from redis import Redis
from app.config import settings

logger = structlog.get_logger()

class TelegramAlertSystem:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def send_message(self, text: str) -> bool:
        """Helper to send telegram message outbound via httpx."""
        if not self.bot_token or not self.chat_id:
            logger.warn("Telegram bot credentials not configured, skipping alert")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    url,
                    data={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "Markdown"
                    },
                    timeout=10.0
                )
                if res.status_code == 200:
                    logger.info("Telegram alert sent successfully")
                    return True
                else:
                    logger.error("Failed to send Telegram alert", status_code=res.status_code, response=res.text)
                    return False
        except Exception as e:
            logger.error("Exception occurred while sending Telegram alert", error=str(e))
            return False

    async def trigger_alert(self, priority: str, alert_type: str, message: str, symbol: str | None = None) -> bool:
        """Trigger structured alert with built-in rate-limiting and anti-spam filters."""
        # 1. Anti-Spam Filter check: block duplicate alerts within 15 minutes (900s)
        if symbol:
            spam_key = f"alert_sent:{alert_type}:{symbol}"
            if self.redis_client.get(spam_key) == "true":
                logger.info("Alert throttled (duplicate filter)", symbol=symbol, alert_type=alert_type)
                return False
            # Set lock for 15 minutes
            self.redis_client.set(spam_key, "true", ex=900)

        # 2. Rate-Limiting check: Max 5 alerts per minute globally
        rate_key = "alert_global_counter"
        current_rate = self.redis_client.get(rate_key)
        if current_rate and int(current_rate) >= 5:
            # We delay or hold and combine. For MVP we log rate-limit limit and drop
            logger.warn("Alert throttled (global rate limit hit, >5/min)")
            # Add message to pending alerts list to combine
            self.redis_client.lpush("alert_pending_queue", f"[{priority.upper()}] {message}")
            return False

        # Increment counter
        if not current_rate:
            self.redis_client.set(rate_key, "1", ex=60)
        else:
            self.redis_client.incr(rate_key)

        # 3. Format templates based on priority
        emoji = "🟢 [INFO]"
        if priority.lower() == "critical":
            emoji = "🚨 [CRITICAL]"
        elif priority.lower() == "warning":
            emoji = "⚠️ [WARNING]"

        payload_text = f"*{emoji}*\n{message}"

        return await self.send_message(payload_text)

    async def check_and_send_pending_summary(self):
        """Process and send queued pending alerts as 1 combined summary message."""
        queue_len = self.redis_client.llen("alert_pending_queue")
        if queue_len == 0:
            return

        # Fetch all pending messages
        alerts = []
        while self.redis_client.llen("alert_pending_queue") > 0:
            item = self.redis_client.rpop("alert_pending_queue")
            if item:
                alerts.append(item)

        if not alerts:
            return

        combined_text = "*⚠️ [WARNING] Ringkasan Alert Terakumulasi*\n\n"
        combined_text += "\n".join(f"- {a}" for a in alerts)

        await self.send_message(combined_text)
