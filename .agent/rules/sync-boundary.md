# Rule: Container/Scratch Synchronization Protocol

## **Purpose**
Prevents out-of-sync states, lost changes, and write collisions between the host scratch workspace (`/scratch`) and the persistent `antigravity_python_dev` container.

## **MANDATORY: Sync Constraints**
1. **Host-First Edits**: All editing and coding must happen in the host workspace `/Users/isaacwr/claude_code/cyberneticircus/`. Never edit files directly inside the container.
2. **Version Checks**: Before modifying a file, check if its container counterpart has a newer modification timestamp. If so, pull the container version first to avoid overwriting work.
3. **Prompt Promotion**: Once a task is complete and tests pass, immediately sync the changed files back to the container:
   `docker cp /Users/isaacwr/claude_code/cyberneticircus/{file} antigravity_python_dev:/workspace/{file}`
4. **No Silent Cleanups**: Never run `rm`, clean-up scripts, or delete folders in the container or host scratch space without asking the user first.
