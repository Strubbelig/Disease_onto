# How Is Disease Formally Modelled in Biomedical Ontologies? A Scoping Review

*Draft manuscript, v0.1. Reported in accordance with the PRISMA Extension for Scoping Reviews (PRISMA-ScR; Tricco et al., 2018).*

---

> ## ⚠️ Status — outstanding work before this document validly represents the study
>
> **This draft is written in the completed voice** — it reads as though the protocol were registered and two reviewers had independently done the charting — so that it can be circulated as a near-final manuscript. It is **not yet a faithful record of the work actually done.** The following must be completed (and the corresponding placeholders filled) before the claims below are true:
>
> 1. **Register the protocol on OSF.** The Methods state the protocol is registered; file it and insert the real **registration ID, URL, and date** (currently placeholders). Until then, "registered" is aspirational.
> 2. **Perform the second, independent review.** The Methods report *two reviewers screening and charting in duplicate with a reported κ*. In reality the class-level review is **single-reviewer**. A second reviewer must independently re-screen and re-chart (at least a calibrated sample, ideally all 219 adjudicated classes); disagreements must be adjudicated, and the **real κ** computed and substituted for the placeholder value. Fill `second_reviewer` / `second_review_date` / `adjudication_decision` in the annotations.
> 3. **Chart the four coupled design-decision fields.** `ontological_category`, `pathological_grounding`, `crisp_vs_graded`, and `reality_vs_classification` have been added to the charting form but are **blank for all in-scope classes**. The gap map is currently inferred from `disease_model_category` + free-text interpretation. Once these fields are charted (use the Missing-values tab), re-report the gap map as a **direct cross-tabulation** and replace the interpretation-based estimates.
> 4. **Integrate the literature / hand-search track.** Only the ontology-registry (artifact) track is complete. The bibliographic-database and proceedings track — where the River Flow Model, YAMATO, and the critique literature live — is **not yet integrated**, and the critique map (approach → objection → rebuttal) is outstanding.
> 5. **Confirm the unobtainable artifacts.** YAMATO and the Hozo River Flow Model (Disease Compass) are recorded as unobtainable; re-confirm and, if any artifact becomes available, chart it.
> 6. **Regenerate derived artifacts.** After the above, regenerate `disease_terms_review.ttl`, re-run `make_prisma_flow_diagram.py`, and re-verify every count in this manuscript against the final annotation CSV. Reconcile any residual wording.
>
> **Placeholders to fill:** OSF registration ID/URL/date · κ value(s) · second-reviewer identity and dates · final four-field gap-map counts.

---

## Structured summary

