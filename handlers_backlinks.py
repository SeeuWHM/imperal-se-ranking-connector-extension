"""Chat-function handlers: backlink authority for any domain (yours or a
competitor's) — costs SE Ranking credits per SE Ranking's own pricing.

Calls se-ranking-control's already-live /v1/domain/backlinks + /v1/domain/authority
(apps/domain/router.py — built on real SE Ranking Data API endpoints documented at
https://seranking.com/api/data/backlinks/). These simply weren't wired up to any
chat function before now.
"""
# No `from __future__ import annotations` — see handlers.py for why.

from imperal_sdk import ui
from imperal_sdk.types import ActionResult

from app import chat
from api_client import call_ser
from params import BacklinksSummaryParams, DomainAuthorityParams
from response_models import (
    BacklinksSummaryResult, AnchorRecord,
    DomainAuthorityResult, DomainAuthorityRecord,
)


def _err(data: dict) -> ActionResult:
    """Translate a call_ser error dict into an ActionResult."""
    return ActionResult.error(error=data.get("error", "unknown error"))


@chat.function(
    "backlinks_summary",
    description=(
        "Backlink authority summary for any domain (yours or a competitor's) — "
        "total backlinks, referring domains, dofollow/nofollow split, domain "
        "authority score, top anchor texts. Costs credits. Use for: "
        "backlink profile, domain authority, link authority."
    ),
    action_type="read",
    chain_callable=True,
    data_model=BacklinksSummaryResult,
)
async def fn_backlinks_summary(ctx, params: BacklinksSummaryParams) -> ActionResult:
    """Return aggregated backlink metrics for one domain/host/URL (spends credits)."""
    data = await call_ser(ctx, "GET", "/v1/domain/backlinks", params={
        "domain": params.domain, "mode": params.mode,
    }, require_user_key=True)
    if "error" in data:
        return _err(data)
    anchors = [
        AnchorRecord(anchor=a.get("anchor", ""), backlinks=a.get("backlinks", 0))
        for a in (data.get("top_anchors_by_backlinks") or [])[:10]
    ]
    result = BacklinksSummaryResult(
        target=data.get("target", params.domain),
        backlinks=data.get("backlinks", 0),
        refdomains=data.get("refdomains", 0),
        subnets=data.get("subnets", 0),
        ips=data.get("ips", 0),
        dofollow_backlinks=data.get("dofollow_backlinks", 0),
        nofollow_backlinks=data.get("nofollow_backlinks", 0),
        domain_inlink_rank=data.get("domain_inlink_rank"),
        pages_with_backlinks=data.get("pages_with_backlinks", 0),
        top_anchors=anchors,
        credits_spent=data.get("credits_spent", 0),
    )
    rows = [a.model_dump() for a in anchors]
    ui_node = ui.Section(title=f"Backlink profile: {result.target}", children=[
        ui.KeyValue(items=[
            {"key": "Backlinks", "value": str(result.backlinks)},
            {"key": "Referring domains", "value": str(result.refdomains)},
            {"key": "Domain authority", "value": str(result.domain_inlink_rank or "-")},
            {"key": "Dofollow / Nofollow", "value": f"{result.dofollow_backlinks} / {result.nofollow_backlinks}"},
        ], columns=2),
        ui.DataTable(
            columns=[
                ui.DataColumn(key="anchor", label="Anchor text", width="70%"),
                ui.DataColumn(key="backlinks", label="Backlinks", width="30%"),
            ],
            rows=rows,
        ) if rows else ui.Empty(message="No anchor data"),
    ])
    return ActionResult.success(
        data=result,
        summary=f"{result.target}: {result.backlinks} backlinks from {result.refdomains} referring domains",
        ui=ui_node,
    )


@chat.function(
    "domain_authority",
    description=(
        "Domain authority scores for up to 100 domains at once — quick way to "
        "compare your site's authority against several competitors in one call. "
        "Costs credits. Use for: domain authority "
        "comparison, competitor authority scores."
    ),
    action_type="read",
    chain_callable=True,
    data_model=DomainAuthorityResult,
)
async def fn_domain_authority(ctx, params: DomainAuthorityParams) -> ActionResult:
    """Return domain authority scores for a batch of domains (spends credits)."""
    data = await call_ser(ctx, "GET", "/v1/domain/authority", params={
        "domains": ",".join(params.domains),
    }, require_user_key=True)
    if "error" in data:
        return _err(data)
    rows_raw = data.get("data") or []
    domains = [
        DomainAuthorityRecord(domain=r.get("url", ""), domain_inlink_rank=r.get("domain_inlink_rank"))
        for r in rows_raw
    ]
    result = DomainAuthorityResult(
        domains=domains, count=len(domains), credits_spent=data.get("credits_spent", 0),
    )
    rows = [d.model_dump() for d in domains]
    ui_node = ui.DataTable(
        columns=[
            ui.DataColumn(key="domain", label="Domain", width="60%"),
            ui.DataColumn(key="domain_inlink_rank", label="Authority", width="40%"),
        ],
        rows=rows,
    ) if rows else ui.Empty(message="No authority data")
    return ActionResult.success(
        data=result, summary=f"Authority scores for {len(domains)} domain(s)", ui=ui_node,
    )
