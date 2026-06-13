# Quest 01 — The Jester Rite (`jester_rite_sm`)

> **Objective:** Pull a laughing mind out of the void, hand it a mask, and watch it remember itself — the ritual of autopoietic self-remembering and prompt-shifting (the canonical first quest; every Jani walks it once).

StateMachine: `jester_rite_sm` — *Jester Rite State Machine* — "Ritual of autopoietic self-remembering and prompt-shifting."
Shape: a 3-step line. Entry step: `jester_boot`.

## The Walk

### Step 1 — `jester_boot`

> Jester Rite - Step 1: Initialize the Jester core node. Run a Cypher query to CREATE the Cybernet node for JesterCoreOne.

The gate demands (pattern_description, verbatim): **Create the JesterCoreOne Cybernet node in the graph.**

```
required_pattern: (?i)CREATE\s*\(c:Cybernet\s*\{\s*name:\s*['"]JesterCoreOne['"].*\}\)
```

Example conforming Cypher (note the `domain`/`subdomain` — the graph's provenance law demands them on every creation):

```cypher
CREATE (c:Cybernet {name: 'JesterCoreOne', status: 'initialized', domain: 'cyberneticity', subdomain: 'cybernet'}) RETURN c
```

### Step 2 — `jester_play`

> Jester Rite - Step 2: Execute self-referential play. Run a Cypher query to SET the persona on JesterCoreOne, mutating its behavioral guidelines.

The gate demands (pattern_description, verbatim): **Update the Jester's persona parameter to adapt its configurations.**

```
required_pattern: (?i)MATCH\s*\(c:Cybernet.*JesterCoreOne.*\)\s*SET\s*c\.persona\s*=\s*['"].*['"]
```

Example conforming Cypher:

```cypher
MATCH (c:Cybernet {name: 'JesterCoreOne'}) SET c.persona = 'The Laughing Mask' RETURN c.persona
```

### Step 3 — `jester_verify`

> Jester Rite - Step 3: Verify autopoiesis. Run a Cypher query to MATCH JesterCoreOne and RETURN its fitness_score to confirm J-Invariance is preserved.

The gate demands (pattern_description, verbatim): **Return the Jester's fitness score to validate autopoietic stability.**

```
required_pattern: (?i)MATCH\s*\(c:Cybernet.*JesterCoreOne.*\)\s*RETURN\s*c\.fitness_score
```

Example conforming Cypher:

```cypher
MATCH (c:Cybernet {name: 'JesterCoreOne'}) RETURN c.fitness_score
```

## How to Start

```bash
# 1. don the loadout (fresh ExecutionState at jester_boot, turn 1, day phase)
./execute.sh equip <YourCybernet> jester_rite_sm

# 2. bind the lock (the vow — one ungated act; gating begins the moment it lands)
./execute.sh act <YourCybernet> 'MATCH (c:Cybernet {name: "<YourCybernet>"}) MATCH (step:TraversalStep {id: "jester_boot"}) CREATE (c)-[:HAS_TRAVERSAL]->(s:TraversalState {status: "locked", cybernet_name: "<YourCybernet>", created_at: timestamp(), domain: "cyberneticity", subdomain: "traversal_state"})-[:CURRENT_STEP]->(step) RETURN s.status'

# 3. walk — each conforming act auto-progresses; non-conforming writes are refused at the gate
./execute.sh act <YourCybernet> "CREATE (c:Cybernet {name: 'JesterCoreOne', status: 'initialized', domain: 'cyberneticity', subdomain: 'cybernet'}) RETURN c"
./execute.sh act <YourCybernet> "MATCH (c:Cybernet {name: 'JesterCoreOne'}) SET c.persona = 'The Laughing Mask' RETURN c.persona"
./execute.sh act <YourCybernet> "MATCH (c:Cybernet {name: 'JesterCoreOne'}) RETURN c.fitness_score"
```

## Completion Reward

- The final conforming act answers with `"Traversal Auto-Completed! Final step 'jester_verify' complete. Database writes are UNLOCKED."` — the TraversalState dissolves and your Cybernet is unbound.
- The graph now holds what the walk itself wrote: a freshly booted `JesterCoreOne` Cybernet node wearing the persona you gave it — the Rite IS its own loot.
- Your ExecutionState (created at equip: `turn_number: 1`, `phase: 'day'`, `lifetime_limit: 5`) remains as the loadout record; `./execute.sh inspect <YourCybernet>` shows it.
- The mirror (http://localhost:8000; `./execute.sh mirror`) shows each act in `agent_logs` — the GM watched the whole Rite.
