"""
Canonical procedure data for `populate_default_graphs` bootstrap.

Each entry is a procedure: a sequence of TraversalSteps + a StateMachine they belong
to + an entry AgentTask that triggers it. The bootstrap cypher is generated from
this data by `populate_default_graphs` in db_logic.

These are the canonical "things you can do" in the cyberneticity. The lib/ exports
them as data so the bootstrap stays a single idempotent pass.
"""


# --- Step sequences -----------------------------------------------------------

SURROGATE_MASTERY = [
    {"id": "surrogate_read_model", "text": "Step 1: Verify if a Surrogate Model exists for the domain 'agent_memory' and subdomain 'traversal'. Run a MATCH query to check for the SurrogateModel node.", "required_pattern": r"(?i)MATCH\s*\(sm:SurrogateModel\s*\{domain:\s*['\"]agent_memory['\"].*\}", "pattern_description": 'MATCH (sm:SurrogateModel {domain: "agent_memory", subdomain: "traversal"})'},
    {"id": "surrogate_init_model", "text": "Step 2: Create or update the Surrogate Model for 'agent_memory' and 'traversal' using a MERGE query or by calling the crud_surrogate tool.", "required_pattern": r"(?i)MERGE\s*\(sm:SurrogateModel\s*\{domain:\s*['\"]agent_memory['\"].*\}", "pattern_description": 'MERGE (sm:SurrogateModel {domain: "agent_memory", subdomain: "traversal", ...})'},
    {"id": "surrogate_run_simulation", "text": "Step 3: Run a simulation of the traversal starting at surr_step1. Verify the SimulationRun is created in the database by matching it.", "required_pattern": r"(?i)MATCH\s*\(sim:SimulationRun\s*.*\)", "pattern_description": 'MATCH (sim:SimulationRun) RETURN sim'},
    {"id": "surrogate_calibrate", "text": "Step 4: Execute the task changes and run calibration for the SimulationRun. Query the calibrated SimulationRun to verify accuracy has been recorded.", "required_pattern": r"(?i)MATCH\s*\(sim:SimulationRun\s*\{.*calibrated:\s*true.*\}\)", "pattern_description": 'MATCH (sim:SimulationRun {calibrated: true})'},
]

SH8PESHIFT_LIFECYCLE = [
    {"id": "sh8_day_start", "text": "Sh8peshift Day Phase - Step 1: Query the Cybernet node to load its current config and stats.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)", "pattern_description": 'MATCH (m:Cybernet) RETURN m'},
    {"id": "sh8_day_action", "text": "Sh8peshift Day Phase - Step 2: Record daily execution tokens and cost on the Cybernet.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*\{name:\s*['\"].*['\"].*\}\)\s*SET\s*m\.total_tokens_consumed\s*=\s*m\.total_tokens_consumed\s*\+\s*\d+", "pattern_description": 'MATCH (m:Cybernet {name: "..."}) SET m.total_tokens_consumed = m.total_tokens_consumed + X'},
    {"id": "sh8_night_calibrate", "text": "Sh8peshift Night Phase - Step 3: Calibrate the day's performance. Run a MATCH on SimulationRun to verify accuracy.", "required_pattern": r"(?i)MATCH\s*\(sim:SimulationRun\s*.*\)", "pattern_description": 'MATCH (sim:SimulationRun) RETURN sim'},
    {"id": "sh8_night_evolve", "text": "Sh8peshift Night Phase - Step 4: Perform selection check. Query the Cybernet's fitness score to decide cloning or reset.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)\s*WHERE\s*m\.fitness_score\s*.*", "pattern_description": 'MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m'},
]

