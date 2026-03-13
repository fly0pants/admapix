#
# AdMapix 安装脚本 (Windows)
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File install.ps1 -ApiKey <API_KEY>
#
param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey
)

$ErrorActionPreference = "Stop"

$InstallDir = Join-Path $env:USERPROFILE ".admapix"
$McporterConfig = Join-Path $env:USERPROFILE ".mcporter\mcporter.json"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MinPyMajor = 3
$MinPyMinor = 10

function Write-Info  { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[ERR] $msg" -ForegroundColor Red; exit 1 }

# ── 工具函数 ──────────────────────────────────────────────────

function Find-Python {
    $candidates = @("python3", "python")
    foreach ($py in $candidates) {
        $cmd = Get-Command $py -ErrorAction SilentlyContinue
        if ($cmd) {
            try {
                $ver = & $py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                $parts = $ver.Split(".")
                if ([int]$parts[0] -ge $MinPyMajor -and [int]$parts[1] -ge $MinPyMinor) {
                    return $cmd.Source
                }
            } catch {}
        }
    }
    return $null
}

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# ── Step 1: Python ───────────────────────────────────────────

Write-Host ""
Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  AdMapix 安装" -ForegroundColor Cyan
Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "── [1/5] 检测 Python 环境 ──"

$PythonBin = Find-Python
if ($PythonBin) {
    $pyVer = & $PythonBin --version 2>&1
    Write-Info "Python 已就绪: $PythonBin ($pyVer)"
} else {
    Write-Warn "未检测到 Python $MinPyMajor.$MinPyMinor+，开始安装..."

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  → 通过 winget 安装 Python..."
        winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    } else {
        Write-Err "请手动安装 Python $MinPyMajor.$MinPyMinor+: https://www.python.org/downloads/"
    }

    Refresh-Path
    $PythonBin = Find-Python
    if (-not $PythonBin) { Write-Err "Python 安装后仍未检测到，请重新打开终端后重试" }
    Write-Info "Python 安装成功: $PythonBin"
}

# ── Step 2: Node.js ──────────────────────────────────────────

Write-Host ""
Write-Host "── [2/5] 检测 Node.js 环境 ──"

if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVer = node --version
    Write-Info "Node.js 已就绪: $nodeVer"
} else {
    Write-Warn "未检测到 Node.js，开始安装..."

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  → 通过 winget 安装 Node.js..."
        winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
    } else {
        Write-Err "请手动安装 Node.js: https://nodejs.org/"
    }

    Refresh-Path
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Err "Node.js 安装后仍未检测到，请重新打开终端后重试"
    }
    Write-Info "Node.js 安装成功: $(node --version)"
}

# ── Step 3: mcporter ─────────────────────────────────────────

Write-Host ""
Write-Host "── [3/5] 检测 mcporter ──"

if (Get-Command mcporter -ErrorAction SilentlyContinue) {
    Write-Info "mcporter 已就绪"
} else {
    Write-Warn "未检测到 mcporter，开始安装..."
    npm install -g mcporter

    Refresh-Path
    if (-not (Get-Command mcporter -ErrorAction SilentlyContinue)) {
        Write-Err "mcporter 安装失败，请检查 npm 全局路径是否在 PATH 中"
    }
    Write-Info "mcporter 安装成功"
}

# ── Step 4: MCP Server + 虚拟环境 ────────────────────────────

Write-Host ""
Write-Host "── [4/5] 安装 MCP Server ──"

if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null }

Copy-Item (Join-Path $ScriptDir "server.py") (Join-Path $InstallDir "server.py") -Force
Copy-Item (Join-Path $ScriptDir "requirements.txt") (Join-Path $InstallDir "requirements.txt") -Force

$VenvDir = Join-Path $InstallDir ".venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "  → 创建虚拟环境..."
    & $PythonBin -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

Write-Host "  → 安装依赖..."
& $VenvPip install -q -r (Join-Path $InstallDir "requirements.txt")
Write-Info "MCP Server 安装完成: $InstallDir"

# ── Step 5: mcporter.json ────────────────────────────────────

Write-Host ""
Write-Host "── [5/5] 配置 mcporter ──"

$ServerPy = Join-Path $InstallDir "server.py"
$McporterDir = Split-Path $McporterConfig
if (-not (Test-Path $McporterDir)) { New-Item -ItemType Directory -Path $McporterDir -Force | Out-Null }

# 用 Python 合并配置
$configScript = @"
import json, os

path = r'$McporterConfig'
cfg = {}
if os.path.exists(path):
    with open(path) as f:
        cfg = json.load(f)

servers = cfg.get('mcpServers', {})
servers['admapix'] = {
    'command': r'$VenvPython $ServerPy',
    'env': {'API_KEY': '$ApiKey'}
}
cfg['mcpServers'] = servers
cfg.setdefault('imports', [])

with open(path, 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
"@

& $VenvPython -c $configScript
Write-Info "mcporter 配置已写入: $McporterConfig"

# ── 完成 ─────────────────────────────────────────────────────

Write-Host ""
Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  安装完成！" -ForegroundColor Cyan
Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  安装目录:  $InstallDir"
Write-Host "  配置文件:  $McporterConfig"
Write-Host ""
Write-Host "  现在可以通过 OpenClaw 使用"
Write-Host "  「搜广告」「找素材」等指令了。"
Write-Host ""
