"""
palace/ — the Mind Palace domain (the Notion-like :MindPalace/:Page/:Block subgraph),
split into per-seam modules so features drop into their own file with no collision:

  crud.py    — :MindPalace + :Page lifecycle (list/create hubs + pages, get/delete page)
  blocks.py  — :Block write path (save_blocks full-replace) + block Cypher
  graph.py   — JSON plugin export/import + graph-view projection
  links.py   — [[wiki-links]] + backlinks               (FLEET STUB)
  search.py  — full-text search across pages + blocks   (FLEET STUB)

This package IS the implementation. `lib/mind_palace.py` is a thin facade that
re-exports this public surface, so `from lib import mind_palace` keeps working
unchanged (routers/mind_palace.py + lib/__init__.py untouched). Graph is sacred —
the node/edge model is identical to before; only the code was reorganized.
"""
from __future__ import annotations

from . import crud, blocks, graph, links, search

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
)
from .blocks import (
    save_blocks,
    SET_PAGE_TITLE_CYPHER,
    DELETE_PAGE_BLOCKS_CYPHER,
    CREATE_BLOCK_CYPHER,
)
from .graph import (
    export_palace,
    import_palace,
    EXPORT_PATHS_CYPHER,
)

__all__ = [
    # submodules
    "crud", "blocks", "graph", "links", "search",
    # crud surface
    "list_mindpalaces", "create_mindpalace", "list_pages", "create_page",
    "get_page", "delete_page",
    # blocks surface
    "save_blocks",
    # graph surface
    "export_palace", "import_palace",
    # Cypher constants (preserved public surface)
    "LIST_MINDPALACES_CYPHER", "CREATE_MINDPALACE_CYPHER", "LIST_PAGES_CYPHER",
    "CREATE_PAGE_CYPHER", "GET_PAGE_CYPHER", "DELETE_PAGE_CYPHER",
    "SET_PAGE_TITLE_CYPHER", "DELETE_PAGE_BLOCKS_CYPHER", "CREATE_BLOCK_CYPHER",
    "EXPORT_PATHS_CYPHER",
]
