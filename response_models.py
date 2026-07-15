"""Pydantic response models for SE Ranking chat functions.

Every @chat.function(action_type="read") must declare a data_model so the
platform can validate return shapes and prevent naming drift (federal V23).
"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


class ProjectRecord(BaseModel):
    id: int
    title: str = ""
    url: str = ""
    keywords: int = 0


class ProjectListResponse(BaseModel):
    projects: List[ProjectRecord] = Field(default_factory=list)
    count: int = 0


class RankingRecord(BaseModel):
    keyword: str = ""
    position: str = "-"
    change: int = 0
    volume: int = 0


class RankingsResponse(BaseModel):
    project_id: int
    rankings: List[RankingRecord] = Field(default_factory=list)
    count: int = 0


class OpportunityRecord(BaseModel):
    keyword: str = ""
    type: str = ""
    priority: float = 0


class OpportunitiesResponse(BaseModel):
    project_id: int
    opportunities: List[OpportunityRecord] = Field(default_factory=list)
    count: int = 0


class CTRGapRecord(BaseModel):
    keyword: str = ""
    impressions: int = 0
    ctr: float = 0
    position: float = 0


class CTRGapsResponse(BaseModel):
    project_id: int
    gaps: List[CTRGapRecord] = Field(default_factory=list)
    count: int = 0


class KeywordCostEstimate(BaseModel):
    keyword: str = ""
    total_estimated_credits: float = 0
    breakdown: dict = Field(default_factory=dict)


class KeywordIdea(BaseModel):
    """One expanded keyword idea — SE Ranking returns questions/related as
    objects with real metrics (volume/difficulty/cpc), not bare strings."""
    keyword: str = ""
    volume: Optional[int] = None
    difficulty: Optional[int] = None
    cpc: Optional[float] = None
    competition: Optional[float] = None
    relevance: Optional[float] = None


class KeywordResearchResponse(BaseModel):
    keyword: str = ""
    country: str = "us"
    longtail: List[str] = Field(default_factory=list)             # SE Ranking returns bare strings
    questions: List[KeywordIdea] = Field(default_factory=list)    # SE Ranking returns objects
    related: List[KeywordIdea] = Field(default_factory=list)      # SE Ranking returns objects
    total_credits_spent: float = 0


class DomainOverviewResponse(BaseModel):
    """Mirrors se-ranking-control's real /v1/domain/overview shape:
    {organic: {keywords_count, traffic_sum, ...}, adv: [...]} — there is no
    top-level traffic/keyword_count/top_pages field upstream."""
    domain: str = ""
    keywords_count: Optional[int] = None
    traffic_sum: Optional[int] = None
    top1_5: Optional[int] = None
    top6_10: Optional[int] = None
    top11_20: Optional[int] = None
    top21_50: Optional[int] = None
    top51_100: Optional[int] = None
    credits_spent: int = 0


class DomainKeywordRecord(BaseModel):
    keyword: str = ""
    volume: int = 0
    difficulty: Optional[float] = None
    position: Optional[float] = None


class DomainKeywordsResponse(BaseModel):
    domain: str = ""
    keywords: List[DomainKeywordRecord] = Field(default_factory=list)
    count: int = 0


class AuditIssue(BaseModel):
    type: str = ""
    keyword: str = ""
    detail: str = ""
    severity: str = "info"


class AuditResponse(BaseModel):
    project_id: int
    issues: List[AuditIssue] = Field(default_factory=list)
    count: int = 0


# ── Competitors ──────────────────────────────────────────────────────────────

class CompetitorRecord(BaseModel):
    id: int
    name: str = ""
    url: str = ""
    domain_trust: Optional[int] = None


class CompetitorListResponse(BaseModel):
    project_id: int
    competitors: List[CompetitorRecord] = Field(default_factory=list)
    count: int = 0


class AddCompetitorResult(BaseModel):
    id: int
    url: str = ""
    name: str = ""


class CompetitorPositionRecord(BaseModel):
    keyword: str = ""
    position: Optional[int] = None
    change: Optional[int] = None
    volume: Optional[int] = None


class CompetitorPositionsResult(BaseModel):
    project_id: int
    competitor_id: int
    positions: List[CompetitorPositionRecord] = Field(default_factory=list)
    count: int = 0


class SerpResultRecord(BaseModel):
    position: Optional[int] = None
    url: str = ""
    domain: str = ""
    backlinks: Optional[int] = None
    referring_domains: Optional[int] = None


class SerpTop10Result(BaseModel):
    project_id: int
    keyword_id: int
    results: List[SerpResultRecord] = Field(default_factory=list)
    count: int = 0


class AllCompetitorRecord(BaseModel):
    domain: str = ""
    backlinks: Optional[str] = None
    domains: Optional[str] = None
    visibility: Optional[float] = None


class AllCompetitorsResult(BaseModel):
    project_id: int
    competitors: List[AllCompetitorRecord] = Field(default_factory=list)
    count: int = 0


class CompetitorGapRecord(BaseModel):
    keyword: str = ""
    competitor: str = ""
    competitor_position: int = 0
    our_position: Optional[int] = None


class CompetitorGapsResult(BaseModel):
    project_id: int
    gaps: List[CompetitorGapRecord] = Field(default_factory=list)
    count: int = 0


class ConnectionStatus(BaseModel):
    connected: bool = False
    masked_key: str = ""
