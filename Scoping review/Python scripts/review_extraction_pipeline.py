#!/usr/bin/env python3
"""One entry point for the disease-ontology scoping-review extraction pipeline.

The older scripts are kept importable, but this class gives one place to run the
main chunks:

    python3 "Scoping review/Python scripts/review_extraction_pipeline.py" --chunk export-review-ontology
    python3 "Scoping review/Python scripts/review_extraction_pipeline.py" --chunk prefill-manual
    python3 "Scoping review/Python scripts/review_extraction_pipeline.py" --chunk search --sources bioportal,ols
    python3 "Scoping review/Python scripts/review_extraction_pipeline.py" --chunk bioportal-hierarchy --limit-rows 10

The review ontology export is intentionally table-free at the point of use: it
turns the enriched extraction CSV and manual annotation CSV into annotation
triples on the extracted OWL classes.
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
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
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
REV = "https://example.org/disease-review/ap/"
CANONICAL_MESH_ONTOLOGY = "MESH"
DUPLICATE_MESH_ONTOLOGIES = {"MDM", "RH-MESH"}

EXTRACTION_REVIEW_COLUMNS = [
    "source_databases",
    "retrieved_at_by_database",
    "ontology_versions",
    "source_urls",
    "ontology_title",
    "ontology_description",
    "ontology_domain",
    "ontology_homepage",
    "ontology_repository",
    "ontology_license",
    "ontology_status",
    "ontology_metadata_source",
    "ontology_metadata_retrieved_at",
    "ontology_scope_category",
    "ontology_exclusion_status",
    "ontology_exclusion_rule",
    "ontology_exclusion_reason",
    "native_ontology_guess",
    "native_term_status",
    "manual_screening_hint",
    "bfo_anchor",
    "mapping_count",
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
        "disease_as_disposition",
        "disease_as_disorder",
        "disease_as_process",
        "disease_as_finding",
        "disease_as_condition",
        "disease_as_pathology",
        "disease_as_syndrome",
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

REVIEW_PROMPT_FIELDS = [
    "ontology_type_manual",
    "native_or_imported_manual",
    "manual_include_status",
    "manual_exclusion_reason",
    "manual_exclusion_detail",
    "disease_model_category",
    "upper_level_interpretation",
    "definition_quality",
    "comment_quality",
    "parentage_quality",
    "provenance_quality",
    "entity_quality_score",
    "quality_decision",
    "reviewer",
    "review_date",
    "review_notes",
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
        self._print_review_packet(target, manual_row, evidence)

        if not self._confirm("Review this class now?", default=True):
            print("No changes written.")
            return

        updated = dict(manual_row)
        for field in REVIEW_PROMPT_FIELDS:
            if field == "reviewer" and args.reviewer and not updated.get(field):
                updated[field] = args.reviewer
            if field == "review_date" and not updated.get(field):
                updated[field] = args.review_date or datetime.now().date().isoformat()
            updated[field] = self._prompt_field(field, updated.get(field, ""))

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

    def _print_review_packet(self, row: dict[str, str], manual: dict[str, str], evidence: dict[str, list[str]]) -> None:
        print("\n" + "=" * 88)
        print("CLASS TO REVIEW")
        print("=" * 88)
        self._print_block("IRI", [row.get("class_iri", "")])
        self._print_block("Label", evidence["labels"] or [row.get("preferred_label", "")])
        self._print_block("Ontology/source", [
            f"ontology: {row.get('ontology', '')}",
            f"source_ontology_ids: {row.get('source_ontology_ids', '')}",
            f"source_databases: {row.get('source_databases', '')}",
            f"ontology_title: {row.get('ontology_title', '')}",
            f"ontology_status: {row.get('ontology_status', '')}",
            f"ontology_scope_category: {row.get('ontology_scope_category', '')}",
            f"ontology_exclusion: {row.get('ontology_exclusion_status', '')} {row.get('ontology_exclusion_reason', '')}",
            f"native_guess: {row.get('native_ontology_guess', '')} / {row.get('native_term_status', '')}",
        ])
        self._print_block("Definitions", evidence["definitions"] or split_semicolon(row.get("definition", "")) or ["(none)"])
        self._print_block("Comments", evidence["comments"] or split_semicolon(row.get("comments", "")) or ["(none)"])
        self._print_block("Synonyms", evidence["synonyms"] or split_semicolon(row.get("synonyms", "")) or ["(none)"])
        self._print_block("Direct parents", evidence["parents"] or self._row_parent_lines(row) or ["(none)"])
        self._print_block("Extraction hints", [
            f"bfo_anchor: {row.get('bfo_anchor', '')}",
            f"manual_screening_hint: {row.get('manual_screening_hint', '')}",
            f"mapping_count: {row.get('mapping_count', '')}",
            f"source_urls: {row.get('source_urls', '')}",
            f"ontology_versions: {row.get('ontology_versions', '')}",
        ])
        self._print_block("Current/manual defaults", [
            f"{field}: {manual.get(field, '')}"
            for field in REVIEW_PROMPT_FIELDS
            if manual.get(field, "")
        ] or ["(none)"])
        self._print_block("Resolving modules", evidence["module_paths"] or ["(no imported module found for this class)"])

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

    @staticmethod
    def _prompt_field(field: str, current: str) -> str:
        values = CONTROLLED_VALUES.get(field)
        if values:
            print(f"\n{field}")
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
        answer = input(f"\n{field} [{current or 'blank'}]: ").strip()
        return current if answer == "" else answer

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
        for row in rows:
            if row.get("ontology", "").upper() in DUPLICATE_MESH_ONTOLOGIES:
                skipped_mesh_duplicates += 1
                continue
            filtered.append(row)
        if skipped_mesh_duplicates:
            print(
                f"Skipped {skipped_mesh_duplicates} duplicate MeSH mirror rows; kept canonical {CANONICAL_MESH_ONTOLOGY}.",
                file=sys.stderr,
            )
        return filtered

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
        triples: set[tuple[str, str, str, bool]] = set()
        parent_labels_by_iri: dict[str, str] = {}
        include_source_axioms = not include_hierarchy_module_imports

        for row in rows:
            iri = row.get("class_iri", "").strip()
            if not iri:
                continue
            triples.add((iri, RDF_TYPE, OWL_CLASS, True))
            self._add_literal(triples, iri, REV + "term", row.get("term", ""))
            self._add_literal(triples, iri, REV + "preferred_label", row.get("preferred_label", ""))
            self._add_literal(triples, iri, REV + "source_ontology_ids", row.get("source_ontology_ids", ""))

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

            for column in manual_script.FIELDNAMES:
                if column == "class_iri":
                    continue
                self._add_literal(triples, iri, REV + column, manual_by_iri.get(iri, {}).get(column, ""))

        for parent_iri, parent_label in parent_labels_by_iri.items():
            self._add_literal(triples, parent_iri, RDFS_LABEL, parent_label)

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
    parser.add_argument("--search-text", default="", help="For --chunk review-class: search label, IRI, ontology, or definition before selecting.")
    parser.add_argument("--reviewer", default=os.environ.get("USER", ""), help="For --chunk review-class: default reviewer name/id.")
    parser.add_argument("--review-date", default="", help="For --chunk review-class: default ISO review date.")
    parser.add_argument("--no-export-after-review", action="store_true", help="For --chunk review-class: update manual CSV only.")
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
