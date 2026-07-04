#!/usr/bin/env python3
"""
Baseline behavior tests for the Mind Palace (the Notion-like :MindPalace/:Page/:Block
subgraph). This is the GREEN BASELINE the palace/ refactor + all fleet features must
protect: it pins the current behavior of the 9 endpoints and the lib compositions.

Two layers, no live neo4j required:
  - LIB level : call lib.mind_palace.* with a FakeDriver that records the Cypher +
                params it is handed and returns canned records. Protects the exact
                Cypher constants, id-coercion, block sorting, save_blocks DETACH+
                recreate order, and export/import graph assembly through the refactor.
  - ROUTER level: FastAPI TestClient over the mind_palace router with the lib surface
                stubbed (mirrors test_router_contracts.py). Protects route->lib wiring
                and status codes (incl. the create-endpoint regression guard).

Run directly:  /opt/homebrew/bin/python3.11 test_mind_palace.py
(also importable/collectable by pytest: the test_* functions raise AssertionError.)
"""
from __future__ import annotations
import os
import sys
import uuid

_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.dirname(_here)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lib import mind_palace as mp  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
# Fake Neo4j driver / session / result / graph objects
# ─────────────────────────────────────────────────────────────────────────

class FakeNode(dict):
    """A dict of properties that also carries element_id + labels (like a neo4j Node)."""
    def __init__(self, element_id, labels, props):
        super().__init__(props)
        self.element_id = element_id
        self.labels = labels


class FakeRel:
    def __init__(self, start_node, end_node, rel_type):
        self.start_node = start_node
        self.end_node = end_node
        self.type = rel_type


class FakePath:
    def __init__(self, nodes, relationships):
        self.nodes = nodes
        self.relationships = relationships


class FakeResult:
    def __init__(self, records):
        self._records = list(records)

    def __iter__(self):
        return iter(self._records)

    def single(self):
        return self._records[0] if self._records else None

    def peek(self):
        return self._records[0] if self._records else None


class FakeSession:
    def __init__(self, driver):
        self._driver = driver

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def run(self, query, parameters=None, **kwargs):
        params = dict(parameters) if parameters else {}
        params.update(kwargs)
        self._driver.queries.append((query, params))
        return FakeResult(self._driver._match(query))


class FakeDriver:
    """Records every (query, params) and answers by first substring match in `responses`."""
    def __init__(self, responses=None):
        self.queries = []
        self.responses = responses or []  # list of (substring, records)

    def session(self):
        return FakeSession(self)

    def _match(self, query):
        for substring, records in self.responses:
            if substring in query:
                return records
        return []

    def when(self, substring, records):
        self.responses.append((substring, records))
        return self


# ─────────────────────────────────────────────────────────────────────────
# LIB level — hubs / pages CRUD
# ─────────────────────────────────────────────────────────────────────────

def test_list_mindpalaces_returns_dicts_and_uses_canonical_cypher():
    d = FakeDriver().when("MATCH (mp:MindPalace)",
                          [{"id": "e1", "name": "Alpha", "domain": "cyberneticity",
                            "subdomain": "mindpalace", "description": "d"}])
    out = mp.list_mindpalaces(d)
    assert out == [{"id": "e1", "name": "Alpha", "domain": "cyberneticity",
                    "subdomain": "mindpalace", "description": "d"}], out
    assert d.queries[0][0] == mp.LIST_MINDPALACES_CYPHER


def test_create_mindpalace_merges_and_generates_id():
    d = FakeDriver().when("MERGE (mp:MindPalace",
                          [{"elem_id": "e9", "id": "mp_x", "name": "Beta", "description": "d"}])
    out = mp.create_mindpalace(d, name="Beta", description="d")
    assert out["name"] == "Beta"
    q, params = d.queries[0]
    assert q == mp.CREATE_MINDPALACE_CYPHER
    assert params["name"] == "Beta" and params["description"] == "d"
    assert params["id"].startswith("mp_")  # server-generated id


def test_list_pages_int_coercion_numeric():
    d = FakeDriver().when("HAS_PAGE", [{"id": "p1", "page_id": "page_1", "title": "T"}])
    mp.list_pages(d, mp_id="123")
    assert d.queries[0][1] == {"mp_id": "123", "mp_id_int": 123}


def test_list_pages_int_coercion_nonnumeric_defaults_minus1():
    d = FakeDriver().when("HAS_PAGE", [])
    mp.list_pages(d, mp_id="4:abc:9")
    assert d.queries[0][1]["mp_id_int"] == -1


def test_create_page_generates_page_id():
    d = FakeDriver().when("CREATE (p:Page", [{"id": "p1", "page_id": "page_z", "title": "T"}])
    out = mp.create_page(d, mp_id="e5", title="T")
    assert out["title"] == "T"
    params = d.queries[0][1]
    assert params["page_id"].startswith("page_") and params["title"] == "T"
    assert params["mp_id"] == "e5" and params["mp_id_int"] == -1


