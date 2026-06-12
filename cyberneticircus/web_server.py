#!/usr/bin/env python3
"""
FastAPI shell for the cyberneticircus — per the APIRouter pattern.

This file is the THIN OUTER FACADE. It does NOT contain business logic.
It just: (1) creates the FastAPI app, (2) mounts static files, (3) includes
the 9 per-domain routers, (4) serves the index.html, (5) starts uvicorn.

The actual logic lives in cyberneticircus/routers/<domain>.py (1-line
delegations) and cyberneticircus/lib/<domain>.py (compositions + atomics).
"""
import os
import sys
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from db_logic import get_driver, populate_default_graphs
from routers import query, commands, cybernet, traversal, graph, logs, mind_palace, specs, system


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("cyberneticircus_web_server")

# Ensure local dir is on path (so `from routers import ...` works under reload)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


app = FastAPI(title="CybernetiCircus Compiler API")

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

# Include the 9 per-domain routers (each is 1-line delegations to lib/)
app.include_router(query.router,      prefix="/api",           tags=["query"])
app.include_router(commands.router,   prefix="/api",           tags=["commands"])
app.include_router(cybernet.router,   prefix="/api",           tags=["cybernet"])
app.include_router(traversal.router,  prefix="/api",           tags=["traversal"])
app.include_router(graph.router,      prefix="/api",           tags=["graph"])
app.include_router(logs.router,       prefix="/api",           tags=["logs"])
app.include_router(mind_palace.router, prefix="/api",          tags=["mind_palace"])
app.include_router(specs.router,      prefix="/api",           tags=["specs"])
app.include_router(system.router,     prefix="/api",           tags=["system"])


@app.get("/", response_class=HTMLResponse)
def get_index():
    """Serve the visualizer's index.html."""
    index_path = os.path.join(current_dir, "static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("index.html not found. Ensure static files are generated in /static/.", status_code=404)


if __name__ == "__main__":
    import uvicorn
    try:
        populate_default_graphs(get_driver())
    except Exception as e:
        logger.error(f"Failed to bootstrap defaults on web server startup: {e}")
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)
