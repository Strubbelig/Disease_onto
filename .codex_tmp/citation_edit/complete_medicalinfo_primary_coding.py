#!/usr/bin/env python3
"""Complete the required model code for the user-included MEDICALINFO row."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "Scoping review" / "Python scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from review_extraction_pipeline import (  # noqa: E402
    ReviewExtractionPipeline,
    ReviewPipelineConfig,
    read_csv_rows,
)


target_iri = "http://webprotege.stanford.edu/R8O0uGFaO8DaQeagclBYpUV"
config = ReviewPipelineConfig()
pipeline = ReviewExtractionPipeline(config)
rows = read_csv_rows(config.enriched_csv)
updated = 0

for row in rows:
    if row.get("class_iri") != target_iri:
        continue
    if row.get("publication_eligibility_override") != "include":
        raise SystemExit("MEDICALINFO is not currently user-included; refusing to alter its coding.")
    if row.get("definition") or row.get("comment") or row.get("parent_iris") or row.get("parent_labels"):
        raise SystemExit("MEDICALINFO now has substantive evidence; manual model reassessment is required.")
    row["disease_model_category"] = "no_grounded_model"
    updated += 1

if updated != 1:
    raise SystemExit(f"Expected one MEDICALINFO target row; found {updated}.")

pipeline._write_master_review_rows(rows)
print(f"Completed disease_model_category for {target_iri}")
