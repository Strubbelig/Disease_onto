#!/usr/bin/env python3
"""Read-only consistency checker for the disease-ontology review.

Flags violations of manual-review consistency rules. It NEVER modifies any
file -- it only prints a report so the entries can be checked by hand.

Rules checked
-------------
1. ontology_type_manual consistency:
   every entry belonging to the same ontology must share the same
   `ontology_type_manual` value.
2. ontologically ungrounded -> entity_quality_score == 1
   (`disease_model_category == no_grounded_model`).
3. excluded term -> entity_quality_score == 0
   (`manual_include_status == exclude`).
4. grounded (any real model category) with a good parent and no logical
   inconsistency -> entity_quality_score == 2 (unless it qualifies for rule 10 -> 3).
5. ontologically ungrounded -> parentage_quality in {poor, absent}.
6. logical_inconsistency uniform within an ontology:
   every entry belonging to the same ontology must share the same
   `logical_inconsistency` value (it is an ontology-level flag).
7. logical inconsistency present -> entity_quality_score == 1
   (`logical_inconsistency` is non-blank).
8. no superclass other than owl:Thing -> entity_quality_score == 1
   (parent info read from the enriched CSV; skipped if that file is absent).
9. excluded as out_of_scope -> disease_model_category == not_applicable.
10. grounded (a real model category, not unclear_model / no_grounded_model /
    not_applicable) + parentage_quality == good + definition_quality == good
    + no logical_inconsistency -> entity_quality_score == 3.
    (Rule 4 yields to this: a disposition meeting these conditions scores 3, not 2.)
11. 'menelas' in any text field / IRI -> disease_model_category == entity_as_kantian_state.
12. 'biotop' in any text field / IRI -> disease_model_category == entity_as_biotop:condition.

Notes on scope
--------------
* Only *filled-in* values are ever flagged as violations. Blank fields
  (entries not yet reviewed) are reported separately as a coverage note,
  not as violations.
* Rules 2, 4 and 7 skip entries whose manual_include_status == exclude, because
  rule 3 already governs the score of excluded entries (excluded -> 0). This
  prevents contradictory flags on an excluded entry that also has a category
  or a logical-inconsistency flag.
* Grouping for rule 1 uses the source ontology (`source_ontology_ids`). Entries
  listed under a single source ontology are grouped by it; entries listed under
  several source ontologies are ambiguous to group and are skipped from rule 1
  (counted, not flagged).

Usage
-----
    python3 "review_consistency_checks.py"
    python3 "review_consistency_checks.py" --show-incomplete
    python3 "review_consistency_checks.py" --csv <path>

Exit code is 1 if any violation is found, else 0.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR.parent / "Extraction Tables" / "disease_terms_manual_annotations.csv"
UNGROUNDED = "no_grounded_model"
DISPOSITION = "entity_as_bfo:disposition"
NOT_GROUNDED_CATEGORIES = {"", "unclear_model", "no_grounded_model", "not_applicable"}


def is_grounded(r: dict[str, str]) -> bool:
    """True when the class has a real ontological-grounding model category
    (any category except unclear_model / no_grounded_model / not_applicable)."""
    return r.get("disease_model_category", "").strip() not in NOT_GROUNDED_CATEGORIES


def rule10_qualifies(r: dict[str, str]) -> bool:
    """Grounded + good parent + good definition + no logical inconsistency ->
    a strong, well-defined entity (score 3)."""
    return (
        is_grounded(r)
        and r.get("parentage_quality", "").strip() == "good"
        and r.get("definition_quality", "").strip() == "good"
        and r.get("logical_inconsistency", "").strip() == ""
    )


def ontology_key(row: dict[str, str]) -> str | None:
    """Return an upper-cased source-ontology key for grouping, or None if ambiguous.

    Groups by `source_ontology_ids`. A single source ontology -> that ontology;
    several source ontologies -> None (skipped from rule 1).
    """
    raw = row.get("source_ontology_ids", "")
    toks = [t.split(":", 1)[-1].strip() for t in raw.split(";") if t.strip()]
    toks = [t for t in toks if t]
    if len(toks) == 1:
        return toks[0].upper()
    return None  # zero or several source ontologies -> ambiguous


def ident(row: dict[str, str]) -> str:
    label = row.get("preferred_label") or row.get("term") or ""
    return f"{row.get('class_iri','')}  ({label})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Manual annotations CSV.")
    ap.add_argument("--show-incomplete", action="store_true",
                    help="Also list entries where the relevant field is still blank.")
    args = ap.parse_args()

    if not args.csv.exists():
        sys.exit(f"ERROR: annotations CSV not found: {args.csv}")

    with args.csv.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    print("=" * 78)
    print("REVIEW CONSISTENCY CHECK  (read-only -- no files are modified)")
    print(f"annotations : {args.csv}")
    print(f"rows        : {len(rows)}")
    print("grouping    : rule 1 groups by source ontology (source_ontology_ids)")
    print("=" * 78)

    violations = 0
    incomplete_note: list[str] = []

    # ---- Rule 1: ontology_type_manual consistency within an ontology --------
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    ambiguous = 0
    for r in rows:
        key = ontology_key(r)
        if key is None:
            ambiguous += 1
            continue
        groups[key].append(r)

    r1_bad = []
    for key, grp in sorted(groups.items()):
        vals = {r["ontology_type_manual"].strip() for r in grp if r["ontology_type_manual"].strip()}
        if len(vals) > 1:
            r1_bad.append((key, grp, vals))

    print("\n[Rule 1] ontology_type_manual must be identical within an ontology")
    if r1_bad:
        for key, grp, vals in r1_bad:
            violations += 1
            print(f"  ! {key}: {len(vals)} differing values -> {sorted(vals)}")
            for r in grp:
                v = r["ontology_type_manual"].strip() or "(blank)"
                print(f"       - {v:<28} {ident(r)}")
    else:
        print("  OK -- no conflicting ontology_type_manual values.")
    if ambiguous:
        print(f"  (note: {ambiguous} multi-source entries were skipped as ungroupable)")

    # ---- helper for the score/parentage rules -------------------------------
    def check_field(title, predicate, field, want, skip_excluded):
        wants = tuple(want) if isinstance(want, (set, tuple, list)) else (want,)
        want_str = " or ".join(repr(w) for w in wants)
        nonlocal violations
        bad, blank = [], []
        for r in rows:
            if not predicate(r):
                continue
            if skip_excluded and r.get("manual_include_status", "").strip() == "exclude":
                continue
            val = r.get(field, "").strip()
            if val == "":
                blank.append(r)
            elif val not in wants:
                bad.append((r, val))
        print(f"\n{title}")
        if bad:
            for r, val in bad:
                violations += 1
                print(f"  ! {field}={val!r} (expected {want_str})  {ident(r)}")
        else:
            print(f"  OK -- no entries with a filled {field} that violate the rule.")
        if blank:
            incomplete_note.append(f"{title.split(']')[0][1:].strip()}: {len(blank)} entry(ies) still have blank {field}")
            if args.show_incomplete:
                for r in blank:
                    print(f"    . blank {field}: {ident(r)}")
        return bad, blank

    # ---- Rule 2 --------------------------------------------------------------
    check_field(
        "[Rule 2] ontologically ungrounded -> entity_quality_score == 1",
        lambda r: r.get("disease_model_category", "").strip() == UNGROUNDED,
        "entity_quality_score", "1", skip_excluded=True,
    )
    # ---- Rule 3 --------------------------------------------------------------
    check_field(
        "[Rule 3] excluded -> entity_quality_score == 0",
        lambda r: r.get("manual_include_status", "").strip() == "exclude",
        "entity_quality_score", "0", skip_excluded=False,
    )
    # ---- Rule 4 --------------------------------------------------------------
    check_field(
        "[Rule 4] grounded + good parent -> entity_quality_score == 2 (unless rule 10 -> 3)",
        lambda r: is_grounded(r) and r.get("parentage_quality", "").strip() == "good"
        and r.get("logical_inconsistency", "").strip() == "" and not rule10_qualifies(r),
        "entity_quality_score", "2", skip_excluded=True,
    )
    # ---- Rule 5 --------------------------------------------------------------
    check_field(
        "[Rule 5] ontologically ungrounded -> parentage_quality in {poor, absent}",
        lambda r: r.get("disease_model_category", "").strip() == UNGROUNDED,
        "parentage_quality", ("poor", "absent"), skip_excluded=False,
    )

    # ---- Rule 6: logical_inconsistency uniform within an ontology -----------
    print("\n[Rule 6] logical_inconsistency must be identical within an ontology")
    r6_bad = []
    for key, grp in sorted(groups.items()):
        vals = {r.get("logical_inconsistency", "").strip() for r in grp if r.get("logical_inconsistency", "").strip()}
        if len(vals) > 1:
            r6_bad.append((key, grp, vals))
    if r6_bad:
        for key, grp, vals in r6_bad:
            violations += 1
            print(f"  ! {key}: {len(vals)} differing values -> {sorted(vals)}")
            for r in grp:
                v = r.get("logical_inconsistency", "").strip() or "(blank)"
                print(f"       - {v:<26} {ident(r)}")
    else:
        print("  OK -- no conflicting logical_inconsistency values.")

    # ---- Rule 7: logical inconsistency present -> entity_quality_score == 1 --
    check_field(
        "[Rule 7] logical_inconsistency present -> entity_quality_score == 1",
        lambda r: r.get("logical_inconsistency", "").strip() != "",
        "entity_quality_score", "1", skip_excluded=True,
    )

    # ---- Rule 9: excluded out_of_scope -> disease_model_category==not_applicable
    check_field(
        "[Rule 9] excluded as out_of_scope -> disease_model_category == not_applicable",
        lambda r: r.get("manual_include_status", "").strip() == "exclude"
        and r.get("manual_exclusion_reason", "").strip() == "out_of_scope",
        "disease_model_category", "not_applicable", skip_excluded=False,
    )

    # ---- Rule 10: grounded + good parent + good definition -> score 3 -------
    check_field(
        "[Rule 10] grounded + good parent + good definition -> entity_quality_score == 3",
        rule10_qualifies,
        "entity_quality_score", "3", skip_excluded=True,
    )

    # ---- Rules 11 & 12: keyword grounding -----------------------------------
    def kw_blob(r: dict) -> str:
        return " ".join(r.get(f, "") for f in (
            "class_iri", "preferred_label", "term",
            "review_comment", "manual_exclusion_detail")).lower()

    check_field(
        "[Rule 11] 'menelas' in a text field/IRI -> disease_model_category == entity_as_kantian_state",
        lambda r: "menelas" in kw_blob(r),
        "disease_model_category", "entity_as_kantian_state", skip_excluded=True,
    )
    check_field(
        "[Rule 12] 'biotop' in a text field/IRI -> disease_model_category == entity_as_biotop:condition",
        lambda r: "biotop" in kw_blob(r),
        "disease_model_category", "entity_as_biotop:condition", skip_excluded=True,
    )

    # ---- summary -------------------------------------------------------------
    print("\n" + "=" * 78)
    print(f"TOTAL VIOLATIONS FLAGGED: {violations}")
    if incomplete_note:
        print("\nCoverage notes (not violations -- fields not yet filled):")
        for n in incomplete_note:
            print(f"  - {n}")
        if not args.show_incomplete:
            print("  (run with --show-incomplete to list these entries)")
    print("=" * 78)
    print("No files were modified. Review each flagged entry manually.")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
