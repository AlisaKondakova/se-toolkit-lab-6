# Agent Documentation

## Overview

`agent.py` is a CLI tool that connects to an LLM (Large Language Model) and answers questions by reading project documentation. It uses an **agentic loop** with tools (`read_file`, `list_files`) to discover and read wiki files, then provides answers with source references.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  CLI Argument   │ ──► │   agent.py   │ ──► │  LLM API    │
│  (question)     │     │  (agentic    │     │  (tools +   │
│                 │     │   loop)      │     │   chat)     │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  Tool Calls  │
                        │  (read_file, │
                        │   list_files)│
                        └──────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  JSON Output │
                        │  (stdout)    │
                        └──────────────┘
```

### Agentic Loop

```
Question ──▶ LLM ──▶ tool call? ──yes──▶ execute tool ──▶ back to LLM
                     │
                     no
                     │
                     ▼
                JSON output
```

1. Send user question + tool schemas to LLM
2. If LLM responds with `tool_calls` → execute each tool, append results as tool messages, go to step 1
3. If LLM responds with text (no tool calls) → final answer, output JSON and exit
4. Maximum 10 tool calls per question

## LLM Provider

**Provider:** Qwen Code API  
**Model:** `qwen3-coder-plus`

### Why Qwen Code?
- 1000 free requests per day
- No credit card required
- Works from Russia
- OpenAI-compatible API with function calling support
- Strong tool calling capabilities

### Alternative: OpenRouter
If Qwen Code is unavailable, OpenRouter provides free models:
- `meta-llama/llama-3.3-70b-instruct:free`
- `qwen/qwen3-coder:free`

**Note:** OpenRouter free tier has a 50 requests/day limit.

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
uv run agent.py "How do you resolve a merge conflict?"
```

### Output

The agent outputs a single JSON line to stdout:

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's answer to the question |
| `source` | string | Wiki section reference (e.g., `wiki/git-workflow.md#section`) |
| `tool_calls` | array | List of tool calls made during the agentic loop |

### Tool Call Entry

| Field | Type | Description |
|-------|------|-------------|
| `tool` | string | Tool name (`read_file` or `list_files`) |
| `args` | object | Arguments passed to the tool |
| `result` | string | Tool output (file contents or directory listing) |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing config, API error, timeout) |

## Tools

### read_file

Read the contents of a file from the project.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as a string, or an error message if the file doesn't exist.

**Security:**
- Rejects absolute paths
- Rejects paths containing `..` (directory traversal)
- Verifies resolved path is within project root

### list_files

List files and directories in a directory.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries, or an error message.

**Security:**
- Same path validation as `read_file`

## System Prompt

The agent uses this system prompt to guide the LLM:

```
You are a documentation agent that answers questions by reading project files.

You have access to two tools:
1. list_files - List files and directories in a given path
2. read_file - Read the contents of a file

To answer questions:
1. Use list_files to discover relevant wiki files (start with "wiki" directory)
2. Use read_file to read the content of relevant files
3. Find the specific section that answers the question
4. Include the source as: wiki/filename.md#section-anchor

Always provide accurate source references based on what you read.
When you have enough information, provide your final answer without calling more tools.
```

## Implementation Details

### Request Flow

1. **Parse Input**: Read question from `sys.argv[1]`
2. **Load Config**: Read `.env.agent.secret` for API credentials
3. **Initialize Messages**: System prompt + user question
4. **Agentic Loop** (max 10 iterations):
   - Call LLM with messages + tool schemas
   - If tool calls: execute each, append results, continue
   - If no tool calls: extract answer, break
5. **Extract Source**: Parse answer for `wiki/...` pattern or infer from last `read_file`
6. **Output JSON**: Print result to stdout

### HTTP Request

```python
POST /v1/chat/completions
Headers:
  Content-Type: application/json
  Authorization: Bearer <LLM_API_KEY>
Body:
{
  "model": "qwen3-coder-plus",
  "messages": [...],
  "tools": [
    {"type": "function", "function": {...}},  # read_file
    {"type": "function", "function": {...}}   # list_files
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### Path Security

```python
def safe_path(relative_path: str) -> Path:
    """Validate and resolve a relative path safely."""
    if relative_path.startswith('/') or '..' in relative_path:
        raise ValueError("Invalid path")
    full_path = (PROJECT_ROOT / relative_path).resolve()
    if not full_path.is_relative_to(PROJECT_ROOT):
        raise ValueError("Path outside project root")
    return full_path
```

### Error Handling

- **Missing config**: Exit 1, error to stderr
- **Timeout (>60s)**: Exit 1, error to stderr
- **HTTP error**: Exit 1, status code and response to stderr
- **Network error**: Exit 1, error description to stderr
- **Tool error**: Return error message as tool result, continue loop
- **Max tool calls**: Use whatever answer is available

### Output Rules

- **stdout**: Only valid JSON (for parsing by other tools)
- **stderr**: All debug/progress/error messages

## Testing

### Manual Testing

```bash
uv run agent.py "How do you resolve a merge conflict?"

uv run agent.py "What files are in the wiki?"
```

### Automated Testing

Run the regression tests:

```bash
uv run pytest tests/test_agent.py -v
```

Tests verify:
- Agent produces valid JSON
- `answer`, `source`, and `tool_calls` fields exist
- Tools are called correctly for specific questions

## Dependencies

- `httpx` - HTTP client for API calls
- Python 3.10+

## File Structure

```
se-toolkit-lab-6/
├── agent.py              # Main agent CLI with agentic loop
├── .env.agent.secret     # LLM credentials (gitignored)
├── .env.agent.example    # Example configuration
├── AGENT.md              # This documentation
├── plans/
│   ├── task-1.md         # Task 1 implementation plan
│   └── task-2.md         # Task 2 implementation plan
└── tests/
    └── test_agent.py     # Regression tests
```

## Task History

### Task 1: Call an LLM from Code
- Basic CLI that sends questions to LLM
- Returns JSON with `answer` and empty `tool_calls`

### Task 2: The Documentation Agent (current)
- Added `read_file` and `list_files` tools
- Implemented agentic loop
- Returns JSON with `answer`, `source`, and populated `tool_calls`

### Future Tasks
- **Task 3**: Additional tools (query_api, etc.) and enhanced agentic reasoning
- **Task 4+**: Domain knowledge and advanced capabilities

