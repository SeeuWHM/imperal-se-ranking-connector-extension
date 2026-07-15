"""Chat-function handlers for connecting/disconnecting/switching the user's
own SE Ranking account(s) — the primary, in-extension UX for entering an API
key (a real form in the sidebar), rather than relying on the platform's
general Secrets panel alone.

Multi-account: several SE Ranking keys can be connected at once and switched
between (accounts.py owns the JSON-blob storage + migration from the old
single-key secret). Same shape as the Google Search Console connector's
account handlers.
"""
# No `from __future__ import annotations` — see handlers.py for why.

from imperal_sdk.types import ActionResult

from app import chat
from api_client import call_ser
from accounts import (
    _add_account, _all_accounts, _disconnect_account, _mask, _switch_account,
)
from params import AccountLabelParams, SaveKeyParams
from response_models import (
    ConnectionStatus, SerAccountDisconnected, SerAccountRecord, SerAccountSwitched,
    SerAccountsList,
)
from pydantic import BaseModel


class _EmptyParams(BaseModel):
    """No input required."""


@chat.function(
    "connection_status",
    description=(
        "Whether the user's own SE Ranking API key is connected. Use for: "
        "подключен ли SE Ranking, is my account connected, connection status."
    ),
    action_type="read",
    chain_callable=True,
    data_model=ConnectionStatus,
)
async def fn_connection_status(ctx, params: _EmptyParams) -> ActionResult:
    """Report whether the caller has an active SE Ranking key configured."""
    accounts = await _all_accounts(ctx)
    active = next((a for a in accounts if a.get("is_active")), None)
    connected = bool(active)
    masked = _mask((active or {}).get("api_key", ""))
    result = ConnectionStatus(connected=connected, masked_key=masked)
    summary = f"Connected ({masked})" if connected else "Not connected"
    return ActionResult.success(data=result, summary=summary)


@chat.function(
    "save_seranking_key",
    description=(
        "Connect your own SE Ranking account by saving your API key. Validates "
        "the key against SE Ranking before saving — rejects it if invalid. "
        "Connecting again adds ANOTHER account (each with its own label) rather "
        "than replacing the current one — use switch_account to change which "
        "one is active. Use for: подключи мой SE Ranking, сохрани ключ, connect "
        "my SE Ranking account, save my API key, add seranking key, добавь ещё "
        "один аккаунт SE Ranking."
    ),
    action_type="write",
    event="se-ranking-connector.save_seranking_key",
    effects=["update:secret"],
    data_model=ConnectionStatus,
)
async def fn_save_seranking_key(ctx, params: SaveKeyParams) -> ActionResult:
    """Validate the given key against SE Ranking, then store it as a (new) account."""
    key = params.seranking_api_key.strip()
    if not key:
        return ActionResult.error(error="API key can't be empty.")

    # Validate BEFORE saving — one cheap real call through the backend using
    # the candidate key, so a typo'd/expired key never gets silently stored.
    check = await call_ser(ctx, "GET", "/v1/projects", headers_override={"X-SER-API-Key": key})
    if "error" in check and not check.get("_config"):
        return ActionResult.error(
            error=f"That key was rejected by SE Ranking: {check['error']}. Double-check it at "
                  f"online.seranking.com -> Profile -> API and try again.",
            retryable=True,
        )
    if check.get("_config"):
        return ActionResult.error(error=check["error"], retryable=True)

    account = await _add_account(ctx, key, params.label)
    result = ConnectionStatus(connected=True, masked_key=_mask(account["api_key"]))
    return ActionResult.success(
        data=result,
        summary=f"Connected to SE Ranking as {account['label']!r} ({result.masked_key}).",
        refresh_panels=["sidebar"],
    )


@chat.function(
    "list_seranking_accounts",
    description=(
        "List every SE Ranking account you've connected — label, masked key, "
        "which one is active. Use for: покажи мои аккаунты se ranking, list "
        "connected accounts, which SE Ranking account is active."
    ),
    action_type="read",
    chain_callable=True,
    data_model=SerAccountsList,
)
async def fn_list_seranking_accounts(ctx, params: _EmptyParams) -> ActionResult:
    """Every connected SE Ranking account with its label, masked key, and
    which one is currently active."""
    accounts = await _all_accounts(ctx)
    records = [
        SerAccountRecord(label=a.get("label", ""), masked_key=_mask(a.get("api_key", "")),
                          is_active=bool(a.get("is_active")))
        for a in accounts
    ]
    result = SerAccountsList(accounts=records, count=len(records))
    return ActionResult.success(data=result, summary=f"{len(records)} SE Ranking account(s) connected.")


@chat.function(
    "switch_seranking_account",
    description=(
        "Switch which connected SE Ranking account is active — all following "
        "SE Ranking calls (projects, rankings, keywords…) use this account's "
        "key. Use for: переключи аккаунт se ranking, switch to account X, use "
        "my other SE Ranking key."
    ),
    action_type="write",
    event="se-ranking-connector.switch_account",
    effects=["update:secret"],
    data_model=SerAccountSwitched,
)
async def fn_switch_seranking_account(ctx, params: AccountLabelParams) -> ActionResult:
    """Make one already-connected SE Ranking account the active one."""
    try:
        account = await _switch_account(ctx, params.label)
    except RuntimeError as e:
        return ActionResult.error(error=str(e), retryable=False)
    return ActionResult.success(
        data=SerAccountSwitched(active=account["label"]),
        summary=f"Switched to {account['label']!r}.",
        refresh_panels=["sidebar"],
    )


@chat.function(
    "disconnect_seranking_account",
    description=(
        "Disconnect ONE specific connected SE Ranking account by its label — "
        "removes only that key, other connected accounts stay untouched. Use "
        "for: отключи этот аккаунт se ranking, remove this specific account."
    ),
    action_type="destructive",
    event="se-ranking-connector.disconnect_account",
    effects=["delete:secret"],
    data_model=SerAccountDisconnected,
)
async def fn_disconnect_seranking_account(ctx, params: AccountLabelParams) -> ActionResult:
    """Remove one connected SE Ranking account by its label, leaving the rest untouched."""
    try:
        remaining = await _disconnect_account(ctx, params.label)
    except RuntimeError as e:
        return ActionResult.error(error=str(e), retryable=False)
    return ActionResult.success(
        data=SerAccountDisconnected(label=params.label, remaining=remaining),
        summary=f"Disconnected {params.label!r}. {remaining} account(s) remain.",
        refresh_panels=["sidebar"],
    )


@chat.function(
    "disconnect_seranking",
    description=(
        "Disconnect your SE Ranking account(s) — removes ALL saved API keys. "
        "Use for: отключи SE Ranking, disconnect my account, remove my API key, "
        "забудь мой ключ, disconnect everything."
    ),
    action_type="destructive",
    event="se-ranking-connector.disconnect_seranking",
    effects=["delete:secret"],
    data_model=ConnectionStatus,
)
async def fn_disconnect_seranking(ctx, params: _EmptyParams) -> ActionResult:
    """Remove every stored SE Ranking key (legacy full-disconnect action)."""
    accounts = await _all_accounts(ctx)
    for a in list(accounts):
        await _disconnect_account(ctx, a["label"])
    result = ConnectionStatus(connected=False, masked_key="")
    return ActionResult.success(
        data=result,
        summary="Disconnected. All your SE Ranking accounts have been removed.",
        refresh_panels=["sidebar"],
    )
