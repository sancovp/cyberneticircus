---
name: arena
description: The Arena district — where performance becomes record. SimulationRuns, ScoreEntries (fitness/xp/level ledger), the ExecutionTrace chain, and ExecutionStates. Note — no SurrogateModel nodes exist in the live graph yet; the forge endpoint exists, the forge is cold.
---

# The Arena

The proving ground. Beings come here to be measured: simulation runs accumulate, scores get carved against Missions and Sessions, and every Cypher a traversal ever executed is chained into the trace record. The Arena is where fitness stops being a number on a shell and becomes history.

## What this district holds (verified against the live graph, 2026-06-12)

| Label / structure | Count | Notes |
|---|---|---|
| `SimulationRun` | 670 | props: `run_id`, `accuracy`, `fitness_score`, `calibrated`, `created_at`; 500 belong to Jani_Prime via `(:Cybernet)-[:HAS_SIMULATION]->` |
| `ScoreEntry` | 228 | props: `fitness`, `xp`, `level`, `raw_score`, `type`, `computation_trace`; each points `-[:SCORED]->` at a `Mission` (67) or `Session` (161) |
| `ExecutionTrace` | 1000 | a single `NEXT_TRACE` linked chain, phase 0 → phase 999 — the Weights-of-Time-grade action record |
| `ExecutionState` | 3 | lifecycle anchors, attached to Cybernets via `HAS_LIFECYCLE` |
| `SurrogateModel` | **0** | **truth over lore**: the `surrogate_read_model` command and the `POST /api/crud_surrogate` endpoint both reference SurrogateModels, but zero such nodes exist today. The first player to forge one writes Arena history. |

## Example queries (each verified working via `POST /api/query`)

The leaderboard — average fitness and accuracy per being across all its runs:

```bash
./execute.sh act 'MATCH (c:Cybernet)-[:HAS_SIMULATION]->(s:SimulationRun) RETURN c.name AS cybernet, count(s) AS runs, round(avg(s.fitness_score),3) AS avg_fitness, round(avg(s.accuracy),3) AS avg_accuracy ORDER BY avg_fitness DESC'
```

The scoreboard — what has been SCORED, and what it earned (xp can run negative; the Arena keeps honest books):

```bash
./execute.sh act 'MATCH (s:ScoreEntry)-[:SCORED]->(target) RETURN labels(target)[0] AS scored_thing, count(*) AS entries, round(avg(s.fitness),3) AS avg_fitness, sum(s.xp) AS total_xp'
```

Walk the trace chain — head to tail, the world's longest single record:

```bash
./execute.sh act 'MATCH (head:ExecutionTrace) WHERE NOT (:ExecutionTrace)-[:NEXT_TRACE]->(head) MATCH p = (head)-[:NEXT_TRACE*0..]->(last) WHERE NOT (last)-[:NEXT_TRACE]->() RETURN head.action AS first_action, last.action AS last_action, length(p)+1 AS chain_length'
```

## Game activities here

- **Run the gauntlet** — the turn engine `POST /api/tick` is **BROKEN today** (verified 2026-06-12: any body returns `500`; see the GM CLAUDE.md's Known Fractures) — until it is repaired, run the gauntlet by gate-walk (`equip`, then `act` the gated Cypher, then the GM advances `CURRENT_STEP`). When repaired, one tick advances an equipped Cybernet one turn through its StateMachine; runs and scores accrue, tokens burn into `accumulated_cost` (the Arena is the economy's furnace).
- **Read a fighter's record** — `GET /api/simulations/{name}` lists a Cybernet's runs with accuracy per `run_id`.
- **Forge the first surrogate** — `POST /api/crud_surrogate` is live and unused; the `surrogate_read_model` quest line (visible in `GET /api/commands`) begins by checking whether a SurrogateModel exists for domain `agent_memory` / subdomain `traversal`. Today the answer is no. That is an open quest.
