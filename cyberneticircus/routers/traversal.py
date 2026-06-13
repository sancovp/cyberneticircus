"""
Router: traversal — 7 endpoints for state machine flow + CRUD.
  - schema, progress, create_flow, create_transition, adjust_weight
  - crud_state_machine_calls, crud_surrogate (SurrogateModel + SimulationRun)

Thin facade per the APIRouter pattern. Each endpoint body is a 1-line delegation
to lib/<module>.py.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db_logic import get_driver
from lib import traversal as lib_traversal
from lib import logs as lib_logs


router = APIRouter()


# --- Pydantic request models -------------------------------------------------

class ProgressRequest(BaseModel):
    cybernet_name: str
    answer: Optional[str] = None


class CreateFlowRequest(BaseModel):
    steps: List[Dict[str, Any]]
    trigger_node_label: Optional[str] = None
    trigger_node_properties: Optional[Dict[str, Any]] = None


class CreateTransitionRequest(BaseModel):
    from_step_id: str
    to_step_id: str
    weight: float = 1.0
    description: str = ""


class AdjustWeightRequest(BaseModel):
    from_step_id: str
    to_step_id: str
    success: bool
    cybernet_name: str


class CrudSurrogateRequest(BaseModel):
    action: str
    parameters: Optional[Dict[str, Any]] = None


class CrudStateMachineCallsRequest(BaseModel):
    action: str
    from_step_id: str
    to_state_machine_id: str


# --- Endpoints ---------------------------------------------------------------

@router.get("/schema")
def get_schema_endpoint():
    """Database labels / relationships / properties dump (for the visualizer's schema panel)."""
    try:
        lib_logs.log_agent_action("system", "Scanned database schema", [], [])
        return lib_traversal.get_schema(get_driver())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/traversal/progress")
def progress_endpoint(req: ProgressRequest):
    """Advance the active :ExecutionState (read current step → evaluate → move NEXT_STEP).

    NB: this endpoint is part of the LLM-loop gate (see DESIGN.md §11.8). Until the
    runtime gating refactor in §11.8 is implemented, this endpoint is effectively a
    no-op because `lib/state_machines.py` cypher builders match the OLD pattern.
    """
    drv = get_driver()
    try:
        active_before = lib_traversal.get_active_step(drv, cybernet_name=req.cybernet_name)
        result = lib_traversal.progress_traversal(drv, cybernet_name=req.cybernet_name, answer=req.answer)
        active_after = lib_traversal.get_active_step(drv, cybernet_name=req.cybernet_name)
        focus_nodes = []
        if active_before and active_before.get("id"):
            focus_nodes.append(str(active_before["id"]))
        if active_after and active_after.get("id"):
            focus_nodes.append(str(active_after["id"]))
        lib_logs.log_agent_action("action", f"Progressed active step. Answer: {req.answer}", focus_nodes, ["TraversalStep"])
        return result
    except Exception as e:
        lib_logs.log_agent_action("error", f"Traversal progress failed: {e}", [], ["TraversalStep"])
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/traversal/create_flow")
def create_flow_endpoint(req: CreateFlowRequest):
    """MERGE a chain of TraversalSteps + NEXT_STEP edges + optional trigger attachment."""
    try:
        result = lib_traversal.create_flow(
            get_driver(), steps=req.steps,
            trigger_node_label=req.trigger_node_label,
            trigger_node_properties=req.trigger_node_properties,
        )
        step_ids = [s["id"] for s in req.steps]
        lib_logs.log_agent_action("success", f"Created Traversal Flow with steps: {', '.join(step_ids)}", step_ids, ["TraversalStep"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        lib_logs.log_agent_action("error", f"Failed to create traversal flow: {e}", [], [])
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/traversal/create_transition")
def create_transition_endpoint(req: CreateTransitionRequest):
    """Create or update a weighted NEXT_STEP edge between two existing TraversalSteps."""
    try:
        result = lib_traversal.create_transition(
            get_driver(),
            from_step_id=req.from_step_id, to_step_id=req.to_step_id,
            weight=req.weight, description=req.description,
        )
        lib_logs.log_agent_action("success", f"Created transition from '{req.from_step_id}' to '{req.to_step_id}' (weight {req.weight})", [req.from_step_id, req.to_step_id], ["TraversalStep"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        lib_logs.log_agent_action("error", f"Failed to create transition: {e}", [req.from_step_id, req.to_step_id], ["TraversalStep"])
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/traversal/adjust_weight")
def adjust_weight_endpoint(req: AdjustWeightRequest):
    """Nudge a NEXT_STEP edge weight (up on success, down on fail — reinforcement learning)."""
    try:
        msg = lib_traversal.adjust_weight(
            get_driver(),
            from_step_id=req.from_step_id, to_step_id=req.to_step_id, success=req.success,
            cybernet_name=req.cybernet_name,
        )
        lib_logs.log_agent_action("success", f"Adjusted transition weight between '{req.from_step_id}' and '{req.to_step_id}' (success: {req.success})", [req.from_step_id, req.to_step_id], ["TraversalStep"])
        return {"message": msg}
    except Exception as e:
        lib_logs.log_agent_action("error", f"Failed to adjust transition weight: {e}", [req.from_step_id, req.to_step_id], ["TraversalStep"])
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crud_state_machine_calls")
def crud_state_machine_calls_endpoint(req: CrudStateMachineCallsRequest):
    """Create or delete a CALLS_SM edge from a TraversalStep to a sub-StateMachine."""
    try:
        return lib_traversal.crud_state_machine_calls(
            get_driver(), action=req.action,
            from_step_id=req.from_step_id, to_state_machine_id=req.to_state_machine_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        lib_logs.log_agent_action("error", f"Compiler call action failed: {e}", [], ["TraversalStep", "StateMachine"])
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crud_surrogate")
def crud_surrogate_endpoint(req: CrudSurrogateRequest):
    """Dispatch a SurrogateModel CRUD action: create|update|read|delete|simulate|calibrate."""
    try:
        return lib_traversal.crud_surrogate(
            get_driver(), action=req.action, parameters=req.parameters,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        lib_logs.log_agent_action("error", f"SurrogateModel action failed: {e}", [], ["SurrogateModel"])
        raise HTTPException(status_code=500, detail=str(e))
