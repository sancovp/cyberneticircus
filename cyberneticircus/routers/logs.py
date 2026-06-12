"""
Router: logs — the in-memory agent trace ring buffer (read by the visualizer's log panel).
The buffer is per-process state in lib/logs.py, not in the graph.
"""
from fastapi import APIRouter, HTTPException

from db_logic import get_driver
from lib import logs as lib_logs


router = APIRouter()


@router.get("/agent_logs")
def get_agent_logs_endpoint():
    """Return the recent log tail + the auto-detected active cybernet + its current step."""
    drv = get_driver()
    try:
        return lib_logs.get_agent_logs(drv)
    except Exception:
        # logs endpoint should never crash the visualizer — return empty state
        return {
            "logs": list(lib_logs.agent_trace_logs),
            "active_cybernet": "",
            "active_step_id": None,
            "active_focus_nodes": list(lib_logs.active_focus_nodes),
            "active_focus_labels": list(lib_logs.active_focus_labels),
        }
