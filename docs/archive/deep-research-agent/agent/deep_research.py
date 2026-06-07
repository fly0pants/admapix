"""Archived AdMapix Deep Research Agent prototype.

Flow:
  1. Plan: LLM generates structured research plan
  2. Confirm: User reviews and approves/edits plan
  3. ReAct Loop: LLM autonomously calls tools (search, web search, summarize, analyze)
  4. Report: Final report generated with streaming output
  5. Save: Markdown + optional PDF

Usage:
    python -m agent
    python -m agent "分析休闲游戏在东南亚的广告趋势"
    admapix-research "puzzle game US market analysis"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic
import httpx

from agent.prompts import PLANNER_SYSTEM, REACT_SYSTEM, REPORT_SYSTEM
from agent.state import ResearchState
from agent.tools import TOOL_SCHEMAS, execute_tool

# ── Config ────────────────────────────────────────────────────

MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-4-6")
REPORTS_DIR = Path(__file__).parent.parent / "reports"
MAX_ITERATIONS = 30


# ── Phase 1: Plan Generation ─────────────────────────────────


async def generate_plan(client: anthropic.AsyncAnthropic, user_request: str) -> dict:
    """Generate a structured research plan using Claude."""
    response = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=PLANNER_SYSTEM,
        messages=[{"role": "user", "content": user_request}],
    )
    text = response.content[0].text.strip()
    # Handle markdown code blocks
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


# ── Phase 2: User Confirmation ───────────────────────────────


def format_plan(plan: dict) -> str:
    """Format plan as readable text for user review."""
    sort_names = {"3": "first seen", "4": "days active", "11": "relevance", "15": "impressions"}
    lines = [
        f"\n{'='*60}",
        f"  {plan.get('title', 'Research Plan')}",
        f"{'='*60}",
        f"\n  Objective: {plan.get('objective', '-')}",
        f"\n  Queries ({len(plan.get('queries', []))}):",
    ]
    for q in plan.get("queries", []):
        p = q.get("params", {})
        lines.append(f"    [{q['id']}] {q['description']}")
        lines.append(f"         keyword: {p.get('keyword', '-')}")
        countries = p.get("country_ids", [])
        lines.append(f"         countries: {', '.join(countries) if countries else 'all'}")
        creative = p.get("creative_team", [])
        lines.append(f"         type: {', '.join(creative) if creative else 'all'}")
        sf = p.get("sort_field", "3")
        lines.append(f"         sort: {sort_names.get(sf, sf)} {p.get('sort_rule', 'desc')}")

    dims = plan.get("analysis_dimensions", [])
    if dims:
        lines.append(f"\n  Analysis Dimensions:")
        for dim in dims:
            lines.append(f"    - {dim}")

    lines.append(f"\n  Output: {plan.get('output_format', 'markdown')}")
    lines.append(f"  Est. API calls: {plan.get('estimated_api_calls', len(plan.get('queries', [])))}")
    lines.append(f"{'='*60}\n")
    return "\n".join(lines)


async def confirm_plan(client: anthropic.AsyncAnthropic, plan: dict) -> dict:
    """Interactive plan confirmation with edit support."""
    print(format_plan(plan))
    loop = asyncio.get_event_loop()

    while True:
        response = (await loop.run_in_executor(
            None, lambda: input("  Proceed? [Y]es / [E]dit / [N]o: ")
        )).strip().lower()

        if response in ("y", "yes", ""):
            return plan
        elif response in ("n", "no"):
            print("\n  Research cancelled.")
            sys.exit(0)
        elif response in ("e", "edit"):
            feedback = (await loop.run_in_executor(
                None, lambda: input("  What to change? > ")
            )).strip()
            if feedback:
                print("\n  Revising plan...")
                resp = await client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=PLANNER_SYSTEM,
                    messages=[
                        {"role": "user", "content": f"Original plan:\n{json.dumps(plan, indent=2)}"},
                        {"role": "assistant", "content": json.dumps(plan, indent=2)},
                        {"role": "user", "content": f"Please revise: {feedback}\n\nOutput revised JSON only."},
                    ],
                )
                text = resp.content[0].text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1]
                    text = text.rsplit("```", 1)[0]
                plan = json.loads(text)
                print(format_plan(plan))


# ── Phase 3: ReAct Agent Loop ────────────────────────────────


async def react_loop(client: anthropic.AsyncAnthropic, state: ResearchState) -> None:
    """Core agent loop — LLM decides which tool to call next."""
    checkpoint = state.checkpoint_path(REPORTS_DIR)

    # Initialize conversation if starting fresh
    if not state.messages:
        context = (
            f"Execute this research plan:\n\n"
            f"{json.dumps(state.plan, indent=2, ensure_ascii=False)}\n\n"
            f"Original user request: {state.user_request}\n\n"
            f"Today's date: {datetime.now().strftime('%Y-%m-%d')}"
        )
        state.messages = [{"role": "user", "content": context}]

    # LLM call helper for tools that need sub-LLM calls (summarize, cross_analyze)
    async def llm_call(messages: list[dict], system: str = "", max_tokens: int = 4096) -> str:
        resp = await client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return resp.content[0].text

    print()
    while state.iteration < MAX_ITERATIONS:
        # Call Claude with tools
        response = await client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=REACT_SYSTEM,
            messages=state.messages,
            tools=TOOL_SCHEMAS,
        )

        # Serialize assistant response to messages
        # Convert content blocks to serializable dicts
        assistant_content = []
        for block in response.content:
            if hasattr(block, "model_dump"):
                assistant_content.append(block.model_dump())
            elif isinstance(block, dict):
                assistant_content.append(block)

        state.messages.append({"role": "assistant", "content": assistant_content})

        # If the model just responded with text (no tool use), check stop reason
        if response.stop_reason == "end_turn":
            # Agent stopped without calling finish_research — extract any text
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    print(f"  Agent: {block.text[:200]}")
            break

        # Process tool calls
        if response.stop_reason == "tool_use":
            tool_results = []
            should_stop = False

            for block in response.content:
                if hasattr(block, "text") and block.text:
                    # Print agent's reasoning
                    print(f"  {_dim(block.text[:150])}")

                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    state.iteration += 1

                    print(f"  [{state.iteration}] {tool_name}({_brief(tool_input)})")

                    result = await execute_tool(
                        tool_name, tool_input, state, llm_call=llm_call
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                    # Print brief result
                    first_line = result.split("\n")[0][:100]
                    print(f"       → {first_line}")

                    if tool_name == "finish_research":
                        should_stop = True

            state.messages.append({"role": "user", "content": tool_results})
            state.save(checkpoint)

            if should_stop:
                return

    if state.iteration >= MAX_ITERATIONS:
        print(f"\n  Reached max iterations ({MAX_ITERATIONS}). Generating report with available data.")
        state.status = "done"


# ── Phase 4: Report Generation (Streaming) ───────────────────


async def generate_report(client: anthropic.AsyncAnthropic, state: ResearchState) -> str:
    """Generate final report with streaming output."""
    # Build report context from state
    parts = [f"Original request: {state.user_request}\n"]
    parts.append(f"Research plan:\n{json.dumps(state.plan, indent=2, ensure_ascii=False)}\n")

    summaries = state.all_summaries()
    if summaries:
        parts.append("=== Per-Query Summaries ===")
        for qid, summary in summaries.items():
            parts.append(f"\n--- {qid} ---\n{summary}")

    if state.cross_analysis:
        parts.append(f"\n=== Cross-Analysis ===\n{state.cross_analysis}")

    if state.brave_results:
        parts.append("\n=== Web Context ===")
        for br in state.brave_results[:10]:
            parts.append(f"  - {br.get('title', '')}: {br.get('snippet', '')[:120]}")

    page_urls = state.all_page_urls()
    if page_urls:
        parts.append("\n=== H5 Preview Pages ===")
        for url in page_urls:
            parts.append(f"  - {url}")

    messages = [{"role": "user", "content": "\n".join(parts)}]

    # Stream the report
    print(f"\n{'─'*60}")
    print("  Generating report...\n")

    full_text = []
    async with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        system=REPORT_SYSTEM,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text.append(text)

    print(f"\n{'─'*60}")

    report = "".join(full_text)
    state.final_report = report
    return report


# ── Report Saving ─────────────────────────────────────────────


def save_report(report: str, plan: dict) -> Path:
    """Save Markdown report to disk."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = plan.get("title", "report")[:40].replace(" ", "_").replace("/", "-")
    filepath = REPORTS_DIR / f"{timestamp}_{slug}.md"
    filepath.write_text(report, encoding="utf-8")
    return filepath


