# Rule 7: Read Tools and Bash Long Output Mitigation

## **Constraints**
* The `Long Output Bug` rules from Rule 6 also apply to read tools and bash tools (`cat`, `ls`, `grep`, `find`, etc.).
* If a terminal command returns a large output, halt execution in that turn and start your response with:
  `⚠️ Long Output alert -- `
