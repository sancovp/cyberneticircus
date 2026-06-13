"""
Cypher helpers for Cybernet identity operations + full runtime helpers.

Originally `lib/cybernet.py` only had `create_cypher` / `equip_state_machine_cypher` /
`tick_cypher` (string constructors). The refactor of `engine.py` moved the
actual implementations of `create_cybernet` / `equip_state_machine` /
`get_character_status` / `evaluate_evolution` into `lib/`, so this file now
contains both the cypher-string constructors AND the running helpers that
execute against a live neo4j driver.
"""
from __future__ import annotations
import os
import json
from typing import Any, Dict, Optional

from neo4j import GraphDatabase


# ---------------------------------------------------------------------------
# Cypher-string constructors (used by the LLM to learn the graph schema)
# ---------------------------------------------------------------------------

def create_cypher(name: str, description: str, model_name: str = "minimax-M3",
                  temperature: float = 0.7, top_p: float = 0.9,
                  max_tokens: int = 2048) -> str:
    """Return the cypher to create a new Cybernet identity + its persona Identity node."""
    return f"""CREATE (c:Cybernet {{
  name: $name, description: $description, model_name: $model_name,
  temperature: $temperature, top_p: $top_p, max_tokens: $max_tokens,
  domain: 'cyberneticity', subdomain: 'cybernet'
}})
CREATE (i:Identity {{
  name: $name, description: $description,
  persona_prompt: 'You are the Cybernet persona ' + $name + '. Guidelines: ' + $description,
  world_prompt: 'State of the Cyberneticity: you are inside the sandbox execution grid.',
  core_loop_prompt: '1. Observe traversal state. 2. Formulate Cypher command. 3. Execute progress.',
  domain: 'cyberneticity', subdomain: 'identity'
}})
CREATE (c)-[:HAS_IDENTITY]->(i)"""


def equip_state_machine_cypher(cybernet_name: str, state_machine_id: str) -> str:
    """Return cypher that equips a state machine to a cybernet + creates an ExecutionState."""
    return f"""MATCH (c:Cybernet {{name: $cybernet_name}})
MATCH (sm:StateMachine {{id: $state_machine_id}})
MERGE (c)-[:EQUIPS]->(sm)
MERGE (c)-[:HAS_LIFECYCLE]->(s:ExecutionState {{equipped_sm_id: $state_machine_id, status: 'locked', domain: 'cyberneticity', subdomain: 'lifecycle'}})
RETURN s"""


def tick_cypher(cybernet_name: str) -> str:
    """Cypher to advance the active state machine step (called by the LLM runner, not user-typed)."""
    return f"""MATCH (c:Cybernet {{name: $cybernet_name}})-[:HAS_LIFECYCLE]->(s:ExecutionState)
MATCH (s)-[:CURRENT_STEP]->(step:TraversalStep)
RETURN step.id, step.text, step.required_pattern, step.pattern_description"""


# ---------------------------------------------------------------------------
# Full Cypher templates (used by the live helpers below)
# ---------------------------------------------------------------------------

CREATE_CYBERNET_CYPHER = """
CREATE (m:Cybernet {
    name: $name, description: $description, model_name: $model_name,
    parameters_count: $parameters_count, temperature: $temperature, top_p: $top_p,
    max_tokens: $max_tokens, mutation_rate: $mutation_rate,
    selection_pressure: $selection_pressure,
    task_success_rate: 1.0, tool_call_frequency: 0.0, avg_latency_ms: 0.0,
    total_tokens_consumed: 0, accumulated_cost: 0.0, fitness_score: 1.0,
    domain: 'cyberneticity', subdomain: 'cybernet'
})
CREATE (i:Identity {
    name: $name, description: $description,
    persona_prompt: 'You are the Cybernet persona ' + $name + '. Guidelines: ' + $description,
    world_prompt: 'State of the Cyberneticity: You are inside the sandbox execution grid of the CybernetiCircus.',
    core_loop_prompt: '1. Observe traversal state. 2. Formulate Cypher command. 3. Execute progress.',
    domain: 'cyberneticity', subdomain: 'identity'
})
CREATE (m)-[:HAS_IDENTITY]->(i)
"""

