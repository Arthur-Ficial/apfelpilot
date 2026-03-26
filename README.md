# apfelpilot

Self-evolving Mac agent powered by [apfel](https://github.com/Arthur-Ficial/apfel)'s on-device AI.

Give it a task in plain English. It calls tools, checks results, and keeps going until it's done. When it needs a tool that doesn't exist, it creates one - a shell script that persists for future tasks. Over time, it builds a toolbox tailored to your Mac and your workflows.

**100% on-device. Free. No API keys. No cloud.**

## Install

```bash
git clone https://github.com/Arthur-Ficial/apfelpilot.git
cd apfelpilot
pip install -e .
```

Requires [apfel](https://github.com/Arthur-Ficial/apfel) installed and on PATH.

## Usage

```bash
# Run a task
apfelpilot "list the 5 largest files in my home directory"

# Multi-step task
apfelpilot "organize my Downloads - create subdirectories by extension and move files"

# Skip confirmation prompts
apfelpilot --yes "clean up .DS_Store files in my projects"

# List available tools
apfelpilot tools

# Show execution history
apfelpilot history
```

## How it works

```
You: "organize my Downloads by file type"

apfelpilot sends task + tools to apfel --serve (on-device LLM)
  |
  v
apfel returns: list_dir("~/Downloads")
  -> apfelpilot executes, sends result back
  |
  v
apfel returns: run_cmd("mkdir -p ~/Downloads/{images,docs,pdf}")
  -> apfelpilot executes, sends result back
  |
  v
apfel returns: run_cmd("mv ~/Downloads/*.jpg ~/Downloads/images/")
  -> apfelpilot executes, sends result back
  |
  v
apfel returns: "Done. Moved 12 images, 5 PDFs, 3 docs."
  -> task complete
```

Each step: apfel decides what tool to call, apfelpilot executes it, sends the result back. Max 10 steps per task.

## Built-in tools

| Tool | What it does |
|------|-------------|
| `run_cmd` | Run any shell command |
| `read_file` | Read file contents (first 50 lines) |
| `write_file` | Write/create a file |
| `list_dir` | List directory contents |
| `create_tool` | Create a new reusable shell script tool |

## Self-evolution: create_tool

When apfelpilot needs a capability it doesn't have, it creates one:

```bash
apfelpilot "create a tool that counts lines of code in a directory"
```

apfel writes a shell script, apfelpilot saves it to `~/.apfelpilot/tools/`. Next time, that tool is available:

```bash
apfelpilot tools
  [built-in] run_cmd - Run a shell command on macOS
  [built-in] read_file - Read the contents of a file
  [learned]  count_loc - Count lines of code in a directory
```

A photographer's apfelpilot learns `resize_images` and `convert_heic`. A developer's learns `git_status` and `run_tests`. The toolbox grows with you.

## Safety

- Dangerous commands are blocked (`rm -rf /`, `mkfs`, `dd`, fork bombs)
- Destructive operations require confirmation (`rm`, `sudo`, system directory writes)
- Tool creation always shows the script and asks for confirmation
- All actions logged to `~/.apfelpilot/history.jsonl`
- `--yes` flag to skip confirmations (for automation)

## Limitations

- **4096 token context window** - apfel's on-device model is small. Tasks must be expressible in short prompts. Complex multi-file operations may need multiple runs.
- **One tool call per step** - the model can't call multiple tools in parallel
- **No vision** - can't see the screen (yet)
- **Guardrails** - Apple's safety system may block benign prompts

## Architecture

```
apfelpilot (Python)          apfel (Swift)
  |                            |
  cli.py                       apfel --serve
  loop.py ---- httpx ------>   /v1/chat/completions
  executor.py                  (tool calling)
  tools.py                     |
  |                            FoundationModels
  ~/.apfelpilot/tools/         (on-device LLM)
```

apfelpilot is a pure consumer of apfel's OpenAI-compatible API. No apfel code changes needed.

## License

[MIT](LICENSE)
