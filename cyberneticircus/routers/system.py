"""
Router: system — 2 host-side utility endpoints.
  - file/read    →  GET /api/file/read       (read a file under the scratch workspace)
  - execute_host_command    →  POST /api/execute_host_command    (run a shell command)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lib import system as lib_system
from lib import logs as lib_logs
from lib import projector as lib_projector
from db_logic import get_driver


router = APIRouter()


@router.get("/context/{cybernet_name}")
def get_context_endpoint(cybernet_name: str):
    """Project a being's context (read-only, DESIGN §13.5): the core-loop-prime
    rendered from its live Core Chain stack + any active COMP MAP rules. The
    describe()-analog / the tick's context-assembly step (PULL from the graph)."""
    try:
        return lib_projector.assemble_context(get_driver(), name=cybernet_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
