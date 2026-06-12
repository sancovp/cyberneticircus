# Rule: Homebrew Python Environment Path

## **Purpose**
Ensures the coding agent never loses track of the correct host-side python executable where FastMCP and local libraries are installed.

## **MANDATORY: Constraints**
1. **Homebrew Python Executable**: The active global python interpreter containing the host-side `mcp`, `neo4j`, and development libraries is located at:
   `/opt/homebrew/bin/python3.11`
2. **Usage**: Whenever running python scripts, starting local development servers, or executing pip commands on the host outside the local virtual environment, the compiler must use this exact path to ensure correct dependency resolution.

## **Triggers**
* Running python commands on the host.
* Troubleshooting MCP server startup issues.
