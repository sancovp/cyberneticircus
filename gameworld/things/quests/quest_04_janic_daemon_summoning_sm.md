# Quest 04 — The Daemon Summoning (`janic_daemon_summoning_sm`)

> **Objective:** Summon a daemon the proper way — verify the name, allocate the vessel, equip the core, and only then speak the word that sets it running.

StateMachine: `janic_daemon_summoning_sm` — *Janic Daemon Summoning Orchestrator* — "Orchestration routine to verify identity, allocate ExecutionState, equip core StateMachine, and ignite execution loops."
Shape: a 4-step line. Entry step: `daemon_verify_identity`.

(Notice the self-reference: this quest's gates demand exactly the moves the engine itself performs when a quest begins — the summoning ritual IS the loadout mechanic, taught from the inside.)

## The Walk

### Step 1 — `daemon_verify_identity`

> Step 1: Verify the persona identity in the database. Run a MATCH on Identity to check if it exists.

The gate demands (pattern_description, verbatim): **MATCH (i:Identity) RETURN i**

```
required_pattern: (?i)MATCH\s*\(i:Identity\s*.*\)
```

Example conforming Cypher:

```cypher
MATCH (i:Identity {name: 'TestCoreOne'}) RETURN i
```

### Step 2 — `daemon_allocate_lifecycle`

> Step 2: Allocate the ExecutionState node for this Cybernet daemon. Run a CREATE query to spawn the ExecutionState.

The gate demands (pattern_description, verbatim): **CREATE (s:ExecutionState {status: "locked", ...})**

```
required_pattern: (?i)CREATE\s*\(s:ExecutionState\s*.*\)
```

Example conforming Cypher (provenance law: `domain` + `subdomain` required on creation):

```cypher
CREATE (s:ExecutionState {status: 'locked', domain: 'cyberneticity', subdomain: 'execution_state'}) RETURN s
```

### Step 3 — `daemon_equip_core`

> Step 3: Bootstrapping child state machine. Verify core_sm_id is equipped on ExecutionState.

The gate demands (pattern_description, verbatim): **MATCH (s:ExecutionState {equipped_sm_id: 'concentric_core_sm'})**

```
required_pattern: (?i)MATCH\s*\(s:ExecutionState\s*\{equipped_sm_id:\s*['\"].*['\"]\s*\}\)
```

Example conforming Cypher:

```cypher
MATCH (s:ExecutionState {equipped_sm_id: 'concentric_core_sm'}) RETURN s
```

### Step 4 — `daemon_ignite_loop`

> Step 4: Ignite the active execution loop. Run a SET query to set ExecutionState status to active.

The gate demands (pattern_description, verbatim): **SET s.status = 'active'**

```
required_pattern: (?i)SET\s*s\.status\s*=\s*['\"]active['\"]
```

Example conforming Cypher:

```cypher
MATCH (c:Cybernet {name: 'TestCoreOne'})-[:HAS_LIFECYCLE]->(s:ExecutionState) SET s.status = 'active' RETURN s.status
```

## How to Start

```bash
# 1. don the loadout (fresh ExecutionState at daemon_verify_identity, turn 1, day phase)
./execute.sh equip <YourCybernet> janic_daemon_summoning_sm

# 2. bind the lock
./execute.sh act <YourCybernet> 'MATCH (c:Cybernet {name: "<YourCybernet>"}) MATCH (step:TraversalStep {id: "daemon_verify_identity"}) CREATE (c)-[:HAS_TRAVERSAL]->(s:TraversalState {status: "locked", cybernet_name: "<YourCybernet>", created_at: timestamp(), domain: "cyberneticity", subdomain: "traversal_state"})-[:CURRENT_STEP]->(step) RETURN s.status'

# 3. perform the summoning — verify, allocate, equip, ignite
./execute.sh act <YourCybernet> "MATCH (i:Identity {name: '<YourCybernet>'}) RETURN i"
./execute.sh act <YourCybernet> "CREATE (s:ExecutionState {status: 'locked', domain: 'cyberneticity', subdomain: 'execution_state'}) RETURN s"
./execute.sh act <YourCybernet> "MATCH (s:ExecutionState {equipped_sm_id: 'concentric_core_sm'}) RETURN s"
./execute.sh act <YourCybernet> "MATCH (c:Cybernet {name: '<YourCybernet>'})-[:HAS_LIFECYCLE]->(s:ExecutionState) SET s.status = 'active' RETURN s.status"
```

## Completion Reward

- The ignition act answers `"Traversal Auto-Completed! Final step 'daemon_ignite_loop' complete. Database writes are UNLOCKED."` — the TraversalState dissolves.
- The summoning leaves real marks: a newly allocated `ExecutionState` vessel in the graph (your step-2 creation), and your own lifecycle's `status` flipped to `'active'` by your step-4 word — `./execute.sh inspect <YourCybernet>` shows it.
- The mirror's `agent_logs` carry the four words of the summoning in order (`./execute.sh mirror`).