EQUIP_SM_CYPHER = """
MATCH (m:Cybernet {name: $name})
MATCH (sm:StateMachine {id: $sm_id})
MERGE (m)-[:EQUIPS]->(sm)
WITH m, sm
OPTIONAL MATCH (m)-[r:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: $sm_id})
DETACH DELETE s
DELETE r
WITH m, sm
CREATE (s:ExecutionState {
    status: 'locked', turn_number: 1, phase: 'day', lifetime_limit: 5,
    tokens_consumed_this_turn: 0, cost_this_turn: 0.0,
    equipped_sm_id: $sm_id, call_stack: '[]',
    current_layer: 'none', completed_layers: [],
    domain: 'cyberneticity', subdomain: 'execution_state'
})
CREATE (m)-[:HAS_LIFECYCLE]->(s)
WITH s, sm
MATCH (sm)-[:HAS_STEP]->(entry:TraversalStep)
WITH s, sm, collect(entry) as entries
UNWIND entries as entry
OPTIONAL MATCH (prev:TraversalStep)-[:NEXT_STEP]->(entry)
WITH s, sm, entry, count(prev) as incoming
ORDER BY incoming ASC, entry.id ASC
WITH s, sm, collect(entry) as sorted_entries
WITH s, sm, sorted_entries[0] as entry
CREATE (s)-[:CURRENT_STEP]->(entry)
"""

GET_STATUS_CYPHER = """
MATCH (m:Cybernet {name: $name})
OPTIONAL MATCH (m)-[:EQUIPS]->(sm:StateMachine)
OPTIONAL MATCH (m)-[:HAS_IDENTITY]->(i:Identity)
OPTIONAL MATCH (m)-[:HAS_LIFECYCLE]->(s:ExecutionState)
OPTIONAL MATCH (s)-[:CURRENT_STEP]->(curr:TraversalStep)
RETURN m, sm.id as equipped_sm_id, sm.name as equipped_sm_name, s, i,
       curr.id as current_step_id, curr.text as current_step_text,
       curr.instruction_file_path as current_step_file_path,
       curr.pattern_description as pattern_description,
       curr.required_pattern as required_pattern,
       s.call_stack as call_stack
"""


LIST_CYBERNETS_CYPHER = "MATCH (m:Cybernet) RETURN m.name as name ORDER BY name"

LIST_STATE_MACHINES_CYPHER = "MATCH (sm:StateMachine) RETURN sm.id as id, sm.name as name ORDER BY name"

LIST_SIMULATIONS_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_SIMULATION]->(sim:SimulationRun)
RETURN sim.run_id as run_id, sim.accuracy as accuracy, sim.created_at as created_at
ORDER BY sim.created_at DESC LIMIT 5
"""


# ---------------------------------------------------------------------------
# Live helpers (the implementations — engine.py wraps these as a thin facade)
# ---------------------------------------------------------------------------

def create(driver, *, name: str, description: str, model_name: str = "gemini-1.5-pro",
           parameters_count: float = 70.0, temperature: float = 0.7,
           top_p: float = 0.9, max_tokens: int = 2048, mutation_rate: float = 0.1,
           selection_pressure: float = 1.0) -> str:
    """Create a Cybernet + Identity + HAS_IDENTITY edge."""
    with driver.session() as session:
        existing = session.run(
            "MATCH (m:Cybernet {name: $name}) RETURN count(m) as c",
            {"name": name},
        ).single()
        if existing["c"] > 0:
            raise ValueError(f"Cybernet character '{name}' already exists.")
        session.run(CREATE_CYBERNET_CYPHER, {
            "name": name, "description": description, "model_name": model_name,
            "parameters_count": float(parameters_count),
            "temperature": float(temperature), "top_p": float(top_p),
            "max_tokens": int(max_tokens), "mutation_rate": float(mutation_rate),
            "selection_pressure": float(selection_pressure),
        })
    return f"Successfully created Cybernet '{name}' identity graph."


def equip_state_machine(driver, *, cybernet_name: str, state_machine_id: str) -> str:
    """Equip a StateMachine + create its ExecutionState at the entry step."""
    with driver.session() as session:
        if not session.run("MATCH (m:Cybernet {name: $n}) RETURN m", {"n": cybernet_name}).peek():
            raise ValueError(f"Cybernet '{cybernet_name}' does not exist.")
        if not session.run("MATCH (sm:StateMachine {id: $i}) RETURN sm", {"i": state_machine_id}).peek():
            raise ValueError(f"StateMachine '{state_machine_id}' does not exist.")
        session.run(EQUIP_SM_CYPHER, {"name": cybernet_name, "sm_id": state_machine_id})
    return f"Successfully equipped StateMachine '{state_machine_id}' onto '{cybernet_name}'."


def get_status(driver, *, name: str) -> Optional[Dict[str, Any]]:
    """Read the Cybernet's full status dict (or None if not found)."""
    with driver.session() as session:
        rec = session.run(GET_STATUS_CYPHER, {"name": name}).single()
        if not rec:
            return None
        return _render_status(rec)


