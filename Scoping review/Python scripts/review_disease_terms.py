#!/usr/bin/env python3
"""
review_disease_terms.py - multi-source survey of disease-modelling root terms

BioPortal is searched first and remains the primary source. OLS and direct OBO
Foundry scans are additive: when they return the same class IRI, the row is
merged and the extra source is recorded in provenance rather than duplicated.

Terms searched (exact preferred label/name match):
    disease, disorder, illness, condition, health condition, syndrome,
    pathological process, pathological disposition, dysfunction

Usage:
    python3 review_disease_terms.py
    python3 review_disease_terms.py --out my.csv
    python3 review_disease_terms.py --sources bioportal,ols
    python3 review_disease_terms.py --sources bioportal,ols,obo --obo-max-ontologies 20
    python3 review_disease_terms.py --no-parents
    python3 review_disease_terms.py --terms "disease,disorder"
    python3 review_disease_terms.py --resume
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
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# -- Config --------------------------------------------------------------------

ENV_FILE = Path(
    "/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Wound ontology/.env"
)

BIOPORTAL_BASE_URL = "https://data.bioontology.org"
OLS_BASE_URL = "https://www.ebi.ac.uk/ols4"
OBO_REGISTRY_URL = "https://obofoundry.org/registry/ontologies.yml"


def default_scoping_review_dir() -> Path:
    if "__file__" in globals():
        return Path(__file__).resolve().parent
    cwd = Path.cwd()
    return cwd if cwd.name == "Scoping review" else cwd / "Scoping review"


SCOPING_REVIEW_DIR = default_scoping_review_dir()
DEFAULT_OUT = SCOPING_REVIEW_DIR / "disease_terms_review.csv"

CACHE_DIR = Path("/tmp/disease_terms_review_cache")

DEFAULT_TERMS = [
    "disease",
    "disorder",
    "disorders",
    "Disorders",
    "illness",
    "condition",
    "health condition",
    "ClinicalCondition",
    "Clinical Condition",
    "syndrome",
    "pathological process",
    "pathological disposition",
    "dysfunction",
]

PRIMARY_DISCOVERY_TIER = "primary_exact_label"
SECONDARY_DISCOVERY_TIER = "secondary_compound_label_sensitivity"
MULTILINGUAL_DISCOVERY_TIER = "multilingual_label_sensitivity"
NON_DISEASE_CONTEXT_TERMS = {"predisposition", "disease course", "disease_course"}
SUPPLEMENTARY_SENSITIVITY_TERMS = [
    "pathological condition",
    "pathological state",
    "abnormal state",
    "disease state",
    "pathologic process",
    "morbid condition",
    "nosological entity",
]
COMPOUND_LABEL_SENSITIVITY_TERMS = [
    "Disease, finding or disorder",
    "DiseaseDisorderOrFinding",
    "Disease or disorder",
    "Disease or syndrome",
    "Disorder or finding",
    "Clinical finding or disorder",
]
SECONDARY_SENSITIVITY_TERMS = SUPPLEMENTARY_SENSITIVITY_TERMS + COMPOUND_LABEL_SENSITIVITY_TERMS
MULTILINGUAL_SENSITIVITY_TERMS = [
    "maladie",
    "trouble",
    "condition pathologique",
    "Krankheit",
    "Erkrankung",
    "Störung",
]

BFO_PREFIX = "http://purl.obolibrary.org/obo/BFO_"
DELAY = 0.12
# Safety cap for BioPortal /search pagination. Multi-word / common terms (e.g.
# "Clinical Condition") get tokenised, so require_exact_match stops limiting and
# BioPortal returns a huge fuzzy result set spanning tens of thousands of pages.
# Exact-label matches (the only ones we keep) rank on the first page(s); deeper
# pages are fuzzy noise that is filtered out anyway. 0 disables the cap.
MAX_SEARCH_PAGES = 50

DEFINITION_KEYS = {
    "definition",
    "definitions",
    "description",
    "dc:description",
    "dcterms:description",
    "iao_0000115",
    "obo:iao_0000115",
    "skos:definition",
    "http://purl.obolibrary.org/obo/iao_0000115",
    "http://www.w3.org/2004/02/skos/core#definition",
}
COMMENT_KEYS = {
    "comment",
    "comments",
    "rdfs:comment",
    "skos:note",
    "skos:scopeNote",
    "scopeNote",
    "editor note",
    "iao_0000116",
    "http://www.w3.org/2000/01/rdf-schema#comment",
    "http://www.w3.org/2004/02/skos/core#note",
    "http://www.w3.org/2004/02/skos/core#scopeNote",
    "http://purl.obolibrary.org/obo/iao_0000116",
}
EXACT_MATCH_KEYS = {
    "exactMatch",
    "skos:exactMatch",
    "http://www.w3.org/2004/02/skos/core#exactMatch",
}
DEFINED_BY_KEYS = {
    "isDefinedBy",
    "rdfs:isDefinedBy",
    "http://www.w3.org/2000/01/rdf-schema#isDefinedBy",
}
CONFORMS_TO_KEYS = {
    "conformsTo",
    "dcterms:conformsTo",
    "http://purl.org/dc/terms/conformsTo",
}
VALUE_KEYS = {"value", "values", "text", "literal", "label"}

THESAURUS_ONTOLOGY_IDS = {"mesh", "rh-mesh", "mdm", "mstde", "umls", "ncit"}
THESAURUS_METADATA_PHRASES = {
    "thesaurus",
    "medical subject headings",
    "national cancer institute thesaurus",
    "umls metathesaurus",
    "metathesaurus",
}


# -- Generic helpers -----------------------------------------------------------

def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def clean_list(values: Any) -> list[str]:
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    return [str(v).strip() for v in values if str(v).strip()]


def first_clean(values: Any) -> str:
    values = clean_list(values)
    return values[0] if values else ""


def join_values(values: Any) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in clean_list(values):
        if value not in seen:
            out.append(value)
            seen.add(value)
    return "; ".join(out)


def append_unique(existing: str, value: str) -> str:
    parts = clean_list(existing.split(";")) if existing else []
    if value and value not in parts:
        parts.append(value)
    return "; ".join(parts)


def cache_path(namespace: str, url: str, params: dict[str, Any] | None = None) -> Path:
    params = params or {}
    serialised = json.dumps([url, sorted(params.items())], sort_keys=True, default=str)
    digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
    path = CACHE_DIR / namespace
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{digest}.json"


def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    namespace: str = "generic",
    retries: int = 3,
    headers: dict[str, str] | None = None,
    cache: bool = True,
) -> Any | None:
    path = cache_path(namespace, url, params)
    if cache and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    for attempt in range(retries):
        try:
            time.sleep(DELAY)
            response = requests.get(url, params=params or {}, headers=headers, timeout=60)
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
            if cache:
                path.write_text(json.dumps(data), encoding="utf-8")
            return data
        except Exception as exc:
            print(f"  [warn] GET {url} attempt {attempt + 1} failed: {exc}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def get_text(
    url: str,
    *,
    namespace: str,
    retries: int = 3,
    cache: bool = True,
) -> str | None:
    path = cache_path(namespace, url)
    text_path = path.with_suffix(".txt")
    if cache and text_path.exists():
        return text_path.read_text(encoding="utf-8", errors="replace")

    for attempt in range(retries):
        try:
            time.sleep(DELAY)
            response = requests.get(url, timeout=120)
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 10))
                print(f"  [rate limit] waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            response.raise_for_status()
            text = response.text
            if cache:
                text_path.write_text(text, encoding="utf-8")
            return text
        except Exception as exc:
            print(f"  [warn] GET {url} attempt {attempt + 1} failed: {exc}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def bfo_anchor(parents: list[dict[str, str]]) -> str:
    for parent in parents:
        iri = parent.get("@id", "") or ""
        if iri.startswith(BFO_PREFIX):
            label = (parent.get("prefLabel") or "").strip()
            return f"{label} ({iri.split('BFO_')[1]})" if label else iri
    return ""


def obo_curie_to_iri(curie: str) -> str:
    return f"http://purl.obolibrary.org/obo/{curie.replace(':', '_')}"


def annotation_key_matches(key: str, wanted_keys: set[str]) -> bool:
    lowered = key.strip().lower()
    local = lowered.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    wanted = {wanted_key.strip().lower() for wanted_key in wanted_keys}
    return lowered in wanted or local in wanted


def clean_annotation_value(value: Any) -> list[str]:
    if isinstance(value, dict):
        for key in VALUE_KEYS:
            if key in value:
                return clean_list(value[key])
        return []
    return clean_list(value)


def extract_annotation_values(data: Any, wanted_keys: set[str]) -> list[str]:
    values: list[str] = []
    if not isinstance(data, dict):
        return values

    for key, value in data.items():
        if annotation_key_matches(str(key), wanted_keys):
            values.extend(clean_annotation_value(value))

    for container_key in ["properties", "annotation", "annotations"]:
        container = data.get(container_key)
        if isinstance(container, dict):
            for key, value in container.items():
                if annotation_key_matches(str(key), wanted_keys):
                    values.extend(clean_annotation_value(value))
        elif isinstance(container, list):
            for item in container:
                if not isinstance(item, dict):
                    continue
                item_keys = clean_list(
                    item.get("property")
                    or item.get("predicate")
                    or item.get("annotationProperty")
                    or item.get("iri")
                    or item.get("@id")
                )
                if any(annotation_key_matches(key, wanted_keys) for key in item_keys):
                    for value_key in VALUE_KEYS:
                        values.extend(clean_annotation_value(item.get(value_key)))
                values.extend(extract_annotation_values(item, wanted_keys))

    return values


def make_row(
    *,
    term: str,
    source: str,
    ontology: str,
    ontology_version: str = "",
    preferred_label: str = "",
    class_iri: str = "",
    definition: str = "",
    comments: str = "",
    synonyms: str = "",
    parent_labels: str = "",
    parent_iris: str = "",
    bfo_anchor_value: str = "",
    mapping_count: str | int = "",
    exact_match_iris: str = "",
    defined_by_iris: str = "",
    conforms_to_iris: str = "",
    source_url: str = "",
    retrieved_at: str | None = None,
    discovery_tier: str = PRIMARY_DISCOVERY_TIER,
) -> dict[str, Any]:
    retrieved_at = retrieved_at or now_iso()
    row = {
        "term": term,
        "discovery_tier": discovery_tier,
        "ontology": ontology,
        "preferred_label": preferred_label,
        "class_iri": class_iri,
        "definition": definition,
        "comments": comments,
        "synonyms": synonyms,
        "parent_labels": parent_labels,
        "parent_iris": parent_iris,
        "bfo_anchor": bfo_anchor_value,
        "mapping_count": mapping_count,
        "exact_match_iris": exact_match_iris,
        "defined_by_iris": defined_by_iris,
        "conforms_to_iris": conforms_to_iris,
        "source_databases": source,
        "retrieved_at_by_database": f"{source}: {retrieved_at}",
        "ontology_versions": f"{source}: {ontology_version}" if ontology_version else "",
        "source_ontology_ids": f"{source}: {ontology}" if ontology else "",
        "source_urls": f"{source}: {source_url}" if source_url else "",
        "source_records": json.dumps(
            [
                {
                    "source": source,
                    "retrieved_at": retrieved_at,
                    "ontology": ontology,
                    "ontology_version": ontology_version,
                    "source_url": source_url,
                    "term": term,
                    "discovery_tier": discovery_tier,
                }
            ],
            ensure_ascii=False,
        ),
    }
    return row


def dedupe_key(row: dict[str, Any]) -> tuple[str, str]:
    iri = str(row.get("class_iri", "")).strip()
    if iri:
        return ("iri", iri)
    label_key = "|".join(
        [
            str(row.get("ontology", "")).lower(),
            str(row.get("preferred_label", "")).lower(),
            str(row.get("term", "")).lower(),
        ]
    )
    return ("fallback", label_key)


def merge_row(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    fill_if_blank = [
        "ontology",
        "preferred_label",
        "class_iri",
        "synonyms",
        "parent_labels",
        "parent_iris",
        "bfo_anchor",
        "mapping_count",
        "exact_match_iris",
        "defined_by_iris",
        "conforms_to_iris",
    ]
    for field in fill_if_blank:
        if not existing.get(field) and incoming.get(field) not in (None, ""):
            existing[field] = incoming[field]

    for field in ["definition", "comments", "exact_match_iris", "defined_by_iris", "conforms_to_iris"]:
        for part in clean_list(str(incoming.get(field, "")).split(";")):
            existing[field] = append_unique(str(existing.get(field, "")), part)

    for field in [
        "discovery_tier",
        "source_databases",
        "retrieved_at_by_database",
        "ontology_versions",
        "source_ontology_ids",
        "source_urls",
    ]:
        for part in clean_list(str(incoming.get(field, "")).split(";")):
            existing[field] = append_unique(str(existing.get(field, "")), part)

    try:
        existing_records = json.loads(existing.get("source_records", "[]") or "[]")
        incoming_records = json.loads(incoming.get("source_records", "[]") or "[]")
        seen = {(r.get("source"), r.get("ontology"), r.get("retrieved_at")) for r in existing_records}
        for record in incoming_records:
            key = (record.get("source"), record.get("ontology"), record.get("retrieved_at"))
            if key not in seen:
                existing_records.append(record)
                seen.add(key)
        existing["source_records"] = json.dumps(existing_records, ensure_ascii=False)
    except json.JSONDecodeError:
        existing["source_records"] = incoming.get("source_records", existing.get("source_records", ""))


def normalise_compound_label(text: str) -> str:
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(text or ""))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def label_matches_search_term(label: str, term: str) -> bool:
    return normalise_compound_label(label) == normalise_compound_label(term)


def primary_covered_ontology_ids(rows: list[dict[str, Any]]) -> set[str]:
    secondary_terms = {normalise_compound_label(term) for term in SECONDARY_SENSITIVITY_TERMS}
    covered: set[str] = set()
    for row in rows:
        tiers = {part.strip() for part in str(row.get("discovery_tier", "")).split(";") if part.strip()}
        term_key = normalise_compound_label(row.get("term", ""))
        if SECONDARY_DISCOVERY_TIER in tiers or term_key in secondary_terms or term_key in NON_DISEASE_CONTEXT_TERMS:
            continue
        covered.update(row_source_ontology_ids(row))
    return {ontology.casefold() for ontology in covered if ontology}


def filter_secondary_rows_to_uncovered_ontologies(
    rows: list[dict[str, Any]],
    covered_ontology_ids: set[str],
) -> list[dict[str, Any]]:
    covered = {ontology.casefold() for ontology in covered_ontology_ids}
    compound_terms = {normalise_compound_label(term) for term in COMPOUND_LABEL_SENSITIVITY_TERMS}
    filtered = []
    for row in rows:
        # Compound labels such as "Disease, finding or disorder" are specific
        # disease/disorder-root candidates, so keep them even when the ontology
        # was already captured by a generic term such as "condition".
        if normalise_compound_label(row.get("term", "")) in compound_terms:
            filtered.append(row)
            continue
        ontology_ids = {ontology.casefold() for ontology in row_source_ontology_ids(row)}
        if ontology_ids and ontology_ids & covered:
            continue
        filtered.append(row)
    return filtered


def merge_rows(rows_by_key: dict[tuple[str, str], dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    for row in rows:
        key = dedupe_key(row)
        if key in rows_by_key:
            merge_row(rows_by_key[key], row)
        else:
            rows_by_key[key] = row


# -- BioPortal -----------------------------------------------------------------

def load_bioportal_api_key() -> str:
    key = os.environ.get("BIOPORTAL_KEY", "")
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("BIOPORTAL_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("ERROR: BIOPORTAL_KEY not found")
    return key


def bioportal_get(url: str, params: dict[str, Any], apikey: str) -> Any | None:
    request_params = {**params, "apikey": apikey}
    return get_json(url, request_params, namespace="bioportal")


def search_bioportal_exact(term: str, apikey: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    page = 1
    while True:
        data = bioportal_get(
            f"{BIOPORTAL_BASE_URL}/search",
            {
                "q": term,
                "require_exact_match": "true",
                "include": "prefLabel,definition,synonym,notation,properties",
                "pagesize": 100,
                "page": page,
            },
            apikey,
        )
        if not data:
            break
        hits.extend(data.get("collection", []))
        if not data.get("links", {}).get("nextPage"):
            break
        page += 1
        if MAX_SEARCH_PAGES and page > MAX_SEARCH_PAGES:
            print(
                f"  [cap] '{term}': stopped at {MAX_SEARCH_PAGES} pages "
                f"(~{len(hits)} raw hits). require_exact_match is not limiting "
                f"this term; exact-label matches rank first, deeper pages are "
                f"fuzzy noise.",
                file=sys.stderr,
            )
            break
    return hits


def fetch_bioportal_parents(ontology: str, class_iri: str, apikey: str) -> list[dict[str, Any]]:
    encoded = urllib.parse.quote(class_iri, safe="")
    data = bioportal_get(
        f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{encoded}/parents",
        {"include": "prefLabel"},
        apikey,
    )
    return data if isinstance(data, list) else []


def fetch_bioportal_mapping_count(ontology: str, class_iri: str, apikey: str) -> int:
    encoded = urllib.parse.quote(class_iri, safe="")
    data = bioportal_get(
        f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{encoded}/mappings",
        {},
        apikey,
    )
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return int(data.get("totalCount", len(data.get("collection", []))))
    return 0


def fetch_bioportal_class_details(ontology: str, class_iri: str, apikey: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(class_iri, safe="")
    data = bioportal_get(
        f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{encoded}",
        {"include": "prefLabel,definition,synonym,notation,properties,cui,semanticType"},
        apikey,
    )
    return data if isinstance(data, dict) else {}


def fetch_bioportal_ontology_version(ontology: str, apikey: str) -> str:
    data = bioportal_get(f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/latest_submission", {}, apikey)
    if not isinstance(data, dict):
        return ""
    parts = []
    for key in ["version", "released", "creationDate", "submissionId"]:
        value = data.get(key)
        if value:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def bioportal_rows(
    terms: list[str],
    apikey: str,
    *,
    fetch_parents: bool,
    fetch_mappings: bool,
    exact_label_only: bool,
    discovery_tier: str = PRIMARY_DISCOVERY_TIER,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    version_cache: dict[str, str] = {}

    for term in terms:
        print(f"\n-- BioPortal: searching '{term}' --", file=sys.stderr)
        hits = search_bioportal_exact(term, apikey)
        raw_count = len(hits)
        if exact_label_only:
            hits = [hit for hit in hits if label_matches_search_term(str(hit.get("prefLabel", "")), term)]
        if exact_label_only:
            print(f"   {len(hits)} exact-label hits ({raw_count} raw BioPortal hits)", file=sys.stderr)
        else:
            print(f"   {len(hits)} hits", file=sys.stderr)

        for hit in hits:
            retrieved_at = now_iso()
            iri = hit.get("@id", "")
            ontology = hit.get("links", {}).get("ontology", "").rstrip("/").split("/")[-1]
            label = hit.get("prefLabel", "").strip()
            detail = fetch_bioportal_class_details(ontology, iri, apikey) if ontology and iri else {}
            definition = join_values(
                clean_list(hit.get("definition"))
                + clean_list(detail.get("definition"))
                + extract_annotation_values(hit, DEFINITION_KEYS)
                + extract_annotation_values(detail, DEFINITION_KEYS)
            )
            comments = join_values(extract_annotation_values(hit, COMMENT_KEYS) + extract_annotation_values(detail, COMMENT_KEYS))
            synonyms = join_values(clean_list(hit.get("synonym")) + clean_list(detail.get("synonym")))
            exact_match_iris = join_values(
                extract_annotation_values(hit, EXACT_MATCH_KEYS)
                + extract_annotation_values(detail, EXACT_MATCH_KEYS)
            )
            defined_by_iris = join_values(
                extract_annotation_values(hit, DEFINED_BY_KEYS)
                + extract_annotation_values(detail, DEFINED_BY_KEYS)
            )
            conforms_to_iris = join_values(
                extract_annotation_values(hit, CONFORMS_TO_KEYS)
                + extract_annotation_values(detail, CONFORMS_TO_KEYS)
            )

            parent_labels = parent_iris = anchor = ""
            mapping_count: str | int = ""

            if ontology and ontology not in version_cache:
                version_cache[ontology] = fetch_bioportal_ontology_version(ontology, apikey)

            if fetch_parents and ontology and iri:
                parents = fetch_bioportal_parents(ontology, iri, apikey)
                parent_labels = join_values(p.get("prefLabel") for p in parents)
                parent_iris = join_values(p.get("@id") for p in parents)
                anchor = bfo_anchor([{"@id": p.get("@id", ""), "prefLabel": p.get("prefLabel", "")} for p in parents])
                if fetch_mappings:
                    mapping_count = fetch_bioportal_mapping_count(ontology, iri, apikey)

            rows.append(
                make_row(
                    term=term,
                    source="BioPortal",
                    ontology=ontology,
                    ontology_version=version_cache.get(ontology, ""),
                    preferred_label=label,
                    class_iri=iri,
                    definition=definition,
                    comments=comments,
                    synonyms=synonyms,
                    parent_labels=parent_labels,
                    parent_iris=parent_iris,
                    bfo_anchor_value=anchor,
                    mapping_count=mapping_count,
                    exact_match_iris=exact_match_iris,
                    defined_by_iris=defined_by_iris,
                    conforms_to_iris=conforms_to_iris,
                    source_url=f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{urllib.parse.quote(iri, safe='')}" if ontology and iri else "",
                    retrieved_at=retrieved_at,
                    discovery_tier=discovery_tier,
                )
            )
            note = f" [BFO: {anchor}]" if anchor else ""
            print(f"   {ontology:15s} {label}{note}", file=sys.stderr)
    return rows


# -- OLS -----------------------------------------------------------------------

def normalise_ols_base_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    return base_url if base_url.endswith("/ols4") else f"{base_url}/ols4"


def ols_get(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any | None:
    return get_json(f"{base_url.rstrip('/')}{path}", params or {}, namespace="ols")


def ols_iri_variants(iri: str) -> list[str]:
    once = urllib.parse.quote(iri, safe="")
    slash_double_encoded = once.replace("%2F", "%252F")
    twice = urllib.parse.quote(once, safe="")
    variants = []
    for value in [slash_double_encoded, once, twice]:
        if value not in variants:
            variants.append(value)
    return variants


def search_ols_exact(term: str, base_url: str) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    rows = 100
    start = 0

    while True:
        data = ols_get(
            base_url,
            "/api/search",
            {
                "q": term,
                "exact": "true",
                "type": "class",
                "queryFields": "label",
                "fieldList": "iri,label,ontology_name,ontology_prefix,description,comment,annotation,synonym,exact_synonyms,obo_id,type",
                "rows": rows,
                "start": start,
            },
        )
        response = data.get("response", {}) if isinstance(data, dict) else {}
        batch = response.get("docs", [])
        docs.extend(batch)
        num_found = int(response.get("numFound", len(docs)))
        start += rows
        if start >= num_found or not batch:
            break

    return [doc for doc in docs if label_matches_search_term(str(doc.get("label", "")), term)]


def fetch_ols_ontology_version(ontology: str, base_url: str) -> str:
    data = ols_get(base_url, f"/api/ontologies/{ontology}")
    if not isinstance(data, dict):
        return ""
    config = data.get("config") or {}
    parts = []
    for key in ["version", "versionIri", "title", "namespace"]:
        value = config.get(key) or data.get(key)
        if value:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def extract_ols_terms(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    embedded = data.get("_embedded", {})
    for key in ["terms", "classes"]:
        if isinstance(embedded.get(key), list):
            return embedded[key]
    if isinstance(data.get("terms"), list):
        return data["terms"]
    if data.get("iri") or data.get("label"):
        return [data]
    return []


def fetch_ols_parents(ontology: str, iri: str, base_url: str) -> list[dict[str, str]]:
    for encoded in ols_iri_variants(iri):
        data = ols_get(base_url, f"/api/ontologies/{ontology}/terms/{encoded}/parents")
        terms = extract_ols_terms(data)
        if terms:
            return [
                {
                    "@id": parent.get("iri", ""),
                    "prefLabel": parent.get("label", ""),
                }
                for parent in terms
            ]
    return []


def fetch_ols_term_details(ontology: str, iri: str, base_url: str) -> dict[str, Any]:
    for encoded in ols_iri_variants(iri):
        data = ols_get(base_url, f"/api/ontologies/{ontology}/terms/{encoded}")
        if isinstance(data, dict) and data:
            return data
    return {}


def ols_rows(
    terms: list[str],
    *,
    base_url: str,
    fetch_parents: bool,
    discovery_tier: str = PRIMARY_DISCOVERY_TIER,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    version_cache: dict[str, str] = {}

    for term in terms:
        print(f"\n-- OLS: searching '{term}' --", file=sys.stderr)
        hits = search_ols_exact(term, base_url)
        print(f"   {len(hits)} hits", file=sys.stderr)

        for hit in hits:
            retrieved_at = now_iso()
            iri = hit.get("iri", "")
            ontology = (hit.get("ontology_name") or hit.get("ontology_prefix") or "").lower()
            label = str(hit.get("label", "")).strip()
            detail = fetch_ols_term_details(ontology, iri, base_url) if ontology and iri else {}
            definition = join_values(
                clean_list(hit.get("description"))
                + clean_list(detail.get("description"))
                + extract_annotation_values(hit, DEFINITION_KEYS)
                + extract_annotation_values(detail, DEFINITION_KEYS)
            )
            comments = join_values(
                clean_list(hit.get("comment"))
                + clean_list(detail.get("comment"))
                + extract_annotation_values(hit, COMMENT_KEYS)
                + extract_annotation_values(detail, COMMENT_KEYS)
            )
            synonyms = join_values(clean_list(hit.get("synonym")) + clean_list(hit.get("exact_synonyms")))

            if ontology and ontology not in version_cache:
                version_cache[ontology] = fetch_ols_ontology_version(ontology, base_url)

            parent_labels = parent_iris = anchor = ""
            if fetch_parents and ontology and iri:
                parents = fetch_ols_parents(ontology, iri, base_url)
                parent_labels = join_values(p.get("prefLabel") for p in parents)
                parent_iris = join_values(p.get("@id") for p in parents)
                anchor = bfo_anchor(parents)

            rows.append(
                make_row(
                    term=term,
                    source="OLS",
                    ontology=ontology,
                    ontology_version=version_cache.get(ontology, ""),
                    preferred_label=label,
                    class_iri=iri,
                    definition=definition,
                    comments=comments,
                    synonyms=synonyms,
                    parent_labels=parent_labels,
                    parent_iris=parent_iris,
                    bfo_anchor_value=anchor,
                    source_url=f"{base_url}/api/ontologies/{ontology}/terms/{ols_iri_variants(iri)[0]}" if ontology and iri else f"{base_url}/api/search",
                    retrieved_at=retrieved_at,
                    discovery_tier=discovery_tier,
                )
            )
            print(f"   {ontology:15s} {label}", file=sys.stderr)
    return rows


# -- OBO Foundry direct scan ---------------------------------------------------

def find_ontology_product_urls(record: dict[str, Any]) -> list[str]:
    urls: list[str] = []

    def add_url(url: str) -> None:
        if url and url not in urls:
            urls.append(url)

    for product in record.get("products", []) or []:
        url = product.get("ontology_purl") or product.get("url") or product.get("id") or ""
        if str(url).endswith(".obo"):
            add_url(str(url))
    for product in record.get("products", []) or []:
        url = product.get("ontology_purl") or product.get("url") or product.get("id") or ""
        if str(url).endswith(".owl"):
            add_url(str(url))
    url = record.get("ontology_purl") or ""
    if str(url).endswith((".obo", ".owl")):
        add_url(str(url))
    return urls


def fetch_obo_registry() -> list[dict[str, Any]]:
    text = get_text(OBO_REGISTRY_URL, namespace="obo-registry")
    if not text:
        return []
    return parse_obo_registry_yaml(text)


def parse_simple_yaml_value(value: str) -> str:
    value = value.strip()
    if value in {"", "|", ">"}:
        return ""
    return value.strip("\"'")


def parse_obo_registry_yaml(text: str) -> list[dict[str, Any]]:
    """Extract the small subset of OBO registry YAML needed for direct scans."""
    records: list[dict[str, Any]] = []
    chunks = re.split(r"\n(?=- activity_status:)", text)
    for chunk in chunks:
        chunk = chunk.strip("\n")
        if not chunk.startswith("- activity_status:"):
            continue

        record: dict[str, Any] = {"products": []}
        lines = chunk.splitlines()
        in_license = False
        for line in lines:
            if line.startswith("- activity_status:"):
                record["activity_status"] = parse_simple_yaml_value(line.split(":", 1)[1])
                in_license = False
            elif match := re.match(r"^  (id|ontology_purl|title|preferredPrefix|domain|homepage|repository|description):\s*(.*)$", line):
                record[match.group(1)] = parse_simple_yaml_value(match.group(2))
                in_license = False
            elif line.startswith("  license:"):
                record["license"] = {}
                in_license = True
            elif in_license and (match := re.match(r"^    (label|url):\s*(.*)$", line)):
                record["license"][match.group(1)] = parse_simple_yaml_value(match.group(2))
            elif line.startswith("  ") and not line.startswith("    "):
                in_license = False

        products_block = re.search(r"(?ms)^  products:\n(.*?)(?=^  [A-Za-z0-9_-]+:|\Z)", chunk)
        if products_block:
            current_product: dict[str, str] | None = None
            for line in products_block.group(1).splitlines():
                if line.startswith("  - "):
                    if current_product:
                        record["products"].append(current_product)
                    current_product = {}
                    rest = line[4:]
                    if ":" in rest:
                        key, value = rest.split(":", 1)
                        current_product[key.strip()] = parse_simple_yaml_value(value)
                elif current_product is not None and (match := re.match(r"^    (id|ontology_purl|title):\s*(.*)$", line)):
                    current_product[match.group(1)] = parse_simple_yaml_value(match.group(2))
            if current_product:
                record["products"].append(current_product)

        records.append(record)
    return records


def parse_obo_header(text: str) -> dict[str, str]:
    header: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "[Term]":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            header[key.strip()] = value.strip()
    return header


def parse_obo_stanza(stanza: dict[str, list[str]], terms_lower: set[str]) -> dict[str, Any] | None:
    names = clean_list(stanza.get("name"))
    if not names:
        return None
    name = names[0]
    if normalise_compound_label(name) not in terms_lower:
        return None
    if first_clean(stanza.get("is_obsolete")).lower() == "true":
        return None

    curie = first_clean(stanza.get("id"))
    definition = ""
    if stanza.get("def"):
        match = re.search(r'"(.*?)"', stanza["def"][0])
        definition = match.group(1) if match else stanza["def"][0]
    comments = join_values(stanza.get("comment"))

    synonyms = []
    for synonym_line in stanza.get("synonym", []):
        match = re.search(r'"(.*?)"', synonym_line)
        if match:
            synonyms.append(match.group(1))

    parents: list[dict[str, str]] = []
    for parent_line in stanza.get("is_a", []):
        parent_curie = parent_line.split()[0]
        parent_label = parent_line.split("!", 1)[1].strip() if "!" in parent_line else ""
        parents.append({"@id": obo_curie_to_iri(parent_curie), "prefLabel": parent_label})

    return {
        "term": name,
        "preferred_label": name,
        "class_iri": obo_curie_to_iri(curie) if curie else "",
        "definition": definition,
        "comments": comments,
        "synonyms": join_values(synonyms),
        "parent_labels": join_values(p.get("prefLabel") for p in parents),
        "parent_iris": join_values(p.get("@id") for p in parents),
        "bfo_anchor": bfo_anchor(parents),
    }


def scan_obo_text(text: str, terms: list[str]) -> tuple[str, list[dict[str, Any]]]:
    header = parse_obo_header(text)
    version = header.get("data-version") or header.get("date") or header.get("format-version") or ""
    terms_lower = {normalise_compound_label(term) for term in terms}

    rows: list[dict[str, Any]] = []
    current_kind = ""
    current: dict[str, list[str]] = {}

    def flush_current() -> None:
        if current_kind != "Term" or not current:
            return
        parsed = parse_obo_stanza(current, terms_lower)
        if parsed:
            rows.append(parsed)

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
    return version, rows


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def child_texts(element: ET.Element, names: set[str]) -> list[str]:
    values = []
    for child in element:
        if local_name(child.tag) in names and child.text and child.text.strip():
            values.append(child.text.strip())
    return values


def scan_owl_xml_text(text: str, terms: list[str]) -> tuple[str, list[dict[str, Any]]]:
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as exc:
        print(f"  [warn] OWL/XML parse failed: {exc}", file=sys.stderr)
        return "", []

    rdf_about = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"
    rdf_resource = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
    owl_version_iri = "{http://www.w3.org/2002/07/owl#}versionIRI"
    owl_version_info = "{http://www.w3.org/2002/07/owl#}versionInfo"
    terms_lower = {normalise_compound_label(term) for term in terms}

    version = ""
    for ontology in root.iter("{http://www.w3.org/2002/07/owl#}Ontology"):
        for child in ontology:
            if child.tag == owl_version_iri and child.attrib.get(rdf_resource):
                version = child.attrib[rdf_resource]
                break
            if child.tag == owl_version_info and child.text:
                version = child.text.strip()
                break
        if version:
            break

    rows: list[dict[str, Any]] = []
    class_elements = list(root.iter("{http://www.w3.org/2002/07/owl#}Class"))
    for element in class_elements:
        iri = element.attrib.get(rdf_about, "")
        if not iri:
            continue
        label = first_clean(child_texts(element, {"label"}))
        if not label or normalise_compound_label(label) not in terms_lower:
            continue

        definitions = child_texts(element, {"IAO_0000115", "definition"})
        comments = child_texts(element, {"comment"})
        synonyms = []
        for child in element:
            name = local_name(child.tag)
            if "Synonym" in name and child.text and child.text.strip():
                synonyms.append(child.text.strip())

        parent_iris = []
        for child in element:
            if local_name(child.tag) == "subClassOf" and child.attrib.get(rdf_resource):
                parent_iris.append(child.attrib[rdf_resource])
        parents = [{"@id": parent_iri, "prefLabel": ""} for parent_iri in parent_iris]

        rows.append(
            {
                "term": label,
                "preferred_label": label,
                "class_iri": iri,
                "definition": first_clean(definitions),
                "comments": join_values(comments),
                "synonyms": join_values(synonyms),
                "parent_labels": "",
                "parent_iris": join_values(parent_iris),
                "bfo_anchor": bfo_anchor(parents),
            }
        )
    return version, rows


def scan_ontology_text(text: str, terms: list[str]) -> tuple[str, list[dict[str, Any]]]:
    stripped = text.lstrip()
    if stripped.startswith("format-version:") or "\n[Term]" in stripped[:5000]:
        return scan_obo_text(text, terms)
    if stripped.startswith("<?xml") or stripped.startswith("<rdf:RDF") or stripped.startswith("<Ontology"):
        return scan_owl_xml_text(text, terms)
    print("  [warn] ontology format not supported for direct OBO Foundry scan", file=sys.stderr)
    return "", []


def fetch_bioportal_ontology_ids(apikey: str) -> set[str]:
    """Return lowercased acronyms of all ontologies indexed in BioPortal."""
    data = get_json(
        f"{BIOPORTAL_BASE_URL}/ontologies",
        {"apikey": apikey, "display_links": "false", "display_context": "false"},
        namespace="bioportal",
    )
    if not isinstance(data, list):
        return set()
    ids = {str(o.get("acronym", "")).lower() for o in data if o.get("acronym")}
    print(f"   BioPortal indexes {len(ids)} ontologies — OBO scan will skip these", file=sys.stderr)
    return ids


def obo_rows(
    terms: list[str],
    *,
    max_ontologies: int | None,
    skip_ids: set[str] | None = None,
    discovery_tier: str = PRIMARY_DISCOVERY_TIER,
) -> list[dict[str, Any]]:
    print("\n-- OBO Foundry: loading registry --", file=sys.stderr)
    registry = fetch_obo_registry()
    active_records = [
        record for record in registry
        if str(record.get("activity_status", "active")).lower() not in {"inactive", "obsolete"}
    ]
    if skip_ids:
        before = len(active_records)
        active_records = [r for r in active_records if str(r.get("id", "")).lower() not in skip_ids]
        print(f"   skipped {before - len(active_records)} ontologies already indexed in BioPortal", file=sys.stderr)
    if max_ontologies is not None:
        active_records = active_records[:max_ontologies]
    print(f"   scanning {len(active_records)} OBO ontologies not in BioPortal", file=sys.stderr)

    rows: list[dict[str, Any]] = []
    for record in active_records:
        ontology = str(record.get("id", "")).lower()
        urls = find_ontology_product_urls(record)
        if not ontology or not urls:
            continue
        text = None
        url = ""
        for candidate_url in urls:
            print(f"   OBO {ontology}: {candidate_url}", file=sys.stderr)
            text = get_text(candidate_url, namespace="obo-files")
            if text:
                url = candidate_url
                break
        if not text:
            continue
        version, parsed_rows = scan_ontology_text(text, terms)
        retrieved_at = now_iso()
        for parsed in parsed_rows:
            rows.append(
                make_row(
                    term=parsed["term"],
                    source="OBO Foundry Direct",
                    ontology=ontology,
                    ontology_version=version,
                    preferred_label=parsed["preferred_label"],
                    class_iri=parsed["class_iri"],
                    definition=parsed["definition"],
                    comments=parsed["comments"],
                    synonyms=parsed["synonyms"],
                    parent_labels=parsed["parent_labels"],
                    parent_iris=parsed["parent_iris"],
                    bfo_anchor_value=parsed["bfo_anchor"],
                    source_url=url,
                    retrieved_at=retrieved_at,
                    discovery_tier=discovery_tier,
                )
            )
    return rows


# -- Review enrichment ---------------------------------------------------------

ENRICHMENT_FIELDNAMES = [
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
    "native_source_ontology_ids",
    "dependent_source_ontology_ids",
    "dependency_on_ontology_ids",
    "source_appearance_summary",
    "review_route",
    "manual_screening_hint",
]


def source_records(row: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        records = json.loads(row.get("source_records", "") or "[]")
    except json.JSONDecodeError:
        records = []
    return records if isinstance(records, list) else []


def row_source_ontology_ids(row: dict[str, Any]) -> set[str]:
    ids = {str(row.get("ontology", "")).lower()} if row.get("ontology") else set()
    for record in source_records(row):
        ontology = record.get("ontology")
        if ontology:
            ids.add(str(ontology).lower())
    return {ontology for ontology in ids if ontology}


def normalise_bioportal_ontology_metadata(data: dict[str, Any], *, retrieved_at: str | None = None) -> dict[str, str]:
    retrieved_at = retrieved_at or now_iso()
    title = first_clean([data.get("name"), data.get("acronym")])
    description = join_values(clean_list(data.get("summary")) + clean_list(data.get("description")))
    homepage = first_clean(data.get("homepage"))
    license_value = first_clean(data.get("license"))
    status = first_clean([data.get("status"), data.get("viewingRestriction")])
    domain = join_values(
        clean_list(data.get("group"))
        + clean_list(data.get("groups"))
        + clean_list(data.get("category"))
        + clean_list(data.get("categories"))
    )
    return {
        "ontology_title": title,
        "ontology_description": description,
        "ontology_domain": domain,
        "ontology_homepage": homepage,
        "ontology_repository": "",
        "ontology_license": license_value,
        "ontology_status": status,
        "ontology_metadata_source": "BioPortal ontology metadata",
        "ontology_metadata_retrieved_at": retrieved_at,
    }


def fetch_bioportal_ontology_metadata_index(apikey: str) -> dict[str, dict[str, str]]:
    data = bioportal_get(
        f"{BIOPORTAL_BASE_URL}/ontologies",
        {"display_links": "false", "display_context": "false"},
        apikey,
    )
    if not isinstance(data, list):
        return {}
    retrieved_at = now_iso()
    index = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        acronym = item.get("acronym")
        if acronym:
            index[str(acronym).lower()] = normalise_bioportal_ontology_metadata(item, retrieved_at=retrieved_at)
    return index


def obo_registry_metadata_by_id() -> dict[str, dict[str, str]]:
    records = fetch_obo_registry()
    metadata: dict[str, dict[str, str]] = {}
    for record in records:
        ontology_id = str(record.get("id", "")).lower()
        if not ontology_id:
            continue
        license_value = ""
        license_data = record.get("license")
        if isinstance(license_data, dict):
            license_value = first_clean([license_data.get("label"), license_data.get("url")])
        elif license_data:
            license_value = str(license_data)
        metadata[ontology_id] = {
            "ontology_title": first_clean([record.get("title"), record.get("preferredPrefix"), ontology_id]),
            "ontology_description": first_clean(record.get("description")),
            "ontology_domain": first_clean(record.get("domain")),
            "ontology_homepage": first_clean(record.get("homepage")),
            "ontology_repository": first_clean(record.get("repository")),
            "ontology_license": license_value,
            "ontology_status": first_clean(record.get("activity_status")),
            "ontology_metadata_source": "OBO Foundry registry",
            "ontology_metadata_retrieved_at": now_iso(),
        }
    return metadata


def ontology_text(row: dict[str, Any]) -> str:
    parts = [
        row.get("ontology", ""),
        row.get("ontology_title", ""),
        row.get("ontology_description", ""),
        row.get("ontology_homepage", ""),
        row.get("ontology_repository", ""),
        row.get("source_ontology_ids", ""),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def is_thesaurus_resource(row: dict[str, Any]) -> bool:
    ontology = str(row.get("ontology", "") or row.get("source_ontology_id", "")).lower().strip()
    text = ontology_text(row)
    return ontology in THESAURUS_ONTOLOGY_IDS or any(phrase in text for phrase in THESAURUS_METADATA_PHRASES)


def infer_ontology_scope_category(row: dict[str, Any]) -> str:
    text = ontology_text(row)
    ontology = row.get("ontology", "").lower()
    if re.search(r"\b(demo|tutorial|training|example|sample|student|thesis)\b", text):
        return "demo_or_training_resource"
    if "generated-ontology" in text or "generated ontology" in text:
        return "generated_or_local_ontology"
    if "value set" in text or ontology in {"valuesets"}:
        return "value_set_or_collection"
    if is_thesaurus_resource(row):
        return "thesaurus"
    if ontology in {"snomedct", "loinc", "icd10", "icd9cm", "icpc2p", "ndfrt", "medgen"}:
        return "clinical_or_biomedical_terminology"
    if ontology in {"ncit", "doid", "mondo", "efo", "ogms", "obi", "sio"}:
        return "curated_biomedical_ontology"
    if "obo foundry" in row.get("ontology_metadata_source", "").lower():
        return "obo_foundry_ontology"
    return "ontology_or_terminology_candidate"


def preassert_exclusion(row: dict[str, Any]) -> tuple[str, str, str]:
    # OBO Foundry ontologies are accepted at the ontology level by standing policy.
    if (
        row.get("ontology_scope_category") == "obo_foundry_ontology"
        or str(row.get("class_iri", "")).startswith("http://purl.obolibrary.org/obo/")
        or "OBO Foundry Direct" in str(row.get("source_databases", ""))
    ):
        return ("candidate", "", "")
    text = ontology_text(row)
    status = row.get("ontology_status", "").lower()
    ontology = row.get("ontology", "").lower()
    if any(token in status for token in ["obsolete", "inactive", "deprecated", "retired"]):
        return ("excluded_preasserted", "E1_status_noncurrent", "Ontology metadata indicates obsolete/inactive/deprecated/retired status.")
    if re.search(r"\b(demo|tutorial|training|example|sample|student|thesis)\b", text):
        return ("excluded_preasserted", "E2_demo_training_or_thesis", "Ontology appears to be a demo, training, student, sample, or thesis resource.")
    if "generated-ontology" in text or "generated ontology" in text:
        return ("excluded_preasserted", "E3_generated_local_ontology", "Ontology appears to be generated/local rather than a reusable published ontology.")
    if "value set" in text or ontology in {"valuesets"}:
        return ("excluded_preasserted", "E4_value_set_collection", "Resource appears to be a value-set collection rather than an ontology implementation.")
    if is_thesaurus_resource(row):
        return ("excluded_preasserted", "E5_thesaurus_title", "Ontology ID or metadata indicates a thesaurus or controlled vocabulary rather than an independent ontology implementation.")
    return ("candidate", "", "")


def infer_native_ontology_guess(class_iri: str) -> str:
    iri = class_iri or ""
    patterns = [
        (r"purl\.obolibrary\.org/obo/([A-Za-z0-9]+)_", None),
        (r"ebi\.ac\.uk/efo/(EFO)_", None),
        (r"ncicb\.nci\.nih\.gov/.+#C[0-9]+", "ncit"),
        (r"bioontology\.org/ontology/LNC/", "loinc"),
        (r"snomed\.info/id/", "snomedct"),
        (r"semanticscience\.org/resource/", "sio"),
        (r"w3id\.org/biolink", "biolink"),
    ]
    for pattern, fixed in patterns:
        match = re.search(pattern, iri, re.IGNORECASE)
        if match:
            return (fixed or match.group(1)).lower()
    return ""


def infer_native_term_status(row: dict[str, Any]) -> tuple[str, str]:
    native_guess = infer_native_ontology_guess(row.get("class_iri", ""))
    ontology_ids = row_source_ontology_ids(row)
    if not native_guess:
        return "", "unknown_native_ontology"
    if native_guess in ontology_ids:
        if len(ontology_ids) > 1:
            return native_guess, "native_source_seen_with_imports"
        return native_guess, "native_source_seen"
    return native_guess, "likely_imported_or_reused_term"


def normalise_ontology_id_for_dependency(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def classify_source_appearances(row: dict[str, Any]) -> dict[str, str]:
    """Separate native class definitions from imported/reused source appearances.

    The review unit is the class IRI. Registry source records often include many
    ontologies that merely import the same IRI. Those should be counted as reuse
    evidence, not as independent disease-modelling implementations.
    """
    native_guess = infer_native_ontology_guess(row.get("class_iri", ""))
    native_key = normalise_ontology_id_for_dependency(native_guess)
    native_sources: list[str] = []
    dependent_sources: list[str] = []
    unknown_sources: list[str] = []

    records = source_records(row)
    if not records and row.get("ontology"):
        records = [{"source": "", "ontology": row.get("ontology", "")}]

    for record in records:
        source = str(record.get("source", "")).strip()
        ontology = str(record.get("ontology", "")).strip()
        if not ontology:
            continue
        source_id = f"{source}: {ontology}" if source else ontology
        ontology_key = normalise_ontology_id_for_dependency(ontology)
        if not native_key:
            unknown_sources.append(source_id)
        elif ontology_key == native_key:
            native_sources.append(source_id)
        else:
            dependent_sources.append(source_id)

    native_sources = list(dict.fromkeys(native_sources))
    dependent_sources = list(dict.fromkeys(dependent_sources))
    unknown_sources = list(dict.fromkeys(unknown_sources))
    dependencies = [native_guess] if native_guess and dependent_sources else []

    if native_sources and dependent_sources:
        route = "independent_class_review_with_dependency_appearances"
    elif native_sources:
        route = "independent_class_review"
    elif dependent_sources and native_guess:
        route = "dependency_only_no_independent_analysis"
    else:
        route = "unknown_namespace_needs_manual_check"

    summary_bits = []
    if native_sources:
        summary_bits.append(f"native in {', '.join(native_sources[:8])}{' ...' if len(native_sources) > 8 else ''}")
    if dependent_sources:
        summary_bits.append(
            f"imported/reused in {len(dependent_sources)} source ontology appearance(s); depends on {native_guess}"
            if native_guess
            else f"appears in {len(dependent_sources)} source ontology appearance(s); native source unknown"
        )
    if unknown_sources:
        summary_bits.append(f"unknown namespace in {len(unknown_sources)} source ontology appearance(s)")

    return {
        "native_source_ontology_ids": "; ".join(native_sources),
        "dependent_source_ontology_ids": "; ".join(dependent_sources),
        "dependency_on_ontology_ids": "; ".join(dependencies),
        "source_appearance_summary": "; ".join(summary_bits),
        "review_route": route,
    }


def manual_screening_hint(row: dict[str, Any]) -> str:
    hints = []
    if row.get("ontology_exclusion_status") == "excluded_preasserted":
        hints.append("preasserted ontology-level exclusion; verify before final exclusion")
    if not row.get("definition"):
        hints.append("missing definition")
    if not row.get("comments"):
        hints.append("missing comment")
    if row.get("native_term_status") == "likely_imported_or_reused_term":
        hints.append("term IRI namespace suggests imported/reused class")
    if row.get("ontology_scope_category") == "clinical_or_biomedical_terminology":
        hints.append("terminology/resource rather than strict ontology; decide scope")
    return "; ".join(hints)


def enrich_rows(rows: list[dict[str, Any]], *, apikey: str | None = None) -> list[dict[str, Any]]:
    apikey = apikey or load_bioportal_api_key()
    obo_metadata = obo_registry_metadata_by_id()
    bioportal_metadata = fetch_bioportal_ontology_metadata_index(apikey)

    enriched = []
    for row in rows:
        row = dict(row)
        ontology = row.get("ontology", "")
        ontology_key = ontology.lower()
        metadata = {}
        if ontology_key in obo_metadata:
            metadata.update(obo_metadata[ontology_key])
        if ontology_key in bioportal_metadata:
            for key, value in bioportal_metadata[ontology_key].items():
                if value:
                    metadata[key] = value

        for field in ENRICHMENT_FIELDNAMES:
            row.setdefault(field, "")
        row.update({key: value for key, value in metadata.items() if key in ENRICHMENT_FIELDNAMES})

        row["ontology_scope_category"] = infer_ontology_scope_category(row)
        status, rule, reason = preassert_exclusion(row)
        row["ontology_exclusion_status"] = status
        row["ontology_exclusion_rule"] = rule
        row["ontology_exclusion_reason"] = reason
        native_guess, native_status = infer_native_term_status(row)
        row["native_ontology_guess"] = native_guess
        row["native_term_status"] = native_status
        row.update(classify_source_appearances(row))
        row["manual_screening_hint"] = manual_screening_hint(row)
        enriched.append(row)
    return enriched


def refresh_row_class_annotations(row: dict[str, Any], *, apikey: str, ols_base_url: str = OLS_BASE_URL) -> dict[str, Any]:
    row = dict(row)
    class_iri = row.get("class_iri", "")
    if not class_iri:
        return row

    bioportal_ontologies = []
    if "BioPortal" in row.get("source_databases", "") and row.get("ontology"):
        bioportal_ontologies.append(row["ontology"])
    for record in source_records(row):
        if record.get("source") == "BioPortal" and record.get("ontology"):
            bioportal_ontologies.append(str(record["ontology"]))
    bioportal_ontologies = list(dict.fromkeys(bioportal_ontologies))[:3]

    definitions = clean_list(str(row.get("definition", "")).split(";"))
    comments = clean_list(str(row.get("comments", "")).split(";"))
    synonyms = clean_list(str(row.get("synonyms", "")).split(";"))
    exact_match_iris = clean_list(str(row.get("exact_match_iris", "")).split(";"))
    defined_by_iris = clean_list(str(row.get("defined_by_iris", "")).split(";"))
    conforms_to_iris = clean_list(str(row.get("conforms_to_iris", "")).split(";"))

    for ontology in bioportal_ontologies:
        detail = fetch_bioportal_class_details(ontology, class_iri, apikey)
        definitions.extend(clean_list(detail.get("definition")) + extract_annotation_values(detail, DEFINITION_KEYS))
        comments.extend(extract_annotation_values(detail, COMMENT_KEYS))
        synonyms.extend(clean_list(detail.get("synonym")))
        exact_match_iris.extend(extract_annotation_values(detail, EXACT_MATCH_KEYS))
        defined_by_iris.extend(extract_annotation_values(detail, DEFINED_BY_KEYS))
        conforms_to_iris.extend(extract_annotation_values(detail, CONFORMS_TO_KEYS))

    for record in source_records(row):
        if record.get("source") != "OLS" or not record.get("ontology"):
            continue
        detail = fetch_ols_term_details(str(record["ontology"]), class_iri, normalise_ols_base_url(ols_base_url))
        definitions.extend(clean_list(detail.get("description")) + extract_annotation_values(detail, DEFINITION_KEYS))
        comments.extend(clean_list(detail.get("comment")) + extract_annotation_values(detail, COMMENT_KEYS))
        synonyms.extend(clean_list(detail.get("synonym")) + clean_list(detail.get("exact_synonyms")))
        exact_match_iris.extend(extract_annotation_values(detail, EXACT_MATCH_KEYS))
        defined_by_iris.extend(extract_annotation_values(detail, DEFINED_BY_KEYS))
        conforms_to_iris.extend(extract_annotation_values(detail, CONFORMS_TO_KEYS))

    row["definition"] = join_values(definitions)
    row["comments"] = join_values(comments)
    row["synonyms"] = join_values(synonyms)
    row["exact_match_iris"] = join_values(exact_match_iris)
    row["defined_by_iris"] = join_values(defined_by_iris)
    row["conforms_to_iris"] = join_values(conforms_to_iris)
    return row


def refresh_class_annotations(rows: list[dict[str, Any]], *, ols_base_url: str = OLS_BASE_URL) -> list[dict[str, Any]]:
    apikey = load_bioportal_api_key()
    refreshed = []
    for index, row in enumerate(rows, start=1):
        if index % 25 == 0:
            print(f"  refreshed annotations for {index}/{len(rows)} rows", file=sys.stderr)
        refreshed.append(refresh_row_class_annotations(row, apikey=apikey, ols_base_url=ols_base_url))
    return refreshed


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def enrich_existing_csv(in_path: Path, out_path: Path, *, refresh_annotations: bool = False) -> None:
    rows = read_csv_rows(in_path)
    if refresh_annotations:
        rows = refresh_class_annotations(rows)
    fieldnames = list(dict.fromkeys(list(rows[0].keys() if rows else FIELDNAMES) + ENRICHMENT_FIELDNAMES))
    enriched = enrich_rows(rows)
    write_csv_rows(out_path, enriched, fieldnames)
    excluded = sum(row.get("ontology_exclusion_status") == "excluded_preasserted" for row in enriched)
    print(f"Enriched {len(enriched)} rows -> {out_path} ({excluded} preasserted ontology exclusions)")


# -- Main ----------------------------------------------------------------------

FIELDNAMES = [
    "term",
    "discovery_tier",
    "ontology",
    "preferred_label",
    "class_iri",
    "definition",
    "comments",
    "synonyms",
    "parent_labels",
    "parent_iris",
    "bfo_anchor",
    "mapping_count",
    "exact_match_iris",
    "defined_by_iris",
    "conforms_to_iris",
    "source_databases",
    "retrieved_at_by_database",
    "ontology_versions",
    "source_ontology_ids",
    "source_urls",
    "source_records",
]


def load_existing_rows(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    if not path.exists():
        return rows_by_key
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for field in FIELDNAMES:
                row.setdefault(field, "")
            rows_by_key[dedupe_key(row)] = row
    return rows_by_key


def parse_sources(raw_sources: str) -> list[str]:
    allowed = {"bioportal", "ols", "obo"}
    sources = [source.strip().lower() for source in raw_sources.split(",") if source.strip()]
    unknown = [source for source in sources if source not in allowed]
    if unknown:
        sys.exit(f"ERROR: unknown source(s): {', '.join(unknown)}")
    if "bioportal" not in sources:
        print("[warn] BioPortal is not selected; add-on sources will run without the primary pass.", file=sys.stderr)
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--enrich-existing",
        default="",
        help="Read an existing extraction CSV and add ontology metadata/native-term/exclusion columns without rerunning searches.",
    )
    parser.add_argument(
        "--enriched-out",
        default="",
        help="Output path for --enrich-existing. Default: <input stem>_enriched.csv",
    )
    parser.add_argument(
        "--refresh-class-annotations",
        action="store_true",
        help="With --enrich-existing, refetch class-detail records to improve definitions/comments/synonyms.",
    )
    parser.add_argument(
        "--sources",
        default="bioportal,ols,obo",
        help="Comma-separated sources to run: bioportal,ols,obo. BioPortal is searched first when included.",
    )
    parser.add_argument(
        "--ols-base-url",
        default=os.environ.get("OLS_BASE_URL", OLS_BASE_URL),
        help="OLS base URL. Defaults to https://www.ebi.ac.uk/ols4. Tunnel URLs can be passed here.",
    )
    parser.add_argument(
        "--obo-max-ontologies",
        type=int,
        default=None,
        help="Limit direct OBO scans for testing. Default: scan all active registry ontologies.",
    )
    parser.add_argument("--no-parents", action="store_true", help="Skip parent fetches")
    parser.add_argument("--no-mappings", action="store_true", help="Skip BioPortal mapping count fetch")
    parser.add_argument(
        "--include-nonlabel-matches",
        action="store_true",
        help="Keep broader BioPortal exact-search hits whose preferred label is not exactly the searched term.",
    )
    parser.add_argument("--terms", default="", help="Override term list (comma-separated)")
    parser.add_argument("--resume", action="store_true", help="Merge into existing output file if present")
    parser.add_argument(
        "--no-enrich-output",
        action="store_true",
        help="Write only raw extraction columns for a fresh search run.",
    )
    args = parser.parse_args()

    if args.enrich_existing:
        in_path = Path(args.enrich_existing)
        out_path = Path(args.enriched_out) if args.enriched_out else in_path.with_name(f"{in_path.stem}_enriched.csv")
        enrich_existing_csv(in_path, out_path, refresh_annotations=args.refresh_class_annotations)
        return

    sources = parse_sources(args.sources)
    terms = [term.strip() for term in args.terms.split(",") if term.strip()] if args.terms else DEFAULT_TERMS
    out_path = Path(args.out)
    rows_by_key = load_existing_rows(out_path) if args.resume else {}

    if rows_by_key:
        print(f"[resume] loaded {len(rows_by_key)} existing merged rows", file=sys.stderr)

    for source in sources:
        if source == "bioportal":
            apikey = load_bioportal_api_key()
            merge_rows(
                rows_by_key,
                bioportal_rows(
                    terms,
                    apikey,
                    fetch_parents=not args.no_parents,
                    fetch_mappings=not args.no_mappings,
                    exact_label_only=not args.include_nonlabel_matches,
                ),
            )
        elif source == "ols":
            ols_base_url = normalise_ols_base_url(args.ols_base_url)
            merge_rows(rows_by_key, ols_rows(terms, base_url=ols_base_url, fetch_parents=not args.no_parents))
        elif source == "obo":
            bp_ids = fetch_bioportal_ontology_ids(load_bioportal_api_key()) if "bioportal" in sources else set()
            merge_rows(rows_by_key, obo_rows(terms, max_ontologies=args.obo_max_ontologies, skip_ids=bp_ids))

    output_rows = sorted(
        rows_by_key.values(),
        key=lambda r: (r.get("term", ""), r.get("ontology", ""), r.get("class_iri", "")),
    )
    output_fieldnames = FIELDNAMES
    if not args.no_enrich_output:
        output_rows = enrich_rows(output_rows)
        output_fieldnames = FIELDNAMES + ENRICHMENT_FIELDNAMES
    write_csv_rows(out_path, output_rows, output_fieldnames)

    print(f"\nDone. {len(rows_by_key)} merged rows -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
