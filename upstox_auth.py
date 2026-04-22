"""upstox_auth.py — Upstox OAuth 2.0 token management.

Handles:
  - Loading access tokens from .env
  - Token validation (hitting /user/profile)
  - Sandbox vs Live mode toggle
  - OAuth redirect flow skeleton for daily re-auth (future)
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── Upstox base URLs ──────────────────────────────────────────────────────────

UPSTOX_BASE_URL = "https://api.upstox.com"
UPSTOX_AUTH_URL = "https://api.upstox.com/v2/login/authorization/dialog"
UPSTOX_TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"


@dataclass
class UpstoxConfig:
    """Configuration for the Upstox API connection."""

    access_token: str = ""
    api_key: str = ""
    api_secret: str = ""
    redirect_uri: str = "http://localhost:8000/callback"
    mode: str = "live"  # "live" or "sandbox"

    # Runtime state
    is_valid: bool = False
    user_name: str = ""
    user_email: str = ""
    broker_id: str = ""
    validated_at: Optional[datetime] = field(default=None, repr=False)

    @property
    def base_url(self) -> str:
        return UPSTOX_BASE_URL

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }


def load_config_from_env() -> UpstoxConfig:
    """Load Upstox configuration from environment variables."""
    config = UpstoxConfig(
        access_token=os.getenv("UPSTOX_ACCESS_TOKEN", ""),
        api_key=os.getenv("UPSTOX_API_KEY", ""),
        api_secret=os.getenv("UPSTOX_API_SECRET", ""),
        redirect_uri=os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/callback"),
        mode=os.getenv("UPSTOX_MODE", "live"),
    )

    if not config.access_token:
        logger.warning(
            "UPSTOX_ACCESS_TOKEN not set in .env — Upstox features will be disabled"
        )

    return config


async def validate_token(config: UpstoxConfig) -> bool:
    """
    Validate the access token by hitting the user profile endpoint.
    Updates config.is_valid, config.user_name, etc.

    Returns True if the token is valid.
    """
    if not config.access_token:
        logger.warning("No Upstox access token configured")
        config.is_valid = False
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{config.base_url}/v2/user/profile",
                headers=config.headers,
            )

        if resp.status_code == 200:
            data = resp.json().get("data", {})
            config.is_valid = True
            config.user_name = data.get("user_name", "")
            config.user_email = data.get("email", "")
            config.broker_id = data.get("broker", "")
            config.validated_at = datetime.now()
            logger.info(
                "✅ Upstox token valid — user: %s (%s mode)",
                config.user_name or "unknown",
                config.mode,
            )
            return True
        else:
            error_msg = resp.json().get("message", resp.text)
            config.is_valid = False
            logger.error(
                "❌ Upstox token invalid (HTTP %d): %s", resp.status_code, error_msg
            )
            return False

    except httpx.TimeoutException:
        logger.error("❌ Upstox token validation timed out")
        config.is_valid = False
        return False
    except Exception as exc:
        logger.error("❌ Upstox token validation failed: %s", exc)
        config.is_valid = False
        return False


def get_login_url(config: UpstoxConfig) -> str:
    """
    Generate the OAuth login URL for the user to authorize.
    After login, Upstox redirects to redirect_uri with ?code=xxx
    """
    return (
        f"{UPSTOX_AUTH_URL}"
        f"?client_id={config.api_key}"
        f"&redirect_uri={config.redirect_uri}"
        f"&response_type=code"
    )


async def exchange_code_for_token(
    config: UpstoxConfig, auth_code: str
) -> Optional[str]:
    """
    Exchange the authorization code for an access token.
    This is Step 2 of the OAuth flow.

    Returns the new access_token or None on failure.
    """
    if not config.api_key or not config.api_secret:
        logger.error("API key/secret not configured — cannot exchange code")
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                UPSTOX_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "code": auth_code,
                    "client_id": config.api_key,
                    "client_secret": config.api_secret,
                    "redirect_uri": config.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

        if resp.status_code == 200:
            token_data = resp.json()
            new_token = token_data.get("access_token", "")
            if new_token:
                config.access_token = new_token
                config.is_valid = True
                config.validated_at = datetime.now()
                logger.info("✅ New Upstox access token obtained")
                return new_token
            else:
                logger.error("Token response missing access_token: %s", token_data)
                return None
        else:
            logger.error(
                "❌ Token exchange failed (HTTP %d): %s",
                resp.status_code,
                resp.text,
            )
            return None

    except Exception as exc:
        logger.error("❌ Token exchange error: %s", exc)
        return None
