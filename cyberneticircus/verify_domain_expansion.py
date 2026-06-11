#!/usr/bin/env python3
import sys
import os
import json

# Ensure python can import from the cyberneticircus folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import CybernetiCircusCompiler, AgentLLMRunner

def verify_expansion():
    print("Starting Jani Domain Expansion Verification...")
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
    print("2. Cleaning up any leftover test data...")
    test_name = "test_jani_expansion"
    with engine.driver.session() as session:
        session.run("MATCH (m:Cybernet) WHERE m.name STARTS WITH $name DETACH DELETE m", {"name": test_name})
        session.run("MATCH (s:TraversalState) DETACH DELETE s")
    print("   [PASS] Wiped previous test data.")
    
    # 3. Create Cybernet
    print(f"3. Creating Cybernet '{test_name}'...")
    try:
        msg = engine.create_cybernet(
            name=test_name,
            description="A test Jani daemon to verify Domain Expansion layer progression.",
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
    print("4. Equipping State Machine 'jani_domain_expansion_sm'...")
    try:
        equip_msg = engine.equip_state_machine(test_name, "jani_domain_expansion_sm")
        print(f"   Equip Response: {equip_msg}")
    except Exception as e:
        print(f"4. [FAIL] Equipping state machine failed: {e}")
        engine.close()
        return False
    
    status = engine.get_character_status(test_name)
    if status["equipped_sm_id"] != "jani_domain_expansion_sm":
        print(f"4. [FAIL] Incorrect equipped state machine ID: {status['equipped_sm_id']}")
        engine.close()
        return False
        
    print(f"   Initial current_layer   : {status['current_layer']}")
    print(f"   Initial completed_layers : {status['completed_layers']}")
    if status['current_layer'] != "none" or status['completed_layers'] != []:
        print(f"4. [FAIL] Expected initial layers to be 'none' and [], got: '{status['current_layer']}', {status['completed_layers']}")
        engine.close()
        return False
    print("   [PASS] State machine equipped and initialized successfully.")
    
    # Run the ticks
    runner = AgentLLMRunner(model_name="test-engine-v1", temperature=1.0, top_p=0.95, max_tokens=2048)
    
    # Step 1: layer1_primitive_boot
    print("\n--- Ticking Step 1: layer1_primitive_boot ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    if status['current_step_id'] != "layer1_primitive_boot":
        print(f"   [FAIL] Expected current step to be layer1_primitive_boot, got: {status['current_step_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    status = engine.get_character_status(test_name)
    print(f"   Updated current_layer   : {status['current_layer']}")
    print(f"   Updated completed_layers : {status['completed_layers']}")
    if status['current_layer'] != "Layer 1" or status['completed_layers'] != ["Layer 1"]:
        print(f"   [FAIL] Expected Layer 1 properties update, got: '{status['current_layer']}', {status['completed_layers']}")
        engine.close()
        return False
    print("   [PASS] Layer 1 booted and tracked successfully.")
    
    # Step 2: layer2_meta_compile
    print("\n--- Ticking Step 2: layer2_meta_compile ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    if status['current_step_id'] != "layer2_meta_compile":
        print(f"   [FAIL] Expected current step to be layer2_meta_compile, got: {status['current_step_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    status = engine.get_character_status(test_name)
    print(f"   Updated current_layer   : {status['current_layer']}")
    print(f"   Updated completed_layers : {status['completed_layers']}")
    if status['current_layer'] != "Layer 2" or status['completed_layers'] != ["Layer 1", "Layer 2"]:
        print(f"   [FAIL] Expected Layer 2 properties update, got: '{status['current_layer']}', {status['completed_layers']}")
        engine.close()
        return False
    print("   [PASS] Layer 2 compiled and tracked successfully.")
    
    # Step 3: layer3_sdlc_ignite
    print("\n--- Ticking Step 3: layer3_sdlc_ignite ---")
    status = engine.get_character_status(test_name)
    print(f"   Current Step: {status['current_step_id']}")
    if status['current_step_id'] != "layer3_sdlc_ignite":
        print(f"   [FAIL] Expected current step to be layer3_sdlc_ignite, got: {status['current_step_id']}")
        engine.close()
        return False
        
    tick_res = engine.tick_turn(test_name, runner)
    print(f"   Action Taken : {tick_res['action_taken']}")
    print(f"   Event Message: {tick_res['event_message']}")
    
    status = engine.get_character_status(test_name)
    print(f"   Updated current_layer   : {status['current_layer']}")
    print(f"   Updated completed_layers : {status['completed_layers']}")
    if status['current_layer'] != "Layer 3" or status['completed_layers'] != ["Layer 1", "Layer 2", "Layer 3"]:
        print(f"   [FAIL] Expected Layer 3 properties update, got: '{status['current_layer']}', {status['completed_layers']}")
        engine.close()
        return False
    print("   [PASS] Layer 3 ignited and tracked successfully.")
    
    print("\n--- Verification completed successfully! ---")
    
    # 5. Clean up test nodes
    print("\n5. Cleaning up test nodes...")
    with engine.driver.session() as session:
        session.run("MATCH (m:Cybernet) WHERE m.name STARTS WITH $name DETACH DELETE m", {"name": test_name})
        session.run("MATCH (s:TraversalState) DETACH DELETE s")
    print("   [PASS] Database cleaned.")
    
    print("=" * 60)
    print("All Jani Domain Expansion tests passed successfully! 🎉")
    engine.close()
    return True

if __name__ == "__main__":
    success = verify_expansion()
    sys.exit(0 if success else 1)
