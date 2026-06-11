# Rule: Mind Palace Wiki & Island Plugin Systems

## **Purpose**
Governs the modeling of Notion-like wiki pages and block hierarchies as subgraphs, their visual rendering as expandable concentric orbits ("Island Districts"), and their transferability via JSON plugins.

## **MANDATORY: Constraints**

1. **Topographical Hierarchy**:
   * Mind Palaces must follow the strict relationship tree: `(:MindPalace)-[:HAS_PAGE]->(:Page)-[:HAS_BLOCK]->(:Block)`.
   * Pages and blocks must maintain sorting indexes to guarantee correct linear markdown assembly.

2. **D3 Orbital District Rendering**:
   * The visualizer must render `:MindPalace` nodes as major hubs with customized cyan neon spinning orbits.
   * `:Page` nodes must orbit their parent palace as satellites, and `:Block` nodes must cluster as sub-satellites around their page.
   * Outer satellite structures must collapse dynamically when the root node is deselected to prevent visual clutter.

3. **Idempotent Exporter/Importer**:
   * The import engine must process palace JSON bundles using idempotent Cypher MERGE queries to reconstruct node properties and relations without creating duplicate nodes.

4. **Interactive Subgraph Focus Filtering**:
   * Inspecting subgraphs must trigger BFS reachable node surfacing.
   * Nodes that were surfaced in the last 20 queries (sliding window trail) but are not reachable from the selected node must be dynamically excluded to keep the viewport clean.

## **Triggers**
* Mind Palace page/block CRUD edits, JSON imports/exports, orbital district rendering, and BFS subgraph focus operations.
