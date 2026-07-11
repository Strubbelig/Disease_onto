#!/usr/bin/env python3
"""Preselect the ontology-level `logical_inconsistency` flag from review comments.

For every ontology you have reviewed, this scans the free-text fields
`review_notes` and `upper_level_interpretation` for language that indicates a
genuine LOGICAL inconsistency (a reasoner-level contradiction, unsatisfiable
classes, or a clearly contradictory modelling commitment) and preselects the
flag `logical_inconsistency = true` for ALL classes of that ontology.

It deliberately does NOT trigger on the bare word "logical" (which is a
substring of "ontological") nor on generic "bad modelling" remarks. Two tiers
are reported:

  STRONG  - explicit contradiction / inconsistency language. Applied by --apply.
  WEAK    - erroneous is_a / subsumption remarks (wrong/false/strange is_a).
            These are shown for your judgement but are NOT written by --apply
            unless you also pass --include-weak.

Default is a DRY RUN: it prints what it would set and writes nothing. Re-run
with --apply to write the preselected values into the manual annotations CSV.
Grouping is by the enriched `ontology` field (the same key the review UI uses),
so applying the flag mirrors the UI's per-ontology propagation.

Usage
-----
    python3 "preselect_logical_inconsistency.py"                # dry run
    python3 "preselect_logical_inconsistency.py" --apply        # write STRONG
    python3 "preselect_logical_inconsistency.py" --apply --include-weak
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR.parent / "Extraction Tables" / "disease_terms_manual_annotations.csv"
DEFAULT_ENRICHED = SCRIPT_DIR.parent / "Extraction Tables" / "disease_terms_review_enriched.csv"

SCAN_FIELDS = ("review_notes", "upper_level_interpretation")

# Explicit contradiction / inconsistency language (word-boundary, case-insensitive).
STRONG_PATTERNS = [
    r"logical error",
    r"logically inconsistent",
    r"inconsisten\w*",
    r"unsatisfiab\w*",
    r"incoheren\w*",
    r"mutually exclusive",
    r"contradict\w*",
    r"\bconflict\w*",
    r"\bdisjoint\w*",
    r"\bclash\w*",
    r"\bstrang\w*",   # reviewer often wrote "strange"/"strangely" for logical/is_a errors
]
# Weaker signals: erroneous subsumption / hierarchy remarks.
WEAK_PATTERNS = [
    r"(wrong|false|strange|incorrect|bad)\s+is_a",
    r"is_a\b.*\b(confusion|error)",
    r"\bfalse\b.*\bis_a",
]

STRONG_RE = re.compile("|".join(STRONG_PATTERNS), re.IGNORECASE)
WEAK_RE = re.compile("|".join(WEAK_PATTERNS), re.IGNORECASE)

# Map matched language to a controlled logical_inconsistency category.
# Checked in priority order; the first category with a match in the ontology wins.
CATEGORY_RES = [
    ("reasoner_inconsistent", re.compile(r"unsatisfiab\w*|\breasoner\b|incoheren\w*", re.IGNORECASE)),
    ("wrong_is_a_hierarchy", re.compile(
        r"\bstrang\w*"
        r"|(wrong|false|incorrect|bad)\s+is_a"
        r"|is_a\b.*\b(confusion|error)"
        r"|\bis_a\b.*\bis_a\b", re.IGNORECASE)),
    ("contradictory_upper_level", re.compile(
        r"mutually exclusive|contradict\w*|\bconflict\w*|\bdisjoint\w*|\bclash\w*|logical error|inconsisten\w*",
        re.IGNORECASE)),
]
DEFAULT_CATEGORY = "other_logical_error"


def categorize(texts) -> str:
    blob = " ".join(texts)
    for name, rx in CATEGORY_RES:
        if rx.search(blob):
            return name
    return DEFAULT_CATEGORY


def sentences(text: str):
    for part in re.split(r"(?<=[.!?])\s+|;\s+", text or ""):
        part = part.strip()
        if part:
            yield part


def load_ontology_by_iri(enriched_path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not enriched_path.exists():
        return mapping
    with enriched_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            iri = row.get("class_iri", "")
            if iri:
                mapping[iri] = (row.get("ontology", "") or "").strip()
    return mapping


def reviewed(row: dict[str, str]) -> bool:
    return bool(row.get("reviewer", "").strip() and row.get("review_date", "").strip()) or \
        row.get("manual_include_status", "").strip() == "exclude"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Manual annotations CSV.")
    ap.add_argument("--enriched", type=Path, default=DEFAULT_ENRICHED, help="Enriched CSV (for the 'ontology' grouping key).")
    ap.add_argument("--apply", action="store_true", help="Write true for STRONG matches (else dry run).")
    ap.add_argument("--include-weak", action="store_true", help="Also apply/report WEAK (erroneous is_a) matches.")
    ap.add_argument("--exclude", default="", help="Comma-separated ontology keys to NOT apply (case-insensitive), e.g. BIOTOP.")
    args = ap.parse_args()
    exclude = {t.strip().upper() for t in args.exclude.split(",") if t.strip()}

    if not args.csv.exists():
        sys.exit(f"ERROR: annotations CSV not found: {args.csv}")

    with args.csv.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    if "logical_inconsistency" not in fieldnames:
        sys.exit("ERROR: 'logical_inconsistency' column missing. Add the field first.")

    onto_by_iri = load_ontology_by_iri(args.enriched)

    def okey(row):
        return onto_by_iri.get(row.get("class_iri", ""), "") or ""

    # group rows by ontology
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        groups[okey(r)].append(r)

    strong_hits: dict[str, list[str]] = {}
    weak_hits: dict[str, list[str]] = {}
    for onto, grp in groups.items():
        if not onto:
            continue
        if not any(reviewed(r) for r in grp):
            continue  # only ontologies you have reviewed
        strong, weak = [], []
        for r in grp:
            for field in SCAN_FIELDS:
                for sent in sentences(r.get(field, "")):
                    if STRONG_RE.search(sent):
                        strong.append(sent)
                    elif WEAK_RE.search(sent):
                        weak.append(sent)
        if strong:
            strong_hits[onto] = sorted(set(strong))
        elif weak:
            weak_hits[onto] = sorted(set(weak))

    # per-ontology controlled category, derived from all matched sentences
    category_by_onto: dict[str, str] = {}
    for onto in list(strong_hits) + list(weak_hits):
        category_by_onto[onto] = categorize(strong_hits.get(onto, []) + weak_hits.get(onto, []))

    print("=" * 78)
    print("PRESELECT logical_inconsistency  (%s)" % ("APPLY" if args.apply else "DRY RUN — writes nothing"))
    print(f"annotations : {args.csv}")
    print("=" * 78)

    print(f"\nSTRONG candidates (explicit contradiction/inconsistency): {len(strong_hits)}")
    for onto in sorted(strong_hits):
        n = len(groups[onto])
        print(f"  ✓ {onto}  [{category_by_onto[onto]}]  (applies to {n} class(es))")
        for s in strong_hits[onto]:
            print(f"       “{s}”")

    print(f"\nWEAK candidates (erroneous is_a / subsumption remarks): {len(weak_hits)}")
    for onto in sorted(weak_hits):
        n = len(groups[onto])
        mark = "✓" if args.include_weak else "·"
        print(f"  {mark} {onto}  [{category_by_onto[onto]}]  (applies to {n} class(es))")
        for s in weak_hits[onto]:
            print(f"       “{s}”")

    apply_set = set(strong_hits)
    if args.include_weak:
        apply_set |= set(weak_hits)
    if exclude:
        skipped = {o for o in apply_set if o.upper() in exclude}
        apply_set -= skipped
        if skipped:
            print(f"\nExcluded from apply (--exclude): {', '.join(sorted(skipped))}")

    if not args.apply:
        print("\n(DRY RUN) Nothing written. Re-run with --apply to set STRONG matches,")
        print("          add --include-weak to also set the weak ones.")
        return 0

    # category to write per class_iri
    category_for_iri: dict[str, str] = {}
    for onto in apply_set:
        cat = category_by_onto.get(onto, DEFAULT_CATEGORY)
        for r in groups[onto]:
            category_for_iri[r["class_iri"]] = cat

    changed = 0
    for r in rows:
        target = category_for_iri.get(r.get("class_iri", ""))
        if target and r.get("logical_inconsistency", "") != target:
            r["logical_inconsistency"] = target
            changed += 1
    with args.csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    applied_summary = ", ".join(f"{o}[{category_by_onto[o]}]" for o in sorted(apply_set))
    print(f"\nAPPLIED: set logical_inconsistency on {changed} row(s) "
          f"across {len(apply_set)} ontology(ies): {applied_summary}")
    print("Re-run the pipeline export to sync the review ontology TTL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
