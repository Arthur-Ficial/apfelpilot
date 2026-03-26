"""Task execution history - append-only JSONL log."""

import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = Path.home() / ".apfelpilot" / "history.jsonl"


def log_step(task: str, step: int, tool: str, args: dict, result: str, duration_ms: int) -> None:
    """Append a step to the history log."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "task": task[:100],
        "step": step,
        "tool": tool,
        "args": {k: str(v)[:200] for k, v in args.items()},
        "result_chars": len(result),
        "duration_ms": duration_ms,
    }

    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_history(last: int = 20) -> list:
    """Read the last N history entries."""
    if not HISTORY_FILE.exists():
        return []

    lines = HISTORY_FILE.read_text().strip().split("\n")
    entries = []
    for line in lines[-last:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries
