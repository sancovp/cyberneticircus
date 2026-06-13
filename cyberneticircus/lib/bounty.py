"""
Bounty spine — the :Finding / :Verdict ledger + the durable bounty economy rail.

The bug-bounty / ignorance-bounty mechanic ported from the proto. Two duals,
both perpendicular to flattening:

  * BUG-FINDING    — an adversarial gaze at the live engine/graph: a probe_cypher
                     that MATCHes a misbehaving region, filed append-only.
  * IGNORANCE-FINDING — a describe-dont-fix witness act: a :Finding linked via
                     :DESCRIBES_VIA to a Mind Palace :Page subgraph that holds the
                     metalanguage description of the flawed region (no mutation).

Lifecycle (this chunk = the persistence half; endpoints + LLM-judge land later):
  FILE   — file_finding   : MERGE a :Finding {status:'open', reward_paid:false}
                            (+ :DESCRIBES_VIA->:Page for ignorance findings).
  BOARD  — list_findings  : read-only list of findings (open / valid / invalid).
  JUDGE  — judge_finding  : the GM marks status=valid|invalid + MERGEs a :Verdict
                            node and a (:Verdict)-[:JUDGES]->(:Finding) edge. The
                            LLM scoring (call_judge) is owned by engine.py and wired
                            in a later chunk; here judge_finding persists a supplied
                            verdict (probe_confirmed/score/rationale) — the durable
                            append-only audit row, distinct from the pay step.

Every node carries domain:'cyberneticity'; :Finding and :Verdict reuse the new
subdomain:'finding' allowed-set entry (added to gates.py in the same change).
Persistence mirrors the db_logic helper style: cypher-string constants up top,
thin `with driver.session()` helpers below, keyword-only args.
"""
from __future__ import annotations
import random
import uuid
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Cypher-string constructors
# ---------------------------------------------------------------------------

CREATE_FINDING_CYPHER = """
MERGE (f:Finding {id: $id})
ON CREATE SET
    f.reporter = $reporter,
    f.kind = $kind,
    f.title = $title,
    f.description = $description,
    f.reproduction = $reproduction,
    f.severity = $severity,
    f.probe_cypher = $probe_cypher,
    f.reported_at = timestamp(),
    f.status = 'open',
    f.reward_paid = false,
    f.domain = 'cyberneticity',
    f.subdomain = 'finding'
RETURN f
"""

# Optionally tie the ignorance-finding to the metalanguage Mind Palace subgraph.
LINK_DESCRIBES_VIA_CYPHER = """
MATCH (f:Finding {id: $id})
MATCH (p:Page) WHERE elementId(p) = $page_id OR id(p) = $page_id_int OR p.id = $page_id
MERGE (f)-[:DESCRIBES_VIA]->(p)
"""

LIST_FINDINGS_CYPHER = """
MATCH (f:Finding)
OPTIONAL MATCH (f)-[:DESCRIBES_VIA]->(p:Page)
RETURN f.id as id, f.reporter as reporter, f.kind as kind, f.title as title,
       f.description as description, f.reproduction as reproduction,
       f.severity as severity, f.probe_cypher as probe_cypher,
       f.reported_at as reported_at, f.status as status, f.reward_paid as reward_paid,
       p.id as describes_via_page_id
ORDER BY f.reported_at DESC
"""

LIST_FINDINGS_BY_STATUS_CYPHER = """
MATCH (f:Finding {status: $status})
OPTIONAL MATCH (f)-[:DESCRIBES_VIA]->(p:Page)
RETURN f.id as id, f.reporter as reporter, f.kind as kind, f.title as title,
       f.description as description, f.reproduction as reproduction,
       f.severity as severity, f.probe_cypher as probe_cypher,
       f.reported_at as reported_at, f.status as status, f.reward_paid as reward_paid,
       p.id as describes_via_page_id
ORDER BY f.reported_at DESC
"""

