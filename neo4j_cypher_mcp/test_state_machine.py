#!/usr/bin/env python3
"""
Integration test suite for Automatic Query-Pattern Gating in Neo4j Cypher MCP.
Tests the lock trigger, invalid writes blocking, matching query execution,
automatic progression, and full unlock.
"""
import os
import sys

# Ensure server module is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import query_database, get_driver, is_traversal_locked

def run_auto_gating_test():
    print("Starting Automatic Query-Pattern Gating integration tests...")
    print("-" * 60)
    
    # 1. Reset database state using direct session (bypasses MCP tool locks)
    print("1. Cleaning up previous test data...")
    driver = get_driver()
    with driver.session() as session:
        session.run("MATCH (s:TraversalState) DETACH DELETE s")
        session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'test_step' DETACH DELETE s")
        session.run("MATCH (t:AgentTask) WHERE t.title = 'Release Code' DETACH DELETE t")
        session.run("MATCH (n:SomeNode) DETACH DELETE n")
        session.run("MATCH (c:CompileCheck) DETACH DELETE c")
    
    if is_traversal_locked():
        print("1. [FAIL] Traversal lock is still active after cleanup.")
        return
    print("   [PASS] Clean starting state verified (Writes unlocked).")
    
    # 2. Setup steps using direct session to avoid triggering safety rules
    print("2. Creating TraversalStep checklist and AgentTask in Neo4j...")
    with driver.session() as session:
        session.run(
            """
            CREATE (s:TraversalStep {
                id: $id, 
                text: $text,
                required_pattern: $pattern,
                pattern_description: $desc
            })
            """,
            {
                "id": "test_step1",
                "text": "Step 1: Create compile verification node",
                "pattern": r"(?i)CREATE\s*\(c:CompileCheck\s*\{.*status:\s*['\"]passed['\"].*\}\)",
                "desc": 'CREATE (c:CompileCheck {status: "passed", ...})'
            }
        )
        session.run(
            """
            CREATE (s:TraversalStep {
                id: $id, 
                text: $text,
                required_pattern: $pattern,
                pattern_description: $desc
            })
            """,
            {
                "id": "test_step2",
                "text": "Step 2: Set task status to completed",
                "pattern": r"(?i)MATCH\s*\(t:AgentTask.*?\)\s*SET\s*t\.status\s*=\s*['\"]completed['\"]",
                "desc": "MATCH (t:AgentTask) SET t.status = 'completed'"
            }
        )
        session.run("MATCH (s1:TraversalStep {id: 'test_step1'}), (s2:TraversalStep {id: 'test_step2'}) CREATE (s1)-[:NEXT_STEP]->(s2)")
        session.run("CREATE (t:AgentTask {title: 'Release Code', trigger_traversal: 'test_step1'})")
    print("   [PASS] Setup complete.")
    
    # 3. Fetch task to auto-trigger the lock
    print("3. Querying task to trigger state machine lock...")
    res = query_database("MATCH (t:AgentTask {title: 'Release Code'}) RETURN t")
    if not res or 'trigger_traversal' not in res[0]['t']['properties']:
        print("3. [FAIL] Task not returned properly.")
        return
        
    if not is_traversal_locked():
        print("3. [FAIL] Traversal lock was not triggered.")
        return
    print("   [PASS] Traversal lock successfully triggered and active.")
    
    # 4. Verify invalid write queries are blocked at Step 1
    print("4. Testing invalid write query at Step 1...")
    try:
        query_database("CREATE (n:SomeNode {val: 1})")
        print("4. [FAIL] Invalid write query CREATE succeeded while locked!")
        return
    except PermissionError as e:
        print(f"   [PASS] Write blocked correctly. Error message: {e}")
        
    # 5. Run matching query for Step 1
    print("5. Executing matching query for Step 1 to auto-progress...")
    res1 = query_database("CREATE (c:CompileCheck {status: 'passed', verified_by: 'test_runner'}) RETURN c")
    print(f"   Query returned result count: {len(res1)}")
    
    # Check if results contains the state machine event
    event = None
    for record in res1:
        if "_state_machine_event" in record:
            event = record["_state_machine_event"]
            break
            
    if not event:
        print("5. [FAIL] Step 1 executed but did not return progression event metadata.")
        return
        
    print(f"   [PASS] Progression event returned: {event}")
    if "Next step: 'test_step2'" not in event:
        print("5. [FAIL] Did not progress to test_step2.")
        return
        
    if not is_traversal_locked():
        print("5. [FAIL] Lock deactivated early.")
        return
    print("   [PASS] Auto-progressed to Step 2. writes remain locked.")
    
    # 6. Verify Step 1 query is now blocked at Step 2 (since required pattern changed)
    print("6. Testing Step 1 query at Step 2...")
    try:
        query_database("CREATE (c:CompileCheck {status: 'passed'})")
        print("6. [FAIL] Step 1 query succeeded at Step 2!")
        return
    except PermissionError as e:
        print(f"   [PASS] Step 1 query blocked at Step 2: {e}")
        
    # 7. Run matching query for Step 2 to auto-complete
    print("7. Executing matching query for Step 2 to auto-complete and unlock...")
    res2 = query_database("MATCH (t:AgentTask {title: 'Release Code'}) SET t.status = 'completed' RETURN t")
    
    event2 = None
    for record in res2:
        if "_state_machine_event" in record:
            event2 = record["_state_machine_event"]
            break
            
    if not event2:
        print("7. [FAIL] Step 2 executed but did not return completion event metadata.")
        return
        
    print(f"   [PASS] Completion event returned: {event2}")
    if "Database writes are UNLOCKED" not in event2:
        print("7. [FAIL] Event did not declare writes unlocked.")
        return
        
    if is_traversal_locked():
        print("7. [FAIL] Database remains locked after completing traversal.")
        return
    print("   [PASS] Auto-completed. Lock deactivated.")
    
    # 8. Verify writes are fully unlocked now
    print("8. Testing arbitrary write query post-unlock...")
    try:
        write_res = query_database("CREATE (n:SomeNode {val: 100}) RETURN n")
        print(f"   [PASS] Arbitrary write query succeeded: {write_res}")
    except Exception as e:
        print(f"8. [FAIL] Write query failed after unlock: {e}")
        return
        
    # 9. Clean up test data using direct session
    print("9. Cleaning up test data...")
    with driver.session() as session:
        session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'test_step' DETACH DELETE s")
        session.run("MATCH (t:AgentTask) WHERE t.title = 'Release Code' DETACH DELETE t")
        session.run("MATCH (n:SomeNode) DETACH DELETE n")
        session.run("MATCH (c:CompileCheck) DETACH DELETE c")
    print("   [PASS] Cleanup complete.")
    
    print("-" * 60)
    print("All Automatic Query-Pattern Gating tests passed successfully! 🎉")

if __name__ == "__main__":
    run_auto_gating_test()
