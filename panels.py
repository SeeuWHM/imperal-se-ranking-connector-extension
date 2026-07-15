"""Sidebar panel — account selector + connection form + full project list.

Multiple SE Ranking accounts can be connected simultaneously (accounts.py);
this panel lists them all with the active one marked, lets you switch/
disconnect, and shows the ACTIVE account's projects below. Submitting the
connect form calls save_seranking_key (handlers_settings.py), which validates
the key against SE Ranking before storing it.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from accounts import _all_accounts, _mask
from api_client import call_ser, ser_ready

_SHOWN_COLLAPSED = 8


def _connect_form(error: str = "") -> ui.UINode:
    children = [
        ui.Header(text="SE Ranking", level=4),
        ui.Badge(label="○ not connected", color="gray"),
        ui.Divider(),
        ui.Text(content=(
            "Connect your own SE Ranking account to see project rankings, "
            "content opportunities and keyword research here. You can connect "
            "more than one account and switch between them below."
        ), variant="body"),
    ]
    if error:
        children.append(ui.Alert(message=error, type="error"))
    children.append(ui.Form(
        action="save_seranking_key",
        submit_label="Connect",
        children=[
            ui.Password(placeholder="Paste your SE Ranking API key…",
                        param_name="seranking_api_key"),
            ui.Input(placeholder="Label (optional, e.g. \"Agency\")", param_name="label"),
        ],
    ))
    children.append(ui.Text(
        content="Get your key at online.seranking.com → Profile → API.",
        variant="caption",
    ))
    return ui.Stack(children=children)


def _account_items(accounts: list[dict]) -> list[ui.UINode]:
    """Every connected SE Ranking account, active one marked, click any other
    to switch. Without this block a second connected key had nowhere to
    render — connecting again looked like a no-op even though it worked."""
    items = []
    for acc in accounts:
        label = acc.get("label", "")
        is_active = bool(acc.get("is_active"))
        items.append(ui.ListItem(
            id=label, title=label,
            subtitle=f"{_mask(acc.get('api_key', ''))} — {'✓ Active' if is_active else 'Click to switch'}",
            avatar=ui.Avatar(fallback=label[0].upper() if label else "?", size="sm"),
            badge=ui.Badge("✓", color="green") if is_active else None,
            on_click=None if is_active else ui.Call("switch_seranking_account", label=label),
            actions=[{"label": "Disconnect", "icon": "Trash2",
                      "on_click": ui.Call("disconnect_seranking_account", label=label)}],
        ))
    return items


@ext.panel("sidebar", slot="left", title="SE Ranking", icon="TrendingUp",
           default_width=260,
           refresh="on_event:se-ranking-connector.switch_account,se-ranking-connector.disconnect_account")
async def sidebar_panel(ctx, show_all: bool = False):
    configured = await ser_ready(ctx)

    if not configured:
        return _connect_form()

    data = await call_ser(ctx, "GET", "/v1/projects", require_user_key=True)
    if "error" in data:
        # A stored key that SE Ranking now rejects (revoked/expired) should
        # drop back to the connect form with the real reason shown, not a
        # dead-end error card with no way to fix it.
        return _connect_form(error=data["error"])

    projects = data.get("data") or []
    total_keywords = sum(p.get("keyword_count", 0) for p in projects)

    # Rank by tracked keyword count so what actually matters shows first,
    # but no longer hard-cap at 8 — a "+N more" toggle expands to the full
    # list instead of pointing the user out to chat for it.
    tracked = sorted(
        (p for p in projects if p.get("keyword_count", 0) > 0),
        key=lambda p: p.get("keyword_count", 0),
        reverse=True,
    )
    shown = tracked if show_all else tracked[:_SHOWN_COLLAPSED]
    remaining = len(tracked) - len(shown)

    list_or_empty = (
        ui.List(items=[
            ui.ListItem(id=str(p.get("id", "")), title=p.get("title") or p.get("url", "untitled"),
                        subtitle=p.get("url", ""),
                        meta=f"{p.get('keyword_count', 0)} kwds",
                        on_click=ui.Call("__panel__workspace", project_id=str(p.get("id", ""))))
            for p in shown
        ])
        if shown else
        ui.Text(content="No tracked keywords yet on any project — add one at seranking.com.", variant="caption")
    )

    footer = (
        [ui.Button(label=f"+ {remaining} more project(s)", variant="ghost", size="sm",
                    on_click=ui.Call("__panel__sidebar", show_all=True))]
        if remaining > 0 else
        ([ui.Button(label="Show fewer", variant="ghost", size="sm",
                     on_click=ui.Call("__panel__sidebar", show_all=False))]
         if show_all and len(tracked) > _SHOWN_COLLAPSED else [])
    )

    accounts = await _all_accounts(ctx)

    root = ui.Stack(children=[
        ui.Header(text="SE Ranking", level=4),
        ui.Badge(label="● connected", color="green"),
        ui.Divider(),
        ui.Stats(children=[
            ui.Stat(label="Projects", value=str(len(projects)), icon="Folder"),
            ui.Stat(label="Keywords tracked", value=f"{total_keywords:,}", icon="Hash"),
        ]),
        ui.Divider(),
        ui.Text(content=f"Accounts ({len(accounts)})", variant="caption"),
        ui.List(items=_account_items(accounts)),
        ui.Stack(direction="h", gap=2, wrap=True, children=[
            ui.Button(label="Add another account", icon="Plus", variant="ghost", size="sm",
                      on_click=ui.Call("__panel__sidebar_add_account")),
        ]),
        ui.Divider(),
        ui.Text(content="Projects by tracked keywords — click one to open", variant="caption"),
        list_or_empty,
        *footer,
    ])
    # Claim the center slot — without this, project clicks from here would
    # open in "right" instead of "center" (same fix as article-writer's
    # sidebar needed).
    root.props["auto_action"] = ui.Call("__panel__workspace").to_dict()
    return root


@ext.panel("sidebar_add_account", slot="overlay", title="Add SE Ranking Account", icon="Plus")
async def add_account_panel(ctx):
    """Overlay form to connect an ADDITIONAL SE Ranking account without
    disturbing the currently-active one — same pattern as mail-client's
    add_account overlay."""
    return _connect_form()
