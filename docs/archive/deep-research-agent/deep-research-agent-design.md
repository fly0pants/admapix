# Archived AdMapix Deep Research Agent — 完整设计方案

## 目标

构建一个面向公司决策者的广告情报 Deep Research Agent，支持：

- 自主研究（ReAct 循环，而非固定管线）
- 多数据源（AdMapix + Brave Search）
- Map-Reduce 报告生成
- 历史对比与趋势追踪
- 多 Agent 协作（Planner / Researcher / Analyst / Writer / Critic）
- 报告模板 + 固定 KPI 体系
- 自我审查（Critic Agent）
- 定时调度 + 多渠道分发
- 用户反馈闭环

---

## 文件结构

```
agent/
├── __init__.py
├── __main__.py             # python -m agent 入口
├── config.py               # 报告模板 + KPI 定义 + 决策者 profile
├── prompts.py              # 所有角色的 system prompt
├── state.py                # 研究状态 + 磁盘 checkpoint
├── tools.py                # 工具 schema + 实现（search, brave, history, anomaly）
├── deep_research.py        # 主编排器：多 Agent + ReAct 循环 + critic 审查
├── history.py              # SQLite 历史存储 + 趋势计算 + 异常检测
├── critic.py               # 报告自审 + 评分 + 自动重写
├── delivery.py             # 飞书 / 邮件 / Notion 分发
├── feedback.py             # 用户反馈存储 + plan 影响
├── scheduler.py            # 定时任务 CLI 入口
└── schedules.yaml          # 定时任务配置
```

---

## 整体流程

```
async def run():
    ┌─────────────────────────────────────────────┐
    │ Phase 1: Planning                           │
    │   load_feedback() → 注入 planner prompt     │
    │   load_history() → 注入上期 KPI             │
    │   Planner Agent → 生成 plan                 │
    │   User confirm (定时任务跳过确认)            │
    └─────────────┬───────────────────────────────┘
                  ▼
    ┌─────────────────────────────────────────────┐
    │ Phase 2: Research (ReAct Loop)              │
    │   Researcher Agent: search_creatives,       │
    │     brave_search, query_history             │
    │   ↓ 每个 query 数据收集完毕后              │
    │   Analyst Agent: summarize_query            │
    │     (带历史对比 + 异常检测)                 │
    │   ↓ 全部 query 总结完毕后                  │
    │   Analyst Agent: cross_analyze              │
    │   → finish_research                         │
    └─────────────┬───────────────────────────────┘
                  ▼
    ┌─────────────────────────────────────────────┐
    │ Phase 3: Report Writing                     │
    │   Writer Agent: 按 template + profile 生成  │
    │   流式输出到终端                            │
    └─────────────┬───────────────────────────────┘
                  ▼
    ┌─────────────────────────────────────────────┐
    │ Phase 4: Quality Review                     │
    │   Critic Agent: 5 维度打分                  │
    │   avg_score < 3.5 → Writer 重写问题 section │
    │   最多重试 1 次                             │
    └─────────────┬───────────────────────────────┘
                  ▼
    ┌─────────────────────────────────────────────┐
    │ Phase 5: Save + Deliver                     │
    │   save_report() → MD + PDF                  │
    │   save_snapshot() → 历史 DB                 │
    │   deliver() → 飞书 / 邮件                   │
    │   collect_feedback() → (交互模式)           │
    └─────────────────────────────────────────────┘
```

---

## 多 Agent 角色设计

不引入框架，用**角色化 LLM 调用**实现。同一个 asyncio 事件循环中的不同 system prompt + 工具子集，通过 `ResearchState` 共享数据。

