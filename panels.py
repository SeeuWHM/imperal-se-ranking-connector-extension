"""Sidebar panel — connection status + quick project overview."""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from api_client import call_ser, ser_ready


@ext.panel("sidebar", slot="left", title="SE Ranking", icon="TrendingUp",
           default_width=260,
           refresh="on_event:ser.settings.saved")
async def sidebar_panel(ctx):
    configured = await ser_ready(ctx)

    if not configured:
        return ui.Stack(children=[
            ui.Header(text="SE Ranking", level=4),
            ui.Badge(label="○ not connected", color="gray"),
            ui.Divider(),
            ui.Alert(
                message=(
                    "Connect your own SE Ranking account to see project rankings, "
                    "content opportunities and keyword research here."
                ),
                type="info",
            ),
            ui.Text(content="Open Settings (gear icon in the top bar) → Secrets → "
                            "'SE Ranking API Key' to paste your key from "
                            "seranking.com → Profile → API.", variant="caption"),
        ])

    data = await call_ser(ctx, "GET", "/v1/projects", require_user_key=True)
    if "error" in data:
        return ui.Stack(children=[
            ui.Header(text="SE Ranking", level=4),
            ui.Badge(label="● error", color="red"),
            ui.Alert(message=data["error"], type="error"),
        ])

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
    ])
