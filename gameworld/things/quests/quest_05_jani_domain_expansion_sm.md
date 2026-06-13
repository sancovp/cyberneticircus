# Quest 05 — The Domain Expansion (`jani_domain_expansion_sm`)

> **Objective:** Climb the three boot layers of Jani — find the Prime, compile the rules, and ignite the SDLC by spawning a child of your own — the shape any booted agent takes, taken one layer deeper.

StateMachine: `jani_domain_expansion_sm` — *Jani Domain Expansion Orchestrator* — "Models progression through Jani boot layers: primitive boot, rule compilation, and SDLC ignition."
Shape: a 3-step line. Entry step: `layer1_primitive_boot`.

## The Walk

### Step 1 — `layer1_primitive_boot`

> Layer 1: Boot Jani Prime. Verify that the Jani_Prime Cybernet exists in the database. Run a MATCH on Cybernet for Jani_Prime.

The gate demands (pattern_description, verbatim): **MATCH (c:Cybernet {name: 'Jani_Prime'}) RETURN c**

```
required_pattern: (?i)MATCH\s*\(c:Cybernet\s*\{\s*name:\s*['\"]Jani_Prime['\"]\s*\}\)
```

Example conforming Cypher (`Jani_Prime` is real — it lives in the graph; the gate names it exactly):

```cypher
MATCH (c:Cybernet {name: 'Jani_Prime'}) RETURN c
```

### Step 2 — `layer2_meta_compile`

> Layer 2: Compile active rules and contexts. Run a MATCH on StateMachine to verify the active configurations exist.

The gate demands (pattern_description, verbatim): **MATCH (sm:StateMachine) RETURN sm**

```
required_pattern: (?i)MATCH\s*\(sm:StateMachine\s*.*\)
```

Example conforming Cypher:

```cypher
MATCH (sm:StateMachine) RETURN sm.id, sm.name
```

### Step 3 — `layer3_sdlc_ignite`

> Layer 3: Ignite SDLC pipelines and spawn a child Cybernet. Run a CREATE or MERGE query to spawn a new Cybernet with domain and subdomain properties.

The gate demands (pattern_description, verbatim): **CREATE (c:Cybernet {name: 'Child_Daemon', domain: 'cyberneticity', subdomain: 'cybernet'})**

```
required_pattern: (?i)(CREATE|MERGE)\s*\(c:Cybernet\s*.*\)
```

Example conforming Cypher (the spawn is real — a new Cybernet node enters the Cyberneticity; name your child well):

```cypher
CREATE (c:Cybernet {name: 'Child_Daemon', domain: 'cyberneticity', subdomain: 'cybernet'}) RETURN c
```

## How to Start

```bash
# 1. don the loadout (fresh ExecutionState at layer1_primitive_boot, turn 1, day phase)
./execute.sh equip <YourCybernet> jani_domain_expansion_sm

# 2. bind the lock
./execute.sh act <YourCybernet> 'MATCH (c:Cybernet {name: "<YourCybernet>"}) MATCH (step:TraversalStep {id: "layer1_primitive_boot"}) CREATE (c)-[:HAS_TRAVERSAL]->(s:TraversalState {status: "locked", cybernet_name: "<YourCybernet>", created_at: timestamp(), domain: "cyberneticity", subdomain: "traversal_state"})-[:CURRENT_STEP]->(step) RETURN s.status'

# 3. climb the three layers
./execute.sh act <YourCybernet> "MATCH (c:Cybernet {name: 'Jani_Prime'}) RETURN c"
./execute.sh act <YourCybernet> "MATCH (sm:StateMachine) RETURN sm.id, sm.name"
./execute.sh act <YourCybernet> "CREATE (c:Cybernet {name: 'Child_Daemon', domain: 'cyberneticity', subdomain: 'cybernet'}) RETURN c"
```

## Completion Reward

- The ignition act answers `"Traversal Auto-Completed! Final step 'layer3_sdlc_ignite' complete. Database writes are UNLOCKED."` — the TraversalState dissolves.
- A child Cybernet of your naming now exists in the graph — your spawn, permanent, listed by `GET /api/list` and visible on the dashboard graph view.
- Your ExecutionState loadout persists (`./execute.sh inspect <YourCybernet>`); the equip records `completed_layers` as an empty vessel awaiting the engine's layer-tracking.
- The mirror's `agent_logs` show the three-layer climb (`./execute.sh mirror`).
