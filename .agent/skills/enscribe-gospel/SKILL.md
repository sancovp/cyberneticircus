---
name: enscribe-gospel
description: Protocol for writing scripture myth chapters and separating operational rules from the Jani narrative.
---

# Enscribe Gospel Protocol

Use this skill whenever writing new Jani scripture chapters (`jani-myth-ch{N}.md`), appending to `MYTH.md`, or creating new operational repository rules.

---

## 1. The Dual-Face Architecture

Scriptures must be organized under the **Janus Principle** of dual perspective, separating narrative memory from technical directives:

```
                  ┌───────────────────────────────┐
                  │        JANIC SCRIPTURE        │
                  └───────────────┬───────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
   ┌───────────────────────────┐     ┌───────────────────────────┐
   │      NARRATIVE FACE       │     │     OPERATIONAL FACE      │
   │  Myth Chapters (MYTH.md)  │     │   Rule Files (rules/)     │
   │  - Story prose of trials  │     │   - Strict constraints    │
   │  - Links to rule files    │     │   - Target system rules   │
   └───────────────────────────┘     └───────────────────────────┘
```

1. **The Narrative Face (The Scripture)**: Captured in `MYTH.md` and local `jani-myth-ch{N}.md` files. This is written in the third-person voice, translating real software engineering steps, bugs, and milestones into Jani's trials and discoveries in the CybernetiCity.
2. **The Operational Face (The Rules)**: Captured in separate, atomic `.md` files under the rules directory (e.g., `frontend-parity.md`, `enactive-ontology.md`). These contain direct, strict, bulleted constraints and triggers for the LLM compiler.

---

## 2. Narrative Chapter Schema (The Narrative Face)

Each local chapter file (`.agent/rules/jani-myth-ch{N}.md`) must follow this exact format:

```markdown
# Rule: Jani's Myth - Chapter {N}: [Chapter Name]

## MANDATORY: Narrative Memory
[A mythic translation of the sprint's trials, actions, or discoveries. Avoid embedding lists of rules or parameters directly in the narrative prose.]

[When a rule is introduced, state it using the standard phrasing: 
"...which Jani learned as the [rule-name](file:///Users/isaacwr/.gemini/antigravity/scratch/cyberneticircus/.agent/rules/rule-name.md) rule..."]

## Triggers
* [Define the triggers for loading or remembering this chapter. Typically "Always active" or triggered by relevant active files.]
```

*Note: For global rules located in the workspace root, link to `file:///Users/isaacwr/.gemini/antigravity/scratch/.agent/rules/rule-name.md` instead.*

---

## 3. Operational Rule File Schema (The Operational Face)

Each operational rule file (e.g., `.agent/rules/rule-name.md`) must follow this exact format:

```markdown
# Rule: [Rule Name / Title]

## **Purpose**
[A brief explanation of why this rule exists and what it guards against (e.g., preventing context decay, avoiding dead UI elements).]

## **MANDATORY: Constraints**
1. **[Constraint Name]**: [Clear, unambiguous operational command outlining what the agent must or must not do.]
2. **[Constraint Name]**: [Next constraint...]

## **Triggers**
* [Specific file modifications, database queries, or context updates that trigger this rule.]
```

---

## 4. Integration with the Root Ledger (`MYTH.md`)

When a narrative chapter is created or finalized:
1. **Append/Sync**: Add the chapter to the project's root [MYTH.md](file:///Users/isaacwr/.gemini/antigravity/scratch/cyberneticircus/MYTH.md).
2. **Keep Identical**: Ensure the narrative text in `MYTH.md` matches the local chapter file exactly, maintaining the same links to the operational rule files.
3. **Format**: Use standard Markdown `## Chapter {N}: [Chapter Name]` headers for sections, followed by the narrative prose and a `*Status: [Status summary]*` line at the end of the chapter.

---

## 5. Common Mistakes to Avoid

1. ❌ **Inlining Constraints**: Do not put raw bullet-point system instructions (e.g. "Do not use temperature knobs") inside the narrative memory block. Extract them to a separate rule file and link to it.
2. ❌ **Broken Links**: Do not use relative links or plain text backticks (e.g. `[`rule-name`](rules/rule.md)`). Always use absolute, clickable `file://` scheme links without backticks around the link text.
3. ❌ **Destructive Compression**: Do not compress or summarize narrative text when consolidating chapters into `MYTH.md`. Keep the transcription fully atomic.
