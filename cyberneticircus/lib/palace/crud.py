"""
Mind Palace CRUD — the :MindPalace + :Page lifecycle (hubs and pages).

Compositions (called by routers/mind_palace.py via the lib.mind_palace facade):
  - list_mindpalaces   →  GET  /api/mindpalaces
  - create_mindpalace  →  POST /api/mindpalace
  - list_pages         →  GET  /api/mindpalace/{mp_id}/pages
  - create_page        →  POST /api/mindpalace/{mp_id}/page
  - get_page           →  GET  /api/mindpalace/page/{page_id}
  - delete_page        →  DELETE /api/mindpalace/page/{page_id}

Block read is included in get_page (the page-read endpoint returns its ordered
blocks); the block WRITE path lives in palace/blocks.py.
"""
from __future__ import annotations
import uuid
from typing import Any, Dict, List


# --- Cypher-string constructors ---------------------------------------------

LIST_MINDPALACES_CYPHER = """
MATCH (mp:MindPalace)
RETURN elementId(mp) as id, mp.name as name, mp.domain as domain, mp.subdomain as subdomain, mp.description as description
ORDER BY mp.name
"""

CREATE_MINDPALACE_CYPHER = """
MERGE (mp:MindPalace {name: $name})
ON CREATE SET mp.id = $id, mp.description = $description, mp.domain = 'cyberneticity', mp.subdomain = 'mindpalace'
ON MATCH SET mp.description = $description
RETURN elementId(mp) as elem_id, mp.id as id, mp.name as name, mp.description as description
"""

LIST_PAGES_CYPHER = """
MATCH (mp:MindPalace) WHERE elementId(mp) = $mp_id OR id(mp) = $mp_id_int OR mp.id = $mp_id
MATCH (mp)-[:HAS_PAGE]->(p:Page)
RETURN elementId(p) as id, p.id as page_id, p.title as title, p.domain as domain, p.subdomain as subdomain
ORDER BY p.title
"""

CREATE_PAGE_CYPHER = """
MATCH (mp:MindPalace) WHERE elementId(mp) = $mp_id OR id(mp) = $mp_id_int OR mp.id = $mp_id
CREATE (p:Page {id: $page_id, title: $title, domain: 'cyberneticity', subdomain: 'page'})
CREATE (mp)-[:HAS_PAGE]->(p)
RETURN elementId(p) as id, p.id as page_id, p.title as title
"""

GET_PAGE_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
OPTIONAL MATCH (p)-[:HAS_BLOCK]->(b:Block)
RETURN elementId(p) as id, p.id as page_id, p.title as title, p.domain as domain, p.subdomain as subdomain,
       collect(properties(b)) as blocks
"""

DELETE_PAGE_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
OPTIONAL MATCH (p)-[:HAS_BLOCK]->(b:Block)
DETACH DELETE p, b
"""


def _coerce_int(value: str) -> int:
    """Numeric ids map to id() lookups; non-numeric (elementId/uuid) map to -1."""
    try:
        return int(value)
    except ValueError:
        return -1


# --- Compositions -----------------------------------------------------------

def list_mindpalaces(driver) -> List[Dict[str, Any]]:
    """List all MindPalace hubs (for the wiki sidebar)."""
    with driver.session() as session:
        res = session.run(LIST_MINDPALACES_CYPHER)
        return [dict(r) for r in res]


def create_mindpalace(driver, *, name: str, description: str = "") -> Dict[str, Any]:
    """MERGE a new MindPalace (idempotent on name). Returns the merged node."""
    mp_id = f"mp_{uuid.uuid4().hex}"
    with driver.session() as session:
        res = session.run(CREATE_MINDPALACE_CYPHER, {"name": name, "description": description, "id": mp_id})
        return dict(res.single())


def list_pages(driver, *, mp_id: str) -> List[Dict[str, Any]]:
    """List all Pages under a MindPalace."""
    with driver.session() as session:
        res = session.run(LIST_PAGES_CYPHER, {"mp_id": mp_id, "mp_id_int": _coerce_int(mp_id)})
        return [dict(r) for r in res]


def create_page(driver, *, mp_id: str, title: str) -> Dict[str, Any]:
    """Create a new Page under a MindPalace."""
    page_id = f"page_{uuid.uuid4().hex}"
    with driver.session() as session:
        res = session.run(CREATE_PAGE_CYPHER,
                          {"mp_id": mp_id, "mp_id_int": _coerce_int(mp_id), "page_id": page_id, "title": title})
        return dict(res.single())


def get_page(driver, *, page_id: str) -> Dict[str, Any]:
    """Get a Page + its ordered Blocks. Returns {} if not found."""
    with driver.session() as session:
        rec = session.run(GET_PAGE_CYPHER, {"page_id": page_id, "page_id_int": _coerce_int(page_id)}).single()
        if not rec:
            return {}
        data = dict(rec)
        blocks = [b for b in data["blocks"] if b]
        blocks.sort(key=lambda x: x.get("position", 0))
        data["blocks"] = blocks
        return data


def delete_page(driver, *, page_id: str) -> Dict[str, Any]:
    """DETACH DELETE a Page and its Blocks."""
    with driver.session() as session:
        session.run(DELETE_PAGE_CYPHER, {"page_id": page_id, "page_id_int": _coerce_int(page_id)})
        return {"status": "success", "message": "Page and associated blocks deleted."}
