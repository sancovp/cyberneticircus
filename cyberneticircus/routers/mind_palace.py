"""
Router: mind_palace — 9 endpoints for the Notion-like wiki CRUD + JSON import/export.
  - list / create / list_pages / create_page / get_page / save_blocks / delete_page
  - export / import
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db_logic import get_driver
from lib import mind_palace as lib_mind_palace
from lib import logs as lib_logs


router = APIRouter()


# --- Pydantic request models -------------------------------------------------

class MindPalaceCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class PageCreate(BaseModel):
    title: str


class BlockItem(BaseModel):
    type: str  # 'header', 'text', 'list', 'code'
    content: str
    level: Optional[int] = 1
    language: Optional[str] = "text"


class BlocksPayload(BaseModel):
    title: Optional[str] = None
    blocks: List[BlockItem]


class ImportPayload(BaseModel):
    export_data: Dict[str, Any]


# --- Endpoints ---------------------------------------------------------------

@router.get("/mindpalaces")
def list_mind_palaces_endpoint():
    """List all MindPalace hubs (for the wiki sidebar)."""
    try:
        return {"mindpalaces": lib_mind_palace.list_mindpalaces(get_driver())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mindpalace")
def create_mind_palace_endpoint(payload: MindPalaceCreate):
    """MERGE a new MindPalace (idempotent on name)."""
    try:
        return lib_mind_palace.create_mind_palace(get_driver(), name=payload.name, description=payload.description or "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mindpalace/{mp_id}/pages")
def list_pages_endpoint(mp_id: str):
    """List all Pages under a MindPalace."""
    try:
        return {"pages": lib_mind_palace.list_pages(get_driver(), mp_id=mp_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mindpalace/{mp_id}/page")
def create_page_endpoint(mp_id: str, payload: PageCreate):
    """Create a new Page under a MindPalace."""
    try:
        return lib_mind_palace.create_page(get_driver(), mp_id=mp_id, title=payload.title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mindpalace/page/{page_id}")
def get_page_endpoint(page_id: str):
    """Get a Page + its ordered Blocks."""
    try:
        result = lib_mind_palace.get_page(get_driver(), page_id=page_id)
        if not result:
            raise HTTPException(status_code=404, detail="Page not found.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mindpalace/page/{page_id}/blocks")
def save_blocks_endpoint(page_id: str, payload: BlocksPayload):
    """Replace the Blocks of a Page atomically (DETACH DELETE old, CREATE new)."""
    try:
        return lib_mind_palace.save_blocks(
            get_driver(), page_id=page_id,
            title=payload.title,
            blocks=[b.model_dump() for b in payload.blocks],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mindpalace/page/{page_id}")
def delete_page_endpoint(page_id: str):
    """DETACH DELETE a Page and its Blocks."""
    try:
        return lib_mind_palace.delete_page(get_driver(), page_id=page_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mindpalace/{mp_id}/export")
def export_endpoint(mp_id: str):
    """Export a MindPalace subgraph (3 hops) as a JSON-serializable dict."""
    try:
        return lib_mind_palace.export_palace(get_driver(), mp_id=mp_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mindpalace/import")
def import_endpoint(payload: ImportPayload):
    """Idempotently import a MindPalace JSON bundle (MERGE on id/name)."""
    try:
        return lib_mind_palace.import_palace(get_driver(), export_data=payload.export_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
