#!/usr/bin/env python3
"""Non-destructive re-run of the BioPortal / OLS / OBO extraction + diff.

PURPOSE
    Re-run the disease-neighbour search across BioPortal, OLS, and the OBO
    Foundry using the *current* search logic (primary exact-label tier +
    secondary compound-label sensitivity + multilingual sensitivity), then
    report which class IRIs would be **added** or **dropped** relative to the
    existing extraction — WITHOUT touching any existing file.

SAFETY (this script never overwrites anything)
    * All output goes into a brand-new, timestamped folder:
          Scoping review/Rerun snapshots/rerun_<UTC-timestamp>/
      The script refuses to run if that folder somehow already exists.
    * It only ever READS the existing tables (disease_terms_review.csv).
    * No existing CSV/TTL in "Extraction Tables" or "Extraction Ontology"
      is opened for writing.

USAGE
    # full re-run of all three sources (needs network + BioPortal API key):
    python3 "Scoping review/Python scripts/rerun_extraction_compare.py"

    # restrict sources / skip enrichment / limit OBO breadth:
    python3 "Scoping review/Python scripts/rerun_extraction_compare.py" \
        --sources bioportal,ols,obo --no-enrich --obo-max-ontologies 200

    # offline check of the diff logic against an existing snapshot CSV:
    python3 "Scoping review/Python scripts/rerun_extraction_compare.py" \
        --self-test

REQUIREMENTS
    * requests (already used by the pipeline)
    * BIOPORTAL_KEY in the environment or in the project .env, for the
      BioPortal and OBO(skip-list) steps. OLS needs no key.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REVIEW_DIR = SCRIPT_DIR.parent
TABLE_DIR = REVIEW_DIR / "Extraction Tables"
SNAP_ROOT = REVIEW_DIR / "Rerun snapshots"

CURRENT_RAW = TABLE_DIR / "disease_terms_review.csv"          # baseline to diff against
CURRENT_ENRICHED = TABLE_DIR / "disease_terms_review_enriched.csv"

sys.path.insert(0, str(SCRIPT_DIR))
import review_disease_terms as terms_script  # noqa: E402


# --------------------------------------------------------------------------- #
# Baseline / diff helpers (network-free)
# --------------------------------------------------------------------------- #
def load_iri_index(path: Path) -> dict[str, dict[str, str]]:
    """class_iri -> {ontology, preferred_label, term, discovery_tier} from a CSV."""
    index: dict[str, dict[str, str]] = {}
    if not path.exists():
        return index
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            iri = (row.get("class_iri") or "").strip()
            if not iri:
                continue
            index[iri] = {
                "ontology": (row.get("ontology") or "").strip(),
                "preferred_label": (row.get("preferred_label") or row.get("label") or "").strip(),
                "term": (row.get("term") or "").strip(),
                "discovery_tier": (row.get("discovery_tier") or "").strip(),
            }
    return index


def diff_indices(current: dict[str, dict], rerun: dict[str, dict]) -> dict[str, list]:
    cur_iris = set(current)
    new_iris = set(rerun)
    added = sorted(new_iris - cur_iris)
    dropped = sorted(cur_iris - new_iris)
    shared = sorted(cur_iris & new_iris)
    return {"added": added, "dropped": dropped, "shared": shared}


def write_diff_report(out_dir: Path, current: dict, rerun: dict, diff: dict) -> Path:
    report = out_dir / "rerun_vs_current_diff.csv"
    with report.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["status", "class_iri", "ontology", "preferred_label", "term", "discovery_tier"])
        for iri in diff["added"]:
            r = rerun[iri]
            w.writerow(["ADDED_would_be_new", iri, r["ontology"], r["preferred_label"], r["term"], r["discovery_tier"]])
        for iri in diff["dropped"]:
            r = current[iri]
            w.writerow(["DROPPED_not_retrieved_now", iri, r["ontology"], r["preferred_label"], r["term"], r["discovery_tier"]])
        for iri in diff["shared"]:
            r = rerun[iri]
            w.writerow(["UNCHANGED_present_both", iri, r["ontology"], r["preferred_label"], r["term"], r["discovery_tier"]])
    return report


def summarise(out_dir: Path, current: dict, rerun: dict, diff: dict, sources: list[str]) -> Path:
    lines = [
        "Non-destructive re-extraction vs current extraction",
        f"generated_utc: {_dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')}",
        f"sources: {', '.join(sources)}",
        f"baseline_file: {CURRENT_RAW.name}  ({len(current)} unique class IRIs)",
        f"rerun_unique_class_iris: {len(rerun)}",
        "",
        f"ADDED   (in re-run, not in current): {len(diff['added'])}",
        f"DROPPED (in current, not in re-run): {len(diff['dropped'])}",
        f"UNCHANGED (present in both):         {len(diff['shared'])}",
        "",
        "First added IRIs:",
    ]
    for iri in diff["added"][:40]:
        r = rerun[iri]
        lines.append(f"  + {iri}  [{r['ontology']}] {r['preferred_label']}")
    if len(diff["added"]) > 40:
        lines.append(f"  ... and {len(diff['added']) - 40} more (see rerun_vs_current_diff.csv)")
    summary = out_dir / "rerun_summary.txt"
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


# --------------------------------------------------------------------------- #
# Search (mirrors review_extraction_pipeline.py :: search, with all tiers)
# --------------------------------------------------------------------------- #
def run_search(args) -> list[dict]:
    sources = terms_script.parse_sources(args.sources)
    terms = terms_script.DEFAULT_TERMS
    rows_by_key: dict = {}

    def _bp_key():
        return terms_script.load_bioportal_api_key()

    # --- primary exact-label tier ---
    for source in sources:
        if source == "bioportal":
            terms_script.merge_rows(rows_by_key, terms_script.bioportal_rows(
                terms, _bp_key(), fetch_parents=not args.no_parents,
                fetch_mappings=not args.no_mappings, exact_label_only=True))
        elif source == "ols":
            base = terms_script.normalise_ols_base_url(args.ols_base_url)
            terms_script.merge_rows(rows_by_key, terms_script.ols_rows(
                terms, base_url=base, fetch_parents=not args.no_parents))
        elif source == "obo":
            bp_ids = terms_script.fetch_bioportal_ontology_ids(_bp_key()) if "bioportal" in sources else set()
            terms_script.merge_rows(rows_by_key, terms_script.obo_rows(
                terms, max_ontologies=args.obo_max_ontologies, skip_ids=bp_ids))

    # --- secondary compound-label sensitivity tier (only uncovered ontologies) ---
    if not args.no_secondary:
        before_rows = list(rows_by_key.values())
        covered = terms_script.primary_covered_ontology_ids(before_rows)
        sec_terms = terms_script.SECONDARY_SENSITIVITY_TERMS
        sec_rows: list[dict] = []
        for source in sources:
            if source == "bioportal":
                sec_rows.extend(terms_script.bioportal_rows(
                    sec_terms, _bp_key(), fetch_parents=not args.no_parents,
                    fetch_mappings=not args.no_mappings, exact_label_only=True,
                    discovery_tier=terms_script.SECONDARY_DISCOVERY_TIER))
            elif source == "ols":
                base = terms_script.normalise_ols_base_url(args.ols_base_url)
                sec_rows.extend(terms_script.ols_rows(
                    sec_terms, base_url=base, fetch_parents=not args.no_parents,
                    discovery_tier=terms_script.SECONDARY_DISCOVERY_TIER))
            elif source == "obo":
                bp_ids = terms_script.fetch_bioportal_ontology_ids(_bp_key()) if "bioportal" in sources else set()
                sec_rows.extend(terms_script.obo_rows(
                    sec_terms, max_ontologies=args.obo_max_ontologies, skip_ids=bp_ids,
                    discovery_tier=terms_script.SECONDARY_DISCOVERY_TIER))
        eligible = terms_script.filter_secondary_rows_to_uncovered_ontologies(sec_rows, covered)
        terms_script.merge_rows(rows_by_key, eligible)

    # --- multilingual label sensitivity tier ---
    if not args.no_multilingual:
        ml_terms = terms_script.MULTILINGUAL_SENSITIVITY_TERMS
        ml_rows: list[dict] = []
        for source in sources:
            if source == "bioportal":
                ml_rows.extend(terms_script.bioportal_rows(
                    ml_terms, _bp_key(), fetch_parents=not args.no_parents,
                    fetch_mappings=not args.no_mappings, exact_label_only=True,
                    discovery_tier=terms_script.MULTILINGUAL_DISCOVERY_TIER))
            elif source == "ols":
                base = terms_script.normalise_ols_base_url(args.ols_base_url)
                ml_rows.extend(terms_script.ols_rows(
                    ml_terms, base_url=base, fetch_parents=not args.no_parents,
                    discovery_tier=terms_script.MULTILINGUAL_DISCOVERY_TIER))
            elif source == "obo":
                bp_ids = terms_script.fetch_bioportal_ontology_ids(_bp_key()) if "bioportal" in sources else set()
                ml_rows.extend(terms_script.obo_rows(
                    ml_terms, max_ontologies=args.obo_max_ontologies, skip_ids=bp_ids,
                    discovery_tier=terms_script.MULTILINGUAL_DISCOVERY_TIER))
        terms_script.merge_rows(rows_by_key, ml_rows)

    rows = sorted(rows_by_key.values(),
                  key=lambda r: (r.get("term", ""), r.get("ontology", ""), r.get("class_iri", "")))
    return rows


def rows_to_index(rows: list[dict]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        iri = (row.get("class_iri") or "").strip()
        if iri:
            index[iri] = {
                "ontology": (row.get("ontology") or "").strip(),
                "preferred_label": (row.get("preferred_label") or "").strip(),
                "term": (row.get("term") or "").strip(),
                "discovery_tier": (row.get("discovery_tier") or "").strip(),
            }
    return index


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def make_snapshot_dir() -> Path:
    SNAP_ROOT.mkdir(exist_ok=True)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SNAP_ROOT / f"rerun_{stamp}"
    if out_dir.exists():  # refuse to overwrite
        raise SystemExit(f"ERROR: snapshot folder already exists, refusing to overwrite: {out_dir}")
    out_dir.mkdir()
    return out_dir


def self_test() -> None:
    """Exercise the diff logic offline against the current CSV (no network)."""
    current = load_iri_index(CURRENT_RAW)
    print(f"[self-test] baseline {CURRENT_RAW.name}: {len(current)} unique class IRIs")
    # Simulate a re-run: same set minus one, plus a fake new IRI.
    fake = dict(current)
    if fake:
        dropped_iri = next(iter(fake))
        del fake[dropped_iri]
    fake["http://example.org/NEW_TEST_0001"] = {
        "ontology": "TESTONT", "preferred_label": "test disease", "term": "disease", "discovery_tier": ""}
    diff = diff_indices(current, fake)
    assert "http://example.org/NEW_TEST_0001" in diff["added"], "added detection failed"
    assert len(diff["added"]) == 1, diff["added"]
    assert len(diff["dropped"]) == 1, diff["dropped"]
    print(f"[self-test] diff ok: +{len(diff['added'])} / -{len(diff['dropped'])} / "
          f"={len(diff['shared'])}  (logic verified, no network used)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default="bioportal,ols,obo")
    ap.add_argument("--ols-base-url", default=terms_script.OLS_BASE_URL)
    ap.add_argument("--obo-max-ontologies", type=int, default=terms_script.__dict__.get("DEFAULT_OBO_MAX_ONTOLOGIES", 400))
    ap.add_argument("--no-parents", action="store_true")
    ap.add_argument("--no-mappings", action="store_true")
    ap.add_argument("--no-secondary", action="store_true", help="skip secondary compound-label tier")
    ap.add_argument("--no-multilingual", action="store_true", help="skip multilingual tier")
    ap.add_argument("--no-enrich", action="store_true", help="skip BioPortal metadata enrichment of the snapshot CSV")
    ap.add_argument("--self-test", action="store_true", help="verify diff logic offline, then exit")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    current = load_iri_index(CURRENT_RAW)
    if not current:
        print(f"[warn] no baseline found at {CURRENT_RAW}; diff will treat everything as ADDED", file=sys.stderr)

    print(f"Re-running extraction (sources: {args.sources}) — this only writes to a NEW snapshot folder.", file=sys.stderr)
    rows = run_search(args)

    out_dir = make_snapshot_dir()
    fieldnames = terms_script.FIELDNAMES
    # raw snapshot
    raw_path = out_dir / "rerun_raw.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # optional enrichment (mirrors pipeline); still only writes into the snapshot
    if not args.no_enrich:
        try:
            enriched = terms_script.enrich_rows(rows)
            en_fields = terms_script.FIELDNAMES + terms_script.ENRICHMENT_FIELDNAMES
            with (out_dir / "rerun_enriched.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=en_fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(enriched)
        except Exception as exc:  # enrichment needs BioPortal; don't fail the diff
            print(f"[warn] enrichment skipped: {exc}", file=sys.stderr)

    rerun = rows_to_index(rows)
    diff = diff_indices(current, rerun)
    report = write_diff_report(out_dir, current, rerun, diff)
    summary = summarise(out_dir, current, rerun, diff, terms_script.parse_sources(args.sources))

    print("\n==== RE-EXTRACTION DIFF ====")
    print(f"baseline unique class IRIs : {len(current)}")
    print(f"re-run   unique class IRIs : {len(rerun)}")
    print(f"ADDED   (would be new)     : {len(diff['added'])}")
    print(f"DROPPED (not retrieved now): {len(diff['dropped'])}")
    print(f"UNCHANGED                  : {len(diff['shared'])}")
    print(f"\nsnapshot folder : {out_dir}")
    print(f"diff report     : {report}")
    print(f"summary         : {summary}")
    print("No existing file was modified.")


if __name__ == "__main__":
    main()