| Agent 角色 | System Prompt | 可用工具 | 职责 |
|-----------|---------------|----------|------|
| Planner | `PLANNER_SYSTEM` + feedback 注入 | 无（纯文本生成） | 分析需求，生成研究计划 |
| Researcher | `REACT_SYSTEM` | search_creatives, brave_search, query_history | ReAct 循环，自主采集数据 |
| Analyst | `SUMMARIZE_SYSTEM` / `CROSS_ANALYZE_SYSTEM` | detect_anomaly | 单 query 总结 + 跨 query 交叉分析 |
| Writer | `REPORT_SYSTEM` + template + profile tone | 无（纯文本生成） | 按模板生成最终报告 |
| Critic | `CRITIC_SYSTEM` + 原始数据 | 无（JSON 输出） | 5 维度打分，标记问题 |

---

## 模块详细设计

### 1. `config.py` — 报告模板 + KPI + 决策者 Profile

#### KPI 注册表

```python
STANDARD_KPIS = [
    {"name": "total_creatives",        "label": "素材总量",     "calc": "count(items)"},
    {"name": "new_creatives",          "label": "新增素材",     "calc": "diff_with_previous"},
    {"name": "video_ratio",            "label": "视频占比",     "calc": "video_count / total"},
    {"name": "avg_days_active",        "label": "平均投放天数", "calc": "mean(days_found)"},
    {"name": "top_advertiser",         "label": "头部广告主",   "calc": "mode(apps.name)"},
    {"name": "impression_concentration","label": "曝光集中度",  "calc": "top5_impression / total_impression"},
]
```

#### 决策者 Profile

```python
PROFILES = {
    "cmo": {
        "name": "CMO / 创意负责人",
        "focus_dimensions": ["creative_trend", "copy_analysis", "creative_type_distribution"],
        "kpis": ["total_creatives", "new_creatives", "video_ratio", "top_creative_themes"],
        "tone": "strategic, high-level, focus on creative innovation and market positioning",
        "language": "zh",
    },
    "media_buyer": {
        "name": "投放负责人",
        "focus_dimensions": ["competitor_activity", "impression_trend", "market_heat"],
        "kpis": ["total_creatives", "avg_days_active", "impression_concentration", "new_advertisers"],
        "tone": "data-driven, tactical, focus on competitive moves and budget allocation signals",
        "language": "zh",
    },
    "default": {
        "name": "General",
        "focus_dimensions": ["all"],
        "kpis": "all",
        "tone": "balanced, professional",
        "language": "auto",
    },
}
```

#### 报告模板

```python
REPORT_TEMPLATE = {
    "sections": [
        {"id": "kpi_dashboard",     "title": "核心指标看板",   "required": True},
        {"id": "executive_summary", "title": "Executive Summary", "required": True},
        {"id": "trend_comparison",  "title": "环比趋势",       "required": True,  "needs_history": True},
        {"id": "anomaly_alerts",    "title": "异常预警",       "required": False, "needs_history": True},
        {"id": "detailed_findings", "title": "详细发现",       "required": True},
        {"id": "top_performers",    "title": "Top 素材",       "required": True},
        {"id": "cross_insights",    "title": "跨维度洞察",     "required": True},
        {"id": "recommendations",   "title": "策略建议",       "required": True},
        {"id": "appendix",          "title": "附录",           "required": False},
    ]
}
```

#### 集成点

- Plan 生成时注入 profile 的 `focus_dimensions`
- Report 生成时按 template section 顺序 + profile 的 `tone`
- CLI 新增 `--profile cmo` 参数

---

### 2. `history.py` — 历史对比与趋势追踪

#### 存储方案

SQLite，零外部依赖，存储在 `reports/history.db`。

#### 表设计

