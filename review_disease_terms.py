#!/usr/bin/env python3
"""
review_disease_terms.py - multi-source survey of disease-modelling root terms

BioPortal is searched first and remains the primary source. OLS and direct OBO
Foundry scans are additive: when they return the same class IRI, the row is
merged and the extra source is recorded in provenance rather than duplicated.

Terms searched (exact preferred label/name match):
    disease, disorder, injury, illness, condition, syndrome,
    pathological process, pathological disposition, dysfunction, predisposition

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
OBO_REGISTRY_URL = "https://obofoundry.org/registry/ontologies.json"

CACHE_DIR = Path("/tmp/disease_terms_review_cache")

DEFAULT_TERMS = [
    "disease",
    "disorder",
    "injury",
    "illness",
    "condition",
    "syndrome",
    "pathological process",
    "pathological disposition",
    "dysfunction",
    "predisposition",
]

BFO_PREFIX = "http://purl.obolibrary.org/obo/BFO_"
DELAY = 0.12


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
        iri = parent.get("@id", "")
        if iri.startswith(BFO_PREFIX):
            label = parent.get("prefLabel", "").strip()
            return f"{label} ({iri.split('BFO_')[1]})" if label else iri
    return ""


def obo_curie_to_iri(curie: str) -> str:
    return f"http://purl.obolibrary.org/obo/{curie.replace(':', '_')}"


def make_row(
    *,
    term: str,
    source: str,
    ontology: str,
    ontology_version: str = "",
    preferred_label: str = "",
    class_iri: str = "",
    definition: str = "",
    synonyms: str = "",
    parent_labels: str = "",
    parent_iris: str = "",
    bfo_anchor_value: str = "",
    mapping_count: str | int = "",
    source_url: str = "",
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    retrieved_at = retrieved_at or now_iso()
    row = {
        "term": term,
        "ontology": ontology,
        "preferred_label": preferred_label,
        "class_iri": class_iri,
        "definition": definition,
        "synonyms": synonyms,
        "parent_labels": parent_labels,
        "parent_iris": parent_iris,
        "bfo_anchor": bfo_anchor_value,
        "mapping_count": mapping_count,
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
        "definition",
        "synonyms",
        "parent_labels",
        "parent_iris",
        "bfo_anchor",
        "mapping_count",
    ]
    for field in fill_if_blank:
        if not existing.get(field) and incoming.get(field) not in (None, ""):
            existing[field] = incoming[field]

    for field in [
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
                "include": "prefLabel,definition,synonym,notation",
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
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    version_cache: dict[str, str] = {}

    for term in terms:
        print(f"\n-- BioPortal: searching '{term}' --", file=sys.stderr)
        hits = search_bioportal_exact(term, apikey)
        print(f"   {len(hits)} hits", file=sys.stderr)

        for hit in hits:
            retrieved_at = now_iso()
            iri = hit.get("@id", "")
            ontology = hit.get("links", {}).get("ontology", "").rstrip("/").split("/")[-1]
            label = hit.get("prefLabel", "").strip()
            definition = first_clean(hit.get("definition"))
            synonyms = join_values(hit.get("synonym"))

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
                    synonyms=synonyms,
                    parent_labels=parent_labels,
                    parent_iris=parent_iris,
                    bfo_anchor_value=anchor,
                    mapping_count=mapping_count,
                    source_url=f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{urllib.parse.quote(iri, safe='')}" if ontology and iri else "",
                    retrieved_at=retrieved_at,
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

    term_lower = term.casefold()
    return [doc for doc in docs if str(doc.get("label", "")).casefold() == term_lower]


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


def ols_rows(
    terms: list[str],
    *,
    base_url: str,
    fetch_parents: bool,
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
            definition = first_clean(hit.get("description"))
            synonyms = join_values(hit.get("synonym"))

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
                    synonyms=synonyms,
                    parent_labels=parent_labels,
                    parent_iris=parent_iris,
                    bfo_anchor_value=anchor,
                    source_url=f"{base_url}/api/ontologies/{ontology}/terms/{ols_iri_variants(iri)[0]}" if ontology and iri else f"{base_url}/api/search",
                    retrieved_at=retrieved_at,
                )
            )
            print(f"   {ontology:15s} {label}", file=sys.stderr)
    return rows


# -- OBO Foundry direct scan ---------------------------------------------------

def find_obo_product_url(record: dict[str, Any]) -> str:
    for product in record.get("products", []) or []:
        url = product.get("ontology_purl") or product.get("url") or product.get("id") or ""
        if str(url).endswith(".obo"):
            return str(url)
    url = record.get("ontology_purl") or ""
    if str(url).endswith(".obo"):
        return str(url)
    ontology_id = record.get("id", "")
    return f"https://purl.obolibrary.org/obo/{ontology_id}.obo" if ontology_id else ""


def fetch_obo_registry() -> list[dict[str, Any]]:
    data = get_json(OBO_REGISTRY_URL, namespace="obo-registry")
    if isinstance(data, dict):
        return data.get("ontologies", []) or []
    if isinstance(data, list):
        return data
    return []


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
    if name.casefold() not in terms_lower:
        return None
    if first_clean(stanza.get("is_obsolete")).lower() == "true":
        return None

    curie = first_clean(stanza.get("id"))
    definition = ""
    if stanza.get("def"):
        match = re.search(r'"(.*?)"', stanza["def"][0])
        definition = match.group(1) if match else stanza["def"][0]

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
        "synonyms": join_values(synonyms),
        "parent_labels": join_values(p.get("prefLabel") for p in parents),
        "parent_iris": join_values(p.get("@id") for p in parents),
        "bfo_anchor": bfo_anchor(parents),
    }


def scan_obo_text(text: str, terms: list[str]) -> tuple[str, list[dict[str, Any]]]:
    header = parse_obo_header(text)
    version = header.get("data-version") or header.get("date") or header.get("format-version") or ""
    terms_lower = {term.casefold() for term in terms}

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


def obo_rows(
    terms: list[str],
    *,
    max_ontologies: int | None,
) -> list[dict[str, Any]]:
    print("\n-- OBO Foundry: loading registry --", file=sys.stderr)
    registry = fetch_obo_registry()
    active_records = [
        record for record in registry
        if str(record.get("activity_status", "active")).lower() not in {"inactive", "obsolete"}
    ]
    if max_ontologies is not None:
        active_records = active_records[:max_ontologies]
    print(f"   scanning {len(active_records)} OBO ontologies", file=sys.stderr)

    rows: list[dict[str, Any]] = []
    for record in active_records:
        ontology = str(record.get("id", "")).lower()
        url = find_obo_product_url(record)
        if not ontology or not url:
            continue
        print(f"   OBO {ontology}: {url}", file=sys.stderr)
        text = get_text(url, namespace="obo-files")
        if not text:
            continue
        version, parsed_rows = scan_obo_text(text, terms)
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
                    synonyms=parsed["synonyms"],
                    parent_labels=parsed["parent_labels"],
                    parent_iris=parsed["parent_iris"],
                    bfo_anchor_value=parsed["bfo_anchor"],
                    source_url=url,
                    retrieved_at=retrieved_at,
                )
            )
    return rows


# -- Main ----------------------------------------------------------------------

FIELDNAMES = [
    "term",
    "ontology",
    "preferred_label",
    "class_iri",
    "definition",
    "synonyms",
    "parent_labels",
    "parent_iris",
    "bfo_anchor",
    "mapping_count",
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
    parser.add_argument("--out", default="disease_terms_review.csv")
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
    parser.add_argument("--terms", default="", help="Override term list (comma-separated)")
    parser.add_argument("--resume", action="store_true", help="Merge into existing output file if present")
    args = parser.parse_args()

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
                ),
            )
        elif source == "ols":
            ols_base_url = normalise_ols_base_url(args.ols_base_url)
            merge_rows(rows_by_key, ols_rows(terms, base_url=ols_base_url, fetch_parents=not args.no_parents))
        elif source == "obo":
            merge_rows(rows_by_key, obo_rows(terms, max_ontologies=args.obo_max_ontologies))

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows_by_key.values(), key=lambda r: (r.get("term", ""), r.get("ontology", ""), r.get("class_iri", ""))):
            writer.writerow(row)

    print(f"\nDone. {len(rows_by_key)} merged rows -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
