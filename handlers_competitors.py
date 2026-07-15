"""Chat-function handlers: competitor tracking and keyword gap analysis.

Every function calls se-ranking-control's /v1/competitors/* — a fully
implemented, tested backend surface that was simply never wired up to any
chat function until now. See core/competitors/router.py + schemas.py on
se-ranking-control for the exact upstream response shapes this mirrors.
"""
# No `from __future__ import annotations` — see handlers.py for why.

from imperal_sdk import ui
from imperal_sdk.types import ActionResult

from app import chat
from api_client import call_ser
from params import (
    ListCompetitorsParams, AddCompetitorParams, DeleteCompetitorParams,
    CompetitorPositionsParams, SerpTop10Params, AllCompetitorsParams,
    CompetitorGapsParams,
)
from response_models import (
    CompetitorListResponse, CompetitorRecord, AddCompetitorResult,
    CompetitorPositionsResult, CompetitorPositionRecord,
    SerpTop10Result, SerpResultRecord,
    AllCompetitorsResult, AllCompetitorRecord,
    CompetitorGapsResult, CompetitorGapRecord,
)
from pydantic import BaseModel


def _err(data: dict) -> ActionResult:
    """Translate a call_ser error dict into an ActionResult."""
    return ActionResult.error(error=data.get("error", "unknown error"))


class _DeleteAck(BaseModel):
    deleted: bool = True
    competitor_id: int = 0


# ── List / Add / Delete ───────────────────────────────────────────────────────

@chat.function(
    "list_competitors",
    description=(
        "List the competitor domains tracked for a SE Ranking project. Use for: "
        "какие конкуренты отслеживаются, list my competitors, show tracked "
        "competitor domains."
    ),
    action_type="read",
    chain_callable=True,
    data_model=CompetitorListResponse,
)
async def fn_list_competitors(ctx, params: ListCompetitorsParams) -> ActionResult:
    """Return every competitor domain tracked for one SE Ranking project."""
    data = await call_ser(ctx, "GET", f"/v1/competitors/{params.project_id}", require_user_key=True)
    if "error" in data:
        return _err(data)
    raw = data.get("data") or []
    competitors = [CompetitorRecord(id=c.get("id", 0), name=c.get("name") or "",
                                     url=c.get("url", ""), domain_trust=c.get("domain_trust"))
                   for c in raw]
    result = CompetitorListResponse(project_id=params.project_id, competitors=competitors, count=len(competitors))
    rows = [c.model_dump() for c in competitors]
    ui_node = ui.DataTable(
        columns=[
            ui.DataColumn(key="url", label="Domain", width="45%"),
            ui.DataColumn(key="name", label="Name", width="30%"),
            ui.DataColumn(key="domain_trust", label="Domain Trust", width="25%"),
        ],
        rows=rows,
    ) if rows else ui.Empty(message="No competitors tracked yet — add one with add_competitor.")
    return ActionResult.success(data=result, summary=f"{len(competitors)} competitor(s) tracked", ui=ui_node)


@chat.function(
    "add_competitor",
    description=(
        "Add a competitor domain to track in a SE Ranking project — SE Ranking "
        "starts tracking their keyword positions daily. Use for: добавь "
        "конкурента, track this competitor, add competitor domain."
    ),
    action_type="write",
    event="se-ranking-connector.add_competitor",
    effects=["create:competitor"],
    data_model=AddCompetitorResult,
)
async def fn_add_competitor(ctx, params: AddCompetitorParams) -> ActionResult:
    """Add a competitor domain to a SE Ranking project's tracking list."""
    data = await call_ser(ctx, "POST", f"/v1/competitors/{params.project_id}", json={
        "url": params.url, "name": params.name,
    }, require_user_key=True)
    if "error" in data:
        return _err(data)
    result = AddCompetitorResult(id=data.get("id", 0), url=data.get("url", params.url),
                                  name=data.get("name") or "")
    return ActionResult.success(data=result, summary=f"Now tracking {result.url} as a competitor")


