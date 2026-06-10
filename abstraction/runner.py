#!/usr/bin/env python3
"""
Sh8peshift RPG Terminal Runner
Interactive CLI to manage MetaShifters, equip State Machines, and tick execution/calibration cycles.
"""
import sys
import os
import time
from engine import Sh8peshiftEngine, AgentLLMRunner

def print_banner():
    banner = """
============================================================
   ____  _     ___                  _     _  __ _   
  / ___|| |__ ( _ ) _ __   ___  ___| |__ (_)/ _| |_ 
  \___ \| '_ \/ _ \| '_ \ / _ \/ __| '_ \| | |_| __|
   ___) | | | | (_) | |_) |  __/\__ \ | | | |  _| |_ 
  |____/|_| |_|\___/| .__/ \___||___/_| |_|_|_|  \__|
                    |_|                             
   -- Idol RPG for LLM Surrogates & Agentic Lifecycles --
============================================================
"""
    print(banner)

def print_character_sheet(status: dict):
    print("\n" + "-"*50)
    print(f" METASHIFTER CHARACTER SHEET (IDENTITY): {status['name']}")
    print("-"*50)
    print(f" Prompt / Behavior    : {status['description']}")
    print(f" Equipped StateMachine: {status['equipped_sm_name'] or 'NONE (Unequipped)'} [{status['equipped_sm_id'] or ''}]")
    if status["equipped_sm_id"]:
        print(f" Turn Count / Lifetime: Day {status['turn_number']} / 5")
        print(f" Phase                : {status['phase'].upper()}")
        print(f" Current Step         : [{status['current_step_id']}]")
        print(f" Current Step Prompt  : {status['current_step_text']}")
    print("\n--- Literal AI & Agentic Statistics ---")
    print(f" Model Engine         : {status['model_name']}")
    print(f" Temperature          : {status['temperature']}")
    print(f" Top-P                : {status['top_p']}")
    print(f" Mutation Rate        : {status['mutation_rate']}")
    print(f" Selection Pressure   : {status['selection_pressure']}")
    print(f" Cumulative Token Cost: ${status['accumulated_cost']:.6f}")
    print(f" Total Tokens Consumed: {status['total_tokens']}")
    print(f" Current Fitness Score: {status['fitness_score']:.2f}")
    print("-"*50 + "\n")

