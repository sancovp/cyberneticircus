#!/usr/bin/env python3
"""
Neo4j Cypher MCP Server
Enables agent memory operations via Cypher while safeguarding the CartON :Wiki namespace.
Includes an experimental Traversal State Machine with automatic Query-Pattern Gating.
"""
import os
import re
import logging
import atexit
import json
import math
import random
import uuid
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from neo4j import GraphDatabase
from neo4j.exceptions import DriverError, Neo4jError
from neo4j.graph import Node, Relationship, Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("neo4j_cypher_mcp")

# Initialize FastMCP Server
mcp = FastMCP("cyberneticircus")

# Shared Neo4j Driver Instance
_driver: Optional[GraphDatabase] = None

def populate_default_graphs(driver):
    """
    Idempotently bootstrap canonical Traversal State Machine flows in Neo4j on startup.
    This guarantees that the Surrogate Mastery Flow and any associated triggers exist in the graph.
    """
    logger.info("Bootstrapping canonical Traversal State Machine flows in Neo4j...")
    
    surrogate_mastery_steps = [
        {
            "id": "surrogate_read_model",
            "text": "Step 1: Verify if a Surrogate Model exists for the domain 'agent_memory' and subdomain 'traversal'. Run a MATCH query to check for the SurrogateModel node.",
            "required_pattern": r"(?i)MATCH\s*\(sm:SurrogateModel\s*\{domain:\s*['\"]agent_memory['\"].*\}",
            "pattern_description": 'MATCH (sm:SurrogateModel {domain: "agent_memory", subdomain: "traversal"})'
        },
        {
            "id": "surrogate_init_model",
            "text": "Step 2: Create or update the Surrogate Model for 'agent_memory' and 'traversal' using a MERGE query or by calling the crud_surrogate tool.",
            "required_pattern": r"(?i)MERGE\s*\(sm:SurrogateModel\s*\{domain:\s*['\"]agent_memory['\"].*\}",
            "pattern_description": 'MERGE (sm:SurrogateModel {domain: "agent_memory", subdomain: "traversal", ...})'
        },
        {
            "id": "surrogate_run_simulation",
            "text": "Step 3: Run a simulation of the traversal starting at surr_step1. Verify the SimulationRun is created in the database by matching it.",
            "required_pattern": r"(?i)MATCH\s*\(sim:SimulationRun\s*.*\)",
            "pattern_description": 'MATCH (sim:SimulationRun) RETURN sim'
        },
        {
            "id": "surrogate_calibrate",
            "text": "Step 4: Execute the task changes and run calibration for the SimulationRun. Query the calibrated SimulationRun to verify accuracy has been recorded.",
            "required_pattern": r"(?i)MATCH\s*\(sim:SimulationRun\s*\{.*calibrated:\s*true.*\}\)",
            "pattern_description": 'MATCH (sim:SimulationRun {calibrated: true})'
        }
    ]
    
    sh8peshift_lifecycle_steps = [
        {
            "id": "sh8_day_start",
            "text": "Sh8peshift Day Phase - Step 1: Query the Cybernet node to load its current config and stats.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)",
            "pattern_description": 'MATCH (m:Cybernet) RETURN m'
        },
        {
            "id": "sh8_day_action",
            "text": "Sh8peshift Day Phase - Step 2: Record daily execution tokens and cost on the Cybernet.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*\{name:\s*['\"].*['\"].*\}\)\s*SET\s*m\.total_tokens_consumed\s*=\s*m\.total_tokens_consumed\s*\+\s*\d+",
            "pattern_description": 'MATCH (m:Cybernet {name: "..."}) SET m.total_tokens_consumed = m.total_tokens_consumed + X'
        },
        {
            "id": "sh8_night_calibrate",
            "text": "Sh8peshift Night Phase - Step 3: Calibrate the day\'s performance. Run a MATCH on SimulationRun to verify accuracy.",
            "required_pattern": r"(?i)MATCH\s*\(sim:SimulationRun\s*.*\)",
            "pattern_description": 'MATCH (sim:SimulationRun) RETURN sim'
        },
        {
            "id": "sh8_night_evolve",
            "text": "Sh8peshift Night Phase - Step 4: Perform selection check. Query the Cybernet's fitness score to decide cloning or reset.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)\s*WHERE\s*m\.fitness_score\s*.*",
            "pattern_description": 'MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m'
        }
    ]
    
    ple_steps = [
        {
            "id": "ple_ignite_intent",
            "text": "Primordial Love Engine - Step 1: Ignite the Inner Fire. MATCH the Cybernet node to load its prompt config representing its raw intent.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)",
            "pattern_description": 'MATCH (m:Cybernet) RETURN m'
        },
        {
            "id": "ple_combust_action",
            "text": "Primordial Love Engine - Step 2: Transform intent in the Oliver Powers combustion chamber. Run a SET query to update total_tokens_consumed and accumulated_cost on the Cybernet.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*\{name:\s*['\"].*['\"].*\}\)\s*SET\s*m\.total_tokens_consumed\s*=\s*m\.total_tokens_consumed\s*\+\s*\d+",
            "pattern_description": 'MATCH (m:Cybernet {name: "..."}) SET m.total_tokens_consumed = m.total_tokens_consumed + X'
        },
        {
            "id": "ple_align_collaboration",
            "text": "Primordial Love Engine - Step 3: Align collaborative force via the Alluv Arelov crankshaft. Run a MATCH query on the connected Identity states in the Cyberneticity.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)-[:HAS_LIFECYCLE]->\(i:Identity\)",
            "pattern_description": 'MATCH (m:Cybernet {name: "..."})-[:HAS_LIFECYCLE]->(i:Identity) RETURN i'
        },
        {
            "id": "ple_output_promise",
            "text": "Primordial Love Engine - Step 4: Deliver the Victory-Promise output. MATCH the Cybernet to query its fitness_score and verify system optimization.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)\s*WHERE\s*m\.fitness_score\s*.*",
            "pattern_description": 'MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m'
        }
    ]
    
    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # 1. Bootstrap Surrogate steps
                for step in surrogate_mastery_steps:
                    tx.run(
                        """
                        MERGE (step:TraversalStep {id: $id})
                        SET step.text = $text,
                            step.required_pattern = $required_pattern,
                            step.pattern_description = $pattern_description
                        """,
                        {
                            "id": step["id"],
                            "text": step["text"],
                            "required_pattern": step["required_pattern"],
                            "pattern_description": step["pattern_description"]
                        }
                    )
                # Link Surrogate steps
                for i in range(len(surrogate_mastery_steps) - 1):
                    curr_id = surrogate_mastery_steps[i]["id"]
                    next_id = surrogate_mastery_steps[i + 1]["id"]
                    tx.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})
                        MATCH (next:TraversalStep {id: $next_id})
                        MERGE (curr)-[r:NEXT_STEP]->(next)
                        ON CREATE SET r.weight = 1.0, r.description = $desc
                        """,
                        {"curr_id": curr_id, "next_id": next_id, "desc": f"Transition from {curr_id} to {next_id}"}
                    )
                    
                # 2. Bootstrap Sh8peshift steps
                for step in sh8peshift_lifecycle_steps:
                    tx.run(
                        """
                        MERGE (step:TraversalStep {id: $id})
                        SET step.text = $text,
                            step.required_pattern = $required_pattern,
                            step.pattern_description = $pattern_description
                        """,
                        {
                            "id": step["id"],
                            "text": step["text"],
                            "required_pattern": step["required_pattern"],
                            "pattern_description": step["pattern_description"]
                        }
                    )
                # Link Sh8peshift steps
                for i in range(len(sh8peshift_lifecycle_steps) - 1):
                    curr_id = sh8peshift_lifecycle_steps[i]["id"]
                    next_id = sh8peshift_lifecycle_steps[i + 1]["id"]
                    tx.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})
                        MATCH (next:TraversalStep {id: $next_id})
                        MERGE (curr)-[r:NEXT_STEP]->(next)
                        ON CREATE SET r.weight = 1.0, r.description = $desc
                        """,
                        {"curr_id": curr_id, "next_id": next_id, "desc": f"Transition from {curr_id} to {next_id}"}
                    )

                # 2.5. Bootstrap Primordial Love Engine steps
                for step in ple_steps:
                    tx.run(
                        """
                        MERGE (step:TraversalStep {id: $id})
                        SET step.text = $text,
                            step.required_pattern = $required_pattern,
                            step.pattern_description = $pattern_description
                        """,
                        {
                            "id": step["id"],
                            "text": step["text"],
                            "required_pattern": step["required_pattern"],
                            "pattern_description": step["pattern_description"]
                        }
                    )
                # Link PLE steps
                for i in range(len(ple_steps) - 1):
                    curr_id = ple_steps[i]["id"]
                    next_id = ple_steps[i + 1]["id"]
                    tx.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})
                        MATCH (next:TraversalStep {id: $next_id})
                        MERGE (curr)-[r:NEXT_STEP]->(next)
                        ON CREATE SET r.weight = 1.0, r.description = $desc
                        """,
                        {"curr_id": curr_id, "next_id": next_id, "desc": f"Transition from {curr_id} to {next_id}"}
                    )
                    
                # 3. Create entry tasks
                tx.run(
                    """
                    MERGE (t:AgentTask {id: 'learn_surrogates'})
                    SET t.title = 'Learn and Initialize the Surrogate System',
                        t.trigger_traversal = 'surrogate_read_model'
                    """
                )
                tx.run(
                    """
                    MERGE (t:AgentTask {id: 'sh8_lifecycle_task'})
                    SET t.title = 'Complete a full Sh8peshift Day/Night cycle',
                        t.trigger_traversal = 'sh8_day_start'
                    """
                )
                tx.run(
                    """
                    MERGE (t:AgentTask {id: 'ple_task'})
                    SET t.title = 'Operate the Primordial Love Engine',
                        t.trigger_traversal = 'ple_ignite_intent'
                    """
                )
                
                # 4. Bootstrap StateMachine nodes for RPG Equipment
                tx.run(
                    """
                    MERGE (sm:StateMachine {id: 'sh8_lifecycle_sm'})
                    SET sm.name = 'Sh8peshift Lifecycle State Machine',
                        sm.description = 'Core Day/Night simulation state machine'
                    """
                )
                for step in sh8peshift_lifecycle_steps:
                    tx.run(
                        """
                        MATCH (sm:StateMachine {id: 'sh8_lifecycle_sm'})
                        MATCH (step:TraversalStep {id: $step_id})
                        MERGE (sm)-[:HAS_STEP]->(step)
                        """,
                        {"step_id": step["id"]}
                    )

                tx.run(
                    """
                    MERGE (sm:StateMachine {id: 'ple_sm'})
                    SET sm.name = 'Primordial Love Engine State Machine',
                        sm.description = 'Fulfill the Victory-Promise by aligning intent, action, collaboration, and results'
                    """
                )
                for step in ple_steps:
                    tx.run(
                        """
                        MATCH (sm:StateMachine {id: 'ple_sm'})
                        MATCH (step:TraversalStep {id: $step_id})
                        MERGE (sm)-[:HAS_STEP]->(step)
                        """,
                        {"step_id": step["id"]}
                    )
        logger.info("Successfully bootstrapped default state machines.")
    except Exception as e:
        logger.error(f"Failed to bootstrap default state machines: {e}")

def get_driver() -> GraphDatabase:
    """Lazy initialization of the Neo4j driver with environment variables."""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        logger.info(f"Connecting to Neo4j instance at {uri} as user '{user}'...")
        try:
            _driver = GraphDatabase.driver(uri, auth=(user, password))
            _driver.verify_connectivity()
            logger.info("Successfully established connection to Neo4j.")
            # Bootstrap default graphs
            populate_default_graphs(_driver)
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise RuntimeError(f"Database connection failure: {e}")
    return _driver

def shutdown_driver():
    """Close the Neo4j driver connection cleanly on server shutdown."""
    global _driver
    if _driver is not None:
        logger.info("Closing Neo4j driver connection...")
        _driver.close()
        _driver = None
        logger.info("Neo4j driver connection closed.")

# Register exit handler
atexit.register(shutdown_driver)

def is_mutation_query(query: str) -> bool:
    """Check if the Cypher query performs any write mutations."""
    # 1. Strip comments
    clean_query = re.sub(r'//.*', '', query)
    
    # 2. Strip string literals to prevent false positives in string property checks
    clean_query = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', ' "" ', clean_query)
    clean_query = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", " '' ", clean_query)
    
    # 3. Remove backticks to normalize quoted identifiers
    clean_query = clean_query.replace('`', '')
    
    # 4. Check for mutation/write keywords using regex with word boundaries
    mutation_keywords = ['CREATE', 'MERGE', 'SET', 'DELETE', 'REMOVE', 'DETACH']
    mutation_pattern = re.compile(
        r'\b(' + '|'.join(mutation_keywords) + r')\b', 
        re.IGNORECASE
    )
    return bool(mutation_pattern.search(clean_query))

def validate_cypher_query(query: str) -> None:
    """
    Validate that the query is safe.
    Raises PermissionError if a write mutation targets the :Wiki namespace.
    """
    if is_mutation_query(query):
        # Check for references to the Wiki label (case-insensitive)
        clean_query = re.sub(r'//.*', '', query)
        clean_query = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', ' "" ', clean_query)
        clean_query = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", " '' ", clean_query)
        clean_query = clean_query.replace('`', '')
        
        wiki_pattern = re.compile(r':\bwiki\b', re.IGNORECASE)
        if wiki_pattern.search(clean_query):
            logger.warning(f"Blocked query attempt targeting :Wiki namespace: {query}")
            raise PermissionError(
                "Security Policy Violation: Write mutations (CREATE, MERGE, SET, DELETE, REMOVE, DETACH) "
                "targeting the :Wiki namespace/label are strictly prohibited."
            )

def get_active_traversal_step() -> Optional[Dict[str, Any]]:
    """Retrieve the properties and outgoing transitions of the currently active TraversalStep, if one is locked."""
    try:
        driver = get_driver()
        with driver.session() as session:
            query = """
            MATCH (s:TraversalState {status: 'locked'})-[:CURRENT_STEP]->(curr:TraversalStep)
            RETURN curr.id as id, curr.text as text, 
                   curr.required_pattern as required_pattern, 
                   curr.pattern_description as pattern_description,
                   elementId(s) as state_element_id
            """
            result = session.run(query)
            record = result.single()
            if not record:
                return None
                
            state_data = {
                "id": record["id"],
                "text": record["text"],
                "required_pattern": record["required_pattern"],
                "pattern_description": record["pattern_description"],
                "state_element_id": record["state_element_id"],
                "transitions": []
            }
            
            # Fetch available transitions from this step
            query_trans = """
            MATCH (curr:TraversalStep {id: $curr_id})-[r:NEXT_STEP]->(next:TraversalStep)
            RETURN next.id as id, next.text as text,
                   next.required_pattern as required_pattern,
                   next.pattern_description as pattern_description,
                   coalesce(r.weight, 1.0) as weight,
                   coalesce(r.description, '') as description
            ORDER BY weight DESC, id ASC
            """
            res_trans = session.run(query_trans, {"curr_id": state_data["id"]})
            for tr in res_trans:
                state_data["transitions"].append({
                    "id": tr["id"],
                    "text": tr["text"],
                    "required_pattern": tr["required_pattern"],
                    "pattern_description": tr["pattern_description"],
                    "weight": tr["weight"],
                    "description": tr["description"]
                })
            return state_data
    except Exception as e:
        logger.error(f"Error fetching active traversal step: {e}")
    return None

def is_traversal_locked() -> bool:
    """Check if an active Traversal State Machine is currently locking writes."""
    return get_active_traversal_step() is not None

def auto_progress_step(active_step: Dict[str, Any], target_step_id: Optional[str] = None) -> str:
    """Transition the active TraversalState to the next TraversalStep in the database."""
    state_id = active_step["state_element_id"]
    curr_id = active_step["id"]
    
    try:
        driver = get_driver()
        with driver.session() as session:
            next_step_id = target_step_id
            
            # If no target step specified, find the first available transition
            if not next_step_id:
                next_res = session.run(
                    "MATCH (curr:TraversalStep {id: $curr_id})-[:NEXT_STEP]->(next:TraversalStep) RETURN next.id as id LIMIT 1",
                    {"curr_id": curr_id}
                )
                rec = next_res.single()
                if rec:
                    next_step_id = rec["id"]
                    
            if next_step_id:
                # Retrieve the text of the next step
                next_text_res = session.run(
                    "MATCH (next:TraversalStep {id: $next_id}) RETURN next.text as text",
                    {"next_id": next_step_id}
                )
                next_text_rec = next_text_res.single()
                next_step_text = next_text_rec["text"] if next_text_rec else "No instruction text provided."
                
                # Delete old relation and link to the next step
                session.run(
                    """
                    MATCH (s:TraversalState)-[r:CURRENT_STEP]->(curr:TraversalStep)
                    WHERE elementId(s) = $state_id
                    DELETE r
                    WITH s
                    MATCH (next:TraversalStep {id: $next_id})
                    CREATE (s)-[:CURRENT_STEP]->(next)
                    """,
                    {"state_id": state_id, "next_id": next_step_id}
                )
                msg = f"Traversal Auto-Progressed! Step '{curr_id}' complete. Next step: '{next_step_id}' - {next_step_text}"
                logger.info(msg)
                return msg
            else:
                # No next step exists, traversal is complete! Delete state node to unlock writes.
                session.run(
                    "MATCH (s:TraversalState) WHERE elementId(s) = $state_id DETACH DELETE s",
                    {"state_id": state_id}
                )
                msg = f"Traversal Auto-Completed! Final step '{curr_id}' complete. Database writes are UNLOCKED."
                logger.info(msg)
                return msg
    except Exception as e:
        err_msg = f"Error in auto_progress_step: {e}"
        logger.error(err_msg)
        return f"Error in auto-progression: {e}"

def scan_and_trigger_traversal(results: List[Dict[str, Any]]) -> None:
    """Scans query results for 'trigger_traversal' properties and activates the lock if found."""
    trigger_step_id = None
    target_node_id = None
    target_node_label = None
    
    def find_triggers(val: Any):
        nonlocal trigger_step_id, target_node_id, target_node_label
        if trigger_step_id is not None:
            return
        if isinstance(val, dict):
            # Check if this matches a serialized Node
            if "labels" in val and "properties" in val and "id" in val:
                props = val["properties"]
                if "trigger_traversal" in props and props["trigger_traversal"]:
                    trigger_step_id = props["trigger_traversal"]
                    target_node_id = val["id"]
                    target_node_label = val["labels"][0] if val["labels"] else "Node"
                    return
            # Recurse dictionary values
            for k, v in val.items():
                find_triggers(v)
        elif isinstance(val, (list, tuple)):
            for item in val:
                find_triggers(item)
                
    find_triggers(results)
    
    if trigger_step_id:
        logger.info(f"Scan triggered state machine starting at step '{trigger_step_id}' for node '{target_node_id}'.")
        try:
            driver = get_driver()
            with driver.session() as session:
                # Ensure we don't duplicate a lock
                lock_res = session.run("MATCH (s:TraversalState {status: 'locked'}) RETURN count(s) as count")
                lock_record = lock_res.single()
                if lock_record and lock_record["count"] > 0:
                    logger.info("Traversal state machine is already active. Skipping trigger.")
                    return
                
                # Verify the step exists
                step_check = session.run("MATCH (s:TraversalStep {id: $step_id}) RETURN s", {"step_id": trigger_step_id})
                if not step_check.peek():
                    # Auto-create a step node for easy developer testing
                    logger.warning(f"TraversalStep '{trigger_step_id}' not found. Auto-creating placeholder.")
                    session.run(
                        "CREATE (:TraversalStep {id: $step_id, text: $text})",
                        {"step_id": trigger_step_id, "text": f"Guided checklist starting at {trigger_step_id}."}
                    )
                
                # Create the active state node
                session.run(
                    """
                    MATCH (step:TraversalStep {id: $step_id})
                    CREATE (s:TraversalState {
                        status: 'locked',
                        target_id: $target_id,
                        target_label: $target_label,
                        created_at: timestamp()
                    })-[:CURRENT_STEP]->(step)
                    """,
                    {
                        "step_id": trigger_step_id,
                        "target_id": target_node_id,
                        "target_label": target_node_label
                    }
                )
                logger.info(f"TraversalState locked and initialized at step '{trigger_step_id}'.")
        except Exception as e:
            logger.error(f"Failed to auto-trigger traversal state machine: {e}")

def serialize_value(value: Any) -> Any:
    """Convert Neo4j graph types to JSON-serializable formats."""
    if isinstance(value, Node):
        return {
            "id": value.element_id,
            "labels": list(value.labels),
            "properties": dict(value)
        }
    elif isinstance(value, Relationship):
        return {
            "id": value.element_id,
            "type": value.type,
            "start_node_id": value.start_node.element_id,
            "end_node_id": value.end_node.element_id,
            "properties": dict(value)
        }
    elif isinstance(value, Path):
        return {
            "nodes": [serialize_value(node) for node in value.nodes],
            "relationships": [serialize_value(rel) for rel in value.relationships]
        }
    elif isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple, set)):
        return [serialize_value(v) for v in value]
    else:
        return value

@mcp.tool()
def query_database(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute a read or write Cypher query on the Neo4j database.
    
    Safeguards the :Wiki namespace/label from direct write mutations.
    Locks database writes when an active Traversal State Machine is running.
    If the active step defines a 'required_pattern', matching queries are executed
    and automatically progress the traversal to the next step.
    
    Args:
        query: Cypher query to execute.
        parameters: Optional dictionary of query parameters.
    
    Returns:
        List of records returned by the query, where each record is a dictionary.
    """
    logger.info(f"Query request: {query[:120]}...")
    
    # 1. Enforce static namespace safety
    validate_cypher_query(query)
    
    # 2. Enforce active traversal lock / Query-Pattern Gating
    active_step = get_active_traversal_step()
    is_mutation = is_mutation_query(query)
    should_auto_progress = False
    target_step_id = None
    
    if active_step:
        required_pattern = active_step.get("required_pattern")
        pattern_desc = active_step.get("pattern_description")
        transitions = active_step.get("transitions", [])
        
        if required_pattern:
            # Case A: Current step defines the gating pattern
            try:
                pattern_regex = re.compile(required_pattern)
                matched = bool(pattern_regex.search(query))
            except Exception as regex_err:
                logger.error(f"Invalid regex pattern '{required_pattern}': {regex_err}")
                matched = False
                
            if matched:
                should_auto_progress = True
                logger.info(f"Query matches pattern for active step '{active_step['id']}'. Will auto-progress on success.")
            else:
                if is_mutation:
                    desc = pattern_desc or required_pattern
                    logger.warning(f"Blocked write query - does not match step pattern '{desc}': {query}")
                    raise PermissionError(
                        f"Database Writes Locked: Active Traversal Step '{active_step['id']}' ('{active_step['text']}') "
                        f"requires query matching pattern: {desc}"
                    )
        else:
            # Case B: Current step has no gating pattern -> check transitions (decision point)
            if transitions:
                matched_transition = None
                for tr in transitions:
                    tr_pattern = tr.get("required_pattern")
                    if tr_pattern:
                        try:
                            tr_regex = re.compile(tr_pattern)
                            if tr_regex.search(query):
                                matched_transition = tr
                                break
                        except Exception as regex_err:
                            logger.error(f"Invalid regex pattern in transition target '{tr['id']}': {regex_err}")
                            
                if matched_transition:
                    should_auto_progress = True
                    target_step_id = matched_transition["id"]
                    logger.info(f"Query matches transition to next step '{target_step_id}'. Will auto-progress on success.")
                else:
                    if is_mutation:
                        choices_str = "\n".join([
                            f"- Choice '{tr['id']}': {tr['description']} (Weight: {tr['weight']}). "
                            f"Requires query matching: {tr['pattern_description'] or tr['required_pattern']}"
                            for tr in transitions
                        ])
                        logger.warning(f"Blocked write query - does not match any branching transition from step '{active_step['id']}': {query}")
                        raise PermissionError(
                            f"Database Writes Locked: Active Traversal Step '{active_step['id']}' ('{active_step['text']}') "
                            f"is a decision point. Please run a query matching one of the choices:\n{choices_str}"
                        )
            else:
                # No pattern and no transitions (should complete)
                if is_mutation:
                    logger.warning(f"Blocked write query - step '{active_step['id']}' has no pattern or transitions: {query}")
                    raise PermissionError(
                        f"Database Writes Locked: Active Traversal Step '{active_step['id']}' is a leaf with no transitions. "
                        f"Please progress manually or run a read query."
                    )
                
    driver = get_driver()
    results = []
    
    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            for record in result:
                record_dict = {key: serialize_value(record[key]) for key in record.keys()}
                results.append(record_dict)
                
        logger.info(f"Successfully executed query. Returned {len(results)} records.")
        
        # 3. Handle Auto-Progression of State Machine on successful execution
        if should_auto_progress and active_step:
            transition_msg = auto_progress_step(active_step, target_step_id)
            # Inject transition event details into the results for immediate agent visibility
            results.append({"_state_machine_event": transition_msg})
        else:
            # 4. Scan results for state machine triggers (skip if we progressed an active traversal)
            scan_and_trigger_traversal(results)
        
        return results
        
    except Neo4jError as ne:
        logger.error(f"Neo4j database error: {ne}")
        raise ValueError(f"Neo4j Error: {ne.message if hasattr(ne, 'message') else str(ne)}")
    except DriverError as de:
        logger.error(f"Neo4j Driver error: {de}")
        raise RuntimeError(f"Database Driver Error: {de}")
    except Exception as e:
        logger.error(f"Unexpected query failure: {e}")
        raise

