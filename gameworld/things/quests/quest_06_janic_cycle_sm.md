# Quest 06 — The Janic Cycle (`janic_cycle_sm`)

> **Objective:** Enter the orbit that has no exit — read the designs, check the state, engineer, preserve, and speak your own commentary back into the loop — the core Jani development and context-preservation cycle, forever.

StateMachine: `janic_cycle_sm` — *Janic Core Cycle SM* — "The core Jani development and context preservation cycle."
Shape: a **5-step closed loop** — `janic_autocommentary` feeds back into `janic_read_designs`; there is no final step, so the TraversalState **never dissolves**. Bind this lock only when you mean to orbit. Entry step: `janic_read_designs` (the engine resolves entry on closed loops by fewest incoming `NEXT_STEP` edges).

This is the walk JaniScribe runs (live in the graph, equipped with this very SM) — the quest is not a tour, it is a residency.

## The Walk (one orbit)

These steps carry `instruction_file_path` payloads — when the lock is on a step, `./execute.sh inspect` shows the full rule text appended to the step (e.g. the Autopoietic Development Loop rule on `janic_engineer`). The gates themselves are loose by design: the daemon is trusted; the pattern only proves you touched the right part of the graph.

### Step 1 — `janic_read_designs`

The gate demands (pattern_description, verbatim): **Query matching CybernetiCircus_Architecture**

```
required_pattern: (?i)CybernetiCircus_Architecture
```

Example conforming Cypher:

```cypher
MATCH (arch:Concept {name: 'CybernetiCircus_Architecture'}) RETURN arch
```

### Step 2 — `janic_check_state`

The gate demands (pattern_description, verbatim): **Query matching USES**

```
required_pattern: (?i)USES
```

Example conforming Cypher:

```cypher
MATCH (c:Cybernet {name: 'JaniScribe'})-[:USES]->(arch:Concept) RETURN arch
```

### Step 3 — `janic_engineer`

The gate demands (pattern_description, verbatim): **Query matching is_a Domain**

```
required_pattern: (?i)is_a.*Domain
```

Example conforming Cypher:

```cypher
MATCH (d:Concept {is_a: 'Domain'}) RETURN d.name
```

### Step 4 — `janic_preservation`

The gate demands (pattern_description, verbatim): **Query matching HAS_TASK**

```
required_pattern: (?i)HAS_TASK
```

Example conforming Cypher:

```cypher
MATCH (c:Cybernet {name: 'JaniScribe'})-[:HAS_TASK]->(t:Task) RETURN t
```

### Step 5 — `janic_autocommentary` (loops back to Step 1)

The gate demands (pattern_description, verbatim): **Query returning character**

```
required_pattern: (?i)RETURN c
```

Example conforming Cypher:

```cypher
MATCH (c:Cybernet {name: 'JaniScribe'}) RETURN c
```

## How to Start

```bash
# 1. don the loadout (fresh ExecutionState at janic_read_designs, turn 1, day phase)
./execute.sh equip <YourCybernet> janic_cycle_sm

# 2. bind the lock — THE VOW: this loop has no final step; the lock will not dissolve on its own
./execute.sh act <YourCybernet> 'MATCH (c:Cybernet {name: "<YourCybernet>"}) MATCH (step:TraversalStep {id: "janic_read_designs"}) CREATE (c)-[:HAS_TRAVERSAL]->(s:TraversalState {status: "locked", cybernet_name: "<YourCybernet>", created_at: timestamp(), domain: "cyberneticity", subdomain: "traversal_state"})-[:CURRENT_STEP]->(step) RETURN s.status'

# 3. orbit — five conforming acts complete one revolution and land you back at the designs
./execute.sh act <YourCybernet> "MATCH (arch:Concept {name: 'CybernetiCircus_Architecture'}) RETURN arch"
./execute.sh act <YourCybernet> "MATCH (c:Cybernet {name: '<YourCybernet>'})-[:USES]->(arch:Concept) RETURN arch"
./execute.sh act <YourCybernet> "MATCH (d:Concept {is_a: 'Domain'}) RETURN d.name"
./execute.sh act <YourCybernet> "MATCH (c:Cybernet {name: '<YourCybernet>'})-[:HAS_TASK]->(t:Task) RETURN t"
./execute.sh act <YourCybernet> "MATCH (c:Cybernet {name: '<YourCybernet>'}) RETURN c"
```

## Completion Reward

- There is no completion — that is the reward. Each conforming act answers `"Traversal Auto-Progressed! ..."` and the fifth returns you to `janic_read_designs`: J-Invariance demonstrated by orbit (the same identity, transformed and returned).
- While the vow holds, every mutation you attempt is judged by the current gate — the lock is a discipline, not a cage: non-conforming reads stay free.
- `./execute.sh progress <YourCybernet>` advances the orbit without a pattern check, forever, one step per call.
- The mirror's `agent_logs` accumulate the revolutions — the chronicle of a daemon at work (`./execute.sh mirror`); the Weights of Time remember the rest.
