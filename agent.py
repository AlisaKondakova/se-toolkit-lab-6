#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).parent.resolve()
MAX_TOOL_CALLS = 10

SYSTEM_PROMPT = """You are a system agent that answers questions by reading project files and querying the backend API.

You have access to three tools:
1. list_files - List files and directories in a given path
2. read_file - Read the contents of a file
3. query_api - Call the deployed backend API to get real-time data

Tool selection guide:
- Use list_files to discover project structure
- Use read_file for: wiki questions, source code analysis, configuration files, documentation
- Use query_api for: live data queries, testing endpoints, status codes, item counts, analytics

When using query_api:
- GET /items/ to list all items
- GET /items/{id} to get a specific item
- GET /analytics/completion-rate?lab=lab-XX for analytics
- GET /analytics/top-learners?lab=lab-XX for top learners
- The API key is automatically included

To answer questions:
1. Use list_files to discover relevant files (start with "wiki" or "backend" directories)
2. Use read_file to read file contents
3. Use query_api for live data or endpoint testing
4. Find the specific section that answers the question
5. Include the source as: wiki/filename.md#section-anchor or backend/path/file.py

Always provide accurate source references based on what you read.
When you have enough information, provide your final answer without calling more tools.
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the deployed backend API to get real-time data or test endpoints",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE)",
                        "enum": ["GET", "POST", "PUT", "DELETE"]
                    },
                    "path": {
                        "type": "string",
                        "description": "API path (e.g., /items/, /analytics/completion-rate)"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT"
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]


def load_env() -> dict[str, str]:
    env_file = PROJECT_ROOT / ".env.agent.secret"
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


def load_docker_env() -> dict[str, str]:
    env_file = PROJECT_ROOT / ".env.docker.secret"
    env_vars = {}

    if not env_file.exists():
        return env_vars

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


def safe_path(relative_path: str) -> Path:
    if not relative_path:
        raise ValueError("Path cannot be empty")
    
    if relative_path.startswith('/'):
        raise ValueError("Absolute paths not allowed")
    
    if '..' in relative_path:
        raise ValueError("Parent directory traversal not allowed")
    
    full_path = (PROJECT_ROOT / relative_path).resolve()
    
    try:
        full_path.relative_to(PROJECT_ROOT)
    except ValueError:
        raise ValueError(f"Path outside project root: {relative_path}")
    
    return full_path


def tool_read_file(path: str) -> str:
    try:
        safe = safe_path(path)
        if not safe.exists():
            return f"Error: File not found: {path}"
        if not safe.is_file():
            return f"Error: Not a file: {path}"
        return safe.read_text()
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def tool_list_files(path: str) -> str:
    try:
        safe = safe_path(path)
        if not safe.exists():
            return f"Error: Directory not found: {path}"
        if not safe.is_dir():
            return f"Error: Not a directory: {path}"
        
        entries = sorted([e.name for e in safe.iterdir()])
        return "\n".join(entries)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing directory: {e}"


def tool_query_api(method: str, path: str, body: str | None = None) -> str:
    docker_env = load_docker_env()
    api_key = os.environ.get("LMS_API_KEY", docker_env.get("LMS_API_KEY", ""))
    base_url = os.environ.get("AGENT_API_BASE_URL", docker_env.get("AGENT_API_BASE_URL", "http://localhost:42002"))
    
    headers = {
        "Content-Type": "application/json",
    }
    
    if api_key:
        headers["X-API-Key"] = api_key
    
    url = f"{base_url.rstrip('/')}{path.lstrip('/')}"
    
    try:
        request_body = None
        if body:
            try:
                request_body = json.loads(body)
            except json.JSONDecodeError:
                request_body = body
        
        response = httpx.request(method, url, headers=headers, json=request_body, timeout=30)
        
        return json.dumps({
            "status_code": response.status_code,
            "body": response.text
        })
    except httpx.TimeoutException:
        return json.dumps({"status_code": 0, "body": "Error: Request timed out"})
    except httpx.RequestError as e:
        return json.dumps({"status_code": 0, "body": f"Error: {str(e)}"})
    except Exception as e:
        return json.dumps({"status_code": 0, "body": f"Error: {str(e)}"})


def execute_tool(name: str, args: dict) -> str:
    if name == "read_file":
        return tool_read_file(args.get("path", ""))
    elif name == "list_files":
        return tool_list_files(args.get("path", ""))
    elif name == "query_api":
        return tool_query_api(
            args.get("method", "GET"),
            args.get("path", ""),
            args.get("body")
        )
    else:
        return f"Error: Unknown tool: {name}"


def call_llm(messages: list[dict], api_key: str, api_base: str, model: str, 
             tools: list[dict] | None = None, timeout: int = 60) -> dict:
    url = f"{api_base.rstrip('/').removesuffix('/v1')}/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
    }
    
    if tools:
        payload["tools"] = tools

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            if not choices:
                print("Error: No choices in LLM response", file=sys.stderr)
                sys.exit(1)

            message = choices[0].get("message", {})
            result = {
                "content": message.get("content"),
                "tool_calls": message.get("tool_calls", []),
            }
            return result

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


def run_agentic_loop(question: str, api_key: str, api_base: str, model: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    tool_calls_log: list[dict] = []
    last_answer: str | None = None
    
    for iteration in range(MAX_TOOL_CALLS):
        print(f"Iteration {iteration + 1}/{MAX_TOOL_CALLS}...", file=sys.stderr)
        
        response = call_llm(messages, api_key, api_base, model, tools=TOOL_SCHEMAS)
        
        tool_calls = response.get("tool_calls", [])
        
        if tool_calls:
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "unknown")
                args_str = func.get("arguments", "{}")
                
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    args = {}
                
                print(f"  Calling tool: {name}({args})", file=sys.stderr)
                result = execute_tool(name, args)
                
                tool_calls_log.append({
                    "tool": name,
                    "args": args,
                    "result": result,
                })
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                })
        else:
            last_answer = response.get("content") or ""
            print(f"Final answer received", file=sys.stderr)
            break
    else:
        print("Max tool calls reached, using last available answer", file=sys.stderr)
        if last_answer is None:
            last_answer = "Unable to complete the task within the tool call limit."
    
    source = ""
    if last_answer:
        match = re.search(r'(wiki/[\w-]+\.md(?:#[\w-]+)?)', last_answer)
        if match:
            source = match.group(1)
    
    if not source and tool_calls_log:
        for tc in reversed(tool_calls_log):
            if tc["tool"] == "read_file":
                path = tc["args"].get("path", "")
                if path:
                    source = path
                break
    
    return {
        "answer": last_answer or "",
        "source": source,
        "tool_calls": tool_calls_log,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

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

    response = run_agentic_loop(question, api_key, api_base, model)

    print(json.dumps(response))


if __name__ == "__main__":
    main()
