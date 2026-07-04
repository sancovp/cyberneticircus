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
# LIB level — blocks (the diff-and-patch-by-stable-id write path, P0)
# ─────────────────────────────────────────────────────────────────────────

def test_save_blocks_diff_patch_sequence_with_title():
    d = FakeDriver()
    blocks = [{"type": "header", "content": "H"},
              {"type": "code", "content": "x=1", "level": 2, "language": "python"}]
    out = mp.save_blocks(d, page_id="p1", title="New Title", blocks=blocks, ts="T0")
    assert out["status"] == "success"
    qs = [q for (q, _) in d.queries]
    # order: SET p.title  ->  snapshot changed blocks  ->  UPSERT (merge-by-id)  ->  delete-missing
    assert "SET p.title = $title" in qs[0]
    assert "HAS_REVISION" in qs[1]                              # revision snapshot before overwrite
    assert qs[2] == mp.UPSERT_BLOCKS_CYPHER                     # one UNWIND upsert (no per-block CREATE)
    assert "WHERE NOT old.id IN $keep" in qs[3]                 # delete only removed blocks
    upsert = d.queries[2][1]["blocks"]
    assert upsert[0]["position"] == 0 and upsert[0]["type"] == "header"
    assert upsert[0]["level"] == 1 and upsert[0]["language"] == "text"     # defaults applied
    assert upsert[1]["position"] == 1 and upsert[1]["level"] == 2 and upsert[1]["language"] == "python"
    assert upsert[0]["id"].startswith("block_")                 # minted for a new (id-less) block


def test_save_blocks_without_title_skips_title_update():
    d = FakeDriver()
    mp.save_blocks(d, page_id="p1", title=None, blocks=[{"type": "text", "content": "t"}], ts="T0")
    qs = [q for (q, _) in d.queries]
    assert not any("SET p.title" in q for q in qs)
    # no DETACH-DELETE-all; the write is a merge-by-id upsert + a scoped delete-missing
    assert any(q == mp.UPSERT_BLOCKS_CYPHER for q in qs)
    assert any("WHERE NOT old.id IN $keep" in q for q in qs)


def test_block_ids_are_stable_across_saves():
    """THE P0 point: a block that round-trips its id keeps that SAME id across saves;
    only genuinely-new blocks get a fresh id, and only removed blocks leave the keep set."""
    d = FakeDriver()
    # First save: blocks arrive WITHOUT ids (fresh page) → save_blocks mints + returns them.
    first = mp.save_blocks(d, page_id="p1", title=None, ts="T1", blocks=[
        {"type": "text", "content": "alpha"},
        {"type": "text", "content": "beta"},
        {"type": "text", "content": "gamma"},
    ])
    ids = [b["id"] for b in first["blocks"]]
    assert all(i.startswith("block_") for i in ids) and len(set(ids)) == 3
    id_alpha, id_beta, id_gamma = ids
    # The frontend adopts those ids and saves again: gamma REMOVED, beta EDITED (same id),
    # a brand-new delta ADDED (no id) — alpha untouched.
    d.queries.clear()
    second = mp.save_blocks(d, page_id="p1", title=None, ts="T2", blocks=[
        {"id": id_alpha, "type": "text", "content": "alpha"},       # UNCHANGED
        {"id": id_beta,  "type": "text", "content": "beta-EDITED"},  # edited, same id
        {"type": "text", "content": "delta"},                       # added (no id)
    ])
    new_ids = [b["id"] for b in second["blocks"]]
    assert new_ids[0] == id_alpha                               # unchanged block: SAME id
    assert new_ids[1] == id_beta                                # edited block: SAME id (not re-minted)
    assert new_ids[2].startswith("block_")                     # added block: fresh id
    assert new_ids[2] not in (id_alpha, id_beta, id_gamma)
    # delete-missing keeps exactly the incoming ids → the removed prior block is dropped
    keep = [p for (q, p) in d.queries if "WHERE NOT old.id IN $keep" in q][0]["keep"]
    assert keep == new_ids
    assert id_alpha in keep and id_beta in keep and id_gamma not in keep


