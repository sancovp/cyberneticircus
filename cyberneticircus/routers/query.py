"""
Router: cypher shell — the only required HTTP endpoint.
A thin transport over the play-facade: call cyberneticircus(), map domain
errors onto HTTP status codes. All play logic lives in facade.py.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from neo4j.exceptions import Neo4jError

from facade import cyberneticircus


router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    cybernet_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    current_filesystem_location: Optional[str] = None


@router.post("/query")
def query_endpoint(req: QueryRequest):
    """Delegate to the play-facade; map its domain errors to HTTP."""
    try:
        return cyberneticircus(req.query, req.cybernet_name, req.parameters,
                               req.current_filesystem_location)
    except PermissionError as e:
        # Gate refusal or :Wiki/domain security policy. The message carries the
        # required regex so a playing agent knows what cypher to emit. 403, never 500.
        raise HTTPException(status_code=403, detail=str(e))
    except Neo4jError as e:
        # Malformed cypher / DB-rejected query — client error, surface the reason.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Anything unexpected: surface the message instead of a bare 500 body.
        raise HTTPException(status_code=500, detail=str(e))
