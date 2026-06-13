#!/usr/bin/env python3
"""
project_places.py — flash the gameworld place dirs into the graph as :Place nodes.

The dir↔graph bijection, made reproducible: each gameworld/places/<dir> declares
its graph binding in a place.json ({name, trigger_traversal}); this projector
scans them and MERGEs a :Place node keyed by filesystem_location. Reporting that
location to the MCP (Law 5) then locks the reporting cybernet into the place's flow.

Admin/setup operation — writes :Place nodes directly via the neo4j HTTP API
(not gameplay, so it does not go through the play-facade or the gate). Idempotent.

Usage:  python3 cyberneticircus/scripts/project_places.py
Env:    NEO4J_HTTP (default http://localhost:7474/db/neo4j/tx/commit)
        NEO4J_USER (default neo4j)
        NEO4J_PASSWORD (default password — localhost dev default)
"""
from __future__ import annotations
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

NEO4J_HTTP = os.getenv("NEO4J_HTTP", "http://localhost:7474/db/neo4j/tx/commit")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# repo root = two levels up from this file (cyberneticircus/scripts/ -> repo root)
REPO_ROOT = Path(__file__).resolve().parents[2]
PLACES_DIR = REPO_ROOT / "gameworld" / "places"


def _run_cypher(statement: str, params: dict) -> dict:
    body = json.dumps({"statements": [{"statement": statement, "parameters": params}]}).encode()
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASSWORD}".encode()).decode()
    req = urllib.request.Request(
        NEO4J_HTTP, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


MERGE_PLACE = """
MERGE (p:Place {filesystem_location: $location})
SET p.name = $name,
    p.domain = 'cyberneticity',
    p.subdomain = 'place',
    p.trigger_traversal = $trigger_traversal
RETURN p.name AS name, p.filesystem_location AS loc, p.trigger_traversal AS trigger
"""


def main() -> int:
    if not PLACES_DIR.is_dir():
        print(f"ERROR: places dir not found: {PLACES_DIR}", file=sys.stderr)
        return 2

    projected = 0
    for child in sorted(PLACES_DIR.iterdir()):
        if not child.is_dir():
            continue
        manifest = child / "place.json"
        if not manifest.is_file():
            print(f"  skip {child.name}/ (no place.json)")
            continue
        decl = json.loads(manifest.read_text())
        # filesystem_location is derived from the dir, relative to the repo root —
        # the exact string an agent reports as current_filesystem_location.
        location = str(child.relative_to(REPO_ROOT))
        params = {
            "location": location,
            "name": decl.get("name", child.name),
            "trigger_traversal": decl.get("trigger_traversal"),
        }
        res = _run_cypher(MERGE_PLACE, params)
        errors = res.get("errors") or []
        if errors:
            print(f"  FAIL {location}: {errors}", file=sys.stderr)
            return 1
        row = res["results"][0]["data"][0]["row"]
        trig = row[2] if row[2] is not None else "(no flow wired yet)"
        print(f"  projected :Place {row[1]} -> name='{row[0]}', trigger={trig}")
        projected += 1

    print(f"Done. {projected} :Place node(s) projected from {PLACES_DIR}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
