# AdMapix

广告素材搜索 MCP Server，配合 OpenClaw 的 `ad-creative-search` skill 使用。

通过 [InsighTrackr](http://ad.h5.miaozhisheng.tech) 平台搜索竞品广告创意素材，返回 H5 结果页面链接。

## 快速安装

需要管理员分配的 **API Key**。

### Mac / Linux

```bash
git clone https://github.com/fly0pants/admapix.git
bash admapix/install.sh <API_KEY>
```

### Windows (PowerShell)

```powershell
git clone https://github.com/fly0pants/admapix.git
powershell -ExecutionPolicy Bypass -File admapix\install.ps1 -ApiKey <API_KEY>
```

安装脚本会自动：

1. 检测并安装 Python 3.10+（如果没有）
2. 检测并安装 Node.js（如果没有）
3. 检测并安装 mcporter（如果没有）
4. 安装 MCP Server 到 `~/.admapix/`
5. 配置 `~/.mcporter/mcporter.json`

## 手动配置

如果不使用安装脚本，手动配置 `~/.mcporter/mcporter.json`：

```json
{
  "mcpServers": {
    "admapix": {
      "command": "<python路径> <server.py路径>",
      "env": {
        "API_KEY": "<管理员分配的密钥>"
      }
    }
  }
}
```

## Skill 安装

将 `skill/` 目录下的文件复制到 OpenClaw skills 目录：

```bash
cp -r skill/ ~/.openclaw/skills/ad-creative-search/
```

## 功能

- 关键词搜索广告素材
- 按素材类型筛选（图片/视频/试玩）
- 按国家/地区筛选
- 按时间范围筛选
- 多种排序方式（最新/最热/最相关/投放最久）
- 自动生成 H5 结果页面
- 支持将视频发送到微信对话
