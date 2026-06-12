"""
Agent logs — in-memory ring buffer of recent agent actions + auto-detected
active cybernet + active step id. Read by the visualizer's log panel.

This is per-process state (not in neo4j), but it queries neo4j to
auto-resolve the active cybernet / step from the database.

Compositions:
  - log_agent_action  (mutator, not a route)
  - get_agent_logs    →  GET /api/agent_logs
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


# --- Module-level state (per-process, like the original web_server.py globals) ---

agent_trace_logs: List[Dict[str, Any]] = []
active_focus_nodes: set = set()
active_focus_labels: set = set()
active_cybernet: str = ""


# --- Mutator (called by other lib/ functions on agent events) ---------------

def log_agent_action(log_type: str, text: str,
                     focus_nodes: Optional[List[str]] = None,
                     focus_labels: Optional[List[str]] = None) -> None:
    """Append a log entry to the ring buffer + update focus sets."""
    global active_focus_nodes, active_focus_labels, active_cybernet
    if len(agent_trace_logs) > 100:
        agent_trace_logs.pop(0)
    agent_trace_logs.append({
        "type": log_type,
        "text": text,
        "focus_nodes": list(focus_nodes) if focus_nodes is not None else [],
        "focus_labels": list(focus_labels) if focus_labels is not None else [],
    })
    if focus_nodes is not None:
        active_focus_nodes = set(focus_nodes)
    if focus_labels is not None:
        active_focus_labels = set(focus_labels)
    if focus_labels is not None and "Cybernet" in focus_labels and focus_nodes:
        active_cybernet = focus_nodes[0]


# --- Auto-detect active cybernet (4-step cascade) ---------------------------

def _resolve_active_cybernet(driver) -> str:
    """1. in-memory active_cybernet if still valid. 2. any traversing cybernet. 3. most active cybernet."""
    global active_cybernet
    current = active_cybernet
    with driver.session() as session:
        if current:
            res = session.run("MATCH (c:Cybernet {name: $name}) RETURN c.name as name", {"name": current})
            if not res.single():
                current = ""
        if not current:
            res = session.run(
                "MATCH (c:Cybernet)-[:HAS_LIFECYCLE]->(i:ExecutionState)-[:CURRENT_STEP]->(curr:TraversalStep) "
                "RETURN c.name as name LIMIT 1"
            )
            rec = res.single()
            if rec:
                current = rec["name"]
                active_cybernet = current
        if not current:
            res = session.run(
                "MATCH (c:Cybernet) "
                "OPTIONAL MATCH (c)-[:HAS_LIFECYCLE]->(i:ExecutionState)-[:HAS_TRACE_HISTORY]->(t:ExecutionTrace) "
                "WITH c, count(t) as traces_count "
                "RETURN c.name as name ORDER BY traces_count DESC LIMIT 1"
            )
            rec = res.single()
            if rec:
                current = rec["name"]
                active_cybernet = current
    return current


# --- Composition (called by routers/logs.py) -------------------------------

def get_agent_logs(driver) -> Dict[str, Any]:
    """Return the recent log tail + the auto-detected active cybernet + its active step id."""
    current_active = _resolve_active_cybernet(driver)
    active_step_id = None
    if current_active:
        with driver.session() as session:
            res = session.run(
                "MATCH (c:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(i:ExecutionState)"
                "-[:CURRENT_STEP]->(curr:TraversalStep) RETURN id(curr) as curr_id",
                {"name": current_active}
            )
            rec = res.single()
            if rec:
                active_step_id = str(rec["curr_id"])
    return {
        "logs": list(agent_trace_logs),
        "active_cybernet": current_active,
        "active_step_id": active_step_id,
        "active_focus_nodes": list(active_focus_nodes),
        "active_focus_labels": list(active_focus_labels),
    }
