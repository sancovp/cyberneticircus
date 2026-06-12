"""
Spec Lab — file-based specs and templates under <project>/specs/ and <project>/templates/.

Compositions:
  - list_specs     →  GET /api/specs/list
  - read_spec      →  GET /api/specs/read
  - save_spec      →  POST /api/specs/save
  - list_templates →  GET /api/specs/templates
  - read_template  →  GET /api/specs/template/read
"""
from __future__ import annotations
import os
from typing import Any, Dict, List


PROJECT_DIR = os.environ.get("PROJECT_DIR", "/Users/isaacwr/.gemini/antigravity/scratch/cyberneticircus")
SPECS_DIR = os.path.join(PROJECT_DIR, "specs")
TEMPLATES_DIR = os.path.join(PROJECT_DIR, "templates")


def _list_files_in(dir_path: str) -> List[str]:
    os.makedirs(dir_path, exist_ok=True)
    return sorted([f for f in os.listdir(dir_path) if f.endswith(".md") or f.endswith(".json")])


def list_specs() -> Dict[str, Any]:
    """List all .md/.json files under <project>/specs/."""
    return {"specs": _list_files_in(SPECS_DIR)}


def read_spec(filename: str) -> Dict[str, Any]:
    """Read a single spec file (path-traversal-protected)."""
    target = os.path.abspath(os.path.join(SPECS_DIR, filename))
    if not target.startswith(os.path.abspath(SPECS_DIR)):
        raise PermissionError("path traversal attempt blocked")
    if not os.path.exists(target):
        raise FileNotFoundError(filename)
    with open(target, "r", encoding="utf-8") as f:
        return {"content": f.read()}


def save_spec(filename: str, content: str) -> Dict[str, Any]:
    """Write a spec file. Filename must end in .md or .json, no path components."""
    if not (filename.endswith(".md") or filename.endswith(".json")):
        raise ValueError("filename must end in .md or .json")
    if filename != os.path.basename(filename) or ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("filename must be a base name, no directory components")
    os.makedirs(SPECS_DIR, exist_ok=True)
    target = os.path.abspath(os.path.join(SPECS_DIR, filename))
    if not target.startswith(os.path.abspath(SPECS_DIR)):
        raise PermissionError("path traversal attempt blocked")
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    return {"success": True, "path": target}


def list_templates() -> Dict[str, Any]:
    """List all .md/.json files under <project>/templates/."""
    return {"templates": _list_files_in(TEMPLATES_DIR)}


def read_template(filename: str) -> Dict[str, Any]:
    """Read a single template file (path-traversal-protected)."""
    target = os.path.abspath(os.path.join(TEMPLATES_DIR, filename))
    if not target.startswith(os.path.abspath(TEMPLATES_DIR)):
        raise PermissionError("path traversal attempt blocked")
    if not os.path.exists(target):
        raise FileNotFoundError(filename)
    with open(target, "r", encoding="utf-8") as f:
        return {"content": f.read()}
