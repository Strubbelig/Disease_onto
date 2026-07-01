# Validation log

## 2026-06-29/30 — OWL 2 DL profile and HermiT coherence check

Input artefact:

- `Disease proposal 2 merged.owl`

Profile validation:

- ROBOT `validate-profile --profile DL` completed successfully.
- Result: `OWL 2 DL Profile Report: [Ontology and imports closure in profile]`.

HermiT / Colab coherence check:

- Parsed `Disease proposal 2 merged.owl` as RDF/XML with rdflib.
- Triples loaded: 217,397.
- Imports stripped: 0, because the reasoning run used the merged content offline.
- Loaded into the reasoner environment: 6,137 classes, 323 object properties, 299 individuals.
- HermiT runtime reported by the notebook: 0.9 seconds.
- Result: ontology consistent.
- Unsatisfiable classes: 0.

Inferred artefact:

- `Disease_proposal_2_inferred-3.owl`

Interpretation:

- The merged OWL is in OWL 2 DL profile.
- The ontology is coherent under the recorded HermiT run.
- The stale generated `Disease proposal 2 merged.ttl` remains a separate generated-file cleanup item.
