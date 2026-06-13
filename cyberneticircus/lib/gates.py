"""
LLM-loop gate implementations.

These are the actual bodies of the public surface in `db_logic.py` (per the
architecture rule §9.1 "thin facade + lib/ deps"). They are passed the
driver-getter, cypher-helpers, and logger from the facade so that:
- this module never imports the driver directly (testable, swappable)
- this module never imports the facade (no cycles)
- the facade stays a thin shim of one-liner delegations

Functions:
- is_mutation_query, validate_cypher_query  -- gate primitives
- serialize_value                          -- Neo4j → JSON-safe converter
- run_cypher                                -- execute + serialize
- get_active_traversal_step                 -- per-cybernet lock read
- auto_progress_step                        -- advance ExecutionState
- scan_and_trigger_traversal                -- trigger_traversal hook
- adjust_transition_weight_internal         -- NEXT_STEP weight tuning
- get_schema                                -- db.labels/rels/props dump
- populate_default_graphs                   -- seed canonical procedures
"""
import os
import re
from typing import Optional, List, Dict, Any, Callable

from neo4j.graph import Node, Relationship, Path

from . import bootstrap_procedures


# --- Gate primitives ---------------------------------------------------------

def is_mutation_query(query: str) -> bool:
    """True if the Cypher performs any write (CREATE/MERGE/SET/DELETE/REMOVE/DETACH)."""
    clean = re.sub(r'//.*', '', query)
    clean = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', ' "" ', clean)
    clean = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", " '' ", clean)
    clean = clean.replace('`', '')
    return bool(re.search(r'\b(CREATE|MERGE|SET|DELETE|REMOVE|DETACH)\b',
                          clean, re.IGNORECASE))


def validate_cypher_query(query: str) -> None:
    """Reject writes to :Wiki; require domain+subdomain on every node creation."""
    if not is_mutation_query(query):
        return
    if re.search(r':\bwiki\b', query, re.IGNORECASE):
        raise PermissionError(
            "Security Policy Violation: Write mutations targeting the :Wiki namespace/label are strictly prohibited."
        )
    if not re.search(r'\b(CREATE|MERGE)\b', query, re.IGNORECASE):
        return
    if not re.search(r'\(\s*[a-zA-Z0-9_]*\s*:\s*[a-zA-Z0-9_]+\b', query):
        return
    lower = query.lower()
    if 'domain' not in lower or 'subdomain' not in lower:
        raise PermissionError(
            "Security Policy Violation: Node creation/merge queries (CREATE or MERGE with a label) "
            "MUST specify both 'domain' and 'subdomain' properties."
        )
    domain_m = re.search(r"(?i)domain\s*:\s*['\"]([a-zA-Z0-9_-]+)['\"]", query)
    subdomain_m = re.search(r"(?i)subdomain\s*:\s*['\"]([a-zA-Z0-9_-]+)['\"]", query)
    if not (domain_m and subdomain_m):
        return
    domain = domain_m.group(1).lower()
    subdomain = subdomain_m.group(1).lower()
    if domain == "cyberneticity":
        allowed = {
            'cybernet', 'identity', 'execution_state', 'state_machine',
            'traversal', 'traversal_state', 'simulation', 'mindpalace',
            'page', 'block', 'task_list', 'task', 'skill',
            'finding', 'place',
        }
        if subdomain not in allowed:
            raise PermissionError(
                f"Ontoshamanisic Security Violation: Subdomain '{subdomain}' is not a valid "
                f"subdomain in the 'cyberneticity' domain. Allowed: {sorted(allowed)}"
            )


# --- Serialization + cypher execution ----------------------------------------

def serialize_value(value: Any) -> Any:
    if isinstance(value, Node):
        return {"id": value.element_id, "labels": list(value.labels), "properties": dict(value)}
    if isinstance(value, Relationship):
        return {"id": value.element_id, "type": value.type,
                "start_node_id": value.start_node.element_id,
                "end_node_id": value.end_node.element_id, "properties": dict(value)}
    if isinstance(value, Path):
        return {"nodes": [serialize_value(n) for n in value.nodes],
                "relationships": [serialize_value(r) for r in value.relationships]}
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serialize_value(v) for v in value]
    return value


