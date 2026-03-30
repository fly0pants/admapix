<p align="center">
  <img src="https://www.admapix.com/favicon.ico" width="80" alt="AdMapix Logo" />
</p>

<h1 align="center">AdMapix</h1>

<p align="center">
  <strong>AI 驱动的广告情报与移动应用分析平台</strong>
</p>

<p align="center">
  <a href="https://www.admapix.com">官网</a> ·
  <a href="README.md">English</a> ·
  <a href="https://github.com/fly0pants/admapix/issues">问题反馈</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Claude%20Code%20%7C%20OpenClaw-blue" alt="Platform" />
  <img src="https://img.shields.io/badge/language-English%20%7C%20%E4%B8%AD%E6%96%87-green" alt="Language" />
  <img src="https://img.shields.io/github/license/fly0pants/admapix" alt="License" />
  <img src="https://img.shields.io/github/last-commit/fly0pants/admapix" alt="Last Commit" />
</p>

---

> **一句话，全局洞察。** 搜索广告素材、分析应用数据、查看排行榜、追踪下载与收入、生成市场分析报告 — 全部通过自然语言完成。

## 为什么选择 AdMapix？

传统广告情报平台需要你在复杂的仪表盘中来回切换、手动拉取数据、交叉比对多个来源。**AdMapix 把这一切都省了。**

用自然语言描述你想了解的内容 — 中文或英文都行 — 即时获得结构化的专业分析结果，背后是业内最大规模的广告素材数据库之一。

- **零门槛** — 没有仪表盘，没有学习成本，直接开问
- **跨维度自动分析** — 地域 × 媒体 × 素材 × 时间，自动交叉关联
- **AI 深度研究引擎** — 自动编排数十个 API 调用，综合分析后生成可分享的智能报告

### 与竞品对比

| 功能 | AdMapix | SpyFu | Pathmatics | AppGrowing |
|------|---------|-------|------------|------------|
| 覆盖国家 | 200+ | 美/英/加/澳 | 美国为主 | 50+ |
| AI 研究报告 | ✅ 深度研究 | ❌ | ❌ | ❌ |
| 自然语言查询 | ✅ 中英双语 | ❌ | ❌ | 部分支持 |
| 应用商店分析 | ✅ iOS + Android | ❌ | ❌ | ✅ |
| 广告素材搜索 | ✅ 全渠道 | 有限 | 仅展示广告 | 仅移动端 |
| 下载量与收入趋势 | ✅ | ❌ | ❌ | ✅ |

## 使用场景

- **竞品广告分析**："帮我看看 TikTok 在美国投了什么广告" → 即时获取结果
- **市场调研**："对比东南亚游戏广告策略" → 生成深度研究报告
- **创意灵感**：按关键词、国家、平台搜索海量广告素材
- **应用情报**：追踪任意 App 的排名、下载量、收入和 SDK 使用情况
- **买量策略**：分析竞品的用户获取渠道和预算分配

## 核心能力

| 能力 | 说明 |
|:---|:---|
| **素材搜索** | 按关键词、地区、媒体、格式搜索海量广告素材，支持 H5 可视化预览 |
| **应用情报** | 应用详情、开发者信息、SDK 使用情况、广告素材库 |
| **排行榜** | App Store & Google Play 各类榜单 — 免费榜、付费榜、畅销榜、推广榜、下载榜、收入榜 |
| **下载量与收入** | 历史下载量和收入趋势（第三方估算数据） |
| **投放分布** | 任意应用的地域分布、媒体渠道、素材格式分析 |
| **市场分析** | 按国家、渠道、广告主、流量主维度的行业级洞察 |
| **深度分析** | 融合以上所有能力的多维度综合报告 |
| **深度研究** | AI 生成的智能分析报告，适用于复杂查询 — 详见下文 |

## 快速开始

### 安装

**方式一：从 ClewHub 安装（推荐）**

```bash
npx clawhub install admapix
```

**方式二：从 GitHub 安装**

```bash
git clone https://github.com/fly0pants/admapix.git ~/.openclaw/skills/admapix
```

### 配置

安装后直接使用即可 — 首次使用时 skill 会自动引导你注册账号并配置 API Key。

如需手动配置：

