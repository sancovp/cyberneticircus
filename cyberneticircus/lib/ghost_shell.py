"""
Ghost Shell — the Cybernet's LLM model config (model_name, temperature, top_p, max_tokens).

Compositions:
  - configure  →  POST /api/configure_ghost_shell  (partial update)
  - status     →  GET  /api/ghost_shell/status/{cybernet_name}
"""
from __future__ import annotations
from typing import Any, Dict, Optional


def configure_cypher(cybernet_name: str, model_name: str = None,
                    temperature: float = None, top_p: float = None,
                    max_tokens: int = None) -> str:
    """Return the partial-SET cypher string for one or more ghost shell fields."""
    sets = []
    params = ["cybernet_name"]
    if model_name is not None:
        sets.append("m.model_name = $model_name")
        params.append("model_name")
    if temperature is not None:
        sets.append("m.temperature = $temperature")
        params.append("temperature")
    if top_p is not None:
        sets.append("m.top_p = $top_p")
        params.append("top_p")
    if max_tokens is not None:
        sets.append("m.max_tokens = $max_tokens")
        params.append("max_tokens")
    if not sets:
        return "/* no ghost shell fields specified */"
    set_clause = ", ".join(sets)
    return f"""MATCH (m:Cybernet {{name: $cybernet_name}})
SET {set_clause}
RETURN m"""


GET_GHOST_SHELL_CYPHER = "MATCH (m:Cybernet {name: $name}) RETURN m"


def configure(driver, *, cybernet_name: str, model_name: Optional[str] = None,
              parameters_count: Optional[float] = None,
              temperature: Optional[float] = None, top_p: Optional[float] = None,
              max_tokens: Optional[int] = None) -> Dict[str, Any]:
    """Partial-update the Cybernet's Ghost Shell fields (only the ones passed)."""
    with driver.session() as session:
        if not session.run("MATCH (m:Cybernet {name: $name}) RETURN m", {"name": cybernet_name}).peek():
            raise ValueError(f"Cybernet '{cybernet_name}' not found")
        updates, params = [], {"cybernet_name": cybernet_name}
        if model_name is not None:
            updates.append("m.model_name = $model_name"); params["model_name"] = model_name
        if parameters_count is not None:
            updates.append("m.parameters_count = $parameters_count"); params["parameters_count"] = float(parameters_count)
        if temperature is not None:
            updates.append("m.temperature = $temperature"); params["temperature"] = float(temperature)
        if top_p is not None:
            updates.append("m.top_p = $top_p"); params["top_p"] = float(top_p)
        if max_tokens is not None:
            updates.append("m.max_tokens = $max_tokens"); params["max_tokens"] = int(max_tokens)
        if updates:
            session.run(
                f"MATCH (m:Cybernet {{name: $cybernet_name}}) SET " + ", ".join(updates),
                params
            )
    return {"message": f"Successfully updated Ghost Shell config for Cybernet '{cybernet_name}'."}


def status(driver, *, cybernet_name: str) -> Dict[str, Any]:
    """Read the Cybernet's full Ghost Shell + accumulated telemetry."""
    with driver.session() as session:
        rec = session.run(GET_GHOST_SHELL_CYPHER, {"name": cybernet_name}).single()
        if not rec:
            raise ValueError(f"Cybernet '{cybernet_name}' not found")
        m = rec["m"]
        return {
            "name": m["name"],
            "model_name": m["model_name"],
            "parameters_count": m["parameters_count"],
            "temperature": m["temperature"],
            "top_p": m["top_p"],
            "max_tokens": m["max_tokens"],
            "total_tokens_consumed": m["total_tokens_consumed"],
            "accumulated_cost": m["accumulated_cost"],
        }