def run_cypher(query: str, parameters: Dict[str, Any],
               get_driver: Callable, serialize: Callable) -> List[Dict[str, Any]]:
    """Execute query against the driver, returning records as JSON-safe dicts."""
    results: List[Dict[str, Any]] = []
    with get_driver().session() as session:
        for record in session.run(query, parameters):
            results.append({k: serialize(record[k]) for k in record.keys()})
    return results


# --- Active step + transitions -----------------------------------------------

def _append_instruction_file(text: Optional[str], file_path: Optional[str],
                             logger) -> Optional[str]:
    if not file_path or not os.path.exists(file_path):
        return text
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"{text}\n\n=== INSTRUCTION FILE CONTENT ===\n{content}" if text else content
    except Exception as e:
        logger.error(f"Error reading instruction file {file_path}: {e}")
        return text


def get_active_traversal_step(cybernet_name: str, get_driver: Callable,
                              sm_cypher, logger) -> Optional[Dict[str, Any]]:
    """Read the locked step (via the cybernet's ExecutionState) per-cybernet scope."""
    try:
        with get_driver().session() as session:
            record = session.run(sm_cypher.get_active_traversal_step_cypher(),
                                 cybernet_name=cybernet_name).single()
            if not record:
                return None
            text = _append_instruction_file(record["text"], record["instruction_file_path"], logger)
            state = {
                "id": record["id"], "text": text,
                "instruction_file_path": record["instruction_file_path"],
                "required_pattern": record["required_pattern"],
                "pattern_description": record["pattern_description"],
                "state_element_id": record["state_element_id"],
                "transitions": [],
            }
            for tr in session.run(sm_cypher.get_outgoing_transitions_cypher(), curr_id=state["id"]):
                state["transitions"].append(dict(tr))
            return state
    except Exception as e:
        logger.error(f"Error fetching active traversal step: {e}")
    return None


def auto_progress_step(active_step: Dict[str, Any], target_step_id: Optional[str],
                       get_driver: Callable, sm_cypher, logger) -> str:
    """Advance this ExecutionState to its next (or explicit) TraversalStep."""
    state_id, curr_id = active_step["state_element_id"], active_step["id"]
    with get_driver().session() as session:
        next_id = target_step_id
        if not next_id:
            rec = session.run(sm_cypher.next_step_id_cypher(), curr_id=curr_id).single()
            if rec:
                next_id = rec["id"]
        if not next_id:
            session.run(sm_cypher.dissolve_state_cypher(), state_id=state_id)
            msg = f"Traversal Auto-Completed! Final step '{curr_id}' complete. Database writes are UNLOCKED."
            logger.info(msg)
            return msg
        rec = session.run(sm_cypher.read_step_text_cypher(), id=next_id).single()
        text = _append_instruction_file(
            rec["text"] if rec else None,
            rec["fp"] if rec else None,
            logger,
        ) or "No instruction text provided."
        session.run(sm_cypher.advance_state_cypher(), state_id=state_id, next_id=next_id)
        msg = f"Traversal Auto-Progressed! Step '{curr_id}' complete. Next step: '{next_id}' - {text}"
        logger.info(msg)
        return msg


# --- Trigger scan (locks an existing ExecutionState if a node has trigger_traversal)

def _find_trigger(val):
    if isinstance(val, dict):
        if "labels" in val and "properties" in val and "id" in val:
            props = val.get("properties") or {}
            if props.get("trigger_traversal"):
                return props["trigger_traversal"], val["id"], (val["labels"] or ["Node"])[0]
        for v in val.values():
            t = _find_trigger(v)
            if t: return t
    elif isinstance(val, (list, tuple)):
        for v in val:
            t = _find_trigger(v)
            if t: return t
    return None


