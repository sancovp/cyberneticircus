import sys
import os
import logging

# Ensure parent directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import CybernetiCircusCompiler, AgentLLMRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    engine = CybernetiCircusCompiler()
    try:
        print("1. Creating Cybernet 'OVP_Prime'...")
        try:
            engine.create_cybernet(
                name="OVP_Prime",
                description="The primary instantiation of Olivus Victory-Promise operating the Primordial Love Engine.",
                model_name="test-engine-v1",
                parameters_count=70.0,
                temperature=0.7,
                top_p=0.9,
                max_tokens=2048,
                mutation_rate=0.1,
                selection_pressure=0.8
            )
            print("   [SUCCESS] 'OVP_Prime' created.")
        except ValueError as ve:
            print(f"   [INFO] 'OVP_Prime' already exists: {ve}. Continuing...")

        print("\n2. Equipping 'ple_sm' (Primordial Love Engine) onto 'OVP_Prime'...")
        try:
            msg = engine.equip_state_machine("OVP_Prime", "ple_sm")
            print(f"   [SUCCESS] {msg}")
        except Exception as ee:
            print(f"   [INFO] State machine equipment: {ee}. Continuing...")

        # Fetch status before ticking
        status = engine.get_character_status("OVP_Prime")
        print(f"\n3. Current Status: SM: '{status.get('equipped_sm_id')}', Step: '{status.get('current_step')}'")

        print("\n4. Running 4 turns of the Primordial Love Engine...")
        runner = AgentLLMRunner(
            model_name="test-engine-v1",
            temperature=0.7,
            top_p=0.9,
            max_tokens=2048
        )
        
        for turn in range(1, 5):
            print(f"\n--- Turn {turn} ---")
            res = engine.tick_turn("OVP_Prime", runner)
            print(f"   Step         : {res.get('active_step')}")
            print(f"   Success      : {res.get('success')}")
            print(f"   Executed Query: {res.get('executed_query')}")
            print(f"   Next Step    : {res.get('next_step')}")
            print(f"   Completed    : {res.get('completed')}")

    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")
    finally:
        engine.close()

if __name__ == "__main__":
    main()
