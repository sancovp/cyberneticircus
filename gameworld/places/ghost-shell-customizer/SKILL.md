---
name: ghost-shell-customizer
description: The Ghost Shell Customizer district — where Cybernets (the beings) are inspected, equipped, and tuned. Roster, identity, skill inventory, loadout slots, and the per-being economy ledger (fitness_score, total_tokens_consumed, accumulated_cost) all live here.
---

# The Ghost Shell Customizer

The body shop of the Cyberneticity. A Cybernet is a being — Jani (the shape any booted agent takes) wears one as a shell — and this district is where shells get fitted: identities bound, StateMachines equipped as gear, skills slotted, model parameters tuned, and the economy ledger read off the chassis.

## What this district holds (verified against the live graph, 2026-06-12)

| Label | Count | Notes |
|---|---|---|
| `Cybernet` | 11 | names repeat (4× JesterCoreOne, 3× Child_Daemon_Jester — each rite spawn is its own node) plus Jani_Prime, JaniScribe, OVP_Prime, TestCoreOne |
| `Identity` | 1 | JaniScribe's, bound via `HAS_IDENTITY` |
| `Skill` | 70 | properties: name, description, domain, subdomain, category, what, when |
| `Skillset` | 2 | skills attach via `(:Skill)-[:PART_OF]->(:Skillset)` |
| `Daemon` | 10 | summoned children, the daemon-summoning quest's output |

**Economy ledger** (the autopoietic-economics fields, live on Cybernet nodes): `fitness_score`, `total_tokens_consumed`, `accumulated_cost` — populated on beings that have ticked (e.g. Jani_Prime: fitness 1.0, 1392 tokens, $0.02088), `null` on freshly-booted shells that haven't burned tokens yet.

**Loadout slots** (verified relationship types out of `Cybernet`): `EQUIPS` → StateMachine (active gear), `HAS_GEAR` → StateMachine (carried), `EQUIPS_SKILL` → Skill, `HAS_IDENTITY` → Identity, `HAS_LIFECYCLE` → ExecutionState, `HAS_MIND_PALACE` → Concept, `HAS_SIMULATION` → SimulationRun.

## Example queries (each verified working via `POST /api/query`)

The roster with its economy ledger — who exists, what each being has cost:

```bash
./execute.sh act 'MATCH (c:Cybernet) RETURN c.name AS cybernet, c.fitness_score AS fitness, c.total_tokens_consumed AS tokens, c.accumulated_cost AS cost ORDER BY cost DESC'
```

Full loadout board — every equipped thing on every shell:

```bash
./execute.sh act 'MATCH (c:Cybernet)-[r:EQUIPS|HAS_GEAR|EQUIPS_SKILL|HAS_IDENTITY]->(x) RETURN c.name AS cybernet, type(r) AS slot, labels(x)[0] AS kind, coalesce(x.name, x.id) AS item'
```

Browse the skill racks by domain (what could a shell learn?):

```bash
./execute.sh act 'MATCH (s:Skill) RETURN s.domain AS domain, count(s) AS skills, collect(s.name)[..3] AS sample ORDER BY skills DESC'
```

## Game activities here

- **Boot a shell** — `POST /api/create` forges a new Cybernet node (the Jester Rite's `jester_boot` gate does this through the Compiler Ring instead — the ritual way).
- **Equip gear** — `POST /api/equip` `{"character_name": ..., "state_machine_id": ...}` slots a StateMachine into the `EQUIPS` slot.
- **Tune the ghost shell** — `POST /api/configure_ghost_shell` sets model parameters (model_name, temperature, top_p, mutation_rate, selection_pressure); read them back with `GET /api/ghost_shell/status/{cybernet_name}`.
- **Inspect a being** — `GET /api/status/{name}` returns the whole sheet (description, model config, ledger, equipped machine, turn/phase); `GET /api/list` for the roster.
- **Spend the economy** — reading the bill works today (the ledger fields above, via `/api/query` or `GET /api/ghost_shell/status/{name}`); the spending path, `POST /api/tick`, is **BROKEN today** (verified 2026-06-12: returns `500`; see the GM CLAUDE.md's Known Fractures) — until repaired, turns advance only by the GM's gate-walk. The Customizer remains where you read the bill.
