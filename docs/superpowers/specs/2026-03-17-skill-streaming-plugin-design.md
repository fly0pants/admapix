# OpenClaw Plugin: Skill Streaming Progress

**Date**: 2026-03-17
**Status**: Draft
**Package**: `openclaw-plugin-skill-streaming`

## Problem

When OpenClaw skills execute tool calls (curl, bash, etc.), users see nothing during the execution period — no progress, no status, no feedback. This creates a "black hole" experience, especially for skills that chain multiple API calls or have long-running operations. This is a common pain point across AI agent frameworks.

## Solution

An OpenClaw plugin that automatically injects streaming progress messages during skill tool call execution. Zero config by default, with optional declarative customization in SKILL.md metadata.

### Goals

- **Universal**: Works for all skills without any modification
- **Simple**: One command install, zero required configuration
- **Non-invasive**: Uses plugin hooks only, never modifies skill execution logic
- **Cross-channel**: Works on Feishu, Telegram, Slack, Discord, webchat, and all other channels
- **Phased release**: v1 as OpenClaw plugin, v2 extract core into standalone npm package for cross-platform reuse

### Non-Goals

- Modifying the LLM's streaming behavior (token-by-token streaming already works)
- Providing a streaming proxy between skills and target APIs
- Injecting prompt instructions into skills

## Architecture

### Core Mechanism: 3 Hooks + State Machine

```
before_tool_call  →  parse tool info → update RunState → send progress message
after_tool_call   →  record duration → update RunState → send completion message
agent_end         →  cleanup state → optional summary message
```

### Data Flow

```
Hook fires
  → ctx.sessionKey parsed → extract channel + peerId + accountId
  → closure-captured api.runtime → call runtime.channel[channel].sendMessage(...)
  → progress message delivered to user

For webchat/SSE:
  → emitAgentEvent({stream: "assistant"}) → gateway SSE handler → browser client
```

### Key Design Decision: Independent Messages (Not Card Streaming)

`emitAgentEvent` and channel streaming cards (`onPartialReply`) are parallel, independent pipelines. Injecting into card streaming from a plugin hook is not feasible without deep framework changes.

**v1 approach**: Send progress as standalone messages via channel send functions. This works universally across all channels.

**Future v2**: Explore bridging into channel-specific streaming cards for a more polished UX.

## State Machine

```typescript
type RunState = {
  runId: string
  skillName: string | null       // null = regular chat, skip progress
  steps: StepRecord[]
  currentStep: number
  startedAt: number
  longRunningTimer?: NodeJS.Timeout
}

type StepRecord = {
  index: number
  label: string                  // from declaration or auto-extracted
  startedAt: number
  finishedAt?: number
  status: "running" | "done" | "error"
  longRunning?: boolean
  timer?: NodeJS.Timeout
}
```

One `RunState` per agent run. Created on first `before_tool_call` for a skill run, cleaned up on `agent_end`.

## Plugin Registration

```typescript
import type { OpenClawPluginDefinition } from "openclaw/plugin-sdk";
import { emitAgentEvent } from "openclaw/plugin-sdk";

const plugin: OpenClawPluginDefinition = {
  id: "skill-streaming",
  name: "Skill Streaming Progress",
  version: "0.1.0",
  description: "Auto-inject streaming progress for skill tool calls",

  register(api) {
    const runtime = api.runtime;   // closure capture
    const config = api.config;     // closure capture
    const runStates = new Map<string, RunState>();

    api.on("before_tool_call", (event, ctx) => {
      if (!isSkillRun(event, ctx)) return;

      const state = getOrCreateRunState(runStates, ctx, config);
      const label = resolveLabel(event, state.skillConfig);
      const step = pushStep(state, label);

      sendProgress(runtime, ctx, emitAgentEvent, formatStepStart(step, state));

      if (step.longRunning) {
        step.timer = setInterval(() => {
          sendProgress(runtime, ctx, emitAgentEvent, formatStillWorking(step, state));
        }, step.pollInterval ?? 15_000);
      }
    });

    api.on("after_tool_call", (event, ctx) => {
      const state = runStates.get(ctx.sessionKey);
      if (!state) return;

      const step = finishCurrentStep(state, event.error, event.durationMs);
      if (step.timer) clearInterval(step.timer);

      sendProgress(runtime, ctx, emitAgentEvent, formatStepDone(step, state));
    });

    api.on("agent_end", (event, ctx) => {
      const state = runStates.get(ctx.sessionKey);
      if (!state) return;

      if (state.steps.length > 1) {
        sendProgress(runtime, ctx, emitAgentEvent, formatSummary(state));
      }
      runStates.delete(ctx.sessionKey);
    });
  }
};
```

## Auto Label Extraction

When no declarative config exists, labels are auto-extracted from tool calls:

| Tool Type | Extraction Logic | Example |
|-----------|-----------------|---------|
| curl command | Regex extract domain + path | `curl api.admapix.com/search` → "Querying api.admapix.com/search" |
| bash command | First 50 chars of command | `python analyze.py --input data.json` → "Running: python analyze.py --input d..." |
| Other tools | Tool name | "Executing: web_search" |

Extraction function:
```typescript
function extractLabel(event: BeforeToolCallEvent): string {
  const { toolName, params } = event;
  if (toolName === "bash" || toolName === "shell") {
    const cmd = String(params.command ?? "");
    const curlMatch = cmd.match(/curl\s+.*?(https?:\/\/[^\s"']+)/);
    if (curlMatch) return `Querying ${new URL(curlMatch[1]).host}${new URL(curlMatch[1]).pathname}`;
    return `Running: ${cmd.slice(0, 50)}${cmd.length > 50 ? "..." : ""}`;
  }
  return `Executing: ${toolName}`;
}
```

