#!/usr/bin/env python3
"""
Download source ontologies referenced by the disease-term review CSV.

The target is the full source-ontology cache ("Import ontologies"), not the
project's extracted module folder ("Disease ontology modules").

Typical usage from the project root:

    python3 "Scoping review/download_review_ontologies.py" --dry-run
    python3 "Scoping review/download_review_ontologies.py" --repositories ols,obo --dry-run
    python3 "Scoping review/download_review_ontologies.py" --limit 10
    python3 "Scoping review/download_review_ontologies.py"

By default, BioPortal ontology acronyms are collected from every BioPortal source
record in the CSV. OLS and OBO Foundry identifiers are collected from their
respective source_records. Use --source-mode row-ontology to download only the
primary ontology shown in each row for BioPortal.
"""

from __future__ import annotations

import argparse
import csv
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


BIOPORTAL_BASE_URL = "https://data.bioontology.org"
OLS_BASE_URL = "https://www.ebi.ac.uk/ols4"
OBO_REGISTRY_URL = "https://obofoundry.org/registry/ontologies.yml"
ENV_FILE = Path(
    "/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Wound ontology/.env"
)
IMPORT_DIR = Path(
    "/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Import ontologies"
)
DEFAULT_CSV = Path(__file__).resolve().parent / "disease_terms_review_enriched.csv"
DEFAULT_MANIFEST = Path(__file__).resolve().parent / "downloaded_review_ontologies_manifest.csv"

