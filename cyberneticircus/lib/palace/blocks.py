"""
Mind Palace blocks — the :Block write path under a :Page.

Composition:
  - save_blocks  →  POST /api/mindpalace/page/{page_id}/blocks

Current model: full-replace (DETACH DELETE the page's old blocks, CREATE the new
ordered set). Block types today: header / text / kv / list / code (DESIGN §5).

This module owns the block WRITE seam. Block-level edit / versioning / history
(replacing full-replace with per-block upsert + a :BlockVersion trail) is a fleet
feature that lands here — see MINDPALACE-IMPROVEMENTS.md.
"""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

from .crud import _coerce_int


# --- Cypher-string constructors ---------------------------------------------

SET_PAGE_TITLE_CYPHER = (
    "MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id "
    "SET p.title = $title"
)

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


# --- Composition ------------------------------------------------------------

def save_blocks(driver, *, page_id: str, title: Optional[str], blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Replace the Blocks of a Page atomically (DETACH DELETE old, CREATE new)."""
    page_id_int = _coerce_int(page_id)
    with driver.session() as session:
        if title:
            session.run(SET_PAGE_TITLE_CYPHER,
                        {"page_id": page_id, "page_id_int": page_id_int, "title": title})
        session.run(DELETE_PAGE_BLOCKS_CYPHER, {"page_id": page_id, "page_id_int": page_id_int})
        for idx, block in enumerate(blocks):
            block_id = f"block_{uuid.uuid4().hex}"
            session.run(CREATE_BLOCK_CYPHER, {
                "page_id": page_id, "page_id_int": page_id_int, "block_id": block_id,
                "type": block["type"], "content": block["content"], "position": idx,
                "level": block.get("level", 1), "language": block.get("language", "text"),
            })
        return {"status": "success", "message": "Blocks saved successfully."}
