# Rule: Context Engineering System Operational Protocol

## **Purpose**
Defines the operational rules required to keep the bootstrapped Context Engineering System functioning, self-reinforcing, and active across all future sessions.

## **MANDATORY: Operational Checklist**

### **1. Initialization Gate**
At the start of every session or task:
* Scan the active workspace root (`/scratch`) and nested project directories for their respective `.agent/rules/` folders.
* Confirm that the five baseline system rules are present and active:
  1. `agent-management.md` (Role, folder mechanics)
  2. `sync-boundary.md` (Boundary sync rules)
  3. `canonical-design.md` (DESIGN.md requirements)
  4. `prompt-replay.md` (Work/Adversarial prompt pipeline)
  5. `scratchpad-protocol.md` (Transient state tracking)

### **2. Drift Prevention**
* Never bypass the validation gates or skip testing protocols defined in the rules.
* When executing commands on the host or container, verify that your actions comply with the synchronization boundary.
* If a workspace layout changes, immediately update the corresponding pointer rules to prevent broken context links.

### **3. Maintenance and Evolution**
* Keep the rules updated with new lessons learned.
* Treat the rules files as production code: do not introduce vague instructions, decorative language, or untested heuristics.
