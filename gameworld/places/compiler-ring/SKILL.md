---
name: compiler-ring
description: The Compiler Ring district — where the Cyberneticity's procedures live as StateMachines and regex-gated TraversalSteps. Study here when you want to read, walk, or pass the gates of any quest line (the Jester Rite included).
---

# The Compiler Ring

The district of executable law. Every procedure in the Cyberneticity — every quest, rite, and lifecycle — is compiled here into a StateMachine whose steps are TraversalSteps, and every step carries a `required_pattern` (a regex gate; your Cypher must match it to pass).

## What this district holds (verified against the live graph, 2026-06-12)

| Label / structure | Count | Notes |
|---|---|---|
| `StateMachine` | 6 | Jester Rite, Sh8peshift Lifecycle, Universal Concentric Core, Janic Core Cycle, Janic Daemon Summoning Orchestrator, Jani Domain Expansion Orchestrator |
| `TraversalStep` | 27 | **all 27** carry a `required_pattern` gate; 23 hang directly off a machine via `HAS_STEP`, 4 are chain-interior (reachable only via `NEXT_STEP`) |
| `(:StateMachine)-[:HAS_STEP]->(:TraversalStep)` | 23 edges | machine → its steps |
| `(:TraversalStep)-[:NEXT_STEP]->(:TraversalStep)` | 21 edges | the quest lines |
| `(:TraversalStep)-[:CALLS_SM]->(:StateMachine)` | 1 edge | `daemon_equip_core` → Universal Concentric State Machine Core (one machine summons another) |

## Example queries (each verified working via `POST /api/query`)

Census of every machine and its step count:

```bash
./execute.sh act 'MATCH (sm:StateMachine) OPTIONAL MATCH (sm)-[:HAS_STEP]->(t:TraversalStep) RETURN sm.name AS machine, sm.description AS purpose, count(t) AS steps ORDER BY steps DESC'
```

Walk the Jester Rite quest line — entry step first, gates exposed (swap the machine name to walk any other line):

```bash
./execute.sh act 'MATCH (sm:StateMachine {name: "Jester Rite State Machine"})-[:HAS_STEP]->(entry:TraversalStep) WHERE NOT (:TraversalStep)-[:NEXT_STEP]->(entry) MATCH p = (entry)-[:NEXT_STEP*0..]->(step) RETURN step.id AS step, step.required_pattern AS gate ORDER BY length(p)'
```

(Returns the canonical three: `jester_boot` → `jester_play` → `jester_verify`, each with its regex gate — CREATE the Cybernet, SET its persona, RETURN its `fitness_score`.)

Find where one machine summons another:

```bash
./execute.sh act 'MATCH (t:TraversalStep)-[:CALLS_SM]->(sm:StateMachine) RETURN t.id AS step, sm.name AS calls'
```

Raw-API equivalent of any `act` (the wrapper is `POST /api/query`):

```bash
curl -s -X POST http://localhost:8000/api/query -H 'Content-Type: application/json' \
  -d '{"query": "MATCH (sm:StateMachine) RETURN sm.name"}'
```

## Game activities here

- **Read the open gates** — `GET /api/commands` lists every currently-summonable entry step (e.g. `jester_boot`, `daemon_verify_identity`, `layer1_primitive_boot`) with its instruction text.
- **Equip a machine** — `POST /api/equip` with `{"character_name": "<cybernet>", "state_machine_id": "<sm_id>"}` (machine ids via `GET /api/state_machines`: `jester_rite_sm`, `janic_cycle_sm`, `sh8_lifecycle_sm`, ...) locks that Cybernet into the machine's traversal.
- **Pass a gate** — issue Cypher through `POST /api/query` with `"cybernet_name"` set; if your query matches the active step's `required_pattern`, the step auto-progresses and the result carries a `_state_machine_event`. This is action validation: the graph judges your spell. (Today's caveat, verified 2026-06-12: auto-progress and the pattern-gate bind to the old-style `HAS_TRAVERSAL` chain, while `equip` creates the new-style `HAS_LIFECYCLE` chain — so for a freshly-equipped being the GM advances `CURRENT_STEP` manually after your gated act; see the GM CLAUDE.md's gate-walk and Known Fractures.)
- **Force-advance** — `POST /api/traversal/progress` with `{"cybernet_name": ..., "answer": ...}` manually steps the traversal (the GM's override lever).
