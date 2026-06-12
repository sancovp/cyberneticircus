# Rule: Provenance — every document is CANON, INPUT, or TRACE

## **Purpose**

Volume I suffered a **provenance collapse**: the Maker's reference material (Sanctuary System docs, shown as *examples of how to organize a world*) and the Maker's biography (the personal origin story of the J-Day concept) were compiled into world-canon surfaces (README, DESIGN preamble), and a Sanctuary-native toy (`ple_sm`, the "Primordial Love Engine") was seeded into the Cyberneticity as if it were a real procedure. An agent reading flat context cannot distinguish teaching-material from spec unless the boundary is marked. This rule marks it permanently.

This is the document-level generalization of `ontological-separation` (the Three Faces of Janus, Vol I ch23): face 1 = the Lore/graph, face 2 = the Compiler, face 3 = the Maker. Face-3 material is INPUT until the Maker explicitly promotes it.

## **MANDATORY: Constraints**

1. **Every document in this repository has exactly one provenance class:**
   - **CANON** — world-truth and system-truth. `DESIGN.md`, `README.md`, the `.agent/rules/`, the graph schema. Authoritative; agents build from it.
   - **INPUT** — the Maker's reference material, examples, inspirations, biography. Lives ONLY under `docs/inputs/`. Agents may *learn organizational patterns* from it but MUST NOT import its concepts, vocabulary, names, or narratives into CANON surfaces or into the graph.
   - **TRACE** — the development ledger (the Weights of Time chapters, scratchpads, session notes). Records what happened; never normative by itself. Realizations in TRACE become CANON only by being explicitly crystallized into a rule or DESIGN section.
2. **Default classification is INPUT.** When the Maker shares material conversationally ("here's how I think about X", "look at this thing I made elsewhere"), it is INPUT — flavor and teaching — unless the Maker says "make this canon."
3. **The Maker's biography is never world-canon.** How the Maker arrived at a concept (personal experiences, other projects) stays out of CANON surfaces; only the *concept itself*, stated neutrally, may be canonized.
4. **Foreign-project vocabulary is quarantined.** Sanctuary / TSS / SANC / IJEGU / Oliver Powers / Victory-Promise / PLE / GNOSYS / OPERA are Sanctuary-System terms (a different project of the Maker's). They appear nowhere in CANON or in the Cyberneticity graph. (`heaven-framework` / `sanctuary-dna` as *pip dependencies* are fine — they are infrastructure, not concepts; list them in install docs, never narrativize them.)
5. **When ingesting any new Maker-provided document, classify it FIRST** (ask if ambiguous), file it accordingly, and only then read it for content.

## **Why**

The cost of the collapse was a full decontamination session (Vol II ch29–31). The cost of prevention is one classification question per document.

## **How to apply**

- Before quoting or summarizing any document into README/DESIGN/graph: check its class. INPUT → stop, extract the *pattern* only, leave the *content*.
- Before seeding a StateMachine/Cybernet into the graph: its concepts must trace to CANON, or it gets a `toy_` prefix and a teardown note.
- **Method of cure differs by class** (see `jday-volumes`): contamination found in CANON is fixed by editing canon in place (with the removed material *moved* to `docs/inputs/`, never deleted); contamination found in TRACE is never edited out — it is reviewed and superseded by a commentary chapter in the next volume.

## **Triggers**

- Consult whenever: writing to README.md or DESIGN.md; seeding graph procedures; ingesting a document the Maker shares; noticing vocabulary in code/docs that has no CANON definition.