def test_get_page_filters_none_and_sorts_blocks_by_position():
    rec = {"id": "p1", "page_id": "page_1", "title": "T",
           "domain": "cyberneticity", "subdomain": "page",
           "blocks": [{"position": 2, "content": "c2"}, None,
                      {"position": 0, "content": "c0"}, {"position": 1, "content": "c1"}]}
    d = FakeDriver().when("OPTIONAL MATCH (p)-[:HAS_BLOCK]", [rec])
    out = mp.get_page(d, page_id="p1")
    assert [b["content"] for b in out["blocks"]] == ["c0", "c1", "c2"]  # sorted, None dropped


def test_get_page_not_found_returns_empty():
    d = FakeDriver()  # no records
    assert mp.get_page(d, page_id="nope") == {}


# ─────────────────────────────────────────────────────────────────────────
# LIB level — blocks (the DETACH-DELETE + recreate write path)
# ─────────────────────────────────────────────────────────────────────────

def test_save_blocks_full_replace_sequence_with_title():
    d = FakeDriver()
    blocks = [{"type": "header", "content": "H"},
              {"type": "code", "content": "x=1", "level": 2, "language": "python"}]
    out = mp.save_blocks(d, page_id="p1", title="New Title", blocks=blocks)
    assert out["status"] == "success"
    qs = [q for (q, _) in d.queries]
    # order: SET p.title  ->  DETACH DELETE old blocks  ->  CREATE each block
    assert "SET p.title = $title" in qs[0]
    assert "DETACH DELETE b" in qs[1]
    assert qs[2] == mp.CREATE_BLOCK_CYPHER and qs[3] == mp.CREATE_BLOCK_CYPHER
    p2, p3 = d.queries[2][1], d.queries[3][1]
    assert p2["position"] == 0 and p2["type"] == "header"
    assert p2["level"] == 1 and p2["language"] == "text"          # defaults applied
    assert p3["position"] == 1 and p3["level"] == 2 and p3["language"] == "python"
    assert p2["block_id"].startswith("block_")


def test_save_blocks_without_title_skips_title_update():
    d = FakeDriver()
    mp.save_blocks(d, page_id="p1", title=None, blocks=[{"type": "text", "content": "t"}])
    qs = [q for (q, _) in d.queries]
    assert not any("SET p.title" in q for q in qs)
    assert "DETACH DELETE b" in qs[0]


def test_delete_page_runs_detach_delete():
    d = FakeDriver()
    out = mp.delete_page(d, page_id="p1")
    assert out["status"] == "success"
    assert "DETACH DELETE p, b" in d.queries[0][0]


# ─────────────────────────────────────────────────────────────────────────
# LIB level — export / import (graph assembly)
# ─────────────────────────────────────────────────────────────────────────

def test_export_palace_assembles_nodes_and_links():
    mp_node = FakeNode("n_mp", ["MindPalace"], {"name": "Alpha", "id": "mp_1"})
    page_node = FakeNode("n_pg", ["Page"], {"title": "Pg", "id": "page_1"})
    block_node = FakeNode("n_bl", ["Block"], {"content": "b", "id": "block_1"})
    r1 = FakeRel(mp_node, page_node, "HAS_PAGE")
    r2 = FakeRel(page_node, block_node, "HAS_BLOCK")
    path = FakePath([mp_node, page_node, block_node], [r1, r2])
    d = FakeDriver().when("OPTIONAL MATCH path = (mp)", [{"mp": mp_node, "paths": [path]}])
    out = mp.export_palace(d, mp_id="mp_1")
    ex = out["export_data"]
    assert {n["id"] for n in ex["nodes"]} == {"n_mp", "n_pg", "n_bl"}
    assert {(l["source"], l["target"], l["type"]) for l in ex["links"]} == {
        ("n_mp", "n_pg", "HAS_PAGE"), ("n_pg", "n_bl", "HAS_BLOCK")}
    names = {n["id"]: n["name"] for n in ex["nodes"]}
    assert names["n_mp"] == "Alpha" and names["n_pg"] == "Pg"  # name||title||id fallback


def test_export_palace_missing_returns_empty_bundle():
    d = FakeDriver()  # no record
    out = mp.export_palace(d, mp_id="ghost")
    assert out == {"mindpalace_id": "ghost", "export_data": {"nodes": [], "links": []}}


def test_import_palace_merges_nodes_and_links():
    d = FakeDriver().when("RETURN elementId(n) as new_id", [{"new_id": "NEW"}])
    bundle = {
        "nodes": [
            {"id": "old_a", "label": "MindPalace", "properties": {"id": "mp_1", "name": "Alpha"}},
            {"id": "old_b", "label": "Page", "properties": {"name": "Pg"}},  # merges on name
        ],
        "links": [{"source": "old_a", "target": "old_b", "type": "HAS_PAGE"}],
    }
    out = mp.import_palace(d, export_data=bundle)
    assert "2 nodes and 1 links" in out["message"]
    # domain/subdomain backfilled onto properties lacking them
    node_b_props = [p for (q, p) in d.queries if "Page" in q and "MERGE" in q][0]["props"]
    assert node_b_props["domain"] == "cyberneticity"
    # link creation MATCHes both merged ids
    link_qs = [q for (q, _) in d.queries if "MERGE (a)-[r:HAS_PAGE]->(b)" in q]
    assert len(link_qs) == 1