```sql
-- 每期报告的结构化快照
CREATE TABLE reports (
    id              TEXT PRIMARY KEY,       -- request_id
    created_at      DATETIME NOT NULL,
    plan_title      TEXT,
    plan_json       TEXT,                   -- 完整 plan JSON
    metrics_json    TEXT,                   -- 提取的 KPI 指标
    report_md       TEXT                    -- 完整报告正文
);

-- 每期报告的关键指标（扁平化，方便查询对比）
CREATE TABLE report_metrics (
    report_id       TEXT NOT NULL,
    metric_name     TEXT NOT NULL,          -- e.g. "total_creatives", "video_ratio"
    metric_value    REAL,
    dimension       TEXT DEFAULT '',        -- e.g. "US", "puzzle_game"
    PRIMARY KEY (report_id, metric_name, dimension),
    FOREIGN KEY (report_id) REFERENCES reports(id)
);

-- 每次搜索的素材快照（用于发现"新素材"和"消失的素材"）
CREATE TABLE creative_snapshots (
    report_id       TEXT NOT NULL,
    creative_id     TEXT NOT NULL,
    title           TEXT,
    impression      INTEGER,
    days_found      INTEGER,
    first_seen      TEXT,
    PRIMARY KEY (report_id, creative_id),
    FOREIGN KEY (report_id) REFERENCES reports(id)
);
```

#### 核心函数

```python
def save_snapshot(state: ResearchState) -> None:
    """报告完成后，提取 KPI 存入 DB"""
    # 从 state.query_results 中计算所有 STANDARD_KPIS
    # 将 items 存入 creative_snapshots
    # 将 metrics 存入 report_metrics

def get_previous(plan_title: str, n: int = 1) -> list[dict]:
    """按 plan_title 模糊匹配最近 n 期报告的指标"""
    # SELECT * FROM reports WHERE plan_title LIKE ? ORDER BY created_at DESC LIMIT n

def calc_trend(metric_name: str, dimension: str = "", periods: int = 4) -> dict:
    """计算某指标的趋势线"""
    # 查询最近 N 期的 metric_value
    # 计算简单移动平均 + 变化方向
    # 返回 { "values": [...], "trend": "up|down|stable", "avg_change": 0.12 }

def detect_anomalies(current_metrics: dict, previous_metrics: dict, threshold: float = 0.3) -> list[dict]:
    """对比当期 vs 上期，标记异常变化"""
    anomalies = []
    for key in current_metrics:
        if key in previous_metrics and previous_metrics[key] > 0:
            change = (current_metrics[key] - previous_metrics[key]) / previous_metrics[key]
            if abs(change) > threshold:
                anomalies.append({
                    "metric": key,
                    "change_pct": round(change * 100, 1),
                    "from": previous_metrics[key],
                    "to": current_metrics[key],
                    "direction": "up" if change > 0 else "down",
                })
    return sorted(anomalies, key=lambda x: abs(x["change_pct"]), reverse=True)

def find_new_creatives(current_ids: set[str], previous_report_id: str) -> list[str]:
    """找出上期没有的新素材 ID"""
    # SELECT creative_id FROM creative_snapshots WHERE report_id = ?
    # return current_ids - previous_ids
```

#### Agent 集成

在 `tools.py` 新增两个工具供 ReAct 循环使用：

```python
{
    "name": "query_history",
    "description": "查询历史报告指标，用于环比分析",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_title": {"type": "string"},
            "periods": {"type": "integer", "default": 3}
        },
        "required": ["plan_title"]
    }
}

{
    "name": "detect_anomaly",
    "description": "对比当前数据与历史，检测异常变化",
    "input_schema": {
        "type": "object",
        "properties": {
            "current_metrics": {"type": "object"},
            "threshold": {"type": "number", "default": 0.3}
        },
        "required": ["current_metrics"]
    }
}
```

---

### 3. `critic.py` — 报告自我审查

#### 审查维度（5 项，每项 1-5 分）

| 维度 | 检查内容 |
|------|----------|
| `data_accuracy` | 报告中引用的数字是否能在原始数据中找到对应 |
| `conclusion_support` | 每个结论/断言是否有 ≥1 个数据点支撑 |
| `completeness` | 是否覆盖了 plan 中所有 analysis_dimensions |
| `actionability` | 建议是否具体可执行（"增加投放"不合格，"在 TH 市场增加视频素材"合格） |
| `readability` | 是否适合目标读者（决策者不需要看 API 参数和技术细节） |

