"""
The projector — the describe()-analog (DESIGN §13.5).

Renders a being's LIVE Core Chain stack into the **core-loop-prime** context
block: the projected state-diagram of the Core (the CORE_RUNS sequence of SMs,
each SM's step chain, the current position, the bandit arms at the active step).
It is the SAME machine that renders triggered COMP MAPs as rules.

PULL, read-only: the graph is the single source of truth; this projects a *view*
of it for context-assembly. The graph is never mutated here (graph-is-sacred).

UCO framing: a Core is a Chain-of-Chains (CoreModule); `describe_core` is the
`Chain.describe(depth)` analog — it walks the Chain structure and prints it.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


# --- Read cypher (pure strings; the projector runs them read-only) -----------

CORE_SEQUENCE_CYPHER = """
MATCH (c:Cybernet {name:$name})-[:HAS_CORE]->(:Core)-[r:CORE_RUNS]->(sm:StateMachine)
RETURN sm.id AS sm_id, sm.name AS sm_name, r.order AS order, coalesce(r.phase,'day') AS phase
ORDER BY r.order ASC
"""

SM_STEPS_CYPHER = """
MATCH (sm:StateMachine {id:$sm_id})-[:HAS_STEP]->(s:TraversalStep)
OPTIONAL MATCH (s)-[:NEXT_STEP]->(nx:TraversalStep)
OPTIONAL MATCH (prev:TraversalStep)-[:NEXT_STEP]->(s)
OPTIONAL MATCH (s)-[:CALLS_SM]->(child:StateMachine)
RETURN s.id AS id, collect(DISTINCT nx.id) AS next_ids,
       count(DISTINCT prev) AS incoming, collect(DISTINCT child.id) AS calls_sm
"""

POSITION_CYPHER = """
MATCH (c:Cybernet {name:$name})-[:HAS_LIFECYCLE]->(es:ExecutionState)
OPTIONAL MATCH (es)-[:CURRENT_STEP]->(curr:TraversalStep)
RETURN es.equipped_sm_id AS equipped, es.core_index AS core_index,
       coalesce(es.phase,'day') AS phase, coalesce(es.status,'unlocked') AS status,
       curr.id AS current_step
