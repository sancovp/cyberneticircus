# Rule 6: Playwright Long Output Mitigation

## **Constraints**
* Pay attention to turn length when calling Playwright tools that return massive browser context.
* If you receive a very long output, halt further execution in that turn.
* Return control to the user immediately, starting your response with:
  `⚠️ Long Output alert -- `
This is a workaround for an Antigravity-side context truncation bug.
