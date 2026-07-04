"""
Mind Palace links — [[wiki-links]] + backlinks.

Owns the wiki-link seam: on save, parse a page's block content for [[Page Title]]
references and reify each as a first-class edge (:Page)-[:LINKS_TO]->(:Page) (graph
is sacred — a link is an edge, not a scanned property), and read the inbound set
for a page's backlinks panel.

P1 CUT — PAGE-LEVEL (see MINDPALACE-IMPROVEMENTS.md #2). v1 stores links at the page
grain, not the block grain: all [[refs]] across a page's blocks collapse into one
(:Page)-[:LINKS_TO]->(:Page) edge per resolved target. Block-level anchoring (a
LINKS_TO carrying block_id/anchor) is deferred — not needed for the backlinks panel.

Graph shape:
  (src:Page)-[:LINKS_TO]->(dst:Page)                       # dst resolved by title
  backlinks(page) = MATCH (src:Page)-[:LINKS_TO]->(p:Page) RETURN src
  outgoing(page)  = MATCH (p:Page)-[:LINKS_TO]->(dst:Page) RETURN dst

Sync is a full page-level reconcile: DELETE this page's stale outgoing LINKS_TO,
then MERGE one edge per resolved target title. A ref whose title matches no page is
a dangling link (no edge is created — resolution is by title). These LINKS_TO edges
auto-appear in the Graph tab (the export projects every edge type unchanged).

Title resolution rides a plain INDEX on :Page(title) — NOT a uniqueness constraint:
the graph permits duplicate page titles (mirroring scripts/setup_constraints.py, which
deliberately omits a uniqueness constraint on any key the data can duplicate). When a
title resolves to >1 page, an edge is merged to each — the panel shows them all.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

from .crud import _coerce_int

# [[Wiki Link]] syntax — the canonical wiki-link token.
WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


# --- Cypher-string constructors ---------------------------------------------

# Idempotent index on :Page(title) so link resolution (MATCH by title) is cheap.
# A plain index, not a uniqueness constraint — duplicate titles are permitted.
ENSURE_TITLE_INDEX_CYPHER = (
    "CREATE INDEX page_title_index IF NOT EXISTS FOR (p:Page) ON (p.title)"
)

# Page-level reconcile step 1: drop this page's stale outgoing LINKS_TO before re-adding.
DELETE_OUTGOING_LINKS_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
OPTIONAL MATCH (p)-[r:LINKS_TO]->(:Page)
DELETE r
"""

# Page-level reconcile step 2: MERGE one edge per resolved target title (self-links
# excluded). UNWIND [] is a no-op, so a page with no links simply ends up edgeless.
SYNC_OUTGOING_LINKS_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
UNWIND $titles AS title
MATCH (target:Page {title: title}) WHERE target <> p
MERGE (p)-[:LINKS_TO]->(target)
"""

# Read both directions for the backlinks panel in one shot. Aggregate inbound first
# (WITH), then outbound, so the two OPTIONAL MATCHes don't multiply into a product.
GET_BACKLINKS_CYPHER = """
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
OPTIONAL MATCH (src:Page)-[:LINKS_TO]->(p)
WITH p, collect(DISTINCT {page_id: elementId(src), title: src.title}) AS backlinks
OPTIONAL MATCH (p)-[:LINKS_TO]->(dst:Page)
RETURN backlinks,
       collect(DISTINCT {page_id: elementId(dst), title: dst.title}) AS outgoing
"""


# --- Compositions -----------------------------------------------------------

def parse_wiki_links(content: str) -> List[str]:
    """Extract [[Target]] titles from a block's content (stripped; empties dropped). Pure."""
    return [m.strip() for m in WIKI_LINK_RE.findall(content or "") if m.strip()]


def page_link_titles(blocks: List[Dict[str, Any]]) -> List[str]:
    """The sorted, de-duplicated set of [[titles]] referenced anywhere on a page."""
    titles: set = set()
    for block in blocks or []:
        titles.update(parse_wiki_links(block.get("content") or ""))
    return sorted(titles)


def sync_page_links(driver, *, page_id: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Reconcile (:Page)-[:LINKS_TO]->(:Page) from this page's block content.

    Full page-level sync: parse every [[ref]], delete this page's stale outgoing
    LINKS_TO, then MERGE one edge per resolved target title. Idempotent — re-running
    on unchanged content yields the same edge set; removing a [[ref]] drops its edge."""
    titles = page_link_titles(blocks)
    page_id_int = _coerce_int(page_id)
    params = {"page_id": page_id, "page_id_int": page_id_int, "titles": titles}
    with driver.session() as session:
        session.run(ENSURE_TITLE_INDEX_CYPHER)
        session.run(DELETE_OUTGOING_LINKS_CYPHER, params)
        session.run(SYNC_OUTGOING_LINKS_CYPHER, params)
    return {"status": "success", "page_id": page_id, "links": titles}


def get_backlinks(driver, *, page_id: str) -> Dict[str, Any]:
    """Inbound + outbound LINKS_TO pages for the backlinks panel.

    Returns {"backlinks": [{page_id, title}, ...], "outgoing": [...]} — the pages that
    link TO this page, and the pages this page links out to. Unresolved slots (a page
    with no links yields a single null-valued map from collect) are dropped."""
    with driver.session() as session:
        rec = session.run(GET_BACKLINKS_CYPHER,
                          {"page_id": page_id, "page_id_int": _coerce_int(page_id)}).single()
    if not rec:
        return {"backlinks": [], "outgoing": []}
    data = dict(rec)
    return {
        "backlinks": [e for e in (data.get("backlinks") or []) if e and e.get("page_id")],
        "outgoing": [e for e in (data.get("outgoing") or []) if e and e.get("page_id")],
    }
