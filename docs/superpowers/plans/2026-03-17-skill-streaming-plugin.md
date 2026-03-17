# Skill Streaming Plugin Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an OpenClaw plugin that auto-injects streaming progress messages during skill tool call execution.

**Architecture:** Plugin registers 4 hooks (llm_input, before_tool_call, after_tool_call, agent_end). Skill detection via llm_input prompt inspection. Progress sent as standalone channel messages via explicit adapter map. State machine tracks steps per session with TTL cleanup.

**Tech Stack:** TypeScript, OpenClaw Plugin SDK (types only), vitest for testing

**Spec:** `docs/superpowers/specs/2026-03-17-skill-streaming-plugin-design.md`

**Project directory:** `~/openclaw-plugin-skill-streaming/`

---

## File Map

| File | Responsibility |
|------|---------------|
| `openclaw.plugin.json` | Plugin manifest for OpenClaw loader |
| `package.json` | Dependencies, scripts, npm metadata |
| `tsconfig.json` | TypeScript config |
| `src/types.ts` | All type definitions (RunState, StepRecord, SendTarget, StreamingConfig) |
| `src/label.ts` | Extract human-readable labels from tool call commands |
| `src/state.ts` | RunState creation, step push/finish, TTL cleanup |
| `src/matcher.ts` | Match tool calls against SKILL.md streaming declarations |
| `src/formatter.ts` | Format progress messages with i18n support |
| `src/sender.ts` | sessionKey parsing, channel adapter map, sendProgress |
| `src/config-loader.ts` | Load StreamingConfig from installed SKILL.md metadata |
| `src/index.ts` | Plugin entry — wire hooks to modules |
| `test/label.test.ts` | Tests for label extraction |
| `test/state.test.ts` | Tests for state machine |
| `test/matcher.test.ts` | Tests for declarative matching |
| `test/formatter.test.ts` | Tests for message formatting |
| `test/sender.test.ts` | Tests for sessionKey parsing |
| `test/config-loader.test.ts` | Tests for SKILL.md config parsing |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `openclaw.plugin.json`
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `src/types.ts`

- [ ] **Step 1: Create project directory**

```bash
mkdir -p ~/openclaw-plugin-skill-streaming/src ~/openclaw-plugin-skill-streaming/test
cd ~/openclaw-plugin-skill-streaming
```

- [ ] **Step 2: Create openclaw.plugin.json**

```json
{
  "id": "skill-streaming",
  "name": "Skill Streaming Progress",
  "version": "0.1.0",
  "description": "Auto-inject streaming progress for skill tool calls",
  "main": "dist/index.js"
}
```

- [ ] **Step 3: Create package.json**

```json
{
  "name": "openclaw-plugin-skill-streaming",
  "version": "0.1.0",
  "description": "Auto-inject streaming progress for OpenClaw skill tool calls",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": ["dist", "openclaw.plugin.json", "README.md", "README_CN.md"],
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "test:watch": "vitest",
    "prepublishOnly": "npm run build"
  },
  "keywords": ["openclaw", "plugin", "streaming", "progress", "skill"],
  "license": "MIT",
  "devDependencies": {
    "typescript": "^5.7.0",
    "vitest": "^3.0.0"
  }
}
```

- [ ] **Step 4: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "declaration": true,
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"],
  "exclude": ["test", "dist"]
}
```

- [ ] **Step 5: Create src/types.ts with all type definitions**

```typescript
// ---- OpenClaw SDK types (subset we depend on) ----

export type PluginHookBeforeToolCallEvent = {
  toolName: string;
  params: Record<string, unknown>;
};

export type PluginHookAfterToolCallEvent = {
  toolName: string;
  params: Record<string, unknown>;
  result?: unknown;
  error?: string;
  durationMs?: number;
};

export type PluginHookToolContext = {
  agentId?: string;
  sessionKey?: string;
  toolName: string;
};

export type PluginHookLlmInputEvent = {
  runId: string;
  sessionId: string;
  provider: string;
  model: string;
  systemPrompt?: string;
  prompt: string;
  historyMessages: unknown[];
  imagesCount: number;
};

export type PluginHookAgentContext = {
  sessionKey?: string;
};

// ---- Plugin's own types ----

export type StepRecord = {
  index: number;
  label: string;
  startedAt: number;
  finishedAt?: number;
  status: "running" | "done" | "error";
  longRunning?: boolean;
  pollInterval?: number;
  timer?: ReturnType<typeof setInterval>;
};

export type RunState = {
  sessionKey: string;
  skillName: string | null;    // null = regular chat, skip progress
  totalSteps: number | null;   // from declarative config, null = unknown
  steps: StepRecord[];
  currentStep: number;
  startedAt: number;
  lastActivityAt: number;
  skillConfig?: StreamingConfig;
};

export type StreamingStepDecl = {
  match: string;
  label: string;
  long_running?: boolean;
  poll_interval?: number;
};

export type StreamingConfig = {
  steps?: StreamingStepDecl[];
  summary?: boolean;
  locale?: string;
};

export type SendTarget = {
  channel: string;
  peerId: string;
  accountId: string;
};

