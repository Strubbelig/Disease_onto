# Publication Readiness Remediation Plan

Status: release candidate built on 2026-08-06. Technical remediation is complete; author decisions and independent human validation remain open.

## Execution Status

| Phase | Status | Remaining gate |
|---|---|---|
| 0. Baseline | Complete | None |
| 1. Native hierarchy | Complete | None; regression checks pass |
| 2. Eligibility | Complete | All 278 records have final first-review outcomes |
| 3. Evidence and licensing | Technical work complete | Final author license/release approval |
| 4. Citations | Complete | No unreviewed citation assignments remain |
| 5. Vocabularies | Complete | None |
| 6. Neutral comments | Complete | All publication wording decisions are resolved |
| 7. Portable OWL | Complete | Fixed UUID URNs and local catalog selected for the publication supplement |
| 8. Validation | Automated checks complete | Independent reviewer, adjudication, Protege spot check |
| 9. Documentation/package | Release candidate complete | OSF/repository details and final author sign-off |

## Objective

Produce a reproducible, portable, publication-ready ontology-artifact evaluation dataset and OWL release in which:

- `disease_terms_review_enriched.csv` is the sole editable master table;
- all eligibility decisions are explicit in that table;
- source evidence and native superclass hierarchies are not contaminated by reuse in other ontologies;
- citations, provenance, and review annotations are internally consistent;
- every TTL and report is generated from the master table and versioned source modules;
- the release passes automated CSV, RDF, and OWL validation; and
- the protocol, workflow, manuscript, and released data describe the same method.

## Ownership Key

- **Codex**: can complete the step end to end, including implementation and automated verification.
- **User**: requires scholarly judgment, legal/release authority, account access, or a genuinely independent human decision.
- **Shared**: Codex prepares a small decision queue or draft; the user approves or adjudicates it.

Codex must not silently replace a human review judgment. Automated corrections will be recorded in a dated changelog, and ambiguous cases will be presented in the UI rather than scattered across additional CSV files.

## Decisions Needed From The User

These are the only decisions needed before the corresponding release gates. Technical work that does not depend on them can proceed first.

| ID | Decision | Recommended default | Why the user is needed |
|---|---|---|---|
| U1 | Release scope | Publish the complete master CSV as the screening record and generate two TTL views: a full review-evidence ontology and an included-only synthesis ontology. | This determines what readers interpret as the analytical corpus. |
| U2 | Review-artifact identifier policy | Use fixed, non-resolving UUID URNs and distribute the ontology package with a local XML import catalog as a publication supplement. | Approved for an attachment-only artifact that is not intended to be maintained as a web ontology. |
| U3 | Insufficient-evidence policy | Retain candidates in the screening record, but exclude them from synthesis with an explicit `insufficient_metadata` reason when native evidence cannot be recovered. | This is an eligibility rule, not merely a software choice. |
| U4 | Second-review design | Have an independent human recheck eligibility decisions and a documented sample of class coding; adjudicate disagreements. | Codex cannot serve as an independent human reviewer. The protocol currently promises dual screening. |
| U5 | Redistribution and licensing policy | Redistribute only source modules whose terms permit it; otherwise publish provenance and retrieval instructions without copying restricted content. | Final copyright and license interpretation belongs to the authors/institution. |
| U6 | Neutralized review comments | Approve the proposed publication wording in one compact UI queue. | The comments encode the reviewer's interpretation, so substantive wording changes need author approval. |

## Phase 0: Protect And Baseline The Review

**Owner: Codex**

- [ ] Create a timestamped, read-only release baseline of the master CSV, pipeline, core ontology, workflow, and current generated TTL.
- [ ] Record file hashes, software versions, row counts, controlled-value counts, and current validation results.
- [ ] Add a machine-readable schema for the master CSV and a human-readable data dictionary.
- [ ] Add a publication changelog. Do not use old annotation or citation tables as inputs.
- [ ] Add a deterministic audit command that never modifies the master CSV.

**Acceptance gate:** A rerun can prove exactly which files and values existed before remediation.

## Phase 1: Repair Native Hierarchy Extraction

**Owner: Codex; Shared only for unresolved source identity**

- [ ] Replace the current import-all-modules behavior with an explicit class-to-native-module manifest generated from the master CSV.
- [ ] Distinguish native definitions from imported, reused, indexed, and mapping-only appearances.
- [ ] Import only native hierarchy evidence for each reviewed class. Keep non-native appearances as provenance annotations, never as superclass evidence.
- [ ] Generate fallback modules only when no native module is available, and mark their evidence status explicitly.
- [ ] Add regression tests for DOID disease, OGMS disease, MONDO disease, and other repeatedly reused IRIs.
- [ ] Add a contamination test that fails when a reviewed class acquires a parent asserted only by a non-native occurrence module.
- [ ] Present only unresolved native-source conflicts to the user for adjudication.

