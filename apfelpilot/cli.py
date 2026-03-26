"""CLI interface for apfelpilot."""

import sys

import click

from apfelpilot import __version__


@click.group(invoke_without_command=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option("--version", "-v", is_flag=True, help="Show version")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--loop", "-l", default=0, type=int, help="Loop mode: repeat task every N seconds")
@click.pass_context
def main(ctx, yes, version, interactive, loop):
    """apfelpilot - self-evolving Mac agent powered by apfel.

    \b
    Run a task:   apfelpilot "organize my Downloads"
    Interactive:  apfelpilot -i
    Loop mode:    apfelpilot -l 60 "check disk space"
    List tools:   apfelpilot tools
    Show history: apfelpilot history
    """
    if version:
        click.echo(f"apfelpilot {__version__}")
        return

    ctx.ensure_object(dict)
    ctx.obj["yes"] = yes
    ctx.obj["loop"] = loop

    if interactive:
        from apfelpilot.interactive import run_interactive
        run_interactive(auto_confirm=yes)
        return

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command(name="run", hidden=True)
@click.argument("task")
@click.pass_context
def run_cmd(ctx, task):
    """Run a task."""
    import time as _time
    from apfelpilot.loop import run_task

    yes = ctx.obj.get("yes", False) if ctx.obj else False
    loop_interval = ctx.obj.get("loop", 0) if ctx.obj else 0

    if loop_interval > 0:
        click.echo(f"\n  Loop mode: running every {loop_interval}s (Ctrl+C to stop)\n", err=True)
        iteration = 0
        try:
            while True:
                iteration += 1
                click.echo(f"  --- iteration {iteration} ---", err=True)
                run_task(task, auto_confirm=yes)
                _time.sleep(loop_interval)
        except KeyboardInterrupt:
            click.echo(f"\n  Stopped after {iteration} iterations.", err=True)
    else:
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

        if isinstance(args, dict):
            args_str = ", ".join(f"{k}={v[:50]}" for k, v in args.items())
        else:
            args_str = str(args)[:100]
        click.echo(f"    [{step}] {tool}({args_str}) - {duration}ms - {ts}")
    click.echo()


def entry_point():
    """Entry point that routes tasks vs subcommands."""
    known = {"tools", "history", "run"}
    args = sys.argv[1:]

    # Find first non-flag argument (skip flag values like -l 60)
    first_arg = None
    skip_next = False
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if a in ("-l", "--loop", "-n", "--last"):
            skip_next = True  # next arg is a value, not a task
            continue
        if a.startswith("-"):
            continue
        first_arg = a
        break

    if first_arg and first_arg not in known:
        idx = args.index(first_arg)
        args.insert(idx, "run")
        sys.argv = [sys.argv[0]] + args

    main()
