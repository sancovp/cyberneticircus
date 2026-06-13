#!/usr/bin/env python3
"""
Integration test suite for Sh8peshift RPG.
Verifies character creation, turn progression, calibration, and selection pressure.
"""
import sys
import os
import random

# Ensure python can import from the sh8peshift folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import CybernetiCircusCompiler, AgentLLMRunner

def run_tests():
    print("Starting CybernetiCircus integration tests...")
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
    test_name = "test_cybernet"
    with engine.driver.session() as session:
        session.run("MATCH (m:Cybernet) WHERE m.name STARTS WITH $name DETACH DELETE m", {"name": test_name})
        session.run("MATCH (s:Identity) DETACH DELETE s")
        session.run("MATCH (s:ExecutionState) DETACH DELETE s")
        session.run("MATCH (sm:StateMachine {id: 'sub_lifecycle_sm'})-[r:HAS_STEP]->(step) DETACH DELETE sm, step")
        session.run("MATCH (sm:StateMachine {id: 'sub_lifecycle_sm'}) DETACH DELETE sm")
        session.run("MATCH (step:TraversalStep {id: 'sh8_day_start'})-[r:CALLS_SM]->() DELETE r")
    print("   [PASS] Wiped previous test data.")
    
    # 3. Create Cybernet
    print("3. Creating Cybernet 'test_cybernet'...")
    try:
        msg = engine.create_cybernet(
            name=test_name,
            description="A test persona designed for validation checks.",
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
        
    # Verify in DB
    status = engine.get_character_status(test_name)
    if not status or status["name"] != test_name:
        print(f"3. [FAIL] Character not found in DB status lookup: {status}")
        engine.close()
        return False
    if status["temperature"] != 1.0 or status["top_p"] != 0.95:
        print(f"3. [FAIL] Character base stats mismatched: {status}")
        engine.close()
        return False
    print("   [PASS] Cybernet created and verified in database.")
    
    # 3.5 Bootstrap sub-state machine
    print("3.5 Bootstrapping test sub-state machine 'sub_lifecycle_sm'...")
    with engine.driver.session() as session:
        session.run(
            """
            MERGE (sm:StateMachine {id: 'sub_lifecycle_sm'})
            SET sm.name = 'Sub Lifecycle SM', sm.description = 'Test sub-state machine',
                sm.domain = 'cyberneticity', sm.subdomain = 'state_machine'
            """
        )
        session.run(
            """
            MERGE (s1:TraversalStep {id: 'sub_step_1'})
            SET s1.text = 'Sub-step 1: Match subnode',
                s1.required_pattern = '(?i)MATCH\\\\s*\\\\(s:SubNode\\\\s*.*\\\\)',
                s1.domain = 'cyberneticity', s1.subdomain = 'traversal'
            """
        )
        session.run(
            """
            MERGE (s2:TraversalStep {id: 'sub_step_2'})
            SET s2.text = 'Sub-step 2: Match subnode done',
                s2.required_pattern = '(?i)MATCH\\\\s*\\\\(s:SubNode\\\\s*\\\\{.*done:\\\\s*true.*\\\\}\\\\)',
                s2.domain = 'cyberneticity', s2.subdomain = 'traversal'
            """
        )
        session.run(
            """
            MATCH (sm:StateMachine {id: 'sub_lifecycle_sm'})
            MATCH (s1:TraversalStep {id: 'sub_step_1'})
            MATCH (s2:TraversalStep {id: 'sub_step_2'})
            MERGE (sm)-[:HAS_STEP]->(s1)
            MERGE (sm)-[:HAS_STEP]->(s2)
            MERGE (s1)-[:NEXT_STEP {weight: 1.0}]->(s2)
            """
        )
        session.run(
            """
            MATCH (parent:TraversalStep {id: 'sh8_day_start'})
            MATCH (child:StateMachine {id: 'sub_lifecycle_sm'})
            MERGE (parent)-[:CALLS_SM]->(child)
            """
        )
    print("   [PASS] Sub-state machine bootstrapped and nested.")
    
    # 4. Equip State Machine and Tick Turn (Day Phase)
    print("4. Equipping State Machine and Ticking Day Phase turn...")
    try:
        equip_msg = engine.equip_state_machine(test_name, "sh8_lifecycle_sm")
        print(f"   Equip Response: {equip_msg}")
    except Exception as e:
        print(f"4. [FAIL] Equipping state machine failed: {e}")
        engine.close()
        return False

    runner = AgentLLMRunner(model_name="test-engine-v1", temperature=1.0, top_p=0.95, max_tokens=2048)
    try:
        # Loop Day Phase until phase becomes 'night'
        status = engine.get_character_status(test_name)
        while status["phase"] == "day":
            print(f"   Ticking day step: {status['current_step_id']}")
            tick_res = engine.tick_turn(test_name, runner)
            print(f"     Action: {tick_res['action_taken']}")
            print(f"     Event : {tick_res['event_message']}")
            status = engine.get_character_status(test_name)
    except Exception as e:
        print(f"4. [FAIL] Day tick turn loop raised error: {e}")
        engine.close()
        return False
        
    if status["total_tokens"] <= 0:
        print(f"4. [FAIL] Token accumulation failed: {status['total_tokens']}")
        engine.close()
        return False
    print("   [PASS] Day turn loop executed, and tokens recorded.")
    
    # 5. Verify transition to Night Phase
    print("5. Verifying Transition to Night Phase...")
    if status["phase"] != "night":
        print(f"5. [FAIL] Phase auto-transition to night failed: {status}")
        engine.close()
        return False
    print("   [PASS] Auto-entered Night Phase.")
    
    # 6. Tick Turn (Night Phase - Calibration & Evolve Step)
    print("6. Ticking Night Phase turn (Calibration & Evolve)...")
    try:
        # Loop Night Phase until phase becomes 'day'
        while status["phase"] == "night":
            print(f"   Ticking night step: {status['current_step_id']}")
            tick_res = engine.tick_turn(test_name, runner)
            print(f"     Action: {tick_res['action_taken']}")
            print(f"     Event : {tick_res['event_message']}")
            status = engine.get_character_status(test_name)
    except Exception as e:
        print(f"6. [FAIL] Night tick turn loop raised error: {e}")
        engine.close()
        return False
        
    if status["phase"] != "day": # Night cycle toggles segment back to day
        print(f"6. [FAIL] Phase did not toggle back to day: {status}")
        engine.close()
        return False
    if status["turn_number"] != 2: # Day increments
        print(f"6. [FAIL] Day index did not increment: {status}")
        engine.close()
        return False
    print("   [PASS] Night calibration turn loop completed, turn incremented.")
    
    # 7. Test Lifetime Selection and Evolution (Reaping)
    print("7. Fast-forwarding to Day 5 Night cycle to test Evolution (Reaping)...")
    with engine.driver.session() as session:
        session.run(
            """
            MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState)
            MATCH (step:TraversalStep {id: 'sh8_night_evolve'})
            MATCH (s)-[r:CURRENT_STEP]->()
            DELETE r
            CREATE (s)-[:CURRENT_STEP]->(step)
            SET s.turn_number = 5, s.phase = 'night'
            """,
            {"name": test_name}
        )
        # Wipe past simulations and create 10 poor accuracy runs to force average fitness below 0.4
        session.run("MATCH (m:Cybernet {name: $name})-[r:HAS_SIMULATION]->(sim) DETACH DELETE sim", {"name": test_name})
        for i in range(10):
            session.run(
                """
                MATCH (m:Cybernet {name: $name})
                CREATE (sim:SimulationRun {
                    run_id: $run_id,
                    created_at: timestamp(),
                    accuracy: 0.1,
                    fitness_score: 0.1,
                    calibrated: true,
                    domain: 'cyberneticity',
                    subdomain: 'simulation'
                })
                CREATE (m)-[:HAS_SIMULATION]->(sim)
                """,
                {"name": test_name, "run_id": f"bad_run_{i}"}
            )
        
    try:
        tick_res = engine.tick_turn(test_name, runner)
        print(f"   Evolution Event: {tick_res['event_message']}")
    except Exception as e:
        print(f"7. [FAIL] Evolution tick raised error: {e}")
        engine.close()
        return False
        
    # Verify Cybernet is reaped (deleted)
    status = engine.get_character_status(test_name)
    if status is not None:
        print("7. [FAIL] Low fitness character was not reaped from database.")
        engine.close()
        return False
    print("   [PASS] Reaping selection pressure validated (deleted poor fitness cybernet).")
    
    # 8. Test Lifetime Selection and Evolution (Reproduction / Cloning)
    print("8. Re-creating cybernet to test Reproduction...")
    engine.create_cybernet(
        name=test_name,
        description="Reproduction test model.",
        model_name="test-engine-v1",
        temperature=1.0,
        top_p=0.95,
        mutation_rate=0.5,
        selection_pressure=2.0
    )
    engine.equip_state_machine(test_name, "sh8_lifecycle_sm")
    
    with engine.driver.session() as session:
        session.run(
            """
            MATCH (m:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(s:ExecutionState)
            MATCH (step:TraversalStep {id: 'sh8_night_evolve'})
            MATCH (s)-[r:CURRENT_STEP]->()
            DELETE r
            CREATE (s)-[:CURRENT_STEP]->(step)
            SET s.turn_number = 5, s.phase = 'night'
            """,
            {"name": test_name}
        )
        # Create 10 high accuracy runs to force average fitness above 0.8
        for i in range(10):
            session.run(
                """
                MATCH (m:Cybernet {name: $name})
                CREATE (sim:SimulationRun {
                    run_id: $run_id,
                    created_at: timestamp(),
                    accuracy: 1.0,
                    fitness_score: 1.0,
                    calibrated: true,
                    domain: 'cyberneticity',
                    subdomain: 'simulation'
                })
                CREATE (m)-[:HAS_SIMULATION]->(sim)
                """,
                {"name": test_name, "run_id": f"good_run_{i}"}
            )
        
    try:
        tick_res = engine.tick_turn(test_name, runner)
        print(f"   Evolution Event: {tick_res['event_message']}")
    except Exception as e:
        print(f"8. [FAIL] Reproduction tick raised error: {e}")
        engine.close()
        return False
        
    # Check if a clone was created
    with engine.driver.session() as session:
        res = session.run("MATCH (m:Cybernet) WHERE m.name STARTS WITH 'test_cybernet_V' RETURN m.name as name, m.temperature as temp")
        clones = [{"name": r["name"], "temp": r["temp"]} for r in res]
        
    if not clones:
        print("8. [FAIL] High fitness character did not reproduce / clone.")
        engine.close()
        return False
    print(f"   Found clone: {clones[0]['name']} (Mutated Temperature: {clones[0]['temp']:.2f})")
    print("   [PASS] Reproduction selection pressure validated (created mutated clone).")
    
    # 9. Clean up test nodes
    print("9. Cleaning up test nodes...")
    with engine.driver.session() as session:
        session.run("MATCH (m:Cybernet) WHERE m.name STARTS WITH $name DETACH DELETE m", {"name": test_name})
        session.run("MATCH (s:Identity) DETACH DELETE s")
        session.run("MATCH (s:ExecutionState) DETACH DELETE s")
        session.run("MATCH (sm:StateMachine {id: 'sub_lifecycle_sm'})-[r:HAS_STEP]->(step) DETACH DELETE sm, step")
        session.run("MATCH (sm:StateMachine {id: 'sub_lifecycle_sm'}) DETACH DELETE sm")
        session.run("MATCH (step:TraversalStep {id: 'sh8_day_start'})-[r:CALLS_SM]->() DELETE r")
    print("   [PASS] Database cleaned.")
    
    print("=" * 60)
    print("All CybernetiCircus RPG integration tests passed successfully! 🎉")
    engine.close()
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
