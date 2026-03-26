# apfelpilot

Self-evolving Mac agent powered by [apfel](https://github.com/Arthur-Ficial/apfel)'s on-device AI.

Give it a task in plain English. It calls tools, checks results, and keeps going until it's done. When it needs a tool that doesn't exist, it creates one - a shell script that persists for future tasks. Over time, it builds a toolbox tailored to your Mac and your workflows.

**100% on-device. Free. No API keys. No cloud. Gets smarter over time.**

## Install

```bash
git clone https://github.com/Arthur-Ficial/apfelpilot.git
cd apfelpilot
pip3 install -e .
```

Requires [apfel](https://github.com/Arthur-Ficial/apfel) installed and on PATH.

## Usage

### One-shot tasks

```bash
apfelpilot "list the 5 largest files in my home directory"
apfelpilot "count how many swift files are in ~/dev/apfel"
apfelpilot "show me system uptime"
apfelpilot --yes "clean up .DS_Store files"    # skip confirmations
```

### Interactive mode

```bash
apfelpilot -i
```

```
  apfelpilot interactive mode
  5 tools available. Type 'tools' to list, 'history' to see log, 'quit' to exit.

  apfelpilot> what files are in my Desktop?
  [1] run_cmd({"command": "ls -la ~/Desktop"})
       -> total 24 ...
  Result: Your Desktop has 2 files: .DS_Store and a screenshot.

  apfelpilot> count swift files in ~/dev/apfel
  [1] run_cmd({"command": "find ~/dev/apfel/Sources -name '*.swift' | wc -l"})
       -> 28
  Result: There are 28 Swift files in ~/dev/apfel/Sources.

  apfelpilot> tools
    [built-in]   run_cmd              Run a shell command on macOS
    [built-in]   read_file            Read the contents of a file
    [built-in]   write_file           Write content to a file
    [built-in]   list_dir             List files and directories
    [built-in]   create_tool          Create a new reusable tool

  apfelpilot> quit
```

### Other commands

```bash
apfelpilot tools      # list all tools (built-in + learned)
apfelpilot history    # show execution history
```

## How it works

```
You: "organize my Downloads by file type"
  |
  v
apfelpilot sends task + tools to apfel --serve (on-device LLM)
  |
  v
apfel returns tool_call: list_dir("~/Downloads")
  -> apfelpilot executes, sends result back
  |
  v
apfel returns tool_call: run_cmd("mkdir ~/Downloads/images")
  -> apfelpilot executes, sends result back
  |
  v
apfel returns: "Done. Created subdirectories and moved files."
  -> task complete
```

## Self-evolution

apfelpilot starts with 5 built-in tools. When it needs a new capability, it creates one:

```bash
apfelpilot "create a tool that counts lines of code by file extension"
```

The new tool is saved as a shell script at `~/.apfelpilot/tools/` and is available for all future tasks:

```bash
apfelpilot tools
  [built-in] run_cmd       - Run a shell command
  [learned]  count_loc     - Count lines of code by extension
```

A photographer's apfelpilot learns `resize_images`. A developer's learns `run_tests`. The toolbox grows with you.

## Safety

- Dangerous commands blocked (`rm -rf /`, `mkfs`, fork bombs)
- Destructive ops require confirmation (`rm`, `sudo`, system dir writes)
- Tool creation shows script content and asks for confirmation
- Every action logged to `~/.apfelpilot/history.jsonl`
- `--yes` flag to skip confirmations for automation

## Limitations

- **4096 token context** - the on-device model is small. Keep tasks focused.
- **One tool call per step** - sequential, not parallel
- **Model quirks** - may hallucinate tool names or use Linux commands on macOS
- **Guardrails** - Apple's safety system may block benign prompts

## Architecture

```
apfelpilot (Python)          apfel (Swift)
  |                            |
  cli.py / interactive.py      apfel --serve
  loop.py ---- httpx ------>   /v1/chat/completions
  executor.py                  (tool calling)
  tools.py                     |
  |                            FoundationModels
  ~/.apfelpilot/tools/         (on-device LLM)
```

## License

[MIT](LICENSE)
