"""Archived tool schemas and implementations for the deep research prototype.

Each tool is defined as:
1. A schema dict for the Anthropic API `tools` parameter
2. An async implementation function
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from agent.state import ResearchState, QueryResult
from agent.prompts import SUMMARIZE_SYSTEM, CROSS_ANALYZE_SYSTEM, REPORT_SYSTEM

# ── Tool Schemas ──────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "search_creatives",
        "description": (
            "Search AdMapix for advertising creatives. Returns items with metrics "
            "(impressions, days active, ad copy, media URLs). Supports pagination."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Search keyword (app name, ad copy, advertiser)"},
                "country_ids": {"type": "array", "items": {"type": "string"}, "description": "Country codes, e.g. ['US','JP']"},
                "creative_team": {"type": "array", "items": {"type": "string"}, "description": "Creative type: '100'=image,'010'=video,'001'=playable"},
                "sort_field": {"type": "string", "enum": ["3", "4", "11", "15"], "description": "3=first seen, 4=days active, 11=relevance, 15=impressions"},
                "sort_rule": {"type": "string", "enum": ["asc", "desc"]},
                "page": {"type": "integer", "description": "Page number (starts at 1)"},
                "page_size": {"type": "integer", "description": "Results per page (max 60)"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "trade_level1": {"type": "array", "items": {"type": "string"}, "description": "Industry category IDs"},
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "brave_search",
        "description": (
            "Web search via Brave for supplementary context — industry news, "
            "app backgrounds, market trends, competitor info. "
            "Use to enrich the report with external context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "count": {"type": "integer", "description": "Number of results (max 10)", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "summarize_query",
        "description": (
            "Summarize the collected results for one research query (map step). "
            "Call after gathering enough data for a query. "
            "Produces a structured summary stored in state."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query_id": {"type": "string", "description": "The query ID from the plan (e.g. 'q1')"},
                "focus_dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Analysis dimensions to focus on",
                },
            },
            "required": ["query_id"],
        },
    },
    {
        "name": "cross_analyze",
        "description": (
            "Cross-analyze all query summaries to find patterns across queries (reduce step). "
            "Call after all queries have been summarized."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Cross-cutting dimensions to analyze",
                },
            },
        },
    },
    {
        "name": "finish_research",
        "description": (
            "Signal that research is complete. Call this exactly once after cross_analyze. "
            "The final report will be generated automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ── Tool Dispatcher ───────────────────────────────────────────


async def execute_tool(
    name: str,
    tool_input: dict,
    state: ResearchState,
    llm_call: Any = None,  # async callable(messages, system, max_tokens) -> str
) -> str:
    """Dispatch tool call and return result as a string for the LLM."""
    try:
        if name == "search_creatives":
            return await _search_creatives(tool_input, state)
        elif name == "brave_search":
            return await _brave_search(tool_input, state)
        elif name == "summarize_query":
            return await _summarize_query(tool_input, state, llm_call)
        elif name == "cross_analyze":
            return await _cross_analyze(tool_input, state, llm_call)
        elif name == "finish_research":
            return _finish_research(state)
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {e}"})


# ── Tool Implementations ─────────────────────────────────────


async def _search_creatives(params: dict, state: ResearchState) -> str:
    """Call AdMapix API and accumulate results in state."""
    from admapix_mcp.api import call_admapix_search

    api_key = os.environ.get("ADMAPIX_API_KEY", "")
    base_url = os.environ.get("ADMAPIX_API_BASE", "https://api.admapix.com")

    result = await call_admapix_search(params, api_key=api_key, base_url=base_url)

    if "error" in result:
        return json.dumps({"error": result["error"], "retry": result.get("retry", False)})

    # Determine which query this belongs to (match by keyword)
    query_id = _match_query_id(params, state)
    if query_id not in state.query_results:
        desc = next(
            (q["description"] for q in state.plan.get("queries", []) if q["id"] == query_id),
            params.get("keyword", ""),
        )
        state.query_results[query_id] = QueryResult(
            query_id=query_id,
            description=desc,
            params=params,
        )

    qr = state.query_results[query_id]
    page = params.get("page", 1)
    qr.pages_fetched.append(page)
    qr.total_available = result.get("total", 0)
    qr.items.extend(result.get("items", []))
    if result.get("page_url"):
        qr.page_urls.append(result["page_url"])

    # Return a concise summary for the LLM (not raw data)
    items = result.get("items", [])
    summary_lines = [
        f"Total available: {result.get('total', 0)}",
        f"Fetched: {len(items)} items (page {page})",
        f"Accumulated: {len(qr.items)} items across {len(qr.pages_fetched)} pages",
    ]
    if items:
        top = sorted(items, key=lambda x: x.get("impression") or 0, reverse=True)[:3]
        summary_lines.append("Top 3 by impressions:")
        for t in top:
            summary_lines.append(
                f"  - {t.get('title', 'N/A')} | "
                f"imp: {t.get('impression', 'N/A')} | "
                f"days: {t.get('days_found', 'N/A')} | "
                f"copy: {(t.get('describe') or '')[:80]}"
            )
    return "\n".join(summary_lines)


async def _brave_search(params: dict, state: ResearchState) -> str:
    """Search the web via Brave Search API."""
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    if not api_key:
        return json.dumps({"error": "BRAVE_SEARCH_API_KEY not set"})

    query = params.get("query", "")
    count = min(params.get("count", 5), 10)

    try:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": count},
                headers={
                    "X-Subscription-Token": api_key,
                    "Accept": "application/json",
                },
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return json.dumps({"error": f"Brave search failed: {e}"})

    results = []
    for item in (data.get("web", {}).get("results") or [])[:count]:
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("description", ""),
            "url": item.get("url", ""),
        })

    state.brave_results.extend(results)

    # Return readable summary
    lines = [f"Web search results for '{query}' ({len(results)} results):"]
    for i, r in enumerate(results, 1):
        lines.append(f"  [{i}] {r['title']}")
        lines.append(f"      {r['snippet'][:150]}")
    return "\n".join(lines)


async def _summarize_query(
    params: dict, state: ResearchState, llm_call: Any
) -> str:
    """Map step: summarize one query's collected data."""
    query_id = params.get("query_id", "")
    qr = state.query_results.get(query_id)
    if not qr:
        return json.dumps({"error": f"No data for query '{query_id}'. Run search_creatives first."})

    if not qr.items:
        summary = f"Query '{query_id}' ({qr.description}): No results found."
        qr.summary = summary
        return summary

    focus = params.get("focus_dimensions", [])

    # Prepare data for LLM — cap items to avoid token overflow
    items_for_llm = qr.items[:40]
    messages = [
        {
            "role": "user",
            "content": (
                f"Query: {qr.description}\n"
                f"Parameters: {json.dumps(qr.params, ensure_ascii=False)}\n"
                f"Total available: {qr.total_available}\n"
                f"Items fetched: {len(qr.items)}\n"
                f"Focus dimensions: {', '.join(focus) if focus else 'general'}\n\n"
                f"Data (top {len(items_for_llm)} items):\n"
                f"{json.dumps(items_for_llm, ensure_ascii=False, indent=1, default=str)}"
            ),
        }
    ]

    summary = await llm_call(messages, system=SUMMARIZE_SYSTEM, max_tokens=2048)
    qr.summary = summary
    return f"Summary for {query_id} saved.\n\n{summary}"


