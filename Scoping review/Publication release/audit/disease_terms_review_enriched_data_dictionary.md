# Disease Ontology Artifact-Evaluation Master Data Dictionary

`disease_terms_review_enriched.csv` is the sole editable master table. All TTL files and reports are generated from it.

| Column | Controlled values |
|---|---|
| `term` | Free text, identifier, provenance value, or generated field |
| `discovery_tier` | Free text, identifier, provenance value, or generated field |
| `ontology` | Free text, identifier, provenance value, or generated field |
| `preferred_label` | Free text, identifier, provenance value, or generated field |
| `class_iri` | Free text, identifier, provenance value, or generated field |
| `definition` | Free text, identifier, provenance value, or generated field |
| `comments` | Free text, identifier, provenance value, or generated field |
| `synonyms` | Free text, identifier, provenance value, or generated field |
| `parent_labels` | Free text, identifier, provenance value, or generated field |
| `parent_iris` | Free text, identifier, provenance value, or generated field |
| `bfo_anchor` | Free text, identifier, provenance value, or generated field |
| `mapping_count` | Free text, identifier, provenance value, or generated field |
| `exact_match_iris` | Free text, identifier, provenance value, or generated field |
| `defined_by_iris` | Free text, identifier, provenance value, or generated field |
| `conforms_to_iris` | Free text, identifier, provenance value, or generated field |
| `source_databases` | Free text, identifier, provenance value, or generated field |
| `retrieved_at_by_database` | Free text, identifier, provenance value, or generated field |
| `ontology_versions` | Free text, identifier, provenance value, or generated field |
| `source_ontology_ids` | Free text, identifier, provenance value, or generated field |
| `source_urls` | Free text, identifier, provenance value, or generated field |
| `source_records` | Free text, identifier, provenance value, or generated field |
| `ontology_title` | Free text, identifier, provenance value, or generated field |
| `ontology_description` | Free text, identifier, provenance value, or generated field |
| `ontology_domain` | Free text, identifier, provenance value, or generated field |
| `ontology_homepage` | Free text, identifier, provenance value, or generated field |
| `ontology_repository` | Free text, identifier, provenance value, or generated field |
| `ontology_license` | Free text, identifier, provenance value, or generated field |
| `ontology_status` | Free text, identifier, provenance value, or generated field |
| `ontology_metadata_source` | Free text, identifier, provenance value, or generated field |
| `ontology_metadata_retrieved_at` | Free text, identifier, provenance value, or generated field |
| `ontology_scope_category` | Free text, identifier, provenance value, or generated field |
| `ontology_exclusion_status` | Free text, identifier, provenance value, or generated field |
| `ontology_exclusion_rule` | Free text, identifier, provenance value, or generated field |
| `ontology_exclusion_reason` | Free text, identifier, provenance value, or generated field |
| `native_ontology_guess` | Free text, identifier, provenance value, or generated field |
| `native_term_status` | Free text, identifier, provenance value, or generated field |
| `native_source_ontology_ids` | Free text, identifier, provenance value, or generated field |
| `dependent_source_ontology_ids` | Free text, identifier, provenance value, or generated field |
| `dependency_on_ontology_ids` | Free text, identifier, provenance value, or generated field |
| `source_appearance_summary` | Free text, identifier, provenance value, or generated field |
| `review_route` | Free text, identifier, provenance value, or generated field |
| `manual_screening_hint` | Free text, identifier, provenance value, or generated field |
| `manual_include_status` | `include`, `exclude` |
| `manual_exclusion_reason` | blank, `demo_or_training_resource`, `value_set_or_collection`, `terminology_not_ontology`, `duplicate_imported_term`, `obsolete_or_noncurrent`, `insufficient_metadata`, `out_of_scope`, `replaced_by_better_native_disease_model_candidate` |
| `manual_exclusion_detail` | Free text, identifier, provenance value, or generated field |
| `ontology_type_manual` | `curated_ontology`, `clinical_terminology`, `thesaurus`, `value_set`, `application_ontology`, `demo_or_training_resource`, `generated_or_local_resource`, `unclear` |
| `native_or_imported_manual` | `native`, `imported`, `reused_unclear`, `unknown` |
| `logical_inconsistency` | blank, `wrong_is_a_hierarchy`, `contradictory_upper_level`, `reasoner_inconsistent`, `other_logical_error` |
| `disease_model_category` | blank, `entity_as_dependent_continuant`, `entity_as_realizable_entity`, `entity_as_bfo:disposition`, `entity_as_disposition_non_bfo`, `entity_as_sio:quality`, `entity_as_situation`, `no_grounded_model`, `entity_as_disorder`, `entity_as_process`, `entity_as_finding`, `entity_as_biotop:condition`, `entity_as_kantian_state`, `entity_as_domain_specific_abnormal_pattern`, `entity_as_pathology`, `entity_as_syndrome`, `mixed_model`, `unclear_model`, `not_applicable` |
| `no_grounded_model_subtype` | Free text, identifier, provenance value, or generated field |
| `ontological_category` | blank, `continuant`, `occurrent`, `mixed_continuant_occurrent_model`, `no_continuant_occurrent_commitment`, `unclear` |
| `pathological_grounding` | blank, `statistical`, `evolutionary_function`, `normative`, `primitive_criteria`, `undefined`, `not_applicable` |
| `crisp_vs_graded` | blank, `crisp`, `graded_or_fuzzy`, `prototype`, `gradedness_in_data`, `silent` |
| `reality_vs_classification` | blank, `biological_state`, `illness_role`, `nosological_category`, `precision_medicine_stratification`, `conflated`, `unclear` |
| `review_comment` | Free text, identifier, provenance value, or generated field |
| `definition_quality` | `good`, `partial`, `poor`, `absent` |
| `comment_quality` | `good`, `partial`, `poor`, `absent`, `not_applicable` |
| `parentage_quality` | `good`, `partial`, `poor`, `absent` |
| `entity_quality_score` | `3`, `2`, `1`, `0` |
| `quality_decision` | `high_confidence_include`, `include_with_caveat`, `uncertain_second_review` |
| `reviewer` | Free text, identifier, provenance value, or generated field |
| `review_date` | Free text, identifier, provenance value, or generated field |
| `second_reviewer` | Free text, identifier, provenance value, or generated field |
| `second_review_date` | Free text, identifier, provenance value, or generated field |
| `disagreement_flag` | Free text, identifier, provenance value, or generated field |
| `adjudication_decision` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_source_ontology_id` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_status` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_confidence` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_doi` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_pmid` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_pmcid` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_url` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_publication_title` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_authors` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_year` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_venue` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_bibliographic_citation` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_lookup_source` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_source` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_approved` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_assignment_flag` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_assignment_flag_reason` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_assignment_checked_at` | Free text, identifier, provenance value, or generated field |
| `hierarchy_evidence_status` | `native_module`, `fallback_with_evidence`, `insufficient_metadata` |
| `hierarchy_module_iri` | Free text, identifier, provenance value, or generated field |
| `hierarchy_module_source` | Free text, identifier, provenance value, or generated field |
| `hierarchy_evidence_detail` | Free text, identifier, provenance value, or generated field |
| `definition_values_json` | Free text, identifier, provenance value, or generated field |
| `comment_values_json` | Free text, identifier, provenance value, or generated field |
| `synonym_values_json` | Free text, identifier, provenance value, or generated field |
| `parent_iri_values_json` | Free text, identifier, provenance value, or generated field |
| `parent_label_values_json` | Free text, identifier, provenance value, or generated field |
| `effective_synthesis_status` | `include`, `exclude`, `needs_user_decision` |
| `effective_synthesis_exclusion_reason` | Free text, identifier, provenance value, or generated field |
| `effective_decision_basis` | Free text, identifier, provenance value, or generated field |
| `effective_decision_rule` | Free text, identifier, provenance value, or generated field |
| `publication_eligibility_override` | blank, `include`, `exclude` |
| `publication_review_comment_proposed` | Free text, identifier, provenance value, or generated field |
| `publication_comment_status` | blank, `not_needed`, `needs_review`, `approved`, `rejected` |
| `publication_ambiguity_flags` | Free text, identifier, provenance value, or generated field |
| `publication_ambiguity_note` | Free text, identifier, provenance value, or generated field |
| `modelling_citation_notes` | Free text, identifier, provenance value, or generated field |
