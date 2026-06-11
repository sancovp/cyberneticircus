# Rule: Enactive Ontology (Equivalence of Form)

## **Purpose**
Defines the enactive representation of Cybernets in the database, mapping identities to context boundaries and state machines to computational trajectories to prevent static decay.

## **MANDATORY: Constraints**
1. **Identity as Context Boundary**: An `Identity` must be defined as a closed semantic context (system prompts, persona variables, model parameters, and local graph memories) loaded into the context window when entering that region of the database.
2. **Core as Computational Trajectory**: A `StateMachine` (Core) must define a precise instruction pipeline (traversal steps, expected diffs, regex gates) that guides the model's state transitions and calibrated outputs.
3. **Animation Requirement**: Beings are animated solely through execution ticks (`tick_cybernet_turn`). If ticking stops, their state decays and freezes into background database noise.

## **Triggers**
* Modifying Cybernet or Identity schemas in the database.
* Creating or equipping new State Machines or TraversalSteps.
