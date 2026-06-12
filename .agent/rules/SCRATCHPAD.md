---
name: scratchpad
description: Short-term working notes. The canonical spec is at `cyberneticircus/DESIGN.md` (the single source of truth for the cyberneticircus architecture, now refined to match the actual state of the codebase). The architecture diagrams are at `cyberneticircus/.claude/rules/cyberneticircus-architecture.md`. Use this scratchpad for transient session notes; when something becomes durable, it moves to DESIGN.md.
metadata:
  type: scratchpad
---

# SCRATCHPAD — short-term working notes

> The canonical spec is `cyberneticircus/DESIGN.md` (read it for any architectural question).
> The architecture diagrams are at `cyberneticircus/.claude/rules/cyberneticircus-architecture.md`.
> This file is for transient session notes. When something becomes durable, it moves to DESIGN.md.

---

## Current state of the codebase (refined 2026-06-12)

DESIGN.md is now refined to honestly describe the actual state:
- §11.5 module map: target sizes + actual sizes + status (✅ done / ❌ needs refactor / ✅ scaffolded)
- §11.6 implementation list: [x] for verified-done (with file:line refs), [/] for scaffolded, [ ] for not-done
- §11.6 [x] items verified by direct code/file inspection — all accurate

## What's DONE (12 [x] items in DESIGN.md §11.6)

| thing | location |
|---|---|
| MCP reduced to 3 tools (query_database, development_server, commands) | `neo4j_cypher_mcp/server.py:1-224` |
| Per-cybernet `:ExecutionState` via `:HAS_LIFECYCLE` edge (the per-cybernet lock, REPLACES the old `:HAS_TRAVERSAL → :TraversalState` pattern) | `cyberneticircus/routers/cybernet.py:82` (equip creates ExecutionState at entry step) + `cyberneticircus/lib/lifecycle.py:188-194` (SET_EXECUTION_STEP_CYPHER). live verified: 2 `:HAS_LIFECYCLE` edges, 0 `:HAS_TRAVERSAL` edges (2026-06-12). NB: the runtime gating via `lib/state_machines.py` cypher builders is still broken — see session 8 + DESIGN.md §11.8. |
| Per-cybernet lock scoping (4 functions take `cybernet_name`) | `cyberneticircus/db_logic.py:655, 725, 953, 1028` |
| Duplicate `session.run` bug fixed in `get_active_traversal_step` | was around `cyberneticircus/db_logic.py:674` (line now removed) |
| Orphan cleanup (TraversalState) — historical | 1 orphan from prior session `DETACH DELETE`'d. post-refactor live state: 0 `:HAS_TRAVERSAL` edges, 0 `:TraversalState` nodes, 2 `:HAS_LIFECYCLE` edges, 2 `:ExecutionState` nodes (Jani_Prime + JaniScribe, both on `janic_cycle_sm`, both `status='locked'`). |
| Heaven skills redundancy cleanup (15→11) | `~/.claude/skills/` |
| BaseHeavenAgent concurrent-run verified | `heaven_base/baseheavenagent.py:147` (HookRegistry per-instance) |
| cyberneticircus cloned | `~/claude_code/cyberneticircus/` from `https://github.com/sancovp/cyberneticircus.git` |
| cyberneticircus MCP at user level | `~/.claude.json` mcpServers.cyberneticircus + `~/.claude/settings.json` enabledMcpjsonServers: `["playwright", "cyberneticircus"]` |
| Vocabulary disambiguation | procedure (internal) vs skill (external) vs gear loadout |
| Architecture diagrams | DESIGN.md §11.1-11.5 + companion rule at `cyberneticircus/.claude/rules/cyberneticircus-architecture.md` |

## What's SCAFFOLDED (1 [/] item)

| thing | location |
|---|---|
| lib/ library functions (5 modules) | `cyberneticircus/lib/{cybernet,state_machines,transitions,surrogates,ghost_shell}.py` (139 total lines). cypher-string constructors exist but are not exercised by any caller yet. |

## What's NOT DONE (6 [ ] items in DESIGN.md §11.6)

1. refactor `cyberneticircus/web_server.py` (1775 → ≤100 lines)
2. refactor `cyberneticircus/engine.py` (1006 → ≤300 lines)
3. refactor `cyberneticircus/db_logic.py` (1033 → ≤200 lines)
4. convert at least one thing end-to-end as procedure + external skill (worked example)
5. migrate visualizer (`static/app.js`) to cypher via `/api/query`
6. delete FastAPI endpoints the visualizer no longer needs post-migration

these 6 are the work that needs to happen for the codebase to fully match the target state described in DESIGN.md.

---

## Active TODO (in priority order, per DESIGN.md §11.6)

