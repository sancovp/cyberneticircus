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
async def get_index():
    index_path = os.path.join(current_dir, "static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("index.html not found. Ensure static files are generated in /static/.", status_code=404)

@app.get("/api/list")
async def list_cybernets():
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
async def list_state_machines():
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
async def get_status(name: str):
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
async def get_simulations(name: str):
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

@app.post("/api/create")
async def create_cybernet(req: CreateCybernetRequest):
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
async def equip_state_machine(req: EquipRequest):
    compiler = CybernetiCircusCompiler()
    try:
        msg = compiler.equip_state_machine(req.character_name, req.state_machine_id)
        return {"success": True, "message": msg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        compiler.close()

@app.post("/api/tick")
async def tick_turn(req: TickRequest):
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
