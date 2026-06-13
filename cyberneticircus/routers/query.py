"""
Router: cypher shell — the only required HTTP endpoint.
Executes cypher against the graph with per-cybernet traversal gating.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from neo4j.exceptions import Neo4jError

from db_logic import query_database, validate_cypher_query
from lib import recognizer, dispatcher, logs as lib_logs


router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    cybernet_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


@router.post("/query")
def query_endpoint(req: QueryRequest):
    """Recognize frontend-action patterns first; if no match, run the cypher through the gate."""
    try:
        action = recognizer.recognize(req.query)
        if action is not None:
            result = dispatcher.dispatch(action)
            if result is not None:
                lib_logs.log_agent_action(
                    "action",
                    f"Dispatched {action.intent} via /api/query",
                    [str(action.params)], [action.intent],
                )
                return result
    except NotImplementedError:
        pass

    try:
        validate_cypher_query(req.query)
        res = query_database(req.query, req.cybernet_name, req.parameters)
    except PermissionError as e:
        # The state-machine gate (or the :Wiki/domain security policy) refused this
        # write. This is the load-bearing case: the message carries the required_pattern
        # so a playing agent knows what to emit next. 403, never a bare 500.
        raise HTTPException(status_code=403, detail=str(e))
    except Neo4jError as e:
        # Malformed cypher / DB-rejected query — client error, surface the reason.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Anything unexpected: still surface the message instead of a bare 500 body.
        raise HTTPException(status_code=500, detail=str(e))

    focus_nodes, focus_labels = _scan_for_focus(res)
    lib_logs.log_agent_action("action", f"Executed query: {req.query}", focus_nodes, focus_labels)
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