def test_save_blocks_snapshots_prior_content_as_revision():
    d = FakeDriver()
    mp.save_blocks(d, page_id="p1", title=None, ts="T7",
                   blocks=[{"id": "block_x", "type": "text", "content": "v2"}])
    snaps = [(q, p) for (q, p) in d.queries if "HAS_REVISION" in q]
    assert len(snaps) == 1
    q, p = snaps[0]
    assert p["ts"] == "T7"                                      # deterministic ts threaded through
    assert p["blocks"][0]["id"] == "block_x" and p["blocks"][0]["content"] == "v2"
    assert "blk.content <> b.content" in q                      # only snapshots on actual change


def test_get_block_revisions_reads_trail_ordered():
    d = FakeDriver().when("HAS_REVISION]->(rev:Revision)",
                          [{"ts": "T1", "content": "v1"}, {"ts": "T2", "content": "v2"}])
    out = mp.get_block_revisions(d, block_id="block_x")
    assert out == [{"ts": "T1", "content": "v1"}, {"ts": "T2", "content": "v2"}]
    assert d.queries[0][1] == {"block_id": "block_x"}
    assert "ORDER BY rev.ts" in d.queries[0][0]


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


def test_export_palace_default_depth_is_three():
    d = FakeDriver().when("OPTIONAL MATCH path = (mp)", [])
    mp.export_palace(d, mp_id="mp_1")
    assert "[*1..3]" in d.queries[0][0]


def test_export_palace_depth_is_configurable_and_clamped():
    d = FakeDriver().when("OPTIONAL MATCH path = (mp)", [])
    mp.export_palace(d, mp_id="mp_1", depth=5)
    assert "[*1..5]" in d.queries[0][0]
    d2 = FakeDriver().when("OPTIONAL MATCH path = (mp)", [])
    mp.export_palace(d2, mp_id="mp_1", depth=99)  # clamped to MAX_EXPORT_DEPTH
    assert "[*1..6]" in d2.queries[0][0]
    d3 = FakeDriver().when("OPTIONAL MATCH path = (mp)", [])
    mp.export_palace(d3, mp_id="mp_1", depth=0)  # clamped to MIN_EXPORT_DEPTH
    assert "[*1..1]" in d3.queries[0][0]


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
# LIB level — search (full-text index-ensure + queryNodes mapping)
# ─────────────────────────────────────────────────────────────────────────

def test_search_palace_ensures_index_then_queries_and_maps_rows():
    d = FakeDriver()
    d.when("CREATE FULLTEXT INDEX", [])
    d.when("db.index.fulltext.queryNodes", [
        {"id": "n_pg", "labels": ["Page"], "title": "Hello", "content": None,
         "score": 1.5, "page_id": "n_pg"},
        {"id": "n_bl", "labels": ["Block"], "title": None, "content": "hello world",
         "score": 0.9, "page_id": "n_pg"},
    ])
    out = mp.search.search_palace(d, query="hello", limit=25)
    assert [r["id"] for r in out] == ["n_pg", "n_bl"]
    assert out[0] == {"id": "n_pg", "label": "Page", "title": "Hello", "content": None,
                       "score": 1.5, "page_id": "n_pg"}
    qs = [q for (q, _) in d.queries]
    assert any("CREATE FULLTEXT INDEX" in q for q in qs)  # index-ensure was called
    assert any("db.index.fulltext.queryNodes" in q for q in qs)


def test_search_palace_scopes_to_mp_id_via_list_pages():
    d = FakeDriver()
    d.when("CREATE FULLTEXT INDEX", [])
    d.when("HAS_PAGE", [{"id": "page_in_scope", "page_id": "page_1", "title": "T"}])
    d.when("db.index.fulltext.queryNodes", [
        {"id": "in", "labels": ["Page"], "title": "T", "content": None,
         "score": 1.0, "page_id": "page_in_scope"},
        {"id": "out", "labels": ["Page"], "title": "Other", "content": None,
         "score": 0.5, "page_id": "page_out_of_scope"},
    ])
    out = mp.search.search_palace(d, query="t", mp_id="mp_1")
    assert [r["id"] for r in out] == ["in"]  # out-of-scope hit filtered