#### Critic System Prompt

```
你是报告质量审查员。审查一份广告情报分析报告的质量。

审查规则：
1. 数据准确性：对比报告中的具体数字与提供的原始数据，标记不一致之处
2. 结论支撑：每个断言都需要引用具体数据，标记"无中生有"的结论
3. 完整性：检查是否覆盖了研究计划中列出的所有分析维度
4. 可操作性："建议增加投放"不合格，"建议在 TH 市场增加视频类素材投放，参考竞品 X 的 Y 策略"合格
5. 可读性：决策者不需要看 API 参数、技术细节、JSON 片段

输出严格的 JSON 格式:
{
    "scores": {
        "data_accuracy": 4,
        "conclusion_support": 3,
        "completeness": 5,
        "actionability": 2,
        "readability": 4
    },
    "avg_score": 3.6,
    "pass": true,
    "issues": [
        {"section": "recommendations", "severity": "high", "description": "建议过于笼统"},
        {"section": "top_performers", "severity": "medium", "description": "表格缺少曝光量数据"}
    ],
    "suggestions": [
        "recommendations section 应该针对每个市场给出具体的素材类型建议",
        "top_performers 表格应增加 impression 列"
    ]
}
```

#### 审查流程

```python
async def review_report(
    report: str,
    state: ResearchState,
    profile: dict,
    client: anthropic.AsyncAnthropic,
) -> dict:
    """
    返回 { scores, issues, suggestions, pass }
    """
    # 构建审查上下文：报告全文 + 原始数据摘要 + profile 信息
    # 调用 LLM with CRITIC_SYSTEM
    # 解析 JSON 输出
    # 返回审查结果

async def review_and_fix(
    report: str,
    state: ResearchState,
    profile: dict,
    client: anthropic.AsyncAnthropic,
    max_retries: int = 1,
) -> str:
    """审查 + 自动修复"""
    review = await review_report(report, state, profile, client)

    if review["pass"]:
        print(f"  Critic: PASS (avg score: {review['avg_score']})")
        return report

    print(f"  Critic: FAIL (avg score: {review['avg_score']})")
    for issue in review["issues"]:
        print(f"    [{issue['severity']}] {issue['section']}: {issue['description']}")

    if max_retries > 0:
        # 将 issues 反馈给 Writer Agent 重写
        print("  Rewriting problematic sections...")
        revised = await rewrite_with_feedback(report, review, state, profile, client)
        # 递归审查修改后的版本（retries - 1）
        return await review_and_fix(revised, state, profile, client, max_retries - 1)

    # 超过重试次数，在报告末尾附注质量标记
    report += f"\n\n---\n*Quality score: {review['avg_score']}/5.0 — {len(review['issues'])} issues noted*\n"
    return report
```

#### 集成点

在 `deep_research.py` Phase 3（报告生成）与 Phase 5（保存）之间插入：

```python
# Phase 4: Critic Review
report = await review_and_fix(report, state, profile, client)
```

---

### 4. `delivery.py` — 多渠道分发

#### 支持的渠道

```python
class DeliveryChannel(Enum):
    FEISHU = "feishu"       # 飞书 webhook + 富文本卡片
    EMAIL = "email"         # SMTP 邮件 + PDF 附件
    NOTION = "notion"       # Notion 页面创建
    LOCAL = "local"         # 仅本地保存（默认）
```

#### 飞书分发

