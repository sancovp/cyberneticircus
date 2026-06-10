#!/usr/bin/env python3
"""
Integration test suite for branching, weighted policy graph traversals in Neo4j Cypher MCP.
Verifies selection routing, block messages with options, leaf step completion, and weight updates.
"""
import os
import sys

# Ensure server module is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import (
    query_database, 
    get_driver, 
    is_traversal_locked, 
    create_traversal_flow, 
    create_weighted_transition, 
    adjust_transition_weight
)

def run_test():
    print("Starting branching policy graph integration tests...")
    print("-" * 60)
    
    driver = get_driver()
    
    # 1. Clean up previous test data
    print("1. Cleaning up previous test data...")
    with driver.session() as session:
        session.run("MATCH (s:TraversalState) DETACH DELETE s")
        session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'branch_' DETACH DELETE s")
        session.run("MATCH (t:AgentTask) WHERE t.title = 'Branch Test Task' DETACH DELETE t")
        session.run("MATCH (n:SomeNode) DETACH DELETE n")
        session.run("MATCH (c:BranchCheck) DETACH DELETE c")
    
    if is_traversal_locked():
        print("1. [FAIL] Traversal lock is still active after cleanup.")
        return False
    print("   [PASS] Clean starting state verified.")

    # 2. Setup steps using our tools
    print("2. Creating branching steps and transitions...")
    try:
        # Create trigger node first so trigger linking works
        with driver.session() as session:
            session.run("CREATE (:AgentTask {title: 'Branch Test Task', status: 'pending'})")

        # Step 1: Decision point (has no pattern, leads to fast/slow paths)
        create_traversal_flow(
            steps=[{"id": "branch_step1", "text": "Step 1: Choose compile method."}],
            trigger_node_label="AgentTask",
            trigger_node_properties={"title": "Branch Test Task"}
        )
        
        # Step 2 Fast: Leaf step that completes traversal
        create_traversal_flow(
            steps=[
                {
                    "id": "branch_step2_fast",
                    "text": "Step 2 Fast: Verify fast compile node.",
                    "required_pattern": r"(?i)CREATE\s*\(c:BranchCheck\s*\{.*method:\s*['\"]fast['\"].*\}\)",
                    "pattern_description": 'CREATE (c:BranchCheck {method: "fast", ...})'
                }
            ]
        )
        
        # Step 2 Slow: Leaf step that completes traversal
        create_traversal_flow(
            steps=[
                {
                    "id": "branch_step2_slow",
                    "text": "Step 2 Slow: Verify slow compile node.",
                    "required_pattern": r"(?i)CREATE\s*\(c:BranchCheck\s*\{.*method:\s*['\"]slow['\"].*\}\)",
                    "pattern_description": 'CREATE (c:BranchCheck {method: "slow", ...})'
                }
            ]
        )
        
        # Create weighted transitions from step1
        create_weighted_transition(
            from_step_id="branch_step1",
            to_step_id="branch_step2_fast",
            weight=0.8,
            description="Use fast compilation bypass"
        )
        create_weighted_transition(
            from_step_id="branch_step1",
            to_step_id="branch_step2_slow",
            weight=0.2,
            description="Use complete slow compilation verification"
        )
            
    except Exception as e:
        print(f"2. [FAIL] Setup tools failed: {e}")
        return False
    print("   [PASS] Branching steps created and transitions linked.")

    # 3. Trigger traversal lock
    print("3. Querying task to trigger traversal lock...")
    query_database("MATCH (t:AgentTask {title: 'Branch Test Task'}) RETURN t")
    if not is_traversal_locked():
        print("3. [FAIL] Traversal lock was not activated.")
        return False
    print("   [PASS] Traversal locked at branch_step1.")

    # 4. Verify blocked writes show choice list in Error Message
    print("4. Testing invalid write at decision point (should show options)...")
    try:
        query_database("CREATE (n:SomeNode {val: 999})")
        print("4. [FAIL] Write succeeded at decision point!")
        return False
    except PermissionError as e:
        err_msg = str(e)
        print(f"   Blocked error message details:\n{err_msg}")
        if "branch_step2_fast" not in err_msg or "branch_step2_slow" not in err_msg:
            print("4. [FAIL] Blocked error message did not print available choices correctly.")
            return False
        if "0.8" not in err_msg or "0.2" not in err_msg:
            print("4. [FAIL] Blocked error message did not print weights correctly.")
            return False
    print("   [PASS] Invalid write correctly blocked with detailed options and cognitive weights.")

    # 5. Route dynamically to the slow path
    print("5. Executing slow compile matching query to dynamically route...")
    res_route = query_database("CREATE (c:BranchCheck {method: 'slow', detail: 'full-check'}) RETURN c")
    event = None
    for record in res_route:
        if "_state_machine_event" in record:
            event = record["_state_machine_event"]
            break
            
    if not event or "Next step: 'branch_step2_slow'" not in event:
        print(f"5. [FAIL] Dynamic routing failed or returned incorrect event: {event}")
        return False
    if not is_traversal_locked():
        print("5. [FAIL] Traversal unlocked early after transition.")
        return False
    print("   [PASS] Dynamically routed to branch_step2_slow. Writes remain locked.")

    # 6. Verify fast path query is now blocked (since we are now locked inside the slow path step)
    print("6. Verifying fast compile query is blocked at slow step...")
    try:
        query_database("CREATE (c:BranchCheck {method: 'fast'})")
        print("6. [FAIL] Fast query succeeded while locked at slow step!")
        return False
    except PermissionError as e:
        print(f"   [PASS] Fast query blocked as expected: {e}")

    # 7. Complete leaf slow step to unlock database
    print("7. Running matching query for slow step to complete and unlock...")
    # Wait, the pattern is: CREATE (c:BranchCheck {method: 'slow', ...})
    # Since we are at branch_step2_slow (which is a leaf and has this required pattern), running it should complete it.
    res_complete = query_database("CREATE (c:BranchCheck {method: 'slow', confirmed: true}) RETURN c")
    event2 = None
    for record in res_complete:
        if "_state_machine_event" in record:
            event2 = record["_state_machine_event"]
            break
            
    if not event2 or "UNLOCKED" not in event2:
        print(f"7. [FAIL] Completion event not found or incorrect: {event2}")
        return False
    if is_traversal_locked():
        print("7. [FAIL] Database remains locked after leaf step completion.")
        return False
    print("   [PASS] Leaf step executed successfully, traversal completed, and writes unlocked.")

    # 8. Verify self-learning weight updates
    print("8. Verifying weight adjustments...")
    try:
        # Check starting weights (0.8 and 0.2)
        # Verify success case (increment)
        msg_inc = adjust_transition_weight("branch_step1", "branch_step2_slow", success=True)
        print(f"   Increment result: {msg_inc}")
        if "0.2 to 0.3" not in msg_inc:
            print(f"8. [FAIL] Weight increment incorrect: {msg_inc}")
            return False
            
        # Verify failure case (decrement)
        msg_dec = adjust_transition_weight("branch_step1", "branch_step2_fast", success=False)
        print(f"   Decrement result: {msg_dec}")
        if "0.8 to 0.6" not in msg_dec:
            print(f"8. [FAIL] Weight decrement incorrect: {msg_dec}")
            return False
    except Exception as e:
        print(f"8. [FAIL] Weight updates failed: {e}")
        return False
    print("   [PASS] Weight updates validated.")

    # 9. Cleanup
    print("9. Cleaning up test data...")
    with driver.session() as session:
        session.run("MATCH (s:TraversalStep) WHERE s.id STARTS WITH 'branch_' DETACH DELETE s")
        session.run("MATCH (t:AgentTask) WHERE t.title = 'Branch Test Task' DETACH DELETE t")
        session.run("MATCH (n:SomeNode) DETACH DELETE n")
        session.run("MATCH (c:BranchCheck) DETACH DELETE c")
    print("   [PASS] Cleanup complete.")
    
    print("-" * 60)
    print("All branching policy graph tests passed successfully! 🎉")
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
