"""
Mind Palace search — full-text search across pages + blocks.

Owns the search seam: a Neo4j full-text index over :Page(title,content) and
:Block(title,content), queried into ranked hits for the workspace search box.

Composition:
  - search_palace  →  GET /api/mindpalace/search   (routers/palace_search.py)

Graph shape:
  CREATE FULLTEXT INDEX mindpalace_fulltext IF NOT EXISTS
    FOR (n:Page|Block) ON EACH [n.title, n.content]
  CALL db.index.fulltext.queryNodes('mindpalace_fulltext', $q) YIELD node, score ...

`domain: 'cyberneticity'` scoping (CREATE_PAGE_CYPHER / CREATE_BLOCK_CYPHER already
stamp it) is respected as a post-YIELD filter, same as the rest of palace/*.
mp_id scoping (optional) is resolved via crud.list_pages rather than a second
Cypher join, so this module stays a single isolated query + a Python filter.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .crud import list_pages

INDEX_NAME = "mindpalace_fulltext"

ENSURE_INDEX_CYPHER = (
    f"CREATE FULLTEXT INDEX {INDEX_NAME} IF NOT EXISTS "
    "FOR (n:Page|Block) ON EACH [n.title, n.content]"
)

SEARCH_CYPHER = """
CALL db.index.fulltext.queryNodes($index_name, $q) YIELD node, score
WHERE node.domain = 'cyberneticity'
OPTIONAL MATCH (owner:Page)-[:HAS_BLOCK]->(node)
WITH node, score, CASE WHEN 'Page' IN labels(node) THEN node ELSE owner END AS page
RETURN elementId(node) as id, labels(node) as labels, node.title as title,
       node.content as content, score, elementId(page) as page_id
ORDER BY score DESC
LIMIT $limit
"""


# --- Compositions -------------------------------------------------------------

def ensure_index(driver) -> None:
    """Idempotently create the :Page/:Block full-text index if absent."""
    with driver.session() as session:
        session.run(ENSURE_INDEX_CYPHER)


def search_palace(driver, *, query: str, mp_id: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
    """Ranked full-text hits across pages + blocks (optionally palace-scoped)."""
    ensure_index(driver)

    page_ids = None
    if mp_id:
        page_ids = {p["id"] for p in list_pages(driver, mp_id=mp_id)}

    with driver.session() as session:
        rows = [dict(r) for r in session.run(SEARCH_CYPHER, {"index_name": INDEX_NAME, "q": query, "limit": limit})]

    results = []
    for row in rows:
        if page_ids is not None and row.get("page_id") not in page_ids:
            continue
        labels = row.get("labels") or []
        results.append({
            "id": row.get("id"),
            "label": labels[0] if labels else "Unknown",
            "title": row.get("title"),
            "content": row.get("content"),
            "score": row.get("score"),
            "page_id": row.get("page_id"),
        })
    return results
