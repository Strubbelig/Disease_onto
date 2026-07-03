#!/usr/bin/env python3
"""One entry point for the disease-ontology scoping-review extraction pipeline.

The older scripts are kept importable, but this class gives one place to run the
main chunks:

    python3 "Scoping review/Python scripts/review_extraction_pipeline.py" --chunk export-review-ontology
    python3 "Scoping review/Python scripts/review_extraction_pipeline.py" --chunk prefill-manual
    python3 "Scoping review/Python scripts/review_extraction_pipeline.py" --chunk search --sources bioportal,ols
    python3 "Scoping review/Python scripts/review_extraction_pipeline.py" --chunk bioportal-hierarchy --limit-rows 10

The review ontology export is intentionally lean: it turns the enriched
extraction CSV and manual annotation CSV into class-review annotations on the
extracted OWL classes. Source-ontology appearances and dependency/reuse routes
are exported as CSV review reports instead of being copied onto each class.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import webbrowser
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
SCOPING_REVIEW_DIR = SCRIPT_DIR.parent
TABLE_DIR = SCOPING_REVIEW_DIR / "Extraction Tables"
ONTOLOGY_DIR = SCOPING_REVIEW_DIR / "Extraction Ontology"

sys.path.insert(0, str(SCRIPT_DIR))
import download_review_ontologies as download_script  # noqa: E402
import prefill_manual_annotations as manual_script  # noqa: E402
import review_disease_terms as terms_script  # noqa: E402


BIOPORTAL_BASE_URL = terms_script.BIOPORTAL_BASE_URL
OLS_BASE_URL = terms_script.OLS_BASE_URL
DELAY = terms_script.DELAY

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
OWL_ONTOLOGY = "http://www.w3.org/2002/07/owl#Ontology"
OWL_IMPORTS = "http://www.w3.org/2002/07/owl#imports"
OWL_VERSION_INFO = "http://www.w3.org/2002/07/owl#versionInfo"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDFS_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"
RDFS_SUBCLASS_OF = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
SKOS_ALT_LABEL = "http://www.w3.org/2004/02/skos/core#altLabel"
IAO_DEFINITION = "http://purl.obolibrary.org/obo/IAO_0000115"
DCTERMS_CREATED = "http://purl.org/dc/terms/created"
DCTERMS_SOURCE = "http://purl.org/dc/terms/source"
DCTERMS_DESCRIPTION = "http://purl.org/dc/terms/description"
DCTERMS_BIBLIOGRAPHIC_CITATION = "http://purl.org/dc/terms/bibliographicCitation"
REV = "https://example.org/disease-review/ap/"
CANONICAL_MESH_ONTOLOGY = "MESH"
DUPLICATE_MESH_ONTOLOGIES = {"MDM", "RH-MESH"}
EXCLUDED_WEBPROTEGE_IRI_HOST = "webprotege.stanford.edu"
WEBPROTEGE_EXCLUSION_REASON = "webprotege_random_or_local_iri_unstable_provenance"
EXCLUDED_VALUESET_ONTOLOGIES = {"VALUESETS"}
VALUESET_EXCLUSION_REASON = "value_set_collection_not_independent_ontology"
CITATION_REVIEW_TERMS = {"condition", "disease", "injury"}
ACCEPTED_CITATION_CONFIDENCES = {"correct", "high", "medium"}
MANUAL_ACCEPTED_CITATION_CONFIDENCES = {"correct"}
REJECTED_CITATION_CONFIDENCES = {
    "not_good",
    "not good",
    "bad",
    "no paper there",
    "no paper yet",
    "no_candidate",
    "very_low",
    "low_screen",
    "wrong ontology",
}
CITATION_DECISION_COLUMNS = [
    "certainty of correctness",
    "certainty_of_correctness",
    "correctness_certainty",
    "best_fit_confidence",
]
BIOPORTAL_NAMESPACE_ALIASES = {
    "CSP": "CRISP",
    "CST": "COSTART",
    "HL7": "HL7",
    "ICPC2P": "ICPC2P",
    "LNC": "LOINC",
    "MEDDRA": "MEDDRA",
    "MESH": "MESH",
    "SNOMEDCT": "SNOMEDCT",
}
NATIVE_NAMESPACE_PATTERNS = [
    (r"ncicb\.nci\.nih\.gov/.+#C\d+", "NCIT", "known NCIT namespace"),
    (r"purl\.obolibrary\.org/obo/NCIT_", "NCIT", "known NCIT namespace"),
    (r"opendata\.inra\.fr/AHOL/", "AHOL", "known AHOL namespace"),
    (r"purl\.org/biotop/", "BIOTOP", "known BioTop namespace"),
    (r"www\.co-ode\.org/ontologies/galen", "GALEN", "known GALEN namespace"),
    (r"purl\.org/cpr/", "CPRO", "known CPRO namespace"),
    (r"semanticweb\.org/rjyy/ontologies/2015/5/ESSO", "ESSO", "known ESSO namespace"),
    (r"semanticweb\.org/ontologies/2009/3/EpilepsyOntology", "EPILONT", "known Epilepsy Ontology namespace"),
    (r"www\.case\.edu/EpSO", "EPSO", "known EpSO namespace"),
    (r"semanticweb\.org/ontologies/2010/2/MiRNA-Ontology", "PVONTO", "known MiRNA ontology namespace"),
    (r"semanticweb\.org/ontologies/Prostate_cancer", "PCALION", "known prostate cancer ontology namespace"),
    (r"limics\.fr/ontologies/ontoDOME", "ONTODOME", "known ontoDOME namespace"),
]

EXTRACTION_REVIEW_COLUMNS = [
    "native_ontology_guess",
    "native_term_status",
    "bfo_anchor",
]

HIERARCHY_DEFINITION_KEYS = {
    "definition",
    "description",
    "iao_0000115",
    "obo:iao_0000115",
    IAO_DEFINITION.lower(),
    "http://www.w3.org/2004/02/skos/core#definition",
}
HIERARCHY_COMMENT_KEYS = {
    "comment",
    "comments",
    "rdfs:comment",
    RDFS_COMMENT.lower(),
    "skos:note",
    "skos:scopenote",
    "scopeNote",
    "iao_0000116",
}
HIERARCHY_SYNONYM_KEYS = {
    "synonym",
    "synonyms",
    "hasExactSynonym",
    "hasRelatedSynonym",
    "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym".lower(),
    "http://www.geneontology.org/formats/oboInOwl#hasRelatedSynonym".lower(),
}

CONTROLLED_VALUES = {
    "manual_include_status": ["include", "exclude", "maybe", "needs_second_review"],
    "manual_exclusion_reason": [
        "",
        "demo_or_training_resource",
        "value_set_or_collection",
        "not_disease_modelling_relevant",
        "terminology_not_ontology",
        "duplicate_imported_term",
        "obsolete_or_noncurrent",
        "insufficient_metadata",
        "out_of_scope_other",
    ],
    "ontology_type_manual": [
        "curated_ontology",
        "clinical_terminology",
        "value_set",
        "application_ontology",
        "demo_or_training_resource",
        "generated_or_local_resource",
        "unclear",
    ],
    "native_or_imported_manual": ["native", "imported", "reused_unclear", "unknown"],
    "disease_model_category": [
        "",
        "entity_as_realizable_entity",
        "entity_as_disposition",
        "entity_as_situation",
        "entity_as_disorder",
        "entity_as_process",
        "entity_as_finding",
        "entity_as_condition",
        "entity_as_state",
        "entity_as_pathology",
        "entity_as_syndrome",
        "mixed_or_unclear",
        "not_applicable",
    ],
    "definition_quality": ["good", "partial", "poor", "absent"],
    "comment_quality": ["good", "partial", "poor", "absent", "not_applicable"],
    "parentage_quality": ["good", "partial", "poor", "absent"],
    "provenance_quality": ["good", "partial", "poor", "absent"],
    "entity_quality_score": ["3", "2", "1", "0"],
    "quality_decision": ["high_confidence_include", "include_with_caveat", "exclude", "uncertain_second_review"],
}

REVIEW_PROMPT_SECTIONS = [
    (
        "1. Eligibility",
        [
            "ontology_type_manual",
            "native_or_imported_manual",
            "manual_include_status",
            "manual_exclusion_reason",
            "manual_exclusion_detail",
        ],
    ),
    (
        "2. Modelling interpretation",
        [
            "upper_level_interpretation",
            "disease_model_category",
        ],
    ),
    (
        "3. Evidence quality",
        [
            "definition_quality",
            "comment_quality",
            "parentage_quality",
            "provenance_quality",
            "entity_quality_score",
        ],
    ),
    (
        "4. Final decision and audit trail",
        [
            "quality_decision",
            "reviewer",
            "review_date",
            "review_notes",
        ],
    ),
]

REVIEW_PROMPT_FIELDS = [
    field
    for _, fields in REVIEW_PROMPT_SECTIONS
    for field in fields
]

PROMPT_GUIDANCE = {
    "ontology_type_manual": "What kind of source resource is this?",
    "native_or_imported_manual": "Is this class defined natively here, imported, or reused unclearly?",
    "manual_include_status": "Should this class enter the substantive review?",
    "manual_exclusion_reason": "If excluded, why? Use blank for included or still-open cases.",
    "manual_exclusion_detail": "Optional free-text detail for exclusions or special cases.",
    "upper_level_interpretation": "Free text first: write what the ontology itself says, e.g. subclass of realizable entity, situation, process, clinical finding, or unclear. Do not force a category.",
    "disease_model_category": "Optional later synthesis bucket. Leave blank if the ontology's own model is more precise than these options.",
    "definition_quality": "How useful is the definition for understanding the entity?",
    "comment_quality": "How useful are comments/notes, if present?",
    "parentage_quality": "How informative is the superclass placement?",
    "provenance_quality": "How adequate is version/source/provenance metadata?",
    "entity_quality_score": "Overall score: 3 strong, 2 usable, 1 weak, 0 excluded.",
    "quality_decision": "Final review decision for synthesis.",
    "reviewer": "Reviewer initials/name.",
    "review_date": "ISO date for this review.",
    "review_notes": "Short caveats, reasoning, or paper evidence used.",
}

FIELD_LABELS = {
    "ontology_type_manual": "Source type",
    "native_or_imported_manual": "Native or imported?",
    "manual_include_status": "Include in substantive review?",
    "manual_exclusion_reason": "Exclusion reason",
    "manual_exclusion_detail": "Exclusion detail",
    "upper_level_interpretation": "Free-text modelling interpretation",
    "disease_model_category": "Optional synthesis category",
    "definition_quality": "Definition quality",
    "comment_quality": "Comment quality",
    "parentage_quality": "Parentage quality",
    "provenance_quality": "Provenance quality",
    "entity_quality_score": "Entity quality score",
    "quality_decision": "Final quality decision",
    "reviewer": "Reviewer",
    "review_date": "Review date",
    "review_notes": "Review notes",
}

MANUAL_REVIEW_COLUMNS_FOR_ONTOLOGY = [
    column
    for column in manual_script.FIELDNAMES
    if column not in {"class_iri", "term", "preferred_label", "source_ontology_ids"}
]


@dataclass
class ReviewPipelineConfig:
    table_dir: Path = TABLE_DIR
    ontology_dir: Path = ONTOLOGY_DIR
    raw_csv: Path = TABLE_DIR / "disease_terms_review.csv"
    enriched_csv: Path = TABLE_DIR / "disease_terms_review_enriched.csv"
    manual_csv: Path = TABLE_DIR / "disease_terms_manual_annotations.csv"
    review_core_ttl: Path = ONTOLOGY_DIR / "review_core.ttl"
    review_ontology_ttl: Path = ONTOLOGY_DIR / "disease_terms_review.ttl"
    smoke_ontology_ttl: Path = ONTOLOGY_DIR / "disease_terms_bioportal_hierarchy_smoke.ttl"
    preferred_citation_workbook: Path = TABLE_DIR / "Ontology_Modelling_Paper_DOIs_changed by MM.xlsx"
    citation_review_workbook: Path = TABLE_DIR / "Ontologies_Needing_Citations.xlsx"
    generated_citation_workbook: Path = TABLE_DIR / "Ontology_Modelling_Paper_DOIs.xlsx"
    citation_lookup_json: Path = TABLE_DIR / "ontology_merged_best_fit_lookup.json"
    citation_coverage_csv: Path = TABLE_DIR / "native_class_citation_coverage.csv"
    exclusion_detail_csv: Path = TABLE_DIR / "ontology_source_exclusions_for_flow_figure.csv"
    exclusion_summary_csv: Path = TABLE_DIR / "ontology_source_exclusion_counts_for_flow_figure.csv"
    fallback_module_dir: Path = ONTOLOGY_DIR / "review_target_fallback_modules"
    bioportal_module_dir: Path = ONTOLOGY_DIR / "bioportal_hierarchy_modules"
    bioportal_merged_ttl: Path = ONTOLOGY_DIR / "disease_terms_bioportal_hierarchy.ttl"
    bioportal_manifest: Path = TABLE_DIR / "bioportal_hierarchy_modules_manifest.csv"
    ols_module_dir: Path = ONTOLOGY_DIR / "ols_hierarchy_modules"
    ols_merged_ttl: Path = ONTOLOGY_DIR / "disease_terms_ols_hierarchy.ttl"
    ols_manifest: Path = TABLE_DIR / "ols_hierarchy_modules_manifest.csv"
    obo_module_dir: Path = ONTOLOGY_DIR / "obo_direct_hierarchy_modules"
    obo_merged_ttl: Path = ONTOLOGY_DIR / "disease_terms_obo_direct_hierarchy.ttl"
    obo_manifest: Path = TABLE_DIR / "obo_direct_hierarchy_modules_manifest.csv"
    import_dir: Path = Path(
        "/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Import ontologies"
    )
    hierarchy_cache_dir: Path = Path("/tmp/disease_review_hierarchy_cache")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).lower()


def clean_list(values: Any) -> list[str]:
    return terms_script.clean_list(values)


def join_values(values: Any) -> str:
    return terms_script.join_values(values)


def split_semicolon(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def citation_lookup_key(value: str) -> str:
    return terms_script.normalise_ontology_id_for_dependency(value)


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("\xa0", " ").strip()


def ttl_literal(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def ttl_iri(iri: str) -> str:
    return f"<{iri}>"


def ttl_line(subject: str, predicate: str, obj: str, *, object_is_iri: bool = False) -> str:
    object_text = ttl_iri(obj) if object_is_iri else ttl_literal(obj)
    return f"{ttl_iri(subject)} {ttl_iri(predicate)} {object_text} ."


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def hierarchy_cache_path(cache_dir: Path, url: str, params: dict[str, Any]) -> Path:
    serialised = json.dumps([url, sorted(params.items())], sort_keys=True, default=str)
    digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{digest}.json"


def hierarchy_get_json(url: str, params: dict[str, Any], cache_dir: Path, retries: int = 3) -> Any | None:
    path = hierarchy_cache_path(cache_dir, url, params)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    for attempt in range(retries):
        try:
            time.sleep(DELAY)
            response = requests.get(url, params=params, timeout=60)
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 10))
                print(f"  [rate limit] waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if response.status_code in {400, 404}:
                print(f"  [warn] GET {url} returned {response.status_code}; skipping", file=sys.stderr)
                return None
            response.raise_for_status()
            data = response.json()
            path.write_text(json.dumps(data), encoding="utf-8")
            return data
        except Exception as exc:
            print(f"  [warn] GET {url} attempt {attempt + 1} failed: {exc}", file=sys.stderr)
            time.sleep(2**attempt)
    return None


def hierarchy_class_url(ontology: str, iri: str, suffix: str = "") -> str:
    encoded = urllib.parse.quote(iri, safe="")
    base = f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{encoded}"
    return f"{base}/{suffix}" if suffix else base


def hierarchy_fetch_class(ontology: str, iri: str, apikey: str, cache_dir: Path) -> dict[str, Any]:
    data = hierarchy_get_json(
        hierarchy_class_url(ontology, iri),
        {"apikey": apikey, "include": "prefLabel,definition,synonym,notation,properties"},
        cache_dir,
    )
    return data if isinstance(data, dict) else {}


def hierarchy_fetch_ancestors(ontology: str, iri: str, apikey: str, cache_dir: Path) -> list[dict[str, Any]]:
    data = hierarchy_get_json(
        hierarchy_class_url(ontology, iri, "ancestors"),
        {"apikey": apikey, "include": "prefLabel,definition,synonym,notation,properties"},
        cache_dir,
    )
    return data if isinstance(data, list) else []


def hierarchy_fetch_parents(ontology: str, iri: str, apikey: str, cache_dir: Path) -> list[dict[str, Any]]:
    data = hierarchy_get_json(
        hierarchy_class_url(ontology, iri, "parents"),
        {"apikey": apikey, "include": "prefLabel,definition,synonym,notation,properties"},
        cache_dir,
    )
    return data if isinstance(data, list) else []


def hierarchy_extract_properties(record: dict[str, Any], wanted_keys: set[str]) -> list[str]:
    values: list[str] = []
    properties = record.get("properties")
    if not isinstance(properties, dict):
        return values
    for key, value in properties.items():
        if terms_script.annotation_key_matches(str(key), wanted_keys):
            values.extend(clean_list(value))
    return values


def hierarchy_triples_for_class(record: dict[str, Any]) -> set[tuple[str, str, str, bool]]:
    iri = record.get("@id", "")
    if not iri:
        return set()

    triples: set[tuple[str, str, str, bool]] = {(iri, RDF_TYPE, OWL_CLASS, True)}
    values_by_predicate = {
        RDFS_LABEL: clean_list(record.get("prefLabel")),
        IAO_DEFINITION: clean_list(record.get("definition")) + hierarchy_extract_properties(record, HIERARCHY_DEFINITION_KEYS),
        RDFS_COMMENT: hierarchy_extract_properties(record, HIERARCHY_COMMENT_KEYS),
        SKOS_ALT_LABEL: clean_list(record.get("synonym")) + hierarchy_extract_properties(record, HIERARCHY_SYNONYM_KEYS),
    }
    for predicate, values in values_by_predicate.items():
        for value in dict.fromkeys(values):
            triples.add((iri, predicate, value, False))
    return triples


def write_hierarchy_ttl(
    path: Path,
    ontology_iri: str,
    triples: set[tuple[str, str, str, bool]],
    *,
    source_label: str,
    ontology_versions: str = "",
    retrieved_at: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n")
        handle.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")
        handle.write("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n")
        handle.write("@prefix iao: <http://purl.obolibrary.org/obo/IAO_> .\n")
        handle.write("@prefix dcterms: <http://purl.org/dc/terms/> .\n\n")
        handle.write(f"{ttl_iri(ontology_iri)} a owl:Ontology ;\n")
        handle.write(f"    dcterms:source {ttl_literal(source_label)}")
        if ontology_versions:
            handle.write(f" ;\n    owl:versionInfo {ttl_literal(ontology_versions)}")
        if retrieved_at:
            handle.write(f" ;\n    dcterms:created {ttl_literal(retrieved_at)}")
        handle.write(
            f" ;\n    rdfs:comment {ttl_literal('Contains review target classes, ancestors or parent paths, direct superclass edges, and common annotations only. Full source OWL axioms are not preserved.')} .\n\n"
        )
        for subject, predicate, obj, object_is_iri in sorted(triples):
            handle.write(ttl_line(subject, predicate, obj, object_is_iri=object_is_iri) + "\n")


def source_names(row: dict[str, str]) -> set[str]:
    return {part.strip().casefold() for part in row.get("source_databases", "").split(";") if part.strip()}


def parse_source_records(row: dict[str, str]) -> list[dict[str, Any]]:
    try:
        records = json.loads(row.get("source_records", "") or "[]")
    except json.JSONDecodeError:
        return []
    return records if isinstance(records, list) else []


def source_specific_rows(row: dict[str, str], source_name: str) -> list[dict[str, str]]:
    wanted = source_name.casefold()
    matches: list[dict[str, str]] = []
    for record in parse_source_records(row):
        if str(record.get("source", "")).casefold() != wanted:
            continue
        expanded = dict(row)
        expanded["ontology"] = str(record.get("ontology") or row.get("ontology", ""))
        expanded["hierarchy_source_database"] = source_name
        expanded["hierarchy_source_url"] = str(record.get("source_url") or "")
        expanded["hierarchy_source_retrieved_at"] = str(record.get("retrieved_at") or "")
        expanded["hierarchy_source_ontology_version"] = str(record.get("ontology_version") or "")
        if expanded["hierarchy_source_ontology_version"]:
            expanded["ontology_versions"] = f"{source_name}: {expanded['hierarchy_source_ontology_version']}"
        matches.append(expanded)

    if matches:
        return matches
    if wanted in source_names(row):
        fallback = dict(row)
        fallback["hierarchy_source_database"] = source_name
        fallback["hierarchy_source_url"] = ""
        fallback["hierarchy_source_retrieved_at"] = ""
        fallback["hierarchy_source_ontology_version"] = ""
        return [fallback]
    return []


def read_source_hierarchy_rows(path: Path, source_name: str, *, only_candidates: bool = True) -> list[dict[str, str]]:
    rows = []
    for row in read_csv_rows(path):
        if only_candidates and row.get("ontology_exclusion_status") == "excluded_preasserted":
            continue
        if not row.get("class_iri"):
            continue
        rows.extend(expanded for expanded in source_specific_rows(row, source_name) if expanded.get("ontology"))
    return rows


def parse_obo_graph(text: str) -> tuple[str, dict[str, dict[str, Any]], dict[str, list[str]]]:
    version = terms_script.parse_obo_header(text).get("data-version", "")
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, list[str]] = defaultdict(list)
    current_kind = ""
    current: dict[str, list[str]] = {}

    def flush_current() -> None:
        if current_kind != "Term" or not current:
            return
        if terms_script.first_clean(current.get("is_obsolete")).lower() == "true":
            return
        curie = terms_script.first_clean(current.get("id"))
        if not curie:
            return
        iri = terms_script.obo_curie_to_iri(curie)
        definition = ""
        if current.get("def"):
            match = re.search(r'"(.*?)"', current["def"][0])
            definition = match.group(1) if match else current["def"][0]
        synonyms = []
        for synonym_line in current.get("synonym", []):
            match = re.search(r'"(.*?)"', synonym_line)
            if match:
                synonyms.append(match.group(1))
        nodes[iri] = {
            "@id": iri,
            "prefLabel": terms_script.first_clean(current.get("name")),
            "definition": clean_list(definition),
            "synonym": synonyms,
            "properties": {RDFS_COMMENT: current.get("comment", [])},
        }
        for parent_line in current.get("is_a", []):
            parent_curie = parent_line.split()[0]
            if parent_curie:
                edges[iri].append(terms_script.obo_curie_to_iri(parent_curie))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("[") and line.endswith("]"):
            flush_current()
            current_kind = line.strip("[]")
            current = {}
            continue
        if current_kind and ":" in line:
            key, value = line.split(":", 1)
            current.setdefault(key.strip(), []).append(value.strip())
    flush_current()
    return version, nodes, edges


def parse_owl_xml_graph(text: str) -> tuple[str, dict[str, dict[str, Any]], dict[str, list[str]]]:
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as exc:
        print(f"  [warn] OWL/XML parse failed: {exc}", file=sys.stderr)
        return "", {}, {}

    rdf_about = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"
    rdf_resource = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
    version = ""
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, list[str]] = defaultdict(list)
    for element in root.iter("{http://www.w3.org/2002/07/owl#}Class"):
        iri = element.attrib.get(rdf_about, "")
        if not iri:
            continue
        synonyms = []
        for child in element:
            name = terms_script.local_name(child.tag)
            if "Synonym" in name and child.text and child.text.strip():
                synonyms.append(child.text.strip())
            if name == "subClassOf" and child.attrib.get(rdf_resource):
                edges[iri].append(child.attrib[rdf_resource])
        nodes[iri] = {
            "@id": iri,
            "prefLabel": terms_script.first_clean(terms_script.child_texts(element, {"label"})),
            "definition": terms_script.child_texts(element, {"IAO_0000115", "definition"}),
            "synonym": synonyms,
            "properties": {RDFS_COMMENT: terms_script.child_texts(element, {"comment"})},
        }
    return version, nodes, edges


def parse_ontology_graph(text: str) -> tuple[str, dict[str, dict[str, Any]], dict[str, list[str]]]:
    stripped = text.lstrip()
    if stripped.startswith("format-version:") or "\n[Term]" in stripped[:5000]:
        return parse_obo_graph(text)
    if stripped.startswith("<?xml") or stripped.startswith("<rdf:RDF") or stripped.startswith("<Ontology"):
        return parse_owl_xml_graph(text)
    print("  [warn] ontology format not supported for OBO direct hierarchy extraction", file=sys.stderr)
    return "", {}, {}


class ReviewExtractionPipeline:
    def __init__(self, config: ReviewPipelineConfig | None = None) -> None:
        self.config = config or ReviewPipelineConfig()

    def run_chunk(self, chunk: str, args: argparse.Namespace) -> None:
        chunks = {
            "search": self.search,
            "enrich": self.enrich,
            "prefill-manual": self.prefill_manual,
            "review-class": self.review_class_interactive,
            "review-ui": self.review_ui,
            "export-appearance-report": self.export_source_appearance_report,
            "export-review-ontology": self.export_review_ontology,
            "export-smoke-ontology": self.export_smoke_ontology,
            "download": self.download_source_ontologies,
            "bioportal-hierarchy": self.extract_bioportal_hierarchy,
            "ols-hierarchy": self.extract_ols_hierarchy,
            "obo-hierarchy": self.extract_obo_hierarchy,
            "all-hierarchies": self.extract_all_hierarchies,
        }
        chunks[chunk](args)

    def search(self, args: argparse.Namespace) -> None:
        sources = terms_script.parse_sources(args.sources)
        terms = [term.strip() for term in args.terms.split(",") if term.strip()] if args.terms else terms_script.DEFAULT_TERMS
        rows_by_key = terms_script.load_existing_rows(self.config.raw_csv) if args.resume else {}

        for source in sources:
            if source == "bioportal":
                apikey = terms_script.load_bioportal_api_key()
                terms_script.merge_rows(
                    rows_by_key,
                    terms_script.bioportal_rows(
                        terms,
                        apikey,
                        fetch_parents=not args.no_parents,
                        fetch_mappings=not args.no_mappings,
                        exact_label_only=not args.include_nonlabel_matches,
                    ),
                )
            elif source == "ols":
                base_url = terms_script.normalise_ols_base_url(args.ols_base_url)
                terms_script.merge_rows(rows_by_key, terms_script.ols_rows(terms, base_url=base_url, fetch_parents=not args.no_parents))
            elif source == "obo":
                bp_ids = terms_script.fetch_bioportal_ontology_ids(terms_script.load_bioportal_api_key()) if "bioportal" in sources else set()
                terms_script.merge_rows(rows_by_key, terms_script.obo_rows(terms, max_ontologies=args.obo_max_ontologies, skip_ids=bp_ids))

        rows = sorted(rows_by_key.values(), key=lambda r: (r.get("term", ""), r.get("ontology", ""), r.get("class_iri", "")))
        fieldnames = terms_script.FIELDNAMES
        if not args.no_enrich_output:
            rows = terms_script.enrich_rows(rows)
            fieldnames = terms_script.FIELDNAMES + terms_script.ENRICHMENT_FIELDNAMES
            write_csv_rows(self.config.enriched_csv, rows, fieldnames)
            print(f"Wrote enriched extraction -> {self.config.enriched_csv}")
        write_csv_rows(self.config.raw_csv, rows, fieldnames)
        print(f"Wrote {len(rows)} extraction rows -> {self.config.raw_csv}")

    def enrich(self, args: argparse.Namespace) -> None:
        rows = read_csv_rows(self.config.raw_csv)
        if args.refresh_class_annotations:
            rows = terms_script.refresh_class_annotations(rows)
        fieldnames = list(dict.fromkeys(list(rows[0].keys() if rows else terms_script.FIELDNAMES) + terms_script.ENRICHMENT_FIELDNAMES))
        enriched = terms_script.enrich_rows(rows)
        write_csv_rows(self.config.enriched_csv, enriched, fieldnames)
        print(f"Enriched {len(enriched)} rows -> {self.config.enriched_csv}")

    def prefill_manual(self, args: argparse.Namespace) -> None:
        enriched_rows = read_csv_rows(self.config.enriched_csv)
        existing = manual_script.load_existing(self.config.manual_csv) if args.merge_manual else {}
        rows = []
        fresh = merged = 0
        for enriched in enriched_rows:
            iri = enriched.get("class_iri", "")
            prefilled = manual_script.prefill_row(enriched)
            if iri in existing and args.merge_manual:
                rows.append(manual_script.merge_rows(existing[iri], prefilled))
                merged += 1
            else:
                rows.append(prefilled)
                fresh += 1
        write_csv_rows(self.config.manual_csv, rows, manual_script.FIELDNAMES)
        print(f"Wrote {len(rows)} manual annotation rows -> {self.config.manual_csv}")
        print(f"  prefilled fresh: {fresh}, merged over existing: {merged}")

    def review_class_interactive(self, args: argparse.Namespace) -> None:
        enriched_rows = self._review_export_rows(read_csv_rows(self.config.enriched_csv))
        if args.limit_rows:
            enriched_rows = enriched_rows[: args.limit_rows]
        existing_manual = manual_script.load_existing(self.config.manual_csv)
        manual_by_iri: dict[str, dict[str, str]] = {iri: dict(row) for iri, row in existing_manual.items()}
        for row in enriched_rows:
            iri = row.get("class_iri", "")
            if not iri:
                continue
            manual_by_iri[iri] = manual_script.merge_rows(existing_manual.get(iri, {}), manual_script.prefill_row(row))

        target = self._select_review_target(enriched_rows, manual_by_iri, args)
        if not target:
            print("No matching class found for review.")
            return

        iri = target["class_iri"]
        manual_row = manual_by_iri[iri]
        evidence = self._class_module_evidence(iri)
        self._print_review_header(target, manual_row, evidence)

        if not self._confirm("Review this class now?", default=True):
            print("No changes written.")
            return

        updated = dict(manual_row)
        for section_title, fields in REVIEW_PROMPT_SECTIONS:
            print("\n" + "-" * 88)
            print(section_title)
            print("-" * 88)
            for field in fields:
                if field == "reviewer" and args.reviewer and not updated.get(field):
                    updated[field] = args.reviewer
                if field == "review_date" and not updated.get(field):
                    updated[field] = args.review_date or datetime.now().date().isoformat()
                updated[field] = self._prompt_field(field, updated.get(field, ""), target, evidence, updated)

        manual_by_iri[iri] = updated
        self._write_manual_annotations(enriched_rows, manual_by_iri)
        print(f"\nSaved review annotations for:\n  {iri}")

        if not args.no_export_after_review:
            self.export_review_ontology(args)

    def _select_review_target(
        self,
        enriched_rows: list[dict[str, str]],
        manual_by_iri: dict[str, dict[str, str]],
        args: argparse.Namespace,
    ) -> dict[str, str] | None:
        if args.class_iri:
            return next((row for row in enriched_rows if row.get("class_iri") == args.class_iri), None)
        if args.search_text:
            needle = args.search_text.casefold()
            matches = [
                row for row in enriched_rows
                if needle in " ".join([
                    row.get("class_iri", ""),
                    row.get("preferred_label", ""),
                    row.get("ontology", ""),
                    row.get("source_ontology_ids", ""),
                    row.get("definition", ""),
                ]).casefold()
            ]
            self._print_target_matches(matches[:20], manual_by_iri)
            if not matches:
                return None
            choice = input("Select number, exact class IRI, or Enter for first match: ").strip()
            if not choice:
                return matches[0]
            if choice.isdigit() and 1 <= int(choice) <= min(len(matches), 20):
                return matches[int(choice) - 1]
            return next((row for row in matches if row.get("class_iri") == choice), None)

        for row in enriched_rows:
            manual = manual_by_iri.get(row.get("class_iri", ""), {})
            if not manual.get("quality_decision") or not manual.get("reviewer"):
                return row
        return None

    @staticmethod
    def _print_target_matches(matches: list[dict[str, str]], manual_by_iri: dict[str, dict[str, str]]) -> None:
        if not matches:
            print("No matches.")
            return
        print("\nMatches:")
        for index, row in enumerate(matches, start=1):
            manual = manual_by_iri.get(row.get("class_iri", ""), {})
            status = manual.get("quality_decision") or manual.get("manual_include_status") or "unreviewed"
            print(f"  {index}. {row.get('preferred_label') or '(no label)'} [{row.get('ontology')}] - {status}")
            print(f"     {row.get('class_iri')}")

    def _write_manual_annotations(self, enriched_rows: list[dict[str, str]], manual_by_iri: dict[str, dict[str, str]]) -> None:
        ordered_rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in enriched_rows:
            iri = row.get("class_iri", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)
            ordered_rows.append({field: manual_by_iri.get(iri, {}).get(field, "") for field in manual_script.FIELDNAMES})
        for iri, row in sorted(manual_by_iri.items()):
            if iri not in seen:
                ordered_rows.append({field: row.get(field, "") for field in manual_script.FIELDNAMES})
        write_csv_rows(self.config.manual_csv, ordered_rows, manual_script.FIELDNAMES)

    def _class_module_evidence(self, class_iri: str) -> dict[str, list[str]]:
        evidence = {"labels": [], "definitions": [], "comments": [], "synonyms": [], "parents": [], "module_paths": []}
        for module_path in self._all_hierarchy_module_paths():
            try:
                text = module_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if f"<{class_iri}>" not in text:
                continue
            module_triples = self._parse_simple_ttl_triples(text)
            labels_by_iri: dict[str, str] = {}
            for subject, predicate, obj, object_is_iri in module_triples:
                if predicate == RDFS_LABEL and not object_is_iri:
                    labels_by_iri.setdefault(subject, obj)
            for subject, predicate, obj, object_is_iri in module_triples:
                if subject != class_iri:
                    continue
                if predicate == RDFS_LABEL and not object_is_iri:
                    evidence["labels"].append(obj)
                elif predicate == IAO_DEFINITION and not object_is_iri:
                    evidence["definitions"].append(obj)
                elif predicate == RDFS_COMMENT and not object_is_iri:
                    evidence["comments"].append(obj)
                elif predicate == SKOS_ALT_LABEL and not object_is_iri:
                    evidence["synonyms"].append(obj)
                elif predicate == RDFS_SUBCLASS_OF and object_is_iri:
                    parent_label = labels_by_iri.get(obj, "")
                    evidence["parents"].append(f"{parent_label} <{obj}>" if parent_label else f"<{obj}>")
            evidence["module_paths"].append(str(module_path))
        return {key: list(dict.fromkeys(values)) for key, values in evidence.items()}

    def _all_hierarchy_module_paths(self) -> list[Path]:
        module_dirs = [
            self.config.bioportal_module_dir,
            self.config.ols_module_dir,
            self.config.obo_module_dir,
            self.config.fallback_module_dir,
        ]
        paths: list[Path] = []
        for module_dir in module_dirs:
            if module_dir.exists():
                paths.extend(sorted(module_dir.glob("*.ttl")))
        return paths

    @staticmethod
    def _parse_simple_ttl_triples(text: str) -> list[tuple[str, str, str, bool]]:
        triples: list[tuple[str, str, str, bool]] = []
        pattern = re.compile(r'^<([^>]+)>\s+<([^>]+)>\s+(<([^>]+)>|"(.*)")\s*\.\s*$', re.MULTILINE)
        for match in pattern.finditer(text):
            subject = match.group(1)
            predicate = match.group(2)
            if match.group(4) is not None:
                triples.append((subject, predicate, match.group(4), True))
            else:
                literal_text = '"' + (match.group(5) or "") + '"'
                try:
                    obj = json.loads(literal_text)
                except json.JSONDecodeError:
                    obj = match.group(5) or ""
                triples.append((subject, predicate, obj, False))
        return triples

    def _print_review_header(self, row: dict[str, str], manual: dict[str, str], evidence: dict[str, list[str]]) -> None:
        print("\n" + "=" * 88)
        print("CLASS TO REVIEW")
        print("=" * 88)
        self._print_block("IRI", [row.get("class_iri", "")])
        self._print_block("Search term / matched concept", [
            f"search term: {row.get('term', '')}",
            f"preferred label: {row.get('preferred_label', '')}",
        ])
        self._print_block("Label", evidence["labels"] or [row.get("preferred_label", "")])
        self._print_block("Source", [
            f"{row.get('ontology', '')}: {row.get('ontology_title', '')}",
            f"native guess: {row.get('native_ontology_guess', '')} / {row.get('native_term_status', '')}",
        ])
        self._print_block("Current/manual defaults", [
            f"{field}: {manual.get(field, '')}"
            for field in REVIEW_PROMPT_FIELDS
            if manual.get(field, "")
        ] or ["(none)"], max_items=8)

    @staticmethod
    def _row_parent_lines(row: dict[str, str]) -> list[str]:
        parent_iris = split_semicolon(row.get("parent_iris", ""))
        parent_labels = split_semicolon(row.get("parent_labels", ""))
        lines = []
        for index, parent_iri in enumerate(parent_iris):
            label = parent_labels[index] if index < len(parent_labels) else ""
            lines.append(f"{label} <{parent_iri}>" if label else f"<{parent_iri}>")
        return lines

    @staticmethod
    def _print_block(title: str, values: list[str], max_items: int = 12) -> None:
        print(f"\n{title}:")
        for value in values[:max_items]:
            text = str(value or "").strip()
            if len(text) > 900:
                text = text[:897] + "..."
            print(f"  - {text}")
        if len(values) > max_items:
            print(f"  ... {len(values) - max_items} more")

    @staticmethod
    def _confirm(question: str, *, default: bool) -> bool:
        suffix = "Y/n" if default else "y/N"
        answer = input(f"{question} [{suffix}] ").strip().lower()
        if not answer:
            return default
        return answer in {"y", "yes"}

    def _prompt_field(
        self,
        field: str,
        current: str,
        row: dict[str, str],
        evidence: dict[str, list[str]],
        manual: dict[str, str],
    ) -> str:
        values = CONTROLLED_VALUES.get(field)
        guidance = PROMPT_GUIDANCE.get(field, "")
        if values:
            print(f"\n{FIELD_LABELS.get(field, field)} ({field})")
            if guidance:
                print(f"  {guidance}")
            self._print_prompt_evidence(field, row, evidence, manual)
            for index, value in enumerate(values, start=1):
                label = "(blank)" if value == "" else value
                default_marker = " [current]" if value == current else ""
                print(f"  {index}. {label}{default_marker}")
            answer = input(f"Choose number/value, Enter keeps {current or '(blank)'}: ").strip()
            if not answer:
                return current
            if answer.isdigit() and 1 <= int(answer) <= len(values):
                return values[int(answer) - 1]
            if answer in values:
                return answer
            print(f"  Invalid value for {field}; keeping current.")
            return current
        print(f"\n{FIELD_LABELS.get(field, field)} ({field})")
        if guidance:
            print(f"  {guidance}")
        self._print_prompt_evidence(field, row, evidence, manual)
        answer = input(f"Enter text, Enter keeps {current or 'blank'}: ").strip()
        return current if answer == "" else answer

    def _print_prompt_evidence(
        self,
        field: str,
        row: dict[str, str],
        evidence: dict[str, list[str]],
        manual: dict[str, str],
    ) -> None:
        lines = self._prompt_evidence_lines(field, row, evidence, manual)
        if lines:
            self._print_block("Evidence for this question", lines, max_items=8)

    def _prompt_evidence_lines(
        self,
        field: str,
        row: dict[str, str],
        evidence: dict[str, list[str]],
        manual: dict[str, str],
    ) -> list[str]:
        definitions = evidence["definitions"] or split_semicolon(row.get("definition", ""))
        comments = evidence["comments"] or split_semicolon(row.get("comments", ""))
        parents = evidence["parents"] or self._row_parent_lines(row)
        base_identity = [
            f"search term: {row.get('term', '')}",
            f"label: {row.get('preferred_label', '')}",
            f"IRI: {row.get('class_iri', '')}",
        ]
        source_context = [
            f"ontology: {row.get('ontology', '')}",
            f"source_ontology_ids: {row.get('source_ontology_ids', '')}",
            f"source databases: {row.get('source_databases', '')}",
            f"ontology title: {row.get('ontology_title', '')}",
            f"ontology status: {row.get('ontology_status', '')}",
            f"scope category: {row.get('ontology_scope_category', '')}",
            f"exclusion status: {row.get('ontology_exclusion_status', '')} {row.get('ontology_exclusion_reason', '')}",
        ]
        native_context = [
            f"native guess: {row.get('native_ontology_guess', '')}",
            f"native term status: {row.get('native_term_status', '')}",
            f"resolving modules: {'; '.join(evidence['module_paths']) or '(none)'}",
        ]
        extraction_hints = [
            f"bfo_anchor: {row.get('bfo_anchor', '')}",
            f"manual_screening_hint: {row.get('manual_screening_hint', '')}",
            f"mapping_count: {row.get('mapping_count', '')}",
        ]
        provenance = [
            f"source_urls: {row.get('source_urls', '')}",
            f"ontology_versions: {row.get('ontology_versions', '')}",
            f"resolving modules: {'; '.join(evidence['module_paths']) or '(none)'}",
        ]
        current_review = [
            f"{name}: {manual.get(name, '')}"
            for name in REVIEW_PROMPT_FIELDS
            if manual.get(name, "") and name != field
        ]

        if field == "ontology_type_manual":
            return self._nonblank(source_context)
        if field == "native_or_imported_manual":
            return self._nonblank(base_identity + source_context[:3] + native_context)
        if field in {"manual_include_status", "manual_exclusion_reason", "manual_exclusion_detail"}:
            return self._nonblank(base_identity + source_context + extraction_hints + definitions[:2] + parents[:3])
        if field in {"disease_model_category", "upper_level_interpretation"}:
            return self._nonblank(base_identity + extraction_hints + definitions[:3] + parents[:6])
        if field == "definition_quality":
            return self._nonblank(definitions or ["(no definition found)"])
        if field == "comment_quality":
            return self._nonblank(comments or ["(no comments found)"])
        if field == "parentage_quality":
            return self._nonblank(extraction_hints[:1] + (parents or ["(no parent found)"]))
        if field == "provenance_quality":
            return self._nonblank(provenance)
        if field in {"entity_quality_score", "quality_decision", "review_notes"}:
            return self._nonblank(current_review[:8] + definitions[:2] + parents[:3])
        return []

    @staticmethod
    def _nonblank(values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            text = str(value or "").strip()
            if not text:
                continue
            if text.endswith(":"):
                continue
            cleaned.append(text)
        return cleaned

    def review_ui(self, args: argparse.Namespace) -> None:
        pipeline = self

        class ReviewUiHandler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *log_args: Any) -> None:
                print(f"[review-ui] {self.address_string()} - {fmt % log_args}")

            def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _send_json(self, payload: Any, status: int = 200) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8", status)

            def do_GET(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                try:
                    if parsed.path in {"/", "/index.html"}:
                        self._send(pipeline._review_ui_html().encode("utf-8"), "text/html; charset=utf-8")
                    elif parsed.path == "/api/config":
                        self._send_json(pipeline._review_ui_config())
                    elif parsed.path == "/api/classes":
                        search = query.get("search", [""])[0]
                        status_filter = query.get("status", ["todo"])[0]
                        self._send_json(pipeline._review_ui_class_summaries(search, status_filter, args))
                    elif parsed.path == "/api/class":
                        iri = query.get("iri", [""])[0]
                        payload = pipeline._review_ui_class_payload(iri, args)
                        self._send_json(payload if payload else {"error": "class not found"}, 200 if payload else 404)
                    elif parsed.path == "/api/health":
                        self._send_json({"ok": True})
                    else:
                        self._send_json({"error": "not found"}, 404)
                except Exception as exc:  # keep the browser from swallowing tracebacks silently
                    self._send_json({"error": str(exc)}, 500)

            def do_POST(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                    if parsed.path == "/api/save":
                        self._send_json(pipeline._review_ui_save(data, args))
                    else:
                        self._send_json({"error": "not found"}, 404)
                except Exception as exc:
                    self._send_json({"error": str(exc)}, 500)

        server = ThreadingHTTPServer((args.host, args.port), ReviewUiHandler)
        url = f"http://{args.host}:{args.port}/"
        print(f"Review UI running at {url}")
        print("Press Ctrl+C to stop the review UI.")
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping review UI.")
        finally:
            server.server_close()

    def _review_ui_rows_and_manual(
        self,
        args: argparse.Namespace,
    ) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
        rows = self._review_export_rows(read_csv_rows(self.config.enriched_csv))
        if args.limit_rows:
            rows = rows[: args.limit_rows]
        existing_manual = manual_script.load_existing(self.config.manual_csv)
        manual_by_iri: dict[str, dict[str, str]] = {iri: dict(row) for iri, row in existing_manual.items()}
        for row in rows:
            iri = row.get("class_iri", "")
            if not iri:
                continue
            manual_by_iri[iri] = manual_script.merge_rows(existing_manual.get(iri, {}), manual_script.prefill_row(row))
        return rows, manual_by_iri

    def _review_ui_config(self) -> dict[str, Any]:
        return {
            "controlledValues": CONTROLLED_VALUES,
            "promptSections": [{"title": title, "fields": fields} for title, fields in REVIEW_PROMPT_SECTIONS],
            "promptGuidance": PROMPT_GUIDANCE,
            "fieldLabels": FIELD_LABELS,
            "manualFields": manual_script.FIELDNAMES,
            "defaultReviewer": os.environ.get("USER", ""),
            "today": datetime.now().date().isoformat(),
            "manualCsv": str(self.config.manual_csv),
            "reviewOntologyTtl": str(self.config.review_ontology_ttl),
        }

    def _review_ui_class_summaries(
        self,
        search: str,
        status_filter: str,
        args: argparse.Namespace,
    ) -> dict[str, Any]:
        rows, manual_by_iri = self._review_ui_rows_and_manual(args)
        seen: set[str] = set()
        search_text = search.casefold().strip()
        summaries = []
        for row in rows:
            iri = row.get("class_iri", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)
            manual = manual_by_iri.get(iri, {})
            if search_text and search_text not in self._review_ui_search_blob(row, manual):
                continue
            reviewed = bool(manual.get("quality_decision") and manual.get("reviewer"))
            excluded = manual.get("quality_decision") == "exclude" or manual.get("manual_include_status") == "exclude"
            if status_filter == "todo" and reviewed:
                continue
            if status_filter == "reviewed" and not reviewed:
                continue
            if status_filter == "excluded" and not excluded:
                continue
            summaries.append({
                "iri": iri,
                "label": row.get("preferred_label", ""),
                "term": row.get("term", ""),
                "ontology": row.get("ontology", ""),
                "ontologyTitle": row.get("ontology_title", ""),
                "status": manual.get("quality_decision") or manual.get("manual_include_status") or "unreviewed",
                "reviewed": reviewed,
                "excluded": excluded,
            })
        return {"classes": summaries, "count": len(summaries)}

    @staticmethod
    def _review_ui_search_blob(row: dict[str, str], manual: dict[str, str]) -> str:
        values = [
            row.get("class_iri", ""),
            row.get("preferred_label", ""),
            row.get("term", ""),
            row.get("ontology", ""),
            row.get("ontology_title", ""),
            row.get("source_ontology_ids", ""),
            row.get("definition", ""),
            manual.get("quality_decision", ""),
            manual.get("manual_include_status", ""),
        ]
        return " ".join(values).casefold()

    def _review_ui_class_payload(self, iri: str, args: argparse.Namespace) -> dict[str, Any] | None:
        rows, manual_by_iri = self._review_ui_rows_and_manual(args)
        row = next((item for item in rows if item.get("class_iri") == iri), None)
        if not row:
            return None
        manual = manual_by_iri.get(iri, {})
        evidence = self._class_module_evidence(iri)
        evidence_by_field = {
            field: self._prompt_evidence_lines(field, row, evidence, manual)
            for field in REVIEW_PROMPT_FIELDS
        }
        return {
            "row": row,
            "manual": {field: manual.get(field, "") for field in manual_script.FIELDNAMES},
            "evidenceByField": evidence_by_field,
            "modulePaths": evidence.get("module_paths", []),
        }

    def _review_ui_save(self, data: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
        iri = str(data.get("iri", "")).strip()
        annotations = data.get("annotations", {})
        if not iri or not isinstance(annotations, dict):
            raise ValueError("Save request needs iri and annotations.")
        rows, manual_by_iri = self._review_ui_rows_and_manual(args)
        row = next((item for item in rows if item.get("class_iri") == iri), None)
        if not row:
            raise ValueError(f"Class not found in current review export rows: {iri}")

        updated = dict(manual_by_iri.get(iri, {}))
        updated["class_iri"] = iri
        updated["term"] = row.get("term", "")
        updated["preferred_label"] = row.get("preferred_label", "")
        updated["source_ontology_ids"] = row.get("source_ontology_ids", "")
        for field in manual_script.FIELDNAMES:
            if field in annotations:
                updated[field] = str(annotations.get(field, "") or "")

        manual_by_iri[iri] = updated
        self._write_manual_annotations(rows, manual_by_iri)
        exported = False
        if bool(data.get("export", True)) and not args.no_export_after_review:
            self.export_review_ontology(args)
            exported = True
        return {
            "ok": True,
            "iri": iri,
            "exported": exported,
            "manualCsv": str(self.config.manual_csv),
            "reviewOntologyTtl": str(self.config.review_ontology_ttl),
        }

    @staticmethod
    def _review_ui_html() -> str:
        return r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Disease Ontology Review</title>
  <style>
    :root {
      --bg: #f6f5f1;
      --panel: #ffffff;
      --ink: #22252b;
      --muted: #6f7480;
      --line: #d9d8d2;
      --accent: #1f6f63;
      --accent-strong: #14574d;
      --warn: #a66b20;
      --soft: #eef4f1;
      --soft-warm: #f7efe3;
      --focus: #6b8cff;
      --danger: #9b3333;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button, input, select, textarea { font: inherit; }
    .app {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr);
    }
    aside {
      border-right: 1px solid var(--line);
      background: #fbfaf7;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }
    header {
      padding: 18px 18px 14px;
      border-bottom: 1px solid var(--line);
    }
    h1 {
      margin: 0 0 4px;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .subtle { color: var(--muted); font-size: 12px; }
    .filters {
      padding: 14px;
      display: grid;
      gap: 10px;
      border-bottom: 1px solid var(--line);
    }
    .search-row {
      display: grid;
      grid-template-columns: 1fr 112px;
      gap: 8px;
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      color: var(--ink);
      padding: 9px 10px;
      min-height: 38px;
    }
    textarea {
      min-height: 76px;
      resize: vertical;
    }
    input:focus, select:focus, textarea:focus {
      outline: 2px solid color-mix(in srgb, var(--focus) 42%, transparent);
      border-color: var(--focus);
    }
    .class-list {
      overflow: auto;
      padding: 8px;
    }
    .class-item {
      width: 100%;
      text-align: left;
      border: 1px solid transparent;
      background: transparent;
      border-radius: 8px;
      padding: 10px;
      margin: 2px 0;
      cursor: pointer;
      color: var(--ink);
    }
    .class-item:hover { background: var(--soft); }
    .class-item.active {
      background: #e6f0ec;
      border-color: #b9d3cb;
    }
    .class-label {
      font-weight: 700;
      overflow-wrap: anywhere;
    }
    .class-meta {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }
    .tag {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 2px 7px;
      border-radius: 999px;
      background: #ecebe6;
      color: #4f545d;
    }
    .tag.reviewed { background: #e4f0dc; color: #355d2d; }
    .tag.excluded { background: #f3dddd; color: var(--danger); }
    main {
      min-width: 0;
      display: flex;
      flex-direction: column;
    }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 5;
      background: rgba(246,245,241,.96);
      border-bottom: 1px solid var(--line);
      padding: 14px 22px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: center;
      backdrop-filter: blur(8px);
    }
    .title-block h2 {
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }
    .source-line {
      color: var(--muted);
      margin-top: 4px;
      overflow-wrap: anywhere;
    }
    .actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    button.primary, button.secondary {
      min-height: 38px;
      border-radius: 7px;
      padding: 8px 12px;
      border: 1px solid transparent;
      cursor: pointer;
      font-weight: 650;
    }
    button.primary {
      background: var(--accent);
      color: white;
    }
    button.primary:hover { background: var(--accent-strong); }
    button.secondary {
      background: #fff;
      color: var(--ink);
      border-color: var(--line);
    }
    button.secondary:hover { background: var(--soft-warm); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .export-toggle {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }
    .export-toggle input {
      width: 16px;
      min-height: 16px;
      padding: 0;
    }
    .content {
      padding: 18px 22px 42px;
      max-width: 1180px;
      width: 100%;
    }
    .empty {
      margin: 40px auto;
      max-width: 520px;
      color: var(--muted);
      text-align: center;
    }
    .identity {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .identity div {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      min-width: 0;
    }
    .identity b {
      display: block;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .04em;
      margin-bottom: 4px;
    }
    .identity span { overflow-wrap: anywhere; }
    .section {
      margin-top: 16px;
      border-top: 2px solid #c9d9d3;
      padding-top: 10px;
    }
    .section h3 {
      margin: 0 0 8px;
      font-size: 15px;
      color: #243b36;
    }
    .field {
      display: grid;
      grid-template-columns: minmax(235px, .72fr) minmax(360px, 1.28fr);
      gap: 14px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      margin: 10px 0;
    }
    .question label {
      display: block;
      font-weight: 750;
      margin-bottom: 6px;
      overflow-wrap: anywhere;
    }
    .guidance {
      color: var(--muted);
      font-size: 13px;
    }
    .answer {
      display: grid;
      gap: 10px;
      align-content: start;
      min-width: 0;
    }
    .evidence {
      background: #f8faf8;
      border: 1px solid #dfe7e2;
      border-radius: 8px;
      padding: 10px 12px;
      min-width: 0;
    }
    .evidence-title {
      font-size: 11px;
      color: #547168;
      text-transform: uppercase;
      letter-spacing: .05em;
      font-weight: 800;
      margin-bottom: 6px;
    }
    .evidence ul {
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 5px;
    }
    .evidence li {
      overflow-wrap: anywhere;
      color: #343941;
    }
    .statusbar {
      min-height: 24px;
      color: var(--muted);
      font-size: 13px;
      padding-top: 3px;
    }
    .statusbar.error { color: var(--danger); }
    @media (max-width: 900px) {
      .app { grid-template-columns: 1fr; }
      aside { min-height: auto; max-height: 44vh; border-right: 0; border-bottom: 1px solid var(--line); }
      .topbar { grid-template-columns: 1fr; }
      .actions { justify-content: flex-start; }
      .field, .identity { grid-template-columns: 1fr; }
      .content { padding: 14px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <header>
        <h1>Class Review</h1>
        <div class="subtle" id="class-count">Loading classes...</div>
      </header>
      <div class="filters">
        <div class="search-row">
          <input id="search" type="search" placeholder="Search term, class, ontology">
          <select id="status-filter">
            <option value="todo">To review</option>
            <option value="reviewed">Reviewed</option>
            <option value="excluded">Excluded</option>
            <option value="all">All</option>
          </select>
        </div>
      </div>
      <div class="class-list" id="class-list"></div>
    </aside>
    <main>
      <div class="topbar">
        <div class="title-block">
          <h2 id="class-title">Choose a class</h2>
          <div class="source-line" id="class-source">The review form will appear here.</div>
        </div>
        <div class="actions">
          <label class="export-toggle"><input id="export-after-save" type="checkbox" checked> regenerate TTL</label>
          <button class="secondary" id="save">Save</button>
          <button class="primary" id="save-next">Save + next</button>
        </div>
      </div>
      <div class="content" id="content">
        <div class="empty">Select a class from the left list.</div>
      </div>
    </main>
  </div>
  <script>
    let config = null;
    let classList = [];
    let selectedIri = "";
    let currentPayload = null;
    let pendingSearchTimer = null;

    const $ = (id) => document.getElementById(id);

    async function requestJson(url, options = {}) {
      const response = await fetch(url, options);
      const payload = await response.json();
      if (!response.ok || payload.error) throw new Error(payload.error || response.statusText);
      return payload;
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;"
      }[char]));
    }

    function shortIri(iri) {
      if (!iri) return "";
      const parts = iri.split(/[\/#]/).filter(Boolean);
      return parts[parts.length - 1] || iri;
    }

    function statusTag(item) {
      const cls = item.excluded ? "excluded" : item.reviewed ? "reviewed" : "";
      return `<span class="tag ${cls}">${escapeHtml(item.status || "unreviewed")}</span>`;
    }

    async function loadClasses(keepSelection = true) {
      const search = encodeURIComponent($("search").value.trim());
      const status = encodeURIComponent($("status-filter").value);
      const payload = await requestJson(`/api/classes?search=${search}&status=${status}`);
      classList = payload.classes || [];
      $("class-count").textContent = `${payload.count} class${payload.count === 1 ? "" : "es"}`;
      renderClassList();
      if (!classList.length) {
        selectedIri = "";
        currentPayload = null;
        renderEmpty("No classes match the current filter.");
        return;
      }
      if (!keepSelection || !classList.some((item) => item.iri === selectedIri)) {
        await loadClass(classList[0].iri);
      }
    }

    function renderClassList() {
      $("class-list").innerHTML = classList.map((item) => `
        <button class="class-item ${item.iri === selectedIri ? "active" : ""}" data-iri="${escapeHtml(item.iri)}">
          <div class="class-label">${escapeHtml(item.label || shortIri(item.iri))}</div>
          <div class="class-meta">
            <span class="tag">${escapeHtml(item.term || "no term")}</span>
            <span class="tag">${escapeHtml(item.ontology || "no ontology")}</span>
            ${statusTag(item)}
          </div>
        </button>
      `).join("");
      document.querySelectorAll(".class-item").forEach((button) => {
        button.addEventListener("click", () => loadClass(button.dataset.iri));
      });
    }

    async function loadClass(iri) {
      selectedIri = iri;
      currentPayload = await requestJson(`/api/class?iri=${encodeURIComponent(iri)}`);
      renderClassList();
      renderClass(currentPayload);
    }

    function renderEmpty(message) {
      $("class-title").textContent = "Choose a class";
      $("class-source").textContent = "";
      $("content").innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
    }

    function renderClass(payload) {
      const row = payload.row || {};
      const manual = payload.manual || {};
      $("class-title").textContent = row.preferred_label || shortIri(row.class_iri);
      $("class-source").textContent = `${row.term || ""} · ${row.ontology || ""} · ${row.ontology_title || ""}`;

      const identity = `
        <div class="identity">
          <div><b>Search term</b><span>${escapeHtml(row.term || "")}</span></div>
          <div><b>Ontology</b><span>${escapeHtml(row.ontology || "")}</span></div>
          <div><b>Native guess</b><span>${escapeHtml((row.native_ontology_guess || "") + " / " + (row.native_term_status || ""))}</span></div>
        </div>
      `;
      const sections = config.promptSections.map((section) => `
        <section class="section">
          <h3>${escapeHtml(section.title)}</h3>
          ${section.fields.map((field) => renderField(field, manual[field] || "", payload.evidenceByField[field] || [])).join("")}
        </section>
      `).join("");
      $("content").innerHTML = identity + sections + `<div class="statusbar" id="statusbar"></div>`;
    }

    function renderField(field, value, evidence) {
      const label = (config.fieldLabels && config.fieldLabels[field]) || field;
      return `
        <div class="field" data-field="${escapeHtml(field)}">
          <div class="question">
            <label for="field-${escapeHtml(field)}">${escapeHtml(label)}</label>
            <div class="subtle">${escapeHtml(field)}</div>
            <div class="guidance">${escapeHtml(config.promptGuidance[field] || "")}</div>
          </div>
          <div class="answer">
            ${renderEvidence(evidence)}
            ${renderControl(field, value)}
          </div>
        </div>
      `;
    }

    function renderEvidence(lines) {
      if (!lines || !lines.length) return "";
      return `
        <div class="evidence">
          <div class="evidence-title">Evidence for this question</div>
          <ul>${lines.slice(0, 8).map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>
        </div>
      `;
    }

    function renderControl(field, value) {
      const controlled = config.controlledValues[field];
      if (controlled) {
        const options = ["", ...controlled.filter((item) => item !== "")];
        return `<select id="field-${escapeHtml(field)}" data-field="${escapeHtml(field)}">
          ${options.map((option) => `<option value="${escapeHtml(option)}" ${option === value ? "selected" : ""}>${escapeHtml(option || "(blank)")}</option>`).join("")}
        </select>`;
      }
      if (field === "review_date") {
        return `<input id="field-${escapeHtml(field)}" data-field="${escapeHtml(field)}" type="date" value="${escapeHtml(value || config.today)}">`;
      }
      if (field === "reviewer") {
        return `<input id="field-${escapeHtml(field)}" data-field="${escapeHtml(field)}" value="${escapeHtml(value || config.defaultReviewer || "")}">`;
      }
      return `<textarea id="field-${escapeHtml(field)}" data-field="${escapeHtml(field)}">${escapeHtml(value || "")}</textarea>`;
    }

    function collectAnnotations() {
      const annotations = {};
      document.querySelectorAll("[data-field]").forEach((control) => {
        if (control.matches("select,input,textarea")) annotations[control.dataset.field] = control.value;
      });
      return annotations;
    }

    function setStatus(message, isError = false) {
      const node = $("statusbar");
      if (!node) return;
      node.textContent = message;
      node.className = `statusbar${isError ? " error" : ""}`;
    }

    async function saveReview(goNext = false) {
      if (!selectedIri) return;
      const savedIri = selectedIri;
      $("save").disabled = true;
      $("save-next").disabled = true;
      setStatus("Saving...");
      try {
        const payload = await requestJson("/api/save", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            iri: selectedIri,
            annotations: collectAnnotations(),
            export: $("export-after-save").checked
          })
        });
        setStatus(payload.exported ? "Saved and regenerated TTL." : "Saved manual annotations.");
        await loadClasses(true);
        if (goNext && classList.length) {
          const savedIndex = classList.findIndex((item) => item.iri === savedIri);
          const next = classList[savedIndex + 1] || classList[0];
          if (next) await loadClass(next.iri);
        } else if (classList.some((item) => item.iri === savedIri)) {
          await loadClass(savedIri);
        }
      } catch (error) {
        setStatus(error.message, true);
      } finally {
        $("save").disabled = false;
        $("save-next").disabled = false;
      }
    }

    $("search").addEventListener("input", () => {
      clearTimeout(pendingSearchTimer);
      pendingSearchTimer = setTimeout(() => loadClasses(false).catch((error) => renderEmpty(error.message)), 180);
    });
    $("status-filter").addEventListener("change", () => loadClasses(false).catch((error) => renderEmpty(error.message)));
    $("save").addEventListener("click", () => saveReview(false));
    $("save-next").addEventListener("click", () => saveReview(true));

    (async function init() {
      try {
        config = await requestJson("/api/config");
        await loadClasses(false);
      } catch (error) {
        renderEmpty(error.message);
      }
    })();
  </script>
</body>
</html>
"""

    def export_source_appearance_report(self, args: argparse.Namespace) -> None:
        rows = self._review_export_rows(read_csv_rows(self.config.enriched_csv))
        detail_rows: list[dict[str, str]] = []
        summary: dict[tuple[str, str], dict[str, Any]] = {}

        title_by_ontology = self._ontology_title_index(rows)

        for row in rows:
            class_iri = row.get("class_iri", "")
            native_guess = row.get("native_ontology_guess") or terms_script.infer_native_ontology_guess(class_iri)
            native_key = terms_script.normalise_ontology_id_for_dependency(native_guess)
            records = parse_source_records(row) or [{"source": "", "ontology": row.get("ontology", "")}]
            for record in records:
                source = str(record.get("source", "")).strip()
                ontology = str(record.get("ontology", "")).strip()
                if not ontology:
                    continue
                ontology_key = terms_script.normalise_ontology_id_for_dependency(ontology)
                if not native_key:
                    route = "unknown_namespace_needs_manual_check"
                    depends_on = ""
                    class_taken_from = ""
                    independent_analysis = "check"
                elif ontology_key == native_key:
                    route = "native_independent_class_definition"
                    depends_on = ""
                    class_taken_from = ontology
                    independent_analysis = "yes"
                else:
                    route = "imported_dependency_no_independent_analysis"
                    depends_on = native_guess
                    class_taken_from = native_guess
                    independent_analysis = "no"

                detail = {
                    "source_database": source,
                    "source_ontology_id": ontology,
                    "source_ontology_title": title_by_ontology.get(ontology.upper(), ""),
                    "term": row.get("term", ""),
                    "class_iri": class_iri,
                    "preferred_label": row.get("preferred_label", ""),
                    "native_ontology_guess": native_guess,
                    "native_ontology_resolution_basis": row.get("native_ontology_resolution_basis", ""),
                    "appearance_route": route,
                    "class_taken_from_ontology_id": class_taken_from,
                    "depends_on_ontology_id": depends_on,
                    "independent_analysis_required": independent_analysis,
                    "source_url": str(record.get("source_url", "")),
                    "ontology_version": str(record.get("ontology_version", "")),
                    "recommendation": self._appearance_recommendation(route, depends_on),
                }
                detail_rows.append(detail)

                key = (source, ontology)
                item = summary.setdefault(
                    key,
                    {
                        "source_database": source,
                        "source_ontology_id": ontology,
                        "source_ontology_title": title_by_ontology.get(ontology.upper(), ""),
                        "terms_seen": set(),
                        "class_iris": set(),
                        "native_class_iris": set(),
                        "imported_class_iris": set(),
                        "unknown_class_iris": set(),
                        "depends_on_ontology_ids": set(),
                    },
                )
                item["terms_seen"].add(row.get("term", ""))
                item["class_iris"].add(class_iri)
                if route == "native_independent_class_definition":
                    item["native_class_iris"].add(class_iri)
                elif route == "imported_dependency_no_independent_analysis":
                    item["imported_class_iris"].add(class_iri)
                    if depends_on:
                        item["depends_on_ontology_ids"].add(depends_on)
                else:
                    item["unknown_class_iris"].add(class_iri)

        summary_rows = []
        for item in summary.values():
            native_n = len(item["native_class_iris"])
            imported_n = len(item["imported_class_iris"])
            unknown_n = len(item["unknown_class_iris"])
            depends_on = "; ".join(sorted(item["depends_on_ontology_ids"]))
            if native_n and imported_n:
                route = "mixed_independent_and_dependency_appearances"
            elif native_n:
                route = "independent_analysis_route"
            elif imported_n and not unknown_n:
                route = "dependency_only_no_independent_analysis"
            else:
                route = "unknown_namespace_needs_manual_check"
            summary_rows.append(
                {
                    "source_database": item["source_database"],
                    "source_ontology_id": item["source_ontology_id"],
                    "source_ontology_title": item["source_ontology_title"],
                    "terms_seen": "; ".join(sorted(x for x in item["terms_seen"] if x)),
                    "class_count": len(item["class_iris"]),
                    "native_class_count": native_n,
                    "imported_dependency_class_count": imported_n,
                    "unknown_namespace_class_count": unknown_n,
                    "depends_on_ontology_ids": depends_on,
                    "ontology_review_route": route,
                    "recommendation": self._appearance_recommendation(route, depends_on),
                    "class_iris": "; ".join(sorted(item["class_iris"])),
                }
            )

        detail_path = self.config.table_dir / "ontology_source_appearance_routes_detail.csv"
        summary_path = self.config.table_dir / "ontology_source_appearance_routes_summary.csv"
        review_table_path = self.config.table_dir / "ontology_term_appearance_review_table.csv"
        detail_fieldnames = [
            "source_database",
            "source_ontology_id",
            "source_ontology_title",
            "term",
            "class_iri",
            "preferred_label",
            "native_ontology_guess",
            "native_ontology_resolution_basis",
            "appearance_route",
            "class_taken_from_ontology_id",
            "depends_on_ontology_id",
            "independent_analysis_required",
            "source_url",
            "ontology_version",
            "recommendation",
        ]
        sorted_detail_rows = sorted(detail_rows, key=lambda r: (r["source_ontology_id"], r["term"], r["preferred_label"], r["class_iri"]))
        write_csv_rows(
            detail_path,
            sorted_detail_rows,
            detail_fieldnames,
        )
        write_csv_rows(
            review_table_path,
            sorted_detail_rows,
            [
                "source_ontology_id",
                "source_ontology_title",
                "term",
                "preferred_label",
                "class_iri",
                "class_taken_from_ontology_id",
                "independent_analysis_required",
                "appearance_route",
                "recommendation",
            ],
        )
        write_csv_rows(
            summary_path,
            sorted(summary_rows, key=lambda r: (r["ontology_review_route"], r["source_ontology_id"])),
            [
                "source_database",
                "source_ontology_id",
                "source_ontology_title",
                "terms_seen",
                "class_count",
                "native_class_count",
                "imported_dependency_class_count",
                "unknown_namespace_class_count",
                "depends_on_ontology_ids",
                "ontology_review_route",
                "recommendation",
                "class_iris",
            ],
        )
        print(f"Wrote source appearance summary -> {summary_path}")
        print(f"Wrote source appearance detail -> {detail_path}")
        print(f"Wrote ontology-term review table -> {review_table_path}")

    def _ontology_title_index(self, rows: list[dict[str, str]]) -> dict[str, str]:
        title_by_id: dict[str, str] = {}
        for row in rows:
            ontology = row.get("ontology", "").upper()
            if ontology and row.get("ontology_title"):
                title_by_id.setdefault(ontology, row["ontology_title"])
        doi_lookup = self.config.table_dir / "ontology_modelling_paper_doi_lookup.json"
        if doi_lookup.exists():
            try:
                data = json.loads(doi_lookup.read_text(encoding="utf-8"))
                for row in data.get("best_rows", []):
                    if row.get("ontology_id") and row.get("ontology_title"):
                        title_by_id.setdefault(str(row["ontology_id"]).upper(), str(row["ontology_title"]))
            except json.JSONDecodeError:
                pass
        return title_by_id

    def _source_ontologies_by_class_iri(self, rows: list[dict[str, str]]) -> dict[str, set[str]]:
        sources_by_iri: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            iri = row.get("class_iri", "")
            if not iri:
                continue
            records = parse_source_records(row) or [{"source": "", "ontology": row.get("ontology", "")}]
            for record in records:
                ontology = str(record.get("ontology", "")).strip()
                if ontology:
                    sources_by_iri[iri].add(ontology)
        return sources_by_iri

    def _resolve_native_ontology_guess(
        self,
        row: dict[str, str],
        sources_by_iri: dict[str, set[str]],
    ) -> tuple[str, str]:
        iri = row.get("class_iri", "")
        existing = terms_script.infer_native_ontology_guess(iri)
        if existing:
            return existing, "standard IRI prefix rule"

        bioportal_match = re.search(r"purl\.bioontology\.org/ontology/([^/]+)/", iri, flags=re.IGNORECASE)
        if bioportal_match:
            namespace = bioportal_match.group(1).upper()
            return BIOPORTAL_NAMESPACE_ALIASES.get(namespace, namespace), "BioPortal ontology namespace"

        for pattern, ontology_id, basis in NATIVE_NAMESPACE_PATTERNS:
            if re.search(pattern, iri, flags=re.IGNORECASE):
                return ontology_id, basis

        source_ontologies = sources_by_iri.get(iri, set())
        normalised_iri = citation_lookup_key(iri)
        for ontology in sorted(source_ontologies, key=lambda value: (-len(value), value.lower())):
            ontology_key = citation_lookup_key(ontology)
            if ontology_key and ontology_key in normalised_iri:
                return ontology, "source ontology ID appears in class IRI"

        if len(source_ontologies) == 1:
            return next(iter(source_ontologies)), "single-source local namespace"

        return "", "ambiguous reused unknown namespace"

    @staticmethod
    def _native_term_status_for_source_set(native_guess: str, source_ontologies: set[str]) -> str:
        if not native_guess:
            return "unknown_native_ontology"
        native_key = citation_lookup_key(native_guess)
        source_keys = {citation_lookup_key(ontology) for ontology in source_ontologies}
        if native_key in source_keys:
            return "native_source_seen_with_imports" if len(source_keys) > 1 else "native_source_seen"
        return "likely_imported_or_reused_term"

    @staticmethod
    def _appearance_recommendation(route: str, depends_on: str) -> str:
        if route in {"dependency_only_no_independent_analysis", "imported_dependency_no_independent_analysis"}:
            return f"List as ontology appearance/reuse only; analyze and cite {depends_on or 'the native source ontology'} instead; do not annotate independently."
        if route == "mixed_independent_and_dependency_appearances":
            return "Review only native disease-model classes independently; treat imported classes as reuse/dependency evidence."
        if route == "independent_analysis_route" or route == "native_independent_class_definition":
            return "Eligible for independent class-level review if otherwise in scope."
        return "Needs manual namespace/provenance check before deciding review route."

    def _citation_workbook_path(self) -> Path | None:
        for path in [self.config.preferred_citation_workbook, self.config.generated_citation_workbook]:
            if path.exists():
                return path
        return None

    def _load_modelling_citations(self) -> dict[str, dict[str, str]]:
        citations: dict[str, dict[str, str]] = {}
        workbook_path = self._citation_workbook_path()
        if workbook_path:
            try:
                manual_decisions = workbook_path == self.config.preferred_citation_workbook
                citations.update(self._load_modelling_citations_from_workbook(workbook_path, manual_decisions=manual_decisions))
            except Exception as exc:
                print(f"  [warn] could not read citation workbook {workbook_path}: {exc}", file=sys.stderr)
        if not citations and self.config.citation_lookup_json.exists():
            try:
                data = json.loads(self.config.citation_lookup_json.read_text(encoding="utf-8"))
                rows = data.get("merged_best_rows", [])
                citations.update(self._citation_lookup_from_rows(rows, source_label=str(self.config.citation_lookup_json), manual_decisions=False))
            except Exception as exc:
                print(f"  [warn] could not read citation lookup JSON {self.config.citation_lookup_json}: {exc}", file=sys.stderr)
        citations.update(self._load_citation_review_overrides())
        return citations

    def _load_citation_review_overrides(self) -> dict[str, dict[str, str]]:
        if not self.config.citation_review_workbook.exists():
            return {}
        try:
            from openpyxl import load_workbook

            workbook = load_workbook(self.config.citation_review_workbook, read_only=True, data_only=True)
            if "Ontologies needing citation" not in workbook.sheetnames:
                return {}
            worksheet = workbook["Ontologies needing citation"]
            rows = worksheet.iter_rows(values_only=True)
            headers = [clean_cell(value) for value in next(rows)]
            records = [
                {headers[index]: clean_cell(value) for index, value in enumerate(row) if index < len(headers)}
                for row in rows
            ]
        except Exception as exc:
            print(f"  [warn] could not read citation review workbook {self.config.citation_review_workbook}: {exc}", file=sys.stderr)
            return {}

        citations: dict[str, dict[str, str]] = {}
        for row in records:
            ontology_id = row.get("Ontology ID", "")
            if not ontology_id:
                continue
            citation = self._normalise_review_citation_row(row, source_label=str(self.config.citation_review_workbook))
            if citation:
                citations[citation_lookup_key(ontology_id)] = citation
        if citations:
            print(f"Loaded {len(citations)} citation override(s) from {self.config.citation_review_workbook}", file=sys.stderr)
        return citations

    def _normalise_review_citation_row(self, row: dict[str, str], *, source_label: str) -> dict[str, str] | None:
        decision = clean_cell(row.get("Certainty assessment", ""))
        decision_key = decision.lower()
        if not decision or decision_key in REJECTED_CITATION_CONFIDENCES:
            return None

        suggested_title = row.get("Suggested paper title", "")
        suggested_doi = self._clean_doi(row.get("Suggested DOI", ""))
        suggested_pmid = row.get("Suggested PMID", "")
        suggested_pmcid = row.get("Suggested PMCID", "")
        suggested_url = row.get("Suggested URL", "")

        if decision_key in MANUAL_ACCEPTED_CITATION_CONFIDENCES or decision_key == "good":
            doi = suggested_doi
            pmid = suggested_pmid
            pmcid = suggested_pmcid
            url = suggested_url or (f"https://doi.org/{doi}" if doi else "")
            citation_text = self._format_review_citation(row, title=suggested_title, doi=doi, pmid=pmid)
            title = suggested_title
        else:
            doi = self._doi_from_text(decision)
            pmid = self._pmid_from_text(decision)
            pmcid = self._pmcid_from_text(decision)
            url = self._url_from_text(decision) or (f"https://doi.org/{doi}" if doi else "")
            title = "" if (doi or pmid or url) else decision
            citation_text = decision
            if doi and not citation_text.lower().startswith(("doi", "http")):
                citation_text = f"doi:{doi}"

        if not citation_text and not doi and not pmid and not url and not title:
            return None
        return {
            "ontology_id": row.get("Ontology ID", ""),
            "confidence": decision,
            "doi": doi,
            "pmid": pmid,
            "pmcid": pmcid,
            "url": url,
            "title": title or suggested_title,
            "bibliographic_citation": citation_text or title or suggested_title,
            "lookup_source": "manual citation-needed workbook",
            "citation_source": source_label,
        }

    @staticmethod
    def _format_review_citation(row: dict[str, str], *, title: str, doi: str, pmid: str) -> str:
        parts = []
        if title:
            parts.append(title.rstrip(".") + ".")
        if row.get("Suggested year"):
            parts.append(f"({row['Suggested year']})")
        if row.get("Suggested venue"):
            parts.append(row["Suggested venue"].rstrip(".") + ".")
        if doi:
            parts.append(f"doi:{doi}")
        elif pmid:
            parts.append(f"PMID:{pmid}")
        return " ".join(parts).strip()

    def _load_modelling_citations_from_workbook(self, path: Path, *, manual_decisions: bool) -> dict[str, dict[str, str]]:
        from openpyxl import load_workbook

        workbook = load_workbook(path, read_only=True, data_only=True)
        if "Merged Best Fit" not in workbook.sheetnames:
            raise ValueError("sheet 'Merged Best Fit' not found")
        worksheet = workbook["Merged Best Fit"]
        rows = worksheet.iter_rows(values_only=True)
        headers = [clean_cell(value) for value in next(rows)]
        records = [
            {headers[index]: clean_cell(value) for index, value in enumerate(row) if index < len(headers)}
            for row in rows
        ]
        return self._citation_lookup_from_rows(records, source_label=str(path), manual_decisions=manual_decisions)

    def _citation_lookup_from_rows(self, rows: list[dict[str, Any]], *, source_label: str, manual_decisions: bool) -> dict[str, dict[str, str]]:
        citations: dict[str, dict[str, str]] = {}
        for raw_row in rows:
            row = {str(key): clean_cell(value) for key, value in raw_row.items()}
            ontology_id = row.get("ontology_id", "")
            if not ontology_id:
                continue
            citation = self._normalise_citation_row(row, source_label=source_label, manual_decisions=manual_decisions)
            if citation:
                citations[citation_lookup_key(ontology_id)] = citation
        return citations

    def _normalise_citation_row(self, row: dict[str, str], *, source_label: str, manual_decisions: bool) -> dict[str, str] | None:
        confidence = self._citation_decision_value(row)
        confidence_key = confidence.strip().lower()
        manual_citation = self._manual_citation_override(confidence)
        accepted_values = MANUAL_ACCEPTED_CITATION_CONFIDENCES if manual_decisions else ACCEPTED_CITATION_CONFIDENCES
        accepted = confidence_key in accepted_values or bool(manual_citation)
        if confidence_key in REJECTED_CITATION_CONFIDENCES and not manual_citation:
            accepted = False
        if not accepted:
            return None

        title = row.get("publication_title", "")
        doi = self._clean_doi(row.get("doi", ""))
        pmid = row.get("pmid", "")
        pmcid = row.get("pmcid", "")
        if manual_citation:
            doi = self._doi_from_text(manual_citation)
            pmid = self._pmid_from_text(manual_citation)
            pmcid = self._pmcid_from_text(manual_citation)
            title = manual_citation
        doi_url = f"https://doi.org/{doi}" if manual_citation and doi else row.get("doi_url", "") or (f"https://doi.org/{doi}" if doi else "")
        url = doi_url or row.get("url", "")
        if manual_citation and not doi:
            url = ""
        bibliographic_citation = manual_citation or self._format_bibliographic_citation(row, doi=doi)
        if not bibliographic_citation and not doi and not url:
            return None
        return {
            "ontology_id": row.get("ontology_id", ""),
            "confidence": confidence,
            "doi": doi,
            "pmid": pmid,
            "pmcid": pmcid,
            "url": url,
            "title": title,
            "bibliographic_citation": bibliographic_citation,
            "lookup_source": row.get("lookup_source", ""),
            "citation_source": source_label,
        }

    @staticmethod
    def _citation_decision_value(row: dict[str, str]) -> str:
        for column in CITATION_DECISION_COLUMNS:
            if row.get(column):
                return row[column]
        return ""

    @staticmethod
    def _manual_citation_override(value: str) -> str:
        text = clean_cell(value)
        lowered = text.lower()
        if not text or lowered in ACCEPTED_CITATION_CONFIDENCES or lowered in REJECTED_CITATION_CONFIDENCES:
            return ""
        if len(text) > 40 and (re.search(r"\b(19|20)\d{2}\b", text) or "doi" in lowered or "pmid" in lowered):
            return text
        return ""

    @staticmethod
    def _clean_doi(value: str) -> str:
        doi = clean_cell(value)
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
        return doi.strip()

    @staticmethod
    def _doi_from_text(value: str) -> str:
        match = re.search(r"(?:doi:\s*|https?://(?:dx\.)?doi\.org/)(10\.\S+)", value, flags=re.IGNORECASE)
        return match.group(1).rstrip(".,;)") if match else ""

    @staticmethod
    def _pmid_from_text(value: str) -> str:
        match = re.search(r"PMID:?\s*(\d+)", value, flags=re.IGNORECASE)
        return match.group(1) if match else ""

    @staticmethod
    def _pmcid_from_text(value: str) -> str:
        match = re.search(r"PMC(?:ID)?:?\s*(PMC\d+|\d+)", value, flags=re.IGNORECASE)
        if not match:
            return ""
        value = match.group(1)
        return value if value.upper().startswith("PMC") else f"PMC{value}"

    @staticmethod
    def _url_from_text(value: str) -> str:
        match = re.search(r"https?://\S+", value)
        return match.group(0).rstrip(".,;)") if match else ""

    @staticmethod
    def _format_bibliographic_citation(row: dict[str, str], *, doi: str) -> str:
        parts = []
        authors = row.get("authors", "")
        year = row.get("year", "")
        title = row.get("publication_title", "")
        venue = row.get("venue", "")
        if authors:
            parts.append(authors)
        if year:
            parts.append(f"({year})")
        if title:
            parts.append(title.rstrip(".") + ".")
        if venue:
            parts.append(venue.rstrip(".") + ".")
        if doi:
            parts.append(f"doi:{doi}")
        elif row.get("pmid"):
            parts.append(f"PMID:{row['pmid']}")
        return " ".join(parts).strip()

    def _native_citation_sources_by_iri(self, rows: list[dict[str, str]]) -> dict[str, list[str]]:
        sources_by_iri: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            term = row.get("term", "").strip().lower()
            iri = row.get("class_iri", "").strip()
            if term not in CITATION_REVIEW_TERMS or not iri:
                continue
            native_guess = row.get("native_ontology_guess") or terms_script.infer_native_ontology_guess(iri)
            native_key = citation_lookup_key(native_guess)
            records = parse_source_records(row) or [{"source": "", "ontology": row.get("ontology", "")}]
            for record in records:
                ontology = str(record.get("ontology", "")).strip()
                if ontology and native_key and citation_lookup_key(ontology) == native_key:
                    sources_by_iri[iri].add(ontology)
            if not sources_by_iri.get(iri) and native_guess and row.get("native_term_status") in {"native_source_seen", "native_source_seen_with_imports"}:
                sources_by_iri[iri].add(native_guess)
        return {iri: sorted(values, key=lambda value: (citation_lookup_key(value), value)) for iri, values in sources_by_iri.items()}

    def _add_modelling_citation_annotations(
        self,
        triples: set[tuple[str, str, str, bool]],
        subject_iri: str,
        source_ids: list[str],
        citations_by_source: dict[str, dict[str, str]],
    ) -> dict[str, str] | None:
        for source_id in source_ids:
            citation = citations_by_source.get(citation_lookup_key(source_id))
            if not citation:
                continue
            self._add_literal(triples, subject_iri, REV + "modelling_citation_source_ontology_id", source_id)
            self._add_literal(triples, subject_iri, DCTERMS_BIBLIOGRAPHIC_CITATION, citation.get("bibliographic_citation", ""))
            self._add_literal(triples, subject_iri, REV + "modelling_citation_doi", citation.get("doi", ""))
            self._add_literal(triples, subject_iri, REV + "modelling_citation_pmid", citation.get("pmid", ""))
            self._add_literal(triples, subject_iri, REV + "modelling_citation_pmcid", citation.get("pmcid", ""))
            self._add_literal(triples, subject_iri, REV + "modelling_citation_url", citation.get("url", ""))
            return {"source_id": source_id, **citation}
        return None

    def _write_citation_coverage_report(self, rows: list[dict[str, str]], citation_sources_by_iri: dict[str, list[str]], citations_by_source: dict[str, dict[str, str]]) -> None:
        report_rows = []
        seen: set[tuple[str, str, str]] = set()
        for row in rows:
            iri = row.get("class_iri", "")
            term = row.get("term", "").strip().lower()
            if term not in CITATION_REVIEW_TERMS or iri not in citation_sources_by_iri:
                continue
            for source_id in citation_sources_by_iri[iri]:
                key = (iri, term, source_id)
                if key in seen:
                    continue
                seen.add(key)
                citation = citations_by_source.get(citation_lookup_key(source_id), {})
                report_rows.append(
                    {
                        "class_iri": iri,
                        "term": term,
                        "preferred_label": row.get("preferred_label", ""),
                        "native_source_ontology_id": source_id,
                        "citation_added_to_review_ttl": "yes" if citation else "no",
                        "doi": citation.get("doi", ""),
                        "pmid": citation.get("pmid", ""),
                        "pmcid": citation.get("pmcid", ""),
                        "publication_title": citation.get("title", ""),
                        "citation_url": citation.get("url", ""),
                        "citation_confidence_or_manual_note": citation.get("confidence", ""),
                        "citation_source": citation.get("citation_source", ""),
                    }
                )
        write_csv_rows(
            self.config.citation_coverage_csv,
            sorted(report_rows, key=lambda r: (r["native_source_ontology_id"].lower(), r["term"], r["class_iri"])),
            [
                "class_iri",
                "term",
                "preferred_label",
                "native_source_ontology_id",
                "citation_added_to_review_ttl",
                "doi",
                "pmid",
                "pmcid",
                "publication_title",
                "citation_url",
                "citation_confidence_or_manual_note",
                "citation_source",
            ],
        )
        added = sum(1 for row in report_rows if row["citation_added_to_review_ttl"] == "yes")
        print(f"Wrote native citation coverage ({added}/{len(report_rows)} cited rows) -> {self.config.citation_coverage_csv}")

    def export_review_ontology(self, args: argparse.Namespace) -> None:
        rows = self._review_export_rows(read_csv_rows(self.config.enriched_csv))
        self._export_review_ontology(
            self.config.review_ontology_ttl,
            ontology_iri="https://example.org/disease-review/extraction",
            rows=rows,
            manual_rows=read_csv_rows(self.config.manual_csv),
            label="Disease ontology scoping review extraction and review annotations",
            include_hierarchy_module_imports=True,
        )

    def _review_export_rows(self, rows: list[dict[str, str]]) -> list[dict[str, str]]:
        filtered = []
        skipped_mesh_duplicates = 0
        webprotege_excluded_rows = []
        valueset_excluded_rows = []
        title_by_ontology = self._ontology_title_index(rows)
        for row in rows:
            if row.get("ontology", "").upper() in DUPLICATE_MESH_ONTOLOGIES:
                skipped_mesh_duplicates += 1
                continue
            if self._is_excluded_valueset_row(row):
                valueset_excluded_rows.append(dict(row))
                continue
            if self._is_excluded_webprotege_row(row):
                webprotege_excluded_rows.append(dict(row))
                continue
            filtered.append(dict(row))
        if skipped_mesh_duplicates:
            print(
                f"Skipped {skipped_mesh_duplicates} duplicate MeSH mirror rows; kept canonical {CANONICAL_MESH_ONTOLOGY}.",
                file=sys.stderr,
            )
        self._write_exclusion_figure_reports(webprotege_excluded_rows, valueset_excluded_rows, title_by_ontology)
        sources_by_iri = self._source_ontologies_by_class_iri(filtered)
        for row in filtered:
            native_guess, basis = self._resolve_native_ontology_guess(row, sources_by_iri)
            row["native_ontology_guess"] = native_guess
            row["native_ontology_resolution_basis"] = basis
            row["native_term_status"] = self._native_term_status_for_source_set(
                native_guess,
                sources_by_iri.get(row.get("class_iri", ""), set()),
            )
        return filtered

    @staticmethod
    def _is_excluded_webprotege_row(row: dict[str, str]) -> bool:
        return EXCLUDED_WEBPROTEGE_IRI_HOST in row.get("class_iri", "").lower()

    @staticmethod
    def _is_excluded_valueset_row(row: dict[str, str]) -> bool:
        ontologies = {row.get("ontology", "").upper()}
        for record in parse_source_records(row):
            ontologies.add(str(record.get("ontology", "")).upper())
        return bool(ontologies & EXCLUDED_VALUESET_ONTOLOGIES)

    def _write_exclusion_figure_reports(
        self,
        webprotege_rows: list[dict[str, str]],
        valueset_rows: list[dict[str, str]],
        title_by_ontology: dict[str, str],
    ) -> None:
        detail_rows: list[dict[str, str]] = []
        exclusion_groups = [
            (
                webprotege_rows,
                "source_ontology_provenance_screen",
                WEBPROTEGE_EXCLUSION_REASON,
                "Discarded because the matched class IRI is a WebProtege-hosted random/local identifier; provenance is unstable for independent ontology-review counting.",
            ),
            (
                valueset_rows,
                "source_ontology_type_screen",
                VALUESET_EXCLUSION_REASON,
                "Discarded because VALUESETS is a value-set collection rather than an independent ontology implementation for disease modelling review.",
            ),
        ]
        for rows, stage, reason_code, reason in exclusion_groups:
            self._add_exclusion_detail_rows(detail_rows, rows, title_by_ontology, stage, reason_code, reason)

        detail_fieldnames = [
            "exclusion_stage",
            "exclusion_reason_code",
            "exclusion_reason",
            "source_database",
            "source_ontology_id",
            "source_ontology_title",
            "term",
            "preferred_label",
            "class_iri",
        ]
        write_csv_rows(self.config.exclusion_detail_csv, sorted(detail_rows, key=lambda r: (r["exclusion_reason_code"], r["source_ontology_id"], r["term"], r["class_iri"])), detail_fieldnames)

        summary_rows = []
        for _, stage, reason_code, _ in exclusion_groups:
            reason_rows = [row for row in detail_rows if row["exclusion_reason_code"] == reason_code]
            unique_ontologies = {row["source_ontology_id"] for row in reason_rows if row.get("source_ontology_id")}
            unique_class_iris = {row["class_iri"] for row in reason_rows if row.get("class_iri")}
            summary_rows.append(
                {
                    "exclusion_stage": stage,
                    "exclusion_reason_code": reason_code,
                    "excluded_source_ontology_appearances": len(reason_rows),
                    "excluded_unique_source_ontologies": len(unique_ontologies),
                    "excluded_unique_class_iris": len(unique_class_iris),
                }
            )
        write_csv_rows(
            self.config.exclusion_summary_csv,
            summary_rows,
            [
                "exclusion_stage",
                "exclusion_reason_code",
                "excluded_source_ontology_appearances",
                "excluded_unique_source_ontologies",
                "excluded_unique_class_iris",
            ],
        )
        if detail_rows:
            print(
                f"Excluded {len({row['source_ontology_id'] for row in detail_rows if row.get('source_ontology_id')})} source ontologies; wrote flow-figure log -> {self.config.exclusion_detail_csv}",
                file=sys.stderr,
            )

    def _add_exclusion_detail_rows(
        self,
        detail_rows: list[dict[str, str]],
        rows: list[dict[str, str]],
        title_by_ontology: dict[str, str],
        stage: str,
        reason_code: str,
        reason: str,
    ) -> None:
        for row in rows:
            records = parse_source_records(row) or [{"source": "", "ontology": row.get("ontology", "")}]
            for record in records:
                ontology = str(record.get("ontology", "")).strip()
                source = str(record.get("source", "")).strip()
                if not ontology:
                    continue
                detail_rows.append(
                    {
                        "exclusion_stage": stage,
                        "exclusion_reason_code": reason_code,
                        "exclusion_reason": reason,
                        "source_database": source,
                        "source_ontology_id": ontology,
                        "source_ontology_title": title_by_ontology.get(ontology.upper(), row.get("ontology_title", "")),
                        "term": row.get("term", ""),
                        "preferred_label": row.get("preferred_label", ""),
                        "class_iri": row.get("class_iri", ""),
                    }
                )

    def export_smoke_ontology(self, args: argparse.Namespace) -> None:
        rows = read_csv_rows(self.config.enriched_csv)
        smoke_rows = self._smoke_rows_by_term(rows, args.smoke_per_term)
        self._export_review_ontology(
            self.config.smoke_ontology_ttl,
            ontology_iri="https://example.org/disease-review/bioportal-hierarchy-smoke",
            rows=smoke_rows,
            manual_rows=read_csv_rows(self.config.manual_csv),
            label="Disease ontology scoping review smoke extraction",
        )

    def _smoke_rows_by_term(self, rows: list[dict[str, str]], per_term: int) -> list[dict[str, str]]:
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            if "BioPortal" not in row.get("source_databases", ""):
                continue
            grouped[row.get("term", "")].append(row)
        smoke_rows = []
        for term in terms_script.DEFAULT_TERMS:
            smoke_rows.extend(grouped.get(term, [])[:per_term])
        return smoke_rows

    def _export_review_ontology(
        self,
        path: Path,
        *,
        ontology_iri: str,
        rows: list[dict[str, str]],
        manual_rows: list[dict[str, str]],
        label: str,
        include_hierarchy_module_imports: bool = False,
    ) -> None:
        manual_by_iri = {row["class_iri"]: row for row in manual_rows if row.get("class_iri")}
        citations_by_source = self._load_modelling_citations()
        citation_sources_by_iri = self._native_citation_sources_by_iri(rows)
        triples: set[tuple[str, str, str, bool]] = set()
        parent_labels_by_iri: dict[str, str] = {}
        include_source_axioms = not include_hierarchy_module_imports
        cited_iris: set[str] = set()

        for row in rows:
            iri = row.get("class_iri", "").strip()
            if not iri:
                continue
            triples.add((iri, RDF_TYPE, OWL_CLASS, True))
            self._add_literal(triples, iri, REV + "term", row.get("term", ""))
            self._add_literal(triples, iri, REV + "preferred_label", row.get("preferred_label", ""))

            if include_source_axioms:
                self._add_literal(triples, iri, RDFS_LABEL, row.get("preferred_label", ""))
                for value in split_semicolon(row.get("definition", "")):
                    self._add_literal(triples, iri, IAO_DEFINITION, value)
                for value in split_semicolon(row.get("comments", "")):
                    self._add_literal(triples, iri, RDFS_COMMENT, value)
                for value in split_semicolon(row.get("synonyms", "")):
                    self._add_literal(triples, iri, SKOS_ALT_LABEL, value)

                parent_iris = split_semicolon(row.get("parent_iris", ""))
                parent_labels = split_semicolon(row.get("parent_labels", ""))
                for index, parent_iri in enumerate(parent_iris):
                    triples.add((iri, RDFS_SUBCLASS_OF, parent_iri, True))
                    triples.add((parent_iri, RDF_TYPE, OWL_CLASS, True))
                    if index < len(parent_labels):
                        parent_labels_by_iri.setdefault(parent_iri, parent_labels[index])

            for column in EXTRACTION_REVIEW_COLUMNS:
                self._add_literal(triples, iri, REV + column, row.get(column, ""))

            for column in MANUAL_REVIEW_COLUMNS_FOR_ONTOLOGY:
                self._add_literal(triples, iri, REV + column, manual_by_iri.get(iri, {}).get(column, ""))

            if iri not in cited_iris:
                citation_added = self._add_modelling_citation_annotations(
                    triples,
                    iri,
                    citation_sources_by_iri.get(iri, []),
                    citations_by_source,
                )
                if citation_added:
                    cited_iris.add(iri)

        for parent_iri, parent_label in parent_labels_by_iri.items():
            self._add_literal(triples, parent_iri, RDFS_LABEL, parent_label)

        if include_hierarchy_module_imports:
            self._write_citation_coverage_report(rows, citation_sources_by_iri, citations_by_source)

        import_iris = [self.config.review_core_ttl.resolve().as_uri()]
        if include_hierarchy_module_imports:
            import_iris.extend(self._hierarchy_module_import_iris())
            import_iris.extend(self._write_missing_target_modules(rows))
            self._assert_exported_targets_are_imported(rows, import_iris)
        self._write_review_ttl(path, ontology_iri, label, triples, len(rows), import_iris)
        print(f"Wrote review ontology with {len(rows)} target rows -> {path}")

    def _assert_exported_targets_are_imported(self, rows: list[dict[str, str]], import_iris: list[str]) -> None:
        target_iris = {row["class_iri"] for row in rows if row.get("class_iri")}
        imported_class_iris: set[str] = set()
        for import_iri in import_iris:
            if not import_iri.startswith("file://"):
                continue
            import_path = Path(urllib.parse.unquote(urllib.parse.urlparse(import_iri).path))
            if not import_path.exists() or import_path == self.config.review_core_ttl:
                continue
            text = import_path.read_text(encoding="utf-8", errors="ignore")
            imported_class_iris.update(
                re.findall(
                    r"<([^>]+)>\s+<http://www\.w3\.org/1999/02/22-rdf-syntax-ns#type>\s+<http://www\.w3\.org/2002/07/owl#Class>",
                    text,
                )
            )
        missing = sorted(target_iris - imported_class_iris)
        if missing:
            preview = "\n  ".join(missing[:20])
            raise RuntimeError(
                f"{len(missing)} exported target classes are not covered by imported modules:\n  {preview}"
            )

    def _write_missing_target_modules(self, rows: list[dict[str, str]]) -> list[str]:
        covered_iris = self._module_class_iris()
        missing_rows = [
            row for row in rows
            if row.get("class_iri") and row["class_iri"] not in covered_iris
        ]
        self.config.fallback_module_dir.mkdir(parents=True, exist_ok=True)
        for stale_path in self.config.fallback_module_dir.glob("*.ttl"):
            stale_path.unlink()
        old_single_fallback = self.config.ontology_dir / "review_target_fallback_stubs.ttl"
        if old_single_fallback.exists():
            old_single_fallback.unlink()
        if not missing_rows:
            return []

        rows_by_ontology: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in missing_rows:
            rows_by_ontology[row.get("ontology", "unknown")].append(row)

        import_iris: list[str] = []
        for ontology, ontology_rows in sorted(rows_by_ontology.items()):
            triples = self._target_module_triples(
                ontology_rows,
                source_label=f"generated review target module for {ontology} from {self.config.enriched_csv.name}",
            )
            module_path = self.config.fallback_module_dir / f"{safe_name(ontology)}_fallback_hierarchy.ttl"
            write_hierarchy_ttl(
                module_path,
                f"https://example.org/disease-review/modules/{safe_name(ontology)}_fallback_hierarchy",
                triples,
                source_label=f"Generated review target module for {ontology}; source API hierarchy module was missing or incomplete",
                ontology_versions=join_values(row.get("ontology_versions", "") for row in ontology_rows),
                retrieved_at=now_iso(),
            )
            import_iris.append(module_path.resolve().as_uri())

        print(
            f"Wrote {len(import_iris)} generated fallback modules covering {len(missing_rows)} exported target classes -> {self.config.fallback_module_dir}"
        )
        return import_iris

    def _target_module_triples(self, rows: list[dict[str, str]], *, source_label: str) -> set[tuple[str, str, str, bool]]:
        triples: set[tuple[str, str, str, bool]] = set()
        parent_labels_by_iri: dict[str, str] = {}
        for row in rows:
            iri = row["class_iri"]
            triples.add((iri, RDF_TYPE, OWL_CLASS, True))
            self._add_literal(triples, iri, RDFS_LABEL, row.get("preferred_label", ""))
            for value in split_semicolon(row.get("definition", "")):
                self._add_literal(triples, iri, IAO_DEFINITION, value)
            for value in split_semicolon(row.get("comments", "")):
                self._add_literal(triples, iri, RDFS_COMMENT, value)
            for value in split_semicolon(row.get("synonyms", "")):
                self._add_literal(triples, iri, SKOS_ALT_LABEL, value)

            parent_iris = split_semicolon(row.get("parent_iris", ""))
            parent_labels = split_semicolon(row.get("parent_labels", ""))
            for index, parent_iri in enumerate(parent_iris):
                triples.add((iri, RDFS_SUBCLASS_OF, parent_iri, True))
                triples.add((parent_iri, RDF_TYPE, OWL_CLASS, True))
                if index < len(parent_labels):
                    parent_labels_by_iri.setdefault(parent_iri, parent_labels[index])

            self._add_literal(triples, iri, DCTERMS_SOURCE, source_label)

        for parent_iri, parent_label in parent_labels_by_iri.items():
            self._add_literal(triples, parent_iri, RDFS_LABEL, parent_label)
        return triples

    def _module_class_iris(self) -> set[str]:
        module_iris: set[str] = set()
        for module_iri in self._hierarchy_module_import_iris():
            if not module_iri.startswith("file://"):
                continue
            module_path = Path(urllib.parse.unquote(urllib.parse.urlparse(module_iri).path))
            if not module_path.exists():
                continue
            text = module_path.read_text(encoding="utf-8", errors="ignore")
            module_iris.update(re.findall(r"<([^>]+)>\s+<http://www\.w3\.org/1999/02/22-rdf-syntax-ns#type>\s+<http://www\.w3\.org/2002/07/owl#Class>", text))
        return module_iris

    def _hierarchy_module_import_iris(self) -> list[str]:
        module_dirs = [
            self.config.bioportal_module_dir,
            self.config.ols_module_dir,
            self.config.obo_module_dir,
        ]
        module_paths: list[Path] = []
        for module_dir in module_dirs:
            if module_dir.exists():
                module_paths.extend(sorted(module_dir.glob("*.ttl")))
        return [path.resolve().as_uri() for path in module_paths]

    @staticmethod
    def _add_literal(triples: set[tuple[str, str, str, bool]], subject: str, predicate: str, value: str) -> None:
        if str(value or "").strip():
            triples.add((subject, predicate, str(value).strip(), False))

    def _write_review_ttl(
        self,
        path: Path,
        ontology_iri: str,
        label: str,
        triples: set[tuple[str, str, str, bool]],
        target_row_count: int,
        import_iris: list[str],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            handle.write("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n")
            handle.write("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n")
            handle.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")
            handle.write("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n")
            handle.write("@prefix iao: <http://purl.obolibrary.org/obo/IAO_> .\n")
            handle.write("@prefix dcterms: <http://purl.org/dc/terms/> .\n")
            handle.write("@prefix rev: <https://example.org/disease-review/ap/> .\n\n")
            handle.write(f"{ttl_iri(ontology_iri)} a owl:Ontology ;\n")
            if import_iris:
                imports = ",\n        ".join(ttl_iri(import_iri) for import_iri in import_iris)
                handle.write(f"    owl:imports {imports} ;\n")
            handle.write(f"    rdfs:label {ttl_literal(label)} ;\n")
            handle.write(f"    dcterms:created {ttl_literal(now_iso())} ;\n")
            handle.write(f"    dcterms:description {ttl_literal(f'Generated from {target_row_count} enriched extraction rows plus manual review annotations.')} .\n\n")
            for subject, predicate, obj, object_is_iri in sorted(triples):
                handle.write(ttl_line(subject, predicate, obj, object_is_iri=object_is_iri) + "\n")

    def download_source_ontologies(self, args: argparse.Namespace) -> None:
        repositories = download_script.parse_repositories(args.repositories)
        ids_by_source = download_script.read_review_ontology_ids(self.config.enriched_csv, args.source_mode)
        existing = download_script.existing_ontology_keys(self.config.import_dir)
        jobs = download_script.build_download_jobs(ids_by_source, repositories, self.config.import_dir, existing, args.overwrite)
        if args.limit_rows:
            jobs = jobs[: args.limit_rows]
        manifest_path = self.config.table_dir / "download_review_ontologies_manifest.csv"
        if args.dry_run:
            rows = [
                download_script.make_dry_row(job["source"], job["ontology"], self.config.import_dir, job.get("download_url", ""), job.get("metadata_url", ""))
                for job in jobs
            ]
            download_script.write_manifest(manifest_path, rows)
            print(f"Dry-run manifest -> {manifest_path}")
            return
        apikey = download_script.load_bioportal_api_key()
        manifest_rows = []
        for job in jobs:
            if not job.get("download_url"):
                row = {
                    "source": job["source"],
                    "ontology": job["ontology"],
                    "status": "error_no_download_url",
                    "path": "",
                    "download_url": "",
                    "metadata_url": job.get("metadata_url", ""),
                    "bytes": 0,
                    "retrieved_at": now_iso(),
                    "message": "No download URL found in source metadata.",
                }
            elif job["source"] == "BioPortal":
                row = download_script.download_url(
                    ontology=job["ontology"],
                    source=job["source"],
                    url=job["download_url"],
                    params={"apikey": apikey},
                    import_dir=self.config.import_dir,
                    overwrite=args.overwrite,
                    metadata_url=job.get("metadata_url", ""),
                )
            else:
                row = download_script.download_url(
                    ontology=job["ontology"],
                    source=job["source"],
                    url=job["download_url"],
                    import_dir=self.config.import_dir,
                    overwrite=args.overwrite,
                    metadata_url=job.get("metadata_url", ""),
                )
            manifest_rows.append(row)
            time.sleep(args.delay)
        download_script.write_manifest(manifest_path, manifest_rows)
        print(f"Download manifest -> {manifest_path}")

    def extract_all_hierarchies(self, args: argparse.Namespace) -> None:
        self.extract_bioportal_hierarchy(args)
        self.extract_ols_hierarchy(args)
        self.extract_obo_hierarchy(args)

    def extract_bioportal_hierarchy(self, args: argparse.Namespace) -> None:
        rows = read_source_hierarchy_rows(self.config.enriched_csv, "BioPortal", only_candidates=not args.include_preexcluded)
        self._extract_bioportal_hierarchy_modules(rows, args)

    def _extract_bioportal_hierarchy_modules(self, rows: list[dict[str, str]], args: argparse.Namespace) -> None:
        if args.limit_rows:
            rows = rows[: args.limit_rows]
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            grouped[row["ontology"]].append(row)
        apikey = terms_script.load_bioportal_api_key()
        all_triples: set[tuple[str, str, str, bool]] = set()
        manifest_rows = []
        run_retrieved_at = now_iso()
        cache_dir = self.config.hierarchy_cache_dir / "bioportal"

        for index, (ontology, ontology_rows) in enumerate(sorted(grouped.items()), start=1):
            print(f"[BioPortal {index}/{len(grouped)}] {ontology}: {len(ontology_rows)} targets", file=sys.stderr)
            module_triples: set[tuple[str, str, str, bool]] = set()
            nodes: dict[str, dict[str, Any]] = {}
            target_iris = {row["class_iri"] for row in ontology_rows}
            for row in ontology_rows:
                iri = row["class_iri"]
                target_record = hierarchy_fetch_class(ontology, iri, apikey, cache_dir)
                if target_record.get("@id"):
                    nodes[target_record["@id"]] = target_record
                for ancestor in hierarchy_fetch_ancestors(ontology, iri, apikey, cache_dir):
                    if ancestor.get("@id"):
                        nodes[ancestor["@id"]] = ancestor
            edge_count = 0
            for child_iri in sorted(nodes):
                for parent in hierarchy_fetch_parents(ontology, child_iri, apikey, cache_dir):
                    parent_iri = parent.get("@id", "")
                    if parent_iri and parent_iri in nodes:
                        module_triples.add((child_iri, RDFS_SUBCLASS_OF, parent_iri, True))
                        edge_count += 1
            for record in nodes.values():
                module_triples.update(hierarchy_triples_for_class(record))
            for target_iri in target_iris:
                module_triples.add((target_iri, DCTERMS_SOURCE, f"review target in BioPortal {ontology} from {self.config.enriched_csv.name}", False))
            module_path = self.config.bioportal_module_dir / f"{safe_name(ontology)}_hierarchy.ttl"
            write_hierarchy_ttl(
                module_path,
                f"https://example.org/disease-review/modules/{safe_name(ontology)}_hierarchy",
                module_triples,
                source_label="BioPortal API hierarchy extraction",
                ontology_versions=join_values(row.get("ontology_versions", "") for row in ontology_rows),
                retrieved_at=run_retrieved_at,
            )
            all_triples.update(module_triples)
            manifest_rows.append(self._manifest_row(ontology, ontology_rows, target_iris, nodes, edge_count, "BioPortal", module_path, run_retrieved_at))

        write_hierarchy_ttl(
            self.config.bioportal_merged_ttl,
            "https://example.org/disease-review/bioportal-hierarchy",
            all_triples,
            source_label="BioPortal API hierarchy extraction",
            retrieved_at=run_retrieved_at,
        )
        self._write_hierarchy_manifest(self.config.bioportal_manifest, manifest_rows)

    def extract_ols_hierarchy(self, args: argparse.Namespace) -> None:
        rows = read_source_hierarchy_rows(self.config.enriched_csv, "OLS", only_candidates=not args.include_preexcluded)
        if args.limit_rows:
            rows = rows[: args.limit_rows]
        base_url = terms_script.normalise_ols_base_url(args.ols_base_url)
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            grouped[row["ontology"].lower()].append(row)
        all_triples: set[tuple[str, str, str, bool]] = set()
        manifest_rows = []
        run_retrieved_at = now_iso()
        for index, (ontology, ontology_rows) in enumerate(sorted(grouped.items()), start=1):
            print(f"[OLS {index}/{len(grouped)}] {ontology}: {len(ontology_rows)} targets", file=sys.stderr)
            module_triples: set[tuple[str, str, str, bool]] = set()
            nodes: dict[str, dict[str, Any]] = {}
            target_iris = {row["class_iri"] for row in ontology_rows}
            edge_count = 0
            queue = [(iri, 0) for iri in sorted(target_iris)]
            seen_depth: dict[str, int] = {}
            while queue:
                iri, depth = queue.pop(0)
                if iri in seen_depth and seen_depth[iri] <= depth:
                    continue
                seen_depth[iri] = depth
                nodes[iri] = self._ols_term_record(ontology, iri, base_url)
                if depth >= args.max_depth:
                    continue
                for parent in terms_script.fetch_ols_parents(ontology, iri, base_url):
                    parent_iri = parent.get("@id", "")
                    if not parent_iri:
                        continue
                    module_triples.add((iri, RDFS_SUBCLASS_OF, parent_iri, True))
                    edge_count += 1
                    nodes.setdefault(parent_iri, {"@id": parent_iri, "prefLabel": parent.get("prefLabel", ""), "definition": [], "synonym": [], "properties": {}})
                    queue.append((parent_iri, depth + 1))
            self._add_target_fallback_nodes(module_triples, nodes, ontology_rows, f"review target in OLS {ontology} from {self.config.enriched_csv.name}")
            for record in nodes.values():
                module_triples.update(hierarchy_triples_for_class(record))
            module_path = self.config.ols_module_dir / f"{safe_name(ontology)}_ols_hierarchy.ttl"
            write_hierarchy_ttl(
                module_path,
                f"https://example.org/disease-review/modules/{safe_name(ontology)}_ols_hierarchy",
                module_triples,
                source_label="OLS API hierarchy extraction",
                ontology_versions=join_values([terms_script.fetch_ols_ontology_version(ontology, base_url)] + [r.get("hierarchy_source_ontology_version", "") for r in ontology_rows]),
                retrieved_at=run_retrieved_at,
            )
            all_triples.update(module_triples)
            manifest_rows.append(self._manifest_row(ontology, ontology_rows, target_iris, nodes, edge_count, "OLS", module_path, run_retrieved_at))
        write_hierarchy_ttl(self.config.ols_merged_ttl, "https://example.org/disease-review/ols-hierarchy", all_triples, source_label="OLS API hierarchy extraction", retrieved_at=run_retrieved_at)
        self._write_hierarchy_manifest(self.config.ols_manifest, manifest_rows)

    def _ols_term_record(self, ontology: str, iri: str, base_url: str) -> dict[str, Any]:
        detail = terms_script.fetch_ols_term_details(ontology, iri, base_url)
        if not detail:
            return {"@id": iri, "prefLabel": "", "definition": [], "synonym": [], "properties": {}}
        annotations = detail.get("annotation") if isinstance(detail.get("annotation"), dict) else {}
        properties: dict[str, Any] = dict(annotations)
        for key in ["comment", "comments"]:
            if detail.get(key):
                properties[key] = detail.get(key)
        return {
            "@id": detail.get("iri") or iri,
            "prefLabel": detail.get("label") or detail.get("prefLabel") or "",
            "definition": clean_list(detail.get("description")) + terms_script.extract_annotation_values(detail, terms_script.DEFINITION_KEYS),
            "synonym": clean_list(detail.get("synonym")) + clean_list(detail.get("exact_synonyms")),
            "properties": properties,
        }

    def extract_obo_hierarchy(self, args: argparse.Namespace) -> None:
        rows = read_source_hierarchy_rows(self.config.enriched_csv, "OBO Foundry Direct", only_candidates=not args.include_preexcluded)
        if args.limit_rows:
            rows = rows[: args.limit_rows]
        grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            source_url = self._obo_source_url(row)
            if source_url:
                grouped[(row["ontology"].lower(), source_url)].append(row)
        all_triples: set[tuple[str, str, str, bool]] = set()
        manifest_rows = []
        run_retrieved_at = now_iso()
        for index, ((ontology, source_url), ontology_rows) in enumerate(sorted(grouped.items()), start=1):
            print(f"[OBO {index}/{len(grouped)}] {ontology}: {len(ontology_rows)} targets", file=sys.stderr)
            text = terms_script.get_text(source_url, namespace="obo-direct-hierarchy")
            if not text:
                continue
            version, source_nodes, source_edges = parse_ontology_graph(text)
            module_triples: set[tuple[str, str, str, bool]] = set()
            nodes: dict[str, dict[str, Any]] = {}
            target_iris = {row["class_iri"] for row in ontology_rows}
            edge_count = 0
            queue = [(iri, 0) for iri in sorted(target_iris)]
            seen_depth: dict[str, int] = {}
            while queue:
                iri, depth = queue.pop(0)
                if iri in seen_depth and seen_depth[iri] <= depth:
                    continue
                seen_depth[iri] = depth
                nodes[iri] = source_nodes.get(iri, {"@id": iri, "prefLabel": "", "definition": [], "synonym": [], "properties": {}})
                if depth >= args.max_depth:
                    continue
                for parent_iri in source_edges.get(iri, []):
                    module_triples.add((iri, RDFS_SUBCLASS_OF, parent_iri, True))
                    edge_count += 1
                    nodes[parent_iri] = source_nodes.get(parent_iri, {"@id": parent_iri, "prefLabel": "", "definition": [], "synonym": [], "properties": {}})
                    queue.append((parent_iri, depth + 1))
            self._add_target_fallback_nodes(module_triples, nodes, ontology_rows, f"review target in OBO Foundry Direct {ontology} from {self.config.enriched_csv.name}")
            for record in nodes.values():
                module_triples.update(hierarchy_triples_for_class(record))
            module_path = self.config.obo_module_dir / f"{safe_name(ontology)}_obo_direct_hierarchy.ttl"
            write_hierarchy_ttl(
                module_path,
                f"https://example.org/disease-review/modules/{safe_name(ontology)}_obo_direct_hierarchy",
                module_triples,
                source_label=f"OBO Foundry Direct hierarchy extraction from {source_url}",
                ontology_versions=join_values([version] + [r.get("hierarchy_source_ontology_version", "") for r in ontology_rows]),
                retrieved_at=run_retrieved_at,
            )
            all_triples.update(module_triples)
            row = self._manifest_row(ontology, ontology_rows, target_iris, nodes, edge_count, "OBO Foundry Direct", module_path, run_retrieved_at)
            row["source_url"] = source_url
            manifest_rows.append(row)
        write_hierarchy_ttl(self.config.obo_merged_ttl, "https://example.org/disease-review/obo-direct-hierarchy", all_triples, source_label="OBO Foundry Direct hierarchy extraction", retrieved_at=run_retrieved_at)
        self._write_hierarchy_manifest(self.config.obo_manifest, manifest_rows)

    @staticmethod
    def _obo_source_url(row: dict[str, str]) -> str:
        if row.get("hierarchy_source_url"):
            return row["hierarchy_source_url"]
        for part in split_semicolon(row.get("source_urls", "")):
            if part.casefold().startswith("obo foundry direct:"):
                return part.split(":", 1)[1].strip()
        return ""

    @staticmethod
    def _add_target_fallback_nodes(
        module_triples: set[tuple[str, str, str, bool]],
        nodes: dict[str, dict[str, Any]],
        rows: list[dict[str, str]],
        source_label: str,
    ) -> None:
        for row in rows:
            iri = row["class_iri"]
            if iri not in nodes or not nodes[iri].get("prefLabel"):
                nodes[iri] = {
                    "@id": iri,
                    "prefLabel": row.get("preferred_label", ""),
                    "definition": split_semicolon(row.get("definition", "")),
                    "synonym": split_semicolon(row.get("synonyms", "")),
                    "properties": {RDFS_COMMENT: split_semicolon(row.get("comments", ""))},
                }
            module_triples.add((iri, DCTERMS_SOURCE, source_label, False))

    def _manifest_row(
        self,
        ontology: str,
        ontology_rows: list[dict[str, str]],
        target_iris: set[str],
        nodes: dict[str, dict[str, Any]],
        edge_count: int,
        source: str,
        module_path: Path,
        retrieved_at: str,
    ) -> dict[str, str | int]:
        return {
            "ontology": ontology,
            "target_rows": len(ontology_rows),
            "target_iris": len(target_iris),
            "classes_written": len(nodes),
            "subclass_edges": edge_count,
            "ontology_versions": join_values(row.get("ontology_versions", "") for row in ontology_rows),
            "retrieval_source_database": source,
            "retrieved_at": retrieved_at,
            "source_csv": str(self.config.enriched_csv),
            "module_path": str(module_path),
        }

    @staticmethod
    def _write_hierarchy_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
        fieldnames = [
            "ontology",
            "target_rows",
            "target_iris",
            "classes_written",
            "subclass_edges",
            "ontology_versions",
            "retrieval_source_database",
            "retrieved_at",
            "source_csv",
            "source_url",
            "module_path",
        ]
        write_csv_rows(path, rows, fieldnames)
        print(f"Wrote hierarchy manifest -> {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--chunk",
        required=True,
        choices=[
            "search",
            "enrich",
            "prefill-manual",
            "review-class",
            "review-ui",
            "export-appearance-report",
            "export-review-ontology",
            "export-smoke-ontology",
            "download",
            "bioportal-hierarchy",
            "ols-hierarchy",
            "obo-hierarchy",
            "all-hierarchies",
        ],
        help="Pipeline chunk to run.",
    )
    parser.add_argument("--sources", default="bioportal,ols,obo", help="For --chunk search: bioportal,ols,obo.")
    parser.add_argument("--terms", default="", help="For --chunk search: comma-separated term override.")
    parser.add_argument("--resume", action="store_true", help="For --chunk search: merge into the existing raw CSV.")
    parser.add_argument("--no-parents", action="store_true", help="For --chunk search: skip parent fetches.")
    parser.add_argument("--no-mappings", action="store_true", help="For --chunk search: skip BioPortal mappings.")
    parser.add_argument("--include-nonlabel-matches", action="store_true", help="For --chunk search: keep non-label exact-search hits.")
    parser.add_argument("--no-enrich-output", action="store_true", help="For --chunk search: write raw columns only.")
    parser.add_argument("--obo-max-ontologies", type=int, default=None, help="For --chunk search: cap direct OBO scans.")
    parser.add_argument("--ols-base-url", default=os.environ.get("OLS_BASE_URL", OLS_BASE_URL), help="OLS base URL.")
    parser.add_argument("--refresh-class-annotations", action="store_true", help="For --chunk enrich.")
    parser.add_argument("--merge-manual", action=argparse.BooleanOptionalAction, default=True, help="For --chunk prefill-manual.")
    parser.add_argument("--class-iri", default="", help="For --chunk review-class: review this exact class IRI.")
    parser.add_argument("--search-text", default="", help="For --chunk review-class: filter by label, IRI, ontology, or definition before selecting. Omit to review all extracted terms.")
    parser.add_argument("--reviewer", default=os.environ.get("USER", ""), help="For --chunk review-class: default reviewer name/id.")
    parser.add_argument("--review-date", default="", help="For --chunk review-class: default ISO review date.")
    parser.add_argument("--no-export-after-review", action="store_true", help="For --chunk review-class: update manual CSV only.")
    parser.add_argument("--host", default="127.0.0.1", help="For --chunk review-ui: local server host.")
    parser.add_argument("--port", type=int, default=8765, help="For --chunk review-ui: local server port.")
    parser.add_argument("--no-browser", action="store_true", help="For --chunk review-ui: do not open the browser automatically.")
    parser.add_argument("--repositories", default="bioportal", help="For --chunk download: bioportal,ols,obo.")
    parser.add_argument("--source-mode", choices=["all-source-records", "row-ontology"], default="all-source-records")
    parser.add_argument("--dry-run", action="store_true", help="For --chunk download.")
    parser.add_argument("--overwrite", action="store_true", help="For --chunk download.")
    parser.add_argument("--delay", type=float, default=0.2, help="For --chunk download.")
    parser.add_argument("--limit-rows", type=int, default=0, help="Limit rows/jobs for smoke tests.")
    parser.add_argument("--include-preexcluded", action="store_true", help="For hierarchy chunks.")
    parser.add_argument("--max-depth", type=int, default=25, help="For OLS/OBO hierarchy chunks.")
    parser.add_argument("--smoke-per-term", type=int, default=1, help="For --chunk export-smoke-ontology.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    ReviewExtractionPipeline().run_chunk(args.chunk, args)


if __name__ == "__main__":
    main()
