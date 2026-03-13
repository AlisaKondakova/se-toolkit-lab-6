#!/usr/bin/env python3
"""Agent CLI - LLM-powered question answering.

Usage:
    uv run agent.py "What does REST stand for?"

Output (JSON to stdout):
    {"answer": "Representational State Transfer.", "tool_calls": []}

All debug/progress output goes to stderr.
"""

import json
import sys
from pathlib import Path

import httpx


def load_env() -> dict[str, str]:
    """Load environment variables from .env.agent.secret."""
    env_file = Path(__file__).parent / ".env.agent.secret"
    env_vars = {}

    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        sys.exit(1)

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env_vars[key] = value

    return env_vars


def call_llm(question: str, api_key: str, api_base: str, model: str, timeout: int = 60) -> str:
    """Call the LLM API and return the answer.

    Args:
        question: The user's question
        api_key: API key for authentication
        api_base: Base URL for the API (should include /v1)
        model: Model name to use
        timeout: Request timeout in seconds

    Returns:
        The LLM's answer as a string

    Raises:
        SystemExit: On API errors or timeouts
    """
    url = f"{api_base.rstrip('/').removesuffix('/v1')}/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer questions concisely and accurately.",
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }

    print(f"Calling LLM: {model}...", file=sys.stderr)

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract answer from OpenAI-compatible response
            choices = data.get("choices", [])
            if not choices:
                print("Error: No choices in LLM response", file=sys.stderr)
                sys.exit(1)

            answer = choices[0].get("message", {}).get("content", "")
            if not answer:
                print("Error: Empty answer from LLM", file=sys.stderr)
                sys.exit(1)

            return answer.strip()

    except httpx.TimeoutException:
        print(f"Error: LLM request timed out after {timeout}s", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error: HTTP {e.response.status_code} from LLM API", file=sys.stderr)
        print(f"Response: {e.response.text[:200]}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Error: Cannot connect to LLM API: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    # Parse command-line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load configuration
    env = load_env()
    api_key = env.get("LLM_API_KEY")
    api_base = env.get("LLM_API_BASE")
    model = env.get("LLM_MODEL", "qwen3-coder-plus")

    if not api_key:
        print("Error: LLM_API_KEY not set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    if not api_base:
        print("Error: LLM_API_BASE not set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    # Call LLM and get answer
    answer = call_llm(question, api_key, api_base, model)

    # Build response
    response = {
        "answer": answer,
        "tool_calls": [],
    }

    # Output JSON to stdout
    print(json.dumps(response))


if __name__ == "__main__":
    main()
