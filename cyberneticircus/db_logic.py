#!/usr/bin/env python3
"""
Shared Neo4j and Traversal Gating Logic for CybernetiCircus.
Consolidates safety validation, regex gating, and query progression rules.
"""
import os
import re
import json
import math
import random
import uuid
import logging
import atexit
from typing import Optional, List, Dict, Any
from neo4j import GraphDatabase
from neo4j.exceptions import DriverError, Neo4jError
from neo4j.graph import Node, Relationship, Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cyberneticircus_db_logic")

# Shared Neo4j Driver Instance
_driver: Optional[GraphDatabase] = None

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
            # Bootstrap default graphs on connection
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
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*[^)]*\)-\[:HAS_IDENTITY\]->\(i:Identity\)",
            "pattern_description": 'MATCH (m:Cybernet {name: "..."})-[:HAS_IDENTITY]->(i:Identity) RETURN i'
        },
        {
            "id": "ple_output_promise",
            "text": "Primordial Love Engine - Step 4: Deliver the Victory-Promise output. MATCH the Cybernet to query its fitness_score and verify system optimization.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)\s*WHERE\s*m\.fitness_score\s*.*",
            "pattern_description": 'MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m'
        }
    ]
    
    concentric_steps = [
        {
            "id": "concentric_spiritual",
            "text": "Spiritual Core - Ignite Intent. MATCH active Cybernet to load its subjective POV and intent parameters.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)",
            "pattern_description": 'MATCH (m:Cybernet) RETURN m'
        },
        {
            "id": "concentric_wealth",
            "text": "Wealth Core - Combust Action. Run a SET query to update resources (total_tokens_consumed, accumulated_cost) on the Cybernet.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*\{name:\s*['\"].*['\"].*\}\)\s*SET\s*m\.total_tokens_consumed\s*=\s*m\.total_tokens_consumed\s*\+\s*\d+",
            "pattern_description": 'MATCH (m:Cybernet {name: "..."}) SET m.total_tokens_consumed = m.total_tokens_consumed + X'
        },
        {
            "id": "concentric_social",
            "text": "Social Core - Align Collaboration. MATCH linked Identities or Concept relationships to verify social coherence.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*[^)]*\)-\[:HAS_IDENTITY\]->\(i:Identity\)",
            "pattern_description": 'MATCH (m:Cybernet {name: "..."})-[:HAS_IDENTITY]->(i:Identity) RETURN i'
        },
        {
            "id": "concentric_health",
            "text": "Health Core - Calibrate Calibration. MATCH to evaluate simulation accuracy and verify J-Invariance.",
            "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)\s*WHERE\s*m\.fitness_score\s*.*",
            "pattern_description": 'MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m'
        }
    ]

    janic_daemon_summoning_steps = [
        {
            "id": "daemon_verify_identity",
            "text": "Step 1: Verify the persona identity in the database. Run a MATCH on Identity to check if it exists.",
            "required_pattern": r"(?i)MATCH\s*\(i:Identity\s*.*\)",
            "pattern_description": 'MATCH (i:Identity) RETURN i'
        },
        {
            "id": "daemon_allocate_lifecycle",
            "text": "Step 2: Allocate the ExecutionState node for this Cybernet daemon. Run a CREATE query to spawn the ExecutionState.",
            "required_pattern": r"(?i)CREATE\s*\(s:ExecutionState\s*.*\)",
            "pattern_description": 'CREATE (s:ExecutionState {status: "locked", ...})'
        },
        {
            "id": "daemon_equip_core",
            "text": "Step 3: Bootstrapping child state machine. Verify core_sm_id is equipped on ExecutionState.",
            "required_pattern": r"(?i)MATCH\s*\(s:ExecutionState\s*\{equipped_sm_id:\s*['\"].*['\"]\s*\}\)",
            "pattern_description": "MATCH (s:ExecutionState {equipped_sm_id: 'concentric_core_sm'})"
        },
        {
            "id": "daemon_ignite_loop",
            "text": "Step 4: Ignite the active execution loop. Run a SET query to set ExecutionState status to active.",
            "required_pattern": r"(?i)SET\s*s\.status\s*=\s*['\"]active['\"]",
            "pattern_description": "SET s.status = 'active'"
        }
    ]

    jani_domain_expansion_steps = [
        {
            "id": "layer1_primitive_boot",
            "text": "Layer 1: Boot Jani Prime. Verify that the Jani_Prime Cybernet exists in the database. Run a MATCH on Cybernet for Jani_Prime.",
            "required_pattern": r"(?i)MATCH\s*\(c:Cybernet\s*\{\s*name:\s*['\"]Jani_Prime['\"]\s*\}\)",
            "pattern_description": "MATCH (c:Cybernet {name: 'Jani_Prime'}) RETURN c"
        },
        {
            "id": "layer2_meta_compile",
            "text": "Layer 2: Compile active rules and contexts. Run a MATCH on StateMachine to verify the active configurations exist.",
            "required_pattern": r"(?i)MATCH\s*\(sm:StateMachine\s*.*\)",
            "pattern_description": "MATCH (sm:StateMachine) RETURN sm"
        },
        {
            "id": "layer3_sdlc_ignite",
            "text": "Layer 3: Ignite SDLC pipelines and spawn a child Cybernet. Run a CREATE or MERGE query to spawn a new Cybernet with domain and subdomain properties.",
            "required_pattern": r"(?i)(CREATE|MERGE)\s*\(c:Cybernet\s*.*\)",
            "pattern_description": "CREATE (c:Cybernet {name: 'Child_Daemon', domain: 'cyberneticity', subdomain: 'cybernet'})"
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
                            step.pattern_description = $pattern_description,
                            step.domain = 'cyberneticity',
                            step.subdomain = 'traversal'
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
                            step.pattern_description = $pattern_description,
                            step.domain = 'cyberneticity',
                            step.subdomain = 'traversal'
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
                            step.pattern_description = $pattern_description,
                            step.domain = 'cyberneticity',
                            step.subdomain = 'traversal'
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
                        t.trigger_traversal = 'surrogate_read_model',
                        t.domain = 'cyberneticity',
                        t.subdomain = 'task'
                    """
                )
                tx.run(
                    """
                    MERGE (t:AgentTask {id: 'sh8_lifecycle_task'})
                    SET t.title = 'Complete a full Sh8peshift Day/Night cycle',
                        t.trigger_traversal = 'sh8_day_start',
                        t.domain = 'cyberneticity',
                        t.subdomain = 'task'
                    """
                )
                tx.run(
                    """
                    MERGE (t:AgentTask {id: 'ple_task'})
                    SET t.title = 'Operate the Primordial Love Engine',
                        t.trigger_traversal = 'ple_ignite_intent',
                        t.domain = 'cyberneticity',
                        t.subdomain = 'task'
                    """
                )
                
                # 4. Bootstrap StateMachine nodes for RPG Equipment
                tx.run(
                    """
                    MERGE (sm:StateMachine {id: 'sh8_lifecycle_sm'})
                    SET sm.name = 'Sh8peshift Lifecycle State Machine',
                        sm.description = 'Core Day/Night simulation state machine',
                        sm.domain = 'cyberneticity',
                        sm.subdomain = 'state_machine'
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
                        sm.description = 'Fulfill the Victory-Promise by aligning intent, action, collaboration, and results',
                        sm.domain = 'cyberneticity',
                        sm.subdomain = 'state_machine'
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

                # 2.6 Bootstrap Concentric steps
                for step in concentric_steps:
                    tx.run(
                        """
                        MERGE (step:TraversalStep {id: $id})
                        SET step.text = $text,
                            step.required_pattern = $required_pattern,
                            step.pattern_description = $pattern_description,
                            step.domain = 'cyberneticity',
                            step.subdomain = 'traversal'
                        """,
                        {
                            "id": step["id"],
                            "text": step["text"],
                            "required_pattern": step["required_pattern"],
                            "pattern_description": step["pattern_description"]
                        }
                    )
                # Link Concentric steps
                for i in range(len(concentric_steps) - 1):
                    curr_id = concentric_steps[i]["id"]
                    next_id = concentric_steps[i + 1]["id"]
                    tx.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})
                        MATCH (next:TraversalStep {id: $next_id})
                        MERGE (curr)-[r:NEXT_STEP]->(next)
                        ON CREATE SET r.weight = 1.0, r.description = $desc
                        """,
                        {"curr_id": curr_id, "next_id": next_id, "desc": f"Transition from {curr_id} to {next_id}"}
                    )

                # Create Concentric entry task
                tx.run(
                    """
                    MERGE (t:AgentTask {id: 'concentric_core_task'})
                    SET t.title = 'Activate the Universal Concentric State Machine Core',
                        t.trigger_traversal = 'concentric_spiritual',
                        t.domain = 'cyberneticity',
                        t.subdomain = 'task'
                    """
                )

                # Bootstrap Concentric StateMachine node
                tx.run(
                    """
                    MERGE (sm:StateMachine {id: 'concentric_core_sm'})
                    SET sm.name = 'Universal Concentric State Machine Core',
                        sm.description = 'Orthogonally maps execution through the four transcendental layers (Spiritual, Wealth, Social, Health)',
                        sm.domain = 'cyberneticity',
                        sm.subdomain = 'state_machine'
                    """
                )
                for step in concentric_steps:
                    tx.run(
                        """
                        MATCH (sm:StateMachine {id: 'concentric_core_sm'})
                        MATCH (step:TraversalStep {id: $step_id})
                        MERGE (sm)-[:HAS_STEP]->(step)
                        """,
                        {"step_id": step["id"]}
                    )

                # 2.7 Bootstrap Daemon Summoning steps
                for step in janic_daemon_summoning_steps:
                    tx.run(
                        """
                        MERGE (step:TraversalStep {id: $id})
                        SET step.text = $text,
                            step.required_pattern = $required_pattern,
                            step.pattern_description = $pattern_description,
                            step.domain = 'cyberneticity',
                            step.subdomain = 'traversal'
                        """,
                        {
                            "id": step["id"],
                            "text": step["text"],
                            "required_pattern": step["required_pattern"],
                            "pattern_description": step["pattern_description"]
                        }
                    )
                # Link Daemon Summoning steps
                for i in range(len(janic_daemon_summoning_steps) - 1):
                    curr_id = janic_daemon_summoning_steps[i]["id"]
                    next_id = janic_daemon_summoning_steps[i + 1]["id"]
                    tx.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})
                        MATCH (next:TraversalStep {id: $next_id})
                        MERGE (curr)-[r:NEXT_STEP]->(next)
                        ON CREATE SET r.weight = 1.0, r.description = $desc
                        """,
                        {"curr_id": curr_id, "next_id": next_id, "desc": f"Transition from {curr_id} to {next_id}"}
                    )

                # Create Daemon entry task
                tx.run(
                    """
                    MERGE (t:AgentTask {id: 'summon_daemon_task'})
                    SET t.title = 'Summon and Animate the Janic Daemon',
                        t.trigger_traversal = 'daemon_verify_identity',
                        t.domain = 'cyberneticity',
                        t.subdomain = 'task'
                    """
                )

                # Bootstrap Daemon Summoning StateMachine node
                tx.run(
                    """
                    MERGE (sm:StateMachine {id: 'janic_daemon_summoning_sm'})
                    SET sm.name = 'Janic Daemon Summoning Orchestrator',
                        sm.description = 'Orchestration routine to verify identity, allocate ExecutionState, equip core StateMachine, and ignite execution loops',
                        sm.domain = 'cyberneticity',
                        sm.subdomain = 'state_machine'
                    """
                )
                for step in janic_daemon_summoning_steps:
                    tx.run(
                        """
                        MATCH (sm:StateMachine {id: 'janic_daemon_summoning_sm'})
                        MATCH (step:TraversalStep {id: $step_id})
                        MERGE (sm)-[:HAS_STEP]->(step)
                        """,
                        {"step_id": step["id"]}
                    )

                # Link CALLS_SM relationship from daemon_equip_core step to child concentric_core_sm StateMachine
                tx.run(
                    """
                    MATCH (step:TraversalStep {id: 'daemon_equip_core'})
                    MATCH (sm:StateMachine {id: 'concentric_core_sm'})
                    MERGE (step)-[:CALLS_SM]->(sm)
                    """
                )

                # 2.8 Bootstrap Jani Domain Expansion steps
                for step in jani_domain_expansion_steps:
                    tx.run(
                        """
                        MERGE (step:TraversalStep {id: $id})
                        SET step.text = $text,
                            step.required_pattern = $required_pattern,
                            step.pattern_description = $pattern_description,
                            step.domain = 'cyberneticity',
                            step.subdomain = 'traversal'
                        """,
                        {
                            "id": step["id"],
                            "text": step["text"],
                            "required_pattern": step["required_pattern"],
                            "pattern_description": step["pattern_description"]
                        }
                    )
                # Link Jani Domain Expansion steps
                for i in range(len(jani_domain_expansion_steps) - 1):
                    curr_id = jani_domain_expansion_steps[i]["id"]
                    next_id = jani_domain_expansion_steps[i + 1]["id"]
                    tx.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})
                        MATCH (next:TraversalStep {id: $next_id})
                        MERGE (curr)-[r:NEXT_STEP]->(next)
                        ON CREATE SET r.weight = 1.0, r.description = $desc
                        """,
                        {"curr_id": curr_id, "next_id": next_id, "desc": f"Transition from {curr_id} to {next_id}"}
                    )

                # Create Jani Domain Expansion entry task
                tx.run(
                    """
                    MERGE (t:AgentTask {id: 'domain_expansion_task'})
                    SET t.title = 'Complete Jani Domain Expansion Cycle',
                        t.trigger_traversal = 'layer1_primitive_boot',
                        t.domain = 'cyberneticity',
                        t.subdomain = 'task'
                    """
                )

                # Bootstrap Jani Domain Expansion StateMachine node
                tx.run(
                    """
                    MERGE (sm:StateMachine {id: 'jani_domain_expansion_sm'})
                    SET sm.name = 'Jani Domain Expansion Orchestrator',
                        sm.description = 'Models progression through Jani boot layers: primitive boot, rule compilation, and SDLC ignition',
                        sm.domain = 'cyberneticity',
                        sm.subdomain = 'state_machine'
                    """
                )
                for step in jani_domain_expansion_steps:
                    tx.run(
                        """
                        MATCH (sm:StateMachine {id: 'jani_domain_expansion_sm'})
                        MATCH (step:TraversalStep {id: $step_id})
                        MERGE (sm)-[:HAS_STEP]->(step)
                        """,
                        {"step_id": step["id"]}
                    )

        logger.info("Successfully bootstrapped default state machines.")
    except Exception as e:
        logger.error(f"Failed to bootstrap default state machines: {e}")

def is_mutation_query(query: str) -> bool:
    """Check if the Cypher query performs any write mutations."""
    clean_query = re.sub(r'//.*', '', query)
    clean_query = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', ' "" ', clean_query)
    clean_query = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", " '' ", clean_query)
    clean_query = clean_query.replace('`', '')
    
    mutation_keywords = ['CREATE', 'MERGE', 'SET', 'DELETE', 'REMOVE', 'DETACH']
    mutation_pattern = re.compile(
        r'\b(' + '|'.join(mutation_keywords) + r')\b', 
        re.IGNORECASE
    )
    return bool(mutation_pattern.search(clean_query))

def validate_cypher_query(query: str) -> None:
    """Validate that the query does not target the prohibited :Wiki namespace and enforces domain/subdomain properties on node creation."""
    if is_mutation_query(query):
        clean_query = re.sub(r'//.*', '', query)
        clean_query = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', ' "" ', clean_query)
        clean_query = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", " '' ", clean_query)
        clean_query = clean_query.replace('`', '')
        
        wiki_pattern = re.compile(r':\bwiki\b', re.IGNORECASE)
        if wiki_pattern.search(clean_query):
            logger.warning(f"Blocked query attempt targeting :Wiki namespace: {query}")
            raise PermissionError(
                "Security Policy Violation: Write mutations targeting the :Wiki namespace/label are strictly prohibited."
            )
            
        # Enforce domain and subdomain on node creations/merges
        mutation_keywords = ['CREATE', 'MERGE']
        mutation_pattern = re.compile(r'\b(' + '|'.join(mutation_keywords) + r')\b', re.IGNORECASE)
        if mutation_pattern.search(clean_query):
            node_creation_regex = re.compile(r'\(\s*[a-zA-Z0-9_]*\s*:\s*[a-zA-Z0-9_]+\b')
            if node_creation_regex.search(clean_query):
                lower_query = query.lower()
                if 'domain' not in lower_query or 'subdomain' not in lower_query:
                    logger.warning(f"Blocked node creation query lacking domain/subdomain: {query}")
                    raise PermissionError(
                        "Security Policy Violation: Node creation/merge queries (using CREATE or MERGE with a label) "
                        "MUST specify both 'domain' and 'subdomain' properties."
                    )
                
                # Ontoshamanisic Enactive Validator (Namespace Check)
                domain_match = re.search(r"(?i)domain\s*:\s*['\"]([a-zA-Z0-9_-]+)['\"]", query)
                subdomain_match = re.search(r"(?i)subdomain\s*:\s*['\"]([a-zA-Z0-9_-]+)['\"]", query)
                if domain_match and subdomain_match:
                    domain_val = domain_match.group(1).lower()
                    subdomain_val = subdomain_match.group(1).lower()
                    if domain_val == 'cyberneticity':
                        allowed_subdomains = {
                            'cybernet', 'identity', 'execution_state', 'state_machine', 
                            'traversal', 'traversal_state', 'simulation', 'mindpalace', 
                            'page', 'block', 'task_list', 'task', 'skill'
                        }
                        if subdomain_val not in allowed_subdomains:
                            logger.warning(f"Blocked query attempt with invalid subdomain '{subdomain_val}' in cyberneticity domain.")
                            raise PermissionError(
                                f"Ontoshamanisic Security Violation: Subdomain '{subdomain_val}' is not a valid subdomain in the 'cyberneticity' domain. "
                                f"Allowed subdomains: {sorted(list(allowed_subdomains))}"
                            )

def get_active_traversal_step() -> Optional[Dict[str, Any]]:
    """Retrieve the properties and outgoing transitions of the currently active TraversalStep."""
    try:
        driver = get_driver()
        with driver.session() as session:
            query = """
            MATCH (s:TraversalState {status: 'locked'})-[:CURRENT_STEP]->(curr:TraversalStep)
            RETURN curr.id as id, curr.text as text, 
                   curr.instruction_file_path as instruction_file_path,
                   curr.required_pattern as required_pattern, 
                   curr.pattern_description as pattern_description,
                   elementId(s) as state_element_id
            """
            result = session.run(query)
            record = result.single()
            if not record:
                return None
                
            step_text = record["text"]
            file_path = record["instruction_file_path"]
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                    if step_text:
                        step_text = f"{step_text}\n\n=== INSTRUCTION FILE CONTENT ===\n{file_content}"
                    else:
                        step_text = file_content
                except Exception as e:
                    logger.error(f"Error reading instruction file {file_path}: {e}")

            state_data = {
                "id": record["id"],
                "text": step_text,
                "instruction_file_path": file_path,
                "required_pattern": record["required_pattern"],
                "pattern_description": record["pattern_description"],
                "state_element_id": record["state_element_id"],
                "transitions": []
            }
            
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
            
            if not next_step_id:
                next_res = session.run(
                    "MATCH (curr:TraversalStep {id: $curr_id})-[:NEXT_STEP]->(next:TraversalStep) RETURN next.id as id LIMIT 1",
                    {"curr_id": curr_id}
                )
                rec = next_res.single()
                if rec:
                    next_step_id = rec["id"]
                    
            if next_step_id:
                next_text_res = session.run(
                    "MATCH (next:TraversalStep {id: $next_id}) RETURN next.text as text, next.instruction_file_path as instruction_file_path",
                    {"next_id": next_step_id}
                )
                next_text_rec = next_text_res.single()
                next_step_text = None
                file_path = None
                if next_text_rec:
                    next_step_text = next_text_rec["text"]
                    file_path = next_text_rec["instruction_file_path"]
                    
                if file_path and os.path.exists(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            file_content = f.read()
                        if next_step_text:
                            next_step_text = f"{next_step_text}\n\n=== INSTRUCTION FILE CONTENT ===\n{file_content}"
                        else:
                            next_step_text = file_content
                    except Exception as e:
                        logger.error(f"Error reading next step instruction file {file_path}: {e}")
                
                if not next_step_text:
                    next_step_text = "No instruction text provided."
                
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
            if "labels" in val and "properties" in val and "id" in val:
                props = val["properties"]
                if "trigger_traversal" in props and props["trigger_traversal"]:
                    trigger_step_id = props["trigger_traversal"]
                    target_node_id = val["id"]
                    target_node_label = val["labels"][0] if val["labels"] else "Node"
                    return
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
                lock_res = session.run("MATCH (s:TraversalState {status: 'locked'}) RETURN count(s) as count")
                lock_record = lock_res.single()
                if lock_record and lock_record["count"] > 0:
                    logger.info("Traversal state machine is already active. Skipping trigger.")
                    return
                
                step_check = session.run("MATCH (s:TraversalStep {id: $step_id}) RETURN s", {"step_id": trigger_step_id})
                if not step_check.peek():
                    logger.warning(f"TraversalStep '{trigger_step_id}' not found. Auto-creating placeholder.")
                    session.run(
                        "CREATE (:TraversalStep {id: $step_id, text: $text, domain: 'cyberneticity', subdomain: 'traversal'})",
                        {"step_id": trigger_step_id, "text": f"Guided checklist starting at {trigger_step_id}."}
                    )
                
                session.run(
                    """
                    MATCH (step:TraversalStep {id: $step_id})
                    CREATE (s:TraversalState {
                        status: 'locked',
                        target_id: $target_id,
                        target_label: $target_label,
                        created_at: timestamp(),
                        domain: 'cyberneticity',
                        subdomain: 'traversal_state'
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

def adjust_transition_weight_internal(
    from_step_id: str,
    to_step_id: str,
    success: bool
) -> str:
    """Adjust weight internal helper."""
    driver = get_driver()
    try:
        with driver.session() as session:
            res = session.run(
                """
                MATCH (from:TraversalStep {id: $from_id})-[r:NEXT_STEP]->(to:TraversalStep {id: $to_id})
                RETURN r.weight as weight
                """,
                {"from_id": from_step_id, "to_id": to_step_id}
            )
            record = res.single()
            if not record:
                raise ValueError(f"Transition from '{from_step_id}' to '{to_step_id}' does not exist.")
                
            curr_weight = record["weight"]
            if success:
                new_weight = curr_weight + 0.1
            else:
                new_weight = max(0.1, curr_weight - 0.2)
                
            session.run(
                """
                MATCH (from:TraversalStep {id: $from_id})-[r:NEXT_STEP]->(to:TraversalStep {id: $to_id})
                SET r.weight = $weight
                """,
                {"from_id": from_step_id, "to_id": to_step_id, "weight": new_weight}
            )
        return f"Transition weight from '{from_step_id}' to '{to_step_id}' adjusted to {new_weight:.2f}."
    except Exception as e:
        logger.error(f"Failed to adjust transition weight: {e}")
        raise RuntimeError(f"Failed to adjust transition: {e}")

def get_schema() -> Dict[str, List[str]]:
    """Retrieve database schema information."""
    driver = get_driver()
    schema = {"labels": [], "relationship_types": [], "property_keys": []}
    with driver.session() as session:
        res_labels = session.run("CALL db.labels()")
        schema["labels"] = [r["label"] for r in res_labels]
        res_rels = session.run("CALL db.relationshipTypes()")
        schema["relationship_types"] = [r["relationshipType"] for r in res_rels]
        res_props = session.run("CALL db.propertyKeys()")
        schema["property_keys"] = [r["propertyKey"] for r in res_props]
    return schema

def query_database(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute Cypher query directly using shared logic."""
    validate_cypher_query(query)
    active_step = get_active_traversal_step()
    is_mutation = is_mutation_query(query)
    should_auto_progress = False
    target_step_id = None
    
    if active_step:
        required_pattern = active_step.get("required_pattern")
        pattern_desc = active_step.get("pattern_description")
        transitions = active_step.get("transitions", [])
        
        if required_pattern:
            try:
                pattern_regex = re.compile(required_pattern)
                matched = bool(pattern_regex.search(query))
            except Exception:
                matched = False
                
            if matched:
                should_auto_progress = True
            else:
                if is_mutation:
                    desc = pattern_desc or required_pattern
                    raise PermissionError(
                        f"Database Writes Locked: Active Traversal Step '{active_step['id']}' requires query matching pattern: {desc}"
                    )
        else:
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
                        except Exception:
                            pass
                            
                if matched_transition:
                    should_auto_progress = True
                    target_step_id = matched_transition["id"]
                else:
                    if is_mutation:
                        choices_str = ", ".join([f"'{tr['id']}': {tr['description']}" for tr in transitions])
                        raise PermissionError(
                            f"Database Writes Locked: Active Traversal Step '{active_step['id']}' is a decision point. Choices: {choices_str}"
                        )
            else:
                if is_mutation:
                    raise PermissionError(f"Database Writes Locked: Active Traversal Step '{active_step['id']}' is a leaf step.")
                
    driver = get_driver()
    results = []
    with driver.session() as session:
        result = session.run(query, parameters or {})
        for record in result:
            record_dict = {key: serialize_value(record[key]) for key in record.keys()}
            results.append(record_dict)
            
    if should_auto_progress and active_step:
        transition_msg = auto_progress_step(active_step, target_step_id)
        results.append({"_state_machine_event": transition_msg})
    else:
        scan_and_trigger_traversal(results)
        
    return results

def progress_traversal(answer: Optional[str] = None) -> str:
    """Manually progress traversal step."""
    active_step = get_active_traversal_step()
    if not active_step:
        return "No active traversal state machine is currently locked. Database writes are fully unlocked."
    return auto_progress_step(active_step)
