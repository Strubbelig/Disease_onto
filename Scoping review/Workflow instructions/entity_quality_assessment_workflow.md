# Entity Quality Assessment Workflow

The reviewed objects are OWL classes, but `disease_terms_review_enriched.csv` is the sole editable master record. Human decisions, extraction evidence, citation decisions, and effective synthesis decisions are stored in that table and keyed by class IRI. The OWL files are generated, inspectable views of the master record and must not be edited as an alternative annotation store.

The formal definitions and controlled-value sets for exported annotation properties are declared in `review_core.ttl` (annotation namespace `urn:uuid:8f96cf34-53c2-48d2-88c5-96d07704fcf7#`). The publication-only ontology package uses non-resolving UUID URNs; its imports resolve through the accompanying local XML catalog. The CSV schema and data dictionary in `Publication release/audit/` define the master-table representation.

## Files

- `disease_terms_review_enriched.csv`: sole editable master table and source for all review decisions and generated products.
- `disease_terms_review.ttl`: complete screening/evidence ontology containing all 278 records, including excluded and unresolved records.
- `disease_terms_synthesis.ttl`: included-only synthesis view; rows marked `needs_user_decision` are not included until adjudicated.
- `review_core.ttl`: core annotation-property ontology defining all `rev:*` fields and controlled values.
- `native_hierarchy_modules/`: subject-sanitized native modules that provide labels, definitions, comments, synonyms, and native asserted superclass paths. Foreign parent classes occur only as stubs.
- `native_hierarchy_modules_manifest.json`: explicit class-to-native-module manifest and evidence status.
- `catalog-v001.xml`: local resolution of persistent module IRIs; generated TTLs contain no absolute local file imports.
- `Publication release/audit/`: baseline hashes, schema, data dictionary, changelog, ambiguity report, and validation report.

Do not use row number as an identifier. Use the class IRI as the primary review key. If a class appears in several registries or source ontologies, keep one reviewed class node and record the source appearances with `rev:source_ontology_ids`, `rev:source_databases`, and related provenance annotations.

## Review Ontology Pattern

Each reviewed disease class should have:

- an `owl:Class` declaration in `disease_terms_review.ttl`;
- provenance and extraction-context annotations copied from the extraction;
- manual review annotations from `review_core.ttl`;
- its asserted labels, definitions, and hierarchy resolved through imported modules, not duplicated in the review ontology.

The evidence ontology should contain only the MIREOT-style stubs and assessment annotations needed for the artifact evaluation. Subclass axioms, labels, definitions, and source ontology metadata should come from the imported modules whenever possible. This keeps Protege readable and prevents doubled axioms.

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

