# Rule: Domain Expansion & Progressive Compiler Layers

## **Purpose**
Governs the modeling and execution of progressive compiler layers on a Cybernet's `:ExecutionState`. This tracks the accumulation of software complexity and evolutionary checks during traversal.

## **MANDATORY: Constraints**

1. **Active Layer Tracking**:
   * The currently active compiler layer must be explicitly tracked inside the `current_layer` string property of the `:ExecutionState` node (e.g., `'Layer 1'`, `'Layer 2'`, etc.).

2. **Historical Accumulation**:
   * All successfully completed compiler layers must be logged as a list inside the `completed_layers` array property of the `:ExecutionState` node.
   * Progression side-effects must append new layers to this list, maintaining a permanent timeline of complexity acquisition.

3. **Step-Specific Side Effects**:
   * Transitions through specific layer steps (`layer1_primitive_boot`, `layer2_meta_compile`, `layer3_sdlc_ignite`) must trigger corresponding Cypher mutations updating both `current_layer` and `completed_layers`.

## **Triggers**
* Domain expansion state machine transitions, compilation layer mutations, and evolution assessments.
