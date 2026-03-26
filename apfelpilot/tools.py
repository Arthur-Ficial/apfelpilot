"""Tool registry - built-in tools and learned tools from ~/.apfelpilot/tools/."""

import json
from pathlib import Path

TOOLS_DIR = Path.home() / ".apfelpilot" / "tools"

# Built-in tool definitions (OpenAI function calling format)
BUILTIN_TOOLS = {
    "run_cmd": {
        "type": "function",
        "function": {
            "name": "run_cmd",
            "description": "Run a shell command on macOS and return its output",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"},
                },
                "required": ["command"],
            },
        },
    },
    "read_file": {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file (first 50 lines)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path"},
                },
                "required": ["path"],
            },
        },
    },
    "write_file": {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    "list_dir": {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"},
                },
                "required": ["path"],
            },
        },
    },
    "create_tool": {
        "type": "function",
        "function": {
            "name": "create_tool",
            "description": "Create a new reusable shell script tool that persists for future tasks",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Tool name (lowercase_underscores)"},
                    "description": {"type": "string", "description": "What this tool does (one line)"},
                    "script": {"type": "string", "description": "Bash script content. Use $1, $2 for positional args."},
                    "args": {"type": "string", "description": "Comma-separated argument names, e.g. 'directory,extension'"},
                },
                "required": ["name", "description", "script"],
            },
        },
    },
}

BUILTIN_NAMES = set(BUILTIN_TOOLS.keys())


def load_learned_tools() -> dict:
    """Load learned tools from ~/.apfelpilot/tools/."""
    tools = {}
    if not TOOLS_DIR.exists():
        return tools

    for meta_file in TOOLS_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_file.read_text())
            name = meta["name"]
            script_file = TOOLS_DIR / f"{name}.sh"
            if not script_file.exists():
                continue

            args = meta.get("args", [])
            props = {}
            required = []
            for arg in args:
                props[arg] = {"type": "string", "description": f"Argument: {arg}"}
                required.append(arg)

            tools[name] = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": meta.get("description", name),
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                    },
                },
                "_meta": meta,
                "_script": str(script_file),
            }
        except (json.JSONDecodeError, KeyError):
            continue

    return tools


def get_all_tools() -> dict:
    """Get all tools (built-in + learned)."""
    tools = dict(BUILTIN_TOOLS)
    tools.update(load_learned_tools())
    return tools


def get_tool_definitions(tools: dict) -> list:
    """Get OpenAI-format tool definitions list (strips internal metadata)."""
    defs = []
    for tool in tools.values():
        defs.append({
            "type": tool["type"],
            "function": tool["function"],
        })
    return defs


def tool_exists(name: str, tools: dict) -> bool:
    """Check if a tool exists in the registry."""
    return name in tools


def list_tools_display(tools: dict) -> list:
    """Return a list of (name, description, source) tuples for display."""
    result = []
    for name, tool in sorted(tools.items()):
        desc = tool["function"]["description"]
        source = "built-in" if name in BUILTIN_NAMES else "learned"
        result.append((name, desc, source))
    return result
