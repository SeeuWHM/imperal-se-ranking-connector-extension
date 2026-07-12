"""Sidebar panel — connection form + quick project overview.

The primary, in-extension way to connect a user's own SE Ranking account:
a real password-masked form right here, not a trip through the platform's
general Secrets panel. Submitting the form calls save_seranking_key
(handlers_settings.py), which validates the key against SE Ranking before
storing it.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from api_client import call_ser, ser_ready


def _connect_form(error: str = "") -> ui.UINode:
    children = [
        ui.Header(text="SE Ranking", level=4),
        ui.Badge(label="○ not connected", color="gray"),
        ui.Divider(),
        ui.Text(content=(
            "Connect your own SE Ranking account to see project rankings, "
            "content opportunities and keyword research here."
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
        ],
    ))
    children.append(ui.Text(
        content="Get your key at online.seranking.com → Profile → API.",
        variant="caption",
    ))
    return ui.Stack(children=children)


@ext.panel("sidebar", slot="left", title="SE Ranking", icon="TrendingUp",
           default_width=260,
           refresh="on_event:ser.settings.saved")
async def sidebar_panel(ctx):
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

    return ui.Stack(children=[
        ui.Header(text="SE Ranking", level=4),
        ui.Badge(label="● connected", color="green"),
        ui.Divider(),
        ui.Stats(children=[
            ui.Stat(label="Projects", value=len(projects)),
            ui.Stat(label="Keywords tracked", value=total_keywords),
        ]),
        ui.Divider(),
        ui.List(items=[
            ui.ListItem(id=str(p.get("id", "")), title=p.get("title", ""), subtitle=p.get("url", ""),
                        meta=f"{p.get('keyword_count', 0)} kw")
            for p in projects[:8]
        ]) if projects else ui.Text(content="No projects yet — add one at seranking.com.", variant="caption"),
        ui.Divider(),
        ui.Button(label="Disconnect", variant="ghost", size="sm",
                  on_click=ui.Call("disconnect_seranking")),
    ])
