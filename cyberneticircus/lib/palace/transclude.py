"""
Mind Palace block transclusion — the ((block_id)) reference + :TRANSCLUDES edge.

The graph-native version of Notion's "sync blocks": a block whose content embeds a
``((block_id))`` token renders the LIVE content of that referenced block — the SAME
graph node, not a copy — so an edit to the source propagates structurally to every
place that transcludes it (no fan-out write, no stale duplicate).

Two seams, both keyed on the STABLE block id (palace/blocks.py, P0 — a transclude
ref keyed on a shifting id would orphan on the next save):

  - resolve_page_blocks  → the READ hook (called inside crud.get_page). For every page
                           block that references ((ids)), it (a) reconciles the
                           first-class ``(:Block)-[:TRANSCLUDES]->(:Block)`` edges for
                           graph-viz, and (b) attaches a `transclusions` list of the
                           resolved live content so the frontend can render the embed
                           in place of the raw ``((id))`` token (the raw token stays in
                           `content`; the resolved side rides alongside).
  - get_transclusions    → GET /api/mindpalace/block/{block_id}/transclusions (reverse
                           edges) — WHO transcludes this block, so editing a source can
                           show its dependents.

Graph is sacred — a transclusion is an EDGE, not a scanned property. Resolution is a
BOUNDED pass: transclusion-of-transclusion is followed only to `depth_limit`, and a
CYCLE GUARD (a block that transcludes itself, or an A→B→A loop) renders a clear "cycle"
placeholder instead of recursing forever.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple

# ((block_id)) syntax — the canonical transclusion token (double parens, no nesting).
TRANSCLUDE_RE = re.compile(r"\(\(([^()]+)\)\)")

# How deep transclusion-of-transclusion is followed (direct ref = depth 1). A ref beyond
# this is returned with depth_exceeded=True rather than expanded — the bound that, with
# the cycle guard, keeps resolution finite.
DEFAULT_DEPTH_LIMIT = 3


# --- Cypher-string constructors ---------------------------------------------

# Fetch a referenced block's LIVE content by stable id (the "same node, not a copy" read).
FETCH_BLOCK_CYPHER = """
MATCH (b:Block {id: $block_id})
RETURN b.id as id, b.content as content, b.type as type
"""

# Reify a transclusion reference as a first-class edge (idempotent; graph-viz reuse).
MERGE_TRANSCLUDES_CYPHER = """
MATCH (src:Block {id: $src_id})
MATCH (dst:Block {id: $dst_id})
MERGE (src)-[:TRANSCLUDES]->(dst)
"""

# Reverse lookup: the blocks (and their owning page) that transclude this block.
GET_TRANSCLUSIONS_CYPHER = """
MATCH (src:Block)-[:TRANSCLUDES]->(b:Block {id: $block_id})
OPTIONAL MATCH (p:Page)-[:HAS_BLOCK]->(src)
RETURN src.id as block_id, src.content as content, src.type as type,
       p.id as page_id, p.title as page_title
ORDER BY src.id
"""


# --- Pure helper ------------------------------------------------------------

def parse_transclusions(content: str) -> List[str]:
    """Extract ((block_id)) refs from a block's content. (Pure; safe to use anywhere.)"""
    return [m.strip() for m in TRANSCLUDE_RE.findall(content or "") if m.strip()]


# --- Read-path resolution ---------------------------------------------------

def _fetch_block(session, block_id: str, cache: Dict[str, Optional[Dict[str, Any]]]
                 ) -> Optional[Dict[str, Any]]:
    """Fetch (once, memoized) a block's live {id, content, type}; None if it is gone."""
    if block_id in cache:
        return cache[block_id]
    rec = session.run(FETCH_BLOCK_CYPHER, {"block_id": block_id}).single()
    node = dict(rec) if rec else None
    cache[block_id] = node
    return node


def _resolve_ref(session, ref_id: str, *, path: Tuple[str, ...], depth: int,
                 depth_limit: int, cache: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    """Resolve one ((ref_id)) to its live content, following nested refs within bounds.

    `path` is the chain of block ids currently being expanded — a ref already on it is a
    CYCLE (render a placeholder, don't recurse). Beyond `depth_limit` the ref is returned
    unexpanded (depth_exceeded)."""
    entry: Dict[str, Any] = {
        "ref": ref_id, "content": None, "type": None,
        "cycle": False, "missing": False, "depth_exceeded": False,
    }
    if ref_id in path:
        entry["cycle"] = True                    # self- or loop-transclusion
        return entry
    if depth > depth_limit:
        entry["depth_exceeded"] = True           # bounded pass — stop expanding
        return entry
    node = _fetch_block(session, ref_id, cache)
    if node is None:
        entry["missing"] = True                  # ref points at a deleted/unknown block
        return entry
    entry["content"] = node["content"]
    entry["type"] = node["type"]
    nested_refs = parse_transclusions(node["content"] or "")
    if nested_refs:
        nested: List[Dict[str, Any]] = []
        for nref in nested_refs:
            if ref_id != nref:                   # a self-edge is degenerate — skip the MERGE
                session.run(MERGE_TRANSCLUDES_CYPHER, {"src_id": ref_id, "dst_id": nref})
            nested.append(_resolve_ref(session, nref, path=path + (ref_id,),
                                       depth=depth + 1, depth_limit=depth_limit, cache=cache))
        entry["nested"] = nested
    return entry


def resolve_page_blocks(session, *, blocks: List[Dict[str, Any]],
                        depth_limit: int = DEFAULT_DEPTH_LIMIT) -> List[Dict[str, Any]]:
    """READ hook: for each page block that references ((ids)), reconcile its :TRANSCLUDES
    edges and attach a `transclusions` list of resolved live content.

    Mutates each referencing block in place (adds `transclusions`) and returns `blocks`.
    Blocks with NO refs are left byte-for-byte untouched (no query, no new key) so the
    plain-page read path is unchanged. Runs on the OPEN session from crud.get_page."""
    cache: Dict[str, Optional[Dict[str, Any]]] = {}
    for block in blocks:
        refs = parse_transclusions(block.get("content", ""))
        if not refs:
            continue
        src_id = block.get("id")
        path: Tuple[str, ...] = (src_id,) if src_id else ()
        resolved: List[Dict[str, Any]] = []
        for ref in refs:
            if src_id and ref and src_id != ref:  # reify the edge (skip a self-edge)
                session.run(MERGE_TRANSCLUDES_CYPHER, {"src_id": src_id, "dst_id": ref})
            resolved.append(_resolve_ref(session, ref, path=path, depth=1,
                                         depth_limit=depth_limit, cache=cache))
        block["transclusions"] = resolved
    return blocks


def get_transclusions(driver, *, block_id: str) -> List[Dict[str, Any]]:
    """Reverse edges: the blocks (with owning page) that transclude `block_id` — its
    dependents, so editing a source can show what it feeds."""
    with driver.session() as session:
        res = session.run(GET_TRANSCLUSIONS_CYPHER, {"block_id": block_id})
        return [dict(r) for r in res]
