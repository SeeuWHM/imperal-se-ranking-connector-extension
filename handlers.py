"""Chat-function handlers: projects, rankings, harvest opportunities.

Every function calls se-ranking-control (see api_client.call_ser) and
degrades gracefully with a friendly error when secrets aren't configured.

See handlers_research.py for keyword research / domain analysis / audit.
"""
# No `from __future__ import annotations` — chat.function's param validator
# needs real runtime type annotations (see matomo-analytics-extension for
# the same convention/reasoning).

from imperal_sdk import ui
from imperal_sdk.types import ActionResult

from app import chat
from api_client import call_ser
from params import ProjectIdParams, RankingsParams, OpportunitiesParams, CTRGapsParams
from response_models import (
    ProjectListResponse, ProjectRecord, RankingsResponse, RankingRecord,
    OpportunitiesResponse, OpportunityRecord, CTRGapsResponse, CTRGapRecord,
)
from pydantic import BaseModel


def _err(data: dict) -> ActionResult:
    """Translate a call_ser error dict into an ActionResult."""
    return ActionResult.error(error=data.get("error", "unknown error"))


class _EmptyParams(BaseModel):
    """No input required."""


# ── Projects ──────────────────────────────────────────────────────────────────

@chat.function(
    "list_projects",
    description=(
        "List your SE Ranking projects (tracked websites) — id, title, url, "
        "keyword count. Use for: покажи мои проекты, какие сайты отслеживаются, "
        "list my SE Ranking projects, show tracked sites."
    ),
    action_type="read",
    chain_callable=True,
    data_model=ProjectListResponse,
)
async def fn_list_projects(ctx, params: _EmptyParams) -> ActionResult:
    """Return every SE Ranking project tracked under the user's own account."""
    data = await call_ser(ctx, "GET", "/v1/projects", require_user_key=True)
    if "error" in data:
        return _err(data)
    raw = data.get("data") or []
    projects = [ProjectRecord(id=p["id"], title=p.get("title", ""), url=p.get("url", ""),
                               keywords=p.get("keyword_count", 0)) for p in raw]
    result = ProjectListResponse(projects=projects, count=len(projects))
    rows = [p.model_dump() for p in projects]
    ui_node = ui.DataTable(
        columns=[
            ui.DataColumn(key="id", label="ID", width="15%"),
            ui.DataColumn(key="title", label="Project", width="35%"),
            ui.DataColumn(key="url", label="URL", width="35%"),
            ui.DataColumn(key="keywords", label="Keywords", width="15%"),
        ],
        rows=rows,
    ) if rows else ui.Empty(message="No projects yet")
    return ActionResult.success(data=result, summary=f"{len(projects)} project(s)", ui=ui_node)


# ── Rankings ──────────────────────────────────────────────────────────────────

@chat.function(
    "rankings",
    description=(
        "Current Google search positions for all tracked keywords in a project — "
        "position, change, volume, CPC. Use for: покажи позиции, SEO rankings, "
        "какие позиции у ключевых слов, current rankings, keyword positions."
    ),
    action_type="read",
    chain_callable=True,
    data_model=RankingsResponse,
)
async def fn_rankings(ctx, params: RankingsParams) -> ActionResult:
    """Return current tracked keyword positions for one SE Ranking project."""
    q = {}
    if params.engine_id:
        q["engine_id"] = params.engine_id
    data = await call_ser(ctx, "GET", f"/v1/rankings/{params.project_id}", params=q, require_user_key=True)
    if "error" in data:
        return _err(data)
    kws = data.get("data") or []
    rankings = [RankingRecord(keyword=k.get("name", ""), position=str(k.get("current_position") or "-"),
                               change=k.get("change", 0), volume=k.get("volume", 0)) for k in kws[:30]]
    result = RankingsResponse(project_id=params.project_id, rankings=rankings, count=len(kws))
    rows = [r.model_dump() for r in rankings]
    ui_node = ui.DataTable(
        columns=[
            ui.DataColumn(key="keyword", label="Keyword", width="40%"),
            ui.DataColumn(key="position", label="Position", width="20%"),
            ui.DataColumn(key="change", label="Δ", width="15%"),
            ui.DataColumn(key="volume", label="Volume", width="25%"),
        ],
        rows=rows,
    ) if rows else ui.Empty(message="No ranking data")
    return ActionResult.success(data=result, summary=f"{len(kws)} keyword(s) tracked", ui=ui_node)


# ── Harvest (zero-credit content opportunities) ───────────────────────────────

@chat.function(
    "opportunities",
    description=(
        "Content opportunities from data SE Ranking already collected (zero extra "
        "credits): quick wins (ranking 4-20, easy to push to page 1), CTR gaps "
        "(showing in search but nobody clicks), keywords not tracked yet. "
        "Use for: что писать дальше, quick wins, content opportunities, "
        "какие темы улучшить, over what should I write next."
    ),
    action_type="read",
    chain_callable=True,
    data_model=OpportunitiesResponse,
)
async def fn_opportunities(ctx, params: OpportunitiesParams) -> ActionResult:
    """Return zero-credit content opportunities (quick wins, untracked keywords)."""
    data = await call_ser(ctx, "GET", f"/v1/harvest/{params.project_id}/opportunities", params={
        "min_volume": params.min_volume, "min_impressions": params.min_impressions,
        "limit": params.limit,
    }, require_user_key=True)
    if "error" in data:
        return _err(data)
    raw = data.get("data") or []
    opps = [OpportunityRecord(keyword=o.get("keyword", ""), type=o.get("type", ""),
                               priority=o.get("priority_score", 0)) for o in raw[:30]]
    result = OpportunitiesResponse(project_id=params.project_id, opportunities=opps, count=len(raw))
    rows = [o.model_dump() for o in opps]
    ui_node = ui.DataTable(
        columns=[
            ui.DataColumn(key="keyword", label="Keyword", width="50%"),
            ui.DataColumn(key="type", label="Type", width="25%"),
            ui.DataColumn(key="priority", label="Priority", width="25%"),
        ],
        rows=rows,
    ) if rows else ui.Empty(message="No opportunities found")
    return ActionResult.success(data=result, summary=f"{len(raw)} opportunit{'y' if len(raw) == 1 else 'ies'}", ui=ui_node)


@chat.function(
    "ctr_gaps",
    description=(
        "Keywords with high search impressions but low click-through rate — "
        "titles/meta descriptions likely need work. Use for: CTR gaps, "
        "низкий CTR, что не кликают, improve click-through rate."
    ),
    action_type="read",
    chain_callable=True,
    data_model=CTRGapsResponse,
)
async def fn_ctr_gaps(ctx, params: CTRGapsParams) -> ActionResult:
    """Return keywords with high impressions but low CTR (content/meta needs work)."""
    data = await call_ser(ctx, "GET", f"/v1/harvest/{params.project_id}/ctr-gaps", params={
        "min_impressions": params.min_impressions, "max_ctr": params.max_ctr,
    }, require_user_key=True)
    if "error" in data:
        return _err(data)
    raw = data.get("data") or []
    gaps = [CTRGapRecord(keyword=g.get("keyword", ""), impressions=g.get("impressions", 0),
                          ctr=g.get("ctr", 0), position=g.get("position", 0)) for g in raw]
    result = CTRGapsResponse(project_id=params.project_id, gaps=gaps, count=len(gaps))
    return ActionResult.success(data=result, summary=f"{len(gaps)} CTR gap(s) found")
