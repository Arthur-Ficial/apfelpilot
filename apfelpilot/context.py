"""Message building and token budget management."""

SYSTEM_PROMPT = """You are apfelpilot, a Mac automation assistant. You complete tasks by calling the provided tools.

RULES:
- Call ONE tool at a time.
- Your available tools are ONLY: run_cmd, read_file, write_file, list_dir, create_tool.
- To run shell commands like ls, find, du, mv, mkdir, use run_cmd.
- Do NOT make up tool names. Do NOT call tools that are not listed.
- When done, respond with a text summary (no tool call).

You MUST use run_cmd for any shell command. Example: to list files, call run_cmd with command "ls -la".
This is macOS (not Linux). Use macOS commands (e.g. df -h, diskutil, open, pbcopy)."""

# Max tool-call/result pairs to keep in history (sliding window)
MAX_HISTORY_PAIRS = 2


def build_initial_messages(task):
    """Build the initial message list for a new task."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]


def build_continuation_messages(task, exchanges, step, max_steps):
    """Build messages for continuation after tool execution.

    exchanges: list of (tool_call_message, tool_result_message) tuples

    The last message is role:"tool" - apfel now accepts this directly
    (TICKET-014 fixed). No synthetic user message needed.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    # Keep only the last MAX_HISTORY_PAIRS exchanges
    recent = exchanges[-MAX_HISTORY_PAIRS:]
    for assistant_msg, tool_msg in recent:
        messages.append(assistant_msg)
        messages.append(tool_msg)

    return messages
