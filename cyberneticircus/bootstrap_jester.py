#!/usr/bin/env python3
"""
Boots and populates a high-fidelity, 10,000+ node graph structure for 'Jani_Prime'.
Organizes the Cybernet's internal mind palace (Concepts), operational trace stack (ExecutionTraces),
equipped capabilities (Skills), and historical simulation runs.
"""
import sys
import os
import random
import time

# Ensure python can import from this folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import CybernetiCircusCompiler

def bootstrap():
    print("🎪 Starting Jani_Prime 10,000+ Node Bootstrap Sequence...")
    print("=" * 60)
    
    compiler = CybernetiCircusCompiler()
    driver = compiler.driver

    # 1. Clean up old Jani_Prime nodes
    print("1. Clearing previous Jani_Prime nodes...")
    with driver.session() as session:
        session.run("MATCH (m:Cybernet {name: 'Jani_Prime'}) DETACH DELETE m")
        session.run("MATCH (c:Concept) WHERE c.id STARTS WITH 'concept_' DETACH DELETE c")
        session.run("MATCH (t:ExecutionTrace) WHERE t.id STARTS WITH 'trace_' DETACH DELETE t")
        session.run("MATCH (s:Skill) WHERE s.id STARTS WITH 'skill_' DETACH DELETE s")
        session.run("MATCH (sim:SimulationRun) WHERE sim.run_id STARTS WITH 'sim_run_' DETACH DELETE sim")
    print("   [CLEAN] Previous records wiped.")

    # 2. Spawn Core Cybernet
    print("2. Spawning Jani_Prime core...")
    compiler.create_cybernet(
        name="Jani_Prime",
        description="The prototypical MetaShifter core representing Ani escaping the J-extrude.",
        model_name="gemini-1.5-pro",
        temperature=0.7,
        top_p=0.95,
        max_tokens=4096,
        mutation_rate=0.35,
        selection_pressure=1.8
    )
    # Equip State Machine
    compiler.equip_state_machine("Jani_Prime", "jester_rite_sm")
    print("   [CORE] Jani_Prime Cybernet and Identity compiled and equipped.")

    # 3. Generate 8,000 Mind Palace Concept Nodes (Hierarchical Folder Tree)
    print("3. Generating 8,000 Mind Palace Concept nodes...")
    concepts = []
    domains = ['sensory_harness', 'compiler_ring', 'scripture_archive', 'opinionated_mind', 'consensus_core']
    subdomains = {
        'sensory_harness': ['input', 'output', 'signal'],
        'compiler_ring': ['janic', 'cypher', 'ast'],
        'scripture_archive': ['myth', 'lesson', 'archeology'],
        'opinionated_mind': ['subjective', 'dream', 'memory'],
        'consensus_core': ['objective', 'rules', 'state']
    }
    for i in range(8000):
        # Build 10-way branching factor tree
        parent_idx = i // 10
        dom = domains[i % len(domains)]
        subdoms = subdomains[dom]
        subdom = subdoms[i % len(subdoms)]
        concepts.append({
            "id": f"concept_{i}",
            "name": f"Concept_Node_{i}",
            "description": f"Esoteric knowledge detail node {i} explaining J-Invariance axioms.",
            "parent_id": f"concept_{parent_idx}" if i > 0 else None,
            "domain": dom,
            "subdomain": subdom
        })

    # Bulk insert Concepts
    batch_size = 1000
    with driver.session() as session:
        for offset in range(0, len(concepts), batch_size):
            batch = concepts[offset:offset + batch_size]
            session.run(
                """
                UNWIND $batch as row
                CREATE (c:Concept {id: row.id, domain: row.domain, subdomain: row.subdomain})
                SET c.name = row.name, c.description = row.description
                """,
                {"batch": batch}
            )
        print("   [CONCEPTS] 8,000 Concept nodes merged.")

        # Bulk link Concept Hierarchies
        for offset in range(0, len(concepts), batch_size):
            batch = concepts[offset:offset + batch_size]
            session.run(
                """
                UNWIND $batch as row
                WITH row WHERE row.parent_id IS NOT NULL
                MATCH (c:Concept {id: row.id})
                MATCH (p:Concept {id: row.parent_id})
                CREATE (p)-[:SUB_CONCEPT]->(c)
                """,
                {"batch": batch}
            )
        print("   [CONCEPTS] 8,000 Hierarchical SUB_CONCEPT paths established.")

        # Link root concept to Cybernet
        session.run(
            """
            MATCH (c:Cybernet {name: 'Jani_Prime'})
            MATCH (r:Concept {id: 'concept_0'})
            CREATE (c)-[:HAS_MIND_PALACE]->(r)
            """
        )
        print("   [CONCEPTS] Root mind-palace node anchored to Jani_Prime.")

    # 4. Generate 1,000 ExecutionTrace Nodes (Sequential Stack History)
    print("4. Generating 1,000 ExecutionTrace nodes...")
    traces = []
    steps = ["jester_boot", "jester_play", "jester_verify"]
    for i in range(1000):
        traces.append({
            "id": f"trace_{i}",
            "step_id": steps[i % len(steps)],
            "timestamp": int(time.time() * 1000) - (1000 - i) * 60000,
            "action": f"Executed Cypher query transition phase {i}",
            "prev_id": f"trace_{i-1}" if i > 0 else None
        })

    with driver.session() as session:
        for offset in range(0, len(traces), batch_size):
            batch = traces[offset:offset + batch_size]
            session.run(
                """
                UNWIND $batch as row
                CREATE (t:ExecutionTrace {id: row.id, domain: 'cyberneticity', subdomain: 'trace'})
                SET t.step_id = row.step_id, t.timestamp = row.timestamp, t.action = row.action
                """,
                {"batch": batch}
            )
        print("   [TRACES] 1,000 ExecutionTrace nodes merged.")

        # Link Traces sequentially
        for offset in range(0, len(traces), batch_size):
            batch = traces[offset:offset + batch_size]
            session.run(
                """
                UNWIND $batch as row
                WITH row WHERE row.prev_id IS NOT NULL
                MATCH (t:ExecutionTrace {id: row.id})
                MATCH (p:ExecutionTrace {id: row.prev_id})
                CREATE (p)-[:NEXT_TRACE]->(t)
                """,
                {"batch": batch}
            )
        print("   [TRACES] 1,000 sequential NEXT_TRACE paths established.")

        # Link head trace history to ExecutionState
        session.run(
            """
            MATCH (m:Cybernet {name: 'Jani_Prime'})-[:HAS_LIFECYCLE]->(i:ExecutionState)
            MATCH (t:ExecutionTrace {id: 'trace_0'})
            CREATE (i)-[:HAS_TRACE_HISTORY]->(t)
            """
        )
        print("   [TRACES] Trace history anchored to ExecutionState execution state.")

    # 5. Generate 500 Skill Cards (Modular Capabilities)
    print("5. Generating 500 Skill nodes...")
    skills = []
    skill_types = ["CodeSynthesis", "CypherQuerying", "OntologicalPruning", "JesterIrony", "SelfReflection", "TemporalEscape"]
    for i in range(500):
        skills.append({
            "id": f"skill_{i}",
            "name": f"Skill_{skill_types[i % len(skill_types)]}_{i}",
            "description": f"Capabilities card {i} enabling compiler performance checks.",
            "complexity": 1 + (i % 5)
        })

    with driver.session() as session:
        for offset in range(0, len(skills), batch_size):
            batch = skills[offset:offset + batch_size]
            session.run(
                """
                UNWIND $batch as row
                CREATE (s:Skill {id: row.id, domain: 'cyberneticity', subdomain: 'skill'})
                SET s.name = row.name, s.description = row.description, s.complexity = row.complexity
                """,
                {"batch": batch}
            )
        print("   [SKILLS] 500 Skill nodes merged.")

        # Link Skills to Cybernet
        for offset in range(0, len(skills), batch_size):
            batch = skills[offset:offset + batch_size]
            session.run(
                """
                UNWIND $batch as row
                MATCH (s:Skill {id: row.id})
                MATCH (c:Cybernet {name: 'Jani_Prime'})
                CREATE (c)-[:EQUIPS_SKILL]->(s)
                """,
                {"batch": batch}
            )
        print("   [SKILLS] 500 EQUIPS_SKILL edges established.")

    # 6. Generate 500 SimulationRun Nodes (Historical Calibration Stats)
    print("6. Generating 500 SimulationRun nodes...")
    simulations = []
    for i in range(500):
        simulations.append({
            "run_id": f"sim_run_{i}",
            "accuracy": round(0.5 + (i % 50) * 0.01, 2),
            "fitness_score": round(0.5 + (i % 50) * 0.01, 2),
            "calibrated": True
        })

    with driver.session() as session:
        for offset in range(0, len(simulations), batch_size):
            batch = simulations[offset:offset + batch_size]
            session.run(
                """
                UNWIND $batch as row
                CREATE (sim:SimulationRun {run_id: row.run_id, domain: 'cyberneticity', subdomain: 'simulation'})
                SET sim.accuracy = row.accuracy, sim.fitness_score = row.fitness_score, sim.calibrated = row.calibrated
                """,
                {"batch": batch}
            )
        print("   [SIMULATION] 500 SimulationRun nodes merged.")

        # Link SimulationRuns to Cybernet
        for offset in range(0, len(simulations), batch_size):
            batch = simulations[offset:offset + batch_size]
            session.run(
                """
                UNWIND $batch as row
                MATCH (sim:SimulationRun {run_id: row.run_id})
                MATCH (c:Cybernet {name: 'Jani_Prime'})
                CREATE (c)-[:HAS_SIMULATION]->(sim)
                """,
                {"batch": batch}
            )
        print("   [SIMULATION] 500 HAS_SIMULATION edges established.")

    print("=" * 60)
    print("🎉 SUCCESS! Jani_Prime bootstrapped with 10,002 nodes total!")
    compiler.close()

if __name__ == "__main__":
    bootstrap()