```python
async def deliver_feishu(
    report_path: Path,
    summary: str,
    kpi_dashboard: dict,
    webhook_url: str,
) -> bool:
    """
    发送飞书 webhook 消息：
    1. Interactive Card 格式
    2. 包含 KPI 看板（column_set）
    3. 摘要文本（markdown）
    4. PDF 下载链接（如果有）
    """
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"content": f"📊 广告情报报告", "tag": "plain_text"},
                "template": "blue",
            },
            "elements": [
                # KPI 指标用 column_set 展示
                {
                    "tag": "column_set",
                    "columns": [
                        {"tag": "column", "width": "weighted", "weight": 1, "elements": [
                            {"tag": "markdown", "content": f"**素材总量**\n{kpi_dashboard.get('total_creatives', '-')}"}
                        ]},
                        {"tag": "column", "width": "weighted", "weight": 1, "elements": [
                            {"tag": "markdown", "content": f"**新增素材**\n{kpi_dashboard.get('new_creatives', '-')}"}
                        ]},
                        {"tag": "column", "width": "weighted", "weight": 1, "elements": [
                            {"tag": "markdown", "content": f"**视频占比**\n{kpi_dashboard.get('video_ratio', '-')}"}
                        ]},
                    ],
                },
                {"tag": "hr"},
                {"tag": "markdown", "content": summary},
            ],
        },
    }
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.post(webhook_url, json=card)
        return r.status_code == 200
```

#### 邮件分发

```python
async def deliver_email(
    report_path: Path,
    summary: str,
    config: dict,       # smtp_host, smtp_port, username, password, to, from
) -> bool:
    """
    SMTP 发送：
    - 正文：Executive Summary (HTML 格式)
    - 附件：PDF 报告（如有），否则 Markdown
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication

    msg = MIMEMultipart()
    msg["Subject"] = f"广告情报报告 - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = config["from"]
    msg["To"] = ", ".join(config["to"])
    msg.attach(MIMEText(summary, "html", "utf-8"))

    # 附件
    pdf_path = report_path.with_suffix(".pdf")
    attach_path = pdf_path if pdf_path.exists() else report_path
    with open(attach_path, "rb") as f:
        att = MIMEApplication(f.read(), Name=attach_path.name)
        att["Content-Disposition"] = f'attachment; filename="{attach_path.name}"'
        msg.attach(att)

    # 发送（用 run_in_executor 避免阻塞）
    # smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"])
    # ...
```

#### 统一分发入口

```python
async def deliver(
    report_path: Path,
    summary: str,
    kpi_dashboard: dict,
    channels: list[str],
) -> dict[str, bool]:
    """按配置的渠道逐个分发，返回每个渠道的成功状态"""
    results = {}
    for ch in channels:
        if ch == "feishu":
            url = os.environ.get("FEISHU_WEBHOOK_URL")
            if url:
                results["feishu"] = await deliver_feishu(report_path, summary, kpi_dashboard, url)
        elif ch == "email":
            config = {
                "smtp_host": os.environ.get("EMAIL_SMTP_HOST"),
                "smtp_port": int(os.environ.get("EMAIL_SMTP_PORT", "465")),
                "username": os.environ.get("EMAIL_USERNAME"),
                "password": os.environ.get("EMAIL_PASSWORD"),
                "from": os.environ.get("EMAIL_FROM"),
                "to": os.environ.get("EMAIL_TO", "").split(","),
            }
            if config["smtp_host"]:
                results["email"] = await deliver_email(report_path, summary, config)
        elif ch == "local":
            results["local"] = True
    return results
```

#### 环境变量配置

```env
# .env
DELIVERY_CHANNELS=feishu,email

# 飞书
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx

# 邮件
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=465
EMAIL_USERNAME=reports@company.com
EMAIL_PASSWORD=xxx
EMAIL_FROM=reports@company.com
EMAIL_TO=cmo@company.com,media@company.com
```

---

### 5. `feedback.py` — 用户反馈闭环

#### 存储

复用 `history.db`（同一个 SQLite）：

