"""Regression tests for agent.py."""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_output_structure():
    """Test that agent.py outputs valid JSON with required fields.

    This test runs agent.py as a subprocess with a simple question,
    parses the stdout JSON, and verifies that:
    - The output is valid JSON
    - The 'answer' field exists and is a non-empty string
    - The 'tool_calls' field exists and is an array
    """
    # Run agent.py with a simple test question
    agent_path = Path(__file__).parent.parent / "agent.py"
    question = "What does HTTP stand for?"

    result = subprocess.run(
        [sys.executable, str(agent_path), question],
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"

    # Check stdout is not empty
    assert result.stdout.strip(), "Agent produced no output"

    # Parse JSON
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e

    # Check 'answer' field exists and is non-empty
    assert "answer" in data, "Missing 'answer' field in output"
    assert isinstance(data["answer"], str), "'answer' must be a string"
    assert len(data["answer"]) > 0, "'answer' must not be empty"

    # Check 'tool_calls' field exists and is an array
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be an array"
