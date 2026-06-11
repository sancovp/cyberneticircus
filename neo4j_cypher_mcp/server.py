#!/opt/homebrew/bin/python3.11
"""
Neo4j Cypher MCP Server (Remote HTTP Proxy Edition)
Acts as a thin client proxy to the single host FastAPI coordinate server.
Delegates all database actions, safety validation, traversal gating, and command execution.
"""
import os
import json
import logging
import urllib.request
import urllib.error
import subprocess
import sys
import time
import signal
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("neo4j_cypher_mcp_proxy")

# Initialize FastMCP Server
mcp = FastMCP("cyberneticircus")

# Configure remote host address
BASE_URL = os.getenv("CYBERNET_API_URL", "http://localhost:8000")

PID_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cyberneticircus", "web_server.pid"))

def is_server_live() -> bool:
    """Check if the HTTP server is listening on port 8000."""
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/schema", method="GET")
        with urllib.request.urlopen(req, timeout=0.5) as response:
            return response.status == 200
    except Exception:
        return False

def get_running_server_pid() -> Optional[int]:
    """Get the running PID of the development server from the pidfile."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            # Check if process is still running (Unix signal 0)
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError, IOError):
            return None
    return None

def _request(method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
    """Proxy request via HTTP to the running coordinate FastAPI server."""
    url = f"{BASE_URL}{path}"
    logger.info(f"Proxying {method} request to live backend: {url}")
    
    if method == "POST":
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8") if data is not None else b"{}",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
    else:
        req = urllib.request.Request(url, method="GET")
        
    try:
        with urllib.request.urlopen(req, timeout=65.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8")
        try:
            detail = json.loads(err_body).get("detail", err_body)
        except Exception:
            detail = err_body
        logger.error(f"HTTP Error {err.code}: {detail}")
        if "Security Policy Violation" in detail or "strictly prohibited" in detail:
            raise PermissionError(detail)
        raise RuntimeError(f"Backend Error: {detail}")
    except Exception as e:
        logger.error(f"Failed to connect to backend {url}: {e}")
        raise RuntimeError(f"Connection to backend failed: {e}. Is the development server running? Use development_server('start') to start it.")

def _post(path: str, data: Optional[Dict[str, Any]] = None) -> Any:
    return _request("POST", path, data)

def _get(path: str) -> Any:
    return _request("GET", path)

@mcp.tool()
def development_server(action: str) -> str:
    """
    Control the FastAPI development server status.
    
    Args:
        action: 'start' to boot the server, 'stop' to shut it down, 'status' to check if it's running.
    """
    action_clean = action.lower().strip()
    if action_clean == "status":
        pid = get_running_server_pid()
        live = is_server_live()
        if pid:
            return f"Development server is RUNNING (PID {pid}), HTTP Live: {live}"
        else:
            if live:
                return f"Development server is RUNNING (External / No PID file), HTTP Live: True"
            return "Development server is STOPPED, HTTP Live: False"
            
    elif action_clean == "start":
        pid = get_running_server_pid()
        if pid:
            return f"Development server is already running (PID {pid})"
        if is_server_live():
            return "Development server is already running externally on port 8000."
        
        # Start the server
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cyberneticircus", "web_server.py"))
        cwd = os.path.dirname(script_path)
        
        logger.info(f"Starting development server from script: {script_path}")
        # Launch using the current python executable in the background
        # Use a new process group so reload subprocesses are killed too
        proc = subprocess.Popen(
            [sys.executable, "web_server.py"],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        
        # Write PID to file
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
            
        # Wait a moment and check if it successfully bound to port
        for _ in range(12):
            time.sleep(0.5)
            if is_server_live():
                return f"Development server started successfully (PID {proc.pid}) at {BASE_URL}"
        
        return f"Development server process started (PID {proc.pid}) but not responding on {BASE_URL} yet."
        
    elif action_clean == "stop":
        pid = get_running_server_pid()
        if not pid:
            # Check if anything is listening on port 8000 and try to kill it
            if is_server_live():
                try:
                    out = subprocess.check_output(["lsof", "-t", "-i", ":8000"]).decode("utf-8").strip()
                    pids = [int(p) for p in out.split() if p]
                    for p in pids:
                        os.kill(p, signal.SIGTERM)
                    # Wait for port to clear
                    for _ in range(10):
                        if not is_server_live():
                            break
                        time.sleep(0.5)
                    return f"Stopped development server by killing port 8000 processes: {pids}"
                except Exception as e:
                    return f"HTTP server is live on port 8000 but PID file was missing and lsof failed: {e}"
            return "Development server is not running."
            
        # Kill the process group
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except OSError:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as e:
                logger.error(f"Failed to kill process {pid}: {e}")
        
        # Remove the PID file if it exists
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
                
        # Wait for port to clear
        for _ in range(10):
            if not is_server_live():
                break
            time.sleep(0.5)
            
        return f"Development server (PID {pid}) stopped."
        
    else:
        return "Invalid action. Supported actions: 'start', 'stop', 'status'."


@mcp.tool()
def query_database(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute a read or write Cypher query on the Neo4j database.
    
    Safeguards the :Wiki namespace/label from direct write mutations.
    Locks database writes when an active Traversal State Machine is running.
    If the active step defines a 'required_pattern', matching queries are executed
    and automatically progress the traversal to the next step.
    
    Args:
        query: Cypher query to execute.
        parameters: Optional dictionary of query parameters.
    
    Returns:
        List of records returned by the query, where each record is a dictionary.
    """
    res = _post("/api/query", {"query": query, "parameters": parameters})
    return res

