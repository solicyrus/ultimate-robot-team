import os
import subprocess
import glob

def read_file(filepath):
    """Reads the contents of a file."""
    try:
        with open(filepath, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading {filepath}: {str(e)}"

def write_file(filepath, content):
    """Writes content to a file."""
    try:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing {filepath}: {str(e)}"

def search_code(pattern, directory="."):
    """Basic text search across Python files in the directory."""
    results = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") or file.endswith(".md"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r") as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if pattern in line:
                                results.append(f"{path}:{i+1}: {line.strip()}")
                except Exception:
                    pass
    return "\n".join(results) if results else "No matches found."

def run_tests(test_path="."):
    """Runs pytest on the specified path."""
    return run_shell(f"pytest {test_path}")

def git_diff():
    """Shows what has changed in the working tree (unstaged + untracked summary).

    Runs git directly with argument lists (no shell), so there is no shell
    parsing or operator injection surface at all.
    """
    try:
        diff = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30
        )
        status = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            timeout=30
        )
        combined = f"--- git status --short ---\n{status.stdout}\n--- git diff HEAD ---\n{diff.stdout}"
        if diff.stderr:
            combined += f"\nSTDERR (diff):\n{diff.stderr}"
        if status.stderr:
            combined += f"\nSTDERR (status):\n{status.stderr}"
        if len(combined) > 6000:
            combined = combined[:6000] + "\n... [truncated at 6000 chars]"
        return combined
    except subprocess.TimeoutExpired:
        return "Error: git command timed out after 30 seconds."
    except Exception as e:
        return f"Error running git diff/status: {str(e)}"

def run_shell(command):
    """Executes a shell command against a strict allowlist."""
    # Manager's security patch (Cyrus, 2026-10-26): a prefix allowlist alone is not
    # enough with shell=True — a command like "ls; <anything>" starts with an allowed
    # word yet smuggles a second command. Reject shell operators outright so exactly
    # ONE simple command can run.
    if any(ch in command for ch in ";&|`$()<>\n\\"):
        return "Security Error: Shell operators are not allowed; run one simple command."
    allowed_commands = ["python", "pytest", "pip list", "ls", "cat"]
    
    if not any(command.startswith(cmd) for cmd in allowed_commands):
        return f"Security Error: Command '{command}' is not in the allowlist."
        
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output or "Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def get_tools_schema():
    """Returns the JSON schema for OpenAI tool calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file in the repository.",
                "parameters": {
                    "type": "object",
                    "properties": {"filepath": {"type": "string"}},
                    "required": ["filepath"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write new content to a file, overwriting it entirely.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["filepath", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": "Search for a text pattern in codebase files (.py and .md).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "directory": {"type": "string"}
                    },
                    "required": ["pattern"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_tests",
                "description": "Run pytest on the repository or a specific path.",
                "parameters": {
                    "type": "object",
                    "properties": {"test_path": {"type": "string", "default": "."}}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "git_diff",
                "description": "Show the current working-tree changes (git status --short plus git diff HEAD), truncated to about 6000 chars. Use it to check your own work before finishing.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_shell",
                "description": "Run a shell command. Allowed: python, pytest, pip list, ls, cat.",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"]
                }
            }
        }
    ]

def execute_tool(name, kwargs):
    """Dispatches the tool call to the corresponding python function."""
    tools = {
        "read_file": read_file,
        "write_file": write_file,
        "search_code": search_code,
        "run_tests": run_tests,
        "git_diff": git_diff,
        "run_shell": run_shell
    }
    if name in tools:
        return tools[name](**kwargs)
    return f"Error: Tool {name} not found."
