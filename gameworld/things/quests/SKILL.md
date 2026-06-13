# SKILL: How Quests Work in the CybernetiCircus

Every quest in this directory is a real StateMachine living in the Cyberneticity (the Neo4j graph behind http://localhost:8000 — the graph IS the source of truth; these files are only the printed map). A quest is not a story you read; it is a walk you take — step by step, gate by gate — as a Cybernet.

Every pattern, message, and endpoint below was verified live against the running API before being written down.

## The Loop (equip -> bind -> gated acts -> auto-progress -> cycle close)

```
equip          POST /api/equip                {character_name, state_machine_id}
bind the lock  POST /api/query                (the TraversalState binding act — see below)
gated act      POST /api/query                {query, cybernet_name}
manual step    POST /api/traversal/progress   {cybernet_name}
watch          GET  /api/status/{name}, GET /api/agent_logs, the dashboard at http://localhost:8000
```

All of it is wrapped by the economy engine at `gameworld/execute.sh`:

```
./execute.sh quests                      # list every equippable StateMachine
./execute.sh equip <cybernet> <sm_id>    # don the quest loadout
./execute.sh act <cybernet> '<cypher>'   # act AS that cybernet (gated by its current step)
./execute.sh progress <cybernet>         # manually advance the walk one step
./execute.sh inspect <cybernet>          # loadout + ExecutionState view
./execute.sh mirror                      # dashboard URL + last 5 agent_logs entries
```

### 1. Equip (the loadout)

`equip` creates a **fresh ExecutionState** for that StateMachine (any prior ExecutionState for the same sm_id is replaced) with: `status: 'locked'`, `turn_number: 1`, `phase: 'day'`, `lifetime_limit: 5`, `tokens_consumed_this_turn: 0`, `cost_this_turn: 0.0`, `call_stack: '[]'`, and a `CURRENT_STEP` edge pointing at the SM's **entry step** (the step with the fewest incoming `NEXT_STEP` edges — this is how closed-loop SMs still get an entry).

### 2. Bind the lock (the vow)

The gate itself lives on a separate node — a **TraversalState** — and equip alone does not create it. You bind it with one act (ungated, because no lock exists yet for you):

```
./execute.sh act <cybernet> 'MATCH (c:Cybernet {name: "<cybernet>"}) MATCH (step:TraversalStep {id: "<entry_step_id>"}) CREATE (c)-[:HAS_TRAVERSAL]->(s:TraversalState {status: "locked", cybernet_name: "<cybernet>", created_at: timestamp(), domain: "cyberneticity", subdomain: "traversal_state"})-[:CURRENT_STEP]->(step) RETURN s.status'
```

Each quest file gives this command pre-filled with its own entry step. The lock is **per-cybernet** — `(c:Cybernet)-[:HAS_TRAVERSAL]->(s:TraversalState {status:'locked'})-[:CURRENT_STEP]->(step)` — so N concurrent Cybernets never block each other. One lock per Cybernet at a time; finish a walk before binding another.

### 3. Gated acts (the walk)

Every `act` (a `POST /api/query` carrying `cybernet_name`) is checked against the locked step's `required_pattern` (a regex stored verbatim on the TraversalStep node — the quest files copy them verbatim):

- **Conforming query** — it executes, and the walk **auto-progresses**: the response gains a trailing row of the form
  `{"_state_machine_event": "Traversal Auto-Progressed! Step '<id>' complete. Next step: '<id>' - <step text>"}`.
- **Non-conforming mutation** (CREATE/MERGE/SET/DELETE/REMOVE/DETACH) — **blocked before execution** with
  `PermissionError: Database Writes Locked: Active Traversal Step '<id>' requires query matching pattern: <pattern_description>` (the API surfaces this as an HTTP 500; the write never touches the graph — verified).
- **Non-conforming read** — executes normally, no progress (you may scout freely; only the conforming act moves you).

### 4. Auto-progress and the cycle close

When the conforming act lands on a step with no outgoing `NEXT_STEP`, the engine responds
`"Traversal Auto-Completed! Final step '<id>' complete. Database writes are UNLOCKED."`
and the TraversalState is **dissolved** (detach-deleted by the engine — the lock vanishes from the graph; verified live). Closed-loop SMs (the Janic Cycle) have no final step — their lock never dissolves; the walk orbits forever by design.

`./execute.sh progress <cybernet>` advances the same TraversalState **without** a pattern check (same `Traversal Auto-Progressed!` / `Auto-Completed!` messages) — the GM's skip-token for stuck players. With no lock bound it answers: `No active traversal state machine is currently locked for cybernet '<name>'. Database writes are fully unlocked for this cybernet.`

## Standing Laws of the Graph (enforced on every act)

1. **The :Wiki firewall** — write mutations touching the `:Wiki` label are rejected outright.
2. **Provenance on creation** — every `CREATE`/`MERGE` of a labeled node MUST carry both `domain` and `subdomain` properties. In the `cyberneticity` domain the allowed subdomains are: `cybernet, identity, execution_state, state_machine, traversal, traversal_state, simulation, mindpalace, page, block, task_list, task, skill`.

All example Cypher in the quest files satisfies both laws and was regex-verified against the live `required_pattern` of its step.

## The Mirror (what the GM sees)

- The visualizer at **http://localhost:8000** is the table view of the Cyberneticity.
- `GET /api/agent_logs` — every act lands here (`active_cybernet`, `active_step_id`, the running log). `./execute.sh mirror` prints the last 5.
- `GET /api/status/{name}` — the Cybernet sheet: equipped SM, `turn_number`, `phase`, the current step's text + verbatim `required_pattern`, and the economy fields (`total_tokens`, `accumulated_cost`, `fitness_score`).
- `GET /api/commands` — the live entry points of all anchored procedures (where the quests begin).

## The Quest Ledger

| # | file | sm_id | steps | shape |
|---|------|-------|-------|-------|
| 01 | quest_01_jester_rite_sm.md | jester_rite_sm | 3 | line (the canonical first quest) |
| 02 | quest_02_sh8_lifecycle_sm.md | sh8_lifecycle_sm | 4 | line (Day/Night) |
| 03 | quest_03_concentric_core_sm.md | concentric_core_sm | 4 | line (the four cores) |
| 04 | quest_04_janic_daemon_summoning_sm.md | janic_daemon_summoning_sm | 4 | line (summoning) |
| 05 | quest_05_jani_domain_expansion_sm.md | jani_domain_expansion_sm | 3 | line (the three layers) |
| 06 | quest_06_janic_cycle_sm.md | janic_cycle_sm | 5 | **closed loop** (the eternal orbit) |