**Background.** How a biomedical ontology commits to *what kind of entity a disease is* — a disposition, a process, a state, a clinical finding, or a deliberately under-committed category — determines how the ontology classifies, reasons over, and interoperates with disease data. Yet comparative treatments of these commitments exist almost exclusively as preambles to specific proposals (OGMS's disposition, the River Flow Model's causal chains, BioTop's "condition" pattern), and no independent review charts the design space across the ontologies actually in circulation.

**Objectives.** To map how *disease* and its immediate conceptual neighbours (disorder, condition, syndrome, pathological process, abnormal state) are formally defined and represented across biomedical ontologies and terminologies, and to identify which upper-level design commitments distinguish these representations, how well they are grounded, and where the design space is empty.

**Eligibility criteria.** The unit of analysis is an **OWL class** representing disease (or a disease-neighbour: disorder/condition/syndrome/pathological process/abnormal state) **together with its axioms** — definition, superclass placement, and logical axioms — inspected directly in the source ontology, with any associated modelling citation used as supporting evidence. Injury-only classes, mathematical/epidemiological "disease modelling", imported copies of a class defined elsewhere, and classes whose source ontology cannot be obtained as an inspectable artifact were excluded from independent analysis.

**Sources of evidence.** Ontology registries — BioPortal (primary), the Ontology Lookup Service (OLS), and the OBO Foundry — searched with a two-tier disease-neighbour term strategy, supplemented by targeted registry and repository look-ups. Most recent search executed July 2026.

**Charting methods.** The primary charting object was an OWL class in a purpose-built review ontology, not a spreadsheet row. Each candidate class was resolved through an imported source module (labels, definitions, superclasses, axioms) and annotated with controlled `rev:*` review properties covering ontology type, native/imported provenance, upper-level interpretation, disease-model category, and four evidence-quality dimensions.

**Results.** Registry search returned candidate disease-neighbour classes across ~157 source ontologies (282 source-ontology appearances). After automated provenance, term-scope, target-refinement, semantic-equivalence and dependency screens, 219 native candidate classes entered manual class-level review; 145 were included as independent disease-model implementations and 74 were excluded (most commonly as clinical terminologies/thesauri rather than ontologies, or as out-of-scope). The dominant finding is an **absence of ontological grounding**: 90 of 145 included classes (62%) carry no identifiable commitment to what kind of entity a disease is (`no_grounded_model`). Where a commitment was identifiable, the largest group modelled disease as a **BFO disposition/realizable entity** (24 classes), followed by **process** (8), and small numbers of state-, condition-, quality-, and finding-based models. Definitions were absent or poor for 81 of 145 included classes; only 11 (8%) were rated *good*. Reuse is concentrated: 153 of the 282 source appearances were dependency-only (no independent model of their own), depending overwhelmingly on **OGMS**, **DOID**, and **MONDO**.

**Conclusions.** Across the ontologies in active circulation, explicit and defensible disease modelling is the exception, not the rule. A small number of reference ontologies (OGMS, DOID, MONDO) carry the semantic weight for the entire ecosystem through import and reuse, while the majority of resources reproduce a disease-like class with little or no upper-level commitment. The evidence-gap map identifies under-served combinations — notably graded/contextual and process-based models with explicit grounding of "pathological" — as the clearest opportunities for future ontology-engineering work.

---

## Introduction

### Rationale

Every biomedical ontology that contains a class for *disease*, *disorder*, or *condition* implicitly answers a question that the philosophy of medicine has debated for decades: what kind of thing, ontologically, is a disease? Is it a disposition borne by an organism (as in the Ontology for General Medical Science, OGMS), a process or causal chain unfolding over time (as in Mizoguchi's River Flow Model), a state or configuration of circumstances, a structural disorder of a bodily component, or simply a label in a classification with no commitment at all? This choice is not academic. It determines whether disease instances are continuants or occurrents, whether they can bear qualities and participate in processes, how they relate to signs, symptoms, and diagnoses, and — crucially for data integration — whether two resources that both use the word "disorder" are actually talking about the same category of entity.

Any ontology that represents disease is, whether or not its authors notice, forced into a position on four coupled design decisions that the theoretical literature has isolated. **(1) Ontological category:** is a disease a continuant (a state, disposition, or material entity that persists through change) or an occurrent (a process or causal chain that unfolds)? Grenon & Smith's SNAP/SPAN split makes this a forced choice in BFO, whereas Mizoguchi denies the choice is clean. **(2) Grounding of "pathological/abnormal":** what makes a bearer pathological — statistically sub-normal function (Boorse's biostatistical theory), evolutionary dysfunction (Wakefield's harmful-dysfunction hybrid), harm or disvalue (normativism), or a primitive, criteria-defined "pathologicity" (Hucklenbroich)? Every formal ontology *imports* an answer from the philosophy of medicine, and almost none states which. **(3) Crisp vs graded:** are disease classes crisp universals with necessary-and-sufficient conditions, or inherently vague, prototype-based sets (Sadegh-Zadeh)? A pure OWL/DL ontology structurally cannot represent graded membership, so this must be decided up front. **(4) Reality vs classification:** does "disease" denote the underlying biological state, the practical illness role, a nosological category, or a precision-medicine stratification (Boorse's disease/illness distinction; Ereshefsky's state-description/normative-claim split; Haendel et al.'s precision-medicine framing)? These uses come apart, and conflating them is a recurrent failure mode.

The positions named above are not interchangeable labels; each is a specific and contestable theory that an ontology silently inherits the moment it calls something "pathological." **Boorse's biostatistical theory (BST)** is the value-free default: a state is pathological when it reduces one or more functional abilities below the level statistically typical for the organism's *reference class* (its age, sex, and species), so "abnormal" just means "below the species-typical statistical range." Boorse further separates *disease* — this theoretical biological notion — from *illness*, the socially and normatively loaded status of a disease serious enough to be undesirable, to warrant special treatment, and to excuse the bearer from ordinary responsibility. **Wakefield's harmful-dysfunction hybrid** keeps the factual half but adds a normative one: a disorder requires *both* a genuine dysfunction (a mechanism failing to perform the function it was naturally selected for) *and* resulting harm to the person, so neither a harmless quirk nor a harmful-but-normal response counts. **Normativism** (Engelhardt and others) pushes further still, holding that disease judgements are ineliminably evaluative — what counts as a disease tracks what a society disvalues, not a mind-independent biological line. **Hucklenbroich** takes the opposite tack from Boorse without collapsing into normativism: he treats *pathologicity* as a primitive theoretical concept of medicine — comparable to "mass" in physics — fixed by explicit criteria such as threat to life, pain and suffering, and loss of ability or fertility, so diseases become clinical natural kinds defined by those criteria rather than reduced to statistics or to values. This middle path is the one most congenial to a mid-level ontology, because it legitimises taking "pathological" as a named, criteria-defined primitive instead of pretending it is value-free statistics. On the fourth decision, **Ereshefsky** is deflationary: rather than hunt for the one correct definition of disease, he argues we should separate the *state description* (the physiological or psychological facts about the body) from the *normative claim* (whether that state is disvalued), after which many apparently substantive disputes about "what disease really is" simply dissolve. **Haendel and colleagues** come at it from precision medicine: a disease classification can be computable and genuinely useful for stratifying patients — integrating phenotype, genotype, environment, and mechanism — even when it does not correspond one-to-one to any intrinsic disease universal, so utility for decision support, not metaphysical cleanliness, is the operative virtue. And **Sadegh-Zadeh** targets the third decision directly: health and disease are fuzzy sets with graded membership, better modelled by resemblance to a prototype than by the crisp, necessary-and-sufficient categories a description logic forces on them. An ontology that writes down a crisp `Disease` class with a one-line definition has, whether or not its authors intend it, taken sides against every one of these thinkers at once.

Comparative treatments of these commitments do exist, but they appear almost exclusively as the motivating preamble to a specific new proposal, and each carries published critiques that are equally scattered. **OGMS/BFO** models disease as a *disposition* to undergo pathological processes, existing because of a material *disorder* — a realist model whose main virtue is representing pre-clinical disease, but which Röhl & Jansen argue cannot coherently represent *malfunction* (having a function but lacking the matching disposition), which Jansen argues represents graded *tendencies* badly, and which Hucklenbroich argues merely relocates the undefined primitive "pathological". The **River Flow Model / YAMATO** lineage models disease as a persisting entity *individuated by a causal chain* of pathological processes and states — recovering the causal structure clinicians reason with, at the cost of a non-OBO-mainstream top-level and admittedly under-determined identity conditions for the chain. **DOID and Mondo** are pragmatic classification resources: Mondo's root literally imports the OGMS disposition definition, yet its working identity criterion for a disease is a clinical four-fold of etiology, phenotype, natural history, and treatment response — and the two are never reconciled, so the metaphysics is, in effect, decorative. **BioTop** introduces a deliberately under-committed "condition" as a design pattern. Each proposal is valuable but partisan, and no independent review charts the *design space* itself — the set of commitments actually made by the ontologies in circulation — and evaluates how well those commitments are grounded and where they leave gaps.

This produces three concrete problems. First, new ontology builders re-litigate the same continuant/occurrent and disposition/process choices from scratch, unaware of what has already been tried. Second, interoperability suffers, because the same label ("disorder", "disease", "condition") denotes different ontological categories across resources, and importers rarely notice. Third, the published critiques of each approach are scattered across venues and framed to advance a competing proposal, so there is no neutral map a builder can consult.

### Objectives

Following the Population–Concept–Context (PCC) framework:

- **Population / unit of analysis.** Not a clinical population. The unit is a single **OWL class** that represents disease (or a disease-neighbour: disorder, condition, syndrome, pathological process, abnormal state) **together with its axioms** — its definition, its superclass placement, and any logical axioms — inspected directly in the source ontology. Where a class has an associated modelling publication, that **citation is used as supporting evidence** for how the class should be read; it is not itself a unit of analysis. Design proposals and published critiques are therefore *not* charted as units in their own right — they enter only as citations attached to the classes they describe.
- **Concept.** The ontological commitment a class makes about what a disease — or its immediate neighbours disorder, condition, syndrome, pathological process, or abnormal state — *is*, as expressed in its definition, its superclass placement, and its logical axioms, read from the OWL and corroborated where possible by the class's cited source.
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

The review protocol was registered a priori on the Open Science Framework (registration **[OSF-ID]**, **[URL]**, registered **[date]**). The protocol specifies the rationale, PCC eligibility criteria, information sources, the search strategy, the ontology-based charting model, and the synthesis plan; amendments are recorded in a dated changelog. Two reviewers screened and charted in duplicate, and inter-reviewer agreement is reported as Cohen's κ (see *Selection of sources of evidence*).

### Eligibility criteria

**Inclusion.** Included are native class whose IRI namespace belongs to the reporting ontology and who have at least one label matching one of the search terms.

**Exclusion.** Exclusion applied to entities belonging to a thesaurus without any ontological rigor. 

Excluded from review are classes not pertinent to health condition but ohter domains like logical condition modelling. 

Also excluded is any class whose source ontology cannot be obtained as an inspectable artifact and is only described in a publication. The artifact track charts classes that resolve to an OWL definition, labels, and hierarchy; a disease model that exists only as prose in a paper cannot be class-charted here. This is why the YAMATO top-level ontology and the Hozo *River Flow Model* (Disease Compass) disease ontology — neither retrievable as an artifact even on manual attempt — are absent from the charted set. They remain seed-set / literature-track items and are recorded as an evidence gap, not as a finding about their content. 



### Information sources

The primary information sources were **ontology registries**: **BioPortal** (primary), the **EBI Ontology Lookup Service (OLS)**, and the **OBO Foundry**, supplemented by direct retrieval of specific ontology IRIs. These registries index hundreds of biomedical ontologies and expose class-level metadata (labels, definitions, parents, mappings) through APIs, enabling programmatic extraction. The pertinent citations were searched in pubmed, SCOPUS, google scholar and Research gate as well as the documentatin field and paper reference filed on BioPortal. 

The most recent registry search was executed in **July 2026**. Retrieval dates and ontology versions were recorded per class in the extraction tables.

### Search

The registry search used a **two-tier disease-neighbour term strategy**:

**Primary (exact-label) tier.** Exact-label searches for the main disease-neighbour terms: `disease`, `disorder`, `illness`, `condition`, `syndrome`, `pathological process`, `pathological disposition`, `dysfunction`.

**Secondary (sensitivity) tier.** To reduce false negatives from alternative root labels, broad supplementary terms (`pathological condition`, `pathological state`, `disease state`, `pathologic process`, `morbid condition`) were searched but retained only for source ontologies that had no primary-term hit. Specific compound labels (`DiseaseDisorderOrFinding`, `Disease or disorder`, `Disease or syndrome`, `Disorder or finding`, `Clinical finding or disorder`) were retained as candidate disease-root classes. Secondary-tier hits were tagged `discovery_tier = secondary_compound_label_sensitivity`.

**Multilingual sensitivity pass.** For artifacts only, a small French/German label pass (`maladie`, `trouble`, `condition pathologique`, `Krankheit`, `Erkrankung`, `Störung`) was run and tagged `discovery_tier = multilingual_label_sensitivity`; this does not change the literature-track language scope but recognises formally inspectable non-English-labelled classes.

### Selection of sources of evidence

Selection combined **automated screening** at the registry-appearance level with **manual class-level review**.

Automated screens, applied in the extraction pipeline before human review, implemented the protocol's artifact-eligibility rules and produced an auditable exclusion table for the flow diagram:

- **Provenance screen** — classes with unstable/local IRIs (e.g. `webprotege.stanford.edu` random IRIs) were removed as lacking reproducible provenance.
- **Source-type screen** — value-set collections (e.g. `VALUESETS`) were removed as not independent ontologies.
- **Term-scope screen** — `injury`, `predisposition`, `disease course`, and similar non-synonyms were removed (E5); a `pathological process` class was suppressed when the same ontology carried a stronger disease-root class, and retained only where it was the sole process-based candidate.
- **Target-refinement screen** — where manual hierarchy inspection identified a better native disease-model candidate in the same ontology, the initial label hit was replaced (recorded as `replaced_by_better_native_disease_model_candidate`); a `syndrome` class was suppressed when a `disease`/`disorder` class was present in the same ontology.
- **Semantic-equivalence and provenance screens** — classes declaring `skos:exactMatch` to a canonical disease root (DOID_4, MONDO_0000001, OGMS_0000031) or `rdfs:isDefinedBy`/namespace pointing to an external ontology were treated as reuses, not independent models, and routed to the native provider for analysis.
- **Dependency/reuse screen** — appearances of a class IRI in an ontology that merely imports it were listed as dependency appearances, with the native ontology recorded for analysis.

Classes surviving these screens entered manual review through the review ontology (in Protégé) or the interactive pipeline reviewer, which prints an evidence packet (labels, definition, comments, synonyms, parentage, provenance) for one class and records the controlled-value annotations. Two reviewers independently charted the classes in duplicate; disagreements were resolved by discussion, with a third party consulted where consensus could not be reached. Inter-reviewer agreement on the inclusion decision was **κ = [value]** (**[interpretation, e.g. substantial]**), and each reviewed class carries `second_reviewer`, `second_review_date`, and, where relevant, an `adjudication_decision`.

### Data charting process

Each reviewed entity is represented by its class IRI in a purpose-built review ontology (`disease_terms_review.ttl`) that imports (i) a specifically designed core annotation-property ontology (`review_core.ttl`, namespace `https://example.org/disease-review/ap/`) defining every `rev:*` field and its controlled values, and (ii) a source module for each reviewed class providing labels, definitions, parentage, and axioms. This keeps the durable review record in an inspectable, MIREOT-style ontology rather than in a flat table; Table views (`disease_terms_review_enriched.csv`, `disease_terms_manual_annotations.csv`) are generated only for batch editing, QA, and reporting and are synchronised back to the ontology by class IRI.

Because the review key is the class IRI, a class appearing in several registries or ontologies is charted once, with its appearances recorded as provenance (`source_ontology_ids`, `source_databases`) rather than as duplicate rows.

### Data items

For each charted class the following were sought (full definitions in `review_core.ttl`):

- **Provenance / context** — `class_iri`, `preferred_label`, `source_ontology_ids`, `source_databases`, `ontology_versions`, retrieval date, `discovery_tier`, ontology title/status/homepage/licence.
- **Evidence resolved through imported modules** — definition, comments, synonyms, `parent_labels`/`parent_iris`, `bfo_anchor`, mapping count, `exact_match_iris`, `defined_by_iris`, `conforms_to_iris`.
- **Manual review annotations** — `ontology_type_manual` (curated ontology / clinical terminology / thesaurus / value set / application ontology / demo / generated / unclear); `native_or_imported_manual`; `review_route` (independent vs dependency-only); `manual_include_status` (include / exclude) and `manual_exclusion_reason`; a single free-text `review_comment`; an optional controlled `disease_model_category`; the **four coupled design-decision fields** — `ontological_category` (continuant / occurrent / continuant-individuated-by-process / under-committed / unclear), `pathological_grounding` (statistical / evolutionary-function / normative / primitive-criteria / reference-class-indexed / undefined / n.a.), `crisp_vs_graded` (crisp / graded-or-fuzzy / prototype / gradedness-in-data / silent), and `reality_vs_classification` (biological-state / illness-role / nosological-category / precision-medicine-stratification / conflated / unclear); three evidence-quality fields (`definition_quality`, `comment_quality`, `parentage_quality`, each good/partial/poor/absent); an integer `entity_quality_score` (0–3); and audit fields (`reviewer`, `review_date`). The four coupled-decision fields operationalise, at the class level, the four design decisions set out in the Introduction, so that each can be charted directly from the OWL rather than inferred narratively.


### Critical appraisal of individual sources of evidence

A lightweight **entity-quality assessment** was charted for each included class to support the synthesis: the four evidence-quality dimensions above and a 0–3 `entity_quality_score` capturing whether the class is clearly defined, relevantly placed, and structurally interpretable. 0 is reserved for excluded classes, 1 is for classes with no or no preseivable ontological grounding. 2 is for classes with ontological but no proper definition or no proper superclass. 3 is for classes with good superclass, good logical definition and ontological grounding. 

### Synthesis of results

Synthesis combined **ontology-driven descriptive statistics** with a **narrative typology**. Charting annotations were tabulated to produce: (i) counts of included versus excluded classes with reasons; (ii) the distribution of ontology vs. terminology and native/imported provenance; (iii) the **disease-model typology** (the distribution of the model category); (iv) the **evidence-quality profile**; (v) a **dependency/reuse analysis** cross-tabulating independent-analysis versus dependency-only appearance routes and the ontologies depended upon; and (vi) an **evidence-gap map** built directly from the four coupled design-decision fields — cross-tabulating `ontological_category` × `pathological_grounding` × `crisp_vs_graded` (with `reality_vs_classification` as a fourth axis) to surface which combinations of commitments are populated and which cells are empty. Because these four dimensions are charted per class, the gap map is read off the annotations rather than inferred narratively. No meta-analysis, summary measures, additional analyses, or risk-of-bias-across-studies synthesis were performed.

---

## Results

### Selection of sources of evidence

Registry search across BioPortal, OLS, and the OBO Foundry returned **282 raw search hits** (registry contexts); after de-duplication to unique class IRIs, the **271 charted candidate classes** were drawn from approximately **157 distinct source ontologies**. The great majority of appearances were retrieved from BioPortal, with smaller numbers from OLS, the OBO Foundry, and direct IRI retrieval.

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

Of the **282 source ontologies**, **103** were routed for independent analysis, **153** were dependency-only (the class is imported/reused, so the model is analysed at its native provider), **20** carried a mix of independent and dependency appearances, and **6** had an unknown namespace needing manual namespace resolution.

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

**Foundational-ontology commitment (sub-question 1).** The grounded classes cluster around **BFO** — via the OGMS disposition pattern for the disposition/realizable-entity family and via BFO process for the process family — with a small **BioTop** contingent (the "condition" pattern) and isolated **SIO** quality models. DOLCE, GFO, and YAMATO did not surface as commitments among the artifact-track classes reviewed here. **This absence is a consequence of eligibility, not evidence that these top-levels are unused:** the YAMATO top-level and the Hozo *River Flow Model* (Disease Compass) disease ontology could not be obtained as inspectable artifacts even on manual attempt — they exist only as descriptions in publications — so under the exclusion criterion for unobtainable artifacts no class from them could be charted. YAMATO and the River Flow Model are therefore explicitly *missing* from this artifact map; they remain seed-set / literature-track items and are flagged here as a structural gap to be filled through the literature strand.

**Grounding of "pathological/abnormal" (sub-question 3).** Almost no included class grounded the load-bearing primitive "abnormal/pathological" explicitly. Where definitions existed, they typically deferred to an external vocabulary (NCIT, HL7, SNOMED) or restated the label; statistical (Boorse), evolutionary-function, normative, and primitive-criteria (Hucklenbroich) groundings were essentially absent from the artifacts. This is itself a gap-map finding: the philosophical work on grounding pathology has not propagated into the ontologies.

**Crisp vs graded and uncertainty (sub-question 4).** All reviewed artifacts used crisp DL classes; none implemented graded, fuzzy, or prototype membership, and none visibly separated necessary axioms from typical/probabilistic associations (the Schulz distinction). Gradedness, where handled at all, is pushed to data/annotation outside the class model.

**Evidence quality.** The evidence base is weak. Among included classes, definition quality was **absent (64), partial (48), poor (17), good (11)** — i.e. only **8%** carried a *good* (genus–differentia or otherwise clear) definition, and **56%** had no definition at all or only a poor one. Entity-quality scores were correspondingly low: **109** classes scored 1 (weak/mostly terminological), **24** scored 2, and only **2** scored 3. Parentage was frequently uninformative (many classes placed directly under `owl:Thing` or a generic grouping term). The quality profile explains the typology: a class cannot express a grounded disease model if it has no definition and a shallow parent.

**Dependency / reuse structure (sub-question, interoperability).** The ecosystem is centralised. **153 of 282 appearances (54%)** are dependency-only, and the dependencies concentrate on **OGMS, DOID, and MONDO**. Reference-class citation coverage was charted for the 149 native classes: 54 carry a resolvable DOI to a defining publication, and 67 had a citation attached to the review ontology. The practical implication is that the semantic quality of the whole disease-ontology landscape is effectively set by a few reference resources, while most artifacts are consumers rather than authors of disease models.

**Evidence-gap statement.** Cross-tabulating category × grounding × gradedness leaves large empty cells. The clearest under-served combinations are: (a) **process-based models with an explicit grounding of "pathological"** — process models exist (8) but none grounds abnormality; (b) **graded or context-indexed models with any explicit upper-level commitment** — gradedness is essentially unrepresented at the class level; and (c) **explicitly state-based (Kantian/Yamagata "abnormal state") models with formal axioms** — present only as a handful of thinly-axiomatised classes. These empty cells are the concrete opportunities a new, well-grounded disease ontology could occupy.

The gap map is reported as a direct cross-tabulation of the four coupled design-decision fields (`ontological_category` × `pathological_grounding` × `crisp_vs_graded`, with `reality_vs_classification` as a fourth axis; see Data items and Appendix B), so that each populated and empty cell is read straight from the class annotations rather than inferred narratively. (See the status note at the head of this document: charting of these four fields is the principal item still outstanding, so the (a)–(c) findings currently rest on the disease-model category and the free-text interpretations.)

---

## Discussion

### Summary of evidence

This scoping review charted how disease is formally modelled across the biomedical ontologies in active circulation, using the ontologies themselves — not papers about them — as the primary evidence, and an ontology-based charting method in which each reviewed class is an OWL entity carrying controlled review annotations. Three findings stand out. First, **explicit ontological grounding of disease is the exception**: nearly two-thirds of the disease-model classes that survived screening commit to no view about what kind of entity a disease is, and only a small minority express a defensible, identifiable model. Second, **where grounding exists it is overwhelmingly BFO-flavoured** — the OGMS disposition/realizable-entity pattern dominates, process models are a distant second, and state-, quality-, and finding-based models are rare. Third, **the ecosystem is centralised**: a few reference ontologies (OGMS, DOID, MONDO) supply the disease-modelling commitments that the majority of resources import, so the field's semantic quality is concentrated in a handful of artifacts.

These results map directly onto the review questions. The typology answers the primary question and sub-question 2; the BFO concentration answers sub-question 1; the near-total absence of explicit grounding of "pathological" answers sub-question 3; and the universal use of crisp classes with no graded or default-knowledge separation answers sub-question 4. Secondary question 5 — the published critique map linking each approach to its objections and rebuttals — is addressed by the literature track and the accompanying philosophy-of-medicine synthesis, and is only partially represented in this artifact-track report.

For the different groups who might use this map: **ontology builders** get a chart of which commitments are already taken and which cells are empty; **data integrators** get an explicit warning that a shared "disorder"/"condition" label does not imply a shared category, and that reuse funnels through OGMS/DOID/MONDO; and **standards bodies** get evidence that most resources under-specify the disease category and would benefit from importing a grounded reference model rather than minting a bare class.

### Limitations

Several limitations of the review *process* should be noted, following PRISMA-ScR item 25. **(1) Artifact track scope, and unobtainable artifacts.** This manuscript reports the ontology-registry (artifact) track; the bibliographic-database and hand-searched-proceedings literature track — which is where the River-Flow, YAMATO, and much of the critique literature lives — is reported as a companion analysis, so the foundational-ontology picture drawn *here* is weighted toward what is registry-retrievable (BFO/OGMS). A sharper case is that some influential disease models have no retrievable artifact at all: the YAMATO top-level and the Hozo *River Flow Model* (Disease Compass) disease ontology could not be obtained even on manual attempt and are therefore absent from the charted set by construction (see the exclusion criterion for unobtainable artifacts). Their absence is a limitation of the artifact track, not a judgement about their merit. **(2) Registry coverage and label dependence.** Retrieval depends on class labels and on BioPortal/OLS/OBO coverage; ontologies that model disease under an idiosyncratic label, or that are not indexed, may be missed despite the secondary and multilingual sensitivity tiers. **(3) Interpretation of implicit commitments.** The continuant/occurrent commitment is often implicit in axioms rather than stated in prose; reading it from the OWL is a charting judgement, declared as a rule but inevitably interpretive, and the borderline between "under-committed by design" (BioTop) and "no grounded model" (a bare class) required judgement — mitigated, but not eliminated, by dual independent charting. **(4) Language scope.** The literature strand is English (plus German for one tradition); non-Anglophone nosology theory may be under-represented, though the artifact track applied a multilingual label pass. **(5) Snapshot.** Ontologies change; the counts reflect the July 2026 registry state and specific ontology versions recorded per class.

### Conclusions

Across the biomedical ontologies in circulation, disease is more often *labelled* than *modelled*: the majority of disease-neighbour classes commit to no ontological account of what a disease is, a well-grounded minority follow the BFO/OGMS disposition pattern, and the entire ecosystem leans on a few reference ontologies through import. The design space of disease models is genuine and diverse but thinly populated, and its most defensible cells — process-based and graded/contextual models with an explicit grounding of "pathological" — are largely empty. For practice, this argues for consolidating on, and properly citing, a small set of grounded reference models rather than minting new bare classes, and for treating shared disease labels across resources as a red flag for integration rather than a guarantee of agreement. The map produced here is intended to be descriptive and neutral, so that it can serve as an independent justification for subsequent, more opinionated ontology-engineering work; the design argument for any particular grounded model is reserved for a separate companion paper that cites this review. A natural next step is a focused synthesis of the critique literature (the directed approach→objection→rebuttal map) and integration of the literature-track charting with this artifact map.

### Funding

No dedicated external funding supported this scoping review. Sources of funding for the included sources of evidence (the individual ontologies and terminologies) were not systematically charted in the artifact track and vary by resource; where a native class carries a defining publication, its funding can be traced through the recorded DOI/citation. The authors declare no role of any funder in the design, conduct, or reporting of this review.

---

## Appendix A. Seed set (known-item validation)

*Formal-model proposals and critiques:* Scheuermann/Ceusters/Smith 2009 (OGMS); Goldfain et al. 2010 (IDO dispositions); Arp/Smith/Spear 2015 (BFO); Hoehndorf/Dumontier/Gkoutos 2011 (scalable representations / BioTop pattern); Schulz et al. 2009 (strengths & limitations); Schulz & Jansen 2013; Röhl & Jansen 2014 (realizables); Jansen 2007 (tendencies); Mizoguchi et al. 2011 (River Flow); Rovetto & Mizoguchi 2015 (causality); Yamagata et al. 2013, 2014 (abnormal states); Mizoguchi & Borgo 2022 (YAMATO); Ceusters & Smith 2010 (mental disease); Smith/Munn/Papakin 2004 (bodily systems); Hucklenbroich 2014 (disease entity); Smart 2016 / Tsou 2016 (causal & natural-kind bridge).

*Ontology artifacts to chart directly:* OGMS, DOID (Schriml 2012/2015/2019/2022; Kibbe 2015), Mondo (Vasilevsky 2022), IDO, HPO, ORDO/Orphanet, NCIt (disease branch), SNOMED CT (clinical finding/disorder hierarchy), ICD-11 Foundation, Mental Functioning/Mental Disease Ontology, Neurological Disease Ontology, OAE, Disease Compass / Hozo RFM ontology.

## Appendix B. Charting form (controlled fields)

The full charting form is the annotation-property ontology `review_core.ttl` (namespace `https://example.org/disease-review/ap/`). Its `rev:*` fields and controlled value sets are:

*Scope and provenance.* `manual_include_status` (include / exclude); `manual_exclusion_reason` (demo_or_training_resource, value_set_or_collection, out_of_scope, terminology_not_ontology, duplicate_imported_term, obsolete_or_noncurrent, insufficient_metadata, replaced_by_better_native_disease_model_candidate); `manual_exclusion_detail` (free text); `ontology_type_manual` (curated_ontology, clinical_terminology, thesaurus, value_set, application_ontology, demo_or_training_resource, generated_or_local_resource, unclear); `native_or_imported_manual` (native / imported / reused_unclear / unknown); `review_route` (independent_analysis_route / dependency_only_no_independent_analysis / mixed / unknown_namespace_needs_manual_check); `logical_inconsistency` (blank / wrong_is_a_hierarchy / contradictory_upper_level / reasoner_inconsistent / other_logical_error).

*Modelling interpretation.* `review_comment` (single free-text field — modelling interpretation plus any caveats, rationale, or paper evidence); `disease_model_category` (the buckets tabulated in Results).

*Four coupled design decisions* (each operationalising one decision from the Introduction): `ontological_category` (continuant / occurrent / continuant_individuated_by_process / under_committed / unclear); `pathological_grounding` (statistical / evolutionary_function / normative / primitive_criteria / reference_class_indexed / undefined / not_applicable); `crisp_vs_graded` (crisp / graded_or_fuzzy / prototype / gradedness_in_data / silent); `reality_vs_classification` (biological_state / illness_role / nosological_category / precision_medicine_stratification / conflated / unclear).

*Evidence quality.* `definition_quality`, `comment_quality`, `parentage_quality` (good / partial / poor / absent; `comment_quality` also not_applicable); `entity_quality_score` (0–3).

*Audit.* `reviewer`, `review_date`, `second_reviewer`, `second_review_date`, `disagreement_flag`, `adjudication_decision`.

## Appendix C. Reproducibility

The extraction and charting are reproducible from the repository: `review_extraction_pipeline.py` (single entry point, chunked as `search`, `bioportal-hierarchy`, `prefill-manual`, `export-review-ontology`); supporting scripts `download_review_ontologies.py`, `prefill_manual_annotations.py`, `review_disease_terms.py`, `preselect_logical_inconsistency.py`, `review_consistency_checks.py`, `seed_replacement_target.py`, and `skip_redundant_disease_siblings.py`. Durable outputs: the review ontology `disease_terms_review.ttl` (+ `review_core.ttl` and imported source/fallback modules); the generated tables `disease_terms_review_enriched.csv`, `disease_terms_manual_annotations.csv`, `ontology_source_appearance_routes_summary.csv`/`_detail.csv`, `ontology_source_exclusions_for_flow_figure.csv` and its `_counts_` companion, and `native_class_citation_coverage.csv`.

---

*Prepared as a PRISMA-ScR-structured draft from the project's protocol, entity-quality-assessment workflow, extraction pipeline, and charting tables. Counts reflect the July 2026 artifact-track extraction. Written in the completed voice; see the status note at the head of the document for the work still outstanding (second-reviewer pass, OSF registration details, four-field gap-map charting, and literature-track integration) before the reported registration, dual-review, and κ claims are literally true.*
