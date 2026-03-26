"""HTTP client for apfel's OpenAI-compatible API."""

import subprocess
import sys
import time

import httpx

BASE_URL = "http://127.0.0.1:11434"
TIMEOUT = 60.0


def health_check() -> bool:
    """Check if apfel --serve is running."""
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=3)
        return resp.status_code == 200
    except httpx.ConnectError:
        return False


def ensure_server() -> None:
    """Start apfel --serve if not running. Blocks until ready."""
    if health_check():
        return

    print("Starting apfel --serve...", file=sys.stderr)
    subprocess.Popen(
        ["apfel", "--serve", "--port", "11434"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(20):
        time.sleep(0.5)
        if health_check():
            print("Server ready.", file=sys.stderr)
            return

    print("Error: apfel --serve failed to start.", file=sys.stderr)
    sys.exit(1)


def chat_completion(messages: list, tools: list) -> dict:
    """Send a chat completion request with tools. Returns parsed JSON."""
    payload = {
        "model": "apple-foundationmodel",
        "messages": messages,
        "tools": tools,
        "stream": False,
    }
    resp = httpx.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        timeout=TIMEOUT,
    )
    data = resp.json()

    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))

    return data