def convert_to_pdf(md_path: Path) -> Path | None:
    """Convert Markdown to PDF. Tries pandoc, then weasyprint."""
    import subprocess

    pdf_path = md_path.with_suffix(".pdf")

    # Try pandoc
    try:
        result = subprocess.run(
            [
                "pandoc", str(md_path), "-o", str(pdf_path),
                "--pdf-engine=xelatex",
                "-V", "CJKmainfont=PingFang SC",
                "-V", "geometry:margin=1in",
            ],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return pdf_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try weasyprint
    try:
        from weasyprint import HTML
        import markdown

        html_content = markdown.markdown(
            md_path.read_text(encoding="utf-8"),
            extensions=["tables", "fenced_code"],
        )
        styled = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ font-family: -apple-system, "PingFang SC", sans-serif; margin: 2cm; line-height: 1.6; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f5f5f5; }}
h1 {{ color: #1a1a2e; border-bottom: 2px solid #16213e; padding-bottom: 0.3em; }}
h2 {{ color: #16213e; }}
code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
</style></head><body>{html_content}</body></html>"""
        HTML(string=styled).write_pdf(str(pdf_path))
        return pdf_path
    except ImportError:
        pass

    return None


# ── Main Flow ─────────────────────────────────────────────────


async def run(user_request: str | None = None):
    """Main deep research flow."""
    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Validate environment
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    if not os.environ.get("ADMAPIX_API_KEY"):
        print("Error: ADMAPIX_API_KEY not set")
        sys.exit(1)

    client = anthropic.AsyncAnthropic()

    # Check for resumable checkpoint
    checkpoint_dir = REPORTS_DIR / ".checkpoints"
    state = None
    if checkpoint_dir.exists():
        checkpoints = sorted(checkpoint_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for cp in checkpoints[:1]:
            try:
                candidate = ResearchState.load(cp)
                if candidate.status not in ("done",):
                    loop = asyncio.get_event_loop()
                    answer = (await loop.run_in_executor(
                        None,
                        lambda: input(f"  Resume incomplete research '{candidate.plan.get('title', '?')}'? [Y/n]: ")
                    )).strip().lower()
                    if answer in ("y", "yes", ""):
                        state = candidate
                        print(f"  Resuming from iteration {state.iteration}...")
            except Exception:
                pass

    if state is None:
        # Get user request
        if not user_request:
            print("\n  AdMapix Deep Research Agent")
            print(f"  {'─'*36}")
            loop = asyncio.get_event_loop()
            user_request = (await loop.run_in_executor(
                None, lambda: input("  What would you like to research?\n  > ")
            )).strip()
            if not user_request:
                print("  No input.")
                return

        # Phase 1: Generate plan
        print("\n  Analyzing request...")
        plan = await generate_plan(client, user_request)

        # Phase 2: Confirm plan
        plan = await confirm_plan(client, plan)

        # Initialize state
        state = ResearchState(user_request=user_request, plan=plan, status="confirmed")

    # Phase 3: ReAct loop
    state.status = "researching"
    state.save(state.checkpoint_path(REPORTS_DIR))

    print("\n  Starting research...")
    await react_loop(client, state)

    # Phase 4: Generate report
    if state.all_items_count() == 0 and not state.all_summaries():
        print("\n  No data collected. Try broadening your search.")
        return

    report = await generate_report(client, state)

    # Save
    md_path = save_report(report, state.plan)
    print(f"\n  Report saved: {md_path}")

    output_format = state.plan.get("output_format", "markdown")
    if output_format == "pdf":
        print("  Converting to PDF...")
        pdf_path = convert_to_pdf(md_path)
        if pdf_path:
            print(f"  PDF saved: {pdf_path}")
        else:
            print("  PDF conversion unavailable. Install: brew install pandoc basictex")

    # Final checkpoint
    state.status = "done"
    state.save(state.checkpoint_path(REPORTS_DIR))

    # Summary
    page_urls = state.all_page_urls()
    print(f"\n{'='*60}")
    print(f"  Research Complete: {state.plan.get('title', '')}")
    print(f"{'='*60}")
    print(f"  Iterations: {state.iteration}")
    print(f"  Creatives collected: {state.all_items_count()}")
    print(f"  Web context: {len(state.brave_results)} results")
    print(f"  Report: {md_path}")
    if page_urls:
        print(f"\n  H5 Previews:")
        for url in page_urls:
            print(f"    {url}")
    print()


# ── Helpers ───────────────────────────────────────────────────


def _brief(d: dict) -> str:
    """Compact dict representation for logging."""
    parts = []
    for k, v in d.items():
        if isinstance(v, str) and len(v) > 30:
            v = v[:27] + "..."
        parts.append(f"{k}={v}")
    return ", ".join(parts)[:80]


def _dim(text: str) -> str:
    """Dim text for console output."""
    return f"\033[90m{text}\033[0m"


def main():
    """CLI entry point."""
    request = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    asyncio.run(run(request))


if __name__ == "__main__":
    main()
