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


def build_initial_messages(task: str) -> list:
    """Build the initial message list for a new task."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]


def build_continuation_messages(
    task: str,
    exchanges: list,
    step: int,
    max_steps: int,
) -> list:
    """Build messages for continuation after tool execution.

    exchanges: list of (tool_call_message, tool_result_message) tuples
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

    # Continuation prompt (satisfies "last message must be user" constraint)
    if step >= max_steps - 2:
        cont = f"Step {step}/{max_steps}. Finish now - give your final answer."
    elif step > max_steps // 2:
        cont = f"Step {step}/{max_steps}. Continue, but wrap up soon."
    else:
        cont = "Continue with the task. Call a tool or give your final answer if done."

    messages.append({"role": "user", "content": cont})
    return messages
