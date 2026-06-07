# AdMapix MCP

面向 MCP 智能体的 AdMapix 广告素材原始数据接口。

AdMapix MCP 让智能体通过自然语言搜索竞品广告素材，并返回 AdMapix API 的结构化 JSON 数据。展示层和分析工作流不属于这个 skill 的范围。

## 功能

- 按关键词、App 名称、广告主、品类或广告文案搜索广告素材
- 按素材类型筛选：图片、视频、试玩广告
- 按国家或地区筛选
- 按日期范围筛选
- 按首次发现、相关性、预估曝光、投放天数排序
- 返回包含媒体 URL 和指标的原始 API 记录

## 快速开始

前提：需要管理员分配的 AdMapix API Key。

### Mac / Linux

```bash
git clone https://github.com/fly0pants/admapix.git
bash admapix/install.sh <你的API_KEY>
```

### Windows PowerShell

```powershell
git clone https://github.com/fly0pants/admapix.git
powershell -ExecutionPolicy Bypass -File admapix\install.ps1 -ApiKey <你的API_KEY>
```

安装脚本会完成：

| 步骤 | 内容 |
|---|---|
| 1 | 检测或安装 Python 3.10+ |
| 2 | 检测或安装 Node.js |
| 3 | 检测或安装 mcporter |
| 4 | 安装 MCP server 到 `~/.admapix/` |
| 5 | 写入 `~/.mcporter/mcporter.json`，配置 `ADMAPIX_API_KEY` |
| 6 | 安装 OpenClaw skill |

## 使用方式

对支持 MCP 的智能体提出数据查询：

| 你说 | 生成的参数 |
|---|---|
| `搜 temu 广告` | `keyword="temu"` |
| `美国 puzzle game 视频广告` | `keyword="puzzle game"`, `creative_team=["010"]`, `country_ids=["US"]` |
| `最近 7 天东南亚休闲游戏素材` | 地区和日期筛选 |
| `按曝光量排序` | `sort_field="15"`, `sort_rule="desc"` |
| `下一页` | 保持筛选条件，`page + 1` |

成功调用返回原始结构化数据：

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

## MCP 工具

`search_creatives` 参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `keyword` | string | 搜索关键词 |
| `creative_team` | string[] | 素材类型代码，例如 `["010"]` 表示视频 |
| `country_ids` | string[] | 国家代码，例如 `["US", "JP"]` |
| `start_date` | string | `YYYY-MM-DD` |
| `end_date` | string | `YYYY-MM-DD` |
| `page` | int | 页码，从 1 开始 |
| `page_size` | int | 每页数量，1-60 |
| `sort_field` | string | `"3"` 首次发现，`"4"` 投放天数，`"11"` 相关性，`"15"` 曝光 |
| `sort_rule` | string | `"desc"` 或 `"asc"` |
| `trade_level1` | string[] | 行业分类 ID |

## 手动配置

```bash
python3 -m venv ~/.admapix/.venv
~/.admapix/.venv/bin/pip install mcp httpx pydantic
```

配置 `~/.mcporter/mcporter.json`：

```json
{
  "mcpServers": {
    "admapix": {
      "command": "~/.admapix/.venv/bin/python3 ~/.admapix/server.py",
      "env": {
        "ADMAPIX_API_KEY": "<你的API_KEY>"
      }
    }
  }
}
```

安装 skill：

```bash
cp -r skill/ ~/.openclaw/skills/admapix/
```

## 开发校验

```bash
python -m compileall src server.py
```

## 许可证

MIT License.
