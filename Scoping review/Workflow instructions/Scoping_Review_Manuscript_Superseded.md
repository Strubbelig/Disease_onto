# SUPERSEDED: How Is Disease Formally Modelled in Biomedical Ontologies? A Scoping Review of Ontology Artifacts

> **Historical record only.** This draft used PRISMA-ScR terminology even though its primary data are ontology artifacts rather than reports of prior studies. On 10 August 2026 the study was reclassified as a systematic cross-sectional evaluation of ontology artifacts. The publication-facing manuscript is `Disease_Ontology_Artifact_Evaluation_Manuscript.md`. This file is retained to document the earlier framing and the embargoed OSF registration history; do not submit it to a journal.

**Moritz Milewski^1,2 and Martin Boeker^3**

1. Plastic and Reconstructive Surgery, Department of Surgery, Yale School of Medicine, New Haven, Connecticut, USA  
2. Department of Plastic, Aesthetic, Hand and Reconstructive Surgery, Hannover Medical School, Hannover, Germany  
3. Chair of Medical Informatics, Technical University of Munich, Munich, Germany

**Corresponding author:** Moritz Milewski, **[institutional postal address, email, and telephone to add before submission]**  
**ORCID:** Moritz Milewski **[add]**; Martin Boeker, 0000-0003-2972-2042  
**Keywords:** disease; biomedical ontology; knowledge representation; scoping review; semantic interoperability

*Draft manuscript, v0.5. Reported in accordance with the PRISMA Extension for Scoping Reviews, PRISMA-ScR (Tricco et al., 2018). The study is an ontology-artifact scoping review; a broader philosophical-literature synthesis is a separate project. Numerical results remain provisional until the three reopened eligibility records and the planned independent validation sample have been resolved.*

---

> ## Status: outstanding work before submission
>
> The extraction and first-review charting are complete. The following tasks remain before the publication dataset can be frozen:
>
> 1. **Resolve the three reopened classes in the UI.** MEDICALINFO, OFDSIPT, and PATEL are no longer automatically excluded because they use WebProtege IRIs; each now requires a substantive include/exclude decision.
> 2. **Perform independent validation.** Ask the second reviewer to assess the prespecified 50-class stratified sample described in `Workflow instructions/second_reviewer_stratified_validation.md`. Preserve the second reviewer's original decisions, reconcile disagreements only afterwards, and report agreement.
> 3. **Complete the OSF record metadata.** The retrospective protocol registration has been submitted and is currently embargoed. Add its registration date and private identifier now if appropriate, and its public URL/DOI when the embargo is lifted. It must not be described as prospective or as a preregistration.
> 4. **Complete author metadata.** Confirm the exact institutional wording, degrees, corresponding-author address/email/telephone, CRediT roles, ORCIDs, and competing-interest statement with both authors.
> 5. **Reconcile references in Zotero.** The draft reference inventory below covers the citations currently used in the text. Replace it with a verified Zotero export in the target journal's style and resolve every item marked for verification.
> 6. **Freeze the publication supplement.** After steps 1 and 2, regenerate both TTL views and Figure 1, re-verify every count against `disease_terms_review_enriched.csv`, and rebuild the release archive. The ontology files use non-resolving UUID URNs and are distributed as a self-contained publication supplement.
>
> **Placeholders to fill:** corresponding-author contact details; Moritz Milewski's ORCID; author degrees; OSF DOI/URL/date; confirmed contributions and conflicts of interest; completed second-review details.

---

## Structured summary

