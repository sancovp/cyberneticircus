#!/usr/bin/env python3
"""
Integration test suite for Surrogate Models in Neo4j Cypher MCP.
Verifies CRUD operations, path simulation, prediction nodes, and calibration loops.
"""
import os
import sys
import json

# Ensure server module is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import query_database, get_driver, crud_surrogate, create_traversal_flow, create_weighted_transition

def run_test():
    print("Starting surrogate model integration tests...")
    print("-" * 60)
    
    driver = get_driver()
    
    # 1. Cleanup
    print("1. Cleaning up previous test data...")
    with driver.session() as session:
        session.run("MATCH (sm:SurrogateModel) DETACH DELETE sm")
        session.run("MATCH (sim:SimulationRun) DETACH DELETE sim")
        session.run("MATCH (pn:PredictionNode) DETACH DELETE pn")
        session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'surr_' DETACH DELETE s")
        session.run("MATCH (t:AgentTask) WHERE t.title = 'Surrogate Test Task' DETACH DELETE t")
    print("   [PASS] Clean starting state verified.")

    # 2. Setup steps with expected diffs and fitnesses
    print("2. Creating TraversalSteps with expected diffs...")
    try:
        # Create steps
        with driver.session() as session:
            session.run(
                """
                CREATE (s1:TraversalStep {
                    id: 'surr_step1', 
                    text: 'Step 1: Choose path',
                    expected_diff: $diff1,
                    expected_fitness: 0.5
                })
                CREATE (s2a:TraversalStep {
                    id: 'surr_step2_fast', 
                    text: 'Step 2 Fast: Execute fast compile',
                    expected_diff: $diff2a,
                    expected_fitness: 1.2
                })
                CREATE (s2b:TraversalStep {
                    id: 'surr_step2_slow', 
                    text: 'Step 2 Slow: Execute slow compile',
                    expected_diff: $diff2b,
                    expected_fitness: 0.8
                })
                """,
                {
                    "diff1": json.dumps({"status": "started"}),
                    "diff2a": json.dumps({"status": "started", "compile": "fast"}),
                    "diff2b": json.dumps({"status": "started", "compile": "slow"})
                }
            )
            
        # Link transitions
        create_weighted_transition("surr_step1", "surr_step2_fast", weight=0.9, description="Fast path choice")
        create_weighted_transition("surr_step1", "surr_step2_slow", weight=0.1, description="Slow path choice")
        
    except Exception as e:
        print(f"2. [FAIL] Setup tools failed: {e}")
        return False
    print("   [PASS] Traversal steps and transitions set up.")

    # 3. Test CRUD Create / Read / Update / Delete
    print("3. Testing SurrogateModel CRUD...")
    try:
        # Create
        msg_create = crud_surrogate(
            action="create",
            parameters={
                "domain": "test_domain",
                "subdomain": "test_subdomain",
                "mutation_rate": 0.0,  # Deterministic selection for testing
                "selection_pressure": 5.0, # High selection pressure
                "reward_weights": {"speed": 0.7, "accuracy": 0.3}
            }
        )
        print(f"   Create response: {msg_create}")
        
        # Read
        model_info = crud_surrogate(
            action="read",
            parameters={"domain": "test_domain", "subdomain": "test_subdomain"}
        )
        print(f"   Read response: {model_info}")
        if not model_info or model_info["mutation_rate"] != 0.0 or model_info["selection_pressure"] != 5.0:
            print("3. [FAIL] Read returned incorrect knobs.")
            return False
            
        # Update
        msg_update = crud_surrogate(
            action="update",
            parameters={
                "domain": "test_domain",
                "subdomain": "test_subdomain",
                "mutation_rate": 0.05,
                "selection_pressure": 4.0,
                "reward_weights": {"speed": 0.5, "accuracy": 0.5}
            }
        )
        print(f"   Update response: {msg_update}")
        
        model_info_updated = crud_surrogate(
            action="read",
            parameters={"domain": "test_domain", "subdomain": "test_subdomain"}
        )
        if not model_info_updated or model_info_updated["mutation_rate"] != 0.05 or model_info_updated["selection_pressure"] != 4.0:
            print("3. [FAIL] Update failed to modify knobs.")
            return False
            
    except Exception as e:
        print(f"3. [FAIL] CRUD actions raised exception: {e}")
        return False
    print("   [PASS] CRUD operations completed successfully.")

    # 4. Test Simulation
    print("4. Executing counterfactual path simulation...")
    # Change mutation rate back to 0.0 to guarantee deterministic choice (fast path weight 0.9 >> slow path 0.1)
    crud_surrogate(
        action="update",
        parameters={
            "domain": "test_domain",
            "subdomain": "test_subdomain",
            "mutation_rate": 0.0,
            "selection_pressure": 10.0
        }
    )
    
    try:
        sim_res = crud_surrogate(
            action="simulate",
            parameters={
                "domain": "test_domain",
                "subdomain": "test_subdomain",
                "start_step_id": "surr_step1",
                "steps_limit": 3
            }
        )
        print(f"   Simulation result: {sim_res}")
        run_id = sim_res["run_id"]
        path = sim_res["path"]
        
        # Verify deterministic path chosen (surr_step1 -> surr_step2_fast)
        if path != ["surr_step1", "surr_step2_fast"]:
            print(f"4. [FAIL] Simulation chose incorrect path: {path}")
            return False
            
        # Verify predicted nodes are in DB
        with driver.session() as session:
            res_nodes = session.run(
                """
                MATCH (sim:SimulationRun {run_id: $run_id})-[:PREDICTS_STATE]->(pn:PredictionNode)
                RETURN pn.step_id as step_id ORDER BY pn.step_id
                """,
                {"run_id": run_id}
            )
            db_steps = [r["step_id"] for r in res_nodes]
            if "surr_step1" not in db_steps or "surr_step2_fast" not in db_steps:
                print(f"4. [FAIL] Predicted nodes not saved correctly in DB: {db_steps}")
                return False
                
    except Exception as e:
        print(f"4. [FAIL] Simulation raised exception: {e}")
        return False
    print("   [PASS] Simulation correctly executed and reified in graph.")

    # 5. Test Calibration Feedback Loop
    print("5. Running calibration feedback loop...")
    # Expected fast path merged diff is {"status": "started", "compile": "fast"} (from surr_step1 + surr_step2_fast)
    # We calibrate with matching actual results (accuracy 100% >= 80% threshold -> success)
    actual_results = {"status": "started", "compile": "fast"}
    
    try:
        # Check transition weight before
        with driver.session() as session:
            weight_before = session.run(
                "MATCH (:TraversalStep {id: 'surr_step1'})-[r:NEXT_STEP]->(:TraversalStep {id: 'surr_step2_fast'}) RETURN r.weight as w"
            ).single()["w"]
            
        cal_res = crud_surrogate(
            action="calibrate",
            parameters={
                "run_id": run_id,
                "actual_diff": actual_results
            }
        )
        print(f"   Calibration result: {cal_res}")
        if cal_res["accuracy"] != 1.0 or not cal_res["success_threshold_met"]:
            print(f"5. [FAIL] Calibration accuracy incorrect: {cal_res}")
            return False
            
        # Check transition weight after (should be reinforced/incremented)
        with driver.session() as session:
            weight_after = session.run(
                "MATCH (:TraversalStep {id: 'surr_step1'})-[r:NEXT_STEP]->(:TraversalStep {id: 'surr_step2_fast'}) RETURN r.weight as w"
            ).single()["w"]
            
        print(f"   Transition weight before: {weight_before}, after: {weight_after}")
        if weight_after != round(weight_before + 0.1, 2):
            print(f"5. [FAIL] Calibration did not correctly increment transition weight.")
            return False
            
    except Exception as e:
        print(f"5. [FAIL] Calibration raised exception: {e}")
        return False
    print("   [PASS] Calibration loop successfully completed and adjusted transition weights.")

    # 6. Test Delete / Clean up
    print("6. Deleting model and verifying cleanup...")
    try:
        crud_surrogate("delete", {"domain": "test_domain", "subdomain": "test_subdomain"})
        
        # Verify model, runs, and predictions are gone
        with driver.session() as session:
            count_sm = session.run("MATCH (sm:SurrogateModel {domain: 'test_domain'}) RETURN count(sm) as c").single()["c"]
            count_sim = session.run("MATCH (sim:SimulationRun {run_id: $run_id}) RETURN count(sim) as c", {"run_id": run_id}).single()["c"]
            
        if count_sm > 0 or count_sim > 0:
            print(f"6. [FAIL] Cleanup failed. SurrogateModel count: {count_sm}, SimulationRun count: {count_sim}")
            return False
            
        # Clean up remaining steps
        with driver.session() as session:
            session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'surr_' DETACH DELETE s")
            
    except Exception as e:
        print(f"6. [FAIL] Cleanup raised exception: {e}")
        return False
    print("   [PASS] Cleanup complete.")
    
    print("-" * 60)
    print("All surrogate model tests passed successfully! 🎉")
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
