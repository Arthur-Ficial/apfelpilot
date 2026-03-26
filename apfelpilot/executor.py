"""Execute tools safely - run commands, read/write files, create tools."""

import json
import os
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from apfelpilot.tools import BUILTIN_NAMES, TOOLS_DIR

MAX_OUTPUT = 2000
TIMEOUT = 30

# Patterns that are always blocked
BLOCKED_PATTERNS = [
    r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/\s*$",
    r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+~/?\s*$",
    r"mkfs\.",
    r"dd\s+if=",
    r">\s*/dev/sd",
    r":\(\)\s*\{",
    r"chmod\s+-R\s+777\s+/",
    r"curl.*\|\s*(ba)?sh",
]

# Patterns that require confirmation
CONFIRM_PATTERNS = [
    (r"\brm\b", "delete files"),
    (r"\bsudo\b", "run as root"),
    (r">\s*/etc/", "write to system directory"),
    (r">\s*/usr/", "write to system directory"),
    (r">\s*/System/", "write to system directory"),
]


def is_blocked(command: str) -> Optional[str]:
    """Check if a command matches blocked patterns. Returns reason or None."""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command):
            return f"Blocked: command matches dangerous pattern '{pattern}'"
    return None


def needs_confirmation(command: str) -> Optional[str]:
    """Check if a command needs user confirmation. Returns reason or None."""
    for pattern, reason in CONFIRM_PATTERNS:
        if re.search(pattern, command):
            return reason
    return None


def confirm(message: str, auto_confirm: bool = False) -> bool:
    """Ask user for confirmation. Returns True if confirmed."""
    if auto_confirm:
        return True
    try:
        resp = input(f"  {message} [y/N] ")
        return resp.strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def truncate(text: str, max_chars: int = MAX_OUTPUT) -> str:
    """Truncate text to max_chars, adding a note if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text)} chars total)"


def execute_tool(name: str, args: dict, tools: dict, auto_confirm: bool = False, task: str = "") -> str:
    """Execute a tool by name with given arguments. Returns output string."""
    if name == "run_cmd":
        return _run_cmd(args, auto_confirm)
    elif name == "read_file":
        return _read_file(args)
    elif name == "write_file":
        return _write_file(args, auto_confirm)
    elif name == "list_dir":
        return _list_dir(args)
    elif name == "create_tool":
        return _create_tool(args, auto_confirm, task)
    elif name in tools and "_script" in tools[name]:
        return _run_learned_tool(name, args, tools[name])
    else:
        return f"Error: unknown tool '{name}'"


def _run_cmd(args: dict, auto_confirm: bool) -> str:
    command = args.get("command") or args.get("cmd") or ""
    if not command:
        return "Error: no command provided"

    blocked = is_blocked(command)
    if blocked:
        return blocked

    reason = needs_confirmation(command)
    if reason:
        print(f"\n  Tool wants to: {reason}", file=sys.stderr)
        print(f"  Command: {command}", file=sys.stderr)
        if not confirm(f"Allow?", auto_confirm):
            return "Command cancelled by user."

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=str(Path.home()),
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"
        return truncate(output) if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {TIMEOUT}s"
    except Exception as e:
        return f"Error: {e}"


def _read_file(args: dict) -> str:
    path = args.get("path") or args.get("file") or ""
    if not path:
        return "Error: no path provided"

    path = os.path.expanduser(path)
    try:
        with open(path) as f:
            lines = f.readlines()[:50]
        content = "".join(lines)
        if len(lines) == 50:
            content += "\n... (truncated at 50 lines)"
        return truncate(content) if content.strip() else "(empty file)"
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except PermissionError:
        return f"Error: permission denied: {path}"
    except Exception as e:
        return f"Error: {e}"


def _write_file(args: dict, auto_confirm: bool) -> str:
    path = args.get("path") or args.get("file") or ""
    content = args.get("content") or ""
    if not path:
        return "Error: no path provided"

    path = os.path.expanduser(path)

    # Safety: confirm writes to system dirs
    for prefix in ("/etc/", "/usr/", "/System/", "/Library/"):
        if path.startswith(prefix):
            print(f"\n  Tool wants to write to system path: {path}", file=sys.stderr)
            if not confirm("Allow?", auto_confirm):
                return "Write cancelled by user."

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Written {len(content)} chars to {path}"
    except Exception as e:
        return f"Error: {e}"


def _list_dir(args: dict) -> str:
    path = args.get("path") or args.get("directory") or args.get("dir") or "."
    path = os.path.expanduser(path)

    try:
        entries = sorted(os.listdir(path))[:50]
        if not entries:
            return "(empty directory)"
        result = "\n".join(entries)
        if len(os.listdir(path)) > 50:
            result += f"\n... ({len(os.listdir(path))} entries total, showing first 50)"
        return result
    except FileNotFoundError:
        return f"Error: directory not found: {path}"
    except PermissionError:
        return f"Error: permission denied: {path}"
    except Exception as e:
        return f"Error: {e}"


def _create_tool(args: dict, auto_confirm: bool, task: str) -> str:
    name = args.get("name") or ""
    description = args.get("description") or ""
    script = args.get("script") or ""
    arg_str = args.get("args") or ""

    if not name or not script:
        return "Error: name and script are required"

    # Validate name
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        return "Error: name must be lowercase letters, digits, and underscores"

    if name in BUILTIN_NAMES:
        return f"Error: '{name}' is a built-in tool name, choose another"

    # Safety check the script
    blocked = is_blocked(script)
    if blocked:
        return f"Script blocked: {blocked}"

    # Always confirm tool creation
    print(f"\n  Creating tool: {name}", file=sys.stderr)
    print(f"  Description: {description}", file=sys.stderr)
    print(f"  Script:\n    {script.replace(chr(10), chr(10) + '    ')}", file=sys.stderr)
    if not confirm("Create this tool?", auto_confirm):
        return "Tool creation cancelled by user."

    # Write script
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    script_path = TOOLS_DIR / f"{name}.sh"
    script_content = f"#!/bin/bash\n{script}\n"
    script_path.write_text(script_content)
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    # Write metadata
    tool_args = [a.strip() for a in arg_str.split(",") if a.strip()] if arg_str else []
    meta = {
        "name": name,
        "description": description,
        "args": tool_args,
        "created": datetime.now(timezone.utc).isoformat(),
        "created_by_task": task,
    }
    meta_path = TOOLS_DIR / f"{name}.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    return f"Tool '{name}' created successfully at {script_path}"


def _run_learned_tool(name: str, args: dict, tool_def: dict) -> str:
    script = tool_def["_script"]
    meta = tool_def.get("_meta", {})
    tool_args = meta.get("args", [])

    arg_values = [str(args.get(a, "")) for a in tool_args]

    try:
        result = subprocess.run(
            [script] + arg_values,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=str(Path.home()),
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"
        return truncate(output) if output.strip() else "(no output)"
    except Exception as e:
        return f"Error running {name}: {e}"
