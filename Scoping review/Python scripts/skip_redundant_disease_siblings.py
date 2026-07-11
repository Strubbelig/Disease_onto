#!/usr/bin/env python3
"""Skip redundant disease-sibling classes.

When a native ontology already has an INCLUDED disease representative (a class
labelled 'disease' or 'état pathologique' with manual_include_status=include),
its generic sibling classes labelled 'dysfunction', 'illness', or 'syndrome' do
not need independent review — the disease is the representative. This script
excludes those siblings as `replaced_by_better_native_disease_model_candidate`.

Grouping is by NATIVE ontology (native_source_ontology_ids -> native_ontology_guess
-> discovery ontology, upper-cased), matching the review UI.

By default it only skips siblings that are still UNREVIEWED (blank include);
already-reviewed siblings are listed but left untouched unless you pass
--include-reviewed. Dry run unless --apply is given.

Usage
-----
    python3 "skip_redundant_disease_siblings.py"                       # dry run
    python3 "skip_redundant_disease_siblings.py" --apply               # skip unreviewed
    python3 "skip_redundant_disease_siblings.py" --apply --include-reviewed
    python3 "skip_redundant_disease_siblings.py" --apply --only OGMS,OMIT
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TABLES = SCRIPT_DIR.parent / "Extraction Tables"
ENRICHED = TABLES / "disease_terms_review_enriched.csv"
MANUAL = TABLES / "disease_terms_manual_annotations.csv"

sys.path.insert(0, str(SCRIPT_DIR))
import prefill_manual_annotations as pm  # noqa: E402

SIBLING_LABELS = {"dysfunction", "illness", "syndrome"}
REASON = pm.REPLACED_CLASS_EXCLUSION_REASON
DETAIL = "Skipped: the native ontology's disease class is already included as the representative; this sibling is not reviewed independently."


def native_group(row: dict) -> str:
    ns = row.get("native_source_ontology_ids", "")
    if ns.strip():
        key = ns.split(";")[0].split(":", 1)[-1].strip()
    else:
        key = row.get("native_ontology_guess", "").strip() or (row.get("ontology", "") or "").strip()
    return key.upper()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write changes (else dry run).")
    ap.add_argument("--include-reviewed", action="store_true", help="Also override already-reviewed sibling rows.")
    ap.add_argument("--only", default="", help="Comma-separated native ontologies to limit to (e.g. OGMS,OMIT).")
    args = ap.parse_args()
    only = {t.strip().upper() for t in args.only.split(",") if t.strip()}

    enr = list(csv.DictReader(ENRICHED.open(encoding="utf-8")))
    man_rows = list(csv.DictReader(MANUAL.open(encoding="utf-8")))
    mcols = list(man_rows[0].keys())
    man = {r["class_iri"]: r for r in man_rows}

    groups = defaultdict(list)
    for e in enr:
        groups[native_group(e)].append(e)

    onto_incl_disease = set()
    for onto, rows in groups.items():
        for e in rows:
            if pm.is_disease_representative_label(e.get("preferred_label", "")) \
               and man.get(e["class_iri"], {}).get("manual_include_status") == "include":
                onto_incl_disease.add(onto)
                break

    applied, reviewed_hits, already = [], [], 0
    for onto in sorted(onto_incl_disease):
        if only and onto not in only:
            continue
        for e in groups[onto]:
            if pm._norm_label(e.get("preferred_label", "") or e.get("term", "")) not in SIBLING_LABELS:
                continue
            r = man.get(e["class_iri"])
            if r is None:
                continue
            inc = r.get("manual_include_status", "").strip()
            if inc == "exclude":
                already += 1
                continue
            is_reviewed = inc != ""
            if is_reviewed and not args.include_reviewed:
                reviewed_hits.append((onto, e.get("preferred_label", ""), inc))
                continue
            if args.apply:
                r["manual_include_status"] = "exclude"
                r["manual_exclusion_reason"] = REASON
                r["manual_exclusion_detail"] = DETAIL
                r["entity_quality_score"] = "0"
            applied.append((onto, e.get("preferred_label", ""), "was " + (inc or "blank")))

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"[{mode}] native ontologies with an included disease: {len(onto_incl_disease)}")
    print(f"\nSkipped siblings ({len(applied)}):")
    for o, lbl, st in applied:
        print(f"  {o}: {lbl!r}  ({st})")
    if reviewed_hits:
        print(f"\nLeft already-reviewed (use --include-reviewed to override): {len(reviewed_hits)}")
        for o, lbl, inc in reviewed_hits:
            print(f"  {o}: {lbl!r}  (reviewed as {inc})")
    print(f"\nalready excluded: {already}")

    if args.apply and applied:
        with MANUAL.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=mcols)
            w.writeheader()
            w.writerows(man_rows)
        print("\nWrote manual annotations. Re-run the pipeline export to sync the TTL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
