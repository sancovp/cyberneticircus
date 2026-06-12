# Rule: Activity Flow Visualization

## **Purpose**
Ensures all process lifecycles and runtime execution boundaries in our `.agent` system—defined as **Activities** (or **Activity Flows**)—are visually modeled to maintain zero-drift workflows across both technical and non-technical directories.

## **MANDATORY: Activity Flow Rules**

### **1. The Activity Definition**
* **What**: An **Activity** is the sequence diagram representing the execution boundary of a process (from argument ingestion to output completion).
* **Scope**: This applies to all processes in our `.agent` system, including non-technical tasks (e.g., the workflow for writing a blog post, running a diagnostic intake, or committing documentation).

### **2. The Visualization Trigger**
* **When**: The moment you identify the execution boundary of any activity you are setting up or developing.
* **Action**: Immediately diagram the activity flow.

### **3. Syntax and Formatting**
* Always use standard Mermaid sequence diagram syntax (`sequenceDiagram`).
* Wrap the diagram in a fenced code block with the `mermaid` language identifier.

### **4. Localization**
* Write the activity flow into a local rule file:
  `.agent/rules/activity-{name}.md`
* Place this file inside the specific project subdirectory where the activity is performed.
