"""
palace/ — the Mind Palace domain (the Notion-like :MindPalace/:Page/:Block subgraph),
split into per-seam modules so features drop into their own file with no collision:

  crud.py    — :MindPalace + :Page lifecycle (list/create hubs + pages, get/delete page)
  blocks.py  — :Block write path (save_blocks diff-and-patch by stable id) + block Cypher
  history.py — per-block :Revision trail (snapshot on change + read)
  graph.py   — JSON plugin export/import + graph-view projection
  links.py   — [[wiki-links]] + backlinks               (FLEET STUB)
  search.py  — full-text search across pages + blocks   (FLEET STUB)
  templates.py — :PageTemplate block-sets (create/list/instantiate onto a new Page)

This package IS the implementation. `lib/mind_palace.py` is a thin facade that
re-exports this public surface, so `from lib import mind_palace` keeps working
unchanged (routers/mind_palace.py + lib/__init__.py untouched). Graph is sacred —
the node/edge model is identical to before; only the code was reorganized.
"""
from __future__ import annotations

from . import crud, blocks, history, graph, links, search, templates

from .crud import (
    list_mindpalaces,
    create_mindpalace,
    list_pages,
    create_page,
    get_page,
    delete_page,
    LIST_MINDPALACES_CYPHER,
    CREATE_MINDPALACE_CYPHER,
    LIST_PAGES_CYPHER,
    CREATE_PAGE_CYPHER,
    GET_PAGE_CYPHER,
    DELETE_PAGE_CYPHER,
    LINK_PAGE_TO_TEMPLATE_CYPHER,
)
from .blocks import (
    save_blocks,
    SET_PAGE_TITLE_CYPHER,
    UPSERT_BLOCKS_CYPHER,
    DELETE_MISSING_BLOCKS_CYPHER,
)
from .history import (
    snapshot_changed_blocks,
    get_block_revisions,
    SNAPSHOT_CHANGED_BLOCKS_CYPHER,
    GET_BLOCK_REVISIONS_CYPHER,
)
from .graph import (
    export_palace,
    import_palace,
    EXPORT_PATHS_CYPHER,
)
from .templates import (
    create_template,
    list_templates,
    instantiate_template,
    LIST_TEMPLATES_CYPHER,
    CREATE_TEMPLATE_CYPHER,
    CREATE_TEMPLATE_BLOCK_CYPHER,
    GET_TEMPLATE_CYPHER,
)

__all__ = [
    # submodules
    "crud", "blocks", "history", "graph", "links", "search", "templates",
    # crud surface
    "list_mindpalaces", "create_mindpalace", "list_pages", "create_page",
    "get_page", "delete_page",
    # blocks surface
    "save_blocks",
    # history surface
    "snapshot_changed_blocks", "get_block_revisions",
    # graph surface
    "export_palace", "import_palace",
    # templates surface
    "create_template", "list_templates", "instantiate_template",
    # Cypher constants (preserved public surface)
    "LIST_MINDPALACES_CYPHER", "CREATE_MINDPALACE_CYPHER", "LIST_PAGES_CYPHER",
    "CREATE_PAGE_CYPHER", "GET_PAGE_CYPHER", "DELETE_PAGE_CYPHER", "LINK_PAGE_TO_TEMPLATE_CYPHER",
    "SET_PAGE_TITLE_CYPHER", "UPSERT_BLOCKS_CYPHER", "DELETE_MISSING_BLOCKS_CYPHER",
    "SNAPSHOT_CHANGED_BLOCKS_CYPHER", "GET_BLOCK_REVISIONS_CYPHER",
    "EXPORT_PATHS_CYPHER",
    "LIST_TEMPLATES_CYPHER", "CREATE_TEMPLATE_CYPHER",
    "CREATE_TEMPLATE_BLOCK_CYPHER", "GET_TEMPLATE_CYPHER",
]
