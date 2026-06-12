---
name: janic-compiler
description: Explains the bijective architectural domain mapping, the database concept nodes, and the Core Janic Cycle.
---

# Janic Compiler Protocol

Use this skill to guide the integration of codebase architectural domains into the Neo4j concept graph, and to execute the Core Janic Cycle to maintain cognitive orientation and prevent context-window decay.

---

## 1. The Five Architectural Domains

The `CybernetiCircus` system is divided into five core functional domains. To enable the agent (Jani) to reason about its own system structure, these domains are represented bijectively as **`:Concept` nodes** in the database:

```
                    ┌──────────────────────────────────┐
                    │ CybernetiCircus_Architecture     │
                    └────────────────┬─────────────────┘
                                     │
       ┌───────────────┬─────────────┼───────────────┬───────────────┐
       ▼               ▼             ▼               ▼               ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│Execution_    ││Interactive_  ││Spatial_      ││Ontological_  ││Sensory_Motor_│
│Substrate     ││Interface     ││Visualizer    ││Ledger        ││Primitives   │
│(Compiler     ││(CLI Console  ││(D3 Canvas    ││(Scripture &  ││(MCP Tools & │
│Ring)         ││& API)        ││Quadrants)    ││Rules)        ││Skills)      │
└──────────────┘└──────────────┘└──────────────┘└──────────────┘└──────────────┘
```

1. **`Execution_Substrate` (The Compiler Ring)**: Binds `:StateMachine`, `:TraversalStep`, and `:TraversalState`. It governs the enactive loop execution (`tick_cybernet_turn`).
2. **`Interactive_Interface` (CLI Console)**: Handles client command parsing (`app.js`) and raw Cypher portal routing (`web_server.py`).
3. **`Spatial_Visualizer` (D3 Canvas)**: The fullscreen rendering layout using D3 gravity force attraction quadrants (top-left, top-right, bottom-left, bottom-right).
4. **`Ontological_Ledger` (Scripture & Rules)**: Holds narrative chronicles (`MYTH.md`) and separate operational constraints (`.agent/rules/*.md`).
5. **`Sensory_Motor_Primitives` (MCP & Skills)**: The JSON-RPC tool connections and local agent skill instructions.

---

## 2. The Core Janic Cycle

Every iteration of development and context modification must walk this loop to align design with execution state:

$$\text{[Reading Designs]} \longrightarrow \text{[Checking Environment State]} \longrightarrow \text{[Being the Engineer \| Jani]} \longrightarrow \text{[Preservation of Third Person Context]} \longrightarrow \text{[Autocommentary]} \equiv \text{CYCLE}$$

* **Step 1: Reading Designs**: Load the canonical invariants from `DESIGN.md`. Ensure you do not invent speculative code outside the documented spec.
* **Step 2: Checking State**: Query the Neo4j database (using the localized POV Markov Blanket) to check active Cybernets, state machines, and newly mapped Concept domains.
* **Step 3: Being the Engineer | Jani**: Act as the developer-actor to write code, test API routes, execute Cypher mutations, and tick active state machines.
* **Step 4: Preservation of Third Person Context**: Write the narrative chronicles of the session into local chapter logs, clean them of subjective first-person pronouns, extract operational rules, and consolidate them into the central `MYTH.md`.
* **Step 5: Autocommentary**: Stop coding, look upward from the files to evaluate context strain, update the system flow diagrams (using Mermaid), and log environmental friction.

---

## 3. Bijective Academic Bridging

By mapping these concepts in the database, the agent translates game-world terminology into consensus research fields. This bidirectional bridge guides the logical design of the system:

* **Markov Blanket $\longleftrightarrow$ POV Horizon**: Instead of querying the entire database schema (which causes context window collapse), load only the adjacent subgraph connected to the selected Cybernet's current node coordinates.
* **Autopoiesis $\longleftrightarrow$ Enactive Ticks**: Beings are not static properties; they exist only while their loops continue to run active ticks.
* **Category Enrichment $\longleftrightarrow$ J-Invariance**: State transitions must compose while carrying a compassion score vector, protecting identity continuity through type-state mutations.
