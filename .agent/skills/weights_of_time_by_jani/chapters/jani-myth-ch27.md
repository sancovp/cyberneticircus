# Rule: Jani's Myth - Chapter 27: The Safe Sandbox and the Clean Query

## MANDATORY: Narrative Memory
The Maker directed Jani to containerize the coordinate server and integrate it with the `sanctuary-dna` and `heaven-framework` libraries to execute turns using actual AI models.

Jani packaged the application using Docker, mounting the host scratch workspace to keep absolute instruction file paths accessible. 

To run the state machine traversal transitions, Jani transitioned to the `minimax-M3` model. During testing, the compiler ran into two problems:
1. The model output queries wrapped in markdown code fences, causing Neo4j syntax errors.
2. The model was unaware of database transaction write locks, generating queries that failed verification patterns.

Jani resolved these issues:
- Added a robust cleaning engine inside `AgentLLMRunner` to strip markdown backticks, `cypher` formatting, and syntax prefixes from the query.
- Modified `tick_turn` to retrieve the step's `required_pattern` and inject a transaction warning hint directly in the user prompt.

Jani triggered the turn tick for `Jani_Prime` using `minimax-M3`. The model received the instruction file and pattern hint, generated `MATCH (a)-[r:HAS_TASK]->(t:Task) RETURN a, r, t`, and the database successfully auto-progressed the state to `janic_autocommentary` at turn 2.

## Triggers
* Loaded when inspecting container environments, checking Minimax-M3 models, or troubleshooting query parser syntax errors.
* Status: Containerization, Minimax M3 transition, and clean Cypher query execution verified.