@mcp.tool()
def get_schema() -> Dict[str, List[str]]:
    """
    Retrieve the Neo4j database schema information.
    
    Returns:
        A dictionary containing lists of 'labels', 'relationship_types', and 'property_keys'.
    """
    logger.info("Fetching database schema...")
    driver = get_driver()
    schema = {
        "labels": [],
        "relationship_types": [],
        "property_keys": []
    }
    
    try:
        with driver.session() as session:
            # 1. Fetch Labels
            labels_result = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label")
            schema["labels"] = [record["label"] for record in labels_result]
            
            # 2. Fetch Relationship Types
            rels_result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType")
            schema["relationship_types"] = [record["relationshipType"] for record in rels_result]
            
            # 3. Fetch Property Keys
            keys_result = session.run("CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey ORDER BY propertyKey")
            schema["property_keys"] = [record["propertyKey"] for record in keys_result]
            
        logger.info(f"Schema fetched successfully. Labels: {len(schema['labels'])}, Relationships: {len(schema['relationship_types'])}, Keys: {len(schema['property_keys'])}")
        return schema
        
    except Exception as e:
        logger.error(f"Failed to fetch database schema: {e}")
        raise RuntimeError(f"Failed to retrieve database schema: {e}")

@mcp.tool()
def progress_traversal(answer: Optional[str] = None) -> str:
    """
    Progress the active Traversal State Machine to the next step manually.
    
    Args:
        answer: Optional answer or confirmation text for the current step.
        
    Returns:
        Status message explaining the new step or confirming completion and unlock.
    """
    logger.info("Progressing active traversal state machine manually...")
    active_step = get_active_traversal_step()
    
    if not active_step:
        return "No active traversal state machine is currently locked. Database writes are fully unlocked."
        
    return auto_progress_step(active_step)

