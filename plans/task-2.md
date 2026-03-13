# Task 2: The Documentation Agent

## Overview

Transform the CLI from Task 1 into an agentic system that can read project documentation. The agent will have two tools (`read_file`, `list_files`) and an agentic loop that allows it to discover and read wiki files to answer questions.

## LLM Provider and Model

**Provider:** Qwen Code API  
**Model:** `qwen3-coder-plus`

Same as Task 1 - supports function calling natively.

## Tool Definitions

### read_file

Read a file from the project repository.

**Schema:**
```json
{
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
```

**Implementation:**
- Read file using `Path.read_text()`
- Security: validate path doesn't contain `..` or absolute paths
- Resolve to absolute path and verify it's within project root
- Return file contents or error message

### list_files

List files and directories at a given path.

**Schema:**
```json
{
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
```

**Implementation:**
- Use `Path.iterdir()` to list entries
- Security: same path validation as `read_file`
- Return newline-separated list of filenames

## Path Security

Both tools must prevent directory traversal attacks:

1. Reject paths starting with `/` (absolute paths)
2. Reject paths containing `..` (parent directory traversal)
3. Resolve the full path and verify it's within project root using `is_relative_to()`

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

## Agentic Loop

The agent follows this loop:

```
Question → LLM (with tool schemas) → tool_call?
    │
    ├─ yes → Execute tool → Append result as tool message → Back to LLM
    │
    └─ no  → Final answer → Extract answer + source → Output JSON
```

### Loop Implementation

```python
MAX_TOOL_CALLS = 10
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": question}
]
tool_calls_log = []

for _ in range(MAX_TOOL_CALLS):
    response = call_llm(messages, tools=TOOL_SCHEMAS)
    
    if response has tool_calls:
        for tool_call in tool_calls:
            result = execute_tool(tool_call)
            tool_calls_log.append({
                "tool": tool_call.name,
                "args": tool_call.args,
                "result": result
            })
            messages.append({"role": "tool", "content": result})
    else:
        answer = extract_answer(response)
        source = extract_source(response)
        break
```

## System Prompt Strategy

The system prompt should guide the LLM to:

1. Use `list_files` to discover wiki files
2. Use `read_file` to find relevant information
3. Include source references (file path + section anchor)
4. Stop calling tools when enough information is gathered

```
You are a documentation agent. You have access to two tools:
- list_files: List files in a directory
- read_file: Read a file's contents

To answer questions:
1. First use list_files to discover relevant wiki files
2. Use read_file to read the content of relevant files
3. Find the specific section that answers the question
4. Include the source as: wiki/filename.md#section-anchor

Always provide accurate source references based on what you read.
```

## Output Format

```json
{
  "answer": "The answer text from the LLM",
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

## Error Handling

- Tool errors: return error message as tool result, continue loop
- LLM errors: exit with error code, message to stderr
- Max tool calls reached: use whatever answer is available
- Invalid paths: return error message, don't crash

## Testing Strategy

Two regression tests:

1. **Merge conflict question**: "How do you resolve a merge conflict?"
   - Expects: `read_file` in tool_calls
   - Expects: `wiki/git-workflow.md` in source

2. **Wiki listing question**: "What files are in the wiki?"
   - Expects: `list_files` in tool_calls
   - Expects: source referencing wiki directory

## Implementation Steps

1. Define `TOOL_SCHEMAS` for OpenAI function calling
2. Implement `read_file` and `list_files` functions with path security
3. Implement `execute_tool` dispatcher
4. Implement agentic loop in `main()`
5. Update output JSON to include `source` and populated `tool_calls`
6. Write system prompt
7. Add regression tests
8. Update AGENT.md documentation