GET_FINDING_CYPHER = """
MATCH (f:Finding {id: $id})
OPTIONAL MATCH (f)-[:DESCRIBES_VIA]->(p:Page)
RETURN f.id as id, f.reporter as reporter, f.kind as kind, f.title as title,
       f.description as description, f.reproduction as reproduction,
       f.severity as severity, f.probe_cypher as probe_cypher,
       f.reported_at as reported_at, f.status as status, f.reward_paid as reward_paid,
       p.id as describes_via_page_id
"""

SET_FINDING_STATUS_CYPHER = """
MATCH (f:Finding {id: $id})
SET f.status = $status
"""

# The durable append-only audit row of a GM validation decision. A re-judgement
# files a NEW :Verdict (unique id), never overwrites — so MERGE is keyed on the
# fresh verdict id, and the JUDGES edge is MERGEd idempotently for that id.
CREATE_VERDICT_CYPHER = """
MATCH (f:Finding {id: $finding_id})
MERGE (v:Verdict {id: $id})
ON CREATE SET
    v.finding_id = $finding_id,
    v.judge = $judge,
    v.kind = $kind,
    v.valid = $valid,
    v.probe_confirmed = $probe_confirmed,
    v.score = $score,
    v.amount_fitness = $amount_fitness,
    v.amount_tokens = $amount_tokens,
    v.rationale = $rationale,
    v.judged_at = timestamp(),
    v.domain = 'cyberneticity',
    v.subdomain = 'finding'
MERGE (v)-[:JUDGES]->(f)
RETURN v
"""


# ---------------------------------------------------------------------------
# PAY — economy constants + payout cypher
# ---------------------------------------------------------------------------
#
# The dole units. A validated BUG pays a flat BUG_FITNESS_UNIT (the circus
# analogue of the proto's 100g/bug); a validated IGNORANCE-finding pays
# IGNORANCE_UNIT * score (graded, rewarding richer accurate description, and
# deliberately SMALL until a discrepancy-probe spec lands — see DESIGN.md §8
# self-critique). Both land on Cybernet.bounty_fitness — the durable additive
# rail the night recompute FOLDS IN (never clobbers), so a paid finding durably
# nudges the reporter toward REPRODUCE_THRESHOLD=0.8 / away from REAP=0.4.
BUG_FITNESS_UNIT = 0.05          # flat fitness nudge per validated bug
IGNORANCE_UNIT = 0.05            # graded: actual award = IGNORANCE_UNIT * score
BOUNTY_TOKEN_CREDIT = 100        # engagement-cost credit folded into total_tokens_consumed

# Select VALID + UNPAID findings — the payout candidate set. The pair
# (status='valid', reward_paid=false) is the idempotency key: once paid, the
# flip to reward_paid=true removes the row from this set forever, so re-running
# payout is a no-op for already-paid findings.
SELECT_UNPAID_VALID_CYPHER = """
MATCH (f:Finding {status: 'valid', reward_paid: false})
RETURN f.id as id, f.reporter as reporter, f.kind as kind, f.title as title
ORDER BY f.reported_at ASC
"""

# Award the rail. A parameterized SET on a MATCHed Cybernet — mirrors the
# canonical ACCUMULATE_TOKEN_COST_CYPHER style (lifecycle.py): bounty_fitness is
# a sibling never-recomputed accumulator next to total_tokens_consumed, so the
# tick writer and the payout writer never collide on a shared field. coalesce
# upgrades a Cybernet minted before the rail existed (bounty_fitness null -> 0.0).
AWARD_BOUNTY_CYPHER = """
MATCH (m:Cybernet {name: $name})
SET m.bounty_fitness = coalesce(m.bounty_fitness, 0.0) + $fitness_amount,
    m.total_tokens_consumed = coalesce(m.total_tokens_consumed, 0) + $tokens_credit
RETURN m.bounty_fitness as bounty_fitness, m.total_tokens_consumed as total_tokens_consumed
"""

