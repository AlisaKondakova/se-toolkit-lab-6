# Agent Documentation

## Overview

`agent.py` is a CLI tool that connects to an LLM (Large Language Model) and answers questions. It forms the foundation for the agentic system that will be extended with tools and an agentic loop in subsequent tasks.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  CLI Argument   │ ──► │   agent.py   │ ──► │  LLM API    │ ──► │  JSON Output │
│  (question)     │     │  (parser +   │     │  (HTTP POST)│     │  (stdout)    │
│                 │     │   client)    │     │             │     │              │
└─────────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

## LLM Provider

**Provider:** Qwen Code API  
**Model:** `qwen3-coder-plus`

### Why Qwen Code?
- 1000 free requests per day
- No credit card required
- Works from Russia
- OpenAI-compatible API
- Strong tool calling capabilities

### Alternative: OpenRouter
If Qwen Code is unavailable, OpenRouter provides free models:
- `meta-llama/llama-3.3-70b-instruct:free`
- `qwen/qwen3-coder:free`

**Note:** OpenRouter free tier has a 50 requests/day limit and may experience rate limiting.

## Configuration

Create `.env.agent.secret` in the project root:

```bash
cp .env.agent.example .env.agent.secret
```

Edit the file with your credentials:

```env
LLM_API_KEY=your-api-key-here
LLM_API_BASE=http://<vm-ip>:<port>/v1
LLM_MODEL=qwen3-coder-plus
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for authentication | `sk-...` |
| `LLM_API_BASE` | Base URL of the LLM API | `http://192.168.1.100:8000/v1` |
| `LLM_MODEL` | Model name to use | `qwen3-coder-plus` |

## Usage

### Basic Usage

```bash
uv run agent.py "What does REST stand for?"
```

### Output

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's answer to the question |
| `tool_calls` | array | List of tool calls (empty in Task 1) |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing config, API error, timeout) |

## Implementation Details

### Request Flow

1. **Parse Input**: Read question from `sys.argv[1]`
2. **Load Config**: Read `.env.agent.secret` for API credentials
3. **Call LLM**: POST to `/v1/chat/completions` endpoint
4. **Parse Response**: Extract answer from LLM response
5. **Output JSON**: Print result to stdout

### HTTP Request

```python
POST /v1/chat/completions
Headers:
  Content-Type: application/json
  Authorization: Bearer <LLM_API_KEY>
Body:
{
  "model": "qwen3-coder-plus",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "<question>"}
  ],
  "temperature": 0.7,
  "max_tokens": 500
}
```

### Error Handling

- **Missing config**: Exit 1, error to stderr
- **Timeout (>60s)**: Exit 1, error to stderr
- **HTTP error**: Exit 1, status code and response to stderr
- **Network error**: Exit 1, error description to stderr

### Output Rules

- **stdout**: Only valid JSON (for parsing by other tools)
- **stderr**: All debug/progress/error messages

## Testing

### Manual Testing

```bash
# Test with a simple question
uv run agent.py "What is HTTP?"

# Test with a complex question
uv run agent.py "Explain the difference between REST and GraphQL"
```

### Automated Testing

Run the regression test:

```bash
uv run pytest tests/test_agent.py -v
```

The test verifies:
- Agent produces valid JSON
- `answer` field exists and is non-empty
- `tool_calls` field exists and is an array

## Dependencies

- `httpx` - HTTP client for API calls
- Python 3.10+

## File Structure

```
se-toolkit-lab-6/
├── agent.py              # Main agent CLI
├── .env.agent.secret     # LLM credentials (gitignored)
├── .env.agent.example    # Example configuration
├── AGENT.md              # This documentation
├── plans/
│   └── task-1.md         # Implementation plan
└── tests/
    └── test_agent.py     # Regression tests
```

## Extending the Agent

In upcoming tasks, the agent will be extended with:

- **Task 2**: Tool definitions and execution
- **Task 3**: Agentic loop (plan → act → observe → repeat)
- **Task 4+**: Domain knowledge and advanced capabilities
