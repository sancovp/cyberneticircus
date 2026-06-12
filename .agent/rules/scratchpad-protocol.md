# Rule: Scratchpad Protocol

## **Purpose**
Defines a lightweight, zero-dependency method for maintaining transient session-specific memory directly in the workspace.

## **MANDATORY: Scratchpad Usage**
1. **The Scratchpad File**: All transient session notes, active task checkpoints, and immediate goals must be written to the local rule file:
   `.agent/rules/scratchpad.md`
2. **Automatic Loading**: The IDE will automatically load `scratchpad.md` as part of the system rules in the next turn, making it part of the active context.
3. **Task Wiping**: Once a sprint, task, or session is complete, you must clear the contents of `scratchpad.md` (or delete the file) to release the context window.
4. **Static Safety**: Do not modify global prompt files (like `GEMINI.md`) for transient session data. Keep the global prompts static.
