<p align="center">
  <img src="https://www.admapix.com/favicon.ico" width="80" alt="AdMapix Logo" />
</p>

<h1 align="center">AdMapix</h1>

<p align="center">
  <strong>AI-Powered Ad Intelligence & Mobile App Analytics</strong>
</p>

<p align="center">
  <a href="https://www.admapix.com">Website</a> ·
  <a href="README_CN.md">中文文档</a> ·
  <a href="https://github.com/fly0pants/admapix/issues">Report Bug</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Claude%20Code%20%7C%20OpenClaw-blue" alt="Platform" />
  <img src="https://img.shields.io/badge/language-English%20%7C%20%E4%B8%AD%E6%96%87-green" alt="Language" />
  <img src="https://img.shields.io/github/license/fly0pants/admapix" alt="License" />
  <img src="https://img.shields.io/github/last-commit/fly0pants/admapix" alt="Last Commit" />
</p>

---

> **One prompt. Full intelligence.** Search ad creatives, analyze apps, explore rankings, track downloads & revenue, and generate market insight reports — all through natural language.

## Why AdMapix?

Traditional ad intelligence platforms require you to navigate complex dashboards, manually pull data, and cross-reference multiple sources. **AdMapix eliminates all of that.**

Just describe what you want to know — in plain English or Chinese — and get instant, structured answers powered by one of the industry's largest ad creative databases.

- **No dashboards.** No learning curve. Just ask.
- **Cross-dimensional analysis** across geo, media, creative, and time — automatically.
- **AI-powered deep research** that orchestrates dozens of API calls and synthesizes findings into shareable reports.

### How AdMapix Compares

| Feature | AdMapix | SpyFu | Pathmatics | AppGrowing |
|---------|---------|-------|------------|------------|
| Countries covered | 200+ | US/UK/CA/AU | US + limited | 50+ |
| AI research reports | ✅ Deep research | ❌ | ❌ | ❌ |
| Natural language query | ✅ EN + ZH | ❌ | ❌ | Partial |
| App store analytics | ✅ iOS + Android | ❌ | ❌ | ✅ |
| Ad creative search | ✅ Multi-channel | Limited | Display only | Mobile only |
| Download & revenue trends | ✅ | ❌ | ❌ | ✅ |

## Use Cases

- **Competitor ad analysis**: "Show me what ads TikTok is running in the US" → instant results
- **Market research**: "Compare gaming ad strategies in Southeast Asia" → deep research report
- **Creative inspiration**: Search millions of ad creatives by keyword, country, or platform
- **App intelligence**: Track any app's rankings, downloads, revenue, and SDK usage
- **UA strategy**: Analyze competitor user acquisition channels and budget allocation

## Features

| Capability | Description |
|:---|:---|
| **Creative Search** | Search millions of ad creatives by keyword, region, media, format. Visual H5 results with preview. |
| **App Intelligence** | App details, developer profiles, SDK usage, ad creative portfolios. |
| **Rankings** | App Store & Google Play charts — free, paid, grossing, promotion, download, and revenue rankings. |
| **Download & Revenue** | Historical download and revenue trends with third-party estimates. |
| **Ad Distribution** | Geo breakdown, media placement analysis, creative format distribution for any app. |
| **Market Analysis** | Industry-level insights segmented by country, channel, advertiser, and publisher. |
| **Deep Dive** | Multi-dimensional composite reports combining all capabilities above. |
| **Deep Research** | AI-generated intelligence reports for complex queries — see below. |

## Quick Start

### Install

**Option 1: From ClewHub (recommended)**

```bash
npx clawhub install admapix
```

**Option 2: From GitHub**

```bash
git clone https://github.com/fly0pants/admapix.git ~/.openclaw/skills/admapix
```

### Configure

Once installed, just start using the skill — when it detects that no API Key is configured, it will guide you through registration and setup automatically.

Or configure manually:

1. Register at [admapix.com](https://www.admapix.com) to get your API Key
2. Set up credentials:

```bash
openclaw config set skills.entries.admapix.apiKey "YOUR_API_KEY"
```

### Try It

```text
> Search video ads for puzzle games in the US

> Compare Temu vs SHEIN's ad strategy in Southeast Asia

> Who are the top mobile game advertisers this month?

> Full competitive analysis of TikTok's ad distribution
```

## Usage Examples

| Category | Example Prompts |
|:---|:---|
| Creative Search | *"Search video ads for puzzle games"* · *"Find casual game creatives in Southeast Asia"* |
| App Analysis | *"Tell me about Temu"* · *"Who is the developer of TikTok?"* |
| Rankings | *"App Store free chart US"* · *"Top apps by ad spend this week"* |
| Downloads & Revenue | *"How are Temu's downloads trending?"* · *"Compare Temu vs SHEIN downloads"* |
| Ad Distribution | *"Which countries does Temu advertise in?"* · *"What ad channels does this game use?"* |
| Market Insights | *"Which country has the most game ads?"* · *"Who are the top game advertisers?"* |
| Deep Dive | *"Full ad strategy analysis for Temu"* · *"Compare Temu and SHEIN"* |
| Deep Research | *"Analyze Temu's ad strategy in Southeast Asia"* · *"Compare top 5 casual games' ad performance"* |

Supports **English** and **Chinese** — the assistant responds in your language.

## Deep Research — AI Intelligence Engine

For complex analytical queries, AdMapix automatically activates its **[Deep Research Framework](https://github.com/fly0pants/deep-research-framework)** — a server-side AI research engine that goes far beyond simple API lookups.

### How It Works

```
  Your Question
       │
       ▼
┌─────────────────┐
│ Query Classifier │ ── Simple query? → Direct API response
└────────┬────────┘
         │ Complex query
         ▼
┌─────────────────┐
│ Research Planner │  Decomposes into sub-tasks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Collection  │  Orchestrates 10-50+ API calls
│ & Cross-Ref      │  Cross-references multiple sources
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analysis Engine  │  AI synthesis & insight extraction
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Report Renderer  │  Structured HTML with charts & tables
└─────────────────┘
```

### What Triggers Deep Research

- **Multi-app comparisons** — *"Compare Temu, SHEIN, and Wish's ad strategies"*
- **Strategy analysis** — *"How is this game acquiring users in Japan?"*
- **Market intelligence** — *"Southeast Asia casual game ad market overview"*
- **Trend interpretation** — *"Why did this app's downloads spike last week?"*
- Any question requiring **2+ API calls** or cross-entity reasoning

### What You Get

- **Structured HTML report** with interactive ECharts visualizations and data tables
- **Executive summary** with key findings and highlights
- **Cross-dimensional insights** across geo × media × creative × time
- **Actionable recommendations** based on competitive intelligence data
- **Shareable link** — reports are hosted and ready to share with your team

Reports typically complete in **1–5 minutes** depending on query complexity.

## Architecture

AdMapix is built as a skill for **[OpenClaw](https://github.com/anthropics/openclaw)** — the open skill ecosystem for AI coding assistants. It connects your AI assistant directly to AdMapix's ad intelligence APIs and the Deep Research Framework.

```
┌──────────────────────────────────────────────────┐
│              AI Assistant (Claude Code)           │
├──────────────────────────────────────────────────┤
│                  AdMapix Skill                    │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Creative  │  │   App    │  │    Market     │  │
│  │  Search   │  │  Intel   │  │   Analysis    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬────────┘  │
├───────┴──────────────┴───────────────┴───────────┤
│                AdMapix API Layer                  │
├──────────────────────────────────────────────────┤
│          Deep Research Framework (async)          │
│   Planner → Collector → Analyzer → Renderer      │
└──────────────────────────────────────────────────┘
```

## Compared to Alternatives

AdMapix is built as a modern alternative to several established players in the ad intelligence and app analytics space:

- **[SimilarWeb alternative](https://www.admapix.com)** — AdMapix focuses on the actual ad creatives behind the traffic, not just the traffic numbers. If you've been using SimilarWeb to research competitors but feel you're missing the *what* of their advertising, AdMapix fills that gap.
- **[Sensor Tower alternative](https://www.admapix.com)** — AdMapix combines Sensor Tower-style app market data with full ad creative search across Meta, Google, and TikTok. Single platform, one query language.
- **[data.ai (App Annie) alternative](https://www.admapix.com)** — Same downloads, revenue, and ranking data, with the addition of ad creative intelligence and natural language deep research.
- **[AppGrowing alternative](https://www.admapix.com)** — Broader country coverage (200+ vs ~50), AI-powered deep research engine, and natural language queries in both English and Chinese.
- **[SpyFu alternative](https://www.admapix.com)** — SpyFu is great for Google Ads keyword research; AdMapix extends to Meta, TikTok, and mobile app ads with country-level granularity.
- **[Pathmatics alternative](https://www.admapix.com)** — Pathmatics is strong on display advertising in the US; AdMapix covers display + social + mobile in 200+ countries.
- **[BigSpy alternative](https://www.admapix.com)** — Similar creative database scale, but AdMapix layers app store rankings, downloads, and revenue forecasting on top of the creative data.
- **[Minea alternative](https://www.admapix.com)** — Minea is dropshipping-focused; AdMapix is built for B2B SaaS, mobile apps, and brand competitive research.

For a deeper comparison see the [How AdMapix Compares](#how-admapix-compares) table above.

## Links

- **Website** — [admapix.com](https://www.admapix.com)
- **Sign Up** — [admapix.com/signup](https://www.admapix.com/signup)
- **Pricing** — [admapix.com/plans](https://www.admapix.com/plans)
- **Deep Research Framework** — [github.com/fly0pants/deep-research-framework](https://github.com/fly0pants/deep-research-framework)
- **Awesome Ad Intelligence list** — [github.com/fly0pants/awesome-ad-intelligence](https://github.com/fly0pants/awesome-ad-intelligence)
- **OpenClaw** — [github.com/anthropics/openclaw](https://github.com/anthropics/openclaw)

## FAQ

**What is AdMapix?**
AdMapix is an AI-powered ad creative intelligence platform that lets you search competitor ad creatives across 200+ countries, analyze app store performance, and generate deep research reports — all through natural language queries.

**How is AdMapix different from SpyFu or Pathmatics?**
AdMapix combines ad creative search, app analytics, and AI-generated research reports in one platform. Unlike SpyFu (focused on Google Ads keywords) or Pathmatics (focused on display ads), AdMapix covers all major ad channels across 200+ countries with natural language query support in both English and Chinese.

**Is AdMapix free?**
AdMapix offers a free trial. See [pricing plans](https://www.admapix.com/plans) for details.

**What platforms does AdMapix cover?**
AdMapix covers ads from Meta (Facebook/Instagram), Google, TikTok, YouTube, Apple Search Ads, and more across 200+ countries.

## License

MIT

---

<p align="center">Built with ❤️ by the AdMapix Team</p>