1. 前往 [admapix.com](https://www.admapix.com) 注册并获取 API Key
2. 设置凭证：

```bash
openclaw config set skills.entries.admapix.apiKey "你的API_KEY"
```

### 试试看

```text
> 搜一下美国市场的 puzzle game 视频广告

> 对比 Temu 和 SHEIN 在东南亚的广告策略

> 这个月投放量最大的手游广告主是谁？

> 全面分析 TikTok 的广告投放分布
```

## 使用示例

| 分类 | 示例指令 |
|:---|:---|
| 素材搜索 | *「搜一下 puzzle game 的视频广告」* · *「找东南亚投放的休闲游戏素材」* |
| 应用分析 | *「分析一下 Temu」* · *「TikTok 的开发者是谁？」* |
| 排行榜 | *「美国 App Store 免费榜」* · *「这周广告投放量最大的 App」* |
| 下载量与收入 | *「Temu 最近下载量怎么样？」* · *「对比 Temu 和 SHEIN 的下载量」* |
| 投放分布 | *「Temu 主要在哪些国家投广告？」* · *「这个游戏用了哪些广告渠道？」* |
| 市场洞察 | *「全球游戏广告市场哪个国家最大？」* · *「谁是最大的游戏广告主？」* |
| 深度分析 | *「全面分析 Temu 的广告策略」* · *「对比 Temu 和 SHEIN」* |
| 深度研究 | *「分析 Temu 在东南亚的广告策略」* · *「对比 Top 5 休闲游戏的广告表现」* |

支持 **中文** 和 **英文** 双语 — 助手自动匹配你的语言。

## 深度研究 — AI 智能分析引擎

面对复杂的分析需求，AdMapix 自动激活 **[深度研究引擎](https://github.com/fly0pants/deep-research-framework)** — 一个服务端 AI 研究系统，远超简单的 API 查询。

### 工作原理

```
  你的问题
       │
       ▼
┌─────────────────┐
│   查询分类器     │ ── 简单查询？ → 直接 API 响应
└────────┬────────┘
         │ 复杂查询
         ▼
┌─────────────────┐
│   研究规划器     │  分解为多个子任务
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   数据采集器     │  编排 10-50+ 个 API 调用
│   & 交叉验证     │  多数据源交叉比对
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   分析引擎       │  AI 综合分析与洞察提炼
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   报告渲染器     │  结构化 HTML + 交互式图表
└─────────────────┘
```

### 什么情况会触发深度研究

- **多应用对比** — *「对比 Temu、SHEIN 和 Wish 的广告策略」*
- **策略分析** — *「这款游戏在日本是怎么做用户获取的？」*
- **市场情报** — *「东南亚休闲游戏广告市场概况」*
- **趋势解读** — *「这个 App 上周下载量为什么暴涨？」*
- 任何需要 **2 个以上 API 调用**或跨实体推理的问题

### 你会得到

- **结构化 HTML 报告** — 内含 ECharts 交互式图表和数据表格
- **核心发现摘要** — 关键洞察一目了然
- **跨维度分析** — 地域 × 媒体 × 素材 × 时间多维交叉
- **可执行建议** — 基于竞品数据的策略建议
- **在线分享** — 报告在线托管，一键分享给团队

报告通常在 **1-5 分钟**内完成，取决于查询复杂度。

## 技术架构

AdMapix 基于 **[OpenClaw](https://github.com/anthropics/openclaw)** 构建 — AI 编程助手的开放 Skill 生态。它将你的 AI 助手直接接入 AdMapix 广告情报 API 和深度研究引擎。

```
┌──────────────────────────────────────────────────┐
│            AI 助手 (Claude Code)                  │
├──────────────────────────────────────────────────┤
│                 AdMapix Skill                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  素材搜索  │  │ 应用情报  │  │   市场分析    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬────────┘  │
├───────┴──────────────┴───────────────┴───────────┤
│               AdMapix API 层                      │
├──────────────────────────────────────────────────┤
│           深度研究引擎 (异步)                       │
│   规划 → 采集 → 分析 → 渲染                        │
└──────────────────────────────────────────────────┘
```

## 相关链接

- **官网** — [admapix.com](https://www.admapix.com)
- **深度研究引擎** — [github.com/fly0pants/deep-research-framework](https://github.com/fly0pants/deep-research-framework)
- **OpenClaw** — [github.com/anthropics/openclaw](https://github.com/anthropics/openclaw)

## 常见问题

**AdMapix 是什么？**
AdMapix 是一个 AI 驱动的广告情报平台，支持在 200+ 个国家搜索竞品广告素材、分析应用商店表现、生成深度研究报告 — 全部通过自然语言完成。

**AdMapix 和 SpyFu、Pathmatics 有什么区别？**
AdMapix 将广告素材搜索、应用分析和 AI 研究报告整合在一个平台。不同于 SpyFu（专注 Google Ads 关键词）或 Pathmatics（专注展示广告），AdMapix 覆盖所有主流广告渠道、200+ 个国家，并支持中英双语自然语言查询。

**AdMapix 免费吗？**
AdMapix 提供免费试用。详情请查看[定价方案](https://www.admapix.com/plans)。

**AdMapix 覆盖哪些广告平台？**
AdMapix 覆盖 Meta（Facebook/Instagram）、Google、TikTok、YouTube、Apple Search Ads 等主流平台，横跨 200+ 个国家。

## 开源协议

MIT

---

<p align="center">由 AdMapix Team 用 ❤️ 打造</p>
