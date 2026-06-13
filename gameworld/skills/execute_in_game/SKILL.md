---
name: execute_in_game
description: >
  WHAT: The seven verbs of the CybernetiCircus economy engine
  (gameworld/execute.sh) — every verb is a live call against the graph API
  at http://localhost:8000 (Neo4j is the source of truth; the visualizer at
  the same URL is the operational mirror).
  WHEN: Any time you need to read the scoreboard, list quests, inspect a
  Cybernet, equip a StateMachine, act as a Cybernet through the pattern gate,
  advance a traversal, or check the mirror.
---

# execute_in_game — the economy engine verbs

The engine lives at `gameworld/execute.sh` (relative to the CybernetiCircus
root: `/Users/isaacwr/claude_code/cyberneticircus/gameworld/execute.sh`).
It is bash + curl + jq; it has no state of its own — the graph behind
`http://localhost:8000` holds everything (override the base with
`$CYBERCITY_API`). Every example below was run against the live server.

## status — the scoreboard

Reads every `:Cybernet` node with its economy fields (`fitness_score`,
`total_tokens_consumed`, `accumulated_cost`) via `POST /api/query`.
Sorted fitness-descending; `-` means the node has no value for that field
(several Cybernets exist as multiple nodes — each row is a real node).

```
$ ./execute.sh status
== CYBERNET SCOREBOARD (live graph @ http://localhost:8000) ==
NAME                 PERSONA  FITNESS             TOKENS  COST
JaniScribe           -        1.0                 5360    0.0804
Jani_Prime           -        1.0                 1392    0.02088
JesterCoreOne        Jester   1.0                 679     0.010185
OVP_Prime            -        1.0                 1383    0.016635
TestCoreOne          -        0.7520000000000001  5809    0.072105
Child_Daemon_Jester  -        -                   -       -
```

## quests — the equippable StateMachine list

Reads every `:StateMachine` (id, name, description) from the graph.

```
$ ./execute.sh quests
== STATEMACHINES (the equippable quest list) ==
* jester_rite_sm
    name: Jester Rite State Machine
    desc: Ritual of autopoietic self-remembering and prompt-shifting.
* concentric_core_sm
    name: Universal Concentric State Machine Core
    desc: Orthogonally maps execution through the four transcendental layers ...
...
```

## inspect <cybernet> — full sheet + execution state

Two live reads: `properties(c)` from the graph (the full node — model params,
mutation_rate, economy fields), then `GET /api/status/<name>` (equipped SM,
turn, phase, current step, and the `required_pattern` gating that step).

```
$ ./execute.sh inspect TestCoreOne
== GRAPH NODE PROPERTIES: TestCoreOne ==
{
  "accumulated_cost": 0.072105,
  "total_tokens_consumed": 5809,
  "fitness_score": 0.7520000000000001,
  "model_name": "gemini-1.5-pro", ...
}
== LIVE EXECUTION STATE (GET /api/status/TestCoreOne) ==
{
  "equipped_sm_id": "jester_rite_sm",
  "turn_number": 1,
  "phase": "day",
  "current_step_id": "jester_boot",
  "required_pattern": "(?i)CREATE\\s*\\(c:Cybernet\\s*\\{\\s*name:\\s*['\"]JesterCoreOne['\"].*\\}\\)", ...
}
```

The `required_pattern` is the gate your next `act` must satisfy when a
traversal lock is active — read it BEFORE acting.

## equip <cybernet> <sm_id> — take on a quest

`POST /api/equip` with the live contract `{character_name, state_machine_id}`
(verified against openapi.json + the server's 422 validation — both fields
are required). Equipping creates a fresh `:ExecutionState` at the
StateMachine's entry step.

```
$ ./execute.sh equip JesterCoreOne jester_rite_sm
== EQUIP: JesterCoreOne <- jester_rite_sm ==
# server response: the new ExecutionState at the SM's entry step
```

NOTE: equip is a WRITE — it replaces the Cybernet's active execution state.
Run `inspect` first; do not casually re-equip a Cybernet that is mid-rite.

## act <cybernet> '<cypher>' — the core game verb

`POST /api/query` with `cybernet_name` set: the server recognizes
frontend-action patterns first, otherwise runs the cypher through the gate
(the current step's `required_pattern`). Read queries pass; write queries
must match the gate when a traversal is locked.

```
$ ./execute.sh act TestCoreOne 'MATCH (c:Cybernet {name: "TestCoreOne"}) RETURN c.name AS name, c.fitness_score AS fitness LIMIT 1'
== ACT AS TestCoreOne (gated by current step) ==
[
  { "name": "TestCoreOne", "fitness": 0.7520000000000001 }
]
```

Quote the cypher in single quotes; use double quotes inside it.

## progress <cybernet> — advance the traversal

`POST /api/traversal/progress` with `{cybernet_name}`. Reads the current
step, evaluates, moves along `NEXT_STEP`. If no traversal is locked, the
server says so (and writes are fully unlocked for that Cybernet):

```
$ ./execute.sh progress TestCoreOne
== PROGRESS: TestCoreOne ==
{
  "message": "No active traversal state machine is currently locked for cybernet 'TestCoreOne'. Database writes are fully unlocked for this cybernet."
}
```

## mirror — the GM's table view

Echoes the dashboard URL and tails the last 5 `agent_logs` entries
(`GET /api/agent_logs`), plus the auto-detected active Cybernet and step.
Every `act`/`status`/`quests` call you make shows up here — the mirror
watches the engine.

```
$ ./execute.sh mirror
== THE OPERATIONAL MIRROR ==
dashboard: http://localhost:8000

{
  "active_cybernet": "TestCoreOne",
  "active_step_id": "508869",
  "last_5_logs": [
    { "type": "action", "text": "Executed query: MATCH (c:Cybernet {name: \"TestCoreOne\"}) ...", ... },
    { "type": "action", "text": "Progressed active step. Answer: None", "focus_labels": ["TraversalStep"] }
  ]
}
```

## The economy loop (how the verbs compose)

`quests` (what exists) -> `equip` (take it on) -> `inspect` (read the gate)
-> `act` (satisfy the `required_pattern`) -> `progress` (advance) ->
`status` (watch fitness/tokens/cost move) -> `mirror` (see it all reflected).
