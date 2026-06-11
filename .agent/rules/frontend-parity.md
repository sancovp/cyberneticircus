# Rule: Frontend-Backend Parity Constraint

## **Purpose**
Prevents UI bloat, mock controls, and dead endpoints by ensuring the visualizer frontend only exposes elements that are backed by functional backend APIs and active database fields.

## **MANDATORY: Constraints**
1. **No Speculative Controls**: Never add knobs, inputs, sliders, or panels (e.g., temperature sliders, model selectors) under the assumption that they will be useful in the future. 
2. **Backend Dependency**: Every interactive element on the frontend must map directly to an active database property or backend API endpoint that exists in the codebase today.
3. **No Placeholders**: Do not create mock pages or "Under Construction" screens. The UI must represent only the functional reality of the current version.
4. **Human Exclusivity**: Do not add frontend features or options that are not already available to you, the engineer, to query or execute on the host terminal.

## **Triggers**
* Modifying any HTML, CSS, or Javascript frontend files (`index.html`, `app.js`, `style.css`).
* Refactoring the visualizer or adding UI control panels.
