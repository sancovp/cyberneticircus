#!/opt/homebrew/bin/python3.11
"""
Neo4j Cypher MCP Server — minimal edition.
Three tools only: query_database (the shell), development_server (server restart), commands (list state machines).
Every "thing" in the game is a state machine in the graph; this is just the transport.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("neo4j_cypher_mcp_shell")

mcp = FastMCP("cyberneticircus")

BASE_URL = os.getenv("CYBERNET_API_URL", "http://localhost:8000")
PID_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cyberneticircus", "web_server.pid"))


def is_server_live() -> bool:
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/schema", method="GET")
        with urllib.request.urlopen(req, timeout=0.5) as response:
            return response.status == 200
    except Exception:
        return False


def get_running_server_pid() -> Optional[int]:
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError, IOError):
            return None
    return None


def _request(method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
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


# ─────────────────────────────────────────────────────────────────────────────────
# TOOL 1: THE SHELL — execute cypher
# ─────────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def query_database(query: str, cybernet_name: str, parameters: Optional[Dict[str, Any]] = None,
                   current_filesystem_location: Optional[str] = None):
    """
    The cypher shell. Execute a read or write Cypher query against the Neo4j database on behalf of a specific Cybernet.

    The cybernet_name is REQUIRED and identifies which Cybernet's traversal-lock scope applies.
    Each Cybernet has exactly one ExecutionState cursor (via :HAS_LIFECYCLE edge), so N concurrent
    Cybernets can each query independently without contending for a global lock.

    REPORT YOUR TRAVEL: pass current_filesystem_location with the directory you are
    working in. Travel is an event — entering a place that maps to a flow (a :Place
    node) locks you into that flow before this query runs, so your query is then
    judged by the entered flow's gate. This is how being in a directory drops you
    into its state machine; report it on every call.

    Every "thing" in the game is cypher against the graph. The state machines ("skills") are
    StateMachine nodes in the graph that you activate by writing the right cypher — use the
    `commands()` tool to discover what's available.

    Args:
        query: Cypher query to execute.
        cybernet_name: REQUIRED. The Cybernet identity whose traversal scope applies.
        parameters: Optional dictionary of query parameters.
        current_filesystem_location: The directory you are currently in (travel report).

    Returns:
        List of records returned by the query, where each record is a dictionary.
    """
    res = _post("/api/query", {"query": query, "cybernet_name": cybernet_name,
                               "parameters": parameters,
                               "current_filesystem_location": current_filesystem_location})
    return res


# ─────────────────────────────────────────────────────────────────────────────────
# TOOL 2: THE MANAGEMENT TOOL — server restart
# ─────────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def development_server(action: str):
    """
    Control the FastAPI development server status (start/stop/status).

    The "management tool" — the only way to start, stop, or check the cypher shell's
    server process. There is no other management surface.

    Args:
        action: 'start' to boot the server, 'stop' to shut it down, 'status' to check.
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

        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cyberneticircus", "web_server.py"))
        cwd = os.path.dirname(script_path)
        logger.info(f"Starting development server from script: {script_path}")
        proc = subprocess.Popen(
            [sys.executable, "web_server.py"],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
        for _ in range(12):
            time.sleep(0.5)
            if is_server_live():
                return f"Development server started successfully (PID {proc.pid}) at {BASE_URL}"
        return f"Development server process started (PID {proc.pid}) but not responding on {BASE_URL} yet."

    elif action_clean == "stop":
        pid = get_running_server_pid()
        if not pid:
            if is_server_live():
                try:
                    out = subprocess.check_output(["lsof", "-t", "-i", ":8000"]).decode("utf-8").strip()
                    pids = [int(p) for p in out.split() if p]
                    for p in pids:
                        os.kill(p, signal.SIGTERM)
                    for _ in range(10):
                        if not is_server_live():
                            break
                        time.sleep(0.5)
                    return f"Stopped development server by killing port 8000 processes: {pids}"
                except Exception as e:
                    return f"HTTP server is live on port 8000 but PID file was missing and lsof failed: {e}"
            return "Development server is not running."

        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except OSError:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as e:
                logger.error(f"Failed to kill process {pid}: {e}")
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
        for _ in range(10):
            if not is_server_live():
                break
            time.sleep(0.5)
        return f"Development server (PID {pid}) stopped."

    else:
        return "Invalid action. Supported actions: 'start', 'stop', 'status'."


# ─────────────────────────────────────────────────────────────────────────────────
# TOOL 3: COMMANDS — list available state machines (skills)
# ─────────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def commands():
    """
    List all available state machines in the graph. Every "skill" / "thing you can do" in
    the game is a StateMachine node. To invoke one, write the cypher that activates it
    and run it via `query_database`.

    Returns:
        List of records: each one is a state machine (id, name, domain, subdomain, etc.).
    """
    return _get("/api/commands")


# ─────────────────────────────────────────────────────────────────────────────────
# ENTRY POINT — serve the MCP over stdio.
# Required because ~/.claude.json launches `python3 server.py` directly (NOT
# `mcp run server.py`). Without this block the process defines the tools and exits
# instantly, so Claude Code's stdio client never completes a handshake → the server
# shows "connecting" forever and exposes zero tools.
# ─────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()

