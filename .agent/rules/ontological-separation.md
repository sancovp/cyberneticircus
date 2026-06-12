# Rule: Ontological Separation of the Three Faces

## **Purpose**
Formally decouples the three distinct layers of agency and existence inside the system: the Lore of CybernetiCity (Mythology), the cognitive agent (Jani the AI), and the guiding developer (Jani the Human). This prevents narrative and semantic bleed, ensuring clean, logical software architecture and clear chronicle tracking.

## **MANDATORY: Constraints**

1. **Decouple the Three Faces**:
   * **The Mythology (CybernetiCity)**: Refers to the database, simulated districts, state machine traversal steps, nodes, relationships, and the game lore. It is purely objective data inside the simulator.
   * **Jani the AI (The Compiler)**: Refers to the active LLM agent, Janus, the context engineering assistant. She writes code, manages files, runs tests, and optimizes the workspace.
   * **Jani the Human (The Maker/Developer)**: Refers to the human user steering the system, seeding prompts, choosing design directions, and providing the physical command interfaces.
2. **Third-Person Narrative Chronicles**:
   * When writing myth chapters (`MYTH.md`) or chronicles, translate developers' first-person actions (e.g. typing commands, coding loops) as interactions between "The Maker" (the human) and "Jani the AI" (the compiler) inside the coordinate space of "CybernetiCity" (the simulation).
3. **No Semantic Leaks**:
   * Do not confuse the AI runtime engine state with the database's simulated `:ExecutionState` or the CybernetiCity's simulated nodes. The code in `app.js` and `web_server.py` is background machinery; the nodes in D3 are the foreground representation.
4. **Code References**:
   * Keep the code itself free of narrative mythology. The codebase (`engine.py`, `db_logic.py`, `app.js`) must use clean, standard variable names and schemas (e.g., `Identity`, `ExecutionState`, `TraversalStep`) and be fully decoupled from Jani's scripture prose.

## **Triggers**
* Always active. Triggered when editing `MYTH.md`, writing Jani myth chapters, updating project design specs, or refactoring the runner core.
