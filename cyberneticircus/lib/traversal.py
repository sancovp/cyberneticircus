"""
Traversal — state machine flow + CRUD (steps, transitions, weights, CALLS_SM edges).

Compositions:
  - get_schema             →  GET /api/schema
  - progress_traversal     →  POST /api/traversal/progress
  - create_flow            →  POST /api/traversal/create_flow
  - create_transition      →  POST /api/traversal/create_transition
  - adjust_weight          →  POST /api/traversal/adjust_weight
  - crud_state_machine_calls → POST /api/crud_state_machine_calls
  - crud_surrogate         →  POST /api/crud_surrogate   (SurrogateModel + SimulationRun + PredictionNode)
"""
from __future__ import annotations
import json
import math
import random
import re
import uuid
from typing import Any, Dict, List, Optional


# --- Schema (delegate to gates.get_schema) ----------------------------------

def get_schema(driver) -> Dict[str, Any]:
    """Database labels / relationships / properties dump (for the visualizer's schema panel)."""
    from . import gates
    return gates.get_schema(get_driver=lambda: driver)


# --- Progress (advance :ExecutionState) -------------------------------------

def progress_traversal(driver, *, cybernet_name: str, answer: Optional[str] = None) -> Dict[str, Any]:
    """Advance the given Cybernet's :ExecutionState (read current step → evaluate → move NEXT_STEP).

    Thin facade over the LLM-loop gate in db_logic/gates. Per-cybernet scope:
    the cybernet_name contract matches db_logic.progress_traversal and the MCP tool.
    """
    from db_logic import progress_traversal as _impl
    return {"message": _impl(cybernet_name, answer)}


def get_active_step(driver, *, cybernet_name: str) -> Optional[Dict[str, Any]]:
    """Read the currently-locked TraversalStep for THIS cybernet (per-cybernet scope)."""
    from db_logic import get_active_traversal_step
    return get_active_traversal_step(cybernet_name)


# --- Create flow (multiple TraversalSteps + NEXT_STEP chain) ----------------