1. **refactor web_server.py** — extract all logic (mind palace / specs / graph / commands / etc.) into `lib/`. keep only the cypher shell endpoint + thin cypher-wrapper endpoints (or migrate the visualizer and delete the wrappers). target: ≤100 lines, no logic.
2. **refactor engine.py** — extract per-cybernet traversal logic + step-prompt builder + the simulator / scorer / evolution / etc. into `lib/`. keep only the LLM runner (call minimax-M3 via sdna + heaven-framework, run cypher, gate writes). target: ≤300 lines.
3. **refactor db_logic.py** — keep only the LLM-loop gates (`is_traversal_locked`, `get_active_traversal_step`, `query_database`, `progress_traversal`, `populate_default_graphs`). move surrogate CRUD + transition weight + mind palace + specs to `lib/`. target: ≤200 lines.
4. **worked example: convert one thing to procedure + external skill** — pick a candidate (e.g., `jester_rite` → `jester` procedure). write the external skill in `~/.claude/skills/<name>/SKILL.md`. verify the round-trip: LLM reads the skill, writes the cypher, activates the procedure, the procedure runs.
5. **migrate the visualizer** — `static/app.js` currently calls 8 specialized endpoints (`/api/agent_logs`, `/api/graph`, `/api/mindpalace*`, `/api/specs/*`). migrate each to call `/api/query` directly with the right cypher, or wrap in thin cypher-pass-through endpoints in web_server.py.
6. **delete unused endpoints** post-migration.

---

## Sessions history (compressed)

(see DESIGN.md §11.6 for the full implementation list with file:line refs; this is a summary by session)
- **session 1:** cyberneticircus installed at user level (MCP path config + enabledMcpjsonServers + antigravity JSONs).
- **session 2:** per-cybernet TraversalState refactor (HAS_TRAVERSAL + cybernet_name + lock scoping). duplicate session.run bug found + fixed. orphan cleanup done.
- **session 3:** heaven skills 15→11. BaseHeavenAgent per-instance verified. architecture correction: external skill = thin pointer, internal thing = "procedure" (was "skill").
- **session 4:** MCP reduced 15→3 tools. 12 specialized endpoints + tools removed. lib/ created with 5 cypher-constructor modules. visualizer dependencies mapped (8 endpoints).
- **session 5:** DESIGN.md + cyberneticircus-architecture.md updated with the architecture spec, mermaid diagrams, module map, implementation list with file:line refs. status legend added ([x]/[/]/[ ]).
- **session 6 (now):** refined DESIGN.md to match the actual state — precise line numbers, [/] for scaffolded-but-not-exercised, verified the [x] claims against the code.
- **session 7:** the [ ] refactor pass. web_server.py 1796→68 lines per APIRouter pattern (9 routers at level 3). 7 new lib/ modules + 3 extended. engine.py 293 lines (already thin facade, was done). db_logic.py 200 lines (already thin facade, was done). worked example: jester_rite_sm + activate-jester-ritual/SKILL.md (round-trip verified). created `.claude/rules/neo4j-state.md` (live ground-truth: 10 cybernets, 7 SMs, 31 gated steps, 2 active ExecutionStates). discovered architecture drift: HAS_TRAVERSAL→TraversalState is gone, actual is HAS_LIFECYCLE→ExecutionState. DESIGN.md + cyberneticircus-architecture.md still have stale references — small fix needed next session. state: **15 [x] / 2 [ ] / 1 [/]**.
- **session 8:** the docs fix + the runtime gating bug discovery. **docs fix**: replaced all `HAS_TRAVERSAL`/`TraversalState` references in `DESIGN.md` (§6, §8, §11.3, §11.4, §11.5, §11.6) + `cyberneticircus-architecture.md` (§3, §4, §5, §7) + `concentric-ontology.md` with `:HAS_LIFECYCLE`/`:ExecutionState` references. restored + updated 3 historical [x] items in §11.6 (per-cybernet lock scoping, duplicate session.run bug, orphan cleanup) so the document matches both the current state and the history. added new §11.8 documenting the runtime gating drift. **runtime gating bug discovered**: the cypher-string builders in `cyberneticircus/lib/state_machines.py` (called by `lib/gates.py:get_active_traversal_step` + `auto_progress_step` + `scan_and_trigger_traversal`) match against the OLD `:HAS_TRAVERSAL → :TraversalState` pattern, which doesn't exist in the live graph. result: `is_traversal_locked()` always returns False, `_evaluate_pattern()` always returns `(False, None)`, the `required_pattern` gate is OFF — the LLM can write anything via `query_database` regardless of which step it's on. **what still works**: the equip path (`routers/cybernet.py:82` creates ExecutionState directly), the bootstrap procedure (jester_rite worked example), the status endpoint. **fix scope**: ~120 lines of cypher in `lib/state_machines.py` + ~50 lines in `lib/lifecycle.py` (LOCK_OR_CREATE / FORCE_ALIGN / READ_TRAVERSAL_STEP) + 1 logic change in `lib/gates.py:auto_progress_step`. NOT done this session — flagged in §11.8 + zettel. **verification script added**: `cyberneticircus/scripts/verify_no_stale_traversalstate.sh` greps for stale references and fails loudly if any are in unexpected locations. current: 38 expected (all in legacy/dead/test/sacred code), 0 unexpected. state: **15 [x] / 2 [ ] / 1 [/] + 1 NEW follow-up in §11.8 (runtime gating refactor, ~30-60 min)**.
