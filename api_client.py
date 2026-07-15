"""HTTP client — calls the shared se-ranking-control backend microservice.

The backend base URL is a baked-in constant (app.py) — the public API
gateway host every extension on this platform calls, not a per-user secret.

Two distinct credentials are involved on every call:
  - `backend_jwt`      (scope="app", write_mode="extension") — authenticates
                         THIS EXTENSION to se-ranking-control. Developer-set
                         only via developer.save_app_secret; never entered
                         or seen by end users, never committed to source.
  - the caller's ACTIVE SE Ranking account key (accounts.py — multi-account
                         store, several keys connected + switchable), forwarded
                         as X-SER-API-Key so the backend can fetch/cache/meter
                         data scoped to that one account. Settable via the
                         sidebar's Connect form (handlers_settings.py); several
                         accounts can be connected and switched between.

Without a JWT, every call fails fast with a clear internal-config error
(never silently falls back — a missing platform secret is our bug, not the
user's). Without an active SE Ranking key, project/ranking/harvest/audit
calls return a friendly "connect your account" message instead of silently
using someone else's data.
"""
from __future__ import annotations

from app import SERVER_URL
from ser_accounts import _active_api_key

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
    """Whether the caller has at least one SE Ranking account connected."""
    key = await _active_api_key(ctx)
    return bool(key)


async def call_ser(ctx, method: str, path: str, params: dict | None = None,
                    json: dict | None = None, timeout: int = TIMEOUT,
                    require_user_key: bool = False,
                    headers_override: dict | None = None) -> dict:
    """Call the se-ranking-control backend.

    `require_user_key=True` short-circuits with a friendly config error for
    endpoints that are meaningless without the CALLER's own SE Ranking
    account (projects, rankings, harvest, audit, competitors). Keyword
    research and domain analysis work against any target keyword/domain, so
    those pass require_user_key=False and work even before the user
    connects their own key (using the backend's shared default key).

    `headers_override` lets a caller supply a CANDIDATE X-SER-API-Key (e.g.
    to validate a key before it's saved) without reading/writing the
    stored secret — merged on top of the normal headers.
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

    user_key = await _active_api_key(ctx)
    if require_user_key and not (headers_override or user_key):
        return {
            "error": (
                "Connect your own SE Ranking account first — open Settings and add your "
                "SE Ranking API key (from online.seranking.com -> API)."
            ),
            "_config": True,
        }

    headers = {"Authorization": f"Bearer {backend_jwt}"}
    if user_key:
        headers["X-SER-API-Key"] = user_key
    if headers_override:
        headers.update(headers_override)

    url = f"{base_url}{path}"
    if method.upper() == "GET":
        resp = await ctx.http.get(url, params=params or {}, headers=headers, timeout=timeout)
    elif method.upper() == "POST":
        resp = await ctx.http.post(url, params=params or {}, json=json or {}, headers=headers, timeout=timeout)
    elif method.upper() == "DELETE":
        resp = await ctx.http.delete(url, params=params or {}, headers=headers, timeout=timeout)
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

    if resp.status_code == 204 or not resp.body:
        return {"ok": True}
    return resp.body if isinstance(resp.body, dict) else {"data": resp.body}
