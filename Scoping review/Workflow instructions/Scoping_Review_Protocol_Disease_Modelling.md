# Scoping Review Protocol — How Disease Is Formally Modelled in Ontologies

*Draft protocol, v0.1. Written to be registrable (OSF / Open Science Framework) and PRISMA-ScR compliant. Scope deliberately narrowed to **ontological/computational modelling of disease**; the philosophy-of-medicine literature enters only where a formal model explicitly imports it.*

---

## 1. Rationale

Comparative treatments of how disease should be modelled exist only as **preambles to specific proposals** (OGMS as a disposition; the River Flow Model as causal chains; BioTop's "blurring" design pattern; SNOMED CT's mixed practice). No independent review charts the design space and evaluates the competing commitments and their published critiques. This produces three problems: (i) new ontology builders re-litigate the same continuant/occurrent and disposition/process choices from scratch; (ii) interoperability suffers because the same term ("disorder", "disease") denotes different ontological categories across resources; (iii) critiques are scattered and partisan. A scoping review is the appropriate instrument because the corpus is **heterogeneous** (journal papers, proceedings, ontology artifacts, standards) and the question is a **mapping** question, not an effect-estimation question.

## 2. Review questions

**Primary.** How is *disease* (and its immediate neighbours — disorder, pathological process, abnormal state, disease course) formally defined and represented across biomedical ontologies and ontology-engineering proposals, and what design commitments distinguish these approaches?

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

**Concept:** the source must make an explicit **ontological or formal-representational commitment about what a disease (or disorder / pathological process / disease course) is** — a definition, axiomatisation, design pattern, or critique thereof.

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

## 6. Information sources

- **Databases:** PubMed/MEDLINE, Scopus, Web of Science, ACM Digital Library, IEEE Xplore, DBLP, PhilPapers (for the formal-philosophy bridge).
- **Proceedings (hand-search; poorly indexed):** ICBO, FOIS, JOWO, KR-MED, ODLS, MEDINFO, AMIA Summits/Symposia, SWAT4(HC)LS.
- **Ontology registries (artifact track):** OBO Foundry, BioPortal, Ontology Lookup Service (OLS), AberOWL.
- **Grey literature / docs:** ontology GitHub repos and ReadTheDocs (OGMS, Mondo, IDO, DOID, HPO), SNOMED CT editorial guide, ICD-11 Foundation reference guide.
- **Snowballing:** backward + forward citation chasing on the seed set (§9); known-author tracking (Smith, Ceusters, Schulz, Jansen, Mizoguchi, Hoehndorf, Schriml, Hucklenbroich).

## 7. Search strategy (illustrative)

Adapt per database; record full strings in an appendix. Core concept blocks combined with AND:

- **Disease block:** disease OR disorder OR "pathological process" OR "abnormal state" OR nosolog* OR "disease course" OR pathologic*
- **Ontology block:** ontolog* OR "knowledge representation" OR "formal definition" OR axiom* OR "description logic" OR OWL OR "top-level ontology" OR BFO OR DOLCE OR OGMS OR taxonom*
- **Commitment block (to raise precision):** disposition OR continuant OR occurrent OR "causal chain" OR process OR realiz* OR "definition of disease" OR represent*

Pilot the string, report sensitivity, then freeze. Use the seed set (§9) as a **known-item validation**: a good strategy must retrieve all of them.

## 8. Ontology-Based Data Charting

The primary charting object is an OWL class in the review ontology, not a spreadsheet row. Each reviewed disease, disorder, pathological process, abnormal state, or disease-course class is represented by its class IRI. The review ontology imports the relevant source module so the reviewer can inspect labels, definitions, axioms, and superclass hierarchy directly in Protege.

Tables may be generated from the ontology for QA and reporting, but the durable review source is the ontology itself. Draft annotation dimensions — pilot on 5-10 sources/classes, then revise (Levac iterative step):

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
| **Grounding of "pathological/abnormal"** | statistical (Boorse) / function-evolutionary / normative / primitive-criteria (Hucklenbroich) / undefined / reference-class-indexed |
| Crisp vs graded | crisp DL classes / fuzzy / prototype / gradedness in data-annotation / silent |
| Ontology vs default knowledge | does it separate necessary axioms from typical/probabilistic associations? (Schulz distinction) |
| Reference-class / context handling | yes/no; mechanism |
| Identity & persistence criteria for a disease instance | stated / absent |
| Intended use case | integration / classification / reasoning / annotation / clinical |
| Empirical scale | # classes / # diseases / # axioms if reported |
| **Critiques received (and citing source)** | logical / biological / clinical / computational; reference |
| Self-stated limitations | — |

For ontology artifacts, class-level annotations should be attached directly to the reviewed class using `rev:*` properties from `review_core.ttl`. For papers, standards, or documentation that describe a disease model without one class IRI, create or reference a source-level record separately and link it to the affected class or modelling approach in the review notes.

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
