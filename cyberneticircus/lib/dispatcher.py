"""
Dispatcher — calls the appropriate lib/<module>.py function for a
recognized Action. Returns the same shape the frontend's REST
endpoint would have returned.

Each handler:
    1. Calls a lib/ function (which constructs cypher + parameters).
    2. Runs the cypher via the shared driver.
    3. Shapes the result into the endpoint's response format.

The dispatcher is the bridge between the cypher shell (which only
knows how to run cypher) and the frontend's REST endpoints (which
know how to format responses).

Move-only rule: every handler MUST call into a lib/ function. No
business logic here — just glue.
"""
from __future__ import annotations
from typing import Any, List, Dict, Optional

from neo4j import GraphDatabase

from lib import recognizer

# Lib modules are imported lazily inside each handler so the dispatcher
# remains importable even before the full lib/ extraction is complete.
# If a lib/ module doesn't exist yet, that handler will return None and
# the cypher will fall through to normal execution.


# Use the shared driver from db_logic (the lib is below db_logic; we
# import lazily to avoid circular imports in the package).
def _driver():
    from db_logic import get_driver
    return get_driver()


def _run(cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Run cypher and return a list of dict records."""
    params = params or {}
    with _driver().session() as session:
        result = session.run(cypher, params)
        return [dict(r) for r in result]


def dispatch(action: recognizer.Action) -> Any:
    """Route a recognized Action to its handler. Return the response body."""
    handler = _HANDLERS.get(action.intent)
    if handler is None:
        raise NotImplementedError(f"No dispatcher for intent: {action.intent}")
    return handler(action.params)


# ─────────────────────────────────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────────────────────────────────

def _h_list_mind_palaces(params: Dict[str, Any]) -> Any:
    try:
        from lib import mind_palace
    except ImportError:
        return None
    cy, p = mind_palace.list_mindpalaces_cypher()
    records = _run(cy, p)
    return records


def _h_list_pages(params: Dict[str, Any]) -> Any:
    try:
        from lib import mind_palace
    except ImportError:
        return None
    cy, p = mind_palace.list_pages_cypher(params["mp_id"])
    records = _run(cy, p)
    return records


def _h_get_page(params: Dict[str, Any]) -> Any:
    try:
        from lib import mind_palace
    except ImportError:
        return None
    cy, p = mind_palace.get_page_cypher(params["page_id"])
    records = _run(cy, p)
    return records[0] if records else {}


def _h_create_mind_palace(params: Dict[str, Any]) -> Any:
    try:
        from lib import mind_palace
    except ImportError:
        return None
    # The frontend's POST /api/mindpalace payload has {id, name, description}.
    # The cypher-MERGE only needs name; the dispatcher fills sensible defaults
    # for the missing fields.
    name = params.get("name", "")
    cy, p = mind_palace.create_mindpalace_cypher(
        mp_id=f"mp_{name.lower().replace(' ', '_')}",
        name=name,
        description="",
    )
    records = _run(cy, p)
    return records[0] if records else {}


def _h_get_graph(params: Dict[str, Any]) -> Any:
    try:
        from lib import visualizer
    except ImportError:
        return None
    cy, p = visualizer.full_graph_cypher()
    return _run(cy, p)


def _h_get_node_subgraph(params: Dict[str, Any]) -> Any:
    try:
        from lib import visualizer
    except ImportError:
        return None
    cy, p = visualizer.node_subgraph_cypher(params["node_id"])
    return _run(cy, p)


_HANDLERS: Dict[str, callable] = {
    "list_mind_palaces":   _h_list_mind_palaces,
    "list_pages":          _h_list_pages,
    "get_page":            _h_get_page,
    "create_mind_palace":  _h_create_mind_palace,
    "get_graph":           _h_get_graph,
    "get_node_subgraph":   _h_get_node_subgraph,
}