**Acceptance gate:** Canonical classes show only their source ontology's asserted hierarchy, and the contamination regression suite passes.

## Phase 2: Make Eligibility Explicit In The Master CSV

**Owner: Codex for reconciliation; Shared for genuine conflicts**

- [ ] Add controlled fields for effective export status, effective exclusion reason, rule provenance, and evidence-resolution status.
- [ ] Materialize the pipeline's final decision for all 278 rows. No row may disappear silently.
- [ ] Reconcile the 14 rows marked `include` but currently suppressed by automated rules.
- [ ] Resolve the 52 blank manual statuses using existing rules where deterministic; queue only ambiguous cases.
- [ ] Preserve the original manual decision and record any rule-based effective decision separately.
- [ ] Define whether manually excluded rows appear in the full evidence TTL, included-only TTL, or both according to U1.
- [ ] Make the UI display manual status, effective status, rule, and conflict together.

**User task:** Adjudicate the compact conflict queue. The user should not need to rereview all 278 rows.

**Acceptance gate:** Every row has an explicit, explainable outcome in the sole master table, and export counts can be reproduced directly from it.

## Phase 3: Complete Evidence, Provenance, And Licensing

**Owner: Codex for retrieval and normalization; Shared for unavailable evidence; User for license approval**

- [ ] Requery BioPortal, OLS, OBO Foundry, source repositories, and stable project pages for the evidence-poor included classes.
- [ ] Attempt to recover native labels, definitions, comments, synonyms, asserted parents, ontology versions, retrieval timestamps, and source URLs.
- [ ] Complete provenance for manual seed rows and normalize the literal string `None` to a controlled blank or explicit value.
- [ ] Populate discovery tier consistently, including explicit `manual_seed` provenance.
- [ ] Record ontology homepage, repository, license identifier, license URL, and redistribution status where available.
- [ ] Mark evidence that could not be recovered instead of generating apparently complete but empty stubs.
- [ ] Route unresolved cases through the U3 policy.

**User task:** Supply inaccessible or private source material if it should remain included, and approve the final redistribution policy under U5.

**Acceptance gate:** Every included class has assessable native evidence or a documented exception consistent with the eligibility policy.

## Phase 4: Normalize And Verify Citations

**Owner: Codex for bibliographic work; Shared for ontology-to-paper assignment**

- [ ] Correct impossible states such as citation approved plus `no_citation`.
- [ ] Review the four unreviewed ontology groups and complete the ten approved but incomplete references.
- [ ] Normalize the malformed OGMS citation and any full references placed in title or confidence fields.
- [ ] Use structured fields for authors, year, title, venue, DOI, PMID, PMCID, URL, approval, assignment status, and notes.
- [ ] Replace free-text confidence values with a documented controlled vocabulary.
- [ ] Enforce the rule that disapproved or `no_citation` records contain no citation payload.
- [ ] Verify DOI and identifier resolution and compare titles/authors against authoritative bibliographic sources.
- [ ] Present ambiguous ontology-to-paper assignments in the existing citation-review UI.

**User task:** Approve or reject only ambiguous citation assignments; factual metadata normalization can be performed automatically.

**Acceptance gate:** Every active ontology group is approved, explicitly has no citation, or is transparently marked unresolved; approved records are bibliographically complete.

## Phase 5: Reconcile Evidence Quality And Controlled Vocabularies

**Owner: Codex for mechanical consistency; Shared for semantic exceptions**

- [ ] Correct cases where definition/comment presence contradicts `absent`, `partial`, `poor`, or `good` quality coding.
- [ ] Preserve intentional exceptions only with an explicit reason.
- [ ] Align every controlled value across the CSV schema, UI, pipeline, `review_core.ttl`, workflow, and manuscript.
- [ ] Formally declare `no_grounded_model_subtype`, all disease-model categories in use, and every exported annotation property.
- [ ] Add the replacement-candidate exclusion reason to the controlled vocabulary or migrate it to the selected canonical value.
- [ ] Narrow over-broad prefill rules for BioTop, Menelas/EPO, and `nosological_category` so they do not overwrite defensible manual coding.
- [ ] Add consistency tests for every prefill rule discussed during review.

**User task:** Decide only semantic exceptions where the source evidence supports more than one reasonable interpretation.

**Acceptance gate:** No undocumented value or evidence-quality contradiction remains.

## Phase 6: Prepare Publication-Neutral Review Text

**Owner: Codex drafts; User approves under U6**

- [ ] Identify subjective, conversational, first-person, truncated, and concatenated review comments.
- [ ] Draft neutral replacements that preserve the original substantive judgment and evidence.
- [ ] Move crisp/graded arguments and other structured assessments out of prose comments into their proper fields.
- [ ] Present original and proposed wording side by side in the UI with accept/edit controls.
- [ ] Record approval and date in the master CSV; do not create a second annotation table.

