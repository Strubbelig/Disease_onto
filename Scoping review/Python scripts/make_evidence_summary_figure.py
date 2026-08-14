#!/usr/bin/env python3
"""Generate the empirical summary figure for the disease-artifact study.

The figure is calculated from included rows in the sole editable master table.
Run this script after changing class-level review decisions:

    python3 "Scoping review/Python scripts/make_evidence_summary_figure.py"

Outputs:
    Figures/disease_model_evidence_summary.png
    Figures/disease_model_evidence_summary.svg
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


SCRIPT_DIR = Path(__file__).resolve().parent
REVIEW_DIR = SCRIPT_DIR.parent
MASTER = REVIEW_DIR / "Extraction Tables" / "disease_terms_review_enriched.csv"
FIGURE_DIR = REVIEW_DIR / "Figures"
FIGURE_DIR.mkdir(exist_ok=True)

N_IN_SCOPE = 144
TEXT = "#20262e"
MUTED = "#66717d"
GRID = "#dde2e6"
GRAY = "#a5adb5"
PALE_GRAY = "#d7dce0"
BLUE = "#3f6f9f"
TEAL = "#2a8c82"
GREEN = "#438b57"
ORANGE = "#cf7b35"
MAGENTA = "#a7597a"
GOLD = "#bc9036"


def load_included_rows() -> list[dict[str, str]]:
    with MASTER.open(newline="", encoding="utf-8-sig") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if (row.get("effective_synthesis_status") or "").strip() == "include"
        ]
    if len(rows) != N_IN_SCOPE:
        raise ValueError(
            f"Expected {N_IN_SCOPE} included rows, found {len(rows)}. "
            "Update the manuscript denominator and this guard together."
        )
    return rows


def count(rows: list[dict[str, str]], field: str) -> Counter[str]:
    return Counter((row.get(field) or "").strip() or "(blank)" for row in rows)


def clean_axis(axis) -> None:
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.spines["bottom"].set_color(GRID)
    axis.tick_params(axis="y", length=0, colors=TEXT, labelsize=9)
    axis.tick_params(axis="x", colors=MUTED, labelsize=8)
    axis.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    axis.grid(axis="x", color=GRID, linewidth=0.7, zorder=0)
    axis.set_axisbelow(True)


def horizontal_bars(axis, labels, values, colors, panel_title, panel_letter) -> None:
    y_positions = list(range(len(labels)))[::-1]
    bars = axis.barh(y_positions, values, color=colors, height=0.62, zorder=3)
    axis.set_yticks(y_positions, labels)
    maximum = max(values)
    axis.set_xlim(0, maximum * 1.28)
    for bar, value in zip(bars, values):
        percentage = 100 * value / N_IN_SCOPE
        axis.text(
            value + maximum * 0.025,
            bar.get_y() + bar.get_height() / 2,
            f"{value} ({percentage:.0f}%)",
            va="center",
            ha="left",
            fontsize=8.5,
            color=TEXT,
        )
    clean_axis(axis)
    axis.set_title(panel_title, loc="left", fontsize=11, fontweight="bold", color=TEXT, pad=10)
    axis.text(
        -0.12,
        1.075,
        panel_letter,
        transform=axis.transAxes,
        fontsize=12,
        fontweight="bold",
        color=BLUE,
        va="top",
    )


def quality_panel(axis, rows: list[dict[str, str]]) -> None:
    fields = [
        ("Definition", "definition_quality"),
        ("Comment", "comment_quality"),
        ("Parentage", "parentage_quality"),
    ]
    levels = ["absent", "poor", "partial", "good", "not_applicable"]
    labels = {
        "absent": "Absent",
        "poor": "Poor",
        "partial": "Partial",
        "good": "Good",
        "not_applicable": "Not applicable",
    }
    colors = {
        "absent": GRAY,
        "poor": ORANGE,
        "partial": BLUE,
        "good": GREEN,
        "not_applicable": PALE_GRAY,
    }
    left = [0.0] * len(fields)
    for level in levels:
        values = [count(rows, field).get(level, 0) * 100 / N_IN_SCOPE for _, field in fields]
        bars = axis.barh(
            [2, 1, 0],
            values,
            left=left,
            color=colors[level],
            height=0.58,
            label=labels[level],
            zorder=3,
        )
        for bar, percentage, (_, field) in zip(bars, values, fields):
            raw = count(rows, field).get(level, 0)
            if percentage >= 7:
                axis.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    str(raw),
                    ha="center",
                    va="center",
                    fontsize=8.5,
                    fontweight="bold",
                    color="white" if level != "not_applicable" else TEXT,
                )
        left = [old + new for old, new in zip(left, values)]

    axis.set_xlim(0, 100)
    axis.set_yticks([2, 1, 0], [label for label, _ in fields])
    axis.set_xlabel("Percentage of included classes", fontsize=8.5, color=MUTED)
    axis.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    axis.grid(axis="x", color=GRID, linewidth=0.7, zorder=0)
    axis.set_axisbelow(True)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.spines["bottom"].set_color(GRID)
    axis.tick_params(axis="y", length=0, colors=TEXT, labelsize=9)
    axis.tick_params(axis="x", colors=MUTED, labelsize=8)
    axis.set_title("Annotation and hierarchy quality", loc="left", fontsize=11, fontweight="bold", color=TEXT, pad=10)
    axis.text(-0.12, 1.075, "D", transform=axis.transAxes, fontsize=12, fontweight="bold", color=BLUE, va="top")
    axis.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.28),
        ncol=3,
        frameon=False,
        fontsize=8,
        handlelength=1.4,
        columnspacing=1.2,
    )
    axis.text(
        0.5,
        -0.5,
        "Small comment segments (not labelled): poor 5, good 2, not applicable 1.",
        transform=axis.transAxes,
        fontsize=7.4,
        color=MUTED,
        ha="center",
    )


def build() -> None:
    rows = load_included_rows()
    categories = count(rows, "ontological_category")
    grounding = count(rows, "pathological_grounding")
    reality = count(rows, "reality_vs_classification")

    figure, axes = plt.subplots(2, 2, figsize=(11.5, 8.3))
    figure.subplots_adjust(left=0.18, right=0.97, top=0.86, bottom=0.21, wspace=0.48, hspace=0.7)
    figure.suptitle(
        "What the included disease classes explicitly commit to",
        x=0.5,
        y=0.965,
        fontsize=15,
        fontweight="bold",
        color=TEXT,
    )
    figure.text(
        0.5,
        0.925,
        "Class-level assessment of 144 included ontology artifacts",
        ha="center",
        fontsize=9.5,
        color=MUTED,
    )

    horizontal_bars(
        axes[0, 0],
        ["No commitment", "Continuant", "Occurrent", "Unclear", "Deliberate mix"],
        [
            categories["no_continuant_occurrent_commitment"],
            categories["continuant"],
            categories["occurrent"],
            categories["unclear"],
            categories["mixed_continuant_occurrent_model"],
        ],
        [GRAY, TEAL, ORANGE, PALE_GRAY, GOLD],
        "Continuant versus occurrent",
        "A",
    )
    horizontal_bars(
        axes[0, 1],
        ["Undefined", "Primitive criteria", "Evolutionary function", "Normative", "Statistical", "Not applicable"],
        [
            grounding["undefined"],
            grounding["primitive_criteria"],
            grounding["evolutionary_function"],
            grounding["normative"],
            grounding["statistical"],
            grounding["not_applicable"],
        ],
        [GRAY, BLUE, GREEN, MAGENTA, ORANGE, PALE_GRAY],
        "Grounding of pathologicality",
        "B",
    )
    horizontal_bars(
        axes[1, 0],
        ["Nosological category", "Biological state", "Unclear", "Conflated"],
        [
            reality["nosological_category"],
            reality["biological_state"],
            reality["unclear"],
            reality["conflated"],
        ],
        [BLUE, TEAL, PALE_GRAY, GOLD],
        "Reality versus classification",
        "C",
    )
    quality_panel(axes[1, 1], rows)

    output_png = FIGURE_DIR / "disease_model_evidence_summary.png"
    output_svg = FIGURE_DIR / "disease_model_evidence_summary.svg"
    figure.savefig(output_png, dpi=300, facecolor="white")
    figure.savefig(output_svg, facecolor="white")
    plt.close(figure)
    print(output_png)
    print(output_svg)


if __name__ == "__main__":
    build()
