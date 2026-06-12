"""
Per-domain FastAPI APIRouter files for the cyberneticircus HTTP API.

Each router is a thin facade: 1-line delegations to lib/<domain>.py compositions.
This directory follows the 3-Levels-Deep Rule:
    cyberneticircus/         (level 1 — package root)
      routers/               (level 2 — domain)
        <module>.py          (level 3 — the router file)
"""
from . import (
    query,
    commands,
    cybernet,
    traversal,
    graph,
    logs,
    mind_palace,
    specs,
    system,
)

__all__ = [
    "query",
    "commands",
    "cybernet",
    "traversal",
    "graph",
    "logs",
    "mind_palace",
    "specs",
    "system",
]
