"""Deterministic prefill rules for the disease review master CSV.

The rules are imported by ``review_extraction_pipeline.py``. Direct execution
updates ``disease_terms_review_enriched.csv`` in place while preserving every
existing non-blank human decision and every extraction/citation column. No
separate manual-annotation table is created.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
TABLE_DIR = SCRIPT_DIR.parent / "Extraction Tables"
MASTER_CSV = TABLE_DIR / "disease_terms_review_enriched.csv"

FIELDNAMES = [
    "class_iri", "term", "preferred_label", "source_ontology_ids",
    "manual_include_status", "manual_exclusion_reason", "manual_exclusion_detail",
    "ontology_type_manual", "native_or_imported_manual", "logical_inconsistency",
    "disease_model_category", "no_grounded_model_subtype",
    "ontological_category", "pathological_grounding", "crisp_vs_graded", "reality_vs_classification",
    "review_comment",
    "definition_quality", "comment_quality", "parentage_quality",
    "entity_quality_score", "quality_decision",
    "reviewer", "review_date",
    "second_reviewer", "second_review_date", "disagreement_flag", "adjudication_decision",
]

OBO_PURL = "http://purl.obolibrary.org/obo/"

IFOMIS_DISPOSITION_PARENT_IRIS = {
    "http://www.ifomis.org/snap#disposition",
    "http://www.ifomis.org/bfo/1.1/snap#disposition",
    "http://www.ifomis.org/bfo/snap#disposition",
    "http://www.ifomis.org/bf0/snap#disposition",
}
IFOMIS_DISPOSITION_INTERPRETATION = "Subclass of disposition, clear BFO legacy."
REPLACED_CLASS_IRIS = {
    "http://purl.org/cpr/syndrome",
    "http://purl.obolibrary.org/obo/DOID_225",
    "http://purl.obolibrary.org/obo/OGMS_0000045",
    "http://purl.obolibrary.org/obo/GSSO_000487",
    "http://purl.obolibrary.org/obo/GSSO_000497",
    "http://www.semanticweb.org/ontologies/epo.owl#Syndrome",
    # SIO: disease (SIO_010299) is the reviewed representative; dysfunction and
    # syndrome are redundant and not reviewed independently.
    "http://semanticscience.org/resource/SIO_000354",
    "http://semanticscience.org/resource/SIO_001017",
    # TRAK: disease (TRAK_0000205) is reviewed; disorder is redundant.
    "http://purl.obolibrary.org/obo/TRAK_0000610",
}
REPLACED_CLASS_EXCLUSION_REASON = "replaced_by_better_native_disease_model_candidate"
REPLACED_CLASS_EXCLUSION_DETAIL = "Skipped because the review already includes the stronger representative disease class for this ontology/source."
DISJUNCTIVE_DISEASE_EXCLUSION_DETAIL = "Skipped: disjunctive 'Disease or …' class; the ontology's plain disease class is reviewed instead of a combined Disease-or-X term."
SYNDROME_EXCLUSION_DETAIL = "Skipped: generic 'syndrome' class; the ontology's disease or état pathologique class is reviewed as the representative instead."

# Ontologies (lower-cased key) that contain a plain 'disease' class, and those
# that contain any disease representative (plain disease OR état pathologique /
# pathological state). Populated from the full enriched row set via
# register_ontology_disease_context() before prefilling, so the skip rules can
# check for a sibling representative class.
_ONTOLOGIES_WITH_PLAIN_DISEASE: set[str] = set()
_ONTOLOGIES_WITH_DISEASE_REPRESENTATIVE: set[str] = set()

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

# BFO IRI -> reviewed entity model category (only where mapping is unambiguous)
BFO_DISEASE_MODEL: dict[str, str] = {
    "BFO_0000016": "entity_as_bfo:disposition",
    "BFO_0000017": "entity_as_realizable_entity",
    "BFO_0000020": "entity_as_dependent_continuant",
    "BFO_0000007": "entity_as_process",
    "BFO_0000015": "entity_as_process",
}

# --- Ontological category (continuant vs occurrent) -------------------------
# disease_model_category values whose BFO/upper-level anchor makes the
# continuant/occurrent split certain. Debatable types (finding, syndrome,
# disorder, biotop:condition, kantian_state) are intentionally NOT listed and
# left blank for human review ("blank unless anchored").
CONTINUANT_MODEL_CATEGORIES = {
    "entity_as_bfo:disposition",
    "entity_as_disposition_non_bfo",
    "entity_as_realizable_entity",
    "entity_as_dependent_continuant",
    "entity_as_sio:quality",
}
OCCURRENT_MODEL_CATEGORIES = {
    "entity_as_process",
}
BIOLOGICAL_STATE_MODEL_CATEGORIES = {
    "entity_as_bfo:disposition",
    "entity_as_disposition_non_bfo",
    "entity_as_realizable_entity",
    "entity_as_dependent_continuant",
    "entity_as_sio:quality",
    "entity_as_process",
    "entity_as_biotop:condition",
    "entity_as_domain_specific_abnormal_pattern",
    "entity_as_pathology",
    "entity_as_disorder",
}
NOSOLOGICAL_NO_GROUNDED_SUBTYPES = {
    "finding_or_phenotype_route",
    "information_model_wrapper",
}
# Raw BFO IRI fragments, used as a fallback when a class carries a BFO parent
# but no model-category mapping fired.
BFO_OCCURRENT_IDS = {"BFO_0000003", "BFO_0000007", "BFO_0000015"}
BFO_CONTINUANT_IDS = {
    "BFO_0000002", "BFO_0000004", "BFO_0000016", "BFO_0000017",
    "BFO_0000019", "BFO_0000020", "BFO_0000023", "BFO_0000031", "BFO_0000040",
}

# Ontology IDs that are unambiguously clinical terminologies regardless of scope category
CLINICAL_TERMINOLOGY_IDS = {
    "snomedct", "loinc", "rcd", "icd10", "icd10cm", "icd9cm",
    "icd9", "icpc2p", "ndfrt", "medgen", "radlex",
}

THESAURUS_ONTOLOGY_IDS = {"mesh", "rh-mesh", "mdm", "mstde", "umls", "ncit"}
THESAURUS_METADATA_PHRASES = {
    "thesaurus",
    "medical subject headings",
    "national cancer institute thesaurus",
    "umls metathesaurus",
    "metathesaurus",
}

THESAURUS_REVIEW_DISABLED_FIELDS = {
    "native_or_imported_manual",
    "disease_model_category",
    "no_grounded_model_subtype",
    "ontological_category",
    "pathological_grounding",
    "crisp_vs_graded",
    "reality_vs_classification",
    "review_comment",
    "definition_quality",
    "comment_quality",
    "parentage_quality",
    "entity_quality_score",
    "quality_decision",
    "reviewer",
    "review_date",
}
THESAURUS_EXCLUSION_DETAIL = "Source type marked as thesaurus/controlled vocabulary, including NCIT, MeSH, and UMLS Metathesaurus; excluded from independent class-level modelling review."

# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

def _text(*values: str) -> str:
    return " ".join(v.lower() for v in values if v)


def is_thesaurus_resource(row: dict) -> bool:
    ontology = row.get("ontology", "").lower().strip()
    text = _text(
        row.get("ontology_title", ""),
        row.get("ontology_description", ""),
        row.get("source_ontology_ids", ""),
    )
    return ontology in THESAURUS_ONTOLOGY_IDS or any(phrase in text for phrase in THESAURUS_METADATA_PHRASES)


def _bfo_ids_in_iris(iris_string: str) -> list[str]:
    """Extract BFO local IDs (e.g. 'BFO_0000016') from a parent_iris string."""
    return re.findall(r"BFO_\d+", iris_string)


def has_ifomis_disposition_parent(row: dict) -> bool:
    parent_iris = row.get("parent_iris", "").lower()
    return any(iri in parent_iris for iri in IFOMIS_DISPOSITION_PARENT_IRIS)


def is_replaced_class(row: dict) -> bool:
    return row.get("class_iri", "").strip() in REPLACED_CLASS_IRIS


def _norm_label(value: str) -> str:
    """Lower-case, collapse whitespace, and strip accents so French labels like
    'État pathologique' fold to 'etat pathologique'."""
    s = unicodedata.normalize("NFKD", value or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.strip().lower())


def is_disease_representative_label(label: str) -> bool:
    """A class label that serves as an ontology's primary disease/condition
    representative: a plain 'disease' or an 'état pathologique' /
    'pathological state|condition' class."""
    n = _norm_label(label)
    return n in {"disease", "etat pathologique", "pathological state", "pathological condition"}


def is_disjunctive_disease_label(label: str) -> bool:
    """True for combined labels like 'Disease or Syndrome', 'X or Disease',
    'Disease or Disorder or Finding' — a disjunction ('… or …') in which one
    disjunct is exactly 'disease'. A plain 'Disease' label is NOT disjunctive.
    'Disorder' etc. are safe because the split is on the standalone word 'or'."""
    norm = _norm_label(label)
    parts = [p.strip() for p in re.split(r"\bor\b", norm) if p.strip()]
    return len(parts) >= 2 and "disease" in parts


def register_ontology_disease_context(enriched_rows: list[dict]) -> None:
    """Record which ontologies contain a plain 'disease' class and which contain
    any disease representative (plain disease OR état pathologique), so the skip
    rules can require a sibling representative to review instead."""
    _ONTOLOGIES_WITH_PLAIN_DISEASE.clear()
    _ONTOLOGIES_WITH_DISEASE_REPRESENTATIVE.clear()
    for r in enriched_rows:
        onto = (r.get("ontology", "") or "").strip().lower()
        if not onto:
            continue
        label = r.get("preferred_label", "")
        if _norm_label(label) == "disease":
            _ONTOLOGIES_WITH_PLAIN_DISEASE.add(onto)
        if is_disease_representative_label(label):
            _ONTOLOGIES_WITH_DISEASE_REPRESENTATIVE.add(onto)


def is_skipped_disjunctive_disease(row: dict) -> bool:
    """Skip a 'Disease or X' class only when its ontology also has a plain
    disease class to review instead."""
    onto = (row.get("ontology", "") or "").strip().lower()
    if onto not in _ONTOLOGIES_WITH_PLAIN_DISEASE:
        return False
    label = row.get("preferred_label", "") or row.get("term", "")
    return is_disjunctive_disease_label(label)


def is_skipped_syndrome(row: dict) -> bool:
    """Skip a generic 'syndrome' class when its ontology has a stronger disease
    representative (plain disease OR état pathologique) to review instead.
    Only the bare 'syndrome' class is affected, not named syndromes."""
    onto = (row.get("ontology", "") or "").strip().lower()
    if onto not in _ONTOLOGIES_WITH_DISEASE_REPRESENTATIVE:
        return False
    label = row.get("preferred_label", "") or row.get("term", "")
    return _norm_label(label) == "syndrome"


def is_skipped_in_favor_of_disease(row: dict) -> bool:
    """A class superseded by a stronger disease representative: a hard-coded
    replaced class, a disjunctive Disease-or-X class (plain disease sibling), or
    a generic syndrome class (disease / état pathologique sibling)."""
    return is_replaced_class(row) or is_skipped_disjunctive_disease(row) or is_skipped_syndrome(row)


def rule_ontology_type(row: dict) -> str:
    """Map scope category and known ontology IDs to manual ontology type."""
    ontology = row.get("ontology", "").lower().strip()
    if is_thesaurus_resource(row):
        return "thesaurus"
    if has_ifomis_disposition_parent(row):
        return "curated_ontology"
    if ontology in CLINICAL_TERMINOLOGY_IDS:
        return "clinical_terminology"
    cat = row.get("ontology_scope_category", "")
    mapping = {
        "curated_biomedical_ontology":        "curated_ontology",
        "obo_foundry_ontology":               "curated_ontology",
        "clinical_or_biomedical_terminology": "clinical_terminology",
        "thesaurus":                          "thesaurus",
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
    if is_skipped_in_favor_of_disease(row):
        return "exclude"
    if has_ifomis_disposition_parent(row):
        return "include"
    if row.get("ontology_exclusion_status") == "excluded_preasserted":
        return "exclude"
    iri = row.get("class_iri", "")
    if iri.startswith(OBO_PURL) or "OBO Foundry Direct" in row.get("source_databases", ""):
        return "include"
    return ""


def rule_exclusion_reason(row: dict) -> str:
    """Map machine exclusion rule codes to manual exclusion reason."""
    if is_skipped_in_favor_of_disease(row):
        return REPLACED_CLASS_EXCLUSION_REASON
    if has_ifomis_disposition_parent(row):
        return ""
    if row.get("ontology_exclusion_status") != "excluded_preasserted":
        return ""
    mapping = {
        "E1_status_noncurrent":       "obsolete_or_noncurrent",
        "E2_demo_training_or_thesis": "demo_or_training_resource",
        "E3_generated_local_ontology":"out_of_scope",
        "E4_value_set_collection":    "value_set_or_collection",
        "E5_thesaurus_title":         "terminology_not_ontology",
    }
    return mapping.get(row.get("ontology_exclusion_rule", ""), "")


def rule_exclusion_detail(row: dict) -> str:
    if row.get("class_iri", "").strip() == "http://purl.obolibrary.org/obo/DOID_225":
        return "Skipped because DOID:disease (DOID_4) is already included as the Human Disease Ontology representative disease class."
    if row.get("class_iri", "").strip() == "http://www.semanticweb.org/ontologies/epo.owl#Syndrome":
        return "Skipped because EPO health condition is the more informative parent class for reviewing EPO disease/condition modelling."
    if row.get("class_iri", "").strip() in {
        "http://purl.obolibrary.org/obo/GSSO_000487",
        "http://purl.obolibrary.org/obo/GSSO_000497",
    }:
        return "Skipped because GSSO disease and disorder have already been reviewed as sufficient representative disease/condition classes for GSSO."
    if row.get("class_iri", "").strip() == "http://purl.obolibrary.org/obo/OGMS_0000045":
        return "Skipped because OGMS disease is already included, and OGMS disorder is not treated as a synonym of disease for this review."
    if is_skipped_disjunctive_disease(row):
        return DISJUNCTIVE_DISEASE_EXCLUSION_DETAIL
    if is_skipped_syndrome(row):
        return SYNDROME_EXCLUSION_DETAIL
    if is_replaced_class(row):
        return REPLACED_CLASS_EXCLUSION_DETAIL
    return ""


def is_ogms_disease_definition(definition: str) -> bool:
    """True for the OGMS disease definition: 'A disease is a disposition (i) to
    undergo pathological processes that (ii) exists in an organism because of one
    or more disorders in that organism.' Robust to the (i)/(ii) markers,
    punctuation, spacing, and process/processes."""
    n = re.sub(r"\(\s*i+\s*\)", " ", (definition or "").lower())
    n = re.sub(r"[^a-z ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return (
        "disease is a disposition" in n
        and "undergo pathological process" in n
        and "because of one or more disorders in that organism" in n
    )


def rule_definition_quality(row: dict) -> str:
    """
    good   — matches the OGMS disease definition (clear genus/differentia).
    absent — no definition text.
    poor   — definition present but very short (≤ 50 chars); likely just a label restatement.
    partial — definition contains a restriction marker (' that ', ' which ', ': ') suggesting
              genus/differentia structure but is not clearly complete.
    Rows with longer definitions are left blank for human review.
    """
    definition = row.get("definition", "").strip()
    if is_ogms_disease_definition(definition):
        return "good"
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
    if has_ifomis_disposition_parent(row):
        return "good"
    if not row.get("parent_labels", "").strip() and not row.get("parent_iris", "").strip():
        return "absent"
    return ""


NOT_GROUNDED_CATEGORIES = {"", "unclear_model", "no_grounded_model", "not_applicable"}


def is_grounded_row(row: dict) -> bool:
    """True when the prefilled disease_model_category is a real ontological
    grounding (any category except unclear_model / no_grounded_model /
    not_applicable). Mirrors is_grounded in review_consistency_checks."""
    return rule_disease_model_category(row).strip() not in NOT_GROUNDED_CATEGORIES


def rule_entity_quality_score(row: dict) -> str:
    """
    Prefill the entity quality score from the extraction evidence:

      3 — ontologically grounded (a real disease_model_category) AND
          parentage_quality == good AND definition_quality == good AND no
          logical inconsistency AND a stated pathology grounding AND a stance on
          crisp vs graded. This is the strong, well-defined-entity case
          and mirrors Rule 10 in review_consistency_checks / the Violations tab.
      2 — grounded via an IFOMIS/BFO disposition parent (good parent, but the
          definition is not the near-certain OGMS-style 'good').
      1 — core evidence missing: no definition, no comment, and no parent.
      0 — reserved for excluded classes (skipped in favour of a disease sibling).

    Blank when the evidence is insufficient to decide (left for the reviewer).
    """
    if is_skipped_in_favor_of_disease(row):
        return "0"
    # Rule 10: grounded + good parent + good definition (+ no logical
    # inconsistency) -> a strong, well-defined entity scores 3. Checked before
    # the disposition -> 2 shortcut so a well-defined disposition scores 3, not 2.
    if (
        is_grounded_row(row)
        and rule_parentage_quality(row).strip() == "good"
        and rule_definition_quality(row).strip() == "good"
        and not row.get("logical_inconsistency", "").strip()
        and row.get("pathological_grounding", "").strip() in {"statistical", "evolutionary_function", "normative", "primitive_criteria"}
        and row.get("crisp_vs_graded", "").strip() not in {"", "silent"}
    ):
        return "3"
    if has_ifomis_disposition_parent(row):
        return "2"
    has_definition = bool(row.get("definition", "").strip())
    has_comment = bool(row.get("comments", "").strip())
    has_parent = bool(row.get("parent_labels", "").strip() or row.get("parent_iris", "").strip())
    if not has_definition and not has_comment and not has_parent:
        return "1"
    return ""


def rule_review_comment(row: dict) -> str:
    """Prefill the single free-text review comment with a first-pass modelling
    interpretation (what the ontology itself says). The reviewer then edits this
    one field, which also absorbs any audit/notes text.

    Priority order (highest confidence first):
    1. BFO IRI match in parent_iris — authoritative, IRI-based.
    2. 'disposition' in label, definition, or parent labels — near-certain (per domain rule).
    3. Unambiguous keywords in parent_labels ('process', 'finding', 'syndrome',
       'disorder', 'quality') — strong structural signal.
    4. BFO anchor text fallback for remaining BFO-anchored cases.
    """
    parent_iris = row.get("parent_iris", "")
    if has_ifomis_disposition_parent(row):
        return IFOMIS_DISPOSITION_INTERPRETATION

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


KEYWORD_GROUNDING = [
    ("biotop", "entity_as_biotop:condition"),
    ("menelas", "entity_as_kantian_state"),
]


def keyword_grounding(*values: str) -> str:
    """If a grounding keyword appears in any of the given text values (including
    the class IRI), return the model category it implies. 'biotop' anywhere ->
    entity_as_biotop:condition; 'menelas' anywhere -> entity_as_kantian_state."""
    blob = " ".join(v for v in values if v).lower()
    for keyword, category in KEYWORD_GROUNDING:
        if keyword in blob:
            return category
    return ""


def keyword_grounding_for_row(row: dict) -> str:
    return keyword_grounding(
        row.get("class_iri", ""), row.get("definition", ""), row.get("comments", ""),
        row.get("synonyms", ""), row.get("preferred_label", ""), row.get("term", ""),
        row.get("parent_iris", ""), row.get("parent_labels", ""), row.get("bfo_anchor", ""),
        row.get("ontology_title", ""), row.get("ontology_description", ""),
        row.get("review_comment", ""),
        row.get("manual_exclusion_detail", ""),
    )


def rule_disease_model_category(row: dict) -> str:
    """
    Pre-fill only when the signal is near-certain:
    0. Keyword grounding: 'biotop' -> entity_as_biotop:condition, 'menelas' ->
       entity_as_kantian_state (matched anywhere, including the class IRI).
    1. BFO IRI in parent_iris with an unambiguous disease-model mapping.
    2. 'disposition' in label, definition, or parent labels.
    3. 'process' in parent labels (structural signal from hierarchy).
    4. 'finding' in parent labels.
    5. 'syndrome' in parent labels.
    6. 'disorder' in parent labels.
    Ambiguous cases ('patholog', 'condition') are left blank.
    """
    kg = keyword_grounding_for_row(row)
    if kg:
        return kg
    parent_iris = row.get("parent_iris", "")
    if has_ifomis_disposition_parent(row):
        return "entity_as_bfo:disposition"

    for bfo_id in _bfo_ids_in_iris(parent_iris):
        if bfo_id in BFO_DISEASE_MODEL:
            return BFO_DISEASE_MODEL[bfo_id]

    text = _text(
        row.get("preferred_label", ""),
        row.get("definition", ""),
        row.get("parent_labels", ""),
    )
    if "conceptual entity" in text or "conceptualentity" in text:
        return "no_grounded_model"
    if "information content entity" in text or "information entity" in text:
        return "no_grounded_model"
    if "disposition" in text:
        # Reaching here means the class is disposition-flavoured but has NO BFO
        # anchor (the IFOMIS-parent check and the BFO_DISEASE_MODEL loop above
        # already returned entity_as_bfo:disposition for genuine BFO cases).
        # So this is a disposition in some other/undeclared upper-ontology sense.
        return "entity_as_disposition_non_bfo"

    parent_text = row.get("parent_labels", "").lower()
    if "process" in parent_text:
        return "entity_as_process"
    if "finding" in parent_text:
        return "entity_as_finding"
    if "syndrome" in parent_text:
        return "entity_as_syndrome"
    if "disorder" in parent_text:
        return "entity_as_disorder"

    return ""


def rule_ontological_category(row: dict, disease_model_category: str) -> str:
    """BFO SNAP/SPAN split: continuant vs occurrent.

    Filled only where the anchor is certain (per user decision "blank unless
    anchored"): disposition / realizable entity / dependent continuant /
    quality -> continuant; process -> occurrent. Finding, syndrome, disorder,
    biotop:condition and kantian_state have no crisp BFO anchor and are left
    blank for human review. A raw BFO parent IRI is used as a fallback signal.
    """
    dmc = (disease_model_category or "").strip()
    if dmc in OCCURRENT_MODEL_CATEGORIES:
        return "occurrent"
    if dmc in CONTINUANT_MODEL_CATEGORIES:
        return "continuant"
    bfo_ids = set(_bfo_ids_in_iris(row.get("parent_iris", "")))
    if bfo_ids & BFO_OCCURRENT_IDS:
        return "occurrent"
    if bfo_ids & BFO_CONTINUANT_IDS:
        return "continuant"
    return ""


def rule_no_grounded_subtype(row: dict, disease_model_category: str) -> str:
    """Refine 'no_grounded_model' into how the ontology avoided a grounded model.

    Only fires when disease_model_category == 'no_grounded_model'. Best-effort
    structural signal; leaves blank when no pattern is clear so a human decides.
      - finding_or_phenotype_route: disease subsumed under a clinical
        finding / observation / sign-symptom / phenotype umbrella (SNOMED-style
        non-decompositional classification).
      - information_model_wrapper: disease placed under a generic structural /
        data container (Concept, Model item, Patient record, phenome,
        BiomedicineConcept, linkML/FHIR class) to leverage a graph/data schema.
      - application_scoped_narrow: disease redefined for one narrow application
        (adherence/influencing factor, exposure outcome, protein annotation),
        not a general disease universal.
    """
    if (disease_model_category or "").strip() != "no_grounded_model":
        return ""
    parents = " ".join([
        row.get("parent_labels", ""),
        row.get("parent_iris", ""),
    ]).lower()
    defn = row.get("definition", "").lower()
    comment = row.get("review_comment", "").lower()
    blob = " ".join((parents, defn, comment))

    hierarchy_finding_signals = (
        "phenotype", "phenomenon", "phenomena", "phenome",
        "finding", "observation",
    )
    finding_signals = (
        "clinical finding", "finding", "phenotyp", "observation",
        "sign/symptom", "sign or symptom", "sign, symptom", "symptom",
        "pathological phenomena", "pathological phenotype",
    )
    wrapper_signals = (
        "concept", "model item", "patient record", "patient-record",
        "patientrecord", "phenome", "biomedicineconcept", "biomedicine concept",
        "linkml", "fhir", "information model", "data ", "record", "construct",
        "characteristic", "annotation", "biophysicochemical",
    )
    narrow_signals = (
        "influencing factor", "adherence", "exposure", "narrow scope",
        "protein annotation", "single use", "application", "outcome of the exposure",
    )

    if any(s in parents for s in hierarchy_finding_signals):
        return "finding_or_phenotype_route"

    # Application-scoped narrowness is otherwise the most specific claim.
    if any(s in blob for s in narrow_signals):
        return "application_scoped_narrow"
    if any(s in blob for s in finding_signals):
        return "finding_or_phenotype_route"
    if any(s in blob for s in wrapper_signals):
        return "information_model_wrapper"
    return ""


def rule_pathological_grounding(row: dict) -> str:
    """Coupled decision #2 — what grounds 'pathological/abnormal', read from the
    class definition. Heuristic first-pass suggestion (human confirms/overrides
    in the review UI). Returns one of the UI's controlled values, or "" when the
    definition gives no usable signal (or is not in English / mixed).

    UI vocabulary: statistical | evolutionary_function | normative |
    primitive_criteria | undefined | not_applicable.
    """
    d = (row.get("definition", "") or "").lower()
    if not d.strip():
        return ""                                   # no definition -> let human decide
    if not any(ch.isalpha() and ord(ch) < 128 for ch in d):
        return ""                                   # non-latin / needs language review

    harm = any(w in d for w in ["discomfort", "distress", "suffering", "detrimental",
                                "harm", "disvalue", "impair", "burden", "well-being",
                                "wellbeing", "quality of life", "damage", "injur"])
    dysf = any(w in d for w in ["dysfunction", "malfunction", "disruption of",
                                "impairment of function", "loss of function", "abnormal function"])
    evol = any(w in d for w in ["evolution", "selected function", "natural function",
                                "designed to", "biological function"])
    stat = any(w in d for w in ["normal function", "species-typical", "statistical",
                                "below normal", "typical function", "normal range",
                                "biologically normal"])
    disorder_based = ("disposition" in d and "disorder" in d) or "physical basis" in d
    primitive = any(w in d for w in ["pathologic process", "pathological process",
                                     "pathologic state", "pathological state", "morbid",
                                     "characteristic set of signs", "signs and symptoms",
                                     "clinicopatholog"])

    if (dysf and harm) or evol:
        return "evolutionary_function"             # Wakefield/Schwartz harmful dysfunction
    if stat and not harm:
        return "statistical"                       # Boorse sub-normal function
    if harm and not dysf and not stat:
        return "normative"                         # harm/disvalue
    if primitive and not (harm or dysf or stat):
        return "primitive_criteria"                # Hucklenbroich criteria-defined
    if disorder_based:
        return "undefined"                         # OGMS: imports a notion, never states which
    if dysf or harm or stat or primitive:
        return ""                                   # mixed cues -> human call
    return "undefined"                             # has a definition but grounds nothing


def rule_reality_vs_classification(
    row: dict,
    disease_model_category: str,
    no_grounded_model_subtype: str,
) -> str:
    """Coupled decision #4 — what 'disease' denotes.

    Strong reality-side model categories are prefilled as biological_state.
    Mixed/unclear models get their direct buckets. For no_grounded_model we only
    prefill nosological_category where the subtype shows a classification,
    finding/phenotype, or information-wrapper route; no_grounded_model does not
    universally imply nosology.
    """
    dmc = (disease_model_category or "").strip()
    subtype = (no_grounded_model_subtype or "").strip()
    if dmc in BIOLOGICAL_STATE_MODEL_CATEGORIES:
        return "biological_state"
    if dmc == "mixed_model":
        return "conflated"
    if dmc == "unclear_model":
        return "unclear"
    if dmc == "no_grounded_model" and subtype in NOSOLOGICAL_NO_GROUNDED_SUBTYPES:
        return "nosological_category"

    text = _text(
        row.get("preferred_label", ""),
        row.get("definition", ""),
        row.get("parent_labels", ""),
        row.get("ontology_title", ""),
        row.get("ontology_description", ""),
    )
    if dmc == "no_grounded_model" and any(
        signal in text
        for signal in (
            "classification", "taxonomy", "terminology", "controlled vocabulary",
            "diagnosis code", "diagnostic category", "disease category",
            "disease classification", "nosology", "nosological",
        )
    ):
        return "nosological_category"
    if any(signal in text for signal in ("patient stratification", "precision medicine", "personalized medicine")):
        return "precision_medicine_stratification"
    if any(signal in text for signal in ("burden of illness", "patient experience", "quality of life", "suffering")):
        return "illness_role"
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
    row["manual_exclusion_detail"]    = rule_exclusion_detail(enriched)
    row["definition_quality"]         = rule_definition_quality(enriched)
    row["comment_quality"]            = rule_comment_quality(enriched)
    row["parentage_quality"]          = rule_parentage_quality(enriched)
    row["entity_quality_score"]       = rule_entity_quality_score(enriched)
    row["review_comment"]             = rule_review_comment(enriched)
    row["disease_model_category"]     = rule_disease_model_category(enriched)
    row["no_grounded_model_subtype"]  = rule_no_grounded_subtype(enriched, row["disease_model_category"])
    row["ontological_category"]       = rule_ontological_category(enriched, row["disease_model_category"])
    row["pathological_grounding"]     = rule_pathological_grounding(enriched)
    row["reality_vs_classification"]  = rule_reality_vs_classification(
        enriched,
        row["disease_model_category"],
        row["no_grounded_model_subtype"],
    )
    if (
        row["definition_quality"] == "absent"
        and row["comment_quality"] == "absent"
        and row["parentage_quality"] in {"poor", "absent"}
    ):
        row["pathological_grounding"] = "undefined"
    if (
        row["definition_quality"] == "absent"
        and row["comment_quality"] == "absent"
        and row["parentage_quality"] == "absent"
    ):
        row["ontological_category"] = "no_continuant_occurrent_commitment"
        row["crisp_vs_graded"] = "silent"
        row["reality_vs_classification"] = "unclear"
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


def normalise_manual_row(row: dict) -> dict:
    """Apply deterministic implications of manual source-type choices."""
    normalised = dict(row)
    if normalised.get("ontology_type_manual") == "thesaurus":
        normalised["manual_include_status"] = "exclude"
        normalised["manual_exclusion_reason"] = "terminology_not_ontology"
        if not normalised.get("manual_exclusion_detail"):
            normalised["manual_exclusion_detail"] = THESAURUS_EXCLUSION_DETAIL
        for field in THESAURUS_REVIEW_DISABLED_FIELDS:
            normalised[field] = ""
        if not normalised.get("review_comment"):
            normalised["review_comment"] = THESAURUS_EXCLUSION_DETAIL
    elif normalised.get("manual_include_status") != "exclude":
        normalised["manual_exclusion_reason"] = ""
        normalised["manual_exclusion_detail"] = ""
    if normalised.get("manual_include_status") == "exclude" \
       and normalised.get("manual_exclusion_reason") == "out_of_scope":
        normalised["disease_model_category"] = "not_applicable"
    return normalised


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    with MASTER_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        enriched_rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    register_ontology_disease_context(enriched_rows)

    output_rows = []
    n_prefilled = n_preserved = 0

    for enriched in enriched_rows:
        prefilled = prefill_row(enriched)
        manual = normalise_manual_row(merge_rows(enriched, prefilled))
        row = dict(enriched)
        for field in FIELDNAMES:
            previous = enriched.get(field, "")
            row[field] = manual.get(field, "")
            if previous.strip():
                n_preserved += 1
            elif row[field].strip():
                n_prefilled += 1
        output_rows.append(row)

    output_fieldnames = list(dict.fromkeys(fieldnames + FIELDNAMES))
    temporary = MASTER_CSV.with_suffix(MASTER_CSV.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)
    temporary.replace(MASTER_CSV)

    print(f"Updated {len(output_rows)} rows in {MASTER_CSV}")
    print(f"  blank manual cells prefilled: {n_prefilled}; existing values preserved: {n_preserved}")

    from collections import Counter
    report_fields = [
        "manual_include_status", "ontology_type_manual", "native_or_imported_manual",
        "definition_quality", "comment_quality", "parentage_quality",
        "review_comment", "disease_model_category",
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
