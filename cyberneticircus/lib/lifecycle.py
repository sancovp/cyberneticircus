"""
Lifecycle helpers for the ExecutionState / TraversalState of a Cybernet.

These were extracted from `engine.py` (which is now the LLM runner only).
Functions take a neo4j session (or driver) and a cybernet_name; they return
the result of their database write so the caller can compose event messages.

The per-cybernet isolation model is:
  (:Cybernet {name})-[:HAS_LIFECYCLE]->(:ExecutionState)
  (:Cybernet {name})-[:HAS_TRAVERSAL]->(:TraversalState {cybernet_name})-[:CURRENT_STEP]->(:TraversalStep)

`entry_step_id` resolves an SM's entry step robustly even when the SM has cycles:
it counts incoming NEXT_STEP edges and picks the minimum (entry has zero or lowest).
"""
from __future__ import annotations
import json
import random
import uuid
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Entry-step discovery (robust to closed loops)
# ---------------------------------------------------------------------------

ENTRY_STEP_CYPHER = """
MATCH (sm:StateMachine {id: $sm_id})-[:HAS_STEP]->(entry:TraversalStep)
WITH collect(entry) as entries
UNWIND entries as entry
OPTIONAL MATCH (prev:TraversalStep)-[:NEXT_STEP]->(entry)
WITH entry, count(prev) as incoming
ORDER BY incoming ASC, entry.id ASC
WITH collect(entry) as sorted_entries
RETURN sorted_entries[0].id as entry_id
"""


def find_entry_step_id(session, sm_id: str) -> Optional[str]:
    """Return the entry step id of a StateMachine (handles closed-loop SMs)."""
    rec = session.run(ENTRY_STEP_CYPHER, {"sm_id": sm_id}).single()
    return rec["entry_id"] if rec else None


# ---------------------------------------------------------------------------
# Side-effect Cypher strings (used by tick_turn's step-driven branches)
# ---------------------------------------------------------------------------

RECORD_SIMULATION_CYPHER = """
MATCH (m:Cybernet {name: $name})
CREATE (sim:SimulationRun {
    run_id: $run_id,
    created_at: timestamp(),
    accuracy: $accuracy,
    fitness_score: $accuracy,
    calibrated: true,
    domain: 'cyberneticity',
    subdomain: 'simulation'
})
CREATE (m)-[:HAS_SIMULATION]->(sim)
"""

RECALC_FITNESS_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_SIMULATION]->(sim:SimulationRun)
RETURN avg(sim.accuracy) as avg_fitness
"""

SET_FITNESS_CYPHER = "MATCH (m:Cybernet {name: $name}) SET m.fitness_score = $avg_fitness"

ACCUMULATE_TOKEN_COST_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: $sm_id})
SET s.tokens_consumed_this_turn = s.tokens_consumed_this_turn + $tokens,
    s.cost_this_turn = s.cost_this_turn + $cost,
    m.total_tokens_consumed = m.total_tokens_consumed + $tokens,
    m.accumulated_cost = m.accumulated_cost + $cost
"""

# Jani domain-expansion layer tracking (per step)
LAYER_STEP_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: $sm_id})
SET s.current_layer = $layer, s.completed_layers = s.completed_layers + $layer
"""

LAYER_STEP_BOOT_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: $sm_id})
SET s.current_layer = $layer, s.completed_layers = [$layer]
"""

# Per-step side-effect map: step_id -> (cypher, is_first_layer)
LAYER_STEP_EFFECTS = {
    "layer1_primitive_boot": (LAYER_STEP_BOOT_CYPHER, "Layer 1"),
    "layer2_meta_compile":   (LAYER_STEP_CYPHER,   "Layer 2"),
    "layer3_sdlc_ignite":    (LAYER_STEP_CYPHER,   "Layer 3"),
}


# ---------------------------------------------------------------------------
# Step-side-effect application
# ---------------------------------------------------------------------------

def run_step_side_effects(session, *, name: str, step_id: str) -> str:
    """Apply step-specific side effects (e.g. sh8_night_calibrate -> create
    SimulationRun, layerN_* -> append to completed_layers). Returns an
    event-message fragment describing what happened (or '')."""
    if step_id == "sh8_night_calibrate":
        accuracy = round(random.uniform(0.5, 1.0), 2)
        run_id = str(uuid.uuid4())
        session.run(
            RECORD_SIMULATION_CYPHER,
            {"name": name, "run_id": run_id, "accuracy": accuracy},
        )
        return f"Calibration triggered. Accuracy recorded: {accuracy}."

    if step_id == "sh8_night_evolve":
        rec = session.run(RECALC_FITNESS_CYPHER, {"name": name}).single()
        avg_fit = rec["avg_fitness"] if rec and rec["avg_fitness"] is not None else 1.0
        session.run(SET_FITNESS_CYPHER, {"name": name, "avg_fit": avg_fit})
        return ""  # fitness update is silent; evolution happens at lifetime end

    if step_id in LAYER_STEP_EFFECTS:
        cypher, layer = LAYER_STEP_EFFECTS[step_id]
        session.run(cypher, {"name": name, "sm_id_param": name, "layer": layer})
        return f"Domain expansion: {layer} recorded."

    return ""


