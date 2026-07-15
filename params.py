"""Pydantic param models for SE Ranking chat functions."""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


class ProjectIdParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID (from list_projects)")


class RankingsParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    engine_id: Optional[int] = Field(default=None, description="Filter by search engine ID (from list_projects)")


class OpportunitiesParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    min_volume: int = Field(default=0, description="Minimum monthly search volume filter")
    min_impressions: int = Field(default=50, description="Minimum GSC impressions filter")
    limit: int = Field(default=50, ge=1, le=200)


class CTRGapsParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    min_impressions: int = Field(default=100)
    max_ctr: float = Field(default=3.0, description="Max actual CTR %% to qualify as a gap")


class AuditParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    min_impressions: int = Field(default=100)


class KeywordEstimateParams(BaseModel):
    keyword: str = Field(..., description="Seed keyword to research")
    types: str = Field(default="longtail,questions,related", description="Comma-separated: longtail,questions,related")
    limit_per_type: int = Field(default=30, ge=1, le=200)


class KeywordExpandParams(BaseModel):
    keyword: str = Field(..., description="Seed keyword to expand")
    country: str = Field(default="us", description="2-letter country code")
    types: str = Field(default="longtail,questions,related")
    limit_per_type: int = Field(default=30, ge=1, le=200)


class DomainOverviewParams(BaseModel):
    domain: str = Field(..., description="Domain to analyze, e.g. competitor.com")
    country: str = Field(default="us")


class DomainKeywordsParams(BaseModel):
    domain: str = Field(..., description="Domain to analyze")
    country: str = Field(default="us")
    limit: int = Field(default=100, ge=1, le=1000)
    type: str = Field(default="organic", description="organic or paid")


class SaveKeyParams(BaseModel):
    seranking_api_key: str = Field(
        ..., min_length=1, max_length=200,
        description="Your SE Ranking API key, from online.seranking.com -> Profile -> API",
    )
    label: str = Field(
        default="", max_length=60,
        description="Optional display name for this account (e.g. 'Agency', 'Client X'). "
                    "Auto-generated if omitted.",
    )


class AccountLabelParams(BaseModel):
    label: str = Field(..., description="Account label (from list_seranking_accounts)")


# ── Competitors ──────────────────────────────────────────────────────────────

class ListCompetitorsParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")


class AddCompetitorParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    url: str = Field(..., description="Competitor domain to track, e.g. hostinger.com")
    name: Optional[str] = Field(default=None, description="Optional display name for the competitor")


class DeleteCompetitorParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    competitor_id: int = Field(..., description="Competitor ID (from list_competitors)")


class CompetitorPositionsParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    competitor_id: int = Field(..., description="Competitor ID (from list_competitors)")
    engine_id: Optional[int] = Field(default=None, description="Filter by search engine ID")


class SerpTop10Params(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    keyword_id: int = Field(..., description="Keyword ID (from the rankings response)")
    engine_id: int = Field(..., description="Search engine ID (from list_projects search engines)")
    date: Optional[str] = Field(default=None, description="Date YYYY-MM-DD, defaults to latest")


class AllCompetitorsParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    engine_id: Optional[int] = Field(default=None, description="Filter by search engine ID")
    date: Optional[str] = Field(default=None, description="Date YYYY-MM-DD, defaults to today")


class CompetitorGapsParams(BaseModel):
    project_id: int = Field(..., description="SE Ranking project ID")
    engine_id: Optional[int] = Field(default=None, description="Filter by search engine ID")


# ── Backlinks ────────────────────────────────────────────────────────────────

class BacklinksSummaryParams(BaseModel):
    domain: str = Field(..., description="Domain, host, or URL to analyze, e.g. competitor.com")
    mode: str = Field(
        default="domain",
        description="'domain' analyzes the whole domain incl. subdomains, "
                    "'host' analyzes this host only, 'url' analyzes one specific URL",
    )


class DomainAuthorityParams(BaseModel):
    domains: List[str] = Field(
        ..., min_length=1, max_length=100,
        description="Domains to score (up to 100), e.g. ['yoursite.com', 'competitor.com']",
    )
