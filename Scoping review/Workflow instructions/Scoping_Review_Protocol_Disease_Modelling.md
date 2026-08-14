# HISTORICAL SUBMITTED PROTOCOL: Scoping Review — How Disease Is Formally Modelled in Ontologies

> **Preserve for registration history; do not use as the publication-facing design description.** The protocol was submitted retrospectively under the label “scoping review.” On 10 August 2026 the implemented study was reclassified as a systematic cross-sectional evaluation of primary ontology artifacts because publications are not its units of analysis. See `OSF_Retrospective_Registration_Addendum.md` and `Reporting_Guideline_Applicability.md`. The underlying retrieval and coding procedures remain documented below.

*Draft protocol, v0.2. Written to be registrable (OSF / Open Science Framework) and PRISMA-ScR compliant. Scope deliberately narrowed to **ontological/computational modelling of disease**; the philosophy-of-medicine literature enters only where a formal model explicitly imports it. This version records the implemented master-table and OWL-release workflow.*

---

## 1. Rationale

Comparative treatments of how disease should be modelled exist only as **preambles to specific proposals** (OGMS as a disposition; the River Flow Model as causal chains; BioTop's "blurring" design pattern; SNOMED CT's mixed practice). No independent review charts the design space and evaluates the competing commitments and their published critiques. This produces three problems: (i) new ontology builders re-litigate the same continuant/occurrent and disposition/process choices from scratch; (ii) interoperability suffers because the same term ("disorder", "disease") denotes different ontological categories across resources; (iii) critiques are scattered and partisan. A scoping review is the appropriate instrument because the corpus is **heterogeneous** (journal papers, proceedings, ontology artifacts, standards) and the question is a **mapping** question, not an effect-estimation question.

## 2. Review questions

**Primary.** How is *disease* (and its immediate neighbours — disorder, pathological process, abnormal state) formally defined and represented across biomedical ontologies and ontology-engineering proposals, and what design commitments distinguish these approaches?

**Secondary.**
- S1. Which top-level/foundational ontology (BFO, DOLCE, YAMATO, BioTop, GFO, none) does each approach commit to, and how does that constrain the disease model?
- S2. To which ontological category is *disease* assigned (continuant/disposition, occurrent/process, causal chain, material structure, deliberately under-committed)?
- S3. How is the load-bearing primitive "abnormal/pathological" grounded (statistical, evolutionary/function, normative, primitive/criteria-based, left undefined)?
- S4. How is variation, gradedness, and uncertainty handled (crisp classes, fuzzy/graded, pushed to data/annotation)?
- S5. What published critiques target each approach, and on what grounds (logical, biological, clinical, computational)?

## 3. Objectives / deliverables

1. A **typology** of disease-modelling approaches.
2. A **review ontology** containing the included disease classes, imported source modules, and manual `rev:*` annotations along the dimensions in §8.
3. A **critique map** linking each approach to its objections and rebuttals.
4. Generated **charting tables and figures** derived from the review ontology for manuscript reporting.
5. An **evidence-gap statement** identifying under-served combinations of commitments.

## 4. Review type & reporting standard

Scoping review following **Arksey & O'Malley (2005)** as refined by **Levac et al. (2010)** and the **JBI** methodology; reported per **PRISMA-ScR** (Tricco et al. 2018). *Optional companion track:* for the subset that is software/artifact (ontologies, not argument papers), apply **Kitchenham & Charters (2007)** systematic-literature-review screening so that branch is reproducible. Register on **OSF**; no protocol amendments without dated changelog.

## 5. Eligibility criteria (PCC framework)

**Population/Participants:** not applicable in the clinical sense; the unit of analysis is a *formal account or artifact* that defines/represents disease.

**Concept:** the source must make an explicit **ontological or formal-representational commitment about what a disease (or disorder / pathological process / abnormal state) is** — a definition, axiomatisation, design pattern, or critique thereof.

**Context:** biomedical/clinical knowledge representation, applied/formal ontology, biomedical informatics, philosophy of medicine *where cited by or directly informing a formal model*.

### Inclusion
- I1. Presents, formalises, critiques, or substantially compares a definition/representation of disease in an ontology, terminology, or formal framework.
- I2. Any of: peer-reviewed articles; full conference papers (ICBO, FOIS, JOWO, MEDINFO, AMIA, KR-MED); books/chapters; **ontology artifacts themselves** (with documentation/IRIs); standards documentation (SNOMED CT, ICD-11 Foundation) where it states a disease model.
- I3. English (and German for the Hucklenbroich/Krankheitstheorie strand — declare as a scope choice; otherwise English-only with justification).
- I4. Any date (the foundational moves predate 2000).

