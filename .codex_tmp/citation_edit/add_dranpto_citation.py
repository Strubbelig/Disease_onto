#!/usr/bin/env python3
"""Add the verified DRANPTO modelling citation to the master review CSV."""

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
    "modelling_citation_source_ontology_id": "DRANPTO",
    "modelling_citation_status": "cited",
    "modelling_citation_confidence": "manual_verified",
    "modelling_citation_doi": "10.1002/trc2.12061",
    "modelling_citation_pmid": "32995470",
    "modelling_citation_pmcid": "PMC7507392",
    "modelling_citation_url": "https://doi.org/10.1002/trc2.12061",
    "modelling_citation_publication_title": (
        "Developing an ontology for representing the domain knowledge specific to "
        "non-pharmacological treatment for agitation in dementia."
    ),
    "modelling_citation_authors": (
        "Zhang Z; Yu P; Chang HCR; Lau SK; Tao C; Wang N; Yin M; Deng C"
    ),
    "modelling_citation_year": "2020",
    "modelling_citation_venue": "Alzheimers Dement (N Y)",
    "modelling_citation_bibliographic_citation": (
        "Zhang Z; Yu P; Chang HCR; Lau SK; Tao C; Wang N; Yin M; Deng C. (2020). "
        "Developing an ontology for representing the domain knowledge specific to "
        "non-pharmacological treatment for agitation in dementia. Alzheimers Dement (N Y). "
        "6(1):e12061. doi:10.1002/trc2.12061. PMID:32995470; PMCID:PMC7507392."
    ),
    "modelling_citation_lookup_source": (
        "User supplied; verified against Crossref DOI 10.1002/trc2.12061 and PubMed PMID 32995470"
    ),
    "modelling_citation_source": "Master CSV citation record; Crossref and PubMed verification",
    "modelling_citation_approved": "yes",
    "modelling_citation_assignment_flag": "ok",
    "modelling_citation_assignment_flag_reason": (
        "The publication explicitly reports development of the ontology represented by DRANPTO "
        "for non-pharmacological treatment of agitation in dementia."
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
    if source_id == "DRANPTO" or row.get("ontology", "").strip().upper() == "DRANPTO":
        row.update(citation)
        updated += 1

if updated == 0:
    raise SystemExit("No DRANPTO row found in the master CSV.")

pipeline._write_master_review_rows(rows)
print(f"Updated {updated} DRANPTO row(s) in {config.enriched_csv}")
