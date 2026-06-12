"""
Recognizer — pattern-matches a Cypher query against a registry of
"frontend action" intents. The dispatcher (lib/dispatcher.py) then
calls the corresponding lib/<module>.py function and returns the
same shape the frontend's REST endpoint would have returned.

This is the "MCP should be able to do what the frontend does"
pattern from cyberneticircus-architecture.md. The cypher shell
(/api/query in web_server.py) runs the recognizer BEFORE the
existing cypher execution; if the recognizer returns an Action,
the cypher is NOT executed against the graph and the dispatcher's
result is returned instead.

The recognizer is intentionally narrow: it only matches the exact
cypher patterns the frontend's endpoints emit. Any other cypher
falls through to the normal execution path.

Adding a new recognized pattern:
    1. Add a new value to the Action enum (or use a string name).
    2. Add a regex to RECOGNIZERS mapping that pattern to that name.
    3. Add a handler in lib/dispatcher.py that calls the right lib/ fn.

The recognizer is read-only — it never mutates. The dispatcher may.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple


@dataclass
class Action:
    """A recognized frontend-style action extracted from a cypher query.

    `intent` is the kind of action (e.g. "list_mind_palaces").
    `params` is the dict of extracted query parameters (e.g. {"mp_id": "..."}).
    """
    intent: str
    params: Dict[str, Any]


# Each entry: (compiled-regex, intent-name, params-extractor)
# The params-extractor takes a Match and returns a dict.
#
# Patterns mirror the cypher the frontend's REST endpoints emit. We are
# NOT trying to recognize every cypher — just the small set the frontend
# (or the MCP acting as the frontend) would send.
def _match_list_mind_palaces(m: re.Match) -> Dict[str, Any]:
    return {}


def _match_list_pages(m: re.Match) -> Dict[str, Any]:
    return {"mp_id": m.group("mp_id")}


def _match_get_page(m: re.Match) -> Dict[str, Any]:
    return {"page_id": m.group("page_id")}


def _match_create_mind_palace(m: re.Match) -> Dict[str, Any]:
    return {"name": m.group("name")}


def _match_get_graph(m: re.Match) -> Dict[str, Any]:
    return {}


def _match_get_node_subgraph(m: re.Match) -> Dict[str, Any]:
    return {"node_id": m.group("node_id")}


RECOGNIZERS: Tuple[Tuple[re.Pattern, str, callable], ...] = (
    # Mind Palace: list all palaces
    (re.compile(
        r"^MATCH\s*\(\s*mp\s*:\s*MindPalace\s*\)\s*RETURN\s+mp(?:\s+LIMIT\s+\d+)?\s*$",
        re.IGNORECASE,
    ), "list_mind_palaces", _match_list_mind_palaces),

    # Mind Palace: list pages under a palace
    (re.compile(
        r"^MATCH\s*\(\s*mp\s*:\s*MindPalace\s*\{[^}]*\}\)\s*-\s*\[\s*:\s*HAS_PAGE\s*\]\s*->\s*\(\s*p\s*:\s*Page\s*\)\s*RETURN\s+(?P<ret>.*)$",
        re.IGNORECASE,
    ), "list_pages", _match_list_pages),

    # Mind Palace: get a single page
    (re.compile(
        r"^MATCH\s*\(\s*p\s*:\s*Page\s*\{[^}]*\}\)\s*OPTIONAL\s+MATCH\s*\(\s*p\s*\)\s*-\s*\[\s*:\s*HAS_BLOCK\s*\]\s*->\s*\(\s*b\s*:\s*Block\s*\)\s*RETURN\s+.*$",
        re.IGNORECASE,
    ), "get_page", _match_get_page),

    # Mind Palace: create / merge a new palace
    (re.compile(
        r"^MERGE\s*\(\s*n\s*:\s*MindPalace\s*\{\s*name\s*:\s*\$name\s*\}\s*\).*$",
        re.IGNORECASE,
    ), "create_mind_palace", _match_create_mind_palace),

    # Graph: full game graph fetch (the visualizer's `MATCH (n) ... RETURN n, r, m`)
    (re.compile(
        r"^MATCH\s*\(\s*n\s*\)\s+WHERE\s+.*OR\s+.*StateMachine.*RETURN\s+n,\s*r,\s*m.*$",
        re.IGNORECASE | re.DOTALL,
    ), "get_graph", _match_get_graph),

    # Graph: focused subgraph of a node
    (re.compile(
        r"^MATCH\s*\(\s*n\s*\)\s+WHERE\s+(?:elementId|n)\(\s*n\s*\)\s*=\s*\$node_id.*RETURN\s+.*$",
        re.IGNORECASE | re.DOTALL,
    ), "get_node_subgraph", _match_get_node_subgraph),
)


def recognize(cypher: str) -> Optional[Action]:
    """Pattern-match a cypher query against the registry of frontend actions.

    Returns an Action if matched, None if no pattern matches (i.e. the
    cypher is not a frontend action and should be executed normally).
    """
    if not cypher or not isinstance(cypher, str):
        return None
    normalized = cypher.strip()
    for pattern, intent, params_fn in RECOGNIZERS:
        m = pattern.match(normalized)
        if m:
            try:
                params = params_fn(m)
            except Exception:
                params = {}
            return Action(intent=intent, params=params)
    return None