@mcp.tool()
def get_schema() -> Dict[str, List[str]]:
    """
    Retrieve the Neo4j database schema information.
    
    Returns:
        A dictionary containing lists of 'labels', 'relationship_types', and 'property_keys'.
    """
    return _get("/api/schema")

@mcp.tool()
def progress_traversal(answer: Optional[str] = None) -> str:
    """
    Progress the active Traversal State Machine to the next step manually.
    
    Args:
        answer: Optional answer or confirmation text for the current step.
        
    Returns:
        Status message explaining the new step or confirming completion and unlock.
    """
    res = _post("/api/traversal/progress", {"answer": answer})
    return res.get("message", "Success")

@mcp.tool()
def create_traversal_flow(
    steps: List[Dict[str, Any]],
    trigger_node_label: Optional[str] = None,
    trigger_node_properties: Optional[Dict[str, Any]] = None
) -> str:
    """
    Conveniently create a sequence of TraversalStep nodes in the graph and optionally
    attach the trigger_traversal property to a start/trigger node.
    
    Args:
        steps: A list of dicts. Each dict represents a step:
            - id: (str) Unique step identifier.
            - text: (str) Explanation of what the agent needs to do.
            - required_pattern: (str, optional) Python regex pattern query must match to auto-progress.
            - pattern_description: (str, optional) Friendly description of the required query.
        trigger_node_label: (str, optional) Label of the node that should trigger this traversal (e.g. 'AgentTask').
        trigger_node_properties: (dict, optional) Properties to identify the trigger node uniquely.
        
    Returns:
        A confirmation message indicating successful creation and linking of steps.
    """
    res = _post("/api/traversal/create_flow", {
        "steps": steps,
        "trigger_node_label": trigger_node_label,
        "trigger_node_properties": trigger_node_properties
    })
    return res.get("message", "Success")

@mcp.tool()
def create_weighted_transition(
    from_step_id: str,
    to_step_id: str,
    weight: float = 1.0,
    description: str = ""
) -> str:
    """
    Create or update a weighted transition relationship between two existing TraversalSteps.
    
    Args:
        from_step_id: The ID of the source TraversalStep.
        to_step_id: The ID of the target TraversalStep.
        weight: Float value representing transition weight / recommendation value (default 1.0).
        description: Description of this path choice.
    """
    res = _post("/api/traversal/create_transition", {
        "from_step_id": from_step_id,
        "to_step_id": to_step_id,
        "weight": weight,
        "description": description
    })
    return res.get("message", "Success")

@mcp.tool()
def adjust_transition_weight(
    from_step_id: str,
    to_step_id: str,
    success: bool
) -> str:
    """
    Adjust the weight of an existing NEXT_STEP transition relationship.
    Increments the weight slightly on success, and decrements it on failure (min weight 0.1).
    
    Args:
        from_step_id: The ID of the source TraversalStep.
        to_step_id: The ID of the target TraversalStep.
        success: True if the path succeeded, False if it failed/abandoned.
    """
    res = _post("/api/traversal/adjust_weight", {
        "from_step_id": from_step_id,
        "to_step_id": to_step_id,
        "success": success
    })
    return res.get("message", "Success")

