// STAGED BANISHMENT — Primordial Love Engine (Sanctuary-System contamination, see provenance rule + Vol II ch31)
// Verified before staging (2026-06-12): no ExecutionState references ple_sm or any ple_* step.
//
// Dry-run first (counts what will be deleted):
//   MATCH (sm:StateMachine {id: 'ple_sm'})
//   OPTIONAL MATCH (sm)-[:HAS_STEP]->(s:TraversalStep)
//   RETURN sm.id, count(s) AS steps;   // expect: ple_sm, 4
//
// The banishment (run via /api/query or cypher-shell, with the Maker's approval):

MATCH (sm:StateMachine {id: 'ple_sm'})
OPTIONAL MATCH (sm)-[:HAS_STEP]->(s:TraversalStep)
DETACH DELETE sm, s;

// Post-check (expect zero rows):
//   MATCH (n) WHERE n.id IN ['ple_sm','ple_ignite_intent','ple_combust_action','ple_align_collaboration','ple_output_promise'] RETURN n;
