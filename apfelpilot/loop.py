"""The core tool-calling loop."""

import json
import re
import sys
import time

from apfelpilot.client import chat_completion, ensure_server
from apfelpilot.context import build_continuation_messages, build_initial_messages
from apfelpilot.executor import execute_tool
from apfelpilot.history import log_step
from apfelpilot.tools import get_all_tools, get_tool_definitions, tool_exists

MAX_STEPS = 10

# Map tool names to their primary parameter for when model sends a plain string
PRIMARY_PARAM = {
    "run_cmd": "command",
    "read_file": "path",
    "write_file": "path",
    "list_dir": "path",
}


def _infer_args(tool_name, raw_value, tools):
    """When model sends a plain string instead of JSON args, infer the parameter name."""
    param = PRIMARY_PARAM.get(tool_name)
    if param:
        return {param: raw_value.strip()}
    # For learned tools, use first arg name
    tool_def = tools.get(tool_name, {})
    meta = tool_def.get("_meta", {})
    tool_args_list = meta.get("args", [])
    if tool_args_list:
        return {tool_args_list[0]: raw_value.strip()}
    return {"value": raw_value.strip()}


def _extract_tool_call_from_content(content):
    """Try to extract a tool call from text content (fallback detection).

    The on-device model sometimes returns tool call JSON as text content
    instead of structured tool_calls. This mirrors apfel's own detection.
    """
    if not content:
        return None

    # Try to find {"tool_calls": ...} in the content
    candidates = []

    # Strip markdown code blocks
    blocks = re.findall(r'```(?:json|function|tool)?\s*\n?(.*?)\n?```', content, re.DOTALL)
    candidates.extend(blocks)

    # Try finding {"tool_calls" substring
    idx = content.find('{"tool_calls"')
    if idx >= 0:
        candidates.append(content[idx:])

    # Try whole content
    candidates.append(content.strip())

    for candidate in candidates:
        candidate = candidate.strip()
        try:
            obj = json.loads(candidate)
            # Handle both {"tool_calls": [...]} and [{"tool_calls": [...]}]
            if isinstance(obj, list) and obj:
                obj = obj[0]
            if not isinstance(obj, dict):
                continue
            calls = obj.get("tool_calls", [])
            if calls:
                call = calls[0]
                fn = call.get("function", {})
                name = fn.get("name", "")
                args_raw = fn.get("arguments", "{}")
                if isinstance(args_raw, str):
                    args = json.loads(args_raw) if args_raw else {}
                else:
                    args = args_raw
                return {
                    "id": call.get("id", "call_fallback"),
                    "name": name,
                    "args": args,
                }
        except (json.JSONDecodeError, KeyError, TypeError):
            continue

    return None


def run_task(task, auto_confirm=False):
    """Run a task through the tool-calling loop."""
    ensure_server()

    tools = get_all_tools()
    tool_defs = get_tool_definitions(tools)
    exchanges = []

    print(f"\n  Task: {task}", file=sys.stderr)
    print(f"  Tools: {', '.join(sorted(tools.keys()))}", file=sys.stderr)
    print(f"  Max steps: {MAX_STEPS}", file=sys.stderr)
    print("", file=sys.stderr)

    for step in range(1, MAX_STEPS + 1):
        if step == 1:
            messages = build_initial_messages(task)
        else:
            messages = build_continuation_messages(task, exchanges, step, MAX_STEPS)

        try:
            response = chat_completion(messages, tool_defs)
        except RuntimeError as e:
            print(f"\n  Error from apfel: {e}", file=sys.stderr)
            break
        except Exception as e:
            print(f"\n  Connection error: {e}", file=sys.stderr)
            break

        choice = response["choices"][0]
        finish_reason = choice.get("finish_reason", "stop")
        message = choice.get("message", {})
        content = message.get("content", "")

        # Extract tool call - try structured first, then fallback from content
        tool_calls = message.get("tool_calls")
        tool_name = None
        tool_id = "call_1"
        tool_args = {}

        if tool_calls:
            tc = tool_calls[0]
            fn = tc.get("function", {})
            tool_name = fn.get("name", "")
            tool_id = tc.get("id", "call_1")
            args_raw = fn.get("arguments", "{}")
            try:
                if isinstance(args_raw, str):
                    tool_args = json.loads(args_raw)
                else:
                    tool_args = args_raw
            except json.JSONDecodeError:
                # Model returned a plain string instead of JSON object
                # Use it as the first required parameter
                tool_args = _infer_args(tool_name, args_raw, tools)

            # If args are empty, try fallback from content
            if not tool_args and content:
                fallback = _extract_tool_call_from_content(content)
                if fallback and fallback["name"]:
                    tool_name = fallback["name"]
                    tool_args = fallback["args"]
                    tool_id = fallback["id"]

        elif content:
            # No structured tool_calls - try fallback from content
            fallback = _extract_tool_call_from_content(content)
            if fallback and fallback["name"]:
                tool_name = fallback["name"]
                tool_args = fallback["args"]
                tool_id = fallback["id"]
                tool_calls = [{
                    "id": tool_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": json.dumps(tool_args)},
                }]

        # No tool call found - check if it's a final text response
        if not tool_name:
            if content and '{"tool_calls"' not in content:
                print(f"\n  Result:\n{content}\n")
            elif content:
                print(f"\n  Model returned unparseable tool call.", file=sys.stderr)
                print(f"  Raw: {content[:200]}", file=sys.stderr)
            else:
                print("\n  Model returned empty response.", file=sys.stderr)
            return

        # Validate tool exists
        if not tool_exists(tool_name, tools):
            available = ", ".join(sorted(tools.keys()))
            print(f"  [{step}] Unknown tool: {tool_name} (available: {available})", file=sys.stderr)
            error_msg = f"Error: tool '{tool_name}' does not exist. Available tools: {available}. Use run_cmd for shell commands."
            assistant_msg = {"role": "assistant", "content": None, "tool_calls": tool_calls}
            tool_msg = {"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": error_msg}
            exchanges.append((assistant_msg, tool_msg))
            continue

        # Display
        args_display = json.dumps(tool_args, ensure_ascii=False)
        if len(args_display) > 120:
            args_display = args_display[:120] + "..."
        print(f"  [{step}] {tool_name}({args_display})", file=sys.stderr)

        # Execute
        start = time.time()
        result = execute_tool(tool_name, tool_args, tools, auto_confirm, task)
        duration_ms = int((time.time() - start) * 1000)

        log_step(task, step, tool_name, tool_args, result, duration_ms)

        result_preview = result[:200].replace("\n", " ")
        if len(result) > 200:
            result_preview += "..."
        print(f"       -> {result_preview}", file=sys.stderr)

        assistant_msg = {"role": "assistant", "content": None, "tool_calls": tool_calls}
        tool_msg = {"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": result}
        exchanges.append((assistant_msg, tool_msg))

        if tool_name == "create_tool" and "successfully" in result:
            tools = get_all_tools()
            tool_defs = get_tool_definitions(tools)

    else:
        print(f"\n  Reached max steps ({MAX_STEPS}).", file=sys.stderr)