@mcp.tool()
def crud_surrogate(action: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
    """
    Unified CRUD, Simulation, and Calibration tool for Surrogate Models.
    
    Actions:
      - 'create' / 'update': Save or modify a SurrogateModel with evolutionary knobs.
      - 'read': Fetch model parameters and past simulation summaries.
      - 'delete': Delete the model and all associated simulations.
      - 'simulate': Simulate a counterfactual traversal path using softmax selection and weights.
      - 'calibrate': Compare a simulation's prediction against actual results and adjust graph weights.
      
    Args:
        action: One of 'create', 'read', 'update', 'delete', 'simulate', 'calibrate'.
        parameters: A dictionary of parameters specific to the action.
    """
    return _post("/api/crud_surrogate", {"action": action, "parameters": parameters})

@mcp.tool()
def commands() -> List[Dict[str, Any]]:
    """
    Retrieve the list of all available commands/traversal flows registered in the graph.
    Returns the entry steps and their description text, along with their Neo4j node identifiers.
    """
    return _get("/api/commands")

@mcp.tool()
def create_cybernet_identity(
    name: str,
    description: str,
    model_name: str = "gemini-1.5-pro",
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 2048,
    mutation_rate: float = 0.1,
    selection_pressure: float = 1.0
) -> str:
    """
    Create a new Cybernet character identity in the Cyberneticity database.
    This registers the character node, defaults stats, and registers prompt keys.
    """
    res = _post("/api/create", {
        "name": name,
        "description": description,
        "model_name": model_name,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "mutation_rate": mutation_rate,
        "selection_pressure": selection_pressure
    })
    return res.get("message", "Success")

@mcp.tool()
def equip_state_machine_loadout(
    cybernet_name: str,
    state_machine_id: str
) -> str:
    """
    Equip a State Machine onto a Cybernet character.
    This links the character to the state machine, creates the execution lifecycle state,
    and initializes traversal status at the start step.
    """
    res = _post("/api/equip", {
        "character_name": cybernet_name,
        "state_machine_id": state_machine_id
    })
    return res.get("message", "Success")

@mcp.tool()
def tick_cybernet_turn(
    cybernet_name: str,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None
) -> Dict[str, Any]:
    """
    Tick one step/phase of a Cybernet's day/night cycle.
    Automatically executes the active state machine flow, runs queries, and calibrates.
    """
    return _post("/api/tick", {
        "character_name": cybernet_name,
        "model_name": model_name,
        "temperature": temperature,
        "top_p": top_p
    })

@mcp.tool()
def crud_state_machine_calls(
    action: str,
    from_step_id: str,
    to_state_machine_id: str
) -> str:
    """
    Establish or delete compiler CALLS_SM transition routes in the database.
    This lets steps in parent state machines route call threads to nested sub-state machines.
    """
    res = _post("/api/crud_state_machine_calls", {
        "action": action,
        "from_step_id": from_step_id,
        "to_state_machine_id": to_state_machine_id
    })
    return res.get("message", "Success")

@mcp.tool()
def configure_ghost_shell(
    cybernet_name: str,
    model_name: Optional[str] = None,
    parameters_count: Optional[float] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Configure or hot-swap the executing model (the Ghost Shell) of a Cybernet.
    Updates properties like model_name, parameters_count, temperature, top_p, and max_tokens on the identity.
    """
    res = _post("/api/configure_ghost_shell", {
        "cybernet_name": cybernet_name,
        "model_name": model_name,
        "parameters_count": parameters_count,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens
    })
    return res.get("message", "Success")

@mcp.tool()
def get_ghost_shell_status(cybernet_name: str) -> Dict[str, Any]:
    """
    Retrieve the details and performance stats of a Cybernet character's executing model config.
    Returns model name, total tokens consumed, accumulated cost, latency metrics, and dream rank.
    """
    return _get(f"/api/ghost_shell/status/{cybernet_name}")

@mcp.tool()
def execute_host_command(command: str) -> str:
    """
    Execute a shell command inside the CybernetiCircus workspace directory on the host machine.
    Provides real-time console stdout/stderr back.
    """
    res = _post("/api/execute_host_command", {"command": command})
    return res.get("output", "No output.")

if __name__ == "__main__":
    mcp.run()
