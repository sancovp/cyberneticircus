"""
Router: commands — list the entry-point TraversalSteps (the available procedures).
This is the 3rd of the 3 MCP tools (the other 2 are query_database + development_server,
which live outside the FastAPI app).
"""
from fastapi import APIRouter

from db_logic import get_driver
from lib import commands as lib_commands, logs as lib_logs


router = APIRouter()


@router.get("/commands")
def get_commands_api():
    """List all entry-point TraversalSteps — these are the procedures the LLM can start."""
    try:
        result = lib_commands.list_entry_steps(get_driver())
        lib_logs.log_agent_action("system", "Retrieved available commands/traversal flows", [], ["TraversalStep"])
        return result
    except Exception as e:
        lib_logs.log_agent_action("error", f"Failed to retrieve commands: {e}", [], ["TraversalStep"])
        raise
