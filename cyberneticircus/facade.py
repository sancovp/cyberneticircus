"""
The inner play-facade — the single callable that IS one CybernetiCircus move.

This is the library surface: a callable API, not a server. Every transport
delegates here — the web_server's POST /api/query (routers/query.py) and the
MCP tool (neo4j_cypher_mcp) — so "playing the game" means exactly one thing in
exactly one place.

The facade runs the play logic and RAISES domain errors for the caller to map
onto its own channel:
  - PermissionError  → a gate/security refusal (HTTP 403 / MCP tool error)
  - Neo4jError       → malformed cypher       (HTTP 400 / MCP tool error)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from db_logic import query_database, validate_cypher_query, trigger_traversal_by_location
from lib import recognizer, dispatcher, logs as lib_logs


def cyberneticircus(query: str, cybernet_name: Optional[str] = None,
                    parameters: Optional[Dict[str, Any]] = None,
                    current_filesystem_location: Optional[str] = None) -> Any:
    """Execute one CybernetiCircus move.

    If current_filesystem_location is reported, that travel is the bridge: a
    location mapping to a :Place flow locks the reporting cybernet into it BEFORE
    the query runs — so the move below is already subject to the entered flow's
    gate (the progressive-disclosure hijack, automated). Then recognize a
    frontend-action pattern; if none, run the cypher through the per-cybernet gate.
    Logs the move for the visualizer's witness; raises on a gated/invalid move.
    """
    if current_filesystem_location:
        lib_logs.log_agent_action(
            "travel", f"{cybernet_name or 'unknown'} entered {current_filesystem_location}",
            [current_filesystem_location], ["Place"],
        )
        trigger_traversal_by_location(cybernet_name, current_filesystem_location)

    try:
        action = recognizer.recognize(query)
        if action is not None:
            result = dispatcher.dispatch(action)
            if result is not None:
                lib_logs.log_agent_action(
                    "action",
                    f"Dispatched {action.intent} via cyberneticircus()",
                    [str(action.params)], [action.intent],
                )
                return result
    except NotImplementedError:
        pass

    validate_cypher_query(query)
    res = query_database(query, cybernet_name, parameters)
    focus_nodes, focus_labels = _scan_for_focus(res)
    lib_logs.log_agent_action("action", f"Executed query: {query}", focus_nodes, focus_labels)
    return res


def _scan_for_focus(results: Any) -> tuple[list[str], list[str]]:
    """Extract node names + labels from query results for the visualizer's focus overlay."""
    nodes: set = set()
    labels: set = set()

    def scan(val):
        if isinstance(val, dict):
            if "labels" in val and "properties" in val:
                props = val.get("properties", {})
                if "name" in props:
                    nodes.add(str(props["name"]))
                if "id" in props:
                    nodes.add(str(props["id"]))
                for k in ("title", "run_id", "sm_id", "id"):
                    if k in props:
                        nodes.add(str(props[k]))
                for lbl in val["labels"]:
                    labels.add(str(lbl))
            else:
                for v in val.values():
                    scan(v)
        elif isinstance(val, list):
            for item in val:
                scan(item)
        elif isinstance(val, (str, int, float)):
            sval = str(val).strip()
            if sval and len(sval) < 100:
                nodes.add(sval)
    try:
        scan(results)
    except Exception:
        pass
    return list(nodes), list(labels)
