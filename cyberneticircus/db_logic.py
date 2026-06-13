#!/usr/bin/env python3
"""
LLM-loop gates for CybernetiCircus — thin facade over `cyberneticircus.lib/`.

This module is the public surface for the LLM-runner / web_server. All
implementation lives in `cyberneticircus.lib/`. Per the architecture rule
(§9.1 "thin facade + lib/ deps"), nothing here is removed — every function
that exists in this module is preserved, with its body delegated to lib/.

The facade owns:
- the Neo4j driver lifecycle (get_driver / shutdown_driver)
- the LLM-loop gate functions (query_database, is_traversal_locked,
  get_active_traversal_step, progress_traversal)
- the bootstrap (populate_default_graphs) — called by get_driver on connect
- the public surface symbols other modules import (get_schema, etc.)
"""
import os
import re
import logging
import atexit
from typing import Optional, List, Dict, Any

from neo4j import GraphDatabase

# Implementation imports — all bodies live in lib/
from cyberneticircus.lib import bootstrap_procedures
from cyberneticircus.lib import state_machines as sm_cypher
from cyberneticircus.lib.gates import (
    is_mutation_query as _is_mutation_query,
    validate_cypher_query as _validate_cypher_query,
    serialize_value as _serialize_value,
    run_cypher as _run_cypher,
    auto_progress_step as _auto_progress_step,
    scan_and_trigger_traversal as _scan_and_trigger_traversal,
    trigger_traversal_by_location as _trigger_traversal_by_location,
    get_active_traversal_step as _get_active_traversal_step_impl,
    adjust_transition_weight_internal as _adjust_transition_weight_impl,
    get_schema as _get_schema_impl,
    populate_default_graphs as _populate_default_graphs_impl,
)

_driver: Optional[GraphDatabase] = None
logger = logging.getLogger("cyberneticircus_db_logic")


# --- Driver lifecycle (the only thing owned, not delegated) -----------------

def get_driver() -> GraphDatabase:
    """Lazy Neo4j driver init; bootstraps canonical procedures on first connect."""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        logger.info(f"Connecting to Neo4j at {uri} as '{user}'...")
        try:
            _driver = GraphDatabase.driver(uri, auth=(user, password))
            _driver.verify_connectivity()
            _populate_default_graphs_impl(_driver)
        except Exception as e:
            raise RuntimeError(f"Database connection failure: {e}")
    return _driver


def shutdown_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


atexit.register(shutdown_driver)


# --- Public surface (thin facades; bodies in lib/) ---------------------------

def populate_default_graphs(driver) -> None:
    """Idempotently seed canonical procedures (steps + StateMachines + entry tasks)."""
    return _populate_default_graphs_impl(driver)


def is_mutation_query(query: str) -> bool:
    """True if the Cypher performs any write (CREATE/MERGE/SET/DELETE/REMOVE/DETACH)."""
    return _is_mutation_query(query)


def validate_cypher_query(query: str) -> None:
    """Reject writes to :Wiki; require domain+subdomain on every node creation."""
    return _validate_cypher_query(query)


def get_active_traversal_step(cybernet_name: str) -> Optional[Dict[str, Any]]:
    """Return the locked TraversalStep for THIS cybernet (per-cybernet scope)."""
    return _get_active_traversal_step_impl(cybernet_name, get_driver, sm_cypher, logger)


def is_traversal_locked(cybernet_name: str) -> bool:
    """Per-cybernet lock check. N concurrent cybernets never block each other."""
    return get_active_traversal_step(cybernet_name) is not None


def auto_progress_step(active_step: Dict[str, Any],
                      target_step_id: Optional[str] = None) -> str:
    """Advance this ExecutionState to its next (or explicit) TraversalStep."""
    return _auto_progress_step(active_step, target_step_id, get_driver, sm_cypher, logger)


def scan_and_trigger_traversal(results: List[Dict[str, Any]],
                               cybernet_name: Optional[str] = None) -> None:
    """If a returned node carries trigger_traversal, lock THIS cybernet's ExecutionState for it."""
    return _scan_and_trigger_traversal(results, cybernet_name, get_driver, sm_cypher, logger)


