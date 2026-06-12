"""
Evolution helpers: lifetime evaluation (Reap / Survive / Reproduce).

Extracted from `engine.py` (which is now the LLM runner only).
Cybernet selection pressure at end of a 5-turn lifetime. Reads the parent's
status + fitness and writes either a REAP (DETACH DELETE), a SURVIVE
(reset turn counter), or a REPRODUCE (mutated clone with cloned EQUIPS).
"""
from __future__ import annotations
import random
from typing import Any, Dict, Optional


REAP_THRESHOLD = 0.4
REPRODUCE_THRESHOLD = 0.8

REAP_CYPHER = """
MATCH (m:Cybernet {name: $name})
OPTIONAL MATCH (m)-[:HAS_LIFECYCLE]->(s:ExecutionState)
OPTIONAL MATCH (m)-[:HAS_IDENTITY]->(i:Identity)
OPTIONAL MATCH (m)-[:HAS_SIMULATION]->(sim:SimulationRun)
DETACH DELETE m, s, i, sim
"""

CLEAR_TRAVERSAL_STATES = "MATCH (s:TraversalState) DETACH DELETE s"

CLONE_CYBERNET_CYPHER = """
CREATE (m:Cybernet {
    name: $child_name,
    description: $description,
    model_name: $model_name,
    parameters_count: $parameters_count,
    temperature: $temperature,
    top_p: $top_p,
    max_tokens: $max_tokens,
    mutation_rate: $mutation_rate,
    selection_pressure: $selection_pressure,
    task_success_rate: 1.0,
    tool_call_frequency: 0.0,
    avg_latency_ms: 0.0,
    total_tokens_consumed: 0,
    accumulated_cost: 0.0,
    fitness_score: 1.0,
    domain: 'cyberneticity',
    subdomain: 'cybernet'
})
"""

CLONE_IDENTITY_CYPHER = """
MATCH (parent:Cybernet {name: $name})-[:HAS_IDENTITY]->(parent_i:Identity)
MATCH (child:Cybernet {name: $child_name})
CREATE (child_i:Identity {
    name: $child_name,
    description: parent_i.description,
    persona_prompt: parent_i.persona_prompt,
    world_prompt: parent_i.world_prompt,
    core_loop_prompt: parent_i.core_loop_prompt,
    domain: parent_i.domain,
    subdomain: parent_i.subdomain
})
CREATE (child)-[:HAS_IDENTITY]->(child_i)
"""

CLONE_EQUIPS_AND_LIFECYCLE_CYPHER = """
MATCH (parent:Cybernet {name: $name})-[:EQUIPS]->(sm:StateMachine)
MATCH (child:Cybernet {name: $child_name})
CREATE (child)-[:EQUIPS]->(sm)
WITH child, sm
CREATE (s:ExecutionState {
    status: 'locked',
    turn_number: 1,
    phase: 'day',
    lifetime_limit: 5,
    tokens_consumed_this_turn: 0,
    cost_this_turn: 0.0,
    equipped_sm_id: sm.id,
    call_stack: '[]',
    domain: 'cyberneticity',
    subdomain: 'execution_state'
})
CREATE (child)-[:HAS_LIFECYCLE]->(s)
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

RESET_LIFECYCLE_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: $sm_id})
MATCH (sm:StateMachine {id: $sm_id})-[:HAS_STEP]->(entry:TraversalStep)
WITH s, collect(entry) as entries
UNWIND entries as entry
OPTIONAL MATCH (prev:TraversalStep)-[:NEXT_STEP]->(entry)
WITH s, entry, count(prev) as incoming
ORDER BY incoming ASC, entry.id ASC
WITH s, collect(entry) as sorted_entries
WITH s, sorted_entries[0] as entry
MATCH (s)-[r:CURRENT_STEP]->()
DELETE r
CREATE (s)-[:CURRENT_STEP]->(entry)
SET s.turn_number = 1,
    s.phase = 'day',
    s.tokens_consumed_this_turn = 0,
    s.cost_this_turn = 0.0,
    s.call_stack = '[]'
"""


def _mutate_status(status: Dict[str, Any]) -> Dict[str, float]:
    """Calculate mutated parameters for a child clone (fitness >= 0.8 branch)."""
    mutation_rate = status["mutation_rate"]
    selection_pressure = status["selection_pressure"]
    return {
        "mutated_temp": max(0.0, min(2.0, round(status["temperature"] + random.uniform(-0.1, 0.1) * mutation_rate, 2))),
        "mutated_top_p": max(0.0, min(1.0, round(status["top_p"] + random.uniform(-0.05, 0.05) * mutation_rate, 2))),
        "mutated_mutation_rate": max(0.01, min(1.0, round(mutation_rate + random.uniform(-0.02, 0.02), 2))),
        "mutated_selection_pressure": max(0.1, round(selection_pressure + random.uniform(-0.1, 0.1), 2)),
    }


def evaluate_evolution(session, *, name: str, status: Dict[str, Any]) -> str:
    """Apply Reap / Survive / Reproduce based on fitness_score. Returns an
    event-message describing the outcome.

    `status` is the output of `get_character_status`. The session is used
    for all DB writes. TraversalState nodes are always cleared at the end
    of an evolution pass (they only live for a single turn's gate).
    """
    fitness = status["fitness_score"]
    sm_id = status["equipped_sm_id"]

    # 1. REAPING (Pruning) — fitness below survival threshold
    if fitness < REAP_THRESHOLD:
        session.run(REAP_CYPHER, {"name": name})
        session.run(CLEAR_TRAVERSAL_STATES)
        return (
            f"Identity graph '{name}' fitness ({fitness}) fell below selection "
            f"threshold. Reaped from DB."
        )

    # 2. REPRODUCTION (mutated clone + reset parent)
    if fitness >= REPRODUCE_THRESHOLD:
        child_name = f"{name}_V{random.randint(2, 99)}"
        m = _mutate_status(status)

        session.run(CLONE_CYBERNET_CYPHER, {
            "child_name": child_name,
            "description": status["description"],
            "model_name": status["model_name"],
            "parameters_count": status.get("parameters_count", 70.0),
            "temperature": m["mutated_temp"],
            "top_p": m["mutated_top_p"],
            "max_tokens": 2048,
            "mutation_rate": m["mutated_mutation_rate"],
            "selection_pressure": m["mutated_selection_pressure"],
        })
        session.run(CLONE_IDENTITY_CYPHER, {"name": name, "child_name": child_name})
        session.run(CLONE_EQUIPS_AND_LIFECYCLE_CYPHER, {"name": name, "child_name": child_name})
        session.run(RESET_LIFECYCLE_CYPHER, {"name": name, "sm_id": sm_id})
        session.run(CLEAR_TRAVERSAL_STATES)

        return (
            f"Identity '{name}' achieved outstanding fitness ({fitness}) and "
            f"REPRODUCED! Clone '{child_name}' spawned with mutated stats "
            f"(temp={m['mutated_temp']}, top_p={m['mutated_top_p']}) inheriting "
            f"equipped StateMachines."
        )

    # 3. SURVIVAL (reset parent for new lifetime)
    session.run(RESET_LIFECYCLE_CYPHER, {"name": name, "sm_id": sm_id})
    session.run(CLEAR_TRAVERSAL_STATES)
    return (
        f"Identity '{name}' fitness ({fitness}) met survival standards. "
        f"Lifetime reset for another cycle."
    )
