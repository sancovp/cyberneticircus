"""
Schema enforcement for the CybernetiCircus graph — the DB-resident "structural
shapes" tier (per DESIGN §13). These constraints ship WITH the database, so an
exported neo4j-as-JSON base DB (or a SaaS tenant) is self-validating without any
python interpreter travelling alongside it.

TWO TIERS of enforcement (DESIGN §13):
  1. STRUCTURAL SHAPES (this script) — statements about the *state* of the graph
     (uniqueness, existence, type). Native neo4j constraints. DB-resident.
  2. THE TRAVERSAL GATE (the running server) — a write-time policy keyed to the
     writer's current locked step (the required_pattern). NOT a graph shape; it
     lives in the thin server/MCP every tenant runs anyway.

WHAT NATIVE CONSTRAINTS CANNOT DO: relationship CARDINALITY (e.g. "a Cybernet has
at most ONE :HAS_LIFECYCLE -> :ExecutionState"). Neo4j has no native edge-cardinality
constraint. That rule is a SOMA/OWL-cardinality concern (inherited when CCC ports
onto CartON, DESIGN §13/§12.6) or an APOC transaction trigger. Until then this
script REPORTS cardinality violations (the scaffold-to-harness pattern) rather than
silently enforcing them.

Run:  NEO4J_PASSWORD=password python3 cyberneticircus/scripts/setup_constraints.py
Idempotent (every constraint is IF NOT EXISTS).
"""
import os
import sys
import json
import base64
import urllib.request

NEO4J_HTTP = os.getenv("NEO4J_HTTP", "http://localhost:7474/db/neo4j/tx/commit")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def _run_cypher(statement: str, params: dict | None = None) -> dict:
    body = json.dumps({"statements": [{"statement": statement, "parameters": params or {}}]}).encode()
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASSWORD}".encode()).decode()
    req = urllib.request.Request(
        NEO4J_HTTP, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


# --- Tier 1: native uniqueness constraints on the key identifiers ------------
# Only keys verified clean (no existing duplicates) are listed. Cybernet.name is
# deliberately ABSENT: the live graph has duplicate beings (JesterCoreOne x5,
# Child_Daemon_Jester x3) from rites that CREATE instead of MERGE — neo4j rejects
# a uniqueness constraint the data already violates. Dedup first (see report), then
# add: CREATE CONSTRAINT cybernet_name_unique FOR (c:Cybernet) REQUIRE c.name IS UNIQUE
CONSTRAINTS = [
    ("state_machine_id_unique", "FOR (sm:StateMachine) REQUIRE sm.id IS UNIQUE"),
    ("traversal_step_id_unique", "FOR (s:TraversalStep) REQUIRE s.id IS UNIQUE"),
    ("core_id_unique", "FOR (co:Core) REQUIRE co.id IS UNIQUE"),
]

# --- Reports: violations that native constraints can't (yet) enforce ---------
REPORT_DUP_CYBERNET = """
MATCH (c:Cybernet) WITH c.name AS name, count(*) AS n WHERE n > 1
RETURN name, n ORDER BY n DESC
"""

REPORT_MULTI_EXECUTION_STATE = """
MATCH (c:Cybernet)-[:HAS_LIFECYCLE]->(s:ExecutionState)
WITH c.name AS cybernet, count(s) AS n, collect(s.equipped_sm_id) AS equipped
WHERE n > 1 RETURN cybernet, n, equipped ORDER BY n DESC
"""


def _rows(resp: dict) -> list:
    results = resp.get("results", [])
    if not results:
        return []
    return [r["row"] for r in results[0].get("data", [])]


def main() -> int:
    # Tier 1 — create the clean uniqueness constraints (idempotent)
    print("=== Tier 1: native uniqueness constraints ===")
    for name, body in CONSTRAINTS:
        stmt = f"CREATE CONSTRAINT {name} IF NOT EXISTS {body}"
        resp = _run_cypher(stmt)
        errs = resp.get("errors", [])
        if errs:
            print(f"  [FAIL] {name}: {errs}", file=sys.stderr)
        else:
            print(f"  [ok]   {name}")

    # Reports — cardinality / uniqueness violations needing dedup or SOMA/APOC
    violations = 0

    print("\n=== Report: duplicate Cybernet.name (blocks cybernet_name_unique) ===")
    dups = _rows(_run_cypher(REPORT_DUP_CYBERNET))
    if not dups:
        print("  none — safe to add cybernet_name_unique now")
    for name, n in dups:
        violations += 1
        print(f"  [DUP] Cybernet '{name}' x{n}  (rite CREATEs instead of MERGEs)")

    print("\n=== Report: >1 ExecutionState per Cybernet (cardinality; non-native) ===")
    multi = _rows(_run_cypher(REPORT_MULTI_EXECUTION_STATE))
    if not multi:
        print("  none — the one-ExecutionState-per-Cybernet invariant holds")
    for cybernet, n, equipped in multi:
        violations += 1
        print(f"  [CARD] '{cybernet}' has {n} ExecutionStates: {equipped}")

    print(f"\nDone. {len(CONSTRAINTS)} constraints ensured; {violations} violation class(es) reported.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
