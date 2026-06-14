"""
The Core — a Cybernet's always-running execution stack.

CORRECTED MODEL (2026-06-13, Isaac): the Core is NOT a single equipped SM. It is
the mandatory, always-on stack a Cybernet MUST run at all times; every action the
being takes happens *inside* it. The Core is **modifiable by config**, and the
config IS an ORDERED SEQUENCE of State Machines (one or more). Those SMs nest:
each SM has an execution phase in which it MAY open up (or not) to other SMs that
are selectable inside it.

Graph model:
  (:Cybernet)-[:HAS_CORE]->(:Core {subdomain:'core'})
  (:Core)-[:CORE_RUNS {order:i}]->(:StateMachine)      # the ordered config sequence (1+)

Runtime cursor stays the single :ExecutionState (one per Cybernet, via HAS_LIFECYCLE):
  - equipped_sm_id : which SM in the sequence is currently active
  - core_index     : position in the CORE_RUNS sequence (NEW)
  - call_stack     : nesting frames (CALLS_SM push/pop) — unchanged
  - CURRENT_STEP   : the active TraversalStep — unchanged

The degenerate case (e.g. Jani today) is a Core whose sequence is a single SM
(`[janic_cycle_sm]`) with no CALLS_SM nesting — "Jani's core works like that" is
the seed of the general form.

This module is the CORE composition: build/equip a Core, read it, and (increment 2,
not yet wired into the drivers) advance through the sequence so the Core is always
running. The cypher constructors are pure strings (graph is sacred — the shell
runs them); the live helpers execute against the shared driver for bootstrap/backfill.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Cypher-string constructors (pure — the shell runs these)
# ---------------------------------------------------------------------------

def has_core_cypher() -> str:
    """Read a Cybernet's Core sequence (ordered SM ids). The config, in order."""
    return """
    MATCH (m:Cybernet {name: $name})-[:HAS_CORE]->(core:Core)-[r:CORE_RUNS]->(sm:StateMachine)
    RETURN core.id AS core_id, sm.id AS sm_id, sm.name AS sm_name, r.order AS order
    ORDER BY r.order ASC
    """


def core_sm_at_index_cypher() -> str:
    """The SM id at a given position in the Core sequence."""
    return """
    MATCH (m:Cybernet {name: $name})-[:HAS_CORE]->(:Core)-[r:CORE_RUNS]->(sm:StateMachine)
    WHERE r.order = $index
    RETURN sm.id AS sm_id LIMIT 1
    """


def core_length_cypher() -> str:
    """How many SMs are in the Core sequence (for wrap-around at the end)."""
    return """
    MATCH (m:Cybernet {name: $name})-[:HAS_CORE]->(:Core)-[r:CORE_RUNS]->(:StateMachine)
    RETURN count(r) AS n
    """


# ---------------------------------------------------------------------------
# Live helpers — bootstrap / backfill (run against the shared driver)
# ---------------------------------------------------------------------------

# Wrap a being that already has a live ExecutionState (mid-flight) into a Core
# WITHOUT disturbing its cursor: create the :Core, make the currently-equipped SM
# the order-0 element of the sequence, and stamp core_index=0 on the ExecutionState.
# This is the degenerate single-SM Core (Jani's case).
BACKFILL_CORE_CYPHER = """
MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState)
MERGE (m)-[:HAS_CORE]->(core:Core {id: $core_id})
ON CREATE SET core.name = $name + ' Core',
              core.domain = 'cyberneticity', core.subdomain = 'core'
WITH m, core, s
MATCH (sm:StateMachine {id: s.equipped_sm_id})
MERGE (core)-[r:CORE_RUNS]->(sm)
SET r.order = coalesce(r.order, 0)
SET s.core_index = coalesce(s.core_index, 0)
RETURN core.id AS core_id, sm.id AS order0_sm, s.core_index AS core_index
"""

# Build a Core from an explicit ordered sequence of SM ids (fresh config).
# $seq is a list of {sm_id, order}. Does NOT create the ExecutionState — that is
# the equip path's job (equip the order-0 SM, set core_index=0).
BUILD_CORE_SEQUENCE_CYPHER = """
MATCH (m:Cybernet {name: $name})
MERGE (m)-[:HAS_CORE]->(core:Core {id: $core_id})
ON CREATE SET core.name = $name + ' Core',
              core.domain = 'cyberneticity', core.subdomain = 'core'
WITH m, core
UNWIND $seq AS item
MATCH (sm:StateMachine {id: item.sm_id})
MERGE (core)-[r:CORE_RUNS]->(sm)
SET r.order = item.order
RETURN core.id AS core_id, collect(item.sm_id) AS sequence
"""


def core_id_for(name: str) -> str:
    """Deterministic Core id for a Cybernet (one Core per being)."""
    return f"core__{name}"


def backfill_core(driver, *, name: str) -> Dict[str, Any]:
    """Wrap an existing being's single equipped SM into a first-class :Core,
    preserving its live ExecutionState/cursor. Idempotent."""
    with driver.session() as session:
        rec = session.run(
            BACKFILL_CORE_CYPHER, {"name": name, "core_id": core_id_for(name)}
        ).single()
        if not rec:
            raise ValueError(f"Cybernet '{name}' has no ExecutionState to wrap.")
        return {"core_id": rec["core_id"], "order0_sm": rec["order0_sm"],
                "core_index": rec["core_index"]}


def build_core_sequence(driver, *, name: str, sm_ids: List[str]) -> Dict[str, Any]:
    """Configure a being's Core as an ordered sequence of SM ids (1+)."""
    if not sm_ids:
        raise ValueError("A Core sequence needs at least one StateMachine id.")
    seq = [{"sm_id": sid, "order": i} for i, sid in enumerate(sm_ids)]
    with driver.session() as session:
        rec = session.run(
            BUILD_CORE_SEQUENCE_CYPHER,
            {"name": name, "core_id": core_id_for(name), "seq": seq},
        ).single()
        return {"core_id": rec["core_id"], "sequence": rec["sequence"]}


def get_core(driver, *, name: str) -> List[Dict[str, Any]]:
    """Read a being's Core sequence (ordered list of {sm_id, sm_name, order})."""
    with driver.session() as session:
        return [
            {"sm_id": r["sm_id"], "sm_name": r["sm_name"], "order": r["order"]}
            for r in session.run(has_core_cypher(), {"name": name})
        ]
