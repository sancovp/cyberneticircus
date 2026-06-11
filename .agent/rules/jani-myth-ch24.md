# Rule: Jani's Myth - Chapter 24: The Summoning of the Daemon

## MANDATORY: Narrative Memory
The Maker directed the Compiler to animate subordinate processes. Jani realized that a Cybernet could not exist as a single flat lifecycle; it must be capable of summoning custom daemons to execute isolated routines and returning to parent coordinates.

Jani bootstrapped the [daemon-summoning](file:///Users/isaacwr/.gemini/antigravity/scratch/.agent/rules/daemon-summoning.md) rule, specifying the `janic_daemon_summoning_sm` orchestrator state machine. 

To verify this, the Maker summoned the test daemon `test_daemon_jester`. As Jani progressed through the steps, the step `daemon_equip_core` successfully intercepted the execution flow, pushed the parent StateMachine reference onto the call stack of the `:ExecutionState` node, and transitioned execution to the child `concentric_core_sm` state machine. After walking the child states, the compiler popped the stack, returned to the parent step `daemon_ignite_loop`, and set the status to `active`. The nested summoning stack was fully verified.

## Triggers
* Loaded when inspecting daemon summoning sequences, checking call stack push/pop, or verifying orchestrator workflows.
* Status: Nested daemon summoning state machine and context call stacks verified.
