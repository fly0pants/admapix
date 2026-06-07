"""Launch the installed AdMapix MCP server without exposing secrets in argv."""

from __future__ import annotations

import json
import os
import runpy
from pathlib import Path


def main() -> None:
    if not os.environ.get("ADMAPIX_API_KEY"):
        key = _read_key_from_mcporter()
        if key:
            os.environ["ADMAPIX_API_KEY"] = key

    server_path = Path.home() / ".admapix" / "server.py"
    runpy.run_path(str(server_path), run_name="__main__")


def _read_key_from_mcporter() -> str:
    path = Path.home() / ".mcporter" / "mcporter.json"
    if not path.exists():
        return ""
    try:
        config = json.loads(path.read_text())
    except Exception:
        return ""

    env = config.get("mcpServers", {}).get("admapix", {}).get("env", {})
    return env.get("ADMAPIX_API_KEY") or env.get("API_KEY") or ""


if __name__ == "__main__":
    main()
