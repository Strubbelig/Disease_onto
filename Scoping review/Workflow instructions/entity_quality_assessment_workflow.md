# Entity Quality Assessment Workflow

This workflow treats the review ontology as the durable review workspace. The reviewed objects are OWL classes, not spreadsheet rows. Human decisions are recorded as `rev:*` annotations on each reviewed class in the review ontology. Tables may still be generated for batch editing, QA, statistics, or manuscript reporting, but they are not the conceptual source of truth.

The formal definitions and controlled-value sets for every annotation property are declared in `review_core.ttl` (namespace `https://example.org/disease-review/ap/`). This document provides the procedural guidance; the ontology is the authoritative source for property semantics and should be imported by the review ontology.

## Files

- `disease_terms_review.ttl`: main review ontology. It declares reviewed class stubs, imports `review_core.ttl`, imports all extraction modules needed to resolve class hierarchy, and stores manual review annotations.
- `review_core.ttl`: core annotation-property ontology defining all `rev:*` fields and controlled values.
- `bioportal_hierarchy_modules/` and `review_target_fallback_modules/`: imported ontology modules that provide labels, definitions, parentage, and hierarchy axioms. These modules provide evidence; they are not where review decisions are made.
- `disease_terms_review_enriched.csv`: generated machine-output table used only as an intermediate extraction and QA view.
- `disease_terms_manual_annotations.csv`: optional compatibility/export table for batch editing or backup. If used, it must be synchronized back into `disease_terms_review.ttl`.
- `disease_terms_review_annotated.csv`: optional generated report view combining extraction context and manual decisions.

Do not use row number as an identifier. Use the class IRI as the primary review key. If a class appears in several registries or source ontologies, keep one reviewed class node and record the source appearances with `rev:source_ontology_ids`, `rev:source_databases`, and related provenance annotations.

## Review Ontology Pattern

Each reviewed disease class should have:

- an `owl:Class` declaration in `disease_terms_review.ttl`;
- provenance and extraction-context annotations copied from the extraction;
- manual review annotations from `review_core.ttl`;
- its asserted labels, definitions, and hierarchy resolved through imported modules, not duplicated in the review ontology.

The review ontology should contain only the MIREOT-style stubs and review annotations needed for the scoping review. Subclass axioms, labels, definitions, and source ontology metadata should come from the imported modules whenever possible. This keeps Protege readable and prevents doubled axioms.

If a reviewed class does not resolve through an imported module, that is a pipeline error or source limitation that must be handled explicitly before review. Either import the missing module or create a documented fallback module for that class. Do not silently review unresolved stubs as if hierarchy evidence were present.

## Native Classes vs Dependency Appearances

The review separates two things that registries often mix together:

- **Class-level disease model:** the ontology that natively defines the disease/disorder class IRI. This is the unit that may receive independent quality assessment and disease-model annotations.
- **Source ontology appearance:** another ontology in which the same class IRI appears because it was imported, reused, or indexed through a dependency. This is useful evidence of reuse, but it is not an independent disease model.

Example: if an application ontology contains `http://purl.obolibrary.org/obo/OGMS_0000031` only by importing OGMS, the application ontology should be listed as an appearance/dependency, but the disease-model analysis and citation belong to OGMS. Do not search for a separate disease-modelling paper for every ontology that merely imports OGMS.

Use the generated fields:

- `native_source_ontology_ids`: sources where the class appears native.
- `dependent_source_ontology_ids`: sources where the class appears imported/reused.
- `dependency_on_ontology_ids`: the native ontology to cite/analyze for dependent appearances.
- `review_route`: whether the class goes through independent review or dependency-only listing.

Dependency-only source ontologies should remain visible in the source-appearance report, but they should not receive independent class-quality annotations unless they add a native disease/disorder/pathological-process class of their own.

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
- `out_of_scope` — the class is out of scope for the review: not conceptually relevant to disease modelling (e.g. a document field, administrative category, or generic label), or otherwise outside scope; elaboration may be given in `manual_exclusion_detail`.
- `terminology_not_ontology` — the resource is a clinical terminology or code system without formal ontological structure adequate for the review purpose.
- `duplicate_imported_term` — the class IRI belongs to another ontology; this occurrence is an import, not an independent implementation.
- `obsolete_or_noncurrent` — the ontology or class is marked deprecated, inactive, retired, or otherwise non-current.
- `insufficient_metadata` — too little metadata (definition, parents, provenance) to assess relevance or quality.

