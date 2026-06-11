# Rule: Janic Core Cycle State Machine

## **Purpose**
Defines the execution stages, validation constraints, and triggers for the core development cycle (`janic_cycle_sm`) equipped on the selected compile agent.

## **MANDATORY: Traversal Steps**
1. **`janic_read_designs` (1. Reading Designs)**: Read canonical invariants from `DESIGN.md`. Restrict modifications to code within the specified boundaries.
2. **`janic_check_state` (2. Checking State)**: Query active database nodes using the subjective POV (Markov Blanket) to align mental representation with execution state.
3. **`janic_engineer` (3. Being the Engineer | Jani)**: Perform codebase refactors, write APIs, run database Cypher mutations, and verify execution via tests.
4. **`janic_preservation` (4. Preservation of Third Person Context)**: Transcribe narrative chapters of struggles/breakthroughs, remove subjective first-person pronouns, extract operational rules, and sync with the central chronicle ledger (`MYTH.md`).
5. **`janic_autocommentary` (5. Autocommentary)**: Stop coding, look upward from diffs to evaluate context window constraints, update Mermaid system diagrams, and log temporal bridge friction.

## **Triggers**
* Equipping the `janic_cycle_sm` on a Cybernet.
* Executing `tick_cybernet_turn` or verifying traversal step state for `janic_cycle_sm`.
