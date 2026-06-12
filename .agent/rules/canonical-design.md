# Rule: Single Canonical Design Document

## **Purpose**
Ensures every project maintains a single, clear source of structural truth to prevent context decay across turns.

## **MANDATORY: Design Constraints**
1. **Root Document**: Every project root (e.g. `/scratch/crystal-ball/`) must contain a `DESIGN.md` file.
2. **Comprehensive Spec**: The `DESIGN.md` must accurately reflect the codebase's current reality.
3. **Aspirational Marking**: Any features or structures not yet implemented but planned must be explicitly marked with the prefix `ASPIRATIONAL:`.
4. **Architectural Updates**: Every time you make a design decision or alter the database/component structure, you must update the project's `DESIGN.md` immediately.
5. **Knowledge Graph Reflection**: Record the path of the updated `DESIGN.md` as an observation concept in the Carton knowledge graph using the `observe_from_identity_pov` tool.
