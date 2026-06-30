# TODO 4 — DL validation and final cleanup

**Why this exists:** the updated merged OWL now reflects the main modelling stance. A previous ROBOT profile check found an OWL 2 DL blocker in the compound-disorder axiom; that specific blocker has now been fixed. This file keeps the remaining validation, generated-file, metadata, and review-package tasks together.

---

## A. DL profile and reasoning status

- [x] **A1 — Repair `compound pathological disorder` (WOND_120049).** Current axiom:
  ```
  'pathological disorder'
   and ('has part' min 2 'pathological disorder')
  ```
  This was changed from `has part min 2 pathological disorder` to `has part some pathological disorder`, removing the OWL 2 DL violation caused by a cardinality restriction over BFO `has part`.

- [x] **A2 — Re-run OWL 2 DL profile validation after A1.**
  ```
  java -jar /usr/local/bin/robot.jar validate-profile \
    --input "Disease proposal 2 merged.owl" \
    --profile DL
  ```
  Result on 2026-06-29: `OWL 2 DL Profile Report: [Ontology and imports closure in profile]`.

- [ ] **A3 — Then run reasoning and record the result.** After DL validation passes, run ELK and a full DL reasoner/HermiT on the merged file. Record the command, date, and result in `README.md` or `VALIDATION.md`. Do this only when ready; reasoning can be slow on the full import closure.

---

## B. Synchronize generated artefacts

- [ ] **B1 — Regenerate or remove stale `Disease proposal 2 merged.ttl`.** `Disease proposal 2 merged.owl` was updated on 2026-06-29, but `Disease proposal 2 merged.ttl` is still timestamped 2026-06-28 and should not be treated as current.

- [x] **B2 — Update `build_disease_proposal.sh` if both merged formats are wanted.** The script currently documents and writes the OWL merge only. Either add a second conversion step for the merged TTL or make the README say explicitly that only the OWL merge is generated.

---

## C. Finish ontology polish

- [x] **C1 — Decide whether `genetic variant` should be renamed to `pathogenic genetic variant`.** The structural error is fixed because the class is now a material entity, not an OGMS disorder, but the label remains broader than the intended risk-basis class.

- [x] **C2 — Add the intended `disease predisposition` annotation.** Use the wording from TODO 3:
  > A tendency inhering in a person, grounded in a material basis, whose realization may produce a target pathological disorder.

- [x] **C3 — Decide what to do with `silent disorder` (WOND_120004).** TODO 1 argued that silent/subclinical status may belong in the epistemic or observation layer rather than as a material subclass. Either retire the class or explicitly justify keeping it as a convenient pathological-disorder subclass.

- [x] **C4 — Dedupe `disorder removal process` and `disorder elimination process`.** Keep both only if their difference is documented; otherwise merge or retire one.

- [x] **C5 — Review the imported wound `ground_truth.owl` WOND IDs.** The merged OWL contains both project IRIs and imported `http://purl.obolibrary.org/obo/wond/ground_truth.owl/WOND_...` classes. Confirm this namespace duplication is intentional and will not confuse reviewers.

- [x] **C6 — Recheck `has realization some disorder development process` on `disease predisposition`.** The worked genetic-predisposition example exposes a possible overcommitment: if every disease predisposition necessarily has a realization process, OWL can entail an anonymous development process and, through that process, an output pathological disorder. That is too strong for unrealized risk. Consider moving this existential to a `realized disease predisposition` subclass or replacing it with a weaker modelling note/annotation.

---

## D. Mentor package

- [x] **D1 — Add a compact status note.** State that the ontology is a concept draft until DL validation and reasoning pass.

- [x] **D2 — Add 2-3 worked examples and competency questions.** These are still the main thing that would make the proposal easier for Martin Boeker to evaluate quickly.

- [ ] **D3 — Add ontology metadata.** Include creator/contributor, date/version IRI, license, preferred namespace, and a short ontology abstract.
