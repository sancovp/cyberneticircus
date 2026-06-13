#!/usr/bin/env python3
import sys
import os
import json

# Ensure python can import from the cyberneticircus folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import CybernetiCircusCompiler, AgentLLMRunner

def verify_summoning():
    print("Starting Janic Daemon Summoning Verification...")
    print("=" * 60)
    
    # 1. Initialize Engine
    print("1. Connecting to CybernetiCircus Compiler...")
    try:
        engine = CybernetiCircusCompiler()
    except Exception as e:
        print(f"1. [FAIL] Connection failed: {e}")
        return False
    print("   [PASS] Connection verified.")
    
    # 2. Cleanup existing test nodes
    print("2. Cleaning up any leftover test daemon data...")
    test_name = "test_daemon_jester"
    with engine.driver.session() as session:
        session.run("MATCH (m:Cybernet) WHERE m.name STARTS WITH $name DETACH DELETE m", {"name": test_name})
        # (the per-cybernet ExecutionState is removed by the DETACH DELETE above)
    print("   [PASS] Wiped previous test data.")
    
    # 3. Create Cybernet
    print(f"3. Creating Cybernet '{test_name}'...")
    try:
        msg = engine.create_cybernet(
            name=test_name,
            description="A test daemon jester for summoning state machine validation.",
            model_name="test-engine-v1",
            temperature=1.0,
            top_p=0.95,
            mutation_rate=0.5,
            selection_pressure=2.0
        )
        print(f"   Response: {msg}")
    except Exception as e:
        print(f"3. [FAIL] Character creation failed: {e}")
        engine.close()
        return False
        
    status = engine.get_character_status(test_name)
    if not status or status["name"] != test_name:
        print(f"3. [FAIL] Character not found in DB status lookup: {status}")
        engine.close()
        return False
    print("   [PASS] Cybernet created and verified.")
    
    # 4. Equip State Machine
    print("4. Equipping State Machine 'janic_daemon_summoning_sm'...")
    try:
        equip_msg = engine.equip_state_machine(test_name, "janic_daemon_summoning_sm")
        print(f"   Equip Response: {equip_msg}")
    except Exception as e:
        print(f"4. [FAIL] Equipping state machine failed: {e}")
        engine.close()
        return False
    
    status = engine.get_character_status(test_name)
    if status["equipped_sm_id"] != "janic_daemon_summoning_sm":
        print(f"4. [FAIL] Incorrect equipped state machine ID: {status['equipped_sm_id']}")
        engine.close()
        return False
    print("   [PASS] State machine equipped successfully.")
    
    # Run the ticks
    runner = AgentLLMRunner(model_name="test-engine-v1", temperature=1.0, top_p=0.95, max_tokens=2048)
    
    # Step 1: daemon_verify_identity
    print("\n--- Ticking Step 1: daemon_verify_identity ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    if status['current_step_id'] != "daemon_verify_identity":
        print(f"   [FAIL] Expected current step to be daemon_verify_identity, got: {status['current_step_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    # Step 2: daemon_allocate_lifecycle
    print("\n--- Ticking Step 2: daemon_allocate_lifecycle ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    if status['current_step_id'] != "daemon_allocate_lifecycle":
        print(f"   [FAIL] Expected current step to be daemon_allocate_lifecycle, got: {status['current_step_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    # Step 3: daemon_equip_core
    print("\n--- Ticking Step 3: daemon_equip_core (Compiler Call triggers child SM) ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    if status['current_step_id'] != "daemon_equip_core":
        print(f"   [FAIL] Expected current step to be daemon_equip_core, got: {status['current_step_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    # Step 3.1: concentric_spiritual (child SM)
    print("\n--- Ticking Concentric Step 1: concentric_spiritual ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    print(f"   Equipped SM : {status['equipped_sm_id']}")
    print(f"   Call Stack  : {status['call_stack']}")
    if status['current_step_id'] != "concentric_spiritual" or status['equipped_sm_id'] != "concentric_core_sm":
        print(f"   [FAIL] Expected child SM step concentric_spiritual, got: {status['current_step_id']} on {status['equipped_sm_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    # Step 3.2: concentric_wealth
    print("\n--- Ticking Concentric Step 2: concentric_wealth ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    if status['current_step_id'] != "concentric_wealth":
        print(f"   [FAIL] Expected concentric_wealth, got: {status['current_step_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    # Step 3.3: concentric_social
    print("\n--- Ticking Concentric Step 3: concentric_social ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    if status['current_step_id'] != "concentric_social":
        print(f"   [FAIL] Expected concentric_social, got: {status['current_step_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    # Step 3.4: concentric_health
    print("\n--- Ticking Concentric Step 4: concentric_health (Completion loops back to parent) ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    if status['current_step_id'] != "concentric_health":
        print(f"   [FAIL] Expected concentric_health, got: {status['current_step_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    # Step 4: daemon_ignite_loop
    print("\n--- Ticking Step 4: daemon_ignite_loop ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    print(f"   Equipped SM : {status['equipped_sm_id']}")
    print(f"   Call Stack  : {status['call_stack']}")
    if status['current_step_id'] != "daemon_ignite_loop" or status['equipped_sm_id'] != "janic_daemon_summoning_sm":
        print(f"   [FAIL] Expected return to daemon_ignite_loop, got: {status['current_step_id']} on {status['equipped_sm_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    # Verify ExecutionState is active
    print("\n--- Verifying Final Sumonning ExecutionState Status ---")
    with engine.driver.session() as session:
        res = session.run(
            """
            MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState)
            RETURN s.status as status, s.equipped_sm_id as sm_id
            """,
            {"name": test_name}
        )
        rec = res.single()
        if not rec:
            print("   [FAIL] ExecutionState node not found.")
            engine.close()
            return False
            
        print(f"   ExecutionState status: {rec['status']}")
        print(f"   ExecutionState equipped SM: {rec['sm_id']}")
        if rec['status'] != "active":
            print(f"   [FAIL] Expected ExecutionState status to be 'active', got: {rec['status']}")
            engine.close()
            return False
            
    print("   [PASS] Verification completed successfully!")
    
    # 5. Clean up test nodes
    print("\n5. Cleaning up test nodes...")
    with engine.driver.session() as session:
        session.run("MATCH (m:Cybernet) WHERE m.name STARTS WITH $name DETACH DELETE m", {"name": test_name})
    print("   [PASS] Database cleaned.")
    
    print("=" * 60)
    print("All Janic Daemon Summoning tests passed successfully! 🎉")
    engine.close()
    return True

if __name__ == "__main__":
    success = verify_summoning()
    sys.exit(0 if success else 1)
