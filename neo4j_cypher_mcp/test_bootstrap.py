#!/usr/bin/env python3
"""
Integration test suite for automatic graph bootstrapping and Surrogate Mastery Flow.
Verifies database bootstrapping, entry listing in commands(), and step-by-step query matching.
"""
import os
import sys
import json

# Ensure server module is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import query_database, get_driver, is_traversal_locked, commands, populate_default_graphs

def run_test():
    print("Starting automatic graph bootstrapping integration tests...")
    print("-" * 60)
    
    driver = get_driver()
    
    # 1. Wipe database to test clean bootstrapping
    print("1. Wiping existing state machines and default task nodes...")
    with driver.session() as session:
        session.run("MATCH (s:TraversalState) DETACH DELETE s")
        session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'surrogate_' DETACH DELETE s")
        session.run("MATCH (t:AgentTask) WHERE t.id = 'learn_surrogates' DETACH DELETE t")
        session.run("MATCH (sm:SurrogateModel {domain: 'agent_memory'}) DETACH DELETE sm")
        session.run("MATCH (sim:SimulationRun) DETACH DELETE sim")
        
    if is_traversal_locked():
        print("1. [FAIL] Traversal lock is still active after cleanup.")
        return False
    print("   [PASS] Database wiped successfully.")
    
    # 2. Trigger bootstrapping
    print("2. Triggering automatic graph bootstrapping...")
    try:
        populate_default_graphs(driver)
    except Exception as e:
        print(f"2. [FAIL] Bootstrapping function raised exception: {e}")
        return False
    print("   [PASS] Bootstrapping executed successfully.")
    
    # 3. Verify graph structures exist in Neo4j
    print("3. Verifying bootstrapped steps and sequence in DB...")
    with driver.session() as session:
        # Check steps exist
        res = session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'surrogate_' RETURN s.id as id")
        db_steps = [r["id"] for r in res]
        expected_steps = ["surrogate_read_model", "surrogate_init_model", "surrogate_run_simulation", "surrogate_calibrate"]
        for est in expected_steps:
            if est not in db_steps:
                print(f"3. [FAIL] Expected step '{est}' not bootstrapped in DB. Found: {db_steps}")
                return False
                
        # Check NEXT_STEP links
        res_rel = session.run(
            """
            MATCH (s1:TraversalStep {id: 'surrogate_read_model'})-[:NEXT_STEP]->(s2:TraversalStep {id: 'surrogate_init_model'})-[:NEXT_STEP]->(s3:TraversalStep {id: 'surrogate_run_simulation'})-[:NEXT_STEP]->(s4:TraversalStep {id: 'surrogate_calibrate'})
            RETURN count(*) as count
            """
        )
        if res_rel.single()["count"] == 0:
            print("3. [FAIL] Bootstrapped steps are not chained sequentially.")
            return False
            
        # Check trigger task
        res_task = session.run("MATCH (t:AgentTask {id: 'learn_surrogates'}) RETURN t.trigger_traversal as trigger")
        record_task = res_task.single()
        if not record_task or record_task["trigger"] != "surrogate_read_model":
            print(f"3. [FAIL] Bootstrapped AgentTask trigger is missing or incorrect: {record_task}")
            return False
            
    print("   [PASS] Graph structures correctly bootstrapped and verified.")
    
    # 4. Verify commands() lists entry point
    print("4. Verifying commands() lists the bootstrapped flow...")
    try:
        available_cmds = commands()
        cmd_ids = [c["id"] for c in available_cmds]
        print(f"   Available commands: {cmd_ids}")
        if "surrogate_read_model" not in cmd_ids:
            print("4. [FAIL] surrogate_read_model not listed in commands().")
            return False
    except Exception as e:
        print(f"4. [FAIL] commands() raised exception: {e}")
        return False
    print("   [PASS] Flow entry listed correctly.")

    # 5. Run through Surrogate Mastery Flow
    print("5. Querying trigger task to lock database writes...")
    query_database("MATCH (t:AgentTask {id: 'learn_surrogates'}) RETURN t")
    if not is_traversal_locked():
        print("5. [FAIL] Database writes did not lock on task query.")
        return False
    print("   [PASS] Database writes locked at surrogate_read_model.")

    # Step 1 -> Step 2
    print("6. Running query matching Step 1 pattern (MATCH SurrogateModel)...")
    res1 = query_database("MATCH (sm:SurrogateModel {domain: 'agent_memory', subdomain: 'traversal'}) RETURN sm")
    event1 = None
    for record in res1:
        if "_state_machine_event" in record:
            event1 = record["_state_machine_event"]
            break
    if not event1 or "Next step: 'surrogate_init_model'" not in event1:
        print(f"6. [FAIL] Progression to surrogate_init_model failed. Event: {event1}")
        return False
    print("   [PASS] Advanced to surrogate_init_model.")

    # Step 2 -> Step 3
    print("7. Running query matching Step 2 pattern (MERGE SurrogateModel)...")
    res2 = query_database(
        """
        MERGE (sm:SurrogateModel {domain: 'agent_memory', subdomain: 'traversal'})
        SET sm.mutation_rate = 0.1
        RETURN sm
        """
    )
    event2 = None
    for record in res2:
        if "_state_machine_event" in record:
            event2 = record["_state_machine_event"]
            break
    if not event2 or "Next step: 'surrogate_run_simulation'" not in event2:
        print(f"7. [FAIL] Progression to surrogate_run_simulation failed. Event: {event2}")
        return False
    print("   [PASS] Advanced to surrogate_run_simulation.")

    # Step 3 -> Step 4
    print("8. Running query matching Step 3 pattern (MATCH SimulationRun)...")
    res3 = query_database("MATCH (sim:SimulationRun) RETURN sim")
    event3 = None
    for record in res3:
        if "_state_machine_event" in record:
            event3 = record["_state_machine_event"]
            break
    if not event3 or "Next step: 'surrogate_calibrate'" not in event3:
        print(f"8. [FAIL] Progression to surrogate_calibrate failed. Event: {event3}")
        return False
    print("   [PASS] Advanced to surrogate_calibrate.")

    # Step 4 -> Unlock
    print("9. Running query matching Step 4 pattern (MATCH calibrated SimulationRun) to complete and unlock...")
    res4 = query_database("MATCH (sim:SimulationRun {calibrated: true}) RETURN sim")
    event4 = None
    for record in res4:
        if "_state_machine_event" in record:
            event4 = record["_state_machine_event"]
            break
    if not event4 or "UNLOCKED" not in event4:
        print(f"9. [FAIL] Completion failed. Event: {event4}")
        return False
        
    if is_traversal_locked():
        print("9. [FAIL] Traversal lock still active after completion query.")
        return False
    print("   [PASS] Completed flow and unlocked database writes.")

    # 10. Clean up test database nodes
    print("10. Cleaning up test data...")
    with driver.session() as session:
        session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'surrogate_' DETACH DELETE s")
        session.run("MATCH (t:AgentTask) WHERE t.id = 'learn_surrogates' DETACH DELETE t")
        session.run("MATCH (sm:SurrogateModel {domain: 'agent_memory'}) DETACH DELETE sm")
    print("    [PASS] Database cleaned up.")

    print("-" * 60)
    print("All bootstrapping and Surrogate Mastery Flow tests passed successfully! 🎉")
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
