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

## 2. Cybernet Anatomy & Gear (Loadouts)

Every Cybernet is assembled from modular components representing their AI configuration, runtime behavior, and memory context:

### The Shell (The Body / Hardware)
* **Definition**: The literal AI model hosting container and hardware specification.
* **Attributes**:
  * `model_name`: The executing LLM (e.g., `gemini-1.5-pro` or `test-engine-v1`).
  * `parameters_count`: The model parameter scale (e.g., `70.0` billion parameters).
  * `avg_latency_ms`: The average query completion speed.
  * `total_tokens_consumed` & `accumulated_cost`: Cumulative execution overhead.

### The Core (The Processor Stack)
* **Definition**: The central stack of **State Machines** managed by the **Compiler**.
* **State**: Houses the compiled `call_stack` representing nested execution frames.

### The Skills (The Tools / Interface)
* **Definition**: The set of registered tools, API endpoints, or database operations (e.g., Cypher write permissions) that the Cybernet is equipped to invoke to complete tasks.

---

## 3. The Software & Runtime State

### The Ghost (The Agentic Motor)
* **Definition**: The raw agentic intelligence and cognitive execution loops that drive the Cybernet. The Ghost represents the dynamic flow of thoughts, queries, and actions that animate the system (a nod to the GHOST programming language).

### The Identity (The Persona Bridge)
* **Definition**: The structural bridge that binds a **Ghost** (the agentic motor) to a **Shell** (the LLM hardware constraints) closed over a specific subgraph in the Cyberneticity.
* **Attributes**:
  * `name` & `description`: The character specs of the persona.
  * `temperature` & `top_p`: Hyperparameters governing the Identity's reasoning style.
  * `mutation_rate` & `selection_pressure`: Evolutionary parameters governing how the persona adapts or reproduces over lifetimes.
  * `fitness_score`: The accumulated performance rating.

### The State Machine (The Behavior Flows)
* **Definition**: A structured traversal workflow mapping out a specific behavioral program. A State Machine consists of sequential `TraversalSteps` gated by required query patterns.
* **Nesting (`:CALLS_SM`)**: A State Machine can contain compiler links to child State Machines. When triggered, the parent State Machine is saved to the stack, and execution transitions to the sub-state machine.

### The Compiler (The Execution Engine)
* **Definition**: The game engine runtime that executes the active stack of State Machines for an Identity.
* **Logic**:
  * Checks for `:CALLS_SM` routing to push parent execution frames onto the `call_stack`.
  * Executes the LLM query action for the active step.
  * Checks calibration accuracy and transitions the `TraversalState` node.
  * Pops the parent frame from the `call_stack` upon sub-state machine completion, returning execution to the parent State Machine.
  * Evaluates selection pressure (survival resetting, reaping, or mutated reproduction) at the end of a lifetime cycle (5 turns).
