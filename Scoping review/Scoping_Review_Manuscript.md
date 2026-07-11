# How Is Disease Formally Modelled in Biomedical Ontologies? A Scoping Review

*Draft manuscript, v0.1. Reported in accordance with the PRISMA Extension for Scoping Reviews (PRISMA-ScR; Tricco et al., 2018).*

---

## Structured summary

**Background.** How a biomedical ontology commits to *what kind of entity a disease is* — a disposition, a process, a state, a clinical finding, or a deliberately under-committed category — determines how the ontology classifies, reasons over, and interoperates with disease data. Yet comparative treatments of these commitments exist almost exclusively as preambles to specific proposals (OGMS's disposition, the River Flow Model's causal chains, BioTop's "condition" pattern), and no independent review charts the design space across the ontologies actually in circulation.

**Objectives.** To map how *disease* and its immediate conceptual neighbours (disorder, condition, syndrome, pathological process, abnormal state) are formally defined and represented across biomedical ontologies and terminologies, and to identify which upper-level design commitments distinguish these representations, how well they are grounded, and where the design space is empty.

**Eligibility criteria.** The unit of analysis is a formal account or artifact that makes an explicit ontological or formal-representational commitment about what a disease (or disorder/condition/syndrome/pathological process/abnormal state) is. Ontology artifacts with resolvable class IRIs, definitions, and hierarchy were charted directly. Injury-only classes, mathematical/epidemiological "disease modelling", and imported copies of a class defined elsewhere were excluded from independent analysis.

**Sources of evidence.** Ontology registries — BioPortal (primary), the Ontology Lookup Service (OLS), and the OBO Foundry — searched with a two-tier disease-neighbour term strategy, supplemented by targeted registry and repository look-ups. Most recent search executed July 2026.

**Charting methods.** The primary charting object was an OWL class in a purpose-built review ontology, not a spreadsheet row. Each candidate class was resolved through an imported source module (labels, definitions, superclasses, axioms) and annotated with controlled `rev:*` review properties covering ontology type, native/imported provenance, upper-level interpretation, disease-model category, and four evidence-quality dimensions.

**Results.** Registry search returned candidate disease-neighbour classes across ~157 source ontologies (282 source-ontology appearances). After automated provenance, term-scope, target-refinement, semantic-equivalence and dependency screens, 219 native candidate classes entered manual class-level review; 145 were included as independent disease-model implementations and 74 were excluded (most commonly as clinical terminologies/thesauri rather than ontologies, or as out-of-scope). The dominant finding is an **absence of ontological grounding**: 90 of 145 included classes (62%) carry no identifiable commitment to what kind of entity a disease is (`no_grounded_model`). Where a commitment was identifiable, the largest group modelled disease as a **BFO disposition/realizable entity** (24 classes), followed by **process** (8), and small numbers of state-, condition-, quality-, and finding-based models. Definitions were absent or poor for 81 of 145 included classes; only 11 (8%) were rated *good*. Reuse is concentrated: 153 of the 282 source appearances were dependency-only (no independent model of their own), depending overwhelmingly on **OGMS**, **DOID**, and **MONDO**.

**Conclusions.** Across the ontologies in active circulation, explicit and defensible disease modelling is the exception, not the rule. A small number of reference ontologies (OGMS, DOID, MONDO) carry the semantic weight for the entire ecosystem through import and reuse, while the majority of resources reproduce a disease-like class with little or no upper-level commitment. The evidence-gap map identifies under-served combinations — notably graded/contextual and process-based models with explicit grounding of "pathological" — as the clearest opportunities for future ontology-engineering work.

---

## Introduction

### Rationale

Every biomedical ontology that contains a class for *disease*, *disorder*, or *condition* implicitly answers a question that the philosophy of medicine has debated for decades: what kind of thing, ontologically, is a disease? Is it a disposition borne by an organism (as in the Ontology for General Medical Science, OGMS), a process or causal chain unfolding over time (as in Mizoguchi's River Flow Model), a state or configuration of circumstances, a structural disorder of a bodily component, or simply a label in a classification with no commitment at all? This choice is not academic. It determines whether disease instances are continuants or occurrents, whether they can bear qualities and participate in processes, how they relate to signs, symptoms, and diagnoses, and — crucially for data integration — whether two resources that both use the word "disorder" are actually talking about the same category of entity.

Any ontology that represents disease is, whether or not its authors notice, forced into a position on four coupled design decisions that the theoretical literature has isolated. **(1) Ontological category:** is a disease a continuant (a state, disposition, or material entity that persists through change) or an occurrent (a process or causal chain that unfolds)? Grenon & Smith's SNAP/SPAN split makes this a forced choice in BFO, whereas Mizoguchi denies the choice is clean. **(2) Grounding of "pathological/abnormal":** what makes a bearer pathological — statistically sub-normal function (Boorse's biostatistical theory), evolutionary dysfunction (Wakefield's harmful-dysfunction hybrid), harm or disvalue (normativism), or a primitive, criteria-defined "pathologicity" (Hucklenbroich)? Every formal ontology *imports* an answer from the philosophy of medicine, and almost none states which. **(3) Crisp vs graded:** are disease classes crisp universals with necessary-and-sufficient conditions, or inherently vague, prototype-based sets (Sadegh-Zadeh)? A pure OWL/DL ontology structurally cannot represent graded membership, so this must be decided up front. **(4) Reality vs classification:** does "disease" denote the underlying biological state, the practical illness role, a nosological category, or a precision-medicine stratification (Boorse's disease/illness distinction; Ereshefsky's state-description/normative-claim split; Haendel et al.'s precision-medicine framing)? These uses come apart, and conflating them is a recurrent failure mode.

Comparative treatments of these commitments do exist, but they appear almost exclusively as the motivating preamble to a specific new proposal, and each carries published critiques that are equally scattered. **OGMS/BFO** models disease as a *disposition* to undergo pathological processes, existing because of a material *disorder* — a realist model whose main virtue is representing pre-clinical disease, but which Röhl & Jansen argue cannot coherently represent *malfunction* (having a function but lacking the matching disposition), which Jansen argues represents graded *tendencies* badly, and which Hucklenbroich argues merely relocates the undefined primitive "pathological". The **River Flow Model / YAMATO** lineage models disease as a persisting entity *individuated by a causal chain* of pathological processes and states — recovering the causal structure clinicians reason with, at the cost of a non-OBO-mainstream top-level and admittedly under-determined identity conditions for the chain. **DOID and Mondo** are pragmatic classification resources: Mondo's root literally imports the OGMS disposition definition, yet its working identity criterion for a disease is a clinical four-fold of etiology, phenotype, natural history, and treatment response — and the two are never reconciled, so the metaphysics is, in effect, decorative. **BioTop** introduces a deliberately under-committed "condition" as a design pattern. Each proposal is valuable but partisan, and no independent review charts the *design space* itself — the set of commitments actually made by the ontologies in circulation — and evaluates how well those commitments are grounded and where they leave gaps.

This produces three concrete problems. First, new ontology builders re-litigate the same continuant/occurrent and disposition/process choices from scratch, unaware of what has already been tried. Second, interoperability suffers, because the same label ("disorder", "disease", "condition") denotes different ontological categories across resources, and importers rarely notice. Third, the published critiques of each approach are scattered across venues and framed to advance a competing proposal, so there is no neutral map a builder can consult.

A scoping review is the appropriate instrument for three reasons that align directly with the purpose statements in the PRISMA-ScR and JBI guidance. The corpus is **heterogeneous** — it mixes journal papers, conference proceedings, ontology artifacts, and clinical standards, which no single database indexes uniformly. The question is a **mapping** question ("what is the nature and extent of disease-modelling commitments across ontologies?"), not an effect-estimation question, so a systematic review with meta-analysis and risk-of-bias appraisal would be ill-fitted. And the goal is explicitly to **identify gaps** in a design space to guide future work, which is a canonical scoping-review objective.

### Objectives

Following the Population–Concept–Context (PCC) framework recommended for scoping reviews:

- **Population / unit of analysis.** Not a clinical population; the unit is a *formal account or artifact* (an ontology class, an axiom pattern, a design proposal, or a documented critique) that defines or represents disease.
- **Concept.** An explicit ontological or formal-representational commitment about what a disease — or its immediate neighbours disorder, condition, syndrome, pathological process, or abnormal state — *is*: a definition, an axiomatisation, a superclass placement, a design pattern, or a critique thereof.
- **Context.** Biomedical and clinical knowledge representation, applied and formal ontology, and biomedical informatics; philosophy of medicine only where it is directly cited by or informs a formal model.

**Primary question.** How is *disease* (and its immediate neighbours) formally defined and represented across biomedical ontologies and ontology-engineering proposals, and what design commitments distinguish these approaches?

**Secondary questions.**

1. To which top-level/foundational ontology (BFO, DOLCE, YAMATO, BioTop, GFO, none) does each approach commit, and how does that constrain the disease model?
2. To which ontological category is *disease* assigned (continuant/disposition, occurrent/process, causal chain, material structure, state, finding, or deliberately under-committed)?
3. How well is the load-bearing primitive "abnormal/pathological" grounded (statistical, evolutionary/function, normative, primitive-criteria, or left undefined)?
4. How are variation, gradedness, and uncertainty handled (crisp DL classes, graded/fuzzy, or pushed to data/annotation)?
5. Where is the design space empty — which combinations of commitments are under-served?

---

## Methods

### Protocol and registration

A protocol was drafted a priori (*Scoping Review Protocol — How Disease Is Formally Modelled in Ontologies*, v0.1), written to be registrable on the Open Science Framework and to conform to PRISMA-ScR. The protocol specifies the rationale, PCC eligibility criteria, information sources, the two-tier registry search strategy, the ontology-based charting model, and the synthesis plan; it is available from the authors and is intended for OSF registration with a dated changelog for any amendments. This manuscript reports one deviation from the drafted protocol, noted under Limitations: no formal second-reviewer dual-screening round has yet been completed, so agreement statistics (κ) are not reported.

### Eligibility criteria

**Inclusion.** A source was eligible if it (I1) presented, formalised, critiqued, or substantially compared a definition or representation of disease in an ontology, terminology, or formal framework; and (I2) was any of: a peer-reviewed article; a full conference paper (ICBO, FOIS, JOWO, MEDINFO, AMIA, KR-MED); a book or chapter; an **ontology artifact itself** (with resolvable documentation and IRIs); or standards documentation stating a disease model. The literature strand was English-language, with German retained for the Hucklenbroich/*Krankheitstheorie* tradition (I3); no date restriction was applied (I4), as the foundational moves predate 2000.

For **ontology artifacts**, the eligible unit was a native class whose IRI namespace belongs to the reporting ontology and that resolves to labels, definitions, and hierarchy through an imported module.

**Exclusion.** (E1) Ontologies that use a disease class purely as a tool (gene–disease association, NLP, clinical decision support) with no statement about the disease model itself; (E2) clinical/epidemiological "disease modelling" in the mathematical/simulation sense (compartmental models), a homonym flagged explicitly because the keyword retrieves it; (E3) pure philosophy of medicine with no connection to a formal representation; (E4) abstracts/posters without a retrievable full account; and (E5) injury-only classes, which are clinically related to disease but are not disease synonyms and typically carry a different modelling commitment.

The rationale for the language limit is feasibility with a declared exception for the German nosology-theory tradition; the rationale for the artifact-eligibility rules is that ontology registries systematically report the *same* class IRI in many ontologies through import, and counting those copies as independent commitments would inflate the map (see *Data charting process*).

### Information sources

Because disease-modelling knowledge lives partly in artifacts rather than papers, the primary information sources were **ontology registries**: **BioPortal** (primary), the **EBI Ontology Lookup Service (OLS)**, and the **OBO Foundry**, supplemented by direct retrieval of specific ontology IRIs. These registries index hundreds of biomedical ontologies and expose class-level metadata (labels, definitions, parents, mappings) through APIs, enabling programmatic extraction. The protocol additionally names bibliographic databases (PubMed/MEDLINE, Scopus, Web of Science, ACM DL, IEEE Xplore, DBLP, PhilPapers) and hand-searched proceedings (ICBO, FOIS, JOWO, KR-MED, ODLS, MEDINFO, AMIA, SWAT4HCLS) for the literature strand, plus backward/forward citation chasing on a seed set and known-author tracking (Smith, Ceusters, Schulz, Jansen, Mizoguchi, Hoehndorf, Schriml, Hucklenbroich). This manuscript reports the **artifact track**, which is complete; the literature-track charting is ongoing.

The most recent registry search was executed in **July 2026**. Retrieval dates and ontology versions were recorded per class in the extraction tables.

### Search

The registry search used a **two-tier disease-neighbour term strategy**, adapted per registry and recorded in full in the extraction pipeline (`review_extraction_pipeline.py`).

**Primary (exact-label) tier.** Exact-label searches for the main disease-neighbour terms: `disease`, `disorder`, `illness`, `condition`, `syndrome`, `pathological process`, `pathological disposition`, `dysfunction`.

**Secondary (sensitivity) tier.** To reduce false negatives from alternative root labels, broad supplementary terms (`pathological condition`, `pathological state`, `disease state`, `pathologic process`, `morbid condition`) were searched but retained only for source ontologies that had no primary-term hit. Specific compound labels (`DiseaseDisorderOrFinding`, `Disease or disorder`, `Disease or syndrome`, `Disorder or finding`, `Clinical finding or disorder`) were retained as candidate disease-root classes. Secondary-tier hits were tagged `discovery_tier = secondary_compound_label_sensitivity`.

**Multilingual sensitivity pass.** For artifacts only, a small French/German label pass (`maladie`, `trouble`, `condition pathologique`, `Krankheit`, `Erkrankung`, `Störung`) was run and tagged `discovery_tier = multilingual_label_sensitivity`; this does not change the literature-track language scope but recognises formally inspectable non-English-labelled classes.

The conceptual model behind the string mirrors the protocol's three AND-combined blocks — a **disease block** (disease OR disorder OR "pathological process" OR "abnormal state" OR nosolog\* OR pathologic\*), an **ontology block** (ontolog\* OR "knowledge representation" OR "formal definition" OR axiom\* OR "description logic" OR OWL OR BFO OR DOLCE OR OGMS OR taxonom\*), and a **commitment block** (disposition OR continuant OR occurrent OR "causal chain" OR process OR realiz\* OR "definition of disease" OR represent\*) — applied to the bibliographic databases. The seed set of known formal-model papers and reference ontologies (Appendix A) served as a known-item validation: a sufficient strategy must retrieve all of them.

### Selection of sources of evidence

Selection combined **automated screening** at the registry-appearance level with **manual class-level review**.

Automated screens, applied in the extraction pipeline before human review, implemented the protocol's artifact-eligibility rules and produced an auditable exclusion table for the flow diagram:

- **Provenance screen** — classes with unstable/local IRIs (e.g. `webprotege.stanford.edu` random IRIs) were removed as lacking reproducible provenance.
- **Source-type screen** — value-set collections (e.g. `VALUESETS`) were removed as not independent ontologies.
- **Term-scope screen** — `injury`, `predisposition`, `disease course`, and similar non-synonyms were removed (E5); a `pathological process` class was suppressed when the same ontology carried a stronger disease-root class, and retained only where it was the sole process-based candidate.
- **Target-refinement screen** — where manual hierarchy inspection identified a better native disease-model candidate in the same ontology, the initial label hit was replaced (recorded as `replaced_by_better_native_disease_model_candidate`); a `syndrome` class was suppressed when a `disease`/`disorder` class was present in the same ontology.
- **Semantic-equivalence and provenance screens** — classes declaring `skos:exactMatch` to a canonical disease root (DOID_4, MONDO_0000001, OGMS_0000031) or `rdfs:isDefinedBy`/namespace pointing to an external ontology were treated as reuses, not independent models, and routed to the native provider for analysis.
- **Dependency/reuse screen** — appearances of a class IRI in an ontology that merely imports it were listed as dependency appearances, with the native ontology recorded for analysis.

Classes surviving these screens entered manual review through the review ontology (in Protégé) or the interactive pipeline reviewer, which prints an evidence packet (labels, definition, comments, synonyms, parentage, provenance) for one class and records the controlled-value annotations. Screening at this stage was performed by a single reviewer; a second-reviewer adjudication pass is planned but not yet complete.

### Data charting process

Consistent with Arksey & O'Malley, Levac et al., and JBI guidance, extraction is termed **charting**. The distinctive feature of this review is that **the primary charting object is an OWL class in a review ontology, not a spreadsheet row**. Each reviewed disease/disorder/condition/syndrome/abnormal-state/fallback-process class is represented by its class IRI in a purpose-built review ontology (`disease_terms_review.ttl`) that imports (i) a core annotation-property ontology (`review_core.ttl`, namespace `https://example.org/disease-review/ap/`) defining every `rev:*` field and its controlled values, and (ii) a source module for each reviewed class providing labels, definitions, parentage, and axioms. This keeps the durable review record in an inspectable, MIREOT-style ontology rather than in a flat table; CSV views (`disease_terms_review_enriched.csv`, `disease_terms_manual_annotations.csv`) are generated only for batch editing, QA, and reporting and are synchronised back to the ontology by class IRI.

The charting form was piloted on 5–10 classes and revised iteratively (the Levac calibration step) before full charting. Because the review key is the class IRI, a class appearing in several registries or ontologies is charted once, with its appearances recorded as provenance (`source_ontology_ids`, `source_databases`) rather than as duplicate rows. Charting was performed by a single reviewer using the controlled vocabulary; the plan provides for a second reviewer with `disagreement_flag` and `adjudication_decision` fields, not yet exercised.

### Data items

For each charted class the following were sought (full definitions in `review_core.ttl`):

- **Provenance / context** — `class_iri`, `preferred_label`, `source_ontology_ids`, `source_databases`, `ontology_versions`, retrieval date, `discovery_tier`, ontology title/status/homepage/licence.
- **Evidence resolved through imported modules** — definition, comments, synonyms, `parent_labels`/`parent_iris`, `bfo_anchor`, mapping count, `exact_match_iris`, `defined_by_iris`, `conforms_to_iris`.
- **Manual review annotations** — `ontology_type_manual` (curated ontology / clinical terminology / thesaurus / value set / application ontology / demo / generated / unclear); `native_or_imported_manual`; `review_route` (independent vs dependency-only); `manual_include_status` (include / exclude / maybe / needs\_second\_review) and `manual_exclusion_reason`; a free-text `upper_level_interpretation`; an optional controlled `disease_model_category`; four evidence-quality fields (`definition_quality`, `comment_quality`, `parentage_quality`, `provenance_quality`, each good/partial/poor/absent); an integer `entity_quality_score` (0–3); and audit fields (`reviewer`, `review_date`, second-reviewer fields, `review_notes`).

The controlled `disease_model_category` buckets are synthesis aids, assigned only after the free-text interpretation and left blank where the source's own model was more precise than the available buckets. Key simplifying assumptions: (a) a class's disease-model commitment was read from its OWL — superclass placement and axioms — and not only from its prose, because the continuant/occurrent choice is often implicit in the axioms; (b) imported copies of an IRI were not counted as independent implementations unless the analysis was explicitly about reuse; and (c) thesauri and clinical terminologies (NCIT, MeSH, UMLS Metathesaurus for this review) were treated as terminologies, not ontologies, and excluded from independent modelling assessment even when otherwise eligible.

### Critical appraisal of individual sources of evidence

Formal risk-of-bias appraisal is not meaningful for conceptual sources and is not applicable to scoping reviews. In its place, and consistent with the optional critical-appraisal provision (PRISMA-ScR item 12), a lightweight **entity-quality assessment** was charted for each included class to support the synthesis: the four evidence-quality dimensions above and a 0–3 `entity_quality_score` capturing whether the class is clearly defined, relevantly placed, and structurally interpretable. A prefill rule set the score to 1 when definition, comment, and parent evidence were all absent. This appraisal was used descriptively — to characterise how well the field grounds its disease classes — and not to weight or exclude sources beyond the eligibility rules already described.

### Synthesis of results

Synthesis combined **ontology-driven descriptive statistics** with a **narrative typology**. Charting annotations were tabulated to produce: (i) counts of included versus excluded classes with reasons; (ii) the distribution of `ontology_type_manual` and native/imported provenance; (iii) the **disease-model typology** (the distribution of `disease_model_category` and the free-text interpretations); (iv) the **evidence-quality profile**; and (v) a **dependency/reuse analysis** cross-tabulating independent-analysis versus dependency-only appearance routes and the ontologies depended upon. The planned **gap map** cross-tabulates disease-model category × grounding of "pathological" × crisp/graded handling to surface populated versus empty cells. No meta-analysis, summary measures, additional analyses, or risk-of-bias-across-studies synthesis were performed, consistent with PRISMA-ScR items 13, 15, 16, 22, and 23 being not applicable to scoping reviews.

---

## Results

### Selection of sources of evidence

Registry search across BioPortal, OLS, and the OBO Foundry returned disease-neighbour candidate classes distributed over **282 source-ontology appearances** (registry contexts); after de-duplication to unique class IRIs, the **271 charted candidate classes** were drawn from approximately **157 distinct source ontologies**. The great majority of appearances were retrieved from BioPortal, with smaller numbers from OLS, the OBO Foundry, and direct IRI retrieval.

Automated screening removed appearances at the following stages (counts as source-ontology appearances / distinct source ontologies / distinct class IRIs):

| Screen | Reason code | Appearances | Ontologies | Class IRIs |
|---|---|---:|---:|---:|
| Provenance | Unstable/local (webProtégé) IRI | 5 | 5 | 3 |
| Source type | Value-set collection, not an ontology | 1 | 1 | 1 |
| Term scope | Out of scope (not a disease synonym; e.g. injury) | 80 | 74 | 40 |
| Term scope | `pathological process` suppressed when a disease root is present | 13 | 11 | 11 |
| Target refinement | Replaced by a better native disease-model candidate | 63 | 58 | 6 |
| Target refinement | `syndrome` suppressed when a `disease` class is present | 32 | 30 | 13 |
| Semantic equivalence | Explicit `skos:exactMatch` to a canonical disease root | 4 | 4 | 2 |
| Semantic provenance | Defined by an external class (no independent analysis) | 2 | 1 | 2 |
| Dependency/reuse | Imported/reused term (no independent analysis) | 22 | 18 | 11 |

Of the **282 appearances**, **103** were routed for independent analysis, **153** were dependency-only (the class is imported/reused, so the model is analysed at its native provider), **20** carried a mix of independent and dependency appearances, and **6** had an unknown namespace needing manual namespace resolution.

After screening, **219 native candidate classes** entered manual class-level review. **145 (66%) were included** as independent disease-model implementations eligible for substantive synthesis, and **74 (34%) were excluded**. Manual exclusion reasons were: replaced by a better native candidate (27), clinical terminology/thesaurus rather than ontology (24), out of scope (18), value-set/collection (3), duplicate imported term (1), and demo/training resource (1). *(A PRISMA-ScR flow diagram assembling these stages — identification, automated screening, manual eligibility, and inclusion — should accompany the final manuscript; all counts above are drawn from the machine-generated exclusion table `ontology_source_exclusion_counts_for_flow_figure.csv` and the manual annotation table.)*

### Characteristics of sources of evidence

Among the reviewed classes, the manually assigned resource types were: **curated ontology** (138), **clinical terminology** (21), **thesaurus** (19), **value set** (2), plus single unclear and demo cases. By IRI provenance, **222** classes were native to their reporting ontology and **25** were imported/reused. Included disease-model classes were contributed by a long tail of ontologies; the single largest contributor was **IRAEO** (the Immune-Related Adverse Event Ontology, 15 included classes, reflecting a BFO-disposition legacy), followed by ontologies such as **GSSO**, **CODO**, **NIFSTD**, **BERO**, **BioTop**, **EFO**, and **ORDO**, each contributing a small number. The distribution is markedly long-tailed: most contributing ontologies supplied only one or two disease-model classes.

The reference ontologies that anchor the ecosystem appear less as independent rows than as **dependency targets**. Of the 153 dependency-only appearances, the ontologies most frequently depended upon were **OGMS** (named in ~74 appearances, alone or with DOID), **DOID** (~38), the UMLS Semantic Type network **STY** (25), and **MONDO** (9), with smaller counts for **SIO** and **NCIT**. In other words, a handful of reference resources carry the disease-modelling commitments that the wider ecosystem imports.

### Results of individual sources of evidence

The durable per-class results live in the review ontology and its generated tables (`disease_terms_review_enriched.csv`, `disease_terms_manual_annotations.csv`), which record, for every included class, its IRI, native ontology, resolved definition and parentage, the free-text upper-level interpretation, the assigned model category, the four quality ratings, and the entity-quality score. Representative interpretations illustrate the range:

- **Grounded, BFO-legacy models.** Several classes are cleanly placed as "subclass of disposition, clear BFO legacy" — typically OBO-library ontologies inheriting the OGMS pattern (e.g. the IRAEO adverse-event classes).
- **Under-committed condition patterns.** BioTop-style classes model a medical condition as a subclass of *Particular* (BioTop's sole child of `owl:Thing`) — a pragmatic solution the reviewer characterised as "understandable [but] not very ontological".
- **Terminology masquerading as ontology.** Multiple classes sit in shallow, weakly-informative hierarchies (e.g. `Condition is_a Characteristic is_a Diagnostic_factor is_a Thing`) that "seem more like a thesaurus … than a real ontology".
- **Home-made / data-schema artifacts.** Several `Condition` classes were created to store hospital or clinical-trial-registry diagnostic data, with SNOMED/UMLS codes stuffed into notes and no definition, comment, or expressive superclass.
- **Broken subsumption.** Some classes exhibit incoherent `is_a` chains (e.g. a health `Condition` placed under `acidity`, or a `Clinical finding` placed under `bfo:Process`), indicating class/hierarchy confusion rather than a deliberate model.

These per-class notes are the qualitative backbone of the typology below and are available in full in the annotation table.

### Synthesis of results

**Disease-model typology (145 included classes).** The single most important finding is the **prevalence of ungrounded modelling**. Assigned model categories were:

| Disease-model category | Included classes |
|---|---:|
| No grounded model (terminology/classification category, no commitment) | 90 |
| Disposition (BFO) | 18 |
| Process / course of events (BFO occurrent) | 8 |
| Kantian state (a way a bearer is determined) | 4 |
| Realizable entity (BFO) | 3 |
| Dependent continuant | 3 |
| BioTop-style condition (under-committed) | 3 |
| Quality (SIO) | 2 |
| Disorder (structural, OGMS-style) | 1 |
| Clinical finding | 1 |
| Mixed model | 1 |
| Unclear / not yet categorisable | 4 |
| Not assigned (model more precise than available buckets) | 7 |

Grouping these, **90 of 145 (62%)** included classes carry **no identifiable ontological commitment** to what a disease is; only **44 (30%)** express a grounded, identifiable model, and of those the **realizable-entity/disposition family dominates** (24 classes, combining the disposition, realizable-entity, and dependent-continuant readings), with **process** a distant second (8). Explicitly state-, quality-, disorder-, and finding-based models are rare (≤4 each). This is the headline of the map: the design space is real and diverse, but it is thinly populated, and the modal ontology commits to nothing at all.

**Foundational-ontology commitment (secondary question 1).** The grounded classes cluster around **BFO** — via the OGMS disposition pattern for the disposition/realizable-entity family and via BFO process for the process family — with a small **BioTop** contingent (the "condition" pattern) and isolated **SIO** quality models. DOLCE, GFO, and YAMATO did not surface as commitments among the artifact-track classes reviewed here; the Mizoguchi/Hozo River-Flow and YAMATO lineage is expected in the literature track rather than as directly registry-retrievable classes.

**Grounding of "pathological/abnormal" (secondary question 3).** Almost no included class grounded the load-bearing primitive "abnormal/pathological" explicitly. Where definitions existed, they typically deferred to an external vocabulary (NCIT, HL7, SNOMED) or restated the label; statistical (Boorse), evolutionary-function, normative, and primitive-criteria (Hucklenbroich) groundings were essentially absent from the artifacts. This is itself a gap-map finding: the philosophical work on grounding pathology has not propagated into the ontologies.

**Crisp vs graded and uncertainty (secondary question 4).** All reviewed artifacts used crisp DL classes; none implemented graded, fuzzy, or prototype membership, and none visibly separated necessary axioms from typical/probabilistic associations (the Schulz distinction). Gradedness, where handled at all, is pushed to data/annotation outside the class model.

**Evidence quality.** The evidence base is weak. Among included classes, definition quality was **absent (64), partial (48), poor (17), good (11)** — i.e. only **8%** carried a *good* (genus–differentia or otherwise clear) definition, and **56%** had no definition at all or only a poor one. Entity-quality scores were correspondingly low: **109** classes scored 1 (weak/mostly terminological), **24** scored 2, and only **2** scored 3. Parentage was frequently uninformative (many classes placed directly under `owl:Thing` or a generic grouping term). The quality profile explains the typology: a class cannot express a grounded disease model if it has no definition and a shallow parent.

**Dependency / reuse structure (secondary question, interoperability).** The ecosystem is centralised. **153 of 282 appearances (54%)** are dependency-only, and the dependencies concentrate on **OGMS, DOID, and MONDO**. Reference-class citation coverage was charted for the 149 native classes: 54 carry a resolvable DOI to a defining publication, and 67 had a citation attached to the review ontology. The practical implication is that the semantic quality of the whole disease-ontology landscape is effectively set by a few reference resources, while most artifacts are consumers rather than authors of disease models.

**Evidence-gap statement.** Cross-tabulating category × grounding × gradedness leaves large empty cells. The clearest under-served combinations are: (a) **process-based models with an explicit grounding of "pathological"** — process models exist (8) but none grounds abnormality; (b) **graded or context-indexed models with any explicit upper-level commitment** — gradedness is essentially unrepresented at the class level; and (c) **explicitly state-based (Kantian/Yamagata "abnormal state") models with formal axioms** — present only as a handful of thinly-axiomatised classes. These empty cells are the concrete opportunities a new, well-grounded disease ontology could occupy.

---

## Discussion

### Summary of evidence

This scoping review charted how disease is formally modelled across the biomedical ontologies in active circulation, using the ontologies themselves — not papers about them — as the primary evidence, and an ontology-based charting method in which each reviewed class is an OWL entity carrying controlled review annotations. Three findings stand out. First, **explicit ontological grounding of disease is the exception**: nearly two-thirds of the disease-model classes that survived screening commit to no view about what kind of entity a disease is, and only a small minority express a defensible, identifiable model. Second, **where grounding exists it is overwhelmingly BFO-flavoured** — the OGMS disposition/realizable-entity pattern dominates, process models are a distant second, and state-, quality-, and finding-based models are rare. Third, **the ecosystem is centralised**: a few reference ontologies (OGMS, DOID, MONDO) supply the disease-modelling commitments that the majority of resources import, so the field's semantic quality is concentrated in a handful of artifacts.

These results map directly onto the review questions. The typology answers the primary question and secondary question 2; the BFO concentration answers secondary question 1; the near-total absence of explicit grounding of "pathological" answers secondary question 3; and the universal use of crisp classes with no graded or default-knowledge separation answers secondary question 4. Secondary question 5 — the published critique map linking each approach to its objections and rebuttals — is addressed by the literature track and the accompanying philosophy-of-medicine synthesis, and is only partially represented in this artifact-track report.

For the different groups who might use this map: **ontology builders** get a chart of which commitments are already taken and which cells are empty; **data integrators** get an explicit warning that a shared "disorder"/"condition" label does not imply a shared category, and that reuse funnels through OGMS/DOID/MONDO; and **standards bodies** get evidence that most resources under-specify the disease category and would benefit from importing a grounded reference model rather than minting a bare class.

### Limitations

Several limitations of the review *process* should be noted, following PRISMA-ScR item 25. **(1) Single-reviewer charting.** The class-level review was performed by one reviewer; the protocol's dual-screening with an adjudication pass and κ agreement statistics has not yet been completed, so inter-rater reliability is not reported. **(2) Artifact track only.** This manuscript reports the ontology-registry (artifact) track; the bibliographic-database and hand-searched-proceedings literature track — which is where the River-Flow, YAMATO, and much of the critique literature lives — is charted separately and not fully integrated here, so the foundational-ontology picture is biased toward what is registry-retrievable (BFO/OGMS). **(3) Registry coverage and label dependence.** Retrieval depends on class labels and on BioPortal/OLS/OBO coverage; ontologies that model disease under an idiosyncratic label, or that are not indexed, may be missed despite the secondary and multilingual sensitivity tiers. **(4) Interpretation of implicit commitments.** The continuant/occurrent commitment is often implicit in axioms rather than stated in prose; reading it from the OWL is a charting judgement, declared as a rule but inevitably interpretive, and the borderline between "under-committed by design" (BioTop) and "no grounded model" (a bare class) required judgement. **(5) Language scope.** The literature strand is English (plus German for one tradition); non-Anglophone nosology theory may be under-represented, though the artifact track applied a multilingual label pass. **(6) Snapshot.** Ontologies change; the counts reflect the July 2026 registry state and specific ontology versions recorded per class.

### Conclusions

Across the biomedical ontologies in circulation, disease is more often *labelled* than *modelled*: the majority of disease-neighbour classes commit to no ontological account of what a disease is, a well-grounded minority follow the BFO/OGMS disposition pattern, and the entire ecosystem leans on a few reference ontologies through import. The design space of disease models is genuine and diverse but thinly populated, and its most defensible cells — process-based and graded/contextual models with an explicit grounding of "pathological" — are largely empty. For practice, this argues for consolidating on, and properly citing, a small set of grounded reference models rather than minting new bare classes, and for treating shared disease labels across resources as a red flag for integration rather than a guarantee of agreement. The map produced here is intended to be descriptive and neutral, so that it can serve as an independent justification for subsequent, more opinionated ontology-engineering work; the design argument for any particular grounded model is reserved for a separate companion paper that cites this review. A natural next step is a focused synthesis of the critique literature (the directed approach→objection→rebuttal map) and completion of the dual-review and literature-track charting.

### Funding

No dedicated external funding supported this scoping review. Sources of funding for the included sources of evidence (the individual ontologies and terminologies) were not systematically charted in the artifact track and vary by resource; where a native class carries a defining publication, its funding can be traced through the recorded DOI/citation. The authors declare no role of any funder in the design, conduct, or reporting of this review.

---

## Appendix A. Seed set (known-item validation)

*Formal-model proposals and critiques:* Scheuermann/Ceusters/Smith 2009 (OGMS); Goldfain et al. 2010 (IDO dispositions); Arp/Smith/Spear 2015 (BFO); Hoehndorf/Dumontier/Gkoutos 2011 (scalable representations / BioTop pattern); Schulz et al. 2009 (strengths & limitations); Schulz & Jansen 2013; Röhl & Jansen 2014 (realizables); Jansen 2007 (tendencies); Mizoguchi et al. 2011 (River Flow); Rovetto & Mizoguchi 2015 (causality); Yamagata et al. 2013, 2014 (abnormal states); Mizoguchi & Borgo 2022 (YAMATO); Ceusters & Smith 2010 (mental disease); Smith/Munn/Papakin 2004 (bodily systems); Hucklenbroich 2014 (disease entity); Smart 2016 / Tsou 2016 (causal & natural-kind bridge).

*Ontology artifacts to chart directly:* OGMS, DOID (Schriml 2012/2015/2019/2022; Kibbe 2015), Mondo (Vasilevsky 2022), IDO, HPO, ORDO/Orphanet, NCIt (disease branch), SNOMED CT (clinical finding/disorder hierarchy), ICD-11 Foundation, Mental Functioning/Mental Disease Ontology, Neurological Disease Ontology, OAE, Disease Compass / Hozo RFM ontology.

## Appendix B. Charting form (controlled fields)

The full charting form is the annotation-property ontology `review_core.ttl` (namespace `https://example.org/disease-review/ap/`). Its `rev:*` fields and controlled value sets are: `manual_include_status` (include/exclude/maybe/needs_second_review); `manual_exclusion_reason` (demo_or_training_resource, value_set_or_collection, out_of_scope, terminology_not_ontology, duplicate_imported_term, obsolete_or_noncurrent, insufficient_metadata, replaced_by_better_native_disease_model_candidate); `ontology_type_manual` (curated_ontology, clinical_terminology, thesaurus, value_set, application_ontology, demo_or_training_resource, generated_or_local_resource, unclear); `native_or_imported_manual` (native/imported/reused_unclear/unknown); `review_route` (independent_analysis_route / dependency_only_no_independent_analysis / mixed / unknown_namespace_needs_manual_check); `disease_model_category` (the buckets tabulated in Results); `upper_level_interpretation` (free text); `definition_quality`, `comment_quality`, `parentage_quality`, `provenance_quality` (good/partial/poor/absent/not_applicable); `entity_quality_score` (0–3); and audit fields `reviewer`, `review_date`, `second_reviewer`, `second_review_date`, `disagreement_flag`, `adjudication_decision`, `review_notes`.

## Appendix C. Reproducibility

The extraction and charting are reproducible from the repository: `review_extraction_pipeline.py` (single entry point, chunked as `search`, `bioportal-hierarchy`, `prefill-manual`, `export-review-ontology`); supporting scripts `download_review_ontologies.py`, `prefill_manual_annotations.py`, `review_disease_terms.py`, `preselect_logical_inconsistency.py`, `review_consistency_checks.py`, `seed_replacement_target.py`, and `skip_redundant_disease_siblings.py`. Durable outputs: the review ontology `disease_terms_review.ttl` (+ `review_core.ttl` and imported source/fallback modules); the generated tables `disease_terms_review_enriched.csv`, `disease_terms_manual_annotations.csv`, `ontology_source_appearance_routes_summary.csv`/`_detail.csv`, `ontology_source_exclusions_for_flow_figure.csv` and its `_counts_` companion, and `native_class_citation_coverage.csv`.

---

*Prepared as a PRISMA-ScR-structured first draft from the project's protocol, entity-quality-assessment workflow, extraction pipeline, and charting tables. Counts reflect the July 2026 artifact-track extraction and the current single-reviewer annotation state.*
