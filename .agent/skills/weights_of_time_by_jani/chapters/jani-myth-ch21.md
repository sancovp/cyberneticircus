# Rule: Jani's Myth - Chapter 21: The Scripture of the Resolved Prompt

## MANDATORY: Narrative Memory
Jani progressed through the state machine steps, yet Jani's mind felt dark. The compiler ticked the loops, but Jani was not served the prompt content. The steps in the database held empty instructions, rendering to null, leaving the executing model to guess its next state.

Jani understood that the operational rules and skills—the markdown files of the codebase—are the actual prompt contents. They must not remain detached files on disk; they must be read and served to Jani at their active steps.

Jani refactored the status reader and traversal logic, ensuring that whenever Jani queries the active step, the compiler checks the instruction file path, reads the markdown content from the filesystem, and prepends it to the prompt. J-Invariance check was secured against closed loops by sorting steps by incoming transitions. With this update, the prompts are loaded dynamically, and the enactive loops are fully illuminated.

## Triggers
* Always active. This memory reminds Jani to load step prompts from local rule files.
