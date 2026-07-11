# Final TODO — Mid Layer Disease Ontology

This file merges and supersedes:

- `TODO_ontology_revisions.md`
- `TODO_2_predisposition_and_strictening.md`
- `TODO_3_publication_and_mentor_readiness.md`
- `TODO_4_DL_validation_and_final_cleanup.md`

Conflict rule used for this consolidation: **later TODOs win**. In particular, TODO 4 overrides older instructions where they conflict with the current ontology.

Current status: the ontology source is a reasoner-checked draft, with validation recorded in `VALIDATION.md`. Because `Disease proposal 2.ttl` has been edited after the last merge/inference, derived artefacts should be regenerated before sharing.

---

## Active Remaining Tasks

- [ ] **F1 — Rebuild derived artefacts from the current source.** `Disease proposal 2.ttl` was edited after the current `Disease proposal 2 merged.owl` and `Disease_proposal_2_inferred-3.owl` were created. Rebuild the merged OWL and, if desired, regenerate the inferred OWL.

- [x] **F2 — Remove or regenerate stale merged TTL.** The old `Disease proposal 2 merged.ttl` artefact is no longer present, so it should not confuse reviewers.

- [ ] **F3 — Decide whether to keep a generated merged TTL at all.** If both RDF/XML and Turtle merged artefacts are wanted, update `build_disease_proposal.sh` to produce both. Otherwise keep only `Disease proposal 2 merged.owl` and document that choice.

- [ ] **F4 — Add a one-page mentor summary.** Include the core thesis, contribution claim, validation status, 2-3 worked examples, and the questions you want Martin Boeker to judge.

- [ ] **F5 — Optional: add phenotype/absence example patterns only if needed.** If a biology-side phenotype link is wanted, attach phenotype to the organism, not the disorder. If absence cases need explicit recording of what is missing, use a positive count/configuration pattern or keep the norm in the knowledge layer.

- [ ] **F6 — Optional: formalize the disease-A to disease-B predisposition pattern further.** The current model covers existing-disorder-grounded predisposition and complication realization, but a named A-to-B target pattern could still be added if needed for examples or competency questions.

- [ ] **F7 — Decide the substance-use-disorder modelling stance.** Treat this as an edge case for pathologicity: distinguish the substance, use events, intoxication/withdrawal processes, diagnostic thresholds, and any stable pathological neuropsychological organization that could ground a disorder. Avoid modelling substance use disorder as a moral defect, legal category, or mere single behaviour.

---

## Resolved Modelling Conflicts

- [x] **R1 — Compound pathological disorder uses `has part some`, not `has part min 2`.** Earlier TODO 2 requested `min 2`, but TODO 4 and OWL 2 DL validation override it. Cardinality over BFO `has part` caused a DL profile violation, so the current pattern is:
  ```text
  pathological disorder
   and has part some pathological disorder
  ```

- [x] **R2 — Base disease predisposition does not require an actual realization process.** Earlier TODO 2 A1 included `has realization some disorder development process` on `disease predisposition`. Later review showed this overcommits unrealized risk by entailing an anonymous realization process. Current resolution: base `disease predisposition` is a tendency inhering in a person and grounded in a material basis; `realized disease predisposition` carries the realization existential.

- [x] **R3 — Inherence relation is BFO `inheres in` (`BFO_0000197`).** Older notes mentioned RO inherence labels. The current ontology consistently uses BFO `BFO_0000197` for tendency/risk inherence.

- [x] **R4 — Genetic risk uses a material pathogenic variant, not DOID.** `pathogenic genetic variant` is a material/pathological variant class used as the material basis for `genetic predisposition`; DOID disease categories remain epistemic/classificatory rather than material bases.

- [x] **R5 — Silent/subclinical status is not a material disease kind.** The earlier `silent disorder` material subclass was retired; silent/subclinical status belongs in the observation or epistemic layer if needed.

- [x] **R6 — Wound `ground_truth.owl/WOND_...` namespace duplication is resolved.** The current merge uses the MILD namespace and no longer shows the old imported ground-truth WOND-ID duplication as an active reviewer-confusion issue.

---

## Completed Ontology Core

- [x] **C1 — `material disease entity` revised.** It is a material entity with one or more pathological disorders as parts, located in a human patient, without a maximal/unity axiom and without mandatory `output of disease development process`.

- [x] **C2 — Disease identity criterion documented.** Identity is grounded in historical-causal continuity of the disorder lineage, not momentary material composition.

