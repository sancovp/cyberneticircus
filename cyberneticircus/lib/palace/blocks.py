"""
Mind Palace blocks — the :Block write path under a :Page.

Composition:
  - save_blocks  →  POST /api/mindpalace/page/{page_id}/blocks

Model: **diff-and-patch keyed by stable block id** (P0, see MINDPALACE-IMPROVEMENTS.md).
Incoming blocks carry an `id` (the frontend round-trips it — app.js:2189/2198/2205);
a block with no id is NEW and gets a stable `block_{uuid4}` minted here (returned so the
frontend can adopt it). On save:
  - MERGE each incoming block by id  → SET its props   (match → update, unmatched → create)
  - MERGE the (:Page)-[:HAS_BLOCK]->(:Block) edge
  - DETACH DELETE only the page's blocks NOT in the incoming id set

Block IDs are therefore STABLE across saves — the hard precondition for every
block-addressable feature (transclusion, block-level backlinks, revisions). Before a
changed block's content is overwritten, its prior content is snapshotted into a
:Revision trail (palace/history.py). Block types today: header / text / kv / list / code
(DESIGN §5). Graph is Sacred — the node/edge model is identical to the old full-replace
path (:Block with the same props, HAS_BLOCK edge); only the write became a diff.
"""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

from .crud import _coerce_int
from . import history


# --- Cypher-string constructors ---------------------------------------------

SET_PAGE_TITLE_CYPHER = (
    "MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id "
    "SET p.title = $title"
)

# Upsert the incoming block set: MERGE by stable id (match → SET, unmatched → CREATE),
# wire the HAS_BLOCK edge. $blocks is the prepared list (each with an id).
UPSERT_BLOCKS_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
UNWIND $blocks AS b
  MERGE (blk:Block {id: b.id})
    ON CREATE SET blk.domain = 'cyberneticity', blk.subdomain = 'block'
  SET blk.type = b.type, blk.content = b.content, blk.position = b.position,
      blk.level = b.level, blk.language = b.language
  MERGE (p)-[:HAS_BLOCK]->(blk)
"""

# Delete ONLY the page's blocks that are no longer in the incoming id set.
DELETE_MISSING_BLOCKS_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
MATCH (p)-[:HAS_BLOCK]->(old:Block) WHERE NOT old.id IN $keep
DETACH DELETE old
"""


# --- Composition ------------------------------------------------------------

def save_blocks(driver, *, page_id: str, title: Optional[str],
                blocks: List[Dict[str, Any]], ts: Optional[str] = None) -> Dict[str, Any]:
    """Diff-and-patch a Page's Blocks by stable id (preserve unchanged ids; delete only removed).

    Returns the ordered {id, position} of every persisted block so the caller can
    adopt the ids minted for new blocks. `ts` timestamps the revision snapshot of any
    block whose content changed (deterministic — never a wall-clock read here)."""
    page_id_int = _coerce_int(page_id)
    prepared: List[Dict[str, Any]] = []
    for idx, block in enumerate(blocks):
        block_id = block.get("id") or f"block_{uuid.uuid4().hex}"
        prepared.append({
            "id": block_id,
            "type": block["type"],
            "content": block["content"],
            "position": idx,
            "level": block.get("level", 1),
            "language": block.get("language", "text"),
        })
    keep = [b["id"] for b in prepared]
    with driver.session() as session:
        if title:
            session.run(SET_PAGE_TITLE_CYPHER,
                        {"page_id": page_id, "page_id_int": page_id_int, "title": title})
        # Snapshot prior content of changed blocks BEFORE the upsert overwrites it.
        history.snapshot_changed_blocks(session, blocks=prepared, ts=ts)
        session.run(UPSERT_BLOCKS_CYPHER,
                    {"page_id": page_id, "page_id_int": page_id_int, "blocks": prepared})
        session.run(DELETE_MISSING_BLOCKS_CYPHER,
                    {"page_id": page_id, "page_id_int": page_id_int, "keep": keep})
    return {
        "status": "success",
        "message": "Blocks saved successfully.",
        "blocks": [{"id": b["id"], "position": b["position"]} for b in prepared],
    }
