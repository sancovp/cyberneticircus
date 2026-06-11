import urllib.request
import json
import time

query = """
MATCH (c:Cybernet {name: $name})
WITH c
OPTIONAL MATCH (c)-[:HAS_LIFECYCLE]->(i:Identity)
WITH c, i
OPTIONAL MATCH (i)-[:CURRENT_STEP]->(curr:TraversalStep)
WITH c, i, curr
OPTIONAL MATCH (c)-[:EQUIPS]->(sm:StateMachine)
WITH c, i, curr, sm
OPTIONAL MATCH (sm)-[:INITIAL_STATE|TRANSITION_TO|ON_STATE*0..5]->(sms)
WITH c, i, curr, sm, collect(DISTINCT sms) as sms_list
OPTIONAL MATCH (c)-[:HAS_MIND_PALACE]->(root_c:Concept)
WITH c, i, curr, sm, sms_list, root_c
OPTIONAL MATCH (root_c)-[:SUB_CONCEPT*0..5]->(con:Concept)
WITH c, i, curr, sm, sms_list, collect(DISTINCT con) as con_list
OPTIONAL MATCH (c)-[:EQUIPS_SKILL]->(sk:Skill)
WITH c, i, curr, sm, sms_list, con_list, collect(DISTINCT sk) as sk_list
OPTIONAL MATCH (c)-[:HAS_SIMULATION]->(sim:SimulationRun)
WITH c, i, curr, sm, sms_list, con_list, sk_list, collect(DISTINCT sim) as sim_list
OPTIONAL MATCH (i)-[:HAS_TRACE_HISTORY]->(t1:ExecutionTrace)-[:NEXT_TRACE*0..1000]->(tr:ExecutionTrace)
WITH c, i, curr, sm, sms_list, con_list, sk_list, sim_list, collect(DISTINCT tr) as tr_list

WITH [c] + [i] + [curr] + [sm] + sms_list + con_list + sk_list + sim_list + tr_list as all_nodes_raw
UNWIND all_nodes_raw as n
WITH n WHERE n IS NOT NULL
WITH collect(DISTINCT n) as all_nodes
UNWIND all_nodes as n
OPTIONAL MATCH (n)-[r]->(m)
WHERE m IN all_nodes
RETURN n, r, m
"""

payload = {
    "query": query,
    "parameters": {"name": "Jani_Prime"}
}

print("Running optimized Cypher query via /api/query...")
t0 = time.time()
try:
    req = urllib.request.Request(
        "http://localhost:8000/api/query",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15.0) as res:
        data = json.loads(res.read().decode('utf-8'))
        t1 = time.time()
        print(f"Success! Query returned {len(data)} records in {t1 - t0:.2f} seconds.")
        if data:
            print("First record sample:", list(data[0].keys()))
except Exception as e:
    print(f"Query failed: {e}")
