#!/usr/bin/env python3
"""
FastAPI Backend for CybernetiCircus RPG.
Exposes REST endpoints to query and execute Cybernet identities and ticks.
"""
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Ensure local dir is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from engine import CybernetiCircusCompiler, AgentLLMRunner

app = FastAPI(title="CybernetiCircus Compiler API")

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

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
            res = session.run("MATCH (m:MetaShifter) RETURN m.name as name ORDER BY name")
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
                MATCH (m:MetaShifter {name: $name})-[:HAS_SIMULATION]->(sim:SimulationRun)
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
                import json
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
        
        # Get active step ID and state machine ID for highlighting
        current_step_node_id = None
        active_shifter_node_id = None
        equipped_sm_node_id = None
        
        if name:
            with compiler.driver.session() as session:
                res = session.run(
                    """
                    MATCH (m:MetaShifter {name: $name})
                    OPTIONAL MATCH (m)-[:HAS_LIFECYCLE]->(s:IdentityState)
                    OPTIONAL MATCH (s)-[:CURRENT_STEP]->(curr:TraversalStep)
                    OPTIONAL MATCH (m)-[:EQUIPS]->(sm:StateMachine)
                    RETURN id(m) as m_id, id(curr) as curr_id, id(sm) as sm_id
                    """,
                    {"name": name}
                )
                rec = res.single()
                if rec:
                    active_shifter_node_id = str(rec["m_id"]) if rec["m_id"] is not None else None
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
                if nid == active_shifter_node_id:
                    is_active = "shifter"
                elif nid == current_step_node_id:
                    is_active = "step"
                elif nid == equipped_sm_node_id:
                    is_active = "state_machine"
                    
                nodes.append({
                    "id": nid,
                    "label": label,
                    "name": display_name,
                    "properties": serialize_properties(dict(node)),
                    "active_tag": is_active
                })
            return nid

        with compiler.driver.session() as session:
            if name:
                # Query the active character's specific subgraph (instant, limited to active machine)
                res = session.run(
                    """
                    MATCH (m:MetaShifter {name: $name})
                    OPTIONAL MATCH (m)-[r1:HAS_LIFECYCLE]->(s:IdentityState)
                    OPTIONAL MATCH (s)-[r2:CURRENT_STEP]->(curr:TraversalStep)
                    OPTIONAL MATCH (m)-[r3:EQUIPS]->(sm:StateMachine)
                    OPTIONAL MATCH (sm)-[r4:HAS_STEP]->(step:TraversalStep)
                    OPTIONAL MATCH (step)-[r5:NEXT_STEP]->(next:TraversalStep)
                    OPTIONAL MATCH (step)-[r6:CALLS_SM]->(child:StateMachine)
                    RETURN m, s, sm, step, next, child, curr, r1, r2, r3, r4, r5, r6
                    """,
                    {"name": name}
                )
                for record in res:
                    m_id = add_node(record["m"])
                    s_id = add_node(record["s"])
                    sm_id = add_node(record["sm"])
                    step_id = add_node(record["step"])
                    next_id = add_node(record["next"])
                    child_id = add_node(record["child"])
                    curr_id = add_node(record["curr"])
                    
                    if m_id and s_id:
                        links.append({"source": m_id, "target": s_id, "type": "HAS_LIFECYCLE"})
                    if m_id and sm_id:
                        links.append({"source": m_id, "target": sm_id, "type": "EQUIPS"})
                    if s_id and curr_id:
                        links.append({"source": s_id, "target": curr_id, "type": "CURRENT_STEP"})
                    if sm_id and step_id:
                        links.append({"source": sm_id, "target": step_id, "type": "HAS_STEP"})
                    if step_id and next_id:
                        links.append({"source": step_id, "target": next_id, "type": "NEXT_STEP"})
                    if step_id and child_id:
                        links.append({"source": step_id, "target": child_id, "type": "CALLS_SM"})
            else:
                # Query all MetaShifters and their high-level active states (keeps it extremely small)
                res = session.run(
                    """
                    MATCH (m:MetaShifter)
                    OPTIONAL MATCH (m)-[r1:HAS_LIFECYCLE]->(s:IdentityState)
                    OPTIONAL MATCH (s)-[r2:CURRENT_STEP]->(curr:TraversalStep)
                    OPTIONAL MATCH (m)-[r3:EQUIPS]->(sm:StateMachine)
                    RETURN m, s, sm, curr, r1, r2, r3
                    """
                )
                for record in res:
                    m_id = add_node(record["m"])
                    s_id = add_node(record["s"])
                    sm_id = add_node(record["sm"])
                    curr_id = add_node(record["curr"])
                    
                    if m_id and s_id:
                        links.append({"source": m_id, "target": s_id, "type": "HAS_LIFECYCLE"})
                    if m_id and sm_id:
                        links.append({"source": m_id, "target": sm_id, "type": "EQUIPS"})
                    if s_id and curr_id:
                        links.append({"source": s_id, "target": curr_id, "type": "CURRENT_STEP"})
                        
        return {"nodes": nodes, "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        compiler.close()


@app.post("/api/create")
def create_cybernet(req: CreateCybernetRequest):
    compiler = CybernetiCircusCompiler()
    try:
        msg = compiler.create_metashifter(
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
        # Attempt to auto-equip default State Machine
        try:
            compiler.equip_state_machine(req.name, "sh8_lifecycle_sm")
        except Exception:
            pass
        return {"success": True, "message": msg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        compiler.close()

@app.post("/api/equip")
def equip_state_machine(req: EquipRequest):
    compiler = CybernetiCircusCompiler()
    try:
        msg = compiler.equip_state_machine(req.character_name, req.state_machine_id)
        return {"success": True, "message": msg}
    except Exception as e:
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
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        compiler.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)
