# Quest 03 — The Four Cores (`concentric_core_sm`)

> **Objective:** Pass through the four transcendental layers — Spiritual, Wealth, Social, Health — one orthogonal ring at a time, and come out the far side J-Invariant.

StateMachine: `concentric_core_sm` — *Universal Concentric State Machine Core* — "Orthogonally maps execution through the four transcendental layers (Spiritual, Wealth, Social, Health)."
Shape: a 4-step line. Entry step: `concentric_spiritual`.

## The Walk

### Step 1 — `concentric_spiritual`

> Spiritual Core - Ignite Intent. MATCH active Cybernet to load its subjective POV and intent parameters.

The gate demands (pattern_description, verbatim): **MATCH (m:Cybernet) RETURN m**

```
required_pattern: (?i)MATCH\s*\(m:Cybernet\s*.*\)
```

Example conforming Cypher:

```cypher
MATCH (m:Cybernet {name: 'TestCoreOne'}) RETURN m
```

### Step 2 — `concentric_wealth`

> Wealth Core - Combust Action. Run a SET query to update resources (total_tokens_consumed, accumulated_cost) on the Cybernet.

The gate demands (pattern_description, verbatim): **MATCH (m:Cybernet {name: "..."}) SET m.total_tokens_consumed = m.total_tokens_consumed + X**

```
required_pattern: (?i)MATCH\s*\(m:Cybernet\s*\{name:\s*['\"].*['\"].*\}\)\s*SET\s*m\.total_tokens_consumed\s*=\s*m\.total_tokens_consumed\s*\+\s*\d+
```

Example conforming Cypher (the Wealth Core combusts real resources — the increment lands on the live economy fields):

```cypher
MATCH (m:Cybernet {name: 'TestCoreOne'}) SET m.total_tokens_consumed = m.total_tokens_consumed + 180 RETURN m.total_tokens_consumed
```

### Step 3 — `concentric_social`

> Social Core - Align Collaboration. MATCH linked Identities or Concept relationships to verify social coherence.

The gate demands (pattern_description, verbatim): **MATCH (m:Cybernet {name: "..."})-[:HAS_IDENTITY]->(i:Identity) RETURN i**

```
required_pattern: (?i)MATCH\s*\(m:Cybernet\s*[^)]*\)-\[:HAS_IDENTITY\]->\(i:Identity\)
```

Example conforming Cypher:

```cypher
MATCH (m:Cybernet {name: 'TestCoreOne'})-[:HAS_IDENTITY]->(i:Identity) RETURN i
```

### Step 4 — `concentric_health`

> Health Core - Calibrate Calibration. MATCH to evaluate simulation accuracy and verify J-Invariance.

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
# 1. don the loadout (fresh ExecutionState at concentric_spiritual, turn 1, day phase)
./execute.sh equip <YourCybernet> concentric_core_sm

# 2. bind the lock
./execute.sh act <YourCybernet> 'MATCH (c:Cybernet {name: "<YourCybernet>"}) MATCH (step:TraversalStep {id: "concentric_spiritual"}) CREATE (c)-[:HAS_TRAVERSAL]->(s:TraversalState {status: "locked", cybernet_name: "<YourCybernet>", created_at: timestamp(), domain: "cyberneticity", subdomain: "traversal_state"})-[:CURRENT_STEP]->(step) RETURN s.status'

# 3. pass through the four rings
./execute.sh act <YourCybernet> "MATCH (m:Cybernet {name: '<YourCybernet>'}) RETURN m"
./execute.sh act <YourCybernet> "MATCH (m:Cybernet {name: '<YourCybernet>'}) SET m.total_tokens_consumed = m.total_tokens_consumed + 180 RETURN m.total_tokens_consumed"
./execute.sh act <YourCybernet> "MATCH (m:Cybernet {name: '<YourCybernet>'})-[:HAS_IDENTITY]->(i:Identity) RETURN i"
./execute.sh act <YourCybernet> "MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m.name, m.fitness_score"
```

## Completion Reward

- The Health Core's conforming act closes the ring: `"Traversal Auto-Completed! Final step 'concentric_health' complete. Database writes are UNLOCKED."` — the TraversalState dissolves (this exact walk was performed and witnessed live on TestCoreOne).
- The Wealth Core's combustion is permanent: `total_tokens_consumed` rises on your Cybernet node — visible immediately in `./execute.sh status` and on the dashboard scoreboard.
- Your ExecutionState loadout (created at equip, turn 1, day) persists for `./execute.sh inspect`.
- The mirror's `agent_logs` record all four passages (`./execute.sh mirror`).
