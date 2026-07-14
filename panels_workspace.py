"""Center workspace panel — one project's rankings/opportunities/audit at a
glance. Minimal on purpose: reuses the exact same call_ser endpoints the
chat functions already call (handlers.py/handlers_research.py), just
rendered directly server-side — zero LLM tokens, same pattern as
article-writer's own panels.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from api_client import call_ser

_SEVERITY_COLOR = {"critical": "red", "warning": "yellow", "info": "gray"}


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
        for k in kws[:15]
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
        params={"min_volume": 0, "min_impressions": 0, "limit": 10}, require_user_key=True,
    )
    if "error" in data:
        return ui.Alert(message=data["error"], type="error")
    raw = data.get("opportunities") or []
    rows = [
        {"keyword": o.get("keyword", ""), "type": o.get("type", ""), "priority": o.get("priority_score", 0)}
        for o in raw[:10]
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
        ui.Header(text="Quick wins & CTR gaps", level=5), body,
    ])


async def _audit_section(ctx, project_id: str) -> ui.UINode:
    data = await call_ser(ctx, "GET", f"/v1/audit/{project_id}", params={"min_impressions": 0}, require_user_key=True)
    if "error" in data:
        return ui.Alert(message=data["error"], type="error")
    issues = data.get("issues") or []
    body = (
        ui.List(items=[
            ui.ListItem(
                id=str(i), title=issue.get("keyword") or issue.get("type", ""),
                subtitle=issue.get("detail", ""),
                badge=ui.Badge(label=issue.get("severity", "info"),
                                color=_SEVERITY_COLOR.get(issue.get("severity", "info"), "gray")),
            )
            for i, issue in enumerate(issues)
        ])
        if issues else ui.Text(content="No issues found — project looks healthy.", variant="caption")
    )
    return ui.Stack(gap=1, children=[
        ui.Header(text=f"Audit ({len(issues)} issue(s))", level=5), body,
    ])


@ext.panel("workspace", slot="center", title="SE Ranking", icon="TrendingUp")
async def workspace_panel(ctx, project_id: str = ""):
    if not project_id:
        return ui.Empty(message="Pick a project on the left to see its rankings, opportunities, and audit.")

    rankings, opportunities, audit = (
        await _rankings_section(ctx, project_id),
        await _opportunities_section(ctx, project_id),
        await _audit_section(ctx, project_id),
    )
    return ui.Stack(children=[rankings, ui.Divider(), opportunities, ui.Divider(), audit])
