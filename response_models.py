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


class KeywordResearchResponse(BaseModel):
    keyword: str = ""
    country: str = "us"
    longtail: List[str] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)
    total_credits_spent: float = 0


class DomainOverviewResponse(BaseModel):
    domain: str = ""
    traffic: Optional[float] = None
    keyword_count: Optional[int] = None
    top_pages: List[dict] = Field(default_factory=list)


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
