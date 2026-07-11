#!/usr/bin/env python3
"""Generate the PRISMA-ScR flow diagram for the disease-modelling scoping review.

The diagram is built *dynamically* from the generated review tables, so it stays
in sync with the extraction/annotation state. Re-run after any pipeline or
manual-annotation change:

    python3 "Scoping review/Python scripts/make_prisma_flow_diagram.py"

Inputs (relative to the "Scoping review" folder):
    Extraction Tables/ontology_source_exclusion_counts_for_flow_figure.csv
    Extraction Tables/disease_terms_manual_annotations.csv
    Extraction Tables/ontology_source_appearance_routes_summary.csv

Outputs:
    Figures/prisma_scr_flow_diagram.png   (300 dpi)
    Figures/prisma_scr_flow_diagram.svg   (vector)

No arguments required. Uses only the standard library + matplotlib.
"""
from __future__ import annotations

import csv
from collections import Counter, OrderedDict
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

EXCL_COUNTS = TABLE_DIR / "ontology_source_exclusion_counts_for_flow_figure.csv"
ANNOTATIONS = TABLE_DIR / "disease_terms_manual_annotations.csv"
ROUTES = TABLE_DIR / "ontology_source_appearance_routes_summary.csv"
REVIEW = TABLE_DIR / "disease_terms_review.csv"

