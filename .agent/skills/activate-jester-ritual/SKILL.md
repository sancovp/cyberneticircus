---
name: activate-jester-ritual
description: |
  WHAT: Activate the `jester_rite_sm` procedure in the cyberneticity (the canonical
        Jester Rite: spawn JesterCoreOne, give it a Jester persona, verify its fitness).
  WHEN: User says "activate the jester rite", "run jester_rite", "spawn a jester",
        "make a jester", or asks to walk through the 3-step jester creation ritual.
        The procedure is the source of truth — discoverable in the graph via
        GET /api/commands (the entry-point step is `jester_boot`).
---

# Activate the Jester Rite

The Jester Rite is a 3-step procedure in the cyberneticity's `:StateMachine {id: 'jester_rite_sm'}`. The procedure walks the canonical Jester creation flow: spawn the Jester, give it a persona, verify its autopoiesis.

**Source of truth: the graph** — `MATCH (sm:StateMachine {id: 'jester_rite_sm'})-[:HAS_STEP]->(s:TraversalStep) RETURN s.id, s.required_pattern, s.pattern_description` reveals the live required_pattern gating. This skill is a thin pointer; if the patterns here drift from the graph, the graph wins.

## Equip first (if not already equipped)

```cypher
MATCH (c:Cybernet {name: 'JesterCoreOne'})
MATCH (sm:StateMachine {id: 'jester_rite_sm'})
MERGE (c)-[:EQUIPS]->(sm)
MERGE (c)-[:HAS_LIFECYCLE]->(s:ExecutionState {equipped_sm_id: 'jester_rite_sm', status: 'locked', domain: 'cyberneticity', subdomain: 'execution_state'})
WITH s, sm
MATCH (sm)-[:HAS_STEP]->(entry:TraversalStep)
WHERE NOT ()-[:NEXT_STEP]->(entry)  -- the entry step (jester_boot, no incoming NEXT_STEP)
WITH s, collect(entry) as entries
UNWIND entries as entry
MERGE (s)-[:CURRENT_STEP]->(entry)
```

## Drive each step

The cypher shell `/api/query` accepts the query + `cybernet_name` and the gate auto-progresses when the query matches the active step's `required_pattern`. Use the cypher shell, NOT raw neo4j (the gate enforces the pattern check + auto-progress + lock scoping).

### Step 1: `jester_boot` — Spawn the Jester core (idempotently)

**Required pattern:** `(?i)MERGE\s*\(c:Cybernet\s*\{\s*name:\s*['"]JesterCoreOne['"]\s*\}\)\s*ON\s+CREATE\s+SET`
**What it does:** MERGEs the JesterCoreOne Cybernet node keyed on name, so re-running the rite never duplicates the being. A bare `CREATE` is now REFUSED by the gate.

```cypher
MERGE (c:Cybernet {name: 'JesterCoreOne'}) ON CREATE SET c.status = 'initialized', c.domain = 'cyberneticity', c.subdomain = 'cybernet'
```

POST to `/api/query`:
```json
{"query": "MERGE (c:Cybernet {name: 'JesterCoreOne'}) ON CREATE SET c.status = 'initialized', c.domain = 'cyberneticity', c.subdomain = 'cybernet'", "parameters": {}}
```

The gate matches the MERGE-on-name + `ON CREATE SET` form and auto-progresses to step 2.

### Step 2: `jester_play` — Apply the Jester persona

**Required pattern:** `MATCH.*Cybernet.*JesterCoreOne.*SET.*persona`
**What it does:** Mutates the Jester's behavioral guidelines to Jester persona.

```cypher
MATCH (c:Cybernet {name: 'JesterCoreOne'}) SET c.persona = 'Jester'
```

The gate matches the pattern and auto-progresses to step 3.

### Step 3: `jester_verify` — Verify J-Invariance

**Required pattern:** `MATCH.*Cybernet.*JesterCoreOne.*RETURN.*fitness_score`
**What it does:** Returns the Jester's fitness score to validate autopoiesis.

```cypher
MATCH (c:Cybernet {name: 'JesterCoreOne'}) RETURN c.fitness_score
```

The gate matches and the procedure completes. The Jester Rite is verified.

## Round-trip verification

After all 3 steps, the procedure has walked its full chain. You can confirm with:

```cypher
MATCH (c:Cybernet {name: 'JesterCoreOne'})-[r:EQUIPS]->(sm:StateMachine {id: 'jester_rite_sm'})
MATCH (c)-[:HAS_LIFECYCLE]->(s:ExecutionState)
RETURN c.name, c.fitness_score, c.persona, s.status, sm.id
```

A successful run returns: JesterCoreOne | 1.0 | 'Jester' | 'locked' (or 'active' if lifetime running) | 'jester_rite_sm'.

## Why this works

- The procedure is in the graph (source of truth). The required_pattern on each TraversalStep gates the LLM's emitted cypher — only valid queries pass the gate and auto-progress.
- The cypher shell `/api/query` is the only required HTTP endpoint. It runs the cypher through the LLM-loop gate (validate + per-cybernet ExecutionState lock + pattern check + auto-progress).
- This skill is the canonical hint for the LLM. If the procedure changes (new steps, new patterns), update the graph + re-discover via the cypher shell. The skill body may lag.

## See also

- The universal concentric state machine: `concentric_core_sm` (4 steps: spiritual → wealth → social → health). Same activation pattern via tick_turn.
- The Janic Core Cycle: `janic_cycle_sm` (5 steps: read_designs → check_state → engineer → preservation → autocommentary). Equipped on Jani_Prime and JaniScribe in the current graph state.
- All entry-point TraversalSteps are discoverable via `GET /api/commands`.
