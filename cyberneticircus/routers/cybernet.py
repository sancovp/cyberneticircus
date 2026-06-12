"""
Router: cybernet — 9 endpoints for the Cybernet lifecycle.
  - create / equip / tick / list / state_machines / status / simulations
  - configure_ghost_shell / ghost_shell/status

Thin facade per the APIRouter pattern. Each endpoint body is a 1-line delegation
to lib/<module>.py. No business logic here.
"""
from __future__ import annotations
import re
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db_logic import get_driver
from engine import AgentLLMRunner
from lib import cybernet as lib_cybernet
from lib import ghost_shell as lib_ghost_shell
from lib import logs as lib_logs


router = APIRouter()


# --- Pydantic request models -------------------------------------------------

class CreateCybernetRequest(BaseModel):
    name: str
    description: str
    model_name: str = "minimax-M3"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    mutation_rate: float = 0.1
    selection_pressure: float = 1.0


class EquipRequest(BaseModel):
    character_name: str
    state_machine_id: str


class TickRequest(BaseModel):
    character_name: str
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class ConfigureGhostShellRequest(BaseModel):
    cybernet_name: str
    model_name: Optional[str] = None
    parameters_count: Optional[float] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


# --- Endpoints (1-line delegations) ----------------------------------------

@router.post("/create")
def create_endpoint(req: CreateCybernetRequest):
    """Create a new Cybernet + Identity + HAS_IDENTITY edge."""
    drv = get_driver()
    try:
        msg = lib_cybernet.create(
            drv,
            name=req.name, description=req.description, model_name=req.model_name,
            parameters_count=70.0, temperature=req.temperature, top_p=req.top_p,
            max_tokens=req.max_tokens, mutation_rate=req.mutation_rate,
            selection_pressure=req.selection_pressure,
        )
        lib_logs.log_agent_action("success", f"Compiled and spawned Cybernet Core '{req.name}'", [req.name], ["Cybernet"])
        return {"message": msg}
    except Exception as e:
        lib_logs.log_agent_action("error", f"Spawn failed for '{req.name}': {e}", [], [])
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/equip")
def equip_endpoint(req: EquipRequest):
    """Equip a StateMachine + create a fresh ExecutionState at the entry step."""
    drv = get_driver()
    try:
        msg = lib_cybernet.equip_state_machine(drv, cybernet_name=req.character_name, state_machine_id=req.state_machine_id)
        lib_logs.log_agent_action("success", f"Equipped StateMachine '{req.state_machine_id}' onto '{req.character_name}'", [req.character_name, req.state_machine_id], ["Cybernet", "StateMachine"])
        return {"message": msg}
    except Exception as e:
        lib_logs.log_agent_action("error", f"Equip failed for '{req.character_name}': {e}", [req.character_name], ["Cybernet"])
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tick")
def tick_endpoint(req: TickRequest):
    """Run one LLM turn for the Cybernet (read step → prompt → call model → execute cypher → auto-progress)."""
    from engine import tick_turn  # local to avoid cycle at import time
    drv = get_driver()
    try:
        status = lib_cybernet.get_status(drv, name=req.character_name)
        if not status:
            raise HTTPException(status_code=404, detail=f"Cybernet Identity '{req.character_name}' not found.")
        run_model = req.model_name or status["model_name"]
        run_temp = req.temperature if req.temperature is not None else status["temperature"]
        run_top_p = req.top_p if req.top_p is not None else status["top_p"]
        runner = AgentLLMRunner(model_name=run_model, temperature=run_temp, top_p=run_top_p, max_tokens=2048)
        res = tick_turn(req.character_name, runner)
        action_query = res.get("action_taken") or ""
        focus_nodes = list(set([req.character_name] + re.findall(r"['\"]([a-zA-Z0-9_\-]+)['\"]", action_query)))
        focus_labels = list(set(["Cybernet"] + re.findall(r":([A-Z][a-zA-Z0-9_]*)", action_query)))
        lib_logs.log_agent_action(
            "event",
            f"Ticked turn for '{req.character_name}'. Action: {res.get('action_taken')}. Event: {res.get('event_message')}",
            focus_nodes, focus_labels,
        )
        return res
    except Exception as e:
        lib_logs.log_agent_action("error", f"Tick failed for '{req.character_name}': {e}", [req.character_name], ["Cybernet"])
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
def list_endpoint():
    """List all Cybernets in the graph."""
    return lib_cybernet.list_cybernets(get_driver())


@router.get("/state_machines")
def list_state_machines_endpoint():
    """List all StateMachines (the equippable gear list)."""
    return lib_cybernet.list_state_machines(get_driver())


@router.get("/status/{name}")
def status_endpoint(name: str):
    """Read the Cybernet's full status (Identity, ExecutionState, current step, etc.)."""
    drv = get_driver()
    try:
        status = lib_cybernet.get_status(drv, name=name)
        if not status:
            raise HTTPException(status_code=404, detail=f"Cybernet Identity '{name}' not found.")
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulations/{name}")
def simulations_endpoint(name: str):
    """List the 5 most recent SimulationRuns for a Cybernet."""
    return lib_cybernet.list_simulations(get_driver(), name=name)


@router.post("/configure_ghost_shell")
def configure_ghost_shell_endpoint(req: ConfigureGhostShellRequest):
    """Partial-update the Cybernet's Ghost Shell (model_name, temperature, etc.)."""
    drv = get_driver()
    try:
        result = lib_ghost_shell.configure(
            drv,
            cybernet_name=req.cybernet_name, model_name=req.model_name,
            parameters_count=req.parameters_count, temperature=req.temperature,
            top_p=req.top_p, max_tokens=req.max_tokens,
        )
        lib_logs.log_agent_action("success", f"Configured Ghost Shell parameters on '{req.cybernet_name}'", [req.cybernet_name], ["Cybernet"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ghost_shell/status/{cybernet_name}")
def ghost_shell_status_endpoint(cybernet_name: str):
    """Read the Cybernet's Ghost Shell + accumulated token/cost telemetry."""
    drv = get_driver()
    try:
        result = lib_ghost_shell.status(drv, cybernet_name=cybernet_name)
        lib_logs.log_agent_action("system", f"Retrieved Ghost Shell status for '{cybernet_name}'", [cybernet_name], ["Cybernet"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