def trigger_traversal_by_location(cybernet_name: Optional[str], location: Optional[str]) -> None:
    """If a reported filesystem location maps to a :Place flow, lock THIS cybernet into it."""
    return _trigger_traversal_by_location(cybernet_name, location, get_driver, sm_cypher, logger)


def serialize_value(value: Any) -> Any:
    """Convert Neo4j graph types to JSON-serializable formats."""
    return _serialize_value(value)


def query_database(query: str, cybernet_name: str,
                   parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute Cypher under the per-cybernet ExecutionState lock (the LLM-loop gate)."""
    _validate_cypher_query(query)
    active_step = get_active_traversal_step(cybernet_name)
    is_mutation = _is_mutation_query(query)
    should_auto_progress, target_step_id = _evaluate_pattern(query, active_step, is_mutation)

    results = _run_cypher(query, parameters or {}, get_driver, _serialize_value)
    if should_auto_progress and active_step:
        results.append({"_state_machine_event":
                        _auto_progress_step(active_step, target_step_id, get_driver, sm_cypher, logger)})
    else:
        _scan_and_trigger_traversal(results, cybernet_name, get_driver, sm_cypher, logger)
    return results


def progress_traversal(cybernet_name: str, answer: Optional[str] = None) -> str:
    """Manually advance the given Cybernet's traversal to its next step."""
    active = get_active_traversal_step(cybernet_name)
    if not active:
        return f"No active traversal state machine is currently locked for cybernet '{cybernet_name}'. Database writes are fully unlocked for this cybernet."
    return _auto_progress_step(active, None, get_driver, sm_cypher, logger)


def get_schema() -> Dict[str, List[str]]:
    """Return the database schema (labels, relationship types, property keys)."""
    return _get_schema_impl(get_driver)


def adjust_transition_weight_internal(from_step_id: str, to_step_id: str,
                                      success: bool, cybernet_name: str) -> str:
    """Adjust weight of a NEXT_STEP transition; reinforcement after calibration."""
    return _adjust_transition_weight_impl(from_step_id, to_step_id, success, cybernet_name,
                                          get_driver, logger)


# --- Internal pattern matcher (gating logic) ---------------------------------

def _evaluate_pattern(query: str, active_step: Optional[Dict[str, Any]],
                      is_mutation: bool):
    """Apply the required_pattern gate; return (should_auto_progress, target_step_id).

    Raises PermissionError on disallowed writes. Centralized here so the gate
    logic is auditable in one place.
    """
    if not active_step:
        return False, None

    required = active_step.get("required_pattern")
    desc = active_step.get("pattern_description")
    transitions = active_step.get("transitions", [])

    if required:
        if _matches(required, query):
            return True, None
        if is_mutation:
            intent = f"Intent: {desc}. " if desc else ""
            raise PermissionError(
                f"Database Writes Locked: Active Traversal Step '{active_step['id']}'. "
                f"{intent}Your Cypher must match this regex pattern: {required}"
            )
        return False, None

    for tr in transitions:
        if tr.get("required_pattern") and _matches(tr["required_pattern"], query):
            return True, tr["id"]
    if transitions and is_mutation:
        choices = "; ".join(
            f"'{t['id']}' ({t.get('description', 'no description')}) → Cypher must match regex: {t['required_pattern']}"
            for t in transitions if t.get("required_pattern")
        )
        raise PermissionError(
            f"Database Writes Locked: Active Traversal Step '{active_step['id']}' "
            f"is a decision point. Choose one by emitting Cypher that matches its regex: {choices}"
        )
    if is_mutation:
        raise PermissionError(
            f"Database Writes Locked: Active Traversal Step '{active_step['id']}' is a leaf step."
        )
    return False, None


def _matches(pattern: str, query: str) -> bool:
    try:
        return bool(re.search(pattern, query))
    except Exception:
        return False
