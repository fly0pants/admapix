# AdMapix MCP

Raw AdMapix ad creative data for MCP-compatible agents.

AdMapix MCP lets an agent search competitor ad creatives and receive structured JSON data from the AdMapix API. Presentation and analysis workflows are out of scope.

## Features

- Search ad creatives by keyword, app name, advertiser, category, or ad copy
- Filter by creative type: image, video, playable ad
- Filter by country or region
- Filter by date range
- Sort by first seen, relevance, estimated impressions, or days active
- Return raw API records with media URLs and metrics

## Quick Start

Prerequisite: an AdMapix API key from your admin.

### Mac / Linux

```bash
git clone https://github.com/fly0pants/admapix.git
bash admapix/install.sh <YOUR_API_KEY>
```

### Windows PowerShell

```powershell
git clone https://github.com/fly0pants/admapix.git
powershell -ExecutionPolicy Bypass -File admapix\install.ps1 -ApiKey <YOUR_API_KEY>
```

The installer sets up:

| Step | What it does |
|---|---|
| 1 | Detects or installs Python 3.10+ |
| 2 | Detects or installs Node.js |
| 3 | Detects or installs mcporter |
| 4 | Installs the MCP server in `~/.admapix/` |
| 5 | Configures `~/.mcporter/mcporter.json` with `ADMAPIX_API_KEY` |
| 6 | Installs the OpenClaw skill |

## Usage

Ask your MCP-compatible agent for data:

| You say | Parameters produced |
|---|---|
| `search temu ads` | `keyword="temu"` |
| `video ads for puzzle games in the US` | `keyword="puzzle games"`, `creative_team=["010"]`, `country_ids=["US"]` |
| `Southeast Asia casual game ads last 7 days` | region and date filters |
| `sort by impressions` | `sort_field="15"`, `sort_rule="desc"` |
| `next page` | same filters, `page + 1` |

Successful calls return raw structured data:

```json
{
  "request": {
    "content_type": "creative",
    "keyword": "puzzle game",
    "page": 1,
    "page_size": 20,
    "sort_field": "3",
    "sort_rule": "desc"
  },
  "totalSize": 1234,
  "page": 1,
  "page_size": 20,
  "list": []
}
```

## MCP Tool

`search_creatives` parameters:

| Parameter | Type | Description |
|---|---|---|
| `keyword` | string | Search keyword |
| `creative_team` | string[] | Creative type codes, e.g. `["010"]` for video |
| `country_ids` | string[] | Country codes, e.g. `["US", "JP"]` |
| `start_date` | string | `YYYY-MM-DD` |
| `end_date` | string | `YYYY-MM-DD` |
| `page` | int | Page number, starting from 1 |
| `page_size` | int | Results per page, 1-60 |
| `sort_field` | string | `"3"` first seen, `"4"` days active, `"11"` relevance, `"15"` impressions |
| `sort_rule` | string | `"desc"` or `"asc"` |
| `trade_level1` | string[] | Industry category IDs |

## Manual Setup

```bash
python3 -m venv ~/.admapix/.venv
~/.admapix/.venv/bin/pip install mcp httpx pydantic
```

Configure `~/.mcporter/mcporter.json`:

```json
{
  "mcpServers": {
    "admapix": {
      "command": "~/.admapix/.venv/bin/python3 ~/.admapix/server.py",
      "env": {
        "ADMAPIX_API_KEY": "<YOUR_API_KEY>"
      }
    }
  }
}
```

Install the skill:

```bash
cp -r skill/ ~/.openclaw/skills/admapix/
```

## Development

```bash
python -m compileall src server.py
```

## License

MIT License.
