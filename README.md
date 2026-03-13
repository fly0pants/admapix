<h1 align="center">🎯 AdMapix</h1>

<p align="center">
  <strong>AI-Powered Ad Creative Intelligence — Search, Discover, Deliver.</strong><br>
  <sub><b>Ad</b>(广告) + <b>Ma</b>(Map/Material) + <b>Pix</b>(Pixel) — 广告素材，像素级洞察。</sub>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-1_min-blue?style=for-the-badge" alt="Quick Start"></a>
  <a href="#-features"><img src="https://img.shields.io/badge/Features-6_Core-green?style=for-the-badge" alt="Features"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/MCP-STDIO-blueviolet" alt="MCP">
  <img src="https://img.shields.io/badge/platform-macOS_|_Linux_|_Windows-lightgrey" alt="Platform">
</p>

---

## 🤔 What is AdMapix?

AdMapix is an **MCP Server + OpenClaw Skill** that lets AI agents search competitor ad creatives through natural language.

Say **"帮我搜一下拼图游戏的广告素材"** in your chat, and get back a rich H5 results page with videos, images, and one-click delivery to WeChat.

```
User: "搜一下东南亚的休闲游戏视频广告"

Agent: 🎯 搜到 2,847 条广告素材（第 1 页）
       👉 http://ad.h5.miaozhisheng.tech/p/abc123
```

---

## ✨ Features

<table>
<tr>
<td width="33%">

### 🔍 Smart Search
Keyword, country, date range, creative type — all expressed in natural language, auto-mapped to API parameters.

</td>
<td width="33%">

### 🌏 Global Coverage
50+ countries, 10+ region shortcuts (东南亚, 北美, 日韩...), filterable by industry.

</td>
<td width="33%">

### 📊 Rich Results
Auto-generated H5 pages with video playback, image gallery, ad metrics, and impression data.

</td>
</tr>
<tr>
<td width="33%">

### 📱 WeChat Delivery
One-tap "Send to Chat" — delivers video files directly to WeChat conversations.

</td>
<td width="33%">

### 🤖 Agent-Native
Built as MCP Server, works with any MCP-compatible agent (OpenClaw, Claude Code, etc).

</td>
<td width="33%">

### ⚡ Zero Config
One install script handles Python, Node.js, mcporter, and config — fully automated.

</td>
</tr>
</table>

---

## 🚀 Quick Start

> **Prerequisite:** An API Key from your admin.

### Mac / Linux

```bash
git clone https://github.com/fly0pants/admapix.git
bash admapix/install.sh <YOUR_API_KEY>
```

### Windows (PowerShell)

```powershell
git clone https://github.com/fly0pants/admapix.git
powershell -ExecutionPolicy Bypass -File admapix\install.ps1 -ApiKey <YOUR_API_KEY>
```

The installer automatically:

| Step | What it does |
|------|-------------|
| 1 | Detects or installs **Python 3.10+** |
| 2 | Detects or installs **Node.js** |
| 3 | Detects or installs **mcporter** |
| 4 | Sets up MCP Server in `~/.admapix/` |
| 5 | Configures `~/.mcporter/mcporter.json` |

**That's it.** Start chatting with your agent — say "搜广告" and go.

---

## 🎯 Usage Examples

Through your AI agent (OpenClaw, etc.), just say:

| You say | What happens |
|---------|-------------|
| "搜一下 temu 的广告" | Search by keyword |
| "只看视频素材" | Filter by creative type |
| "东南亚地区的" | Filter by region |
| "按曝光量排序" | Sort by impression |
| "最近一周的" | Filter by date range |
| "下一页" | Paginate |

---

## 🔧 Manual Setup

<details>
<summary>If you prefer manual configuration over the install script</summary>

1. **Install dependencies**

```bash
python3 -m venv ~/.admapix/.venv
~/.admapix/.venv/bin/pip install mcp httpx pydantic
```

2. **Configure `~/.mcporter/mcporter.json`**

```json
{
  "mcpServers": {
    "admapix": {
      "command": "~/.admapix/.venv/bin/python3 ~/.admapix/server.py",
      "env": {
        "API_KEY": "<YOUR_API_KEY>"
      }
    }
  }
}
```

3. **Install the Skill**

```bash
cp -r skill/ ~/.openclaw/skills/ad-creative-search/
```

</details>

---

## 🏗️ Architecture

```
User (WeChat / Agent)
  → AI Agent (OpenClaw)
    → mcporter call 'admapix.search_creatives(...)'
      → MCP Server (Python, STDIO)
        → InsighTrackr API
          → H5 Result Page ← User views in browser
          → Video Delivery  ← User receives in WeChat
```

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<div align="center">

**AdMapix** — *Ad intelligence at your fingertips.*

</div>
