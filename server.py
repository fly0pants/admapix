"""Standalone AdMapix MCP server exposing raw ad creative search data."""

from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP


API_BASE_URL = os.environ.get("ADMAPIX_API_BASE", "https://api.admapix.com")
API_KEY = os.environ.get("ADMAPIX_API_KEY") or os.environ.get("API_KEY", "")
SORT_FIELDS = {"3", "4", "11", "15"}
SORT_RULES = {"asc", "desc"}

mcp_server = FastMCP("admapix")


@mcp_server.tool()
async def search_creatives(
    keyword: str = "",
    creative_team: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_field: str = "3",
    sort_rule: str = "desc",
    country_ids: list[str] | None = None,
    trade_level1: list[str] | None = None,
) -> dict:
    """Search AdMapix advertising creatives and return raw data."""
    sort_field = str(sort_field)
    sort_rule = str(sort_rule).lower()

    if page < 1:
        return _invalid_parameter("page", "page must be >= 1")
    if page_size < 1 or page_size > 60:
        return _invalid_parameter("page_size", "page_size must be between 1 and 60")
    if sort_field not in SORT_FIELDS:
        return _invalid_parameter("sort_field", 'sort_field must be one of "3", "4", "11", "15"')
    if sort_rule not in SORT_RULES:
        return _invalid_parameter("sort_rule", 'sort_rule must be "asc" or "desc"')

    params = {
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
        "sort_field": sort_field,
        "sort_rule": sort_rule,
    }
    if creative_team:
        params["creative_team"] = creative_team
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if country_ids:
        params["country_ids"] = country_ids
    if trade_level1:
        params["trade_level1"] = trade_level1

    return await _call_admapix_search(params)


async def _call_admapix_search(params: dict) -> dict:
    if not API_KEY:
        return _error("missing_api_key", "Missing ADMAPIX_API_KEY environment variable")

    body = _build_search_body(params)
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(
                f"{API_BASE_URL}/api/data/search",
                json=body,
                headers=headers,
            )
    except httpx.TimeoutException:
        return _error("timeout", "Request timed out", retry=True)
    except Exception as exc:
        return _error("request_failed", f"Request failed: {exc}")

    if response.status_code == 401:
        return _error("auth_failed", "Authentication failed: invalid API key")
    if response.status_code == 403:
        return _error("forbidden", "Access forbidden")
    if response.status_code == 429:
        return _error("rate_limited", "Rate limited; try again later", retry=True)

    try:
        data = response.json()
    except ValueError:
        return _error("invalid_response", "AdMapix returned a non-JSON response")

    if isinstance(data.get("detail"), str):
        msg = data["detail"]
        code = "quota_exhausted" if "quota" in msg.lower() else "api_error"
        return _error(code, msg)

    result = dict(data)
    result["request"] = body
    result["page"] = body["page"]
    result["page_size"] = body["page_size"]
    result.setdefault("list", [])
    return result


def _build_search_body(params: dict) -> dict:
    body: dict = {
        "content_type": "creative",
        "keyword": params.get("keyword", ""),
        "page": max(int(params.get("page") or 1), 1),
        "page_size": min(max(int(params.get("page_size") or 20), 1), 60),
        "sort_field": params.get("sort_field", "3"),
        "sort_rule": params.get("sort_rule", "desc"),
    }
    for key in ("start_date", "end_date", "country_ids", "creative_team", "trade_level1"):
        if params.get(key):
            body[key] = params[key]
    return body


def _invalid_parameter(name: str, message: str) -> dict:
    return {"error": {"code": "invalid_parameter", "parameter": name, "message": message, "retry": False}}


def _error(code: str, message: str, retry: bool = False) -> dict:
    return {"error": {"code": code, "message": message, "retry": retry}}


if __name__ == "__main__":
    mcp_server.run(transport="stdio")
