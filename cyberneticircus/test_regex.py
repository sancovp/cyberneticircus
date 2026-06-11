import re

pattern = r"(?i)MATCH\s*\(m:Cybernet\s*[^)]*\)-\[:HAS_LIFECYCLE\]->\(i:Identity\)"
query = "MATCH (m:Cybernet {name: 'OVP_Prime'})-[:HAS_LIFECYCLE]->(i:Identity) RETURN i"

m = re.search(pattern, query)
print("Match object:", m)
