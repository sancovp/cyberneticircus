"""
Mind Palace links — [[wiki-links]] + backlinks.  (FLEET STUB — see MINDPALACE-IMPROVEMENTS.md)

Owns the wiki-link seam: on save, parse a block's content for [[Page Title]]
references and reify each as a first-class edge (:Page)-[:LINKS_TO]->(:Page) (graph
is sacred — a link is an edge, not a scanned property), and read the inbound set
for a page's backlinks panel.

Graph shape (target):
  (src:Page)-[:LINKS_TO {block_id, anchor}]->(dst:Page)
  backlinks(page) = MATCH (src:Page)-[:LINKS_TO]->(p:Page) WHERE <id match> RETURN src

This module is a stub so a fleet agent can own it end-to-end without touching
crud/blocks/graph. Nothing here is wired into the router yet.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

# [[Wiki Link]] syntax — the canonical wiki-link token.
WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def parse_wiki_links(content: str) -> List[str]:
    """Extract [[Target]] titles from a block's content. (Pure; safe to use now.)"""
    return [m.strip() for m in WIKI_LINK_RE.findall(content or "") if m.strip()]


def sync_page_links(driver, *, page_id: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """ASPIRATIONAL: reconcile (:Page)-[:LINKS_TO]->(:Page) edges from block content."""
    raise NotImplementedError("palace.links.sync_page_links — fleet feature (backlinks/wiki-links)")


def get_backlinks(driver, *, page_id: str) -> List[Dict[str, Any]]:
    """ASPIRATIONAL: inbound :LINKS_TO pages for the backlinks panel."""
    raise NotImplementedError("palace.links.get_backlinks — fleet feature (backlinks panel)")
