# Task 3: The System Agent

## Overview

Extend the documentation agent from Task 2 with a new `query_api` tool that can call the deployed backend API. This enables the agent to answer:
1. Static system facts (framework, ports, status codes)
2. Data-dependent queries (item count, scores, analytics)

## LLM Provider and Model

**Provider:** Qwen Code API  
**Model:** `qwen3-coder-plus`

## New Tool: query_api

### Schema

```json
{
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
```

### Implementation

```python
def tool_query_api(method: str, path: str, body: str | None = None) -> str:
    """Call the backend API with authentication."""
    api_key = os.environ.get("LMS_API_KEY")
    base_url = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }
    
    url = f"{base_url.rstrip('/')}{path}"
    
    response = httpx.request(method, url, headers=headers, json=body)
    
    return json.dumps({
        "status_code": response.status_code,
        "body": response.text
    })
```

### Authentication

- Uses `LMS_API_KEY` from `.env.docker.secret` (not `LLM_API_KEY`)
- Sent as `X-API-Key` header
- `AGENT_API_BASE_URL` defaults to `http://localhost:42002`

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Backend URL (optional) | `.env.docker.secret` or default |

## System Prompt Update

The system prompt must guide the LLM to choose the right tool:

```
You are a system agent with access to:
1. list_files - Discover project files
2. read_file - Read file contents
3. query_api - Call the deployed backend API

Tool selection guide:
- Use list_files/read_file for: wiki questions, source code analysis, configuration
- Use query_api for: live data queries, testing endpoints, status codes, counts

For API calls:
- GET /items/ to list items
- GET /analytics/completion-rate?lab=lab-XX for analytics
- Always include X-API-Key header (handled automatically)
```

## Agentic Loop

Same as Task 2, but with 3 tools now:
1. Send question + all 3 tool schemas to LLM
2. Execute tool calls, feed results back
3. Max 10 iterations
4. Output JSON with answer, source (optional), tool_calls

## Output Format

```json
{
  "answer": "There are 42 items in the database.",
  "source": "",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": [...]}"
    }
  ]
}
```

Note: `source` is now optional - system questions may not have wiki sources.

## Benchmark Strategy

The 10 local questions cover:
- 2 wiki lookup (read_file)
- 2 source code analysis (read_file, list_files)
- 2 API data queries (query_api)
- 2 API error diagnosis (query_api + read_file)
- 2 reasoning questions (LLM judge)

### Iteration Process

1. Run `uv run run_eval.py`
2. Analyze failures:
   - Wrong tool: improve system prompt
   - Tool error: fix implementation
   - Wrong answer: adjust prompt or add hints
3. Re-run until all pass

## Implementation Steps

1. Add `query_api` tool schema to `TOOL_SCHEMAS`
2. Implement `tool_query_api` function with auth
3. Update system prompt with tool selection guidance
4. Load `LMS_API_KEY` and `AGENT_API_BASE_URL` from env
5. Test with sample API questions
6. Run `run_eval.py` and iterate
7. Update AGENT.md with lessons learned
8. Add 2 regression tests
