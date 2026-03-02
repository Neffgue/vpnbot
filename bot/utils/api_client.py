"""Async HTTP client for backend API communication"""

import httpx
from typing import Optional, Any, Dict
from datetime import datetime
import logging

from bot.config import config

logger = logging.getLogger(__name__)


class APIClient:
    """Async client for backend API calls"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth if available"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to API"""
        if not self._client:
            raise RuntimeError("APIClient not initialized. Use 'async with APIClient(...)'")
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = kwargs.pop("headers", {})
        headers.update(self._get_headers())
        
        try:
            response = await self._client.request(
                method,
                url,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request"""
        return await self._request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """POST request"""
        return await self._request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PUT request"""
        return await self._request("PUT", endpoint, **kwargs)
    
    async def patch(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PATCH request"""
        return await self._request("PATCH", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE request"""
        return await self._request("DELETE", endpoint, **kwargs)
    
    # User endpoints
    async def register_user(self, user_id: int, username: str, first_name: str, ref_code: Optional[str] = None) -> Dict[str, Any]:
        """Register new user"""
        return await self.post(
            "/users/register",
            json={
                "telegram_id": user_id,
                "username": username,
                "first_name": first_name,
                "referral_code": ref_code,
            }
        )
    
    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user info"""
        try:
            return await self.get(f"/users/{user_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise

    async def update_user(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user info (email, username, etc.)"""
        return await self.patch(f"/users/{user_id}", json=data)
    
    async def check_ban(self, user_id: int) -> Dict[str, Any]:
        """Check if user is banned"""
        return await self.get(f"/users/{user_id}/ban-status")
    
    # Subscription endpoints
    async def get_subscription(self, user_id: int) -> Dict[str, Any]:
        """Get user's active subscription"""
        try:
            return await self.get(f"/users/{user_id}/subscription")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise
    
    async def get_subscription_plans(self) -> Dict[str, Any]:
        """Get available subscription plans"""
        return await self.get("/subscriptions/plans")
    
    async def create_payment_link(
        self,
        user_id: int,
        plan_id: str,
        period_days: int,
        payment_method: str = "yookassa"
    ) -> Dict[str, Any]:
        """Create payment link"""
        return await self.post(
            f"/users/{user_id}/create-payment",
            json={
                "plan_id": plan_id,
                "period_days": period_days,
                "payment_method": payment_method,
            }
        )
    
    async def confirm_payment(self, user_id: int, payment_id: str) -> Dict[str, Any]:
        """Confirm payment and activate subscription"""
        return await self.post(
            f"/users/{user_id}/confirm-payment",
            json={"payment_id": payment_id}
        )
    
    # Free trial endpoints
    async def activate_free_trial(self, user_id: int) -> Dict[str, Any]:
        """Activate free 24h trial"""
        return await self.post(f"/users/{user_id}/free-trial")
    
    async def check_free_trial_used(self, user_id: int) -> Dict[str, Any]:
        """Check if user already used free trial"""
        return await self.get(f"/users/{user_id}/free-trial-status")
    
    # Referral endpoints
    async def get_referral_info(self, user_id: int) -> Dict[str, Any]:
        """Get user's referral info"""
        try:
            return await self.get(f"/users/{user_id}/referral")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise
    
    # Device endpoints
    async def get_user_devices(self, user_id: int) -> Dict[str, Any]:
        """Get list of user's connected devices"""
        try:
            return await self.get(f"/users/{user_id}/devices")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise
    
    async def add_device(self, user_id: int, device_name: str) -> Dict[str, Any]:
        """Add new device (generate new config)"""
        return await self.post(
            f"/users/{user_id}/devices",
            json={"device_name": device_name}
        )
    
    async def delete_device(self, user_id: int, device_id: str) -> Dict[str, Any]:
        """Delete/unlink device"""
        return await self.delete(f"/users/{user_id}/devices/{device_id}")
    
    # Bot text endpoints (message templates from backend)
    async def get_bot_text(self, key: str, language: str = "ru") -> Dict[str, Any]:
        """Get bot message text from backend"""
        return await self.get(f"/bot-texts/{key}", params={"language": language})
    
    async def get_all_bot_texts(self, language: str = "ru") -> Dict[str, Any]:
        """Get all bot message texts — uses public endpoint (no admin auth needed)"""
        try:
            return await self.get("/bot-texts/public")
        except Exception:
            try:
                return await self.get("/admin/bot-texts")
            except Exception:
                return {}

    async def get_bot_settings(self) -> Dict[str, Any]:
        """Get bot settings (media URLs, support username, etc.) — uses public endpoint"""
        try:
            return await self.get("/bot-settings/public")
        except Exception:
            try:
                return await self.get("/admin/settings")
            except Exception:
                return {}

    async def get_bot_buttons(self) -> list:
        """Get main menu buttons — uses public endpoint"""
        try:
            result = await self.get("/bot-buttons/public")
            return result.get("buttons", [])
        except Exception:
            try:
                result = await self.get("/admin/bot-buttons")
                return result.get("buttons", [])
            except Exception:
                return []
    
    # Instructions endpoints
    async def get_instructions(self) -> Dict[str, Any]:
        """Get connection instructions with images"""
        return await self.get("/instructions")
    
    # Admin endpoints
    async def ban_user(self, user_id: int, reason: str) -> Dict[str, Any]:
        """Ban user (admin only)"""
        return await self.post(
            f"/admin/users/{user_id}/ban",
            json={"user_id": str(user_id), "is_banned": True, "reason": reason}
        )
    
    async def unban_user(self, user_id: int) -> Dict[str, Any]:
        """Unban user (admin only)"""
        return await self.post(f"/admin/users/{user_id}/unban")
    
    async def add_balance(self, user_id: int, amount: float, reason: str) -> Dict[str, Any]:
        """Add balance to user (admin only)"""
        return await self.post(
            f"/admin/users/{user_id}/balance",
            json={"amount": amount, "reason": reason}
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics (admin only)"""
        return await self.get("/admin/stats")
    
    async def send_broadcast(self, message: str, user_ids: Optional[list[int]] = None) -> Dict[str, Any]:
        """Send broadcast message (admin only)"""
        payload: Dict[str, Any] = {"message": message or ""}
        if user_ids:
            payload["user_ids"] = user_ids
        return await self.post("/admin/broadcasts", json=payload)
    
    async def reissue_vpn_key(self, user_id: int) -> Dict[str, Any]:
        """Перевыпустить VPN-ключ пользователя."""
        return await self.post(f"/users/{user_id}/reissue-key")

    async def get_user_payments(self, user_id: int) -> Dict[str, Any]:
        """Получить историю платежей пользователя."""
        try:
            return await self.get(f"/users/{user_id}/payments")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise

    # Notification endpoints
    async def send_notification(self, user_id: int, message: str, notification_type: str) -> Dict[str, Any]:
        """Send notification to user"""
        return await self.post(
            f"/users/{user_id}/notifications",
            json={
                "message": message,
                "type": notification_type,
            }
        )
