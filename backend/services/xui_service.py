import logging
import json
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from backend.config import settings

logger = logging.getLogger(__name__)


class XUIService:
    """Service for interacting with 3x-ui panel."""

    def __init__(self, panel_url: str, panel_username: str, panel_password: str, inbound_id: int):
        """Initialize XUI service."""
        self.panel_url = panel_url.rstrip("/")
        self.panel_username = panel_username
        self.panel_password = panel_password
        self.inbound_id = inbound_id
        self.session_cookie: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=settings.XUI_API_TIMEOUT)

    async def login(self) -> bool:
        """Login to 3x-ui panel and get session cookie."""
        try:
            url = f"{self.panel_url}/login"
            payload = {
                "username": self.panel_username,
                "password": self.panel_password,
            }

            response = await self.client.post(url, json=payload)
            if response.status_code == 200:
                # Extract session cookie from response
                cookies = response.cookies
                if "session" in cookies:
                    self.session_cookie = cookies.get("session")
                    logger.info(f"Successfully logged in to {self.panel_url}")
                    return True
                else:
                    logger.warning("No session cookie in login response")
                    return False
            else:
                logger.error(f"Login failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def add_client(
        self, client_uuid: str, traffic_limit_gb: int, expiry_timestamp_ms: int,
        device_limit: int = 1,
    ) -> bool:
        """Add a client to inbound."""
        try:
            if not self.session_cookie:
                if not await self.login():
                    return False

            # Convert traffic GB to bytes
            traffic_limit_bytes = traffic_limit_gb * 1024 * 1024 * 1024

            url = f"{self.panel_url}/api/inbounds/{self.inbound_id}/addClient"
            payload = {
                "id": client_uuid,
                "alterId": 0,
                "email": f"client_{client_uuid}",
                "limitIp": device_limit,
                "totalGB": traffic_limit_bytes,
                "expiryTime": expiry_timestamp_ms,
                "tls": "tls",
                "flow": "xtls-rprx-vision",
            }

            cookies = {"session": self.session_cookie}
            response = await self.client.post(url, json=payload, cookies=cookies)

            if response.status_code == 200:
                logger.info(f"Successfully added client {client_uuid}")
                return True
            else:
                logger.error(f"Failed to add client: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error adding client: {e}")
            return False

    async def update_client(
        self,
        client_uuid: str,
        traffic_limit_gb: Optional[int] = None,
        expiry_timestamp_ms: Optional[int] = None,
        device_limit: Optional[int] = None,
    ) -> bool:
        """Update client traffic limit and/or expiry."""
        try:
            if not self.session_cookie:
                if not await self.login():
                    return False

            url = f"{self.panel_url}/api/inbounds/{self.inbound_id}/updateClient/{client_uuid}"
            payload = {}

            if traffic_limit_gb is not None:
                payload["totalGB"] = traffic_limit_gb * 1024 * 1024 * 1024

            if expiry_timestamp_ms is not None:
                payload["expiryTime"] = expiry_timestamp_ms

            if device_limit is not None:
                payload["limitIp"] = device_limit

            if not payload:
                logger.warning("No updates specified for client")
                return False

            cookies = {"session": self.session_cookie}
            response = await self.client.post(url, json=payload, cookies=cookies)

            if response.status_code == 200:
                logger.info(f"Successfully updated client {client_uuid}")
                return True
            else:
                logger.error(f"Failed to update client: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error updating client: {e}")
            return False

    async def delete_client(self, client_uuid: str) -> bool:
        """Delete client from inbound."""
        try:
            if not self.session_cookie:
                if not await self.login():
                    return False

            url = f"{self.panel_url}/api/inbounds/{self.inbound_id}/delClient/{client_uuid}"

            cookies = {"session": self.session_cookie}
            response = await self.client.delete(url, cookies=cookies)

            if response.status_code == 200:
                logger.info(f"Successfully deleted client {client_uuid}")
                return True
            else:
                logger.error(f"Failed to delete client: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error deleting client: {e}")
            return False

    async def get_client_stats(self, client_uuid: str) -> Optional[Dict[str, Any]]:
        """Get client statistics (used traffic, expiry)."""
        try:
            if not self.session_cookie:
                if not await self.login():
                    return None

            url = f"{self.panel_url}/api/inbounds/{self.inbound_id}/getClientStats/{client_uuid}"

            cookies = {"session": self.session_cookie}
            response = await self.client.get(url, cookies=cookies)

            if response.status_code == 200:
                stats = response.json()
                logger.info(f"Successfully got stats for client {client_uuid}")
                return stats
            else:
                logger.error(f"Failed to get client stats: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting client stats: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
