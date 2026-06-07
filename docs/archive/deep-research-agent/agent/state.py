"""Archived state management for the removed deep research prototype."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class QueryResult:
    query_id: str
    description: str
    params: dict
    pages_fetched: list[int] = field(default_factory=list)
    total_available: int = 0
    items: list[dict] = field(default_factory=list)
    page_urls: list[str] = field(default_factory=list)
    summary: str | None = None


@dataclass
class ResearchState:
    user_request: str
    plan: dict = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    query_results: dict[str, QueryResult] = field(default_factory=dict)
    brave_results: list[dict] = field(default_factory=list)
    cross_analysis: str | None = None
    final_report: str | None = None
    messages: list[dict] = field(default_factory=list)
    iteration: int = 0
    status: str = "planning"  # planning | confirmed | researching | done | error
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # ── Serialization ────────────────────────────────────────

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert messages containing Anthropic SDK objects to plain dicts
        d["messages"] = _serialize_messages(self.messages)
        return d

    def save(self, path: Path) -> None:
        """Atomically write checkpoint to disk."""
        self.updated_at = datetime.now().isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str))
        tmp.rename(path)

    @classmethod
    def load(cls, path: Path) -> ResearchState:
        raw = json.loads(path.read_text(encoding="utf-8"))
        # Reconstruct QueryResult objects
        qr = {}
        for k, v in raw.pop("query_results", {}).items():
            qr[k] = QueryResult(**v)
        state = cls(
            user_request=raw.pop("user_request"),
            plan=raw.pop("plan", {}),
            request_id=raw.pop("request_id"),
            query_results=qr,
            brave_results=raw.pop("brave_results", []),
            cross_analysis=raw.pop("cross_analysis", None),
            final_report=raw.pop("final_report", None),
            messages=raw.pop("messages", []),
            iteration=raw.pop("iteration", 0),
            status=raw.pop("status", "planning"),
            created_at=raw.pop("created_at", ""),
            updated_at=raw.pop("updated_at", ""),
        )
        return state

    def checkpoint_path(self, reports_dir: Path) -> Path:
        return reports_dir / ".checkpoints" / f"{self.request_id}.json"

    # ── Helpers ───────────────────────────────────────────────

    def all_items_count(self) -> int:
        return sum(len(qr.items) for qr in self.query_results.values())

    def all_summaries(self) -> dict[str, str]:
        return {qid: qr.summary for qid, qr in self.query_results.items() if qr.summary}

    def all_page_urls(self) -> list[str]:
        urls = []
        for qr in self.query_results.values():
            urls.extend(qr.page_urls)
        return urls


def _serialize_messages(messages: list) -> list[dict]:
    """Convert messages list to JSON-safe dicts, handling Anthropic SDK content blocks."""
    result = []
    for msg in messages:
        if isinstance(msg, dict):
            m = dict(msg)
            if "content" in m:
                m["content"] = _serialize_content(m["content"])
            result.append(m)
        elif hasattr(msg, "model_dump"):
            result.append(msg.model_dump())
        else:
            result.append(msg)
    return result


def _serialize_content(content: Any) -> Any:
    """Recursively serialize content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for item in content:
            if hasattr(item, "model_dump"):
                out.append(item.model_dump())
            elif isinstance(item, dict):
                out.append(item)
            else:
                out.append(item)
        return out
    if hasattr(content, "model_dump"):
        return content.model_dump()
    return content
