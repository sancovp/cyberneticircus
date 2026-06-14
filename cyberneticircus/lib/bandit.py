"""
The bandit — selection over arms at a Core step (DESIGN §6.A increment 3 / §13.4).

The being SELECTS among arms; the DEFAULT, always-present root arm is
"make a thing or not" (Isaac: "it's a bandit process and the first thing they can
select is to make a thing or not"). Arm-weights are learnable from reward
(computed at Night) and ride on the existing NEXT_STEP / CALLS_SM weights.

This module is the PURE selection logic, with no fork: classify a being's write
into the make-a-thing-or-not root arm, list the arm-set at a step, and compute
the reward delta. It is intentionally NOT yet wired into the live gate
(`gates.auto_progress_step`) — *that* wiring (how the choice plugs into the gate
state-machine) is the one open design decision. Pure functions → unit-testable,
zero risk to the live gate, no neo4j.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

# The default root arms — every selectable step bottoms out in this binary.
ARM_MAKE = "make_a_thing"
ARM_NOT = "not"

# A creation = CREATE/MERGE of a *labelled* node (the "make a thing" act).
_CREATION_RE = re.compile(r"(?i)\b(CREATE|MERGE)\b\s*\(\s*[a-zA-Z0-9_]*\s*:\s*[a-zA-Z0-9_]+")


def is_creation(query: str) -> bool:
    """True if the write creates/merges a labelled node — the 'make a thing' act.
    Scale-relative: at the top this is Daemon-Summon a Cybernet; lower down, any
    node/SM/object. String literals are stripped so a literal 'CREATE' inside a
    quoted value does not count."""
    clean = re.sub(r"'[^']*'", "''", re.sub(r'"[^"]*"', '""', query))
    return bool(_CREATION_RE.search(clean))


def classify_default_arm(query: str) -> str:
    """The default 'make a thing or not' selection: which root arm did the being
    pick by what it wrote? ARM_MAKE if the write makes a thing, else ARM_NOT."""
    return ARM_MAKE if is_creation(query) else ARM_NOT


def arms_for_step(calls_sm: List[str]) -> List[Dict[str, Any]]:
    """The arm-set offered at a step: the default {make_a_thing, not} root arms
    ALWAYS present, PLUS any selectable inner SMs (the step's CALLS_SM children).
    Each arm carries its kind ('default' | 'callsm')."""
    arms: List[Dict[str, Any]] = [
        {"arm": ARM_MAKE, "kind": "default"},
        {"arm": ARM_NOT, "kind": "default"},
    ]
    for child in calls_sm or []:
        if child:
            arms.append({"arm": child, "kind": "callsm"})
    return arms


def reward_delta(success: bool, fitness_delta: float = 0.0) -> float:
    """Asserted v1 reward (computed at Night, applied to the chosen arm's weight):
    +0.1 on step-success / -0.2 on failure, plus the run's fitness_score delta.
    Both signals already live in the graph. The exact signal is Isaac's to confirm;
    this is the defensible default ('the Cybernet updates the weights and calculates
    scores during night')."""
    base = 0.1 if success else -0.2
    return round(base + fitness_delta, 3)
