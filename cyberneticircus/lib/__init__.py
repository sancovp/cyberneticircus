"""
Library-level API functions for the cyberneticircus.

These are NOT MCP tools. They are Python helpers that return cypher strings (or take
a query-execution function and run them). Use them to:
- construct cypher for the operations that used to be MCP tools
- learn the cypher pattern that activates a state machine in the graph

The actual "things you can do" are state machines in the graph. This lib helps you
construct the cypher that activates them.
"""

from . import (
    cybernet,
    state_machines,
    transitions,
    surrogates,
    ghost_shell,
    gates,
    bootstrap_procedures,
    lifecycle,
    evolution,
    mind_palace,
    specs,
    system,
    visualizer,
    commands,
    logs,
    traversal,
    dispatcher,
    recognizer,
)

__all__ = [
    "cybernet",
    "state_machines",
    "transitions",
    "surrogates",
    "ghost_shell",
    "gates",
    "bootstrap_procedures",
    "lifecycle",
    "evolution",
    "mind_palace",
    "specs",
    "system",
    "visualizer",
    "commands",
    "logs",
    "traversal",
    "dispatcher",
    "recognizer",
]
