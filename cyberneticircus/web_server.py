#!/usr/bin/env python3
"""
FastAPI Backend for CybernetiCircus RPG.
Exposes REST endpoints to query and execute Cybernet identities and ticks.
Also hosts the API layer forwarding MCP proxy calls to the shared db_logic.
"""
import os
import sys
import re
import json
import math
import random
import uuid
import logging
import subprocess
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from neo4j.exceptions import Neo4jError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cyberneticircus_web_server")

# Ensure local dir is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from engine import CybernetiCircusCompiler, AgentLLMRunner
from db_logic import (
    get_driver,
    populate_default_graphs,
    query_database,
    get_schema,
    progress_traversal,
    adjust_transition_weight_internal,
    serialize_value,
    validate_cypher_query
)

app = FastAPI(title="CybernetiCircus Compiler API")

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

# Pydantic Requests for endpoints
class CreateCybernetRequest(BaseModel):
    name: str
    description: str
    model_name: str = "gemini-1.5-pro"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    mutation_rate: float = 0.1
    selection_pressure: float = 1.0

class EquipRequest(BaseModel):
    character_name: str
    state_machine_id: str

class TickRequest(BaseModel):
    character_name: str
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None

class QueryRequest(BaseModel):
    query: str
    parameters: Optional[Dict[str, Any]] = None

class ProgressRequest(BaseModel):
    answer: Optional[str] = None

class CreateFlowRequest(BaseModel):
    steps: List[Dict[str, Any]]
    trigger_node_label: Optional[str] = None
    trigger_node_properties: Optional[Dict[str, Any]] = None

class CreateTransitionRequest(BaseModel):
    from_step_id: str
    to_step_id: str
    weight: float = 1.0
    description: str = ""

class AdjustWeightRequest(BaseModel):
    from_step_id: str
    to_step_id: str
    success: bool

class CrudSurrogateRequest(BaseModel):
    action: str
    parameters: Optional[Dict[str, Any]] = None

class CrudStateMachineCallsRequest(BaseModel):
    action: str
    from_step_id: str
    to_state_machine_id: str

class ConfigureGhostShellRequest(BaseModel):
    cybernet_name: str
    model_name: Optional[str] = None
    parameters_count: Optional[float] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None

class ExecuteHostCommandRequest(BaseModel):
    command: str

# Real-time Agent Operations Trace logs & Focus tracking
agent_trace_logs = []
active_focus_nodes = set()
active_focus_labels = set()
active_cybernet = ""

def log_agent_action(log_type: str, text: str, focus_nodes: Optional[List[str]] = None, focus_labels: Optional[List[str]] = None):
    """Log an agent action and update the visualizer's focal points."""
    global agent_trace_logs, active_focus_nodes, active_focus_labels, active_cybernet
    
    # Keep logs size capped at 100 entries to prevent memory leak
    if len(agent_trace_logs) > 100:
        agent_trace_logs.pop(0)
        
    agent_trace_logs.append({
        "type": log_type,
        "text": text
    })
    
    # Update active focus targets
    if focus_nodes is not None:
        active_focus_nodes = set(focus_nodes)
    if focus_labels is not None:
        active_focus_labels = set(focus_labels)
        
    # Auto-track the focused Cybernet character
    if focus_labels is not None and "Cybernet" in focus_labels and focus_nodes:
        active_cybernet = focus_nodes[0]

def extract_nodes_from_results(results: Any):
    """Scan query results to extract names and labels for visual highlighting."""
    nodes_found = set()
    labels_found = set()
    
    def scan(val):
        global active_cybernet
        if isinstance(val, dict):
            # Check if this represents a serialized node
            if "labels" in val and "properties" in val:
                props = val["properties"]
                if "name" in props:
                    nodes_found.add(str(props["name"]))
                    if "Cybernet" in val["labels"]:
                        active_cybernet = str(props["name"])
                if "id" in props:
                    nodes_found.add(str(props["id"]))
                # Also check standard key fields
                for k in ("title", "run_id", "sm_id", "id"):
                    if k in props:
                        nodes_found.add(str(props[k]))
                for lbl in val["labels"]:
                    labels_found.add(str(lbl))
            else:
                for k, v in val.items():
                    scan(v)
        elif isinstance(val, list):
            for item in val:
                scan(item)
                
    try:
        scan(results)
    except Exception as e:
        logger.error(f"Error scanning results for focus nodes: {e}")
        
    return list(nodes_found), list(labels_found)

