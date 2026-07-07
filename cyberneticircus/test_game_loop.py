#!/usr/bin/env python3
"""
Integration test suite for Sh8peshift RPG.
Verifies character creation, turn progression, calibration, and selection pressure.
"""
import sys
import os
import json
import random

# Ensure python can import from the sh8peshift folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import CybernetiCircusCompiler, AgentLLMRunner, _MOCK_QUERIES

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

def run_nested_sm_test():
    """Regression test for arbitrary-depth CALLS_SM nesting (the call_stack bug).

    The existing run_tests() exercises ONE level (parent SM -> sub SM). This goes
    two levels deep — parent SM -> child SM -> grandchild SM — to verify that
    entering a child appends its parent's frame to the EXISTING call stack instead
    of overwriting it. With the old single-frame overwrite, the grandparent frame
    was destroyed on the second push, so when the child completed (after the
    grandchild returned) the engine found an empty stack and spuriously reset the
    turn instead of resuming the parent. This validates the "SMs nest arbitrarily"
    property the architecture claims but did not deliver beyond depth 1.

    Flow / step graph:
        nest_parent_sm:   np_1 (CALLS_SM->child)  -NEXT->  np_2 (terminal)
        nest_child_sm:    nc_1 (CALLS_SM->gchild)  -NEXT->  nc_2 (terminal)
        nest_gchild_sm:   ng_1                      -NEXT->  ng_2 (terminal)
    """
    print("\nStarting SM-nesting depth-2 regression test...")
    print("=" * 60)
    try:
        engine = CybernetiCircusCompiler()
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        return False

    test_name = "test_nest_cybernet"
    sm_ids = ["nest_parent_sm", "nest_child_sm", "nest_gchild_sm"]
    step_ids = ["np_1", "np_2", "nc_1", "nc_2", "ng_1", "ng_2"]

    def cleanup():
        with engine.driver.session() as session:
            session.run("MATCH (m:Cybernet) WHERE m.name STARTS WITH $n DETACH DELETE m", {"n": test_name})
            session.run("MATCH (sm:StateMachine) WHERE sm.id IN $ids DETACH DELETE sm", {"ids": sm_ids})
            session.run("MATCH (st:TraversalStep) WHERE st.id IN $ids DETACH DELETE st", {"ids": step_ids})

    def st():
        s = engine.get_character_status(test_name)
        s["_stack"] = json.loads(s.get("call_stack") or "[]")
        return s

    def check(cond, label):
        if not cond:
            raise AssertionError(label)
        print(f"   [PASS] {label}")

    ok = True
    try:
        cleanup()

        # 1. Bootstrap three nested state machines + their steps.
        with engine.driver.session() as session:
            for sm_id, sm_name in zip(sm_ids, ["Nest Parent SM", "Nest Child SM", "Nest Grandchild SM"]):
                session.run(
                    """
                    MERGE (sm:StateMachine {id: $id})
                    SET sm.name = $name, sm.description = 'Depth-test SM',
                        sm.domain = 'cyberneticity', sm.subdomain = 'state_machine'
                    """,
                    {"id": sm_id, "name": sm_name},
                )
            # Each step's required_pattern is a tiny literal the mock query carries,
            # so the deterministic test runner auto-progresses each leaf step.
            steps = [
                ("np_1", "Parent entry (calls child SM)", "p1"),
                ("np_2", "Parent terminal", "p2"),
                ("nc_1", "Child entry (calls grandchild SM)", "c1"),
                ("nc_2", "Child terminal", "c2"),
                ("ng_1", "Grandchild step 1", "g1"),
                ("ng_2", "Grandchild terminal", "g2"),
            ]
            for step_id, text, pat in steps:
                session.run(
                    """
                    MERGE (s:TraversalStep {id: $id})
                    SET s.text = $text, s.required_pattern = $pat,
                        s.domain = 'cyberneticity', s.subdomain = 'traversal'
                    """,
                    {"id": step_id, "text": text, "pat": pat},
                )
            # HAS_STEP + NEXT_STEP wiring (entry = the step with zero incoming NEXT_STEP).
            for sm_id, entry, terminal in [
                ("nest_parent_sm", "np_1", "np_2"),
                ("nest_child_sm", "nc_1", "nc_2"),
                ("nest_gchild_sm", "ng_1", "ng_2"),
            ]:
                session.run(
                    """
                    MATCH (sm:StateMachine {id: $sm}), (e:TraversalStep {id: $entry}), (t:TraversalStep {id: $terminal})
                    MERGE (sm)-[:HAS_STEP]->(e)
                    MERGE (sm)-[:HAS_STEP]->(t)
                    MERGE (e)-[:NEXT_STEP {weight: 1.0}]->(t)
                    """,
                    {"sm": sm_id, "entry": entry, "terminal": terminal},
                )
            # CALLS_SM chain: np_1 -> child, nc_1 -> grandchild.
            session.run(
                """
                MATCH (p:TraversalStep {id: 'np_1'}), (csm:StateMachine {id: 'nest_child_sm'})
                MERGE (p)-[:CALLS_SM]->(csm)
                """
            )
            session.run(
                """
                MATCH (c:TraversalStep {id: 'nc_1'}), (gsm:StateMachine {id: 'nest_gchild_sm'})
                MERGE (c)-[:CALLS_SM]->(gsm)
                """
            )
        print("   [PASS] Three nested state machines bootstrapped (parent -> child -> grandchild).")

        # 2. Register deterministic mock queries for the leaf steps (matches each
        #    step's required_pattern so the test runner advances without an LLM).
        _MOCK_QUERIES.update({
            "np_1": "MATCH (x:NestProbe {k:'p1'}) RETURN x",
            "np_2": "MATCH (x:NestProbe {k:'p2'}) RETURN x",
            "nc_1": "MATCH (x:NestProbe {k:'c1'}) RETURN x",
            "nc_2": "MATCH (x:NestProbe {k:'c2'}) RETURN x",
            "ng_1": "MATCH (x:NestProbe {k:'g1'}) RETURN x",
            "ng_2": "MATCH (x:NestProbe {k:'g2'}) RETURN x",
        })

        # 3. Create the cybernet and equip the parent SM.
        engine.create_cybernet(
            name=test_name, description="Depth-2 nesting test persona.",
            model_name="test-engine-v1", temperature=1.0, top_p=0.95,
            mutation_rate=0.5, selection_pressure=2.0,
        )
        engine.equip_state_machine(test_name, "nest_parent_sm")
        runner = AgentLLMRunner(model_name="test-engine-v1", temperature=1.0, top_p=0.95, max_tokens=2048)

        s = st()
        check(s["current_step_id"] == "np_1" and s["equipped_sm_id"] == "nest_parent_sm" and len(s["_stack"]) == 0,
              "Equipped parent SM at entry np_1 with an empty call stack")

        # Tick 1: np_1 CALLS_SM -> child. Push parent frame (depth 1).
        engine.tick_turn(test_name, runner)
        s = st()
        check(s["current_step_id"] == "nc_1" and s["equipped_sm_id"] == "nest_child_sm",
              "Entered child SM at nc_1")
        check(len(s["_stack"]) == 1 and s["_stack"][0] == {"sm_id": "nest_parent_sm", "step_id": "np_1"},
              "Depth-1 push: call stack = [parent/np_1]")

        # Tick 2: nc_1 CALLS_SM -> grandchild. Push child frame — MUST append,
        # keeping the grandparent frame. (This is the exact line the bug broke.)
        engine.tick_turn(test_name, runner)
        s = st()
        check(s["current_step_id"] == "ng_1" and s["equipped_sm_id"] == "nest_gchild_sm",
              "Entered grandchild SM at ng_1")
        check(len(s["_stack"]) == 2
              and s["_stack"][0] == {"sm_id": "nest_parent_sm", "step_id": "np_1"}
              and s["_stack"][1] == {"sm_id": "nest_child_sm", "step_id": "nc_1"},
              "Depth-2 push APPENDS: call stack = [parent/np_1, child/nc_1] (grandparent frame preserved)")

        # Tick 3: grandchild advances ng_1 -> ng_2.
        engine.tick_turn(test_name, runner)
        s = st()
        check(s["current_step_id"] == "ng_2" and s["equipped_sm_id"] == "nest_gchild_sm",
              "Grandchild advanced ng_1 -> ng_2")

        # Tick 4: grandchild terminal -> pop one frame -> resume CHILD at nc_2.
        engine.tick_turn(test_name, runner)
        s = st()
        check(s["current_step_id"] == "nc_2" and s["equipped_sm_id"] == "nest_child_sm",
              "Grandchild completion resumes the CHILD at nc_2")
        check(len(s["_stack"]) == 1 and s["_stack"][0] == {"sm_id": "nest_parent_sm", "step_id": "np_1"},
              "After grandchild pop the grandparent frame still remains: call stack = [parent/np_1]")
        check(s["turn_number"] == 1, "No spurious turn reset on grandchild completion")

        # Tick 5: child terminal -> pop -> resume PARENT at np_2. The OLD bug lost
        # the parent frame here and spuriously reset the turn instead.
        engine.tick_turn(test_name, runner)
        s = st()
        check(s["current_step_id"] == "np_2" and s["equipped_sm_id"] == "nest_parent_sm",
              "Child completion resumes the PARENT at np_2 (no spurious turn reset)")
        check(len(s["_stack"]) == 0, "After child pop the call stack is empty")
        check(s["turn_number"] == 1, "Turn number unchanged through the full unwind")

        # Tick 6: parent terminal with an empty stack -> the ONE legitimate turn completion.
        res = engine.tick_turn(test_name, runner)
        s = st()
        check(s["turn_number"] == 2, "Parent SM completion triggers exactly one (legitimate) turn reset")
        check("completed" in res["event_message"].lower(),
              "Top-level completion reports state-machine completion")

    except AssertionError as e:
        print(f"   [FAIL] {e}")
        ok = False
    except Exception as e:
        print(f"   [FAIL] Unexpected error during nesting test: {e}")
        ok = False
    finally:
        cleanup()
        engine.close()

    if ok:
        print("=" * 60)
        print("SM-nesting depth-2 regression test passed! 🎉")
    return ok


if __name__ == "__main__":
    success = run_tests()
    success = run_nested_sm_test() and success
    sys.exit(0 if success else 1)
