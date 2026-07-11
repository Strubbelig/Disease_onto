# PRISMA-ScR Checklist — Completed

*Preferred Reporting Items for Systematic reviews and Meta-Analyses extension for Scoping Reviews (Tricco et al., 2018).*
Each of the 20 required items (+2 optional) is checked off against **How Is Disease Formally Modelled in Biomedical Ontologies? A Scoping Review** (`Scoping_Review_Manuscript_Disease_Modelling.md`), with the actual reporting text quoted. Items 13, 15, 16, 22, and 23 are **not applicable** to scoping reviews by design.

Legend: ✅ reported · ⚠️ reported with a noted caveat/deviation · ➖ not applicable (per PRISMA-ScR).

---

## Title

**Item 1 — Title.** *Identify the report as a scoping review.* — ✅

> **How Is Disease Formally Modelled in Biomedical Ontologies? A Scoping Review**

*Location: title line. The phrase "A Scoping Review" appears in the title; the PCC key elements (disease modelling / ontologies) are reflected per JBI guidance.*

---

## Abstract

**Item 2 — Structured summary.** *Background, objectives, eligibility criteria, sources of evidence, charting methods, results, conclusions.* — ✅

> **Objectives.** "To map how *disease* and its immediate conceptual neighbours … are formally defined and represented across biomedical ontologies and terminologies …"
> **Eligibility criteria.** "The unit of analysis is a formal account or artifact that makes an explicit ontological or formal-representational commitment about what a disease … is."
> **Sources of evidence.** "Ontology registries — BioPortal (primary), the Ontology Lookup Service (OLS), and the OBO Foundry … Most recent search executed July 2026."
> **Charting methods.** "The primary charting object was an OWL class in a purpose-built review ontology, not a spreadsheet row."
> **Results.** "145 were included as independent disease-model implementations … 90 of 145 included classes (62%) carry no identifiable commitment …"
> **Conclusions.** "Across the ontologies in active circulation, explicit and defensible disease modelling is the exception, not the rule."

*Location: Structured summary (all seven elements present: background, objectives, eligibility, sources, charting, results, conclusions).*

---

## Introduction

**Item 3 — Rationale.** *Rationale in the context of what is known; why a scoping review.* — ✅

> "Comparative treatments of these commitments do exist, but they appear almost exclusively as the motivating preamble to a specific new proposal … No independent review charts the *design space* itself …"
> "A scoping review is the appropriate instrument for three reasons … The corpus is **heterogeneous** … the question is a **mapping** question … and the goal is explicitly to **identify gaps** …"

*Location: Introduction → Rationale. Includes the four coupled design decisions (category, grounding of "pathological", crisp/graded, reality/classification) and the map of existing approaches (OGMS, River Flow/YAMATO, DOID/Mondo, BioTop) with their published critiques.*

**Item 4 — Objectives.** *Explicit questions/objectives with key elements (PCC).* — ✅

> "**Population / unit of analysis.** … a *formal account or artifact* … that defines or represents disease.
> **Concept.** An explicit ontological or formal-representational commitment about what a disease … *is* …
> **Context.** Biomedical and clinical knowledge representation, applied and formal ontology, and biomedical informatics …"
> "**Primary question.** How is *disease* … formally defined and represented across biomedical ontologies …?" (plus five secondary questions)

*Location: Introduction → Objectives. Uses the PCC framework explicitly.*

---

## Methods

**Item 5 — Protocol and registration.** *Whether a protocol exists, where accessible, registration.* — ⚠️

> "A protocol was drafted a priori (*Scoping Review Protocol — How Disease Is Formally Modelled in Ontologies*, v0.1), written to be registrable on the Open Science Framework and to conform to PRISMA-ScR … available from the authors and is intended for OSF registration with a dated changelog …"

*Location: Methods → Protocol and registration. Caveat: OSF registration is intended but a registration number is not yet issued; one protocol deviation (no completed dual-screening) is disclosed here and under Limitations.*

**Item 6 — Eligibility criteria.** *Characteristics used as eligibility criteria, with rationale.* — ✅

> "**Inclusion.** A source was eligible if it (I1) presented, formalised, critiqued, or substantially compared a definition or representation of disease … (I2) was any of: a peer-reviewed article; a full conference paper …; an **ontology artifact itself** …"
> "**Exclusion.** (E1) … tool use with no statement about the disease model; (E2) mathematical/simulation 'disease modelling' …; (E5) injury-only classes …"
> "The rationale for the language limit is feasibility with a declared exception for the German nosology-theory tradition …"

*Location: Methods → Eligibility criteria. Rationale provided for language limit and artifact-eligibility rules.*

**Item 7 — Information sources.** *All sources with coverage dates; date of most recent search.* — ⚠️

> "the primary information sources were **ontology registries**: **BioPortal** (primary), the **EBI Ontology Lookup Service (OLS)**, and the **OBO Foundry** … The protocol additionally names bibliographic databases (PubMed/MEDLINE, Scopus, Web of Science, ACM DL, IEEE Xplore, DBLP, PhilPapers) and hand-searched proceedings …"
> "The most recent registry search was executed in **July 2026**. Retrieval dates and ontology versions were recorded per class …"

