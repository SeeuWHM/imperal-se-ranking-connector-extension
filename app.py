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
    version="1.2.1",
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
    scope="app",  # app-scope secrets are owner-only regardless of write_mode (SDK 5.9.9 warns on a redundant write_mode= here)
    env_fallback="IMPERAL_APPSECRET_SE_RANKING_BACKEND_JWT",
    max_bytes=2048,
)(lambda: None)

# ── User-scope secret: the user's OWN SE Ranking API key(s) ──────────────────
# Real per-user credential(s). Interpreted literally as the key value(s): no
# URL is ever assembled or guessed from it.
#
# `seranking_api_key` (legacy, single value, write_mode="both") is kept
# declared so existing installs that already saved a key via the platform's
# general Secrets panel keep working — accounts.py transparently migrates it
# into the new multi-account store on first read.
#
# `seranking_accounts` (current, JSON list, write_mode="extension" — only
# this extension's own handlers write it, never the generic Secrets panel,
# since its shape is a JSON blob of {label, api_key, is_active} records, not
# a single opaque value) is the real source of truth: multiple SE Ranking
# accounts connected simultaneously, one active at a time, switchable —
# same pattern as mail-client's `imap_credentials`.
ext.secret(
    name="seranking_api_key",
    description=(
        "(Legacy) Your SE Ranking API key. Superseded by seranking_accounts "
        "(multi-account) — kept only so pre-existing single-key connections "
        "keep working; new connections go through the sidebar's Connect form."
    ),
    required=False,
    write_mode="both",
    scope="user",
    max_bytes=200,
)(lambda: None)

ext.secret(
    name="seranking_accounts",
    description=(
        "Every SE Ranking account you've connected (JSON list of "
        "{label, api_key, is_active}) — lets you track multiple SE Ranking "
        "accounts and switch between them. Managed only through this "
        "extension's own connect/switch/disconnect actions, never edited "
        "directly."
    ),
    required=False,
    write_mode="extension",
    scope="user",
    max_bytes=8192,
)(lambda: None)


@ext.health_check
async def health(ctx) -> dict:
    """Report whether the user has at least one SE Ranking account connected."""
    from ser_accounts import ser_ready
    return {"status": "ok", "version": ext.version, "seranking_connected": await ser_ready(ctx)}
