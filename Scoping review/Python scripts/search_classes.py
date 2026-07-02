#!/usr/bin/env python3
"""
search_classes.py — BioPortal keyword → ontology class extractor

Usage:
    python3 search_classes.py "diabetes mellitus" "chronic inflammation"
    python3 search_classes.py --ontologies DOID,HP,PATO "necrosis"
    python3 search_classes.py --wound "inflammation"    # cross-ref wound ontology
    python3 search_classes.py --out results.csv "fibrosis"

Options:
    --ontologies  Comma-separated BioPortal ontology acronyms to restrict search
                  (default: DOID,HP,PATO,OBI,OGMS,GO,CHEBI,NCBITAXON,UO,COB,RO)
    --wound       Cross-reference results against wound ontology classes (mark overlap)
    --out FILE    Write CSV output to FILE (default: print to stdout)
    --exact       Require exact label match
    --limit N     Max results per keyword (default: 20)
"""

import argparse, csv, os, sys
from pathlib import Path
import requests

# ── Config ────────────────────────────────────────────────────────────────────

ENV_FILE = Path("/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Wound ontology/.env")
WOND_OWL = Path("/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Wound ontology/src/ontology/wond-edit.owl")
BIOPORTAL_SEARCH = "https://data.bioontology.org/search"

DEFAULT_ONTOS = "DOID,HP,PATO,OBI,OGMS,GO,CHEBI,NCBITAXON,UO,COB,RO,IAO"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_api_key() -> str:
    key = os.environ.get("BIOPORTAL_KEY", "")
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("BIOPORTAL_KEY="):
                key = line.split("=", 1)[1].strip()
                break
    if not key:
        sys.exit("ERROR: BIOPORTAL_KEY not found in env or " + str(ENV_FILE))
    return key


def load_wound_iris() -> set[str]:
    """Return set of IRIs already declared in the wound ontology."""
    if not WOND_OWL.exists():
        print(f"[warn] wound ontology not found at {WOND_OWL}", file=sys.stderr)
        return set()
    try:
        import rdflib
        g = rdflib.Graph()
        g.parse(str(WOND_OWL))
        from rdflib import RDF, OWL
        iris = {str(s) for s in g.subjects(RDF.type, OWL.Class)
                if not str(s).startswith("_")}
        print(f"[info] wound ontology: {len(iris)} classes loaded", file=sys.stderr)
        return iris
    except ImportError:
        print("[warn] rdflib not installed — wound cross-reference unavailable", file=sys.stderr)
        return set()


def search_bioportal(keyword: str, apikey: str, ontologies: str,
                     exact: bool, limit: int) -> list[dict]:
    params = {
        "q": keyword,
        "apikey": apikey,
        "include": "prefLabel,definition,synonym,notation",
        "pagesize": limit,
        "page": 1,
    }
    if ontologies:
        params["ontologies"] = ontologies
    if exact:
        params["require_exact_match"] = "true"

    try:
        r = requests.get(BIOPORTAL_SEARCH, params=params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[warn] BioPortal request failed for '{keyword}': {e}", file=sys.stderr)
        return []

    results = []
    for item in r.json().get("collection", []):
        onto = item.get("links", {}).get("ontology", "").rstrip("/").split("/")[-1]
        iri  = item.get("@id", "")
        label = item.get("prefLabel", "")
        defn  = (item.get("definition") or [""])[0]
        syns  = "; ".join(item.get("synonym") or [])
        results.append({
            "keyword":    keyword,
            "iri":        iri,
            "label":      label,
            "ontology":   onto,
            "definition": defn,
            "synonyms":   syns,
        })
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("keywords", nargs="+", help="Keywords to search")
    parser.add_argument("--ontologies", default=DEFAULT_ONTOS,
                        help="Comma-separated BioPortal ontology acronyms")
    parser.add_argument("--wound", action="store_true",
                        help="Mark classes already present in the wound ontology")
    parser.add_argument("--out", metavar="FILE", help="Write CSV to FILE")
    parser.add_argument("--exact", action="store_true", help="Require exact label match")
    parser.add_argument("--limit", type=int, default=20, help="Max results per keyword")
    args = parser.parse_args()

    apikey = load_api_key()
    wound_iris = load_wound_iris() if args.wound else set()

    all_rows: list[dict] = []
    for kw in args.keywords:
        print(f"Searching: '{kw}' ...", file=sys.stderr)
        rows = search_bioportal(kw, apikey, args.ontologies, args.exact, args.limit)
        for row in rows:
            row["in_wound_onto"] = "yes" if row["iri"] in wound_iris else ""
        all_rows.extend(rows)
        print(f"  → {len(rows)} results", file=sys.stderr)

    if not all_rows:
        print("No results.", file=sys.stderr)
        return

    fieldnames = ["keyword", "ontology", "label", "iri", "definition", "synonyms"]
    if args.wound:
        fieldnames.append("in_wound_onto")

    if args.out:
        out_path = Path(args.out)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_rows)
        print(f"Saved {len(all_rows)} rows → {out_path}", file=sys.stderr)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)


if __name__ == "__main__":
    main()
