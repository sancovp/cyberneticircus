"""
Visualizer data — the D3 graph + focused subgraph.

Compositions:
  - get_graph            →  GET /api/graph
  - get_node_subgraph    →  GET /api/node/subgraph

Both use isolated CALL subqueries (per jani_likes) to query one-to-many
relationships independently and keep variable scopes isolated — sub-100ms
response times even on 500k+ node databases.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Set


# --- Cypher strings ---------------------------------------------------------

GRAPH_FOR_CYBERNET_CYPHER = """
MATCH (c:Cybernet {name: $name})
OPTIONAL MATCH (c)-[:HAS_LIFECYCLE]->(es:ExecutionState)
OPTIONAL MATCH (es)-[:CURRENT_STEP]->(curr:TraversalStep)
OPTIONAL MATCH (c)-[:EQUIPS]->(sm:StateMachine)
OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)

CALL {
    WITH sm
    OPTIONAL MATCH (sm)-[:INITIAL_STATE|TRANSITION_TO|ON_STATE*0..5]->(sms)
    RETURN collect(DISTINCT sms) as sms_list
}

CALL {
    WITH c
    OPTIONAL MATCH (c)-[:HAS_MIND_PALACE]->(root_c:Concept)
    OPTIONAL MATCH (root_c)-[:SUB_CONCEPT*0..1]->(con:Concept)
    RETURN collect(DISTINCT con)[0..30] as con_list
}

CALL {
    WITH c
    OPTIONAL MATCH (c)-[:EQUIPS_SKILL]->(sk:Skill)
    RETURN collect(DISTINCT sk)[0..30] as sk_list
}

CALL {
    WITH c
    OPTIONAL MATCH (c)-[:HAS_SIMULATION]->(sim:SimulationRun)
    RETURN collect(DISTINCT sim)[0..30] as sim_list
}

CALL {
    WITH es
    OPTIONAL MATCH (es)-[:HAS_TRACE_HISTORY]->(t1:ExecutionTrace)-[:NEXT_TRACE*0..30]->(tr:ExecutionTrace)
    RETURN collect(DISTINCT tr)[0..30] as tr_list
}

WITH [c] + [es] + [i] + [curr] + [sm] + sms_list + con_list + sk_list + sim_list + tr_list as all_nodes_raw
UNWIND all_nodes_raw as n
WITH n WHERE n IS NOT NULL
WITH collect(DISTINCT n) as all_nodes
UNWIND all_nodes as n
OPTIONAL MATCH (n)-[r]->(m)
WHERE m IN all_nodes
RETURN n, r, m
"""

FULL_GRAPH_CYPHER = """
MATCH (n)
WHERE n:Cybernet OR n:Identity OR n:ExecutionState OR n:StateMachine OR n:TraversalStep OR n:TraversalState OR n:SimulationRun OR n:MindPalace OR n:Page
WITH collect(DISTINCT n) as all_nodes
UNWIND all_nodes as n
WITH DISTINCT n, all_nodes
OPTIONAL MATCH (n)-[r]->(m)
WHERE m IN all_nodes
RETURN n, r, m
"""

NODE_SUBGRAPH_CYPHER = """
MATCH (n) WHERE elementId(n) = $node_id OR id(n) = $node_id_int
OPTIONAL MATCH path = (n)-[*0..2]->(m)
WITH path LIMIT 200
WITH collect(path) as paths
UNWIND paths as p
UNWIND nodes(p) as nd
WITH DISTINCT nd, paths
OPTIONAL MATCH (nd)-[r]->(md)
WHERE any(p in paths WHERE md IN nodes(p))
RETURN nd, r, md
"""

ACTIVE_NODES_CYPHER = """
MATCH (m:Cybernet {name: $name})
OPTIONAL MATCH (m)-[:HAS_LIFECYCLE]->(s:ExecutionState)
OPTIONAL MATCH (s)-[:CURRENT_STEP]->(curr:TraversalStep)
OPTIONAL MATCH (m)-[:EQUIPS]->(sm:StateMachine)
RETURN id(m) as m_id, id(curr) as curr_id, id(sm) as sm_id
"""


def _serialize_props(properties: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-safe conversion of neo4j property values."""
    import json
    out = {}
    for k, v in properties.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
            out[k] = str(v)
        else:
            try:
                json.dumps(v)
                out[k] = v
            except TypeError:
                out[k] = str(v)
    return out


def _node_id(node) -> str:
    if hasattr(node, "element_id") and node.element_id is not None:
        return str(node.element_id)
    if hasattr(node, "id") and node.id is not None:
        return str(node.id)
    return str(hash(node))


