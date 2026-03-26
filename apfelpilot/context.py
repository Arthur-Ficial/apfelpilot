"""Message building and token budget management."""

SYSTEM_PROMPT_TEMPLATE = """You are apfelpilot, a Mac automation assistant. You complete tasks by calling tools.

RULES:
- Call ONE tool at a time. Wait for the result before calling the next.
- Your available tools are ONLY: {tool_names}.
- To run ANY shell command, use run_cmd with the "command" parameter.
- Do NOT invent tool names. Do NOT call tools not listed above.
- When the task is complete, respond with a short text summary. No tool call.
- To create a reusable tool, use create_tool with name, description, and script parameters.

IMPORTANT: Use run_cmd for shell commands. Example: run_cmd(command="ls -la ~/Desktop")
This is macOS with zsh. Use macOS commands (df -h, pbcopy, open, osascript)."""

# Max tool-call/result pairs to keep in history (sliding window)
MAX_HISTORY_PAIRS = 2


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
    """Build messages for continuation after tool execution.

    exchanges: list of (tool_call_message, tool_result_message) tuples

    The last message is role:"tool" - apfel accepts this directly.
    """
    messages = [
        {"role": "system", "content": build_system_prompt(tool_names)},
        {"role": "user", "content": task},
    ]

    # Keep only the last MAX_HISTORY_PAIRS exchanges
    recent = exchanges[-MAX_HISTORY_PAIRS:]
    for assistant_msg, tool_msg in recent:
        messages.append(assistant_msg)
        messages.append(tool_msg)

    return messages