Unresolved publication eligibility is represented separately as `effective_synthesis_status = needs_user_decision`; do not put provisional values into `manual_include_status`.

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
- `entity_as_disposition_non_bfo` — explicitly a disposition in a non-BFO model.
- `entity_as_dependent_continuant` — a dependent continuant without a narrower disposition commitment.
- `entity_as_sio:quality` — modelled as an SIO quality or attribute.
- `entity_as_situation` — the reviewed entity is modelled as a situation, state of affairs, or configuration of circumstances.
- `no_grounded_model` — the reviewed entity is modelled as a terminology/classification category without a clear commitment to what kind of biomedical entity disease is.
- `entity_as_disorder` — the reviewed entity is modelled as a structural or functional disorder of a bodily entity (e.g. OGMS disorder).
- `entity_as_process` — the reviewed entity is modelled as a pathological process or course of events unfolding over time (e.g. BFO process).
- `entity_as_finding` — the reviewed entity is modelled as a clinical observation or finding recorded about a patient (e.g. SNOMED clinical finding).
- `entity_as_biotop:condition` — the reviewed entity is modelled as a BioTop-style condition (or reuses BioTop's condition): a patient condition without further upper-ontological commitment.
- `entity_as_kantian_state` — the reviewed entity is modelled as a state in the Kantian sense: a way a substance/bearer is determined, rather than an independent entity.
- `entity_as_domain_specific_abnormal_pattern` — a source-specific abnormal pattern whose scope is too narrow for a general disease model.
- `entity_as_pathology` — the reviewed entity is modelled as a pathological state or tissue-level change (e.g. morphological abnormality).
- `entity_as_syndrome` — the reviewed entity is modelled as a named cluster of co-occurring signs and symptoms without a single unifying cause.
- `mixed_model` — the class intentionally combines more than one modelling perspective.
- `unclear_model` — the available evidence is insufficient to assign a philosophical/modelling synthesis category.
- `not_applicable` — the class is not a disease-like entity proper (e.g. a process or quality encountered through hierarchy traversal).

### Quality fields (`definition_quality`, `comment_quality`, `parentage_quality`)

- `good` — fully adequate for the purpose; see per-field guidance in Assessment Steps.
- `partial` — informative but incomplete, inconsistent, or underspecified.
- `poor` — minimal or unhelpful; provides little usable information.
- `absent` — the field is entirely missing.
- `not_applicable` — the field is not a meaningful evidence type for this class or source (used for `comment_quality` only).

### `quality_decision` legacy field

This field is retained for compatibility with earlier exports, but it is no longer part of the active review workflow. Use `manual_include_status`, `review_comment`, `disease_model_category`, the coupled-decision fields, the quality fields, and `entity_quality_score` instead.

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

   Record the interpretation and supporting evidence in `review_comment`. Use the ontology's own wording where possible, for example `subclass of realizable entity`, `subclass of disposition`, `situation`, `process/course`, `clinical finding`, `state`, `quality`, or `unclear`.

   Set `parentage_quality`:

   - `good`: placed under a meaningful, informative superclass that reflects a deliberate upper-level modelling choice.
   - `partial`: some placement present but shallow, inconsistent across sources, or only weakly informative.
   - `poor`: placed directly under `owl:Thing` or a very generic class that provides no modelling information.
   - `absent`: no parent class asserted.

6. Optionally assign a synthesis category.

   Choose `disease_model_category` only if a controlled bucket is clear. The values are review synthesis aids, not a claim that every bucket corresponds to a named philosophical position. If evidence is insufficient, use `unclear_model` and explain why in `review_comment`.

7. Score entity quality.

   Set `entity_quality_score` as a small integer:

   - `3`: clear, relevant, well-defined, and structurally interpretable.
   - `2`: relevant but incomplete or partially underspecified.
   - `1`: weak, vague, mostly terminological, or poorly grounded.
   - `0`: use only when the class is excluded at the final scope step.

   Prefill rule: if definition, comment, and superclass/parent evidence are all absent, set `entity_quality_score` to `1`.

8. Decide final scope inclusion.

   Only after checking definition, comment, superclass/parentage, source context, and modelling interpretation, set `manual_include_status`.

   If the class is not conceptually relevant, set `manual_include_status` to `exclude` and `manual_exclusion_reason` to `out_of_scope` or another matching value. For included classes, leave `manual_exclusion_reason` and `manual_exclusion_detail` blank. Rule/manual conflicts are surfaced through `effective_synthesis_status = needs_user_decision` and resolved with `publication_eligibility_override`.

9. Preserve auditability.

    Fill `reviewer`, `review_date`, and `review_comment`. Use ISO dates such as `2026-06-29`.

    If a second reviewer checks the class, fill `second_reviewer`, `second_review_date`, `disagreement_flag` (`true` if decisions differ), and `adjudication_decision`.

## Suggested Counting Rules

Report both counts separately:

- Unique entity implementations by `class_iri`.
- Ontology appearances by `source_ontology_ids` or `source_records`.

Do not count imported copies of the same IRI as independent disease implementations unless the analysis question is explicitly about reuse/import patterns.

## Rerun Workflow

1. Preserve the current master CSV and run the search merge by class IRI; never replace reviewed fields by row position.
2. Run `python3 "Scoping review/Python scripts/publication_readiness.py" build-native-modules`.
3. Run `python3 "Scoping review/Python scripts/publication_readiness.py" citations` and then `materialize`.
4. Resolve items in the UI's **Publication decisions** and **Citations** tabs.
5. Run `python3 "Scoping review/Python scripts/publication_readiness.py" export` and `audit`.
6. Run `python3 -m unittest "Scoping review/Python scripts/test_publication_readiness.py"` and ROBOT OWL 2 DL validation on both generated TTLs.

New IRIs receive blank human-review fields. Previously reviewed IRIs are retained by class IRI. The stable review record is the master CSV; TTLs, modules, reports, and the catalog are reproducible generated artifacts.
