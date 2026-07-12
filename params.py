"""Pydantic param models for SE Ranking chat functions."""
from __future__ import annotations

from typing import Optional
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
