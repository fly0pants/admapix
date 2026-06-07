"""AdMapix MCP server exposing raw ad creative search data."""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from admapix_mcp.api import call_admapix_search


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
    """Search AdMapix advertising creatives and return raw data.

    Args:
        keyword: Search keyword, such as app name, ad copy, or advertiser.
        creative_team: Creative type codes, e.g. ["100"] image, ["010"] video, ["001"] playable.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        page: Page number, starting from 1.
        page_size: Results per page, 1-60.
        sort_field: Sort field: "3" first seen, "4" days active, "11" relevance, "15" impressions.
        sort_rule: Sort direction: "desc" or "asc".
        country_ids: Country codes, e.g. ["US", "JP"].
        trade_level1: Industry category IDs.
    """
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

    return await call_admapix_search(params, api_key=API_KEY, base_url=API_BASE_URL)


def _invalid_parameter(name: str, message: str) -> dict:
    return {"error": {"code": "invalid_parameter", "parameter": name, "message": message, "retry": False}}


if __name__ == "__main__":
    mcp_server.run(transport="stdio")
