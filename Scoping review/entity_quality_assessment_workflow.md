# Entity Quality Assessment Workflow

This workflow keeps human review reusable across regenerated extraction files. Treat `disease_terms_review_enriched.csv` as machine output and `disease_terms_manual_annotations.csv` as the durable human annotation layer.

The formal definitions and controlled-value sets for every annotation property are declared in `review_core.ttl` (namespace `https://example.org/disease-review/ap/`). This document provides the procedural guidance; the ontology is the authoritative source for property semantics.

## Files

- `disease_terms_review_enriched.csv`: generated search and enrichment output.
- `disease_terms_manual_annotations.csv`: stable manual annotations keyed by `class_iri`.
- `disease_terms_review_annotated.csv`: merged working file produced from generated extraction plus manual annotations.
- `review_core.ttl`: core annotation-property ontology defining all manual-annotation fields.

Do not use row number as an identifier. Use `class_iri` as the primary key. Keep `term`, `preferred_label`, and `source_ontology_ids` in the manual file only as human-readable context.

## Controlled Values

Use these values where possible. Full definitions are in `review_core.ttl`.

### `manual_include_status`

- `include` — class is suitable for substantive analysis without reservation.
- `exclude` — class is not used in substantive synthesis; set `manual_exclusion_reason`.
- `maybe` — relevance or quality is uncertain; needs further evidence before a firm decision.
- `needs_second_review` — borderline or low-confidence case; flagged for an independent second pass.

### `manual_exclusion_reason`

- `demo_or_training_resource` — the ontology is a demo, tutorial, student thesis, or training exercise.
- `value_set_or_collection` — the resource is a value-set collection or coding catalogue, not a formal ontology.
- `not_disease_modelling_relevant` — the class is not conceptually relevant to disease modelling (e.g. a document field, administrative category, or generic label).
- `terminology_not_ontology` — the resource is a clinical terminology or code system without formal ontological structure adequate for the review purpose.
- `duplicate_imported_term` — the class IRI belongs to another ontology; this occurrence is an import, not an independent implementation.
- `obsolete_or_noncurrent` — the ontology or class is marked deprecated, inactive, retired, or otherwise non-current.
- `insufficient_metadata` — too little metadata (definition, parents, provenance) to assess relevance or quality.
- `out_of_scope_other` — excluded for a reason not covered above; elaboration required in `manual_exclusion_detail`.

### `ontology_type_manual`

- `curated_ontology` — formally maintained, logically structured ontology intended for community reuse.
- `clinical_terminology` — terminological resource primarily for clinical coding (e.g. SNOMED CT, LOINC, MeSH); may lack formal ontological structure.
- `value_set` — collection of terms assembled for a specific coding context; not a standalone ontology.
- `application_ontology` — ontology built for a single application domain or system; limited general reusability.
- `demo_or_training_resource` — resource created for teaching, demonstration, or student exercise.
- `generated_or_local_resource` — automatically generated or internal ontology not intended for community reuse.
- `unclear` — insufficient metadata to classify the resource type.

### `native_or_imported_manual`

- `native` — the class IRI namespace matches the ontology; the class is defined here.
- `imported` — the class IRI namespace belongs to a different ontology; the class is imported or copied.
- `reused_unclear` — the IRI suggests reuse from elsewhere but the relationship is ambiguous.
- `unknown` — insufficient information to determine provenance.

### `disease_model_category`

- `disease_as_disposition` — disease modelled as a realizable entity, tendency, or disposition of a bearer (e.g. BFO disposition or risk).
- `disease_as_disorder` — disease modelled as a structural or functional disorder of a bodily entity (e.g. OGMS disorder).
- `disease_as_process` — disease modelled as a pathological process or course of events unfolding over time (e.g. BFO process).
- `disease_as_finding` — disease modelled as a clinical observation or finding recorded about a patient (e.g. SNOMED clinical finding).
- `disease_as_condition` — disease modelled as a patient condition without further upper-ontological commitment.
- `disease_as_pathology` — disease modelled as a pathological state or tissue-level change (e.g. morphological abnormality).
- `disease_as_syndrome` — disease modelled as a named cluster of co-occurring signs and symptoms without a single unifying cause.
- `mixed_or_unclear` — the class combines multiple views or the evidence is insufficient to assign one category.
- `not_applicable` — the class is not a disease class proper (e.g. a process or quality encountered through hierarchy traversal).

### Quality fields (`definition_quality`, `comment_quality`, `parentage_quality`, `provenance_quality`)

- `good` — fully adequate for the purpose; see per-field guidance in Assessment Steps.
- `partial` — informative but incomplete, inconsistent, or underspecified.
- `poor` — minimal or unhelpful; provides little usable information.
- `absent` — the field is entirely missing.
- `not_applicable` — the field is not a meaningful evidence type for this class or source (used for `comment_quality` only).

### `quality_decision`

- `high_confidence_include` — definition, parentage, and relevance are all adequate; no reservation.
- `include_with_caveat` — usable but with a noted limitation (e.g. missing definition, imported term, shallow parentage) that should be acknowledged in reporting.
- `exclude` — not used in substantive synthesis.
- `uncertain_second_review` — confidence is insufficient for a unilateral decision; requires an independent second reviewer.

