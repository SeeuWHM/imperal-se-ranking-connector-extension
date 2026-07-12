"""Chat-function handlers for connecting/disconnecting the user's own
SE Ranking account — the primary, in-extension UX for entering the API key
(a proper ui.Form in the sidebar), rather than relying on the platform's
general Secrets panel alone.

`seranking_api_key` is declared write_mode="both": the platform Secrets
panel and this extension's own ctx.secrets.set() call both work and store
the exact same value.
"""
# No `from __future__ import annotations` — see handlers.py for why.

from imperal_sdk.types import ActionResult

from app import chat
from api_client import call_ser
from params import SaveKeyParams
from response_models import ConnectionStatus
from pydantic import BaseModel


class _EmptyParams(BaseModel):
    """No input required."""


def _mask(key: str) -> str:
    key = (key or "").strip()
    if not key:
        return ""
    tail = key[-4:] if len(key) >= 4 else key
    return f"••••{tail}"


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
    """Report whether the caller's own SE Ranking key is configured."""
    key = await ctx.secrets.get("seranking_api_key")
    key = (key or "").strip()
    result = ConnectionStatus(connected=bool(key), masked_key=_mask(key))
    summary = f"Connected ({result.masked_key})" if result.connected else "Not connected"
    return ActionResult.success(data=result, summary=summary)


@chat.function(
    "save_seranking_key",
    description=(
        "Connect your own SE Ranking account by saving your API key. Validates "
        "the key against SE Ranking before saving — rejects it if invalid. Use "
        "for: подключи мой SE Ranking, сохрани ключ, connect my SE Ranking "
        "account, save my API key, add seranking key."
    ),
    action_type="write",
    event="se-ranking-connector.save_seranking_key",
    effects=["update:secret"],
    data_model=ConnectionStatus,
)
async def fn_save_seranking_key(ctx, params: SaveKeyParams) -> ActionResult:
    """Validate the given key against SE Ranking, then store it for this user."""
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

    await ctx.secrets.set("seranking_api_key", key)
    result = ConnectionStatus(connected=True, masked_key=_mask(key))
    return ActionResult.success(
        data=result,
        summary=f"Connected to SE Ranking ({result.masked_key}).",
        refresh_panels=["sidebar"],
    )


@chat.function(
    "disconnect_seranking",
    description=(
        "Disconnect your SE Ranking account — removes the saved API key. Use "
        "for: отключи SE Ranking, disconnect my account, remove my API key, "
        "забудь мой ключ."
    ),
    action_type="write",
    event="se-ranking-connector.disconnect_seranking",
    effects=["delete:secret"],
    data_model=ConnectionStatus,
)
async def fn_disconnect_seranking(ctx, params: _EmptyParams) -> ActionResult:
    """Remove the caller's stored SE Ranking API key."""
    await ctx.secrets.delete("seranking_api_key")
    result = ConnectionStatus(connected=False, masked_key="")
    return ActionResult.success(
        data=result,
        summary="Disconnected. Your SE Ranking key has been removed.",
        refresh_panels=["sidebar"],
    )
