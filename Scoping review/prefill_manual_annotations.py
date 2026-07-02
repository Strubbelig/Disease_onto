"""prefill_manual_annotations.py

Generates pre-filled rows in disease_terms_manual_annotations.csv from the
machine-generated disease_terms_review_enriched.csv using deterministic rules.
Human fields (reviewer, review_date, entity_quality_score, quality_decision,
disease_model_category, review_notes, and all second-reviewer fields) are left
blank — they require human judgement.

Run from the Scoping review directory:
    python prefill_manual_annotations.py

To merge onto an existing manual annotations file instead of overwriting,
set MERGE = True below. Existing non-blank values are never overwritten.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCOPING_DIR = Path(__file__).resolve().parent
ENRICHED_CSV  = SCOPING_DIR / "disease_terms_review_enriched.csv"
MANUAL_CSV    = SCOPING_DIR / "disease_terms_manual_annotations.csv"
MERGE         = True   # False = overwrite, True = preserve existing non-blank values

FIELDNAMES = [
    "class_iri", "term", "preferred_label", "source_ontology_ids",
    "manual_include_status", "manual_exclusion_reason", "manual_exclusion_detail",
    "ontology_type_manual", "native_or_imported_manual",
    "disease_model_category", "upper_level_interpretation",
    "definition_quality", "comment_quality", "parentage_quality", "provenance_quality",
    "entity_quality_score", "quality_decision",
    "reviewer", "review_date",
    "second_reviewer", "second_review_date", "disagreement_flag", "adjudication_decision",
    "review_notes",
]

OBO_PURL = "http://purl.obolibrary.org/obo/"

# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

def _text(*values: str) -> str:
    return " ".join(v.lower() for v in values if v)


def rule_ontology_type(row: dict) -> str:
    """Map machine scope category to manual ontology type."""
    cat = row.get("ontology_scope_category", "")
    mapping = {
        "curated_biomedical_ontology": "curated_ontology",
        "obo_foundry_ontology":        "curated_ontology",
        "clinical_or_biomedical_terminology": "clinical_terminology",
        "value_set_or_collection":     "value_set",
        "demo_or_training_resource":   "demo_or_training_resource",
        "generated_or_local_ontology": "generated_or_local_resource",
    }
    return mapping.get(cat, "")


def rule_native_or_imported(row: dict) -> str:
    """Map native_term_status to native_or_imported_manual."""
    status = row.get("native_term_status", "")
    if status in {"native_source_seen", "native_source_seen_with_imports"}:
        return "native"
    if status == "likely_imported_or_reused_term":
        return "imported"
    return ""


def rule_include_status(row: dict) -> str:
    """Pre-fill inclusion status where a rule is unambiguous."""
    if row.get("ontology_exclusion_status") == "excluded_preasserted":
        return "exclude"
    iri = row.get("class_iri", "")
    if iri.startswith(OBO_PURL) or "OBO Foundry Direct" in row.get("source_databases", ""):
        return "include"
    return ""


def rule_exclusion_reason(row: dict) -> str:
    """Map machine exclusion rule codes to manual exclusion reason."""
    if row.get("ontology_exclusion_status") != "excluded_preasserted":
        return ""
    rule = row.get("ontology_exclusion_rule", "")
    mapping = {
        "E1_status_noncurrent":      "obsolete_or_noncurrent",
        "E2_demo_training_or_thesis":"demo_or_training_resource",
        "E3_generated_local_ontology":"out_of_scope_other",
        "E4_value_set_collection":   "value_set_or_collection",
    }
    return mapping.get(rule, "")


def rule_definition_quality(row: dict) -> str:
    """Mark absent when no definition text is present."""
    return "absent" if not row.get("definition", "").strip() else ""


def rule_comment_quality(row: dict) -> str:
    """Mark absent when no comment text is present."""
    return "absent" if not row.get("comments", "").strip() else ""


def rule_parentage_quality(row: dict) -> str:
    """Mark absent when no parent is recorded."""
    if not row.get("parent_labels", "").strip() and not row.get("parent_iris", "").strip():
        return "absent"
    return ""


def rule_provenance_quality(row: dict) -> str:
    """
    good  — ontology_versions, retrieved_at_by_database, and source_urls all present.
    partial — at least one present.
    absent — none present.
    """
    has_version  = bool(row.get("ontology_versions", "").strip())
    has_date     = bool(row.get("retrieved_at_by_database", "").strip())
    has_url      = bool(row.get("source_urls", "").strip())
    count = sum([has_version, has_date, has_url])
    if count == 3:
        return "good"
    if count > 0:
        return "partial"
    return "absent"


def rule_upper_level_interpretation(row: dict) -> str:
    """
    If 'disposition' appears in label, definition, or parent labels the class
    is almost certainly modelled as a disposition at the upper level.
    """
    text = _text(
        row.get("preferred_label", ""),
        row.get("definition", ""),
        row.get("parent_labels", ""),
    )
    if "disposition" in text:
        return "subclass of disposition"
    # Seed from BFO anchor when present and unambiguous
    anchor = row.get("bfo_anchor", "").lower()
    if anchor:
        if "disposition" in anchor:
            return "subclass of disposition"
        if "process" in anchor:
            return "subclass of process"
        if "quality" in anchor:
            return "subclass of quality"
        if "material entity" in anchor or "object" in anchor:
            return "subclass of material entity"
        if "information" in anchor:
            return "subclass of information content entity"
        if "role" in anchor:
            return "subclass of role"
        if "function" in anchor:
            return "subclass of function"
        if "site" in anchor:
            return "subclass of site"
    return ""


def rule_disease_model_category(row: dict) -> str:
    """
    Pre-fill only when the signal is unambiguous. 'disposition' in label,
    definition, or parent labels is treated as almost certain.
    """
    text = _text(
        row.get("preferred_label", ""),
        row.get("definition", ""),
        row.get("parent_labels", ""),
    )
    if "disposition" in text:
        return "disease_as_disposition"
    return ""


# ---------------------------------------------------------------------------
# Apply all rules to one enriched row
# ---------------------------------------------------------------------------

def prefill_row(enriched: dict) -> dict:
    row: dict[str, str] = {f: "" for f in FIELDNAMES}
    # Context columns (read-only)
    row["class_iri"]          = enriched.get("class_iri", "")
    row["term"]               = enriched.get("term", "")
    row["preferred_label"]    = enriched.get("preferred_label", "")
    row["source_ontology_ids"]= enriched.get("source_ontology_ids", "")
    # Rule-based fills
    row["ontology_type_manual"]      = rule_ontology_type(enriched)
    row["native_or_imported_manual"] = rule_native_or_imported(enriched)
    row["manual_include_status"]     = rule_include_status(enriched)
    row["manual_exclusion_reason"]   = rule_exclusion_reason(enriched)
    row["definition_quality"]        = rule_definition_quality(enriched)
    row["comment_quality"]           = rule_comment_quality(enriched)
    row["parentage_quality"]         = rule_parentage_quality(enriched)
    row["provenance_quality"]        = rule_provenance_quality(enriched)
    row["upper_level_interpretation"]= rule_upper_level_interpretation(enriched)
    row["disease_model_category"]    = rule_disease_model_category(enriched)
    return row


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def load_existing(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {r["class_iri"]: r for r in csv.DictReader(f) if r.get("class_iri")}


def merge(existing: dict, prefilled: dict) -> dict:
    """Return merged row: existing non-blank values win; blanks filled from prefilled."""
    merged = dict(prefilled)
    for key, value in existing.items():
        if key in merged and value.strip():
            merged[key] = value
    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    existing_rows = load_existing(MANUAL_CSV) if MERGE else {}

    enriched_rows = []
    with ENRICHED_CSV.open(newline="", encoding="utf-8") as f:
        enriched_rows = list(csv.DictReader(f))

    output_rows = []
    stats = {"prefilled": 0, "merged": 0, "disposition_flagged": 0}

    for enriched in enriched_rows:
        iri = enriched.get("class_iri", "")
        prefilled = prefill_row(enriched)
        if prefilled.get("upper_level_interpretation") == "subclass of disposition":
            stats["disposition_flagged"] += 1
        if iri in existing_rows and MERGE:
            row = merge(existing_rows[iri], prefilled)
            stats["merged"] += 1
        else:
            row = prefilled
            stats["prefilled"] += 1
        output_rows.append(row)

    with MANUAL_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Wrote {len(output_rows)} rows to {MANUAL_CSV}")
    print(f"  prefilled: {stats['prefilled']}, merged over existing: {stats['merged']}")
    print(f"  disposition signal detected: {stats['disposition_flagged']} rows")

    # Summary of what was prefilled
    from collections import Counter
    for field in ["manual_include_status", "ontology_type_manual",
                  "native_or_imported_manual", "definition_quality",
                  "parentage_quality", "provenance_quality",
                  "upper_level_interpretation", "disease_model_category"]:
        counts = Counter(r[field] for r in output_rows if r[field])
        if counts:
            print(f"\n  {field}:")
            for val, n in counts.most_common():
                print(f"    {val}: {n}")


if __name__ == "__main__":
    main()
