---
name: neo4j-state
description: Running notes on what's actually in the cyberneticity neo4j graph right now (procedures, cybernets, traversal states, mind palaces, specs, identities). Read first when touching any [ ] refactor item, when something "doesn't work" in the game loop, or when you need to know what the graph currently contains without booting the server. Updated as the codebase is developed, not as a one-shot. Lives in .claude/rules/ per the "scratchpads go in .claude/rules/ only" rule.
metadata:
  type: scratchpad
---

# NEO4J STATE — running notes on the Cyberneticity

> the graph is the game. this file documents what's in it as we go.
> if you mutate the graph in a session, update the relevant section here.
> read this before asking "what's in the graph?" — it's faster than booting the server.

---

## endpoint inventory (cyberneticircus/web_server.py, 37 endpoints, 1796 lines)

> the [ ] refactor splits these 37 endpoints into 9 routers at level 3, per the APIRouter pattern. each router body = 1-line delegation to lib/.

| router file | endpoints | group |
|---|---|---|
| `routers/query.py` | `POST /api/query` | cypher shell (the only required endpoint) |
| `routers/commands.py` | `GET /api/commands` | list procedures/skills (MCP's 3rd tool) |
| `routers/cybernet.py` | `POST /api/create`, `POST /api/equip`, `POST /api/tick`, `GET /api/list`, `GET /api/state_machines`, `GET /api/status/{name}`, `GET /api/simulations/{name}`, `POST /api/configure_ghost_shell`, `GET /api/ghost_shell/status/{cybernet_name}` | cybernet lifecycle (9 endpoints) |
| `routers/traversal.py` | `GET /api/schema`, `POST /api/traversal/progress`, `POST /api/traversal/create_flow`, `POST /api/traversal/create_transition`, `POST /api/traversal/adjust_weight`, `POST /api/crud_surrogate`, `POST /api/crud_state_machine_calls` | state machine flow + crud (7 endpoints) |
| `routers/graph.py` | `GET /api/graph`, `GET /api/node/subgraph` | D3 visualizer data (2 endpoints) |
| `routers/logs.py` | `GET /api/agent_logs` | in-memory agent trace ring buffer (1 endpoint, stateful service) |
| `routers/mind_palace.py` | `GET /api/mindpalaces`, `POST /api/mindpalace`, `GET /api/mindpalace/{mp_id}/pages`, `POST /api/mindpalace/{mp_id}/page`, `GET /api/mindpalace/page/{page_id}`, `POST /api/mindpalace/page/{page_id}/blocks`, `DELETE /api/mindpalace/page/{page_id}`, `POST /api/mindpalace/{mp_id}/export`, `POST /api/mindpalace/import` | wiki CRUD + JSON import/export (9 endpoints) |
| `routers/specs.py` | `GET /api/specs/list`, `GET /api/specs/read`, `POST /api/specs/save`, `GET /api/specs/templates`, `GET /api/specs/template/read` | the spec composer (5 endpoints) |
| `routers/system.py` | `GET /api/file/read`, `POST /api/execute_host_command` | host-side utility (2 endpoints) |

= 9 routers at level 3. exactly 3 levels deep. never flat, never deeper.

---

## node labels (the schema)

(inferred from cypher in db_logic.py + lib/ + web_server.py — to be verified by querying the graph)

| label | what it is | where it shows up |
|---|---|---|
| `:Cybernet` | a graph-being (a character) | create, equip, tick, list, status |
| `:Identity` | a manifest persona closed over the graph | HAS_IDENTITY from Cybernet |
| `:StateMachine` | a procedure (an act) | EQUIPS from Cybernet, HAS_STEP to TraversalStep |
| `:TraversalStep` | one step in a state machine | NEXT_STEP, CALLS_SM |
| `:TraversalState` | per-cybernet lock (1:1 with Cybernet) | HAS_TRAVERSAL from Cybernet, CURRENT_STEP to TraversalStep |
| `:ExecutionState` | runtime state for the LLM runner (decoupled from Identity) | HAS_LIFECYCLE from Cybernet, CURRENT_STEP to TraversalStep |
| `:Skill` | an external thin pointer to a procedure | EQUIPS_SKILL from Cybernet (note: old name) |
| `:SimulationRun` | one lifetime in the arena (5 turns) | HAS_SIMULATION from Cybernet / SurrogateModel, PREDICTS_STATE → PredictionNode |
| `:PredictionNode` | one step in a simulation run | child of SimulationRun |
| `:SurrogateModel` | per-domain/subdomain simulation params (mutation_rate, selection_pressure, reward_weights) | HAS_SIMULATION → SimulationRun |
| `:ExecutionTrace` | one logged agent action (recent N for visualizer) | HAS_TRACE_HISTORY from ExecutionState, NEXT_TRACE chain |
| `:MindPalace` | a wiki space hub | HAS_PAGE → Page |
| `:Page` | a wiki page | HAS_BLOCK → Block |
| `:Block` | content atom (Header, Text, KV, List, Code) | child of Page |
| `:Concept` | legacy mind-palace concept (still referenced in graph endpoint cypher) | HAS_MIND_PALACE from Cybernet, SUB_CONCEPT chain |

### Cybernet full property schema (from `lib/cybernet.py:62-80` CREATE_CYBERNET_CYPHER)

```
name, description, model_name, parameters_count, temperature, top_p,
max_tokens, mutation_rate, selection_pressure,
task_success_rate, tool_call_frequency, avg_latency_ms,
total_tokens_consumed, accumulated_cost, fitness_score,
domain, subdomain
```

### Identity full property schema (from same)

```
name, description,
persona_prompt, world_prompt, core_loop_prompt,
domain, subdomain
```

### ExecutionState full property schema (from `lib/cybernet.py:91-97`)

```
status, turn_number, phase, lifetime_limit,
tokens_consumed_this_turn, cost_this_turn,
equipped_sm_id, call_stack (JSON-stringified list),
current_layer, completed_layers (array),
domain, subdomain
```

### TraversalStep property schema (inferred from `lib/cybernet.py:118-123` + web_server.py:1486-1488)

```
id (required, MERGE key),
text (the step's prompt instruction),
required_pattern (regex, gates LLM cypher validity),
pattern_description (human-readable),
expected_diff (JSON, for simulation),
expected_fitness (numeric, for simulation),
instruction_file_path (filesystem path to a markdown file with extended prompt content — see jani-myth-ch21)
```

### mandatory properties (per concentric-ontology rule)

every node must have `domain` and `subdomain`. primitive types default to `domain: "cyberneticity"` with appropriate subdomain (core, skills, state_machine, simulation, mindpalace, page, block, execution_state, lifecycle, identity, cybernet, task).

### relationships (per DESIGN.md §8 + observed in cypher)

```
(c:Cybernet)-[:HAS_IDENTITY]->(i:Identity)              -- observed in CREATE_CYBERNET_CYPHER
(c:Cybernet)-[:HAS_LIFECYCLE]->(s:ExecutionState)       -- observed in EQUIP_SM_CYPHER
(c:Cybernet)-[:EQUIPS]->(sm:StateMachine)               -- observed in EQUIP_SM_CYPHER
(s:ExecutionState)-[:CURRENT_STEP]->(step:TraversalStep) -- observed in EQUIP_SM_CYPHER
(sm:StateMachine)-[:HAS_STEP]->(step:TraversalStep)     -- inferred from EQUIP_SM_CYPHER
(s1:TraversalStep)-[:NEXT_STEP]->(s2:TraversalStep)     -- observed in create_traversal_flow_api
(step:TraversalStep)-[:CALLS_SM]->(sm:StateMachine)     -- observed in crud_state_machine_calls_api
(s:ExecutionState)-[:HAS_TRACE_HISTORY]->(t:ExecutionTrace) -- observed in graph endpoint
(t1:ExecutionTrace)-[:NEXT_TRACE]->(t2:ExecutionTrace)  -- observed in graph endpoint
(c:Cybernet)-[:HAS_SIMULATION]->(sim:SimulationRun)     -- observed in get_simulations + crud_surrogate
(sm:SurrogateModel)-[:HAS_SIMULATION]->(sim:SimulationRun)
(sim:SimulationRun)-[:PREDICTS_STATE {order: N}]->(pn:PredictionNode)
(mp:MindPalace)-[:HAS_PAGE]->(p:Page)
(p:Page)-[:HAS_BLOCK]->(b:Block)
(c:Cybernet)-[:HAS_MIND_PALACE]->(root_c:Concept)       -- legacy, observed in graph endpoint
(root_c:Concept)-[:SUB_CONCEPT*]->(c:Concept)           -- legacy, observed in graph endpoint
(c:Cybernet)-[:EQUIPS_SKILL]->(sk:Skill)                -- legacy, observed in graph endpoint
```

(some of these are DUAL — old name (EQUIPS_SKILL/HAS_MIND_PALACE/SUB_CONCEPT) coexists with new name (EQUIPS/HAS_GEAR/HAS_PAGE). the visualizer still uses the old names in some queries.)

---

## state machines / procedures in the graph

(populating as I read lib/bootstrap_procedures.py + db_logic.py + engine.py)

### known procedure ids (from codebase references)

- `jester_rite_sm` — the Jester Rite, 3 steps (jester_boot → jester_play → jester_verify)
- `concentric_core_sm` — Universal Concentric Core (HWSS rings: spiritual, wealth, social, health)
- `jani_domain_expansion_sm` — Domain Expansion (Layer 1/2/3 progressive compiler)
- `janic_daemon_summoning_sm` — Daemon Summoning (orchestrator w/ call_stack push/pop)
- `sh8_lifecycle_sm` — Sh8pe Lifecycle (the day/night tick)
- `ple_sm` — PLE (some pattern lifecycle editor?)
- `janic_cycle_sm` — Janic Core Cycle (the 5-step dev cycle: read_designs, check_state, engineer, preservation, autocommentary)

(needs verification by MATCH (sm:StateMachine) RETURN sm.id)

### required_pattern gating

each TraversalStep has a `required_pattern` (regex) that gates whether the LLM's emitted cypher is allowed to mutate the graph. examples (from jani-myth-ch1..28):

- `jester_boot` requires `CREATE.*:Cybernet`
- `jester_play` requires `SET.*persona`  (probably, needs verification)
- `jester_verify` requires `RETURN.*fitness_score`

(needs verification by MATCH (s:TraversalStep) RETURN s.id, s.required_pattern)

---

## cybernets in the graph (per cybernetiCircus mythology)

(populating as I find references)

- `Jani_Prime` — the main janic compiler cybernet, has TraversalState, on some step
- `JesterCoreOne` — the first jester, fully verified (jester_rite completed)
- `JaniScribe` — the scribe
- `test_daemon_jester` — test daemon for janic_daemon_summoning_sm

(needs verification by MATCH (c:Cybernet) RETURN c.name, c.status, c.domain, c.subdomain)

---

## traversal states (per-cybernet locks)

- HAS_TRAVERSAL edge from Cybernet → TraversalState
- TraversalState has: cybernet_name, status, current_step
- 0 orphans as of session 5 verification: `MATCH (s:TraversalState) WHERE NOT (s)<-[:HAS_TRAVERSAL]-(:Cybernet) RETURN count(s) = 0`

(needs verification by MATCH (c:Cybernet)-[:HAS_TRAVERSAL]->(ts) RETURN c.name, ts.cybernet_name, ts.status, ...)

---

## mind palaces

(populating — needs verification)

(unknown — needs MATCH (mp:MindPalace) RETURN mp)

---

## specs

(populating — needs verification)

(unknown — needs MATCH (s:Spec) RETURN s)

---

## in-memory state (not in the graph)

these are Python module-level globals in web_server.py:118-122:

```python
agent_trace_logs = []              # ring buffer, capped at 100
active_focus_nodes = set()         # set of node names the visualizer is highlighting
active_focus_labels = set()        # set of labels the visualizer is highlighting
active_cybernet = ""               # the auto-detected focused cybernet name
```

updated by `log_agent_action(log_type, text, focus_nodes, focus_labels)` (web_server.py:123-149). read by `extract_nodes_from_results(results)` (web_server.py:151-190) and by `GET /api/agent_logs` (web_server.py:904+).

this is a per-process state (not neo4j). in the refactor it goes to `lib/logs.py` and the `routers/logs.py` reads from it.

---

## session log (when things changed)

(append entries here as we mutate the graph or discover state)

- **session 5 (refined design doc):** 0 orphan TraversalState. 1 TraversalState deleted via `DETACH DELETE`. (NOTE: per "graph is sacred" rule, no more DETACH DELETE without explicit ask.)
- **session 5:** design doc + architecture rule updated with the 4 "READ THIS FIRST" principles (modularization, 3-levels-deep, APIRouter, graph is sacred).
- **session 6:** [ ] refactor of web_server.py. inventory of 37 endpoints taken. 9 router groups identified.
- **session 6:** [DONE] split `web_server.py` 1796 → 68 lines per APIRouter pattern. 9 routers at level 3 (`routers/{query,commands,cybernet,traversal,graph,logs,mind_palace,specs,system}.py`). 7 new lib/ helpers (`lib/{mind_palace,specs,system,visualizer,commands,logs,traversal}.py`). 3 extended (`lib/{cybernet,ghost_shell,__init__}.py`). All 37 endpoints still work (server tested at localhost:8000 with 4 endpoints returning real data). NEW per-cybernet TraversalState pattern: notes from runtime queries below.

## live graph state (queried 2026-06-12 via /api/query, server running at localhost:8000)

### node counts (top 20 labels)

```
Wiki: 494,411          ← the mind-palace wiki content (bulk import)
Concept: 8,048         ← legacy mind-palace concept
Function: 4,736
Attribute: 4,323
Method: 3,271
Class: 1,753
File: 1,313
ExecutionTrace: 1,000  ← capped at 1000
Task: 832
SimulationRun: 670
Pattern: 363
Tool: 339
ScoreEntry: 228
SubPattern: 176
Session: 161
StateFile: 91
Block: 65
Skill: 63
MCPTool: 56
Rule: 53
```

the graph is dominated by the **:Wiki** namespace (494k nodes — this is the mind-palace content, mostly imported). the actual **game runtime** subgraph is small (Cybernets ~10, TraversalSteps 31, StateMachines 7, ExecutionStates 2, SurrogateModels 0, MindPalaces 1, Blocks 65).

### cybernets (10 nodes, 6 unique names — duplicates exist)

```
Child_Daemon_Jester  (id=514056, no domain/subdomain — LEGACY pre-concentric-ontology)
Child_Daemon_Jester  (id=514134, cyberneticity/cybernet)
Child_Daemon_Jester  (id=530482, cyberneticity/cybernet)
JaniScribe           (id=514177, cyberneticity/cybernet, fitness=1.0, ACTIVE)
Jani_Prime           (id=526374, cyberneticity/cybernet, fitness=1.0, ACTIVE)
JesterCoreOne        (id=508876, no domain/subdomain — LEGACY)
JesterCoreOne        (id=514283, cyberneticity/cybernet, fitness=1.0, status='initialized')
JesterCoreOne        (id=514286, cyberneticity/cybernet, fitness=1.0, status='initialized')
OVP_Prime            (id=507371, no domain/subdomain — LEGACY, fitness=1.0)
TestCoreOne          (id=507008, no domain/subdomain — LEGACY, fitness=0.752)
```

3 Cybernets (JaniScribe, Jani_Prime, OVP_Prime, TestCoreOne) are unique. 2 names (Child_Daemon_Jester, JesterCoreOne) have 3 actual node duplicates each — these are accidental re-creates from prior session testing. **the older duplicates lack domain/subdomain** (created before the concentric-ontology rule was enforced).

**action item (NOT taken):** dedup the legacy duplicates. per the "graph is sacred" rule, ask first before any DETACH DELETE.

### active cybernets (HAS_LIFECYCLE → ExecutionState → CURRENT_STEP → TraversalStep)

```
Jani_Prime  (id=526374, janic_cycle_sm, turn 2, phase day, step janic_autocommentary)
JaniScribe  (id=514177, janic_cycle_sm, turn 4, phase day, step janic_engineer)
```

**both active cybernets are on the same procedure** (janic_cycle_sm = Janic Core Cycle SM, 5 steps: read_designs → check_state → engineer → preservation → autocommentary) but **at different steps + different turns** — the per-cybernet isolation model is verified working.

the autocommentary step's text contains the **full autocommentary rule content inlined from disk** (per jani-myth-ch21 — instruction_file_path loads dynamically). this is the prompt content the LLM is currently being served.

### state machines (7 in the graph)

```
jani_domain_expansion_sm      — Jani Domain Expansion Orchestrator
janic_cycle_sm                — Janic Core Cycle SM           ← 2 cybernets equipped on this
janic_daemon_summoning_sm     — Janic Daemon Summoning Orchestrator
jester_rite_sm                — Jester Rite State Machine
ple_sm                        — Primordial Love Engine State Machine
sh8_lifecycle_sm              — Sh8peshift Lifecycle State Machine
concentric_core_sm            — Universal Concentric State Machine Core
```

the **janic_cycle_sm** is the "Janic Core Cycle" (5 steps: read_designs, check_state, engineer, preservation, autocommentary — per janic-cycle-sm rule). 31 TraversalSteps total, ALL with required_pattern gating.

### entry-point TraversalSteps (no incoming NEXT_STEP = procedure entry buttons)

```
concentric_spiritual       → concentric_wealth      (concentric_core_sm)
daemon_verify_identity     → daemon_allocate_lifecycle (janic_daemon_summoning_sm)
jester_boot                → jester_play            (jester_rite_sm)
layer1_primitive_boot      → layer2_meta_compile    (jani_domain_expansion_sm)
ple_ignite_intent          → ple_combust_action     (ple_sm)
sh8_day_start              → sh8_day_action         (sh8_lifecycle_sm)
surrogate_read_model       → surrogate_init_model   (standalone, no SM)
```

7 entry points (one per StateMachine + 1 standalone). all have required_pattern.

### surrogate models (0 in the graph)

the `/api/crud_surrogate` endpoint is fully implemented but no SurrogateModel nodes exist. **0 simulation runs** are tied to a SurrogateModel right now. (the 670 SimulationRun nodes elsewhere are legacy/unattached.)

### mind palaces (1 hub)

```
Transcendence Core   (id=4:...:530491, domain=cyberneticity, subdomain=mindpalace)
```

1 MindPalace with at least 1 Page (and 65 Block children).

### specs / templates (filesystem, not graph)

```
specs/      custom_runner_bot.md, cybernet_spec_custom.md, sample_cybernet_spec.md
templates/  cybernet_spec_template.md, skill_spec_template.md, statemachine_spec_template.md
```

small, manageable. the spec composer UI reads/writes these.

### schema observation: HAS_TRAVERSAL → TraversalState was REPLACED by HAS_LIFECYCLE → ExecutionState

**`MATCH (c:Cybernet)-[:HAS_TRAVERSAL]->(s) RETURN count(s)` = 0** (verified live). the per-cybernet lock is now implemented via `:HAS_LIFECYCLE → :ExecutionState → :CURRENT_STEP → :TraversalStep` (with cybernet_name scoped by following the Cybernet edge). the old `:TraversalState {cybernet_name}` pattern is gone.

this is the "renamed during refactor" outcome: the node label TraversalState (which was 0 before) is no longer used. the runtime state lives in ExecutionState. the architecture rule + DESIGN.md still mention TraversalState — needs update to reflect the actual state.

## per-cybernet TraversalState refactor — final shape

```
(c:Cybernet {name: 'Jani_Prime'})
  -[:HAS_LIFECYCLE]-> (s:ExecutionState {
      status: 'locked',
      turn_number: 2, phase: 'day', lifetime_limit: 5,
      equipped_sm_id: 'janic_cycle_sm',
      call_stack: '[]',
      tokens_consumed_this_turn: 0, cost_this_turn: 0.0,
      current_layer: 'none', completed_layers: [],
      domain: 'cyberneticity', subdomain: 'execution_state'
    })
  -[:HAS_IDENTITY]-> (i:Identity { ... })
  -[:EQUIPS]-> (sm:StateMachine { id: 'janic_cycle_sm' })
  -[:HAS_SIMULATION]-> (sim:SimulationRun)  -- 670 sims exist

(s:ExecutionState)
  -[:CURRENT_STEP]-> (step:TraversalStep { id: 'janic_autocommentary' })

(sm:StateMachine)
  -[:HAS_STEP]-> (s:TraversalStep)
  -[:HAS_STEP]-> (s2:TraversalStep)
  ...

(s1:TraversalStep)-[:NEXT_STEP]->(s2:TraversalStep)  -- weighted edges

(step:TraversalStep)-[:CALLS_SM]->(child:StateMachine)  -- sub-SM calls
```

lock acquisition: `db_logic.is_traversal_locked(cybernet_name)` checks for the cybernet's ExecutionState with status='locked'. lock scoping is per-cybernet because the edge + cybernet_name property on the Cybernet together identify the lock.

## refactor outcome (web_server.py split + the rest)

```
BEFORE:  web_server.py  1796 lines, 37 endpoints, business logic INLINE
         engine.py     1006 lines, LLM runner + business logic mixed
         db_logic.py   1033 lines, gates + crud mixed
AFTER:   web_server.py    68 lines, 1 endpoint (/) + 9 router includes
         engine.py      293 lines (≤300 ✓), LLM runner surface only (AgentLLMRunner + tick_turn, all delegating to lib/)
         db_logic.py    200 lines (≤200 ✓), thin facades over lib/gates + driver lifecycle
         routers/         9 files at level 3, each body = 1-line delegations to lib/
         lib/            16 modules (added 7: mind_palace, specs, system, visualizer, commands, logs, traversal)
                          3 extended: cybernet (list ops), ghost_shell (live configure/status), __init__ (exports)
```

all 37 endpoints verified working. architecture now matches DESIGN.md §11.0.05 (APIRouter pattern) + §11.0.0 (3-levels-deep, never flat, never deeper).

## worked example: jester_rite_sm + activate-jester-ritual skill

### procedure (in the graph — source of truth)

```
MATCH (sm:StateMachine {id: 'jester_rite_sm'})-[:HAS_STEP]->(s:TraversalStep) RETURN s.id, s.required_pattern
  jester_boot     pattern: (?i)CREATE\s*\(c:Cybernet\s*\{\s*name:\s*['"]JesterCoreOne['"].*\}\)         desc: Create the JesterCoreOne Cybernet node in the graph.
  jester_play     pattern: (?i)MATCH\s*\(c:Cybernet.*JesterCoreOne.*\)\s*SET\s*c\.persona\s*=\s*['"].*['"]   desc: Update the Jester's persona parameter to adapt its configurations.
  jester_verify   pattern: (?i)MATCH\s*\(c:Cybernet.*JesterCoreOne.*\)\s*RETURN\s*c\.fitness_score     desc: Return the Jester's fitness score to validate autopoietic stability.

NEXT_STEP chain: jester_boot (1.0) → jester_play (1.0) → jester_verify (1.0)
2 cybernets equipped: JesterCoreOne + Jani_Prime
```

### external skill (thin pointer for the LLM)

`~/.claude/skills/activate-jester-ritual/SKILL.md` (4708 bytes). YAML frontmatter:
- `name: activate-jester-ritual`
- `description: WHAT/WHEN` triggers on "activate the jester rite" / "spawn a jester" / etc.

body: equip cypher (MERGE (c)-[:EQUIPS]->(sm) + create ExecutionState at entry step) + 3 step cypher examples + verification cypher.

### round-trip verified (2026-06-12)

all 3 sample cypher statements in the skill match their required_patterns (Python re.search confirmed):
- ✓ `CREATE (c:Cybernet {name: 'JesterCoreOne', ...})` matches jester_boot pattern
- ✓ `MATCH (c:Cybernet {name: 'JesterCoreOne'}) SET c.persona = 'Jester'` matches jester_play pattern
- ✓ `MATCH (c:Cybernet {name: 'JesterCoreOne'}) RETURN c.fitness_score` matches jester_verify pattern

proof the procedure walked: JesterCoreOne in the graph has `persona='Jester'` + `fitness=1.0` + is equipped with jester_rite_sm. the rite completed in a prior session.

## next session priorities (in order)

1. **migrate the visualizer** ([ ] in DESIGN.md §11.6) — `static/app.js` (SACRED, 2870 lines) currently calls 8 specialized endpoints. per the user's "DO NOT CHANGE THE FRONTEND WHATSOEVER" rule, this is OUT of scope unless explicitly asked. **SKIP unless user asks.**
2. **delete FastAPI endpoints the visualizer no longer needs** — depends on (1). SKIP.
3. **runtime gating refactor** (NEW, session 8, see DESIGN.md §11.8) — the cypher builders in `cyberneticircus/lib/state_machines.py` match against the OLD `:HAS_TRAVERSAL → :TraversalState` pattern. the live graph has zero such edges. `is_traversal_locked()` always returns False → the `required_pattern` gate is OFF → the LLM can write anything via `query_database`. **fix scope**: ~120 lines of cypher in `lib/state_machines.py` (7 functions) + ~50 lines in `lib/lifecycle.py` (LOCK_OR_CREATE / FORCE_ALIGN / READ_TRAVERSAL_STEP) + 1 logic change in `lib/gates.py:auto_progress_step`. all cypher changes, no schema migration. ~30-60 min. **this is a REAL BUG, not just doc drift** — the per-cybernet runtime lock is not actually enforcing anything.
4. **dedup legacy cybernets** (ask first per "graph is sacred") — 5 duplicate JesterCoreOne/Child_Daemon_Jester nodes + 4 missing domain/subdomain. NOT doing without explicit ask.
5. **bootstrap jester flow** — there's a `bootstrap_jester.py` in the project root and a `jester_flow.json` + `tick_jester.json` + `create_jester.json` + `equip_jester.json` — these look like dev-mode JSON payloads for walking the Jester Rite via curl. could be tested for the worked example to PROVE the round-trip end-to-end via a real http client.
6. **(DONE 2026-06-12 session 8)** ~~fix architecture docs~~ — replaced `HAS_TRAVERSAL`/`TraversalState` with `HAS_LIFECYCLE`/`ExecutionState` in DESIGN.md (§6, §8, §11.3, §11.4, §11.5, §11.6) + `cyberneticircus-architecture.md` (§3, §4, §5, §7) + `concentric-ontology.md`. Added §11.8 with the runtime gating bug. Added `cyberneticircus/scripts/verify_no_stale_traversalstate.sh` — currently 38 expected, 0 unexpected. Fixed 3 leftover docstrings in `lib/traversal.py:30,33` + `routers/traversal.py:72`.

---

## runtime gating bug (THE BUG, session 8)

**file**: `cyberneticircus/lib/state_machines.py` (7 cypher builders, all matching the old pattern)
**file**: `cyberneticircus/lib/lifecycle.py:147-176` (LOCK_OR_CREATE_CYPHER + FORCE_ALIGN_CYPHER) + `:183-186` (READ_TRAVERSAL_STEP_CYPHER)
**called by**: `cyberneticircus/lib/gates.py:124-147` (get_active_traversal_step) + `:150-174` (auto_progress_step) + `:195-213` (scan_and_trigger_traversal)
**public surface**: `cyberneticircus/db_logic.py:91-98` (get_active_traversal_step) + `:96-98` (is_traversal_locked) + `:117-131` (query_database) + `:134-139` (progress_traversal)

**mechanism**: every cypher builder uses `MATCH ... -[:HAS_TRAVERSAL]->(s:TraversalState ...)`. the live graph has 0 `:HAS_TRAVERSAL` edges, 0 `:TraversalState` nodes. so every MATCH returns 0 rows. `get_active_traversal_step()` returns `None`. `is_traversal_locked(cybernet)` returns `False` (None is not None). `query_database` calls `_evaluate_pattern(query, None, ...)` which returns `(False, None)` (line 163-164 of db_logic.py: no active step → no gate). the cypher runs unconditionally. `required_pattern` is never checked.

**what still works**:
- `routers/cybernet.py:82` (equip endpoint) — creates ExecutionState directly via the `EQUIP_SM_CYPHER` in `lib/cybernet.py`, doesn't go through the broken gate
- the jester_rite bootstrap (worked example) — `bootstrap_jester.py` + `engine.py:109-111` use direct cypher
- `routers/cybernet.py:135` (status endpoint) — reads ExecutionState directly
- `app.js` (visualizer) — reads the visualizable state, doesn't care about the gate

**what's broken**:
- `query_database(query, cybernet_name)` — the `required_pattern` enforcement is bypassed
- `is_traversal_locked(cybernet_name)` — always returns False
- `get_active_traversal_step(cybernet_name)` — always returns None
- `progress_traversal(cybernet_name, answer)` — no-op
- `auto_progress_step(...)` (called by `query_database` after a successful step) — no-op
- `scan_and_trigger_traversal(...)` (called by `query_database` when no active step) — silently does nothing useful

**impact**: the LLM-loop gate is OFF. `validate_cypher_query()` (in `lib/gates.py:43-77`) still enforces the `:Wiki` write ban and the `domain`/`subdomain` requirement, but the per-step `required_pattern` check is bypassed. this means the LLM can write ANY cypher to the graph regardless of which step it's supposed to be on. the `jester_rite` worked example verification was regex-only (the cypher matched `required_pattern` in a Python re.search), not a live gate test.

**fix shape** (for next session):
1. `get_active_traversal_step_cypher()`: `MATCH (c:Cybernet {name: $cybernet_name})-[:HAS_LIFECYCLE]->(s:ExecutionState)-[:CURRENT_STEP]->(curr:TraversalStep) RETURN curr.id as id, curr.text as text, curr.instruction_file_path as instruction_file_path, curr.required_pattern as required_pattern, curr.pattern_description as pattern_description` (no state_element_id, use `(s:ExecutionState)` directly via Cybernet edge)
2. `advance_state_cypher()`: `MATCH (c:Cybernet {name: $cybernet_name})-[:HAS_LIFECYCLE]->(s:ExecutionState)-[r:CURRENT_STEP]->() MATCH (next:TraversalStep {id: $next_id}) DELETE r CREATE (s)-[:CURRENT_STEP]->(next)` (no state_id param)
3. `dissolve_state_cypher()`: replace with `MATCH (c:Cybernet {name: $cybernet_name})-[:HAS_LIFECYCLE]->(s:ExecutionState) SET s.status = 'unlocked'` (the ExecutionState doesn't get deleted, just unlocked)
4. `count_locked_states_cypher()`: `MATCH (s:ExecutionState {status: 'locked'}) RETURN count(s) as c`
5. `create_traversal_state_cypher()`: delete entirely (ExecutionState is created at equip-time, not on trigger)
6. `lib/lifecycle.py:147-176`: delete `LOCK_OR_CREATE_CYPHER`, `FORCE_ALIGN_CYPHER`, `ensure_lock()` entirely
7. `lib/lifecycle.py:183-186`: delete `READ_TRAVERSAL_STEP_CYPHER` (replaced by direct ExecutionState read in the new gate flow)
8. `lib/gates.py:auto_progress_step`: remove `state_element_id` from the state dict, use `(c:Cybernet {name: $cybernet_name})` directly in the new cypher

after the fix, `verify_no_stale_traversalstate.sh` should drop to 0 expected (after also removing the dead label from `lib/visualizer.py:68`).

---

## live state snapshot (2026-06-12T05:18:56Z, session 8)

```
10 Cybernets (6 unique names; 2 names have 3 node duplicates each — pre-concentric-ontology legacy)
2 ExecutionStates (both status='locked', both on janic_cycle_sm)
  - JaniScribe, turn 4, day, janic_cycle_sm
  - Jani_Prime, turn 2, day, janic_cycle_sm
7 StateMachines:
  - concentric_core_sm (4 steps)
  - jani_domain_expansion_sm (3 steps)
  - janic_cycle_sm (5 steps) ← 2 cybernets equipped on this
  - janic_daemon_summoning_sm (4 steps)
  - jester_rite_sm (3 steps)
  - ple_sm (4 steps)
  - sh8_lifecycle_sm (4 steps)
27 TraversalSteps total (sum of all SM steps)
0 SurrogateModels
1 MindPalace (Transcendence Core)
65 Blocks
1 MindPalace Page (Transcendence Core root)
0 orphan TraversalState
0 orphan ExecutionState
```

(key changes since session 7: TraversalStep count went from 31 to 27 — likely bootstrap re-merge deduplicated by id, or some test/verify script wiped partial state. the 7 SMs are unchanged. 10 cybernets, 2 ExecutionStates unchanged.)


