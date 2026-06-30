# TODO 3 — Publication and mentor-readiness pass

**Why this exists:** `Disease proposal 2.ttl` now contains much of the intended modelling stance, but the folder is not yet in a clean state for review by Martin Boeker or for publication work. This checklist focuses on the final artefact: synchronized source/merged files, reproducible validation, cleaned prose, and a short argument package that makes the proposal easy to evaluate.

**Target state:** a reviewer can open the folder, read the modelling note, inspect the current ontology, run the build/reasoning workflow, and understand the contribution without first reconstructing which files are stale.

---

## A. Synchronize the ontology artefacts

- [ ] **A1 — Rebuild the merged ontology from the current source.** `Disease proposal 2.ttl` is newer than `Disease proposal 2 merged.ttl` / `.owl`, and the merged files still contain older axioms and labels. Rebuild before sharing either merged file.

- [x] **A2 — Confirm the merged file reflects the current core axioms.** After rebuilding, spot-check that:
  - `material disease entity` has `has part some pathological disorder` and no obsolete mandatory `output of disease development process`;
  - `pathological disorder` has no `has quality some phenotypic abnormality` and no `material basis of some disease predisposition`;
  - `disease diagnostic result` is about `some pathological disorder`, not only `material disease entity`;
  - `compound pathological disorder` uses `has part min 2 pathological disorder`.

- [x] **A3 — Fix the import catalog so ROBOT can load local modules.** Current validation fails because the catalog resolves paths with escaped spaces such as `Disease%20ontology%20modules/...` as literal filesystem paths. Regenerate or edit `catalog-v001.xml` so ROBOT can resolve every imported module locally.

- [x] **A4 — Run the reasoners on the rebuilt merge.** Run ELK first, then HermiT/full DL. Record the exact command, date, and result in `README.md` or a short `VALIDATION.md`. Recorded in `VALIDATION.md`: HermiT/Colab reported the merged ontology consistent with 0 unsatisfiable classes.

- [x] **A5 — Record expected satisfiability checks.** Confirm that `material disease entity`, `pathological disorder`, `disease predisposition`, `material complication disease entity`, and `disease course process putting out disorders as part of a complication` remain satisfiable.

---

## B. Resolve remaining ontology issues

- [x] **B1 — Fix the genetic-variant modelling.** `genetic variant` should not simply be `subClassOf OGMS disorder`. Create or rename to `pathogenic genetic variant` as a material entity, e.g. a portion of DNA / allele. Only classify pathogenic variants as `pathological disorder` where the pathologicity criterion independently licenses that judgement.

- [x] **B2 — Reword `disease predisposition` annotations.** The class now models a tendency, but the description still says "disease disposition". Replace with:
  > A tendency inhering in a person, grounded in a material basis, whose realization may produce a target pathological disorder.

- [x] **B3 — Decide whether every disorder development realizes a predisposition.** `disorder development process` currently has `realizes some disease predisposition`. Keep this only if "predisposition" is intended in the broad metaphysical sense that every realized disorder-development process had some preceding tendency. Otherwise move this axiom to a narrower risk-development subclass.

- [x] **B4 — Check `has part` reflexivity in the active imports.** BFO documents that everything has itself as a part. If this is represented strongly enough for reasoning, `material disease entity ⊑ has part some pathological disorder` risks classifying every pathological disorder as a disease. If that is unwanted, use a proper-part relation or explicitly document that single-disorder diseases are acceptable.

- [x] **B5 — Clean duplicate or near-duplicate process classes.** Decide whether `disorder removal process` and `disorder elimination process` are distinct. If not, keep one class and retire/merge the other.

- [x] **B6 — Fix small labels and typos.** At minimum: `Delibarately` -> `Deliberately`, `ouput` -> `output`, and `Unknown-disorder disease` -> a stable singular label such as `unknown-substrate disease` or `unknown-disorder disease`.

- [x] **B7 — Review relation IRIs for inherence.** The source uses `BFO_0000197` for `inheres in`, while the earlier TODO also mentions RO inherence relations. Confirm the chosen relation is intentional and consistent across tendency, plan, phenotype, and risk modelling.

---

## C. Clean the prose package