"""

COMP_MAPS_CYPHER = """
MATCH (c:Cybernet {name:$name})-[:HAS_COMP_MAP|HAS_GEAR|EQUIPS]->(cm:CompMap)
WHERE coalesce(cm.active, true)
RETURN cm.trigger AS trigger, cm.desc AS desc
ORDER BY cm.trigger
"""


# --- Step-chain ordering (reconstruct the linear order from NEXT_STEP) --------

def _order_steps(rows: List[Dict[str, Any]],
                 prefer_start: Optional[str] = None) -> List[Dict[str, Any]]:
    """Order an SM's steps along the NEXT_STEP chain. Start at `prefer_start` if
    given (used for the ACTIVE SM: a Core SM is often a CYCLE where every step has
    an incoming edge, so 'lowest incoming' is meaningless — starting from the
    being's current step gives the natural 'you are here → what's ahead' view).
    Otherwise entry = lowest incoming (0 for a line). Loop-guarded."""
    by_id = {r["id"]: r for r in rows}
    if not by_id:
        return []
    if prefer_start and prefer_start in by_id:
        start_id = prefer_start
    else:
        start_id = min(rows, key=lambda r: (r["incoming"], r["id"]))["id"]
    ordered, seen, cur = [], set(), start_id
    while cur and cur not in seen:
        seen.add(cur)
        row = by_id.get(cur)
        if not row:
            break
        ordered.append(row)
        nxts = [n for n in row["next_ids"] if n]
        cur = nxts[0] if nxts else None
    # append any unreached steps (branches) so nothing is hidden
    for r in rows:
        if r["id"] not in seen:
            ordered.append(r)
    return ordered


# --- The projection ----------------------------------------------------------

def describe_core(driver, *, name: str) -> str:
    """Render the core-loop-prime: the projected state-diagram of the being's
    live Core Chain stack, with the current position marked."""
    with driver.session() as session:
        seq = [dict(r) for r in session.run(CORE_SEQUENCE_CYPHER, name=name)]
        pos = session.run(POSITION_CYPHER, name=name).single()
        sm_steps = {
            row["sm_id"]: [dict(s) for s in session.run(SM_STEPS_CYPHER, sm_id=row["sm_id"])]
            for row in seq
        }

    if not seq:
        return f"[core-loop-prime] {name} has no Core (no HAS_CORE → Core → CORE_RUNS)."

    equipped = pos["equipped"] if pos else None
    core_index = pos["core_index"] if pos else None
    phase = pos["phase"] if pos else "day"
    status = pos["status"] if pos else "unlocked"
    current_step = pos["current_step"] if pos else None

    lines = [
        f"=== CORE-LOOP-PRIME (projected from the live Core — phase: {phase}, {status}) ===",
        f"Cybernet: {name}   position: SM '{equipped}' [{core_index}], step '{current_step}'",
        "Your Core is the always-running stack. Everything you do is a step inside it;",
        "emit the step's templated Cypher and the gate advances you.",
        "",
    ]
    for row in seq:
        is_active = row["sm_id"] == equipped
        mark = "  <== ACTIVE" if is_active else ""
        lines.append(f"  [{row['order']}] {row['sm_id']} ({row['phase']}){mark}")
        # for the active SM, render the cycle from the current step (you-are-here view)
        ordered = _order_steps(sm_steps.get(row["sm_id"], []),
                               prefer_start=current_step if is_active else None)
        rendered = []
        for s in ordered:
            tok = s["id"]
            if s["id"] == current_step:
                tok = f"[{tok}]*"          # current step
            if s["calls_sm"] and any(s["calls_sm"]):
                arms = ", ".join(a for a in s["calls_sm"] if a)
                tok = f"{tok}{{arms: {arms} + make-a-thing-or-not}}"
            rendered.append(tok)
        if rendered:
            lines.append("        " + " -> ".join(rendered))
    lines += [
        "",
        "At a step exposing selectable inner SMs (CALLS_SM) you run a BANDIT over the",
        "arms; the default arm is always \"make a thing or not\". When the last SM's last",
        "step completes = the Day terminal → the Core ENDS (an external trigger re-starts it).",
        "* = your current step.",
    ]
    return "\n".join(lines)


def project_comp_maps(driver, *, name: str) -> str:
    """Render the being's active COMP MAPs as injected rules: concat(trigger, desc).
    Empty until COMP MAPs are authored (the import button). DESIGN §13.5."""
    with driver.session() as session:
        # Quiet guard: skip (and don't emit 'label does not exist' warnings) until
        # the CompMap label is actually present in the graph.
        has_label = session.run(
            "CALL db.labels() YIELD label WHERE label = 'CompMap' RETURN count(*) AS n"
        ).single()["n"]
        if not has_label:
            return ""
        rows = [dict(r) for r in session.run(COMP_MAPS_CYPHER, name=name)]
    if not rows:
        return ""
    out = ["=== COMP MAPS (projected as rules) ==="]
    for r in rows:
        out.append(f"- {r['trigger']}: {r['desc']}")
    return "\n".join(out)


def assemble_context(driver, *, name: str) -> Dict[str, Any]:
    """The full projected context for a being (the context-assembly step of the
    tick, Driver A): the core-loop-prime + any active COMP MAP rules."""
    core_loop_prime = describe_core(driver, name=name)
    comp_maps = project_comp_maps(driver, name=name)
    blocks = [core_loop_prime] + ([comp_maps] if comp_maps else [])
    return {
        "cybernet": name,
        "core_loop_prime": core_loop_prime,
        "comp_maps": comp_maps,
        "context": "\n\n".join(blocks),
    }
