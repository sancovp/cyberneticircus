"""
Cypher helpers for SurrogateModel operations (per-cybernet evolutionary knobs).
SurrogateModels are scoped per-cybernet via (domain, subdomain, owner_cybernet) key.
"""


def upsert_cypher(domain: str, subdomain: str, owner_cybernet: str,
                  mutation_rate: float = 0.1, selection_pressure: float = 1.0,
                  reward_weights: str = '{"accuracy": 1.0}') -> str:
    return f"""MERGE (sm:SurrogateModel {{
  domain: $domain, subdomain: $subdomain, owner_cybernet: $owner_cybernet
}})
SET sm.mutation_rate = $mutation_rate,
    sm.selection_pressure = $selection_pressure,
    sm.reward_weights = $reward_weights"""


def read_cypher(domain: str, subdomain: str, owner_cybernet: str) -> str:
    return f"""MATCH (sm:SurrogateModel {{
  domain: $domain, subdomain: $subdomain, owner_cybernet: $owner_cybernet
}})
RETURN sm.mutation_rate, sm.selection_pressure, sm.reward_weights"""