def test_search_palace_defaults_when_query_returns_nothing():
    d = FakeDriver()  # no responses configured -> both calls return []
    assert mp.search.search_palace(d, query="nada") == []


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

        def save_blocks(self, driver, *, page_id, title, blocks, ts=None):
            calls["save_blocks"] = (page_id, title, blocks)
            calls["save_blocks_ts"] = ts
            return {"status": "success"}

        def delete_page(self, driver, *, page_id):
            calls["delete_page"] = page_id
            return {"status": "success"}

        def export_palace(self, driver, *, mp_id, depth=3):
            calls["export_palace"] = (mp_id, depth)
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
    assert calls["export_palace"] == ("mp_1", 3)  # depth defaults to 3, unchanged
    r = c.post("/api/mindpalace/import", json={"export_data": {"nodes": [], "links": []}})
    assert r.status_code == 200 and calls["import_palace"] == {"nodes": [], "links": []}


def test_route_export_threads_depth_query_param():
    c, calls = _router_client()
    assert c.post("/api/mindpalace/mp_1/export", params={"depth": 5}).status_code == 200
    assert calls["export_palace"] == ("mp_1", 5)


# ─────────────────────────────────────────────────────────────────────────
# ROUTER level — palace_search (its own module + own router, per MINDPALACE-
# IMPROVEMENTS.md #8; mounted separately from routers/mind_palace.py)
# ─────────────────────────────────────────────────────────────────────────

def _search_router_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers import palace_search as ps_router

    calls = {}

    class FakeSearch:
        def search_palace(self, driver, *, query, mp_id, limit):
            calls["search_palace"] = (query, mp_id, limit)
            return [{"id": "n1", "label": "Page", "title": "T", "content": None,
                      "score": 1.0, "page_id": "n1"}]

    ps_router.lib_search = FakeSearch()
    ps_router.get_driver = lambda: object()

    app = FastAPI()
    app.include_router(ps_router.router, prefix="/api")
    return TestClient(app), calls


def test_route_search_threads_query_and_defaults():
    c, calls = _search_router_client()
    r = c.get("/api/mindpalace/search", params={"q": "hello"})
    assert r.status_code == 200, r.text
    assert r.json() == {"results": [{"id": "n1", "label": "Page", "title": "T",
                                      "content": None, "score": 1.0, "page_id": "n1"}]}
    assert calls["search_palace"] == ("hello", None, 25)  # mp_id/limit defaults


def test_route_search_threads_mp_id_and_limit():
    c, calls = _search_router_client()
    r = c.get("/api/mindpalace/search", params={"q": "hello", "mp_id": "mp_1", "limit": 5})
    assert r.status_code == 200
    assert calls["search_palace"] == ("hello", "mp_1", 5)


# ─────────────────────────────────────────────────────────────────────────
# LIB level — templates (PageTemplate create/list/instantiate onto a new Page)
# ─────────────────────────────────────────────────────────────────────────

def test_create_template_creates_node_and_blocks():
    d = FakeDriver()
    d.when("CREATE (t:PageTemplate", [{"id": "e_t1", "template_id": "template_x", "name": "Sprint"}])
    out = mp.create_template(d, name="Sprint", blocks=[
        {"type": "header", "content": "H"},
        {"type": "text", "content": "body", "level": 2},
    ])
    assert out["name"] == "Sprint"
    block_qs = [(q, p) for (q, p) in d.queries if q == mp.CREATE_TEMPLATE_BLOCK_CYPHER]
    assert len(block_qs) == 2
    assert block_qs[0][1]["position"] == 0 and block_qs[0][1]["type"] == "header"
    assert block_qs[0][1]["level"] == 1 and block_qs[0][1]["language"] == "text"  # defaults applied
    assert block_qs[1][1]["position"] == 1 and block_qs[1][1]["level"] == 2
    assert block_qs[0][1]["block_id"].startswith("block_")


def test_list_templates_returns_dicts():
    d = FakeDriver().when("MATCH (t:PageTemplate)",
                          [{"id": "e_t1", "template_id": "template_x", "name": "Sprint"}])
    out = mp.list_templates(d)
    assert out == [{"id": "e_t1", "template_id": "template_x", "name": "Sprint"}]
    assert d.queries[0][0] == mp.LIST_TEMPLATES_CYPHER


