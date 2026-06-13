"""
Router: bounty — the bug-bounty / ignorance-bounty HTTP surface.
  - finding   (FILE)  : file a :Finding (bug-finding OR ignorance-report)
  - findings  (BOARD) : read-only list of findings (open / valid / invalid)
  - judge     (JUDGE) : the GM marks a :Finding valid|invalid + records a :Verdict

Thin facade per the APIRouter pattern. Each endpoint body is a 1-line delegation
to lib/bounty.py (which carries domain+subdomain on every create via db_logic).
No business logic here — mirrors routers/traversal.py exactly (ValueError->400,
Exception->500, log_agent_action on every mutating route).

NB: the JUDGE route currently delegates to lib/bounty.judge_finding's durable
"mark" half (status flip + :Verdict audit row). The probe-gate + LLM scoring
(call_judge / runner_factory) is owned by engine.py and wired in a later chunk;
it will swap the delegation target without changing this route's shape.

The PAY route (POST /api/bounty/payout) is the idempotent additive sweep: it
routes each reporter's owed bounty through Cybernet.bounty_fitness (the
tick-never-written rail), flips reward_paid:false->true per paid finding (the
once-only guard), and logs the payout breakdown to the agent log.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db_logic import get_driver
from lib import bounty as lib_bounty
from lib import logs as lib_logs


router = APIRouter()


# --- Pydantic request models -------------------------------------------------

class BountyFindingRequest(BaseModel):
    reporter: str
    kind: str                       # 'bug' | 'ignorance'
    title: str
    description: str
    reproduction: str
    severity: str                   # 'low' | 'med' | 'high' | 'critical'
    probe_cypher: str
    page_id: Optional[str] = None   # ignorance-only: link the DESCRIBES_VIA->Page subgraph


class BountyJudgeRequest(BaseModel):
    finding_id: str
    valid: bool
    kind: Optional[str] = None
    probe_confirmed: bool = False
    score: float = 0.0
    amount_fitness: float = 0.0
    amount_tokens: int = 0
    rationale: str = ""


class BountyPayoutRequest(BaseModel):
    pass  # no body — idempotent batch sweep over VALID + UNPAID findings


# --- Endpoints (1-line delegations) ----------------------------------------

@router.post("/bounty/finding")
def file_finding_endpoint(req: BountyFindingRequest):
    """FILE step: mint + MERGE a :Finding {status:'open', reward_paid:false}.

    Covers BOTH duals — a bug-finding (probe_cypher MATCHes a misbehaving region)
    and an ignorance-report (kind=='ignorance' + page_id links the metalanguage
    Mind Palace :Page via :DESCRIBES_VIA). The reporter NEVER mutates the flawed
    region; it only files a description + a read-only probe.
    """
    try:
        finding = lib_bounty.file_finding(
            get_driver(),
            reporter=req.reporter, kind=req.kind, title=req.title,
            description=req.description, reproduction=req.reproduction,
            severity=req.severity, probe_cypher=req.probe_cypher, page_id=req.page_id,
        )
        lib_logs.log_agent_action("success", f"Filed {req.kind}-finding '{req.title}' by '{req.reporter}'", [finding.get("id", ""), req.reporter], ["Finding"])
        return finding
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        lib_logs.log_agent_action("error", f"Failed to file finding by '{req.reporter}': {e}", [req.reporter], ["Finding"])
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bounty/findings")
def list_findings_endpoint(status: Optional[str] = None):
    """BOARD: read-only list of findings (optionally filtered to open|valid|invalid).

    Lists OPEN findings (needs GM review) and VALID-unpaid findings (pays on the
    next payout sweep). Reads only; never blocked by any gate.
    """
    try:
        return lib_bounty.list_findings(get_driver(), status=status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bounty/judge")
def judge_finding_endpoint(req: BountyJudgeRequest):
    """JUDGE step (GM mark): SET Finding.status=valid|invalid + MERGE a :Verdict.

    Records the durable append-only audit row of the validation decision and the
    (:Verdict)-[:JUDGES]->(:Finding) edge; leaves reward_paid untouched (the
    proto's mark-vs-pay separation — payout is a separate later sweep).
    """
    try:
        verdict = lib_bounty.judge_finding(
            get_driver(),
            finding_id=req.finding_id, valid=req.valid, kind=req.kind,
            probe_confirmed=req.probe_confirmed, score=req.score,
            amount_fitness=req.amount_fitness, amount_tokens=req.amount_tokens,
            rationale=req.rationale,
        )
        lib_logs.log_agent_action("success", f"GM judged finding '{req.finding_id}' valid={req.valid}", [req.finding_id, verdict.get("id", "")], ["Finding", "Verdict"])
        return verdict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        lib_logs.log_agent_action("error", f"Failed to judge finding '{req.finding_id}': {e}", [req.finding_id], ["Finding", "Verdict"])
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bounty/payout")
def payout_endpoint(req: BountyPayoutRequest = BountyPayoutRequest()):
    """PAY step: idempotent additive sweep over VALID + UNPAID findings.

    For each reporter, awards the summed bounty onto Cybernet.bounty_fitness (the
    durable rail the night recompute folds into fitness_score — NOT clobbered),
    credits total_tokens_consumed, then flips each paid Finding.reward_paid=true
    so a validated finding pays exactly once across sweeps. Returns a per-reporter
    breakdown + the list of finding ids paid this sweep.
    """
    try:
        result = lib_bounty.pay_bounties(get_driver())
        reporters = list(result.get("breakdown", {}).keys())
        lib_logs.log_agent_action(
            "success",
            f"Bounty payout: {result.get('total_findings_paid', 0)} finding(s) paid to {len(reporters)} reporter(s) [{', '.join(reporters)}]",
            result.get("paid", []) + reporters,
            ["Finding", "Cybernet"],
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        lib_logs.log_agent_action("error", f"Bounty payout failed: {e}", [], ["Finding", "Cybernet"])
        raise HTTPException(status_code=500, detail=str(e))
