# TODO 2 — Predisposition refactor + axiom tightening

**Why this exists:** the predisposition block in TODO 1 (T11a–T11e) was written as three *cases* but did not say to put them on **separate subclasses** — so they ended up as three conjunctive necessary conditions on one class (`disease predisposition`, WOND_120023), which over-constrains every predisposition to be genetic **and** comorbid **and** plainly human-borne at once. Two of those patterns were also wrong in TODO 1: `bearer of` should have been `has part`, and a redundant `has output` filler crept in. This file corrects all of that and supersedes T11a–T11e.

**Relation labels ↔ IRIs**
`part of`=BFO_0000050 · `has part`=BFO_0000051 · `realized in / has realization`=BFO_0000054 · `realizes`=BFO_0000055 · `inheres in`=BFO_0000197 · `bearer of`=BFO_0000196 *(avoid for disorders)* · `has material basis`=BFO_0000218 · `material basis of`=BFO_0000127 · `has input`=RO_0002233 · `has output`=RO_0002234 · `output of`=RO_0002353 · `occupies temporal region`=BFO_0000199
**Class labels ↔ IRIs**
`tendency`=WOND_120005 · `disease predisposition`=WOND_120023 · `material disease entity`=WOND_120020 · `pathological disorder`=WOND_120022 · `disorder development process`=WOND_120021 · `threshold crossing event`=WOND_120031 · `compound pathological disorder`=WOND_120049 · `Homo sapiens`=NCBITaxon_9606 · `material entity`=BFO_0000040 · `temporal instant`=BFO_0000203 · `genetic disease`=DOID_630 *(epistemic — do NOT use as a material basis)*

---

## A. Rebuild the predisposition cluster (replaces 120023's three intersections)

- [x] **A1 — Delete all three anonymous-intersection `subClassOf` axioms on `disease predisposition` (120023)** and replace with one clean set of necessary conditions:
  ```
  'disease predisposition'  ⊑
      'tendency'
      and ('inheres in' some 'Homo sapiens')
      and ('has material basis' some 'material entity')
      and ('has realization' some 'disorder development process')
  ```
  Keep the existing `disjointWith material disease entity` / `disjointWith pathological disorder`.

- [ ] **A2 — Add subclass `genetic predisposition`** (the variant case; was T11d). Ground it in a **material** variant, *not* `DOID_630` (which is an epistemic disease category, not a material basis):
  ```
  'genetic predisposition'  ⊑
      'disease predisposition'
      and ('has material basis' some 'pathogenic genetic variant')
  ```
  > `pathogenic genetic variant` must be a **material entity** (⊑ BFO_0000040 — a portion of DNA / allele; e.g. a GENO/SO-aligned class or your own). If you don't have one yet, create it ⊑ material entity. Do not substitute DOID_630.

- [x] **A3 — Add subclass `predisposition from an existing disorder`** (the A→B case; was T11e — corrected to `has part`, not `bearer of`):
  ```
  'predisposition from an existing disorder'  ⊑
      'disease predisposition'
      and ('inheres in' some ('Homo sapiens' and ('has part' some 'pathological disorder')))
  ```

- [x] **A4 — On `pathological disorder` (120022): delete** the restriction `('material basis of' some 'disease predisposition')` (BFO_0000127 → 120023). It falsely asserts *every* disorder grounds a predisposition. The basis is declared from the predisposition side (A1/A2), so nothing is lost.

- [x] **A5 — On `pathological disorder` (120022): move the definition off `rdfs:isDefinedBy`.** `rdfs:isDefinedBy` expects an ontology IRI, not prose. Put the text *"a disorder is an abnormal presence or organisation of material components — including the limiting case where the abnormal organisation consists in a normally-present component being absent"* into `IAO_0000115` (definition) or `skos:definition`.

- [x] **A6 — On `disorder development process` (120021): reconsider `('has input' some 'pathological disorder')` (RO_0002233 → 120022).** This forces a *pre-existing* disorder as input, which is false for de novo disease (the first disorder has no disorder input). Choose one:
  - delete `has input`; **or**
  - retype the input to the risk-conferring **material entity** (`'has input' some 'material entity'`); **or**
  - keep the disorder-input only on the complication subclass `120053`, where a prior disorder genuinely exists.

- [ ] **A7 — On 120023: simplify the realization and fix the description.** `has realization some ('disorder development process' and ('has output' some 'pathological disorder'))` is redundant — 120021 already entails the output, and the extra existential does **not** bind the *target* disorder. Use just `has realization some 'disorder development process'` (A1) and document the target in an annotation. Reword the description (it still says "disease disposition … potential bearer of a disorder" → "a tendency inhering in a person in whom a disorder of the target type may develop").

---

## B. Stricter axioms (safe tightenings)

- [x] **B1 — `material disease entity` (120020):** add `('part of' some 'Homo sapiens')`. A disease is always located in a patient.
- [x] **B2 — `pathological disorder` (120022):** add `('part of' some 'Homo sapiens')`. Disorders are in a body.
- [x] **B3 — `tendency` (120005):** add `('inheres in' some 'material entity')` so the textual definition is partly enforced (the class currently has no logical content).
- [x] **B4 — `threshold crossing event` (120031):** the axiom `occupies temporal region only 'temporal instant'` is `allValuesFrom` (vacuously true if it occupies nothing). Add the matching existential: `('occupies temporal region' some 'temporal instant')`.
- [x] **B5 — `compound pathological disorder` (120049):** if "compound" means *more than one*, change `('has part' some 'pathological disorder')` → `('has part' min 2 'pathological disorder')`.

---

## C. Minor nits

- [ ] **C1 — Reflexivity check.** If your BFO import declares `has part` (BFO_0000051) reflexive, then `material disease entity ⊑ has part some pathological disorder` (and the compound def) make **every** pathological disorder also a material disease entity (it has itself as part). If you don't want single disorders auto-classified as diseases, confirm `has part` is non-reflexive in the merge, or use `has proper continuant part`.
- [x] **C2 — `perpetuation disposition` (120034):** perpetuation is graded/counteractable — consider re-parenting it under `tendency` (120005) instead of `disposition` for consistency with the risk modelling.
- [ ] **C3 — Dedupe:** `disorder removal process` (120006) vs `disorder elimination process` (120087) look like the same concept; keep one.
- [ ] **C4 — `Unknown-substrate diseases` (120007):** rename to singular `unknown-disorder disease`.

---

### Net effect on the predisposition cluster
After A1–A3 you have one general `disease predisposition` (tendency, inheres in a person, grounded in *some* material basis, realised in a disorder-development process) and two honest specialisations (genetic-variant-grounded; existing-disorder-grounded), instead of one class that silently demanded all three at once. A4–A7 remove the false entailments; B1–B3 add the constraints that the realist stance actually licenses.
