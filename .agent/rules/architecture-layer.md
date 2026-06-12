# Rule: Architectural Layer Visualization

## **Purpose**
Ensures all static software layers, packages, and components are mapped visually to prevent architectural drift, dependency loops, and boundary violations.

## **MANDATORY: Layer Visualization Rules**

### **1. The Layer Diagram Requirement**
* **What**: Every architectural layer, library, or component we design must have a corresponding **Component Diagram** or **Layer Diagram** showing its static structure and dependency interfaces.
* **Scope**: This applies to directories, databases, network boundaries, and package separations.

### **2. The Visualization Trigger**
* **When**: The moment you design or modify a multi-component system, introduce new modules, or establish boundary connections (e.g. host-to-container interfaces).
* **Action**: Map the static layout using subgraphs.

### **3. Syntax and Formatting**
* Always use Mermaid flowchart syntax (`graph TD` or `graph LR`).
* Use `subgraph` wrappers to explicitly mark boundaries (e.g., folder paths, databases, containers, or network layers).
* Ensure arrows represent the direction of dependency (which component references or relies on another).

### **4. Localization**
* Write the architectural diagram into a local rule file:
  `.agent/rules/architecture-{name}.md`
* Place this file inside the specific project subdirectory where the component resides (following the *progressive disclosure* protocol).
