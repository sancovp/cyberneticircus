"""
Mind Palace block revision history — the per-block :Revision trail.

Graph shape (edges + nodes, never a scanned property):
  (:Block)-[:HAS_REVISION]->(:Revision {ts, content, domain, subdomain:'revision'})

A :Revision captures a block's content AS IT WAS just before an edit overwrote it, so
each save that changes a block appends one revision (unchanged blocks and brand-new
blocks append nothing). The trail is meaningful only because block ids are stable across
saves (palace/blocks.py, P0) — an edit history keyed on a shifting id would be noise.

Compositions:
  - snapshot_changed_blocks  → called inside save_blocks BEFORE the upsert (write path)
  - get_block_revisions      → GET /api/mindpalace/block/{block_id}/revisions (read path)

`ts` is passed in (never read from a wall-clock here) so the write path stays
deterministic and testable.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


# --- Cypher-string constructors ---------------------------------------------

# For each incoming block that already exists AND whose content is changing, append a
# :Revision holding the PRIOR content. New blocks (no match) and unchanged blocks (equal
# content) append nothing. $blocks is the prepared block list (each with id + content).
SNAPSHOT_CHANGED_BLOCKS_CYPHER = """
UNWIND $blocks AS b
MATCH (blk:Block {id: b.id})
WHERE blk.content <> b.content
CREATE (blk)-[:HAS_REVISION]->(:Revision {
    ts: $ts, content: blk.content,
    domain: 'cyberneticity', subdomain: 'revision'
})
"""

GET_BLOCK_REVISIONS_CYPHER = """
MATCH (blk:Block {id: $block_id})-[:HAS_REVISION]->(rev:Revision)
RETURN rev.ts as ts, rev.content as content
ORDER BY rev.ts
"""


# --- Compositions -----------------------------------------------------------

def snapshot_changed_blocks(session, *, blocks: List[Dict[str, Any]], ts: Optional[str]) -> None:
    """Append a :Revision (prior content) for every incoming block whose content changed.

    Takes an open session (it runs in the same write path as the upsert, so it must run
    on the same session BEFORE the content is overwritten). No-op on an empty block set."""
    if not blocks:
        return
    session.run(SNAPSHOT_CHANGED_BLOCKS_CYPHER, {"blocks": blocks, "ts": ts})


def get_block_revisions(driver, *, block_id: str) -> List[Dict[str, Any]]:
    """Return a block's revision trail (oldest first) as {ts, content} dicts."""
    with driver.session() as session:
        res = session.run(GET_BLOCK_REVISIONS_CYPHER, {"block_id": block_id})
        return [dict(r) for r in res]
