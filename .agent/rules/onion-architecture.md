---
name: onion-architecture
description: The Onion Architecture pattern for Python packages. Layers, facades, dependency rules, and canonical filenames. Codenose blocks non-canonical filenames when ~/.claude/.codenose_arch_lock exists.
metadata:
  type: architecture
source: understand-onion-arch skill from mind_of_god container
---

# Onion Architecture for Python Packages

## The Onion Model (Visual)

```
         ┌─────────────────────────────────────────┐
         │            OUTER LAYER                  │
         │   mcp_server.py / api.py / cli.py       │
         │   (Server Facades — pure delegation)    │
         │                                         │
         │    ┌─────────────────────────────┐      │
         │    │       MIDDLE LAYER          │      │
         │    │         core.py             │      │
         │    │   (Library Facade — thin)   │      │
         │    │                             │      │
         │    │   ┌─────────────────┐       │      │
         │    │   │   INNER LAYER   │       │      │
         │    │   │    utils.py     │       │      │
         │    │   │  (ALL THE STUFF)│       │      │
         │    │   │  - primitives   │       │      │
         │    │   │  - assemblies   │       │      │
         │    │   │  - mixins       │       │      │
         │    │   └─────────────────┘       │      │
         │    │                             │      │
         │    │   ┌─────────────────┐       │      │
         │    │   │   util_deps/    │       │      │
         │    │   │ (atomic deps)   │       │      │
         │    │   └─────────────────┘       │      │
         │    └─────────────────────────────┘      │
         │                                         │
         │   models.py (types/schemas float here)  │
         └─────────────────────────────────────────┘
```

## The Three Rules (NEVER VIOLATED)

### Rule 1: Dependencies Point Inward Only
- `mcp_server.py` → imports from `core.py`
- `core.py` → imports from `utils.py`
- `utils.py` → imports from `util_deps/`
- **NEVER** the reverse

### Rule 2: Facades Are Pure Delegation
```python
# CORRECT — pure delegation
@mcp.tool()
def do_thing(arg: str) -> str:
    return core.do_thing(arg)

# WRONG — logic in facade
@mcp.tool()
def do_thing(arg: str) -> str:
    processed = arg.strip().lower()  # ← THIS BELONGS IN CORE (OR UTILS)
    return core.do_thing(processed)
```

**The Facade Test:** If you can't delete a line from the facade without breaking functionality, that line belongs somewhere else.

### Rule 3: Logic Lives in utils.py
- **Primitives**: Pure functions, atomic operations
- **Assemblies**: Functions that compose primitives
- **Mixins**: Stateful capabilities (provide, don't dispatch)
- **Adapters**: Transformations between formats

`core.py` is SMALL — it's a facade over utils, not a logic container.

## Canonical Package Structure

```
my_package/
├── __init__.py          # exports from core.py
├── util_deps/           # atomic dependencies for utils
├── utils.py             # ALL THE STUFF — primitives, assemblies, mixins
├── models.py            # Pydantic models, types (optional)
├── core.py              # LIBRARY FACADE — small file, wraps utils
├── mcp_server.py        # SERVER FACADE — wraps core for MCP
└── (or api.py/cli.py)   # SERVER FACADE — wraps core for REST/CLI
```

## Canonical Filenames
`utils.py`, `core.py`, `models.py`, `mcp_server.py`, `api.py`, `cli.py`, `main.py`, `config.py`

**Lock mode:** `~/.claude/.codenose_arch_lock` exists = non-canonical filenames BLOCKED.

## Mapping to cyberneticircus

| onion layer | cyberneticircus equivalent | current state |
|---|---|---|
| OUTER (mcp_server.py) | `neo4j_cypher_mcp/server.py` (224 lines, 3 tools) | ✅ correct — 3 thin 1-line delegations to `_post` |
| OUTER (api.py) | `cyberneticircus/web_server.py` (1796 lines) | ❌ has business logic IN it — should be 1-line delegations only |
| MIDDLE (core.py) | `cyberneticircus/db_logic.py` (200 lines) + `cyberneticircus/engine.py` (293 lines) | ⚠️ partially — these are thin facades that delegate to lib/ but have some logic too |
| INNER (utils.py) | `cyberneticircus/lib/*.py` (10 modules) | ✅ correct — all the logic lives here |
| BASE (util_deps/) | (atomic deps within lib/) | ✅ — atomic functions live inside each lib/ module |
| models.py | the pydantic request models in web_server.py | ⚠️ mixed in with the routes — should be separate |

## Direction for refactoring web_server.py

per the onion arch, the `api.py` (web_server.py) layer should be **pure delegation**:
```python
# CURRENT (web_server.py) — bad, has business logic
@app.post("/api/tick")
def tick_api(req: TickRequest):
    compiler = CybernetiCircusCompiler()
    try:
        with compiler.driver.session() as session:
            # 200 lines of business logic inline...
            result = tick_turn(req.character_name, req.model_name, req.temperature, req.top_p)
            # more logic...
    except Exception as e:
        # more logic...
    return result

# TARGET — pure delegation
@app.post("/api/tick")
def tick_api(req: TickRequest) -> Dict[str, Any]:
    return lib_lifecycle.tick_turn(req.character_name, req.model_name, req.temperature, req.top_p)
```

the route body = 1 line. ALL the logic is in `lib/lifecycle.py` (or wherever the composition function lives).

## 3 Levels Deep Rule (from user feedback)

**It must be exactly nested 3 levels deep and that's it, never more.** Never make anything flat.

```
cyberneticircus/                      # level 1 — package root
  <domain>/                           # level 2 — domain (cybernet, gates, etc.)
    <module>/                         # level 3 — module (utils.py, core.py, api.py, etc.)
      # files go at level 3, NOT deeper
```

don't do:
- flat `cyberneticircus/lib/cybernet.py` + `cyberneticircus/lib/gates.py` + ... (flat)
- deep `cyberneticircus/lib/cybernet/utils/atomic_helpers/x.py` (too deep)

do:
- `cyberneticircus/lib/cybernet/utils.py` (lib/ as the level-2 domain, cybernet as the level-3 module)
- `cyberneticircus/lib/gates/utils.py` (each domain in its own subdir)