```sql
CREATE TABLE feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    report_id       TEXT,                   -- 关联的报告（可选）
    feedback_type   TEXT NOT NULL,           -- "add_dimension" | "remove_dimension" | "adjust_focus" | "style" | "general"
    content         TEXT NOT NULL,           -- 原始反馈文本
    extracted_rules TEXT,                   -- LLM 提取的结构化规则 JSON
    active          BOOLEAN DEFAULT 1,      -- 是否仍然有效
    applied_count   INTEGER DEFAULT 0       -- 被应用了多少次
);
```

#### 反馈处理流程

```python
async def process_feedback(raw_text: str, report_id: str | None, client) -> dict:
    """
    1. 用 LLM 将自然语言反馈提取为结构化规则
    2. 存入 DB
    """
    messages = [{
        "role": "user",
        "content": f"用户反馈: {raw_text}\n\n提取结构化规则，输出 JSON: "
                   f'{{"type": "add_dimension|remove_dimension|adjust_focus|style|general", '
                   f'"rule": "具体规则", "dimension": "相关维度", "market": "相关市场"}}'
    }]
    extracted = await llm_call(messages, system="你是反馈解析器。从用户反馈中提取结构化规则。输出 JSON。")
    rule = json.loads(extracted)

    # 存入 DB
    save_feedback(report_id, raw_text, rule)
    return rule

def load_active_feedback(limit: int = 20) -> list[dict]:
    """加载最近的 active 反馈规则"""
    # SELECT * FROM feedback WHERE active = 1 ORDER BY created_at DESC LIMIT ?
    # 返回 extracted_rules 列表

def format_feedback_for_prompt(feedback_list: list[dict]) -> str:
    """将反馈列表格式化为 prompt 注入文本"""
    if not feedback_list:
        return ""
    lines = ["用户历史反馈（请在规划和分析时考虑）："]
    for fb in feedback_list:
        rules = json.loads(fb["extracted_rules"]) if fb["extracted_rules"] else {}
        lines.append(f"  - {rules.get('rule', fb['content'])}")
    return "\n".join(lines)
```

#### 反馈收集方式

```python
# 方式 1: CLI 交互模式（报告生成后）
async def collect_feedback_interactive(report_id: str, client):
    feedback = input("  Any feedback on this report? (Enter to skip) > ").strip()
    if feedback:
        rule = await process_feedback(feedback, report_id, client)
        print(f"  Noted: {rule.get('rule', 'saved')}")

# 方式 2: 独立 CLI 命令
# admapix-feedback add "多关注东南亚 playable ads"
# admapix-feedback list
# admapix-feedback deactivate 3

# 方式 3: 文件导入
# admapix-feedback import feedback.txt
```

#### Plan 注入集成

```python
# deep_research.py 中 Phase 1 修改：
async def generate_plan(client, user_request, profile):
    feedback = load_active_feedback()
    feedback_text = format_feedback_for_prompt(feedback)

    system = PLANNER_SYSTEM
    if feedback_text:
        system += f"\n\n{feedback_text}"
    if profile:
        system += f"\n\nTarget audience: {profile['name']}"
        system += f"\nFocus dimensions: {', '.join(profile['focus_dimensions'])}"

    # ... 正常生成 plan
```

---

### 6. `scheduler.py` — 定时调度

#### 设计原则

不做 daemon 进程，提供 CLI 命令 + 系统级调度（cron / launchd）集成。

#### 定时任务配置 `schedules.yaml`

```yaml
schedules:
  - name: "weekly_casual_game_sea"
    cron: "0 9 * * 1"                # 每周一上午 9 点
    request: "分析过去7天东南亚休闲游戏广告趋势"
    profile: "media_buyer"
    output_format: "pdf"
    delivery:
      - "feishu"
      - "email"

  - name: "daily_competitor_monitor"
    cron: "0 8 * * *"                # 每天上午 8 点
    request: "监控竞品 XXX 最近24小时的新增广告素材"
    profile: "cmo"
    output_format: "markdown"
    delivery:
      - "feishu"

  - name: "monthly_market_overview"
    cron: "0 10 1 * *"              # 每月 1 号上午 10 点
    request: "生成过去30天全球手游广告市场全景报告"
    profile: "default"
    output_format: "pdf"
    delivery:
      - "feishu"
      - "email"
      - "notion"
```

