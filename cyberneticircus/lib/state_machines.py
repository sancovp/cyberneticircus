"""
Cypher helpers for state machine structure (transitions, CALLS_SM, gating).

These are pure string-returning functions: no driver, no session. The LLM-loop
gates in `db_logic.py` import them and run them via the shared driver.
"""


# --- Structural / bootstrap helpers -----------------------------------------

def create_transition_cypher(from_id: str, to_id: str, weight: float = 1.0,
                             description: str = "") -> str:
    return f"""MATCH (from:TraversalStep {{id: $from_id}})
MATCH (to:TraversalStep {{id: $to_id}})
MERGE (from)-[r:NEXT_STEP]->(to)
SET r.weight = $weight, r.description = $description"""


def adjust_weight_cypher(from_id: str, to_id: str) -> str:
    return f"""MATCH (from:TraversalStep {{id: $from_id}})-[r:NEXT_STEP]->(to:TraversalStep {{id: $to_id}})
SET r.weight = r.weight + 0.1"""


def create_calls_sm_cypher(from_step_id: str, to_state_machine_id: str) -> str:
    return f"""MATCH (s:TraversalStep {{id: $from_step_id}})
MATCH (sm:StateMachine {{id: $to_state_machine_id}})
MERGE (s)-[:CALLS_SM]->(sm)"""


# --- Gating cypher (used by db_logic's LLM-loop gates) ----------------------

def get_active_traversal_step_cypher() -> str:
    """Read the locked TraversalStep for the given cybernet (per-cybernet scope)."""
    return """
    MATCH (c:Cybernet {name: $cybernet_name})-[:HAS_TRAVERSAL]->(s:TraversalState {status: 'locked'})-[:CURRENT_STEP]->(curr:TraversalStep)
    RETURN curr.id as id, curr.text as text,
           curr.instruction_file_path as instruction_file_path,
           curr.required_pattern as required_pattern,
           curr.pattern_description as pattern_description,
           elementId(s) as state_element_id
    """


def get_outgoing_transitions_cypher() -> str:
    """Read NEXT_STEP transitions from a given TraversalStep, ordered by weight DESC."""
    return """
    MATCH (curr:TraversalStep {id: $curr_id})-[r:NEXT_STEP]->(next:TraversalStep)
    RETURN next.id as id, next.text as text,
           next.required_pattern as required_pattern,
           next.pattern_description as pattern_description,
           coalesce(r.weight, 1.0) as weight,
           coalesce(r.description, '') as description
    ORDER BY weight DESC, id ASC
    """


def next_step_id_cypher() -> str:
    """Return the highest-weight NEXT_STEP neighbour of the current step (one row)."""
    return """
    MATCH (:TraversalStep {id: $curr_id})-[:NEXT_STEP]->(next:TraversalStep)
    RETURN next.id as id LIMIT 1
    """


def read_step_text_cypher() -> str:
    """Read the text + instruction_file_path of a target step (for auto_progress)."""
    return """
    MATCH (n:TraversalStep {id: $id})
    RETURN n.text as text, n.instruction_file_path as fp
    """


def advance_state_cypher() -> str:
    """Move CURRENT_STEP from one step to another for a given TraversalState elementId."""
    return """
    MATCH (s:TraversalState)-[r:CURRENT_STEP]->(curr:TraversalStep)
    WHERE elementId(s) = $state_id
    DELETE r
    WITH s
    MATCH (next:TraversalStep {id: $next_id})
    CREATE (s)-[:CURRENT_STEP]->(next)
    """


def dissolve_state_cypher() -> str:
    """Final step reached: detach the TraversalState entirely (unlocks writes)."""
    return """
    MATCH (s:TraversalState) WHERE elementId(s) = $state_id DETACH DELETE s
    """


def count_locked_states_cypher() -> str:
    """Count global locked TraversalStates (used by scan_and_trigger_traversal)."""
    return "MATCH (s:TraversalState {status: 'locked'}) RETURN count(s) as c"


def step_exists_cypher() -> str:
    """Quick existence check for a TraversalStep (used by scan_and_trigger_traversal)."""
    return "MATCH (s:TraversalStep {id: $id}) RETURN s"


def create_placeholder_step_cypher() -> str:
    """Create a TraversalStep with minimal fields (used by scan_and_trigger_traversal)."""
    return """
    CREATE (:TraversalStep {id: $id, text: $text, domain: 'cyberneticity', subdomain: 'traversal'})
    """


def create_traversal_state_cypher() -> str:
    """Materialize a fresh locked TraversalState pointing at a given TraversalStep."""
    return """
    MATCH (step:TraversalStep {id: $step_id})
    CREATE (s:TraversalState {status: 'locked', target_id: $tid, target_label: $tl,
           created_at: timestamp(), domain: 'cyberneticity', subdomain: 'traversal_state'})
    -[:CURRENT_STEP]->(step)
    """
