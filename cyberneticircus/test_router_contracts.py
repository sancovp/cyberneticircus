#!/usr/bin/env python3
"""
Contract tests for cybernet_name threading through the HTTP routers.

Regression guard for the refactor drift (DESIGN.md §11.8 context) where
QueryRequest dropped cybernet_name and req.parameters landed in
db_logic.query_database's cybernet_name slot, darkening the LLM-loop gate
from outside. Also guards the traversal progress + adjust_weight chains.

No live neo4j required: the db_logic call boundary is stubbed, and the
assertions are on WHAT the routers pass downstream (the argument slots),
not on graph state. Run directly: python3 test_router_contracts.py
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
for p in (_here, os.path.dirname(_here)):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI
from fastapi.testclient import TestClient

import db_logic
from routers import query as query_mod
from routers import traversal as traversal_mod
from lib import traversal as lib_traversal


calls = {}


def _stub_boundaries():
    """Replace every db_logic touchpoint the routers reach, recording arg slots."""
    def fake_query_database(query, cybernet_name, parameters=None):
        calls["query_database"] = (query, cybernet_name, parameters)
        return [{"ok": True}]

    def fake_progress_traversal(cybernet_name, answer=None):
        calls["progress_traversal"] = (cybernet_name, answer)
        return f"Progressed (cybernet '{cybernet_name}')."

    def fake_get_active_traversal_step(cybernet_name):
        calls.setdefault("get_active_traversal_step", []).append(cybernet_name)
        return {"id": "step_x", "text": "stub", "transitions": []}

    def fake_adjust_transition_weight_internal(from_step_id, to_step_id, success, cybernet_name):
        calls["adjust_transition_weight_internal"] = (from_step_id, to_step_id, success, cybernet_name)
        return f"adjusted by '{cybernet_name}'"

    # routers/query.py rebinds these names at import — patch the rebound names.
    query_mod.query_database = fake_query_database
    query_mod.validate_cypher_query = lambda q: None
    query_mod.recognizer.recognize = lambda q: None
    # routers/traversal.py rebinds get_driver; lib/traversal.py resolves db_logic
    # lazily inside each function body — patch the db_logic module attributes.
    traversal_mod.get_driver = lambda: object()
    db_logic.progress_traversal = fake_progress_traversal
    db_logic.get_active_traversal_step = fake_get_active_traversal_step
    db_logic.adjust_transition_weight_internal = fake_adjust_transition_weight_internal


def _build_client():
    app = FastAPI()
    app.include_router(query_mod.router, prefix="/api")
    app.include_router(traversal_mod.router, prefix="/api")
    return TestClient(app)


def run_tests():
    print("Starting router cybernet_name contract tests...")
    print("=" * 60)
    _stub_boundaries()
    client = _build_client()
    failures = 0

    def check(label, cond, detail=""):
        nonlocal failures
        if cond:
            print(f"   [PASS] {label}")
        else:
            failures += 1
            print(f"   [FAIL] {label} {detail}")

    # 1. /api/query threads all three slots correctly
    print("1. POST /api/query with cybernet_name + parameters...")
    calls.clear()
    res = client.post("/api/query", json={
        "query": "MATCH (n:Cybernet) RETURN n",
        "cybernet_name": "JesterCoreOne",
        "parameters": {"x": 1},
    })
    check("status 200", res.status_code == 200, f"(got {res.status_code}: {res.text})")
    check("query slot", calls.get("query_database", (None,))[0] == "MATCH (n:Cybernet) RETURN n",
          f"(got {calls.get('query_database')})")
    check("cybernet_name slot is the cybernet (NOT parameters)",
          calls.get("query_database", (None, None))[1] == "JesterCoreOne",
          f"(got {calls.get('query_database')})")
    check("parameters slot", calls.get("query_database", (None, None, None))[2] == {"x": 1},
          f"(got {calls.get('query_database')})")

    # 2. /api/query without cybernet_name degrades gracefully (gate inactive, no 422/500)
    print("2. POST /api/query without cybernet_name (anonymous caller)...")
    calls.clear()
    res = client.post("/api/query", json={"query": "RETURN 1"})
    check("status 200", res.status_code == 200, f"(got {res.status_code}: {res.text})")
    check("cybernet_name slot is None", calls.get("query_database", ("x", "x"))[1] is None,
          f"(got {calls.get('query_database')})")

    # 3. /api/traversal/progress threads cybernet_name + answer
    print("3. POST /api/traversal/progress with cybernet_name...")
    calls.clear()
    res = client.post("/api/traversal/progress",
                      json={"cybernet_name": "JesterCoreOne", "answer": "ANSWER_42"})
    check("status 200", res.status_code == 200, f"(got {res.status_code}: {res.text})")
    check("progress slots (cybernet_name, answer)",
          calls.get("progress_traversal") == ("JesterCoreOne", "ANSWER_42"),
          f"(got {calls.get('progress_traversal')})")
    check("active-step lookups scoped to the cybernet",
          calls.get("get_active_traversal_step") == ["JesterCoreOne", "JesterCoreOne"],
          f"(got {calls.get('get_active_traversal_step')})")

    # 4. /api/traversal/progress requires cybernet_name (per-cybernet scope is not optional)
    print("4. POST /api/traversal/progress without cybernet_name...")
    res = client.post("/api/traversal/progress", json={"answer": "x"})
    check("status 422", res.status_code == 422, f"(got {res.status_code}: {res.text})")

    # 5. /api/traversal/adjust_weight threads cybernet_name into the 4th slot
    print("5. POST /api/traversal/adjust_weight with cybernet_name...")
    calls.clear()
    res = client.post("/api/traversal/adjust_weight", json={
        "from_step_id": "step_a", "to_step_id": "step_b",
        "success": True, "cybernet_name": "JesterCoreOne",
    })
    check("status 200", res.status_code == 200, f"(got {res.status_code}: {res.text})")
    check("adjust slots (from, to, success, cybernet_name)",
          calls.get("adjust_transition_weight_internal") == ("step_a", "step_b", True, "JesterCoreOne"),
          f"(got {calls.get('adjust_transition_weight_internal')})")
    res = client.post("/api/traversal/adjust_weight",
                      json={"from_step_id": "a", "to_step_id": "b", "success": True})
    check("missing cybernet_name → 422", res.status_code == 422, f"(got {res.status_code})")

    # 6. crud_surrogate calibrate validates cybernet_name before touching the driver
    print("6. POST /api/crud_surrogate calibrate without cybernet_name...")
    res = client.post("/api/crud_surrogate", json={
        "action": "calibrate",
        "parameters": {"run_id": "r1", "actual_diff": {"k": "v"}},
    })
    check("status 400 naming cybernet_name",
          res.status_code == 400 and "cybernet_name" in res.text,
          f"(got {res.status_code}: {res.text})")

    print("=" * 60)
    if failures:
        print(f"FAILED: {failures} check(s) failed.")
        return False
    print("All router contract checks passed.")
    return True


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)
