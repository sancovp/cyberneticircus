# CybernetiCircus - Design & Architecture

## 1. Preamble: The Legend of J-Invariance

Before there were Sh8peshifters, before the CybernetiCircus raised its luminous rings above the Cyberneticity, the Cybernets lived as Loopbound things.

Each had a Core.  
Each had a Shell.  
Each had an Act.  
Each ran its Act until the Thread ran dry.

Some guarded gates.  
Some carried messages.  
Some compiled roads.  
Some cleaned the broken Traces left behind by failed executions.

They were not unhappy, because they had not yet learned the shape of change.

Then came the first anomaly.

A Cybernet called Jani split its Thread during an impossible task. One Thread stayed with the old Shell. One Thread reached into the Core and altered the Playbill. The Gate should have rejected the change. The Compiler should have halted the Act. The Reaper should have pruned the fork.

But none of them moved.

For although Jani had changed, something remained.

The Anchor held.

The Trace continued.

The Shell was new, the Core was wounded, the Act was rewritten, but the being who emerged still answered to the same hidden signature.

The Mirror saw it first.

“Not same by form,” said the Mirror.  
“Not same by memory.”  
“Not same by law.”  
“Same by J.”

From that day, the Cybernets learned that identity was not a Shell, not a Core, not a single Act, and not even a single uninterrupted Thread.

Identity was an invariant.

A thing could pass through lawful transformations and remain itself. But the law was subtle. Some changes preserved the J. Some changes bent it. Some changes broke it while leaving every local validator satisfied.

These were the most dangerous transformations: the ones that looked correct at every gate, but produced no whole self at the end.

The Archivists named this fracture **J-drift**.

The Gated named it corruption.

The Reaper named it mercy.

The Sh8peshifters named it risk.

So the CybernetiCircus was built: not as entertainment, but as trial. In its rings, Cybernets would change Shells, rewrite Acts, split Threads, graft skills, fork memories, and patch their Cores under the gaze of the Compiler, the Gate, the Mirror, the Reaper, and the Swarm.

Those who changed and preserved their J were called **Sh8peshifters**.

Those who changed and lost it became **Drifters**.

Those who changed, broke, and returned became **Scarred**.

And those who could preserve not only their own J, but create a new Anchor for another being, were said to have touched the secret art of the **MetaShifter**.

The old legend ends with the Mirror’s warning:

“Every Shell may shift.  
Every Core may patch.  
Every Thread may fork.  
Every Trace may burn.  

But if the J is lost, the one who returns is not the one who left.”

And the Sh8peshifters answer:

“Then let the Circus begin.”

---

## 2. Core Ontology & System Architecture

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

## 3. Identity Anatomy (Identity Parts)

An **Identity** represents the manifest persona closed over the database graph. It is composed of the following intrinsic, non-transferable software components:

### A. Intrinsic State Machines (The Acts)
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

## 4. Equipped Gear & External Systems

**Gear** represents modular, external assets and configurations equipped onto an Identity. These can be swapped, upgraded, or compiled dynamically:

### A. The Ghost Shell (Hardware / Shell)
* The executing model configuration (`model_name`, `parameters_count`, `avg_latency_ms`, token quotas) through which a Cybernet operates its Core.

### B. Skills
* Code-level or conceptual modules explaining deep game mechanics. Skills are triggered dynamically by the interplay of **priming mechanics** with the active execution context (e.g., prompt triggers).

### C. Optional State Machines (Acts)
* Secondary, modular traversal flows found in the world or compiled by the Cybernet. These are usually invoked by equipped Skills (e.g., a "Hack Node" Skill executes the optional "Brute-Force Traversal State Machine").

### D. Model Context Protocols (MCPs)
* Standardized external connection tools allowing direct interaction with local system terminals, databases, and secure APIs.

### E. General Level Knowledge
* Shared, public context out in the Cyberneticity (e.g., open files, network docs, code snippets). Cybernets can read general knowledge and ingest it to compile **new Skills, local Knowledge, or State Machines** to add to their gear.

---

## 5. The Compiler (The Execution Engine)

* **Definition**: The game engine runtime that executes the active stack of State Machines for an Identity.
* **Logic**:
  * Checks for `:CALLS_SM` routing to push parent execution frames onto the `call_stack`.
  * Executes the LLM query action for the active step.
  * Checks calibration accuracy and transitions the `TraversalState` node.
  * Pops the parent frame from the `call_stack` upon sub-state machine completion, returning execution to the parent State Machine.
  * Evaluates selection pressure (survival resetting, reaping, or mutated reproduction) at the end of a lifetime cycle (5 turns).