- [x] **C1 — Keep one modelling-considerations document.** `Modelling_Considerations.docx` appears aligned with the current thesis; `Modelling Considerations.docx` contains older stage-based/persistence wording. Archive or rename the older version so reviewers do not read the wrong argument.

- [x] **C2 — Add citations to the modelling note.** The prose should cite the key moves: OGMS/Ceusters-Smith for disorder/disease background, Hucklenbroich for pathologicity, Jansen/Rohl for tendency/realizables, Schulz for ontology vs clinical defaults, and Mizoguchi/River Flow for persistence-through-change.

- [x] **C3 — State the controversial commitments explicitly.** Add a short paragraph saying:
  - disorders are the primary mind-independent material entities;
  - disease boundaries are classification-relative;
  - disease instances are material continuants whose identity depends on historical-causal continuity of the disorder lineage;
  - diagnostic categories and thresholds belong to the epistemic layer.

- [x] **C4 — Add a limitations paragraph.** Mention OWL crispness despite biological vagueness, the primitive status of pathologicity, the human-only scope if `Homo sapiens` remains hard-coded, and the fact that clinical defaults are intentionally not encoded as universal axioms.

- [x] **C5 — Make the contribution claim modest and sharp.** Proposed wording:
  > The contribution is not another disease classification, but a mid-level modelling pattern that separates material pathological disorder, disease individuation, disease course, predisposition, and diagnostic classification.

---

## D. Prepare examples and competency questions

- [x] **D1 — Add 2-3 worked examples.** Good candidates:
  - a simple single-disorder disease;
  - a complication case where disease A produces a disorder grouped under disease B;
  - a genetic predisposition case where the variant grounds risk but is not itself the target disease.

- [x] **D2 — Write competency questions.** Include questions such as:
  - Can a patient have a pathological disorder without a diagnosis?
  - Can two diagnostic results group overlapping but non-identical disorder sets?
  - Can a predisposition exist without the target disorder already existing?
  - Can a disease persist while its material constituents change?

- [x] **D3 — State expected entailments and non-entailments.** For each example, list what the reasoner should infer and what it should not infer. This is especially important for predisposition and complication cases.

- [x] **D4 — Add a small diagram.** A one-page diagram should show:
  ```
  organism -> has part -> pathological disorder
  pathological disorder(s) -> grouped by diagnostic result -> material disease entity
  disease predisposition -> realized in -> disorder development process -> has output -> pathological disorder
  ```

---

## E. Make the folder presentable

- [x] **E1 — Update `README.md`.** Add `TODO_3_publication_and_mentor_readiness.md`, mention which files are current, and state which files are generated artefacts.

- [x] **E2 — Add a short status note.** Include whether the ontology is currently "concept draft", "reasoner-checked draft", or "submission draft". Do not let stale merged files imply a stronger status than the source supports.

- [x] **E3 — Decide what to do with unchecked TODOs.** Either mark completed items in `TODO_ontology_revisions.md` / `TODO_2_predisposition_and_strictening.md`, or add a note that those TODOs are historical and superseded where `Disease proposal 2.ttl` already implements them.

- [ ] **E4 — Add ontology metadata.** Include version IRI/date, creator/contributor, license, preferred namespace, and a short abstract annotation on the ontology itself.

- [x] **E5 — Keep generated and source files clearly separated.** Make it obvious that `Disease proposal 2.ttl` is the editable source and `Disease proposal 2 merged.*` are generated from the build.

---

### Mentor-ready minimum

Before sending to Martin, do at least:

1. Rebuild merged `.ttl` / `.owl` from the current source.
2. Fix ROBOT import resolution and record one successful validation/reasoning run.
3. Fix the genetic-variant class.
4. Reword the predisposition annotation.
5. Remove or clearly archive the outdated modelling-considerations document.
6. Add a one-page summary with the core thesis, contribution, and 2-3 questions you want Martin to judge.

### Publication-ready minimum

For publication, also add:

1. Cited prose with a clear related-work contrast.
2. Worked examples and competency questions.
3. Expected entailments/non-entailments.
4. Validation results and reproducible build instructions.
5. A limitations section that explicitly addresses vagueness, pathologicity, human scope, and separation from clinical defaults.
