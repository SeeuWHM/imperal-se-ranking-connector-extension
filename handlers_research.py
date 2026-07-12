"""Chat-function handlers: keyword research, domain analysis, project audit.

Split out of handlers.py to respect the 300-line file rule.
"""
# No `from __future__ import annotations` — see handlers.py for why.

from imperal_sdk.types import ActionResult

from app import chat
from api_client import call_ser, HEAVY_TIMEOUT
from params import (
    AuditParams, KeywordEstimateParams, KeywordExpandParams,
    DomainOverviewParams, DomainKeywordsParams,
)
from response_models import (
    KeywordCostEstimate, KeywordResearchResponse, DomainOverviewResponse,
    DomainKeywordsResponse, DomainKeywordRecord, AuditResponse, AuditIssue,
)


def _err(data: dict) -> ActionResult:
    """Translate a call_ser error dict into an ActionResult."""
    return ActionResult.error(error=data.get("error", "unknown error"))


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
