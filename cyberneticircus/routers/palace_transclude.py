"""
Router: palace_transclude — the reverse block-transclusion lookup.
  - get_transclusions  →  GET /api/mindpalace/block/{block_id}/transclusions

The forward side (resolving a block's ((ids)) to live content + reconciling the
:TRANSCLUDES edges) happens inside crud.get_page on read (palace/transclude.py); this
router only exposes the reverse edges — WHO transcludes this block, so editing a source
can surface its dependents. Mounted by the append-only auto-register loop in web_server.py.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException

from db_logic import get_driver
from lib.palace import transclude as lib_transclude


router = APIRouter()


@router.get("/mindpalace/block/{block_id}/transclusions")
def get_transclusions_endpoint(block_id: str):
    """What transcludes this block (reverse :TRANSCLUDES edges) — its dependents."""
    try:
        return {"transclusions": lib_transclude.get_transclusions(get_driver(), block_id=block_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
