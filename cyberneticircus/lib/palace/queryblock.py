"""
Mind Palace query-block — run a block's read-only Cypher inline (MINDPALACE-IMPROVEMENTS.md #4 / A2).

A query-block is a normal `:Block {type:'query', content:<cypher>, subdomain:'block'}` (no new
node type, no allowlist change) whose `content` is a **read-only Cypher query**. Running it
renders LIVE graph state inside a page — the graph-native wiki feature Notion structurally cannot
have (Roam/Tana fake it with a mini-language; here it is real Cypher against the real graph).

SECURITY IS THE POINT of this module. The guard is COMPOSED from the canonical gate atoms in
`lib/gates.py` — it is NOT a new validator (reference-canonical-impl-first):

  1. `is_mutation_query`  → refuse ANY write (CREATE/MERGE/SET/DELETE/REMOVE/DETACH). A render
     block must never mutate. This is STRICTER than `validate_cypher_query`, which only refuses
     :Wiki *writes* + un-scoped CREATE/MERGE and would let a bare `MATCH .. DELETE` through.
  2. the :Wiki firewall (mirrors the pattern in gates.py `validate_cypher_query`) → refuse any
     query that TOUCHES :Wiki. The canonical gate only blocks :Wiki *writes*; a read-only block
     must not READ :Wiki either, or private-wiki content would leak into the palace.
  3. `validate_cypher_query` → still run the canonical gate (a no-op for a clean read; belt-and-
     suspenders if a mutation ever slipped past step 1).

Execution reuses `run_cypher` (the canonical raw executor) rather than `query_database`, so a
passive render block does NOT trigger the per-cybernet ExecutionState lock / bandit auto-progress
that "playing the game" via `query_database` entails — a query block observes, it does not play.

Composition:
  - run_query_block  →  POST /api/mindpalace/queryblock/run   (routers/palace_queryblock.py)
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

from ..gates import (
    is_mutation_query,
    validate_cypher_query,
    run_cypher,
    serialize_value,
)

# Mirrors the canonical :Wiki firewall pattern in lib/gates.py (validate_cypher_query).
_WIKI_RE = re.compile(r':\bwiki\b', re.IGNORECASE)


def guard_read_only(cypher: str) -> None:
    """Refuse anything that is not a pure, :Wiki-free read. Raises PermissionError (→ HTTP 403)."""
    if is_mutation_query(cypher):
        raise PermissionError(
            "Security Policy Violation: Query blocks are STRICTLY READ-ONLY; write mutations "
            "(CREATE / MERGE / SET / DELETE / REMOVE / DETACH) are refused."
        )
    if _WIKI_RE.search(cypher):
        raise PermissionError(
            "Security Policy Violation: Query blocks may not touch the :Wiki namespace."
        )
    validate_cypher_query(cypher)  # canonical gate — no-op for a clean read


def run_query_block(driver, *, cypher: str) -> List[Dict[str, Any]]:
    """Guard a query-block's Cypher (read-only + :Wiki-free), execute it, return JSON-safe rows.

    Reuses the canonical `run_cypher` executor (per-record `serialize_value`); no parameters and
    no ExecutionState side-effects — a query block renders graph state, it does not mutate or play.
    """
    guard_read_only(cypher)
    return run_cypher(cypher, {}, lambda: driver, serialize_value)