@chat.function(
    "delete_competitor",
    description=(
        "Stop tracking a competitor domain in a SE Ranking project. Use for: "
        "убери конкурента, stop tracking this competitor, remove competitor."
    ),
    action_type="write",
    event="se-ranking-connector.delete_competitor",
    effects=["delete:competitor"],
    data_model=_DeleteAck,
)
async def fn_delete_competitor(ctx, params: DeleteCompetitorParams) -> ActionResult:
    """Remove a competitor from a SE Ranking project's tracking list."""
    data = await call_ser(ctx, "DELETE", f"/v1/competitors/{params.project_id}/{params.competitor_id}",
                           require_user_key=True)
    if "error" in data:
        return _err(data)
    result = _DeleteAck(deleted=True, competitor_id=params.competitor_id)
    return ActionResult.success(data=result, summary=f"Competitor {params.competitor_id} removed from tracking")


# ── Positions / SERP ──────────────────────────────────────────────────────────

@chat.function(
    "competitor_positions",
    description=(
        "Keyword positions for one tracked competitor — how they rank for your "
        "project's tracked keywords. Use for: позиции конкурента, how does this "
        "competitor rank, competitor keyword positions."
    ),
    action_type="read",
    chain_callable=True,
    data_model=CompetitorPositionsResult,
)
async def fn_competitor_positions(ctx, params: CompetitorPositionsParams) -> ActionResult:
    """Return current keyword positions for one tracked competitor."""
    q = {}
    if params.engine_id:
        q["engine_id"] = params.engine_id
    data = await call_ser(ctx, "GET",
                           f"/v1/competitors/{params.project_id}/positions/{params.competitor_id}",
                           params=q, require_user_key=True)
    if "error" in data:
        return _err(data)
    raw = data.get("data") or []
    positions = []
    for block in raw:
        for kw in block.get("keywords", []):
            kw_positions = kw.get("positions", [])
            if not kw_positions:
                continue
            latest = sorted(kw_positions, key=lambda x: x["date"])[-1]
            positions.append(CompetitorPositionRecord(
                keyword=kw.get("name", ""), position=latest.get("pos"),
                change=latest.get("change", 0), volume=kw.get("volume", 0),
            ))
    result = CompetitorPositionsResult(project_id=params.project_id, competitor_id=params.competitor_id,
                                        positions=positions, count=len(positions))
    rows = [p.model_dump() for p in positions[:50]]
    ui_node = ui.DataTable(
        columns=[
            ui.DataColumn(key="keyword", label="Keyword", width="40%"),
            ui.DataColumn(key="position", label="Position", width="20%"),
            ui.DataColumn(key="change", label="Δ", width="15%"),
            ui.DataColumn(key="volume", label="Volume", width="25%"),
        ],
        rows=rows,
    ) if rows else ui.Empty(message="No position data for this competitor yet")
    return ActionResult.success(data=result, summary=f"{len(positions)} keyword position(s)", ui=ui_node)


@chat.function(
    "serp_top10",
    description=(
        "The current top-10 Google results for one specific tracked keyword — "
        "who's ranking, their backlinks/referring domains. Use for: топ-10 по "
        "ключевому слову, who ranks for this keyword, SERP results."
    ),
    action_type="read",
    chain_callable=True,
    data_model=SerpTop10Result,
)
async def fn_serp_top10(ctx, params: SerpTop10Params) -> ActionResult:
    """Return the top-10 SERP entries for one tracked keyword."""
    q = {"keyword_id": params.keyword_id, "engine_id": params.engine_id}
    if params.date:
        q["date"] = params.date
    data = await call_ser(ctx, "GET", f"/v1/competitors/{params.project_id}/top10", params=q,
                           require_user_key=True)
    if "error" in data:
        return _err(data)
    raw = data.get("data") or []
    results = [SerpResultRecord(position=e.get("position"), url=e.get("url") or "",
                                 domain=e.get("domain") or "", backlinks=e.get("backlinks"),
                                 referring_domains=e.get("referring_domains")) for e in raw]
    result = SerpTop10Result(project_id=params.project_id, keyword_id=params.keyword_id,
                              results=results, count=len(results))
    rows = [r.model_dump() for r in results]
    ui_node = ui.DataTable(
        columns=[
            ui.DataColumn(key="position", label="#", width="10%"),
            ui.DataColumn(key="domain", label="Domain", width="35%"),
            ui.DataColumn(key="backlinks", label="Backlinks", width="20%"),
            ui.DataColumn(key="referring_domains", label="Ref. Domains", width="20%"),
            ui.DataColumn(key="url", label="URL", width="15%"),
        ],
        rows=rows,
    ) if rows else ui.Empty(message="No SERP data for this keyword yet")
    return ActionResult.success(data=result, summary=f"Top {len(results)} result(s)", ui=ui_node)


