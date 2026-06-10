#!/usr/bin/env python3
"""
Integration test suite for the create_traversal_flow tool in Neo4j Cypher MCP.
Verifies sequence creation, trigger node linking, query pattern progression, and error handling.
"""
import os
import sys

# Ensure server module is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import query_database, get_driver, is_traversal_locked, create_traversal_flow

def run_test():
    print("Starting create_traversal_flow integration tests...")
    print("-" * 60)
    
    driver = get_driver()
    
    # 1. Clean up previous test data
    print("1. Cleaning up previous test data...")
    with driver.session() as session:
        session.run("MATCH (s:TraversalState) DETACH DELETE s")
        session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'flow_step' DETACH DELETE s")
        session.run("MATCH (t:AgentTask) WHERE t.title = 'Create Flow Test Task' DETACH DELETE t")
        session.run("MATCH (c:FlowCheck) DETACH DELETE c")
    
    if is_traversal_locked():
        print("1. [FAIL] Traversal lock is still active after cleanup.")
        return False
    print("   [PASS] Clean starting state verified.")

    # 2. Setup trigger node using direct session
    print("2. Creating trigger node (AgentTask)...")
    with driver.session() as session:
        session.run("CREATE (:AgentTask {title: 'Create Flow Test Task', status: 'pending'})")
    print("   [PASS] Trigger node created.")

    # 3. Test validation error with invalid regex
    print("3. Testing invalid regex detection...")
    invalid_steps = [
        {"id": "flow_step1", "text": "Step 1", "required_pattern": "*invalid regex*", "pattern_description": "bad"}
    ]
    try:
        create_traversal_flow(invalid_steps)
        print("3. [FAIL] Expected ValueError for invalid regex, but tool succeeded.")
        return False
    except ValueError as e:
        print(f"   [PASS] Invalid regex correctly rejected: {e}")

    # 4. Create a valid 2-step traversal flow and attach it to the task node
    print("4. Executing create_traversal_flow...")
    valid_steps = [
        {
            "id": "flow_step1",
            "text": "First, create a flow check node with status ok.",
            "required_pattern": r"(?i)CREATE\s*\(c:FlowCheck\s*\{.*status:\s*['\"]ok['\"].*\}\)",
            "pattern_description": 'CREATE (c:FlowCheck {status: "ok", ...})'
        },
        {
            "id": "flow_step2",
            "text": "Second, set the task status to completed.",
            "required_pattern": r"(?i)MATCH\s*\(t:AgentTask.*?\)\s*SET\s*t\.status\s*=\s*['\"]completed['\"]",
            "pattern_description": "MATCH (t:AgentTask) SET t.status = 'completed'"
        }
    ]
    
    try:
        msg = create_traversal_flow(
            steps=valid_steps,
            trigger_node_label="AgentTask",
            trigger_node_properties={"title": "Create Flow Test Task"}
        )
        print(f"   Tool return message: {msg}")
        if "Successfully created traversal flow" not in msg:
            print("4. [FAIL] Success message not returned or invalid.")
            return False
        if "Successfully attached trigger" not in msg:
            print("4. [FAIL] Trigger was not attached.")
            return False
    except Exception as e:
        print(f"4. [FAIL] Tool raised unexpected exception: {e}")
        return False
    print("   [PASS] Flow created and trigger attached.")

    # 5. Verify database structure using direct session
    print("5. Verifying step and sequence structure in DB...")
    with driver.session() as session:
        # Check steps exist
        res = session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'flow_step' RETURN s.id as id, s.text as text")
        db_steps = {r["id"]: r["text"] for r in res}
        if "flow_step1" not in db_steps or "flow_step2" not in db_steps:
            print(f"5. [FAIL] Expected steps not found in DB: {db_steps}")
            return False
            
        # Check NEXT_STEP relationship
        res_rel = session.run("MATCH (s1:TraversalStep {id: 'flow_step1'})-[:NEXT_STEP]->(s2:TraversalStep {id: 'flow_step2'}) RETURN count(*) as count")
        if res_rel.single()["count"] == 0:
            print("5. [FAIL] NEXT_STEP relationship between step1 and step2 not found.")
            return False
            
        # Check trigger property
        res_trigger = session.run("MATCH (t:AgentTask {title: 'Create Flow Test Task'}) RETURN t.trigger_traversal as trigger")
        trigger_val = res_trigger.single()["trigger"]
        if trigger_val != "flow_step1":
            print(f"5. [FAIL] Trigger property on task node was: {trigger_val}, expected 'flow_step1'")
            return False
            
    print("   [PASS] Graph structures validated.")

    # 6. Test flow execution via query_database
    print("6. Fetching task to trigger traversal lock...")
    res_fetch = query_database("MATCH (t:AgentTask {title: 'Create Flow Test Task'}) RETURN t")
    if not is_traversal_locked():
        print("6. [FAIL] Traversal was not locked on node fetch.")
        return False
    print("   [PASS] Lock activated.")

    print("7. Running invalid write query (should be blocked)...")
    try:
        query_database("CREATE (n:SomeNode {val: 999})")
        print("7. [FAIL] Write succeeded while locked.")
        return False
    except PermissionError as e:
        print(f"   [PASS] Write blocked correctly: {e}")

    print("8. Running matching query for Step 1 (should auto-progress)...")
    res_progress = query_database("CREATE (c:FlowCheck {status: 'ok', owner: 'test_runner'}) RETURN c")
    event = None
    for record in res_progress:
        if "_state_machine_event" in record:
            event = record["_state_machine_event"]
            break
    if not event or "Next step: 'flow_step2'" not in event:
        print(f"8. [FAIL] Progression event not found or incorrect: {event}")
        return False
    if not is_traversal_locked():
        print("8. [FAIL] Lock deactivated early.")
        return False
    print("   [PASS] Successfully auto-progressed to Step 2.")

    print("9. Running matching query for Step 2 (should auto-complete and unlock)...")
    res_complete = query_database("MATCH (t:AgentTask {title: 'Create Flow Test Task'}) SET t.status = 'completed' RETURN t")
    event2 = None
    for record in res_complete:
        if "_state_machine_event" in record:
            event2 = record["_state_machine_event"]
            break
    if not event2 or "UNLOCKED" not in event2:
        print(f"9. [FAIL] Completion event not found or incorrect: {event2}")
        return False
    if is_traversal_locked():
        print("9. [FAIL] Database remains locked after traversal completion.")
        return False
    print("   [PASS] Successfully completed traversal and unlocked database.")

    # 10. Clean up
    print("10. Cleaning up test data...")
    with driver.session() as session:
        session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'flow_step' DETACH DELETE s")
        session.run("MATCH (t:AgentTask) WHERE t.title = 'Create Flow Test Task' DETACH DELETE t")
        session.run("MATCH (c:FlowCheck) DETACH DELETE c")
    print("    [PASS] Cleanup complete.")
    
    print("-" * 60)
    print("All create_traversal_flow tests passed successfully! 🎉")
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
