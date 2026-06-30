# Disease ontology

A realist, BFO/OGMS-based proposal for modelling disease as a **material entity** (the aggregate of an organism's pathological disorders), with a strict separation between biological reality and the epistemic layer of diagnosis and classification.

## Contents

### Ontology
- `Disease proposal 2.ttl` — current working ontology (own classes/axioms; imports the modules below).
- `Disease proposal 2 merged.owl` — generated merged OWL with all imports resolved; rebuild with `build_disease_proposal.sh`.
- `Disease proposal 2 merged.ttl` — older merged TTL artefact; currently stale until regenerated.
- `Disease proposal.ttl` — earlier version.
- `Disease ontology modules/` — imported module extracts (BFO, OGMS, OBI, PATO, HPO, CHEBI, DOID, uPheno, …).
- `catalog-v001.xml` — Protégé import catalogue.
- `build_disease_proposal.sh` — build/merge script.

### Accompanying research
- `Disease_Modelling_Synthesis.md` — synthesis of the philosophy-of-medicine and formal-ontology literature on defining disease, with critiques.
- `Worked_Examples_and_Competency_Questions.md` — first-draft examples, competency questions, expected entailments/non-entailments, and a small diagram.
- `TODO_ontology_revisions.md` — actionable Protégé revision checklist (Manchester axioms) aligning the ontology with the modelling stance.
- `TODO_2_predisposition_and_strictening.md` — follow-up checklist for the predisposition refactor and stricter core axioms.
- `TODO_3_publication_and_mentor_readiness.md` — final readiness checklist before mentor review or publication work.
- `TODO_4_DL_validation_and_final_cleanup.md` — current blocker list after the updated merge, especially reasoning/validation follow-up and stale generated artefacts.
- `Scoping_Review_Protocol_Disease_Modelling.md` — PRISMA-ScR protocol for a review of disease modelling in ontologies.
- `Modelling_Considerations.docx` — the modelling-considerations section for the paper.
- `Disease_Ontology_Literature_DOIs.xlsx` (+ `_Additions`) — verified DOI bibliography.

## Note
Full-text PDFs of cited papers are intentionally excluded (copyright); see `.gitignore`.

## Status

Current status: **concept draft**, not yet a reasoner-checked draft. `Disease proposal 2 merged.owl` reflects the updated source and now passes OWL 2 DL profile validation. Full reasoner/coherence checks are still pending; see `TODO_4_DL_validation_and_final_cleanup.md`.
