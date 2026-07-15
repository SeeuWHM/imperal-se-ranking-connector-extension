"""Center workspace panel — one project's rankings + top keyword
opportunities. Deliberately just these two (audit dropped 2026-07-15 — kept
scope tight) — reuses the exact same call_ser endpoints the chat functions
already call (handlers.py/handlers_research.py), just rendered directly
server-side — zero LLM tokens, same pattern as article-writer's own panels.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from api_client import call_ser

RANKINGS_LIMIT = 30
OPPORTUNITIES_LIMIT = 25


async def _rankings_section(ctx, project_id: str) -> ui.UINode:
    data = await call_ser(ctx, "GET", f"/v1/rankings/{project_id}", require_user_key=True)
    if "error" in data:
        return ui.Alert(message=data["error"], type="error")
    kws = data.get("keywords") or []
    rows = [
        {
            "keyword": k.get("name", ""),
            "position": str(k.get("current_position") or "-"),
            "change": k.get("change", 0),
            "volume": k.get("volume", 0),
        }
        for k in kws[:RANKINGS_LIMIT]
    ]
    body = ui.DataTable(
        columns=[
            ui.DataColumn(key="keyword", label="Keyword", width="40%"),
            ui.DataColumn(key="position", label="Position", width="20%"),
            ui.DataColumn(key="change", label="Δ", width="15%"),
            ui.DataColumn(key="volume", label="Volume", width="25%"),
        ],
        rows=rows,
    ) if rows else ui.Text(content="No ranking data yet.", variant="caption")
    return ui.Stack(gap=1, children=[
        ui.Header(text=f"Rankings ({len(kws)} tracked)", level=5), body,
    ])


async def _opportunities_section(ctx, project_id: str) -> ui.UINode:
    data = await call_ser(
        ctx, "GET", f"/v1/harvest/{project_id}/opportunities",
        params={"min_volume": 0, "min_impressions": 0, "limit": OPPORTUNITIES_LIMIT}, require_user_key=True,
    )
    if "error" in data:
        return ui.Alert(message=data["error"], type="error")
    raw = data.get("opportunities") or []
    rows = [
        {"keyword": o.get("keyword", ""), "type": o.get("type", ""), "priority": o.get("priority_score", 0)}
        for o in raw[:OPPORTUNITIES_LIMIT]
    ]
    body = ui.DataTable(
        columns=[
            ui.DataColumn(key="keyword", label="Keyword", width="50%"),
            ui.DataColumn(key="type", label="Type", width="25%"),
            ui.DataColumn(key="priority", label="Priority", width="25%"),
        ],
        rows=rows,
    ) if rows else ui.Text(content="No opportunities found.", variant="caption")
    return ui.Stack(gap=1, children=[
        ui.Header(text="Top keyword opportunities", level=5), body,
    ])


@ext.panel("workspace", slot="center", title="SE Ranking", icon="TrendingUp")
async def workspace_panel(ctx, project_id: str = ""):
    if not project_id:
        return ui.Empty(message="Pick a project on the left to see its rankings and top keyword opportunities.")

    rankings, opportunities = (
        await _rankings_section(ctx, project_id),
        await _opportunities_section(ctx, project_id),
    )
    return ui.Stack(children=[rankings, ui.Divider(), opportunities])