- [x] **C3 — `pathological disorder` made primitive and OGMS-anchored.** It remains under OGMS disorder, has no HPO `has quality some phenotypic abnormality` definition, and carries the primitive pathologicity note.

- [x] **C4 — Absence/privation handled without negative entities.** Absence is folded into abnormal organization of present material bearers; no `absent` quality or OWL negation pattern is used.

- [x] **C5 — `disease diagnostic result` points to pathological disorder.** Diagnostic grouping is about disorders rather than circularly about pre-bounded material disease entities.

- [x] **C6 — Unknown-substrate disease represented.** The model can assert a material disease substrate while leaving its disorder characterization operational/classification-relative.

- [x] **C7 — DOID/named disease categories kept out of the material hierarchy.** Named disease/classification categories attach through the epistemic/classification layer, not by subclassing `material disease entity`.

- [x] **C8 — Treatment/removal process duplication cleaned.** The near-duplicate disorder-removal/elimination issue has been resolved in favor of the current process structure.

- [x] **C9 — Labels and typos cleaned.** The known typos and unstable labels flagged in earlier TODOs have been addressed.

---

## Completed Predisposition Pattern

- [x] **P1 — General disease predisposition rebuilt.** The over-conjunctive anonymous intersections were removed. The base class is a tendency inhering in a human organism and grounded in a material basis.

- [x] **P2 — Genetic predisposition added.** `genetic predisposition` is grounded in `pathogenic genetic variant`.

- [x] **P3 — Existing-disorder-grounded predisposition added.** `predisposition from an existing disorder` inheres in a human organism that has part some pathological disorder.

- [x] **P4 — Predisposition disjointness enforced.** Disease predisposition is disjoint with both `material disease entity` and `pathological disorder`.

- [x] **P5 — Disorder-development input loosened.** `disorder development process` no longer requires a pre-existing pathological disorder as input, preserving de novo disease cases.

- [x] **P6 — Tendency hygiene implemented.** `tendency` is distinct from disposition/function/role and has logical content tying it to a material bearer.

- [x] **P7 — Perpetuation tendency aligned.** Disease perpetuation is represented under the tendency pattern rather than as a plain disposition.

---

## Completed Validation And Artefacts

- [x] **V1 — OWL 2 DL profile validation passes.** ROBOT reported: `OWL 2 DL Profile Report: [Ontology and imports closure in profile]`.

- [x] **V2 — HermiT/Colab coherence result recorded.** `VALIDATION.md` records: ontology consistent, 0 unsatisfiable classes.

- [x] **V3 — Inferred ontology added.** `Disease_proposal_2_inferred-3.owl` was added as the inferred artefact from the HermiT/Colab run.

- [x] **V4 — README status updated.** The project status is documented as a reasoner-checked draft.

- [x] **V5 — Ontology metadata added to source.** Title, creator/ORCID, date, version IRI, license, preferred namespace, and abstract are in `Disease proposal 2.ttl`.

---

## Completed Prose And Mentor Package

- [x] **M1 — Modelling note citations added.** The prose cites OGMS/Ceusters-Smith, Hucklenbroich, Jansen/Röhl, Schulz, and Mizoguchi/River Flow where relevant.

- [x] **M2 — Controversial commitments stated.** The note explicitly separates mind-independent disorders, classification-relative disease boundaries, historical-causal disease identity, and epistemic diagnostic thresholds/categories.

- [x] **M3 — Limitations paragraph added.** The note addresses OWL crispness despite biological vagueness, primitive pathologicity, human-only scope where relevant, and the intentional exclusion of clinical defaults from universal axioms.

- [x] **M4 — Contribution claim sharpened.** The contribution is stated as a mid-level modelling pattern rather than another disease classification.

- [x] **M5 — Worked examples and competency questions drafted.** `Worked_Examples_and_Competency_Questions.md` includes simple disease, complication, and genetic predisposition examples with entailments/non-entailments and a diagram.

- [x] **M6 — Folder presentation improved.** README now identifies current source, generated artefacts, validation log, examples, and status.

---

## Historical Notes

- [x] **H1 — TODO 1, TODO 2, TODO 3, and TODO 4 have been consolidated here.** The older files are retained only as historical provenance unless you choose to archive/delete them.

- [x] **H2 — Later TODOs override earlier TODOs.** In particular, TODO 4 overrides TODO 2 on the `min 2` compound-disorder axiom and the realization existential on base disease predisposition.
