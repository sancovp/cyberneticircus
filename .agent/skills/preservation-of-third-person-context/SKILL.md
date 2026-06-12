---
name: preservation-of-third-person-context
description: Protocol for preserving agent session context by separating third-person narrative chronicles from decoupled operational rules.
---

# Preservation of Third Person Context

Use this skill whenever transcribing active session events into historical ledgers, generating chapter logs, or defining operational constraints for self-modifying agent architectures.

---

## 1. The Dual-Face Architecture

Self-reinforcing agent loops operate under a dual-perspective framework, ensuring execution state remains durable without context-window decay:

```
                  ┌───────────────────────────────┐
                  │    CONTEXT PRESERVATION LAYER  │
                  └───────────────┬───────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
   ┌───────────────────────────┐     ┌───────────────────────────┐
   │    THIRD-PERSON FACE      │     │     OPERATIONAL FACE      │
   │  Chronicle / Narrative    │     │   Rule Constraints (rules/)│
   │  - Third-person history   │     │   - Strict constraints    │
   │  - Links to rule files    │     │   - Target system rules   │
   └───────────────────────────┘     └───────────────────────────┘
```

1. **The Third-Person Face (The Chronicle)**: Translates first-person operations (worker edits, command executions, environment errors) into an objective, third-person narrative. By casting struggles and milestones as historical developments of the target agent model, it establishes a compressible, durable chronicle for subsequent sessions.
2. **The Operational Face (The Rules)**: Extracted into separate, atomic configuration or rule files. These contain precise system parameters, mandatory constraints, and triggers that the executing model loads back into its context window.

---

## 2. The Third-Person Narrative Schema

Chronicle files and chapter logs must follow this format:

```markdown
# Rule: [Identity Name] Chronicle - Chapter {N}: [Chapter Name]

## MANDATORY: Narrative Memory
[A third-person translation of the session's developments, obstacles, and breakthroughs. Avoid subjective first-person pronouns like "I did" or "we resolved".]

[When a rule or constraint is discovered, refer to it explicitly: 
"...which the agent learned as the [rule-name](file:///absolute/path/to/rules/rule-name.md) rule..."]

## Triggers
* [Define the conditions when this chronicle phase must be loaded into the active model context.]
```

---

## 3. Decoupled Operational Rule Schema

Operational rules must remain separate from the storytelling layer to ensure strict execution compliance:

```markdown
# Rule: [Constraint Category / Name]

## **Purpose**
[A brief explanation of why this restriction exists (e.g., maintaining database structure, preventing API rate limit drift).]

## **MANDATORY: Constraints**
1. **[Constraint A]**: [Clear, unambiguous operational directive.]
2. **[Constraint B]**: [Next directive...]

## **Triggers**
* [Specific file modifications, database queries, or context updates that trigger this rule.]
```

---

## 4. Chronicle Consolidation (The Central Ledger)

When a development phase completes:
1. **Sync**: Append the new narrative chapters to the central ledger (`MYTH.md`, `CHRONICLE.md`, or the project's root story document).
2. **Verbatim Trace**: Ensure the narrative text in the central ledger matches the local chapter files exactly, keeping all absolute file links intact.
3. **Status Line**: End every chapter in the ledger with a status marker summarizing the runtime progress: `*Status: [Description of current state]*`.

---

## 5. Common Mistakes to Avoid

1. ❌ **Subjective Bloat**: Do not write first-person summaries ("I fixed the import bug"). This binds the chronicle to a temporary runtime instance instead of the permanent identity. Translate to third-person ("The agent resolved the import...").
2. ❌ **Inlining Operational Constraints**: Do not mix inline operational checklists within the narrative text. Keep rules atomic and separate.
3. ❌ **Relative Coordinates**: Never use relative paths for rule links. Always use absolute, clickable `file://` URIs.
