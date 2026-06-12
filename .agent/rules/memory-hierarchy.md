# Rule: Workspace Memory Hierarchy Protocol

## **Purpose**
Establishes the three-tier memory architecture to govern state tracking, project mapping, and rule crystallization without prompt bloat.

## **THE THREE MEMORY LAYERS**

### **1. Semantic Graph Memory (CartON)**
* **What**: Relational and property-based knowledge about the codebase structure, concept networks, and historical sprint notes.
* **When**: Use continuously during research and exploration to map connections (e.g., "Component X imports Component Y", "System Z has design flaw W").
* **Tools**: `observe_from_identity_pov`, `add_to_collection`, etc.

### **2. Transient Session Memory (Scratchpad)**
* **What**: Linear, short-term checklists, current task lists, and step-by-step sprint logs.
* **When**: Use for the active session context. Written to `.agent/rules/scratchpad.md`.
* **Cleanup**: Wiped or deleted immediately when the task is complete.

### **3. Regulatory Long-Term Memory (Rules)**
* **What**: Permanent operational rules, testing gates, and workflow constraints.
* **When**: Crystallized from the scratchpad into `.agent/rules/{name}.md` only after a procedure has proven successful and must be remembered permanently by future agents.