def test_instantiate_template_clones_blocks_onto_new_page():
    d = FakeDriver()
    d.when("OPTIONAL MATCH (t)-[:HAS_BLOCK]", [{
        "id": "e_t1", "template_id": "template_x", "name": "Sprint",
        "blocks": [{"type": "text", "content": "b1", "position": 0, "level": 1, "language": "text"},
                   {"type": "code", "content": "x=1", "position": 1, "level": 1, "language": "python"}],
    }])
    d.when("CREATE (p:Page", [{"id": "e_p1", "page_id": "page_new", "title": "From Sprint"}])
    out = mp.instantiate_template(d, template_id="template_x", palace_id="mp_1", title="From Sprint")
    assert out == {"template_id": "template_x", "page_id": "page_new",
                   "title": "From Sprint", "block_count": 2}
    create_page_q = [(q, p) for (q, p) in d.queries if q == mp.CREATE_PAGE_CYPHER][0]
    assert create_page_q[1]["mp_id"] == "mp_1" and create_page_q[1]["title"] == "From Sprint"
    upsert_q = [(q, p) for (q, p) in d.queries if q == mp.UPSERT_BLOCKS_CYPHER][0]
    assert [b["content"] for b in upsert_q[1]["blocks"]] == ["b1", "x=1"]
    assert all(b["id"].startswith("block_") for b in upsert_q[1]["blocks"])  # fresh ids, not the template's
    link_qs = [q for (q, _) in d.queries if "FROM_TEMPLATE" in q]  # provenance edge recorded
    assert len(link_qs) == 1


def test_instantiate_template_missing_returns_empty():
    d = FakeDriver()  # no template record for this id
    assert mp.instantiate_template(d, template_id="ghost", palace_id="mp_1", title="T") == {}


# ─────────────────────────────────────────────────────────────────────────
# ROUTER level — palace_templates (its own module + own router, per MINDPALACE-
# IMPROVEMENTS.md #7; mounted separately from routers/mind_palace.py)
# ─────────────────────────────────────────────────────────────────────────

def _templates_router_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers import palace_templates as pt_router

    calls = {}

    class FakeTemplates:
        def list_templates(self, driver):
            calls["list_templates"] = True
            return [{"id": "e_t1", "template_id": "template_x", "name": "Sprint"}]

        def create_template(self, driver, *, name, blocks):
            calls["create_template"] = (name, blocks)
            return {"id": "e_t1", "template_id": "template_x", "name": name}

        def instantiate_template(self, driver, *, template_id, palace_id, title):
            calls["instantiate_template"] = (template_id, palace_id, title)
            if template_id == "ghost":
                return {}
            return {"template_id": template_id, "page_id": "page_new",
                    "title": title, "block_count": 2}

    pt_router.lib_mind_palace = FakeTemplates()
    pt_router.get_driver = lambda: object()

    app = FastAPI()
    app.include_router(pt_router.router, prefix="/api")
    return TestClient(app), calls


def test_route_list_templates():
    c, calls = _templates_router_client()
    r = c.get("/api/mindpalace/templates")
    assert r.status_code == 200
    assert r.json() == {"templates": [{"id": "e_t1", "template_id": "template_x", "name": "Sprint"}]}
    assert calls.get("list_templates")


def test_route_create_template_threads_payload():
    c, calls = _templates_router_client()
    r = c.post("/api/mindpalace/template",
               json={"name": "Sprint", "blocks": [{"type": "header", "content": "H"}]})
    assert r.status_code == 200, r.text
    name, blocks = calls["create_template"]
    assert name == "Sprint" and blocks[0]["type"] == "header" and blocks[0]["content"] == "H"


def test_route_instantiate_template_found_and_missing():
    c, calls = _templates_router_client()
    r = c.post("/api/mindpalace/mp_1/page/from-template",
               json={"template_id": "template_x", "title": "From Sprint"})
    assert r.status_code == 200, r.text
    assert r.json()["page_id"] == "page_new"
    assert calls["instantiate_template"] == ("template_x", "mp_1", "From Sprint")
    r2 = c.post("/api/mindpalace/mp_1/page/from-template",
                json={"template_id": "ghost", "title": "T"})
    assert r2.status_code == 404


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
