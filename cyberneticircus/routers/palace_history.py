"""
Router: palace_history — the per-block :Revision read path.
  - get_block_revisions  →  GET /api/mindpalace/block/{block_id}/revisions

The write side (snapshotting a block's prior content on change) happens inside
save_blocks (palace/blocks.py → palace/history.py); this router only exposes the trail.
Mounted by one append-only include_router line in web_server.py.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException

from db_logic import get_driver
from lib import mind_palace as lib_mind_palace


router = APIRouter()


@router.get("/mindpalace/block/{block_id}/revisions")
def get_block_revisions_endpoint(block_id: str):
    """Return a block's revision trail (oldest first) as {ts, content} entries."""
    try:
        return {"revisions": lib_mind_palace.get_block_revisions(get_driver(), block_id=block_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