### Exclusion
- E1. Uses a disease ontology purely as a *tool* (e.g. gene–disease association, NLP, CDSS) with **no statement about the disease model itself**.
- E2. Clinical/epidemiological "disease modelling" in the *mathematical/simulation* sense (compartmental models, etc.) — homonym, out of scope; **flag explicitly** because the keyword "disease modelling" retrieves these.
- E3. Pure philosophy of medicine with no connection to formal/computational representation (covered by a *separate* review; cite, don't chart).
- E4. Abstracts/posters without a retrievable full account.
- E5. Injury-only classes or ontologies retrieved by registry searches are out of scope for this disease-modelling review. Injury may be clinically related to disease, but it is not treated as a disease synonym and usually carries a different modelling commitment. These hits are recorded as term-scope exclusions for the flow diagram, but they are not included in the review ontology's active class set or independent synthesis.

## 6. Information sources

- **Databases:** PubMed/MEDLINE, Scopus, Web of Science, ACM Digital Library, IEEE Xplore, DBLP, PhilPapers (for the formal-philosophy bridge).
- **Proceedings (hand-search; poorly indexed):** ICBO, FOIS, JOWO, KR-MED, ODLS, MEDINFO, AMIA Summits/Symposia, SWAT4(HC)LS.
- **Ontology registries (artifact track):** OBO Foundry, BioPortal, Ontology Lookup Service (OLS), AberOWL.
- **Grey literature / docs:** ontology GitHub repos and ReadTheDocs (OGMS, Mondo, IDO, DOID, HPO), SNOMED CT editorial guide, ICD-11 Foundation reference guide.
- **Snowballing:** backward + forward citation chasing on the seed set (§9); known-author tracking (Smith, Ceusters, Schulz, Jansen, Mizoguchi, Hoehndorf, Schriml, Hucklenbroich).

## 7. Search strategy (illustrative)

Adapt per database; record full strings in an appendix. Core concept blocks combined with AND:

- **Disease block:** disease OR disorder OR "pathological process" OR "abnormal state" OR nosolog* OR pathologic*
- **Ontology block:** ontolog* OR "knowledge representation" OR "formal definition" OR axiom* OR "description logic" OR OWL OR "top-level ontology" OR BFO OR DOLCE OR OGMS OR taxonom*
- **Commitment block (to raise precision):** disposition OR continuant OR occurrent OR "causal chain" OR process OR realiz* OR "definition of disease" OR represent*

Pilot the string, report sensitivity, then freeze. Use the seed set (§9) as a **known-item validation**: a good strategy must retrieve all of them.

For ontology-registry extraction, use a two-tier term strategy. The primary exact-label tier searches the main disease-neighbour terms (`disease`, `disorder`, `illness`, `condition`, `health condition`, `syndrome`, `pathological process`, `pathological disposition`, `dysfunction`). A secondary sensitivity tier is then used to reduce false negatives from alternative root labels. Broad supplementary terms such as `pathological condition`, `pathological state`, `disease state`, `pathologic process`, and `morbid condition` are retained only for source ontologies that had no primary-term hit. Specific compound disease/disorder labels such as `DiseaseDisorderOrFinding`, `Disease or disorder`, and `Disease or syndrome` are retained as candidate disease-root classes because they may represent the relevant modelling class even when the same ontology also contains a generic `condition` class. Secondary-tier hits are marked with `discovery_tier = secondary_compound_label_sensitivity`.

`Pathological process` is treated as a disease-neighbour/fallback signal rather than as an ordinary disease synonym. If a source ontology already has a stronger disease-like review target (`disease`, `disorder`, `condition`, `syndrome`, etc.), its `pathological process` class is suppressed from the active class-review list and recorded as contextual vocabulary for the flow/audit tables. If no stronger disease-like target is found in that source ontology, `pathological process` remains eligible as a process-based candidate.

Non-canonical classes that explicitly declare `skos:exactMatch` to an already represented canonical disease-model class are treated as semantic reuses rather than independent modelling proposals, unless manual inspection shows that the source adds a materially different definition, superclass, or axiom pattern. The automated exclusion rule is intentionally conservative: it uses only ontology-authored `skos:exactMatch` metadata to recognised canonical disease-model roots (e.g. DOID, MONDO, OGMS, NCIT disease roots), not BioPortal LOOM mappings. Such rows are suppressed from the active class-review ontology/UI but retained in extraction and source-appearance tables with the exact-match target and a no-independent-analysis recommendation; canonical/reference roots remain reviewable as comparison anchors.

Likewise, source appearances whose class IRI resolves to a different native ontology namespace are treated as imported or reused vocabulary. They remain in the comprehensive extraction and source-appearance tables to document that the source ontology contains a disease-related term, but they are not exported to the active class-review ontology/UI for independent modelling assessment. The modelling assessment is assigned to the native class provider instead.

Classes with `rdfs:isDefinedBy` pointing to an external ontology class are treated as externally defined class reuses. They are retained in the comprehensive extraction and source-appearance tables with the defining class IRI, but suppressed from the active class-review ontology/UI unless manual inspection shows that the source ontology adds a materially different definition, superclass, or axiom pattern. `dcterms:conformsTo` is recorded as provenance/cross-reference evidence but is not by itself used as an exclusion criterion.

When manual hierarchy inspection identifies a better native disease-model candidate in the same ontology than the initially extracted label hit, the active review target may be refined. The replaced class remains recorded in the extraction provenance and flow-exclusion table under `replaced_by_better_native_disease_model_candidate`, while the replacement class is added to the active review ontology/UI.

Risk, susceptibility, predisposition, and disease-course terms are not treated as disease synonyms. They may be recorded as contextual evidence about a source ontology's disease-modelling vocabulary, but they are not active class-review targets for the disease-model synthesis unless the ontology explicitly models disease itself through such a class.

The literature/document search remains language-scoped to English, with German retained for the Hucklenbroich/Krankheitstheorie strand. This language restriction does not exclude ontology artifact classes solely because their labels are non-English. For ontology artifacts, apply a small multilingual label-sensitivity pass for French and German disease/disorder equivalents (e.g. `maladie`, `trouble`, `condition pathologique`, `Krankheit`, `Erkrankung`, `Störung`). These hits are marked with `discovery_tier = multilingual_label_sensitivity` and enter the same ontology-based review workflow.

## 8. Ontology-Based Data Charting

The unit of analysis is an OWL class identified by its IRI. The sole editable charting record is `disease_terms_review_enriched.csv`; the full evidence ontology and included-only synthesis ontology are generated from it. Each reviewed disease, disorder, condition, syndrome, abnormal state, or fallback pathological-process class resolves through a subject-sanitized native source module so the reviewer can inspect labels, definitions, comments, synonyms, and asserted superclass hierarchy directly in Protege or the review UI.

The generated `disease_terms_review.ttl` retains all screened records; `disease_terms_synthesis.ttl` contains only rows with `effective_synthesis_status = include`. Manual decisions are preserved separately from rule-derived effective decisions, and unresolved conflicts use `needs_user_decision`. Draft annotation dimensions — pilot on 5-10 sources/classes, then revise (Levac iterative step):

| Field | Values / notes |
|---|---|
| Citation / artifact IRI | — |
| Type | journal / proceedings / book / ontology artifact / standard |
| Year, venue | — |
| Foundational ontology | BFO / DOLCE / YAMATO / BioTop / GFO / none / other |
| **Category of *disease*** | disposition (continuant) / process (occurrent) / causal chain / material structure / under-committed / other |
| Category of *disorder* | material continuant / abnormal state / quality / process / n.a. |
| Pathological process modelled? | yes/no; relation to disorder (manifestation-of, part-of, constitutes) |
| Disease course modelled? | yes/no; how |
| **Grounding of "pathological/abnormal"** | statistical (Boorse) / function-evolutionary / normative / primitive-criteria (Hucklenbroich) / undefined / not applicable; reference classes such as age, sex, species, breed, or life stage qualify the underlying grounding rather than forming a separate category |
| Crisp vs graded | crisp DL classes / fuzzy / prototype / gradedness in data-annotation / silent |
| Ontology vs default knowledge | does it separate necessary axioms from typical/probabilistic associations? (Schulz distinction) |
| Reference-class / context handling | yes/no; mechanism |
| Identity & persistence criteria for a disease instance | stated / absent |
| Intended use case | integration / classification / reasoning / annotation / clinical |
| Empirical scale | # classes / # diseases / # axioms if reported |
| **Critiques received (and citing source)** | logical / biological / clinical / computational; reference |
| Self-stated limitations | — |

For ontology artifacts, class-level annotations should be attached directly to the reviewed class using `rev:*` properties from `review_core.ttl`. For papers, standards, or documentation that describe a disease model without one class IRI, create or reference a source-level record separately and link it to the affected class or modelling approach in the review notes.

### Native definition vs imported dependency

Ontology registries frequently report the same disease class IRI in many ontologies because the class is imported or reused. These appearances are not counted as independent disease-modelling commitments. For example, an application ontology that contains OGMS `disease` only through import is listed as an ontology appearance, but the disease model is charted and cited once under OGMS.

The artifact pipeline also applies a term-scope screen before class-level review. `Injury` hits are excluded at this stage because injury is not used as a synonym for disease in the review question. The excluded source appearances are kept in the generated exclusion table so the PRISMA-ScR-style flow diagram can report them transparently.

The artifact pipeline records whether a reviewed class was found in the primary exact-label tier or in the secondary sensitivity tier. Secondary hits enter the same class-level review workflow, but their discovery route is preserved as review context and should be reported separately in the methods/results.

Multilingual label-sensitivity hits are also preserved with their own discovery tier. They are not evidence that the literature language scope has changed; they are ontology-artifact evidence that a formally inspectable class was labelled in another language.

Therefore the artifact track reports two counts:

- native class implementations that can enter the independent analysis route;
- dependent/imported appearances that document reuse but do not receive independent class-quality assessment.

## 9. Candidate seed set to screen (known-item set)

*Formal-model proposals & critiques:* Scheuermann/Ceusters/Smith 2009 (OGMS); Goldfain et al. 2010 (IDO dispositions); Arp/Smith/Spear 2015 (BFO); Hoehndorf/Dumontier/Gkoutos 2011 (Scalable representations / BioTop pattern); Schulz et al. 2009 (strengths & limitations); Schulz & Jansen 2013; Röhl & Jansen 2014 (realizables); Jansen 2007 (tendencies); Mizoguchi et al. 2011 (River Flow); Rovetto & Mizoguchi 2015 (causality); Yamagata et al. 2013, 2014 (abnormal states); Mizoguchi & Borgo 2022 (YAMATO); Ceusters & Smith 2010 (mental disease); Smith/Munn/Papakin 2004 (bodily systems); Hucklenbroich 2014 (disease entity, bridge); Smart 2016 / Tsou 2016 (causal & natural-kind bridge).

*Ontology artifacts to chart directly:* OGMS, DOID (Schriml 2012/2015/2019/2022; Kibbe 2015), Mondo (Vasilevsky 2022), IDO, HPO, ORDO/Orphanet, NCIt (disease branch), SNOMED CT (clinical finding/disorder hierarchy), ICD-11 Foundation, Mental Functioning/Mental Disease Ontology, Neurological Disease Ontology, OAE, Disease Compass / Hozo RFM ontology.

## 10. Selection & synthesis process

- **Screening:** two reviewers, title/abstract then full text; κ for agreement; disagreements by discussion/third party. Tool: **Covidence** or **Rayyan**. Record reasons for full-text exclusion (PRISMA-ScR flow diagram).
- **Synthesis:** ontology-driven descriptive statistics + narrative. Export charting tables from the review ontology, then cross-tabulate **§8 "category of disease" × "grounding of pathological" × "crisp/graded"** to surface populated vs empty cells (the gap map). Produce the **critique map** as a directed graph (approach → objection → rebuttal).
- **No formal quality appraisal of "risk of bias"** (not meaningful for conceptual sources) — standard for scoping reviews; instead chart self-stated limitations and received critiques.

## 11. Anticipated limitations

- "Disease modelling" homonymy inflates retrieval with mathematical epidemiology (mitigated by E2 + concept blocks).
- Proceedings and artifact documentation are inconsistently indexed → reliance on hand-search and registries; risk of missing grey artifacts.
- Language scoping (English ± German) may under-represent non-Anglophone nosology theory.
- The continuant/occurrent commitment is sometimes *implicit* in axioms; charting it requires inspecting the OWL, not just the prose — declare this as a charting rule.

## 12. Indicative timeline

Protocol registration → pilot search & charting-form calibration (2–3 wks) → full search & deduplication → dual screening → charting → synthesis → PRISMA-ScR write-up. Realistic span 4–6 months at part-time effort.

---

### Note on positioning your own ontology
Keep the review **descriptive/neutral** (no advocacy) so it is citable as an independent map; reserve your design argument for a **separate companion paper** that cites the review as its justification. This is cleaner than a review-that-argues and avoids reviewer objections about a foregone conclusion.
