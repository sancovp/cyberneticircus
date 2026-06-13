#!/usr/bin/env python3
"""
decompose_cybernets.py — close the aspirational gap: bring the flat :Cybernet nodes
up to the canonical being-composition in DESIGN.md §5 (Cybernet = Identity + Gear,
Identity = Ghost ⊕ Shell).

Today a being is a single flat :Cybernet node (persona on `description`, model-config
as substrate props, Gear hung directly off it via EQUIPS / EQUIPS_SKILL). This
migration ADDITIVELY builds, for every Cybernet:

    (c:Cybernet)-[:HAS_IDENTITY]->(:Identity)
        (:Identity)-[:HAS_GHOST]->(:Ghost {persona: c.description})
        (:Identity)-[:HAS_SHELL]->(:Shell)
            (:Shell)-[:HOLDS]->(each equipped :StateMachine and :Skill)   # the Gear

It does NOT remove the existing flat edges (EQUIPS / EQUIPS_SKILL / description), so
nothing that reads the old shape breaks — the canonical structure now exists alongside
it, ready for the logic to migrate onto. Idempotent (MERGE); safe to re-run.

Admin/setup op — writes directly via neo4j HTTP (not gameplay, not through the gate).

Usage:  python3 cyberneticircus/scripts/decompose_cybernets.py
Env:    NEO4J_HTTP (default http://localhost:7474/db/neo4j/tx/commit)
        NEO4J_USER (default neo4j) / NEO4J_PASSWORD (default password)
"""
from __future__ import annotations
import base64
import json
import os
import sys
import urllib.request

NEO4J_HTTP = os.getenv("NEO4J_HTTP", "http://localhost:7474/db/neo4j/tx/commit")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def run(statement: str) -> dict:
    body = json.dumps({"statements": [{"statement": statement}]}).encode()
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASSWORD}".encode()).decode()
    req = urllib.request.Request(
        NEO4J_HTTP, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read().decode())
    if out.get("errors"):
        raise RuntimeError(out["errors"])
    return out


# 1. Identity → Ghost + Shell, for every Cybernet (persona lifted into the Ghost).
STRUCTURE = """
MATCH (c:Cybernet)
MERGE (c)-[:HAS_IDENTITY]->(i:Identity {name: c.name + '_identity'})
  ON CREATE SET i.domain = 'cyberneticity', i.subdomain = 'identity'
MERGE (i)-[:HAS_GHOST]->(g:Ghost {name: c.name + '_ghost'})
  ON CREATE SET g.domain = 'cyberneticity', g.subdomain = 'ghost'
SET g.persona = c.description
MERGE (i)-[:HAS_SHELL]->(sh:Shell {name: c.name + '_shell'})
  ON CREATE SET sh.domain = 'cyberneticity', sh.subdomain = 'shell'
RETURN count(c) AS cybernets_decomposed
"""

# 2. Re-home equipped State Machines into the Shell as Gear (additive).
GEAR_SM = """
MATCH (c:Cybernet)-[:HAS_IDENTITY]->(:Identity)-[:HAS_SHELL]->(sh:Shell)
MATCH (c)-[:EQUIPS]->(sm:StateMachine)
MERGE (sh)-[:HOLDS]->(sm)
RETURN count(*) AS state_machines_held
"""

# 3. Re-home equipped Skills into the Shell as Gear (additive).
GEAR_SKILL = """
MATCH (c:Cybernet)-[:HAS_IDENTITY]->(:Identity)-[:HAS_SHELL]->(sh:Shell)
MATCH (c)-[:EQUIPS_SKILL]->(sk:Skill)
MERGE (sh)-[:HOLDS]->(sk)
RETURN count(*) AS skills_held
"""


def main() -> int:
    try:
        s = run(STRUCTURE)["results"][0]["data"][0]["row"][0]
        print(f"  decomposed {s} Cybernet(s) -> Identity + Ghost + Shell")
        sm = run(GEAR_SM)["results"][0]["data"][0]["row"][0]
        print(f"  re-homed {sm} StateMachine gear edge(s) into Shells")
        sk = run(GEAR_SKILL)["results"][0]["data"][0]["row"][0]
        print(f"  re-homed {sk} Skill gear edge(s) into Shells")
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("Done. Flat Cybernets now carry the canonical Identity/Ghost/Shell/Gear structure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
