"""AdMapix MCP Server — exposes ad creative search via STDIO transport.

Talks to the proxy API with X-API-Key authentication.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP
import httpx

# ── Config ────────────────────────────────────────────────────

API_BASE_URL = "https://ad.h5.miaozhisheng.tech"
API_KEY = os.environ.get("API_KEY", "")

mcp_server = FastMCP("admapix")


# ── Tool ──────────────────────────────────────────────────────


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
    delivery_channel: str | None = None,
    delivery_user_id: str | None = None,
) -> dict:
    """Search advertising creatives from AdMapix.

    Always generates an H5 result page and returns its URL in the page_url field.

    Args:
        keyword: Search keyword (supports app name, ad copy, advertiser, etc.)
        creative_team: Creative group type filter (e.g. ["100"] for image, ["010"] for video, ["001"] for playable)
        start_date: Start date in YYYY-MM-DD format (defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (defaults to today)
        page: Page number (default 1)
        page_size: Results per page (default 20, max 60)
        sort_field: Sort field - "3" first seen, "4" days found, "11" relevance, "15" impression
        sort_rule: Sort direction - "desc" or "asc"
        country_ids: Filter by country IDs (e.g. ["US", "JP"])
        trade_level1: Filter by industry category IDs
        delivery_channel: Delivery channel for H5 page (e.g. "wechat_kf", "feishu")
        delivery_user_id: External user ID for H5 page delivery actions
    """
    if not API_KEY:
        return {"error": "Missing API_KEY environment variable"}

    # Build flat request body for the proxy API
    body: dict = {
        "content_type": "creative",
        "keyword": keyword,
        "page": page,
        "page_size": min(page_size, 60),
        "sort_field": sort_field,
        "sort_rule": sort_rule,
    }
    if start_date:
        body["start_date"] = start_date
    if end_date:
        body["end_date"] = end_date
    if country_ids:
        body["country_ids"] = country_ids
    if trade_level1:
        body["trade_level1"] = trade_level1
    # creative_team is not directly supported by the proxy API's flat schema;
    # the proxy may ignore it or map it internally. Pass it anyway.
    if creative_team:
        body["creative_team"] = creative_team
    body["generate_page"] = True
    delivery_api_base = os.environ.get("DELIVERY_API_BASE", "https://ad.api.miaozhisheng.tech")
    delivery = {"apiBase": delivery_api_base}
    if delivery_channel:
        delivery["channel"] = delivery_channel
    if delivery_user_id:
        delivery["externalUserId"] = delivery_user_id
    if len(delivery) > 1:
        body["delivery"] = delivery

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.post(
                f"{API_BASE_URL}/api/data/search",
                json=body,
                headers=headers,
            )
            if r.status_code == 401:
                return {"error": "Authentication failed: invalid API key"}
            if r.status_code == 403:
                return {"error": "Access forbidden"}
            if r.status_code == 429:
                return {"error": "Rate limited — try again later"}

            data = r.json()

            # Check for error responses
            if "detail" in data and isinstance(data["detail"], str):
                msg = data["detail"]
                if "quota" in msg.lower():
                    return {"error": f"Quota exhausted: {msg}"}
                return {"error": msg}

    except httpx.TimeoutException:
        return {"error": "Request timed out"}
    except Exception as e:
        return {"error": f"Request failed: {e}"}

    # Extract items (same format as upstream)
    items = []
    for raw in data.get("list") or []:
        items.append({
            "id": raw.get("id"),
            "title": raw.get("title"),
            "describe": raw.get("describe"),
            "image_urls": raw.get("imageUrl") or [],
            "video_urls": raw.get("videoUrl") or [],
            "playable_urls": raw.get("playHtmlUrl") or [],
            "first_seen": raw.get("globalFirstTime") or raw.get("firstTime"),
            "last_seen": raw.get("globalLastTime") or raw.get("lastTime"),
            "days_found": raw.get("findCntSum") or raw.get("findCnt"),
            "impression": raw.get("impression"),
            "show_count": raw.get("showCnt") or raw.get("demoadCnt"),
            "ad_source": raw.get("adSource"),
            "apps": [
                {"name": a.get("name"), "pkg": a.get("pkg"), "logo": a.get("logo")}
                for a in (raw.get("appList") or [])
            ],
            "website": raw.get("webSite") or raw.get("demoadWebSite"),
        })

    result = {
        "total": data.get("totalSize"),
        "page": page,
        "page_size": min(page_size, 60),
        "items": items,
    }

    # Include page URL when H5 page was generated
    if data.get("page_url"):
        result["page_url"] = f"{API_BASE_URL}{data['page_url']}"
        result["page_key"] = data.get("page_key")
        result["page_expires_at"] = data.get("page_expires_at")

    return result


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    mcp_server.run(transport="stdio")
