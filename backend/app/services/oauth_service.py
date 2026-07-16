"""
Douyin (抖音) OAuth 2.0 service.
"""
import hmac
import hashlib
import uuid
from base64 import urlsafe_b64encode, urlsafe_b64decode

import httpx

from app.config import settings

DOUYIN_AUTH_BASE = "https://open.douyin.com"


def sign_state(user_id: str) -> str:
    """Sign user_id as OAuth state parameter to prevent CSRF."""
    payload = f"{user_id}:{uuid.uuid4().hex[:8]}"
    sig = hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    token = urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()
    return token


def verify_state(state: str) -> str | None:
    """Verify OAuth state parameter and return user_id, or None if invalid."""
    try:
        decoded = urlsafe_b64decode(state.encode()).decode()
        payload, sig = decoded.rsplit(":", 1)
        expected = hmac.new(
            settings.SECRET_KEY.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return payload.split(":")[0]
    except Exception:
        return None


def build_douyin_authorize_url(state: str) -> str:
    """Build Douyin OAuth authorization URL."""
    from urllib.parse import urlencode

    params = {
        "client_key": settings.DOUYIN_CLIENT_KEY,
        "response_type": "code",
        "scope": settings.DOUYIN_OAUTH_SCOPE,
        "redirect_uri": settings.DOUYIN_REDIRECT_URI,
        "state": state,
    }
    return f"{DOUYIN_AUTH_BASE}/platform/oauth/connect/?{urlencode(params)}"


async def douyin_exchange_code(code: str) -> dict:
    """Exchange authorization code for access token."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{DOUYIN_AUTH_BASE}/oauth/access_token/",
            json={
                "client_key": settings.DOUYIN_CLIENT_KEY,
                "client_secret": settings.DOUYIN_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        return resp.json()


async def douyin_refresh_token(refresh_token: str) -> dict:
    """Refresh an expired access token."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{DOUYIN_AUTH_BASE}/oauth/refresh_token/",
            json={
                "client_key": settings.DOUYIN_CLIENT_KEY,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        return resp.json()


async def douyin_get_user_info(access_token: str, open_id: str) -> dict:
    """Get Douyin user profile info."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{DOUYIN_AUTH_BASE}/oauth/userinfo/",
            params={"access_token": access_token, "open_id": open_id},
        )
        return resp.json()
