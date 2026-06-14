"""
Night consolidation (DESIGN §6.A increment 2b) — the close-out at the Day terminal.

"The Cybernet updates the weights and looks over all of that to calculate scores
during night ... the entire point is to make sure the stored context from the run
gets webbed" (Isaac). At the Day terminal (the Core's last SM completes), before
the Core ENDS, consolidate the run:

  1. REINFORCE — bump the NEXT_STEP weight of each bandit arm the being CHOSE this
     run (recorded on ExecutionState.bandit_choices during the Day, as 'from|to').
     This is the bandit learning: the chosen arms get heavier.
  2. SCORE + WEB — create a :Consolidation node linking the being to this run
     (the transient run becomes permanent graph structure — graph-as-coding-substrate),
     recording how many arms were reinforced.
  3. CLEAR the run's choices.

Keyed on the ExecutionState elementId so it composes with gates.auto_progress_step
(which holds state_element_id, not the cybernet name). Runs in the gate's session.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

READ_CHOICES_CYPHER = """
MATCH (c:Cybernet)-[:HAS_LIFECYCLE]->(s:ExecutionState) WHERE elementId(s) = $state_id
RETURN coalesce(s.bandit_choices, []) AS choices, c.name AS name
"""

REINFORCE_ONE_CYPHER = """
MATCH (:TraversalStep {id: $from_id})-[r:NEXT_STEP]->(:TraversalStep {id: $to_id})
SET r.weight = coalesce(r.weight, 1.0) + $delta
RETURN r.weight AS weight
"""

WEB_CONSOLIDATION_CYPHER = """
MATCH (c:Cybernet)-[:HAS_LIFECYCLE]->(s:ExecutionState) WHERE elementId(s) = $state_id
CREATE (con:Consolidation {
    id: 'consol_' + $name + '_' + toString(timestamp()),
    reinforced: $n, created_at: timestamp(),
    domain: 'cyberneticity', subdomain: 'consolidation'
})
CREATE (c)-[:HAS_CONSOLIDATION]->(con)
SET s.bandit_choices = []
RETURN con.id AS id
"""


def consolidate(session, *, state_id: str, delta: float = 0.1) -> Optional[str]:
    """Run the Night consolidation for the being whose ExecutionState is `state_id`.
    Reinforces the run's recorded bandit choices, webs a :Consolidation node, and
    clears the choices. Returns a short summary, or None if no ExecutionState."""
    rec = session.run(READ_CHOICES_CYPHER, state_id=state_id).single()
    if not rec:
        return None
    choices = rec["choices"] or []
    name = rec["name"]
    reinforced = 0
    for ch in choices:
        if isinstance(ch, str) and "|" in ch:
            from_id, to_id = ch.split("|", 1)
            r = session.run(REINFORCE_ONE_CYPHER, from_id=from_id, to_id=to_id,
                            delta=delta).single()
            if r:
                reinforced += 1
    web = session.run(WEB_CONSOLIDATION_CYPHER, state_id=state_id, name=name,
                      n=reinforced).single()
    return (f"Night consolidation: {reinforced} bandit arm(s) reinforced (+{delta}); "
            f"run webbed as {web['id'] if web else '?'}.")
