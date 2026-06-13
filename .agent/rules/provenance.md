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
4. **Sanctuary is the SUPERORDINATE layer, not foreign junk — but it is staged.** Correction (Maker, 2026-06-12): the Sanctuary System is NOT a separate project to discard; it is the Maker's top-level language that **compiles onto this Jani substrate** (Sanctuary `PRODUCES` Journeys; a Journey `IS A` VEC link; the VEC = Universal Chain Ontology is the chain above; Sanctuary `COMPILES ONTO` CybernetiCircus). The Jani/CybernetiCircus corpus is *preliminary substrate*. So the original sin was never "Sanctuary is junk" — it was **unmapped premature leakage**: Sanctuary terms appearing in Jani-substrate canon *before the compile-mapping between the layers is defined*. Discipline therefore = **staging, not banishment**: keep Sanctuary vocabulary (TSS / SANC / IJEGU / Oliver Powers / Olivus Victory-Promise / PLE / GNOSYS / OPERA) out of *substrate* CANON and the graph UNTIL the Sanctuary→Jani compile boundary is specified, at which point it is promoted by mapping, not quarantined. Explicit standing exceptions the Maker has confirmed canonical-at-the-Sanctuary-layer: **VEC stays** (the Math/Polysemic shells' IJEGU/VEC are the top ontology surfacing, not contamination); **PLE is a real Sanctuary concept** (the collaborative two-Cybernet rite ≡ the Raid primitive) — `ple_sm` was deleted only as a malformed *substrate node*, not as a rejected concept; it returns when the collaborative-mint layer is built. (`heaven-framework` / `sanctuary-dna` as *pip dependencies* remain plain infrastructure; list them in install docs, never narrativize.)
5. **When ingesting any new Maker-provided document, classify it FIRST** (ask if ambiguous), file it accordingly, and only then read it for content.

## **Why**

The cost of the collapse was a full decontamination session (Vol II ch29–31). The cost of prevention is one classification question per document.

## **How to apply**

- Before quoting or summarizing any document into README/DESIGN/graph: check its class. INPUT → stop, extract the *pattern* only, leave the *content*.
- Before seeding a StateMachine/Cybernet into the graph: its concepts must trace to CANON, or it gets a `toy_` prefix and a teardown note.
- **Method of cure differs by class** (see `jday-volumes`): contamination found in CANON is fixed by editing canon in place (with the removed material *moved* to `docs/inputs/`, never deleted); contamination found in TRACE is never edited out — it is reviewed and superseded by a commentary chapter in the next volume.

## **Triggers**

- Consult whenever: writing to README.md or DESIGN.md; seeding graph procedures; ingesting a document the Maker shares; noticing vocabulary in code/docs that has no CANON definition.
