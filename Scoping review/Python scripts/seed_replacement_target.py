#!/usr/bin/env python3
"""Seed a manual replacement review target and skip the class it replaces.

Some ontologies (e.g. the Menelas-derived ONTOLURGENCES / OntoPneumo / OntoAD
family) carry a French 'État pathologique' class that the search terms never
matched, so only their 'syndrome' class was extracted. This script seeds the
'état pathologique' class as the review target (like the EPO HealthCondition
precedent) and lets the general selection rule skip the ontology's generic
'syndrome' class in its favour.

It writes to disease_terms_review_enriched.csv and
disease_terms_manual_annotations.csv, then you re-run the pipeline export
(--chunk export-review-ontology) to sync the review ontology TTL.

Usage
-----
    python3 "seed_replacement_target.py" \
        --ontology ONTOPNEUMO \
        --target-iri http://doe-generated-ontology.com/OntoPneumo#EtatPathologique

Options:
    --target-label   label for the seeded class (default 'état pathologique')
    --parent-iri     optional superclass IRI to record in the generated module
    --parent-label   optional superclass label
    --replaced-label the generic class to skip in favour of the target
                     (default 'syndrome')
    --dry-run        show what would change, write nothing
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TABLES = SCRIPT_DIR.parent / "Extraction Tables"
ENRICHED = TABLES / "disease_terms_review_enriched.csv"
MANUAL = TABLES / "disease_terms_manual_annotations.csv"

sys.path.insert(0, str(SCRIPT_DIR))
import prefill_manual_annotations as m  # noqa: E402


def local_name(iri: str) -> str:
    return iri.split("#")[-1].split("/")[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ontology", required=True, help="Ontology key as in the enriched 'ontology' column, e.g. ONTOPNEUMO.")
    ap.add_argument("--target-iri", required=True, help="Full IRI of the replacement target class.")
    ap.add_argument("--target-label", default="état pathologique")
    ap.add_argument("--parent-iri", default="")
    ap.add_argument("--parent-label", default="")
    ap.add_argument("--replaced-label", default="syndrome", help="Generic class label to skip in favour of the target.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    enr = list(csv.DictReader(ENRICHED.open(encoding="utf-8")))
    enr_cols = list(enr[0].keys())
    man = list(csv.DictReader(MANUAL.open(encoding="utf-8")))
    man_cols = list(man[0].keys())

    onto_rows = [r for r in enr if (r.get("ontology", "") or "").upper() == args.ontology.upper()]
    if not onto_rows:
        sys.exit(f"ERROR: no enriched rows for ontology {args.ontology!r}.")
    base = onto_rows[0]
    base_local = local_name(base["class_iri"])
    tgt_local = local_name(args.target_iri)

    # ---- seed enriched target row (mirror provenance from a sibling row) ----
    if any(r["class_iri"] == args.target_iri for r in enr):
        print(f"note: {args.target_iri} already in enriched; not re-seeding.")
    else:
        e = dict(base)
        e["class_iri"] = args.target_iri
        e["term"] = ""
        e["preferred_label"] = args.target_label
        e["discovery_tier"] = "manual_parent_replacement"
        e["definition"] = ""
        e["comments"] = ""
        e["synonyms"] = ""
        e["parent_iris"] = args.parent_iri
        e["parent_labels"] = args.parent_label
        for col in ("source_urls", "source_records"):
            e[col] = base.get(col, "").replace(base_local, tgt_local)
        e["native_ontology_guess"] = args.ontology
        e["native_term_status"] = "native_source_seen"
        e["native_source_ontology_ids"] = args.ontology
        e["source_appearance_summary"] = f"manual replacement target for {args.ontology} {args.replaced_label}"
        e["review_route"] = "manual_selected_replacement_target"
        e["manual_screening_hint"] = f"manual replacement for {args.ontology} {args.replaced_label}; review {tgt_local} instead of {args.replaced_label.title()}"
        enr.append(e)
        print(f"seeded enriched target: {args.target_iri}")

    # register AFTER seeding so the target counts as a disease representative
    m.register_ontology_disease_context(enr)
    enr_by_iri = {r["class_iri"]: r for r in enr}

    # ---- seed manual target row (include) ----
    if not any(r["class_iri"] == args.target_iri for r in man):
        pf = m.prefill_row(enr_by_iri[args.target_iri])
        pf["manual_include_status"] = "include"
        pf["review_comment"] = f"Manual replacement target for {args.ontology} {args.replaced_label}; review {tgt_local} instead of {args.replaced_label.title()}."
        man.append({k: pf.get(k, "") for k in man_cols})
        print(f"seeded manual target row (include): {args.target_iri}")

    # ---- skip the replaced generic class where unreviewed ----
    applied, kept = [], []
    for r in man:
        e = enr_by_iri.get(r["class_iri"], {})
        if (e.get("ontology", "") or "").upper() != args.ontology.upper():
            continue
        if m._norm_label(e.get("preferred_label", "") or e.get("term", "")) != m._norm_label(args.replaced_label):
            continue
        inc = r.get("manual_include_status", "").strip()
        if inc == "":
            r["manual_include_status"] = "exclude"
            r["manual_exclusion_reason"] = m.REPLACED_CLASS_EXCLUSION_REASON
            r["manual_exclusion_detail"] = m.SYNDROME_EXCLUSION_DETAIL
            r["entity_quality_score"] = "0"
            applied.append(r["class_iri"])
        else:
            kept.append(f"{r['class_iri']} ({inc})")

    print(f"\nskipped {args.replaced_label} (was blank): {applied}")
    if kept:
        print(f"left already-reviewed (unchanged): {kept}")

    if args.dry_run:
        print("\n(DRY RUN) nothing written.")
        return 0

    with ENRICHED.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=enr_cols); w.writeheader(); w.writerows(enr)
    with MANUAL.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=man_cols); w.writeheader(); w.writerows(man)
    print("\nWrote enriched + manual CSVs. Re-run the pipeline export to sync the TTL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
