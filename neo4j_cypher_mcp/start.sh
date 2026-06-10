#!/bin/bash
# Startup script for Neo4j Cypher MCP Server

# Set defaults for Neo4j connection if not already in env
export NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"

# Navigate to the server directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Check for 'dev' argument
if [ "$1" == "dev" ]; then
    echo "Starting Neo4j Cypher MCP Server in DEV mode (mcp dev)..."
    mcp dev server.py
else
    echo "Starting Neo4j Cypher MCP Server..."
    # If mcp CLI is available, use 'mcp run', otherwise fall back to direct python execution
    if command -v mcp &> /dev/null; then
        mcp run server.py
    else
        python3 server.py
    fi
fi
