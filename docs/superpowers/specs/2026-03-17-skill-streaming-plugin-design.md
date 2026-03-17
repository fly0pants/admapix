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
Hook fires (before_tool_call / after_tool_call)
  → ctx.sessionKey parsed via parseAgentSessionKey() → extract channel + peerId + accountId
  → closure-captured api.runtime → call channel-specific send function
  → progress message delivered to user as standalone message
```

### Key Design Decision: Independent Messages (Not Card Streaming)

`onPartialReply` (which drives channel streaming cards like Feishu CardKit) only receives data from the LLM token stream. Plugin hooks cannot inject into this pipeline. `emitAgentEvent` is an internal function not exported from Plugin SDK.

**v1 approach**: Send progress as standalone messages via channel-specific send functions (`runtime.channel.telegram.sendMessageTelegram`, etc.). This works universally across all native channels.

**Webchat/SSE**: Webchat connections go through the gateway WebSocket. Progress messages for webchat sessions will be sent via a registered gateway method (see Message Sending section).

**Future v2**: Explore bridging into channel-specific streaming cards for a more polished UX.

## Skill Detection

`before_tool_call` context only has `agentId`, `sessionKey`, and `toolName` — it does NOT indicate which skill is active. We solve this by tracking skill activation in an earlier hook.

**Strategy**: Use the `llm_input` hook to detect skill activation. When the system prompt contains skill markers (SKILL.md content is injected into the prompt by OpenClaw), we record the active skill for that session. Then `before_tool_call` looks up the session to determine if a skill is running.

```typescript
// In register():
const activeSkills = new Map<string, string | null>(); // sessionKey → skillName

