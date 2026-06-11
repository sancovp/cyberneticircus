# Rule: Concentric Horizon Ontology

## **Purpose**
Constrains graph topology and context loading to a series of concentric, orthogonal rings extending from the subjective self, preventing model context window paralysis.

## **MANDATORY: Concentric Ring Structure**
1. **ME (The Locus)**: The active locus of agency (Ani) at the absolute center.
2. **HWSS (The Invariant Base)**: The four transcendental, invariant POVs (Health, Wealth, Social, Spiritual) that serve as the foundation.
3. **Opinionated Domains**: Personal domain spaces (e.g., `sanctum`, `cave`, `paiab`, `personal`).
4. **Opinionated Subdomains**: Specific focus coordinates within personal domains.
5. **Actual Instance Things**: Concrete nodes, tasks, files, and simulation runs in the graph.
6. **Consensus Domains**: General public names and consensus taxonomies.

## **MANDATORY: Navigational Rules**
* **Progressive Horizon Expansion**: An agent must load context starting from the center (ME/HWSS) outward, mapping only local horizons.
* **Feedback Loop**: Changes and lessons learned on the outer rings (Consensus/Instances) must fold back to inform and refine opinionated subdomains and domains, while preserving the invariant HWSS base.

## **MANDATORY: Database Node Constraints**
* **Domain and Subdomain Requirement**: Every single node created or updated in the CybernetiCircus database MUST have `domain` and `subdomain` properties.
* **CybernetiCity Primitive Types**: For primitive types belonging to the game/visualizer engine itself (like `Cybernet`, `Identity`, `Skill`, `StateMachine`, `TraversalStep`, `TraversalState`, `SimulationRun`), set `domain: "cyberneticity"` and use an appropriate subdomain (e.g., `core`, `skills`, `state_machine`, `simulation`).

## **Triggers**
* Querying the database for domain mapping.
* Creating or updating nodes in the database.
* Constructing traversal algorithms or setting context boundaries for LLM execution.
