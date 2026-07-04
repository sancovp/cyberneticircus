"""
Router: palace_search — full-text search across Mind Palace Pages + Blocks.
  - search  →  GET /api/mindpalace/search
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException

from db_logic import get_driver
from lib.palace import search as lib_search


router = APIRouter()


@router.get("/mindpalace/search")
def search_endpoint(q: str, mp_id: Optional[str] = None, limit: int = 25):
    """Full-text hits across :Page/:Block (title + content), optionally scoped to a MindPalace."""
    try:
        return {"results": lib_search.search_palace(get_driver(), query=q, mp_id=mp_id, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
