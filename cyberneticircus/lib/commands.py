"""
Commands — the list of available entry-point TraversalSteps.
(Equivalent to MCP's `commands` tool. Returns the procedures the LLM can start.)

Composition:
  - list_entry_steps  →  GET /api/commands
"""
from __future__ import annotations
from typing import Any, Dict, List


ENTRY_STEPS_CYPHER = """
MATCH (s:TraversalStep)
WHERE NOT ()-[:NEXT_STEP]->(s)
RETURN s.id as id, s.text as text, elementId(s) as node_element_id
ORDER BY id ASC
"""


def list_entry_steps(driver) -> List[Dict[str, Any]]:
    """List all entry-point TraversalSteps (no incoming NEXT_STEP). These are the procedures' entry buttons."""
    with driver.session() as session:
        return [
            {"id": r["id"], "text": r["text"], "node_element_id": r["node_element_id"]}
            for r in session.run(ENTRY_STEPS_CYPHER)
        ]