def _add_node(node, *, node_ids: Set[str], active_cybernet_id: Optional[str],
              current_step_id: Optional[str], equipped_sm_id: Optional[str],
              active_focus_nodes: Set[str], active_focus_labels: Set[str],
              active_tag_default: str = None) -> Optional[Dict[str, Any]]:
    """Build the JSON shape the visualizer expects (id, label, name, properties, active_tag, highlighted)."""
    if not node:
        return None
    nid = _node_id(node)
    if nid in node_ids:
        return None
    node_ids.add(nid)
    labels = list(node.labels)
    label = labels[0] if labels else "Unknown"
    display_name = node.get("name") or node.get("id") or node.get("run_id") or label

    if active_tag_default is None:
        if nid == active_cybernet_id:
            active_tag = "cybernet"
        elif nid == current_step_id:
            active_tag = "step"
        elif nid == equipped_sm_id:
            active_tag = "state_machine"
        else:
            active_tag = False
    else:
        active_tag = active_tag_default

    highlighted = (
        display_name in active_focus_nodes
        or nid in active_focus_nodes
        or label in active_focus_labels
        or any(lbl in active_focus_labels for lbl in labels)
    )
    return {
        "id": nid,
        "label": label,
        "name": display_name,
        "properties": _serialize_props(dict(node)),
        "active_tag": active_tag,
        "highlighted": highlighted,
    }


# --- Compositions (called by routers/graph.py) -----------------------------

def get_graph(driver, *, name: Optional[str] = None,
              active_focus_nodes: Optional[set] = None,
              active_focus_labels: Optional[set] = None) -> Dict[str, Any]:
    """Build the d3 graph JSON for the visualizer.

    If `name` is given: focused subgraph around the named Cybernet (4-step
    isolated CALL subquery pattern, per jani_likes, no cartesian blowup).
    If `name` is None: full game graph (all known primitive labels).
    """
    active_focus_nodes = active_focus_nodes or set()
    active_focus_labels = active_focus_labels or set()
    nodes: list = []
    links: list = []
    node_ids: set = set()
    current_step_node_id = None
    active_cybernet_node_id = None
    equipped_sm_node_id = None

    with driver.session() as session:
        if name:
            rec = session.run(ACTIVE_NODES_CYPHER, {"name": name}).single()
            if rec:
                active_cybernet_node_id = str(rec["m_id"]) if rec["m_id"] is not None else None
                current_step_node_id = str(rec["curr_id"]) if rec["curr_id"] is not None else None
                equipped_sm_node_id = str(rec["sm_id"]) if rec["sm_id"] is not None else None
            res = session.run(GRAPH_FOR_CYBERNET_CYPHER, {"name": name})
        else:
            res = session.run(FULL_GRAPH_CYPHER)
        for record in res:
            n_node = record["n"]
            m_node = record["m"]
            rel = record["r"]
            n_item = _add_node(n_node, node_ids=node_ids,
                               active_cybernet_id=active_cybernet_node_id,
                               current_step_id=current_step_node_id,
                               equipped_sm_id=equipped_sm_node_id,
                               active_focus_nodes=active_focus_nodes,
                               active_focus_labels=active_focus_labels)
            m_item = _add_node(m_node, node_ids=node_ids,
                               active_cybernet_id=active_cybernet_node_id,
                               current_step_id=current_step_node_id,
                               equipped_sm_id=equipped_sm_node_id,
                               active_focus_nodes=active_focus_nodes,
                               active_focus_labels=active_focus_labels)
            if n_item is not None:
                nodes.append(n_item)
            if m_item is not None:
                nodes.append(m_item)
            if rel is not None and n_node is not None and m_node is not None:
                n_id = _node_id(n_node)
                m_id = _node_id(m_node)
                link_item = {"source": n_id, "target": m_id, "type": rel.type}
                if link_item not in links:
                    links.append(link_item)
    return {"nodes": nodes, "links": links}


def get_node_subgraph(driver, *, node_id: str) -> Dict[str, Any]:
    """Focused 2-hop subgraph around a specific node (used by the visualizer inspector)."""
    try:
        node_id_int = int(node_id)
    except ValueError:
        node_id_int = -1
    nodes: list = []
    links: list = []
    node_ids: set = set()
    with driver.session() as session:
        for record in session.run(NODE_SUBGRAPH_CYPHER, {"node_id": node_id, "node_id_int": node_id_int}):
            nd = record["nd"]
            md = record["md"]
            rel = record["r"]
            n_item = _add_node(nd, node_ids=node_ids, active_cybernet_id=None, current_step_id=None,
                               equipped_sm_id=None, active_focus_nodes=set(), active_focus_labels=set())
            m_item = _add_node(md, node_ids=node_ids, active_cybernet_id=None, current_step_id=None,
                               equipped_sm_id=None, active_focus_nodes=set(), active_focus_labels=set())
            if n_item is not None:
                nodes.append(n_item)
            if m_item is not None:
                nodes.append(m_item)
            if rel is not None and nd is not None and md is not None:
                link_item = {"source": _node_id(nd), "target": _node_id(md), "type": rel.type}
                if link_item not in links:
                    links.append(link_item)
    return {"nodes": nodes, "links": links}
