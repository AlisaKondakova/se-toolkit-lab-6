# Task 1: Call an LLM from Code

## LLM Provider and Model

**Provider:** Qwen Code API  
**Model:** `qwen3-coder-plus`

### Why Qwen Code?
- 1000 free requests per day
- Works from Russia without restrictions
- No credit card required
- OpenAI-compatible API (easy integration)
- Strong tool calling capabilities (needed for Task 2-3)

### Configuration
The agent reads credentials from `.env.agent.secret`:
- `LLM_API_KEY` - API key for authentication
- `LLM_API_BASE` - Base URL (e.g., `http://<vm-ip>:<port>/v1`)
- `LLM_MODEL` - Model name (`qwen3-coder-plus`)

## Agent Architecture

### Input/Output Flow
```
CLI argument (question) → agent.py → LLM API → JSON response → stdout
```

### Components

1. **Argument Parsing**
   - Read question from `sys.argv[1]`
   - Validate input exists

2. **Environment Loading**
   - Load `.env.agent.secret` using manual parsing
   - Extract `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

3. **LLM Client**
   - Use `httpx` (already in dependencies) for async HTTP
   - Call OpenAI-compatible `/chat/completions` endpoint
   - Send system prompt + user question
   - Parse response to extract answer

4. **Response Formatting**
   - Build JSON: `{"answer": "<text>", "tool_calls": []}`
   - Output to stdout (single line)
   - All debug/progress to stderr

### Error Handling
- Timeout: 60 seconds max for API call
- Network errors: exit with non-zero code, error to stderr
- Invalid response: exit with non-zero code

### Testing Strategy
- Subprocess test: run `agent.py "test question"`
- Parse stdout JSON
- Verify `answer` field exists and is non-empty
- Verify `tool_calls` field exists and is array

## Implementation Steps
1. Create `.env.agent.secret` with real credentials
2. Write `agent.py` with LLM integration
3. Test manually with sample questions
4. Write regression test in `tests/test_agent.py`
5. Create `AGENT.md` documentation

