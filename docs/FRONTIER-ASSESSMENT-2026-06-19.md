# CybernetiCircus — Frontier / SOTA Assessment (2026-06-19)

> Method: 4 Explore agents mapped the canonical repo to file:line mechanisms; a 76-agent
> research workflow then ran per-mechanism prior-art web research → 3-lens adversarial novelty
> panel (academic-skeptic / industry-OSS-skeptic / steelman+implementation-auditor) → reconciling
> judge → cluster synthesis → overall + completeness critic. Every verdict names dated prior art,
> grades the CCC↔nearest-known correspondence on the G0–G9 ladder (no rounding up), and separates
> BUILT from ASPIRATIONAL against verified source paths.

## Bottom line

**No — CCC does not push any subfield's state of the art.** It is a competently-built,
internally-coherent **NOVEL RECOMBINATION** whose every load-bearing primitive is published prior
art. The defensible deltas are *fusion / co-location on one live Neo4j graph* plus *a couple of
framing inversions*. **Architecturally distinctive, mechanistically derivative, partly aspirational.**

- **0** mechanisms are FRONTIER_NOVEL (genuinely unprecedented).
- **2** are CONVERGENT_FRONTIER (independent parallel invention inside a live 2025–26 race).
- **9** are NOVEL_RECOMBINATION (known parts, uncommon assembly — defensible as "an uncommon
  integration," not "frontier").
- **3** are KNOWN_TECHNIQUE (textbook / pre-dated; one because its keystone isn't built).

## Per-mechanism verdicts

| # | Mechanism | Cluster | Grade | Built? | Closest prior art (the thing it duplicates) |
|---|---|---|---|---|---|
| 1 | Graph-native runtime-mutable FSM (FSM as Neo4j data) | state-machine | NOVEL_RECOMBINATION | built | AutoGRAMS 2024 (covers 3/4 pillars); table-driven FSM 1981; RETE/Drools |
| 2 | Regex-gated transitions / 403-as-typecheck | state-machine | NOVEL_RECOMBINATION | built | Safety Chip 2023 (same refuse-then-instruct loop, G5) |
| 3 | Homoiconic + call-stack nesting (CALLS_SM) | state-machine | **KNOWN_TECHNIQUE** | partial | Recursive Transition Networks, Woods 1970; SteP 2023 |
| 4 | Decision-points-as-bandit-arms | state-machine | NOVEL_RECOMBINATION | built | HAM choice-states, Parr & Russell 1997; off-policy RL/DQN |
| 5 | Night consolidation (batch weight reinforce @ cycle boundary) | weight | **CONVERGENT_FRONTIER** | partial | SCM 2026; HAGE 2026; Experience-Evolving 2025; CLS theory |
| 6 | "Make a thing or not" primordial arm | weight | NOVEL_RECOMBINATION | partial | go/no-go learning (Guitart-Masip/Dayan 2012); ReAct parsing |
| 7 | Evolutionary population (reap/survive/reproduce + self-tune) | weight | NOVEL_RECOMBINATION | partial | **Population Based Training, DeepMind 2017** (G2 match); ES self-adaptation |
| 8 | Softmax / selection-pressure weighted walk | weight | **KNOWN_TECHNIQUE** | built | Boltzmann selective pressure, de la Maza & Tidor 1991–93 (G1) |
| 9 | "The graph IS the prompt" (per-tick projection) | prompt | NOVEL_RECOMBINATION | built | StateFlow 2024; LangGraph; MemGPT; computational reflection (Smith 1984) |
| 10 | Retrieval-is-activation / location-as-trigger | prompt | NOVEL_RECOMBINATION | built | production-system recognize-act (SOAR/ACT-R); Agent Skills 2025; HippoRAG |
| 11 | Persona compilation + J-Invariance | prompt | **CONVERGENT_FRONTIER** | partial | **ID-RAG 2025** (near 1:1 twin); Lee 2024 (stronger formal invariant) |
| 12 | Custodian genus = loop-runner gated by warrant | other | **KNOWN_TECHNIQUE** | partial | MetaAgent 2025 (covers claims 1+2); MAPE-K 2003; Statecharts 1987 |
| 13 | AIOS: graph-as-runtime + LLM-as-only-interpreter | other | NOVEL_RECOMBINATION | partial | CoRE / AIOS-Compiler 2024 (LLM-as-interpreter, minus graph substrate) |
| 14 | Daemon-summoning + provenance + on-node economy | other | NOVEL_RECOMBINATION | partial | ADAS 2024; Darwin Gödel Machine 2025; W3C PROV; BAMAS |

## The genuinely publishable parts (frontier-as-recombination/inversion)

1. **403-as-typecheck / constraint-leak-as-feature** (#2, built, conf 0.77) — *the single most
   publishable item.* A deliberate **inversion** of the 2024–26 agent-security frontier
   (KAIJU / PAuth / intent-gated-execution), which calls "a 403 leaks the policy boundary and the
   model adapts to satisfy it" a **vulnerability** to hide. CCC returns the *exact regex on purpose*
   because the leak **is** the steering signal. No published work positions the constraint-leaking
   refusal as a feature. (Mechanism class itself = Safety Chip 2023, G5 — cite it.)
2. **Gate == scheduler identity** (inside #13, built, conf 0.75) — one `required_pattern` match
   *simultaneously* typechecks the LLM's Cypher write **and** advances the FSM cursor
   (`db_logic.py:188`), 23 patterns held as graph data. Sharpest source-verified original primitive;
   currently buried under the over-claimed AIOS framing.
3. **The graph IS simultaneously program + memory** (#1, #9, #5) — one live Neo4j store is the
   agent's memory, its walked control-flow, and (at Night) its reinforced learned weights; the
   prompt is re-projected from it each tick. The fusion is the delta (G7), not any primitive.

## Reinventions to stop claiming (name the canonical technique)

- **Softmax/selection-pressure walk (#8)** = Boltzmann selective pressure (1991–93) + ε-greedy
  softmax (Sutton & Barto) + evolved temperature (PBT 2017). **G1, unanimous.** 20–35 yrs old.
- **Evolutionary population (#7)** = Population Based Training (DeepMind 2017), **G2 behavioral
  match.** "Self-adaptive mutation" is *degenerate* — `mutation_rate` is perturbed by a **fixed**
  `uniform(-0.02, 0.02)`, not log-normal self-scaling.
- **Homoiconic call-stack (#3)** = Recursive Transition Networks (Woods 1970), G2; SteP 2023 for LLMs.
- **Custodian genus (#12)** = MAPE-K (2003) + guarded-FSM (Harel 1987) + prototype delegation
  (Self, 1987); MetaAgent 2025 covers it in the LLM register.

## Aspirational gaps — claimed but NOT in the code (verified against source)

These are the ones that will sink a reviewer's confidence if claimed as built:

- **The learning loop is largely not running.** Bandit reward is *intentionally not wired* into the
  live gate (`bandit.py:57-64` docstring). The live consolidation is a flat `+0.1` usage counter — no
  penalty, no normalization, no forgetting — the **weakest** instantiation on the frontier.
- **Evolutionary fitness is a random stub:** `lifecycle.py:109` sets `accuracy = random.uniform(0.5,1.0)`.
  The reap/survive/reproduce loop currently **optimizes on noise.**
- **"Arbitrary-depth nesting" (#3) is not built:** the push path *overwrites* `call_stack` to a single
  frame (`lifecycle.py:264,301`) — real depth is capped at 1. A grandchild call destroys the
  grandparent frame.
- **J-Invariance "conservation law" + runtime J-drift gate (#11) are lore, not code** —
  grep returns nothing in `*.py`; they live in MYTH.md/DESIGN.md. `j_invariant.json` checks
  Ship-of-Theseus *structural* continuity, not a conserved quantity.
- **AIOS over-claim (#13):** Tier-2 enforcement is ~1100 lines of Python (not in-DB); only structural
  shape constraints ship in-DB; the `is_complete()` completeness oracle is spec'd 1:1 in DESIGN §12.5
  but has **no code.**
- **CANON/INPUT/TRACE provenance (#14) is prose**, not a graph type — the built firewall is the
  `:Wiki` write-ban + mandatory `domain/subdomain` (`gates.py:46-82`).
- **Custodian's real contributions are unbuilt** — the deductive SOMA closure gate and federating
  the Steward into CCC as a sibling are aspirational (DESIGN §2.1:165); zero `Steward` refs in code.

## Highest-leverage moves (to make the real novelty defensible)

1. **Lead any paper with the 403-as-typecheck inversion.** Position explicitly against the
   agent-security literature; run a small controlled study (steps-to-valid-write *with* the exact
   regex vs a generic 403); cite Safety Chip 2023 as the closest prior loop.
2. **Wire the learning before claiming learning.** Replace the random-stub fitness; wire
   `reward_delta` into the live gate; add penalty + normalization. Until then, drop every "it learns /
   frontier of agent optimization" framing — a reviewer who reads the code sinks it instantly.
3. **Fix the call-stack read-append** (3-line fix) → converts a flat reinvention into a small
   persisted-RTN-over-graph recombination, or downgrade the claim to "depth-1 persisted RTN."
4. **Convert "no shipped system does this" from asserted absence into a documented systematic search**
   — the fusion claims are only as strong as the absence proof.
5. **Foreground gate==scheduler as a named, micro-benchmarked primitive**; build `is_complete()` and
   move Tier-2 enforcement DB-resident so "ships as self-validating data" becomes true.
6. **Grade-discipline everywhere:** "an uncommon integration / a deliberate inversion," cited at
   G4–G7 — never "first dynamic prompt," "self-adaptive mutation," or "a conservation law."

## Caveats (from the completeness critic)

- Confidences are moderate (0.74–0.88). The most load-bearing deltas (graph-FSM fusion;
  constraint-leak-as-feature) rest on **asserted absence** found via search, not exhaustive proof.
- Several anchor papers are **2025–26 arXiv preprints at/past the Jan-2026 cutoff** (SCM, HAGE,
  ID-RAG, MetaAgent, BAMAS, KAIJU/PAuth), some snippet-verified rather than fully read. **Re-verify
  SCM (2604.20943) and KAIJU/PAuth before publishing any claim that pivots on them** — they drive the
  night-consolidation downgrade and the flagship 403-inversion claim respectively.
- **Cleanest missed prior art: GPTSwarm (Zhuge et al., ICML 2024, arXiv:2402.16823)** — learned edge
  weights over an LLM-agent graph — direct prior art for the entire weight cluster, absent from the
  run. Also worth adding: SGLang, LMQL, GraphRAG, RoleLLM.
- The **built-vs-aspirational splits are the trustworthy core** (grounded in verified source paths);
  the precise frontier-positioning of 2026 prior art is the soft layer.
