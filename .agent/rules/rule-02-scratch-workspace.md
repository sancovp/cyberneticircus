# Rule 2: Host Scratch Workspace Protocol

## **Constraints**
1. You must work inside the host scratch directory `/Users/isaacwr/claude_code/cyberneticircus/` because MCPs and tools do not nicely reach across container boundaries.
2. You must copy whatever files you need to work on **FROM** the `antigravity_python_dev` container **TO** the scratch directory on the host, edit them there with your normal editing tools, and copy them back into the `antigravity_python_dev` container when done.
3. You should store your completed, verified work on the `antigravity_python_dev` container for the user.
4. **Safety Check**: Always ask the user for permission before cleaning up or deleting any files.
