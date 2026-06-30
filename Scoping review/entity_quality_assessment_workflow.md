# Entity Quality Assessment Workflow

This workflow keeps human review reusable across regenerated extraction files. Treat `disease_terms_review_enriched.csv` as machine output and `disease_terms_manual_annotations.csv` as the durable human annotation layer.

## Files

- `disease_terms_review_enriched.csv`: generated search and enrichment output.
- `disease_terms_manual_annotations.csv`: stable manual annotations keyed by `class_iri`.
- `disease_terms_review_annotated.csv`: merged working file produced from generated extraction plus manual annotations.

Do not use row number as an identifier. Use `class_iri` as the primary key. Keep `term`, `preferred_label`, and `source_ontology_ids` in the manual file only as human-readable context.

## Controlled Values

Use these values where possible.

`manual_include_status`:

- `include`
- `exclude`
- `maybe`
- `needs_second_review`

`manual_exclusion_reason`:

- `demo_or_training_resource`
- `value_set_or_collection`
- `not_disease_modelling_relevant`
- `terminology_not_ontology`
- `duplicate_imported_term`
- `obsolete_or_noncurrent`
- `insufficient_metadata`
- `out_of_scope_other`

`ontology_type_manual`:

- `curated_ontology`
- `clinical_terminology`
- `value_set`
- `application_ontology`
- `demo_or_training_resource`
- `generated_or_local_resource`
- `unclear`

`native_or_imported_manual`:

- `native`
- `imported`
- `reused_unclear`
- `unknown`

`disease_model_category`:

- `disease_as_disposition`
- `disease_as_disorder`
- `disease_as_process`
- `disease_as_finding`
- `disease_as_condition`
- `disease_as_pathology`
- `disease_as_syndrome`
- `mixed_or_unclear`
- `not_applicable`

Quality fields use:

- `good`
- `partial`
- `poor`
- `absent`
- `not_applicable`

`quality_decision`:

- `high_confidence_include`
- `include_with_caveat`
- `exclude`
- `uncertain_second_review`

## Assessment Steps

1. Start from the enriched extraction.

   Use `disease_terms_review_enriched.csv` because it contains machine provenance, ontology metadata, preasserted exclusion hints, native/imported-term guesses, definitions, comments, parents, and BFO anchors.

2. Check ontology-level eligibility.

   Review `ontology_exclusion_status`, `ontology_exclusion_rule`, `ontology_scope_category`, `ontology_title`, `ontology_status`, `ontology_homepage`, and `ontology_license`.

   If the ontology is clearly a demo, training resource, value-set collection, obsolete resource, or generated local artifact, keep the entity row in the extraction but mark the manual annotation as `exclude`.

3. Decide whether the row represents a native term or an imported/reused term.

   Compare `class_iri`, `ontology`, `source_ontology_ids`, and `native_ontology_guess`.

   If the IRI namespace points to a different ontology than the reporting ontology, mark `native_or_imported_manual` as `imported` or `reused_unclear`. Imported terms are not automatically excluded, but they should not be counted as independent implementations unless the review question explicitly includes reuse/import behavior.

4. Assess entity relevance.

   Ask whether the class is genuinely relevant to disease modelling, not merely a clinical data field, value-set category, document field, or generic label.

   If it is not conceptually relevant, set `manual_include_status` to `exclude` and choose `not_disease_modelling_relevant` or another matching exclusion reason.

5. Assess definition quality.

   Use `definition`, `comments`, and `synonyms`.

   Mark `definition_quality` as:

   - `good`: genus/differentia or otherwise clear ontological meaning.
   - `partial`: informative but incomplete, circular, or underspecified.
   - `poor`: vague, operational, or mostly lexical.
   - `absent`: no definition.

6. Assess parentage and upper-level modelling.

   Use `parent_labels`, `parent_iris`, and `bfo_anchor`.

   Record `upper_level_interpretation` in plain language, for example `subclass of disposition`, `subclass of process`, `clinical finding`, `quality/state`, or `unclear`.

   Mark `parentage_quality` as `good`, `partial`, `poor`, or `absent`.

7. Assign disease model category.

   Choose the best-fitting `disease_model_category` from the controlled list. If the class mixes several views or the evidence is insufficient, use `mixed_or_unclear`.

8. Score entity quality.

   Use `entity_quality_score` as a small integer:

   - `3`: clear, relevant, well-defined, and structurally interpretable.
   - `2`: relevant but incomplete or partially underspecified.
   - `1`: weak, vague, mostly terminological, or poorly grounded.
   - `0`: exclude from substantive analysis.

9. Decide inclusion.

   Set `quality_decision`:

   - `high_confidence_include`: suitable for analysis.
   - `include_with_caveat`: usable, but note limitation.
   - `exclude`: not used in substantive synthesis.
   - `uncertain_second_review`: needs another pass.

10. Preserve auditability.

   Fill `reviewer`, `review_date`, and `review_notes`. Use ISO dates such as `2026-06-29`.

   If a second reviewer checks the row, fill `second_reviewer`, `second_review_date`, `disagreement_flag`, and `adjudication_decision`.

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