*Location: Methods → Information sources. Caveat: this manuscript reports the completed artifact track; the literature-track search is ongoing (disclosed).*

**Item 8 — Search.** *Full electronic search strategy for ≥1 source, repeatable.* — ✅

> "The registry search used a **two-tier disease-neighbour term strategy** … **Primary (exact-label) tier.** Exact-label searches for … `disease`, `disorder`, `illness`, `condition`, `syndrome`, `pathological process`, `pathological disposition`, `dysfunction`. **Secondary (sensitivity) tier.** … `pathological condition`, `pathological state`, `disease state`, `pathologic process`, `morbid condition` … **Multilingual sensitivity pass.** … `maladie`, `trouble`, `condition pathologique`, `Krankheit`, `Erkrankung`, `Störung` …"

*Location: Methods → Search + Appendix A (seed set for known-item validation). The three AND-combined bibliographic blocks are also given in full.*

**Item 9 — Selection of sources of evidence.** *Process for screening/eligibility.* — ⚠️

> "Selection combined **automated screening** at the registry-appearance level with **manual class-level review**. Automated screens … implemented the protocol's artifact-eligibility rules and produced an auditable exclusion table for the flow diagram … Classes surviving these screens entered manual review through the review ontology (in Protégé) or the interactive pipeline reviewer …"

*Location: Methods → Selection of sources of evidence. Caveat: "Screening at this stage was performed by a single reviewer; a second-reviewer adjudication pass is planned but not yet complete."*

**Item 10 — Data charting process.** *Charting method; calibrated/tested forms; independent or duplicate.* — ⚠️

> "the **primary charting object is an OWL class in a review ontology, not a spreadsheet row** … a purpose-built review ontology (`disease_terms_review.ttl`) that imports (i) a core annotation-property ontology (`review_core.ttl` …) and (ii) a source module for each reviewed class … The charting form was piloted on 5–10 classes and revised iteratively (the Levac calibration step) before full charting."

*Location: Methods → Data charting process. Caveat: "Charting was performed by a single reviewer … the plan provides for a second reviewer with `disagreement_flag` and `adjudication_decision` fields, not yet exercised."*

**Item 11 — Data items.** *List and define all variables sought; assumptions/simplifications.* — ✅

> "For each charted class the following were sought … **Provenance / context** — `class_iri`, `preferred_label`, `source_ontology_ids`, `source_databases`, `ontology_versions`, retrieval date, `discovery_tier` … **Manual review annotations** — `ontology_type_manual` …; `disease_model_category`; four evidence-quality fields …; an integer `entity_quality_score` (0–3) …"
> "Key simplifying assumptions: (a) a class's disease-model commitment was read from its OWL … (b) imported copies of an IRI were not counted as independent implementations …; (c) thesauri and clinical terminologies … were treated as terminologies, not ontologies …"

*Location: Methods → Data items + Appendix B (full charting form and controlled value sets).*

**Item 12 (optional) — Critical appraisal of individual sources.** *If done: rationale, methods, use.* — ✅ (optional, performed in adapted form)

> "a lightweight **entity-quality assessment** was charted for each included class … the four evidence-quality dimensions … and a 0–3 `entity_quality_score` … This appraisal was used descriptively — to characterise how well the field grounds its disease classes — and not to weight or exclude sources beyond the eligibility rules already described."

*Location: Methods → Critical appraisal of individual sources of evidence.*

**Item 13 — Summary measures.** ➖ Not applicable for scoping reviews.

> "No meta-analysis, summary measures, additional analyses, or risk-of-bias-across-studies synthesis were performed, consistent with PRISMA-ScR items 13, 15, 16, 22, and 23 being not applicable to scoping reviews."

**Item 14 — Synthesis of results (methods).** *Methods of handling and summarising charted data.* — ✅

> "Synthesis combined **ontology-driven descriptive statistics** with a **narrative typology**. Charting annotations were tabulated to produce: (i) counts of included versus excluded classes …; (iii) the **disease-model typology** …; (iv) the **evidence-quality profile**; and (v) a **dependency/reuse analysis** … The planned **gap map** cross-tabulates disease-model category × grounding of 'pathological' × crisp/graded handling …"

*Location: Methods → Synthesis of results.*

**Item 15 — Risk of bias across studies.** ➖ Not applicable for scoping reviews. *(See item 13 statement.)*

**Item 16 — Additional analyses.** ➖ Not applicable for scoping reviews. *(See item 13 statement.)*

---

## Results

**Item 17 — Selection of sources of evidence.** *Numbers screened/eligible/included with exclusion reasons; ideally a flow diagram.* — ✅

> "Registry search … returned disease-neighbour candidate classes distributed over **282 source-ontology appearances** … After screening, **219 native candidate classes** entered manual class-level review. **145 (66%) were included** … and **74 (34%) were excluded**."
> Automated-screen exclusion table (per stage) and manual-exclusion reasons are given in full.

