#!/usr/bin/env python3
"""
CybernetiCircus RPG Game Compiler
Handles Cybernet creation, equipping State Machines, Day/Night turn loops, calibration, and evolutionary steps.
"""
import os
import re
import json
import math
import random
import uuid
import logging
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("cyberneticircus_compiler")

class AgentLLMRunner:
    """
    Modular LLM call hook representing the model configuration of a Cybernet.
    This class is passed to the engine and simulates query output matching the step prompts.
    """
    def __init__(self, model_name: str, temperature: float, top_p: float, max_tokens: int):
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens

    def call_llm(self, system_prompt: str, user_prompt: str, character_name: str, step_id: str) -> str:
        """
        Modular LLM call wrapper. Can be overridden with actual API endpoints.
        In this framework runner, it generates mock queries matching the current step's gating criteria.
        """
        logger.info(f"LLM Call [Model: {self.model_name}, Temp: {self.temperature}] - Step: {step_id}")
        
        # Generates exact queries to successfully progress the Traversal State Machine
        if step_id == "sh8_day_start":
            return f"MATCH (m:Cybernet) RETURN m"
        elif step_id == "sh8_day_action":
            tokens_generated = random.randint(100, 300)
            return f"MATCH (m:Cybernet {{name: '{character_name}'}}) SET m.total_tokens_consumed = m.total_tokens_consumed + {tokens_generated}"
        elif step_id == "sh8_night_calibrate":
            return "MATCH (sim:SimulationRun) RETURN sim"
        elif step_id == "sh8_night_evolve":
            return "MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m"
        elif step_id == "sub_step_1":
            return "MATCH (s:SubNode) RETURN s"
        elif step_id == "sub_step_2":
            return "MATCH (s:SubNode {done: true}) RETURN s"
        
        return "MATCH (n) RETURN n"

