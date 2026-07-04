"""
Router: palace_links — [[wiki-links]] backlinks panel for Mind Palace Pages.
  - backlinks  →  GET /api/mindpalace/page/{page_id}/backlinks

The LINKS_TO edges themselves are synced on save (lib.palace.links.sync_page_links,
hooked into save_blocks); this router only READS the inbound/outbound set.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException

from db_logic import get_driver
from lib.palace import links as lib_links


router = APIRouter()


@router.get("/mindpalace/page/{page_id}/backlinks")
def backlinks_endpoint(page_id: str):
    """Pages that link TO this page, plus the pages it links out to → {backlinks, outgoing}."""
    try:
        return lib_links.get_backlinks(get_driver(), page_id=page_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
