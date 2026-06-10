#!/usr/bin/env python3
"""
Test suite for Cypher safety validation logic.
Verifies namespace safety rules for the :Wiki namespace.
"""
from server import validate_cypher_query

def run_tests():
    # Format: (query, should_pass, description)
    test_cases = [
        # Read operations on :Wiki (Should Pass)
        (
            "MATCH (n:Wiki) RETURN count(n)", 
            True, 
            "Read-only query targeting :Wiki"
        ),
        (
            "MATCH (n:Wiki {name: 'Sanctum'})-[r:RELATES_TO]->(m:Wiki) RETURN n, r, m",
            True,
            "Complex read-only query targeting :Wiki"
        ),
        
        # Write operations on other namespaces (Should Pass)
        (
            "CREATE (t:AgentTask {title: 'Verify Sanctum UI', status: 'completed'})", 
            True, 
            "Write query targeting :AgentTask"
        ),
        (
            "MERGE (c:SessionContext {id: 'session-123'}) ON CREATE SET c.active = true",
            True,
            "Merge query targeting :SessionContext"
        ),
        
        # False positive checks (Should Pass)
        (
            'MATCH (n:Wiki) WHERE n.name = "CREATE" RETURN n',
            True,
            "Query with write keyword inside double-quoted string literal"
        ),
        (
            "MATCH (n:Wiki) WHERE n.name = 'SET' RETURN n",
            True,
            "Query with write keyword inside single-quoted string literal"
        ),
        (
            "MATCH (n:Wiki) // This is a comment containing CREATE keyword\nRETURN n",
            True,
            "Query with write keyword inside inline comment"
        ),
        
        # Write operations on :Wiki (Should Fail)
        (
            'MATCH (n:Wiki {n: "Sanctum"}) SET n.d = "corrupted"',
            False,
            "SET mutation targeting :Wiki"
        ),
        (
            "MATCH (n:wiki) DETACH DELETE n",
            False,
            "DETACH DELETE mutation targeting :wiki (lowercase)"
        ),
        (
            "CREATE (w:Wiki {n: 'NewWiki', d: 'NewDescription'})",
            False,
            "CREATE mutation targeting :Wiki"
        ),
        (
            "MERGE (w:Wiki {n: 'NewWiki'})",
            False,
            "MERGE mutation targeting :Wiki"
        ),
        (
            "MATCH (w:Wiki) REMOVE w.d",
            False,
            "REMOVE mutation targeting :Wiki"
        ),
        (
            "MATCH (w:`Wiki`) SET w.d = 'test'",
            False,
            "SET mutation targeting backtick-quoted `Wiki`"
        )
    ]
    
    passed_count = 0
    failed_count = 0
    
    print("Running Cypher query validation safety tests...")
    print("-" * 60)
    
    for i, (query, should_pass, desc) in enumerate(test_cases, 1):
        try:
            validate_cypher_query(query)
            # If no exception raised, it passed the validation
            if should_pass:
                print(f"Test {i:02d}: [PASS] {desc}")
                passed_count += 1
            else:
                print(f"Test {i:02d}: [FAIL] {desc} (Expected validation to reject, but it allowed the query)")
                print(f"  Query: {query}")
                failed_count += 1
        except PermissionError as e:
            # If PermissionError raised, it was rejected
            if not should_pass:
                print(f"Test {i:02d}: [PASS] {desc} (Successfully blocked with error: {e})")
                passed_count += 1
            else:
                print(f"Test {i:02d}: [FAIL] {desc} (Expected validation to allow, but it blocked the query with error: {e})")
                print(f"  Query: {query}")
                failed_count += 1
        except Exception as e:
            print(f"Test {i:02d}: [ERROR] {desc} (Unexpected exception: {type(e).__name__}: {e})")
            print(f"  Query: {query}")
            failed_count += 1
            
    print("-" * 60)
    print(f"Summary: {passed_count} passed, {failed_count} failed out of {len(test_cases)} tests.")
    
    if failed_count > 0:
        exit(1)
    else:
        print("All safety checks passed successfully! ✅")
        exit(0)

if __name__ == "__main__":
    run_tests()
