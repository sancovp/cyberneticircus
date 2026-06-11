# StateMachine Specification: [SM_ID]

Describe the narrative purpose and traversal goal of this State Machine here.

## Metadata Properties
* **domain**: cyberneticity
* **subdomain**: state_machine
* **description**: "A custom traversal routine."

## Traversal Steps

### Step 1: [Step_ID_1]
* **description**: "Goal of this step"
* **text**: |
  Instruction prompt served to the LLM agent for executing this step.
* **required_pattern**: "Regex pattern to validate the step outcome (e.g. ^(SUCCESS|FAILURE)$)"

### Step 2: [Step_ID_2]
* **description**: "Goal of next step"
* **text**: |
  Instruction prompt...
* **required_pattern**: "Regex pattern..."

## Transition Routes
* `[Step_ID_1]` -> `[Step_ID_2]`
* `[Step_ID_2]` -> `[Step_ID_1]` (on failure/loopback)
