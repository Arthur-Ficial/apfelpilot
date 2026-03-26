# apfelpilot - Project Instructions

## The Golden Goal

apfelpilot has ONE purpose:

> **Turn any Mac into a self-driving computer using the FREE on-device Apple Intelligence model.
> Accept tasks in plain English, execute them via tool calls, and get smarter over time
> by creating and remembering new tools.**

### The two modes:

1. **One-shot** (`apfelpilot "organize my Downloads"`)
   - Takes a task, runs the tool-calling loop, prints the result
   - Max 10 steps per task
   - Supports --yes for unattended execution

2. **Interactive** (`apfelpilot -i`)
   - Persistent session with prompt
   - Type tasks, see results, type more
   - Tools created during session are immediately available
   - Type `tools` to see what's available, `history` for log

### The self-evolution principle:

apfelpilot starts with 5 built-in tools. When it needs a capability it doesn't have,
it creates a new tool (a shell script) that persists at `~/.apfelpilot/tools/`.
Over time, YOUR apfelpilot has different tools than anyone else's - it adapts to
your workflows, your file structure, your habits.

### Non-negotiable principles:

- **Powered by apfel.** All inference via `apfel --serve` (on-device, free, private)
- **No apfel changes.** Pure consumer of the OpenAI-compatible API
- **Safe by default.** Destructive commands blocked or require confirmation
- **Transparent.** Every action logged. Every tool readable. No magic.
- **Simple.** Python, httpx, click. No async, no frameworks, no complexity.

## Architecture

```
apfelpilot (Python CLI)
  |
  cli.py ─── entry point, arg routing
  interactive.py ─── interactive REPL mode
  loop.py ──── tool-calling loop (max 10 steps)
  client.py ── httpx → apfel --serve (localhost:11434)
  tools.py ─── tool registry (built-in + learned)
  executor.py ─ execute tools, safety checks
  context.py ── system prompt, message building
  history.py ── JSONL audit log

  ~/.apfelpilot/
    tools/*.sh + *.json  ← learned tools
    history.jsonl        ← execution log
```

## Build & Test

```bash
pip3 install -e .                          # install in dev mode
apfelpilot "list my Desktop files"         # one-shot task
apfelpilot -i                              # interactive mode
apfelpilot tools                           # list tools
apfelpilot history                         # show log
```

## Key Constraints (from apfel)

- 4096 token context window (input + output combined)
- One tool call per step (no parallel calls)
- Model may hallucinate tool names or rename parameters
- Some benign prompts trigger Apple's safety guardrails
- role:"tool" accepted as last message (TICKET-014 fixed)
