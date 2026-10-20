# Disease ontology

A realist, BFO/OGMS-based proposal for modelling disease as a **material entity** (the aggregate of an organism's pathological disorders), with a strict separation between biological reality and the epistemic layer of diagnosis and classification.

## Contents

### Ontology
- `mild.ttl` — MILD, the current working ontology (until 2026-10-16 `Disease proposal 2.ttl`) (own classes/axioms; imports the modules below).
- `mild_merged.owl` — generated merged OWL with all imports resolved; rebuild with `build_disease_proposal.sh`.
- `Disease_proposal_2_inferred-3.owl` — inferred OWL produced from the HermiT/Colab coherence run.
- `Disease proposal.ttl` — earlier version.
- `Disease ontology modules/` — imported module extracts (BFO, OGMS, OBI, PATO, HPO, CHEBI, DOID, uPheno, …).
- `catalog-v001.xml` — Protégé import catalogue.
- `build_disease_proposal.sh` — build/merge script.

### Accompanying research
- `Disease_Modelling_Synthesis.md` — synthesis of the philosophy-of-medicine and formal-ontology literature on defining disease, with critiques.
- `Paper_Draft_MILD_MIRO.md` — first manuscript draft structured around the MIRO reporting topics.
- `VALIDATION.md` — recorded OWL 2 DL profile and HermiT coherence results.
- `Worked_Examples_and_Competency_Questions.md` — first-draft examples, competency questions, expected entailments/non-entailments, and a small diagram.
- `TODO_FINAL_disease_ontology.md` — consolidated final TODO/checklist.
- `Scoping_Review_Protocol_Disease_Modelling.md` — PRISMA-ScR protocol for a review of disease modelling in ontologies.
- `Modelling_Considerations.docx` — the modelling-considerations section for the paper.
- `Disease_Ontology_Literature_DOIs.xlsx` (+ `_Additions`) — verified DOI bibliography.

## Note
Full-text PDFs of cited papers are intentionally excluded (copyright); see `.gitignore`.

## Status

Current status: **reasoner-checked draft**. `mild_merged.owl` passes OWL 2 DL profile validation and was reported coherent by a HermiT/Colab run with 0 unsatisfiable classes; see `VALIDATION.md`. Since `Disease proposal 2.ttl` has been edited after the last generated artefacts, rebuild the merged/inferred files before sharing.