# The ignorance dole is GRADED (IGNORANCE_UNIT * score). Read the score off the
# most-recent VALID :Verdict for this finding (a re-judgement files a NEW row, so
# we take the latest by judged_at). Bug findings ignore this and pay the flat unit.
LATEST_VERDICT_SCORE_CYPHER = """
MATCH (v:Verdict {finding_id: $finding_id, valid: true})
RETURN v.score as score
ORDER BY v.judged_at DESC
LIMIT 1
"""

# Flip the idempotency guard: a validated finding is paid exactly once across
# payout calls. Done per-finding AFTER its reporter's award lands.
MARK_PAID_CYPHER = """
MATCH (f:Finding {id: $id})
SET f.reward_paid = true
"""


# ---------------------------------------------------------------------------
# Row -> dict renderer (keeps every list/get on one shape)
# ---------------------------------------------------------------------------

def _render_finding(rec) -> Dict[str, Any]:
    """Project a finding record into the dict the board + judge consume."""
    return {
        "id": rec["id"],
        "reporter": rec["reporter"],
        "kind": rec["kind"],
        "title": rec["title"],
        "description": rec["description"],
        "reproduction": rec["reproduction"],
        "severity": rec["severity"],
        "probe_cypher": rec["probe_cypher"],
        "reported_at": rec["reported_at"],
        "status": rec["status"],
        "reward_paid": rec["reward_paid"],
        "describes_via_page_id": rec["describes_via_page_id"],
    }


# ---------------------------------------------------------------------------
# FILE — file_finding (bug + ignorance)
# ---------------------------------------------------------------------------

def file_finding(driver, *, reporter: str, kind: str, title: str, description: str,
                 reproduction: str, severity: str, probe_cypher: str,
                 page_id: Optional[str] = None) -> Dict[str, Any]:
    """File a :Finding (append-only) — the FILE step of the bounty spine.

    Mints `finding_<ts>_<rand>_<name>`, MERGEs a :Finding {status:'open',
    reward_paid:false} via the driver (every create carries domain+subdomain).
    For kind=='ignorance' with a page_id, MERGEs (f)-[:DESCRIBES_VIA]->(p:Page)
    linking the metalanguage Mind Palace subgraph (the describe-dont-fix artifact).
    The reporter NEVER mutates the flawed region — it only files a description +
    a read-only probe. Returns the filed finding dict.
    """
    if kind not in ("bug", "ignorance"):
        raise ValueError(f"kind must be 'bug' or 'ignorance', got '{kind}'.")
    if severity not in ("low", "med", "high", "critical"):
        raise ValueError(f"severity must be one of low|med|high|critical, got '{severity}'.")
    if not reporter or not title or not probe_cypher:
        raise ValueError("reporter, title, and probe_cypher are required.")

    safe_name = "".join(ch if ch.isalnum() else "_" for ch in reporter).strip("_") or "anon"
    finding_id = f"finding_{int(_now_ts())}_{uuid.uuid4().hex[:6]}_{safe_name}"

    with driver.session() as session:
        if not session.run("MATCH (c:Cybernet {name: $n}) RETURN c", {"n": reporter}).peek():
            raise ValueError(f"Reporter Cybernet '{reporter}' does not exist.")
        rec = session.run(CREATE_FINDING_CYPHER, {
            "id": finding_id, "reporter": reporter, "kind": kind, "title": title,
            "description": description, "reproduction": reproduction,
            "severity": severity, "probe_cypher": probe_cypher,
        }).single()
        finding_node = dict(rec["f"]) if rec else {}
        if kind == "ignorance" and page_id:
            try:
                page_id_int = int(page_id)
            except (TypeError, ValueError):
                page_id_int = -1
            session.run(LINK_DESCRIBES_VIA_CYPHER, {
                "id": finding_id, "page_id": page_id, "page_id_int": page_id_int,
            })
            finding_node["describes_via_page_id"] = page_id
    finding_node.setdefault("id", finding_id)
    return finding_node