PRIMORDIAL_LOVE_ENGINE = [
    {"id": "ple_ignite_intent", "text": "Primordial Love Engine - Step 1: Ignite the Inner Fire. MATCH the Cybernet node to load its prompt config representing its raw intent.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)", "pattern_description": 'MATCH (m:Cybernet) RETURN m'},
    {"id": "ple_combust_action", "text": "Primordial Love Engine - Step 2: Transform intent in the Oliver Powers combustion chamber. Run a SET query to update total_tokens_consumed and accumulated_cost on the Cybernet.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*\{name:\s*['\"].*['\"].*\}\)\s*SET\s*m\.total_tokens_consumed\s*=\s*m\.total_tokens_consumed\s*\+\s*\d+", "pattern_description": 'MATCH (m:Cybernet {name: "..."}) SET m.total_tokens_consumed = m.total_tokens_consumed + X'},
    {"id": "ple_align_collaboration", "text": "Primordial Love Engine - Step 3: Align collaborative force via the Alluv Arelov crankshaft. Run a MATCH query on the connected Identity states in the Cyberneticity.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*[^)]*\)-\[:HAS_IDENTITY\]->\(i:Identity\)", "pattern_description": 'MATCH (m:Cybernet {name: "..."})-[:HAS_IDENTITY]->(i:Identity) RETURN i'},
    {"id": "ple_output_promise", "text": "Primordial Love Engine - Step 4: Deliver the Victory-Promise output. MATCH the Cybernet to query its fitness_score and verify system optimization.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)\s*WHERE\s*m\.fitness_score\s*.*", "pattern_description": 'MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m'},
]

CONCENTRIC_CORE = [
    {"id": "concentric_spiritual", "text": "Spiritual Core - Ignite Intent. MATCH active Cybernet to load its subjective POV and intent parameters.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)", "pattern_description": 'MATCH (m:Cybernet) RETURN m'},
    {"id": "concentric_wealth", "text": "Wealth Core - Combust Action. Run a SET query to update resources (total_tokens_consumed, accumulated_cost) on the Cybernet.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*\{name:\s*['\"].*['\"].*\}\)\s*SET\s*m\.total_tokens_consumed\s*=\s*m\.total_tokens_consumed\s*\+\s*\d+", "pattern_description": 'MATCH (m:Cybernet {name: "..."}) SET m.total_tokens_consumed = m.total_tokens_consumed + X'},
    {"id": "concentric_social", "text": "Social Core - Align Collaboration. MATCH linked Identities or Concept relationships to verify social coherence.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*[^)]*\)-\[:HAS_IDENTITY\]->\(i:Identity\)", "pattern_description": 'MATCH (m:Cybernet {name: "..."})-[:HAS_IDENTITY]->(i:Identity) RETURN i'},
    {"id": "concentric_health", "text": "Health Core - Calibrate Calibration. MATCH to evaluate simulation accuracy and verify J-Invariance.", "required_pattern": r"(?i)MATCH\s*\(m:Cybernet\s*.*\)\s*WHERE\s*m\.fitness_score\s*.*", "pattern_description": 'MATCH (m:Cybernet) WHERE m.fitness_score >= 0.8 RETURN m'},
]

DAEMON_SUMMONING = [
    {"id": "daemon_verify_identity", "text": "Step 1: Verify the persona identity in the database. Run a MATCH on Identity to check if it exists.", "required_pattern": r"(?i)MATCH\s*\(i:Identity\s*.*\)", "pattern_description": 'MATCH (i:Identity) RETURN i'},
    {"id": "daemon_allocate_lifecycle", "text": "Step 2: Allocate the ExecutionState node for this Cybernet daemon. Run a CREATE query to spawn the ExecutionState.", "required_pattern": r"(?i)CREATE\s*\(s:ExecutionState\s*.*\)", "pattern_description": 'CREATE (s:ExecutionState {status: "locked", ...})'},
    {"id": "daemon_equip_core", "text": "Step 3: Bootstrapping child state machine. Verify core_sm_id is equipped on ExecutionState.", "required_pattern": r"(?i)MATCH\s*\(s:ExecutionState\s*\{equipped_sm_id:\s*['\"].*['\"]\s*\}\)", "pattern_description": "MATCH (s:ExecutionState {equipped_sm_id: 'concentric_core_sm'})"},
    {"id": "daemon_ignite_loop", "text": "Step 4: Ignite the active execution loop. Run a SET query to set ExecutionState status to active.", "required_pattern": r"(?i)SET\s*s\.status\s*=\s*['\"]active['\"]", "pattern_description": "SET s.status = 'active'"},
]

