"""
Mind Palace graph — JSON plugin export/import + graph-view projection.

Compositions:
  - export_palace  →  POST /api/mindpalace/{mp_id}/export
  - import_palace  →  POST /api/mindpalace/import

Export walks the palace subgraph (3 hops) into a {nodes, links} bundle; import
idempotently MERGEs it back (on id, else name). This is also the natural home for
the D3 "Island District" graph-view projection (:MindPalace hub + :Page/:Block
satellites) — a fleet feature; see MINDPALACE-IMPROVEMENTS.md.
"""
from __future__ import annotations
from typing import Any, Dict

from .crud import _coerce_int


# --- Cypher-string constructors ---------------------------------------------

EXPORT_PATHS_CYPHER = """
MATCH (mp:MindPalace) WHERE elementId(mp) = $mp_id OR id(mp) = $mp_id_int OR mp.id = $mp_id
OPTIONAL MATCH path = (mp)-[*1..3]->(m)
WITH mp, collect(path) as paths
RETURN mp, paths
"""


# --- Compositions -----------------------------------------------------------

def export_palace(driver, *, mp_id: str) -> Dict[str, Any]:
    """Export a MindPalace subgraph (3 hops) as a JSON-serializable dict."""
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
        record = session.run(EXPORT_PATHS_CYPHER, {"mp_id": mp_id, "mp_id_int": _coerce_int(mp_id)}).single()
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
