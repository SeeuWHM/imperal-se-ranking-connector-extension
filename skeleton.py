"""Skeleton context providers for SE Ranking.

Per Imperal SDK: skeleton = LLM context cache holding ready API responses.
More data here = better Webbee routing and answers, with zero extra round-trips.
"""
from app import ext
from api_client import call_ser, ser_ready


@ext.skeleton("ser_config", ttl=300,
              description="SE Ranking connection status — whether the user's own API key is configured")
async def skeleton_refresh_ser_config(ctx) -> dict:
    configured = await ser_ready(ctx)
    return {"response": {
        "configured": configured,
        "instruction": (
            "SE Ranking not configured — tell the user to open Settings and add "
            "their own SE Ranking API key (from seranking.com → API Dashboard) "
            "before asking about projects/rankings/opportunities."
            if not configured else
            "SE Ranking is configured. Call list_projects to see tracked sites."
        ),
    }}


@ext.skeleton("ser_projects", ttl=600,
              description="List of the user's tracked SE Ranking projects — id, title, url, keyword count")
async def skeleton_refresh_ser_projects(ctx) -> dict:
    if not await ser_ready(ctx):
        return {"response": {"configured": False, "projects": []}}

    data = await call_ser(ctx, "GET", "/v1/projects", require_user_key=True)
    if "error" in data:
        return {"response": {"configured": True, "projects": [], "error": data["error"]}}

    projects = data.get("data") or []
    return {"response": {
        "configured": True,
        "projects": [
            {"id": p["id"], "title": p.get("title", ""), "url": p.get("url", ""),
             "keyword_count": p.get("keyword_count", 0)}
            for p in projects
        ],
    }}
