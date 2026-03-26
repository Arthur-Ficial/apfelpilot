"""CLI interface for apfelpilot."""

import sys

import click

from apfelpilot import __version__


@click.group(invoke_without_command=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option("--version", "-v", is_flag=True, help="Show version")
@click.pass_context
def main(ctx, yes, version):
    """apfelpilot - self-evolving Mac agent powered by apfel.

    \b
    Run a task:   apfelpilot "organize my Downloads"
    List tools:   apfelpilot tools
    Show history: apfelpilot history
    """
    if version:
        click.echo(f"apfelpilot {__version__}")
        return

    ctx.ensure_object(dict)
    ctx.obj["yes"] = yes


@main.command(name="run", hidden=True)
@click.argument("task")
@click.pass_context
def run_cmd(ctx, task):
    """Run a task (internal - called via entry point wrapper)."""
    from apfelpilot.loop import run_task
    yes = ctx.obj.get("yes", False) if ctx.obj else False
    run_task(task, auto_confirm=yes)


@main.command()
def tools():
    """List all available tools (built-in + learned)."""
    from apfelpilot.tools import get_all_tools, list_tools_display

    all_tools = get_all_tools()
    items = list_tools_display(all_tools)

    if not items:
        click.echo("No tools found.")
        return

    click.echo(f"\n  {len(items)} tools available:\n")
    for name, desc, source in items:
        tag = click.style(f"[{source}]", fg="cyan" if source == "built-in" else "green")
        click.echo(f"  {tag} {click.style(name, bold=True)} - {desc}")
    click.echo()


@main.command()
@click.option("--last", "-n", default=20, help="Number of entries to show")
def history(last):
    """Show recent task execution history."""
    from apfelpilot.history import read_history

    entries = read_history(last)
    if not entries:
        click.echo("No history yet.")
        return

    click.echo(f"\n  Last {len(entries)} steps:\n")
    current_task = None
    for entry in entries:
        task = entry.get("task", "?")
        if task != current_task:
            current_task = task
            click.echo(f"  {click.style(task, bold=True)}")

        step = entry.get("step", "?")
        tool = entry.get("tool", "?")
        args = entry.get("args", {})
        ts = entry.get("ts", "")[:19].replace("T", " ")
        duration = entry.get("duration_ms", 0)

        args_str = ", ".join(f"{k}={v[:50]}" for k, v in args.items())
        click.echo(f"    [{step}] {tool}({args_str}) - {duration}ms - {ts}")
    click.echo()


def entry_point():
    """Entry point that routes tasks vs subcommands.

    If the first non-flag arg is not a known subcommand, treat it as a task.
    This allows: apfelpilot "organize files" without a 'run' subcommand.
    """
    known = {"tools", "history", "run"}
    args = sys.argv[1:]

    # Find first non-flag argument
    first_arg = None
    for a in args:
        if not a.startswith("-"):
            first_arg = a
            break

    if first_arg and first_arg not in known:
        # Insert 'run' subcommand before the task argument
        # Find where the task arg is and insert 'run' before it
        idx = args.index(first_arg)
        args.insert(idx, "run")
        sys.argv = [sys.argv[0]] + args

    main()