def main():
    print_banner()
    
    try:
        engine = Sh8peshiftEngine()
    except Exception as e:
        print(f"Error connecting to Neo4j. Is the server running? Details: {e}")
        sys.exit(1)
        
    active_char = None
    
    while True:
        print("Main Menu:")
        if active_char:
            status = engine.get_character_status(active_char)
            if not status:
                print("Active character was reaped or deleted. Deselecting.")
                active_char = None
                continue
                
            print(f" [*] Selected Identity: {active_char}")
            print(" 1. View Character Sheet")
            if not status["equipped_sm_id"]:
                print(" 2. Equip a State Machine (Loadout)")
            else:
                print(" 2. Change Equipped State Machine")
                print(" 3. Tick Turn Step (Day Phase query -> Night Phase calibration)")
                print(" 4. Fast-Forward Turn Cycle (Full Day + Night cycle)")
                print(" 5. Fast-Forward Lifetime (Run through 5 turns to Evolve / Reap)")
            print(" 6. Deselect Character")
        else:
            print(" 1. Create a new MetaShifter Persona")
            print(" 2. Select an existing MetaShifter Persona")
            
        print(" 9. Exit Game")
        choice = input("\nSelect an option: ").strip()
        
        if choice == "9":
            print("\nExiting Sh8peshift. Stay agentic!")
            engine.close()
            break
            
        if not active_char:
            if choice == "1":
                print("\n--- CREATE METASHIFTER ---")
                name = input("Enter character name (no spaces): ").strip()
                desc = input("Enter behavior/prompt description: ").strip()
                model = input("Enter AI model engine [default: gemini-1.5-pro]: ").strip() or "gemini-1.5-pro"
                try:
                    temp = float(input("Enter model temperature (0.0 to 2.0) [default: 0.7]: ").strip() or "0.7")
                    top_p = float(input("Enter model Top-P (0.0 to 1.0) [default: 0.9]: ").strip() or "0.9")
                    mutation = float(input("Enter model mutation rate (0.0 to 1.0) [default: 0.1]: ").strip() or "0.1")
                except ValueError:
                    print("Invalid numerical input. Reverting to default values.")
                    temp, top_p, mutation = 0.7, 0.9, 0.1
                    
                try:
                    msg = engine.create_metashifter(
                        name=name,
                        description=desc,
                        model_name=model,
                        temperature=temp,
                        top_p=top_p,
                        mutation_rate=mutation
                    )
                    print(f"\n[SUCCESS] {msg}")
                    active_char = name
                    
                    # Proactively equip default State Machine
                    print("\nEquipping default Sh8peshift Lifecycle State Machine...")
                    equip_msg = engine.equip_state_machine(name, "sh8_lifecycle_sm")
                    print(f"[SUCCESS] {equip_msg}")
                except Exception as e:
                    print(f"\n[ERROR] Failed to create MetaShifter: {e}")
                    
            elif choice == "2":
                print("\n--- SELECT METASHIFTER ---")
                with engine.driver.session() as s:
                    res = s.run("MATCH (m:MetaShifter) RETURN m.name as name")
                    names = [r["name"] for r in res]
                if not names:
                    print("No characters found in database. Create one first!")
                    continue
                print("Available characters:")
                for idx, n in enumerate(names):
                    print(f" {idx + 1}. {n}")
                try:
                    select_idx = int(input("\nSelect character index: ").strip()) - 1
                    if 0 <= select_idx < len(names):
                        active_char = names[select_idx]
                        print(f"\nSelected character: {active_char}")
                    else:
                        print("Invalid index selection.")
                except ValueError:
                    print("Please enter a valid enter.")
            else:
                print("Unknown choice. Please try again.")
                
        else: # Active Character Selected
            status = engine.get_character_status(active_char)
            if not status:
                print("Active character was reaped or deleted. Deselecting.")
                active_char = None
                continue
                
            runner = AgentLLMRunner(
                model_name=status["model_name"],
                temperature=status["temperature"],
                top_p=status["top_p"],
                max_tokens=2048
            )
            
            if choice == "1":
                print_character_sheet(status)
                
            elif choice == "2":
                print("\n--- EQUIP STATE MACHINE (EQUIPMENT) ---")
                with engine.driver.session() as s:
                    res = s.run("MATCH (sm:StateMachine) RETURN sm.id as id, sm.name as name")
                    machines = [{"id": r["id"], "name": r["name"]} for r in res]
                if not machines:
                    print("No State Machines bootstrapped. Run MCP server to populate default graphs.")
                    continue
                print("Available State Machine Equipment:")
                for idx, m in enumerate(machines):
                    print(f" {idx + 1}. {m['name']} [{m['id']}]")
                try:
                    select_idx = int(input("\nSelect State Machine index: ").strip()) - 1
                    if 0 <= select_idx < len(machines):
                        sm_id = machines[select_idx]["id"]
                        msg = engine.equip_state_machine(active_char, sm_id)
                        print(f"\n[SUCCESS] {msg}")
                    else:
                        print("Invalid index selection.")
                except ValueError:
                    print("Please enter a valid number.")
                    
            elif choice == "3" and status["equipped_sm_id"]:
                print(f"\nTicking turn cycle step... (Current Turn: Day {status['turn_number']}, Phase: {status['phase'].upper()})")
                try:
                    tick_res = engine.tick_turn(active_char, runner)
                    print(f"\nAction Query : {tick_res['action_taken']}")
                    print(f"Event Details: {tick_res['event_message']}")
                except Exception as e:
                    print(f"Tick turn failed: {e}")
                    
            elif choice == "4" and status["equipped_sm_id"]:
                print(f"\nRunning full Day + Night turn cycle for '{active_char}'...")
                try:
                    # Keep ticking Day Phase actions until Night Phase is triggered
                    ticked_any = False
                    while status["phase"] == "day":
                        print(f"Ticking Day Phase Step: [{status['current_step_id']}]...")
                        tick_res = engine.tick_turn(active_char, runner)
                        print(f" - Day Action: {tick_res['action_taken']}")
                        print(f" - Day Event : {tick_res['event_message']}")
                        status = engine.get_character_status(active_char)
                        ticked_any = True
                        
                    # Tick Night Calibration & Evolution
                    while status["phase"] == "night":
                        print(f"Ticking Night Phase Step: [{status['current_step_id']}]...")
                        tick_res = engine.tick_turn(active_char, runner)
                        print(f" - Night Event: {tick_res['event_message']}")
                        status = engine.get_character_status(active_char)
                        
                    print("\n[SUCCESS] Completed turn cycle.")
                except Exception as e:
                    print(f"Turn fast-forward failed: {e}")
                    
            elif choice == "5" and status["equipped_sm_id"]:
                print(f"\nFast-forwarding remaining lifetime for '{active_char}'...")
                current_day = status["turn_number"]
                days_left = 6 - current_day
                print(f"Simulating {days_left} turn cycles...")
                
                try:
                    for d in range(days_left):
                        print(f"\n--- Turn Cycle {current_day + d} ---")
                        status = engine.get_character_status(active_char)
                        if not status:
                            break
                        runner.temperature = status["temperature"]
                        runner.top_p = status["top_p"]
                        
                        # Loop Day Phase
                        while status["phase"] == "day":
                            tick_res = engine.tick_turn(active_char, runner)
                            print(f" - Day Action: {tick_res['action_taken']}")
                            print(f" - Day Event : {tick_res['event_message']}")
                            status = engine.get_character_status(active_char)
                            if not status:
                                break
                                
                        if not status:
                            break
                            
                        # Loop Night Phase
                        while status["phase"] == "night":
                            tick_res = engine.tick_turn(active_char, runner)
                            print(f" - Night Event: {tick_res['event_message']}")
                            status = engine.get_character_status(active_char)
                            if not status:
                                break
                            
                        time.sleep(0.5)
                        
                    print("\n[SUCCESS] Completed lifetime fast-forward.")
                    
                    final_status = engine.get_character_status(active_char)
                    if not final_status:
                        print(f"\n[EVOLUTION EVENT] Character '{active_char}' was REAPED due to poor selection accuracy.")
                        active_char = None
                    else:
                        print_character_sheet(final_status)
                except Exception as e:
                    print(f"Lifetime fast-forward failed: {e}")
                    
            elif choice == "6":
                print(f"Deselected character: {active_char}")
                active_char = None
            else:
                print("Unknown choice. Please try again.")

if __name__ == "__main__":
    main()
