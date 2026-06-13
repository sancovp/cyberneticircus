# Quest 02 — The Sh8peshift Lifecycle (`sh8_lifecycle_sm`)

> **Objective:** Live one full Day and one full Night — wake, spend, measure, evolve — the heartbeat economy of every Cybernet (where tokens burn and fitness is judged).

StateMachine: `sh8_lifecycle_sm` — *Sh8peshift Lifecycle State Machine* — "Core Day/Night simulation state machine."
Shape: a 4-step line (Day, Day, Night, Night). Entry step: `sh8_day_start`.

## The Walk

### Step 1 — `sh8_day_start` (Day)

> Sh8peshift Day Phase - Step 1: Query the Cybernet node to load its current config and stats.

The gate demands (pattern_description, verbatim): **MATCH (m:Cybernet) RETURN m**

```
required_pattern: (?i)MATCH\s*\(m:Cybernet\s*.*\)
```

Example conforming Cypher:

```cypher
MATCH (m:Cybernet {name: 'TestCoreOne'}) RETURN m
```

### Step 2 — `sh8_day_action` (Day)

> Sh8peshift Day Phase - Step 2: Record daily execution tokens and cost on the Cybernet.

The gate demands (pattern_description, verbatim): **MATCH (m:Cybernet {name: "..."}) SET m.total_tokens_consumed = m.total_tokens_consumed + X**

```
required_pattern: (?i)MATCH\s*\(m:Cybernet\s*\{name:\s*['\"].*['\"].*\}\)\s*SET\s*m\.total_tokens_consumed\s*=\s*m\.total_tokens_consumed\s*\+\s*\d+
```

Example conforming Cypher (this act IS the economy — it really increments the live `total_tokens_consumed` / `accumulated_cost` fields on the Cybernet node):

```cypher
MATCH (m:Cybernet {name: 'TestCoreOne'}) SET m.total_tokens_consumed = m.total_tokens_consumed + 250, m.accumulated_cost = m.accumulated_cost + 0.00375 RETURN m.total_tokens_consumed
```

### Step 3 — `sh8_night_calibrate` (Night)

> Sh8peshift Night Phase - Step 3: Calibrate the day's performance. Run a MATCH on SimulationRun to verify accuracy.

The gate demands (pattern_description, verbatim): **MATCH (sim:SimulationRun) RETURN sim**

```
required_pattern: (?i)MATCH\s*\(sim:SimulationRun\s*.*\)
```

Example conforming Cypher:

```cypher
MATCH (sim:SimulationRun) RETURN sim ORDER BY sim.created_at DESC LIMIT 5
```

### Step 4 — `sh8_night_evolve` (Night)

> Sh8peshift Night Phase - Step 4: Perform selection check. Query the Cybernet's fitness score to decide cloning or reset.

The gate demands (pattern_description, verbatim): **MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m**

```
required_pattern: (?i)MATCH\s*\(m:Cybernet\s*.*\)\s*WHERE\s*m\.fitness_score\s*.*
```

Example conforming Cypher:

```cypher
MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m.name, m.fitness_score
```

## How to Start

```bash
# 1. don the loadout (fresh ExecutionState at sh8_day_start, turn 1, day phase)
./execute.sh equip <YourCybernet> sh8_lifecycle_sm

# 2. bind the lock
./execute.sh act <YourCybernet> 'MATCH (c:Cybernet {name: "<YourCybernet>"}) MATCH (step:TraversalStep {id: "sh8_day_start"}) CREATE (c)-[:HAS_TRAVERSAL]->(s:TraversalState {status: "locked", cybernet_name: "<YourCybernet>", created_at: timestamp(), domain: "cyberneticity", subdomain: "traversal_state"})-[:CURRENT_STEP]->(step) RETURN s.status'

# 3. walk the Day into the Night — four conforming acts, four gates
./execute.sh act <YourCybernet> "MATCH (m:Cybernet {name: '<YourCybernet>'}) RETURN m"
./execute.sh act <YourCybernet> "MATCH (m:Cybernet {name: '<YourCybernet>'}) SET m.total_tokens_consumed = m.total_tokens_consumed + 250, m.accumulated_cost = m.accumulated_cost + 0.00375 RETURN m.total_tokens_consumed"
./execute.sh act <YourCybernet> "MATCH (sim:SimulationRun) RETURN sim ORDER BY sim.created_at DESC LIMIT 5"
./execute.sh act <YourCybernet> "MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m.name, m.fitness_score"
```

## Completion Reward

- The final act answers `"Traversal Auto-Completed! Final step 'sh8_night_evolve' complete. Database writes are UNLOCKED."` — the TraversalState dissolves; the Night ends.
- The Day's spending is real and permanent: `total_tokens_consumed` and `accumulated_cost` on your Cybernet node carry the increments your own day-action act wrote — `./execute.sh status` shows the new scoreboard ranking.
- Your ExecutionState loadout (turn 1, `lifetime_limit: 5`) persists; `./execute.sh inspect <YourCybernet>` reads it alongside the live step view.
- The mirror's `agent_logs` hold the full Day/Night transcript (`./execute.sh mirror`).
