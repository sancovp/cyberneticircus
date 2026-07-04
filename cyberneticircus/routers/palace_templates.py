"""
Router: palace_templates — PageTemplate CRUD + one-click page instantiation.
  - GET  /api/mindpalace/templates                        list_templates
  - POST /api/mindpalace/template                          create_template
  - POST /api/mindpalace/{palace_id}/page/from-template    instantiate_template

Own Pydantic models here (not mind_palace.BlockItem) — that struct is mid-flight
across #1/#4/#6; a template block only ever needs type/content/level/language, so
decoupling avoids the shared-file churn.
"""
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db_logic import get_driver
from lib import mind_palace as lib_mind_palace


router = APIRouter()


# --- Pydantic request models -------------------------------------------------

class TemplateBlockItem(BaseModel):
    type: str  # 'header', 'text', 'list', 'code', 'kv'
    content: str
    level: Optional[int] = 1
    language: Optional[str] = "text"


class TemplateCreate(BaseModel):
    name: str
    blocks: List[TemplateBlockItem]


class InstantiatePayload(BaseModel):
    template_id: str
    title: str


# --- Endpoints ---------------------------------------------------------------

@router.get("/mindpalace/templates")
def list_templates_endpoint():
    """List all PageTemplates (for the `/` slash-insert menu)."""
    try:
        return {"templates": lib_mind_palace.list_templates(get_driver())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mindpalace/template")
def create_template_endpoint(payload: TemplateCreate):
    """Create a new PageTemplate with an ordered block-set."""
    try:
        return lib_mind_palace.create_template(
            get_driver(), name=payload.name,
            blocks=[b.model_dump() for b in payload.blocks],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mindpalace/{palace_id}/page/from-template")
def instantiate_template_endpoint(palace_id: str, payload: InstantiatePayload):
    """Instantiate a PageTemplate as a new Page under `palace_id`."""
    try:
        result = lib_mind_palace.instantiate_template(
            get_driver(), template_id=payload.template_id,
            palace_id=palace_id, title=payload.title,
        )
        if not result:
            raise HTTPException(status_code=404, detail="Template not found.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