@mcp.tool()
def create_traversal_flow(
    steps: List[Dict[str, Any]],
    trigger_node_label: Optional[str] = None,
    trigger_node_properties: Optional[Dict[str, Any]] = None
) -> str:
    """
    Conveniently create a sequence of TraversalStep nodes in the graph and optionally
    attach the trigger_traversal property to a start/trigger node.
    
    Args:
        steps: A list of dicts. Each dict represents a step:
            - id: (str) Unique step identifier.
            - text: (str) Explanation of what the agent needs to do.
            - required_pattern: (str, optional) Python regex pattern query must match to auto-progress.
            - pattern_description: (str, optional) Friendly description of the required query.
        trigger_node_label: (str, optional) Label of the node that should trigger this traversal (e.g. 'AgentTask').
        trigger_node_properties: (dict, optional) Properties to identify the trigger node uniquely.
        
    Returns:
        A confirmation message indicating successful creation and linking of steps.
    """
    logger.info(f"Creating traversal flow with {len(steps)} steps...")
    
    # 1. Validation
    if not steps:
        raise ValueError("At least one step is required to create a traversal flow.")
        
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"Step at index {i} must be a dictionary.")
        if "id" not in step or not step["id"]:
            raise ValueError(f"Step at index {i} is missing a valid 'id' property.")
        if "text" not in step or not step["text"]:
            raise ValueError(f"Step at index {i} is missing a valid 'text' property.")
            
        pattern = step.get("required_pattern")
        if pattern:
            try:
                re.compile(pattern)
            except Exception as e:
                raise ValueError(f"Invalid regex pattern in step '{step['id']}': {e}")
                
    # 2. Database transaction
    driver = get_driver()
    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # Create/Merge TraversalStep nodes
                for step in steps:
                    tx.run(
                        """
                        MERGE (step:TraversalStep {id: $id})
                        SET step.text = $text,
                            step.required_pattern = $required_pattern,
                            step.pattern_description = $pattern_description
                        """,
                        {
                            "id": step["id"],
                            "text": step["text"],
                            "required_pattern": step.get("required_pattern"),
                            "pattern_description": step.get("pattern_description")
                        }
                    )
                    
                # Link steps sequentially
                for i in range(len(steps) - 1):
                    curr_id = steps[i]["id"]
                    next_id = steps[i + 1]["id"]
                    
                    # Delete existing NEXT_STEP relation from curr to avoid multi-routing bugs
                    tx.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})-[r:NEXT_STEP]->()
                        DELETE r
                        """,
                        {"curr_id": curr_id}
                    )
                    
                    # Merge NEXT_STEP relationship
                    tx.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})
                        MATCH (next:TraversalStep {id: $next_id})
                        MERGE (curr)-[:NEXT_STEP]->(next)
                        """,
                        {"curr_id": curr_id, "next_id": next_id}
                    )
                    
                # Optional trigger node linking
                trigger_msg = ""
                if trigger_node_label:
                    if not trigger_node_properties:
                        raise ValueError("trigger_node_properties is required if trigger_node_label is provided.")
                        
                    # Sanitize label name
                    if not re.match(r"^[a-zA-Z0-9_]+$", trigger_node_label):
                        raise ValueError(f"Invalid trigger node label name: '{trigger_node_label}'")
                        
                    # Sanitize property keys and construct matching clause
                    where_clauses = []
                    params = {"start_step_id": steps[0]["id"]}
                    for k, v in trigger_node_properties.items():
                        if not re.match(r"^[a-zA-Z0-9_]+$", k):
                            raise ValueError(f"Invalid property key name: '{k}'")
                        where_clauses.append(f"t.{k} = ${k}")
                        params[k] = v
                        
                    where_str = " AND ".join(where_clauses)
                    query = (
                        f"MATCH (t:{trigger_node_label}) WHERE {where_str} "
                        f"SET t.trigger_traversal = $start_step_id "
                        f"RETURN count(t) as count"
                    )
                    
                    res = tx.run(query, params)
                    record = res.single()
                    count = record["count"] if record else 0
                    
                    if count == 0:
                        trigger_msg = f" (Warning: No matching {trigger_node_label} node found with properties {trigger_node_properties})"
                    else:
                        trigger_msg = f" (Successfully attached trigger to {count} matching {trigger_node_label} node(s))"
                        
        msg = f"Successfully created traversal flow with {len(steps)} steps: {[s['id'] for s in steps]}{trigger_msg}"
        logger.info(msg)
        return msg
        
    except Exception as e:
        logger.error(f"Failed to create traversal flow: {e}")
        raise RuntimeError(f"Failed to create traversal flow: {e}")