# Existing endpoints
@app.get("/", response_class=HTMLResponse)
def get_index():
    index_path = os.path.join(current_dir, "static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("index.html not found. Ensure static files are generated in /static/.", status_code=404)

@app.get("/api/list")
def list_cybernets():
    compiler = CybernetiCircusCompiler()
    try:
        with compiler.driver.session() as session:
            res = session.run("MATCH (m:Cybernet) RETURN m.name as name ORDER BY name")
            names = [r["name"] for r in res]
        return {"cybernets": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        compiler.close()

@app.get("/api/state_machines")
def list_state_machines():
    compiler = CybernetiCircusCompiler()
    try:
        with compiler.driver.session() as session:
            res = session.run("MATCH (sm:StateMachine) RETURN sm.id as id, sm.name as name ORDER BY name")
            machines = [{"id": r["id"], "name": r["name"]} for r in res]
        return {"state_machines": machines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        compiler.close()

@app.get("/api/status/{name}")
def get_status(name: str):
    compiler = CybernetiCircusCompiler()
    try:
        status = compiler.get_character_status(name)
        if not status:
            raise HTTPException(status_code=404, detail=f"Cybernet Identity '{name}' not found.")
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        compiler.close()

@app.get("/api/simulations/{name}")
def get_simulations(name: str):
    compiler = CybernetiCircusCompiler()
    try:
        with compiler.driver.session() as session:
            res = session.run(
                """
                MATCH (m:Cybernet {name: $name})-[:HAS_SIMULATION]->(sim:SimulationRun)
                RETURN sim.run_id as run_id, sim.accuracy as accuracy, sim.created_at as created_at
                ORDER BY sim.created_at DESC LIMIT 5
                """,
                {"name": name}
            )
            sims = []
            for r in res:
                sims.append({
                    "run_id": r["run_id"],
                    "accuracy": r["accuracy"],
                    "created_at": r["created_at"]
                })
        return {"simulations": sims}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        compiler.close()

def serialize_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
    serialized = {}
    for k, v in properties.items():
        if hasattr(v, "isoformat"):
            serialized[k] = v.isoformat()
        elif hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
            serialized[k] = str(v)
        else:
            try:
                json.dumps(v)
                serialized[k] = v
            except TypeError:
                serialized[k] = str(v)
    return serialized

@app.get("/api/graph")
def get_graph(name: Optional[str] = None):
    compiler = CybernetiCircusCompiler()
    try:
        nodes = []
        links = []
        node_ids = set()
        
        current_step_node_id = None
        active_cybernet_node_id = None
        equipped_sm_node_id = None
        
        if name:
            with compiler.driver.session() as session:
                res = session.run(
                    """
                    MATCH (m:Cybernet {name: $name})
                    OPTIONAL MATCH (m)-[:HAS_LIFECYCLE]->(s:Identity)
                    OPTIONAL MATCH (s)-[:CURRENT_STEP]->(curr:TraversalStep)
                    OPTIONAL MATCH (m)-[:EQUIPS]->(sm:StateMachine)
                    RETURN id(m) as m_id, id(curr) as curr_id, id(sm) as sm_id
                    """,
                    {"name": name}
                )
                rec = res.single()
                if rec:
                    active_cybernet_node_id = str(rec["m_id"]) if rec["m_id"] is not None else None
                    current_step_node_id = str(rec["curr_id"]) if rec["curr_id"] is not None else None
                    equipped_sm_node_id = str(rec["sm_id"]) if rec["sm_id"] is not None else None
        
        def get_node_id(node):
            if hasattr(node, 'id') and node.id is not None:
                return str(node.id)
            if hasattr(node, 'element_id') and node.element_id is not None:
                return str(node.element_id)
            return str(hash(node))
            
        def add_node(node):
            if not node:
                return None
            nid = get_node_id(node)
            if nid not in node_ids:
                node_ids.add(nid)
                labels = list(node.labels)
                label = labels[0] if labels else "Unknown"
                display_name = node.get("name") or node.get("id") or node.get("run_id") or label
                
                is_active = False
                if nid == active_cybernet_node_id:
                    is_active = "cybernet"
                elif nid == current_step_node_id:
                    is_active = "step"
                elif nid == equipped_sm_node_id:
                    is_active = "state_machine"
                    
                is_highlighted = (
                    display_name in active_focus_nodes or 
                    nid in active_focus_nodes or 
                    label in active_focus_labels or
                    any(lbl in active_focus_labels for lbl in labels)
                )
                    
                nodes.append({
                    "id": nid,
                    "label": label,
                    "name": display_name,
                    "properties": serialize_properties(dict(node)),
                    "active_tag": is_active,
                    "highlighted": is_highlighted
                })
            return nid

        with compiler.driver.session() as session:
            if name:
                # Query only nodes and relationships connected to the active Cybernet using optimized step-by-step collects to prevent memory out-of-memory errors
                res = session.run(
                    """
                    MATCH (c:Cybernet {name: $name})
                    WITH c
                    OPTIONAL MATCH (c)-[:HAS_LIFECYCLE]->(i:Identity)
                    WITH c, i
                    OPTIONAL MATCH (i)-[:CURRENT_STEP]->(curr:TraversalStep)
                    WITH c, i, curr
                    OPTIONAL MATCH (c)-[:EQUIPS]->(sm:StateMachine)
                    WITH c, i, curr, sm
                    OPTIONAL MATCH (sm)-[:INITIAL_STATE|TRANSITION_TO|ON_STATE*0..5]->(sms)
                    WITH c, i, curr, sm, collect(DISTINCT sms) as sms_list
                    OPTIONAL MATCH (c)-[:HAS_MIND_PALACE]->(root_c:Concept)
                    WITH c, i, curr, sm, sms_list, root_c
                    OPTIONAL MATCH (root_c)-[:SUB_CONCEPT*0..5]->(con:Concept)
                    WITH c, i, curr, sm, sms_list, collect(DISTINCT con) as con_list
                    OPTIONAL MATCH (c)-[:EQUIPS_SKILL]->(sk:Skill)
                    WITH c, i, curr, sm, sms_list, con_list, collect(DISTINCT sk) as sk_list
                    OPTIONAL MATCH (c)-[:HAS_SIMULATION]->(sim:SimulationRun)
                    WITH c, i, curr, sm, sms_list, con_list, sk_list, collect(DISTINCT sim) as sim_list
                    OPTIONAL MATCH (i)-[:HAS_TRACE_HISTORY]->(t1:ExecutionTrace)-[:NEXT_TRACE*0..1000]->(tr:ExecutionTrace)
                    WITH c, i, curr, sm, sms_list, con_list, sk_list, sim_list, collect(DISTINCT tr) as tr_list
                    
                    WITH [c] + [i] + [curr] + [sm] + sms_list + con_list + sk_list + sim_list + tr_list as all_nodes_raw
                    UNWIND all_nodes_raw as n
                    WITH n WHERE n IS NOT NULL
                    WITH collect(DISTINCT n) as all_nodes
                    UNWIND all_nodes as n
                    OPTIONAL MATCH (n)-[r]->(m)
                    WHERE m IN all_nodes
                    RETURN n, r, m
                    """,
                    {"name": name}
                )
            else:
                # Query only game nodes and relationships to build the total game graph
                res = session.run(
                    """
                    MATCH (n)
                    WHERE n:Cybernet OR n:Identity OR n:StateMachine OR n:TraversalStep OR n:TraversalState OR n:SimulationRun
                    WITH collect(DISTINCT n) as all_nodes
                    UNWIND all_nodes as n
                    WITH DISTINCT n, all_nodes
                    OPTIONAL MATCH (n)-[r]->(m)
                    WHERE m IN all_nodes
                    RETURN n, r, m
                    """
                )
            for record in res:
                n_node = record["n"]
                m_node = record["m"]
                rel = record["r"]
                
                n_id = add_node(n_node)
                m_id = add_node(m_node)
                
                if rel is not None and n_id and m_id:
                    link_item = {"source": n_id, "target": m_id, "type": rel.type}
                    if link_item not in links:
                        links.append(link_item)
                        
        return {"nodes": nodes, "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        compiler.close()

@app.get("/api/agent_logs")
def get_agent_logs():
    global active_cybernet
    current_active = active_cybernet
    active_step_id = None
    
    compiler = CybernetiCircusCompiler()
    try:
        with compiler.driver.session() as session:
            # 1. If we have an active cybernet in memory, check if it is still valid in the database
            if current_active:
                res = session.run(
                    "MATCH (c:Cybernet {name: $name}) RETURN c.name as name",
                    {"name": current_active}
                )
                if not res.single():
                    current_active = ""
                    
            # 2. If no active cybernet, try to find one that is currently traversing a step
            if not current_active:
                res = session.run(
                    """
                    MATCH (c:Cybernet)-[:HAS_LIFECYCLE]->(i:Identity)-[:CURRENT_STEP]->(curr:TraversalStep)
                    RETURN c.name as name
                    LIMIT 1
                    """
                )
                rec = res.single()
                if rec:
                    current_active = rec["name"]
                    active_cybernet = current_active
                    
            # 3. Fallback if still nothing: get the most active Cybernet in the database
            if not current_active:
                res_fallback = session.run(
                    """
                    MATCH (c:Cybernet) 
                    OPTIONAL MATCH (c)-[:HAS_LIFECYCLE]->(i:Identity)-[:HAS_TRACE_HISTORY]->(t:ExecutionTrace) 
                    WITH c, count(t) as traces_count 
                    RETURN c.name as name 
                    ORDER BY traces_count DESC 
                    LIMIT 1
                    """
                )
                rec_fallback = res_fallback.single()
                if rec_fallback:
                    current_active = rec_fallback["name"]
                    active_cybernet = current_active
                    
            # 4. Fetch the active step ID for the active Cybernet
            if current_active:
                res_step = session.run(
                    """
                    MATCH (c:Cybernet {name: $name})-[:HAS_LIFECYCLE]->(i:Identity)-[:CURRENT_STEP]->(curr:TraversalStep)
                    RETURN id(curr) as curr_id
                    """,
                    {"name": current_active}
                )
                rec_step = res_step.single()
                if rec_step:
                    active_step_id = str(rec_step["curr_id"])
    except Exception:
        pass
    finally:
        compiler.close()
        
    return {
        "logs": agent_trace_logs,
        "active_cybernet": current_active,
        "active_step_id": active_step_id,
        "active_focus_nodes": list(active_focus_nodes),
        "active_focus_labels": list(active_focus_labels)
    }

@app.post("/api/create")
def create_cybernet(req: CreateCybernetRequest):
    compiler = CybernetiCircusCompiler()
    try:
        msg = compiler.create_cybernet(
            name=req.name,
            description=req.description,
            model_name=req.model_name,
            parameters_count=70.0,
            temperature=req.temperature,
            top_p=req.top_p,
            max_tokens=req.max_tokens,
            mutation_rate=req.mutation_rate,
            selection_pressure=req.selection_pressure
        )
        log_agent_action("success", f"Compiled and spawned Cybernet Core '{req.name}'", [req.name], ["Cybernet"])
        return {"message": msg}
    except Exception as e:
        log_agent_action("error", f"Spawn failed for '{req.name}': {e}", [], [])
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        compiler.close()

@app.post("/api/equip")
def equip_state_machine(req: EquipRequest):
    compiler = CybernetiCircusCompiler()
    try:
        msg = compiler.equip_state_machine(req.character_name, req.state_machine_id)
        log_agent_action("success", f"Equipped State Machine '{req.state_machine_id}' onto '{req.character_name}'", [req.character_name, req.state_machine_id], ["Cybernet", "StateMachine"])
        return {"message": msg}
    except Exception as e:
        log_agent_action("error", f"Equip failed for '{req.character_name}': {e}", [req.character_name], ["Cybernet"])
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        compiler.close()

@app.post("/api/tick")
def tick_turn(req: TickRequest):
    compiler = CybernetiCircusCompiler()
    try:
        status = compiler.get_character_status(req.character_name)
        if not status:
            raise HTTPException(status_code=404, detail=f"Cybernet Identity '{req.character_name}' not found.")
        
        run_model = req.model_name or status["model_name"]
        run_temp = req.temperature if req.temperature is not None else status["temperature"]
        run_top_p = req.top_p if req.top_p is not None else status["top_p"]
        
        runner = AgentLLMRunner(
            model_name=run_model,
            temperature=run_temp,
            top_p=run_top_p,
            max_tokens=2048
        )
        
        res = compiler.tick_turn(req.character_name, runner)
        log_agent_action(
            "event",
            f"Ticked turn for '{req.character_name}'. Action: {res.get('action_taken')}. Event: {res.get('event_message')}",
            [req.character_name],
            ["Cybernet"]
        )
        return res
    except Exception as e:
        log_agent_action("error", f"Tick failed for '{req.character_name}': {e}", [req.character_name], ["Cybernet"])
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        compiler.close()

# Migrated MCP wrapper endpoints (delegating to db_logic)
@app.post("/api/query")
def query_database_api(req: QueryRequest):
    try:
        validate_cypher_query(req.query)
        res = query_database(req.query, req.parameters)
        
        # Scan results for highlights
        focus_nodes, focus_labels = extract_nodes_from_results(res)
        log_agent_action("action", f"Executed query: {req.query}", focus_nodes, focus_labels)
        
        return res
    except PermissionError as pe:
        log_agent_action("error", f"Security Policy Violation: {pe}", [], [])
        raise HTTPException(status_code=403, detail=str(pe))
    except Neo4jError as ne:
        msg = ne.message if hasattr(ne, 'message') else str(ne)
        log_agent_action("error", f"Neo4j Error: {msg}", [], [])
        raise HTTPException(status_code=400, detail=f"Neo4j Error: {msg}")
    except Exception as e:
        log_agent_action("error", f"Query failed: {e}", [], [])
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/traversal/progress")
def progress_traversal_api(req: ProgressRequest):
    try:
        msg = progress_traversal(req.answer)
        log_agent_action("action", f"Progressed active step. Answer: {req.answer}", [], ["TraversalStep"])
        return {"message": msg}
    except Exception as e:
        log_agent_action("error", f"Traversal progress failed: {e}", [], ["TraversalStep"])
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schema")
def get_schema_api():
    try:
        log_agent_action("system", "Scanned database schema", [], [])
        return get_schema()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/file/read")
def read_file_api(path: str):
    # Security: enforce that the file must be within the scratch workspace
    allowed_prefix = "/Users/isaacwr/.gemini/antigravity/scratch"
    normalized_path = os.path.abspath(path)
    if not normalized_path.startswith(allowed_prefix):
        raise HTTPException(status_code=403, detail="Access denied: file path is outside the allowed workspace.")
    
    if not os.path.exists(normalized_path):
        raise HTTPException(status_code=404, detail="File not found.")
        
    try:
        with open(normalized_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/traversal/create_flow")
def create_traversal_flow_api(req: CreateFlowRequest):
    if not req.steps:
        raise HTTPException(status_code=400, detail="At least one step is required.")
    for i, step in enumerate(req.steps):
        if "id" not in step or not step["id"]:
            raise HTTPException(status_code=400, detail=f"Step at index {i} missing 'id'.")
        if "text" not in step or not step["text"]:
            raise HTTPException(status_code=400, detail=f"Step at index {i} missing 'text'.")
        pattern = step.get("required_pattern")
        if pattern:
            try:
                re.compile(pattern)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid regex in step '{step['id']}': {e}")
                
    driver = get_driver()
    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                for step in req.steps:
                    tx.run(
                        """
                        MERGE (step:TraversalStep {id: $id})
                        SET step.text = $text,
                            step.required_pattern = $required_pattern,
                            step.pattern_description = $pattern_description
                        """,
                        {
                            "id": step["id"],
                            "text": step["text"],
                            "required_pattern": step.get("required_pattern"),
                            "pattern_description": step.get("pattern_description")
                        }
                    )
                for i in range(len(req.steps) - 1):
                    tx.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})
                        MATCH (next:TraversalStep {id: $next_id})
                        MERGE (curr)-[r:NEXT_STEP]->(next)
                        ON CREATE SET r.weight = 1.0, r.description = $desc
                        """,
                        {
                            "curr_id": req.steps[i]["id"],
                            "next_id": req.steps[i+1]["id"],
                            "desc": f"Transition from {req.steps[i]['id']} to {req.steps[i+1]['id']}"
                        }
                    )
                trigger_msg = ""
                if req.trigger_node_label and req.trigger_node_properties:
                    props_filter = "{" + ", ".join([f"{k}: ${k}" for k in req.trigger_node_properties.keys()]) + "}"
                    query_trigger = f"""
                    MATCH (n:{req.trigger_node_label} {props_filter})
                    SET n.trigger_traversal = $trigger_step_id
                    RETURN count(n) as count
                    """
                    params = dict(req.trigger_node_properties)
                    params["trigger_step_id"] = req.steps[0]["id"]
                    t_res = tx.run(query_trigger, params)
                    count = t_res.single()["count"]
                    if count == 0:
                        trigger_msg = f" (Warning: No matching {req.trigger_node_label} node found)"
                    else:
                        trigger_msg = f" (Successfully attached trigger to {count} node(s))"
        step_ids = [s["id"] for s in req.steps]
        log_agent_action("success", f"Created Traversal Flow with steps: {', '.join(step_ids)}{trigger_msg}", step_ids, ["TraversalStep"])
        return {"message": f"Successfully created traversal flow with {len(req.steps)} steps.{trigger_msg}"}
    except Exception as e:
        log_agent_action("error", f"Failed to create traversal flow: {e}", [], [])
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/traversal/create_transition")
def create_weighted_transition_api(req: CreateTransitionRequest):
    driver = get_driver()
    try:
        with driver.session() as session:
            res_from = session.run("MATCH (s:TraversalStep {id: $id}) RETURN count(s) as count", {"id": req.from_step_id})
            if res_from.single()["count"] == 0:
                raise HTTPException(status_code=400, detail=f"Source step '{req.from_step_id}' does not exist.")
            res_to = session.run("MATCH (s:TraversalStep {id: $id}) RETURN count(s) as count", {"id": req.to_step_id})
            if res_to.single()["count"] == 0:
                raise HTTPException(status_code=400, detail=f"Target step '{req.to_step_id}' does not exist.")
            session.run(
                """
                MATCH (from:TraversalStep {id: $from_id})
                MATCH (to:TraversalStep {id: $to_id})
                MERGE (from)-[r:NEXT_STEP]->(to)
                SET r.weight = $weight, r.description = $description
                """,
                {
                    "from_id": req.from_step_id,
                    "to_id": req.to_step_id,
                    "weight": float(req.weight),
                    "description": req.description
                }
            )
        log_agent_action("success", f"Created transition from '{req.from_step_id}' to '{req.to_step_id}' (weight {req.weight})", [req.from_step_id, req.to_step_id], ["TraversalStep"])
        return {"message": f"Successfully created transition from '{req.from_step_id}' to '{req.to_step_id}' with weight {req.weight}."}
    except Exception as e:
        log_agent_action("error", f"Failed to create transition: {e}", [req.from_step_id, req.to_step_id], ["TraversalStep"])
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/traversal/adjust_weight")
def adjust_transition_weight_api(req: AdjustWeightRequest):
    try:
        msg = adjust_transition_weight_internal(req.from_step_id, req.to_step_id, req.success)
        log_agent_action("success", f"Adjusted transition weight between '{req.from_step_id}' and '{req.to_step_id}' (success: {req.success})", [req.from_step_id, req.to_step_id], ["TraversalStep"])
        return {"message": msg}
    except Exception as e:
        log_agent_action("error", f"Failed to adjust transition weight: {e}", [req.from_step_id, req.to_step_id], ["TraversalStep"])
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crud_surrogate")
def crud_surrogate_api(req: CrudSurrogateRequest):
    action = req.action.lower()
    params = req.parameters or {}
    driver = get_driver()
    
    if action in ('create', 'update'):
        domain = params.get("domain")
        subdomain = params.get("subdomain")
        if not domain or not subdomain:
            raise HTTPException(status_code=400, detail="domain and subdomain parameters are required.")
        mutation_rate = float(params.get("mutation_rate", 0.1))
        selection_pressure = float(params.get("selection_pressure", 1.0))
        reward_weights = params.get("reward_weights", {"accuracy": 1.0})
        reward_weights_str = json.dumps(reward_weights)
        try:
            with driver.session() as session:
                session.run(
                    """
                    MERGE (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
                    SET sm.mutation_rate = $mutation_rate,
                        sm.selection_pressure = $selection_pressure,
                        sm.reward_weights = $reward_weights
                    """,
                    {
                        "domain": domain,
                        "subdomain": subdomain,
                        "mutation_rate": mutation_rate,
                        "selection_pressure": selection_pressure,
                        "reward_weights": reward_weights_str
                    }
                )
            log_agent_action("success", f"Saved SurrogateModel for {domain}/{subdomain}.", [f"SurrogateModel:{domain}/{subdomain}"], ["SurrogateModel"])
            return {"message": f"Successfully saved SurrogateModel for {domain}/{subdomain}."}
        except Exception as e:
            log_agent_action("error", f"Failed to save SurrogateModel for {domain}/{subdomain}: {e}", [], ["SurrogateModel"])
            raise HTTPException(status_code=500, detail=str(e))
            
    elif action == 'read':
        domain = params.get("domain")
        subdomain = params.get("subdomain")
        if not domain or not subdomain:
            raise HTTPException(status_code=400, detail="domain and subdomain parameters are required.")
        try:
            with driver.session() as session:
                res = session.run(
                    """
                    MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
                    RETURN sm.mutation_rate as mutation_rate,
                           sm.selection_pressure as selection_pressure,
                           sm.reward_weights as reward_weights
                    """,
                    {"domain": domain, "subdomain": subdomain}
                )
                record = res.single()
                if not record:
                    return {}
                reward_weights = json.loads(record["reward_weights"]) if record["reward_weights"] else {}
                sims_res = session.run(
                    """
                    MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})-[:HAS_SIMULATION]->(sim:SimulationRun)
                    RETURN sim.run_id as run_id, sim.fitness_score as fitness_score, 
                           sim.outcome_class as outcome_class, sim.calibrated as calibrated,
                           sim.accuracy as accuracy
                    ORDER BY sim.created_at DESC LIMIT 10
                    """,
                    {"domain": domain, "subdomain": subdomain}
                )
                simulations = []
                for s in sims_res:
                    simulations.append({
                        "run_id": s["run_id"],
                        "fitness_score": s["fitness_score"],
                        "outcome_class": s["outcome_class"],
                        "calibrated": s["calibrated"],
                        "accuracy": s["accuracy"]
                    })
                log_agent_action("system", f"Read SurrogateModel for {domain}/{subdomain}.", [f"SurrogateModel:{domain}/{subdomain}"], ["SurrogateModel"])
                return {
                    "domain": domain,
                    "subdomain": subdomain,
                    "mutation_rate": record["mutation_rate"],
                    "selection_pressure": record["selection_pressure"],
                    "reward_weights": reward_weights,
                    "recent_simulations": simulations
                }
        except Exception as e:
            log_agent_action("error", f"Failed to read SurrogateModel for {domain}/{subdomain}: {e}", [], ["SurrogateModel"])
            raise HTTPException(status_code=500, detail=str(e))
            
    elif action == 'delete':
        domain = params.get("domain")
        subdomain = params.get("subdomain")
        if not domain or not subdomain:
            raise HTTPException(status_code=400, detail="domain and subdomain parameters are required.")
        try:
            with driver.session() as session:
                session.run(
                    """
                    MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
                    OPTIONAL MATCH (sm)-[:HAS_SIMULATION]->(sim:SimulationRun)
                    OPTIONAL MATCH (sim)-[:PREDICTS_STATE]->(pn:PredictionNode)
                    DETACH DELETE sm, sim, pn
                    """,
                    {"domain": domain, "subdomain": subdomain}
                )
            log_agent_action("success", f"Deleted SurrogateModel for {domain}/{subdomain}.", [], ["SurrogateModel"])
            return {"message": f"Successfully deleted SurrogateModel for {domain}/{subdomain}."}
        except Exception as e:
            log_agent_action("error", f"Failed to delete SurrogateModel for {domain}/{subdomain}: {e}", [], ["SurrogateModel"])
            raise HTTPException(status_code=500, detail=str(e))
            
    elif action == 'simulate':
        domain = params.get("domain")
        subdomain = params.get("subdomain")
        start_step_id = params.get("start_step_id")
        steps_limit = int(params.get("steps_limit", 5))
        if not domain or not subdomain or not start_step_id:
            raise HTTPException(status_code=400, detail="domain, subdomain, and start_step_id are required.")
        try:
            model_info = crud_surrogate_api(CrudSurrogateRequest(action="read", parameters={"domain": domain, "subdomain": subdomain}))
            if model_info:
                mutation_rate = model_info.get("mutation_rate", 0.1)
                selection_pressure = model_info.get("selection_pressure", 1.0)
                reward_weights = model_info.get("reward_weights", {"accuracy": 1.0})
            else:
                mutation_rate = 0.1
                selection_pressure = 1.0
                reward_weights = {"accuracy": 1.0}
            path = []
            expected_diffs = []
            total_fitness = 0.0
            curr_id = start_step_id
            
            with driver.session() as session:
                for step_idx in range(steps_limit):
                    step_res = session.run(
                        "MATCH (s:TraversalStep {id: $id}) RETURN s.text as text, s.expected_diff as expected_diff, s.expected_fitness as expected_fitness",
                        {"id": curr_id}
                    )
                    step_rec = step_res.single()
                    if not step_rec:
                        break
                    path.append(curr_id)
                    diff_val = json.loads(step_rec["expected_diff"]) if step_rec["expected_diff"] else {}
                    expected_diffs.append(diff_val)
                    total_fitness += float(step_rec["expected_fitness"] or 0.0)
                    trans_res = session.run(
                        """
                        MATCH (curr:TraversalStep {id: $curr_id})-[r:NEXT_STEP]->(next:TraversalStep)
                        RETURN next.id as id, coalesce(r.weight, 1.0) as weight
                        """,
                        {"curr_id": curr_id}
                    )
                    transitions = [{"id": tr["id"], "weight": tr["weight"]} for tr in trans_res]
                    if not transitions:
                        break
                    exps = [math.exp(tr["weight"] * selection_pressure) for tr in transitions]
                    sum_exps = sum(exps)
                    probs = [val / sum_exps for val in exps] if sum_exps > 0 else [1.0 / len(transitions)] * len(transitions)
                    if random.random() < mutation_rate:
                        chosen_tr = random.choice(transitions)
                    else:
                        chosen_tr = random.choices(transitions, weights=probs)[0]
                    curr_id = chosen_tr["id"]
                    
                run_id = str(uuid.uuid4())
                outcome_class = "SUCCESS" if total_fitness >= 1.0 else "PENDING"
                session.run(
                    """
                    MATCH (sm:SurrogateModel {domain: $domain, subdomain: $subdomain})
                    CREATE (sim:SimulationRun {
                        run_id: $run_id,
                        created_at: timestamp(),
                        fitness_score: $fitness_score,
                        outcome_class: $outcome_class,
                        calibrated: false
                    })
                    CREATE (sm)-[:HAS_SIMULATION]->(sim)
                    """,
                    {
                        "domain": domain,
                        "subdomain": subdomain,
                        "run_id": run_id,
                        "fitness_score": total_fitness,
                        "outcome_class": outcome_class
                    }
                )
                for i, step_id in enumerate(path):
                    diff_str = json.dumps(expected_diffs[i])
                    session.run(
                        """
                        MATCH (sim:SimulationRun {run_id: $run_id})
                        CREATE (pn:PredictionNode {
                            step_id: $step_id,
                            expected_diff: $expected_diff
                        })
                        CREATE (sim)-[:PREDICTS_STATE {order: $order}]->(pn)
                        """,
                        {
                            "run_id": run_id,
                            "step_id": step_id,
                            "expected_diff": diff_str,
                            "order": i
                        }
                    )
            log_agent_action("event", f"Simulated traversal starting at {start_step_id} for {domain}/{subdomain}. Run ID: {run_id}. Outcome: {outcome_class}.", path, ["TraversalStep", "SimulationRun"])
            return {
                "run_id": run_id,
                "path": path,
                "expected_diffs": expected_diffs,
                "expected_fitness": total_fitness,
                "outcome_class": outcome_class
            }
        except Exception as e:
            log_agent_action("error", f"Simulation failed for {domain}/{subdomain}: {e}", [], ["SimulationRun"])
            raise HTTPException(status_code=500, detail=str(e))
            
    elif action == 'calibrate':
        run_id = params.get("run_id")
        actual_diff = params.get("actual_diff")
        if not run_id or actual_diff is None:
            raise HTTPException(status_code=400, detail="run_id and actual_diff are required.")
        try:
            with driver.session() as session:
                res = session.run(
                    """
                    MATCH (sim:SimulationRun {run_id: $run_id})-[r:PREDICTS_STATE]->(pn:PredictionNode)
                    RETURN pn.step_id as step_id, pn.expected_diff as expected_diff
                    ORDER BY r.order
                    """,
                    {"run_id": run_id}
                )
                steps_data = []
                for rec in res:
                    steps_data.append({
                        "step_id": rec["step_id"],
                        "expected_diff": json.loads(rec["expected_diff"]) if rec["expected_diff"] else {}
                    })
                if not steps_data:
                    raise HTTPException(status_code=400, detail=f"No predictions found for run_id '{run_id}'.")
                merged_expected = {}
                for step in steps_data:
                    merged_expected.update(step["expected_diff"])
                total_actual_keys = len(actual_diff)
                matching_keys = 0
                for k, v in actual_diff.items():
                    if k in merged_expected and merged_expected[k] == v:
                        matching_keys += 1
                accuracy = matching_keys / total_actual_keys if total_actual_keys > 0 else 1.0
                success_run = accuracy >= 0.8
                adjustments = []
                for i in range(len(steps_data) - 1):
                    from_id = steps_data[i]["step_id"]
                    to_id = steps_data[i + 1]["step_id"]
                    adjust_msg = adjust_transition_weight_internal(from_id, to_id, success_run)
                    adjustments.append(adjust_msg)
                session.run(
                    """
                    MATCH (sim:SimulationRun {run_id: $run_id})
                    SET sim.actual_diff = $actual_diff,
                        sim.accuracy = $accuracy,
                        sim.calibrated = true
                    """,
                    {
                        "run_id": run_id,
                        "actual_diff": json.dumps(actual_diff),
                        "accuracy": accuracy
                    }
                )
            log_agent_action("success", f"Calibrated SimulationRun {run_id}. Accuracy: {accuracy:.2f}.", [run_id], ["SimulationRun"])
            return {
                "run_id": run_id,
                "accuracy": accuracy,
                "success_threshold_met": success_run,
                "adjustments": adjustments
            }
        except Exception as e:
            log_agent_action("error", f"Calibration failed for run {run_id}: {e}", [run_id], ["SimulationRun"])
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: '{action}'.")

@app.get("/api/commands")
def get_commands_api():
    driver = get_driver()
    try:
        with driver.session() as session:
            query = """
            MATCH (s:TraversalStep)
            WHERE NOT ()-[:NEXT_STEP]->(s)
            RETURN s.id as id, s.text as text, elementId(s) as node_element_id
            ORDER BY id ASC
            """
            res = session.run(query)
            cmds = []
            for record in res:
                cmds.append({
                    "id": record["id"],
                    "text": record["text"],
                    "node_element_id": record["node_element_id"]
                })
            log_agent_action("system", "Retrieved available commands/traversal flows", [], ["TraversalStep"])
            return cmds
    except Exception as e:
        log_agent_action("error", f"Failed to retrieve commands: {e}", [], ["TraversalStep"])
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crud_state_machine_calls")
def crud_state_machine_calls_api(req: CrudStateMachineCallsRequest):
    driver = get_driver()
    action = req.action.lower()
    try:
        with driver.session() as session:
            if action == "create":
                res_step = session.run("MATCH (s:TraversalStep {id: $id}) RETURN count(s) as count", {"id": req.from_step_id})
                if res_step.single()["count"] == 0:
                    raise HTTPException(status_code=400, detail=f"TraversalStep '{req.from_step_id}' does not exist.")
                res_sm = session.run("MATCH (sm:StateMachine {id: $id}) RETURN count(sm) as count", {"id": req.to_state_machine_id})
                if res_sm.single()["count"] == 0:
                    raise HTTPException(status_code=400, detail=f"StateMachine '{req.to_state_machine_id}' does not exist.")
                session.run(
                    """
                    MATCH (s:TraversalStep {id: $step_id})
                    MATCH (sm:StateMachine {id: $sm_id})
                    MERGE (s)-[:CALLS_SM]->(sm)
                    """,
                    {"step_id": req.from_step_id, "sm_id": req.to_state_machine_id}
                )
                log_agent_action("success", f"Linked step '{req.from_step_id}' to sub-state machine '{req.to_state_machine_id}'.", [req.from_step_id, req.to_state_machine_id], ["TraversalStep", "StateMachine"])
                return {"message": f"Successfully linked step '{req.from_step_id}' to sub-state machine '{req.to_state_machine_id}'."}
            elif action == "delete":
                session.run(
                    """
                    MATCH (s:TraversalStep {id: $step_id})-[r:CALLS_SM]->(sm:StateMachine {id: $sm_id})
                    DELETE r
                    """,
                    {"step_id": req.from_step_id, "sm_id": req.to_state_machine_id}
                )
                log_agent_action("success", f"Deleted compiler call link from step '{req.from_step_id}' to sub-state machine '{req.to_state_machine_id}'.", [req.from_step_id, req.to_state_machine_id], ["TraversalStep", "StateMachine"])
                return {"message": f"Successfully deleted compiler call link from step '{req.from_step_id}' to sub-state machine '{req.to_state_machine_id}'."}
            else:
                raise HTTPException(status_code=400, detail=f"Unknown action: '{action}'. Must be 'create' or 'delete'.")
    except HTTPException as he:
        log_agent_action("error", f"Compiler call action failed: {he.detail}", [], ["TraversalStep", "StateMachine"])
        raise he
    except Exception as e:
        log_agent_action("error", f"Compiler call action failed: {e}", [], ["TraversalStep", "StateMachine"])
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/configure_ghost_shell")
def configure_ghost_shell_api(req: ConfigureGhostShellRequest):
    driver = get_driver()
    try:
        with driver.session() as session:
            res = session.run("MATCH (m:Cybernet {name: $name}) RETURN m", {"name": req.cybernet_name})
            if not res.peek():
                raise HTTPException(status_code=404, detail=f"Cybernet '{req.cybernet_name}' not found.")
            
            updates = []
            params = {"cybernet_name": req.cybernet_name}
            if req.model_name is not None:
                updates.append("m.model_name = $model_name")
                params["model_name"] = req.model_name
            if req.parameters_count is not None:
                updates.append("m.parameters_count = $parameters_count")
                params["parameters_count"] = float(req.parameters_count)
            if req.temperature is not None:
                updates.append("m.temperature = $temperature")
                params["temperature"] = float(req.temperature)
            if req.top_p is not None:
                updates.append("m.top_p = $top_p")
                params["top_p"] = float(req.top_p)
            if req.max_tokens is not None:
                updates.append("m.max_tokens = $max_tokens")
                params["max_tokens"] = int(req.max_tokens)
                
            if updates:
                query = f"MATCH (m:Cybernet {{name: $cybernet_name}}) SET " + ", ".join(updates)
                session.run(query, params)
            log_agent_action("success", f"Configured Ghost Shell parameters on '{req.cybernet_name}'", [req.cybernet_name], ["Cybernet"])
            return {"message": f"Successfully updated Ghost Shell config for Cybernet '{req.cybernet_name}'."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ghost_shell/status/{cybernet_name}")
def get_ghost_shell_status_api(cybernet_name: str):
    driver = get_driver()
    try:
        with driver.session() as session:
            res = session.run("MATCH (m:Cybernet {name: $name}) RETURN m", {"name": cybernet_name})
            record = res.single()
            if not record:
                raise HTTPException(status_code=404, detail=f"Cybernet '{cybernet_name}' not found.")
            rec = record["m"]
            log_agent_action("system", f"Retrieved Ghost Shell status for '{cybernet_name}'", [cybernet_name], ["Cybernet"])
            return {
                "name": rec["name"],
                "model_name": rec["model_name"],
                "parameters_count": rec["parameters_count"],
                "temperature": rec["temperature"],
                "top_p": rec["top_p"],
                "max_tokens": rec["max_tokens"],
                "total_tokens_consumed": rec["total_tokens_consumed"],
                "accumulated_cost": rec["accumulated_cost"]
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute_host_command")
def execute_host_command_api(req: ExecuteHostCommandRequest):
    logger.info(f"Executing shell command in project directory: {req.command}")
    log_agent_action("action", f"Executed shell command: {req.command}", [], [])
    try:
        project_dir = "/Users/isaacwr/.gemini/antigravity/scratch/cyberneticircus"
        res = subprocess.run(
            req.command,
            shell=True,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = []
        if res.stdout:
            output.append(res.stdout)
        if res.stderr:
            output.append(f"STDERR:\n{res.stderr}")
        if not output:
            return {"output": f"Command finished with exit code {res.returncode} (no output)."}
        return {"output": "\n".join(output)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shell command execution failed: {e}")

if __name__ == "__main__":
    import uvicorn
    # Make sure default graphs populate on start
    try:
        dr = get_driver()
        populate_default_graphs(dr)
    except Exception as e:
        logger.error(f"Failed to bootstrap defaults on web server startup: {e}")
        
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)
