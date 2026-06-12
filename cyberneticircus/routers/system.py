"""
Router: system — 2 host-side utility endpoints.
  - file/read    →  GET /api/file/read       (read a file under the scratch workspace)
  - execute_host_command    →  POST /api/execute_host_command    (run a shell command)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lib import system as lib_system
from lib import logs as lib_logs


router = APIRouter()


class ExecuteHostCommandRequest(BaseModel):
    command: str


@router.get("/file/read")
def read_file_endpoint(path: str):
    """Read a file under the scratch workspace (path-traversal-protected)."""
    try:
        return lib_system.read_scratch_file(path)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute_host_command")
def execute_host_command_endpoint(req: ExecuteHostCommandRequest):
    """Run a shell command in the project dir (60s timeout)."""
    lib_logs.log_agent_action("action", f"Executed shell command: {req.command}", [], [])
    try:
        return lib_system.execute_host_cmd(req.command)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shell command execution failed: {e}")
