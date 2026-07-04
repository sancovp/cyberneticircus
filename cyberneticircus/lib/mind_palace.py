"""
Mind Palace CRUD + JSON import/export — the wiki/Notion-like subgraph in the graph.

THIN FACADE (architecture rule §9.1 "thin facade + lib/ deps"): the implementation
was MOVED — not removed — into the `lib/palace/` package. This module preserves the
exact public surface so `from lib import mind_palace` keeps working unchanged
(routers/mind_palace.py + lib/__init__.py are untouched), while each seam now lives
in its own file so fleet features drop in without collision:

  palace/crud.py    — list_mindpalaces / create_mindpalace / list_pages /
                      create_page / get_page / delete_page
  palace/blocks.py  — save_blocks (the :Block write path)
  palace/graph.py   — export_palace / import_palace
  palace/links.py   — [[wiki-links]] + backlinks             (FLEET STUB)
  palace/search.py  — full-text search across pages + blocks (FLEET STUB)
  palace/templates.py — :PageTemplate block-sets (create/list/instantiate)
  palace/transclude.py — ((block_id)) refs + :TRANSCLUDES edges (FLEET STUB)

Route → composition map (unchanged):
  - list_mindpalaces  →  GET  /api/mindpalaces
  - create_mindpalace →  POST /api/mindpalace
  - list_pages        →  GET  /api/mindpalace/{mp_id}/pages
  - create_page       →  POST /api/mindpalace/{mp_id}/page
  - get_page          →  GET  /api/mindpalace/page/{page_id}
  - save_blocks       →  POST /api/mindpalace/page/{page_id}/blocks
  - delete_page       →  DELETE /api/mindpalace/page/{page_id}
  - export_palace     →  POST /api/mindpalace/{mp_id}/export
  - import_palace     →  POST /api/mindpalace/import
"""
from __future__ import annotations

# Re-export the whole palace public surface (functions + Cypher constants).
from .palace import *  # noqa: F401,F403
from .palace import (  # noqa: F401  (explicit re-exports for tooling/discoverability)
    crud, blocks, history, graph, links, search, templates, transclude,
    list_mindpalaces, create_mindpalace, list_pages, create_page, get_page,
    delete_page, save_blocks, snapshot_changed_blocks, get_block_revisions,
    export_palace, import_palace,
    create_template, list_templates, instantiate_template,
    LIST_MINDPALACES_CYPHER, CREATE_MINDPALACE_CYPHER, LIST_PAGES_CYPHER,
    CREATE_PAGE_CYPHER, GET_PAGE_CYPHER, DELETE_PAGE_CYPHER, LINK_PAGE_TO_TEMPLATE_CYPHER,
    SET_PAGE_TITLE_CYPHER, UPSERT_BLOCKS_CYPHER, DELETE_MISSING_BLOCKS_CYPHER,
    SNAPSHOT_CHANGED_BLOCKS_CYPHER, GET_BLOCK_REVISIONS_CYPHER,
    EXPORT_PATHS_CYPHER,
    LIST_TEMPLATES_CYPHER, CREATE_TEMPLATE_CYPHER,
    CREATE_TEMPLATE_BLOCK_CYPHER, GET_TEMPLATE_CYPHER,
)
from .palace import __all__ as __all__  # noqa: F401
