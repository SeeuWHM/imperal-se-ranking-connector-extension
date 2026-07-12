"""Chat-function handlers: projects, rankings, harvest opportunities,
keyword research, domain analysis, project audit.

Every function calls se-ranking-control (see api_client.call_ser) and
degrades gracefully with a friendly error when secrets aren't configured.
"""
# No `from __future__ import annotations` — chat.function's param validator
# needs real runtime type annotations (see matomo-analytics-extension for
# the same convention/reasoning).

from imperal_sdk import ui
from imperal_sdk.types import ActionResult

from app import chat, ext
from api_client import call_ser, HEAVY_TIMEOUT
from params import (
    ProjectIdParams, RankingsParams, OpportunitiesParams, CTRGapsParams,
    AuditParams, KeywordEstimateParams, KeywordExpandParams,
    DomainOverviewParams, DomainKeywordsParams,
)
from response_models import (
    ProjectListResponse, ProjectRecord, RankingsResponse, RankingRecord,
    OpportunitiesResponse, OpportunityRecord, CTRGapsResponse, CTRGapRecord,
    KeywordCostEstimate, KeywordResearchResponse, DomainOverviewResponse,
    DomainKeywordsResponse, DomainKeywordRecord, AuditResponse, AuditIssue,
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


# ── Keyword research (Data API, costs credits) ────────────────────────────────

@chat.function(
    "estimate_keyword_cost",
    description=(
        "Estimate SE Ranking credit cost for researching a keyword BEFORE spending "
        "any — always call this first. Use for: сколько это будет стоить, estimate "
        "cost, credit estimate for keyword research."
    ),
    action_type="read",
    chain_callable=True,
    data_model=KeywordCostEstimate,
)
async def fn_estimate_keyword_cost(ctx, params: KeywordEstimateParams) -> ActionResult:
    """Return the credit cost estimate for expanding a seed keyword, spending nothing."""
    data = await call_ser(ctx, "GET", "/v1/keywords/estimate", params={
        "keyword": params.keyword, "types": params.types, "limit_per_type": params.limit_per_type,
    })
    if "error" in data:
        return _err(data)
    result = KeywordCostEstimate(
        keyword=params.keyword,
        total_estimated_credits=data.get("total_estimated_credits", 0),
        breakdown=data.get("breakdown", {}),
    )
    return ActionResult.success(data=result, summary=f"Estimated cost: {result.total_estimated_credits} credits")


@chat.function(
    "research_keywords",
    description=(
        "Expand a seed keyword into longtail variants, related keywords and "
        "questions people ask — real SE Ranking data, spends credits. Use for: "
        "найди ключевые слова, keyword research, longtail keywords, related "
        "keywords, questions about topic, keyword ideas."
    ),
    action_type="read",
    chain_callable=True,
    data_model=KeywordResearchResponse,
)
async def fn_research_keywords(ctx, params: KeywordExpandParams) -> ActionResult:
    """Expand a seed keyword into longtail/related/question variants (spends credits)."""
    data = await call_ser(ctx, "POST", "/v1/keywords/expand", json={
        "keyword": params.keyword, "country": params.country,
        "types": params.types.split(","), "limit_per_type": params.limit_per_type,
    }, timeout=HEAVY_TIMEOUT)
    if "error" in data:
        return _err(data)
    result = KeywordResearchResponse(
        keyword=params.keyword, country=params.country,
        longtail=data.get("longtail", []), questions=data.get("questions", []),
        related=data.get("related", []),
        total_credits_spent=data.get("total_credits_spent", 0),
    )
    return ActionResult.success(data=result, summary=f"Keyword research for '{params.keyword}' complete")


# ── Domain analysis ───────────────────────────────────────────────────────────

@chat.function(
    "domain_overview",
    description=(
        "Traffic overview for any domain (yours or a competitor's) — organic "
        "traffic estimate, keyword count, top pages. Costs credits. Use for: "
        "анализ домена, domain overview, competitor traffic estimate."
    ),
    action_type="read",
    chain_callable=True,
    data_model=DomainOverviewResponse,
)
async def fn_domain_overview(ctx, params: DomainOverviewParams) -> ActionResult:
    """Return a traffic/keyword overview for any domain (spends credits)."""
    data = await call_ser(ctx, "GET", "/v1/domain/overview", params={
        "domain": params.domain, "country": params.country,
    })
    if "error" in data:
        return _err(data)
    result = DomainOverviewResponse(
        domain=params.domain, traffic=data.get("traffic"),
        keyword_count=data.get("keyword_count"), top_pages=data.get("top_pages", []),
    )
    return ActionResult.success(data=result, summary=f"Overview for {params.domain}")


@chat.function(
    "domain_keywords",
    description=(
        "Keywords a domain ranks for organically or via paid ads — volume, "
        "difficulty, position. Costs credits. Use for: ключевые слова конкурента, "
        "keywords a domain ranks for, competitor keyword list."
    ),
    action_type="read",
    chain_callable=True,
    data_model=DomainKeywordsResponse,
)
async def fn_domain_keywords(ctx, params: DomainKeywordsParams) -> ActionResult:
    """Return the keywords a domain ranks for, organic or paid (spends credits)."""
    data = await call_ser(ctx, "GET", "/v1/domain/keywords", params={
        "domain": params.domain, "country": params.country,
        "limit": params.limit, "type": params.type,
    })
    if "error" in data:
        return _err(data)
    raw = data.get("data") or []
    kws = [DomainKeywordRecord(keyword=k.get("keyword", ""), volume=k.get("volume", 0),
                                difficulty=k.get("difficulty"), position=k.get("position")) for k in raw]
    result = DomainKeywordsResponse(domain=params.domain, keywords=kws, count=len(kws))
    return ActionResult.success(data=result, summary=f"{len(kws)} keyword(s) found for {params.domain}")


# ── Audit ──────────────────────────────────────────────────────────────────────

@chat.function(
    "audit_project",
    description=(
        "Full project health audit — zero extra credits. Surfaces CTR gaps, "
        "keywords ranking but not tracked, deep-ranking slots wasting quota. "
        "Use for: аудит проекта, project audit, health check my SEO, "
        "what's wrong with my rankings."
    ),
    action_type="read",
    chain_callable=True,
    data_model=AuditResponse,
)
async def fn_audit_project(ctx, params: AuditParams) -> ActionResult:
    """Return a zero-credit SEO health audit for one tracked project."""
    data = await call_ser(ctx, "GET", f"/v1/audit/{params.project_id}", params={
        "min_impressions": params.min_impressions,
    }, require_user_key=True)
    if "error" in data:
        return _err(data)
    raw = data.get("issues") or []
    issues = [AuditIssue(type=i.get("type", ""), keyword=i.get("keyword", ""),
                          detail=i.get("detail", ""), severity=i.get("severity", "info")) for i in raw]
    result = AuditResponse(project_id=params.project_id, issues=issues, count=len(issues))
    return ActionResult.success(data=result, summary=f"{len(issues)} issue(s) found")