# ─────────────────────────────────────────────────────────────────────────
# ROUTER level — the 9 endpoints (lib surface stubbed; mirrors test_router_contracts)
# ─────────────────────────────────────────────────────────────────────────

def _router_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers import mind_palace as mp_router

    calls = {}

    class FakeLib:
        def list_mindpalaces(self, driver):
            calls["list_mindpalaces"] = True
            return [{"id": "e1", "name": "Alpha"}]

        def create_mindpalace(self, driver, *, name, description):
            calls["create_mindpalace"] = (name, description)
            return {"id": "mp_1", "name": name, "description": description}

        def list_pages(self, driver, *, mp_id):
            calls["list_pages"] = mp_id
            return [{"id": "p1", "title": "T"}]

        def create_page(self, driver, *, mp_id, title):
            calls["create_page"] = (mp_id, title)
            return {"id": "p1", "title": title}

        def get_page(self, driver, *, page_id):
            calls["get_page"] = page_id
            return {} if page_id == "missing" else {"id": page_id, "title": "T", "blocks": []}

        def save_blocks(self, driver, *, page_id, title, blocks):
            calls["save_blocks"] = (page_id, title, blocks)
            return {"status": "success"}

        def delete_page(self, driver, *, page_id):
            calls["delete_page"] = page_id
            return {"status": "success"}

        def export_palace(self, driver, *, mp_id):
            calls["export_palace"] = mp_id
            return {"mindpalace_id": mp_id, "export_data": {"nodes": [], "links": []}}

        def import_palace(self, driver, *, export_data):
            calls["import_palace"] = export_data
            return {"status": "success", "message": "ok"}

    mp_router.lib_mind_palace = FakeLib()
    mp_router.get_driver = lambda: object()
    mp_router.lib_logs = type("L", (), {"__getattr__": lambda s, n: (lambda *a, **k: None)})()

    app = FastAPI()
    app.include_router(mp_router.router, prefix="/api")
    return TestClient(app), calls


def test_route_list_mindpalaces():
    c, calls = _router_client()
    r = c.get("/api/mindpalaces")
    assert r.status_code == 200 and r.json() == {"mindpalaces": [{"id": "e1", "name": "Alpha"}]}
    assert calls.get("list_mindpalaces")


def test_route_create_mindpalace_wires_to_create_mindpalace():
    # Regression guard: the route previously called the non-existent
    # lib_mind_palace.create_mind_palace (typo) -> AttributeError -> 500.
    c, calls = _router_client()
    r = c.post("/api/mindpalace", json={"name": "Beta", "description": "d"})
    assert r.status_code == 200, r.text
    assert calls.get("create_mindpalace") == ("Beta", "d")


def test_route_list_and_create_page():
    c, calls = _router_client()
    assert c.get("/api/mindpalace/e5/pages").status_code == 200
    assert calls["list_pages"] == "e5"
    r = c.post("/api/mindpalace/e5/page", json={"title": "T"})
    assert r.status_code == 200 and calls["create_page"] == ("e5", "T")


def test_route_get_page_found_and_404():
    c, calls = _router_client()
    assert c.get("/api/mindpalace/page/p1").status_code == 200
    assert c.get("/api/mindpalace/page/missing").status_code == 404


def test_route_save_blocks_threads_payload():
    c, calls = _router_client()
    r = c.post("/api/mindpalace/page/p1/blocks",
               json={"title": "T", "blocks": [{"type": "text", "content": "c"}]})
    assert r.status_code == 200
    page_id, title, blocks = calls["save_blocks"]
    assert page_id == "p1" and title == "T"
    assert blocks[0]["type"] == "text" and blocks[0]["content"] == "c"


def test_route_delete_export_import():
    c, calls = _router_client()
    assert c.delete("/api/mindpalace/page/p1").status_code == 200
    assert calls["delete_page"] == "p1"
    assert c.post("/api/mindpalace/mp_1/export").status_code == 200
    assert calls["export_palace"] == "mp_1"
    r = c.post("/api/mindpalace/import", json={"export_data": {"nodes": [], "links": []}})
    assert r.status_code == 200 and calls["import_palace"] == {"nodes": [], "links": []}


# ─────────────────────────────────────────────────────────────────────────
# Runner (mirrors test_router_contracts.py — no pytest dependency required)
# ─────────────────────────────────────────────────────────────────────────

def run_tests():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    print("Mind Palace baseline tests")
    print("=" * 60)
    failures = 0
    for t in tests:
        try:
            t()
            print(f"   [PASS] {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"   [FAIL] {t.__name__}: {type(e).__name__}: {e}")
    print("=" * 60)
    print(f"{len(tests) - failures}/{len(tests)} passed."
          if not failures else f"FAILED: {failures}/{len(tests)} failed.")
    return failures == 0


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)
