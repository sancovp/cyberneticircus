"""
System utilities — host file read + shell command execution.
Both run on the host terminal, not in the graph.

Compositions:
  - read_scratch_file  →  GET /api/file/read
  - execute_host_cmd   →  POST /api/execute_host_command
"""
from __future__ import annotations
import os
import subprocess
from typing import Any, Dict


DEFAULT_SCRATCH_DIR = "/Users/isaacwr/.gemini/antigravity/scratch"
DEFAULT_PROJECT_DIR = "/Users/isaacwr/.gemini/antigravity/scratch/cyberneticircus"


def read_scratch_file(path: str) -> Dict[str, Any]:
    """Read a file under the scratch workspace (security: must be inside it)."""
    allowed_prefix = os.environ.get("SCRATCH_WORKSPACE_DIR", DEFAULT_SCRATCH_DIR)
    normalized = os.path.abspath(path)
    if not normalized.startswith(allowed_prefix):
        raise PermissionError(f"path '{path}' is outside the allowed workspace '{allowed_prefix}'")
    if not os.path.exists(normalized):
        raise FileNotFoundError(normalized)
    with open(normalized, "r", encoding="utf-8") as f:
        return {"content": f.read()}


def execute_host_cmd(command: str, *, cwd: str = None, timeout: int = 60) -> Dict[str, Any]:
    """Run a shell command in the project dir. Returns stdout+stderr."""
    project_dir = cwd or os.environ.get("PROJECT_DIR", DEFAULT_PROJECT_DIR)
    res = subprocess.run(command, shell=True, cwd=project_dir, capture_output=True, text=True, timeout=timeout)
    output = []
    if res.stdout:
        output.append(res.stdout)
    if res.stderr:
        output.append(f"STDERR:\n{res.stderr}")
    if not output:
        return {"output": f"Command finished with exit code {res.returncode} (no output)."}
    return {"output": "\n".join(output)}
