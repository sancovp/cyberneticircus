"""
Mind Palace templates — reusable :PageTemplate block-sets for one-click page seeding.

Compositions:
  - create_template      →  POST /api/mindpalace/template            (routers/palace_templates.py)
  - list_templates       →  GET  /api/mindpalace/templates           (routers/palace_templates.py)
  - instantiate_template  →  POST /api/mindpalace/{mp_id}/page/from-template (routers/palace_templates.py)

Graph shape:
  (:PageTemplate {id, name, domain, subdomain:'template'})-[:HAS_BLOCK]->(:Block ...)

Same HAS_BLOCK edge type as :Page->:Block (a template IS a block-holder, just not a
:Page). instantiate_template clones the template's blocks onto a brand-new Page by
handing them (bare — no `id`) to blocks.save_blocks, the canonical :Block write path;
since the page has no prior blocks, save_blocks mints fresh stable ids for every one
(P0's diff-and-patch, degenerate to "create all" on an empty page) — the same
node-by-node clone-with-fresh-ids spirit graph.import_palace uses for export/import,
reusing the writer instead of re-deriving it.
"""
from __future__ import annotations
import uuid
from typing import Any, Dict, List

from .crud import _coerce_int, create_page
from .blocks import save_blocks


# --- Cypher-string constructors ---------------------------------------------

LIST_TEMPLATES_CYPHER = """
MATCH (t:PageTemplate)
RETURN elementId(t) as id, t.id as template_id, t.name as name
ORDER BY t.name
"""

CREATE_TEMPLATE_CYPHER = """
CREATE (t:PageTemplate {id: $template_id, name: $name, domain: 'cyberneticity', subdomain: 'template'})
RETURN elementId(t) as id, t.id as template_id, t.name as name
"""

CREATE_TEMPLATE_BLOCK_CYPHER = """
MATCH (t:PageTemplate) WHERE elementId(t) = $template_id OR id(t) = $template_id_int OR t.id = $template_id
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
CREATE (t)-[:HAS_BLOCK]->(b)
"""

GET_TEMPLATE_CYPHER = """
MATCH (t:PageTemplate) WHERE elementId(t) = $template_id OR id(t) = $template_id_int OR t.id = $template_id
OPTIONAL MATCH (t)-[:HAS_BLOCK]->(b:Block)
RETURN elementId(t) as id, t.id as template_id, t.name as name, collect(properties(b)) as blocks
"""


# --- Compositions -------------------------------------------------------------

def list_templates(driver) -> List[Dict[str, Any]]:
    """List all PageTemplates (for the `/` slash-insert menu)."""
    with driver.session() as session:
        res = session.run(LIST_TEMPLATES_CYPHER)
        return [dict(r) for r in res]


def create_template(driver, *, name: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a new PageTemplate with an ordered block-set."""
    template_id = f"template_{uuid.uuid4().hex}"
    with driver.session() as session:
        rec = session.run(CREATE_TEMPLATE_CYPHER, {"template_id": template_id, "name": name}).single()
        template_id_int = _coerce_int(template_id)
        for idx, block in enumerate(blocks):
            block_id = f"block_{uuid.uuid4().hex}"
            session.run(CREATE_TEMPLATE_BLOCK_CYPHER, {
                "template_id": template_id, "template_id_int": template_id_int, "block_id": block_id,
                "type": block["type"], "content": block["content"], "position": idx,
                "level": block.get("level", 1), "language": block.get("language", "text"),
            })
        return dict(rec)


def instantiate_template(driver, *, template_id: str, palace_id: str, title: str) -> Dict[str, Any]:
    """Clone a PageTemplate's blocks onto a NEW Page under `palace_id`.

    Reuses crud.create_page for the Page, then blocks.save_blocks (bare blocks, no
    `id`) to write the clone — the canonical writer mints fresh stable ids itself.
    """
    template_id_int = _coerce_int(template_id)
    with driver.session() as session:
        rec = session.run(GET_TEMPLATE_CYPHER, {
            "template_id": template_id, "template_id_int": template_id_int,
        }).single()
        if not rec:
            return {}
        template_blocks = [b for b in rec["blocks"] if b]
        template_blocks.sort(key=lambda x: x.get("position", 0))

    page = create_page(driver, mp_id=palace_id, title=title, template_id=template_id)
    page_id = page.get("page_id")
    clone_blocks = [
        {"type": b["type"], "content": b["content"],
         "level": b.get("level", 1), "language": b.get("language", "text")}
        for b in template_blocks
    ]
    save_blocks(driver, page_id=page_id, title=None, blocks=clone_blocks)
    return {"template_id": template_id, "page_id": page_id, "title": title, "block_count": len(template_blocks)}