api.on("llm_input", (event, ctx) => {
  // event.systemPrompt contains injected skill content
  // Check for skill metadata markers (e.g., "primaryEnv:", skill-specific patterns)
  const skillName = detectSkillFromPrompt(event.systemPrompt);
  if (ctx.sessionKey) {
    activeSkills.set(ctx.sessionKey, skillName);
  }
});
```

In `before_tool_call`, check `activeSkills.get(ctx.sessionKey)`. If null, skip progress (regular chat). If set, proceed with progress injection.

**This plugin never blocks or modifies tool calls** — it only observes and sends progress messages. The `before_tool_call` handler returns void (not `{ block: true }`).

## State Machine

```typescript
type RunState = {
  sessionKey: string             // used as key (runId not available in hook ctx)
  skillName: string | null       // null = regular chat, skip progress
  steps: StepRecord[]
  currentStep: number
  startedAt: number
  lastActivityAt: number         // for TTL cleanup
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

One `RunState` per session. Created on first `before_tool_call` for a skill run, cleaned up on `agent_end`.

**TTL cleanup**: A periodic sweep (every 60s) removes RunState entries where `Date.now() - lastActivityAt > 600_000` (10 minutes), preventing memory leaks if `agent_end` is missed.

## Plugin Registration

Plugin metadata lives in `openclaw.plugin.json` (required by OpenClaw plugin system):

```json
{
  "id": "skill-streaming",
  "name": "Skill Streaming Progress",
  "version": "0.1.0",
  "description": "Auto-inject streaming progress for skill tool calls",
  "main": "dist/index.js"
}
```

The plugin exports a `register` function that receives `OpenClawPluginApi`:

```typescript
// src/index.ts
import type { OpenClawPluginApi, OpenClawPluginDefinition } from "openclaw/plugin-sdk";

const plugin: OpenClawPluginDefinition = {
  register(api: OpenClawPluginApi) {
  const runtime = api.runtime;   // closure capture — access to channel send functions
  const config = api.config;     // closure capture — access to global config
  const runStates = new Map<string, RunState>();
  const activeSkills = new Map<string, string | null>();

  // TTL cleanup: prevent memory leaks if agent_end is missed
  const cleanupInterval = setInterval(() => {
    const now = Date.now();
    for (const [key, state] of runStates) {
      if (now - state.lastActivityAt > 600_000) {
        clearAllTimers(state);
        runStates.delete(key);
      }
    }
  }, 60_000);

  // Hook 0: detect active skill from system prompt
  api.on("llm_input", (event, ctx) => {
    const skillName = detectSkillFromPrompt(event.systemPrompt);
    if (ctx.sessionKey) activeSkills.set(ctx.sessionKey, skillName);
  });

  // Hook 1: tool call starts — send progress message
  api.on("before_tool_call", (event, ctx) => {
    // event: { toolName: string, params: Record<string, unknown> }
    // ctx: { agentId?: string, sessionKey?: string, toolName: string }
    const skillName = activeSkills.get(ctx.sessionKey ?? "");
    if (!skillName) return; // not a skill run, skip

    const state = getOrCreateRunState(runStates, ctx.sessionKey!, skillName, config);
    const label = resolveLabel(event, state.skillConfig);
    const step = pushStep(state, label);

    sendProgress(runtime, ctx.sessionKey!, formatStepStart(step, state));

    if (step.longRunning) {
      step.timer = setInterval(() => {
        sendProgress(runtime, ctx.sessionKey!, formatStillWorking(step, state));
      }, step.pollInterval ?? 15_000);
    }
  });

  // Hook 2: tool call ends — send completion message
  api.on("after_tool_call", (event, ctx) => {
    // event: { toolName, params, result?, error?: string, durationMs?: number }
    const state = runStates.get(ctx.sessionKey ?? "");
    if (!state) return;

    const step = finishCurrentStep(state, event.error, event.durationMs);
    if (step.timer) clearInterval(step.timer);

    sendProgress(runtime, ctx.sessionKey!, formatStepDone(step, state));
  });

  // Hook 3: agent run ends — cleanup + optional summary
  api.on("agent_end", (event, ctx) => {
    const key = ctx.sessionKey ?? "";
    const state = runStates.get(key);
    if (!state) return;

    if (state.steps.length > 1) {
      sendProgress(runtime, key, formatSummary(state));
    }
    clearAllTimers(state);
    runStates.delete(key);
    activeSkills.delete(key);
  });
  }  // end register
};

export default plugin;
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
function extractLabel(event: PluginHookBeforeToolCallEvent): string {
  const { toolName, params } = event;
  if (toolName === "bash" || toolName === "shell") {
    const cmd = String(params.command ?? "");
    const curlMatch = cmd.match(/curl\s+.*?(https?:\/\/[^\s"']+)/);
    if (curlMatch) {
      try {
        const url = new URL(curlMatch[1]);
        return `Querying ${url.host}${url.pathname}`;
      } catch {
        return `Querying ${curlMatch[1].slice(0, 50)}`;
      }
    }
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

sessionKey format varies by dmScope configuration. Use SDK's `parseAgentSessionKey()` for base parsing, then extract channel info from the `rest` segment.

Examples:
- `agent:main:main` → webchat/local (no native channel)
- `agent:main:telegram:default:direct:123456` → Telegram DM
- `agent:main:discord:default:guild-abc:channel-def` → Discord channel
- `agent:main:feishu:default:direct:user789` → Feishu DM

```typescript
// NOTE: parseAgentSessionKey is NOT exported from plugin-sdk public surface.
// We implement our own minimal parser based on the known format:
//   agent:<agentId>:<rest...>
// where rest = "main" (webchat) or "<channel>:<accountId>:<peerKind>:<peerId>"

type SendTarget = {
  channel: string;      // "telegram", "discord", "slack", etc.
  peerId: string;       // target chat/user/channel ID
  accountId: string;    // OpenClaw account ID for this channel
};

function parseSessionKey(sessionKey: string): { agentId: string; rest: string } | null {
  const raw = (sessionKey ?? "").trim();
  if (!raw) return null;
  const parts = raw.split(":").filter(Boolean);
  if (parts.length < 3 || parts[0] !== "agent") return null;
  return { agentId: parts[1], rest: parts.slice(2).join(":") };
}

function parseTarget(sessionKey: string): SendTarget | null {
  const parsed = parseSessionKey(sessionKey);
  if (!parsed) return null;

  const parts = parsed.rest.split(":").filter(Boolean);
  // "main" alone means webchat/local — handled via gateway, not channel send
  if (parts.length <= 1 && parts[0] === "main") return null;

  const channel = parts[0];
  // Known channels in PluginRuntime.channel:
  // telegram, discord, slack, whatsapp, signal, imessage, line
  // Feishu is an extension — may or may not be on runtime.channel
  const accountId = parts[1] ?? "default";
  const peerId = parts[parts.length - 1]; // last segment is always target ID

  return { channel, peerId, accountId };
}
```

### Channel Send with Explicit Adapter Map

Instead of dynamic function name construction, use an explicit adapter map for type safety and per-channel signature handling:

```typescript
type ChannelSender = (
  runtime: PluginRuntime,
  target: SendTarget,
  message: string
) => Promise<unknown>;  // channel send functions return channel-specific result types

// Explicit adapter per supported channel
const channelAdapters: Record<string, ChannelSender> = {
  telegram: async (rt, t, msg) => {
    await rt.channel.telegram.sendMessageTelegram(t.peerId, msg, {
      accountId: t.accountId,
      textMode: "markdown",
    });
  },
  discord: async (rt, t, msg) => {
    await rt.channel.discord.sendMessageDiscord(t.peerId, msg, {
      accountId: t.accountId,
    });
  },
  slack: async (rt, t, msg) => {
    await rt.channel.slack.sendMessageSlack(t.peerId, msg, {
      accountId: t.accountId,
    });
  },
  whatsapp: async (rt, t, msg) => {
    await rt.channel.whatsapp.sendMessageWhatsApp(t.peerId, msg, {
      accountId: t.accountId,
    });
  },
  signal: async (rt, t, msg) => {
    await rt.channel.signal.sendMessageSignal(t.peerId, msg, {
      accountId: t.accountId,
    });
  },
  line: async (rt, t, msg) => {
    await rt.channel.line.sendMessageLine(t.peerId, msg, {
      accountId: t.accountId,
    });
  },
  // Feishu: extension-based, attempt dynamic access with fallback
  feishu: async (rt, t, msg) => {
    const feishuSend = (rt.channel as any)?.feishu?.sendMessageFeishu;
    if (feishuSend) {
      await feishuSend(t.peerId, msg, { accountId: t.accountId });
    }
    // If feishu send not available, silently skip (logged as warning)
  },
};

function sendProgress(
  runtime: PluginRuntime,
  sessionKey: string,
  message: string
) {
  const target = parseTarget(sessionKey);
  if (!target) return; // webchat/local — no standalone message needed for v1

  const adapter = channelAdapters[target.channel];
  if (adapter) {
    adapter(runtime, target, message).catch(() => {
      // Silently swallow send errors — progress is best-effort
    });
  }
}
```

### Webchat/SSE Support

For webchat sessions (sessionKey = `agent:main:main`), the plugin registers a gateway method during setup. This allows pushing progress events through the gateway WebSocket to connected browser clients:

```typescript
// In register():
api.registerGatewayMethod("skill-streaming.progress", (opts) => {
  // Push progress event to the specific webchat session
  opts.context.nodeSendToSession(
    opts.params.sessionKey as string,
    "skill-streaming:progress",
    { text: opts.params.message }
  );
  opts.respond(true);
});
```

For v1, webchat progress is a stretch goal — native channel support is the priority.

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
├── openclaw.plugin.json      # Plugin manifest (id, name, version, main)
├── package.json
├── tsconfig.json
├── README.md
├── README_CN.md
├── src/
│   ├── index.ts              # Plugin entry (export register function)
│   ├── state.ts              # RunState management + TTL cleanup
│   ├── label.ts              # Auto label extraction (URL/command parsing)
│   ├── matcher.ts            # Declarative steps matching against SKILL.md config
│   ├── formatter.ts          # Progress message formatting (i18n)
│   ├── sender.ts             # Channel adapter map + sendProgress
│   └── types.ts              # Type definitions
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
- Core hook-based progress injection (before_tool_call, after_tool_call, agent_end)
- Skill detection via llm_input hook
- Auto label extraction from tool call commands
- Declarative SKILL.md enhancement (optional)
- Channel adapter map for native channels (Telegram, Discord, Slack, WhatsApp, Signal, Line)
- Feishu support (best-effort, depends on extension availability)
- TTL-based state cleanup
- Publish to ClawHub + npm

### Phase 2 (v0.2.0+): Enhancements
- Webchat/SSE support via gateway method
- Extract channel-agnostic logic (state, formatter, label, matcher) into `skill-streaming-core` npm package
- OpenClaw plugin becomes a thin adapter over the core
- Document protocol for other frameworks to integrate
- Evaluate whether standalone core has enough reusable value (state machine + formatter + label extractor)

## Resolved Design Decisions

1. **Skill detection**: Solved via `llm_input` hook — detect skill markers in system prompt, store per session. `before_tool_call` looks up session to decide whether to inject progress.
2. **No `emitAgentEvent` in Plugin SDK**: Confirmed not exported. v1 uses channel-specific send functions exclusively. Webchat/SSE deferred to v2 via gateway method.
3. **Hook context limitations**: `before_tool_call` ctx has no `runId`. Use `sessionKey` as state key instead.
4. **`parseAgentSessionKey` not in public SDK**: Implement our own minimal parser (`parseSessionKey`). The format is stable (`agent:<agentId>:<rest>`), and the parser is trivial (~5 lines).
5. **Plugin export form**: Use `OpenClawPluginDefinition` object with `register` method, `export default`. This matches SDK's expected module shape.
6. **Plugin does not block tool calls**: All hook handlers return void. No modification to tool call params or execution.

## Open Questions / Risks

1. **Feishu send function availability**: Feishu is an extension, not core plugin-sdk. `runtime.channel.feishu` may not exist. Adapter uses dynamic access with silent fallback.
2. **Message ordering**: Progress messages are standalone. Under high concurrency, they may arrive out of order. Mitigated by step number in message text (`[1/3]`, `[2/3]`).
3. **Rate limiting**: Channels have rate limits. Default `long_running` poll interval of 15s is conservative. Per-channel rate limit awareness may be needed for very chatty skills.
4. **Skill detection accuracy**: `llm_input` prompt may not always contain clear skill markers. False positives (progress on non-skill tool calls) are low-risk but annoying. May need refinement based on real-world testing.
5. **sessionKey format evolution**: sessionKey format varies by dmScope and may change across OpenClaw versions. Rely on SDK's `parseAgentSessionKey()` rather than manual parsing to stay compatible.