export type Locale = "en" | "zh" | "auto";
```

- [ ] **Step 6: Install dependencies and verify build**

```bash
cd ~/openclaw-plugin-skill-streaming
npm install
npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git init
git add -A
git commit -m "chore: scaffold project with types, config, and dependencies"
```

---

### Task 2: Label Extraction (TDD)

**Files:**
- Create: `src/label.ts`
- Create: `test/label.test.ts`

- [ ] **Step 1: Write failing tests for label extraction**

File: `test/label.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import { extractLabel } from "../src/label.js";

describe("extractLabel", () => {
  it("extracts domain+path from curl command", () => {
    const result = extractLabel({
      toolName: "bash",
      params: { command: 'curl -s -X POST "https://api.admapix.com/api/data/search" -H "Content-Type: application/json"' },
    });
    expect(result).toBe("Querying api.admapix.com/api/data/search");
  });

  it("handles curl with single-quoted URL", () => {
    const result = extractLabel({
      toolName: "bash",
      params: { command: "curl -s 'https://example.com/api/v1/users'" },
    });
    expect(result).toBe("Querying example.com/api/v1/users");
  });

  it("falls back to truncated command for non-curl bash", () => {
    const result = extractLabel({
      toolName: "bash",
      params: { command: "python analyze.py --input data.json --output result.json --verbose" },
    });
    expect(result).toBe("Running: python analyze.py --input data.json --output ...");
  });

  it("handles curl with query parameters", () => {
    const result = extractLabel({
      toolName: "bash",
      params: { command: 'curl "https://api.example.com/search?q=test&page=1"' },
    });
    expect(result).toBe("Querying api.example.com/search");
  });

  it("handles short bash commands without truncation", () => {
    const result = extractLabel({
      toolName: "bash",
      params: { command: "ls -la" },
    });
    expect(result).toBe("Running: ls -la");
  });

  it("returns tool name for non-bash tools", () => {
    const result = extractLabel({
      toolName: "web_search",
      params: { query: "test" },
    });
    expect(result).toBe("Executing: web_search");
  });

  it("handles malformed URL in curl gracefully", () => {
    const result = extractLabel({
      toolName: "bash",
      params: { command: "curl http://not a valid url here" },
    });
    expect(result).toMatch(/^(Querying|Running:)/);
  });

  it("handles missing command param", () => {
    const result = extractLabel({
      toolName: "bash",
      params: {},
    });
    expect(result).toBe("Running: ");
  });

  it("handles shell tool name", () => {
    const result = extractLabel({
      toolName: "shell",
      params: { command: "echo hello" },
    });
    expect(result).toBe("Running: echo hello");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/openclaw-plugin-skill-streaming
npx vitest run test/label.test.ts
```
Expected: FAIL — `extractLabel` not found.

- [ ] **Step 3: Implement label.ts**

File: `src/label.ts`
```typescript
import type { PluginHookBeforeToolCallEvent } from "./types.js";

export function extractLabel(event: PluginHookBeforeToolCallEvent): string {
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
    const maxLen = 50;
    if (cmd.length > maxLen) {
      return `Running: ${cmd.slice(0, maxLen)}...`;
    }
    return `Running: ${cmd}`;
  }

  return `Executing: ${toolName}`;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run test/label.test.ts
```
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/label.ts test/label.test.ts
git commit -m "feat: add auto label extraction from tool call commands"
```

---

### Task 3: State Machine (TDD)

**Files:**
- Create: `src/state.ts`
- Create: `test/state.test.ts`

- [ ] **Step 1: Write failing tests for state machine**

File: `test/state.test.ts`
```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createRunState,
  pushStep,
  finishCurrentStep,
  clearAllTimers,
  createCleanupInterval,
} from "../src/state.js";

describe("createRunState", () => {
  it("creates a new RunState with correct defaults", () => {
    const state = createRunState("session:123", "admapix");
    expect(state.sessionKey).toBe("session:123");
    expect(state.skillName).toBe("admapix");
    expect(state.steps).toEqual([]);
    expect(state.currentStep).toBe(0);
    expect(state.startedAt).toBeGreaterThan(0);
    expect(state.lastActivityAt).toBeGreaterThan(0);
  });
});

describe("pushStep", () => {
  it("adds a step and increments currentStep", () => {
    const state = createRunState("s1", "skill1");
    const step = pushStep(state, "Querying API");
    expect(step.index).toBe(1);
    expect(step.label).toBe("Querying API");
    expect(step.status).toBe("running");
    expect(state.currentStep).toBe(1);
    expect(state.steps).toHaveLength(1);
  });

  it("adds multiple steps sequentially", () => {
    const state = createRunState("s1", "skill1");
    pushStep(state, "Step 1");
    const step2 = pushStep(state, "Step 2");
    expect(step2.index).toBe(2);
    expect(state.currentStep).toBe(2);
    expect(state.steps).toHaveLength(2);
  });

  it("supports longRunning flag", () => {
    const state = createRunState("s1", "skill1");
    const step = pushStep(state, "Deep analysis", { longRunning: true, pollInterval: 20000 });
    expect(step.longRunning).toBe(true);
    expect(step.pollInterval).toBe(20000);
  });
});

describe("finishCurrentStep", () => {
  it("marks current step as done with duration", () => {
    const state = createRunState("s1", "skill1");
    pushStep(state, "Test step");
    const step = finishCurrentStep(state, undefined);
    expect(step.status).toBe("done");
    expect(step.finishedAt).toBeGreaterThan(0);
  });

  it("marks step as error when error is provided", () => {
    const state = createRunState("s1", "skill1");
    pushStep(state, "Failing step");
    const step = finishCurrentStep(state, "timeout");
    expect(step.status).toBe("error");
  });

  it("returns last step even if no steps exist (defensive)", () => {
    const state = createRunState("s1", "skill1");
    // no steps pushed
    const step = finishCurrentStep(state, undefined);
    expect(step).toBeDefined();
    expect(step.status).toBe("done");
  });
});

describe("clearAllTimers", () => {
  it("clears all step timers", () => {
    vi.useFakeTimers();
    const state = createRunState("s1", "skill1");
    const step = pushStep(state, "Test");
    step.timer = setInterval(() => {}, 1000);
    clearAllTimers(state);
    expect(step.timer).toBeUndefined();
    vi.useRealTimers();
  });
});

describe("createCleanupInterval", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("removes stale entries after TTL", () => {
    const map = new Map();
    const state = createRunState("stale", "skill");
    state.lastActivityAt = Date.now() - 700_000; // 11+ min ago
    map.set("stale", state);

    const cleanup = createCleanupInterval(map, 60_000, 600_000);
    vi.advanceTimersByTime(60_000);
    expect(map.has("stale")).toBe(false);
    clearInterval(cleanup);
  });

  it("keeps fresh entries", () => {
    const map = new Map();
    const state = createRunState("fresh", "skill");
    map.set("fresh", state);

    const cleanup = createCleanupInterval(map, 60_000, 600_000);
    vi.advanceTimersByTime(60_000);
    expect(map.has("fresh")).toBe(true);
    clearInterval(cleanup);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run test/state.test.ts
```
Expected: FAIL.

- [ ] **Step 3: Implement state.ts**

File: `src/state.ts`
```typescript
import type { RunState, StepRecord, StreamingConfig } from "./types.js";

export function createRunState(
  sessionKey: string,
  skillName: string | null,
  skillConfig?: StreamingConfig,
): RunState {
  const now = Date.now();
  return {
    sessionKey,
    skillName,
    totalSteps: skillConfig?.steps?.length ?? null,
    steps: [],
    currentStep: 0,
    startedAt: now,
    lastActivityAt: now,
    skillConfig,
  };
}

export function pushStep(
  state: RunState,
  label: string,
  opts?: { longRunning?: boolean; pollInterval?: number },
): StepRecord {
  state.currentStep += 1;
  state.lastActivityAt = Date.now();
  const step: StepRecord = {
    index: state.currentStep,
    label,
    startedAt: Date.now(),
    status: "running",
    longRunning: opts?.longRunning,
    pollInterval: opts?.pollInterval,
  };
  state.steps.push(step);
  return step;
}

export function finishCurrentStep(
  state: RunState,
  error: string | undefined,
): StepRecord {
  state.lastActivityAt = Date.now();
  const step = state.steps[state.steps.length - 1];
  if (!step) {
    // Defensive: create a phantom step if none exists
    const phantom: StepRecord = {
      index: 0,
      label: "unknown",
      startedAt: Date.now(),
      finishedAt: Date.now(),
      status: error ? "error" : "done",
    };
    return phantom;
  }
  step.finishedAt = Date.now();
  step.status = error ? "error" : "done";
  return step;
}

export function clearAllTimers(state: RunState): void {
  for (const step of state.steps) {
    if (step.timer) {
      clearInterval(step.timer);
      step.timer = undefined;
    }
  }
}

export function createCleanupInterval(
  map: Map<string, RunState>,
  intervalMs: number,
  ttlMs: number,
): ReturnType<typeof setInterval> {
  return setInterval(() => {
    const now = Date.now();
    for (const [key, state] of map) {
      if (now - state.lastActivityAt > ttlMs) {
        clearAllTimers(state);
        map.delete(key);
      }
    }
  }, intervalMs);
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run test/state.test.ts
```
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/state.ts test/state.test.ts
git commit -m "feat: add RunState management with TTL cleanup"
```

---

### Task 4: Declarative Matcher (TDD)

**Files:**
- Create: `src/matcher.ts`
- Create: `test/matcher.test.ts`

- [ ] **Step 1: Write failing tests**

File: `test/matcher.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import { matchStep, detectSkillFromPrompt } from "../src/matcher.js";
import type { StreamingConfig, PluginHookBeforeToolCallEvent } from "../src/types.js";

describe("matchStep", () => {
  const config: StreamingConfig = {
    steps: [
      { match: "api.admapix.com/api/data/search", label: "搜索广告素材" },
      { match: "api.admapix.com/api/data/product", label: "获取应用详情" },
      { match: "research/async", label: "深度分析", long_running: true, poll_interval: 15000 },
    ],
  };

  it("matches a declared step by URL includes", () => {
    const event: PluginHookBeforeToolCallEvent = {
      toolName: "bash",
      params: { command: 'curl -s -X POST "https://api.admapix.com/api/data/search"' },
    };
    const result = matchStep(event, config);
    expect(result).not.toBeNull();
    expect(result!.label).toBe("搜索广告素材");
    expect(result!.totalSteps).toBe(3);
  });

  it("matches long_running step", () => {
    const event: PluginHookBeforeToolCallEvent = {
      toolName: "bash",
      params: { command: 'curl "http://47.236.184.176:8100/research/async"' },
    };
    const result = matchStep(event, config);
    expect(result!.label).toBe("深度分析");
    expect(result!.longRunning).toBe(true);
    expect(result!.pollInterval).toBe(15000);
  });

  it("returns null when no match", () => {
    const event: PluginHookBeforeToolCallEvent = {
      toolName: "bash",
      params: { command: "echo hello" },
    };
    const result = matchStep(event, config);
    expect(result).toBeNull();
  });

  it("returns null when config has no steps", () => {
    const result = matchStep(
      { toolName: "bash", params: { command: "curl https://example.com" } },
      {},
    );
    expect(result).toBeNull();
  });

  it("returns null when config is undefined", () => {
    const result = matchStep(
      { toolName: "bash", params: { command: "curl https://example.com" } },
      undefined,
    );
    expect(result).toBeNull();
  });
});

describe("detectSkillFromPrompt", () => {
  it("detects skill name from prompt with primaryEnv marker", () => {
    const prompt = `You are an assistant.\n\n# Skill: admapix\nprimaryEnv: ADMAPIX_API_KEY\n...`;
    expect(detectSkillFromPrompt(prompt)).toBe("admapix");
  });

  it("detects skill name from SKILL.md header", () => {
    const prompt = `Some system prompt.\n---\nname: weather\ndescription: Get weather info\n---`;
    expect(detectSkillFromPrompt(prompt)).toBe("weather");
  });

  it("returns null for prompts without skill markers", () => {
    expect(detectSkillFromPrompt("You are a helpful assistant.")).toBeNull();
  });

  it("returns null for undefined prompt", () => {
    expect(detectSkillFromPrompt(undefined)).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run test/matcher.test.ts
```
Expected: FAIL.

- [ ] **Step 3: Implement matcher.ts**

File: `src/matcher.ts`
```typescript
import type { PluginHookBeforeToolCallEvent, StreamingConfig } from "./types.js";

export type MatchResult = {
  label: string;
  totalSteps: number;
  longRunning?: boolean;
  pollInterval?: number;
};

export function matchStep(
  event: PluginHookBeforeToolCallEvent,
  config: StreamingConfig | undefined,
): MatchResult | null {
  if (!config?.steps?.length) return null;

  const cmd = String(event.params.command ?? event.params.url ?? "");

  for (const decl of config.steps) {
    if (cmd.includes(decl.match)) {
      return {
        label: decl.label,
        totalSteps: config.steps.length,
        longRunning: decl.long_running,
        pollInterval: decl.poll_interval,
      };
    }
  }

  return null;
}

export function detectSkillFromPrompt(prompt: string | undefined): string | null {
  if (!prompt) return null;

  // Pattern 1: "# Skill: <name>" header
  const skillHeader = prompt.match(/^#\s*Skill:\s*(\S+)/m);
  if (skillHeader) return skillHeader[1].toLowerCase();

  // Pattern 2: YAML frontmatter "name: <name>"
  const yamlName = prompt.match(/^---[\s\S]*?^name:\s*(\S+)[\s\S]*?^---/m);
  if (yamlName) return yamlName[1].toLowerCase();

  // Pattern 3: primaryEnv marker (skill metadata injected by OpenClaw)
  const primaryEnv = prompt.match(/primaryEnv:\s*\S+/);
  if (primaryEnv) {
    // Try to find a skill name nearby
    const nameNearby = prompt.match(/(?:skill|name)[\s:]+(\w[\w-]*)/i);
    if (nameNearby) return nameNearby[1].toLowerCase();
    return "unknown-skill"; // skill detected but name unclear
  }

  return null;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run test/matcher.test.ts
```
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/matcher.ts test/matcher.test.ts
git commit -m "feat: add declarative step matching and skill detection"
```

---

### Task 5: Formatter (TDD)

**Files:**
- Create: `src/formatter.ts`
- Create: `test/formatter.test.ts`

- [ ] **Step 1: Write failing tests**

File: `test/formatter.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import { formatStepStart, formatStepDone, formatStillWorking, formatSummary } from "../src/formatter.js";
import type { RunState, StepRecord } from "../src/types.js";

function makeState(overrides?: Partial<RunState>): RunState {
  return {
    sessionKey: "s1",
    skillName: "test-skill",
    steps: [],
    currentStep: 0,
    startedAt: Date.now(),
    lastActivityAt: Date.now(),
    ...overrides,
  };
}

function makeStep(overrides?: Partial<StepRecord>): StepRecord {
  return {
    index: 1,
    label: "Test step",
    startedAt: Date.now(),
    status: "running",
    ...overrides,
  };
}

describe("formatStepStart", () => {
  it("formats with known total steps", () => {
    const result = formatStepStart(makeStep({ index: 2, label: "搜索广告素材" }), 3, "en");
    expect(result).toContain("[2/3]");
    expect(result).toContain("搜索广告素材");
  });

  it("formats with unknown total steps", () => {
    const result = formatStepStart(makeStep({ index: 1, label: "Querying api.com" }), null, "en");
    expect(result).toContain("[1/?]");
  });

  it("uses Chinese prefix for zh locale", () => {
    const result = formatStepStart(makeStep(), null, "zh");
    expect(result).toMatch(/^⏳/);
  });
});

describe("formatStepDone", () => {
  it("formats with duration", () => {
    const step = makeStep({ index: 1, status: "done", finishedAt: Date.now() });
    const result = formatStepDone(step, 3, 2100, "en");
    expect(result).toContain("[1/3]");
    expect(result).toContain("2.1s");
  });

  it("formats error step", () => {
    const step = makeStep({ index: 1, status: "error" });
    const result = formatStepDone(step, null, 500, "en");
    expect(result).toContain("0.5s");
  });
});

describe("formatStillWorking", () => {
  it("shows elapsed time", () => {
    const step = makeStep({ startedAt: Date.now() - 18000 });
    const result = formatStillWorking(step, "en");
    expect(result).toMatch(/Still working/);
    expect(result).toMatch(/1[78](\.\d)?s/); // ~18s
  });

  it("uses Chinese for zh locale", () => {
    const step = makeStep({ startedAt: Date.now() - 5000 });
    const result = formatStillWorking(step, "zh");
    expect(result).toMatch(/仍在执行/);
  });
});

describe("formatSummary", () => {
  it("formats multi-step summary", () => {
    const state = makeState({
      startedAt: Date.now() - 28700,
      steps: [
        makeStep({ index: 1, status: "done" }),
        makeStep({ index: 2, status: "done" }),
        makeStep({ index: 3, status: "done" }),
      ],
    });
    const result = formatSummary(state, "en");
    expect(result).toContain("3 steps");
    expect(result).toMatch(/2[89](\.\d)?s/);
  });

  it("uses Chinese for zh locale", () => {
    const state = makeState({
      startedAt: Date.now() - 5000,
      steps: [makeStep(), makeStep()],
    });
    const result = formatSummary(state, "zh");
    expect(result).toMatch(/完成.*2.*步/);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run test/formatter.test.ts
```
Expected: FAIL.

- [ ] **Step 3: Implement formatter.ts**

File: `src/formatter.ts`
```typescript
import type { RunState, StepRecord, Locale } from "./types.js";

function fmtDuration(ms: number): string {
  return (ms / 1000).toFixed(1) + "s";
}

function stepPrefix(index: number, total: number | null): string {
  return total ? `[${index}/${total}]` : `[${index}/?]`;
}

export function formatStepStart(
  step: StepRecord,
  totalSteps: number | null,
  locale: Locale,
): string {
  return `⏳ ${stepPrefix(step.index, totalSteps)} ${step.label}...`;
}

export function formatStepDone(
  step: StepRecord,
  totalSteps: number | null,
  durationMs: number | undefined,
  locale: Locale,
): string {
  const icon = step.status === "error" ? "❌" : "✅";
  const dur = durationMs != null ? ` (${fmtDuration(durationMs)})` : "";
  return `${icon} ${stepPrefix(step.index, totalSteps)} ${step.label}${dur}`;
}

export function formatStillWorking(step: StepRecord, locale: Locale): string {
  const elapsed = fmtDuration(Date.now() - step.startedAt);
  if (locale === "zh") {
    return `⚠️ 仍在执行 ${step.label}... (${elapsed})`;
  }
  return `⚠️ Still working on ${step.label}... (${elapsed})`;
}

export function formatSummary(state: RunState, locale: Locale): string {
  const elapsed = fmtDuration(Date.now() - state.startedAt);
  const count = state.steps.length;
  if (locale === "zh") {
    return `📊 完成: ${count} 步, 耗时 ${elapsed}`;
  }
  return `📊 Done: ${count} steps in ${elapsed}`;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run test/formatter.test.ts
```
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/formatter.ts test/formatter.test.ts
git commit -m "feat: add progress message formatter with i18n"
```

---

### Task 6: Sender (sessionKey Parsing + Channel Adapters) (TDD)

**Files:**
- Create: `src/sender.ts`
- Create: `test/sender.test.ts`

- [ ] **Step 1: Write failing tests for sessionKey parsing**

File: `test/sender.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import { parseSessionKey, parseTarget } from "../src/sender.js";

describe("parseSessionKey", () => {
  it("parses standard session key", () => {
    const result = parseSessionKey("agent:main:telegram:default:direct:123456");
    expect(result).toEqual({ agentId: "main", rest: "telegram:default:direct:123456" });
  });

  it("parses webchat session key", () => {
    const result = parseSessionKey("agent:main:main");
    expect(result).toEqual({ agentId: "main", rest: "main" });
  });

  it("returns null for empty string", () => {
    expect(parseSessionKey("")).toBeNull();
  });

  it("returns null for non-agent prefix", () => {
    expect(parseSessionKey("cron:daily:task")).toBeNull();
  });

  it("returns null for too few parts", () => {
    expect(parseSessionKey("agent:main")).toBeNull();
  });
});

describe("parseTarget", () => {
  it("extracts Telegram DM target", () => {
    const result = parseTarget("agent:main:telegram:default:direct:123456");
    expect(result).toEqual({ channel: "telegram", accountId: "default", peerId: "123456" });
  });

  it("extracts Discord channel target", () => {
    const result = parseTarget("agent:main:discord:default:guild-abc:channel-def");
    expect(result).toEqual({ channel: "discord", accountId: "default", peerId: "channel-def" });
  });

  it("extracts Feishu DM target", () => {
    const result = parseTarget("agent:main:feishu:default:direct:user789");
    expect(result).toEqual({ channel: "feishu", accountId: "default", peerId: "user789" });
  });

  it("returns null for webchat session (main)", () => {
    expect(parseTarget("agent:main:main")).toBeNull();
  });

  it("returns null for empty/malformed key", () => {
    expect(parseTarget("")).toBeNull();
    expect(parseTarget("not-a-session-key")).toBeNull();
  });

  it("defaults accountId to 'default' when missing", () => {
    // per-peer scope without account: agent:main:telegram:direct:123
    const result = parseTarget("agent:main:telegram:direct:123");
    expect(result).toEqual({ channel: "telegram", accountId: "direct", peerId: "123" });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run test/sender.test.ts
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement sender.ts**

File: `src/sender.ts`
```typescript
import type { SendTarget } from "./types.js";

export function parseSessionKey(sessionKey: string): { agentId: string; rest: string } | null {
  const raw = (sessionKey ?? "").trim();
  if (!raw) return null;
  const parts = raw.split(":").filter(Boolean);
  if (parts.length < 3 || parts[0] !== "agent") return null;
  return { agentId: parts[1], rest: parts.slice(2).join(":") };
}

export function parseTarget(sessionKey: string): SendTarget | null {
  const parsed = parseSessionKey(sessionKey);
  if (!parsed) return null;

  const parts = parsed.rest.split(":").filter(Boolean);
  if (parts.length <= 1 && parts[0] === "main") return null;

  return {
    channel: parts[0],
    accountId: parts[1] ?? "default",
    peerId: parts[parts.length - 1],
  };
}

type ChannelSender = (runtime: any, target: SendTarget, message: string) => Promise<unknown>;

const channelAdapters: Record<string, ChannelSender> = {
  telegram: (rt, t, msg) =>
    rt.channel.telegram.sendMessageTelegram(t.peerId, msg, {
      accountId: t.accountId,
      textMode: "markdown",
    }),
  discord: (rt, t, msg) =>
    rt.channel.discord.sendMessageDiscord(t.peerId, msg, {
      accountId: t.accountId,
    }),
  slack: (rt, t, msg) =>
    rt.channel.slack.sendMessageSlack(t.peerId, msg, {
      accountId: t.accountId,
    }),
  whatsapp: (rt, t, msg) =>
    rt.channel.whatsapp.sendMessageWhatsApp(t.peerId, msg, {
      accountId: t.accountId,
    }),
  signal: (rt, t, msg) =>
    rt.channel.signal.sendMessageSignal(t.peerId, msg, {
      accountId: t.accountId,
    }),
  line: (rt, t, msg) =>
    rt.channel.line.sendMessageLine(t.peerId, msg, {
      accountId: t.accountId,
    }),
  feishu: (rt, t, msg) => {
    const fn = rt.channel?.feishu?.sendMessageFeishu;
    return fn ? fn(t.peerId, msg, { accountId: t.accountId }) : Promise.resolve();
  },
};

export function sendProgress(runtime: any, sessionKey: string, message: string): void {
  const target = parseTarget(sessionKey);
  if (!target) return;

  const adapter = channelAdapters[target.channel];
  if (adapter) {
    adapter(runtime, target, message).catch(() => {
      // Best-effort: silently swallow send errors
    });
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run test/sender.test.ts
```
Expected: All tests PASS.

- [ ] **Step 5: Verify build**

```bash
npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add src/sender.ts test/sender.test.ts
git commit -m "feat: add channel adapter map and sendProgress with sessionKey parsing"
```

---

### Task 7: SKILL.md Config Loader (TDD)

**Files:**
- Create: `src/config-loader.ts`
- Create: `test/config-loader.test.ts`

This module reads the `streaming` config from a skill's SKILL.md metadata YAML frontmatter. It parses the YAML header and extracts the `StreamingConfig` if declared.

- [ ] **Step 1: Write failing tests**

File: `test/config-loader.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import { parseStreamingConfig } from "../src/config-loader.js";

describe("parseStreamingConfig", () => {
  it("extracts streaming config from SKILL.md frontmatter", () => {
    const content = `---
name: admapix
description: Ad creative search
metadata:
  openclaw:
    emoji: "\uD83C\uDFAF"
    primaryEnv: ADMAPIX_API_KEY
    streaming:
      steps:
        - match: "api.admapix.com/api/data/search"
          label: "搜索广告素材"
        - match: "research/async"
          label: "深度分析"
          long_running: true
          poll_interval: 15000
      summary: true
      locale: auto
---
# Admapix Skill
...`;
    const config = parseStreamingConfig(content);
    expect(config).not.toBeNull();
    expect(config!.steps).toHaveLength(2);
    expect(config!.steps![0].match).toBe("api.admapix.com/api/data/search");
    expect(config!.steps![0].label).toBe("搜索广告素材");
    expect(config!.steps![1].long_running).toBe(true);
    expect(config!.summary).toBe(true);
  });

  it("returns null when no streaming config", () => {
    const content = `---
name: weather
description: Get weather
metadata:
  openclaw:
    emoji: "\u2600\uFE0F"
---
# Weather`;
    expect(parseStreamingConfig(content)).toBeNull();
  });

  it("returns null for content without frontmatter", () => {
    expect(parseStreamingConfig("# Just a markdown file")).toBeNull();
  });

  it("returns null for empty content", () => {
    expect(parseStreamingConfig("")).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run test/config-loader.test.ts
```
Expected: FAIL.

- [ ] **Step 3: Implement config-loader.ts**

File: `src/config-loader.ts`
```typescript
import type { StreamingConfig, StreamingStepDecl } from "./types.js";

/**
 * Parse streaming config from SKILL.md content.
 * Extracts the YAML frontmatter and looks for metadata.openclaw.streaming.
 *
 * We use a lightweight regex-based parser rather than a full YAML library
 * to keep the plugin dependency-free.
 */
export function parseStreamingConfig(content: string): StreamingConfig | null {
  if (!content) return null;

  // Extract YAML frontmatter
  const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
  if (!fmMatch) return null;

  const yaml = fmMatch[1];

  // Check if streaming config exists
  if (!yaml.includes("streaming:")) return null;

  // Extract streaming block — find indentation level and capture until dedent
  const streamingMatch = yaml.match(/streaming:\n((?:[ ]{6,}.*\n?)*)/);
  if (!streamingMatch) return null;

  const streamBlock = streamingMatch[1];

  // Parse steps
  const steps: StreamingStepDecl[] = [];
  const stepMatches = streamBlock.matchAll(/-\s*match:\s*"?([^"\n]+)"?\n\s+label:\s*"?([^"\n]+)"?(?:\n\s+long_running:\s*(true|false))?(?:\n\s+poll_interval:\s*(\d+))?/g);

  for (const m of stepMatches) {
    steps.push({
      match: m[1].trim(),
      label: m[2].trim(),
      long_running: m[3] === "true" ? true : undefined,
      poll_interval: m[4] ? Number(m[4]) : undefined,
    });
  }

  // Parse summary
  const summaryMatch = streamBlock.match(/summary:\s*(true|false)/);
  const summary = summaryMatch?.[1] === "true";

  // Parse locale
  const localeMatch = streamBlock.match(/locale:\s*"?(\w+)"?/);
  const locale = localeMatch?.[1];

  if (steps.length === 0 && !summary && !locale) return null;

  return {
    steps: steps.length > 0 ? steps : undefined,
    summary,
    locale,
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run test/config-loader.test.ts
```
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/config-loader.ts test/config-loader.test.ts
git commit -m "feat: add SKILL.md streaming config parser"
```

---

### Task 8: Plugin Entry (Wire Everything Together)

**Files:**
- Create: `src/index.ts`

- [ ] **Step 1: Create index.ts with types and setup**

File: `src/index.ts`
```typescript
import type { RunState, Locale } from "./types.js";
import { createRunState, pushStep, finishCurrentStep, clearAllTimers, createCleanupInterval } from "./state.js";
import { extractLabel } from "./label.js";
import { matchStep, detectSkillFromPrompt } from "./matcher.js";
import { parseStreamingConfig } from "./config-loader.js";
import { formatStepStart, formatStepDone, formatStillWorking, formatSummary } from "./formatter.js";
import { sendProgress } from "./sender.js";
import { readFileSync } from "node:fs";
import { join } from "node:path";

// OpenClaw Plugin SDK types — minimal subset for type safety
type OpenClawPluginApi = {
  runtime: any;
  config: any;
  pluginConfig?: Record<string, unknown>;
  resolvePath: (input: string) => string;
  on: (hookName: string, handler: (...args: any[]) => any, opts?: { priority?: number }) => void;
};

type OpenClawPluginDefinition = {
  register?: (api: OpenClawPluginApi) => void | Promise<void>;
};

function resolveLocale(pluginConfig?: Record<string, unknown>): Locale {
  const val = pluginConfig?.locale;
  if (val === "zh" || val === "en") return val;
  return "auto";
}

function resolveEffectiveLocale(locale: Locale): "en" | "zh" {
  if (locale === "zh" || locale === "en") return locale;
  return "en";
}

/**
 * Load streaming config for a skill by reading its SKILL.md from the
 * installed skills directory (~/.openclaw/skills/<name>/SKILL.md).
 * Returns null if not found or no streaming config declared.
 * Results are cached in skillConfigCache.
 */
const skillConfigCache = new Map<string, ReturnType<typeof parseStreamingConfig>>();

function loadSkillConfig(skillName: string, resolvePath: (s: string) => string) {
  if (skillConfigCache.has(skillName)) return skillConfigCache.get(skillName)!;

  try {
    const skillDir = resolvePath(`~/.openclaw/skills/${skillName}/SKILL.md`);
    const content = readFileSync(skillDir, "utf-8");
    const config = parseStreamingConfig(content);
    skillConfigCache.set(skillName, config);
    return config;
  } catch {
    skillConfigCache.set(skillName, null);
    return null;
  }
}

const plugin: OpenClawPluginDefinition = {
  register(api) {
    const runtime = api.runtime;
    const pluginConfig = api.pluginConfig;
    const runStates = new Map<string, RunState>();
    const activeSkills = new Map<string, string | null>();
    const locale = resolveLocale(pluginConfig);

    const enabled = pluginConfig?.enabled !== false;
    if (!enabled) return;

    // TTL cleanup
    createCleanupInterval(runStates, 60_000, 600_000);

    // Hook 0: detect active skill from system prompt
    api.on("llm_input", (event: any, ctx: any) => {
      const skillName = detectSkillFromPrompt(event.systemPrompt);
      const key = ctx?.sessionKey;
      if (key) activeSkills.set(key, skillName);
    });

    // Hook 1: tool call starts — send progress message
    api.on("before_tool_call", (event: any, ctx: any) => {
      const key = ctx?.sessionKey ?? "";
      const skillName = activeSkills.get(key);
      if (!skillName) return;

      let state = runStates.get(key);
      if (!state) {
        const skillConfig = loadSkillConfig(skillName, api.resolvePath) ?? undefined;
        state = createRunState(key, skillName, skillConfig);
        runStates.set(key, state);
      }

      // Try declarative match first, fall back to auto extraction
      const match = matchStep(event, state.skillConfig);
      const label = match?.label ?? extractLabel(event);
      const step = pushStep(state, label, {
        longRunning: match?.longRunning,
        pollInterval: match?.pollInterval,
      });

      // Use totalSteps from match (declarative) or state (cached)
      const totalSteps = match?.totalSteps ?? state.totalSteps;
      const eff = resolveEffectiveLocale(locale);
      sendProgress(runtime, key, formatStepStart(step, totalSteps, eff));

      if (step.longRunning) {
        const longRunningMs = Number(pluginConfig?.longRunningMs) || 15_000;
        step.timer = setInterval(() => {
          sendProgress(runtime, key, formatStillWorking(step, eff));
        }, step.pollInterval ?? longRunningMs);
      }
    });

    // Hook 2: tool call ends — send completion message
    api.on("after_tool_call", (event: any, ctx: any) => {
      const key = ctx?.sessionKey ?? "";
      const state = runStates.get(key);
      if (!state) return;

      const step = finishCurrentStep(state, event.error);
      if (step.timer) clearInterval(step.timer);

      // Reuse totalSteps from state (set during createRunState) — no need to re-match
      const eff = resolveEffectiveLocale(locale);
      sendProgress(runtime, key, formatStepDone(step, state.totalSteps, event.durationMs, eff));
    });

    // Hook 3: agent run ends — cleanup + optional summary
    api.on("agent_end", (_event: any, ctx: any) => {
      const key = ctx?.sessionKey ?? "";
      const state = runStates.get(key);
      if (!state) return;

      const summaryEnabled = pluginConfig?.summaryEnabled !== false;
      if (summaryEnabled && state.steps.length > 1) {
        const eff = resolveEffectiveLocale(locale);
        sendProgress(runtime, key, formatSummary(state, eff));
      }
      clearAllTimers(state);
      runStates.delete(key);
      activeSkills.delete(key);
    });
  },
};

export default plugin;
```

- [ ] **Step 2: Run full build**

```bash
npx tsc
```
Expected: No errors, `dist/` created with all compiled files.

- [ ] **Step 3: Run all tests**

```bash
npx vitest run
```
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/index.ts
git commit -m "feat: wire plugin entry with all hooks and modules"
```

---

### Task 9: README and Documentation

**Files:**
- Create: `README.md`
- Create: `README_CN.md`

- [ ] **Step 1: Create README.md**

Cover: what it does, installation, zero-config usage, declarative enhancement example, configuration options, architecture diagram, contributing.

- [ ] **Step 2: Create README_CN.md**

Chinese translation of README.md.

- [ ] **Step 3: Commit**

```bash
git add README.md README_CN.md
git commit -m "docs: add README in English and Chinese"
```

---

### Task 10: Integration Test with OpenClaw

**Files:** None (manual testing)

- [ ] **Step 1: Build the plugin**

```bash
cd ~/openclaw-plugin-skill-streaming
npm run build
```

- [ ] **Step 2: Link to local OpenClaw**

```bash
# Copy to OpenClaw plugins directory
cp -r ~/openclaw-plugin-skill-streaming ~/.openclaw/plugins/skill-streaming
```

- [ ] **Step 3: Test with admapix skill**

Send a message to OpenClaw (via Feishu or CLI) that triggers admapix skill:
- Verify progress messages appear during tool calls
- Verify step numbering is correct
- Verify completion messages show duration
- Verify summary appears for multi-step queries

- [ ] **Step 4: Test without skill (regular chat)**

Send a regular chat message that triggers tool calls:
- Verify NO progress messages appear (skill detection should filter)

- [ ] **Step 5: Fix any issues found**

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "fix: address issues found during integration testing"
```

---

### Task 11: Publish

- [ ] **Step 1: Verify package contents**

```bash
npm pack --dry-run
```

Verify: `dist/`, `openclaw.plugin.json`, `README.md`, `README_CN.md` included. No `test/`, `src/`, or config files.

- [ ] **Step 2: Publish to npm**

```bash
npm publish
```

- [ ] **Step 3: Publish to ClawHub (if applicable)**

```bash
npx clawhub publish
```

- [ ] **Step 4: Test install from npm**

```bash
openclaw plugin install skill-streaming
```

- [ ] **Step 5: Tag release**

```bash
git tag v0.1.0
git push origin main --tags
```
