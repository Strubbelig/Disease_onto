"""prefill_manual_annotations.py

Generates pre-filled rows in disease_terms_manual_annotations.csv from the
machine-generated disease_terms_review_enriched.csv using deterministic rules.
Human fields (reviewer, review_date, entity_quality_score, quality_decision,
disease_model_category where ambiguous, and all second-reviewer fields) are
left blank — they require human judgement.

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

SCOPING_DIR  = Path(__file__).resolve().parent
ENRICHED_CSV = SCOPING_DIR / "disease_terms_review_enriched.csv"
MANUAL_CSV   = SCOPING_DIR / "disease_terms_manual_annotations.csv"
MERGE        = True   # False = overwrite, True = preserve existing non-blank values

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

# BFO IRI → upper-level label (authoritative, IRI-based)
BFO_UPPER_LEVEL: dict[str, str] = {
    "BFO_0000016": "subclass of disposition",
    "BFO_0000017": "subclass of realizable entity",
    "BFO_0000019": "subclass of quality",
    "BFO_0000020": "subclass of specifically dependent continuant",
    "BFO_0000023": "subclass of role",
    "BFO_0000031": "subclass of generically dependent continuant",
    "BFO_0000040": "subclass of material entity",
    "BFO_0000004": "subclass of independent continuant",
    "BFO_0000003": "subclass of occurrent",
    "BFO_0000007": "subclass of process",
    "BFO_0000015": "subclass of process",
}

# BFO IRI → disease model category (only where mapping is unambiguous)
BFO_DISEASE_MODEL: dict[str, str] = {
    "BFO_0000016": "disease_as_disposition",
    "BFO_0000017": "disease_as_disposition",   # realizable entity subsumes disposition
    "BFO_0000007": "disease_as_process",
    "BFO_0000015": "disease_as_process",
}

# Ontology IDs that are unambiguously clinical terminologies regardless of scope category
CLINICAL_TERMINOLOGY_IDS = {
    "snomedct", "loinc", "rcd", "rh-mesh", "icd10", "icd10cm", "icd9cm",
    "icd9", "icpc2p", "ndfrt", "medgen", "radlex",
}

# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

def _text(*values: str) -> str:
    return " ".join(v.lower() for v in values if v)


def _bfo_ids_in_iris(iris_string: str) -> list[str]:
    """Extract BFO local IDs (e.g. 'BFO_0000016') from a parent_iris string."""
    return re.findall(r"BFO_\d+", iris_string)


def rule_ontology_type(row: dict) -> str:
    """Map scope category and known ontology IDs to manual ontology type."""
    ontology = row.get("ontology", "").lower().strip()
    if ontology in CLINICAL_TERMINOLOGY_IDS:
        return "clinical_terminology"
    cat = row.get("ontology_scope_category", "")
    mapping = {
        "curated_biomedical_ontology":        "curated_ontology",
        "obo_foundry_ontology":               "curated_ontology",
        "clinical_or_biomedical_terminology": "clinical_terminology",
        "value_set_or_collection":            "value_set",
        "demo_or_training_resource":          "demo_or_training_resource",
        "generated_or_local_ontology":        "generated_or_local_resource",
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
    mapping = {
        "E1_status_noncurrent":       "obsolete_or_noncurrent",
        "E2_demo_training_or_thesis": "demo_or_training_resource",
        "E3_generated_local_ontology":"out_of_scope_other",
        "E4_value_set_collection":    "value_set_or_collection",
    }
    return mapping.get(row.get("ontology_exclusion_rule", ""), "")


def rule_definition_quality(row: dict) -> str:
    """
    absent — no definition text.
    poor   — definition present but very short (≤ 50 chars); likely just a label restatement.
    partial — definition contains a restriction marker (' that ', ' which ', ': ') suggesting
              genus/differentia structure but is not clearly complete.
    Rows with longer definitions are left blank for human review.
    """
    definition = row.get("definition", "").strip()
    if not definition:
        return "absent"
    if len(definition) <= 50:
        return "poor"
    if re.search(r"\b(that|which)\b|:\s", definition):
        return "partial"
    return ""


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
    good    — ontology_versions, retrieved_at_by_database, and source_urls all present.
    partial — at least one present.
    absent  — none present.
    """
    has_version = bool(row.get("ontology_versions", "").strip())
    has_date    = bool(row.get("retrieved_at_by_database", "").strip())
    has_url     = bool(row.get("source_urls", "").strip())
    count = sum([has_version, has_date, has_url])
    if count == 3:
        return "good"
    if count > 0:
        return "partial"
    return "absent"


