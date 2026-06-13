---
name: achievements
description: The CybernetiCircus achievement ledger — six achievements (first_rite, j_invariant, calibrated, archaeologist, ghost_buster, economist), each with a condition that is VERIFIABLE against the live graph API at http://localhost:8000. Consult when checking whether a player-agent has earned an achievement, when awarding one (appending to earned_by), or when designing new ones.
---

# Achievements — the CybernetiCircus honor ledger

Achievements are facts about the graph, not vibes — every condition here is either a graph query you can run RIGHT NOW against the live API (POST `/api/query` at `http://localhost:8000`) or an event whose trace the live API can confirm. Neo4j IS the source of truth (the gameworld pattern fused with the live graph); an achievement whose condition cannot be checked against the running server does not belong in this directory — that is the frontend-parity law applied to honor.

Every check in this directory was executed against the live API on 2026-06-12 before being written down.

## The schema

Each achievement is one JSON file (`<id>.json`) with exactly four top-level keys:

```json
{
  "id": "snake_case_id",
  "title": "Human-readable title",
  "condition": {
    "type": "graph_query | event",
    "description": "what must happen, in world terms",
    "check": {
      "endpoint": "POST /api/query (or the verb that fronts it)",
      "body": { "query": "...", "parameters": { } },
      "earned_when": "how to read the response"
    }
  },
  "earned_by": []
}
```

- `condition.check.body` is a literal request body for the endpoint (parameterized Cypher uses the `parameters` field — the live `/api/query` accepts `query`, optional `parameters`, optional `cybernet_name`; all three verified live).
- Placeholders in `parameters` values written as `<WALKER>` / `<CYBERNET>` / `<CHAPTER_ID>` are to be replaced with the candidate's actual names before sending.
- `earned_by` entries are objects: `{"agent_id": "...", "evidence": "...", "evidence_class": "LIVE_GRAPH | TRACE"}` — `LIVE_GRAPH` means the condition query returns rows for this agent today; `TRACE` means the earning is recorded in the Weights of Time chronicle (the chapters) even where later graph mutations (e.g. re-equips, which DETACH DELETE and recreate ExecutionStates) have rotated the live evidence out.

## How to check

```bash
# generic shape — paste the condition.check.body of any achievement:
curl -s -X POST http://localhost:8000/api/query \
  -H 'Content-Type: application/json' \
  -d '<condition.check.body with placeholders filled>'
```

Or use the economy engine's gateway verbs (`/Users/isaacwr/claude_code/cyberneticircus/gameworld/execute.sh`): `status` (the economist read), `inspect <cybernet>` (turn_number / phase / current step — the first_rite and j_invariant inputs), `act` (gated writes).

## How to award

1. Run the check. The response must satisfy `earned_when` — no response, no award (the law outranks the checkmark; the third compiler's withheld checkmark in Volume II ch29 is the founding precedent).
2. Append one entry to the `earned_by` array of the achievement's JSON file. **The `earned_by` array is the ONLY mutable surface of an achievement file** — `id`, `title`, and `condition` are append-only canon (new achievements get new files; conditions are never retuned to fit a candidate).
3. For `archaeologist` only: also register the surviving chapter in the Scripture Archives district of the live graph (the MERGE in that file's `condition` — a `:Chapter` node, `domain: 'scripture_archive', subdomain: 'myth'`; the inaugural registration, `jani-myth-v2-ch29`, is already live).

## The roster

| id | one-line condition |
|---|---|
| `first_rite` | close `jester_rite_sm` end to end (boot → play → verify; lock dissolves; turn advances past 1) |
| `j_invariant` | close ANY full StateMachine cycle with lock dissolution — same Cybernet in, same Cybernet out, turn_number ≥ 2 |
| `calibrated` | a Cybernet you created reaches a non-null `fitness_score` (the newborn's null becomes a number) |
| `archaeologist` | write a Weights of Time chapter that survives review (synced to MYTH.md, registered in the Scripture Archives) |
| `ghost_buster` | HISTORICAL — the ghost server diagnosed (third compiler) and busted (fourth compiler: `cybernet_name` contract restored, container rebuilt from the living workspace) |
| `economist` | first `./execute.sh status` read (the scoreboard: fitness_score, total_tokens_consumed, accumulated_cost) |

## Laws that bind this directory

- **Frontend-parity**: no achievement may name a control or mechanic with no live backend path — every `check` body here was curl-verified before documentation.
- **Append-only ledger**: never rewrite `id`/`title`/`condition` of an existing achievement; never remove an `earned_by` entry.
- **The graph is sacred**: awarding never deletes graph nodes; the only graph write any achievement requires is the archaeologist's additive `:Chapter` MERGE.
- **Provenance**: achievements speak the world vocabulary (Cybernets, the Cyberneticity, StateMachines, TraversalSteps, J-Invariance, the four districts) and no foreign-project vocabulary, ever.