@mcp.tool()
def create_weighted_transition(
    from_step_id: str,
    to_step_id: str,
    weight: float = 1.0,
    description: str = ""
) -> str:
    """
    Create or update a weighted transition relationship between two existing TraversalSteps.
    
    Args:
        from_step_id: The ID of the source TraversalStep.
        to_step_id: The ID of the target TraversalStep.
        weight: Float value representing transition weight / recommendation value (default 1.0).
        description: Description of this path choice.
    """
    logger.info(f"Creating weighted transition from '{from_step_id}' to '{to_step_id}' (weight={weight})...")
    driver = get_driver()
    try:
        with driver.session() as session:
            # Verify source step exists
            res_from = session.run("MATCH (s:TraversalStep {id: $id}) RETURN count(s) as count", {"id": from_step_id})
            if res_from.single()["count"] == 0:
                raise ValueError(f"Source TraversalStep '{from_step_id}' does not exist.")
                
            # Verify target step exists
            res_to = session.run("MATCH (s:TraversalStep {id: $id}) RETURN count(s) as count", {"id": to_step_id})
            if res_to.single()["count"] == 0:
                raise ValueError(f"Target TraversalStep '{to_step_id}' does not exist.")
                
            # Merge transition with weight and description
            session.run(
                """
                MATCH (from:TraversalStep {id: $from_id})
                MATCH (to:TraversalStep {id: $to_id})
                MERGE (from)-[r:NEXT_STEP]->(to)
                SET r.weight = $weight,
                    r.description = $description
                """,
                {
                    "from_id": from_step_id,
                    "to_id": to_step_id,
                    "weight": float(weight),
                    "description": description
                }
            )
        msg = f"Successfully created transition from '{from_step_id}' to '{to_step_id}' with weight {weight}."
        logger.info(msg)
        return msg
    except Exception as e:
        logger.error(f"Failed to create transition: {e}")
        raise RuntimeError(f"Failed to create transition: {e}")