# ---------------------------------------------------------------------------
# BOARD — list_findings
# ---------------------------------------------------------------------------

def list_findings(driver, *, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read-only board: list findings, optionally filtered to one status.

    `status` in (open|valid|invalid). With no status, returns every finding
    (newest first). Reads only; never blocked by any gate.
    """
    if status is not None and status not in ("open", "valid", "invalid"):
        raise ValueError(f"status must be one of open|valid|invalid, got '{status}'.")
    with driver.session() as session:
        if status is None:
            res = session.run(LIST_FINDINGS_CYPHER)
        else:
            res = session.run(LIST_FINDINGS_BY_STATUS_CYPHER, {"status": status})
        return [_render_finding(r) for r in res]


def get_finding(driver, *, finding_id: str) -> Optional[Dict[str, Any]]:
    """Read a single :Finding by id (or None). Used by the judge to fetch the probe."""
    with driver.session() as session:
        rec = session.run(GET_FINDING_CYPHER, {"id": finding_id}).single()
        return _render_finding(rec) if rec else None


# ---------------------------------------------------------------------------
# JUDGE — judge_finding (the GM mark; persistence half)
# ---------------------------------------------------------------------------

def judge_finding(driver, *, finding_id: str, valid: bool, kind: Optional[str] = None,
                  probe_confirmed: bool = False, score: float = 0.0,
                  amount_fitness: float = 0.0, amount_tokens: int = 0,
                  rationale: str = "", judge: str = "GM") -> Dict[str, Any]:
    """Persist a GM validation decision — the JUDGE step's durable half.

    SETs Finding.status = valid|invalid, MERGEs a :Verdict node and a
    (:Verdict)-[:JUDGES]->(:Finding) edge, and leaves reward_paid untouched
    (the proto's mark-vs-pay separation; payout is a later, separate sweep).

    The :Verdict is append-only — a re-judgement files a NEW row (fresh id),
    never overwrites. The LLM scoring (call_judge / probe_confirmed gate) is
    owned by engine.py and wired in a later chunk; this helper persists a
    decision that is already computed, so it is the pure-graph mark.
    """
    with driver.session() as session:
        existing = session.run(GET_FINDING_CYPHER, {"id": finding_id}).single()
        if not existing:
            raise ValueError(f"Finding '{finding_id}' does not exist.")
        resolved_kind = kind or existing["kind"]
        status = "valid" if valid else "invalid"
        verdict_id = f"verdict_{int(_now_ts())}_{uuid.uuid4().hex[:6]}"

        session.run(SET_FINDING_STATUS_CYPHER, {"id": finding_id, "status": status})
        rec = session.run(CREATE_VERDICT_CYPHER, {
            "id": verdict_id, "finding_id": finding_id, "judge": judge,
            "kind": resolved_kind, "valid": bool(valid),
            "probe_confirmed": bool(probe_confirmed), "score": float(score),
            "amount_fitness": float(amount_fitness), "amount_tokens": int(amount_tokens),
            "rationale": rationale,
        }).single()
        verdict_node = dict(rec["v"]) if rec else {}
    verdict_node.setdefault("id", verdict_id)
    verdict_node.setdefault("finding_id", finding_id)
    verdict_node.setdefault("status_set", status)
    return verdict_node


# ---------------------------------------------------------------------------
# PAY — award_bounty (the rail SET) + pay_bounties (the idempotent sweep)
# ---------------------------------------------------------------------------

def award_bounty(session, *, name: str, fitness_amount: float, tokens_credit: int) -> Dict[str, Any]:
    """Route a bounty increment through the durable Cybernet.bounty_fitness rail.

    A lifecycle-style parameterized SET on a MATCHed Cybernet (mirrors
    lifecycle.ACCUMULATE_TOKEN_COST_CYPHER): bumps bounty_fitness (the
    tick-NEVER-written rail the night recompute folds into fitness_score) by
    `fitness_amount` and credits total_tokens_consumed (an existing
    never-recomputed accumulator) by `tokens_credit`. Takes an open session so
    the caller can sweep many reporters in one transaction scope. Returns the
    post-award {bounty_fitness, total_tokens_consumed} for the breakdown.
    """
    rec = session.run(AWARD_BOUNTY_CYPHER, {
        "name": name,
        "fitness_amount": float(fitness_amount),
        "tokens_credit": int(tokens_credit),
    }).single()
    if not rec:
        raise ValueError(f"Cannot award bounty: Cybernet '{name}' does not exist.")
    return {
        "bounty_fitness": rec["bounty_fitness"],
        "total_tokens_consumed": rec["total_tokens_consumed"],
    }


def pay_bounties(driver) -> Dict[str, Any]:
    """The PAY sweep — idempotent additive payout over VALID + UNPAID findings.

    Selects (f:Finding {status:'valid', reward_paid:false}), groups by reporter,
    and for each reporter sums BUG_FITNESS_UNIT (kind='bug') + IGNORANCE_UNIT*score
    (kind='ignorance'); since this chunk's :Verdict score for bugs is the durable
    audit row, the bug payout is the flat unit (the proto's 100g/bug analogue) and
    the ignorance payout reads the latest :Verdict.score for that finding. Routes
    each reporter's total through award_bounty (the bounty_fitness rail — NOT
    fitness_score, so the night recompute can't clobber it), then flips
    reward_paid=true per finding (the once-only idempotency guard). Re-running is
    a no-op: paid findings have left the candidate set. Returns a per-reporter
    breakdown + the list of finding ids paid this sweep.
    """
    paid_findings: List[str] = []
    breakdown: Dict[str, Dict[str, Any]] = {}

    with driver.session() as session:
        candidates = list(session.run(SELECT_UNPAID_VALID_CYPHER))
        if not candidates:
            return {"paid": [], "breakdown": {}, "total_findings_paid": 0}

        # Group candidate findings by reporter, accumulating the owed amount.
        for row in candidates:
            fid = row["id"]
            reporter = row["reporter"]
            kind = row["kind"]
            if kind == "ignorance":
                vrec = session.run(LATEST_VERDICT_SCORE_CYPHER, {"finding_id": fid}).single()
                score = vrec["score"] if vrec and vrec["score"] is not None else 0.0
                amount = IGNORANCE_UNIT * float(score)
            else:  # 'bug' (or any non-ignorance kind) pays the flat unit
                amount = BUG_FITNESS_UNIT
            entry = breakdown.setdefault(reporter, {"amount_fitness": 0.0, "tokens_credit": 0, "finding_ids": []})
            entry["amount_fitness"] += amount
            entry["tokens_credit"] += BOUNTY_TOKEN_CREDIT
            entry["finding_ids"].append(fid)

        # Per reporter: award the rail, then flip each of their findings to paid.
        for reporter, entry in breakdown.items():
            award = award_bounty(
                session,
                name=reporter,
                fitness_amount=entry["amount_fitness"],
                tokens_credit=entry["tokens_credit"],
            )
            entry["bounty_fitness_after"] = award["bounty_fitness"]
            entry["total_tokens_consumed_after"] = award["total_tokens_consumed"]
            for fid in entry["finding_ids"]:
                session.run(MARK_PAID_CYPHER, {"id": fid})
                paid_findings.append(fid)

    return {
        "paid": paid_findings,
        "breakdown": breakdown,
        "total_findings_paid": len(paid_findings),
    }


# ---------------------------------------------------------------------------
# Internal: timestamp (kept tiny + swappable; mirrors lifecycle's uuid usage)
# ---------------------------------------------------------------------------

def _now_ts() -> float:
    """Wall-clock seconds — only used to make ids sortable/unique alongside uuid."""
    import time
    return time.time()