**User task:** Approve, edit, or reject the queued wording changes.

**Acceptance gate:** Public comments are precise, descriptive, evidence-based, and free of editing artifacts.

## Phase 7: Build A Portable OWL Release

**Owner: Codex after U1 and U2**

- [x] Replace the reserved `example.org` review namespace with fixed publication-scoped UUID URNs.
- [ ] Replace absolute local `file:` imports with persistent ontology IRIs and a packaged XML catalog for local resolution.
- [ ] Declare all annotation properties and controlled concepts in `review_core.ttl`.
- [ ] Export database, retrieval-date, version, ontology-ID, and source-URL provenance required by the workflow.
- [ ] Replace ambiguous semicolon splitting with lossless structured multi-value serialization.
- [ ] Generate the release view or views selected in U1 from the master CSV only.
- [ ] Include ontology metadata: title, description, creators, version IRI, version information, license, issued date, source commit/hash, and generation software version.
- [ ] Package source modules only according to U5.

**User decision:** The review ontology is an attachment-only publication supplement and does not require a web namespace or repository.

**Acceptance gate:** The release opens on a different machine without local paths and preserves literal values exactly.

## Phase 8: Automated And Human Validation

**Owner: Codex for automated validation; User/second reviewer for human validation**

Codex will run:

- [ ] CSV parsing, uniqueness, datatype, controlled-value, and required-field checks.
- [ ] Eligibility/status reconciliation and citation-state checks.
- [ ] Native hierarchy and cross-module contamination tests.
- [ ] CSV-to-TTL annotation equality tests.
- [ ] Turtle parsing, ROBOT OWL 2 DL profile validation, and undeclared-property checks.
- [ ] Import closure and catalog resolution from a clean temporary directory.
- [ ] Reproducible-build test: identical inputs produce semantically identical output.
- [ ] Release checks for local paths, reserved namespaces, malformed IRIs, and missing ontology metadata.

The user or an independent reviewer must perform:

- [ ] Eligibility second screening required by the protocol.
- [ ] A documented double-coded sample of class assessments, or a transparent methods amendment if class charting remains single-reviewer.
- [ ] Adjudication and agreement reporting.
- [ ] A visual spot check in Protege of canonical, fallback, and conceptually ambiguous examples.

**Acceptance gate:** All automated tests pass, human disagreements are adjudicated, and the manuscript accurately reports who reviewed what.

## Phase 9: Align Documentation And Publish

**Owner: Codex drafts and packages; User signs off and releases**

- [ ] Update the workflow so the master CSV is the sole editable source of truth and TTLs are generated artifacts.
- [ ] Remove references to deleted tables and nonexistent fields.
- [ ] Align protocol value sets, actual UI options, pipeline behavior, and `review_core.ttl` definitions.
- [ ] Update manuscript methods, artifact-flow counts, limitations, data-availability statement, and citation methods from final generated statistics.
- [ ] Produce a README, data dictionary, changelog, machine-readable environment, build command, validation report, and release manifest.
- [ ] Create a clean release archive and verify it independently from the working directory.

**User task:** Approve the scholarly interpretation, authorship text, license, protocol deviations, OSF record, and final publication supplement.

**Acceptance gate:** The archived package, manuscript, protocol, and live repository all describe the same frozen version.

## What Codex Can Complete Without Further Manual Work

Codex can independently implement the hierarchy fix, master-table schema, UI changes, reconciliation logic, API retrieval, bibliographic normalization, controlled-vocabulary synchronization, OWL declarations, portable build system, QA suite, documentation drafts, and release packaging. Codex can also reduce all ambiguous issues to short review queues and provide a recommendation with evidence for each one.

## What Codex Cannot Properly Do On The User's Behalf

Codex cannot be the independent second human reviewer, make undisclosed subjective inclusion decisions, accept copyright or license liability, register or publish under the user's identity without account authorization, or give final authorial approval to interpretive wording.

## Recommended Execution Checkpoints

1. **Technical checkpoint:** Codex completes Phases 0-2 and reports the native-hierarchy fix plus the short eligibility conflict queue.
2. **Evidence checkpoint:** Codex completes Phases 3-6; the user adjudicates unresolved evidence, citations, semantic exceptions, and neutral wording in the UI.
3. **Release checkpoint:** After U1, U2, and U5, Codex completes Phases 7-9 and produces a release candidate.
4. **Human validation checkpoint:** The user arranges independent screening/coding, resolves disagreements, and authorizes publication.

## Definition Of Publication Ready

The review is publication ready only when all phase acceptance gates pass, all user decisions U1-U6 are recorded, no blocking validation result remains, and a frozen release can be rebuilt and understood without access to the author's local computer.