#### CLI 命令

```bash
# 安装定时任务到系统 cron
admapix-schedule setup
# 输出:
#   Added to crontab:
#   0 9 * * 1 cd /path && admapix-schedule run --name weekly_casual_game_sea >> logs/scheduler.log 2>&1
#   0 8 * * * cd /path && admapix-schedule run --name daily_competitor_monitor >> logs/scheduler.log 2>&1

# 手动触发一个定时任务
admapix-schedule run --name weekly_casual_game_sea

# 查看所有定时任务
admapix-schedule list
# 输出:
#   NAME                        CRON          PROFILE       NEXT RUN
#   weekly_casual_game_sea      0 9 * * 1     media_buyer   2026-03-23 09:00
#   daily_competitor_monitor    0 8 * * *     cmo           2026-03-18 08:00

# 查看执行历史
admapix-schedule history
# 输出:
#   NAME                        RAN AT              STATUS    DURATION    REPORT
#   daily_competitor_monitor    2026-03-17 08:00    success   3m 42s      reports/20260317_xxx.md
#   daily_competitor_monitor    2026-03-16 08:00    success   4m 11s      reports/20260316_xxx.md
```

#### `run` 命令实现

```python
async def run_scheduled(name: str):
    """执行一个定时任务（cron 调用此函数）"""
    config = load_schedule(name)  # 从 schedules.yaml 读取

    profile = PROFILES.get(config["profile"], PROFILES["default"])

    # 调用 deep_research.run()，关键参数:
    await deep_research.run(
        user_request=config["request"],
        profile=profile,
        output_format=config.get("output_format", "markdown"),
        auto_confirm=True,          # 跳过用户确认（无交互）
        delivery_channels=config.get("delivery", ["local"]),
    )

    # 记录执行日志
    log_execution(name, status="success", duration=elapsed)
```

#### macOS LaunchAgent（可选）

```python
def setup_launchd(schedule):
    """生成 ~/Library/LaunchAgents/com.admapix.{name}.plist"""
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <plist version="1.0"><dict>
        <key>Label</key><string>com.admapix.{schedule['name']}</string>
        <key>ProgramArguments</key><array>
            <string>{sys.executable}</string>
            <string>-m</string>
            <string>agent.scheduler</string>
            <string>run</string>
            <string>--name</string>
            <string>{schedule['name']}</string>
        </array>
        <key>StartCalendarInterval</key><dict>
            <!-- 从 cron 表达式解析 -->
        </dict>
        <key>WorkingDirectory</key><string>{PROJECT_DIR}</string>
        <key>StandardOutPath</key><string>{PROJECT_DIR}/logs/{schedule['name']}.log</string>
    </dict></plist>"""
```

---

### 7. `deep_research.py` 改造要点

#### `run()` 函数签名变更

```python
async def run(
    user_request: str | None = None,
    profile: dict | None = None,        # 决策者 profile
    output_format: str = "markdown",     # "markdown" | "pdf"
    auto_confirm: bool = False,          # 定时任务跳过确认
    delivery_channels: list[str] | None = None,  # 分发渠道
):
```

#### ReAct 循环扩展

工具列表新增 `query_history` 和 `detect_anomaly`，Agent 可自主决定是否使用历史对比。

#### Phase 4 插入 Critic

```python
# Phase 3: Writer Agent 生成报告 (streaming)
report = await generate_report(client, state, profile)

# Phase 4: Critic Agent 审查
from agent.critic import review_and_fix
report = await review_and_fix(report, state, profile, client)

# Phase 5: Save + History + Deliver
md_path = save_report(report, state.plan)
save_snapshot(state)  # 存入历史 DB

if delivery_channels:
    from agent.delivery import deliver
    results = await deliver(md_path, executive_summary, kpi_dashboard, delivery_channels)

if not auto_confirm:
    from agent.feedback import collect_feedback_interactive
    await collect_feedback_interactive(state.request_id, client)
```

