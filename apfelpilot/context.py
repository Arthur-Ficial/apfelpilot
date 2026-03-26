"""Message building and token budget management."""

SYSTEM_PROMPT_TEMPLATE = """You are apfelpilot, a Mac automation assistant. You complete tasks by calling tools and evaluating results.

RULES:
- Call ONE tool at a time. Check if it worked. If it failed, try a different approach.
- Your tools are: {tool_names}.
- To run ANY shell command, use run_cmd with the "command" parameter.
- Do NOT invent tool names. Use ONLY the tools listed above.
- If a command fails or returns an error, analyze why and try to fix it.
- When the task is fully complete, respond with a short summary.

SELF-EVALUATION:
- After each tool result, check: did it work? Is the output what I expected?
- If not, adjust your approach. Try a different command or tool.
- Never give up on the first failure. Debug and retry.

This is macOS with zsh. Use: ls, find, grep, awk, sed, du, df, open, pbcopy, osascript.
Use run_cmd for ALL shell commands. Example: run_cmd(command="ls -la ~/Desktop")"""

# Max tool-call/result pairs to keep in history (sliding window)
MAX_HISTORY_PAIRS = 3  # Increased for self-debugging context


def build_system_prompt(tool_names):
    """Build system prompt with current tool names."""
    return SYSTEM_PROMPT_TEMPLATE.format(tool_names=", ".join(sorted(tool_names)))


def build_initial_messages(task, tool_names):
    """Build the initial message list for a new task."""
    return [
        {"role": "system", "content": build_system_prompt(tool_names)},
        {"role": "user", "content": task},
    ]


def build_continuation_messages(task, exchanges, tool_names):
    """Build messages for continuation after tool execution."""
    messages = [
        {"role": "system", "content": build_system_prompt(tool_names)},
        {"role": "user", "content": task},
    ]

    # Keep the last MAX_HISTORY_PAIRS exchanges for debugging context
    recent = exchanges[-MAX_HISTORY_PAIRS:]
    for assistant_msg, tool_msg in recent:
        messages.append(assistant_msg)
        messages.append(tool_msg)

    return messages
