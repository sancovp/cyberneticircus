# Field Guide: Workspace Configurator and Operational Playbook for the `.agent` Directory

## **Domain Orientation**

The `.agent` directory is a local workspace configurator. It is not a passive documentation folder; it is an active control directory that dictates how a coding agent operates, verifies, and adapts within a specific codebase. 

In this architecture, the codebase and the configuration are bound together. The `.agent` directory allows the agent to read local constraints, execute specialized workflows, and write back its learning, converting a static codebase into an environment optimized for automated execution.

---

## **Mechanics of the `.agent` Layout**

The directory operates through two native subdirectories: `/rules` and `/skills`.

### **1. How to Write Rules (`.agent/rules/`)**
Rules are Markdown files (`.md`) placed in the `.agent/rules/` directory. 

* **The Loading Mechanism**: When the IDE initializes or refreshes the agent session in a workspace, it automatically scans `.agent/rules/`, reads all markdown files, and appends them to the active system prompt rules.
* **Writing Protocol**:
  1. Create a markdown file: `.agent/rules/{rule-name}.md`.
  2. Structure the file with clear headers: `## MANDATORY: Constraints`, `## Verification Gate`, and `## Triggers`.
  3. Keep the rules strict, imperative, and actionable. Avoid narrative or explanations.

### **2. How to Write Skills (`.agent/skills/`)**
Skills are self-contained folders placed under `.agent/skills/` that extend the agent's active capabilities.

* **The Loading Mechanism**: The IDE scans `.agent/skills/`. For every subdirectory, it requires a file named `SKILL.md`. It parses this file to extract the skill's name, description, and guidelines, and registers them under the available skills list.
* **Writing Protocol**:
  1. Create a subdirectory: `.agent/skills/{skill-name}/`.
  2. Create the required file: `.agent/skills/{skill-name}/SKILL.md`.
  3. Include the standard skill schema:
     ```markdown
     # Skill Name: sic-{name}
     
     ## Description
     Clear, compact summary of what this skill does and when the agent must trigger it.
     
     ## Guidelines
     Step-by-step instructions on how the agent runs the helper scripts or executes the task.
     ```
  4. Place any supporting Python, Node, or Shell scripts inside that same folder. The agent will read `SKILL.md` to learn the exact terminal command required to execute these scripts.

---

## **Good vs. Bad Architecture Patterns**

### **Rules**

#### **❌ A Bad Rule**
```markdown
# General Coding Guidelines
Be very careful when you write code in this directory. Try to write clean code, follow SOLID principles, and make sure you add some comments so the user can understand what you did. Also, run tests if you can.
```
* **Why it fails**: It is purely decorative. "Be careful" and "write clean code" cannot be verified programmatically. It lacks triggers, specific command locations, and kill criteria.

#### **✅ A Good Rule**
```markdown
# Crystal Ball Base Library Constraints

## MANDATORY: Pipeline Check
All edits to the Crystal Ball codebase must start in the base library at `/lib/crystal-ball/`. You must not write logic in `/crystal-ball-viz/` that does not exist in the kernel API.

## Verification Gate
Before completing any task, run the test suite:
`/Users/isaacwr/.gemini/antigravity/scratch/.venv/bin/pytest /Users/isaacwr/.gemini/antigravity/scratch/observatory-sdna`
If the tests do not return a 100% pass rate, you must stop, revert the change, and analyze the failure.
```
* **Why it succeeds**: It establishes clear boundaries, names specific directories, and defines a strict, non-negotiable verification gate with an exact execution path.

---

### **Skills**

#### **❌ A Bad Skill**
```markdown
# Skill: Code Importer

## Description
This skill helps the agent import files from the container.

## Guidelines
Just copy the files over using standard commands like cp or docker cp whenever you feel like you need them.
```
* **Why it fails**: It has no structure. It doesn't define the input/output expectations, does not provide a specific shell command template, and leaves the execution path entirely up to the agent's guesswork.

#### **✅ A Good Skill**
```markdown
# Skill: sic-sync-container-source

## Description
Synchronizes file modifications between the host scratch workspace and the `antigravity_python_dev` container. Use this skill immediately before writing files to verify you are working with the latest codebase.

## Guidelines
Execute the synchronization script from the host shell:
`python3 /Users/isaacwr/.gemini/antigravity/scratch/scripts/sync_source.py --direction {host_to_container|container_to_host} --file {relative_path}`

## Verification Gate
The script will output `SYNC_COMPLETE: {hash}` on success. If it prints `SYNC_ERROR`, halt execution and report the diff.
```
* **Why it succeeds**: It names a specific script, declares clear parameter configurations, sets trigger conditions, and defines a machine-readable validation marker (`SYNC_COMPLETE`).
