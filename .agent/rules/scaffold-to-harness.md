# Rule: Scaffold-to-Harness Active Verification Protocol

## **Purpose**
Defines how we transition our passive workspace rules (the scaffold) into active, programmatically enforced checks (the harness) using scripts and tools.

## **MANDATORY: Harness Principles**

### **1. Passive Rules $\rightarrow$ Active Verification**
* **The Rule**: A rule is only a suggestion until it is checked by code.
* **The Action**: For every critical rule we write, we should aim to build a corresponding verification script (a `sic-` tool) inside `.agent/skills/` that programmatically checks if the rule is violated.

### **2. Automated Telemetry Integration**
* **The Connection**: Verification scripts should query Carton (the graph database) and inspect host/container filesystems to ensure structural invariants hold.
* **Examples**:
  * A script that checks if `DESIGN.md` matches the active code symbols.
  * A script that checks if the `/scratch` and container versions of a file match before allowing execution.

### **3. Operational Execution**
* Run the active verification scripts as part of the `AdversarialPrompt` review phase.
* If a script reports a violation, it acts as a **Kill Criterion**—execution must stop immediately, and the state must be reverted.