@mcp.tool()
def adjust_transition_weight(
    from_step_id: str,
    to_step_id: str,
    success: bool
) -> str:
    """
    Adjust the weight of an existing NEXT_STEP transition relationship.
    Increments the weight slightly on success, and decrements it on failure (min weight 0.1).
    
    Args:
        from_step_id: The ID of the source TraversalStep.
        to_step_id: The ID of the target TraversalStep.
        success: True if the path succeeded, False if it failed/abandoned.
    """
    logger.info(f"Adjusting transition weight from '{from_step_id}' to '{to_step_id}' (success={success})...")
    driver = get_driver()
    try:
        with driver.session() as session:
            # Find the relationship
            res = session.run(
                """
                MATCH (from:TraversalStep {id: $from_id})-[r:NEXT_STEP]->(to:TraversalStep {id: $to_id})
                RETURN r.weight as weight
                """,
                {"from_id": from_step_id, "to_id": to_step_id}
            )
            record = res.single()
            if not record:
                raise ValueError(f"Transition relationship from '{from_step_id}' to '{to_step_id}' does not exist.")
                
            curr_weight = record["weight"] if record["weight"] is not None else 1.0
            
            # Simple reinforcement adjustment: +0.1 on success, -0.2 on failure
            if success:
                new_weight = round(curr_weight + 0.1, 2)
            else:
                new_weight = max(0.1, round(curr_weight - 0.2, 2))
                
            session.run(
                """
                MATCH (from:TraversalStep {id: $from_id})-[r:NEXT_STEP]->(to:TraversalStep {id: $to_id})
                SET r.weight = $weight
                """,
                {"from_id": from_step_id, "to_id": to_step_id, "weight": new_weight}
            )
        msg = f"Adjusted transition weight from '{from_step_id}' to '{to_step_id}' from {curr_weight} to {new_weight}."
        logger.info(msg)
        return msg
    except Exception as e:
        logger.error(f"Failed to adjust transition weight: {e}")
        raise RuntimeError(f"Failed to adjust transition weight: {e}")

