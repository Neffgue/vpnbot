"""
Mock XUI Service — используется когда VPN_MOCK_MODE=true
Возвращает успешные ответы без реального обращения к 3x-ui панели.
Используется для локальной разработки и тестирования бота/панели.
"""
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv("VPN_MOCK_MODE", "false").lower() == "true"


class XUIServiceMock:
    """Mock service for 3x-ui panel interactions in development mode."""

    def __init__(self, panel_url: str, panel_username: str, panel_password: str, inbound_id: int):
        self.panel_url = panel_url
        self.panel_username = panel_username
        self.panel_password = panel_password
        self.inbound_id = inbound_id
        logger.info(f"[MOCK] XUIService initialized for {panel_url} (MOCK MODE)")

    async def login(self) -> bool:
        logger.info(f"[MOCK] Login to {self.panel_url} — SUCCESS (mock)")
        return True

    async def add_client(
        self, client_uuid: str, traffic_limit_gb: int, expiry_timestamp_ms: int,
        device_limit: int = 1,
    ) -> bool:
        logger.info(
            f"[MOCK] add_client uuid={client_uuid} traffic={traffic_limit_gb}GB "
            f"expiry={expiry_timestamp_ms} device_limit={device_limit} – SUCCESS (mock)"
        )
        return True

    async def update_client(
        self,
        client_uuid: str,
        traffic_limit_gb: Optional[int] = None,
        expiry_timestamp_ms: Optional[int] = None,
        device_limit: Optional[int] = None,
    ) -> bool:
        logger.info(
            f"[MOCK] update_client uuid={client_uuid} traffic={traffic_limit_gb} "
            f"expiry={expiry_timestamp_ms} device_limit={device_limit} – SUCCESS (mock)"
        )
        return True

    async def delete_client(self, client_uuid: str) -> bool:
        logger.info(f"[MOCK] delete_client uuid={client_uuid} — SUCCESS (mock)")
        return True

    async def get_client_stats(self, client_uuid: str) -> Optional[Dict[str, Any]]:
        logger.info(f"[MOCK] get_client_stats uuid={client_uuid} — returning mock stats")
        return {
            "up": 1024 * 1024 * 512,       # 512 MB upload
            "down": 1024 * 1024 * 1024 * 2, # 2 GB download
            "total": 1024 * 1024 * 1024 * 3, # 3 GB total
            "expiryTime": 0,
            "enable": True,
        }

    async def close(self):
        pass


def get_xui_service(panel_url: str, panel_username: str, panel_password: str, inbound_id: int):
    """
    Factory function: возвращает мок или реальный XUI сервис
    в зависимости от переменной окружения VPN_MOCK_MODE.
    """
    if MOCK_MODE:
        return XUIServiceMock(panel_url, panel_username, panel_password, inbound_id)

    from backend.services.xui_service import XUIService
    return XUIService(panel_url, panel_username, panel_password, inbound_id)
