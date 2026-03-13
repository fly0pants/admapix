<h1 align="center">🎯 AdMapix</h1>

<p align="center">
  <strong>AI 驱动的广告素材情报 — 搜索、发现、送达。</strong><br>
  <sub><b>Ad</b>(广告) + <b>Ma</b>(Map/Material) + <b>Pix</b>(Pixel) — 广告素材，像素级洞察。</sub>
</p>

<p align="center">
  <a href="#-快速开始"><img src="https://img.shields.io/badge/快速开始-1_分钟-blue?style=for-the-badge" alt="Quick Start"></a>
  <a href="#-功能特性"><img src="https://img.shields.io/badge/核心功能-6_项-green?style=for-the-badge" alt="Features"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/MCP-STDIO-blueviolet" alt="MCP">
  <img src="https://img.shields.io/badge/平台-macOS_|_Linux_|_Windows-lightgrey" alt="Platform">
</p>

<p align="center">
  <a href="README.md"><strong>English</strong></a>
</p>

---

## 🤔 AdMapix 是什么？

AdMapix 是一个 **MCP Server + OpenClaw Skill**，让 AI 智能体通过自然语言搜索竞品广告素材。

只需对你的 AI 助手说出想搜的内容，即可获得包含视频、图片、数据指标的 H5 结果页面，还能一键将视频发送到微信对话。

```
用户: "搜一下东南亚的休闲游戏视频广告"

助手: 🎯 搜到 2,847 条广告素材（第 1 页）
      👉 http://ad.h5.miaozhisheng.tech/p/abc123
```

---

## ✨ 功能特性

<table>
<tr>
<td width="33%">

### 🔍 智能搜索
关键词、国家、时间范围、素材类型 — 自然语言表达，自动映射为 API 参数。

</td>
<td width="33%">

### 🌏 全球覆盖
50+ 国家，10+ 地区快捷词（东南亚、北美、日韩……），支持行业分类筛选。

</td>
<td width="33%">

### 📊 丰富展示
自动生成 H5 页面，包含视频播放、图片画廊、广告指标、预估曝光量等数据。

</td>
</tr>
<tr>
<td width="33%">

### 📱 微信送达
一键"发送到对话" — 将视频文件直接发送到微信聊天中。

</td>
<td width="33%">

### 🤖 智能体原生
基于 MCP 协议，兼容任何支持 MCP 的智能体（OpenClaw、Claude Code 等）。

</td>
<td width="33%">

### ⚡ 零配置安装
一个脚本搞定 Python、Node.js、mcporter 和配置文件 — 全程自动化。

</td>
</tr>
</table>

---

## 🚀 快速开始

> **前提：** 需要管理员分配的 **API Key**。

### Mac / Linux

```bash
git clone https://github.com/fly0pants/admapix.git
bash admapix/install.sh <你的API_KEY>
```

### Windows (PowerShell)

```powershell
git clone https://github.com/fly0pants/admapix.git
powershell -ExecutionPolicy Bypass -File admapix\install.ps1 -ApiKey <你的API_KEY>
```

安装脚本自动完成：

| 步骤 | 做什么 |
|------|--------|
| 1 | 检测或安装 **Python 3.10+** |
| 2 | 检测或安装 **Node.js** |
| 3 | 检测或安装 **mcporter** |
| 4 | 安装 MCP Server 到 `~/.admapix/` |
| 5 | 配置 `~/.mcporter/mcporter.json` |

**搞定。** 对你的 AI 助手说「搜广告」就可以用了。

---

## 🎯 使用方式

通过 AI 助手（OpenClaw 等），直接说：

| 你说 | 效果 |
|------|------|
| "搜一下 temu 的广告" | 按关键词搜索 |
| "只看视频素材" | 按素材类型筛选 |
| "东南亚地区的" | 按地区筛选 |
| "按曝光量排序" | 按曝光量排序 |
| "最近一周的" | 按时间范围筛选 |
| "下一页" | 翻页 |

---

## 🔧 手动配置

<details>
<summary>如果你不想用安装脚本，也可以手动配置</summary>

1. **安装依赖**

```bash
python3 -m venv ~/.admapix/.venv
~/.admapix/.venv/bin/pip install mcp httpx pydantic
```

2. **配置 `~/.mcporter/mcporter.json`**

```json
{
  "mcpServers": {
    "admapix": {
      "command": "~/.admapix/.venv/bin/python3 ~/.admapix/server.py",
      "env": {
        "API_KEY": "<你的API_KEY>"
      }
    }
  }
}
```

3. **安装 Skill**

```bash
cp -r skill/ ~/.openclaw/skills/ad-creative-search/
```

</details>

---

## 🏗️ 架构

```
用户（微信 / 智能体）
  → AI 智能体（OpenClaw）
    → mcporter call 'admapix.search_creatives(...)'
      → MCP Server（Python, STDIO）
        → InsighTrackr API
          → H5 结果页面 ← 用户在浏览器中查看
          → 视频送达    ← 用户在微信中接收
```

---

## 📄 许可证

MIT License — 自由使用、修改和分发。

---

<div align="center">

**AdMapix** — *广告情报，触手可及。*

</div>
