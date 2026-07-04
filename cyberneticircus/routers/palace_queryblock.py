"""
Router: palace_queryblock — run a Mind Palace query-block's read-only Cypher inline (#4 / A2).
  - run  →  POST /api/mindpalace/queryblock/run

Auto-registers by name (web_server.py's palace_* import loop) — no web_server edit needed.
Error mapping mirrors routers/query.py: a gate refusal (read-only / :Wiki firewall) is 403,
malformed Cypher is 400, anything else is 500.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from neo4j.exceptions import Neo4jError

from db_logic import get_driver
from lib.palace import queryblock as lib_queryblock


router = APIRouter()


class QueryBlockRun(BaseModel):
    cypher: str


@router.post("/mindpalace/queryblock/run")
def run_query_block_endpoint(payload: QueryBlockRun):
    """Execute a query-block's STRICTLY READ-ONLY Cypher and return rows for inline rendering."""
    try:
        return {"rows": lib_queryblock.run_query_block(get_driver(), cypher=payload.cypher)}
    except PermissionError as e:
        # Read-only guard / :Wiki firewall refusal — the message says which. 403, never 500.
        raise HTTPException(status_code=403, detail=str(e))
    except Neo4jError as e:
        # Malformed / DB-rejected Cypher — client error, surface the reason.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