def scan_and_trigger_traversal(results: List[Dict[str, Any]], cybernet_name: Optional[str],
                               get_driver: Callable, sm_cypher, logger) -> None:
    found = None
    for r in results:
        found = found or _find_trigger(r)
    if not found:
        return
    if not cybernet_name:
        # No cybernet to scope the lock to — cannot safely activate a flow without
        # knowing WHO retrieved the trigger node, so skip rather than lock a random
        # cybernet's cursor.
        return
    step_id, target_id, target_label = found
    try:
        with get_driver().session() as session:
            if session.run(sm_cypher.count_locked_states_cypher(),
                           cybernet_name=cybernet_name).single()["c"]:
                return
            if not session.run(sm_cypher.step_exists_cypher(), id=step_id).peek():
                session.run(sm_cypher.create_placeholder_step_cypher(),
                            id=step_id, text=f"Guided checklist starting at {step_id}.")
            session.run(sm_cypher.lock_and_align_state_cypher(),
                        cybernet_name=cybernet_name,
                        step_id=step_id, tid=target_id, tl=target_label)
    except Exception as e:
        logger.error(f"Failed to auto-trigger traversal: {e}")


def trigger_traversal_by_location(cybernet_name: Optional[str], location: Optional[str],
                                  get_driver: Callable, sm_cypher, logger) -> None:
    """The progressive-disclosure bridge, automated: a reported filesystem location
    maps (via a :Place node) to a flow, and entering that location locks the
    reporting cybernet into the flow — same mechanism as scan_and_trigger, but the
    trigger is WHERE you are, not what a query returned.

    No-op unless: a location is reported, a cybernet is named to scope the lock,
    the location maps to a :Place with a trigger_traversal, and that cybernet is
    not already locked (don't interrupt a live flow)."""
    if not location or not cybernet_name:
        return
    try:
        with get_driver().session() as session:
            place = session.run(sm_cypher.find_place_trigger_cypher(), location=location).single()
            if not place:
                return
            step_id = place["step_id"]
            if session.run(sm_cypher.count_locked_states_cypher(),
                           cybernet_name=cybernet_name).single()["c"]:
                return
            if not session.run(sm_cypher.step_exists_cypher(), id=step_id).peek():
                session.run(sm_cypher.create_placeholder_step_cypher(),
                            id=step_id, text=f"Guided checklist starting at {step_id}.")
            session.run(sm_cypher.lock_and_align_state_cypher(),
                        cybernet_name=cybernet_name,
                        step_id=step_id, tid=None, tl=None)
            logger.info(f"Travel: {cybernet_name} entered {location} → locked into {step_id}")
    except Exception as e:
        logger.error(f"Failed to trigger traversal by location: {e}")


# --- Schema + transition weight (public surface, impls in lib) --------------

def get_schema(get_driver: Callable) -> Dict[str, List[str]]:
    schema = {"labels": [], "relationship_types": [], "property_keys": []}
    with get_driver().session() as session:
        schema["labels"] = [r["label"] for r in session.run("CALL db.labels()")]
        schema["relationship_types"] = [r["relationshipType"] for r in session.run("CALL db.relationshipTypes()")]
        schema["property_keys"] = [r["propertyKey"] for r in session.run("CALL db.propertyKeys()")]
    return schema


def adjust_transition_weight_internal(from_step_id: str, to_step_id: str,
                                      success: bool, cybernet_name: str,
                                      get_driver: Callable, logger) -> str:
    """Adjust NEXT_STEP weight by ±0.1 (calibration reinforcement)."""
    try:
        with get_driver().session() as session:
            rec = session.run(
                """
                MATCH (:TraversalStep {id: $from_id})-[r:NEXT_STEP]->(:TraversalStep {id: $to_id})
                RETURN r.weight as weight
                """, from_id=from_step_id, to_id=to_step_id,
            ).single()
            if not rec:
                raise ValueError(f"Transition from '{from_step_id}' to '{to_step_id}' does not exist.")
            curr = rec["weight"]
            new = curr + 0.1 if success else max(0.1, curr - 0.2)
            session.run(
                """
                MATCH (:TraversalStep {id: $from_id})-[r:NEXT_STEP]->(:TraversalStep {id: $to_id})
                SET r.weight = $weight, r.last_adjusted_by_cybernet = $cn
                """, from_id=from_step_id, to_id=to_step_id, weight=new, cn=cybernet_name,
            )
        return f"Transition weight from '{from_step_id}' to '{to_step_id}' adjusted to {new:.2f} (by cybernet '{cybernet_name}')."
    except Exception as e:
        logger.error(f"Failed to adjust transition weight: {e}")
        raise RuntimeError(f"Failed to adjust transition: {e}")