ONTOLOGY_EXTENSIONS = {".owl", ".obo", ".ttl", ".rdf", ".xml", ".json", ".nt", ".n3"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_bioportal_api_key() -> str:
    key = os.environ.get("BIOPORTAL_KEY", "")
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("BIOPORTAL_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit(f"ERROR: BIOPORTAL_KEY not found in env or {ENV_FILE}")
    return key


def normalise_acronym(value: str) -> str:
    return value.strip().lower()


def filename_stem_variants(stem: str) -> set[str]:
    stem = stem.lower()
    variants = {stem}
    variants.add(stem.replace("-", "_"))
    variants.add(stem.replace("_", "-"))
    return variants


def existing_ontology_keys(import_dir: Path) -> set[str]:
    keys: set[str] = set()
    if not import_dir.exists():
        return keys
    for path in import_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in ONTOLOGY_EXTENSIONS:
            continue
        keys.update(filename_stem_variants(path.stem))
    return keys


def parse_repositories(raw_repositories: str) -> list[str]:
    allowed = {"bioportal", "ols", "obo"}
    repositories = [part.strip().lower() for part in raw_repositories.split(",") if part.strip()]
    unknown = [repository for repository in repositories if repository not in allowed]
    if unknown:
        sys.exit(f"ERROR: unknown repositories: {', '.join(unknown)}")
    return repositories


def read_review_ontology_ids(csv_path: Path, source_mode: str) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = {"bioportal": set(), "ols": set(), "obo": set()}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("ontology"):
                ids["bioportal"].add(row["ontology"].strip())
            try:
                source_records = json.loads(row.get("source_records") or "[]")
            except json.JSONDecodeError:
                source_records = []
            if not isinstance(source_records, list):
                continue
            for record in source_records:
                if not isinstance(record, dict):
                    continue
                source = record.get("source")
                ontology = str(record.get("ontology", "")).strip()
                if not ontology:
                    continue
                if source == "BioPortal" and source_mode == "all-source-records":
                    ids["bioportal"].add(ontology)
                elif source == "OLS":
                    ids["ols"].add(ontology.lower())
                elif source == "OBO Foundry Direct":
                    ids["obo"].add(ontology.lower())
    return {key: {value for value in values if value} for key, values in ids.items()}


def safe_filename(acronym: str, fallback_ext: str = ".owl") -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", acronym.strip()).lower()
    return f"{safe}{fallback_ext}"


def filename_from_content_disposition(header_value: str) -> str:
    if not header_value:
        return ""
    match = re.search(r"filename\\*?=(?:UTF-8''|UTF-8\\'\\')?\"?([^\";]+)\"?", header_value, flags=re.IGNORECASE)
    if not match:
        return ""
    return Path(urllib.parse.unquote(match.group(1))).name


def infer_extension(content_type: str, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in ONTOLOGY_EXTENSIONS:
        return suffix
    content_type = (content_type or "").lower()
    if "json" in content_type:
        return ".json"
    if "turtle" in content_type:
        return ".ttl"
    if "rdf" in content_type or "xml" in content_type:
        return ".owl"
    return ".owl"


def extension_from_url(url: str) -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return suffix if suffix in ONTOLOGY_EXTENSIONS else ".owl"


def download_url(
    *,
    ontology: str,
    source: str,
    url: str,
    import_dir: Path,
    overwrite: bool = False,
    params: dict[str, str] | None = None,
    metadata_url: str = "",
) -> dict[str, Any]:
    started_at = now_iso()
    response = requests.get(url, params=params or {}, stream=True, timeout=120)
    if response.status_code != 200:
        return {
            "source": source,
            "ontology": ontology,
            "status": f"error_http_{response.status_code}",
            "path": "",
            "download_url": response.url,
            "metadata_url": metadata_url,
            "bytes": 0,
            "retrieved_at": started_at,
            "message": response.text[:500],
        }

    cd_filename = filename_from_content_disposition(response.headers.get("content-disposition", ""))
    ext = infer_extension(response.headers.get("content-type", ""), cd_filename or url)
    if not cd_filename:
        ext = extension_from_url(url)
    target_name = safe_filename(ontology, ext)
    target_path = import_dir / target_name
    if target_path.exists() and not overwrite:
        response.close()
        return {
            "source": source,
            "ontology": ontology,
            "status": "skipped_existing_after_request",
            "path": str(target_path),
            "download_url": response.url,
            "metadata_url": metadata_url,
            "bytes": target_path.stat().st_size,
            "retrieved_at": started_at,
            "message": "",
        }

    tmp_path = target_path.with_suffix(target_path.suffix + ".part")
    bytes_written = 0
    with tmp_path.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue
            handle.write(chunk)
            bytes_written += len(chunk)
    tmp_path.replace(target_path)
    return {
        "source": source,
        "ontology": ontology,
        "status": "downloaded",
        "path": str(target_path),
        "download_url": response.url,
        "metadata_url": metadata_url,
        "bytes": bytes_written,
        "retrieved_at": started_at,
        "message": "",
    }


def download_bioportal_ontology(acronym: str, import_dir: Path, apikey: str, overwrite: bool = False) -> dict[str, Any]:
    url = f"{BIOPORTAL_BASE_URL}/ontologies/{acronym}/download"
    return download_url(
        ontology=acronym,
        source="BioPortal",
        url=url,
        params={"apikey": apikey},
        import_dir=import_dir,
        overwrite=overwrite,
        metadata_url=f"{BIOPORTAL_BASE_URL}/ontologies/{acronym}",
    )


def ols_ontology_download_url(ontology: str) -> tuple[str, str]:
    metadata_url = f"{OLS_BASE_URL}/api/ontologies/{ontology}"
    response = requests.get(metadata_url, timeout=60)
    if response.status_code != 200:
        return "", metadata_url
    data = response.json()
    config = data.get("config", {}) if isinstance(data, dict) else {}
    url = config.get("fileLocation") or config.get("versionIri") or data.get("versionIri") or ""
    return str(url), metadata_url


def parse_simple_yaml_value(value: str) -> str:
    value = value.strip()
    if value in {"", "|", ">"}:
        return ""
    return value.strip("\"'")


def parse_obo_registry_yaml(text: str) -> dict[str, list[str]]:
    registry: dict[str, list[str]] = {}
    chunks = re.split(r"\n(?=- activity_status:)", text)
    for chunk in chunks:
        chunk = chunk.strip("\n")
        if not chunk.startswith("- activity_status:"):
            continue
        ontology_id = ""
        top_level_purl = ""
        products: list[str] = []
        for line in chunk.splitlines():
            if match := re.match(r"^  id:\s*(.*)$", line):
                ontology_id = parse_simple_yaml_value(match.group(1)).lower()
            elif match := re.match(r"^  ontology_purl:\s*(.*)$", line):
                top_level_purl = parse_simple_yaml_value(match.group(1))
            elif match := re.match(r"^    ontology_purl:\s*(.*)$", line):
                products.append(parse_simple_yaml_value(match.group(1)))
        if not ontology_id:
            continue
        candidates = []
        candidates.extend(url for url in products if url.endswith(".owl"))
        candidates.extend(url for url in products if url.endswith(".obo"))
        candidates.extend(url for url in products if url and url not in candidates)
        if top_level_purl:
            candidates.append(top_level_purl)
        registry[ontology_id] = list(dict.fromkeys(url for url in candidates if url))
    return registry


def obo_registry_download_urls() -> dict[str, list[str]]:
    response = requests.get(OBO_REGISTRY_URL, timeout=60)
    response.raise_for_status()
    return parse_obo_registry_yaml(response.text)


def make_dry_row(source: str, ontology: str, import_dir: Path, download_url: str = "", metadata_url: str = "") -> dict[str, Any]:
    return {
        "source": source,
        "ontology": ontology,
        "status": "missing_dry_run",
        "path": str(import_dir / safe_filename(ontology, extension_from_url(download_url) if download_url else ".owl")),
        "download_url": download_url,
        "metadata_url": metadata_url,
        "bytes": 0,
        "retrieved_at": now_iso(),
        "message": "",
    }


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["source", "ontology", "status", "path", "download_url", "metadata_url", "bytes", "retrieved_at", "message"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_download_jobs(
    ids_by_source: dict[str, set[str]],
    repositories: list[str],
    import_dir: Path,
    existing: set[str],
    overwrite: bool,
) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    if "bioportal" in repositories:
        for ontology in sorted(ids_by_source.get("bioportal", [])):
            if not overwrite and normalise_acronym(ontology) in existing:
                continue
            jobs.append(
                {
                    "source": "BioPortal",
                    "ontology": ontology,
                    "download_url": f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/download",
                    "metadata_url": f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}",
                }
            )
    if "ols" in repositories:
        for ontology in sorted(ids_by_source.get("ols", [])):
            if not overwrite and normalise_acronym(ontology) in existing:
                continue
            download_url, metadata_url = ols_ontology_download_url(ontology)
            jobs.append(
                {
                    "source": "OLS",
                    "ontology": ontology,
                    "download_url": download_url,
                    "metadata_url": metadata_url,
                }
            )
    if "obo" in repositories:
        obo_urls = obo_registry_download_urls()
        for ontology in sorted(ids_by_source.get("obo", [])):
            if not overwrite and normalise_acronym(ontology) in existing:
                continue
            candidates = obo_urls.get(ontology, [])
            jobs.append(
                {
                    "source": "OBO Foundry",
                    "ontology": ontology,
                    "download_url": candidates[0] if candidates else "",
                    "metadata_url": OBO_REGISTRY_URL,
                }
            )
    return jobs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="Review CSV to read ontology acronyms from.")
    parser.add_argument("--import-dir", default=str(IMPORT_DIR), help="Source ontology cache directory.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Download manifest CSV.")
    parser.add_argument(
        "--repositories",
        default="bioportal",
        help="Comma-separated repositories to use: bioportal,ols,obo.",
    )
    parser.add_argument(
        "--source-mode",
        choices=["all-source-records", "row-ontology"],
        default="all-source-records",
        help="Use all BioPortal source_records or only each row's primary ontology column.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only report missing ontologies; do not download.")
    parser.add_argument("--limit", type=int, default=0, help="Download at most N missing ontologies.")
    parser.add_argument("--overwrite", action="store_true", help="Redownload even if a matching file already exists.")
    parser.add_argument("--delay", type=float, default=0.2, help="Seconds between downloads.")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    import_dir = Path(args.import_dir)
    manifest_path = Path(args.manifest)
    import_dir.mkdir(parents=True, exist_ok=True)

    repositories = parse_repositories(args.repositories)
    ids_by_source = read_review_ontology_ids(csv_path, args.source_mode)
    existing = existing_ontology_keys(import_dir)
    all_jobs = build_download_jobs(ids_by_source, repositories, import_dir, existing, args.overwrite)
    jobs = list(all_jobs)
    if args.limit:
        jobs = jobs[: args.limit]

    total_selected = sum(len(ids_by_source.get(repository, set())) for repository in repositories)
    print(f"Repositories: {', '.join(repositories)}")
    print(f"Review ontology ids selected: {total_selected}")
    print(f"Already present in import dir: {total_selected - len(all_jobs)}")
    print(f"Missing total: {len(all_jobs)}")
    if args.limit:
        print(f"Missing selected by --limit: {len(jobs)}")
    else:
        print(f"Missing to download: {len(jobs)}")
    print(f"Import dir: {import_dir}")

    if args.dry_run:
        for job in jobs:
            print(f"{job['source']},{job['ontology']},{job['download_url']}")
        dry_rows = [
            make_dry_row(job["source"], job["ontology"], import_dir, job.get("download_url", ""), job.get("metadata_url", ""))
            for job in jobs
        ]
        write_manifest(manifest_path, dry_rows)
        print(f"Dry-run manifest -> {manifest_path}")
        return

    apikey = load_bioportal_api_key()
    manifest_rows: list[dict[str, Any]] = []
    for index, job in enumerate(jobs, start=1):
        print(f"[{index}/{len(jobs)}] {job['source']} {job['ontology']}", file=sys.stderr)
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
            row = download_url(
                ontology=job["ontology"],
                source=job["source"],
                url=job["download_url"],
                params={"apikey": apikey},
                import_dir=import_dir,
                overwrite=args.overwrite,
                metadata_url=job.get("metadata_url", ""),
            )
        else:
            row = download_url(
                ontology=job["ontology"],
                source=job["source"],
                url=job["download_url"],
                import_dir=import_dir,
                overwrite=args.overwrite,
                metadata_url=job.get("metadata_url", ""),
            )
        manifest_rows.append(row)
        print(f"  {row['status']} {row['bytes']} bytes {row['path']}", file=sys.stderr)
        time.sleep(args.delay)

    write_manifest(manifest_path, manifest_rows)
    print(f"Manifest -> {manifest_path}")


if __name__ == "__main__":
    main()
