"""Interactive CLI mode for apfelpilot."""

import sys

from apfelpilot import __version__
from apfelpilot.client import ensure_server
from apfelpilot.loop import run_task
from apfelpilot.tools import get_all_tools, list_tools_display


def run_interactive(auto_confirm=False):
    """Run apfelpilot in interactive mode."""
    ensure_server()

    tools = get_all_tools()
    tool_count = len(tools)

    print("")
    print(f"  \033[36mapfelpilot\033[0m v{__version__} - {tool_count} tools ready")
    print(f"  \033[90mType a task, 'tools', 'history', 'help', or 'quit'\033[0m")
    print("")

    while True:
        try:
            task = input("  \033[36m>\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not task:
            continue

        if task in ("quit", "exit", "q"):
            break

        if task == "tools":
            tools = get_all_tools()
            items = list_tools_display(tools)
            print("")
            for name, desc, source in items:
                if source == "built-in":
                    print(f"    \033[90m[built-in]\033[0m  \033[1m{name:18s}\033[0m {desc}")
                else:
                    print(f"    \033[32m[learned]\033[0m   \033[1m{name:18s}\033[0m {desc}")
            print("")
            continue

        if task == "history":
            from apfelpilot.history import read_history
            entries = read_history(10)
            if not entries:
                print("\n    \033[90mNo history yet.\033[0m\n")
                continue
            print("")
            current = None
            for entry in entries:
                t = entry.get("task", "?")
                if t != current:
                    current = t
                    print(f"    \033[1m{t}\033[0m")
                step = entry.get("step", "?")
                tool = entry.get("tool", "?")
                args = entry.get("args", {})
                args_str = ", ".join(f"{k}={v[:30]}" for k, v in args.items()) if isinstance(args, dict) else str(args)[:60]
                print(f"      \033[90m[{step}] {tool}({args_str})\033[0m")
            print("")
            continue

        if task == "help":
            print("")
            print("    \033[1mCommands:\033[0m")
            print("      \033[36m<task>\033[0m       Describe what you want done")
            print("      \033[36mtools\033[0m       List available tools (built-in + learned)")
            print("      \033[36mhistory\033[0m     Show recent execution log")
            print("      \033[36mquit\033[0m        Exit")
            print("")
            print("    \033[1mExamples:\033[0m")
            print("      list files in my Downloads")
            print("      use run_cmd to run: df -h /")
            print("      create a tool that counts lines in a file")
            print("      what is today's date")
            print("")
            continue

        run_task(task, auto_confirm=auto_confirm)

        # Reload tools in case new ones were created
        tools = get_all_tools()
