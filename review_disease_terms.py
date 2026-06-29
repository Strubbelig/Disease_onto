#!/usr/bin/env python3
"""
review_disease_terms.py — BioPortal survey of disease-modelling root terms

Searches BioPortal for the core disease-modelling term family across ALL
ontologies, fetches full class details (definition, direct parents, BFO anchor,
mapping count), and writes a CSV for comparative review.

Terms searched (exact label match):
    disease, disorder, injury, illness, condition, syndrome,
    pathological process, pathological disposition, dysfunction, predisposition

Usage:
    python3 review_disease_terms.py                   # full run → disease_terms_review.csv
    python3 review_disease_terms.py --out my.csv
    python3 review_disease_terms.py --no-parents      # skip parent fetch (faster)
    python3 review_disease_terms.py --terms "disease,disorder"   # override term list
    python3 review_disease_terms.py --resume          # continue interrupted run
"""

import argparse, csv, json, os, sys, time, urllib.parse
from pathlib import Path
import requests

# ── Config ────────────────────────────────────────────────────────────────────

ENV_FILE = Path("/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Wound ontology/.env")
BASE_URL  = "https://data.bioontology.org"
CACHE_DIR = Path("/tmp/bioportal_cache")

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

BFO_PREFIX   = "http://purl.obolibrary.org/obo/BFO_"
DELAY        = 0.12   # seconds between API calls (~8 req/s, within free-tier limit)

# ── API helpers ───────────────────────────────────────────────────────────────

def load_api_key() -> str:
    key = os.environ.get("BIOPORTAL_KEY", "")
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("BIOPORTAL_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("ERROR: BIOPORTAL_KEY not found")
    return key


def get(url: str, params: dict, apikey: str, retries: int = 3) -> dict | None:
    params = {**params, "apikey": apikey}
    CACHE_DIR.mkdir(exist_ok=True)
    cache_key = urllib.parse.urlencode(sorted(params.items()))
    cache_file = CACHE_DIR / (str(abs(hash(url + cache_key))) + ".json")
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    for attempt in range(retries):
        try:
            time.sleep(DELAY)
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10))
                print(f"  [rate limit] waiting {wait}s …", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            cache_file.write_text(json.dumps(data))
            return data
        except Exception as e:
            print(f"  [warn] attempt {attempt+1} failed: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


# ── Search ────────────────────────────────────────────────────────────────────

def search_exact(term: str, apikey: str) -> list[dict]:
    """Return all BioPortal classes whose prefLabel exactly matches term."""
    hits = []
    page = 1
    while True:
        data = get(f"{BASE_URL}/search", {
            "q": term,
            "require_exact_match": "true",
            "include": "prefLabel,definition,synonym,notation",
            "pagesize": 100,
            "page": page,
        }, apikey)
        if not data:
            break
        hits.extend(data.get("collection", []))
        links = data.get("links", {})
        if not links.get("nextPage"):
            break
        page += 1
    return hits


# ── Parents ───────────────────────────────────────────────────────────────────

def fetch_parents(onto: str, class_iri: str, apikey: str) -> list[dict]:
    encoded = urllib.parse.quote(class_iri, safe="")
    data = get(f"{BASE_URL}/ontologies/{onto}/classes/{encoded}/parents",
               {"include": "prefLabel"}, apikey)
    if not data or not isinstance(data, list):
        return []
    return data


def bfo_anchor(parents: list[dict]) -> str:
    """Return the BFO IRI of the first BFO parent found, or ''."""
    for p in parents:
        iri = p.get("@id", "")
        if iri.startswith(BFO_PREFIX):
            label = (p.get("prefLabel") or "").strip()
            return f"{label} ({iri.split('BFO_')[1]})" if label else iri
    return ""


# ── Mapping count ─────────────────────────────────────────────────────────────

def fetch_mapping_count(onto: str, class_iri: str, apikey: str) -> int:
    encoded = urllib.parse.quote(class_iri, safe="")
    data = get(f"{BASE_URL}/ontologies/{onto}/classes/{encoded}/mappings",
               {}, apikey)
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return data.get("totalCount", len(data.get("collection", [])))
    return 0


# ── Main ──────────────────────────────────────────────────────────────────────

FIELDNAMES = [
    "term", "ontology", "preferred_label", "class_iri",
    "definition", "synonyms",
    "parent_labels", "parent_iris",
    "bfo_anchor", "mapping_count",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="disease_terms_review.csv")
    parser.add_argument("--no-parents", action="store_true",
                        help="Skip parent + mapping fetch (much faster)")
    parser.add_argument("--no-mappings", action="store_true",
                        help="Skip mapping count fetch")
    parser.add_argument("--terms", default="",
                        help="Override term list (comma-separated)")
    parser.add_argument("--resume", action="store_true",
                        help="Append to existing output file, skip already-written rows")
    args = parser.parse_args()

    apikey = load_api_key()
    terms  = [t.strip() for t in args.terms.split(",")] if args.terms else DEFAULT_TERMS
    out_path = Path(args.out)

    # Resume: load already-done (term, ontology, iri) triples.
    done: set[tuple] = set()
    write_mode = "a" if args.resume and out_path.exists() else "w"
    if args.resume and out_path.exists():
        with out_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done.add((row["term"], row["ontology"], row["class_iri"]))
        print(f"[resume] {len(done)} rows already written", file=sys.stderr)

    with out_path.open(write_mode, newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES, extrasaction="ignore")
        if write_mode == "w":
            writer.writeheader()

        for term in terms:
            print(f"\n── Searching '{term}' ──", file=sys.stderr)
            hits = search_exact(term, apikey)
            print(f"   {len(hits)} hits", file=sys.stderr)

            for h in hits:
                iri  = h.get("@id", "")
                onto = h.get("links", {}).get("ontology", "").rstrip("/").split("/")[-1]
                key  = (term, onto, iri)
                if key in done:
                    continue

                label = h.get("prefLabel", "").strip()
                defn  = (h.get("definition") or [""])[0].strip()
                syns  = "; ".join(s for s in (h.get("synonym") or []) if s)

                parent_labels = parent_iris = bfo = ""
                mapping_count = ""

                if not args.no_parents and onto and iri:
                    parents = fetch_parents(onto, iri, apikey)
                    parent_labels = "; ".join(
                        (p.get("prefLabel") or "").strip() for p in parents if p.get("prefLabel"))
                    parent_iris = "; ".join(
                        p.get("@id", "") for p in parents if p.get("@id"))
                    bfo = bfo_anchor(parents)

                    if not args.no_mappings:
                        mapping_count = fetch_mapping_count(onto, iri, apikey)

                row = {
                    "term":           term,
                    "ontology":       onto,
                    "preferred_label": label,
                    "class_iri":      iri,
                    "definition":     defn,
                    "synonyms":       syns,
                    "parent_labels":  parent_labels,
                    "parent_iris":    parent_iris,
                    "bfo_anchor":     bfo,
                    "mapping_count":  mapping_count,
                }
                writer.writerow(row)
                fout.flush()
                done.add(key)

                bfo_note = f" [BFO: {bfo}]" if bfo else ""
                print(f"   {onto:15s}  {label}{bfo_note}", file=sys.stderr)

    total = len(done)
    print(f"\nDone. {total} rows → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