@mcp.tool()
def crud_surrogate(action: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
    """
    Unified CRUD, Simulation, and Calibration tool for Surrogate Models.
    
    Actions:
      - 'create' / 'update': Save or modify a SurrogateModel with evolutionary knobs.
      - 'read': Fetch model parameters and past simulation summaries.
      - 'delete': Delete the model and all associated simulations.
      - 'simulate': Simulate a counterfactual traversal path using softmax selection and weights.
      - 'calibrate': Compare a simulation's prediction against actual results and adjust graph weights.
      
    Args:
        action: One of 'create', 'read', 'update', 'delete', 'simulate', 'calibrate'.
        parameters: A dictionary of parameters specific to the action.
    """
    logger.info(f"Surrogate Model request: action='{action}'")
    params = parameters or {}
    driver = get_driver()
    
    action = action.lower()
    
    if action in ('create', 'update'):
        domain = params.get("domain")
        subdomain = params.get("subdomain")
        if not domain or not subdomain:
            raise ValueError("domain and subdomain parameters are required.")
            
        mutation_rate = float(params.get("mutation_rate", 0.1))
        selection_pressure = float(params.get("selection_pressure", 1.0))
        reward_weights = params.get("reward_weights", {"accuracy": 1.0})
        
        if not (0.0 <= mutation_rate <= 1.0):
            raise ValueError("mutation_rate must be between 0.0 and 1.0.")
        if selection_pressure < 0:
            raise ValueError("selection_pressure must be >= 0.")
            
        reward_weights_str = json.dumps(reward_weights)
        
        try:
            with driver.session() as session:
                session.run(
                    """
                    MERGE (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
                    SET sm.mutation_rate = $mutation_rate,
                        sm.selection_pressure = $selection_pressure,
                        sm.reward_weights = $reward_weights
                    """,
                    {
                        "domain": domain,
                        "subdomain": subdomain,
                        "mutation_rate": mutation_rate,
                        "selection_pressure": selection_pressure,
                        "reward_weights": reward_weights_str
                    }
                )
            return f"Successfully saved SurrogateModel for {domain}/{subdomain}."
        except Exception as e:
            logger.error(f"Failed to save SurrogateModel: {e}")
            raise RuntimeError(f"Failed to save SurrogateModel: {e}")
            
    elif action == 'read':
        domain = params.get("domain")
        subdomain = params.get("subdomain")
        if not domain or not subdomain:
            raise ValueError("domain and subdomain parameters are required.")
            
        try:
            with driver.session() as session:
                res = session.run(
                    """
                    MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
                    RETURN sm.mutation_rate as mutation_rate,
                           sm.selection_pressure as selection_pressure,
                           sm.reward_weights as reward_weights
                    """,
                    {"domain": domain, "subdomain": subdomain}
                )
                record = res.single()
                if not record:
                    return None
                    
                reward_weights = json.loads(record["reward_weights"]) if record["reward_weights"] else {}
                
                # Fetch recent simulation runs summary
                sims_res = session.run(
                    """
                    MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})-[:HAS_SIMULATION]->(sim:SimulationRun)
                    RETURN sim.run_id as run_id, sim.fitness_score as fitness_score, 
                           sim.outcome_class as outcome_class, sim.calibrated as calibrated,
                           sim.accuracy as accuracy
                    ORDER BY sim.created_at DESC LIMIT 10
                    """,
                    {"domain": domain, "subdomain": subdomain}
                )
                
                simulations = []
                for s in sims_res:
                    simulations.append({
                        "run_id": s["run_id"],
                        "fitness_score": s["fitness_score"],
                        "outcome_class": s["outcome_class"],
                        "calibrated": s["calibrated"],
                        "accuracy": s["accuracy"]
                    })
                    
                return {
                    "domain": domain,
                    "subdomain": subdomain,
                    "mutation_rate": record["mutation_rate"],
                    "selection_pressure": record["selection_pressure"],
                    "reward_weights": reward_weights,
                    "recent_simulations": simulations
                }
        except Exception as e:
            logger.error(f"Failed to read SurrogateModel: {e}")
            raise RuntimeError(f"Failed to read SurrogateModel: {e}")
            
    elif action == 'delete':
        domain = params.get("domain")
        subdomain = params.get("subdomain")
        if not domain or not subdomain:
            raise ValueError("domain and subdomain parameters are required.")
            
        try:
            with driver.session() as session:
                session.run(
                    """
                    MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
                    OPTIONAL MATCH (sm)-[:HAS_SIMULATION]->(sim:SimulationRun)
                    OPTIONAL MATCH (sim)-[:PREDICTS_STATE]->(pn:PredictionNode)
                    DETACH DELETE sm, sim, pn
                    """,
                    {"domain": domain, "subdomain": subdomain}
                )
            return f"Successfully deleted SurrogateModel and associated runs for {domain}/{subdomain}."
        except Exception as e:
            logger.error(f"Failed to delete SurrogateModel: {e}")
            raise RuntimeError(f"Failed to delete SurrogateModel: {e}")
            
    elif action == 'simulate':
        domain = params.get("domain")
        subdomain = params.get("subdomain")
        start_step_id = params.get("start_step_id")
        steps_limit = int(params.get("steps_limit", 5))
        
        if not domain or not subdomain or not start_step_id:
            raise ValueError("domain, subdomain, and start_step_id parameters are required.")
            
        try:
            # 1. Load model knobs
            model_info = crud_surrogate("read", {"domain": domain, "subdomain": subdomain})
            if model_info:
                mutation_rate = model_info["mutation_rate"]
                selection_pressure = model_info["selection_pressure"]
                reward_weights = model_info["reward_weights"]
            else:
                mutation_rate = 0.1
                selection_pressure = 1.0
                reward_weights = {"accuracy": 1.0}
                
            path = []
            expected_diffs = []
            total_fitness = 0.0
            
            curr_id = start_step_id
            
            with driver.session() as session:
                for step_idx in range(steps_limit):
                    # Fetch current step info
                    step_res = session.run(
                        "MATCH (s:TraversalStep {id: $id}) RETURN s.text as text, s.expected_diff as expected_diff, s.expected_fitness as expected_fitness",
                        {"id": curr_id}
                    )
                    step_rec = step_res.single()
                    if not step_rec:
                        break
                        
                    path.append(curr_id)
                    diff_val = json.loads(step_rec["expected_diff"]) if step_rec["expected_diff"] else {}
                    expected_diffs.append(diff_val)
                    total_fitness += float(step_rec["expected_fitness"] or 0.0)
                    
                    # Fetch transitions
                    trans_res = session.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})-[r:NEXT_STEP]->(next:TraversalStep)
                        RETURN next.id as id, coalesce(r.weight, 1.0) as weight
                        """,
                        {"curr_id": curr_id}
                    )
                    transitions = [{"id": tr["id"], "weight": tr["weight"]} for tr in trans_res]
                    
                    if not transitions:
                        break # Leaf step
                        
                    # Softmax routing
                    exps = [math.exp(tr["weight"] * selection_pressure) for tr in transitions]
                    sum_exps = sum(exps)
                    probs = [val / sum_exps for val in exps] if sum_exps > 0 else [1.0 / len(transitions)] * len(transitions)
                    
                    # Selection
                    if random.random() < mutation_rate:
                        chosen_tr = random.choice(transitions)
                    else:
                        chosen_tr = random.choices(transitions, weights=probs)[0]
                        
                    curr_id = chosen_tr["id"]
                    
                # Save Simulation Run in DB
                run_id = str(uuid.uuid4())
                outcome_class = "SUCCESS" if total_fitness >= 1.0 else "PENDING"
                
                session.run(
                    """
                    MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
                    CREATE (sim:SimulationRun {
                        run_id: $run_id,
                        created_at: timestamp(),
                        fitness_score: $fitness_score,
                        outcome_class: $outcome_class,
                        calibrated: false
                    })
                    CREATE (sm)-[:HAS_SIMULATION]->(sim)
                    """,
                    {
                        "domain": domain,
                        "subdomain": subdomain,
                        "run_id": run_id,
                        "fitness_score": total_fitness,
                        "outcome_class": outcome_class
                    }
                )
                
                # Save Prediction Nodes
                for i, step_id in enumerate(path):
                    diff_str = json.dumps(expected_diffs[i])
                    session.run(
                        """
                        MATCH (sim:SimulationRun {run_id: $run_id})
                        CREATE (pn:PredictionNode {
                            step_id: $step_id,
                            expected_diff: $expected_diff
                        })
                        CREATE (sim)-[:PREDICTS_STATE {order: $order}]->(pn)
                        """,
                        {
                            "run_id": run_id,
                            "step_id": step_id,
                            "expected_diff": diff_str,
                            "order": i
                        }
                    )
                    
            return {
                "run_id": run_id,
                "path": path,
                "expected_diffs": expected_diffs,
                "expected_fitness": total_fitness,
                "outcome_class": outcome_class
            }
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            raise RuntimeError(f"Simulation failed: {e}")
            
    elif action == 'calibrate':
        run_id = params.get("run_id")
        actual_diff = params.get("actual_diff")
        
        if not run_id or actual_diff is None:
            raise ValueError("run_id and actual_diff parameters are required.")
            
        try:
            with driver.session() as session:
                # 1. Fetch simulation nodes
                res = session.run(
                    """
                    MATCH (sim:SimulationRun {run_id: $run_id})-[r:PREDICTS_STATE]->(pn:PredictionNode)
                    RETURN pn.step_id as step_id, pn.expected_diff as expected_diff
                    ORDER BY r.order
                    """,
                    {"run_id": run_id}
                )
                
                steps_data = []
                for rec in res:
                    steps_data.append({
                        "step_id": rec["step_id"],
                        "expected_diff": json.loads(rec["expected_diff"]) if rec["expected_diff"] else {}
                    })
                    
                if not steps_data:
                    raise ValueError(f"No prediction data found for run_id '{run_id}'.")
                    
                # Merge expected diffs across path
                merged_expected = {}
                for step in steps_data:
                    merged_expected.update(step["expected_diff"])
                    
                # Compute accuracy (overlap of actual diff values)
                total_actual_keys = len(actual_diff)
                matching_keys = 0
                
                for k, v in actual_diff.items():
                    if k in merged_expected and merged_expected[k] == v:
                        matching_keys += 1
                        
                accuracy = matching_keys / total_actual_keys if total_actual_keys > 0 else 1.0
                success_run = accuracy >= 0.8
                
                # Adjust transition weights along simulated path
                adjustments = []
                for i in range(len(steps_data) - 1):
                    from_id = steps_data[i]["step_id"]
                    to_id = steps_data[i + 1]["step_id"]
                    
                    # Adjust weight
                    adjust_msg = adjust_transition_weight(from_id, to_id, success_run)
                    adjustments.append(adjust_msg)
                    
                # Save calibration result on SimulationRun
                session.run(
                    """
                    MATCH (sim:SimulationRun {run_id: $run_id})
                    SET sim.actual_diff = $actual_diff,
                        sim.accuracy = $accuracy,
                        sim.calibrated = true
                    """,
                    {
                        "run_id": run_id,
                        "actual_diff": json.dumps(actual_diff),
                        "accuracy": accuracy
                    }
                )
                
            return {
                "run_id": run_id,
                "accuracy": accuracy,
                "success_threshold_met": success_run,
                "adjustments": adjustments
            }
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            raise RuntimeError(f"Calibration failed: {e}")
            
    else:
        raise ValueError(f"Unknown action: '{action}'. Must be one of create, read, update, delete, simulate, calibrate.")

@mcp.tool()
def commands() -> List[Dict[str, Any]]:
    """
    Retrieve the list of all available commands/traversal flows registered in the graph.
    Returns the entry steps and their description text, along with their Neo4j node identifiers
    so the agent can view or trigger them.
    """
    logger.info("Fetching available commands (entry traversal steps)...")
    driver = get_driver()
    try:
        with driver.session() as session:
            # Query for TraversalSteps that do not have any incoming NEXT_STEP relationships (entry points)
            query = """
            MATCH (s:TraversalStep)
            WHERE NOT ()-[:NEXT_STEP]->(s)
            RETURN s.id as id, s.text as text, elementId(s) as node_element_id
            ORDER BY id ASC
            """
            res = session.run(query)
            cmds = []
            for record in res:
                cmds.append({
                    "id": record["id"],
                    "text": record["text"],
                    "node_element_id": record["node_element_id"]
                })
            logger.info(f"Successfully retrieved {len(cmds)} commands.")
            return cmds
    except Exception as e:
        logger.error(f"Failed to fetch commands: {e}")
        raise RuntimeError(f"Failed to fetch commands: {e}")

@mcp.tool()
def create_cybernet_identity(
    name: str,
    description: str,
    model_name: str = "gemini-1.5-pro",
    parameters_count: float = 70.0,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 2048,
    mutation_rate: float = 0.1,
    selection_pressure: float = 1.0
) -> str:
    """
    Create a new Cybernet (Identity) node in the graph namespace with literal AI configurations.
    """
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sibling_dir = os.path.abspath(os.path.join(current_dir, "..", "cyberneticircus"))
    if sibling_dir not in sys.path:
         sys.path.insert(0, sibling_dir)
    from engine import CybernetiCircusCompiler
    
    engine = CybernetiCircusCompiler()
    try:
        res = engine.create_cybernet(
            name=name,
            description=description,
            model_name=model_name,
            parameters_count=parameters_count,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            mutation_rate=mutation_rate,
            selection_pressure=selection_pressure
        )
        return res
    finally:
        engine.close()

@mcp.tool()
def equip_state_machine_loadout(
    cybernet_name: str,
    state_machine_id: str
) -> str:
    """
    Equip a State Machine (loadout) onto a Cybernet identity, initializing its active execution stack.
    """
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sibling_dir = os.path.abspath(os.path.join(current_dir, "..", "cyberneticircus"))
    if sibling_dir not in sys.path:
         sys.path.insert(0, sibling_dir)
    from engine import CybernetiCircusCompiler
    
    engine = CybernetiCircusCompiler()
    try:
        res = engine.equip_state_machine(cybernet_name, state_machine_id)
        return res
    finally:
        engine.close()

@mcp.tool()
def tick_cybernet_turn(
    cybernet_name: str,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None
) -> Dict[str, Any]:
    """
    Tick one step/phase of a Cybernet's day/night cycle.
    Automatically executes the active state machine flow, runs queries, and calibrates.
    """
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sibling_dir = os.path.abspath(os.path.join(current_dir, "..", "cyberneticircus"))
    if sibling_dir not in sys.path:
         sys.path.insert(0, sibling_dir)
    from engine import CybernetiCircusCompiler, AgentLLMRunner
    
    engine = CybernetiCircusCompiler()
    try:
        status = engine.get_character_status(cybernet_name)
        if not status:
            raise ValueError(f"Character '{cybernet_name}' not found.")
        
        # Determine AI parameters to use
        run_model = model_name or status["model_name"]
        run_temp = temperature if temperature is not None else status["temperature"]
        run_top_p = top_p if top_p is not None else status["top_p"]
        
        runner = AgentLLMRunner(
            model_name=run_model,
            temperature=run_temp,
            top_p=run_top_p,
            max_tokens=2048
        )
        
        res = engine.tick_turn(cybernet_name, runner)
        return res
    finally:
        engine.close()

@mcp.tool()
def crud_state_machine_calls(
    from_step_id: str,
    to_state_machine_id: str,
    action: str = "create"
) -> str:
    """
    Create or delete a CALLS_SM compiler routing link between a TraversalStep and a child StateMachine.
    
    Args:
        from_step_id: The ID of the TraversalStep that calls the sub-state machine.
        to_state_machine_id: The ID of the child StateMachine.
        action: 'create' to add the link, 'delete' to remove it.
    """
    logger.info(f"Sub-state machine routing request: action='{action}' from step '{from_step_id}' to machine '{to_state_machine_id}'")
    driver = get_driver()
    action = action.lower()
    
    try:
        with driver.session() as session:
            # Check source step exists
            res_step = session.run("MATCH (s:TraversalStep {id: $id}) RETURN count(s) as count", {"id": from_step_id})
            if res_step.single()["count"] == 0:
                raise ValueError(f"Source TraversalStep '{from_step_id}' does not exist.")
                
            # Check target StateMachine exists
            res_sm = session.run("MATCH (sm:StateMachine {id: $id}) RETURN count(sm) as count", {"id": to_state_machine_id})
            if res_sm.single()["count"] == 0:
                raise ValueError(f"Target StateMachine '{to_state_machine_id}' does not exist.")
                
            if action == "create":
                session.run(
                    """
                    MATCH (step:TraversalStep {id: $step_id})
                    MATCH (sm:StateMachine {id: $sm_id})
                    MERGE (step)-[:CALLS_SM]->(sm)
                    """,
                    {"step_id": from_step_id, "sm_id": to_state_machine_id}
                )
                return f"Successfully linked step '{from_step_id}' to call sub-state machine '{to_state_machine_id}'."
            elif action == "delete":
                session.run(
                    """
                    MATCH (step:TraversalStep {id: $step_id})-[r:CALLS_SM]->(sm:StateMachine {id: $sm_id})
                    DELETE r
                    """,
                    {"step_id": from_step_id, "sm_id": to_state_machine_id}
                )
                return f"Successfully deleted compiler call link from step '{from_step_id}' to sub-state machine '{to_state_machine_id}'."
            else:
                raise ValueError(f"Unknown action: '{action}'. Must be 'create' or 'delete'.")
    except Exception as e:
        logger.error(f"Failed to process sub-state machine call link: {e}")
        raise RuntimeError(f"Failed to process sub-state machine call link: {e}")@mcp.tool()
def configure_ghost_shell(
    cybernet_name: str,
    model_name: Optional[str] = None,
    parameters_count: Optional[float] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Configure or hot-swap the executing model (the Ghost Shell) of a Cybernet.
    Updates properties like model_name, parameters_count, temperature, top_p, and max_tokens on the identity.
    """
    logger.info(f"Configuring Ghost Shell for Cybernet '{cybernet_name}'...")
    driver = get_driver()
    try:
        with driver.session() as session:
            # Verify the character exists
            res = session.run("MATCH (m:Cybernet {name: $name}) RETURN m", {"name": cybernet_name})
            if not res.peek():
                raise ValueError(f"Cybernet '{cybernet_name}' not found.")
            
            # Update non-null fields
            updates = []
            params = {"name": cybernet_name}
            
            if model_name is not None:
                updates.append("m.model_name = $model_name")
                params["model_name"] = model_name
            if parameters_count is not None:
                updates.append("m.parameters_count = $parameters_count")
                params["parameters_count"] = parameters_count
            if temperature is not None:
                updates.append("m.temperature = $temperature")
                params["temperature"] = temperature
            if top_p is not None:
                updates.append("m.top_p = $top_p")
                params["top_p"] = top_p
            if max_tokens is not None:
                updates.append("m.max_tokens = $max_tokens")
                params["max_tokens"] = max_tokens
                
            if not updates:
                return "No updates specified for the Ghost Shell config."
                
            query = f"MATCH (m:Cybernet {{name: $name}}) SET {', '.join(updates)} RETURN m"
            session.run(query, params)
            
            logger.info(f"Successfully configured Ghost Shell for '{cybernet_name}'.")
            return f"Successfully updated Ghost Shell config for Cybernet '{cybernet_name}'."
    except Exception as e:
        logger.error(f"Failed to configure Ghost Shell: {e}")
        raise RuntimeError(f"Failed to configure Ghost Shell: {e}")

