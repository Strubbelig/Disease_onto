#!/usr/bin/env python3
"""Reconcile the PATEL BioPortal submission with the later COVID19-IBO record."""

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
    "modelling_citation_source_ontology_id": "PATEL",
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
    "modelling_citation_lookup_source": (
        "User supplied; verified against PubMed PMID 34667368 and BioPortal submission metadata"
    ),
    "modelling_citation_source": "Master CSV citation record; PubMed and BioPortal verification",
    "modelling_citation_approved": "yes",
    "modelling_citation_assignment_flag": "ok",
    "modelling_citation_assignment_flag_reason": (
        "PATEL v1 and COVID19-IBO v1.5 share the same submitter, contact, and ontology description; "
        "PATEL is the earlier BioPortal submission of the ontology described by this publication."
    ),
    "modelling_citation_assignment_checked_at": checked_at,
}

updated = 0
for row in rows:
    if row.get("ontology", "").strip().upper() != "PATEL":
        continue
    row.update(citation)
    row["manual_include_status"] = "exclude"
    row["manual_exclusion_reason"] = "replaced_by_better_native_disease_model_candidate"
    row["manual_exclusion_detail"] = (
        "Earlier BioPortal v1 submission of Covid19-IBO; retained as a screening and review record, "
        "but the later formally named COVID19-IBO v1.5 record is used for independent synthesis."
    )
    row["publication_eligibility_override"] = ""
    row["publication_ambiguity_note"] = (
        "BioPortal metadata identifies PATEL as the earlier v1 submission of Covid19-IBO; it is "
        "retained for provenance and excluded from independent ontology counts."
    )
    updated += 1

if updated != 1:
    raise SystemExit(f"Expected one PATEL row; found {updated}.")

pipeline._write_master_review_rows(rows)
print("Reconciled PATEL as the earlier Covid19-IBO submission and attached its modelling citation.")