# --- Bootstrap (canonical procedure seeding) ---------------------------------

def _merge_steps(tx, steps: List[Dict[str, Any]]) -> None:
    for step in steps:
        tx.run(
            """
            MERGE (step:TraversalStep {id: $id})
            SET step.text = $text, step.required_pattern = $required_pattern,
                step.pattern_description = $pattern_description,
                step.domain = 'cyberneticity', step.subdomain = 'traversal'
            """,
            id=step["id"], text=step["text"],
            required_pattern=step["required_pattern"],
            pattern_description=step["pattern_description"],
        )


def _link_steps(tx, steps: List[Dict[str, Any]]) -> None:
    for i in range(len(steps) - 1):
        curr_id, next_id = steps[i]["id"], steps[i + 1]["id"]
        tx.run(
            """
            MATCH (curr:TraversalStep {id: $curr_id})
            MATCH (next:TraversalStep {id: $next_id})
            MERGE (curr)-[r:NEXT_STEP]->(next)
            ON CREATE SET r.weight = 1.0, r.description = $desc
            """,
            curr_id=curr_id, next_id=next_id, desc=f"Transition from {curr_id} to {next_id}",
        )


def _anchor_procedure(tx, proc: Dict[str, Any]) -> None:
    tx.run(
        """
        MERGE (sm:StateMachine {id: $sm_id})
        SET sm.name = $sm_name, sm.description = $sm_desc,
            sm.domain = 'cyberneticity', sm.subdomain = 'state_machine'
        """,
        sm_id=proc["sm_id"], sm_name=proc["sm_name"], sm_desc=proc["sm_desc"],
    )
    for step in proc["steps"]:
        tx.run(
            """
            MATCH (sm:StateMachine {id: $sm_id})
            MATCH (step:TraversalStep {id: $step_id})
            MERGE (sm)-[:HAS_STEP]->(step)
            """, sm_id=proc["sm_id"], step_id=step["id"],
        )
    tx.run(
        """
        MERGE (t:AgentTask {id: $task_id})
        SET t.title = $task_title, t.trigger_traversal = $trigger,
            t.domain = 'cyberneticity', t.subdomain = 'task'
        """,
        task_id=proc["task_id"], task_title=proc["task_title"], trigger=proc["trigger"],
    )


def populate_default_graphs(driver) -> None:
    """Idempotently seed canonical procedures (steps + StateMachines + entry tasks)."""
    try:
        with driver.session() as session, session.begin_transaction() as tx:
            for proc in bootstrap_procedures.PROCEDURES:
                _merge_steps(tx, proc["steps"])
                _link_steps(tx, proc["steps"])
                _anchor_procedure(tx, proc)
            for standalone in bootstrap_procedures.STANDALONE_STEP_SEQUENCES:
                _merge_steps(tx, standalone["steps"])
                _link_steps(tx, standalone["steps"])
                tx.run(
                    """
                    MERGE (t:AgentTask {id: $task_id})
                    SET t.title = $task_title, t.trigger_traversal = $trigger,
                        t.domain = 'cyberneticity', t.subdomain = 'task'
                    """,
                    task_id=standalone["task_id"], task_title=standalone["task_title"],
                    trigger=standalone["trigger"],
                )
            for from_id, to_sm in bootstrap_procedures.CALLS_SM_EDGES:
                tx.run(
                    """
                    MATCH (s:TraversalStep {id: $from_id})
                    MATCH (sm:StateMachine {id: $to_sm})
                    MERGE (s)-[:CALLS_SM]->(sm)
                    """, from_id=from_id, to_sm=to_sm,
                )
    except Exception as e:
        # Bootstrap is best-effort; log + continue. The driver is already up.
        import logging as _l
        _l.getLogger("cyberneticircus_db_logic").error(f"Bootstrap failed: {e}")
