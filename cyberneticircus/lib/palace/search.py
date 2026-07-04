"""
Mind Palace search — full-text search across pages + blocks.  (FLEET STUB — see MINDPALACE-IMPROVEMENTS.md)

Owns the search seam: a Neo4j full-text index over :Page(title) and :Block(content),
queried into ranked {page_id, title, snippet} hits for the workspace search box.

Graph shape (target):
  CREATE FULLTEXT INDEX palace_fts IF NOT EXISTS FOR (n:Page|Block) ON EACH [n.title, n.content]
  CALL db.index.fulltext.queryNodes('palace_fts', $q) YIELD node, score ...

Stubbed so a fleet agent can own it end-to-end without touching crud/blocks/graph.
Nothing here is wired into the router yet.
"""
from __future__ import annotations
from typing import Any, Dict, List


def ensure_index(driver) -> None:
    """ASPIRATIONAL: create the :Page/:Block full-text index if absent (idempotent)."""
    raise NotImplementedError("palace.search.ensure_index — fleet feature (full-text search)")


def search_palace(driver, *, query: str, mp_id: str | None = None, limit: int = 25) -> List[Dict[str, Any]]:
    """ASPIRATIONAL: ranked full-text hits across pages + blocks (optionally palace-scoped)."""
    raise NotImplementedError("palace.search.search_palace — fleet feature (full-text search)")