## Assessment Steps

1. Start from the enriched extraction.

   Use `disease_terms_review_enriched.csv` because it contains machine provenance, ontology metadata, preasserted exclusion hints, native/imported-term guesses, definitions, comments, parents, and BFO anchors.

2. Check ontology-level eligibility.

   Review `ontology_exclusion_status`, `ontology_exclusion_rule`, `ontology_scope_category`, `ontology_title`, `ontology_status`, `ontology_homepage`, and `ontology_license`.

   Assign `ontology_type_manual` from its controlled list. If the ontology is clearly a demo, training resource, value-set collection, obsolete resource, or generated local artifact, keep the entity row in the extraction but set `manual_include_status` to `exclude` and `manual_exclusion_reason` accordingly.

3. Decide whether the row represents a native term or an imported/reused term.

   Compare `class_iri`, `ontology`, `source_ontology_ids`, and `native_ontology_guess`.

   If the IRI namespace points to a different ontology than the reporting ontology, set `native_or_imported_manual` to `imported` or `reused_unclear`. Imported terms are not automatically excluded, but they should not be counted as independent implementations unless the review question explicitly includes reuse/import behaviour.

4. Assess entity relevance.

   Ask whether the class is genuinely relevant to disease modelling, not merely a clinical data field, value-set category, document field, or generic label.

   If it is not conceptually relevant, set `manual_include_status` to `exclude` and `manual_exclusion_reason` to `not_disease_modelling_relevant` or another matching value.

5. Assess definition quality.

   Use `definition`, `comments`, and `synonyms`.

   Set `definition_quality`:

   - `good`: genus/differentia structure or otherwise clear, unambiguous ontological meaning.
   - `partial`: informative but incomplete, circular, or underspecified in a way that limits precise interpretation.
   - `poor`: vague, operational (describes use rather than meaning), or mostly lexical.
   - `absent`: no definition present.

   Set `comment_quality` using the same scale (substitute `not_applicable` if comments are not a meaningful evidence type for this source).

6. Assess parentage and upper-level modelling.

   Use `parent_labels`, `parent_iris`, and `bfo_anchor`.

   Record `upper_level_interpretation` in plain language, for example `subclass of disposition`, `subclass of process`, `clinical finding`, `quality or state`, or `unclear`.

   Set `parentage_quality`:

   - `good`: placed under a meaningful, informative superclass that reflects a deliberate upper-level modelling choice.
   - `partial`: some placement present but shallow, inconsistent across sources, or only weakly informative.
   - `poor`: placed directly under `owl:Thing` or a very generic class that provides no modelling information.
   - `absent`: no parent class asserted.

   Set `provenance_quality`:

   - `good`: ontology version, retrieval date, and source URL are all present and machine-readable.
   - `partial`: some provenance present but one or more fields are missing or ambiguous.
   - `poor`: only minimal provenance available (e.g. retrieval date only, no version).
   - `absent`: no provenance metadata recorded.

7. Assign disease model category.

   Choose the best-fitting `disease_model_category` from the controlled list. If the class mixes several views or the evidence is insufficient, use `mixed_or_unclear`.

8. Score entity quality.

   Set `entity_quality_score` as a small integer:

   - `3`: clear, relevant, well-defined, and structurally interpretable.
   - `2`: relevant but incomplete or partially underspecified.
   - `1`: weak, vague, mostly terminological, or poorly grounded.
   - `0`: exclude from substantive analysis.

9. Decide inclusion.

   Set `quality_decision`:

   - `high_confidence_include`: suitable for analysis without reservation.
   - `include_with_caveat`: usable, but note limitation in `review_notes`.
   - `exclude`: not used in substantive synthesis.
   - `uncertain_second_review`: needs an independent second pass.

   Align `manual_include_status` with this decision: `include` or `maybe` for the first two, `exclude` for the third, `needs_second_review` for the fourth.

10. Preserve auditability.

    Fill `reviewer`, `review_date`, and `review_notes`. Use ISO dates such as `2026-06-29`.

    If a second reviewer checks the row, fill `second_reviewer`, `second_review_date`, `disagreement_flag` (`true` if decisions differ), and `adjudication_decision` (uses the same values as `quality_decision`).

## Suggested Counting Rules

Report both counts separately:

- Unique entity implementations by `class_iri`.
- Ontology appearances by `source_ontology_ids` or `source_records`.

Do not count imported copies of the same IRI as independent disease implementations unless the analysis question is explicitly about reuse/import patterns.

## Rerun Workflow

1. Rerun the extraction script or notebook to produce a fresh enriched CSV.
2. Keep `disease_terms_manual_annotations.csv` unchanged.
3. Merge manual annotations onto the fresh extraction by `class_iri`.
4. New IRIs receive blank manual fields.
5. Annotated IRIs missing from the new extraction should be kept in the manual file and flagged in a merge report as not currently retrieved.

This keeps the review reproducible while allowing the generated extraction file to change.
