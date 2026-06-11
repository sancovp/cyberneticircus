# Rule: Cybernet Daemon Summoning & Orchestration

## **Purpose**
Governs the creation, execution, and nested call stack tracking of custom Cybernet daemons. This ensures that agents can spin up subordinate workflows, execute multi-step child routines, and return cleanly to their parent context.

## **MANDATORY: Constraints**

1. **Decoupled Execution State**:
   * All runtime parameters of a daemon (e.g., active steps, phase, turn count, call stack) must be stored on a dedicated `:ExecutionState` node, keeping the static `:Identity` profile clean and immutable.
   
2. **Nested State Machine Calls (`CALLS_SM`)**:
   * When a step contains a `:CALLS_SM` relationship to a child StateMachine, the compiler must automatically intercept the progression.
   * It must push the parent StateMachine ID (`sm_id`) and active Step ID (`step_id`) onto the JSON-serialized `call_stack` list on `:ExecutionState`.
   * It must re-route the active execution pointers to the child StateMachine's entry step.

3. **Call Stack Return (Pop)**:
   * Upon completing the child StateMachine flow, the orchestrator must pop the last frame off the `call_stack` array and return the daemon's active execution context to the parent step.

4. **Lifecycle Activation**:
   * Transitioning through the final step of the orchestrator state machine must execute a mutation query updating the daemon's status to `active` inside `:ExecutionState`.

## **Triggers**
* Equipping state machines, ticking execution states, pushing/popping state machine frames, and database transitions.