# ---------------------------------------------------------------------------
# Token / cost accounting
# ---------------------------------------------------------------------------

def accumulate_token_cost(session, *, name: str, sm_id: str) -> tuple:
    """Add a random token + cost increment to the ExecutionState. Returns
    (tokens_used, cost_increase) for the caller to report."""
    tokens = random.randint(100, 400)
    cost = round(tokens * 0.000015, 6)
    session.run(
        ACCUMULATE_TOKEN_COST_CYPHER,
        {"name": name, "sm_id": sm_id, "tokens": tokens, "cost": cost},
    )
    return tokens, cost


# ---------------------------------------------------------------------------
# Per-cybernet TraversalState lock (the gate)
# ---------------------------------------------------------------------------

LOCK_OR_CREATE_CYPHER = """
MATCH (c:Cybernet {name: $name})
MATCH (step:TraversalStep {id: $step_id})
CREATE (c)-[:HAS_TRAVERSAL]->(s:TraversalState {
    status: 'locked',
    cybernet_name: $name,
    created_at: timestamp(),
    domain: 'cyberneticity',
    subdomain: 'traversal_state'
})-[:CURRENT_STEP]->(step)
"""

FORCE_ALIGN_CYPHER = """
MATCH (c:Cybernet {name: $name})-[:HAS_TRAVERSAL]->(s:TraversalState)
MATCH (s)-[r:CURRENT_STEP]->()
DELETE r
WITH s
MATCH (step:TraversalStep {id: $step_id})
CREATE (s)-[:CURRENT_STEP]->(step)
"""


def ensure_lock(session, *, name: str, step_id: str, is_locked: bool) -> None:
    """Create THIS cybernet's TraversalState if missing, or force-align its
    CURRENT_STEP to the active ExecutionState step. Scoped per-cybernet so
    concurrent cybernets never block each other."""
    if not is_locked:
        session.run(LOCK_OR_CREATE_CYPHER, {"name": name, "step_id": step_id})
    else:
        session.run(FORCE_ALIGN_CYPHER, {"name": name, "step_id": step_id})


# ---------------------------------------------------------------------------
# ExecutionState CURRENT_STEP update after a successful step
# ---------------------------------------------------------------------------

READ_TRAVERSAL_STEP_CYPHER = """
MATCH (c:Cybernet {name: $name})-[:HAS_TRAVERSAL]->(s:TraversalState {status: 'locked'})-[:CURRENT_STEP]->(curr:TraversalStep)
RETURN curr.id as current_step_id
"""

SET_EXECUTION_STEP_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: $sm_id})
MATCH (next:TraversalStep {id: $new_step_id})
MATCH (s)-[r:CURRENT_STEP]->()
DELETE r
CREATE (s)-[:CURRENT_STEP]->(next)
"""

SET_PHASE_NIGHT_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: $sm_id})
SET s.phase = 'night'
"""

TURN_RESET_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: $sm_id})
SET s.turn_number = s.turn_number + 1,
    s.phase = 'day',
    s.tokens_consumed_this_turn = 0,
    s.cost_this_turn = 0.0,
    s.call_stack = '[]'
"""


def sync_execution_state_from_traversal(session, *, name: str, sm_id: str) -> Optional[str]:
    """After the LLM's cypher has run + auto-progressed, sync the
    ExecutionState.CURRENT_STEP to the TraversalState's new step. Returns
    the new step id (or None if TraversalState was completed/cleared)."""
    rec = session.run(READ_TRAVERSAL_STEP_CYPHER, {"name": name}).single()
    if not rec:
        return None
    new_step_id = rec["current_step_id"]
    session.run(
        SET_EXECUTION_STEP_CYPHER,
        {"name": name, "sm_id": sm_id, "new_step_id": new_step_id},
    )
    if "night" in new_step_id.lower():
        session.run(SET_PHASE_NIGHT_CYPHER, {"name": name, "sm_id": sm_id})
    return new_step_id


def advance_turn(session, *, name: str, sm_id: str) -> None:
    """Bump turn_number, reset phase/tokens/cost/call_stack."""
    session.run(TURN_RESET_CYPHER, {"name": name, "sm_id": sm_id})


# Reset turn + repoint CURRENT_STEP to the SM's entry step (used by
# _trigger_turn_completion when a top-level SM completes).
RESET_TURN_TO_ENTRY_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: $sm_id})
MATCH (entry:TraversalStep {id: $entry_id})
MATCH (s)-[r:CURRENT_STEP]->()
DELETE r
CREATE (s)-[:CURRENT_STEP]->(entry)
SET s.turn_number = s.turn_number + 1,
    s.phase = 'day',
    s.tokens_consumed_this_turn = 0,
    s.cost_this_turn = 0.0,
    s.call_stack = '[]'
"""