### `ontology_type_manual`

- `curated_ontology` — formally maintained, logically structured ontology intended for community reuse.
- `clinical_terminology` — terminological resource primarily for clinical coding (e.g. SNOMED CT, LOINC); may lack formal ontological structure.
- `thesaurus` — controlled vocabulary/thesaurus organized primarily for term lookup, indexing, or synonym management, including NCIT, MeSH, and UMLS Metathesaurus for this review. Selecting this source type excludes the row from independent class-level modelling review; set `manual_include_status` to `exclude` and `manual_exclusion_reason` to `terminology_not_ontology`. Do not exclude an otherwise eligible ontology only because it cites, maps to, or exact-matches a thesaurus class.
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

- Optional synthesis bucket. Use only after writing the free-text `upper_level_interpretation`; leave blank if the source's own model is more precise than the available buckets.
- `entity_as_realizable_entity` — the reviewed entity is modelled at the broader level of realizable entity, without enough evidence to narrow it to disposition.
- `entity_as_bfo:disposition` — the reviewed entity is modelled as a realizable entity, tendency, or disposition of a bearer (e.g. BFO disposition or risk).
- `entity_as_situation` — the reviewed entity is modelled as a situation, state of affairs, or configuration of circumstances.
- `no_grounded_model` — the reviewed entity is modelled as a terminology/classification category without a clear commitment to what kind of biomedical entity disease is.
- `entity_as_disorder` — the reviewed entity is modelled as a structural or functional disorder of a bodily entity (e.g. OGMS disorder).
- `entity_as_process` — the reviewed entity is modelled as a pathological process or course of events unfolding over time (e.g. BFO process).
- `entity_as_finding` — the reviewed entity is modelled as a clinical observation or finding recorded about a patient (e.g. SNOMED clinical finding).
- `entity_as_biotop:condition` — the reviewed entity is modelled as a BioTop-style condition (or reuses BioTop's condition): a patient condition without further upper-ontological commitment.
- `entity_as_kantian_state` — the reviewed entity is modelled as a state in the Kantian sense: a way a substance/bearer is determined, rather than an independent entity.
- `entity_as_pathology` — the reviewed entity is modelled as a pathological state or tissue-level change (e.g. morphological abnormality).
- `entity_as_syndrome` — the reviewed entity is modelled as a named cluster of co-occurring signs and symptoms without a single unifying cause.
- `mixed_model` — the class intentionally combines more than one modelling perspective.
- `unclear_model` — the available evidence is insufficient to assign a philosophical/modelling synthesis category.
- `not_applicable` — the class is not a disease-like entity proper (e.g. a process or quality encountered through hierarchy traversal).

### Quality fields (`definition_quality`, `comment_quality`, `parentage_quality`, `provenance_quality`)

- `good` — fully adequate for the purpose; see per-field guidance in Assessment Steps.
- `partial` — informative but incomplete, inconsistent, or underspecified.
- `poor` — minimal or unhelpful; provides little usable information.
- `absent` — the field is entirely missing.
- `not_applicable` — the field is not a meaningful evidence type for this class or source (used for `comment_quality` only).

### `quality_decision` legacy field

This field is retained for compatibility with earlier exports, but it is no longer part of the active review workflow. Use `manual_include_status`, `upper_level_interpretation`, `disease_model_category`, the quality fields, `entity_quality_score`, and `review_notes` instead.

## Assessment Steps

1. Open the review ontology.

   Open `disease_terms_review.ttl` in Protege, with `review_core.ttl` and all extraction modules imported. Confirm that the class resolves to labels, definitions, and hierarchy axioms from an imported module. The CSV extraction can be used to find candidates, but the review should be performed against the ontology view.

   If Protege becomes hard to navigate, use the interactive pipeline reviewer instead:

   ```bash
   python3 "Scoping review/Python scripts/review_extraction_pipeline.py" --chunk review-class
   ```

   The reviewer prints the evidence packet for one class, asks for the controlled-value annotations, writes the manual review annotations, and regenerates `disease_terms_review.ttl`.

2. Record source context.

   Review the source context annotations on the class: `ontology_exclusion_status`, `ontology_exclusion_rule`, `ontology_scope_category`, `ontology_title`, `ontology_status`, `ontology_homepage`, `ontology_license`, `source_ontology_ids`, and `source_databases`.

   Assign `ontology_type_manual` from its controlled list. If the source is a `thesaurus`, exclude it from independent class-level modelling review and do not complete the downstream quality-assessment fields. Otherwise, do not decide final inclusion yet unless the source is obviously out of scope and no class-level evidence is needed.

3. Decide whether the class is native or imported/reused.

   Compare the reviewed class IRI, source ontology identifiers, imported module, namespace, and `native_ontology_guess`.

   If the IRI namespace points to a different ontology than the reporting source, set `native_or_imported_manual` to `imported` or `reused_unclear`. Imported terms may remain in the ontology to document reuse, but they should not be counted as independent disease-modelling implementations unless the analysis explicitly studies reuse/import behaviour.

   If `review_route` is `dependency_only_no_independent_analysis`, do not complete the full quality-assessment route for that source ontology. List the source as a dependency appearance and analyze the native ontology named in `dependency_on_ontology_ids` instead.

4. Assess definition quality.

   Use the class annotations shown through the imported module: definitions, comments, synonyms, editorial notes, and provenance annotations.

   Set `definition_quality`:

   - `good`: genus/differentia structure or otherwise clear, unambiguous ontological meaning.
   - `partial`: informative but incomplete, circular, or underspecified in a way that limits precise interpretation.
   - `poor`: vague, operational (describes use rather than meaning), or mostly lexical.
   - `absent`: no definition present.

   Set `comment_quality` using the same scale (substitute `not_applicable` if comments are not a meaningful evidence type for this source).

5. Assess parentage and upper-level modelling.

   Use the asserted and imported superclass hierarchy visible in Protege, plus extracted helper annotations such as `parent_iris`, `parent_labels`, and `bfo_anchor` when present.

   Record `upper_level_interpretation` in plain language first. Use the ontology's own wording where possible, for example `subclass of realizable entity`, `subclass of disposition`, `situation`, `process/course`, `clinical finding`, `state`, `quality`, or `unclear`. Do not force a controlled category at this stage.

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

6. Optionally assign a synthesis category.

   Choose `disease_model_category` only if a controlled bucket is already clear. The values are review synthesis aids, not a claim that every bucket corresponds to a named philosophical position. If the source model is specific, unusual, or not yet confidently categorizable, leave this blank and rely on `upper_level_interpretation`.

7. Score entity quality.

   Set `entity_quality_score` as a small integer:

   - `3`: clear, relevant, well-defined, and structurally interpretable.
   - `2`: relevant but incomplete or partially underspecified.
   - `1`: weak, vague, mostly terminological, or poorly grounded.
   - `0`: use only when the class is excluded at the final scope step.

   Prefill rule: if definition, comment, and superclass/parent evidence are all absent, set `entity_quality_score` to `1`.

8. Decide final scope inclusion.

   Only after checking definition, comment, superclass/parentage, source context, and modelling interpretation, set `manual_include_status`.

   If the class is not conceptually relevant, set `manual_include_status` to `exclude` and `manual_exclusion_reason` to `out_of_scope` or another matching value. If the source is clearly a demo, training resource, value-set collection, obsolete resource, or generated local artifact, set the matching exclusion reason. For included, maybe, or second-review cases, leave `manual_exclusion_reason` and `manual_exclusion_detail` blank.

9. Preserve auditability.

    Fill `reviewer`, `review_date`, and `review_notes`. Use ISO dates such as `2026-06-29`.

    If a second reviewer checks the class, fill `second_reviewer`, `second_review_date`, `disagreement_flag` (`true` if decisions differ), and `adjudication_decision`.

## Suggested Counting Rules

Report both counts separately:

- Unique entity implementations by `class_iri`.
- Ontology appearances by `source_ontology_ids` or `source_records`.

Do not count imported copies of the same IRI as independent disease implementations unless the analysis question is explicitly about reuse/import patterns.

## Rerun Workflow

1. Rerun the extraction pipeline to produce fresh extraction data and modules.
2. Regenerate `disease_terms_review.ttl` in ontology-first mode, preserving existing `rev:*` manual annotations by class IRI.
3. Import one module for every reviewed class, or create a documented fallback module when a source module cannot be obtained.
4. Validate that every reviewed class resolves through at least one imported module.
5. New IRIs receive blank manual review annotations.
6. Previously annotated IRIs missing from the new extraction should remain in the review ontology and be flagged with a note such as "not retrieved in current extraction run".
7. Export CSV views only after the ontology has been regenerated and validated.

This keeps the review reproducible while allowing generated extraction files and imported modules to change. The stable review record is the ontology, not the table.
