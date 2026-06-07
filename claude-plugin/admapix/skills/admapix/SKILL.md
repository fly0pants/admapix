---
name: admapix
description: "Raw AdMapix ad creative data search. Use for 搜广告, 找素材, 广告视频, 创意素材, 竞品广告, ad creative, search ads, find creatives, competitor ads, ad spy. Returns structured JSON data only."
metadata: {"openclaw":{"primaryEnv":"ADMAPIX_API_KEY"}}
---

# AdMapix Raw Data Search

Use this skill to fetch raw competitor ad creative data from AdMapix.

Return structured data from the API. Presentation, message-send, autonomous research, summary, insight, recommendation, and dashboard workflows are out of scope.

## Data Source

Prefer the `admapix.search_creatives` MCP tool when it is available. If no MCP tool is available, call the API directly:

```bash
curl -s -X POST "https://api.admapix.com/api/data/search" \
  -H "X-API-Key: $ADMAPIX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content_type":"creative","keyword":"puzzle game","page":1,"page_size":20,"sort_field":"3","sort_rule":"desc"}'
```

Never print or expose the API key.

## Request Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| keyword | string | "" | Search keyword: app name, ad copy, advertiser, product, or category |
| creative_team | string[] | omit | Creative type codes, e.g. `["010"]` for video |
| country_ids | string[] | omit | Country codes, e.g. `["US","JP"]` |
| start_date | string | API default | Start date, `YYYY-MM-DD` |
| end_date | string | API default | End date, `YYYY-MM-DD` |
| sort_field | string | `"3"` | `"3"` first seen, `"4"` days active, `"11"` relevance, `"15"` impressions |
| sort_rule | string | `"desc"` | `"desc"` or `"asc"` |
| page | int | `1` | Page number, starting from 1 |
| page_size | int | `20` | Results per page, 1-60 |
| trade_level1 | string[] | omit | Industry category IDs |
| content_type | string | `"creative"` | Fixed request value |

Do not add presentation-generation or message-send fields to the request body.

## Parameter Parsing

Extract all parameters the user provides. Read `references/param-mappings.md` when natural-language mapping is needed for:

- creative type: video/image/playable, 视频/图片/试玩
- region or country: Southeast Asia, 美国, 日韩, Europe
- relative date ranges: last week, 最近一周, last month
- sorting: newest, most impressions, longest running
- page size and pagination

If the user did not provide a keyword or an equivalent searchable target, ask one concise question for the keyword. Other parameters can use defaults.

## Output Rules

Return raw structured JSON only. Keep the API field names when possible.

Required response shape after a successful call:

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

For errors, return structured JSON:

```json
{
  "error": {
    "code": "missing_api_key",
    "message": "Missing ADMAPIX_API_KEY environment variable",
    "retry": false
  }
}
```

Do not:

- hide the records behind external presentation links
- hide the records behind a link
- summarize the result list
- rank, analyze, or recommend strategy unless the user separately asks for analysis after receiving data
- run multi-step autonomous workflows or external search
- format the response as a landing page, card, table-first document, or dashboard

## Raw Response Fields

Each item in `list` may include upstream fields such as:

```json
{
  "id": "creative-id",
  "title": "App or advertiser name",
  "describe": "Ad copy",
  "imageUrl": ["https://..."],
  "videoUrl": ["https://..."],
  "playHtmlUrl": ["https://..."],
  "globalFirstTime": "2026-03-08 12:00:00",
  "globalLastTime": "2026-03-10 12:00:00",
  "findCntSum": 3,
  "impression": 123456,
  "showCnt": 5,
  "adSource": "network",
  "appList": [
    {"name": "App", "pkg": "com.example.app", "logo": "https://..."}
  ]
}
```