def reset_turn_to_entry(session, *, name: str, sm_id: str, entry_id: str) -> None:
    """Bump turn + repoint CURRENT_STEP to the SM's entry step (turn-completion path)."""
    session.run(
        RESET_TURN_TO_ENTRY_CYPHER,
        {"name": name, "sm_id": sm_id, "entry_id": entry_id},
    )


# ---------------------------------------------------------------------------
# CALLS_SM entry step + call stack push/pop
# ---------------------------------------------------------------------------

CHECK_CALLS_SM_CYPHER = """
MATCH (curr:TraversalStep {id: $step_id})-[:CALLS_SM]->(child_sm:StateMachine)
RETURN child_sm.id as child_sm_id
"""

PUSH_CALL_FRAME_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState)
MATCH (entry:TraversalStep {id: $entry_id})
MATCH (s)-[r:CURRENT_STEP]->()
DELETE r
CREATE (s)-[:CURRENT_STEP]->(entry)
SET s.equipped_sm_id = $child_sm_id,
    s.call_stack = $call_stack
"""

POP_CALL_FRAME_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState)
MATCH (next:TraversalStep {id: $next_step_id})
MATCH (s)-[r:CURRENT_STEP]->()
DELETE r
CREATE (s)-[:CURRENT_STEP]->(next)
SET s.equipped_sm_id = $parent_sm_id,
    s.call_stack = $call_stack
"""

SET_PHASE_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState)
SET s.phase = $phase
"""

CHILD_NEXT_STEP_CYPHER = """
MATCH (curr:TraversalStep {id: $parent_step_id})-[:NEXT_STEP]->(next:TraversalStep)
RETURN next.id as next_id
"""


def find_calls_sm(session, *, step_id: str) -> Optional[str]:
    """If the active step has a CALLS_SM, return the child SM id. Else None."""
    rec = session.run(CHECK_CALLS_SM_CYPHER, {"step_id": step_id}).single()
    return rec["child_sm_id"] if rec else None


def enter_child_state_machine(session, *, name: str, child_sm_id: str,
                              parent_sm_id: str, parent_step_id: str) -> Optional[str]:
    """Push parent frame onto call_stack + repoint ExecutionState to child's
    entry step. Returns the child entry step id, or None on failure."""
    entry_id = find_entry_step_id(session, child_sm_id)
    if not entry_id:
        return None
    call_stack = json.dumps([{"sm_id": parent_sm_id, "step_id": parent_step_id}])
    session.run(
        PUSH_CALL_FRAME_CYPHER,
        {"name": name, "child_sm_id": child_sm_id, "entry_id": entry_id, "call_stack": call_stack},
    )
    return entry_id


def pop_call_stack_until_resolved(session, *, name: str, call_stack: list) -> tuple:
    """Pop frames until we find a parent with a NEXT_STEP. Returns
    (parent_sm_id, next_step_id) or (None, None) if all frames popped."""
    while call_stack:
        parent_frame = call_stack.pop()
        parent_sm_id = parent_frame["sm_id"]
        parent_step_id = parent_frame["step_id"]
        rec = session.run(CHILD_NEXT_STEP_CYPHER, {"parent_step_id": parent_step_id}).single()
        next_step_id = rec["next_id"] if rec else None
        if next_step_id:
            return parent_sm_id, next_step_id
    return None, None


def return_to_parent(session, *, name: str, parent_sm_id: str, next_step_id: str,
                     call_stack: list) -> None:
    """Restore ExecutionState to the popped parent's next step."""
    session.run(
        POP_CALL_FRAME_CYPHER,
        {
            "name": name,
            "parent_sm_id": parent_sm_id,
            "next_step_id": next_step_id,
            "call_stack": json.dumps(call_stack),
        },
    )
    phase = "night" if "night" in next_step_id.lower() else "day"
    session.run(SET_PHASE_CYPHER, {"name": name, "phase": phase})
