#!/usr/bin/env python3
"""Generate the selection flow diagram for the disease-ontology artifact study.

The diagram is built *dynamically* from the generated review tables, so it stays
in sync with the extraction/annotation state. Re-run after any pipeline or
manual-annotation change:

    python3 "Scoping review/Python scripts/make_artifact_selection_flow_diagram.py"

Input (relative to the "Scoping review" folder):
    Extraction Tables/disease_terms_review_enriched.csv

Outputs:
    Figures/artifact_selection_flow_diagram.png   (300 dpi)
    Figures/artifact_selection_flow_diagram.svg   (vector)

No arguments required. Uses only the standard library + matplotlib.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
SCRIPT_DIR = Path(__file__).resolve().parent
REVIEW_DIR = SCRIPT_DIR.parent
TABLE_DIR = REVIEW_DIR / "Extraction Tables"
FIG_DIR = REVIEW_DIR / "Figures"
FIG_DIR.mkdir(exist_ok=True)

MASTER = TABLE_DIR / "disease_terms_review_enriched.csv"
EXCLUSION_REASON_LABELS = {
    "replaced_by_better_native_disease_model_candidate": "Replaced by a better native candidate",
    "terminology_not_ontology": "Clinical terminology / thesaurus, not an ontology",
    "out_of_scope": "Out of scope",
    "term_out_of_scope_not_disease_synonym": "Search-term hit not representing disease",
    "value_set_or_collection": "Value-set / collection",
    "duplicate_imported_term": "Duplicate imported term",
    "demo_or_training_resource": "Demo / training resource",
    "process_context_suppressed_when_disease_root_present": "Process-context term suppressed with disease root",
    "insufficient_metadata": "Insufficient metadata",
    "imported_or_reused_term_no_independent_analysis": "Imported/reused term without independent analysis",
    "webprotege_random_or_local_iri_unstable_provenance": "Unstable or local WebProtege IRI",
    "explicit_exact_match_to_canonical_disease_model": "Exact match to a canonical disease model",
    "defined_by_external_class_no_independent_analysis": "External definition without independent analysis",
}


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def gather_numbers() -> dict:
    """Read the CSVs and compute every number the diagram needs."""
    rows = load_rows(MASTER)

    charted_ontologies = len({(r.get("ontology") or "").strip() for r in rows if (r.get("ontology") or "").strip()})
    provenance_counts = Counter((r.get("native_or_imported_manual") or "unresolved").strip() or "unresolved" for r in rows)

    # --- Class-level review funnel ----------------------------------------- #
    def _final_status(row: dict) -> str:
        return (
            row.get("effective_synthesis_status")
            or row.get("manual_include_status")
            or ""
        ).strip()

    status = Counter(_final_status(r) for r in rows)
    n_total_classes = len(rows)
    n_include = status.get("include", 0)
    n_exclude = status.get("exclude", 0)
    n_pending = status.get("needs_user_decision", 0) + status.get("", 0)
    n_adjudicated = n_include + n_exclude

    excl_reasons = Counter()
    for r in rows:
        if _final_status(r) == "exclude":
            reason = (
                r.get("effective_synthesis_exclusion_reason")
                or r.get("manual_exclusion_reason")
                or "unspecified"
            ).strip() or "unspecified"
            excl_reasons[reason] += 1

    return {
        "charted_ontologies": charted_ontologies,
        "provenance_counts": provenance_counts,
        "n_total_classes": n_total_classes,
        "n_pending": n_pending,
        "n_adjudicated": n_adjudicated,
        "n_include": n_include,
        "n_exclude": n_exclude,
        "excl_reasons": excl_reasons,
    }


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #
MAIN = "#2c3e50"      # main box edge
MAIN_FILL = "#eaf2f8"
SIDE_FILL = "#fdf2e9"  # exclusion (side) boxes
SIDE_EDGE = "#b9770e"
INCL_FILL = "#e8f6ef"
INCL_EDGE = "#1e8449"
ARROW = "#34495e"


def box(ax, x, y, w, h, text, *, fill=MAIN_FILL, edge=MAIN, fontsize=9, weight="normal", align="center"):
    ax.add_patch(
        FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.015,rounding_size=0.08",
            linewidth=1.3, edgecolor=edge, facecolor=fill, zorder=2,
        )
    )
    ha = {"center": "center", "left": "left"}[align]
    tx = x if align == "center" else x - w / 2 + 0.18
    ax.text(tx, y, text, ha=ha, va="center", fontsize=fontsize,
            color="#1b2631", zorder=3, weight=weight, wrap=True,
            linespacing=1.08)


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=15,
            linewidth=1.3, color=ARROW, zorder=1, shrinkA=2, shrinkB=2,
        )
    )


# --------------------------------------------------------------------------- #
# Diagram
# --------------------------------------------------------------------------- #
def build(nums: dict):
    fig, ax = plt.subplots(figsize=(14.0, 9.0))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    cx = 3.55         # centre column x
    bw = 5.35         # main box width
    sx = 10.55        # side (routing/exclusion) column x
    sw = 5.75         # side box width

    # 1) Identification
    y1 = 9.34
    box(ax, cx, y1, bw, 0.66,
        "Registry and artifact retrieval\n"
        "BioPortal (primary) · OLS · OBO Foundry · targeted sources",
        fontsize=9.5, weight="bold")

    # 2) Automated screening
    y2 = 8.04
    box(ax, cx, y2, bw, 0.66,
        "Candidate normalization and routing\n(exact labels · scope · target refinement · provenance · reuse)",
        fontsize=9.5, weight="bold")
    arrow(ax, cx, y1 - 0.33, cx, y2 + 0.33)

    # Side box: routing rules. Appearance logs overlap because excluded/reused
    # appearances are deliberately retained as provenance, so they are not
    # presented as additive flow denominators.
    route_lines = [
        "• out-of-scope and collection terms flagged",
        "• weaker same-ontology targets replaced",
        "• imported and exact-match reuse identified",
        "• source appearances merged by exact class IRI",
        "• excluded/reused appearances retained for audit",
    ]
    side_h = 1.04
    ys = y2
    box(ax, sx, ys, sw, side_h,
        "Automated and deterministic routing\n" + "\n".join(route_lines),
        fill=SIDE_FILL, edge=SIDE_EDGE, fontsize=8.0, align="left")
    arrow(ax, cx + bw / 2, y2, sx - sw / 2, ys)

    # 3) Unique class records assembled
    y3 = 6.62
    box(ax, cx, y3, bw, 0.72,
        f"Unique class records assembled after IRI de-duplication\n"
        f"{nums['n_total_classes']} class IRIs from {nums['charted_ontologies']} ontology identifiers",
        fontsize=9.5, weight="bold")
    arrow(ax, cx, y2 - 0.33, cx, y3 + 0.36)

    # Side box: denominator note
    yb = 6.60
    box(ax, sx, yb, sw, 0.62,
        "Primary analytical denominator\n"
        f"{nums['n_total_classes']} unique class IRIs\n"
        "Registry appearances are provenance, not independent observations",
        fill=SIDE_FILL, edge=SIDE_EDGE, fontsize=8.2, align="left")
    arrow(ax, cx + bw / 2, y3, sx - sw / 2, yb)

    # 4) Assessed for eligibility (manual)
    y4 = 5.18
    box(ax, cx, y4, bw, 0.66,
        f"Class-level eligibility assessment\n"
        f"{nums['n_adjudicated']} decided · {nums['n_pending']} awaiting decision",
        fontsize=9.5, weight="bold")
    arrow(ax, cx, y3 - 0.36, cx, y4 + 0.33)

    # side box: manual exclusions with reasons
    reason_lines = [
        f"• {EXCLUSION_REASON_LABELS.get(k, k)}: {v}"
        for k, v in nums["excl_reasons"].most_common()
    ]
    mside_h = 2.20
    ym = 4.38
    box(ax, sx, ym, sw, mside_h,
        f"Excluded after human assessment: {nums['n_exclude']}\n" + "\n".join(reason_lines),
        fill=SIDE_FILL, edge=SIDE_EDGE, fontsize=8.6, align="left")
    arrow(ax, cx + bw / 2, y4, sx - sw / 2, ym + 0.35)

    # 5) Included
    y5 = 3.72
    box(ax, cx, y5, bw, 0.72,
        f"Included in artifact analysis\n"
        f"{nums['n_include']} classes",
        fill=INCL_FILL, edge=INCL_EDGE, fontsize=10.5, weight="bold")
    arrow(ax, cx, y4 - 0.33, cx, y5 + 0.36)

    # 6) Provenance note (context band)
    pc = nums["provenance_counts"]
    y6 = 1.35
    xmid = 7.0
    span_w = 10.4
    box(ax, xmid, y6, span_w, 0.72,
        f"Recorded class provenance (all {nums['n_total_classes']} unique IRIs):\n"
        f"native: {pc.get('native', 0)}   ·   imported/reused: {pc.get('imported', 0)}   ·   "
        f"unresolved or not recorded: {pc.get('unresolved', 0)}",
        fill="#f4f6f7", edge="#7f8c8d", fontsize=8.8)

    ax.text(xmid, 0.62,
            "Unit of analysis: unique class IRI. Source appearances may occur in both routing and exclusion logs because\n"
            "reused or excluded appearances remain in the audit trail; they are not added as independent observations.",
            ha="center", va="center", fontsize=7.8, color="#566573", style="italic",
            linespacing=1.08)

    fig.tight_layout()
    png = FIG_DIR / "artifact_selection_flow_diagram.png"
    svg = FIG_DIR / "artifact_selection_flow_diagram.svg"
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png, svg


def main() -> None:
    nums = gather_numbers()
    png, svg = build(nums)
    print("Ontology-artifact selection flow generated from live assessment tables:")
    print(f"  ontology ids   : {nums['charted_ontologies']}")
    print(f"  charted classes: {nums['n_total_classes']} after IRI de-duplication")
    print(f"  decided        : {nums['n_adjudicated']}  ->  "
          f"included {nums['n_include']} / excluded {nums['n_exclude']}")
    print(f"  pending        : {nums['n_pending']}")
    print(f"  wrote {png}")
    print(f"  wrote {svg}")


if __name__ == "__main__":
    main()
