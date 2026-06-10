#!/usr/bin/env python3
"""
Integration test suite for Neo4j Cypher MCP Server.
Verifies live connectivity, schema reading, safe writes, and validation blocking.
"""
import os
import sys

# Ensure server module is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import query_database, get_schema

def test_integration():
    print("Running integration tests against Neo4j...")
    print("-" * 60)
    
    # 1. Test get_schema
    try:
        schema = get_schema()
        print("1. [PASS] Schema fetched successfully:")
        print(f"   Labels: {schema.get('labels', [])}")
        print(f"   Relationship Types: {schema.get('relationship_types', [])}")
        print(f"   Property Keys: {schema.get('property_keys', [])}")
    except Exception as e:
        print(f"1. [FAIL] Failed to fetch schema: {e}")
        return
        
    # 2. Test read-only query on Wiki namespace
    try:
        res = query_database("MATCH (n:Wiki) RETURN count(n) as count")
        print(f"2. [PASS] Read-only query count(n:Wiki) succeeded: {res}")
    except Exception as e:
        print(f"2. [FAIL] Read-only query on Wiki failed: {e}")
        
    # 3. Test non-Wiki write query
    try:
        # Create a test node
        res = query_database(
            "CREATE (t:AgentTask {title: $title, status: $status}) RETURN t",
            {"title": "Verify Cypher MCP Integration", "status": "in-progress"}
        )
        print(f"3. [PASS] Write query to AgentTask succeeded: {res}")
        
        # Extract node standard ID
        node = res[0]['t']
        node_id = node['id']
        print(f"   Created node ID: {node_id}")
        
        # Clean up the test node (using elementId matching which is 5.x standard)
        cleanup_query = "MATCH (t:AgentTask) WHERE elementId(t) = $id DETACH DELETE t"
        cleanup_res = query_database(cleanup_query, {"id": node_id})
        print(f"4. [PASS] Cleanup query (DELETE) succeeded: {cleanup_res}")
    except Exception as e:
        print(f"3/4. [FAIL] Write/cleanup operations failed: {e}")
        import traceback
        traceback.print_exc()
        
    # 5. Test blocked Wiki write query
    try:
        query_database("MATCH (n:Wiki {n: 'Sanctum'}) SET n.d = 'corrupted'")
        print("5. [FAIL] Mutation query targeting :Wiki was NOT blocked!")
    except PermissionError as e:
        print(f"5. [PASS] Mutation query targeting :Wiki was correctly blocked: {e}")
    except Exception as e:
        print(f"5. [FAIL] Unexpected error when testing blocked query: {e}")

    print("-" * 60)
    print("Integration tests completed.")

if __name__ == "__main__":
    test_integration()
