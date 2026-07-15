"""Multi-account SE Ranking key storage.

The platform's generic Secrets panel only ever holds ONE named value per
secret, so multi-account (several SE Ranking API keys, switchable) can't
live in the single `seranking_api_key` secret used until now — it has to be
an extension-owned JSON blob, same pattern as mail-client's
`imap_credentials` (write_mode="extension", one JSON document holding every
connected credential).

`seranking_accounts` holds: [{"label": str, "api_key": str, "is_active": bool}, ...]

Backward compat: a user who already connected via the OLD single-key
`seranking_api_key` secret must not lose that connection. On first read,
if no `seranking_accounts` exist yet but a legacy key is set, it's migrated
into a single "Default" account — transparent, no action needed from the
user.
"""
from __future__ import annotations

import json

ACCOUNTS_SECRET = "seranking_accounts"
LEGACY_KEY_SECRET = "seranking_api_key"


def _mask(key: str) -> str:
    key = (key or "").strip()
    if not key:
        return ""
    tail = key[-4:] if len(key) >= 4 else key
    return f"••••{tail}"


async def _load_raw(ctx) -> list[dict]:
    raw = await ctx.secrets.get(ACCOUNTS_SECRET)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def _save_raw(ctx, accounts: list[dict]) -> None:
    await ctx.secrets.set(ACCOUNTS_SECRET, json.dumps(accounts))


async def _all_accounts(ctx) -> list[dict]:
    """Every connected SE Ranking key, migrating the legacy single-key secret
    into a "Default" account on first read if no accounts exist yet."""
    accounts = await _load_raw(ctx)
    if accounts:
        return accounts

    legacy = (await ctx.secrets.get(LEGACY_KEY_SECRET) or "").strip()
    if not legacy:
        return []

    migrated = [{"label": "Default", "api_key": legacy, "is_active": True}]
    await _save_raw(ctx, migrated)
    return migrated


async def _active_account(ctx) -> dict | None:
    accounts = await _all_accounts(ctx)
    if not accounts:
        return None
    return next((a for a in accounts if a.get("is_active")), accounts[0])


async def _active_api_key(ctx) -> str:
    """The currently-active connected key, or '' if none connected."""
    acc = await _active_account(ctx)
    return (acc or {}).get("api_key", "").strip()


async def ser_ready(ctx) -> bool:
    """Whether the caller has at least one SE Ranking key connected."""
    return bool(await _active_api_key(ctx))


async def _add_account(ctx, api_key: str, label: str = "") -> dict:
    """Add a new connected key (becomes active). If this exact key is
    already connected, just re-activates it instead of duplicating."""
    accounts = await _all_accounts(ctx)
    api_key = api_key.strip()

    existing = next((a for a in accounts if a.get("api_key") == api_key), None)
    if existing:
        for a in accounts:
            a["is_active"] = (a is existing)
        await _save_raw(ctx, accounts)
        return existing

    default_label = f"Account {len(accounts) + 1}" if accounts else "Default"
    label = label.strip() or default_label
    for a in accounts:
        a["is_active"] = False
    new_account = {"label": label, "api_key": api_key, "is_active": True}
    accounts.append(new_account)
    await _save_raw(ctx, accounts)
    return new_account


async def _switch_account(ctx, label: str) -> dict:
    accounts = await _all_accounts(ctx)
    match = next((a for a in accounts if a.get("label") == label), None)
    if not match:
        available = [a.get("label") for a in accounts]
        raise RuntimeError(f"Account {label!r} not found. Connected: {available}")
    for a in accounts:
        a["is_active"] = (a is match)
    await _save_raw(ctx, accounts)
    return match


async def _disconnect_account(ctx, label: str) -> int:
    accounts = await _all_accounts(ctx)
    match = next((a for a in accounts if a.get("label") == label), None)
    if not match:
        available = [a.get("label") for a in accounts]
        raise RuntimeError(f"Account {label!r} not found. Connected: {available}")
    was_active = match.get("is_active", False)
    remaining = [a for a in accounts if a is not match]
    if was_active and remaining:
        remaining[0]["is_active"] = True
    await _save_raw(ctx, remaining)
    # Also clear the legacy secret if this was the migrated default — avoids
    # re-migrating a disconnected key back in on the next _all_accounts() call.
    if not remaining:
        await ctx.secrets.delete(LEGACY_KEY_SECRET)
    return len(remaining)
