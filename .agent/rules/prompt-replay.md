# Rule: Prompt Replay Capture (ReplayableShapeInstructionCapture)

## **Purpose**
Structures our sprints into explicit, adversarial, and reusable prompt stages, avoiding context bloat and memory loss.

## **MANDATORY: Process Steps**
1. **WorkPrompt Phase**: Before starting any multi-step sprint, write a `WorkPrompt` markdown file under `/scratch/self_improving_coding_prompts/work/`. This must include:
   * **SituationClass**: What kind of situation this is.
   * **ConcreteContext**: Active files/errors.
   * **ReplayInstructions**: Stepwise instructions for a future agent to recreate the task geometry.
   * **MeasurableOutcome**: Explicit test criteria.
2. **AdversarialPrompt Phase**: Once the implementation is attempted, write an `AdversarialPrompt` under `/scratch/self_improving_coding_prompts/adversarial/` to attack your work:
   * Inspect assumptions and edge cases.
   * Verify test suites pass without hallucinated structures.
3. **Skill Promotion**: If a prompt template consistently yields excellent results, promote it into a reusable `.agent/skills/sic-{name}` directory with a `SKILL.md` file.