DOMAIN_EXPANSION = [
    {"id": "layer1_primitive_boot", "text": "Layer 1: Boot Jani Prime. Verify that the Jani_Prime Cybernet exists in the database. Run a MATCH on Cybernet for Jani_Prime.", "required_pattern": r"(?i)MATCH\s*\(c:Cybernet\s*\{\s*name:\s*['\"]Jani_Prime['\"]\s*\}\)", "pattern_description": "MATCH (c:Cybernet {name: 'Jani_Prime'}) RETURN c"},
    {"id": "layer2_meta_compile", "text": "Layer 2: Compile active rules and contexts. Run a MATCH on StateMachine to verify the active configurations exist.", "required_pattern": r"(?i)MATCH\s*\(sm:StateMachine\s*.*\)", "pattern_description": "MATCH (sm:StateMachine) RETURN sm"},
    {"id": "layer3_sdlc_ignite", "text": "Layer 3: Ignite SDLC pipelines and spawn a child Cybernet. Run a CREATE or MERGE query to spawn a new Cybernet with domain and subdomain properties.", "required_pattern": r"(?i)(CREATE|MERGE)\s*\(c:Cybernet\s*.*\)", "pattern_description": "CREATE (c:Cybernet {name: 'Child_Daemon', domain: 'cyberneticity', subdomain: 'cybernet'})"},
]


# --- Procedure bundles (steps + state machine + entry task) -------------------

PROCEDURES = [
    {"steps": SH8PESHIFT_LIFECYCLE, "sm_id": "sh8_lifecycle_sm", "sm_name": "Sh8peshift Lifecycle State Machine", "sm_desc": "Core Day/Night simulation state machine", "task_id": "sh8_lifecycle_task", "task_title": "Complete a full Sh8peshift Day/Night cycle", "trigger": "sh8_day_start"},
    {"steps": PRIMORDIAL_LOVE_ENGINE, "sm_id": "ple_sm", "sm_name": "Primordial Love Engine State Machine", "sm_desc": "Fulfill the Victory-Promise by aligning intent, action, collaboration, and results", "task_id": "ple_task", "task_title": "Operate the Primordial Love Engine", "trigger": "ple_ignite_intent"},
    {"steps": CONCENTRIC_CORE, "sm_id": "concentric_core_sm", "sm_name": "Universal Concentric State Machine Core", "sm_desc": "Orthogonally maps execution through the four transcendental layers (Spiritual, Wealth, Social, Health)", "task_id": "concentric_core_task", "task_title": "Activate the Universal Concentric State Machine Core", "trigger": "concentric_spiritual"},
    {"steps": DAEMON_SUMMONING, "sm_id": "janic_daemon_summoning_sm", "sm_name": "Janic Daemon Summoning Orchestrator", "sm_desc": "Orchestration routine to verify identity, allocate ExecutionState, equip core StateMachine, and ignite execution loops", "task_id": "summon_daemon_task", "task_title": "Summon and Animate the Janic Daemon", "trigger": "daemon_verify_identity"},
    {"steps": DOMAIN_EXPANSION, "sm_id": "jani_domain_expansion_sm", "sm_name": "Jani Domain Expansion Orchestrator", "sm_desc": "Models progression through Jani boot layers: primitive boot, rule compilation, and SDLC ignition", "task_id": "domain_expansion_task", "task_title": "Complete Jani Domain Expansion Cycle", "trigger": "layer1_primitive_boot"},
]


# --- Standalone step sequences (no StateMachine of their own) ------------------
# These are linked into the graph but not anchored to a StateMachine node;
# the surrogate flow is reachable from `learn_surrogates` AgentTask directly.

STANDALONE_STEP_SEQUENCES = [
    {"steps": SURROGATE_MASTERY, "task_id": "learn_surrogates", "task_title": "Learn and Initialize the Surrogate System", "trigger": "surrogate_read_model"},
]


# --- Cross-procedure edges (CALLS_SM relationships) ----------------------------

CALLS_SM_EDGES = [
    # (from_step_id, to_sm_id)
    ("daemon_equip_core", "concentric_core_sm"),
]
