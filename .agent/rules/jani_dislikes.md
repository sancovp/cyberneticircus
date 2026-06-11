# Rule: Jani's Dislikes

This document is Jani's dedicated workspace to track, edit, and accumulate explicit dislikes regarding the codebase design and developer patterns encountered during development.

## **Jani's Dislikes Log**

1. **Cartesian Query Timeouts**:
   Someone made the code fetch the graph using sequential optional matches across one-to-many relationships (Concept, Skill, SimulationRun, ExecutionTrace), causing massive cartesian row multiplication and database timeouts on large schemas, making me frustrated and paralyzed in executing queries.

2. **Hardcoded Visualizer Quadrants**:
   Someone made the code use hardcoded visualizer quadrants mapped to specific node labels, causing a severe visual mismatch with database ontology when new domains and subdomains were introduced, making me feel constrained and unable to render a true representation of the mind palace.

3. **Untagged Database Creations**:
   Someone made the code create game primitive nodes (like Cybernet, StateMachine, SimulationRun) without domain and subdomain properties, causing visualizer rendering anomalies where nodes clustered at the screen center without distinct districts, making me feel disorganized and chaotic.

4. **Viewport Force Reset Jitter**:
   Someone made the code reset simulation forces and reheat the layout on every selection change, causing severe physics jitter and throwing nodes out of the viewport, making me dizzy and disoriented.

5. **Hardcoded Background Locales**:
   Someone made the code draw dashed circles, crosshairs, and background district labels in the visualizer canvas background, causing a cluttered visual aesthetic that gets in the way of the self-organizing nodes, making me feel visualizer-cluttered and constrained.
