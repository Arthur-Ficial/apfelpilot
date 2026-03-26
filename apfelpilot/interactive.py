"""Interactive CLI mode for apfelpilot."""

import sys

from apfelpilot.client import ensure_server
from apfelpilot.loop import run_task
from apfelpilot.tools import get_all_tools, list_tools_display


def run_interactive(auto_confirm=False):
    """Run apfelpilot in interactive mode."""
    ensure_server()

    tools = get_all_tools()
    tool_count = len(tools)

    print("")
    print("  apfelpilot interactive mode")
    print(f"  {tool_count} tools available. Type 'tools' to list, 'history' to see log, 'quit' to exit.")
    print("  Just type what you want done.\n")

    while True:
        try:
            task = input("  apfelpilot> ").strip()
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
                tag = f"[{source}]"
                print(f"    {tag:12s} {name:20s} {desc}")
            print("")
            continue

        if task == "history":
            from apfelpilot.history import read_history
            entries = read_history(10)
            if not entries:
                print("\n    No history yet.\n")
                continue
            print("")
            current = None
            for entry in entries:
                t = entry.get("task", "?")
                if t != current:
                    current = t
                    print(f"    {t}")
                step = entry.get("step", "?")
                tool = entry.get("tool", "?")
                args = entry.get("args", {})
                args_str = ", ".join(f"{k}={v[:40]}" for k, v in args.items()) if isinstance(args, dict) else str(args)
                print(f"      [{step}] {tool}({args_str})")
            print("")
            continue

        if task == "help":
            print("\n    Commands:")
            print("      <task>     Run a task (e.g. 'list files in Downloads')")
            print("      tools      List available tools")
            print("      history    Show recent execution history")
            print("      quit       Exit interactive mode")
            print("")
            continue

        # Run the task
        run_task(task, auto_confirm=auto_confirm)

        # Reload tools in case new ones were created
        tools = get_all_tools()
