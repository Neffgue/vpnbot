import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via Telegram."""

    async def send_message(self, chat_id: int, message: str, bot_token: str, api_url: str) -> bool:
        """Send message to Telegram user."""
        try:
            import httpx
            
            url = f"{api_url}{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending telegram message: {e}")
            return False

    async def send_subscription_expiry_warning(
        self, chat_id: int, days_left: int, bot_token: str, api_url: str
    ) -> bool:
        """Send subscription expiry warning."""
        message = f"⚠️ Your VPN subscription expires in {days_left} days. Please renew to continue using the service."
        return await self.send_message(chat_id, message, bot_token, api_url)

    async def send_payment_confirmed(self, chat_id: int, plan: str, bot_token: str, api_url: str) -> bool:
        """Send payment confirmation message."""
        message = f"✅ Payment confirmed!\n\nPlan: {plan}\nYour subscription is now active."
        return await self.send_message(chat_id, message, bot_token, api_url)

    async def send_referral_bonus(
        self, chat_id: int, bonus_days: int, bot_token: str, api_url: str
    ) -> bool:
        """Send referral bonus notification."""
        message = f"🎁 Referral bonus!\n\nYour referred user made a purchase.\nYou received {bonus_days} days bonus to your subscription."
        return await self.send_message(chat_id, message, bot_token, api_url)
