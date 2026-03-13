#!/usr/bin/env bash
#
# AdMapix 安装脚本 (macOS / Linux)
#
# 用法：
#   bash install.sh <API_KEY>
#
set -euo pipefail

API_KEY="${1:-}"
if [ -z "$API_KEY" ]; then
  echo "用法: bash install.sh <API_KEY>"
  echo "  API_KEY: 管理员分配的密钥"
  exit 1
fi

INSTALL_DIR="$HOME/.admapix"
MCPORTER_CONFIG="$HOME/.mcporter/mcporter.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MIN_PY_MAJOR=3
MIN_PY_MINOR=10

info()  { echo "✅ $*"; }
warn()  { echo "⚠️  $*"; }
error() { echo "❌ $*" >&2; exit 1; }

# ── 工具函数 ──────────────────────────────────────────────────

check_python_version() {
  local py="$1"
  command -v "$py" &>/dev/null || return 1
  "$py" -c "import sys; exit(0 if sys.version_info >= ($MIN_PY_MAJOR,$MIN_PY_MINOR) else 1)" 2>/dev/null
}

find_python() {
  for py in python3.13 python3.12 python3.11 python3.10 python3; do
    if check_python_version "$py"; then
      command -v "$py"
      return 0
    fi
  done
  return 1
}

ensure_homebrew() {
  if command -v brew &>/dev/null; then return 0; fi
  echo "  → 安装 Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null)"
}

# ── Step 1: Python ───────────────────────────────────────────

echo ""
echo "══════════════════════════════════════"
echo "  AdMapix 安装"
echo "══════════════════════════════════════"
echo ""
echo "── [1/5] 检测 Python 环境 ──"

PYTHON_BIN=""
if PYTHON_BIN=$(find_python); then
  info "Python 已就绪: $PYTHON_BIN ($($PYTHON_BIN --version 2>&1))"
else
  warn "未检测到 Python $MIN_PY_MAJOR.$MIN_PY_MINOR+，开始安装..."
  case "$(uname -s)" in
    Darwin)
      ensure_homebrew
      brew install python@3.12
      ;;
    Linux)
      if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-venv python3-pip
      elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 python3-pip
      elif command -v yum &>/dev/null; then
        sudo yum install -y python3 python3-pip
      else
        error "无法识别包管理器，请手动安装 Python $MIN_PY_MAJOR.$MIN_PY_MINOR+"
      fi
      ;;
    *) error "不支持的系统: $(uname -s)" ;;
  esac

  PYTHON_BIN=$(find_python) || error "Python 安装后仍未检测到，请检查 PATH"
  info "Python 安装成功: $PYTHON_BIN"
fi

# ── Step 2: Node.js ──────────────────────────────────────────

echo ""
echo "── [2/5] 检测 Node.js 环境 ──"

if command -v node &>/dev/null; then
  info "Node.js 已就绪: $(node --version)"
else
  warn "未检测到 Node.js，开始安装..."
  case "$(uname -s)" in
    Darwin)
      ensure_homebrew
      brew install node
      ;;
    Linux)
      if command -v apt-get &>/dev/null; then
        # NodeSource 官方源
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
        sudo apt-get install -y -qq nodejs
      elif command -v dnf &>/dev/null; then
        sudo dnf install -y nodejs
      elif command -v yum &>/dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -
        sudo yum install -y nodejs
      else
        error "无法识别包管理器，请手动安装 Node.js"
      fi
      ;;
    *) error "不支持的系统" ;;
  esac

  command -v node &>/dev/null || error "Node.js 安装失败"
  info "Node.js 安装成功: $(node --version)"
fi

# ── Step 3: mcporter ─────────────────────────────────────────

echo ""
echo "── [3/5] 检测 mcporter ──"

if command -v mcporter &>/dev/null; then
  info "mcporter 已就绪: $(command -v mcporter)"
else
  warn "未检测到 mcporter，开始安装..."
  npm install -g mcporter
  command -v mcporter &>/dev/null || error "mcporter 安装失败，请检查 npm 全局安装路径是否在 PATH 中"
  info "mcporter 安装成功"
fi

# ── Step 4: MCP Server + 虚拟环境 ────────────────────────────

echo ""
echo "── [4/5] 安装 MCP Server ──"

mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/server.py" "$INSTALL_DIR/server.py"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/requirements.txt"

if [ ! -d "$INSTALL_DIR/.venv" ]; then
  echo "  → 创建虚拟环境..."
  "$PYTHON_BIN" -m venv "$INSTALL_DIR/.venv"
fi

echo "  → 安装依赖..."
"$INSTALL_DIR/.venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"
info "MCP Server 安装完成: $INSTALL_DIR"

# ── Step 5: mcporter.json ────────────────────────────────────

echo ""
echo "── [5/5] 配置 mcporter ──"

VENV_PYTHON="$INSTALL_DIR/.venv/bin/python3"
SERVER_PY="$INSTALL_DIR/server.py"

mkdir -p "$(dirname "$MCPORTER_CONFIG")"

"$VENV_PYTHON" -c "
import json, os

path = '$MCPORTER_CONFIG'
cfg = {}
if os.path.exists(path):
    with open(path) as f:
        cfg = json.load(f)

servers = cfg.get('mcpServers', {})
servers['admapix'] = {
    'command': '$VENV_PYTHON $SERVER_PY',
    'env': {'API_KEY': '$API_KEY'}
}
cfg['mcpServers'] = servers
cfg.setdefault('imports', [])

with open(path, 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
"
info "mcporter 配置已写入: $MCPORTER_CONFIG"

# ── 完成 ─────────────────────────────────────────────────────

echo ""
echo "══════════════════════════════════════"
echo "  安装完成！"
echo "══════════════════════════════════════"
echo ""
echo "  安装目录:  $INSTALL_DIR"
echo "  配置文件:  $MCPORTER_CONFIG"
echo ""
echo "  现在可以通过 OpenClaw 使用"
echo "  「搜广告」「找素材」等指令了。"
echo ""
