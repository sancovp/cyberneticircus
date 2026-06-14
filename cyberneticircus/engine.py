#!/usr/bin/env python3
"""CybernetiCircus — LLM Runner. Thin facade per `cyberneticircus-architecture.md` §9.1.
The engine owns only: AgentLLMRunner, CybernetiCircusCompiler (thin facade), per-cybernet
ExecutionState lock acquisition, and tick_turn (read step -> call LLM -> execute cypher
-> gate -> auto-progress). All real logic lives in lib/."""
import os, json, logging, random
from typing import Any, Dict, Optional
from neo4j import GraphDatabase
from lib import cybernet as lib_cybernet
from lib import lifecycle as lib_lifecycle
from lib import evolution as lib_evolution

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("cyberneticircus_compiler")


class AgentLLMRunner:
    """LLM wrapper. Holds a Cybernet's model config and produces one Cypher
    query per `call_llm` call. Uses sanctuary-dna + heaven-framework with
    minimax-M3 when MINIMAX_API_KEY / ANTHROPIC_API_KEY is set; otherwise
    falls back to deterministic mock queries keyed on step_id."""
    def __init__(self, model_name: str, temperature: float, top_p: float, max_tokens: int):
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens

    def call_llm(self, system_prompt: str, user_prompt: str, character_name: str, step_id: str) -> str:
        logger.info(f"LLM Call [Model: {self.model_name}, Temp: {self.temperature}] - Step: {step_id}")
        minimax_key = os.environ.get("MINIMAX_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if minimax_key or anthropic_key:
            try:
                from sdna import HermesConfig
                from sdna.config import HeavenInputs, HeavenAgentArgs
                from sdna.heaven_runner import heaven_agent_step
                import asyncio
                model_to_use = self.model_name
                if not model_to_use or not model_to_use.lower().startswith("minimax"):
                    model_to_use = "minimax-M3"
                config = HermesConfig(
                    name=character_name,
                    system_prompt=system_prompt + "\nIMPORTANT: You must return a valid Cypher query (and only the query) that resolves the active step goal.",
                    goal=user_prompt, model=model_to_use, max_turns=5,
                    backend="heaven", permission_mode="bypassPermissions",
                    heaven_inputs=HeavenInputs(agent=HeavenAgentArgs(
                        provider="ANTHROPIC", temperature=self.temperature,
                        max_tokens=self.max_tokens or 8000,
                    )),
                )
                async def run_agent():
                    res = await heaven_agent_step(config)
                    if res and res.status.name == "SUCCESS" and "text" in res.output:
                        return res.output["text"].strip()
                    raise RuntimeError(f"Agent status: {res.status.name if res else 'None'}. Error: {res.error if res else 'None'}")
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                if loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()
                    query = loop.run_until_complete(run_agent())
                else:
                    query = loop.run_until_complete(run_agent())
                # Strip markdown fences / backticks / "cypher" prefix
                if query:
                    query = query.strip()
                    if query.startswith("```"):
                        lines = query.splitlines()
                        if len(lines) >= 2:
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines[-1].strip() == "```":
                                lines = lines[:-1]
                            query = "\n".join(lines).strip()
                    if query.startswith("`") and query.endswith("`"):
                        query = query.strip("`").strip()
                    if query.lower().startswith("cypher"):
                        query = query[6:].strip()
                return query
            except Exception as e:
                logger.warning(f"SDNA/HEAVEN failed: {e}. Falling back to mock queries.")
        return _mock_query_for_step(step_id, character_name)


_MOCK_QUERIES = {
    "sh8_day_start": "MATCH (m:Cybernet) RETURN m",
    "ple_ignite_intent": "MATCH (m:Cybernet) RETURN m",
    "concentric_spiritual": "MATCH (m:Cybernet) RETURN m",
    "sh8_night_calibrate": "MATCH (sim:SimulationRun) RETURN sim",
    "ple_align_collaboration": "MATCH (m:Cybernet {name: '$c'})-[:HAS_IDENTITY]->(i:Identity) RETURN i",
    "concentric_social": "MATCH (m:Cybernet {name: '$c'})-[:HAS_IDENTITY]->(i:Identity) RETURN i",
    "sh8_night_evolve": "MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m",
    "ple_output_promise": "MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m",
    "concentric_health": "MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m",
    "sub_step_1": "MATCH (s:SubNode) RETURN s",
    "sub_step_2": "MATCH (s:SubNode {done: true}) RETURN s",
    "jester_boot": "MERGE (c:Cybernet {name: 'JesterCoreOne'}) ON CREATE SET c.status = 'initialized', c.domain = 'cyberneticity', c.subdomain = 'cybernet'",
    "jester_play": "MATCH (c:Cybernet {name: 'JesterCoreOne'}) SET c.persona = 'Jester'",
    "jester_verify": "MATCH (c:Cybernet {name: 'JesterCoreOne'}) RETURN c.fitness_score",
    "janic_read_designs": "MATCH (arch:Concept {name: 'CybernetiCircus_Architecture'}) RETURN arch",
    "janic_check_state": "MATCH (c:Cybernet {name: '$c'})-[:USES]->(arch:Concept) RETURN arch",
    "janic_engineer": "MATCH (d:Concept {is_a: 'Domain'}) RETURN d.name",
    "janic_preservation": "MATCH (c:Cybernet {name: '$c'})-[:HAS_TASK]->(t:Task) RETURN t",
    "janic_autocommentary": "MATCH (c:Cybernet {name: '$c'}) RETURN c",
    "daemon_verify_identity": "MATCH (i:Identity) RETURN i",
    "daemon_allocate_lifecycle": "CREATE (s:ExecutionState {status: 'locked', domain: 'cyberneticity', subdomain: 'lifecycle'})",
    "daemon_equip_core": "MATCH (s:ExecutionState {equipped_sm_id: 'concentric_core_sm'}) RETURN s",
    "daemon_ignite_loop": "MATCH (c:Cybernet {name: '$c'})-[:HAS_LIFECYCLE]->(s:ExecutionState) SET s.status = 'active' RETURN s",
    "layer1_primitive_boot": "MATCH (c:Cybernet {name: 'Jani_Prime'}) RETURN c",
    "layer2_meta_compile": "MATCH (sm:StateMachine) RETURN sm",
    "layer3_sdlc_ignite": "MERGE (c:Cybernet {name: 'Child_Daemon_Jester'}) ON CREATE SET c.domain = 'cyberneticity', c.subdomain = 'cybernet'",
}
_MOCK_TOKEN_STEPS = {"sh8_day_action", "ple_combust_action", "concentric_wealth"}


def _mock_query_for_step(step_id: str, character_name: str) -> str:
    """Deterministic mock query that matches the active step's required_pattern."""
    if step_id in _MOCK_TOKEN_STEPS:
        return f"MATCH (m:Cybernet {{name: '{character_name}'}}) SET m.total_tokens_consumed = m.total_tokens_consumed + {random.randint(100, 300)}"
    if step_id in _MOCK_QUERIES:
        return _MOCK_QUERIES[step_id].replace("$c", character_name)
    return "MATCH (n) RETURN n"


class CybernetiCircusCompiler:
    """The LLM-loop compiler. `tick_turn` is the only LLM-loop method; the
    rest are thin facades over `lib/cybernet` and `lib/evolution` per §9.1."""
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.driver.verify_connectivity()
        logger.info("Successfully connected Compiler to the Cyberneticity (Neo4j).")

    def close(self):
        self.driver.close()

    # --- Thin facades over lib.cybernet (preserved for callers like runner.py) ---
    def create_cybernet(self, name, description, model_name="gemini-1.5-pro",
                        parameters_count=70.0, temperature=0.7, top_p=0.9,
                        max_tokens=2048, mutation_rate=0.1, selection_pressure=1.0):
        return lib_cybernet.create(self.driver, name=name, description=description,
            model_name=model_name, parameters_count=parameters_count,
            temperature=temperature, top_p=top_p, max_tokens=max_tokens,
            mutation_rate=mutation_rate, selection_pressure=selection_pressure)

    def equip_state_machine(self, cybernet_name, state_machine_id):
        return lib_cybernet.equip_state_machine(
            self.driver, cybernet_name=cybernet_name, state_machine_id=state_machine_id)

    def get_character_status(self, name):
        return lib_cybernet.get_status(self.driver, name=name)

    # --- The LLM loop: tick_turn ---
    def tick_turn(self, name: str, runner: AgentLLMRunner) -> Dict[str, Any]:
        """One step of the Day/Night cycle. Reads active step, gates via
        per-cybernet ExecutionState lock, calls the LLM, executes the query,
        and auto-progresses (or pops the call stack on child-SM completion,
        or evaluates evolution at lifetime end)."""
        status = self.get_character_status(name)
        if not status:
            raise ValueError(f"Character '{name}' not found.")
        if not status["equipped_sm_id"]:
            raise ValueError(f"Cybernet '{name}' does not have any State Machine equipped.")

        step_id, sm_id = status["current_step_id"], status["equipped_sm_id"]
        call_stack = json.loads(status.get("call_stack", "[]"))
        output = {"name": name, "turn": status["turn_number"],
                  "previous_phase": status["phase"], "action_taken": "", "event_message": ""}

        with self.driver.session() as session:
            # 0. CALLS_SM intercept — push parent frame, switch to child SM
            child_sm_id = lib_lifecycle.find_calls_sm(session, step_id=step_id)
            if child_sm_id:
                entry_id = lib_lifecycle.enter_child_state_machine(
                    session, name=name, child_sm_id=child_sm_id,
                    parent_sm_id=sm_id, parent_step_id=step_id)
                if not entry_id:
                    raise ValueError(f"StateMachine '{child_sm_id}' has no valid entry step.")
                output["action_taken"] = f"Compiler call to sub-state machine '{child_sm_id}'."
                output["event_message"] = (
                    f"Saved parent step '{step_id}' to call stack. "
                    f"Transitioned loadout to child state machine '{child_sm_id}'.")
                return output

            # 1. Step-driven side effects (calibration, fitness, domain expansion)
            output["event_message"] = lib_lifecycle.run_step_side_effects(
                session, name=name, step_id=step_id)

            # 2. Per-cybernet ExecutionState lock (gate)
            from db_logic import is_traversal_locked, query_database
            lib_lifecycle.ensure_lock(session, name=name, step_id=step_id,
                                      is_locked=is_traversal_locked(name))

            # 3. Build prompt + call LLM
            system_prompt = (
                f"You are the Cybernet persona '{name}' with behavior guidelines: "
                f"{status['description']}. Your active model configuration has "
                f"temperature={runner.temperature}, top_p={runner.top_p}.")
            pattern_hint = ""
            if status.get("pattern_description") or status.get("required_pattern"):
                desc = status.get("pattern_description") or status.get("required_pattern")
                pattern_hint = (f"\n\n[TRANSACTION GUARD WARNING]\n"
                                f"To complete this step, the Neo4j transaction guard requires "
                                f"the Cypher query to match: '{desc}'.")
            user_prompt = f"Active step prompt: {status['current_step_text']}{pattern_hint}"
            output["action_taken"] = runner.call_llm(system_prompt, user_prompt, name, step_id)

            # 4. Execute cypher (gated write — auto-progresses on pattern match)
            try:
                results = query_database(output["action_taken"], name)
                event_msg = next((r["_state_machine_event"] for r in results
                                  if "_state_machine_event" in r), "")
                if event_msg:
                    output["event_message"] = (f"{output['event_message']} {event_msg}"
                                                if output["event_message"] else event_msg)
                elif not output["event_message"]:
                    output["event_message"] = "Action query executed successfully."

                # 5. Token + cost accounting
                lib_lifecycle.accumulate_token_cost(session, name=name, sm_id=sm_id)

                # 6. Read back the ExecutionState's CURRENT_STEP (auto_progress
                #    already advanced it; None means the rite completed/unlocked).
                new_step_id = lib_lifecycle.read_active_execution_step(
                    session, name=name, sm_id=sm_id)
                if new_step_id is not None:
                    entry_id = lib_lifecycle.find_entry_step_id(session, sm_id)
                    if new_step_id == entry_id:
                        if status["turn_number"] >= 5:
                            output["event_message"] += (
                                f" [LIFETIME COMPLETED] {self.evaluate_evolution(name)}")
                        else:
                            lib_lifecycle.advance_turn(session, name=name, sm_id=sm_id)
                            output["event_message"] += " State machine completed. Resetting for next Day cycle."
                else:
                    self._handle_call_stack_pop(name, sm_id, call_stack, output)
            except Exception as e:
                output["event_message"] = f"Failed to execute query: {e}"
        return output

    def _handle_call_stack_pop(self, name, sm_id, call_stack, output):
        with self.driver.session() as session:
            if call_stack:
                parent_sm_id, next_step_id = lib_lifecycle.pop_call_stack_until_resolved(
                    session, name=name, call_stack=call_stack)
                if next_step_id and parent_sm_id:
                    lib_lifecycle.return_to_parent(
                        session, name=name, parent_sm_id=parent_sm_id,
                        next_step_id=next_step_id, call_stack=call_stack)
                    output["event_message"] += (
                        f" Sub-state machine completed. Popped call stack. "
                        f"Returned to parent step '{next_step_id}'.")
                    return
        self._trigger_turn_completion(name, sm_id, output)

    def _trigger_turn_completion(self, name, sm_id, output):
        status = self.get_character_status(name)
        if not status:
            return
        if status["turn_number"] >= 5:
            output["event_message"] += f" [LIFETIME COMPLETED] {self.evaluate_evolution(name)}"
        else:
            with self.driver.session() as session:
                entry_id = lib_lifecycle.find_entry_step_id(session, sm_id)
                if not entry_id:
                    return
                lib_lifecycle.reset_turn_to_entry(
                    session, name=name, sm_id=sm_id, entry_id=entry_id)
            output["event_message"] += " State machine completed. Resetting for next Day cycle."

    def evaluate_evolution(self, name: str) -> str:
        status = self.get_character_status(name)
        if not status:
            return "No status found for evolution evaluation."
        with self.driver.session() as session:
            return lib_evolution.evaluate_evolution(session, name=name, status=status)


# Backward-compat alias (was the original module name)
Sh8peshiftEngine = CybernetiCircusCompiler


if __name__ == "__main__":
    try:
        _e = CybernetiCircusCompiler()
        print("Compiler connected successfully to Cyberneticity.")
        _e.close()
    except Exception as e:
        print(f"Compiler connection failed: {e}")