def create_flow(driver, *, steps: List[Dict[str, Any]],
                trigger_node_label: Optional[str] = None,
                trigger_node_properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Idempotently MERGE a chain of TraversalSteps + their NEXT_STEP edges + optional trigger."""
    if not steps:
        raise ValueError("at least one step is required")
    for i, step in enumerate(steps):
        if "id" not in step or not step["id"]:
            raise ValueError(f"step at index {i} missing 'id'")
        if "text" not in step or not step["text"]:
            raise ValueError(f"step at index {i} missing 'text'")
        pattern = step.get("required_pattern")
        if pattern:
            try:
                re.compile(pattern)
            except Exception as e:
                raise ValueError(f"invalid regex in step '{step['id']}': {e}")

    trigger_msg = ""
    with driver.session() as session:
        with session.begin_transaction() as tx:
            for step in steps:
                tx.run(
                    """MERGE (step:TraversalStep {id: $id})
                    SET step.text = $text,
                        step.required_pattern = $required_pattern,
                        step.pattern_description = $pattern_description""",
                    {
                        "id": step["id"], "text": step["text"],
                        "required_pattern": step.get("required_pattern"),
                        "pattern_description": step.get("pattern_description"),
                    }
                )
            for i in range(len(steps) - 1):
                tx.run(
                    """MATCH (curr:TraversalStep {id: $curr_id})
                    MATCH (next:TraversalStep {id: $next_id})
                    MERGE (curr)-[r:NEXT_STEP]->(next)
                    ON CREATE SET r.weight = 1.0, r.description = $desc""",
                    {
                        "curr_id": steps[i]["id"],
                        "next_id": steps[i + 1]["id"],
                        "desc": f"Transition from {steps[i]['id']} to {steps[i+1]['id']}",
                    }
                )
            if trigger_node_label and trigger_node_properties:
                props_filter = "{" + ", ".join([f"{k}: ${k}" for k in trigger_node_properties.keys()]) + "}"
                query_trigger = f"""
                MATCH (n:{trigger_node_label} {props_filter})
                SET n.trigger_traversal = $trigger_step_id
                RETURN count(n) as count
                """
                params = dict(trigger_node_properties)
                params["trigger_step_id"] = steps[0]["id"]
                t_res = tx.run(query_trigger, params)
                count = t_res.single()["count"]
                if count == 0:
                    trigger_msg = f" (Warning: No matching {trigger_node_label} node found)"
                else:
                    trigger_msg = f" (Successfully attached trigger to {count} node(s))"
    return {"message": f"Successfully created traversal flow with {len(steps)} steps.{trigger_msg}"}


# --- Create transition (single weighted edge) -------------------------------

def create_transition(driver, *, from_step_id: str, to_step_id: str,
                      weight: float = 1.0, description: str = "") -> Dict[str, Any]:
    """Validate both steps exist + MERGE the weighted NEXT_STEP edge."""
    with driver.session() as session:
        for step_id in (from_step_id, to_step_id):
            res = session.run("MATCH (s:TraversalStep {id: $id}) RETURN count(s) as count", {"id": step_id})
            if res.single()["count"] == 0:
                raise ValueError(f"step '{step_id}' does not exist")
        session.run(
            """MATCH (from:TraversalStep {id: $from_id})
            MATCH (to:TraversalStep {id: $to_id})
            MERGE (from)-[r:NEXT_STEP]->(to)
            SET r.weight = $weight, r.description = $description""",
            {"from_id": from_step_id, "to_id": to_step_id, "weight": float(weight), "description": description}
        )
    return {"message": f"Successfully created transition from '{from_step_id}' to '{to_step_id}' with weight {weight}."}


# --- Adjust weight (success/fail nudge) -------------------------------------

def adjust_weight(driver, *, from_step_id: str, to_step_id: str, success: bool,
                  cybernet_name: str) -> str:
    """Thin facade over db_logic's adjust_transition_weight_internal."""
    from db_logic import adjust_transition_weight_internal
    return adjust_transition_weight_internal(from_step_id, to_step_id, success, cybernet_name)


# --- CRUD: state machine calls (CALLS_SM edges) ------------------------------

def crud_state_machine_calls(driver, *, action: str,
                             from_step_id: str, to_state_machine_id: str) -> Dict[str, Any]:
    """Create or delete a CALLS_SM edge from a TraversalStep to a sub-StateMachine."""
    action = action.lower()
    with driver.session() as session:
        if action == "create":
            for nid, label in ((from_step_id, "TraversalStep"), (to_state_machine_id, "StateMachine")):
                res = session.run(f"MATCH (n:{label} {{id: $id}}) RETURN count(n) as count", {"id": nid})
                if res.single()["count"] == 0:
                    raise ValueError(f"{label} '{nid}' does not exist")
            session.run(
                "MATCH (s:TraversalStep {id: $step_id}) MATCH (sm:StateMachine {id: $sm_id}) MERGE (s)-[:CALLS_SM]->(sm)",
                {"step_id": from_step_id, "sm_id": to_state_machine_id}
            )
            return {"message": f"Successfully linked step '{from_step_id}' to sub-state machine '{to_state_machine_id}'."}
        elif action == "delete":
            session.run(
                "MATCH (s:TraversalStep {id: $step_id})-[r:CALLS_SM]->(sm:StateMachine {id: $sm_id}) DELETE r",
                {"step_id": from_step_id, "sm_id": to_state_machine_id}
            )
            return {"message": f"Successfully deleted compiler call link from '{from_step_id}' to '{to_state_machine_id}'."}
        else:
            raise ValueError(f"unknown action: '{action}' (must be 'create' or 'delete')")


# --- CRUD: SurrogateModel (per-domain/subdomain simulation params) ----------

def _upsert_surrogate(driver, *, domain: str, subdomain: str, params: Dict[str, Any]) -> Dict[str, Any]:
    with driver.session() as session:
        session.run(
            """MERGE (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
            SET sm.mutation_rate = $mutation_rate,
                sm.selection_pressure = $selection_pressure,
                sm.reward_weights = $reward_weights""",
            {
                "domain": domain, "subdomain": subdomain,
                "mutation_rate": float(params.get("mutation_rate", 0.1)),
                "selection_pressure": float(params.get("selection_pressure", 1.0)),
                "reward_weights": json.dumps(params.get("reward_weights", {"accuracy": 1.0})),
            }
        )
    return {"message": f"Successfully saved SurrogateModel for {domain}/{subdomain}."}


def _read_surrogate(driver, *, domain: str, subdomain: str) -> Dict[str, Any]:
    with driver.session() as session:
        rec = session.run(
            """MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
            RETURN sm.mutation_rate as mutation_rate,
                   sm.selection_pressure as selection_pressure,
                   sm.reward_weights as reward_weights""",
            {"domain": domain, "subdomain": subdomain}
        ).single()
        if not rec:
            return {}
        reward_weights = json.loads(rec["reward_weights"]) if rec["reward_weights"] else {}
        sims_res = session.run(
            """MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})-[:HAS_SIMULATION]->(sim:SimulationRun)
            RETURN sim.run_id as run_id, sim.fitness_score as fitness_score,
                   sim.outcome_class as outcome_class, sim.calibrated as calibrated,
                   sim.accuracy as accuracy
            ORDER BY sim.created_at DESC LIMIT 10""",
            {"domain": domain, "subdomain": subdomain}
        )
        return {
            "domain": domain, "subdomain": subdomain,
            "mutation_rate": rec["mutation_rate"],
            "selection_pressure": rec["selection_pressure"],
            "reward_weights": reward_weights,
            "recent_simulations": [
                {"run_id": s["run_id"], "fitness_score": s["fitness_score"],
                 "outcome_class": s["outcome_class"], "calibrated": s["calibrated"],
                 "accuracy": s["accuracy"]}
                for s in sims_res
            ],
        }


def _delete_surrogate(driver, *, domain: str, subdomain: str) -> Dict[str, Any]:
    with driver.session() as session:
        session.run(
            """MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
            OPTIONAL MATCH (sm)-[:HAS_SIMULATION]->(sim:SimulationRun)
            OPTIONAL MATCH (sim)-[:PREDICTS_STATE]->(pn:PredictionNode)
            DETACH DELETE sm, sim, pn""",
            {"domain": domain, "subdomain": subdomain}
        )
    return {"message": f"Successfully deleted SurrogateModel for {domain}/{subdomain}."}


def _simulate_traversal(driver, *, domain: str, subdomain: str,
                        start_step_id: str, steps_limit: int = 5) -> Dict[str, Any]:
    """Run a softmax-weighted random walk over the StateMachine from start_step_id,
    collect expected_diffs and total fitness, then record as a SimulationRun with
    a chain of PREDICTS_STATE→PredictionNode children."""
    info = _read_surrogate(driver, domain=domain, subdomain=subdomain)
    if info:
        mutation_rate = info.get("mutation_rate", 0.1)
        selection_pressure = info.get("selection_pressure", 1.0)
        reward_weights = info.get("reward_weights", {"accuracy": 1.0})
    else:
        mutation_rate, selection_pressure, reward_weights = 0.1, 1.0, {"accuracy": 1.0}

    path: List[str] = []
    expected_diffs: List[Dict[str, Any]] = []
    total_fitness = 0.0
    curr_id = start_step_id

    with driver.session() as session:
        for _ in range(steps_limit):
            step_rec = session.run(
                "MATCH (s:TraversalStep {id: $id}) "
                "RETURN s.text as text, s.expected_diff as expected_diff, s.expected_fitness as expected_fitness",
                {"id": curr_id}
            ).single()
            if not step_rec:
                break
            path.append(curr_id)
            expected_diffs.append(json.loads(step_rec["expected_diff"]) if step_rec["expected_diff"] else {})
            total_fitness += float(step_rec["expected_fitness"] or 0.0)
            trans_res = session.run(
                """MATCH (curr:TraversalStep {id: $curr_id})-[r:NEXT_STEP]->(next:TraversalStep)
                RETURN next.id as id, coalesce(r.weight, 1.0) as weight""",
                {"curr_id": curr_id}
            )
            transitions = [{"id": tr["id"], "weight": tr["weight"]} for tr in trans_res]
            if not transitions:
                break
            exps = [math.exp(tr["weight"] * selection_pressure) for tr in transitions]
            sum_exps = sum(exps)
            probs = [val / sum_exps for val in exps] if sum_exps > 0 else [1.0 / len(transitions)] * len(transitions)
            chosen_tr = random.choice(transitions) if random.random() < mutation_rate else random.choices(transitions, weights=probs)[0]
            curr_id = chosen_tr["id"]

        run_id = str(uuid.uuid4())
        outcome_class = "SUCCESS" if total_fitness >= 1.0 else "PENDING"
        session.run(
            """MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
            CREATE (sim:SimulationRun {
                run_id: $run_id, created_at: timestamp(),
                fitness_score: $fitness_score, outcome_class: $outcome_class, calibrated: false
            })
            CREATE (sm)-[:HAS_SIMULATION]->(sim)""",
            {"domain": domain, "subdomain": subdomain, "run_id": run_id,
             "fitness_score": total_fitness, "outcome_class": outcome_class}
        )
        for i, step_id in enumerate(path):
            session.run(
                """MATCH (sim:SimulationRun {run_id: $run_id})
                CREATE (pn:PredictionNode {step_id: $step_id, expected_diff: $expected_diff})
                CREATE (sim)-[:PREDICTS_STATE {order: $order}]->(pn)""",
                {"run_id": run_id, "step_id": step_id,
                 "expected_diff": json.dumps(expected_diffs[i]), "order": i}
            )
    return {"run_id": run_id, "path": path, "expected_diffs": expected_diffs,
            "expected_fitness": total_fitness, "outcome_class": outcome_class}


def _calibrate_simulation(driver, *, run_id: str, actual_diff: Dict[str, Any],
                          cybernet_name: str) -> Dict[str, Any]:
    """Score a SimulationRun by matching its expected_diffs against actual_diff, then
    nudge each step's transition weight (success on ≥80% match, fail otherwise)."""
    with driver.session() as session:
        steps_data = [
            {"step_id": rec["step_id"],
             "expected_diff": json.loads(rec["expected_diff"]) if rec["expected_diff"] else {}}
            for rec in session.run(
                """MATCH (sim:SimulationRun {run_id: $run_id})-[r:PREDICTS_STATE]->(pn:PredictionNode)
                RETURN pn.step_id as step_id, pn.expected_diff as expected_diff ORDER BY r.order""",
                {"run_id": run_id}
            )
        ]
        if not steps_data:
            raise ValueError(f"no predictions found for run_id '{run_id}'")
        merged_expected = {}
        for step in steps_data:
            merged_expected.update(step["expected_diff"])
        total_actual = len(actual_diff)
        matching = sum(1 for k, v in actual_diff.items() if k in merged_expected and merged_expected[k] == v)
        accuracy = matching / total_actual if total_actual > 0 else 1.0
        success_run = accuracy >= 0.8
        adjustments = []
        for i in range(len(steps_data) - 1):
            from_id, to_id = steps_data[i]["step_id"], steps_data[i + 1]["step_id"]
            adjustments.append(adjust_weight(driver, from_step_id=from_id, to_step_id=to_id,
                                             success=success_run, cybernet_name=cybernet_name))
        session.run(
            """MATCH (sim:SimulationRun {run_id: $run_id})
            SET sim.actual_diff = $actual_diff, sim.accuracy = $accuracy, sim.calibrated = true""",
            {"run_id": run_id, "actual_diff": json.dumps(actual_diff), "accuracy": accuracy}
        )
    return {"run_id": run_id, "accuracy": accuracy, "success_threshold_met": success_run, "adjustments": adjustments}


def crud_surrogate(driver, *, action: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Dispatch a SurrogateModel CRUD action: create|update|read|delete|simulate|calibrate."""
    action = action.lower()
    params = parameters or {}
    if action in ("create", "update"):
        domain, subdomain = params.get("domain"), params.get("subdomain")
        if not domain or not subdomain:
            raise ValueError("domain and subdomain required")
        return _upsert_surrogate(driver, domain=domain, subdomain=subdomain, params=params)
    if action == "read":
        domain, subdomain = params.get("domain"), params.get("subdomain")
        if not domain or not subdomain:
            raise ValueError("domain and subdomain required")
        return _read_surrogate(driver, domain=domain, subdomain=subdomain)
    if action == "delete":
        domain, subdomain = params.get("domain"), params.get("subdomain")
        if not domain or not subdomain:
            raise ValueError("domain and subdomain required")
        return _delete_surrogate(driver, domain=domain, subdomain=subdomain)
    if action == "simulate":
        domain = params.get("domain")
        subdomain = params.get("subdomain")
        start_step_id = params.get("start_step_id")
        steps_limit = int(params.get("steps_limit", 5))
        if not (domain and subdomain and start_step_id):
            raise ValueError("domain, subdomain, and start_step_id required")
        return _simulate_traversal(driver, domain=domain, subdomain=subdomain,
                                  start_step_id=start_step_id, steps_limit=steps_limit)
    if action == "calibrate":
        run_id = params.get("run_id")
        actual_diff = params.get("actual_diff")
        cybernet_name = params.get("cybernet_name")
        if not run_id or actual_diff is None or not cybernet_name:
            raise ValueError("run_id, actual_diff, and cybernet_name required")
        return _calibrate_simulation(driver, run_id=run_id, actual_diff=actual_diff,
                                     cybernet_name=cybernet_name)
    raise ValueError(f"unknown action: '{action}'")