def list_cybernets(driver) -> Dict[str, Any]:
    """List all Cybernet names (for the visualizer's character list)."""
    with driver.session() as session:
        names = [r["name"] for r in session.run(LIST_CYBERNETS_CYPHER)]
    return {"cybernets": names}


def list_state_machines(driver) -> Dict[str, Any]:
    """List all StateMachine (id, name) — the equippable gear list."""
    with driver.session() as session:
        machines = [{"id": r["id"], "name": r["name"]} for r in session.run(LIST_STATE_MACHINES_CYPHER)]
    return {"state_machines": machines}


def list_simulations(driver, *, name: str) -> Dict[str, Any]:
    """List the 5 most recent SimulationRuns for a Cybernet (used by /api/simulations/{name})."""
    with driver.session() as session:
        sims = [
            {"run_id": r["run_id"], "accuracy": r["accuracy"], "created_at": r["created_at"]}
            for r in session.run(LIST_SIMULATIONS_CYPHER, {"name": name})
        ]
    return {"simulations": sims}


def _render_status(rec) -> Dict[str, Any]:
    """Convert the GET_STATUS_CYPHER record into the dict the runners + scripts expect."""
    out = {
        "name": rec["m"]["name"],
        "description": rec["i"]["description"] if rec["i"] else rec["m"]["description"],
        "model_name": rec["m"]["model_name"],
        "temperature": rec["m"]["temperature"],
        "top_p": rec["m"]["top_p"],
        "mutation_rate": rec["m"]["mutation_rate"],
        "selection_pressure": rec["m"]["selection_pressure"],
        "total_tokens": rec["m"]["total_tokens_consumed"],
        "accumulated_cost": rec["m"]["accumulated_cost"],
        "fitness_score": rec["m"]["fitness_score"],
        "equipped_sm_id": rec["equipped_sm_id"],
        "equipped_sm_name": rec["equipped_sm_name"],
        "turn_number": None, "phase": None,
        "current_step_id": None, "current_step_text": None,
        "current_step_file_path": None,
        "pattern_description": None, "required_pattern": None,
        "call_stack": "[]", "current_layer": None, "completed_layers": [],
        "identity_name": rec["i"]["name"] if rec["i"] else rec["m"]["name"],
        "persona_prompt": rec["i"]["persona_prompt"] if rec["i"] else "",
        "world_prompt": rec["i"]["world_prompt"] if rec["i"] else "",
        "core_loop_prompt": rec["i"]["core_loop_prompt"] if rec["i"] else "",
    }
    if rec["s"]:
        step_text = rec["current_step_text"]
        file_path = rec["current_step_file_path"]
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                step_text = (
                    f"{step_text}\n\n=== INSTRUCTION FILE CONTENT ===\n{file_content}"
                    if step_text else file_content
                )
            except Exception as e:
                pass  # log externally; don't crash the read
        out.update({
            "turn_number": rec["s"]["turn_number"],
            "phase": rec["s"]["phase"],
            "current_step_id": rec["current_step_id"],
            "current_step_text": step_text,
            "current_step_file_path": file_path,
            "pattern_description": rec["pattern_description"],
            "required_pattern": rec["required_pattern"],
            "equipped_sm_id": rec["s"]["equipped_sm_id"] or rec["equipped_sm_id"],
            "call_stack": rec["call_stack"] or "[]",
            "current_layer": rec["s"].get("current_layer", "none"),
            "completed_layers": rec["s"].get("completed_layers", []),
        })
    return out