**Background.** How a biomedical ontology commits to *what kind of entity a disease is* — a disposition, a process, a state, a clinical finding, or a deliberately under-committed category — determines how the ontology classifies, reasons over, and interoperates with disease data. Yet comparative treatments of these commitments exist almost exclusively as preambles to specific proposals (OGMS's disposition, the River Flow Model's causal chains, BioTop's "condition" pattern), and no independent review charts the design space across the ontologies actually in circulation.

**Objectives.** To map how *disease* and its immediate conceptual neighbours (disorder, condition, syndrome, pathological process, abnormal state) are formally defined and represented across biomedical ontologies and terminologies, and to identify which upper-level design commitments distinguish these representations, how well they are grounded, and where the design space is empty.

**Eligibility criteria.** The unit of analysis is an **OWL/RDFS class** representing disease or a disease-neighbour, together with its available labels, definitions, comments, synonyms, asserted named superclass hierarchy, mappings, and source provenance. Associated modelling publications were used as supporting evidence. Out-of-scope concepts, thesauri/value sets, weaker duplicate candidates, and mapping-only or unmodified imported appearances were excluded from independent analysis. Sparse annotation and local- or WebProtege-looking IRIs were assessed as evidence-quality issues rather than automatic exclusions. Imported or externally sourced classes were retained when their placement or reuse constituted an explicit implementation choice in the receiving ontology and were coded as imported/reused.

**Sources of evidence.** BioPortal (primary), the Ontology Lookup Service (OLS), and the OBO Foundry were searched programmatically between 29 June and 6 July 2026 using exact-label disease-neighbour terms, sensitivity terms, and targeted artifact retrieval.

**Charting methods.** The unit of analysis was an OWL class keyed by IRI. One reviewer charted the complete set using a structured evidence packet and controlled fields covering provenance, eligibility, upper-level interpretation, four coupled design decisions, and evidence quality. A second reviewer will independently validate a prespecified stratified 50-class sample before the dataset is frozen. The sole editable master table is converted into a complete evidence ontology and an included-only synthesis ontology.

**Results.** IRI de-duplication produced 278 class-level records. At the current publication-readiness checkpoint, 146 are included, 129 excluded, and three await substantive eligibility decisions after removal of an IRI-format exclusion rule. Among the provisionally included classes, 100 of 146 (68%) use `no_grounded_model`. The disposition/realizable/dependent-continuant family accounts for 24 classes and process models for eight. Definition quality is absent or poor for 84 classes; 11 (8%) are rated good. Appearance-level flow counts and all percentages will be regenerated after the three decisions and independent validation.

**Conclusions.** Most biomedical ontologies use a disease class without explicitly modelling what a disease is. Across the ontologies in active circulation, explicit and defensible disease modelling is the exception, not the rule. A small number of reference ontologies (OGMS, DOID, MONDO) carry the semantic weight for the entire ecosystem through import and reuse, while the majority of resources reproduce a disease-like class with little or no upper-level commitment. The evidence-gap map identifies under-served combinations — notably graded/contextual and process-based models with explicit grounding of "pathological" — as the clearest opportunities for future ontology-engineering work.

---

## Introduction

### Rationale

Every biomedical ontology that contains a class for *disease*, *disorder*, or *condition* implicitly answers a question that the philosophy of medicine has debated for decades: what kind of thing, ontologically, is a disease? Is it a disposition borne by an organism, as in the Ontology for General Medical Science (Scheuermann et al., 2009), a process or causal chain unfolding over time, as in the River Flow Model (Mizoguchi et al., 2011), a state or configuration of circumstances, a structural disorder of a bodily component, or simply a label in a classification with no commitment at all? This choice is not academic. It determines whether disease instances are continuants or occurrents, whether they can bear qualities and participate in processes, how they relate to signs, symptoms, and diagnoses, and — crucially for data integration — whether two resources that both use the word "disorder" are actually talking about the same category of entity.

Any ontology that represents disease is, whether or not its authors notice, forced into a position on four coupled design decisions that the theoretical literature has isolated. **(1) Ontological category:** is a disease a continuant (a state, disposition, or material entity that persists through change) or an occurrent (a process or causal chain that unfolds)? The SNAP/SPAN split makes this a forced choice in BFO (Grenon et al., 2004), whereas the River Flow Model denies that the choice is clean (Mizoguchi et al., 2011). **(2) Grounding of "pathological/abnormal":** what makes a bearer pathological — statistically sub-normal function (Boorse et al., 1977), evolutionary dysfunction (Wakefield et al., 1992), harm or disvalue (Engelhardt et al., 1975), or a primitive, criteria-defined "pathologicity" (Hucklenbroich et al., 2014)? Every formal ontology *imports* an answer from the philosophy of medicine, and almost none states which. **(3) Crisp vs graded:** are disease classes crisp universals with necessary-and-sufficient conditions, or inherently vague, prototype-based sets (Sadegh-Zadeh et al., 2000)? A pure OWL/DL ontology structurally cannot represent graded membership, so this must be decided up front. **(4) Reality vs classification:** does "disease" denote the underlying biological state, the practical illness role, a nosological category, or a precision-medicine stratification? These alternatives are articulated by the disease/illness distinction (Boorse et al., 1977), the state-description/normative-claim split (Ereshefsky et al., 2009), and precision-medicine stratification (Haendel et al., 2018). These uses come apart, and conflating them is a recurrent failure mode.

The positions named above are not interchangeable labels; each is a specific and contestable theory that an ontology silently inherits the moment it calls something "pathological." **The biostatistical theory (BST)** is the value-free default: a state is pathological when it reduces one or more functional abilities below the level statistically typical for the organism's *reference class* (its age, sex, and species), so "abnormal" just means "below the species-typical statistical range." It further separates *disease* — this theoretical biological notion — from *illness*, the socially and normatively loaded status of a disease serious enough to be undesirable, to warrant special treatment, and to excuse the bearer from ordinary responsibility (Boorse et al., 1977). **The harmful-dysfunction hybrid** keeps the factual half but adds a normative one: a disorder requires *both* a genuine dysfunction (a mechanism failing to perform the function it was naturally selected for) *and* resulting harm to the person, so neither a harmless quirk nor a harmful-but-normal response counts (Wakefield et al., 1992). **Normativism** pushes further still, holding that disease judgements are ineliminably evaluative — what counts as a disease tracks what a society disvalues, not a mind-independent biological line (Engelhardt et al., 1975). **The primitive-pathologicity account** takes the opposite tack from the biostatistical theory without collapsing into normativism: it treats *pathologicity* as a primitive theoretical concept of medicine — comparable to "mass" in physics — fixed by explicit criteria such as threat to life, pain and suffering, and loss of ability or fertility, so diseases become clinical natural kinds defined by those criteria rather than reduced to statistics or to values (Hucklenbroich et al., 2014). This middle path is the one most congenial to a mid-level ontology, because it legitimises taking "pathological" as a named, criteria-defined primitive instead of pretending it is value-free statistics. On the fourth decision, a deflationary account separates the *state description* (the physiological or psychological facts about the body) from the *normative claim* (whether that state is disvalued), after which many apparently substantive disputes about "what disease really is" dissolve (Ereshefsky et al., 2009). The precision-medicine account instead treats a disease classification as computable and useful for stratifying patients — integrating phenotype, genotype, environment, and mechanism — even when it does not correspond one-to-one to an intrinsic disease universal, so utility for decision support, not metaphysical cleanliness, is the operative virtue (Haendel et al., 2018). Finally, the fuzzy-set account treats health and disease as having graded membership, better modelled by resemblance to a prototype than by the crisp, necessary-and-sufficient categories a description logic forces on them (Sadegh-Zadeh et al., 2000). An ontology that writes down a crisp `Disease` class with a one-line definition has, whether or not its authors intend it, taken sides against every one of these accounts at once.

Comparative treatments of these commitments do exist, but they appear almost exclusively as the motivating preamble to a specific new proposal, and each carries published critiques that are equally scattered. **OGMS/BFO** models disease as a *disposition* to undergo pathological processes, existing because of a material *disorder* (Scheuermann et al., 2009). Its main virtue is representing pre-clinical disease, but critics argue that it cannot coherently represent *malfunction* — having a function but lacking the matching disposition (Röhl et al., 2014), that it represents graded *tendencies* poorly (Jansen et al., 2007), and that it merely relocates the undefined primitive "pathological" (Hucklenbroich et al., 2014). The **River Flow Model / YAMATO** lineage models disease as a persisting entity *individuated by a causal chain* of pathological processes and states, recovering the causal structure clinicians reason with at the cost of a non-OBO-mainstream top-level and under-determined identity conditions for the chain (Mizoguchi et al., 2011; Rovetto et al., 2015; Mizoguchi et al., 2022). **DOID and Mondo** are pragmatic classification resources: Mondo's root imports the OGMS disposition definition, yet its working identity criterion for a disease is a clinical four-fold of etiology, phenotype, natural history, and treatment response (Haendel et al., 2018). The two are never reconciled, so the metaphysics is, in effect, decorative. **BioTop** introduces a deliberately under-committed "condition" as a design pattern (Schulz et al., 2011). Each proposal is valuable but partisan, and no independent review charts the *design space* itself — the set of commitments actually made by the ontologies in circulation — and evaluates how well those commitments are grounded and where they leave gaps.

This produces three concrete problems. First, new ontology builders re-litigate the same continuant/occurrent and disposition/process choices from scratch, unaware of what has already been tried. Second, interoperability suffers, because the same label ("disorder", "disease", "condition") denotes different ontological categories across resources, and importers rarely notice. Third, the published critiques of each approach are scattered across venues and framed to advance a competing proposal, so there is no neutral map a builder can consult.

### Objectives

Following the Population–Concept–Context (PCC) framework:

- **Population / unit of analysis.** Not a clinical population. The unit is a single **OWL/RDFS class** that represents disease or a disease-neighbour, examined through its available annotations, asserted named superclass hierarchy, mappings, and provenance. Where a class has an associated modelling publication, that citation is supporting evidence for how the class should be read; it is not itself a unit of analysis. Design proposals and published critiques are therefore not charted as units in their own right.
- **Concept.** The ontological commitment a class makes about what a disease — or its immediate neighbours disorder, condition, syndrome, pathological process, or abnormal state — *is*, as expressed in the retrievable class definition, comments, superclass placement, and source metadata and corroborated where possible by its cited publication.
- **Context.** Biomedical and clinical knowledge representation, applied and formal ontology, and biomedical informatics; philosophy of medicine only where it is directly cited by or informs a formal model.

**Primary question.** How is *disease* (and its immediate neighbours) formally defined and represented across biomedical ontologies, and what design commitments distinguish these approaches?

A full answer to this question is not a single figure; it decomposes into the following constituent sub-questions, each capturing one dimension along which a disease class can be characterised. Answering all of them *is* answering the primary question:

1. To which top-level/foundational ontology (BFO, DOLCE, YAMATO, BioTop, GFO, none) does each class commit, and how does that constrain its disease model?
2. To which ontological category is *disease* assigned (continuant/disposition, occurrent/process, causal chain, material structure, state, finding, or deliberately under-committed)?
3. How well is the load-bearing primitive "abnormal/pathological" grounded (statistical, evolutionary/function, normative, primitive-criteria, or left undefined)?
4. How are variation, gradedness, and uncertainty handled (crisp DL classes, graded/fuzzy, or pushed to data/annotation)?
5. Taken together across (1)–(4), where is the design space empty — which combinations of commitments are under-served?

---

## Methods

### Protocol and registration

A written protocol exists in the project repository as `Scoping_Review_Protocol_Disease_Modelling.md`. It was not publicly registered before retrieval or analysis. A time-stamped **retrospective registration** was submitted to OSF Registries using the Generalized Systematic Review template and is currently under embargo (**OSF DOI [add when public]**, **URL [add when public]**, registered **[date pending]**). The registration identifies the review as completed at the time of registration and distinguishes the implemented artifact-review methods from earlier plans for a broader literature review. Method changes are recorded in the project changelog. One reviewer performed the complete eligibility assessment and charting. A second reviewer will independently assess a prespecified stratified sample before submission; the sampling and reconciliation procedure is reported in the supplementary workflow.

### Eligibility criteria

Eligibility was defined for the ontology-artifact track using a Population-Concept-Context adaptation in which the unit of analysis is a class rather than a human population. No publication-date limit was applied because ontology versions and legacy disease models remain relevant to present interoperability. Publication status was not an eligibility criterion: the source of evidence had to be an inspectable ontology artifact or registry class record, while papers were used only to support interpretation and provenance. Artifact labels in any language were eligible, although discovery used English exact-label terms plus a limited French/German sensitivity pass.

**Inclusion.** A record was eligible when it represented an identifiable OWL/RDFS class relevant to disease, disorder, illness, health condition, syndrome, pathological process/disposition, dysfunction, or a justified replacement disease-model class, and exposed enough inspectable class or registry evidence to assess at least its label and asserted hierarchy. The hostname or visual form of an IRI was not itself an eligibility criterion. Native classes entered independent analysis. Imported or externally sourced classes were retained only when their placement, extension, or reuse in the receiving ontology constituted an explicit implementation choice; they were marked `imported/reused` so they were not mistaken for independently authored definitions. Clinical terminologies could remain as comparison cases, but thesauri and value-set collections were excluded from the synthesis because their purpose is terminological organization rather than independent ontological modelling.

**Exclusion.** Records were excluded when the retrieved class denoted an unrelated sense of *condition* or another concept outside the disease-model scope; denoted injury, predisposition, disease course, or another contextual concept rather than disease; belonged to a value set, thesaurus, demo, or training resource; duplicated a better native disease-model candidate; or was only a mapping, exact-match, or imported appearance of a canonical class without an independent implementation. Sparse annotation or a WebProtege/local-looking IRI could lower evidence quality but did not independently exclude a class. A syndrome or pathological-process hit was suppressed when the same ontology contained a more direct disease/disorder target. Excluded records remained in the master screening table with reason codes.

Models identified only in publications could not become class-level evidence when neither an inspectable artifact nor sufficient class-level registry metadata was available. The Hozo *River Flow Model* (Disease Compass) was not indexed in BioPortal, OLS, or the OBO Foundry (Mizoguchi et al., 2011). Manual retrieval through the ontology laboratory website was unsuccessful because the available links did not resolve to a downloadable, inspectable ontology. YAMATO was likewise unobtainable as an inspectable artifact (Mizoguchi et al., 2022). These models are discussed from publications but are not counted as charted artifacts; their absence is an evidence gap, not a judgement about their content or merit.



### Information sources

The primary information sources were **BioPortal** (`https://data.bioontology.org`), the **EBI Ontology Lookup Service v4** (`https://www.ebi.ac.uk/ols4`), and the **OBO Foundry registry** (`https://obofoundry.org/registry/ontologies.yml`). BioPortal was the primary registry. OLS supplied additional registry contexts, and active OBO Foundry products not indexed in BioPortal were scanned directly. Targeted GitHub or ontology-site retrieval was used only to resolve a known artifact or replacement class and is identified in the provenance fields.

Registry retrieval ran from **29 June through 6 July 2026**. The last recorded BioPortal retrieval was 6 July 2026, the last OLS retrieval was 4 July 2026, and the OBO Foundry direct scan was executed on 29 June 2026. Retrieval timestamps, source databases, source URLs, and available ontology-version metadata were retained per class. PubMed, Scopus, Google Scholar, ResearchGate, and ontology documentation/reference fields were searched only to locate a modelling publication for a retrieved ontology; those bibliographic searches did not generate additional class-level study records.

### Search

The executable search is implemented in `review_disease_terms.py` and invoked through:

```bash
python3 "Scoping review/Python scripts/review_extraction_pipeline.py" \
  --chunk search --sources bioportal,ols,obo
```

No ontology or date filter was applied. API credentials were transmitted to BioPortal but are not included in the reproducibility materials. The database-specific electronic strategy was:

| Source | Endpoint and parameters | Matching and pagination |
|---|---|---|
| BioPortal | `GET https://data.bioontology.org/search`; `q={term}`; `require_exact_match=true`; `include=prefLabel,definition,synonym,notation,properties`; `pagesize=100`; `page={n}` | Pages followed until `nextPage` was absent, with a 50-page safety cap for common tokenized queries. Results were then filtered locally to normalized exact label equality. Class detail, direct parents, mappings, and latest-submission metadata were fetched from the corresponding `/ontologies/{acronym}/classes/{encodedIRI}` endpoints. |
| OLS v4 | `GET https://www.ebi.ac.uk/ols4/api/search`; `q={term}`; `exact=true`; `type=class`; `queryFields=label`; `rows=100`; `start={n}` | Pagination continued to `numFound`; results were filtered locally to normalized exact label equality. Term details, direct parents, and ontology metadata were fetched from `/api/ontologies/{ontology}/terms/{encodedIRI}` and `/api/ontologies/{ontology}`. |
| OBO Foundry | `GET https://obofoundry.org/registry/ontologies.yml`, followed by direct retrieval of active `.obo` or `.owl` products | Ontologies already indexed in BioPortal were skipped. Labels in each remaining active product were parsed and compared by normalized exact equality. No ontology-count cap was applied. |

Normalization inserted spaces at camel-case boundaries, removed punctuation, collapsed whitespace, and compared case-folded strings. Records were de-duplicated by exact class IRI; when no IRI was available, the fallback key was normalized ontology, preferred label, and search term. Source appearances, definitions, comments, and provenance were merged rather than discarded.

**Primary exact-label tier.** The complete primary list was: `disease`, `disorder`, `disorders`, `Disorders`, `illness`, `condition`, `health condition`, `ClinicalCondition`, `Clinical Condition`, `syndrome`, `pathological process`, `pathological disposition`, and `dysfunction`.

**Secondary sensitivity tier.** Broad supplementary terms were `pathological condition`, `pathological state`, `abnormal state`, `disease state`, `pathologic process`, `morbid condition`, and `nosological entity`. They were retained only for source ontologies without a primary-tier hit. Compound-label terms were `Disease, finding or disorder`, `DiseaseDisorderOrFinding`, `Disease or disorder`, `Disease or syndrome`, `Disorder or finding`, and `Clinical finding or disorder`; these remained eligible even when a generic primary hit existed. Secondary hits were tagged `discovery_tier = secondary_compound_label_sensitivity`.

**Multilingual sensitivity pass.** A limited French/German pass searched `maladie`, `trouble`, `condition pathologique`, `Krankheit`, `Erkrankung`, and `Störung`; these hits were tagged `discovery_tier = multilingual_label_sensitivity`. This pass broadened artifact-label discovery only and did not constitute a separate literature search.

### Selection of sources of evidence

Selection combined **automated screening** at the registry-appearance level with **manual class-level review**.

Automated screens, applied in the extraction pipeline before human review, implemented reproducible candidate-routing rules and produced an auditable table for the flow diagram:

- **Source-type screen** — value-set collections (e.g. `VALUESETS`) were removed as not independent ontologies.
- **Term-scope screen** — `injury`, `predisposition`, `disease course`, and similar non-synonyms were removed (E5); a `pathological process` class was suppressed when the same ontology carried a stronger disease-root class, and retained only where it was the sole process-based candidate.
- **Target-refinement screen** — where manual hierarchy inspection identified a better native disease-model candidate in the same ontology, the initial label hit was replaced (recorded as `replaced_by_better_native_disease_model_candidate`); a `syndrome` class was suppressed when a `disease`/`disorder` class was present in the same ontology.
- **Semantic-equivalence and provenance screens** — classes declaring `skos:exactMatch` to a canonical disease root (DOID_4, MONDO_0000001, OGMS_0000031) or `rdfs:isDefinedBy`/namespace pointing to an external ontology were treated as reuses, not independent models, and routed to the native provider for analysis.
- **Dependency/reuse screen** — appearances of a class IRI in an ontology that merely imports it were listed as dependency appearances, with the native ontology recorded for analysis.

Classes surviving these screens entered manual review through Protégé or the interactive review UI, which presents an evidence packet (labels, definition, comments, synonyms, parentage, provenance) and records controlled values in the master CSV. One reviewer assessed all class-level records. Rule-based prefill was used only for explicit evidence patterns and remained visible for manual confirmation. Three records formerly excluded solely because of their WebProtege IRIs were reopened for substantive assessment. Before submission, a second reviewer will independently assess a prespecified stratified 50-class sample while blinded to the first reviewer's decisions; raw decisions, agreement, and reconciliation will be retained.

### Data charting process

Each reviewed entity is keyed by class IRI in the sole editable master table, `disease_terms_review_enriched.csv`. The pipeline generates (i) `disease_terms_review.ttl`, containing every screening record and review annotation, and (ii) `disease_terms_synthesis.ttl`, containing only `effective_synthesis_status = include`. Both import `review_core.ttl` (annotation namespace `urn:uuid:8f96cf34-53c2-48d2-88c5-96d07704fcf7#`) and subject-sanitized native hierarchy modules. The review package uses non-resolving UUID URNs because it is intended as a self-contained publication supplement rather than a web-hosted ontology. Imports resolve locally through the supplied XML catalog. Imported/reused appearances remain provenance evidence and cannot contribute superclass assertions to a different native module.

Because the review key is the class IRI, a class appearing in several registries or ontologies is charted once, with its appearances recorded as provenance (`source_ontology_ids`, `source_databases`) rather than as duplicate rows.

The charting form was iteratively refined while reviewing the artifact set. Whenever a controlled category or deterministic prefill rule changed, the rule was applied consistently across the full master table and the affected classes remained available for manual review. Definitions, comments, labels, synonyms, superclass assertions, and mappings were taken from registry APIs or source artifacts; modelling publications were used as corroborating evidence. Ontology developers were not contacted to clarify missing information. Data were charted by one reviewer rather than independently or in duplicate.

### Data items

For each charted class the following were sought (full definitions in `review_core.ttl`):

- **Provenance / context** — `class_iri`, `preferred_label`, `source_ontology_ids`, `source_databases`, `ontology_versions`, retrieval date, `discovery_tier`, ontology title/status/homepage/licence.
- **Evidence resolved through imported modules** — definition, comments, synonyms, `parent_labels`/`parent_iris`, `bfo_anchor`, mapping count, `exact_match_iris`, `defined_by_iris`, `conforms_to_iris`.
- **Manual review annotations** — `ontology_type_manual` (curated ontology / clinical terminology / thesaurus / value set / application ontology / demo / generated / unclear); `native_or_imported_manual`; `review_route` (independent vs dependency-only); `manual_include_status` (include / exclude) and `manual_exclusion_reason`; a single free-text `review_comment`; an optional controlled `disease_model_category`; the **four coupled design-decision fields** — `ontological_category` (continuant / occurrent / mixed-continuant-occurrent-model / no-continuant-occurrent-commitment / unclear), `pathological_grounding` (statistical / evolutionary-function / normative / primitive-criteria / undefined / n.a.), `crisp_vs_graded` (crisp / graded-or-fuzzy / prototype / gradedness-in-data / silent), and `reality_vs_classification` (biological-state / illness-role / nosological-category / precision-medicine-stratification / conflated / unclear); three evidence-quality fields (`definition_quality`, `comment_quality`, `parentage_quality`, each good/partial/poor/absent); an integer `entity_quality_score` (0–3); and audit fields (`reviewer`, `review_date`). The four coupled-decision fields operationalise, at the class level, the four design decisions set out in the Introduction, so that each can be charted directly from the OWL rather than inferred narratively.


### Critical appraisal of individual sources of evidence

A lightweight **entity-quality assessment** was charted for each included class to support the synthesis. Definition, comment, and parentage quality were recorded separately, alongside a 0–3 `entity_quality_score` capturing whether the class was clearly defined, relevantly placed, and structurally interpretable. Score 0 was reserved for excluded classes; score 1 denoted absent or non-discernible ontological grounding; score 2 denoted identifiable grounding with an incomplete definition or superclass account; and score 3 required a good superclass, a good logical definition, and explicit ontological grounding. Quality scores did not independently determine eligibility; they were summarized descriptively after inclusion decisions. The appraisal concerns entity modelling quality, not risk of bias in a clinical study.

### Synthesis of results

Synthesis combined **ontology-driven descriptive statistics** with a **narrative typology**. Charting annotations were tabulated to produce: (i) counts of included versus excluded classes with reasons; (ii) the distribution of ontology vs. terminology and native/imported provenance; (iii) the **disease-model typology** (the distribution of the model category); (iv) the **evidence-quality profile**; (v) a **dependency/reuse analysis** cross-tabulating independent-analysis versus dependency-only appearance routes and the ontologies depended upon; and (vi) an **evidence-gap map** built directly from the four coupled design-decision fields — cross-tabulating `ontological_category` × `pathological_grounding` × `crisp_vs_graded` (with `reality_vs_classification` as a fourth axis) to surface which combinations of commitments are populated and which cells are empty. Because these four dimensions were charted per class, the gap map was read from the annotations rather than inferred narratively. Counts, percentages, and selected group means were descriptive; no meta-analysis or risk-of-bias-across-studies synthesis was performed.

---

## Results

### Selection of sources of evidence

Registry searching and targeted artifact retrieval identified **504 source-ontology appearances**. The initial flow report excluded 222 appearances, but five appearances representing three class IRIs had been excluded solely because they used WebProtege IRIs and have now been reopened. The remaining automated exclusion stages account for 217 appearances. The final retained-appearance and de-duplication counts will be regenerated after substantive review of the reopened records. The current master contains **278 unique class IRIs**. BioPortal supplied the great majority of records, with smaller contributions from OLS, the OBO Foundry direct scan, and one targeted GitHub artifact.

Apart from the withdrawn IRI-format rule, automated screening removed appearances at the following stages (counts as source-ontology appearances / distinct source ontologies / distinct class IRIs):

| Screen | Reason code | Appearances | Ontologies | Class IRIs |
|---|---|---:|---:|---:|
| Source type | Value-set collection, not an ontology | 1 | 1 | 1 |
| Term scope | Out of scope (not a disease synonym; e.g. injury) | 80 | 74 | 40 |
| Term scope | `pathological process` suppressed when a disease root is present | 13 | 11 | 11 |
| Target refinement | Replaced by a better native disease-model candidate | 63 | 58 | 6 |
| Target refinement | `syndrome` suppressed when a `disease` class is present | 32 | 30 | 13 |
| Semantic equivalence | Explicit `skos:exactMatch` to a canonical disease root | 4 | 4 | 2 |
| Semantic provenance | Defined by an external class (no independent analysis) | 2 | 1 | 2 |
| Dependency/reuse | Imported/reused term (no independent analysis) | 22 | 18 | 11 |

In the pre-correction appearance report, **103** appearances were routed for independent analysis, **153** were dependency-only (the class is imported/reused, so the model is analysed at its native provider), **20** carried a mix of independent and dependency appearances, and **6** had an unknown namespace that required manual namespace resolution. These route counts are retained here as provisional and will be replaced by the regenerated report.

The deduplicated master screening record contains **278 unique class IRIs**. The current decision materialization yields **146 provisionally included**, **129 excluded**, and **three requiring a substantive user decision**. The final appearance flow, class totals, Figure 1, and percentages will be regenerated after those records and the independent validation sample have been resolved. All class-level counts derive from `disease_terms_review_enriched.csv` and the machine-generated audit report.

![Figure 1. PRISMA-ScR flow diagram for the ontology-artifact review. Counts distinguish source-ontology appearances from unique class IRIs.](Figures/prisma_scr_flow_diagram.png)

**Figure 1. PRISMA-ScR flow diagram for the ontology-artifact review.** “Appearance” denotes one class in one registry/source-ontology context; “class” denotes a unique IRI after de-duplication.

### Characteristics of sources of evidence

Among the 146 provisionally included classes, 137 were charted as curated ontologies and nine as clinical terminologies; 133 classes were charted as native and 13 as imported/reused. Their source-ontology distribution is long-tailed, with most resources supplying one or two classes.

Characteristics for every screened class — including ontology title, version metadata, retrieval source/date, IRI, native/imported status, definition, parentage, eligibility decision, quality appraisal, and modelling citation or explicit no-citation status — are reported in **Supplementary Table S1** (`disease_terms_review_enriched.csv`).

The reference ontologies that anchor the ecosystem appear less as independent rows than as **dependency targets**. Of the 153 dependency-only appearances, the ontologies most frequently depended upon were **OGMS** (named in ~74 appearances, alone or with DOID), **DOID** (~38), the UMLS Semantic Type network **STY** (25), and **MONDO** (9), with smaller counts for **SIO** and **NCIT**. In other words, a handful of reference resources carry the disease-modelling commitments that the wider ecosystem imports.

### Results of individual sources of evidence

The complete per-class results are reported in **Supplementary Table S1** (`disease_terms_review_enriched.csv`); the two review ontologies are machine-generated supplementary views. The master records each IRI, native ontology, evidence, citation or no-citation decision, eligibility basis, modelling category, four coupled decisions, three evidence-quality ratings, and entity-quality score. Representative interpretations illustrate the range:

- **Grounded, BFO-legacy models.** Several classes are cleanly placed as "subclass of disposition, clear BFO legacy" — typically OBO-library ontologies inheriting the OGMS pattern (e.g. the IRAEO adverse-event classes).
- **Under-committed condition patterns.** BioTop-style classes model a medical condition as a subclass of *Particular* (BioTop's sole child of `owl:Thing`) — a pragmatic solution the reviewer characterised as "understandable [but] not very ontological".
- **Terminology-like structures.** Multiple classes sit in shallow, weakly informative hierarchies (e.g. `Condition is_a Characteristic is_a Diagnostic_factor is_a Thing`) that function more like terminology groupings than formal domain models.
- **Application and data-schema artifacts.** Several `Condition` classes were created to store hospital or clinical-trial-registry diagnostic data, with SNOMED/UMLS codes embedded in notes and no definition, comment, or expressive superclass.
- **Broken subsumption.** Some classes exhibit incoherent `is_a` chains (e.g. a health `Condition` placed under `acidity`, or a `Clinical finding` placed under `bfo:Process`), indicating class/hierarchy confusion rather than a deliberate model.

These per-class notes are the qualitative backbone of the typology below and are available in full in the annotation table.

### Synthesis of results

**Disease-model typology (146 provisionally included classes).** The single most important finding is the **prevalence of ungrounded modelling**. Current first-review categories are:

| Disease-model category | Included classes |
|---|---:|
| No grounded model (terminology/classification category, no commitment) | 100 |
| Disposition (BFO) | 17 |
| Process / course of events (BFO occurrent) | 8 |
| Kantian state (a way a bearer is determined) | 3 |
| Realizable entity (BFO) | 4 |
| Dependent continuant | 3 |
| BioTop-style condition (under-committed) | 3 |
| Quality (SIO) | 2 |
| Mixed model | 1 |
| Disorder | 1 |
| Unclear / not yet categorisable | 4 |

Thus **100 of 146 (68%)** provisionally included classes carry no identifiable ontological commitment to what a disease is. The **realizable-entity/disposition family** accounts for 24 classes (17 dispositions, four broader realizable entities, and three dependent continuants), with **process** a distant second (eight). State-, quality-, BioTop-condition, disorder, and deliberately mixed models are rare.

**Foundational-ontology commitment (sub-question 1).** The grounded classes cluster around **BFO** — via the OGMS disposition pattern for the disposition/realizable-entity family (Scheuermann et al., 2009) and via BFO process for the process family (Arp et al., 2015) — with a small **BioTop** contingent using the "condition" pattern (Schulz et al., 2011) and isolated **SIO** quality models. DOLCE, GFO, and YAMATO did not surface as commitments among the artifact-track classes reviewed here. **This absence is a consequence of artifact availability, not evidence that these top-levels are unused:** the YAMATO top-level and the Hozo *River Flow Model* (Disease Compass) could not be obtained as inspectable artifacts; only their publication descriptions were retrievable (Mizoguchi et al., 2011; Mizoguchi et al., 2022). They are therefore outside the artifact denominator and constitute an artifact-availability gap.

**Foundational alignment and entity quality.** The BFO-aligned disposition/realizable-entity/dependent-continuant family performed substantially better on the review rubric than classes with no identifiable upper-level grounding. Its 24 classes had a mean entity-quality score of **1.92/3**: 20 were scored 2 or 3, and 19 (79%) had good parentage. By comparison, all 100 `no_grounded_model` classes scored **1/3**; none had good parentage, and 97 (97%) had poor or absent parentage. Good definitions were also more frequent in the BFO-aligned family (4/24, 17%) than among ungrounded classes (5/100, 5%). This is a descriptive association, not a causal estimate: explicit grounding and relevant parentage are themselves components of the quality rubric. It nevertheless shows that BFO/OGMS alignment makes a disease class's ontological category and placement markedly more inspectable. BFO does not by itself solve every modelling question: 11 of the 24 BFO-aligned classes still left the meaning of "pathological" undefined.

**Grounding of "pathological/abnormal" (sub-question 3).** Grounding was coded as undefined for 111 of 146 provisionally included classes. The remaining classes were coded as primitive-criteria (16), evolutionary-function (11), normative (4), statistical (3), and not applicable (1). Explicit grounding is therefore uncommon, but not absent.

**Crisp vs graded and uncertainty (sub-question 4).** All 146 provisionally included classes were coded `silent`: the reviewed class evidence did not state a crisp, fuzzy, prototype, or gradedness-in-data commitment. OWL class representation alone was not treated as evidence that the ontology had explicitly chosen a crisp theory of disease membership.

**Evidence quality.** Definition quality was **absent (69), partial (51), poor (15), good (11)**; only **8%** carried a good definition, while **58%** had an absent or poor definition. Entity-quality scores were 1 for **122** classes, 2 for **22**, and 3 for **2**. Parentage was poor or absent for 108 classes. The quality profile helps explain the prevalence of under-specified models.

**Dependency / reuse structure (sub-question, interoperability).** The ecosystem is centralised. In the pre-validation appearance routing, **153 of 282 appearances (54%)** were dependency-only, and the dependencies concentrated on **OGMS, DOID, and MONDO**. Among the 133 provisionally included native classes, 69 have an approved modelling citation and 58 carry a DOI. The practical implication is that the semantic quality of the whole disease-ontology landscape is effectively set by a few reference resources, while most artifacts are consumers rather than authors of disease models. Appearance-level counts will be regenerated for the final flow diagram.

**Evidence-gap statement.** Cross-tabulating category, pathological grounding, gradedness, and reality/classification leaves large empty cells. The clearest gap is explicit gradedness: every included class is silent. Process models are uncommon (eight), and state-based models are represented only by three Kantian-state classes.

The gap map is derived directly from the four coupled fields (`ontological_category` × `pathological_grounding` × `crisp_vs_graded`, with `reality_vs_classification` as a fourth axis) in the master table and will be frozen after validation.

---

## Discussion

### Summary of evidence

This scoping review charted how disease is formally modelled across the biomedical ontologies in active circulation, using the ontologies themselves — not papers about them — as the primary evidence, and an ontology-based charting method in which each reviewed class is an OWL entity carrying controlled review annotations. Three findings stand out. First, **explicit ontological grounding of disease is the exception**: nearly two-thirds of the disease-model classes that survived screening commit to no view about what kind of entity a disease is, and only a small minority express a defensible, identifiable model. Second, **where grounding exists it is overwhelmingly BFO-flavoured** — the OGMS disposition/realizable-entity pattern dominates, process models are a distant second, and state-, quality-, and finding-based models are rare. Third, **the ecosystem is centralised**: a few reference ontologies (OGMS, DOID, MONDO) supply the disease-modelling commitments that the majority of resources import, so the field's semantic quality is concentrated in a handful of artifacts.

These results map directly onto the review questions. The typology answers the primary question and sub-question 2; the BFO concentration answers sub-question 1; the near-total absence of explicit grounding of "pathological" answers sub-question 3; the universal silence about crispness, graded membership, and gradedness in data answers sub-question 4; and the cross-tabulated empty cells answer sub-question 5. Published philosophical critiques provide context but are not a second study-selection track in this artifact review.

**Suitability of foundational frameworks for disease grounding.** The comparison distinguishes *support* (providing categories and relations in which a disease account can be stated) from *enforcement* (making incompatible category assignments detectable or impossible). No upper ontology alone determines what counts as pathological; that requires a disease-specific theory or extension.

| Framework | Support for disease modelling | What it can enforce | Principal limitation in this review |
|---|---|---|---|
| **BFO with the OGMS pattern** (Scheuermann et al., 2009; Arp et al., 2015) | Strong support for realist modelling: disease as a specifically dependent continuant/disposition, disorder as material basis, and pathological process as realization | Strong separation of continuants and occurrents; explicit bearer, realization, and process placement can expose category mistakes | BFO constrains entity type but does not define "pathological"; the OGMS extension, not BFO alone, supplies the disease pattern |
| **BFO process route** (Arp et al., 2015) | Clear support when the intended referent is a pathological process or pathway | Enforces occurrent placement and prevents treating the process itself as a continuant | Risks collapsing disease into its manifestation or course unless the ontology separately represents bearer, disorder, or disposition |
| **BioTop condition pattern** (Schulz et al., 2011) | Broad, deliberately under-committed support for integrating state-, quality-, and process-oriented clinical descriptions | Limited enforcement of one disease category because flexibility across representational views is part of the design | Useful for interoperability, but comparatively weak for forcing a single answer to what kind of entity a disease is |
| **SIO quality route** | Clear support for treating disease-related status as a dependent quality and connecting it to measurements and data | Enforces a quality-like continuant interpretation | Generic information/quality semantics do not by themselves supply a disease-specific causal or pathological theory |
| **YAMATO / River Flow Model** (Mizoguchi et al., 2011; Mizoguchi et al., 2022) | The published account is designed to support diachronic causal chains of abnormal states and processes | Potentially supports identity through causal organization rather than a single continuant/occurrent choice | Suitability could not be tested against OWL axioms because no inspectable artifact was retrievable in the registry or manual artifact search |
| **DOLCE or GFO** | Both could support state, process, quality, and bearer distinctions | Their category systems could constrain placement if a disease extension chose and axiomatized a pattern | No eligible artifact-track disease class committed to them, so this review provides no empirical comparison |
| **No identifiable top ontology** | Leaves maximum local freedom | Provides no shared upper-level constraints capable of exposing category inconsistency across ontologies | Dominant in the sample and associated with poor or absent parentage and under-specified disease meaning |

For disease-class grounding in interoperable biomedical ontologies, the reviewed evidence therefore favours **BFO plus an explicit disease-level pattern such as OGMS**, rather than bare BFO import or an unanchored `Disease` class. BioTop is better suited when deliberate ontological under-commitment is a requirement, while SIO is useful for quality- and measurement-centred representations. The River Flow/YAMATO approach may be attractive for causal and temporal modelling, but its implementation could not be evaluated here. This ranking concerns suitability for making commitments explicit and checkable; it is not a claim that one top ontology settles the philosophical definition of disease.

For the different groups who might use this map: **ontology builders** get a chart of which commitments are already taken and which cells are empty; **data integrators** get an explicit warning that a shared "disorder"/"condition" label does not imply a shared category, and that reuse funnels through OGMS/DOID/MONDO; and **standards bodies** get evidence that most resources under-specify the disease category and would benefit from importing a grounded reference model rather than minting a bare class.

### Limitations

Several limitations of the review *process* should be noted, following PRISMA-ScR item 20 (Tricco et al., 2018). **(1) Artifact-only scope and unobtainable artifacts.** The evidence units are ontology classes; publications provide interpretation but were not independently screened as study records. The Hozo *River Flow Model* was absent from BioPortal, OLS, and the OBO Foundry, and the ontology laboratory website links inspected manually did not yield a downloadable artifact (Mizoguchi et al., 2011). YAMATO was likewise unobtainable as an inspectable ontology (Mizoguchi et al., 2022). Both are absent by construction; this is not a judgement about their merit. **(2) Registry coverage and label dependence.** Retrieval depends on BioPortal/OLS/OBO coverage and normalized exact labels. Idiosyncratically labelled, unindexed, or non-English ontologies may be missed despite sensitivity tiers. **(3) One complete reviewer.** One reviewer performed the complete screening and charting. Reading ontological commitments from definitions and hierarchy requires judgement, so reviewer error and interpretive bias remain possible. A prespecified stratified sample will be reviewed independently before submission, but this does not provide duplicate review of the full dataset. **(4) Incomplete annotation and axiom evidence.** Registry APIs may omit annotations, anonymous restrictions, or imported axioms present in a source distribution. Native modules and targeted retrieval reduced but could not eliminate this risk; the review therefore does not claim complete logical-axiom extraction. **(5) Snapshot.** Ontologies change; counts reflect the recorded versions and retrieval dates from 29 June through 6 July 2026. **(6) Quality-comparison dependence.** The comparison between BFO-aligned and ungrounded classes is partly criterion-dependent because explicit grounding and parentage contribute to the entity-quality score; it should not be interpreted as a causal effect of adopting BFO. **(7) Funding of source artifacts.** Funding for individual ontology projects was not systematically available from artifact metadata and was not charted.

### Conclusions

Across the biomedical ontologies in circulation, disease is more often *labelled* than *modelled*: the majority of disease-neighbour classes commit to no ontological account of what a disease is, a well-grounded minority follow the BFO/OGMS disposition pattern, and the entire ecosystem leans on a few reference ontologies through import. The design space of disease models is genuine and diverse but thinly populated, and its most defensible cells — process-based and graded/contextual models with an explicit grounding of "pathological" — are largely empty. For practice, this argues for consolidating on, and properly citing, a small set of grounded reference models rather than minting new bare classes, and for treating shared disease labels across resources as a red flag for integration rather than a guarantee of agreement. The map produced here is intended to be descriptive and neutral, so that it can serve as an independent justification for subsequent, more opinionated ontology-engineering work; the design argument for any particular grounded model is reserved for a separate companion paper that cites this review. A natural next step is a focused synthesis of the critique literature (the directed approach→objection→rebuttal map) and integration of the literature-track charting with this artifact map.

### Funding

No dedicated external funding supported this scoping review. Sources of funding for the included sources of evidence (the individual ontologies and terminologies) were not systematically charted in the artifact track and vary by resource; where a native class carries a defining publication, its funding can be traced through the recorded DOI/citation. The authors declare no role of any funder in the design, conduct, or reporting of this review.

### Ethics approval

The review used publicly available ontology artifacts and bibliographic metadata and involved no human participants, patient data, or animal research. Institutional ethics approval and consent to participate were therefore not required.

### Competing interests

**[Both authors to confirm before submission.]** Draft statement: The authors declare no competing interests.

### Author contributions

**Draft CRediT statement, to be confirmed by both authors.** Moritz Milewski: Conceptualization; Data curation; Formal analysis; Investigation; Methodology; Project administration; Software; Visualization; Writing – original draft; Writing – review and editing. Martin Boeker: Methodology; Supervision; Writing – review and editing. Add **Validation** to Martin Boeker's roles only after he or another supervisor has completed and documented the independent stratified sample.

### Acknowledgements and use of generative AI

A generative AI coding assistant was used to support script development, deterministic data transformations, quality-control checks, and language editing. It did not make autonomous eligibility decisions or serve as an author. All class-level screening, interpretive coding, citation approval, and manuscript claims were made or confirmed by the human reviewer, and the authors take responsibility for the final work. **[Confirm that this description is complete and adapt it to the selected journal's disclosure policy and cover-letter requirements.]**

### Data and code availability

The complete class-level screening and charting record is provided as Supplementary Table S1 (`disease_terms_review_enriched.csv`). Supplementary Data S2 (`disease_terms_review.ttl`) contains all screening/evidence records, and Supplementary Data S3 (`disease_terms_synthesis.ttl`) contains the included-only synthesis view. Source modules, extraction and publication scripts, the schema, data dictionary, audit report, and release manifest are included in the publication supplement. The review ontologies use fixed non-resolving UUID URNs and are not maintained as web ontologies or in a separate public repository. The BioPortal API key is not distributed.

## Supplementary materials

- **Figure 1:** `Figures/prisma_scr_flow_diagram.png` and `.svg` — PRISMA-ScR flow diagram.
- **Supplementary Table S1:** `Extraction Tables/disease_terms_review_enriched.csv` — all 278 class-level screening and charting records.
- **Supplementary Data S2:** `Extraction Ontology/disease_terms_review.ttl` — complete evidence ontology.
- **Supplementary Data S3:** `Extraction Ontology/disease_terms_synthesis.ttl` — included-only synthesis ontology.
- **Supplementary Data S4:** `Extraction Ontology/native_hierarchy_modules/` and manifest — source-evidence modules and provenance.
- **Supplementary Methods S5:** extraction, PRISMA-figure, publication-readiness, and validation scripts in `Python scripts/`, plus the schema, data dictionary, audit report, and release manifest.

---

## Appendix A. Seed set (known-item validation)

*Formal-model proposals and critiques:* OGMS (Scheuermann et al., 2009); IDO dispositions (Goldfain et al., 2010); BFO (Arp et al., 2015); scalable representations and the BioTop pattern (Schulz et al., 2011); strengths and limitations of ontology-based representations (Schulz et al., 2009; Schulz et al., 2013); realizables and tendencies (Jansen et al., 2007; Röhl et al., 2014); the River Flow Model and causality (Mizoguchi et al., 2011; Rovetto et al., 2015); abnormal states (Yamagata et al., 2013; Yamagata et al., 2014); YAMATO (Mizoguchi et al., 2022); mental disease (Ceusters et al., 2010); bodily systems (Smith et al., 2004); disease entity theory (Hucklenbroich et al., 2014); and causal and natural-kind approaches (Smart et al., 2016; Tsou et al., 2016).

*Ontology artifacts to chart directly:* OGMS; DOID (Schriml et al., 2012; Kibbe et al., 2015; Schriml et al., 2019; Schriml et al., 2022); Mondo (Vasilevsky et al., 2022); IDO; HPO; ORDO/Orphanet; the NCIt disease branch; the SNOMED CT clinical finding/disorder hierarchy; the ICD-11 Foundation; the Mental Functioning/Mental Disease Ontology; the Neurological Disease Ontology; OAE; and the Disease Compass / Hozo RFM ontology.

## Appendix B. Charting form (controlled fields)

The full charting form is represented in the master CSV and exported through `review_core.ttl` (annotation namespace `urn:uuid:8f96cf34-53c2-48d2-88c5-96d07704fcf7#`). Its `rev:*` fields and controlled value sets are:

*Scope and provenance.* `manual_include_status` (include / exclude); `manual_exclusion_reason` (demo_or_training_resource, value_set_or_collection, out_of_scope, terminology_not_ontology, duplicate_imported_term, obsolete_or_noncurrent, insufficient_metadata, replaced_by_better_native_disease_model_candidate); `manual_exclusion_detail` (free text); `ontology_type_manual` (curated_ontology, clinical_terminology, thesaurus, value_set, application_ontology, demo_or_training_resource, generated_or_local_resource, unclear); `native_or_imported_manual` (native / imported / reused_unclear / unknown); `review_route` (independent_analysis_route / dependency_only_no_independent_analysis / mixed / unknown_namespace_needs_manual_check); `logical_inconsistency` (blank / wrong_is_a_hierarchy / contradictory_upper_level / reasoner_inconsistent / other_logical_error).

*Modelling interpretation.* `review_comment` (single free-text field — modelling interpretation plus any caveats, rationale, or paper evidence); `disease_model_category` (the buckets tabulated in Results).

*Four coupled design decisions* (each operationalising one decision from the Introduction): `ontological_category` (continuant / occurrent / mixed_continuant_occurrent_model / no_continuant_occurrent_commitment / unclear); `pathological_grounding` (statistical / evolutionary_function / normative / primitive_criteria / undefined / not_applicable); `crisp_vs_graded` (crisp / graded_or_fuzzy / prototype / gradedness_in_data / silent); `reality_vs_classification` (biological_state / illness_role / nosological_category / precision_medicine_stratification / conflated / unclear).

*Evidence quality.* `definition_quality`, `comment_quality`, `parentage_quality` (good / partial / poor / absent; `comment_quality` also not_applicable); `entity_quality_score` (0–3).

*Audit.* `reviewer`, `review_date`, `second_reviewer`, `second_review_date`, `disagreement_flag`, `adjudication_decision`.

## Appendix C. Reproducibility

The sole editable source is `disease_terms_review_enriched.csv`. `publication_readiness.py` builds native modules, normalizes citations, materializes effective decisions, exports both TTL views, and writes the audit report. `review_extraction_pipeline.py` provides registry extraction and the review UI. Generated release artifacts are `disease_terms_review.ttl`, `disease_terms_synthesis.ttl`, `review_core.ttl`, `native_hierarchy_modules/`, `native_hierarchy_modules_manifest.json`, `catalog-v001.xml`, and the reports under `Publication release/audit/`.

## Appendix D. PRISMA-ScR checklist crosswalk

Section locators are supplied while the manuscript remains in Markdown; replace them with final page numbers after journal formatting.

| Item | PRISMA-ScR topic | Where reported | Status / remaining action |
|---:|---|---|---|
| 1 | Title | Title | Reported |
| 2 | Structured summary | Structured summary | Reported |
| 3 | Rationale | Introduction: Rationale | Reported |
| 4 | Objectives | Introduction: Objectives | Reported using PCC |
| 5 | Protocol and registration | Methods: Protocol and registration | Protocol exists; retrospective OSF DOI/URL/date pending |
| 6 | Eligibility criteria | Methods: Eligibility criteria | Reported with rationale, language, date, artifact, and provenance rules |
| 7 | Information sources | Methods: Information sources | Reported with source-specific search dates |
| 8 | Search | Methods: Search; Supplementary Methods S5 | Full executable strategy and API parameters reported |
| 9 | Selection of sources | Methods: Selection of sources of evidence | One complete reviewer reported; stratified independent validation pending |
| 10 | Data charting process | Methods: Data charting process | One complete reviewer; prespecified 50-class independent sample pending; no investigator contact |
| 11 | Data items | Methods: Data items; Appendix B; Supplementary Table S1 | Reported |
| 12 | Critical appraisal | Methods: Critical appraisal | Optional item performed and reported as entity-quality appraisal |
| 13 | Synthesis methods | Methods: Synthesis of results | Reported |
| 14 | Selection results | Results: Selection of sources; Figure 1 | Reported with stage counts and exclusion reasons |
| 15 | Source characteristics | Results: Characteristics; Supplementary Table S1 | Reported per class with citation/no-citation status |
| 16 | Critical appraisal results | Results: Evidence quality; Supplementary Table S1 | Optional item performed and reported |
| 17 | Individual-source results | Results: Results of individual sources; Supplementary Table S1 | Complete per-class results supplied |
| 18 | Synthesis results | Results: Synthesis of results | Reported |
| 19 | Summary of evidence | Discussion: Summary of evidence | Reported and linked to user groups |
| 20 | Limitations | Discussion: Limitations | Reported |
| 21 | Conclusions | Discussion: Conclusions | Reported with implications and next steps |
| 22 | Funding | Funding; Limitations | Review funding reported; source-artifact funding was not charted and is disclosed as unavailable |

---

## References

*Draft reference inventory for Zotero reconciliation. Before submission, import or match every item in Zotero, verify author order, title, year, venue, pages, DOI, and preprint/publication status, remove this note, and export the complete list in the selected journal's style. Every in-text citation must have one matching entry and vice versa.*

Arp, R., Smith, B., & Spear, A. D. (2015). *Building ontologies with Basic Formal Ontology*. MIT Press.

Boorse, C. (1977). Health as a theoretical concept. *Philosophy of Science, 44*(4), 542–573. https://doi.org/10.1086/288768

Ceusters, W., & Smith, B. (2010). Foundations for a realist ontology of mental disease. *Journal of Biomedical Semantics, 1*, 10. https://doi.org/10.1186/2041-1480-1-10

Engelhardt, H. T., Jr. (1975). The concepts of health and disease. In H. T. Engelhardt Jr. & S. F. Spicker (Eds.), *Evaluation and explanation in the biomedical sciences* (pp. 125–141). Reidel. https://doi.org/10.1007/978-94-010-1769-5_9

Ereshefsky, M. (2009). Defining “health” and “disease”. *Studies in History and Philosophy of Biological and Biomedical Sciences, 40*(3), 221–227. **[Verify title punctuation and DOI in Zotero.]**

Goldfain, A., Smith, B., & Cowell, L. G. (2010). Dispositions and the Infectious Disease Ontology. In *Formal Ontology in Information Systems: Proceedings of FOIS 2010* (pp. 400–413). IOS Press. https://doi.org/10.3233/978-1-60750-535-8-400

Grenon, P., Smith, B., & Goldberg, L. (2004). Biodynamic ontology: Applying BFO in the biomedical domain. *Studies in Health Technology and Informatics, 102*, 20–38. PMID: 15853262.

Haendel, M. A., McMurry, J. A., Relevo, R., Mungall, C. J., Robinson, P. N., & Chute, C. G. (2018). A census of disease ontologies. *Annual Review of Biomedical Data Science, 1*, 305–331. https://doi.org/10.1146/annurev-biodatasci-080917-013459

Hucklenbroich, P. (2014). “Disease entity” as the key theoretical concept of medicine. *Journal of Medicine and Philosophy, 39*(6), 609–633. https://doi.org/10.1093/jmp/jhu040

Jansen, L. (2007). Tendencies and other realizables in medical information sciences. *The Monist, 90*(4), 534–554. https://doi.org/10.5840/monist200790436

Kibbe, W. A., Arze, C., Felix, V., Mitraka, E., Bolton, E., Fu, G., et al. (2015). Disease Ontology 2015 update: An expanded and updated database of human diseases for linking biomedical knowledge through disease data. *Nucleic Acids Research, 43*(D1), D1071–D1078. https://doi.org/10.1093/nar/gku1011

Mizoguchi, R., Kozaki, K., Kou, H., Yamagata, Y., Imai, T., & Ohe, K. (2011). River Flow Model of diseases. In *Proceedings of the International Conference on Biomedical Ontology 2011* (pp. 63–70). **[Verify proceedings metadata in Zotero.]**

Mizoguchi, R., & Borgo, S. (2022). YAMATO: Yet-another more advanced top-level ontology. *Applied Ontology, 17*(1), 211–232. https://doi.org/10.3233/AO-210257

Röhl, J., & Jansen, L. (2014). Why functions are not special dispositions: An improved classification of realizables for top-level ontologies. *Journal of Biomedical Semantics, 5*, 27. https://doi.org/10.1186/2041-1480-5-27

Rovetto, R. J., & Mizoguchi, R. (2015). Causality and the ontology of disease. *Applied Ontology, 10*(2). https://doi.org/10.3233/AO-150147 **[Add pages from Zotero.]**

Sadegh-Zadeh, K. (2000). Fuzzy health, illness, and disease. *Journal of Medicine and Philosophy, 25*(5), 605–638. https://doi.org/10.1076/0360-5310(200010)25:5;1-W;FT605

Scheuermann, R. H., Ceusters, W., & Smith, B. (2009). Toward an ontological treatment of disease and diagnosis. *Summit on Translational Bioinformatics*, 116–120. PMCID: PMC3041577.

Schriml, L. M., Arze, C., Nadendla, S., Chang, Y.-W. W., Mazaitis, M., Felix, V., et al. (2012). Disease Ontology: A backbone for disease semantic integration. *Nucleic Acids Research, 40*(D1), D940–D946. https://doi.org/10.1093/nar/gkr972

Schriml, L. M., Mitraka, E., Munro, J., Tauber, B., Schor, M., Nickle, L., et al. (2019). Human Disease Ontology 2018 update: Classification, content and workflow expansion. *Nucleic Acids Research, 47*(D1), D955–D962. https://doi.org/10.1093/nar/gky1032

Schriml, L. M., Munro, J. B., Schor, M., Olley, D., McCracken, C., Felix, V., et al. (2022). The Human Disease Ontology 2022 update. *Nucleic Acids Research, 50*(D1), D1255–D1261. https://doi.org/10.1093/nar/gkab1063

Schulz, S., Beisswanger, E., van den Hoek, L., Bodenreider, O., & van Mulligen, E. M. (2009). Alignment of the UMLS semantic network with BioTop: Methodology and assessment. *Bioinformatics, 25*(12), i69–i76. https://doi.org/10.1093/bioinformatics/btp194

Schulz, S., Spackman, K., James, A., Cocos, C., & Boeker, M. (2011). Scalable representations of diseases in biomedical ontologies. *Journal of Biomedical Semantics, 2*(Suppl 2), S6. https://doi.org/10.1186/2041-1480-2-S2-S6

Schulz, S., & Jansen, L. (2013). Formal ontologies in biomedical knowledge representation. *Yearbook of Medical Informatics, 8*(1), 132–146. https://doi.org/10.1055/s-0038-1638845

Smart, B. (2016). *The philosophy of disease*. Palgrave Macmillan. https://doi.org/10.1057/9781137552921

Smith, B., Munn, K., & Papakin, I. (2004). Bodily systems and the spatial-functional structure of the human body. *Studies in Health Technology and Informatics, 102*, 39–63. https://doi.org/10.3233/978-1-60750-945-5-39

Tricco, A. C., Lillie, E., Zarin, W., O'Brien, K. K., Colquhoun, H., Levac, D., et al. (2018). PRISMA Extension for Scoping Reviews (PRISMA-ScR): Checklist and explanation. *Annals of Internal Medicine, 169*(7), 467–473. https://doi.org/10.7326/M18-0850

Tsou, J. Y. (2016). Natural kinds, psychiatric classification and the history of the DSM. *History of Psychiatry, 27*(4), 406–424. https://doi.org/10.1177/0957154X16656580

Vasilevsky, N. A., Matentzoglu, N., Toro, S., Flack, J. E., Hegde, H., Unni, D. R., et al. (2022). Mondo: Unifying diseases for the world, by the world. *medRxiv*. https://doi.org/10.1101/2022.04.13.22273750 **[Check for a peer-reviewed replacement in Zotero before submission.]**

Wakefield, J. C. (1992). The concept of mental disorder: On the boundary between biological facts and social values. *American Psychologist, 47*(3), 373–388. https://doi.org/10.1037/0003-066X.47.3.373

Yamagata, Y., Kou, H., Kozaki, K., Mizoguchi, R., Imai, T., & Ohe, K. (2013). Ontological model of abnormal states and its application in the medical domain. In *Proceedings of the 4th International Conference on Biomedical Ontology* (CEUR Workshop Proceedings, Vol. 1060, pp. 22–27).

Yamagata, Y., Kozaki, K., Imai, T., & Ohe, K. (2014). An ontological modeling approach for abnormal states and its application in the medical domain. *Journal of Biomedical Semantics, 5*, 23. https://doi.org/10.1186/2041-1480-5-23

*Prepared as a PRISMA-ScR pre-submission draft. Current counts are generated from the master CSV but remain provisional until the reopened records and independent validation are complete. The retrospective OSF registration is submitted under embargo; see the status note.*
