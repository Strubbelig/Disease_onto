# Supplementary Methods: Systematic Ontology-Artifact Evaluation

## Study object

The primary data are ontology classes, not publications. Each record is keyed by exact class IRI and contains the retrievable evidence needed to characterize that class at the recorded time: preferred label, synonyms, definitions, comments, asserted named superclass hierarchy, mappings, registry/source provenance, and available ontology metadata. The analytical unit is one unique class IRI. Source-ontology and registry appearances are retained separately as provenance and routing data.

## Registry search

Retrieval ran from 29 June through 6 July 2026. BioPortal was the primary sampling frame. OLS supplied supplementary registry coverage. Active OBO Foundry products absent from BioPortal were scanned directly. Targeted source retrieval was used only to resolve a known artifact or replacement class.

| Source | Endpoint and parameters | Local processing |
|---|---|---|
| BioPortal | `GET https://data.bioontology.org/search`; `q={term}`; `require_exact_match=true`; `include=prefLabel,definition,synonym,notation,properties`; `pagesize=100`; `page={n}` | Followed pagination until `nextPage` was absent, with a 50-page safety cap. Results were filtered to normalized exact-label equality. Class details, parents, mappings, and current submission metadata were retrieved from ontology class endpoints. |
| OLS v4 | `GET https://www.ebi.ac.uk/ols4/api/search`; `q={term}`; `exact=true`; `type=class`; `queryFields=label`; `rows=100`; `start={n}` | Continued to `numFound`, filtered to normalized exact-label equality, and retrieved term, parent, and ontology metadata from OLS term endpoints. |
| OBO Foundry | `GET https://obofoundry.org/registry/ontologies.yml`, then active `.obo` or `.owl` products | Products already indexed in BioPortal were skipped. Named classes and superclass links were parsed from each remaining active artifact without an ontology-count cap. |

Normalization inserted spaces at camel-case boundaries, removed punctuation, collapsed whitespace, and applied case folding.

### Primary exact-label terms

`disease`; `disorder`; `disorders`; `illness`; `condition`; `health condition`; `ClinicalCondition`; `Clinical Condition`; `syndrome`; `pathological process`; `pathological disposition`; `dysfunction`.

### Sensitivity terms

`pathological condition`; `pathological state`; `abnormal state`; `disease state`; `pathologic process`; `morbid condition`; `nosological entity`.

Compound labels included `Disease, finding or disorder`, `DiseaseDisorderOrFinding`, `Disease or disorder`, `Disease or syndrome`, `Disorder or finding`, and `Clinical finding or disorder`. A limited multilingual pass used `maladie`, `trouble`, `condition pathologique`, `Krankheit`, `Erkrankung`, and `Störung`.

Secondary broad terms were retained only for source ontologies without a primary-tier target, while compound disease labels remained independently eligible.

## Candidate routing

Automated, auditable routing preceded human assessment:

1. Value-set collections were retained in the source log but removed from independent ontology analysis.
2. Injury, predisposition, disease course, and other non-synonymous contextual concepts were excluded as out of scope.
3. A syndrome candidate was suppressed when the same ontology supplied a disease or disorder target.
4. A pathological-process candidate was suppressed when a stronger disease root was present, but retained when the process was the ontology's disease model.
5. A weaker label hit was replaced when hierarchy inspection identified a better native disease-model class.
6. Explicit exact matches to canonical disease roots and classes defined by an external namespace were routed as reuse rather than independent models.
7. Imported appearances were retained as dependency evidence and analysed at the native provider unless the receiving ontology made an independent placement or modification.

Local or WebProtege IRIs were not excluded solely because of IRI form. Sparse evidence lowered quality or could lead to an `insufficient_metadata` decision, but it was not an automatic provenance exclusion.

## Deduplication

The primary key was exact class IRI. When no IRI was available during raw retrieval, the temporary fallback key combined normalized ontology identifier, preferred label, and search term. Before analytical inclusion, every retained row required a class IRI. Definitions, comments, source databases, ontology identifiers, versions, URLs, and timestamps from duplicate appearances were merged without discarding provenance.

## Eligibility

A class was eligible when it represented disease or a justified immediate conceptual neighbour and supplied enough inspectable evidence to identify the class and assess its asserted placement. A class was excluded from independent synthesis when it was a thesaurus/value-set entry, demo/training resource, out-of-scope concept, obsolete/noncurrent record, weaker duplicate, mapping-only appearance, or unmodified external import. Excluded records remained in the master table with a reason code.

Models described only in publications were not analytical observations when no class-level artifact or sufficient registry record could be inspected. The Hozo River Flow Model and YAMATO were discussed as contextual proposals but were absent from the artifact denominator because inspectable implementations could not be retrieved.

## Evidence extraction and coding

The interface presented the retrieved label, definition, comments, synonyms, named parent labels and IRIs, mappings, provenance, ontology metadata, and any approved supporting citation. One human assessor assigned:

- eligibility and exclusion reason;
- ontology type and native/imported status;
- independent-analysis or dependency-only route;
- logical inconsistency flags;
- disease-model category;
- ontological category;
- pathological grounding;
- crisp-versus-graded commitment;
- reality-versus-classification commitment;
- definition, comment, and parentage quality;
- entity-quality score from 0 to 3;
- a concise evidence-based modelling comment.

Definitions of all controlled values are serialized in `review_core.ttl` and documented in the publication data dictionary. Deterministic prefills were used only when explicit lexical or superclass evidence met a documented rule. Prefilled values remained visible and editable by the assessor.

## Reliability

One assessor completed the full dataset. A second assessor will independently evaluate 50 unique class IRIs selected through the prespecified stratified procedure in `second_reviewer_stratified_validation.md`. The second assessor will be blinded to first-assessor decisions and comments. Both original values will be retained before reconciliation. Raw agreement will be reported for all controlled fields; Cohen's kappa will be reported for eligible nominal fields and weighted kappa for the ordinal entity-quality score. A field with no between-class variation will be reported descriptively because kappa is undefined.

## Analysis

The analysis reports counts, percentages, cross-tabulations, and selected group means. The four principal dimensions are `ontological_category`, `pathological_grounding`, `crisp_vs_graded`, and `reality_vs_classification`. Entity quality is descriptive and is not an eligibility criterion. Comparisons between grounded and ungrounded classes are explicitly interpreted as associations because grounding and parentage are components of the rubric.

## Reproducibility

The sole editable data source is `Extraction Tables/disease_terms_review_enriched.csv`. `publication_readiness.py` materializes publication decisions, builds source modules, normalizes approved citations, exports complete and included-only TTL views, creates an audit report, and packages the release. `review_extraction_pipeline.py` implements registry extraction and the assessment interface. `make_artifact_selection_flow_diagram.py` generates Figure 1 directly from the master and routing tables.

Generated ontology files use fixed non-resolving UUID URNs and resolve locally through `catalog-v001.xml`. The publication package includes the schema, data dictionary, audit report, source-module manifest, and hashes. Credentials are not distributed.