*Location: Results → Selection of sources of evidence. **Flow diagram: `Figures/prisma_scr_flow_diagram.png` / `.svg`**, generated dynamically by `Python scripts/make_prisma_flow_diagram.py`.*

**Item 18 — Characteristics of sources of evidence.** *Characteristics charted, with citations.* — ✅

> "the manually assigned resource types were: **curated ontology** (138), **clinical terminology** (21), **thesaurus** (19), **value set** (2) … By IRI provenance, **222** classes were native … and **25** were imported/reused. … the single largest contributor was **IRAEO** … (15 included classes) …"

*Location: Results → Characteristics of sources of evidence.*

**Item 19 (optional) — Critical appraisal within sources of evidence.** *If done, present appraisal data.* — ✅ (optional)

> "Among included classes, definition quality was **absent (64), partial (48), poor (17), good (11)** … Entity-quality scores were correspondingly low: **109** classes scored 1 …, **24** scored 2, and only **2** scored 3."

*Location: Results → Synthesis of results → "Evidence quality".*

**Item 20 — Results of individual sources of evidence.** *Relevant charted data per source, tied to questions.* — ✅

> "The durable per-class results live in the review ontology and its generated tables … which record, for every included class, its IRI, native ontology, resolved definition and parentage, the free-text upper-level interpretation, the assigned model category, the four quality ratings, and the entity-quality score." (with representative per-class interpretations quoted)

*Location: Results → Results of individual sources of evidence. Full per-class table: `disease_terms_manual_annotations.csv` / `disease_terms_review_enriched.csv`.*

**Item 21 — Synthesis of results.** *Charting results summarised against questions/objectives.* — ✅

> "The single most important finding is the **prevalence of ungrounded modelling** … **90 of 145 (62%)** included classes carry **no identifiable ontological commitment** … the **realizable-entity/disposition family dominates** (24 classes) … with **process** a distant second (8)."
> "**Evidence-gap statement.** … the clearest under-served combinations are: (a) **process-based models with an explicit grounding of 'pathological'** …; (b) **graded or context-indexed models with any explicit upper-level commitment** …; (c) **explicitly state-based … models with formal axioms** …"

*Location: Results → Synthesis of results (typology table, secondary-question answers, dependency/reuse analysis, gap statement).*

**Item 22 — Risk of bias across studies.** ➖ Not applicable for scoping reviews.

**Item 23 — Additional analyses.** ➖ Not applicable for scoping reviews.

---

## Discussion

**Item 24 — Summary of evidence.** *Summarise main results, link to questions, relevance to key groups.* — ✅

> "Three findings stand out. First, **explicit ontological grounding of disease is the exception** … Second, **where grounding exists it is overwhelmingly BFO-flavoured** … Third, **the ecosystem is centralised** …"
> "For … **ontology builders** … **data integrators** … and **standards bodies** …"

*Location: Discussion → Summary of evidence.*

**Item 25 — Limitations.** *Limitations of the scoping review process.* — ✅

> "**(1) Single-reviewer charting.** … inter-rater reliability is not reported. **(2) Artifact track only.** … the literature track … is not fully integrated here … **(3) Registry coverage and label dependence.** … **(4) Interpretation of implicit commitments.** … **(5) Language scope.** … **(6) Snapshot.** … the counts reflect the July 2026 registry state …"

*Location: Discussion → Limitations (six process limitations, including the protocol deviation).*

**Item 26 — Conclusions.** *General interpretation vs questions/objectives; implications/next steps.* — ✅

> "Across the biomedical ontologies in circulation, disease is more often *labelled* than *modelled* … this argues for consolidating on, and properly citing, a small set of grounded reference models rather than minting new bare classes … A natural next step is a focused synthesis of the critique literature … and completion of the dual-review and literature-track charting."

*Location: Discussion → Conclusions.*

**Item 27 — Funding.** *Funding for included sources and for the review; role of funders.* — ✅

> "No dedicated external funding supported this scoping review. Sources of funding for the included sources of evidence … were not systematically charted in the artifact track and vary by resource … The authors declare no role of any funder in the design, conduct, or reporting of this review."

*Location: Discussion → Funding.*

---

## Summary

| Status | Items |
|---|---|
| ✅ Reported | 1, 2, 3, 4, 6, 8, 11, 12, 14, 17, 18, 19, 20, 21, 24, 25, 26, 27 |
| ⚠️ Reported with caveat/deviation | 5 (registration pending), 7 (literature track ongoing), 9 & 10 (single reviewer) |
| ➖ Not applicable (per PRISMA-ScR) | 13, 15, 16, 22, 23 |

**All 20 required items and both optional items (12, 19) are addressed.** The three caveats are transparently disclosed in the manuscript and reflect that this is a single-reviewer, artifact-track first draft with OSF registration intended.

*Flow diagram regenerates from live data via `python3 "Scoping review/Python scripts/make_prisma_flow_diagram.py"`.*
