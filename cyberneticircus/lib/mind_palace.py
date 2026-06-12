"""
Mind Palace CRUD + JSON import/export — the wiki/Notion-like subgraph in the graph.

Compositions:
  - list_mindpalaces  →  GET /api/mindpalaces
  - create_mindpalace  →  POST /api/mindpalace
  - list_pages         →  GET /api/mindpalace/{mp_id}/pages
  - create_page        →  POST /api/mindpalace/{mp_id}/page
  - get_page           →  GET /api/mindpalace/page/{page_id}
  - save_blocks        →  POST /api/mindpalace/page/{page_id}/blocks
  - delete_page        →  DELETE /api/mindpalace/page/{page_id}
  - export_palace      →  POST /api/mindpalace/{mp_id}/export
  - import_palace      →  POST /api/mindpalace/import
"""
from __future__ import annotations
import json
import uuid
from typing import Any, Dict, List, Optional


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

DELETE_PAGE_BLOCKS_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
OPTIONAL MATCH (p)-[:HAS_BLOCK]->(b:Block)
DETACH DELETE b
"""

CREATE_BLOCK_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
CREATE (b:Block {
    id: $block_id,
    type: $type,
    content: $content,
    position: $position,
    level: $level,
    language: $language,
    domain: 'cyberneticity',
    subdomain: 'block'
})
CREATE (p)-[:HAS_BLOCK]->(b)
"""

DELETE_PAGE_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
OPTIONAL MATCH (p)-[:HAS_BLOCK]->(b:Block)
DETACH DELETE p, b
"""

EXPORT_PATHS_CYPHER = """
MATCH (mp:MindPalace) WHERE elementId(mp) = $mp_id OR id(mp) = $mp_id_int OR mp.id = $mp_id
OPTIONAL MATCH path = (mp)-[*1..3]->(m)
WITH mp, collect(path) as paths
RETURN mp, paths
"""


# --- Compositions (called by routers/mind_palace.py — 1-line delegations) ---

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
    try:
        mp_id_int = int(mp_id)
    except ValueError:
        mp_id_int = -1
    with driver.session() as session:
        res = session.run(LIST_PAGES_CYPHER, {"mp_id": mp_id, "mp_id_int": mp_id_int})
        return [dict(r) for r in res]


def create_page(driver, *, mp_id: str, title: str) -> Dict[str, Any]:
    """Create a new Page under a MindPalace."""
    try:
        mp_id_int = int(mp_id)
    except ValueError:
        mp_id_int = -1
    page_id = f"page_{uuid.uuid4().hex}"
    with driver.session() as session:
        res = session.run(CREATE_PAGE_CYPHER, {"mp_id": mp_id, "mp_id_int": mp_id_int, "page_id": page_id, "title": title})
        return dict(res.single())


def get_page(driver, *, page_id: str) -> Dict[str, Any]:
    """Get a Page + its ordered Blocks. Returns {} if not found."""
    try:
        page_id_int = int(page_id)
    except ValueError:
        page_id_int = -1
    with driver.session() as session:
        rec = session.run(GET_PAGE_CYPHER, {"page_id": page_id, "page_id_int": page_id_int}).single()
        if not rec:
            return {}
        data = dict(rec)
        blocks = [b for b in data["blocks"] if b]
        blocks.sort(key=lambda x: x.get("position", 0))
        data["blocks"] = blocks
        return data


def save_blocks(driver, *, page_id: str, title: Optional[str], blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Replace the Blocks of a Page atomically (DETACH DELETE old, CREATE new)."""
    try:
        page_id_int = int(page_id)
    except ValueError:
        page_id_int = -1
    with driver.session() as session:
        if title:
            session.run(
                "MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id SET p.title = $title",
                {"page_id": page_id, "page_id_int": page_id_int, "title": title}
            )
        session.run(DELETE_PAGE_BLOCKS_CYPHER, {"page_id": page_id, "page_id_int": page_id_int})
        for idx, block in enumerate(blocks):
            block_id = f"block_{uuid.uuid4().hex}"
            session.run(CREATE_BLOCK_CYPHER, {
                "page_id": page_id, "page_id_int": page_id_int, "block_id": block_id,
                "type": block["type"], "content": block["content"], "position": idx,
                "level": block.get("level", 1), "language": block.get("language", "text"),
            })
        return {"status": "success", "message": "Blocks saved successfully."}


