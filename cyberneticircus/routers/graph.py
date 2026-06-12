"""
Router: graph — the D3 visualizer data endpoints.
  - get_graph            →  GET /api/graph
  - get_node_subgraph    →  GET /api/node/subgraph
"""
from typing import Optional
from fastapi import APIRouter, HTTPException

from db_logic import get_driver
from lib import visualizer as lib_visualizer
from lib import logs as lib_logs


router = APIRouter()


@router.get("/graph")
def get_graph_endpoint(name: Optional[str] = None):
    """Build the d3 graph JSON. If `name` is given, focus on that Cybernet's subgraph."""
    drv = get_driver()
    try:
        return lib_visualizer.get_graph(
            drv, name=name,
            active_focus_nodes=lib_logs.active_focus_nodes,
            active_focus_labels=lib_logs.active_focus_labels,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node/subgraph")
def get_node_subgraph_endpoint(node_id: str):
    """2-hop subgraph around a specific node (visualizer inspector)."""
    drv = get_driver()
    try:
        return lib_visualizer.get_node_subgraph(drv, node_id=node_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
