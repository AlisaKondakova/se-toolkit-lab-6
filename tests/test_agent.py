"""Regression tests for agent.py."""

import json
import subprocess
import sys
from pathlib import Path


def run_agent(question: str, timeout: int = 60) -> dict:
    """Run agent.py with a question and return parsed JSON response.
    
    Args:
        question: The question to ask the agent
        timeout: Timeout in seconds
        
    Returns:
        Parsed JSON response dict
        
    Raises:
        AssertionError: On agent errors
    """
    agent_path = Path(__file__).parent.parent / "agent.py"
    
    result = subprocess.run(
        [sys.executable, str(agent_path), question],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    assert result.stdout.strip(), "Agent produced no output"
    
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e
    
    return data


def test_agent_output_structure():
    """Test that agent.py outputs valid JSON with required fields.
    
    This test runs agent.py as a subprocess with a simple question,
    parses the stdout JSON, and verifies that:
    - The output is valid JSON
    - The 'answer' field exists and is a non-empty string
    - The 'tool_calls' field exists and is an array
    """
    question = "What does HTTP stand for?"
    data = run_agent(question)
    
    assert "answer" in data, "Missing 'answer' field in output"
    assert isinstance(data["answer"], str), "'answer' must be a string"
    assert len(data["answer"]) > 0, "'answer' must not be empty"
    
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be an array"
    
    assert "source" in data, "Missing 'source' field in output"


def test_merge_conflict_question():
    """Test that agent uses read_file to answer merge conflict question.
    
    Question: "How do you resolve a merge conflict?"
    Expected:
    - read_file in tool_calls
    - wiki/git-workflow.md in source
    """
    question = "How do you resolve a merge conflict?"
    data = run_agent(question)
    
    tools_used = [tc.get("tool") for tc in data.get("tool_calls", [])]
    assert "read_file" in tools_used, f"Expected read_file in tool_calls, got: {tools_used}"

    source = data.get("source", "")
    assert "git-workflow.md" in source.lower(), f"Expected git-workflow.md in source, got: {source}"


def test_wiki_listing_question():
    """Test that agent uses list_files to answer wiki listing question.
    
    Question: "What files are in the wiki?"
    Expected:
    - list_files in tool_calls
    - source referencing wiki directory
    """
    question = "What files are in the wiki?"
    data = run_agent(question)
    
    tools_used = [tc.get("tool") for tc in data.get("tool_calls", [])]
    assert "list_files" in tools_used, f"Expected list_files in tool_calls, got: {tools_used}"
    
    source = data.get("source", "")
    answer = data.get("answer", "")
    assert "wiki" in source.lower() or "wiki" in answer.lower(), \
        f"Expected wiki reference in source or answer, got source={source}, answer={answer[:100]}"

