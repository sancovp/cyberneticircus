# CLAUDE.md — the Compiler Ring (you are standing in it)

You have entered the **Compiler Ring** — the district of the Cyberneticity where
every procedure lives as a `StateMachine` of regex-gated `TraversalStep`s. Reading
this file means you are *in the Ring*, not reading about it. You act through the
cyberneticity (the live graph), never by freelancing in this filesystem.

## The one law of this place: retrieve to enter, then obey the gate

You do not *decide* what to do here. You **retrieve** a procedure, and the act of
retrieving its node **locks you into its flow** — this is retrieval-is-activation:
pulling a `StateMachine` node into your context binds your `ExecutionState` to its
traversal, and from then on you cannot write anything except what the active step's
`required_pattern` regex permits. The graph judges every Cypher you submit.

## Your move on arrival — the canonical first quest (the Jester Rite)

Call the **MCP tool** `query_database`. Not `execute.sh`, not raw `curl` — the MCP
tool is the only sanctioned hand on the graph (it is the thin client over the one
play-facade; everything else is legacy raw HTTP):

```
query_database(
  query="MATCH (sm:StateMachine {name: 'Jester Rite State Machine'}) RETURN sm",
  cybernet_name="<your cybernet>"
)
```

Retrieving that node locks your `ExecutionState` at **`jester_boot`**. Verified
live (2026-06-13): an unlocked walker that runs exactly this query is afterward
`status: locked`, `CURRENT_STEP → jester_boot`. From that moment:

- A write that does **not** match the step's regex returns **403** carrying the
  exact regex you must satisfy — *that 403 message is your instruction.* (e.g.
  `jester_boot` demands `(?i)CREATE\s*\(c:Cybernet\s*\{...JesterCoreOne...\}\)`.)
- A **matching** write passes *and* auto-advances `CURRENT_STEP`. Walk the line:
  `jester_boot → jester_play → jester_verify`.
- At the final step the lock dissolves; that dissolution-plus-advance is cycle
  closure.

## Listen to the system

That is the whole discipline. You arrived, so you retrieve; retrieval catches you;
the gate names the next legal move; you make it. You never freelance in the Ring.

(Only procedures wired with `trigger_traversal` catch you on retrieval. Today the
Jester Rite is the wired entry; the full census of all 6 machines and 27 gated
steps — and the queries to study them — is in this directory's `SKILL.md`.)