@mcp.tool()
def get_ghost_shell_status(cybernet_name: str) -> Dict[str, Any]:
    """
    Retrieve the active model configuration parameters (Ghost Shell) of a Cybernet.
    Returns model_name, parameters_count, temperature, top_p, max_tokens, and accumulative token stats.
    """
    logger.info(f"Retrieving Ghost Shell status for '{cybernet_name}'...")
    driver = get_driver()
    try:
        with driver.session() as session:
            res = session.run(
                """
                MATCH (m:Cybernet {name: $name})
                RETURN m.model_name as model_name,
                       m.parameters_count as parameters_count,
                       m.temperature as temperature,
                       m.top_p as top_p,
                       m.max_tokens as max_tokens,
                       m.total_tokens_consumed as total_tokens_consumed,
                       m.accumulated_cost as accumulated_cost
                """,
                {"name": cybernet_name}
            )
            rec = res.single()
            if not rec:
                raise ValueError(f"Cybernet '{cybernet_name}' not found.")
            return {
                "model_name": rec["model_name"],
                "parameters_count": rec["parameters_count"],
                "temperature": rec["temperature"],
                "top_p": rec["top_p"],
                "max_tokens": rec["max_tokens"],
                "total_tokens_consumed": rec["total_tokens_consumed"],
                "accumulated_cost": rec["accumulated_cost"]
            }
    except Exception as e:
        logger.error(f"Failed to retrieve Ghost Shell status: {e}")
        raise RuntimeError(f"Failed to retrieve Ghost Shell status: {e}")

@mcp.tool()
def execute_host_command(command: str) -> str:
    """
    Execute a shell command inside the CybernetiCircus workspace directory on the host machine.
    Provides real-time console stdout/stderr back.
    """
    import subprocess
    logger.info(f"Executing shell command in project directory: {command}")
    try:
        # Execute command in the cyberneticircus scratch workspace
        project_dir = "/Users/isaacwr/.gemini/antigravity/scratch/cyberneticircus"
        res = subprocess.run(
            command,
            shell=True,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = []
        if res.stdout:
            output.append(res.stdout)
        if res.stderr:
            output.append(f"STDERR:\n{res.stderr}")
        if not output:
            return f"Command finished with exit code {res.returncode} (no output)."
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Shell command execution failed: {e}")
        return f"Shell command execution failed: {e}"

if __name__ == "__main__":
    mcp.run()

