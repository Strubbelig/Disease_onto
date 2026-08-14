#!/usr/bin/env python3
"""Update the user-supplied COVID19-IBO citation in the master review CSV."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "Scoping review" / "Python scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from review_extraction_pipeline import (  # noqa: E402
    ReviewExtractionPipeline,
    ReviewPipelineConfig,
    read_csv_rows,
)


config = ReviewPipelineConfig()
pipeline = ReviewExtractionPipeline(config)
rows = read_csv_rows(config.enriched_csv)
checked_at = datetime.now().astimezone().replace(microsecond=0).isoformat()

citation = {
    "modelling_citation_source_ontology_id": "COVID19-IBO",
    "modelling_citation_status": "cited",
    "modelling_citation_confidence": "manual_verified",
    "modelling_citation_doi": "10.1007/s00354-021-00136-0",
    "modelling_citation_pmid": "34667368",
    "modelling_citation_pmcid": "PMC8517947",
    "modelling_citation_url": "https://doi.org/10.1007/s00354-021-00136-0",
    "modelling_citation_publication_title": (
        "Covid19-IBO: A Covid-19 Impact on Indian Banking Ontology Along with an Efficient "
        "Schema Matching Approach."
    ),
    "modelling_citation_authors": "Patel A; Debnath NC; Mishra AK; Jain S",
    "modelling_citation_year": "2021",
    "modelling_citation_venue": "New Gener Comput",
    "modelling_citation_bibliographic_citation": (
        "Patel A; Debnath NC; Mishra AK; Jain S. (2021). Covid19-IBO: A Covid-19 Impact on "
        "Indian Banking Ontology Along with an Efficient Schema Matching Approach. New Gener "
        "Comput. 39(3-4):647-676. doi:10.1007/s00354-021-00136-0. PMID:34667368; "
        "PMCID:PMC8517947."
    ),
    "modelling_citation_lookup_source": "User supplied; verified against PubMed PMID 34667368",
    "modelling_citation_source": "Master CSV citation record; PubMed verification",
    "modelling_citation_approved": "yes",
    "modelling_citation_assignment_flag": "ok",
    "modelling_citation_assignment_flag_reason": (
        "Publication title and abstract explicitly identify and describe the Covid19-IBO ontology."
    ),
    "modelling_citation_assignment_checked_at": checked_at,
}

updated = 0
for row in rows:
    source_id = (
        row.get("modelling_citation_source_ontology_id", "")
        or row.get("native_ontology_guess", "")
        or row.get("ontology", "")
    ).strip().upper()
    if source_id == "COVID19-IBO" or row.get("ontology", "").strip().upper() == "COVID19-IBO":
        row.update(citation)
        updated += 1

if updated == 0:
    raise SystemExit("No COVID19-IBO row found in the master CSV.")

pipeline._write_master_review_rows(rows)
print(f"Updated {updated} COVID19-IBO row(s) in {config.enriched_csv}")