async def _cross_analyze(
    params: dict, state: ResearchState, llm_call: Any
) -> str:
    """Reduce step: cross-analyze all query summaries."""
    summaries = state.all_summaries()
    if not summaries:
        return json.dumps({"error": "No query summaries available. Call summarize_query first."})

    dimensions = params.get("dimensions", [])

    # Build context
    parts = [f"User's original request: {state.user_request}\n"]
    for qid, summary in summaries.items():
        parts.append(f"--- Query {qid} Summary ---\n{summary}\n")

    if state.brave_results:
        parts.append("--- Supplementary Web Context ---")
        for br in state.brave_results[:10]:
            parts.append(f"  - {br['title']}: {br['snippet'][:120]}")

    if dimensions:
        parts.append(f"\nCross-analysis dimensions: {', '.join(dimensions)}")

    messages = [{"role": "user", "content": "\n".join(parts)}]
    analysis = await llm_call(messages, system=CROSS_ANALYZE_SYSTEM, max_tokens=3072)
    state.cross_analysis = analysis
    return f"Cross-analysis complete.\n\n{analysis}"


def _finish_research(state: ResearchState) -> str:
    """Mark research as complete."""
    state.status = "done"
    stats = {
        "queries_executed": len(state.query_results),
        "total_items": state.all_items_count(),
        "queries_summarized": len(state.all_summaries()),
        "has_cross_analysis": state.cross_analysis is not None,
        "brave_results": len(state.brave_results),
    }
    return f"Research complete. Stats: {json.dumps(stats)}"


# ── Helpers ───────────────────────────────────────────────────


def _match_query_id(params: dict, state: ResearchState) -> str:
    """Match search params to a query ID in the plan."""
    keyword = params.get("keyword", "").lower()
    for q in state.plan.get("queries", []):
        qp = q.get("params", {})
        if qp.get("keyword", "").lower() == keyword:
            return q["id"]
    # Fallback: match by closest keyword or assign new ID
    existing_ids = {q["id"] for q in state.plan.get("queries", [])}
    for qid in [f"q{i}" for i in range(1, 20)]:
        if qid not in existing_ids and qid not in state.query_results:
            return qid
    return f"q_extra_{len(state.query_results)}"
