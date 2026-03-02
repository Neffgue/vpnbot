import logging
import base64
from typing import List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class HappLinkGenerator:
    """Generate Happ subscription links and VPN configuration."""

    @staticmethod
    def generate_vless_link(
        uuid: str,
        server_name: str,
        host: str,
        port: int,
        flow: str = "xtls-rprx-vision",
        security: str = "reality",
        sni: str = "google.com",
        pbk: str = "public_key_here",
    ) -> str:
        """
        Generate a VLESS link for a server.
        Format: vless://uuid@host:port?params#server_name
        """
        params = {
            "type": "tcp",
            "security": security,
            "flow": flow,
            "sni": sni,
            "pbk": pbk,
            "fp": "firefox",
        }

        # Build query string
        query_parts = [f"{k}={v}" for k, v in params.items()]
        query_string = "&".join(query_parts)

        # Build VLESS URL
        vless_url = f"vless://{uuid}@{host}:{port}?{query_string}#{quote(server_name)}"
        return vless_url

    @staticmethod
    def generate_subscription_link(vless_links: List[str]) -> str:
        """
        Generate a subscription link from VLESS links.
        Encodes as base64 for use in Happ app.
        """
        content = "\n".join(vless_links)
        encoded = base64.b64encode(content.encode()).decode()
        return f"data:text/plain;base64,{encoded}"

    @staticmethod
    def decode_subscription_link(link: str) -> List[str]:
        """Decode a subscription link to get individual VLESS links."""
        try:
            # Remove prefix if present
            if link.startswith("data:text/plain;base64,"):
                link = link.replace("data:text/plain;base64,", "")

            # Decode base64
            decoded = base64.b64decode(link).decode()
            links = [l.strip() for l in decoded.split("\n") if l.strip()]
            return links
        except Exception as e:
            logger.error(f"Failed to decode subscription link: {e}")
            return []

    @staticmethod
    def generate_config_json(
        telegram_id: int,
        traffic_remaining_gb: int,
        expires_at: str,
        servers_list: list,
    ) -> dict:
        """
        Generate JSON config for Happ app.
        Returns dict with subscription info and server list with VLESS links.
        """
        return {
            "telegram_id": telegram_id,
            "traffic_remaining_gb": traffic_remaining_gb,
            "expires_at": expires_at,
            "servers": servers_list,
        }
