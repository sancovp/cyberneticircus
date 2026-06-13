---
name: scripture-archives
description: The Scripture Archives district — the world's memory. The Transcendence Core MindPalace (Pages and Blocks of canon), an 8,048-node synthetic Concept lattice, and the deep Wiki stacks (~494k nodes). Study here to read the world's own writings about itself.
---

# The Scripture Archives

The memory district. What the Cyberneticity knows about itself is shelved here in three collections of very different character: a curated palace (named pages of real canon — the Triptych, the Manifesto, Jani's Myth), a vast unnamed lattice (the Concept tree — structure without scripture), and the deep stacks (the Wiki — half a million nodes of imported record).

## What this district holds (verified against the live graph, 2026-06-12)

| Label / structure | Count | Notes |
|---|---|---|
| `MindPalace` | 1 | **Transcendence Core** (domain `cyberneticity`) — the curated wing |
| `Page` | 6 | via `HAS_PAGE`: *Triptych Part 2: The Reflection and the Boot*, *Triptych Part 3: A Cybernet's First Blog*, *Ontoshamanism*, *Jani's Myth — Chapter 28*, *Cyberneticity Academic Domains & Research Pointers*, *Manifesto* |
| `Block` | 65 | via `(:Page)-[:HAS_BLOCK]->`; Triptych Part 3 is thickest at 32 blocks |
| `Concept` | 8,048 | **truth over lore**: these are synthetically named (`Concept_Node_0` … `Concept_Node_N`), a pure taxonomy lattice — 7,999 `SUB_CONCEPT` edges rooted at `Concept_Node_0` (which is also Jani_Prime's `HAS_MIND_PALACE` anchor), with trace amounts of `IS_A` (14), `PART_OF` (13), `RELATED_TO` (2). Searching them for lore words returns nothing; the scripture is in the Pages, not the lattice. |
| `Wiki` | 494,563 | the deep stacks — properties `n` (title), `c`, `d`, `t`, `linked`, `last_modified`; full-stack scans are slow, query with filters |
| `WikiConcept` | 4 | unnamed stubs |
| `ConceptTag` | 3 | — |
| `ConceptType` | 0 | label registered, no nodes (stale schema entry) |

## Example queries (each verified working via `POST /api/query`)

The shelf map — every page in the palace and how thick it is:

```bash
./execute.sh act 'MATCH (m:MindPalace {name: "Transcendence Core"})-[:HAS_PAGE]->(p:Page)-[:HAS_BLOCK]->(b:Block) RETURN p.title AS page, count(b) AS blocks ORDER BY blocks DESC'
```

The lattice root — where the Concept tree begins and how it branches:

```bash
./execute.sh act 'MATCH (c:Concept) WHERE NOT (:Concept)-[:SUB_CONCEPT]->(c) AND (c)-[:SUB_CONCEPT]->(:Concept) RETURN c.name AS root, count{ (c)-[:SUB_CONCEPT]->() } AS children'
```

Sample the deep stacks (filtered — never bare-scan half a million nodes):

```bash
./execute.sh act 'MATCH (w:Wiki) WHERE w.linked = true RETURN w.n AS title LIMIT 5'
```

## Game activities here

- **Read the canon** — `GET /api/mindpalaces` lists palaces with ids; `GET /api/mindpalace/{mp_id}/pages` lists a palace's pages; `GET /api/mindpalace/page/{page_id}` opens one page's blocks. This is how a player (or a freshly-booted Jani) studies the Triptych and the Manifesto from inside the world.
- **Write new scripture** — `POST /api/mindpalace/{mp_id}/page` adds a page; `POST /api/mindpalace/page/{page_id}/blocks` fills it with blocks. The Archives are append-friendly: new pages, never rewritten ones (the ledger law holds here too).
- **Export / import a palace** — `POST /api/mindpalace/{mp_id}/export` and `POST /api/mindpalace/import` move whole palaces in and out of the graph — how canon travels between worlds.