## Declarative Enhancement (SKILL.md)

Skill developers can optionally declare streaming steps in SKILL.md metadata:

```yaml
metadata:
  openclaw:
    emoji: 🎯
    primaryEnv: ADMAPIX_API_KEY
    streaming:
      steps:
        - match: "api.admapix.com/api/data/search"
          label: "搜索广告素材"
        - match: "api.admapix.com/api/data/product"
          label: "获取应用详情"
        - match: "research/async"
          label: "深度分析"
          long_running: true
          poll_interval: 15000
      summary: true
      locale: "auto"
```

### Matching Logic

- `match` field does `includes` check against the tool call command/URL
- Hit → use `label`, total steps known (e.g., `[1/3]`)
- Miss → fallback to auto-extraction, total unknown (`[1/?]`)
- `long_running: true` → start periodic "Still working..." reminders

### Config Reading

- On first `before_tool_call` per run, read installed skills' SKILL.md metadata for `streaming` config
- Cache parsed config per skill to avoid re-reading
- Match current skill by checking which skill is active in the session

## Message Sending

### sessionKey Parsing

Format: `agent:<agentId>:<channel>:<accountId>:<peerKind>:<peerId>`

```typescript
function parseTarget(sessionKey: string): { channel: string; peerId: string; accountId: string } | null {
  const parsed = parseAgentSessionKey(sessionKey);
  if (!parsed) return null;

  const parts = parsed.rest.split(":").filter(Boolean);
  // "main" = local/webchat, no channel send needed
  if (parts[0] === "main") return null;

  return {
    channel: parts[0],          // "feishu", "telegram", "discord", etc.
    accountId: parts[1] ?? "default",
    peerId: parts.slice(-1)[0]  // last segment is always the target ID
  };
}
```

### Dual-Path Sending

```typescript
function sendProgress(
  runtime: PluginRuntime,
  ctx: HookContext,
  emit: typeof emitAgentEvent,
  message: string
) {
  // Path 1: global event bus → webchat/SSE clients
  emit({
    runId: ctx.runId,
    stream: "assistant",
    sessionKey: ctx.sessionKey,
    data: { text: message, type: "streaming_progress" }
  });

  // Path 2: native channel → standalone message
  const target = parseTarget(ctx.sessionKey);
  if (!target) return;

  const sender = runtime.channel?.[target.channel];
  const sendFn = sender?.[`sendMessage${capitalize(target.channel)}`];
  if (sendFn) {
    sendFn(target.peerId, message, { accountId: target.accountId }).catch(() => {});
  }
}
```

**Risk note**: Feishu is an extension, not core plugin-sdk. Its send function may be mounted differently on `runtime.channel`. Needs verification during implementation.

## Progress Message Format

```
⏳ [1/3] 搜索广告素材...              ← step start (declared)
⏳ [1/?] Querying api.admapix.com...   ← step start (auto-extracted)
✅ [1/3] 搜索广告素材 (2.1s)          ← step done
⏳ [2/3] 获取应用详情...              ← step start
⚠️ Still working... (18s)             ← long running warning
✅ [2/3] 获取应用详情 (21.3s)         ← step done
📊 Done: 3 steps in 28.7s            ← summary (multi-step only)
```

### Locale Support

- `"auto"` → detect from user message language or system locale
- `"zh"` → Chinese labels for built-in messages
- `"en"` → English labels
- Custom labels from SKILL.md `steps[].label` are used as-is regardless of locale

## Project Structure

```
openclaw-plugin-skill-streaming/
├── package.json
├── README.md
├── README_CN.md
├── src/
│   ├── index.ts              # Plugin entry (register + hooks)
│   ├── state.ts              # RunState management
│   ├── label.ts              # Auto label extraction (URL/command parsing)
│   ├── matcher.ts            # Declarative steps matching
│   ├── formatter.ts          # Progress message formatting (i18n)
│   ├── sender.ts             # Channel message sending (sessionKey parse + runtime call)
│   └── types.ts              # Type definitions
├── tsconfig.json
└── test/
    ├── state.test.ts
    ├── label.test.ts
    ├── matcher.test.ts
    └── formatter.test.ts
```

## Installation & Configuration

```bash
# Install
openclaw plugin install skill-streaming

# Optional global config
openclaw config set plugins.skill-streaming.enabled true
openclaw config set plugins.skill-streaming.summaryEnabled true
openclaw config set plugins.skill-streaming.locale "zh"
openclaw config set plugins.skill-streaming.longRunningMs 10000
```

Zero external dependencies. Only depends on OpenClaw Plugin SDK types.

## Release Phases

### Phase 1 (v0.1.0): OpenClaw Plugin
- Core hook-based progress injection
- Auto label extraction
- Declarative SKILL.md enhancement
- Dual-path message sending (emitAgentEvent + channel send)
- Publish to ClawHub + npm

### Phase 2 (v0.2.0+): Standalone Core
- Extract channel-agnostic logic into `skill-streaming-core` npm package
- OpenClaw plugin becomes a thin adapter over the core
- Document protocol for other frameworks to integrate

## Open Questions / Risks

1. **Feishu send function availability**: Feishu is an extension, its send function may not be on `runtime.channel.feishu`. Verify during implementation; fallback to `emitAgentEvent` only.
2. **Skill detection in hooks**: `before_tool_call` context has `sessionKey` and `toolName` but may not directly indicate which skill is active. May need to track skill activation via `session_start` or `llm_input` hooks.
3. **Message ordering**: Progress messages are sent as independent messages. Under high concurrency, they may arrive out of order on some channels. Use sequence numbers in message text as mitigation.
4. **Rate limiting**: Channels have rate limits (Feishu, Telegram, etc.). The `long_running` timer should respect per-channel limits. Default 15s interval should be safe for all channels.
