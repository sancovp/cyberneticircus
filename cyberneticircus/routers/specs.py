"""
Router: specs — 5 endpoints for the spec composer (markdown/json files under <project>/specs/).
  - list / read / save
  - list templates / read template
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lib import specs as lib_specs
from lib import logs as lib_logs


router = APIRouter()


class SaveSpecRequest(BaseModel):
    filename: str
    content: str


@router.get("/specs/list")
def list_specs_endpoint():
    """List all .md/.json files under <project>/specs/."""
    try:
        return lib_specs.list_specs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specs/read")
def read_spec_endpoint(filename: str):
    """Read a single spec file (path-traversal-protected)."""
    try:
        return lib_specs.read_spec(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Specification file not found.")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/specs/save")
def save_spec_endpoint(req: SaveSpecRequest):
    """Write a spec file (filename must end in .md or .json, no path components)."""
    try:
        return lib_specs.save_spec(req.filename, req.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specs/templates")
def list_templates_endpoint():
    """List all .md/.json files under <project>/templates/."""
    try:
        return lib_specs.list_templates()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specs/template/read")
def read_template_endpoint(filename: str):
    """Read a single template file (path-traversal-protected)."""
    try:
        return lib_specs.read_template(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template file not found.")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