@chat.function(
    "all_competitors",
    description=(
        "Every domain appearing in top-10 Google results for any of your "
        "tracked keywords — discover organic competitors you haven't added yet. "
        "Use for: кто ещё конкурирует, discover competitors, who else ranks for "
        "my keywords."
    ),
    action_type="read",
    chain_callable=True,
    data_model=AllCompetitorsResult,
)
async def fn_all_competitors(ctx, params: AllCompetitorsParams) -> ActionResult:
    """Return every domain appearing in top-10 results across the project's tracked keywords."""
    q = {}
    if params.engine_id:
        q["engine_id"] = params.engine_id
    if params.date:
        q["date"] = params.date
    data = await call_ser(ctx, "GET", f"/v1/competitors/{params.project_id}/all", params=q,
                           require_user_key=True)
    if "error" in data:
        return _err(data)
    raw = data.get("data") or []
    competitors = [AllCompetitorRecord(domain=c.get("domain", ""), backlinks=c.get("backlinks"),
                                        domains=c.get("domains"), visibility=c.get("visibility"))
                   for c in raw]
    result = AllCompetitorsResult(project_id=params.project_id, competitors=competitors, count=len(competitors))
    rows = [c.model_dump() for c in competitors[:50]]
    ui_node = ui.DataTable(
        columns=[
            ui.DataColumn(key="domain", label="Domain", width="40%"),
            ui.DataColumn(key="visibility", label="Visibility", width="20%"),
            ui.DataColumn(key="backlinks", label="Backlinks", width="20%"),
            ui.DataColumn(key="domains", label="Ref. Domains", width="20%"),
        ],
        rows=rows,
    ) if rows else ui.Empty(message="No organic competitor data yet")
    return ActionResult.success(data=result, summary=f"{len(competitors)} organic competitor domain(s) found", ui=ui_node)


# ── Gaps (the money function) ─────────────────────────────────────────────────

@chat.function(
    "competitor_gaps",
    description=(
        "Keywords where your tracked competitors rank in the top-10 but you "
        "don't (or rank much lower) — direct content opportunities for Article "
        "Writer briefs. Use for: пробелы против конкурентов, competitor "
        "keyword gaps, what keywords are competitors beating us on, content "
        "gap analysis."
    ),
    action_type="read",
    chain_callable=True,
    data_model=CompetitorGapsResult,
)
async def fn_competitor_gaps(ctx, params: CompetitorGapsParams) -> ActionResult:
    """Return keywords where tracked competitors outrank us (top-10 vs absent/much-lower)."""
    q = {}
    if params.engine_id:
        q["engine_id"] = params.engine_id
    data = await call_ser(ctx, "GET", f"/v1/competitors/{params.project_id}/gaps", params=q,
                           require_user_key=True)
    if "error" in data:
        return _err(data)
    raw = data.get("data") or []
    gaps = [CompetitorGapRecord(keyword=g.get("keyword", ""), competitor=g.get("competitor", ""),
                                 competitor_position=g.get("competitor_position", 0),
                                 our_position=g.get("our_position")) for g in raw]
    result = CompetitorGapsResult(project_id=params.project_id, gaps=gaps, count=len(gaps))
    rows = [g.model_dump() for g in gaps[:50]]
    ui_node = ui.DataTable(
        columns=[
            ui.DataColumn(key="keyword", label="Keyword", width="35%"),
            ui.DataColumn(key="competitor", label="Competitor", width="30%"),
            ui.DataColumn(key="competitor_position", label="Their Pos.", width="15%"),
            ui.DataColumn(key="our_position", label="Our Pos.", width="20%"),
        ],
        rows=rows,
    ) if rows else ui.Empty(message="No keyword gaps found — add competitors first with add_competitor.")
    return ActionResult.success(data=result, summary=f"{len(gaps)} keyword gap(s) found", ui=ui_node)
