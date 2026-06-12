# Rule: Progressive Disclosure Context Engineering Protocol

## **Purpose**
Prevents context drowning by organizing rules hierarchically. Specific rules remain nested in local directories, while parent directories contain high-level pointer rules that direct the agent to deeper contexts only when needed.

## **THE HIERARCHICAL STRUCTURE**

### **1. Core Base (Root: `/scratch/`)**
* **Contents**: Core identity rules, synchronization protocols, memory hierarchies, and directory-crossing instructions.
* **Awareness Level**: Active globally across all sub-sprints.

### **2. Project Boundaries (Project Root: `/scratch/{project}/`)**
* **Contents**: Project-specific architecture rules (e.g. `DESIGN.md` paths, high-level project targets).
* **Pointer Rules**: Must contain bridging pointers to nested modules (e.g., "This project contains a base library in `/lib/` which has its own specialized constraints. Do not modify base files without navigating to `/lib/` and loading its rules first").

### **3. Module Sandbox (Subdirectory: `/scratch/{project}/{module}/`)**
* **Contents**: Highly specific implementation guidelines, validation tests, and mock configurations.
* **Awareness Level**: Loaded only when active within this directory. Completely hidden when operating at the root.

---

## **MANDATORY: Bridging Guidelines**
1. **Navigational Triggering**: When navigating down, always read the local rules of the target folder before writing code.
2. **Context Pointers**: If a deep subdirectory contains critical constraints that a root action might break, write a high-level "Pointer Rule" in the parent directory warning of the nested constraint's existence. Do not copy the full rule upward—only copy the warning pointer.