def delete_page(driver, *, page_id: str) -> Dict[str, Any]:
    """DETACH DELETE a Page and its Blocks."""
    try:
        page_id_int = int(page_id)
    except ValueError:
        page_id_int = -1
    with driver.session() as session:
        session.run(DELETE_PAGE_CYPHER, {"page_id": page_id, "page_id_int": page_id_int})
        return {"status": "success", "message": "Page and associated blocks deleted."}


def export_palace(driver, *, mp_id: str) -> Dict[str, Any]:
    """Export a MindPalace subgraph (3 hops) as a JSON-serializable dict."""
    try:
        mp_id_int = int(mp_id)
    except ValueError:
        mp_id_int = -1

    nodes = []
    links = []
    node_ids = set()

    def _add_node(node):
        if not node:
            return None
        nid = str(node.element_id) if hasattr(node, "element_id") else (str(node.id) if hasattr(node, "id") else str(hash(node)))
        if nid not in node_ids:
            node_ids.add(nid)
            labels = list(node.labels)
            label = labels[0] if labels else "Unknown"
            display_name = node.get("name") or node.get("title") or node.get("id") or label
            nodes.append({"id": nid, "label": label, "name": display_name, "properties": dict(node)})
        return nid

    with driver.session() as session:
        record = session.run(EXPORT_PATHS_CYPHER, {"mp_id": mp_id, "mp_id_int": mp_id_int}).single()
        if not record:
            return {"mindpalace_id": mp_id, "export_data": {"nodes": [], "links": []}}
        mp_node = record["mp"]
        paths = record["paths"] or []
        _add_node(mp_node)
        for path in paths:
            if not path:
                continue
            for nd in path.nodes:
                _add_node(nd)
            for rel in path.relationships:
                src_nid = str(rel.start_node.element_id) if hasattr(rel.start_node, "element_id") else str(rel.start_node.id)
                tgt_nid = str(rel.end_node.element_id) if hasattr(rel.end_node, "element_id") else str(rel.end_node.id)
                link_item = {"source": src_nid, "target": tgt_nid, "type": rel.type}
                if link_item not in links:
                    links.append(link_item)
    return {"mindpalace_id": mp_id, "export_data": {"nodes": nodes, "links": links}}


def import_palace(driver, *, export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Idempotently import a MindPalace JSON bundle (MERGE on id/name)."""
    nodes = export_data.get("nodes", [])
    links = export_data.get("links", [])
    id_map = {}
    with driver.session() as session:
        for nd in nodes:
            properties = nd.get("properties", {})
            label = nd.get("label", "Unknown")
            old_id = nd.get("id")
            if "domain" not in properties:
                properties["domain"] = "cyberneticity"
            if "subdomain" not in properties:
                properties["subdomain"] = "imported"
            merge_key = "id" if "id" in properties else "name"
            merge_val = properties.get(merge_key)
            if merge_val is not None:
                res = session.run(
                    f"MERGE (n:{label} {{{merge_key}: $merge_val}}) SET n += $props RETURN elementId(n) as new_id",
                    {"merge_val": merge_val, "props": properties}
                )
            else:
                res = session.run(
                    f"CREATE (n:{label}) SET n = $props RETURN elementId(n) as new_id",
                    {"props": properties}
                )
            record = res.single()
            if record:
                id_map[old_id] = record["new_id"]
        for l in links:
            src_old = l["source"]
            tgt_old = l["target"]
            rel_type = l["type"]
            src_new = id_map.get(src_old)
            tgt_new = id_map.get(tgt_old)
            if src_new and tgt_new:
                session.run(
                    "MATCH (a) WHERE elementId(a) = $src MATCH (b) WHERE elementId(b) = $tgt MERGE (a)-[r:%s]->(b)" % rel_type,
                    {"src": src_new, "tgt": tgt_new}
                )
        return {"status": "success", "message": f"Successfully imported {len(nodes)} nodes and {len(links)} links."}
