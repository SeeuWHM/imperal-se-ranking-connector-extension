"""HTTP client — calls the shared se-ranking-control backend microservice.

The backend base URL is a baked-in constant (app.py) — the public API
gateway host every extension on this platform calls, not a per-user secret.

Two distinct secrets are involved on every call:
  - `backend_jwt`      (write_mode="extension") — authenticates THIS
                         EXTENSION to se-ranking-control. Developer-set only
                         via developer.save_app_secret; never entered or
                         seen by end users, never committed to source.
  - `seranking_api_key` (write_mode="user")      — the CALLER's own SE
                         Ranking account key, forwarded as X-SER-API-Key so
                         the backend can fetch/cache/meter data scoped to
                         that one user.

Without a JWT, every call fails fast with a clear internal-config error
(never silently falls back — a missing platform secret is our bug, not the
user's). Without the user's own SE Ranking key, project/ranking/harvest/
audit calls return a friendly "connect your account" message instead of
silently using someone else's data.
"""
from __future__ import annotations

from app import SERVER_URL

TIMEOUT = 30
HEAVY_TIMEOUT = 90  # research/brief-style calls: several sequential SE Ranking API calls


def _normalize_backend_url(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value.rstrip("/")


async def ser_ready(ctx) -> bool:
    """Whether the caller has their own SE Ranking API key configured."""
    key = await ctx.secrets.get("seranking_api_key")
    return bool(key and key.strip())


async def call_ser(ctx, method: str, path: str, params: dict | None = None,
                    json: dict | None = None, timeout: int = TIMEOUT,
                    require_user_key: bool = False) -> dict:
    """Call the se-ranking-control backend.

    `require_user_key=True` short-circuits with a friendly config error for
    endpoints that are meaningless without the CALLER's own SE Ranking
    account (projects, rankings, harvest, audit, competitors). Keyword
    research and domain analysis work against any target keyword/domain, so
    those pass require_user_key=False and work even before the user
    connects their own key (using the backend's shared default key).
    """
    base_url = _normalize_backend_url(SERVER_URL)
    if not base_url:
        return {"error": "SE Ranking backend URL is not configured.", "_config": True}

    backend_jwt = await ctx.secrets.get("backend_jwt")
    if not backend_jwt:
        return {
            "error": "SE Ranking backend is not configured on our side yet — this has been logged.",
            "_config": True,
        }

    user_key = await ctx.secrets.get("seranking_api_key")
    if require_user_key and not (user_key and user_key.strip()):
        return {
            "error": (
                "Connect your own SE Ranking account first — open Settings and add your "
                "SE Ranking API key (from online.seranking.com -> API)."
            ),
            "_config": True,
        }

    headers = {"Authorization": f"Bearer {backend_jwt}"}
    if user_key and user_key.strip():
        headers["X-SER-API-Key"] = user_key.strip()

    url = f"{base_url}{path}"
    if method.upper() == "GET":
        resp = await ctx.http.get(url, params=params or {}, headers=headers, timeout=timeout)
    elif method.upper() == "POST":
        resp = await ctx.http.post(url, params=params or {}, json=json or {}, headers=headers, timeout=timeout)
    else:
        return {"error": f"Unsupported method {method}", "_config": True}

    if resp.status_code == 401:
        return {"error": "SE Ranking backend rejected our credentials — this has been logged.", "_config": True}
    if resp.status_code == 404:
        return {"error": "Not found.", "_config": True}
    if resp.status_code >= 400:
        detail = resp.body if isinstance(resp.body, dict) else {"detail": resp.body}
        msg = detail.get("detail", detail) if isinstance(detail, dict) else detail
        return {"error": f"SE Ranking error: {msg}", "_config": False}

    return resp.body if isinstance(resp.body, dict) else {"data": resp.body}