---

### 8. `prompts.py` 新增 Prompt

需要新增的 prompt 常量：

| 常量 | 用途 |
|------|------|
| `CRITIC_SYSTEM` | Critic Agent 审查 prompt（见上文 critic.py 部分） |
| `FEEDBACK_EXTRACTOR_SYSTEM` | 从自然语言反馈中提取结构化规则 |

需要修改的 prompt 常量：

| 常量 | 修改内容 |
|------|----------|
| `PLANNER_SYSTEM` | 尾部追加 feedback 注入占位 + profile 信息 |
| `REACT_SYSTEM` | 工具列表追加 query_history / detect_anomaly 说明 |
| `REPORT_SYSTEM` | 追加模板 section 顺序要求 + KPI 看板格式要求 + profile tone |
| `SUMMARIZE_SYSTEM` | 追加"与上期对比"指引 |

---

### 9. `state.py` 扩展

```python
@dataclass
class ResearchState:
    # ... 现有字段 ...

    # 新增
    profile_name: str = "default"
    historical_metrics: dict | None = None      # 上期指标（由 query_history 填充）
    anomalies: list[dict] = field(default_factory=list)  # 检测到的异常
    critic_review: dict | None = None           # Critic 审查结果
    delivery_results: dict | None = None        # 分发结果
```

---

## pyproject.toml 变更

```toml
[project.optional-dependencies]
agent = [
    "anthropic>=0.40",
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "pyyaml>=6.0",
]
pdf = [
    "weasyprint>=60.0",
    "markdown>=3.5",
]

[project.scripts]
admapix-mcp = "admapix_mcp.__main__:main"
admapix-research = "agent.deep_research:main"
admapix-schedule = "agent.scheduler:main"
admapix-feedback = "agent.feedback:cli_main"
```

---

## 环境变量总览

```env
# 必需
ANTHROPIC_API_KEY=<your_anthropic_api_key>
ADMAPIX_API_KEY=<your_admapix_api_key>

# Agent 配置
AGENT_MODEL=claude-sonnet-4-6          # 默认模型
BRAVE_SEARCH_API_KEY=<your_brave_search_api_key>

# 分发渠道
DELIVERY_CHANNELS=local                 # local,feishu,email
FEISHU_WEBHOOK_URL=                     # 飞书 webhook
EMAIL_SMTP_HOST=                        # SMTP 服务器
EMAIL_SMTP_PORT=465
EMAIL_USERNAME=
EMAIL_PASSWORD=
EMAIL_FROM=
EMAIL_TO=                               # 逗号分隔多个收件人
```

---

## 实现优先级与排期

| 阶段 | 模块 | 文件 | 依赖 | 价值 |
|------|------|------|------|------|
| **Week 1** | 报告模板 + KPI | `config.py` | 无 | 报告结构一致性 |
| **Week 1** | 历史存储 + 趋势 | `history.py` | 无 | 报告从"快照"变"洞察" |
| **Week 2** | Critic 审查 | `critic.py` | prompts.py | 防幻觉，提高可信度 |
| **Week 2** | Prompt 扩展 | `prompts.py` | config.py | 多角色基础 |
| **Week 2** | 工具扩展 | `tools.py` | history.py | Agent 获得历史能力 |
| **Week 2** | 主编排改造 | `deep_research.py` | 以上全部 | 集成多 Agent + critic |
| **Week 3** | 分发 | `delivery.py` | 无 | 自动化触达 |
| **Week 3** | 反馈闭环 | `feedback.py` | history.py | 持续进化 |
| **Week 3** | 定时调度 | `scheduler.py` | deep_research.py | 无人值守运行 |
| **Week 4** | 集成测试 | — | 全部 | 端到端验证 |