def rule_upper_level_interpretation(row: dict) -> str:
    """
    Priority order (highest confidence first):
    1. BFO IRI match in parent_iris — authoritative, IRI-based.
    2. 'disposition' in label, definition, or parent labels — near-certain (per domain rule).
    3. Unambiguous keywords in parent_labels ('process', 'finding', 'syndrome',
       'disorder', 'quality') — strong structural signal.
    4. BFO anchor text fallback for remaining BFO-anchored cases.
    """
    parent_iris = row.get("parent_iris", "")
    for bfo_id in _bfo_ids_in_iris(parent_iris):
        if bfo_id in BFO_UPPER_LEVEL:
            return BFO_UPPER_LEVEL[bfo_id]

    text = _text(
        row.get("preferred_label", ""),
        row.get("definition", ""),
        row.get("parent_labels", ""),
    )
    if "disposition" in text:
        return "subclass of disposition"

    parent_text = row.get("parent_labels", "").lower()
    if "process" in parent_text:
        return "subclass of process"
    if "finding" in parent_text:
        return "subclass of finding"
    if "syndrome" in parent_text:
        return "subclass of syndrome"
    if "disorder" in parent_text:
        return "subclass of disorder"
    if "quality" in parent_text:
        return "subclass of quality"

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
    Pre-fill only when the signal is near-certain:
    1. BFO IRI in parent_iris with an unambiguous disease-model mapping.
    2. 'disposition' in label, definition, or parent labels.
    3. 'process' in parent labels (structural signal from hierarchy).
    4. 'finding' in parent labels.
    5. 'syndrome' in parent labels.
    6. 'disorder' in parent labels.
    Ambiguous cases ('patholog', 'condition') are left blank.
    """
    parent_iris = row.get("parent_iris", "")
    for bfo_id in _bfo_ids_in_iris(parent_iris):
        if bfo_id in BFO_DISEASE_MODEL:
            return BFO_DISEASE_MODEL[bfo_id]

    text = _text(
        row.get("preferred_label", ""),
        row.get("definition", ""),
        row.get("parent_labels", ""),
    )
    if "disposition" in text:
        return "disease_as_disposition"

    parent_text = row.get("parent_labels", "").lower()
    if "process" in parent_text:
        return "disease_as_process"
    if "finding" in parent_text:
        return "disease_as_finding"
    if "syndrome" in parent_text:
        return "disease_as_syndrome"
    if "disorder" in parent_text:
        return "disease_as_disorder"

    return ""


# ---------------------------------------------------------------------------
# Apply all rules to one enriched row
# ---------------------------------------------------------------------------

def prefill_row(enriched: dict) -> dict:
    row: dict[str, str] = {f: "" for f in FIELDNAMES}
    # Context columns (read-only)
    row["class_iri"]           = enriched.get("class_iri", "")
    row["term"]                = enriched.get("term", "")
    row["preferred_label"]     = enriched.get("preferred_label", "")
    row["source_ontology_ids"] = enriched.get("source_ontology_ids", "")
    # Rule-based fills
    row["ontology_type_manual"]       = rule_ontology_type(enriched)
    row["native_or_imported_manual"]  = rule_native_or_imported(enriched)
    row["manual_include_status"]      = rule_include_status(enriched)
    row["manual_exclusion_reason"]    = rule_exclusion_reason(enriched)
    row["definition_quality"]         = rule_definition_quality(enriched)
    row["comment_quality"]            = rule_comment_quality(enriched)
    row["parentage_quality"]          = rule_parentage_quality(enriched)
    row["provenance_quality"]         = rule_provenance_quality(enriched)
    row["upper_level_interpretation"] = rule_upper_level_interpretation(enriched)
    row["disease_model_category"]     = rule_disease_model_category(enriched)
    return row


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def load_existing(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {r["class_iri"]: r for r in csv.DictReader(f) if r.get("class_iri")}


def merge_rows(existing: dict, prefilled: dict) -> dict:
    """Existing non-blank values win; blanks are filled from prefilled."""
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

    with ENRICHED_CSV.open(newline="", encoding="utf-8") as f:
        enriched_rows = list(csv.DictReader(f))

    output_rows = []
    n_prefilled = n_merged = 0

    for enriched in enriched_rows:
        iri = enriched.get("class_iri", "")
        prefilled = prefill_row(enriched)
        if iri in existing_rows and MERGE:
            row = merge_rows(existing_rows[iri], prefilled)
            n_merged += 1
        else:
            row = prefilled
            n_prefilled += 1
        output_rows.append(row)

    with MANUAL_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Wrote {len(output_rows)} rows to {MANUAL_CSV}")
    print(f"  prefilled fresh: {n_prefilled}, merged over existing: {n_merged}")

    from collections import Counter
    report_fields = [
        "manual_include_status", "ontology_type_manual", "native_or_imported_manual",
        "definition_quality", "comment_quality", "parentage_quality", "provenance_quality",
        "upper_level_interpretation", "disease_model_category",
    ]
    for field in report_fields:
        counts = Counter(r[field] for r in output_rows if r[field])
        if counts:
            print(f"\n  {field}:")
            for val, n in counts.most_common():
                print(f"    {val}: {n}")
        blank = sum(1 for r in output_rows if not r[field])
        print(f"    (blank / needs human review: {blank})")


if __name__ == "__main__":
    main()