class CybernetiCircusCompiler:
    """
    The CybernetiCircus compiler managing Cybernet Identities, State Machines (Equipment),
    turn loops, and evolutionary cycles.
    """
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password"):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()
        logger.info("Successfully connected Compiler to the Cyberneticity (Neo4j).")

    def close(self):
        self.driver.close()

    def create_cybernet(
        self,
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
        Create a new Cybernet (Identity) node in the graph.
        """
        with self.driver.session() as session:
            # Check if Cybernet already exists
            check_res = session.run("MATCH (m:Cybernet {name: $name}) RETURN count(m) as count", {"name": name})
            if check_res.single()["count"] > 0:
                raise ValueError(f"Cybernet character '{name}' already exists.")
                
            # Create the character graph identity
            session.run(
                """
                CREATE (m:Cybernet {
                    name: $name,
                    description: $description,
                    model_name: $model_name,
                    parameters_count: $parameters_count,
                    temperature: $temperature,
                    top_p: $top_p,
                    max_tokens: $max_tokens,
                    mutation_rate: $mutation_rate,
                    selection_pressure: $selection_pressure,
                    task_success_rate: 1.0,
                    tool_call_frequency: 0.0,
                    avg_latency_ms: 0.0,
                    total_tokens_consumed: 0,
                    accumulated_cost: 0.0,
                    fitness_score: 1.0
                })
                """,
                {
                    "name": name,
                    "description": description,
                    "model_name": model_name,
                    "parameters_count": float(parameters_count),
                    "temperature": float(temperature),
                    "top_p": float(top_p),
                    "max_tokens": int(max_tokens),
                    "mutation_rate": float(mutation_rate),
                    "selection_pressure": float(selection_pressure)
                }
            )
            return f"Successfully created Cybernet '{name}' identity graph."

    def equip_state_machine(self, cybernet_name: str, state_machine_id: str) -> str:
        """
        Equip a State Machine onto a Cybernet (creates :EQUIPS relationship and starts :HAS_LIFECYCLE execution state).
        """
        with self.driver.session() as session:
            # Check if Cybernet exists
            ms_check = session.run("MATCH (m:Cybernet {name: $name}) RETURN m", {"name": cybernet_name})
            if not ms_check.peek():
                raise ValueError(f"Cybernet '{cybernet_name}' does not exist.")
                
            # Check if State Machine exists
            sm_check = session.run("MATCH (sm:StateMachine {id: $sm_id}) RETURN sm", {"sm_id": state_machine_id})
            if not sm_check.peek():
                raise ValueError(f"StateMachine '{state_machine_id}' does not exist.")
                
            # Equips State Machine and creates an execution lifecycle linked to the entry step
            # Entry step has no incoming NEXT_STEP relationship
            session.run(
                """
                MATCH (m:Cybernet {name: $name})
                MATCH (sm:StateMachine {id: $sm_id})
                MERGE (m)-[:EQUIPS]->(sm)
                
                // Clear any existing lifecycle state for this state machine
                WITH m, sm
                OPTIONAL MATCH (m)-[r:HAS_LIFECYCLE]->(s:Identity {equipped_sm_id: $sm_id})
                DETACH DELETE s
                DELETE r
                
                // Create new lifecycle state
                WITH m, sm
                CREATE (s:Identity {
                    status: 'locked',
                    turn_number: 1,
                    phase: 'day',
                    lifetime_limit: 5,
                    tokens_consumed_this_turn: 0,
                    cost_this_turn: 0.0,
                    equipped_sm_id: $sm_id,
                    call_stack: '[]'
                })
                CREATE (m)-[:HAS_LIFECYCLE]->(s)
                
                // Find entry step of the StateMachine and link s to it
                WITH s, sm
                MATCH (sm)-[:HAS_STEP]->(entry:TraversalStep)
                WHERE NOT ()-[:NEXT_STEP]->(entry)
                CREATE (s)-[:CURRENT_STEP]->(entry)
                """,
                {"name": cybernet_name, "sm_id": state_machine_id}
            )
            return f"Successfully equipped StateMachine '{state_machine_id}' onto '{cybernet_name}'."

    def get_character_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch status and metrics of a Cybernet and its equipped state machine lifecycle.
        """
        with self.driver.session() as session:
            res = session.run(
                """
                MATCH (m:Cybernet {name: $name})
                OPTIONAL MATCH (m)-[:EQUIPS]->(sm:StateMachine)
                OPTIONAL MATCH (m)-[:HAS_LIFECYCLE]->(s:Identity)
                OPTIONAL MATCH (s)-[:CURRENT_STEP]->(curr:TraversalStep)
                RETURN m, sm.id as equipped_sm_id, sm.name as equipped_sm_name, s, 
                       curr.id as current_step_id, curr.text as current_step_text,
                       s.call_stack as call_stack
                """,
                {"name": name}
            )
            rec = res.single()
            if not rec:
                return None
                
            status_data = {
                "name": rec["m"]["name"],
                "description": rec["m"]["description"],
                "model_name": rec["m"]["model_name"],
                "temperature": rec["m"]["temperature"],
                "top_p": rec["m"]["top_p"],
                "mutation_rate": rec["m"]["mutation_rate"],
                "selection_pressure": rec["m"]["selection_pressure"],
                "total_tokens": rec["m"]["total_tokens_consumed"],
                "accumulated_cost": rec["m"]["accumulated_cost"],
                "fitness_score": rec["m"]["fitness_score"],
                "equipped_sm_id": rec["equipped_sm_id"],
                "equipped_sm_name": rec["equipped_sm_name"],
                "turn_number": None,
                "phase": None,
                "current_step_id": None,
                "current_step_text": None,
                "call_stack": "[]"
            }
            
            if rec["s"]:
                status_data.update({
                    "turn_number": rec["s"]["turn_number"],
                    "phase": rec["s"]["phase"],
                    "current_step_id": rec["current_step_id"],
                    "current_step_text": rec["current_step_text"],
                    "equipped_sm_id": rec["s"]["equipped_sm_id"] or rec["equipped_sm_id"],
                    "call_stack": rec["call_stack"] or "[]"
                })
                
            return status_data

    def tick_turn(self, name: str, runner: AgentLLMRunner) -> Dict[str, Any]:
        """
        Tick one step/phase of the Day/Night cycle.
        Returns the action taken and new status.
        """
        status = self.get_character_status(name)
        if not status:
            raise ValueError(f"Character '{name}' not found.")
            
        if not status["equipped_sm_id"]:
            raise ValueError(f"Cybernet '{name}' does not have any State Machine equipped.")
            
        phase = status["phase"]
        step_id = status["current_step_id"]
        turn_number = status["turn_number"]
        sm_id = status["equipped_sm_id"]
        call_stack = json.loads(status.get("call_stack", "[]"))
        
        output_data = {
            "name": name,
            "turn": turn_number,
            "previous_phase": phase,
            "action_taken": "",
            "event_message": ""
        }
        
        # Lazy load server module to run queries securely
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sibling_dir = os.path.abspath(os.path.join(current_dir, "..", "neo4j_cypher_mcp"))
        if sibling_dir not in sys.path:
            sys.path.insert(0, sibling_dir)
        from server import query_database, is_traversal_locked, progress_traversal
        
        # 0. Check if the active step triggers a compiler call to a sub-state machine
        with self.driver.session() as session:
            sub_res = session.run(
                """
                MATCH (curr:TraversalStep {id: $step_id})-[:CALLS_SM]->(child_sm:StateMachine)
                RETURN child_sm.id as child_sm_id
                """,
                {"step_id": step_id}
            )
            sub_record = sub_res.single()
            child_sm_id = sub_record["child_sm_id"] if sub_record else None

        if child_sm_id:
            # Push parent frame onto call stack
            call_stack.append({"sm_id": sm_id, "step_id": step_id})
            
            # Find entry step of the child StateMachine
            with self.driver.session() as session:
                entry_res = session.run(
                    """
                    MATCH (sm:StateMachine {id: $child_sm_id})-[:HAS_STEP]->(entry:TraversalStep)
                    WHERE NOT ()-[:NEXT_STEP]->(entry)
                    RETURN entry.id as entry_id
                    """,
                    {"child_sm_id": child_sm_id}
                )
                entry_rec = entry_res.single()
                if not entry_rec:
                    raise ValueError(f"StateMachine '{child_sm_id}' does not have a valid entry step.")
                child_entry_id = entry_rec["entry_id"]
                
                # Update Identity in database
                session.run(
                    """
                    MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity)
                    MATCH (entry:TraversalStep {id: $entry_id})
                    MATCH (s)-[r:CURRENT_STEP]->()
                    DELETE r
                    CREATE (s)-[:CURRENT_STEP]->(entry)
                    SET s.equipped_sm_id = $child_sm_id,
                        s.call_stack = $call_stack
                    """,
                    {
                        "name": name,
                        "child_sm_id": child_sm_id,
                        "entry_id": child_entry_id,
                        "call_stack": json.dumps(call_stack)
                    }
                )
            output_data["action_taken"] = f"Compiler call to sub-state machine '{child_sm_id}'."
            output_data["event_message"] = f"Saved parent step '{step_id}' to call stack. Transitioned loadout to child state machine '{child_sm_id}'."
            return output_data
        
        # 1. Run step-specific side effects before executing the query
        if step_id == "sh8_night_calibrate":
            # Save simulation result linked to Cybernet in Neo4j
            accuracy = round(random.uniform(0.5, 1.0), 2)
            run_id = str(uuid.uuid4())
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (m:Cybernet {name: $name})
                    CREATE (sim:SimulationRun {
                        run_id: $run_id,
                        created_at: timestamp(),
                        accuracy: $accuracy,
                        fitness_score: $accuracy,
                        calibrated: true
                    })
                    CREATE (m)-[:HAS_SIMULATION]->(sim)
                    """,
                    {"name": name, "run_id": run_id, "accuracy": accuracy}
                )
            output_data["event_message"] = f"Calibration triggered. Accuracy recorded: {accuracy}."
            
        elif step_id == "sh8_night_evolve":
            # Update fitness score by averaging all simulation runs
            with self.driver.session() as session:
                fit_res = session.run(
                    """
                    MATCH (m:Cybernet {name: $name})-[:HAS_SIMULATION]->(sim:SimulationRun)
                    RETURN avg(sim.accuracy) as avg_fitness
                    """,
                    {"name": name}
                )
                avg_fit = fit_res.single()["avg_fitness"] or 1.0
                session.run(
                    "MATCH (m:Cybernet {name: $name}) SET m.fitness_score = $avg_fitness",
                    {"name": name, "avg_fitness": avg_fit}
                )
            
        # 2. Lock traversal database state if not already locked
        if not is_traversal_locked():
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (step:TraversalStep {id: $step_id})
                    CREATE (s:TraversalState {
                        status: 'locked',
                        created_at: timestamp()
                    })-[:CURRENT_STEP]->(step)
                    """,
                    {"step_id": step_id}
                )
        else:
            # Force-align TraversalState's CURRENT_STEP with Identity's CURRENT_STEP
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (s:TraversalState {status: 'locked'})-[r:CURRENT_STEP]->()
                    DELETE r
                    WITH s
                    MATCH (step:TraversalStep {id: $step_id})
                    CREATE (s)-[:CURRENT_STEP]->(step)
                    """,
                    {"step_id": step_id}
                )
        
        # 3. Call the LLM runner to fetch the query/action
        system_prompt = (
            f"You are the Cybernet persona '{name}' with behavior guidelines: {status['description']}. "
            f"Your active model configuration has temperature={runner.temperature}, top_p={runner.top_p}."
        )
        user_prompt = f"Active step prompt: {status['current_step_text']}"
        query_action = runner.call_llm(system_prompt, user_prompt, name, step_id)
        output_data["action_taken"] = query_action
        
        # 4. Execute the generated query via query_database
        tokens_used = random.randint(100, 400)
        cost_increase = round(tokens_used * 0.000015, 6)
        
        try:
            results = query_database(query_action)
            
            event_msg = ""
            for record in results:
                if "_state_machine_event" in record:
                    event_msg = record["_state_machine_event"]
                    break
            
            if event_msg:
                if output_data["event_message"]:
                    output_data["event_message"] += " " + event_msg
                else:
                    output_data["event_message"] = event_msg
            elif not output_data["event_message"]:
                output_data["event_message"] = "Action query executed successfully."
                
            # Accumulate tokens and cost
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity {equipped_sm_id: $sm_id})
                    SET s.tokens_consumed_this_turn = s.tokens_consumed_this_turn + $tokens,
                        s.cost_this_turn = s.cost_this_turn + $cost,
                        m.total_tokens_consumed = m.total_tokens_consumed + $tokens,
                        m.accumulated_cost = m.accumulated_cost + $cost
                    """,
                    {"name": name, "sm_id": sm_id, "tokens": tokens_used, "cost": cost_increase}
                )
                
            # Now we must update the Identity's CURRENT_STEP to match the TraversalState's new step.
            with self.driver.session() as session:
                step_res = session.run(
                    """
                    MATCH (s:TraversalState {status: 'locked'})-[:CURRENT_STEP]->(curr:TraversalStep)
                    RETURN curr.id as current_step_id
                    """
                )
                rec = step_res.single()
                if rec:
                    new_step_id = rec["current_step_id"]
                    # Update Identity to point to new_step_id
                    session.run(
                        """
                        MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity {equipped_sm_id: $sm_id})
                        MATCH (next:TraversalStep {id: $new_step_id})
                        MATCH (s)-[r:CURRENT_STEP]->()
                        DELETE r
                        CREATE (s)-[:CURRENT_STEP]->(next)
                        """,
                        {"name": name, "sm_id": sm_id, "new_step_id": new_step_id}
                    )
                    
                    # Update phase: if new_step_id contains 'night', transition phase to 'night'
                    if "night" in new_step_id.lower():
                        session.run(
                            """
                            MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity {equipped_sm_id: $sm_id})
                            SET s.phase = 'night'
                            """,
                            {"name": name, "sm_id": sm_id}
                        )
                else:
                    # TraversalState was completed/deleted!
                    # Check if inside a sub-state machine (call stack is not empty)
                    if call_stack:
                        next_step_id = None
                        parent_sm_id = None
                        
                        while call_stack and not next_step_id:
                            parent_frame = call_stack.pop()
                            parent_sm_id = parent_frame["sm_id"]
                            parent_step_id = parent_frame["step_id"]
                            
                            with self.driver.session() as session:
                                next_res = session.run(
                                    """
                                    MATCH (curr:TraversalStep {id: $parent_step_id})-[:NEXT_STEP]->(next:TraversalStep)
                                    RETURN next.id as next_id
                                    """,
                                    {"parent_step_id": parent_step_id}
                                )
                                next_rec = next_res.single()
                                next_step_id = next_rec["next_id"] if next_rec else None
                                
                        if next_step_id and parent_sm_id:
                            with self.driver.session() as session:
                                session.run(
                                    """
                                    MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity)
                                    MATCH (next:TraversalStep {id: $next_step_id})
                                    MATCH (s)-[r:CURRENT_STEP]->()
                                    DELETE r
                                    CREATE (s)-[:CURRENT_STEP]->(next)
                                    SET s.equipped_sm_id = $parent_sm_id,
                                        s.call_stack = $call_stack
                                    """,
                                    {
                                        "name": name,
                                        "parent_sm_id": parent_sm_id,
                                        "next_step_id": next_step_id,
                                        "call_stack": json.dumps(call_stack)
                                    }
                                )
                                # Align phase
                                if "night" in next_step_id.lower():
                                    session.run(
                                        "MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity) SET s.phase = 'night'",
                                        {"name": name}
                                    )
                                else:
                                    session.run(
                                        "MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity) SET s.phase = 'day'",
                                        {"name": name}
                                    )
                            output_data["event_message"] += f" Sub-state machine completed. Popped call stack. Returned to parent step '{next_step_id}'."
                        else:
                            # Popped all frames, no next step found. Reset top-level.
                            self._trigger_turn_completion(name, sm_id, output_data)
                    else:
                        # Top-level state machine completed.
                        self._trigger_turn_completion(name, sm_id, output_data)
                        
        except Exception as e:
            output_data["event_message"] = f"Failed to execute query: {e}"
                
        return output_data

    def _trigger_turn_completion(self, name: str, sm_id: str, output_data: Dict[str, Any]):
        """Helper to handle turn cycle completion (lifetime evaluation or turn reset)."""
        updated_status = self.get_character_status(name)
        if updated_status["turn_number"] >= 5:
            evolve_msg = self.evaluate_evolution(name)
            output_data["event_message"] += f" [LIFETIME COMPLETED] {evolve_msg}"
        else:
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity {equipped_sm_id: $sm_id})
                    MATCH (sm:StateMachine {id: $sm_id})-[:HAS_STEP]->(entry:TraversalStep)
                    WHERE NOT ()-[:NEXT_STEP]->(entry)
                    MATCH (s)-[r:CURRENT_STEP]->()
                    DELETE r
                    CREATE (s)-[:CURRENT_STEP]->(entry)
                    SET s.turn_number = s.turn_number + 1,
                        s.phase = 'day',
                        s.tokens_consumed_this_turn = 0,
                        s.cost_this_turn = 0.0,
                        s.call_stack = '[]'
                    """,
                    {"name": name, "sm_id": sm_id}
                )
                output_data["event_message"] += " State machine completed. Resetting for next Day cycle."

    def evaluate_evolution(self, name: str) -> str:
        """
        Evaluate selection pressure at the end of a Cybernet's lifetime.
        """
        status = self.get_character_status(name)
        if not status:
            return "No status found for evolution evaluation."
            
        fitness = status["fitness_score"]
        mutation_rate = status["mutation_rate"]
        selection_pressure = status["selection_pressure"]
        sm_id = status["equipped_sm_id"]
        
        with self.driver.session() as session:
            if fitness < 0.4:
                # 1. REAPING (Pruning)
                session.run(
                    """
                    MATCH (m:Cybernet {name: $name})
                    OPTIONAL MATCH (m)-[:HAS_LIFECYCLE]->(s:Identity)
                    OPTIONAL MATCH (m)-[:HAS_SIMULATION]->(sim:SimulationRun)
                    DETACH DELETE m, s, sim
                    """,
                    {"name": name}
                )
                session.run("MATCH (s:TraversalState) DETACH DELETE s")
                return f"Identity graph '{name}' fitness ({fitness}) fell below selection threshold. Reaped from DB."
                
            elif fitness >= 0.8:
                # 2. REPRODUCTION (Cloning and Mutating AI stats + cloning equipped state machines)
                child_name = f"{name}_V{random.randint(2, 99)}"
                
                # Calculate mutated stats
                mutated_temp = max(0.0, min(2.0, round(status["temperature"] + random.uniform(-0.1, 0.1) * mutation_rate, 2)))
                mutated_top_p = max(0.0, min(1.0, round(status["top_p"] + random.uniform(-0.05, 0.05) * mutation_rate, 2)))
                mutated_mutation_rate = max(0.01, min(1.0, round(mutation_rate + random.uniform(-0.02, 0.02), 2)))
                mutated_selection_pressure = max(0.1, round(selection_pressure + random.uniform(-0.1, 0.1), 2))
                
                # Create clone Cybernet (clones all equipped StateMachines)
                session.run(
                    """
                    CREATE (m:Cybernet {
                        name: $child_name,
                        description: $description,
                        model_name: $model_name,
                        parameters_count: $parameters_count,
                        temperature: $temperature,
                        top_p: $top_p,
                        max_tokens: $max_tokens,
                        mutation_rate: $mutation_rate,
                        selection_pressure: $selection_pressure,
                        task_success_rate: 1.0,
                        tool_call_frequency: 0.0,
                        avg_latency_ms: 0.0,
                        total_tokens_consumed: 0,
                        accumulated_cost: 0.0,
                        fitness_score: 1.0
                    })
                    """,
                    {
                        "child_name": child_name,
                        "description": status["description"],
                        "model_name": status["model_name"],
                        "parameters_count": status["parameters_count"] if "parameters_count" in status else 70.0,
                        "temperature": mutated_temp,
                        "top_p": mutated_top_p,
                        "max_tokens": 2048,
                        "mutation_rate": mutated_mutation_rate,
                        "selection_pressure": mutated_selection_pressure
                    }
                )
                
                # Clone equipped state machines and recreate lifecycles
                session.run(
                    """
                    MATCH (parent:Cybernet {name: $name})-[:EQUIPS]->(sm:StateMachine)
                    MATCH (child:Cybernet {name: $child_name})
                    CREATE (child)-[:EQUIPS]->(sm)
                    
                    WITH child, sm
                    CREATE (s:Identity {
                        status: 'locked',
                        turn_number: 1,
                        phase: 'day',
                        lifetime_limit: 5,
                        tokens_consumed_this_turn: 0,
                        cost_this_turn: 0.0,
                        equipped_sm_id: sm.id,
                        call_stack: '[]'
                    })
                    CREATE (child)-[:HAS_LIFECYCLE]->(s)
                    
                    WITH s, sm
                    MATCH (sm)-[:HAS_STEP]->(entry:TraversalStep)
                    WHERE NOT ()-[:NEXT_STEP]->(entry)
                    CREATE (s)-[:CURRENT_STEP]->(entry)
                    """,
                    {"name": name, "child_name": child_name}
                )
                
                # Reset parent turn/lifetime stats to start a new cycle
                session.run(
                    """
                    MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity {equipped_sm_id: $sm_id})
                    MATCH (sm:StateMachine {id: $sm_id})-[:HAS_STEP]->(entry:TraversalStep)
                    WHERE NOT ()-[:NEXT_STEP]->(entry)
                    MATCH (s)-[r:CURRENT_STEP]->()
                    DELETE r
                    CREATE (s)-[:CURRENT_STEP]->(entry)
                    SET s.turn_number = 1,
                        s.phase = 'day',
                        s.tokens_consumed_this_turn = 0,
                        s.cost_this_turn = 0.0,
                        s.call_stack = '[]'
                    """,
                    {"name": name, "sm_id": sm_id}
                )
                session.run("MATCH (s:TraversalState) DETACH DELETE s")
                
                return (
                    f"Identity '{name}' achieved outstanding fitness ({fitness}) and REPRODUCED! "
                    f"Clone '{child_name}' spawned with mutated stats (temp={mutated_temp}, top_p={mutated_top_p}) inheriting equipped StateMachines."
                )
                
            else:
                # 3. SURVIVAL (Reset turn stats to start next lifetime cycle)
                session.run(
                    """
                    MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:Identity {equipped_sm_id: $sm_id})
                    MATCH (sm:StateMachine {id: $sm_id})-[:HAS_STEP]->(entry:TraversalStep)
                    WHERE NOT ()-[:NEXT_STEP]->(entry)
                    MATCH (s)-[r:CURRENT_STEP]->()
                    DELETE r
                    CREATE (s)-[:CURRENT_STEP]->(entry)
                    SET s.turn_number = 1,
                        s.phase = 'day',
                        s.tokens_consumed_this_turn = 0,
                        s.cost_this_turn = 0.0,
                        s.call_stack = '[]'
                    """,
                    {"name": name, "sm_id": sm_id}
                )
                session.run("MATCH (s:TraversalState) DETACH DELETE s")
                return f"Identity '{name}' fitness ({fitness}) met survival standards. Lifetime reset for another cycle."

# Alias for backward compatibility
Sh8peshiftEngine = CybernetiCircusCompiler

if __name__ == "__main__":
    try:
        engine = CybernetiCircusCompiler()
        print("Compiler connected successfully to Cyberneticity.")
        engine.close()
    except Exception as e:
        print(f"Compiler connection failed: {e}")