# Human-readable labels for the automated-screen reason codes.
SCREEN_LABELS = {
    "webprotege_random_or_local_iri_unstable_provenance": "Unstable/local (webProtégé) IRI",
    "value_set_collection_not_independent_ontology": "Value-set collection, not an ontology",
    "term_out_of_scope_not_disease_synonym": "Out of scope (not a disease synonym; e.g. injury)",
    "process_context_suppressed_when_disease_root_present": "`pathological process` suppressed (disease root present)",
    "replaced_by_better_native_disease_model_candidate": "Replaced by a better native candidate",
    "syndrome_suppressed_when_disease_present": "`syndrome` suppressed (disease class present)",
    "explicit_exact_match_to_canonical_disease_model": "Exact-match to a canonical disease root",
    "defined_by_external_class_no_independent_analysis": "Defined by an external class",
    "imported_or_reused_term_no_independent_analysis": "Imported/reused term (reuse, not a new model)",
}
EXCLUSION_REASON_LABELS = {
    "replaced_by_better_native_disease_model_candidate": "Replaced by a better native candidate",
    "terminology_not_ontology": "Clinical terminology / thesaurus, not an ontology",
    "out_of_scope": "Out of scope",
    "value_set_or_collection": "Value-set / collection",
    "duplicate_imported_term": "Duplicate imported term",
    "demo_or_training_resource": "Demo / training resource",
}


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def gather_numbers() -> dict:
    """Read the CSVs and compute every number the diagram needs."""
    excl = load_rows(EXCL_COUNTS)
    ann = load_rows(ANNOTATIONS)
    routes = load_rows(ROUTES)
    review = load_rows(REVIEW) if REVIEW.exists() else []

    # --- Identification (appearance level) --------------------------------- #
    total_appearances = len(routes)
    # Ontology breadth of the *charted* candidate classes (review table's
    # 'ontology' field), which is the meaningful "how many ontologies" figure.
    charted_ontologies = len({(r.get("ontology") or "").strip() for r in review if (r.get("ontology") or "").strip()})

    route_counts = Counter((r.get("ontology_review_route") or "").strip() for r in routes)

    # --- Automated screening exclusions ------------------------------------ #
    def _int(v: str) -> int:
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    screens = OrderedDict()
    total_excl_appearances = 0
    total_excl_classes = 0
    for r in excl:
        code = (r.get("exclusion_reason_code") or "").strip()
        app = _int(r.get("excluded_source_ontology_appearances"))
        cls = _int(r.get("excluded_unique_class_iris"))
        screens[code] = {
            "label": SCREEN_LABELS.get(code, code),
            "appearances": app,
            "classes": cls,
            "stage": (r.get("exclusion_stage") or "").strip(),
        }
        total_excl_appearances += app
        total_excl_classes += cls

    # --- Class-level review funnel ----------------------------------------- #
    status = Counter((r.get("manual_include_status") or "").strip() for r in ann)
    n_total_classes = len(ann)
    n_include = status.get("include", 0)
    n_exclude = status.get("exclude", 0)
    n_blank = status.get("", 0)  # auto-excluded / should-not-appear per review logic
    n_adjudicated = n_include + n_exclude

    excl_reasons = Counter()
    for r in ann:
        if (r.get("manual_include_status") or "").strip() == "exclude":
            reason = (r.get("manual_exclusion_reason") or "unspecified").strip() or "unspecified"
            excl_reasons[reason] += 1

    return {
        "total_appearances": total_appearances,
        "charted_ontologies": charted_ontologies,
        "route_counts": route_counts,
        "screens": screens,
        "total_excl_appearances": total_excl_appearances,
        "total_excl_classes": total_excl_classes,
        "n_total_classes": n_total_classes,
        "n_blank": n_blank,
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
            boxstyle="round,pad=0.02,rounding_size=0.15",
            linewidth=1.3, edgecolor=edge, facecolor=fill, zorder=2,
        )
    )
    ha = {"center": "center", "left": "left"}[align]
    tx = x if align == "center" else x - w / 2 + 0.18
    ax.text(tx, y, text, ha=ha, va="center", fontsize=fontsize,
            color="#1b2631", zorder=3, weight=weight, wrap=True)


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
    fig, ax = plt.subplots(figsize=(15.5, 12.5))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 15)
    ax.axis("off")

    cx = 3.8          # centre column x
    bw = 5.6          # main box width  -> right edge 6.6
    sx = 11.1         # side (exclusion) column x
    sw = 6.8          # side box width  -> left edge 7.7

    # Title
    ax.text(cx, 14.6, "PRISMA-ScR flow — disease-modelling scoping review\n(ontology-artifact track)",
            ha="center", va="center", fontsize=13, weight="bold", color="#1b2631")

    # 1) Identification
    y1 = 13.4
    box(ax, cx, y1, bw, 1.0,
        f"Identification (ontology registries: BioPortal, OLS, OBO Foundry)\n"
        f"{nums['total_appearances']} source-ontology appearances "
        f"(registry contexts)",
        fontsize=9.5, weight="bold")

    # 2) Automated screening
    y2 = 11.9
    box(ax, cx, y2, bw, 0.9,
        "Automated eligibility screening\n(provenance · scope · target refinement · reuse)",
        fontsize=9.5, weight="bold")
    arrow(ax, cx, y1 - 0.5, cx, y2 + 0.45)

    # side box: automated exclusions breakdown
    screen_lines = [
        f"• {v['label']}: {v['appearances']} app / {v['classes']} cls"
        for v in nums["screens"].values()
    ]
    side_h = 0.42 * (len(screen_lines) + 1) + 0.3
    ys = y2
    box(ax, sx, ys, sw, side_h,
        f"Excluded by automated screens\n({nums['total_excl_appearances']} appearances)\n"
        + "\n".join(screen_lines),
        fill=SIDE_FILL, edge=SIDE_EDGE, fontsize=8.0, align="left")
    arrow(ax, cx + bw / 2, y2, sx - sw / 2, ys)

    # 3) Class-level candidates
    y3 = 9.9
    box(ax, cx, y3, bw, 1.0,
        f"Native candidate disease-model classes charted\n"
        f"{nums['n_total_classes']} unique class IRIs "
        f"from ~{nums['charted_ontologies']} ontologies",
        fontsize=9.5, weight="bold")
    arrow(ax, cx, y2 - 0.45, cx, y3 + 0.5)

    # side box: blanks (auto-excluded / should-not-appear per review logic)
    yb = 8.9
    box(ax, sx, yb, sw, 0.95,
        f"Removed by review logic before adjudication: {nums['n_blank']}\n"
        f"(auto-excluded, or should not have appeared\nin the candidate set per the screening rules)",
        fill=SIDE_FILL, edge=SIDE_EDGE, fontsize=8.2, align="left")
    arrow(ax, cx + bw / 2, y3 - 0.15, sx - sw / 2, yb)

    # 4) Assessed for eligibility (manual)
    y4 = 8.1
    box(ax, cx, y4, bw, 0.9,
        f"Assessed for eligibility at manual class-level review\n"
        f"{nums['n_adjudicated']} classes",
        fontsize=9.5, weight="bold")
    arrow(ax, cx, y3 - 0.5, cx, y4 + 0.45)

    # side box: manual exclusions with reasons
    reason_lines = [
        f"• {EXCLUSION_REASON_LABELS.get(k, k)}: {v}"
        for k, v in nums["excl_reasons"].most_common()
    ]
    mside_h = 0.42 * (len(reason_lines) + 1) + 0.3
    ym = 6.6
    box(ax, sx, ym, sw, mside_h,
        f"Excluded at manual review: {nums['n_exclude']}\n" + "\n".join(reason_lines),
        fill=SIDE_FILL, edge=SIDE_EDGE, fontsize=8.2, align="left")
    arrow(ax, cx + bw / 2, y4 - 0.1, sx - sw / 2, ym)

    # 5) Included
    y5 = 6.2
    box(ax, cx, y5, bw, 1.0,
        f"Included as independent disease-model implementations\n"
        f"{nums['n_include']} classes",
        fill=INCL_FILL, edge=INCL_EDGE, fontsize=10.5, weight="bold")
    arrow(ax, cx, y4 - 0.45, cx, y5 + 0.5)

    # 6) Appearance-route note (context band)
    rc = nums["route_counts"]
    y6 = 4.4
    xmid = ((cx - bw / 2) + (sx + sw / 2)) / 2.0
    span_w = (sx + sw / 2) - (cx - bw / 2) - 0.3
    box(ax, xmid, y6, span_w, 1.15,
        "Appearance-route context (all "
        f"{nums['total_appearances']} appearances):\n"
        f"independent analysis route: {rc.get('independent_analysis_route', 0)}   ·   "
        f"dependency-only: {rc.get('dependency_only_no_independent_analysis', 0)}\n"
        f"mixed: {rc.get('mixed_independent_and_dependency_appearances', 0)}   ·   "
        f"unknown namespace: {rc.get('unknown_namespace_needs_manual_check', 0)}",
        fill="#f4f6f7", edge="#7f8c8d", fontsize=8.6)

    ax.text(xmid, 3.55,
            "Units: 'app' = source-ontology appearance, 'cls' = unique class IRI. "
            "Dependency-only appearances are analysed at their native provider\n"
            "(OGMS / DOID / MONDO), not counted as independent models. "
            "Generated dynamically from the review tables.",
            ha="center", va="center", fontsize=7.6, color="#566573", style="italic")

    fig.tight_layout()
    png = FIG_DIR / "prisma_scr_flow_diagram.png"
    svg = FIG_DIR / "prisma_scr_flow_diagram.svg"
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png, svg


def main() -> None:
    nums = gather_numbers()
    png, svg = build(nums)
    print("PRISMA-ScR flow diagram generated from live review tables:")
    print(f"  identification : {nums['total_appearances']} appearances "
          f"(charted classes from ~{nums['charted_ontologies']} ontologies)")
    print(f"  auto-excluded  : {nums['total_excl_appearances']} appearances "
          f"across {len(nums['screens'])} screens")
    print(f"  charted classes: {nums['n_total_classes']} "
          f"(removed by review logic: {nums['n_blank']})")
    print(f"  adjudicated    : {nums['n_adjudicated']}  ->  "
          f"included {nums['n_include']} / excluded {nums['n_exclude']}")
    print(f"  wrote {png}")
    print(f"  wrote {svg}")


if __name__ == "__main__":
    main()
