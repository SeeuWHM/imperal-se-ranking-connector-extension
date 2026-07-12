"""SE Ranking extension — core init + shared helpers.

Architecture (mirrors imperal-matomo-analytics-extension's shared-backend
pattern):

  - The extension calls a SHARED backend microservice (se-ranking-control,
    reachable at https://api.webhostmost.com/se-ranking/) that talks to the
    real SE Ranking API. The backend is multi-tenant: every request can
    carry the caller's OWN SE Ranking API key via the X-SER-API-Key header,
    and the backend partitions caching + daily credit quota per key so one
    user's data/spend never leaks into another's.

  - se-ranking-control requires a platform JWT on every call. That token
    is NOT a per-user credential — it identifies this extension to the
    backend, same value for every installer — so it's declared as an
    ext.secret with write_mode="extension" (developer-set only, via
    developer.save_app_secret; never entered by end users, never
    committed to source).

  - The user's own SE Ranking API key IS a per-user credential — declared
    with write_mode="both" so it can be entered either via the platform's
    Secrets panel OR via a proper in-extension form (a save_seranking_key
    chat.function backed by a real ui.Form in the sidebar) — the form is
    the primary, obvious UX; the Secrets panel is just the same value
    surfaced platform-wide. Without it, project/ranking/harvest/audit
    endpoints require the caller's own key and say so clearly when it's
    missing (keyword research and domain analysis still work on the
    backend's shared default key, since those aren't scoped to one
    account).
"""
from __future__ import annotations

import os

from imperal_sdk import Extension, ChatExtension

# Shared backend bridge — same public API gateway host every extension on
# this platform calls. Not a secret: it's the platform's own microservice.
SERVER_URL = os.environ.get("SER_BACKEND_URL", "") or "https://api.webhostmost.com/se-ranking"

ext = Extension(
    "se-ranking-connector",
    version="1.0.0",
    display_name="SE Ranking Connector",
    description=(
        "SEO rank tracking and keyword research powered by SE Ranking: project "
        "rankings, content opportunities (quick wins, CTR gaps), keyword research "
        "(longtail/related/questions), domain analysis and project health audits. "
        "Connect your own SE Ranking account to track your own projects."
    ),
    icon="icon.svg",
    actions_explicit=True,
    capabilities=[
        "Project Rankings",
        "Content Opportunities",
        "Keyword Research",
        "Domain Analysis",
        "Project Health Audit",
        "Competitor Tracking",
    ],
)

chat = ChatExtension(
    ext,
    tool_name="se_ranking",
    description=(
        "SE Ranking — SEO rank tracking and keyword research. Use for: Google "
        "search positions/rankings for MY tracked project (покажи позиции, SEO "
        "rankings), content opportunities / quick wins / CTR gaps (что писать "
        "дальше, quick wins), keyword research — longtail/related/questions "
        "(найди ключевые слова, keyword research), domain analysis (анализ "
        "домена конкурента), project health audit (аудит проекта)."
    ),
    max_rounds=10,
)

ext.secret(
    name="backend_jwt",
    description=(
        "Platform JWT authenticating this extension to the se-ranking-control "
        "backend microservice. Developer-managed only — never entered or seen "
        "by end users."
    ),
    required=True,
    write_mode="extension",
    scope="app",
    env_fallback="IMPERAL_APPSECRET_SE_RANKING_BACKEND_JWT",
    max_bytes=2048,
)(lambda: None)

# ── User-scope secret: the user's OWN SE Ranking API key ─────────────────────
# Real per-user credential — every installer's own value. Interpreted
# literally as the key value: no URL is ever assembled or guessed from it.
ext.secret(
    name="seranking_api_key",
    description=(
        "Your SE Ranking API key (from online.seranking.com -> API). "
        "Used to fetch YOUR projects, rankings and keyword data — "
        "never shared with other users. Enter it via the form in the "
        "sidebar, or the platform's Secrets panel — same value either way."
    ),
    required=False,
    write_mode="both",
    scope="user",
    max_bytes=200,
)(lambda: None)


async def seranking_key_status(ctx) -> dict:
    """Masked status of the user's SE Ranking key, for forms/panels."""
    key = await ctx.secrets.get("seranking_api_key")
    key = (key or "").strip()
    if not key:
        return {"connected": False, "masked": ""}
    tail = key[-4:] if len(key) >= 4 else key
    return {"connected": True, "masked": f"••••{tail}"}


@ext.health_check
async def health(ctx) -> dict:
    """Report whether the user's own SE Ranking key is configured."""
    key = await ctx.secrets.get("seranking_api_key")
    return {"status": "ok", "version": ext.version, "seranking_connected": bool(key and key.strip())}
