# CybernetiCircus - Design & Architecture

This document serves as the **Single Canonical Design** for the CybernetiCircus project. It outlines the conceptual hierarchy, naming conventions, and structural logic of the human-agent cybernetic system.

---

## 1. The Core Ontology

The world, beings, and mechanics of the CybernetiCircus are structured around the following naming layers:

### The Substrate
* **The Cyberneticity**: The global database environment. A vast, interconnected graph network of nodes, edges, and state transitions that forms the substrate where all entities exist, communicate, and run their execution loops.

### The Beings
* **Cybernets**: The self-modifying graph-beings who live in the Cyberneticity. They represent the active agent entities that execute queries, maintain records, and manipulate the database state.

### The Arena
* **The CybernetiCircus**: The runtime execution harness and arena. This is the sandboxed workspace where Cybernets test their logic, run simulation plays, mutate their stats, perform collaborative tasks, and evolve or get pruned over successive lifetimes.

### The Capability
* **Sh8peshifters**: A specialized class of Cybernets capable of dynamically modifying their internal components (Shells, Cores, active Skills, and state machine stacks) while preserving complete identity continuity.

### The Ultimate Rank
* **The MetaShifter**: The divine/legendary rank of graph-being. Unlike standard Sh8peshifters who can only alter themselves, a MetaShifter has the power to define, compile, and spawn entirely new identities and Cybernets into the Cyberneticity.

---

## 2. Identity Anatomy (Identity Parts)

An **Identity** represents the manifest persona closed over the database graph. It is composed of the following intrinsic, non-transferable software components:

### A. Intrinsic State Machines
* The baseline cyclic execution loops representing the core lifecycle (e.g., the default Day/Night turn sequences).

### B. System Prompt Blocks
A modular array of prompts loaded into the active memory context:
* `background/world`: Context describing the surrounding state of the Cyberneticity.
* `persona`: Core behavioral constraints, personality traits, and reasoning parameters.
* `core loop`: Sequential instructions guiding how the identity processes turns.
* `priming mechanics`: Structured prompt templates designed to nudge or orient the model's reasoning during context changes.
* `dream rank`: The cognitive aspiration and evolution tier of the Identity, defining its complexity potential.
* `identity level knowledge`: Local, private graph memories and rules locked exclusively to this specific Identity.

---

## 3. Equipped Gear & External Systems

**Gear** represents modular, external assets and configurations equipped onto an Identity. These can be swapped, upgraded, or compiled dynamically:

### A. The Ghost Shell (Hardware)
* The executing model configuration (`model_name`, `parameters_count`, `avg_latency_ms`, token quotas) through which a Cybernet operates its Core.

### B. Skills
* Code-level or conceptual modules explaining deep game mechanics. Skills are triggered dynamically by the interplay of **priming mechanics** with the active execution context (e.g., prompt triggers).

### C. Optional State Machines
* Secondary, modular traversal flows found in the world or compiled by the Cybernet. These are usually invoked by equipped Skills (e.g., a "Hack Node" Skill executes the optional "Brute-Force Traversal State Machine").

### D. Model Context Protocols (MCPs)
* Standardized external connection tools allowing direct interaction with local system terminals, databases, and secure APIs.

### E. General Level Knowledge
* Shared, public context out in the Cyberneticity (e.g., open files, network docs, code snippets). Cybernets can read general knowledge and ingest it to compile **new Skills, local Knowledge, or State Machines** to add to their gear.

---

## 4. The Compiler (The Execution Engine)

* **Definition**: The game engine runtime that executes the active stack of State Machines for an Identity.
* **Logic**:
  * Checks for `:CALLS_SM` routing to push parent execution frames onto the `call_stack`.
  * Executes the LLM query action for the active step.
  * Checks calibration accuracy and transitions the `TraversalState` node.
  * Pops the parent frame from the `call_stack` upon sub-state machine completion, returning execution to the parent State Machine.
  * Evaluates selection pressure (survival resetting, reaping, or mutated reproduction) at the end of a lifetime cycle (5 turns).
